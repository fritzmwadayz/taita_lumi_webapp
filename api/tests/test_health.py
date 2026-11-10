"""Tests for health check endpoints."""

import pytest


@pytest.mark.asyncio
async def test_health(client):
    """Liveness endpoint returns 200 with status ok."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_root(client):
    """Root endpoint returns API info."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Lumi API"
    assert "version" in data
