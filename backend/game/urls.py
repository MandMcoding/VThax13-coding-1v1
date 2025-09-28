from django.urls import path
from .views import (
    QueueJoinView, QueueCheckView, QueueLeaveView,
    MatchStateView, MatchReadyView, MatchQuestionView, MatchNextQuestionView,
    MatchSubmitAnswerView, MatchFinishView, MatchResultsView,
    LeaderboardView,
)

urlpatterns = [
    path("queue/join/", QueueJoinView.as_view()),
    path("queue/check/", QueueCheckView.as_view()),
    path("queue/leave/", QueueLeaveView.as_view()),
    path("match/<int:match_id>/state/", MatchStateView.as_view()),
    path("match/<int:match_id>/ready/", MatchReadyView.as_view()),
    path("match/<int:match_id>/question/", MatchQuestionView.as_view()),
    path("match/<int:match_id>/next-question/", MatchNextQuestionView.as_view()),
    path("match/<int:match_id>/submit/", MatchSubmitAnswerView.as_view()),
    path("match/<int:match_id>/finish/", MatchFinishView.as_view()),
    path("match/<int:match_id>/results/", MatchResultsView.as_view()),
    path("leaderboard/", LeaderboardView.as_view()),
]
