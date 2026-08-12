#!/usr/bin/env python3
"""Run the canonical SIA graph generator with Blogger API v3 when available.

Mode is controlled by BLOGGER_API_MODE:

- auto (default): OAuth -> API key -> public feed fallback
- oauth: require OAuth refresh-token credentials
- api-key: require a public API key
- required: require either API credential mode
- feed/off: bypass Blogger API and use the canonical public feed

The canonical graph algorithm is not duplicated here. This wrapper swaps its
content acquisition function and adds conservative API-only body corroboration
for already-established entity candidates. Primary Silo and all SIA v0.1
ranking weights remain owned by the canonical generator.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys

from blogger_api import BloggerAPIClient, BloggerAPIError

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "generator" / "generate_graph.py"
API_BODY_ENTITY_CHAR_LIMIT = 12000
API_BODY_ENTITY_MIN_MENTIONS = 2

spec = importlib.util.spec_from_file_location("sia_graph_generator_api", GENERATOR)
if not spec or not spec.loader:
    raise RuntimeError("Unable to load canonical SIA graph generator")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

ORIGINAL_FETCH_POSTS = module.fetch_posts
ORIGINAL_DETECT_ENTITIES = module.detect_entities
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
        image_posts = sum(1 for post in posts if post.get("image_candidates"))
        print(
            "[SIA] Blogger API v3 source:",
            client.credential_mode,
            "| blog:",
            blog_url,
            "| posts:",
            len(posts),
            "| image-posts:",
            image_posts,
        )
        return posts
    except BloggerAPIError as exc:
        if requested != "auto":
            raise
        print("[SIA] Blogger API v3 unavailable; public feed fallback:", str(exc))
        return ORIGINAL_FETCH_POSTS(blog_url, max_posts)


def _phrase_mentions(haystack: str, phrase: str) -> int:
    if not haystack or not phrase:
        return 0
    return haystack.count(" " + phrase + " ")


def api_aware_detect_entities(post, candidates, preferred, custom_aliases):
    """Corroborate established entities with rich API body text.

    The body is not allowed to invent arbitrary entity candidates. Normal
    candidates must already exist in the canonical title/label corpus and must
    occur at least twice in the API body. Explicit configured aliases may be
    corroborated by one exact body occurrence because the publisher supplied
    that mapping deliberately.
    """
    base = ORIGINAL_DETECT_ENTITIES(post, candidates, preferred, custom_aliases)
    post["_sia_api_body_entities"] = []

    if post.get("source") != "blogger-api-v3" or len(base) >= 8:
        return base

    text = str(post.get("text") or "")[:API_BODY_ENTITY_CHAR_LIMIT]
    body = " " + module.canonical_phrase(text) + " "
    if not body.strip():
        return base

    seen = {module.canonical_phrase(name) for name in base if module.canonical_phrase(name)}
    ranked = []

    for alias, canonical in custom_aliases.items():
        key = module.canonical_phrase(canonical)
        if not alias or not key or key in seen:
            continue
        mentions = _phrase_mentions(body, alias)
        if mentions >= 1:
            ranked.append((1_000_000 + mentions, canonical))

    for key, corpus_count in candidates.items():
        canonical = preferred.get(key, module.smart_title(key))
        canonical_key = module.canonical_phrase(canonical)
        if not key or not canonical_key or canonical_key in seen:
            continue
        mentions = _phrase_mentions(body, key)
        if mentions < API_BODY_ENTITY_MIN_MENTIONS:
            continue
        # Body mentions rank additions, but base title/label entities always
        # remain ahead because they were already emitted by the canonical pass.
        ranked.append((mentions * 1000 + int(corpus_count) * 10 + len(key), canonical))

    additions = []
    for _, name in sorted(ranked, key=lambda item: (-item[0], -len(item[1]), item[1])):
        key = module.canonical_phrase(name)
        if not key or key in seen:
            continue
        seen.add(key)
        additions.append(name)
        if len(base) + len(additions) >= 8:
            break

    post["_sia_api_body_entities"] = additions
    return base + additions


module.fetch_posts = api_aware_fetch_posts
module.detect_entities = api_aware_detect_entities


def main() -> None:
    module.main()


if __name__ == "__main__":
    main()
