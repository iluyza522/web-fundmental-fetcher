"""Command-line interface for the fundamental data fetcher."""

from __future__ import annotations

import asyncio
from pathlib import Path

import click

from src.config import load_config, save_config
from src.storage import Storage
from src.fetchers.cninfo import CninfoFetcher
from src.fetchers.eastmoney import EastmoneyReportFetcher, EastmoneyNewsFetcher
from src.fetchers.zsxq import ZsxqFetcher
from src.fetchers.xueqiu import XueqiuScraper, SortBy
from src.models import FetchResult, SourceType
from src.utils.http import create_client


@click.group(invoke_without_command=True)
@click.option("--config", "-c", default=None, help="Config file path")
@click.pass_context
def main(ctx, config):
    """A 股基本面文本信息搜集工具

    从巨潮资讯、东方财富、知识星球等数据源搜集 A 股基本面文本信息
    （公司公告、券商研报、财经新闻、星球讨论），统一以 JSON 格式存入本地。

    数据存储结构:
        data/<stock_code>/    公告/研报/新闻（按股票代码分类）
        data/zsxq/<星球名>/    知识星球内容
        data/search/<关键词>/  星球搜索结果

    使用前需要配置知识星球 Cookie:
        ff config --cookie-zsxq "zsxq_access_token=你的token"

    Examples:
        ff search 000001             搜索平安银行（公告+研报+新闻）
        ff search 600519 --sources news 只拉贵州茅台新闻
        ff zsxq list                 列出星球
        ff zsxq fetch                拉取星球内容
        ff zsxq search 先导基电       搜索星球历史
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        return
    ctx.ensure_object(dict)
    cfg = load_config(config)
    ctx.obj["config"] = cfg
    ctx.obj["storage"] = Storage(cfg.data_dir)


@main.command()
@click.argument("stock_code")
@click.option("--sources", default="all",
              help="数据源: all(全部), announcements(公告), reports(研报), news(新闻)")
@click.option("--days", default=30, type=int, help="搜索范围: 最近几天")
@click.option("--limit", default=30, type=int, help="每个来源最多拉取条数")
@click.pass_context
def search(ctx, stock_code, sources, days, limit):
    """按股票代码搜索基本面信息

    同时从巨潮资讯（公告）、东方财富（研报+新闻）拉取数据，去重后存入本地。

    示例:
        ff search 000001               搜索平安银行全部来源
        ff search 600519 --sources news 只搜索贵州茅台新闻
        ff search 300750 --days 7      只搜索最近7天
    """
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
                    stock_code=stock_code, since=since, limit=limit
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
def zsxq(ctx):
    """知识星球操作

    需要先配置 Cookie 才能使用:
        ff config --cookie-zsxq "zsxq_access_token=你的token"
    """


@zsxq.command("list")
@click.pass_context
def zsxq_list(ctx):
    """列出已加入的知识星球"""
    cfg = ctx.obj["config"]
    if not cfg.zsxq_cookie:
        click.echo("No ZSXQ cookie configured. Use: ff config --cookie-zsxq <token>")
        return
    fetcher = ZsxqFetcher(cookie=cfg.zsxq_cookie)

    async def run():
        groups = await fetcher.list_groups()
        if not groups:
            click.echo("No groups found. Check your cookie.")
            return
        click.echo("Your groups:")
        for g in groups:
            click.echo(f"  {g.get('group_id')}: {g.get('name', 'unknown')}")

    asyncio.run(run())


@zsxq.command("fetch")
@click.option("--group", default=None, help="星球 Group ID（不指定则拉取全部）")
@click.option("--days", default=7, type=int, help="最近几天")
@click.option("--limit", default=200, type=int, help="最大拉取条数")
@click.pass_context
def zsxq_fetch(ctx, group, days, limit):
    """拉取知识星球最新内容

    遍历所有或指定星球，拉取最新讨论话题并存入 data/zsxq/ 目录。
    结果按星球名称+月份分目录存储。

    示例:
        ff zsxq fetch             拉取所有星球最近7天内容
        ff zsxq fetch --days 30   拉取最近30天
        ff zsxq fetch --limit 500 最多拉取500条
    """
    from src.utils.date import days_ago_iso

    since = days_ago_iso(days)
    cfg = ctx.obj["config"]
    if not cfg.zsxq_cookie:
        click.echo("No ZSXQ cookie configured.")
        return

    storage: Storage = ctx.obj["storage"]
    fetcher = ZsxqFetcher(cookie=cfg.zsxq_cookie)

    async def run():
        results = await fetcher.fetch(since=since, limit=limit)
        saved = 0
        for r in results:
            if group and r.group_name != group:
                continue
            storage.save(r)
            saved += 1
        click.echo(f"Saved {saved} items")

    asyncio.run(run())


@zsxq.command("search")
@click.argument("keyword")
@click.option("--limit", default=50, type=int, help="最大返回条数")
@click.pass_context
def zsxq_search(ctx, keyword, limit):
    """搜索知识星球历史内容

    使用知识星球内置搜索引擎搜索所有历史内容（不限时间范围），
    匹配结果存入 data/search/<关键词>/ 目录。

    示例:
        ff zsxq search 先导基电     搜索历史讨论
        ff zsxq search 茅台         搜索茅台相关
        ff zsxq search 半导体 --limit 200  搜索更多结果
    """
    cfg = ctx.obj["config"]
    if not cfg.zsxq_cookie:
        click.echo("No ZSXQ cookie configured.")
        return

    fetcher = ZsxqFetcher(cookie=cfg.zsxq_cookie)

    async def run():
        async with create_client(cookie=cfg.zsxq_cookie) as client:
            # Warm up session — retry if rate limited
            groups = []
            for attempt in range(3):
                resp = await client.get("https://api.zsxq.com/v2/groups")
                groups = resp.json().get("resp_data", {}).get("groups", [])
                if groups:
                    break
                if attempt < 2:
                    await asyncio.sleep(1)
            found = 0
            search_dir = cfg.data_dir / "search" / keyword
            for g in groups:
                gid = g.get("group_id")
                name = g.get("name", "unknown")
                click.echo(f"Searching {name}...")
                topics = await fetcher.search_topics(
                    keyword, group_id=gid, limit=limit, client=client
                )
                for t in topics:
                    ts = (t.get("create_time") or "")[:19]
                    r = FetchResult(
                        source=SourceType.ZSXQ,
                        title=t.get("title", ""),
                        content=t.get("text", ""),
                        published_at=ts,
                        url=f"https://wx.zsxq.com/topic/{t.get('topic_id', '')}",
                        group_name=name,
                    )
                    # Save to data/search/<keyword>/<YYYY-MM>/<id>.json
                    month = ts[:7]
                    path = search_dir / month / f"{r.id}.json"
                    if not path.exists():
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_text(
                            __import__("json").dumps(r.to_dict(), ensure_ascii=False, indent=2)
                        )
                    click.echo(f"  [{r.published_at[:10]}] {r.title[:60]}")
                    found += 1
        click.echo(f"\nFound and saved {found} items")

    asyncio.run(run())


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
    """抓取雪球社区帖子

    使用浏览器自动化绕过 WAF，抓取雪球个股社区讨论帖。

    示例:
        ff xueqiu search SH600519             贵州茅台社区帖子
        ff xueqiu search SH600519 --pages 5   抓取5页
        ff xueqiu search SZ000858 --sort hot  按热帖排序
        ff xueqiu search SH600519 --before 2026-01-01  日期过滤
    """
    from datetime import datetime
    import json
    from pathlib import Path

    cfg = ctx.obj["config"]
    output_dir = cfg.data_dir / "xueqiu" / symbol

    before_ts = None
    if before:
        try:
            dt = datetime.strptime(before, "%Y-%m-%d")
            before_ts = int(dt.timestamp() * 1000)
        except ValueError:
            click.echo(f"日期格式错误: {before}，请使用 YYYY-MM-DD", err=True)
            return

    sort_by = SortBy.ALPHA if sort == "alpha" else SortBy.TIME

    async def run():
        async with XueqiuScraper(headless=headless) as scraper:
            click.echo(f"Fetching {symbol}...")
            community = await scraper.get_stock_community(
                symbol=symbol,
                max_pages=pages,
                posts_per_page=limit,
                sort=sort_by,
                before=before_ts,
            )
            data = {
                "symbol": symbol,
                "stock_name": community.stock_name,
                "total_followers": community.total_followers,
                "total_posts": len(community.posts),
                "before_filter": before,
                "scraped_at": datetime.now().isoformat(),
                "posts": [
                    {
                        "id": p.id,
                        "created_at": p.created_at,
                        "datetime": p.created_datetime.isoformat(),
                        "user": {
                            "id": p.user.id,
                            "name": p.user.screen_name,
                            "profile": p.user.profile,
                            "followers": p.user.followers_count,
                        },
                        "content": p.cleaned_text,
                        "source": p.source,
                        "stats": {
                            "replies": p.reply_count,
                            "likes": p.like_count,
                            "views": p.view_count,
                            "favorites": p.fav_count,
                        },
                    }
                    for p in community.posts
                ],
            }
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = output_dir / f"{symbol}_community_{timestamp}.json"
            filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2))
            click.echo(f"Saved {len(community.posts)} posts to {filepath}")

    asyncio.run(run())


@main.command()
@click.option("--cookie-zsxq", default=None, help="设置知识星球 Cookie: zsxq_access_token=xxx")
@click.pass_context
def config(ctx, cookie_zsxq):
    """查看或修改配置

    配置保存在项目根目录的 config.toml 中。
    知识星球 Cookie 从浏览器开发者工具中获取:
        F12 → Application → Cookies → wx.zsxq.com → zsxq_access_token

    示例:
        ff config                               查看当前配置
        ff config --cookie-zsxq "zsxq_access_token=xxx"  设置 Cookie
    """
    cfg = ctx.obj["config"]
    if cookie_zsxq:
        cfg.zsxq_cookie = cookie_zsxq
        save_config(cfg)
        click.echo("Cookie updated")
    else:
        click.echo(f"Data dir: {cfg.data_dir}")
        click.echo(f"ZSXQ cookie: {'set' if cfg.zsxq_cookie else 'not set'}")


if __name__ == "__main__":
    main()
