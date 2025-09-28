# game/urls.py
from django.urls import re_path
from .views import (
    QueueJoinView, QueueCheckView, QueueLeaveView,
    MatchReadyView, MatchStateView,
)

urlpatterns = [
    re_path(r"^queue/join/?$",  QueueJoinView.as_view(),  name="queue-join"),
    re_path(r"^queue/check/?$", QueueCheckView.as_view(), name="queue-check"),
    re_path(r"^queue/leave/?$", QueueLeaveView.as_view(), name="queue-leave"),
    re_path(r"^match/(?P<match_id>\d+)/ready/?$", MatchReadyView.as_view(), name="match-ready"),
    re_path(r"^match/(?P<match_id>\d+)/state/?$", MatchStateView.as_view(), name="match-state"),
]
