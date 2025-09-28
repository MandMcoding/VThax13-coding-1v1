from django.urls import path
from .views import (
    QueueJoinView, QueueCheckView, QueueLeaveView,
    MatchStateView, MatchReadyView, MatchQuestionView,
    MatchSubmitAnswerView,
)

urlpatterns = [
    path("queue/join/",  QueueJoinView.as_view(),  name="queue-join"),
    path("queue/check/", QueueCheckView.as_view(), name="queue-check"),
    path("queue/leave/", QueueLeaveView.as_view(), name="queue-leave"),

    path("match/<int:match_id>/state/",   MatchStateView.as_view(),   name="match-state"),
    path("match/<int:match_id>/ready/",   MatchReadyView.as_view(),   name="match-ready"),
    path("match/<int:match_id>/question/",MatchQuestionView.as_view(),name="match-question"),
    path("match/<int:match_id>/submit/",  MatchSubmitAnswerView.as_view(),name="match-submit"),
]
