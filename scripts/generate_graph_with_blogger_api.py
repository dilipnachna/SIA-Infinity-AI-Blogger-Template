#!/usr/bin/env python3
"""Run the canonical SIA graph generator with Blogger API v3 when available.

Mode is controlled by BLOGGER_API_MODE:

- auto (default): OAuth -> API key -> public feed fallback
- oauth: require OAuth refresh-token credentials
- api-key: require a public API key
- required: require either API credential mode
- feed/off: bypass Blogger API and use the canonical public feed

The canonical graph algorithm is not duplicated here. This wrapper only swaps
its content acquisition function, preserving all SIA v0.1 ranking semantics.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys

from blogger_api import BloggerAPIClient, BloggerAPIError

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "generator" / "generate_graph.py"

spec = importlib.util.spec_from_file_location("sia_graph_generator_api", GENERATOR)
if not spec or not spec.loader:
    raise RuntimeError("Unable to load canonical SIA graph generator")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

ORIGINAL_FETCH_POSTS = module.fetch_posts
VALID_MODES = {"auto", "oauth", "api-key", "required", "feed", "off"}


def configured_mode(client: BloggerAPIClient, requested: str) -> str:
    if requested in {"feed", "off"}:
        return "feed"
    if requested == "oauth":
        if not client.oauth_configured:
            raise BloggerAPIError("BLOGGER_API_MODE=oauth but OAuth credentials are missing")
        return "oauth"
    if requested == "api-key":
        if not client.api_key_configured:
            raise BloggerAPIError("BLOGGER_API_MODE=api-key but BLOGGER_API_KEY is missing")
        return "api-key"
    if requested == "required":
        if not client.configured:
            raise BloggerAPIError("BLOGGER_API_MODE=required but no Blogger API credentials are configured")
        return "oauth" if client.oauth_configured else "api-key"
    if client.oauth_configured:
        return "oauth"
    if client.api_key_configured:
        return "api-key"
    return "feed"


def api_aware_fetch_posts(blog_url: str, max_posts: int):
    requested = os.getenv("BLOGGER_API_MODE", "auto").strip().lower() or "auto"
    if requested not in VALID_MODES:
        raise BloggerAPIError("Unsupported BLOGGER_API_MODE: " + requested)

    client = BloggerAPIClient.from_env()
    selected = configured_mode(client, requested)
    if selected == "feed":
        if requested == "auto":
            print("[SIA] Blogger API v3 credentials not configured; using public Blogger feed.")
        else:
            print("[SIA] Blogger API v3 disabled; using public Blogger feed.")
        return ORIGINAL_FETCH_POSTS(blog_url, max_posts)

    try:
        posts = client.list_posts(blog_url, max_posts)
        print(
            "[SIA] Blogger API v3 source:",
            client.credential_mode,
            "| blog:",
            blog_url,
            "| posts:",
            len(posts),
        )
        return posts
    except BloggerAPIError as exc:
        if requested != "auto":
            raise
        print("[SIA] Blogger API v3 unavailable; public feed fallback:", str(exc))
        return ORIGINAL_FETCH_POSTS(blog_url, max_posts)


module.fetch_posts = api_aware_fetch_posts


def main() -> None:
    module.main()


if __name__ == "__main__":
    main()
