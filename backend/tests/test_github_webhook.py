import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app


@pytest.fixture
def webhook_client(monkeypatch):
    secret = "test-webhook-secret"
    task_payloads = []

    class FakeTask:
        def delay(self, payload):
            task_payloads.append(payload)

    monkeypatch.setattr("app.api.github.run_pull_request_scan", FakeTask())
    app.dependency_overrides[get_settings] = lambda: Settings(
        github_webhook_secret=secret
    )
    try:
        with TestClient(app) as client:
            yield client, secret, task_payloads
    finally:
        app.dependency_overrides.clear()


def _payload() -> dict:
    return {
        "action": "synchronize",
        "number": 42,
        "pull_request": {
            "head": {
                "sha": "a" * 40,
            }
        },
        "repository": {
            "html_url": "https://github.com/acme/api",
        },
    }


def test_github_webhook_requires_valid_signature(webhook_client) -> None:
    client, _, _ = webhook_client
    response = client.post(
        "/api/webhooks/github",
        headers={"X-GitHub-Event": "pull_request", "X-Hub-Signature-256": "sha256=bad"},
        content=json.dumps(_payload()),
    )
    assert response.status_code == 401


def test_github_webhook_queues_supported_pull_request(webhook_client) -> None:
    client, secret, task_payloads = webhook_client
    body = json.dumps(_payload()).encode()
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    response = client.post(
        "/api/webhooks/github",
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": f"sha256={signature}",
        },
        content=body,
    )

    assert response.status_code == 202
    assert response.json() == {"status": "queued"}
    assert task_payloads == [
        {
            "repository_url": "https://github.com/acme/api",
            "pull_request_number": 42,
            "head_sha": "a" * 40,
            "head_repository_url": "https://github.com/acme/api",
        }
    ]
