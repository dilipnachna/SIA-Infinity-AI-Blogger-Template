#!/usr/bin/env python3
"""Offline self-test for SIA Blogger API v3 integration."""
from __future__ import annotations

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from blogger_api import BloggerAPIClient, normalize_api_post
from generate_graph_with_blogger_api import api_aware_detect_entities


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
assert post["image_candidates"] == [
    "https://blogger.googleusercontent.com/img/featured.jpg",
    "https://blogger.googleusercontent.com/img/a.jpg",
]
assert "Hello world" in post["text"]
assert post["author"]["display_name"] == "Example Author"
assert post["author"]["image"].endswith("avatar.jpg")
assert post["source"] == "blogger-api-v3"

# Content-image fallback works when API image metadata is absent.
content_only = dict(sample)
content_only["images"] = []
normalized_content_only = normalize_api_post(content_only)
assert normalized_content_only["featured_image"].endswith("a.jpg")
assert normalized_content_only["image_candidates"] == [
    "https://blogger.googleusercontent.com/img/a.jpg"
]

# Duplicate API/body image URLs are preserved only once.
duplicate_image = dict(sample)
duplicate_image["content"] = (
    '<img src="https://blogger.googleusercontent.com/img/featured.jpg"/>'
    '<img src="https://blogger.googleusercontent.com/img/second.jpg"/>'
)
assert normalize_api_post(duplicate_image)["image_candidates"] == [
    "https://blogger.googleusercontent.com/img/featured.jpg",
    "https://blogger.googleusercontent.com/img/second.jpg",
]

# Rich API body text may corroborate an entity that was already established by
# the canonical title/label corpus, but it cannot invent a new candidate.
body_post = {
    "title": "A Neutral Guide",
    "labels": ["Guide"],
    "text": "Alpha Project launched carefully. Alpha Project now has a second milestone.",
    "source": "blogger-api-v3",
}
entities = api_aware_detect_entities(
    body_post,
    {"alpha project": 3},
    {"alpha project": "Alpha Project"},
    {},
)
assert entities == ["Alpha Project"]
assert body_post["_sia_api_body_entities"] == ["Alpha Project"]

single_mention = dict(body_post)
single_mention["text"] = "Alpha Project appears once in this article."
assert api_aware_detect_entities(
    single_mention,
    {"alpha project": 3},
    {"alpha project": "Alpha Project"},
    {},
) == []

feed_post = dict(body_post)
feed_post.pop("source", None)
assert api_aware_detect_entities(
    feed_post,
    {"alpha project": 3},
    {"alpha project": "Alpha Project"},
    {},
) == []

unknown_body_entity = dict(body_post)
unknown_body_entity["text"] = "Gamma Widget appears here. Gamma Widget appears again."
assert api_aware_detect_entities(
    unknown_body_entity,
    {"alpha project": 3},
    {"alpha project": "Alpha Project"},
    {},
) == []

# Explicit publisher aliases are allowed to corroborate with one exact body hit.
alias_post = dict(body_post)
alias_post["text"] = "The Atlas Initiative is discussed in detail."
assert api_aware_detect_entities(
    alias_post,
    {},
    {},
    {"atlas initiative": "Atlas Program"},
) == ["Atlas Program"]

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
assert "module.detect_entities = api_aware_detect_entities" in wrapper
assert "ORIGINAL_FETCH_POSTS(blog_url, max_posts)" in wrapper
assert "BLOGGER_API_MODE" in wrapper
assert "API_BODY_ENTITY_MIN_MENTIONS = 2" in wrapper

print("SIA Blogger API v3 self-test OK: richer images + conservative body entity corroboration")
