#!/usr/bin/env python3
"""Generate one SIA graph per enabled Blogger site in sia.blogs.json."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.parse import urlparse


def parse_args():
    p = argparse.ArgumentParser(description="Generate SIA graphs for registered Blogger sites.")
    p.add_argument("--registry", default="sia.blogs.json")
    p.add_argument("--base-config", default="sia.config.json")
    return p.parse_args()


def load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def hostname_for(url: str) -> str:
    host = (urlparse(url).hostname or "").strip().lower()
    if not host or "/" in host or "\\" in host or ".." in host:
        raise ValueError(f"Invalid blog URL: {url}")
    return host


def merge_aliases(base: dict, override: dict | None) -> dict:
    aliases = copy.deepcopy(base.get("aliases") or {})
    for group in ("content_types", "facets", "entities"):
        aliases.setdefault(group, {})
        if override and isinstance(override.get(group), dict):
            aliases[group].update(override[group])
    return aliases


def build_one(base_config: dict, item: dict) -> Path:
    url = str(item.get("url") or "").strip().rstrip("/")
    if not url:
        raise ValueError("Registered blog is missing url")

    host = hostname_for(url)
    output = Path("public") / "graphs" / host / "sia-graph.json"

    config = copy.deepcopy(base_config)
    config["blog_url"] = url
    config["output"] = output.as_posix()
    config["aliases"] = merge_aliases(base_config, item.get("aliases"))

    # New adaptive controls plus legacy v0.1 controls for fork compatibility.
    for key in (
        "max_posts",
        "entity_min_occurrences",
        "related_display_limit",
        "related_max_k",
        "related_min_similarity",
        "related_limit",
        "related_min_score",
        "compact",
    ):
        if key in item:
            config[key] = item[key]

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".json",
        delete=False,
    ) as tmp:
        json.dump(config, tmp, ensure_ascii=False, indent=2)
        temp_path = Path(tmp.name)

    try:
        subprocess.run(
            [sys.executable, "generator/generate_graph.py", "--config", str(temp_path)],
            check=True,
        )
    finally:
        temp_path.unlink(missing_ok=True)

    if not output.exists():
        raise RuntimeError(f"Graph was not created: {output}")
    return output


def main():
    args = parse_args()
    registry = load_json(args.registry)
    base_config = load_json(args.base_config)

    blogs = registry.get("blogs") or []
    enabled = [item for item in blogs if item.get("enabled", True)]
    if not enabled:
        raise SystemExit("No enabled blogs in sia.blogs.json")

    outputs = []
    seen = set()
    for item in enabled:
        host = hostname_for(str(item.get("url") or ""))
        if host in seen:
            raise SystemExit(f"Duplicate blog hostname in registry: {host}")
        seen.add(host)
        outputs.append(build_one(base_config, item))

    print(f"[SIA] Generated {len(outputs)} graph(s):")
    for path in outputs:
        print(f"  - {path}")


if __name__ == "__main__":
    main()
