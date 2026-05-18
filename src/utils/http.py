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
