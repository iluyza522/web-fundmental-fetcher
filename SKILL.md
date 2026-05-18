---
name: ff
description: A-share stock fundamental text data fetcher CLI. Search company announcements (巨潮), research reports and news (东方财富), Knowledge Planet (zsxq) content, and Xueqiu (雪球) community posts. Use when user wants to fetch/find/search stock info, financial reports, research reports, zsxq content, xueqiu community posts, or fundamental data for A-share (Chinese) stocks.
---

# Fundamental Fetcher

A 股基本面文本信息搜集 CLI 工具。从巨潮资讯（公告）、东方财富（研报+新闻）、知识星球、雪球拉取信息，JSON 格式存入 `~/.fundamental-data/`。

## Commands

```
ff search <code>        拉取公告+研报+新闻
ff zsxq list            列出已加入的星球
ff zsxq fetch           拉取星球最新内容
ff zsxq search <kw>     搜索星球历史内容
ff xueqiu search <sym>  抓取雪球社区帖子
ff config               查看/设置 Cookie
```

## Quick Start

```bash
# Search a stock
ff search 000001
ff search 600519 --sources news --days 7

# Knowledge Planet (requires cookie)
ff config --cookie-zsxq "zsxq_access_token=xxx"
ff zsxq list
ff zsxq fetch --days 7
ff zsxq search 茅台

# Xueqiu (requires playwright chromium)
ff xueqiu search SH600519
ff xueqiu search SZ000858 --sort alpha --pages 5
```

## Data Storage

```
~/.fundamental-data/
├── <stock_code>/    公告/研报/新闻
├── zsxq/<星球名>/    星球内容
├── search/<关键词>/  星球搜索结果
└── xueqiu/<symbol>/ 雪球社区帖子
```

## Config

知识星球 Cookie 获取: 浏览器登录 wx.zsxq.com → F12 → Application → Cookies → 复制 zsxq_access_token
