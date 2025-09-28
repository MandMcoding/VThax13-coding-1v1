# pyright: reportMissingImports=false
from __future__ import annotations

from datetime import timedelta
import threading

from django.db.models import Q
from django.db.models.functions import Random
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Match, Question, MCQ, Coding

try:
    from authapp.models import Users  # optional, for usernames
except Exception:
    Users = None


# ---- DEMO-ONLY in-memory queue (single process). Use DB/Redis in prod.
_queue: list[int] = []
_queue_lock = threading.Lock()


def _no_store(resp: Response) -> Response:
    resp["Cache-Control"] = "no-store, no-cache, must-revalidate"
    resp["Pragma"] = "no-cache"
    return resp


def _username(uid: int, fallback: str) -> str:
    if not Users:
        return fallback
    u = Users.objects.filter(user_id=uid).first()
    return u.username if u else fallback


def _pick_first_question(kind: str) -> Question | None:
    kind = (kind or "mcq").lower()
    qs = Question.objects.filter(question_kind=kind)
    return qs.order_by(Random()).first() if qs.exists() else None


def _state(m: Match) -> dict:
    return {
        "id": m.id,
        "status": m.status,
        "kind": m.kind,
        "player1_id": m.player1_id,
        "player2_id": m.player2_id,
        "player1_username": _username(m.player1_id, "Player1"),
        "player2_username": _username(m.player2_id, "Player2"),
        "p1_ready": m.p1_ready,
        "p2_ready": m.p2_ready,
        "countdown_started_at": m.countdown_started_at.isoformat() if m.countdown_started_at else None,
        "begin_at": m.begin_at.isoformat() if m.begin_at else None,
        "question_id": m.first_question_id,
        "now": timezone.now().isoformat(),
    }


class QueueJoinView(APIView):
    """
    POST body: { "user_id": 123, "kind": "mcq" | "coding" }
    Returns:
      - {status:"queued"} OR
      - {status:"matched", match_id, opponent_id, opponent_username, kind, question_id}
    """
    def post(self, request):
        user_id = request.data.get("user_id")
        kind = (request.data.get("kind") or "mcq").lower()
        if not user_id:
            return _no_store(Response({"error": "user_id required"}, status=400))
        user_id = int(user_id)

        # Reuse existing pending/active match if any
        existing = Match.objects.only(
            "id", "player1_id", "player2_id", "status", "created_at", "kind", "first_question_id"
        ).filter(
            Q(player1_id=user_id) | Q(player2_id=user_id),
            status__in=["pending", "active"],
        ).order_by("-created_at").first()

        if existing:
            opp = existing.player2_id if existing.player1_id == user_id else existing.player1_id
            return _no_store(Response({
                "status": "matched",
                "match_id": existing.id,
                "opponent_id": opp,
                "opponent_username": _username(opp, "Opponent"),
                "kind": existing.kind,
                "question_id": existing.first_question_id,
            }))

        with _queue_lock:
            if user_id in _queue:
                return _no_store(Response({"status": "queued"}))

            _queue.append(user_id)

            if len(_queue) >= 2:
                a = _queue.pop(0)
                b = _queue.pop(0)

                q = _pick_first_question(kind)
                now = timezone.now()
                m = Match.objects.create(
                    player1_id=a,
                    player2_id=b,
                    kind=kind,
                    status="pending",
                    countdown_started_at=now,
                    begin_at=now + timedelta(seconds=3),
                    first_question=q,
                )

                payload = {
                    "status": "matched",
                    "match_id": m.id,
                    "kind": m.kind,
                    "question_id": m.first_question_id,
                }
                if user_id == a:
                    payload.update({"opponent_id": b, "opponent_username": _username(b, "PlayerB")})
                else:
                    payload.update({"opponent_id": a, "opponent_username": _username(a, "PlayerA")})
                return _no_store(Response(payload))

        return _no_store(Response({"status": "queued"}))


class QueueCheckView(APIView):
    """GET ?user_id=123  -> matched match (if any)"""
    def get(self, request):
        user_id = request.GET.get("user_id")
        if not user_id:
            return _no_store(Response({"error": "user_id required"}, status=400))
        user_id = int(user_id)

        m = Match.objects.only(
            "id", "player1_id", "player2_id", "status", "created_at", "kind", "first_question_id"
        ).filter(
            Q(player1_id=user_id) | Q(player2_id=user_id),
            status__in=["pending", "active"],
        ).order_by("-created_at").first()

        if not m:
            return _no_store(Response({"status": "waiting"}))

        opp = m.player2_id if m.player1_id == user_id else m.player1_id
        return _no_store(Response({
            "status": "matched",
            "match_id": m.id,
            "opponent_id": opp,
            "opponent_username": _username(opp, "Opponent"),
            "kind": m.kind,
            "question_id": m.first_question_id,
        }))


class QueueLeaveView(APIView):
    """POST {user_id}  -> remove from in-memory queue"""
    def post(self, request):
        user_id = request.data.get("user_id")
        if not user_id:
            return _no_store(Response({"error": "user_id required"}, status=400))
        user_id = int(user_id)

        with _queue_lock:
            if user_id in _queue:
                _queue.remove(user_id)
                return _no_store(Response({"removed": True}))
        return _no_store(Response({"removed": False}))


class MatchStateView(APIView):
    """GET /api/match/<id>/state  -> live state; flips to 'active' once begin_at passes."""
    def get(self, request, match_id: int):
        m = get_object_or_404(Match, id=match_id)
        m.maybe_promote_to_active()
        return _no_store(Response(_state(m)))


class MatchReadyView(APIView):
    """
    POST /api/match/<id>/ready { user_id } -> optional 'Ready' flow
    Not required if you want auto-start; kept here in case you add a 'Ready' button.
    """
    def post(self, request, match_id: int):
        user_id = request.data.get("user_id")
        if not user_id:
            return _no_store(Response({"error": "user_id required"}, status=400))
        user_id = int(user_id)

        m = get_object_or_404(Match, id=match_id)
        if user_id not in (m.player1_id, m.player2_id):
            return _no_store(Response({"error": "not a participant"}, status=403))

        changed = False
        if user_id == m.player1_id and not m.p1_ready:
            m.p1_ready = True; changed = True
        if user_id == m.player2_id and not m.p2_ready:
            m.p2_ready = True; changed = True

        if m.start_countdown_if_ready() or changed:
            m.save()

        return _no_store(Response(_state(m)))


class MatchQuestionView(APIView):
    """GET /api/match/<id>/question -> first question (no answer leak)."""
    def get(self, request, match_id: int):
        m = get_object_or_404(Match, id=match_id)
        q = m.first_question
        if not q:
            return _no_store(Response({"error": "no question assigned"}, status=404))

        data = {
            "id": q.id,
            "title": q.title,
            "descriptor": q.descriptor,
            "kind": q.question_kind,
        }

        if q.question_kind == "mcq":
            try:
                data["choices"] = q.mcq.choices
            except MCQ.DoesNotExist:
                data["choices"] = []
        else:
            try:
                data["prompt"] = q.coding.prompt
                data["template_code"] = q.coding.template_code
            except Coding.DoesNotExist:
                data["prompt"] = ""
                data["template_code"] = ""

        return _no_store(Response(data))
