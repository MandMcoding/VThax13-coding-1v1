# pyright: reportMissingImports=false
from __future__ import annotations

from datetime import timedelta
import threading
import logging

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

logger = logging.getLogger(__name__)

# ---- DEMO-ONLY in-memory queue (single process)
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


def _ensure_question_assigned(m: Match, kind: str | None = None) -> bool:
    """
    Ensure match has at least one question in question_ids.
    Returns True if we assigned one now.
    """
    if (m.question_ids or []):
        return False
    k = (kind or m.kind or "mcq").lower()
    q = _pick_first_question(k)
    if not q:
        logger.warning("No questions available for kind=%s; match=%s", k, m.id)
        return False
    m.question_ids = [q.id]
    m.save(update_fields=["question_ids"])
    logger.info("Assigned question %s to match %s", q.id, m.id)
    return True


def _finalize_scores(match: Match) -> None:
    """Compute p1/p2 scores from game_results and store on Match."""
    p1 = GameResult.objects.filter(match_id=match.id, player_id=match.player1_id, is_correct=True).count()
    p2 = GameResult.objects.filter(match_id=match.id, player_id=match.player2_id, is_correct=True).count()
    if match.p1_score != p1 or match.p2_score != p2 or match.status != "finished":
        match.p1_score = p1
        match.p2_score = p2
        match.status = "finished"
        match.save(update_fields=["p1_score", "p2_score", "status"])
        logger.info("Match %s finalized: p1_score=%s p2_score=%s", match.id, p1, p2)


def _ensure_unanswered_rows(match: Match) -> None:
    """
    For every question in match.question_ids, ensure both players have a row.
    If missing, insert a 'timeout' incorrect row so game_results reflects the game.
    """
    qids = (match.question_ids or [])[:]
    if not qids:
        logger.info("Match %s has no questions; no unanswered rows to insert", match.id)
        return
    for pid in (match.player1_id, match.player2_id):
        existing = set(
            GameResult.objects.filter(match_id=match.id, player_id=pid)
            .values_list("question_id", flat=True)
        )
        missing = [qid for qid in qids if qid not in existing]
        for qid in missing:
            q = Question.objects.filter(id=qid).only("id", "question_kind").first()
            if not q:
                continue
            try:
                GameResult.objects.create(
                    match=match,
                    player_id=pid,
                    question=q,
                    question_kind=q.question_kind,
                    answer={"timeout": True},
                    is_correct=False,
                    elapsed_ms=None,
                )
                logger.info("Inserted timeout row: match=%s player=%s q=%s", match.id, pid, qid)
            except IntegrityError:
                pass
            except Exception as e:
                logger.exception("Failed inserting timeout row for match=%s player=%s q=%s: %s",
                                 match.id, pid, qid, e)


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
        "time_left_seconds": m.time_left_seconds() if hasattr(m, "time_left_seconds") else None,
        "question_id": m.first_question_id,
        "p1_score": m.p1_score,
        "p2_score": m.p2_score,
        "now": now.isoformat(),
    }


class QueueJoinView(APIView):
    def post(self, request):
        user_id = request.data.get("user_id")
        kind = (request.data.get("kind") or "mcq").lower()
        if not user_id:
            return _no_store(Response({"error": "user_id required"}, status=400))
        user_id = int(user_id)

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
                question_ids = [q.id] if q else []
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
                logger.info("Match %s created: players=%s vs %s kind=%s qids=%s", m.id, a, b, kind, question_ids)

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
            "question_id": m.first_question_id,
        }))


class QueueLeaveView(APIView):
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
    def get(self, request, match_id: int):
        user_id = request.GET.get("user_id")
        user_id = int(user_id) if user_id else None
        m = get_object_or_404(Match, id=match_id)

        changed = m.maybe_promote_to_active()
        if changed:
            logger.info("Match %s promoted to active", m.id)
            # Make sure a question is assigned once we go active
            _ensure_question_assigned(m)

        # If the minute expired, finish + fill unanswered + finalize scores.
        if m.maybe_finish_if_expired():
            logger.info("Match %s expired; finalizing", m.id)
            _ensure_question_assigned(m)
            _ensure_unanswered_rows(m)
            _finalize_scores(m)

        return _no_store(Response(_state(m, user_id)))


