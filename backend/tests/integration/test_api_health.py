"""Health-endpoint smoke test (Task 12.8, Requirement 15.6).

Confirms the service boots and ``GET /health`` returns a 200 success response.
This is the minimal liveness check Docker Compose and uptime probes rely on; it
touches no services or database, so a pass proves the app assembles and routes.
"""

from __future__ import annotations


def test_health_returns_success(client):
    """``GET /health`` responds 200 with a success status (Requirement 15.6)."""
    response = client.get("/health")
    assert response.status_code == 200, response.text
    assert response.json() == {"status": "ok"}
