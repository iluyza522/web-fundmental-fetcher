---
name: ff
description: A-share stock fundamental text data fetcher CLI. Search company announcements (巨潮), research reports and news (东方财富), Knowledge Planet (zsxq) content, and Xueqiu (雪球) community posts. Use when user wants to fetch/find/search stock info, financial reports, research reports, zsxq content, xueqiu community posts, or fundamental data for A-share (Chinese) stocks.
---

# Fundamental Fetcher

A 股基本面文本信息搜集 CLI 工具。从巨潮资讯（公告）、东方财富（研报+新闻）、知识星球、雪球拉取信息，JSON 格式存入 `~/.fundamental-data/`。

## Commands

```
ff search <code>        拉取公告+研报+新闻
ff quote <code>         获取股票实时市值
ff zsxq list            列出已加入的星球
ff zsxq fetch           拉取星球最新内容
ff zsxq search <kw>     搜索星球历史内容
ff xueqiu hot           抓取雪球首页热门帖子
ff xueqiu kw <keyword>  按关键词搜索雪球帖子
ff xueqiu search <sym>  抓取雪球个股社区帖子
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
ff xueqiu hot                              首页热门（默认过滤粉丝≥500, 字数≥300）
ff xueqiu hot --min-followers 0 --min-length 0  取消过滤
ff xueqiu kw 预期                          关键词搜索
ff xueqiu kw 半导体 --sort alpha --pages 5  综合排序搜索5页
ff xueqiu search SH600519                  个股社区
ff xueqiu search SH600519 --min-followers 10000  只看粉丝过万

# Quote (实时市值)
ff quote 600519                            贵州茅台市值
```

## Data Storage

```
~/.fundamental-data/
├── <stock_code>/    公告/研报/新闻
├── zsxq/<星球名>/    星球内容
├── search/<关键词>/  星球搜索结果
├── xueqiu/<symbol>/ 雪球个股社区帖子
├── xueqiu/hot/      雪球首页热门
├── xueqiu/search/<keyword>/ 雪球关键词搜索结果
```

## Config

知识星球 Cookie 获取: 浏览器登录 wx.zsxq.com → F12 → Application → Cookies → 复制 zsxq_access_token