class MatchReadyView(APIView):
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

            if m.both_ready() and not m.begin_at:
                now = timezone.now()
                m.countdown_started_at = now
                m.begin_at = now + timedelta(seconds=3)
                fields += ["countdown_started_at", "begin_at"]

            if fields:
                m.save(update_fields=fields)
                logger.info("Match %s ready update by user %s -> p1=%s p2=%s",
                            m.id, user_id, m.p1_ready, m.p2_ready)

        m.maybe_promote_to_active()
        return _no_store(Response(_state(m, user_id)))


class MatchQuestionView(APIView):
    def get(self, request, match_id: int):
        m = get_object_or_404(Match, id=match_id)

        # Assign on-demand if missing
        if not m.first_question_id:
            _ensure_question_assigned(m)
        qid = m.first_question_id
        if not qid:
            return _no_store(Response({"error": "no question available"}, status=503))

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

        m = get_object_or_404(Match, id=match_id)
        if user_id not in (m.player1_id, m.player2_id):
            return _no_store(Response({"error": "not a participant"}, status=403))

        # If match time is over, finish and block further answers.
        if m.maybe_finish_if_expired() or m.status == "finished":
            logger.info("Reject submit: match %s finished", m.id)
            return _no_store(Response({"error": "match finished"}, status=409))

        q = get_object_or_404(Question, id=question_id)
        if q.question_kind != "mcq":
            return _no_store(Response({"error": "only mcq supported here"}, status=400))

        try:
            mcq = q.mcq
        except MCQ.DoesNotExist:
            return _no_store(Response({"error": "mcq not found"}, status=404))

        correct = (answer_index == mcq.answer_index)

        logger.info("Submit: match=%s user=%s q=%s ans=%s correct=%s elapsed_ms=%s",
                    m.id, user_id, question_id, answer_index, correct, elapsed_ms)

        try:
            with transaction.atomic():
                GameResult.objects.update_or_create(
                    match=m,
                    player_id=user_id,
                    question=q,
                    defaults={
                        "question_kind": q.question_kind,
                        "answer": {"answer_index": answer_index},
                        "is_correct": bool(correct),
                        "elapsed_ms": elapsed_ms,
                    },
                )
        except IntegrityError as e:
            logger.warning("IntegrityError writing game_results (match=%s user=%s q=%s): %s",
                           m.id, user_id, question_id, e)
        except Exception as e:
            logger.exception("Unexpected error writing game_results: %s", e)
            return _no_store(Response({"error": "write failed"}, status=500))

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

        # If the 60s window just expired, finish the match now: fill unanswered + finalize scores.
        if m.maybe_finish_if_expired():
            _ensure_question_assigned(m)
            _ensure_unanswered_rows(m)
            _finalize_scores(m)

        return _no_store(Response({
            "correct": correct,
            "elo_delta": elo_delta,
            "new_elo": new_elo,
            "time_left_seconds": m.time_left_seconds() if hasattr(m, "time_left_seconds") else None,
        }, status=status.HTTP_200_OK))


class MatchFinishView(APIView):
    """
    Force finish — idempotent. Ensures unanswered rows exist, then finalizes scores.
    """
    def post(self, request, match_id: int):
        m = get_object_or_404(Match, id=match_id)

        # Make sure we have a question to log against
        _ensure_question_assigned(m)

        # If time hasn't expired yet, we still allow manual finish for safety.
        m.maybe_promote_to_active()
        m.maybe_finish_if_expired()

        _ensure_unanswered_rows(m)
        _finalize_scores(m)

        return _no_store(Response(_state(m)))


class MatchResultsView(APIView):
    def get(self, request, match_id: int):
        m = get_object_or_404(Match, id=match_id)

        # Ensure we’re finished (and scores reflect rows)
        if m.maybe_finish_if_expired():
            _ensure_question_assigned(m)
            _ensure_unanswered_rows(m)
            _finalize_scores(m)

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
