from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q

from .models import Match
from .matchmaking import enqueue, leave

class QueueJoinView(APIView):
    """
    POST /api/queue/join/ { "user_id": 7 }
    Returns: { status: "queued" } or { status: "matched", match_id, opponent_id }
    """
    authentication_classes = []   # demo
    permission_classes = []       # demo

    def post(self, request):
        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"error": "user_id required"}, status=400)

        pair = enqueue(int(user_id))
        if pair is None:
            return Response({"status": "queued"}, status=200)

        a, b = pair
        match = Match.objects.create(player1_id=a, player2_id=b, status="pending")
        # tell each side who they face
        opponent_for_a = b
        opponent_for_b = a
        if int(user_id) == a:
            return Response({"status": "matched", "match_id": match.id, "opponent_id": opponent_for_a}, status=200)
        elif int(user_id) == b:
            return Response({"status": "matched", "match_id": match.id, "opponent_id": opponent_for_b}, status=200)
        else:
            # Very rare race; safe fallback
            return Response({"status": "queued"}, status=200)

class QueueCheckView(APIView):
    """
    GET /api/queue/check/?user_id=7
    If a match exists in 'pending' for this user, return it.
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        user_id = request.GET.get("user_id")
        if not user_id:
            return Response({"error": "user_id required"}, status=400)

        m = Match.objects.filter(
            Q(player1_id=user_id) | Q(player2_id=user_id),
            status="pending"
        ).order_by("-created_at").first()

        if not m:
            return Response({"status": "waiting"}, status=200)

        opponent = m.player2_id if m.player1_id == int(user_id) else m.player1_id
        return Response({"status": "matched", "match_id": m.id, "opponent_id": opponent}, status=200)

class QueueLeaveView(APIView):
    """
    POST /api/queue/leave/ { "user_id": 7 }
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"error": "user_id required"}, status=400)
        removed = leave(int(user_id))
        return Response({"removed": removed}, status=200)
