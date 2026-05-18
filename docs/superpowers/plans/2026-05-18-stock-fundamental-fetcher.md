# Stock Fundamental Fetcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CLI tool that fetches A-share stock fundamental text data (company announcements, research reports, news, industry reports, paid Knowledge Planet content) and stores as local JSON.

**Architecture:** Python async CLI with pluggable fetchers per data source. Each fetcher implements a common interface and returns typed `FetchResult` objects. Storage layer handles dedup via content hashing. httpx for HTTP, click for CLI.

**Tech Stack:** Python 3.11+, httpx, click, beautifulsoup4, toml

---

### Task 0: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `Makefile`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "fundamental-fetcher"
version = "0.1.0"
description = "A-share stock fundamental text data fetcher"
requires-python = ">=3.11"
dependencies = [
    "httpx>=0.27.0",
    "click>=8.1.0",
    "beautifulsoup4>=4.12.0",
    "lxml>=5.0.0",
    "toml>=0.10.2",
]

[project.scripts]
ff = "cli:main"
```

- [ ] **Step 2: Create requirements.txt**

```
httpx>=0.27.0
click>=8.1.0
beautifulsoup4>=4.12.0
lxml>=5.0.0
toml>=0.10.2
pytest>=8.0.0
pytest-asyncio>=0.24.0
```

- [ ] **Step 3: Create Makefile**

```makefile
.PHONY: install test

install:
	pip install -r requirements.txt

test:
	pytest -v

test-cov:
	pytest --cov=. --cov-report=term-missing
```

- [ ] **Step 4: Create directory structure**

```bash
mkdir -p src/fetchers src/utils tests
touch src/__init__.py src/fetchers/__init__.py src/utils/__init__.py tests/__init__.py
```

---

### Task 1: Data models

**Files:**
- Create: `src/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write the test**

```python
"""Tests for data models."""
from src.models import FetchResult, SourceType


def test_fetch_result_minimal():
    r = FetchResult(
        source=SourceType.CNINFO,
        title="测试公告",
        content="正文",
        published_at="2026-05-18T10:00:00",
    )
    assert r.id is not None
    assert len(r.id) == 16
    assert r.stock_code is None


def test_fetch_result_full():
    r = FetchResult(
        source=SourceType.ZSXQ,
        title="测试帖",
        content="内容",
        published_at="2026-05-18T10:00:00",
        stock_code="000001",
        stock_name="平安银行",
        url="https://zsxq.com/123",
        authors=["作者"],
        tags=["讨论"],
        group_name="某星球",
        mentions_stocks=["000001"],
    )
    assert r.group_name == "某星球"
    assert r.mentions_stocks == ["000001"]


def test_fetch_result_id_deterministic():
    r1 = FetchResult(
        source=SourceType.CNINFO,
        title="公告",
        content="内容",
        published_at="2026-05-18T10:00:00",
    )
    r2 = FetchResult(
        source=SourceType.CNINFO,
        title="公告",
        content="内容",
        published_at="2026-05-18T10:00:00",
    )
    assert r1.id == r2.id


def test_fetch_result_id_different_source():
    r1 = FetchResult(source=SourceType.CNINFO, title="X", content="C", published_at="2026-05-18T10:00:00")
    r2 = FetchResult(source=SourceType.EASTMONEY_REPORT, title="X", content="C", published_at="2026-05-18T10:00:00")
    assert r1.id != r2.id


def test_fetch_result_to_dict():
    r = FetchResult(
        source=SourceType.CNINFO,
        title="公告",
        content="内容",
        published_at="2026-05-18T10:00:00",
        stock_code="000001",
    )
    d = r.to_dict()
    assert d["id"] == r.id
    assert d["source"] == "cninfo"
    assert d["stock_code"] == "000001"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL with "No module named ..."

- [ ] **Step 3: Implement models.py**

```python
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional


class SourceType(str, Enum):
    CNINFO = "cninfo"
    EASTMONEY_REPORT = "eastmoney_report"
    EASTMONEY_NEWS = "eastmoney_news"
    ZSXQ = "zsxq"


def _compute_id(source: str, title: str, published_at: str) -> str:
    raw = f"{source}|{title}|{published_at}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass
