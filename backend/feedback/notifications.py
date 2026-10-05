"""
In-process pub/sub for server-sent events.

`EventBroker` keeps one queue per open SSE connection. Publishers only know
the small `publish(user_id, event)` surface, so the broker can be swapped
for Redis/Channels later without touching callers (DIP).
"""

import json
import queue
import threading
from collections import defaultdict


class EventBroker:
    def __init__(self):
        self._lock = threading.Lock()
        self._subscribers = defaultdict(set)

    def subscribe(self, user_id):
        q = queue.Queue()
        with self._lock:
            self._subscribers[user_id].add(q)
        return q

    def unsubscribe(self, user_id, q):
        with self._lock:
            self._subscribers[user_id].discard(q)
            if not self._subscribers[user_id]:
                del self._subscribers[user_id]

    def publish(self, user_id, event):
        with self._lock:
            targets = list(self._subscribers.get(user_id, ()))
        for q in targets:
            q.put(event)


broker = EventBroker()


def format_sse(event):
    """Serialize an event dict as one SSE frame."""
    return f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"
