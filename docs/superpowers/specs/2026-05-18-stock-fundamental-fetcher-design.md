# A 股基本面文本信息搜集工具 — 设计文档

## 概述

命令行工具，从互联网免费公开来源搜集 A 股基本面**文本信息**（公告、研报、新闻、行业报告），以及付费知识星球内容，统一以 JSON 格式存到本地。

## 数据源

| 数据源 | 类型 | 方式 | 认证 |
|--------|------|------|------|
| 巨潮资讯网 cninfo.com.cn | 公司公告 | 公开 JSONP API | 无 |
| 东方财富 data.eastmoney.com | 券商研报 + 财经新闻 | 公开 API / 页面解析 | 无 |
| 知识星球 zsxq.com | 星球讨论/分析帖 | 私有 API | Cookie |

## 架构

```
CLI (cli.py)
  │
  ├─ config.py          → TOML 配置文件管理
  ├─ storage.py         → JSON 存储 + 去重 + 索引
  ├─ models.py          → dataclass: FetchResult
  │
  ├─ fetchers/
  │   ├─ base.py        → abstract Fetcher
  │   ├─ cninfo.py      → 巨潮公告
  │   ├─ eastmoney.py   → 研报 + 新闻
  │   └─ zsxq.py        → 知识星球
  │
  └─ utils/
      ├─ http.py        → httpx.AsyncClient 统一会话
      └─ date.py        → 日期处理
```

## 数据模型

### 统一 FetchResult

```
id: str            = sha256(source + title + published_at)
source: str        = "cninfo" | "eastmoney_report" | "eastmoney_news" | "zsxq"
stock_code: str    = 6 位代码 / 空（星球）
stock_name: str    = 股票名称 / 空（星球）
title: str         = 标题
content: str       = 全文
summary: str       = 摘要
url: str           = 原文链接
published_at: str  = ISO 时间戳
fetched_at: str    = ISO 时间戳
authors: list[str] = 作者
tags: list[str]    = 标签
metadata: dict     = 源特定扩展字段
group_name: str    = (zsxq 专用) 星球名称
mentions_stocks: list[str] = (zsxq 专用) 提及的股票
```

### 存储结构

```
data/
├── <stock_code>/
│   ├── cninfo/           → 按年-月分目录
│   ├── eastmoney_report/
│   ├── eastmoney_news/
│   └── index.json        → 所有条目摘要索引
├── zsxq/
│   └── <group_id>/
│       └── index.json
└── errors.log
```

### 去重

对 `sha256(source + title + published_at)[:16]` 取 id，写入前查 index 跳过已有条目。

## CLI 接口

```
ff search <stock_code>  [--sources] [--days]
ff watch  add|list|update <codes...>
ff zsxq   list|fetch [--group]
ff config [--cookie-zsxq]
```

## 容错

- fetcher 独立运行，单源失败不阻塞其他
- 网络错误自动重试 2 次（指数退避 1s → 3s）
- 失败记录到 `errors.log`，不在终端抛异常
- 所有写操作幂等，重复执行不产生重复数据

## 非目标

- 不抓取股价、PE/PB 等数值指标
- 不提供 Web 界面
- 不做自动登录（只持 Cookie）
- 不处理知识星球付费墙检测（用户需自己续费）
