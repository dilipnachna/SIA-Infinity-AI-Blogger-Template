#!/usr/bin/env python3
"""Offline self-test for SIA Blogger API v3 integration."""
from __future__ import annotations

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from blogger_api import BloggerAPIClient, normalize_api_post


sample = {
    "id": "123",
    "title": "Sample Post",
    "url": "https://example.blogspot.com/2026/08/sample.html",
    "published": "2026-08-01T00:00:00Z",
    "updated": "2026-08-02T00:00:00Z",
    "content": '<p>Hello <b>world</b>.</p><img src="https://blogger.googleusercontent.com/img/a.jpg"/>',
    "images": [{"url": "https://blogger.googleusercontent.com/img/featured.jpg"}],
    "labels": ["AI", "Guide"],
    "author": {
        "id": "42",
        "displayName": "Example Author",
        "url": "https://www.blogger.com/profile/42",
        "image": {"url": "https://blogger.googleusercontent.com/avatar.jpg"},
    },
}

post = normalize_api_post(sample)
assert post["id"] == "123"
assert post["title"] == "Sample Post"
assert post["labels"] == ["AI", "Guide"]
assert post["featured_image"].endswith("featured.jpg")
assert "Hello world" in post["text"]
assert post["author"]["display_name"] == "Example Author"
assert post["author"]["image"].endswith("avatar.jpg")
assert post["source"] == "blogger-api-v3"

# Content-image fallback works when API image metadata is absent.
content_only = dict(sample)
content_only["images"] = []
assert normalize_api_post(content_only)["featured_image"].endswith("a.jpg")

# Credential selection is deterministic and never requires a committed secret.
client = BloggerAPIClient(api_key="public-key")
assert client.configured
assert client.credential_mode == "api-key-public"
assert not client.oauth_configured

oauth_client = BloggerAPIClient(client_id="desktop-client", refresh_token="refresh")
assert oauth_client.configured
assert oauth_client.oauth_configured
assert oauth_client.credential_mode == "oauth-readonly"

# Source must keep credentials out of browser/theme assets.
theme = (ROOT / "theme" / "SIA-Infinity-AI-Blogger-Template-v0.1.xml").read_text(encoding="utf-8")
adapter = (ROOT / "assets" / "sia-graph-adapter-v0.1.js").read_text(encoding="utf-8")
for forbidden in ("BLOGGER_CLIENT_SECRET", "BLOGGER_REFRESH_TOKEN", "oauth2.googleapis.com/token"):
    assert forbidden not in theme
    assert forbidden not in adapter

wrapper = (ROOT / "scripts" / "generate_graph_with_blogger_api.py").read_text(encoding="utf-8")
assert "module.fetch_posts = api_aware_fetch_posts" in wrapper
assert "ORIGINAL_FETCH_POSTS(blog_url, max_posts)" in wrapper
assert "BLOGGER_API_MODE" in wrapper

print("SIA Blogger API v3 self-test OK: read-only API + secure feed fallback")
