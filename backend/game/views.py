# pyright: reportMissingImports=false
from __future__ import annotations

from datetime import timedelta
import threading

from django.db import transaction, IntegrityError
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

    # tolerate older model without helper
    time_left = m.time_left_seconds() if hasattr(m, "time_left_seconds") else None

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
        "countdown_seconds": countdown_seconds,   # 3..2..1 lobby countdown
        "time_left_seconds": time_left,           # 60..0 in-match clock
        "question_id": m.first_question_id,       # derived from question_ids[0]
        "p1_score": m.p1_score,
        "p2_score": m.p2_score,
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

        # Reuse existing pending/active match if any
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
                question_ids = [q.id] if q else []

                # Wait for both players to Ready before countdown.
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
    Promotes pending->active after begin_at, and auto-finishes when the 60s window expires.
    """
    def get(self, request, match_id: int):
        user_id = request.GET.get("user_id")
        user_id = int(user_id) if user_id else None
        m = get_object_or_404(Match, id=match_id)
        m.maybe_promote_to_active()
        if hasattr(m, "maybe_finish_if_expired"):
            m.maybe_finish_if_expired()
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

            fields = []
            if m.player1_id == user_id and m.p1_ready != ready:
                m.p1_ready = ready; fields.append("p1_ready")
            if m.player2_id == user_id and m.p2_ready != ready:
                m.p2_ready = ready; fields.append("p2_ready")

            # start 3-second countdown once, when both are ready
            if m.both_ready() and not m.begin_at:
                now = timezone.now()
                m.countdown_started_at = now
                m.begin_at = now + timedelta(seconds=3)
                fields += ["countdown_started_at", "begin_at"]

            if fields:
                m.save(update_fields=fields)

        m.maybe_promote_to_active()
        return _no_store(Response(_state(m, user_id)))


class MatchQuestionView(APIView):
    """GET /api/match/<match_id>/question -> first question (no answer leak)."""
    def get(self, request, match_id: int):
        m = get_object_or_404(Match, id=match_id)

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
    Body: { user_id: int, question_id: int, answer_index: int, elapsed_ms?: int }

    Validates MCQ and records (upserts) a row in game_results.
    Also keeps p1_score/p2_score in sync without double counting.
    """
    def post(self, request, match_id: int):
        user_id = request.data.get("user_id")
        question_id = request.data.get("question_id")
        answer_index = request.data.get("answer_index")
        elapsed_ms = request.data.get("elapsed_ms")

        if user_id is None or question_id is None or answer_index is None:
            return _no_store(Response({"error": "user_id, question_id, answer_index required"}, status=400))

        user_id = int(user_id)
        question_id = int(question_id)
        answer_index = int(answer_index)
        elapsed_ms = int(elapsed_ms) if elapsed_ms is not None else None

        # Validate question & kind
        q = get_object_or_404(Question, id=question_id)
        if q.question_kind != "mcq":
            return _no_store(Response({"error": "only mcq supported here"}, status=400))
        try:
            mcq = q.mcq
        except MCQ.DoesNotExist:
            return _no_store(Response({"error": "mcq not found"}, status=404))
        correct = (answer_index == mcq.answer_index)

        with transaction.atomic():
            # Lock match so score updates are consistent
            m = Match.objects.select_for_update().get(id=match_id)
            if user_id not in (m.player1_id, m.player2_id):
                return _no_store(Response({"error": "not a participant"}, status=403))

            # If match time is over, finish and block further answers.
            if hasattr(m, "maybe_finish_if_expired") and (m.maybe_finish_if_expired() or m.status == "finished"):
                return _no_store(Response({"error": "match finished"}, status=409))

            # Upsert result; read previous correctness to adjust score
            prev = GameResult.objects.select_for_update().filter(
                match=m, player_id=user_id, question=q
            ).first()
            prev_correct = bool(prev and prev.is_correct)

            defaults = {
                "question_kind": q.question_kind,
                "answer": {"answer_index": answer_index},
                "is_correct": bool(correct),
                "elapsed_ms": elapsed_ms,
            }

            if prev:
                # update existing
                for k, v in defaults.items():
                    setattr(prev, k, v)
                prev.save(update_fields=list(defaults.keys()))
                created = False
            else:
                GameResult.objects.create(
                    match=m, player_id=user_id, question=q, **defaults
                )
                created = True

            # Adjust scoreboard if correctness changed
            if user_id == m.player1_id:
                if correct and not prev_correct:
                    m.p1_score += 1
                elif not correct and prev_correct:
                    m.p1_score -= 1
                m.save(update_fields=["p1_score"])
            else:
                if correct and not prev_correct:
                    m.p2_score += 1
                elif not correct and prev_correct:
                    m.p2_score -= 1
                m.save(update_fields=["p2_score"])

        # Optional ELO bump
        elo_delta = 10 if correct else 0
        new_elo = None
        try:
            from authapp.models import Users  # type: ignore
            if hasattr(Users, "elo"):
                user = Users.objects.filter(user_id=user_id).first()
                if user is not None:
                    current = getattr(user, "elo", 0) or 0
                    if elo_delta:
                        setattr(user, "elo", current + elo_delta)
                        try:
                            user.save(update_fields=["elo"])
                        except Exception:
                            pass
                        new_elo = current + elo_delta
                    else:
                        new_elo = current
        except Exception:
            pass

        # If the 60s window just expired after this submit, flip to finished.
        if hasattr(m, "maybe_finish_if_expired"):
            m.maybe_finish_if_expired()

        return _no_store(Response({
            "correct": correct,
            "elo_delta": elo_delta,
            "new_elo": new_elo,
            "time_left_seconds": m.time_left_seconds() if hasattr(m, "time_left_seconds") else None,
            "p1_score": m.p1_score,
            "p2_score": m.p2_score,
        }, status=status.HTTP_200_OK))


