import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient) -> None:
    """
    Verifies that the /health endpoint compiles, handles requests, and returns healthy status.
    """
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"

@pytest.mark.asyncio
async def test_root_status(client: AsyncClient) -> None:
    """
    Verifies that the root / endpoint responds correctly with project details.
    """
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "project" in data
