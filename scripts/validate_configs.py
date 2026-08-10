#!/usr/bin/env python3
"""Validate SIA v0.1 config and multi-blog registry using Python stdlib only."""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit

CONFIG_PATH = Path("sia.config.json")
BLOGS_PATH = Path("sia.blogs.json")


def fail(message: str) -> None:
    raise SystemExit("SIA config validation failed: " + message)


def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"{path}: {exc}")
    if not isinstance(value, dict):
        fail(f"{path} must contain a JSON object")
    return value


def valid_http_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.hostname)


def require_int(obj: dict, key: str, low: int, high: int) -> None:
    value = obj.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        fail(f"{key} must be an integer from {low} to {high}")


def require_number(obj: dict, key: str, low: float, high: float) -> None:
    value = obj.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= float(value) <= high:
        fail(f"{key} must be a number from {low} to {high}")


def validate_aliases(aliases: object, where: str) -> None:
    if not isinstance(aliases, dict):
        fail(f"{where}.aliases must be an object")
    allowed = {"content_types", "facets", "entities"}
    extra = set(aliases) - allowed
    if extra:
        fail(f"{where}.aliases has unknown keys: {sorted(extra)}")
    for key in allowed:
        if key in aliases and not isinstance(aliases[key], dict):
            fail(f"{where}.aliases.{key} must be an object")


def validate_adaptive_overrides(obj: dict, where: str, require_all: bool = False) -> None:
    fields = {
        "max_posts": (1, 10000, require_int),
        "entity_min_occurrences": (2, 1000, require_int),
        "related_display_limit": (1, 12, require_int),
        "related_max_k": (3, 55, require_int),
        "related_min_similarity": (0, 100, require_number),
    }
    for key, (low, high, checker) in fields.items():
        if require_all and key not in obj:
            fail(f"{where} is missing {key}")
        if key in obj:
            try:
                checker(obj, key, low, high)
            except SystemExit as exc:
                fail(f"{where}.{key}: {str(exc).split(': ', 1)[-1]}")
    if "compact" in obj and not isinstance(obj["compact"], bool):
        fail(f"{where}.compact must be boolean")
    if "aliases" in obj:
        validate_aliases(obj["aliases"], where)


def validate_config(config: dict) -> None:
    allowed = {
        "blog_url", "output", "max_posts", "entity_min_occurrences",
        "related_display_limit", "related_max_k", "related_min_similarity",
        "related_limit", "related_min_score", "compact", "aliases",
    }
    extra = set(config) - allowed
    if extra:
        fail(f"sia.config.json has unknown keys: {sorted(extra)}")
    if not valid_http_url(config.get("blog_url")):
        fail("sia.config.json blog_url must be http/https URL")
    if not isinstance(config.get("output"), str) or not config["output"].strip():
        fail("sia.config.json output must be a non-empty string")
    validate_adaptive_overrides(config, "sia.config.json", require_all=True)
    if "aliases" not in config:
        fail("sia.config.json is missing aliases")
    validate_aliases(config["aliases"], "sia.config.json")


def validate_blogs(registry: dict) -> None:
    if registry.get("version") != "0.1":
        fail("sia.blogs.json version must remain 0.1")
    if set(registry) - {"version", "blogs"}:
        fail("sia.blogs.json contains unknown top-level keys")
    blogs = registry.get("blogs")
    if not isinstance(blogs, list) or not blogs:
        fail("sia.blogs.json blogs must be a non-empty array")

    seen = set()
    allowed = {
        "url", "enabled", "community", "max_posts", "entity_min_occurrences",
        "related_display_limit", "related_max_k", "related_min_similarity",
        "related_limit", "related_min_score", "compact", "aliases",
    }
    for index, item in enumerate(blogs):
        where = f"sia.blogs.json blogs[{index}]"
        if not isinstance(item, dict):
            fail(f"{where} must be an object")
        extra = set(item) - allowed
        if extra:
            fail(f"{where} has unknown keys: {sorted(extra)}")
        if not valid_http_url(item.get("url")):
            fail(f"{where}.url must be http/https URL")
        if not isinstance(item.get("enabled"), bool):
            fail(f"{where}.enabled must be boolean")
        if "community" in item and not isinstance(item["community"], bool):
            fail(f"{where}.community must be boolean")
        host = (urlsplit(item["url"]).hostname or "").lower().rstrip(".")
        if host in seen:
            fail(f"duplicate blog hostname: {host}")
        seen.add(host)
        if item.get("community") is True and not host.endswith(".blogspot.com"):
            fail(f"{where}: community v0.1 currently supports Blogspot hostnames only")
        validate_adaptive_overrides(item, where, require_all=False)


def main() -> None:
    validate_config(load(CONFIG_PATH))
    validate_blogs(load(BLOGS_PATH))
    print("SIA v0.1 config validation OK")


if __name__ == "__main__":
    main()
