# Fundamental Fetcher

A 股基本面文本信息搜集工具。从巨潮资讯（公司公告）、东方财富（研报+新闻）、知识星球、雪球等数据源搜集基本面文本信息，统一以 JSON 格式存入本地。

## 安装

### CLI 工具

```bash
git clone <repo-url>
cd fundamental-fetcher
pip install -e .
```

依赖：Python 3.11+, httpx, click, beautifulsoup4, lxml, toml, playwright, cloakbrowser, rich, pydantic

### Claude Code Skill（可选）

在 Claude Code 中可通过 `/ff` 调用此工具：

```bash
mkdir -p ~/.claude/skills/ff
cp SKILL.md ~/.claude/skills/ff/SKILL.md
```

## 使用

```bash
# 按股票代码搜索（公告 + 研报 + 新闻）
ff search 000001
ff search 600519 --sources news --days 7
ff search 300750 --limit 50

# 知识星球（需先配置 Cookie）
ff config --cookie-zsxq "zsxq_access_token=你的token"
ff zsxq list
ff zsxq fetch --days 7
ff zsxq search 茅台

# 雪球社区帖子（需安装 Playwright）
ff xueqiu search SH600519
ff xueqiu search SZ000858 --sort alpha --pages 5
ff xueqiu search SH600519 --before 2026-01-01

# 雪球首页热门
ff xueqiu hot

# 雪球关键词搜索
ff xueqiu kw 预期

# 实时市值
ff quote 600519
```

## 数据存储

```
~/.fundamental-data/
├── <stock_code>/    公告/研报/新闻（按股票代码分类）
├── zsxq/<星球名>/    知识星球内容
├── search/<关键词>/  星球搜索结果
├── xueqiu/<symbol>/ 雪球个股社区帖子
├── xueqiu/hot/      雪球首页热门
├── xueqiu/search/<keyword>/ 雪球关键词搜索
└── history.json     知识星球拉取历史
```

所有结果以 JSON 格式存储。

## 配置知识星球

1. 浏览器登录 [wx.zsxq.com](https://wx.zsxq.com)
2. F12 → Application → Cookies → `wx.zsxq.com`
3. 复制 `zsxq_access_token` 的值
4. 执行：

```bash
ff config --cookie-zsxq "zsxq_access_token=复制的值"
```

## 数据源

| 数据源 | 内容 | 认证 | 技术 |
|--------|------|------|------|
| 巨潮资讯 cninfo.com.cn | 公司公告 | 无 | HTTP API |
| 东方财富 eastmoney.com | 券商研报 + 财经新闻 | 无 | HTTP API |
| 知识星球 zsxq.com | 星球讨论/分析帖 | Cookie | HTTP API（`index` 1-based 页码翻页） |
| 雪球 xueqiu.com | 社区讨论帖 | 无 | Playwright 浏览器 |

## 命令参考

```
ff search <code>    搜索股票（公告+研报+新闻）
  --sources         数据源: all/announcements/reports/news
  --days            搜索范围（默认 30 天）
  --limit           每个来源最多条数（默认 30）

ff quote <code>     获取股票实时市值

ff zsxq list        列出已加入的星球
ff zsxq fetch       拉取星球最新内容
  --days            最近几天（默认 7）
  --limit           最大条数（默认 40）
  --exclude/--no-exclude  按屏蔽词过滤（默认启用）
  --print           打印帖子内容

ff zsxq search <keyword>  搜索星球历史内容
  --limit           最大条数（默认 50）
  --exclude/--no-exclude  按屏蔽词过滤（默认启用）

ff xueqiu hot       抓取雪球首页热门帖子
  --pages           最大抓取页数（默认 999，由字数上限控制）
  --min-followers   贴主最少粉丝数（默认 500）
  --max-followers   贴主最大粉丝数（默认 10000）
  --min-length      帖子最少字数（默认 300）
  --max-total-length 累计最大总字数（默认 20000）
  --exclude/--no-exclude  按屏蔽词过滤（默认启用）
  --print           打印帖子内容

ff xueqiu kw <keyword>  按关键词搜索雪球帖子
  --pages           最大抓取页数
  --sort            time/alpha 排序
  --limit           每页条数（默认 10）
  --min-followers   贴主最少粉丝数（默认 500）
  --max-followers   贴主最大粉丝数（默认 10000）
  --min-length      帖子最少字数（默认 300）
  --max-total-length 累计最大总字数（默认 20000）
  --exclude/--no-exclude  按屏蔽词过滤（默认启用）
  --print           打印帖子内容

ff xueqiu search <symbol>  抓取雪球个股社区帖子
  --pages           最大抓取页数
  --sort            time/alpha 排序
  --before          日期过滤 YYYY-MM-DD
  --limit           每页条数（默认 20）
  --min-followers   贴主最少粉丝数（默认 500）
  --max-followers   贴主最大粉丝数（默认 10000）
  --min-length      帖子最少字数（默认 300）
  --max-total-length 累计最大总字数（默认 20000）
  --exclude/--no-exclude  按屏蔽词过滤（默认启用）
  --print           打印帖子内容

ff config           查看或修改配置
  --cookie-zsxq     设置知识星球 Cookie
```

## 项目结构

```
src/
├── cli.py            CLI 入口（click）
├── config.py         配置管理（TOML）
├── models.py         数据模型（FetchResult, StockQuote）
├── storage.py        JSON 存储 + 去重
├── xueqiu_exclude.py 屏蔽词列表
├── zsxq_history.py   星球拉取历史追踪
├── fetchers/
│   ├── base.py       抽象基类
│   ├── cninfo.py     巨潮资讯
│   ├── eastmoney.py  东方财富
│   ├── zsxq.py       知识星球
│   ├── xueqiu.py     雪球（Playwright 浏览器）
│   ├── xueqiu_models.py  雪球数据模型
│   └── quote.py      实时市值（Playwright 浏览器）
└── utils/
    ├── http.py       HTTP 客户端
    └── date.py       日期工具
SKILL.md              Claude Code 技能定义
CLAUDE.md             项目文档
```
