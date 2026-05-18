# 合并 xueqiu-fetcher 设计文档

## 概述

将 xueqiu-fetcher（雪球社区帖子抓取工具）作为新数据源合并到 fundamental-fetcher 中。

## 文件变更

### 新增
- `src/fetchers/xueqiu.py` — XueqiuScraper 类（Playwright + CloakBrowser）
- `src/fetchers/xueqiu_models.py` — pydantic 数据模型

### 修改
- `src/cli.py` — 新增 `ff xueqiu` 子命令组
- `requirements.txt` — 添加 playwright, cloakbrowser, rich, pydantic

## CLI

```
ff xueqiu search <symbol> [--pages] [--sort] [--before] [--limit]
```

## 存储

`~/.fundamental-data/xueqiu/<symbol>/<symbol>_<timestamp>.json`

保持原有 JSON 结构不变（含用户信息、互动数据等）。

## 架构

xueqiu fetcher 使用 Playwright + CloakBrowser 绕过 Cloudflare WAF，在浏览器内执行 fetch() 调用雪球 API。与 fundamental-fetcher 的其他 fetcher（httpx 直连）技术栈不同，保持独立模块。
