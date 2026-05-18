"""Tests for cninfo fetcher."""
import pytest
from src.fetchers.cninfo import CninfoFetcher


@pytest.mark.asyncio
async def test_cninfo_fetch():
    f = CninfoFetcher()
    results = await f.fetch(stock_code="000001")
    assert len(results) > 0
    for r in results:
        assert r.source.value == "cninfo"
        assert r.title
        assert r.content or r.url
        assert r.published_at


@pytest.mark.asyncio
async def test_cninfo_fetch_with_limit():
    f = CninfoFetcher()
    results = await f.fetch(stock_code="000001", limit=5)
    assert len(results) <= 5


@pytest.mark.asyncio
async def test_cninfo_fetch_invalid_code():
    f = CninfoFetcher()
    results = await f.fetch(stock_code="999999")
    assert len(results) == 0