class FetchResult:
    source: SourceType
    title: str
    content: str
    published_at: str

    # Optional common fields
    stock_code: Optional[str] = None
    stock_name: Optional[str] = None
    summary: Optional[str] = None
    url: Optional[str] = None
    authors: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    # ZSXQ-specific
    group_name: Optional[str] = None
    mentions_stocks: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not hasattr(self, "_id"):
            self._id = _compute_id(self.source.value, self.title, self.published_at)

    @property
    def id(self) -> str:
        return self._id if hasattr(self, "_id") else _compute_id(
            self.source.value, self.title, self.published_at
        )

    def to_dict(self) -> dict:
        d = asdict(self)
        d["id"] = self.id
        d["source"] = self.source.value
        d.pop("_id", None)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> FetchResult:
        data["source"] = SourceType(data["source"])
        return cls(**data)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: 5 PASSED

---

### Task 2: Configuration management

**Files:**
- Create: `src/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the test**

```python
"""Tests for config."""
import tempfile
from pathlib import Path
from src.config import Config, load_config


def test_config_defaults():
    c = Config()
    assert c.data_dir == Path("data")
    assert c.zsxq_cookie == ""


def test_config_load_with_file():
    content = """
data_dir = "/tmp/ff-data"
zsxq_cookie = "test-cookie"

[watchlist]
stocks = ["000001", "600519"]
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(content)
        p = f.name
    try:
        c = load_config(p)
        assert c.data_dir.resolve() == Path("/tmp/ff-data").resolve()
        assert c.zsxq_cookie == "test-cookie"
        assert c.watchlist == ["000001", "600519"]
    finally:
        Path(p).unlink()


def test_config_to_dict():
    c = Config(zsxq_cookie="abc", watchlist=["000001"])
    d = c.to_dict()
    assert d["zsxq_cookie"] == "abc"
    assert d["watchlist"]["stocks"] == ["000001"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL

- [ ] **Step 3: Implement config.py**

```python
from __future__ import annotations

from pathlib import Path
from typing import Optional
import toml


class Config:
    def __init__(
        self,
        data_dir: Path | str = Path("data"),
        zsxq_cookie: str = "",
        watchlist: list[str] | None = None,
    ):
        self.data_dir = Path(data_dir).resolve()
        self.zsxq_cookie = zsxq_cookie
        self.watchlist = watchlist or []

    def to_dict(self) -> dict:
        return {
            "data_dir": str(self.data_dir),
            "zsxq_cookie": self.zsxq_cookie,
            "watchlist": {"stocks": self.watchlist},
        }


def load_config(path: str | Path | None = None) -> Config:
    path = Path(path) if path else Path("config.toml")
    if not path.exists():
        return Config()
    raw = toml.load(path)
    data = raw.get("config", raw)
    return Config(
        data_dir=data.get("data_dir", "data"),
        zsxq_cookie=data.get("zsxq_cookie", ""),
        watchlist=data.get("watchlist", {}).get("stocks", []),
    )


def save_config(config: Config, path: str | Path = Path("config.toml")) -> None:
    path = Path(path)
    path.write_text(toml.dumps({"config": config.to_dict()}))
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_config.py -v`
Expected: PASS

---

### Task 3: HTTP client utility

**Files:**
- Create: `src/utils/http.py`
- Test: `tests/test_http.py`

- [ ] **Step 1: Write the test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_http.py -v`
Expected: FAIL

- [ ] **Step 3: Implement http.py**

```python
from __future__ import annotations

import httpx


def create_client(
    cookie: str = "",
    headers: dict[str, str] | None = None,
    timeout: float = 15.0,
) -> httpx.AsyncClient:
    default_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
    }
    if cookie:
        default_headers["Cookie"] = cookie
    if headers:
        default_headers.update(headers)
    return httpx.AsyncClient(
        headers=default_headers,
        timeout=httpx.Timeout(timeout, connect=timeout),
        follow_redirects=True,
    )
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_http.py -v`
Expected: PASS

---

### Task 4: Date utility

**Files:**
- Create: `src/utils/date.py`
- Test: `tests/test_date.py`

- [ ] **Step 1: Write the test**

```python
"""Tests for date utilities."""
from src.utils.date import parse_date, days_ago_iso


def test_parse_date_iso():
    assert parse_date("2026-05-18T10:00:00") == "2026-05-18T10:00:00"


def test_parse_date_cn():
    assert parse_date("2026-05-18 10:00:00") == "2026-05-18T10:00:00"


def test_days_ago_iso():
    result = days_ago_iso(0)
    from datetime import date
    assert result.startswith(str(date.today()))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_date.py -v`
Expected: FAIL

- [ ] **Step 3: Implement date.py**

```python
from datetime import datetime, timedelta, date


def parse_date(s: str) -> str:
    """Normalize various date formats to ISO 8601."""
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%dT%H:%M:%S")
        except ValueError:
            continue
    return s


def days_ago_iso(days: int) -> str:
    dt = date.today() - timedelta(days=days)
    return dt.strftime("%Y-%m-%dT00:00:00")
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_date.py -v`
Expected: PASS

---

### Task 5: Storage layer

**Files:**
- Create: `src/storage.py`
- Test: `tests/test_storage.py`

- [ ] **Step 1: Write the test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_storage.py -v`
Expected: FAIL

- [ ] **Step 3: Implement storage.py**

```python
from __future__ import annotations

from pathlib import Path
import json
from src.models import FetchResult, SourceType


class Storage:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    def _result_path(self, r: FetchResult) -> Path:
        if r.source == SourceType.ZSXQ:
            group = r.group_name or "default"
            base = self.data_dir / "zsxq" / group
        else:
            code = r.stock_code or "unknown"
            base = self.data_dir / code / r.source.value
        month = r.published_at[:7]  # YYYY-MM
        return base / month / f"{r.id}.json"

    def exists(self, r: FetchResult) -> bool:
        return self._result_path(r).exists()

    def save(self, r: FetchResult) -> Path:
        path = self._result_path(r)
        if path.exists():
            return path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(r.to_dict(), ensure_ascii=False, indent=2))
        return path
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_storage.py -v`
Expected: PASS

---

### Task 6: Fetcher base class

**Files:**
- Create: `src/fetchers/base.py`
- Test: `tests/test_fetcher_base.py`

- [ ] **Step 1: Write the test**

```python
"""Tests for fetcher base class."""
from src.fetchers.base import Fetcher
from src.models import FetchResult, SourceType


class DummyFetcher(Fetcher):
    source = SourceType.CNINFO

    async def fetch(self, stock_code=None, stock_name=None, since=None, limit=50):
        return [
            FetchResult(
                source=self.source,
                title="test",
                content="test",
                published_at="2026-05-18T10:00:00",
                stock_code=stock_code,
            )
        ]


def test_fetcher_abstract():
    f = DummyFetcher()
    assert f.source == SourceType.CNINFO


def test_fetcher_name_property():
    f = DummyFetcher()
    assert f.name == "cninfo"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_fetcher_base.py -v`
Expected: FAIL

- [ ] **Step 3: Implement base.py**

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
from src.models import FetchResult, SourceType


class Fetcher(ABC):
    source: SourceType

    @property
    def name(self) -> str:
        return self.source.value

    @abstractmethod
    async def fetch(
        self,
        stock_code: Optional[str] = None,
        stock_name: Optional[str] = None,
        since: Optional[str] = None,
        limit: int = 50,
    ) -> list[FetchResult]:
        ...
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_fetcher_base.py -v`
Expected: PASS

---

### Task 7: Cninfo fetcher (巨潮资讯 — company announcements)

**Files:**
- Create: `src/fetchers/cninfo.py`
- Test: `tests/test_cninfo.py`

- [ ] **Step 1: Write the test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cninfo.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement cninfo.py**

```python
from __future__ import annotations

from typing import Optional
from src.fetchers.base import Fetcher
from src.models import FetchResult, SourceType
from src.utils.http import create_client

# Column code mapping: 沪市主板=sse, 深市主板/创业板=szse, 科创板=sse
_MARKET_MAP = {
    "600": "sse", "601": "sse", "603": "sse", "688": "sse",
    "000": "szse", "001": "szse", "002": "szse", "300": "szse",
}


def _guess_market(code: str) -> str:
    prefix = code[:3]
    return _MARKET_MAP.get(prefix, "szse")


class CninfoFetcher(Fetcher):
    source = SourceType.CNINFO

    async def fetch(
        self,
        stock_code: Optional[str] = None,
        stock_name: Optional[str] = None,
        since: Optional[str] = None,
        limit: int = 50,
    ) -> list[FetchResult]:
        if not stock_code:
            return []
        market = _guess_market(stock_code)
        results: list[FetchResult] = []
        async with create_client(timeout=20.0) as client:
            resp = await client.post(
                "http://www.cninfo.com.cn/new/hisAnnouncement/query",
                data={
                    "stock": stock_code,
                    "pageNum": 1,
                    "pageSize": min(limit, 30),
                    "column": market,
                    "tabName": "fulltext",
                    "plate": "",
                    "category": "",
                    "searchkey": "",
                    "secid": "",
                    "seDate": f"{since or '2025-01-01'} ~ {since or '2026-12-31'}",
                    "sortName": "",
                    "sortType": "",
                    "isHLtitle": "true",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            data = resp.json()
            for item in data.get("announcements", []):
                pub = item.get("announcementTime", "")
                if pub and len(pub) >= 10:
                    pub = pub[:10] + "T" + pub[11:19] if "T" not in pub else pub
                results.append(FetchResult(
                    source=self.source,
                    title=item.get("announcementTitle", ""),
                    content="",
                    summary=item.get("announcementTitle", ""),
                    published_at=pub or "2026-01-01T00:00:00",
                    stock_code=stock_code,
                    url=f"http://www.cninfo.com.cn/new/disclosure/detail?stockCode={stock_code}&announcementId={item.get('announcementId', '')}",
                    tags=["公告"],
                ))
        return results[:limit]
```

- [ ] **Step 4: Run integration test**

Run: `pytest tests/test_cninfo.py -v`
Expected: PASS (hits real API)

---

### Task 8: Eastmoney fetcher (研报 + 新闻)

**Files:**
- Create: `src/fetchers/eastmoney.py`
- Test: `tests/test_eastmoney.py`

- [ ] **Step 1: Write the test**

```python
"""Tests for eastmoney fetcher."""
import pytest
from src.fetchers.eastmoney import EastmoneyReportFetcher, EastmoneyNewsFetcher


@pytest.mark.asyncio
async def test_eastmoney_report_fetch():
    f = EastmoneyReportFetcher()
    results = await f.fetch(stock_code="000001", limit=5)
    assert len(results) > 0
    for r in results:
        assert r.source.value == "eastmoney_report"
        assert r.title


@pytest.mark.asyncio
async def test_eastmoney_news_fetch():
    f = EastmoneyNewsFetcher()
    results = await f.fetch(stock_code="000001", limit=5)
    assert len(results) > 0
    for r in results:
        assert r.source.value == "eastmoney_news"
        assert r.title
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_eastmoney.py -v`
Expected: FAIL

- [ ] **Step 3: Implement eastmoney.py**

```python
from __future__ import annotations

from typing import Optional
from src.fetchers.base import Fetcher
from src.models import FetchResult, SourceType
from src.utils.http import create_client


class EastmoneyReportFetcher(Fetcher):
    source = SourceType.EASTMONEY_REPORT

    async def fetch(
        self,
        stock_code: Optional[str] = None,
        stock_name: Optional[str] = None,
        since: Optional[str] = None,
        limit: int = 50,
    ) -> list[FetchResult]:
        if not stock_code:
            return []
        results: list[FetchResult] = []
        url = (
            f"https://reportapi.eastmoney.com/report/list"
            f"?stockCode={stock_code}"
            f"&pageSize={min(limit, 50)}"
            f"&pageNo=1"
        )
        async with create_client() as client:
            resp = await client.get(url)
            data = resp.json()
            for item in data.get("data", data.get("list", [])):
                results.append(FetchResult(
                    source=self.source,
                    title=item.get("title", item.get("infoTitle", ""))[:500],
                    content=item.get("abstract", item.get("infoContent", "")),
                    summary=item.get("abstract", ""),
                    published_at=(item.get("publishDate") or "").replace("T", "T")[:19],
                    stock_code=stock_code,
                    url=item.get("url", ""),
                    authors=[item.get("author", item.get("researchName", ""))],
                    tags=["研报"],
                ))
        return results[:limit]


class EastmoneyNewsFetcher(Fetcher):
    source = SourceType.EASTMONEY_NEWS

    async def fetch(
        self,
        stock_code: Optional[str] = None,
        stock_name: Optional[str] = None,
        since: Optional[str] = None,
        limit: int = 50,
    ) -> list[FetchResult]:
        if not stock_code:
            return []
        results: list[FetchResult] = []
        code_num = stock_code.lstrip("0") if stock_code else ""
        url = (
            f"https://search-api-web.eastmoney.com/search/jsonp"
            f"?cb=jQuery&param=%7B%22uid%22%3A%22%22%2C%22keyword%22%3A%22{stock_code}%22%2C%22type%22%3A%5B%22cmsArticleWebOld%22%5D%2C%22client%22%3A%22web%22%2C%22clientType%22%3A%22web%22%2C%22clientVersion%22%3A%22curr%22%2C%22param%22%3A%7B%22cmsArticleWebOld%22%3A%7B%22searchScope%22%3A%22default%22%2C%22sort%22%3A%22default%22%2C%22pageIndex%22%3A1%2C%22pageSize%22%3A{min(limit, 20)}%7D%7D%7D"
        )
        async with create_client() as client:
            resp = await client.get(url)
            text = resp.text
            import json
            start = text.index("(") + 1
            end = text.rindex(")")
            data = json.loads(text[start:end])
            for item in data.get("result", {}).get("cmsArticleWebOld", {}).get("list", []):
                results.append(FetchResult(
                    source=self.source,
                    title=item.get("title", ""),
                    content=item.get("content", item.get("summary", "")),
                    summary=item.get("summary", ""),
                    published_at=(item.get("date") or "").replace("T", "T")[:19],
                    stock_code=stock_code,
                    url=item.get("url", item.get("articleUrl", "")),
                    tags=["新闻"],
                ))
        return results[:limit]
```

- [ ] **Step 4: Run integration tests**

Run: `pytest tests/test_eastmoney.py -v`
Expected: PASS

---

### Task 9: ZSXQ fetcher (知识星球)

**Files:**
- Create: `src/fetchers/zsxq.py`
- Test: `tests/test_zsxq.py`

- [ ] **Step 1: Write the test**

```python
"""Tests for zsxq fetcher."""
import pytest
from src.fetchers.zsxq import ZsxqFetcher


@pytest.mark.asyncio
async def test_zsxq_list_groups():
    f = ZsxqFetcher(cookie="zsxq_access_token=placeholder")
    try:
        groups = await f.list_groups()
    except Exception as e:
        # Without a valid cookie this will fail — test the structure
        assert "401" in str(e) or "403" in str(e)


def test_zsxq_requires_cookie():
    try:
        ZsxqFetcher(cookie="")
    except ValueError:
        return
    assert False, "Should have raised ValueError"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_zsxq.py -v`
Expected: FAIL

- [ ] **Step 3: Implement zsxq.py**

```python
from __future__ import annotations

from typing import Optional
from src.fetchers.base import Fetcher
from src.models import FetchResult, SourceType
from src.utils.http import create_client


class ZsxqFetcher(Fetcher):
    source = SourceType.ZSXQ

    def __init__(self, cookie: str = ""):
        if not cookie:
            raise ValueError("ZSXQ fetcher requires a cookie")
        self.cookie = cookie

    async def list_groups(self) -> list[dict]:
        async with create_client(cookie=self.cookie) as client:
            resp = await client.get("https://api.zsxq.com/v2/groups")
            resp.raise_for_status()
            data = resp.json()
            return data.get("resp_data", {}).get("groups", [])

    async def fetch(
        self,
        stock_code: Optional[str] = None,
        stock_name: Optional[str] = None,
        since: Optional[str] = None,
        limit: int = 50,
    ) -> list[FetchResult]:
        results: list[FetchResult] = []
        async with create_client(cookie=self.cookie) as client:
            groups = await self.list_groups()
            for group in groups:
                group_id = group.get("group_id")
                name = group.get("name", "")
                topics = await self._fetch_topics(client, group_id, limit)
                for t in topics:
                    results.append(FetchResult(
                        source=self.source,
                        title=t.get("title", ""),
                        content=t.get("text", ""),
                        published_at=(t.get("create_time") or "")[:19],
                        url=f"https://wx.zsxq.com/topic/{t.get('topic_id', '')}",
                        group_name=name,
                    ))
        return results

    async def _fetch_topics(self, client, group_id: str, limit: int) -> list[dict]:
        topics: list[dict] = []
        url = f"https://api.zsxq.com/v2/groups/{group_id}/topics"
        resp = await client.get(url, params={"count": min(limit, 20)})
        resp.raise_for_status()
        data = resp.json()
        for item in data.get("resp_data", {}).get("topics", []):
            talk = item.get("talk", {})
            text_parts: list[str] = []
            for part in talk.get("text", ""):
                if isinstance(part, dict):
                    text_parts.append(part.get("text", ""))
            full_text = "".join(text_parts)
            topics.append({
                "title": full_text[:80] or "无标题",
                "text": full_text,
                "create_time": item.get("create_time", ""),
                "topic_id": item.get("topic_id", ""),
            })
        return topics
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_zsxq.py -v`
Expected: PASS (only structural tests, integration needs real cookie)

---

### Task 10: CLI entry point

**Files:**
- Create: `src/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the test**

```python
"""Tests for CLI."""
from click.testing import CliRunner
from src.cli import main


def test_cli_search_no_args():
    runner = CliRunner()
    result = runner.invoke(main, ["search"])
    assert result.exit_code != 0


def test_cli_search_missing_code():
    runner = CliRunner()
    result = runner.invoke(main, ["search"])
    assert "stock_code" in result.output.lower() or result.exit_code != 0


def test_cli_watch_list_empty():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["watch", "list"])
        assert result.exit_code == 0


def test_cli_zsxq_no_cookie():
    runner = CliRunner()
    result = runner.invoke(main, ["zsxq", "list"])
    # Should either error or warn about missing cookie
    assert result.exit_code != 0 or "cookie" in result.output.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL

- [ ] **Step 3: Implement cli.py**

```python
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
import click

from src.config import load_config
from src.storage import Storage
from src.fetchers.cninfo import CninfoFetcher
from src.fetchers.eastmoney import EastmoneyReportFetcher, EastmoneyNewsFetcher
from src.fetchers.zsxq import ZsxqFetcher


@click.group()
@click.option("--config", "-c", default=None, help="Config file path")
@click.pass_context
def main(ctx, config):
    ctx.ensure_object(dict)
    cfg = load_config(config)
    ctx.obj["config"] = cfg
    ctx.obj["storage"] = Storage(cfg.data_dir)


@main.command()
@click.argument("stock_code")
@click.option("--sources", default="all", help="Sources: all,announcements,reports,news")
@click.option("--days", default=30, type=int, help="Days of history")
@click.pass_context
def search(ctx, stock_code, sources, days):
    """Search fundamental information for a stock."""
    from src.utils.date import days_ago_iso
    since = days_ago_iso(days)
    fetchers = []
    if sources in ("all", "announcements"):
        fetchers.append(CninfoFetcher())
    if sources in ("all", "reports"):
        fetchers.append(EastmoneyReportFetcher())
    if sources in ("all", "news"):
        fetchers.append(EastmoneyNewsFetcher())

    storage: Storage = ctx.obj["storage"]
    total = 0

    async def run():
        nonlocal total
        for fetcher in fetchers:
            try:
                results = await fetcher.fetch(
                    stock_code=stock_code, since=since, limit=30
                )
                for r in results:
                    storage.save(r)
                click.echo(f"  {fetcher.name}: {len(results)} items")
                total += len(results)
            except Exception as e:
                click.echo(f"  {fetcher.name}: ERROR - {e}", err=True)

    asyncio.run(run())
    click.echo(f"\nTotal saved: {total} items")


@main.group()
@click.pass_context
def watch(ctx):
    """Manage watchlist."""


@watch.command("list")
@click.pass_context
def watch_list(ctx):
    """List watched stocks."""
    cfg = ctx.obj["config"]
    if not cfg.watchlist:
        click.echo("Watchlist is empty")
        return
    for code in cfg.watchlist:
        click.echo(code)


@watch.command("add")
@click.argument("codes", nargs=-1, required=True)
@click.pass_context
def watch_add(ctx, codes):
    """Add stocks to watchlist."""
    cfg = ctx.obj["config"]
    from src.config import save_config
    existing = set(cfg.watchlist)
    for code in codes:
        if code not in existing:
            cfg.watchlist.append(code)
            click.echo(f"Added: {code}")
    save_config(cfg)


@watch.command("update")
@click.option("--days", default=7, type=int)
@click.pass_context
def watch_update(ctx, days):
    """Fetch latest data for all watched stocks."""
    from src.utils.date import days_ago_iso
    since = days_ago_iso(days)
    cfg = ctx.obj["config"]
    storage: Storage = ctx.obj["storage"]
    if not cfg.watchlist:
        click.echo("Watchlist is empty. Use 'watch add' first.")
        return

    fetchers = [CninfoFetcher(), EastmoneyReportFetcher(), EastmoneyNewsFetcher()]
    total = 0

    async def run():
        nonlocal total
        for code in cfg.watchlist:
            click.echo(f"\n{code}:")
            for fetcher in fetchers:
                try:
                    results = await fetcher.fetch(
                        stock_code=code, since=since, limit=20
                    )
                    for r in results:
                        storage.save(r)
                    click.echo(f"  {fetcher.name}: {len(results)} new")
                    total += len(results)
                except Exception as e:
                    click.echo(f"  {fetcher.name}: ERROR - {e}", err=True)

    asyncio.run(run())
    click.echo(f"\nTotal new items: {total}")


@main.group()
@click.pass_context
def zsxq(ctx):
    """Knowledge Planet operations."""


@zsxq.command("list")
@click.pass_context
def zsxq_list(ctx):
    """List accessible groups."""
    cfg = ctx.obj["config"]
    if not cfg.zsxq_cookie:
        click.echo("No ZSXQ cookie configured. Use: ff config --cookie-zsxq <token>")
        return
    fetcher = ZsxqFetcher(cookie=cfg.zsxq_cookie)

    async def run():
        groups = await fetcher.list_groups()
        for g in groups:
            click.echo(f"  {g.get('group_id')}: {g.get('name', 'unknown')}")

    asyncio.run(run())


@zsxq.command("fetch")
@click.option("--group", default=None, help="Group ID to fetch (all if omitted)")
@click.option("--days", default=7, type=int)
@click.pass_context
def zsxq_fetch(ctx, group, days):
    """Fetch topics from groups."""
    from src.utils.date import days_ago_iso
    since = days_ago_iso(days)
    cfg = ctx.obj["config"]
    if not cfg.zsxq_cookie:
        click.echo("No ZSXQ cookie configured.")
        return

    storage: Storage = ctx.obj["storage"]
    fetcher = ZsxqFetcher(cookie=cfg.zsxq_cookie)

    async def run():
        results = await fetcher.fetch(limit=50)
        saved = 0
        for r in results:
            if group and r.group_name != group:
                continue
            storage.save(r)
            saved += 1
        click.echo(f"Saved {saved} items")

    asyncio.run(run())


@main.command()
@click.option("--cookie-zsxq", default=None, help="Set ZSXQ cookie")
@click.pass_context
def config(ctx, cookie_zsxq):
    """View or modify configuration."""
    cfg = ctx.obj["config"]
    if cookie_zsxq:
        cfg.zsxq_cookie = cookie_zsxq
        from src.config import save_config
        save_config(cfg)
        click.echo("Cookie updated")
    else:
        click.echo(f"Data dir: {cfg.data_dir}")
        click.echo(f"ZSXQ cookie: {'set' if cfg.zsxq_cookie else 'not set'}")
        click.echo(f"Watchlist: {cfg.watchlist or 'empty'}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run CLI tests**

Run: `pytest tests/test_cli.py -v`
Expected: PASS

---

### Task 11: Fetcher __init__ exports

**Files:**
- Modify: `src/fetchers/__init__.py`

- [ ] **Step 1: Write __init__.py exports**

```python
from src.fetchers.cninfo import CninfoFetcher
from src.fetchers.eastmoney import EastmoneyReportFetcher, EastmoneyNewsFetcher
from src.fetchers.zsxq import ZsxqFetcher

__all__ = [
    "CninfoFetcher",
    "EastmoneyReportFetcher",
    "EastmoneyNewsFetcher",
    "ZsxqFetcher",
]
```

- [ ] **Step 2: Verify imports work**

Run: `python -c "from src.fetchers import CninfoFetcher; print('OK')"`
Expected: OK
