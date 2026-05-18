# Merge xueqiu-fetcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans.

**Goal:** Integrate xueqiu (雪球) stock community scraper as a new data source into the `ff` CLI.

**Architecture:** Copy xueqiu models and scraper into `src/fetchers/`, add `ff xueqiu` CLI commands, save output to `~/.fundamental-data/xueqiu/<symbol>/`.

---

### Task 1: Add dependencies

**Files:**
- Modify: `requirements.txt`
- Modify: `pyproject.toml`

- [ ] **Step 1: Update requirements.txt**

Append:
```
playwright>=1.50.0
cloakbrowser>=0.1.0
rich>=13.0.0
pydantic>=2.0.0
```

- [ ] **Step 2: Update pyproject.toml**

```toml
dependencies = [
    "httpx>=0.27.0",
    "click>=8.1.0",
    "beautifulsoup4>=4.12.0",
    "lxml>=5.0.0",
    "toml>=0.10.2",
    "playwright>=1.50.0",
    "cloakbrowser>=0.1.0",
    "rich>=13.0.0",
    "pydantic>=2.0.0",
]
```

- [ ] **Step 3: Install**

Run: `pip install -e .`

---

### Task 2: Copy xueqiu models

**Files:**
- Create: `src/fetchers/xueqiu_models.py`

Copy from `../xueqiu-fetcher/fetcher/models.py` (pydantic models: User, CommunityPost, StockCommunity, RecommendUser, APIResponse).

---

### Task 3: Copy xueqiu scraper

**Files:**
- Create: `src/fetchers/xueqiu.py`

Copy from `../xueqiu-fetcher/fetcher/xueqiu.py` (XueqiuScraper class). Adjust imports to point to `src.fetchers.xueqiu_models`.

---

### Task 4: Add CLI commands

**Files:**
- Modify: `src/cli.py`
- Test: `tests/test_xueqiu_cli.py`

- [ ] **Step 1: Write test**

```python
"""Tests for xueqiu CLI."""
from click.testing import CliRunner
from src.cli import main


def test_xueqiu_search_no_symbol():
    runner = CliRunner()
    result = runner.invoke(main, ["xueqiu", "search"])
    assert result.exit_code != 0
```

- [ ] **Step 2: Implement CLI**

Add to `src/cli.py`:
```python
@main.group()
@click.pass_context
def xueqiu(ctx):
    """雪球社区帖子抓取"""


@xueqiu.command("search")
@click.argument("symbol")
@click.option("--pages", default=3, type=int, help="抓取页数")
@click.option("--sort", type=click.Choice(["time", "alpha"]), default="time",
              help="time=最新 alpha=热帖")
@click.option("--before", help="日期过滤 YYYY-MM-DD")
@click.option("--limit", default=20, type=int, help="每页条数")
@click.option("--headless/--no-headless", default=True)
@click.pass_context
def xueqiu_search(ctx, symbol, pages, sort, before, limit, headless):
    """抓取雪球社区帖子"""
    ...
```

---

### Task 5: Update fetcher __init__

**Files:**
- Modify: `src/fetchers/__init__.py`

Add: `from src.fetchers.xueqiu import XueqiuScraper`
