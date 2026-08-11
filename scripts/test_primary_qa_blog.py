#!/usr/bin/env python3
"""Validate the configured primary Blogger QA graph.

The primary QA blog should be rich enough to exercise visual related cards,
Primary Silo clustering, image hydration and evidence-aware relations. This is
an offline graph assertion: network fetching remains owned by graph generation.
"""
from pathlib import Path
import json
from urllib.parse import urlparse

CONFIG = Path("sia.config.json")

config = json.loads(CONFIG.read_text(encoding="utf-8"))
blog_url = str(config.get("blog_url", "")).rstrip("/")
output = Path(str(config.get("output", "")))

assert blog_url, "Primary QA blog_url is missing"
assert output.is_file(), f"Primary QA graph is missing: {output}"

graph = json.loads(output.read_text(encoding="utf-8"))
sia = graph.get("sia", {})
posts = graph.get("posts", {})

assert sia.get("blog_url", "").rstrip("/") == blog_url
assert sia.get("post_count") == len(posts)
assert len(posts) >= 10, "Primary QA target needs at least 10 posts"
assert sia.get("related_engine") == "sia-fibonacci-knn-v0.1"
assert sia.get("related_display_limit") == 6

hostname = (urlparse(blog_url).hostname or "").lower()
assert hostname.endswith(".blogspot.com")

image_posts = 0
related_posts = 0
same_silo_relations = 0
semantic_only_relations = 0

for post in posts.values():
    title = str(post.get("title", "")).strip()
    url = str(post.get("url", "")).strip()
    silo = str(post.get("silo", "")).strip()
    assert title
    assert urlparse(url).hostname == hostname
    assert silo

    image = str(post.get("image", "")).strip()
    if image:
        image_posts += 1

    related = post.get("related", []) or []
    if related:
        related_posts += 1
    assert len(related) <= 55

    for relation in related:
        assert relation.get("evidence_status") == "semantic_only"
        assert relation.get("supports_claim") is False
        semantic_only_relations += 1
        if "same_silo" in (relation.get("relation_types") or []):
            same_silo_relations += 1

image_ratio = image_posts / len(posts)
related_ratio = related_posts / len(posts)

# Older Blogger archives may legitimately have posts without a feed-exposed
# thumbnail. The browser runtime has a same-origin recovery layer for those
# cards, so the graph gate protects against a broad extraction regression rather
# than pretending every historical post must expose an image in the feed.
assert image_ratio >= 0.50, f"Primary QA image coverage too low: {image_ratio:.1%}"
assert related_ratio >= 0.50, f"Primary QA related coverage too low: {related_ratio:.1%}"
assert semantic_only_relations > 0, "Primary QA graph has no semantic relations"
assert same_silo_relations > 0, "Primary QA graph is not exercising same-silo relations"

print(
    "Primary Blogger QA graph OK:",
    {
        "blog": hostname,
        "posts": len(posts),
        "image_coverage": round(image_ratio, 3),
        "related_coverage": round(related_ratio, 3),
        "same_silo_relations": same_silo_relations,
    },
)