class MatchFinishView(APIView):
    """
    POST /api/match/<match_id>/finish
    Force finish (e.g., when the minute elapses on the client) — idempotent.
    """
    def post(self, request, match_id: int):
        m = get_object_or_404(Match, id=match_id)
        # Try the timed finish first
        if hasattr(m, "maybe_finish_if_expired") and not m.maybe_finish_if_expired():
            if m.status != "finished":
                # compute scores from stored results just in case
                p1 = GameResult.objects.filter(match_id=m.id, player_id=m.player1_id, is_correct=True).count()
                p2 = GameResult.objects.filter(match_id=m.id, player_id=m.player2_id, is_correct=True).count()
                m.p1_score = p1
                m.p2_score = p2
                m.status = "finished"
                m.save(update_fields=["p1_score", "p2_score", "status"])
        return _no_store(Response(_state(m)))


class MatchResultsView(APIView):
    """
    GET /api/match/<match_id>/results
    Returns per-player results and final scores once finished (or live).
    """
    def get(self, request, match_id: int):
        m = get_object_or_404(Match, id=match_id)
        if hasattr(m, "maybe_finish_if_expired"):
            m.maybe_finish_if_expired()

        def _rows(pid: int):
            rows = (GameResult.objects
                    .filter(match_id=m.id, player_id=pid)
                    .order_by("created_at")
                    .values("question_id", "question_kind", "answer", "is_correct", "elapsed_ms", "created_at"))
            return list(rows)

        data = {
            "match_id": m.id,
            "status": m.status,
            "kind": m.kind,
            "p1": {
                "player_id": m.player1_id,
                "username": _username(m.player1_id, "Player1"),
                "score": m.p1_score,
                "answers": _rows(m.player1_id),
            },
            "p2": {
                "player_id": m.player2_id,
                "username": _username(m.player2_id, "Player2"),
                "score": m.p2_score,
                "answers": _rows(m.player2_id),
            },
        }
        return _no_store(Response(data))
