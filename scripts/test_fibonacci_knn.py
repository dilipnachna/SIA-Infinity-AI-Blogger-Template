#!/usr/bin/env python3
"""Small deterministic self-test for SIA Fibonacci-KNN v0.1."""
import importlib.util
from pathlib import Path
import sys

MODULE_PATH = Path("generator/generate_graph.py")
spec = importlib.util.spec_from_file_location("sia_graph_generator", MODULE_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

Post = module.Post
related_score = module.related_score
precompute_related = module.precompute_related


def post(pid, title, labels, entities=None, silo=None, content_types=None, facets=None):
    return Post(
        id=pid,
        title=title,
        url=f"https://example.blogspot.com/2026/01/{pid}.html",
        labels=labels,
        published="2026-01-01T00:00:00Z",
        updated="2026-01-01T00:00:00Z",
        tokens=[],
        title_tokens=module.tokenize(title),
        content_types=content_types or [],
        facets=facets or [],
        entities=entities or [],
        silo=silo or (labels[0] if labels else "general"),
    )


base = post(
    "base",
    "OpenAI Agents Guide",
    ["AI", "Agents"],
    entities=["OpenAI"],
    content_types=["tutorials"],
)
strong = post(
    "strong",
    "OpenAI Agent Tutorial",
    ["AI", "Agents"],
    entities=["OpenAI"],
    content_types=["tutorials"],
)
label_only = post(
    "label",
    "General AI Commentary",
    ["AI", "Opinion"],
    entities=[],
    content_types=["news"],
)
unrelated = post(
    "other",
    "Chocolate Cake Recipe",
    ["Food", "Recipes"],
    entities=[],
    content_types=["recipes"],
)

strong_score, strong_reasons = related_score(base, strong)
label_score, _ = related_score(base, label_only)
unrelated_score, _ = related_score(base, unrelated)

assert strong_score > label_score > unrelated_score
assert "shared_entity" in strong_reasons
assert "same_silo" in strong_reasons

ranked = precompute_related(
    [base, strong, label_only, unrelated],
    limit=2,
    min_score=0.01,
)
assert ranked["base"][0]["id"] == "strong"
assert ranked["base"][0]["rank"] == 1
assert ranked["base"][0]["distance"] < ranked["base"][1]["distance"]

print(
    "Fibonacci-KNN self-test OK:",
    {"strong": strong_score, "label_only": label_score, "unrelated": unrelated_score},
)
