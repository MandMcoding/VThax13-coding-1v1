# game/views.py
from datetime import timedelta
import threading

from django.db.models import Q
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Match
try:
    from authapp.models import Users  # if you have it
except Exception:
    Users = None

# Demo-only in-memory queue (single process). Use a DB/Redis queue in prod.
_queue = []
_queue_lock = threading.Lock()

def _no_store(resp: Response) -> Response:
    resp["Cache-Control"] = "no-store, no-cache, must-revalidate"
    resp["Pragma"] = "no-cache"
    return resp

def _username(uid: int, fallback: str):
    if not Users:
        return fallback
    u = Users.objects.filter(user_id=uid).first()
    return u.username if u else fallback

class QueueJoinView(APIView):
    def post(self, request):
        user_id = request.data.get("user_id")
        if not user_id:
            return _no_store(Response({"error": "user_id required"}, status=400))
        user_id = int(user_id)

        # If user already has a pending/active match, reuse it
        existing = Match.objects.filter(
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
            }))

        with _queue_lock:
            if user_id in _queue:
                return _no_store(Response({"status": "queued"}))
            _queue.append(user_id)
            if len(_queue) >= 2:
                a = _queue.pop(0)
                b = _queue.pop(0)
                m = Match.objects.create(player1_id=a, player2_id=b, status="pending")
                if user_id == a:
                    return _no_store(Response({
                        "status": "matched",
                        "match_id": m.id,
                        "opponent_id": b,
                        "opponent_username": _username(b, "PlayerB"),
                    }))
                else:
                    return _no_store(Response({
                        "status": "matched",
                        "match_id": m.id,
                        "opponent_id": a,
                        "opponent_username": _username(a, "PlayerA"),
                    }))
        return _no_store(Response({"status": "queued"}))


class QueueCheckView(APIView):
    def get(self, request):
        user_id = request.GET.get("user_id")
        if not user_id:
            return _no_store(Response({"error": "user_id required"}, status=400))
        user_id = int(user_id)

        m = Match.objects.filter(
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


class MatchReadyView(APIView):
    """Mark player ready; when both ready, start 3s countdown."""
    def post(self, request, match_id: int):
        user_id = request.data.get("user_id")
        if not user_id:
            return _no_store(Response({"error": "user_id required"}, status=400))
        user_id = int(user_id)

        try:
            m = Match.objects.get(id=match_id)
        except Match.DoesNotExist:
            return _no_store(Response({"error": "match not found"}, status=404))

        if user_id not in (m.player1_id, m.player2_id):
            return _no_store(Response({"error": "not a participant"}, status=403))

        changed = False
        if user_id == m.player1_id and not m.p1_ready:
            m.p1_ready = True; changed = True
        if user_id == m.player2_id and not m.p2_ready:
            m.p2_ready = True; changed = True

        if m.both_ready() and not m.begin_at:
            now = timezone.now()
            m.countdown_started_at = now
            m.begin_at = now + timedelta(seconds=3)
            changed = True

        if changed:
            m.save()

        return _no_store(Response(_state(m)))


class MatchStateView(APIView):
    """Return match state; flips to active once begin_at passes."""
    def get(self, request, match_id: int):
        try:
            m = Match.objects.get(id=match_id)
        except Match.DoesNotExist:
            return _no_store(Response({"error": "match not found"}, status=404))

        m.maybe_promote_to_active()
        return _no_store(Response(_state(m)))


def _state(m: Match) -> dict:
    return {
        "id": m.id,
        "status": m.status,
        "player1_id": m.player1_id,
        "player2_id": m.player2_id,
        "player1_username": _username(m.player1_id, "Player1"),
        "player2_username": _username(m.player2_id, "Player2"),
        "p1_ready": m.p1_ready,
        "p2_ready": m.p2_ready,
        "countdown_started_at": m.countdown_started_at.isoformat() if m.countdown_started_at else None,
        "begin_at": m.begin_at.isoformat() if m.begin_at else None,
        "now": timezone.now().isoformat(),
    }
