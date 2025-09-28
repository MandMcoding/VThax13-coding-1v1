# pyright: reportMissingImports=false
from __future__ import annotations

from datetime import timedelta
import threading

from django.db import transaction
from django.db.models import Q
from django.db.models.functions import Random
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Match, Question, MCQ, Coding, GameResult

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


def _state(m: Match, user_id: int | None = None) -> dict:
    now = timezone.now()
    countdown_seconds: int | None = None
    if m.begin_at:
        delta = (m.begin_at - now).total_seconds()
        countdown_seconds = int(delta) if delta > 0 else 0

    you_ready = None
    opponent_ready = None
    if user_id is not None:
        if m.player1_id == user_id:
            you_ready, opponent_ready = m.p1_ready, m.p2_ready
        elif m.player2_id == user_id:
            you_ready, opponent_ready = m.p2_ready, m.p1_ready

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
        "you_ready": you_ready,
        "opponent_ready": opponent_ready,
        "countdown_started_at": m.countdown_started_at.isoformat() if m.countdown_started_at else None,
        "begin_at": m.begin_at.isoformat() if m.begin_at else None,
        "countdown_seconds": countdown_seconds,
        "question_id": m.first_question_id,  # property derived from question_ids[0]
        "now": now.isoformat(),
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

        # Reuse existing pending/active match if any (do NOT select 'first_question_id' — it is a property now)
        existing = Match.objects.only(
            "id", "player1_id", "player2_id", "status", "created_at", "kind",
            "p1_ready", "p2_ready", "begin_at"
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
                "question_id": existing.first_question_id,  # property
            }))

        with _queue_lock:
            if user_id in _queue:
                return _no_store(Response({"status": "queued"}))

            _queue.append(user_id)

            if len(_queue) >= 2:
                a = _queue.pop(0)
                b = _queue.pop(0)

                q = _pick_first_question(kind)
                question_ids = [q.id] if q else []  # you can push more ids here later

                # Wait for both players to Ready
                m = Match.objects.create(
                    player1_id=a,
                    player2_id=b,
                    kind=kind,
                    status="pending",
                    p1_ready=False,
                    p2_ready=False,
                    countdown_started_at=None,
                    begin_at=None,
                    question_ids=question_ids,
                )

                payload = {
                    "status": "matched",
                    "match_id": m.id,
                    "kind": m.kind,
                    "question_id": m.first_question_id,  # property
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
            "id", "player1_id", "player2_id", "status", "created_at", "kind",
            "p1_ready", "p2_ready", "begin_at"
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
            "question_id": m.first_question_id,  # property
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
    """
    GET /api/match/<match_id>/state?user_id=...
    Returns match state; also promotes to 'active' once begin_at passed.
    """
    def get(self, request, match_id: int):
        user_id = request.GET.get("user_id")
        user_id = int(user_id) if user_id else None
        m = get_object_or_404(Match, id=match_id)
        m.maybe_promote_to_active()
        return _no_store(Response(_state(m, user_id)))


class MatchReadyView(APIView):
    """
    POST /api/match/<match_id>/ready
    Body: { user_id: int, ready: bool }  (ready defaults to true)
    """
    def post(self, request, match_id: int):
        user_id = request.data.get("user_id")
        ready = request.data.get("ready", True)
        if user_id is None:
            return _no_store(Response({"error": "user_id required"}, status=400))
        user_id = int(user_id)
        ready = bool(ready)

        with transaction.atomic():
            m = Match.objects.select_for_update().get(id=match_id)

            if user_id not in (m.player1_id, m.player2_id):
                return _no_store(Response({"error": "not a participant"}, status=403))

            # toggle your ready flag
            fields = []
            if m.player1_id == user_id and m.p1_ready != ready:
                m.p1_ready = ready; fields.append("p1_ready")
            if m.player2_id == user_id and m.p2_ready != ready:
                m.p2_ready = ready; fields.append("p2_ready")

            # start countdown once, when both are ready
            if m.both_ready() and not m.begin_at:
                now = timezone.now()
                m.countdown_started_at = now
                m.begin_at = now + timedelta(seconds=3)
                fields += ["countdown_started_at", "begin_at"]

            if fields:
                m.save(update_fields=fields)

        # flip to active if countdown elapsed
        m.maybe_promote_to_active()
        return _no_store(Response(_state(m, user_id)))


class MatchQuestionView(APIView):
    """GET /api/match/<match_id>/question -> first question (no answer leak)."""
    def get(self, request, match_id: int):
        m = get_object_or_404(Match, id=match_id)

        # Use property backed by question_ids
        qid = m.first_question_id
        if not qid:
            return _no_store(Response({"error": "no question assigned"}, status=404))

        q = get_object_or_404(Question, id=qid)

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


class MatchSubmitAnswerView(APIView):
    """
    POST /api/match/<match_id>/submit
    Body (MCQ): { user_id: int, question_id: int, answer_index: int, elapsed_ms?: int }

    Saves/updates a per-question result, increments score (once), and
    auto-finishes the match when both players answered all questions.
    """
    def post(self, request, match_id: int):
        user_id = request.data.get("user_id")
        question_id = request.data.get("question_id")
        answer_index = request.data.get("answer_index")
        elapsed_ms = request.data.get("elapsed_ms")

        if user_id is None or question_id is None or answer_index is None:
            return _no_store(Response(
                {"error": "user_id, question_id, answer_index required"},
                status=status.HTTP_400_BAD_REQUEST,
            ))

        user_id = int(user_id)
        question_id = int(question_id)
        answer_index = int(answer_index)
        elapsed_ms = int(elapsed_ms) if elapsed_ms is not None else None

        with transaction.atomic():
            m = Match.objects.select_for_update().get(id=match_id)

            # Only participants can submit
            if user_id not in (m.player1_id, m.player2_id):
                return _no_store(Response({"error": "not a participant"}, status=403))

            # Validate question is part of this match if list provided
            qids = list(m.question_ids or [])
            if qids and question_id not in qids:
                return _no_store(Response({"error": "question not in match"}, status=400))

            q = get_object_or_404(Question, id=question_id)
            if q.question_kind != "mcq":
                return _no_store(Response({"error": "only mcq supported here"}, status=400))

            # Correctness
            try:
                mcq = q.mcq
            except MCQ.DoesNotExist:
                return _no_store(Response({"error": "mcq not found"}, status=404))

            is_correct = (answer_index == mcq.answer_index)

            # Upsert result; only increment score if it's the first time
            # or a change from incorrect -> correct.
            obj, created = GameResult.objects.get_or_create(
                match=m,
                player_id=user_id,
                question=q,
                defaults={
                    "question_kind": q.question_kind,
                    "answer": {"answer_index": answer_index},
                    "is_correct": is_correct,
                    "elapsed_ms": elapsed_ms,
                },
            )

            prev_correct = False
            if not created:
                prev_correct = bool(obj.is_correct)
                obj.question_kind = q.question_kind
                obj.answer = {"answer_index": answer_index}
                obj.is_correct = is_correct
                obj.elapsed_ms = elapsed_ms
                obj.save(update_fields=["question_kind", "answer", "is_correct", "elapsed_ms"])

            # Increment score once per question per player when it becomes correct
            fields_to_save = []
            if is_correct and not prev_correct:
                if user_id == m.player1_id:
                    m.p1_score = (m.p1_score or 0) + 1
                    fields_to_save.append("p1_score")
                else:
                    m.p2_score = (m.p2_score or 0) + 1
                    fields_to_save.append("p2_score")

            # Auto-finish when both have answered all questions
            total = len(qids) if qids else 0
            if total > 0:
                ans_p1 = GameResult.objects.filter(match=m, player_id=m.player1_id).count()
                ans_p2 = GameResult.objects.filter(match=m, player_id=m.player2_id).count()
                if ans_p1 >= total and ans_p2 >= total and m.status != "finished":
                    m.status = "finished"
                    fields_to_save.append("status")

            if fields_to_save:
                m.save(update_fields=fields_to_save)

        # outside the transaction, return the latest state
        your_score = m.p1_score if user_id == m.player1_id else m.p2_score
        opp_score = m.p2_score if user_id == m.player1_id else m.p1_score
        finished = (m.status == "finished")

        return _no_store(Response({
            "correct": is_correct,
            "your_score": your_score,
            "opponent_score": opp_score,
            "finished": finished,
            "expected_answers": len(m.question_ids or []),
        }, status=status.HTTP_200_OK))


class MatchResultsView(APIView):
    """GET /api/match/<match_id>/results -> scoreboard + per-question results."""
    def get(self, request, match_id: int):
        m = get_object_or_404(Match, id=match_id)
        results = GameResult.objects.filter(match=m).order_by("created_at")

        items = []
        for r in results:
            items.append({
                "player_id": r.player_id,
                "question_id": r.question_id,
                "question_kind": r.question_kind,
                "answer": r.answer,
                "is_correct": r.is_correct,
                "elapsed_ms": r.elapsed_ms,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            })

        return _no_store(Response({
            "match_id": m.id,
            "status": m.status,
            "kind": m.kind,
            "player1_id": m.player1_id,
            "player2_id": m.player2_id,
            "p1_score": m.p1_score,
            "p2_score": m.p2_score,
            "expected_answers": len(m.question_ids or []),
            "results": items,
        }))
