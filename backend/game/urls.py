from django.urls import path
from .views import QueueJoinView, QueueCheckView, QueueLeaveView

urlpatterns = [
    path("queue/join/",  QueueJoinView.as_view(),  name="queue-join"),
    path("queue/check/", QueueCheckView.as_view(), name="queue-check"),
    path("queue/leave/", QueueLeaveView.as_view(), name="queue-leave"),
]
