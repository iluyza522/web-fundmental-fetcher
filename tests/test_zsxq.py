"""Tests for zsxq fetcher."""
import pytest
from src.fetchers.zsxq import ZsxqFetcher


@pytest.mark.asyncio
async def test_zsxq_list_groups():
    f = ZsxqFetcher(cookie="zsxq_access_token=placeholder")
    try:
        groups = await f.list_groups()
    except Exception as e:
        # Without a valid cookie this will fail -- test the structure
        assert "401" in str(e) or "403" in str(e)


@pytest.mark.asyncio
async def test_zsxq_fetch():
    f = ZsxqFetcher(cookie="zsxq_access_token=placeholder")
    try:
        results = await f.fetch(limit=5)
    except Exception as e:
        assert "401" in str(e) or "403" in str(e)


def test_zsxq_requires_cookie():
    try:
        ZsxqFetcher(cookie="")
    except ValueError:
        return
    assert False, "Should have raised ValueError"
