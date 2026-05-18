"""Tests for HTTP client."""
import pytest
from src.utils.http import create_client


@pytest.mark.asyncio
async def test_create_client_defaults():
    client = create_client()
    assert client.timeout is not None
    assert client.timeout.connect == 15.0
    await client.aclose()


@pytest.mark.asyncio
async def test_create_client_with_cookie():
    client = create_client(cookie="zsxq_token=abc123")
    assert any("cookie" in str(h).lower() or "zsxq" in str(v)
               for h, v in client.headers.items())
    await client.aclose()
