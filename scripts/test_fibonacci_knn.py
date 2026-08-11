#!/usr/bin/env python3
"""Deterministic self-test for SIA adaptive Fibonacci-KNN v0.1."""
import importlib.util
import math
from pathlib import Path
import subprocess
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
fibonacci_floor = module.fibonacci_floor
adaptive_fibonacci_k = module.adaptive_fibonacci_k
golden_rank_weights = module.golden_rank_weights
relation_types_from_reasons = module.relation_types_from_reasons


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


# Source-framework K examples and edge cases.
assert adaptive_fibonacci_k(0) == 0
assert adaptive_fibonacci_k(1) == 1
assert adaptive_fibonacci_k(2) == 2
assert adaptive_fibonacci_k(3) == 3
assert adaptive_fibonacci_k(10) == 3
assert adaptive_fibonacci_k(100) == 8
assert adaptive_fibonacci_k(1000) == 21
assert adaptive_fibonacci_k(10000) == 55
assert fibonacci_floor(math.sqrt(100)) == 8
assert fibonacci_floor(math.sqrt(1000)) == 21

# Golden-ratio weights are normalized and strictly decreasing.
weights = golden_rank_weights(8)
assert len(weights) == 8
assert abs(sum(weights) - 1.0) < 1e-12
assert all(weights[i] > weights[i + 1] for i in range(len(weights) - 1))
phi = (1 + math.sqrt(5)) / 2
assert abs((weights[0] / weights[1]) - phi) < 1e-12

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
assert "semantic_similarity" in strong_reasons

semantic_types = relation_types_from_reasons(strong_reasons)
assert "related" in semantic_types
assert "same_entity" in semantic_types
assert "same_silo" in semantic_types
assert "supporting" not in semantic_types
assert "source_reference" not in semantic_types
assert "contrasting" not in semantic_types

ranked = precompute_related(
    [base, strong, label_only, unrelated],
    min_score=0.01,
    max_k=55,
)
base_neighbors = ranked["base"]
assert base_neighbors[0]["id"] == "strong"
assert base_neighbors[0]["rank"] == 1
assert base_neighbors[0]["distance"] < base_neighbors[1]["distance"]
assert base_neighbors[0]["rank_weight"] > base_neighbors[1]["rank_weight"]
assert abs(
    base_neighbors[0]["recall_score"]
    - base_neighbors[0]["similarity"] * base_neighbors[0]["rank_weight"]
) < 1e-4
assert "adaptive_fibonacci_k" in base_neighbors[0]["reasons"]
assert "golden_ratio_rank" in base_neighbors[0]["reasons"]

# Evidence-aware invariant: semantic recall is useful for navigation/retrieval,
# but it must never manufacture factual support.
assert base_neighbors[0]["evidence_status"] == "semantic_only"
assert base_neighbors[0]["supports_claim"] is False
assert "related" in base_neighbors[0]["relation_types"]
assert "same_entity" in base_neighbors[0]["relation_types"]
assert "same_silo" in base_neighbors[0]["relation_types"]
assert not {
    "supporting",
    "source_reference",
    "contrasting",
}.intersection(base_neighbors[0]["relation_types"])

print(
    "Adaptive Fibonacci-KNN + evidence-aware relation self-test OK:",
    {
        "strong": strong_score,
        "label_only": label_score,
        "unrelated": unrelated_score,
        "k100": adaptive_fibonacci_k(100),
        "k1000": adaptive_fibonacci_k(1000),
        "evidence_status": base_neighbors[0]["evidence_status"],
    },
)

subprocess.run([sys.executable, "scripts/test_attention_map.py"], check=True)
