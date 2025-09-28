from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q

from .models import Match
from authapp.models import Users

# In-memory queue for demo (replace with persistent queue in production)
queue = []

class QueueJoinView(APIView):
    def post(self, request):
        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"error": "user_id required"}, status=400)
        user_id = int(user_id)
        if user_id in queue:
            return Response({"status": "queued"}, status=200)
        queue.append(user_id)
        if len(queue) >= 2:
            a = queue.pop(0)
            b = queue.pop(0)
            match = Match.objects.create(player1_id=a, player2_id=b, status="pending")
            # Get usernames
            user_a = Users.objects.filter(user_id=a).first()
            user_b = Users.objects.filter(user_id=b).first()
            username_a = user_a.username if user_a else "PlayerA"
            username_b = user_b.username if user_b else "PlayerB"
            # Respond to both
            if user_id == a:
                return Response({"status": "matched", "match_id": match.id, "opponent_id": b, "opponent_username": username_b}, status=200)
            else:
                return Response({"status": "matched", "match_id": match.id, "opponent_id": a, "opponent_username": username_a}, status=200)
        return Response({"status": "queued"}, status=200)

class QueueCheckView(APIView):
    def get(self, request):
        user_id = request.GET.get("user_id")
        if not user_id:
            return Response({"error": "user_id required"}, status=400)
        user_id = int(user_id)
        m = Match.objects.filter(
            Q(player1_id=user_id) | Q(player2_id=user_id),
            status="pending"
        ).order_by("-created_at").first()
        if not m:
            return Response({"status": "waiting"}, status=200)
        # Find opponent
        if m.player1_id == user_id:
            opponent_id = m.player2_id
        else:
            opponent_id = m.player1_id
        opponent = Users.objects.filter(user_id=opponent_id).first()
        opponent_username = opponent.username if opponent else "Opponent"
        return Response({"status": "matched", "match_id": m.id, "opponent_id": opponent_id, "opponent_username": opponent_username}, status=200)

class QueueLeaveView(APIView):
    def post(self, request):
        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"error": "user_id required"}, status=400)
        if int(user_id) in queue:
            queue.remove(int(user_id))
            return Response({"removed": True}, status=200)
        return Response({"removed": False}, status=200)
