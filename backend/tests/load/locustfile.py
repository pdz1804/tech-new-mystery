"""Locust load test for chatbot and clustering endpoints.

Usage:
    locust -f backend/tests/load/locustfile.py --host http://localhost:8000

Scenarios:
    - ChatUser:     SSE streaming, session CRUD (weight 70%)
    - ClusterUser:  Browse clusters, trending (weight 30%)

Targets (per TASKS.md CHT-020):
    - p95 < 3s for chat at 100 concurrent users
    - error rate < 0.1%
    - auto-scaling verified under load
"""

import json
import uuid
import time
import os

from locust import HttpUser, task, between, events
from locust.exception import StopUser


AUTH_TOKEN = os.getenv("LOAD_TEST_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {AUTH_TOKEN}"} if AUTH_TOKEN else {}


# ---------------------------------------------------------------------------
# Chat load user
# ---------------------------------------------------------------------------

class ChatUser(HttpUser):
    """Simulates a user interacting with the chatbot."""

    weight = 7
    wait_time = between(1, 3)

    def on_start(self):
        self._session_id = None
        self._create_session()

    def _create_session(self):
        resp = self.client.post(
            "/v1/chat/sessions",
            json={"title": f"load-test-{uuid.uuid4().hex[:8]}"},
            headers=HEADERS,
            name="/v1/chat/sessions [POST]",
        )
        if resp.status_code == 201:
            data = resp.json()
            self._session_id = data.get("data", {}).get("session_id")

    @task(5)
    def stream_message(self):
        if not self._session_id:
            self._create_session()
            return

        start = time.perf_counter()
        token_count = 0

        with self.client.post(
            f"/v1/chat/sessions/{self._session_id}/stream",
            json={"content": "What are the latest tech trends?"},
            headers={**HEADERS, "Accept": "text/event-stream"},
            stream=True,
            name="/v1/chat/sessions/[id]/stream [POST]",
            catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"HTTP {resp.status_code}")
                return

            for line in resp.iter_lines():
                if line.startswith(b"data:"):
                    try:
                        payload = json.loads(line[5:])
                        if payload.get("type") == "token":
                            token_count += 1
                        elif payload.get("type") == "done":
                            break
                        elif payload.get("type") == "error":
                            resp.failure(f"SSE error: {payload.get('message')}")
                            return
                    except json.JSONDecodeError:
                        pass

            elapsed = time.perf_counter() - start
            if elapsed > 10:
                resp.failure(f"Response too slow: {elapsed:.1f}s")
            else:
                resp.success()

    @task(3)
    def list_sessions(self):
        self.client.get(
            "/v1/chat/sessions",
            params={"page": 1, "page_size": 20},
            headers=HEADERS,
            name="/v1/chat/sessions [GET]",
        )

    @task(2)
    def get_session(self):
        if not self._session_id:
            return
        self.client.get(
            f"/v1/chat/sessions/{self._session_id}",
            headers=HEADERS,
            name="/v1/chat/sessions/[id] [GET]",
        )

    @task(1)
    def get_messages(self):
        if not self._session_id:
            return
        self.client.get(
            f"/v1/chat/sessions/{self._session_id}/messages",
            params={"page": 1, "page_size": 20},
            headers=HEADERS,
            name="/v1/chat/sessions/[id]/messages [GET]",
        )


# ---------------------------------------------------------------------------
# Cluster browse user
# ---------------------------------------------------------------------------

class ClusterUser(HttpUser):
    """Simulates a user browsing topic clusters."""

    weight = 3
    wait_time = between(1, 5)

    @task(5)
    def list_clusters(self):
        self.client.get(
            "/v1/clusters",
            params={"page": 1, "page_size": 20, "sort_by": "size"},
            name="/v1/clusters [GET]",
        )

    @task(2)
    def trending_clusters(self):
        self.client.get(
            "/v1/clusters/trending",
            params={"limit": 5},
            name="/v1/clusters/trending [GET]",
        )

    @task(1)
    def health_check(self):
        self.client.get("/health", name="/health [GET]")


# ---------------------------------------------------------------------------
# Event hooks for reporting
# ---------------------------------------------------------------------------

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **_kw):
    if exception:
        print(f"[LOAD] FAIL {name}: {exception}")
    elif response_time > 3000:
        print(f"[LOAD] SLOW {name}: {response_time:.0f}ms")
