# DEMO-ONLY in-memory queue (one Django process)
from collections import deque

_queue = deque()  # holds user_ids

def enqueue(user_id: int):
    if user_id in _queue:
        return None  # already queued
    _queue.append(user_id)
    if len(_queue) >= 2:
        a = _queue.popleft()
        b = _queue.popleft()
        return (a, b)  # a pair is ready
    return None

def leave(user_id: int):
    try:
        _queue.remove(user_id)
        return True
    except ValueError:
        return False
