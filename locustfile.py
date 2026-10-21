import os
from urllib.parse import urljoin

from locust import HttpUser, between, task


PRIVACY_NOTICE_VERSION = "2026-10-21"


class SchemeSageUser(HttpUser):
    wait_time = between(1, 3)

    @task(4)
    def health_check(self):
        self.client.get("/api/health", name="/api/health")

    @task(1)
    def create_and_delete_session(self):
        with self.client.post(
            "/api/sessions",
            json={"accepted": True, "notice_version": PRIVACY_NOTICE_VERSION},
            name="/api/sessions",
            catch_response=True,
        ) as response:
            if response.status_code != 201:
                response.failure(f"Session creation returned HTTP {response.status_code}")
                return
            session_id = response.json().get("session_id")

        if session_id:
            self.client.delete(
                urljoin("/api/sessions/", session_id),
                name="/api/sessions/{session_id}",
            )
