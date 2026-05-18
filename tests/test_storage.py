"""Tests for storage."""
import json
import tempfile
from pathlib import Path
from src.models import FetchResult, SourceType
from src.storage import Storage


def test_storage_save_and_exists():
    with tempfile.TemporaryDirectory() as tmp:
        s = Storage(Path(tmp))
        r = FetchResult(
            source=SourceType.CNINFO,
            title="公告",
            content="内容",
            published_at="2026-05-18T10:00:00",
            stock_code="000001",
        )
        assert not s.exists(r)
        s.save(r)
        assert s.exists(r)


def test_storage_save_creates_file():
    with tempfile.TemporaryDirectory() as tmp:
        s = Storage(Path(tmp))
        r = FetchResult(
            source=SourceType.CNINFO,
            title="公告",
            content="内容",
            published_at="2026-05-18T10:00:00",
            stock_code="000001",
        )
        path = s.save(r)
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["title"] == "公告"


def test_storage_zsxq_path():
    with tempfile.TemporaryDirectory() as tmp:
        s = Storage(Path(tmp))
        r = FetchResult(
            source=SourceType.ZSXQ,
            title="帖",
            content="C",
            published_at="2026-05-18T10:00:00",
            group_name="测试星球",
        )
        path = s.save(r)
        assert "zsxq" in str(path)
        assert path.exists()


def test_storage_dedup():
    with tempfile.TemporaryDirectory() as tmp:
        s = Storage(Path(tmp))
        r = FetchResult(
            source=SourceType.CNINFO,
            title="公告",
            content="内容",
            published_at="2026-05-18T10:00:00",
            stock_code="000001",
        )
        p1 = s.save(r)
        p2 = s.save(r)
        assert p1 == p2
