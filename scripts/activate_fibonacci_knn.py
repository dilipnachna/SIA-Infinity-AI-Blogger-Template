#!/usr/bin/env python3
"""Activate the SIA v0.1 Fibonacci-weighted symbolic KNN related engine.

This is a deterministic SIA-specific nearest-neighbor method, not a claim of a
standard published algorithm named "Fibonacci-KNN".

Similarity dimensions use descending Fibonacci weights so stronger semantic
signals dominate weaker presentation/facet signals:

- shared named entities: 34
- same Primary Silo: 21
- title-token pattern similarity: 13
- shared Blogger labels: 8
- shared content type: 5
- shared facet: 3

The final pair score is normalized to 0..100. For every post, the graph keeps
only the K nearest candidates above the configured minimum similarity.
"""
from pathlib import Path
import re

GENERATOR = Path("generator/generate_graph.py")
ADAPTER = Path("assets/sia-graph-adapter-v0.1.js")

ENGINE = "fibonacci-knn-v0.1"

CONSTANTS = '''\nFIBONACCI_KNN_ENGINE = "fibonacci-knn-v0.1"\nFIBONACCI_KNN_WEIGHTS = {\n    "entity": 34.0,\n    "silo": 21.0,\n    "title": 13.0,\n    "label": 8.0,\n    "content_type": 5.0,\n    "facet": 3.0,\n}\nFIBONACCI_KNN_TOTAL = sum(FIBONACCI_KNN_WEIGHTS.values())\n'''

RELATED_BLOCK = r'''def related_score(a: Post, b: Post):
    """Return normalized Fibonacci-weighted symbolic similarity (0..100)."""
    if a.id == b.id:
        return -1.0, []

    a_entities = {canonical_phrase(x) for x in a.entities if canonical_phrase(x)}
    b_entities = {canonical_phrase(x) for x in b.entities if canonical_phrase(x)}
    entity_similarity = jaccard(a_entities, b_entities)

    silo_similarity = 1.0 if (
        a.silo != "general"
        and canonical_phrase(a.silo) == canonical_phrase(b.silo)
    ) else 0.0

    title_similarity = jaccard(a.title_tokens, b.title_tokens)

    a_labels = {canonical_phrase(x) for x in a.labels if canonical_phrase(x)}
    b_labels = {canonical_phrase(x) for x in b.labels if canonical_phrase(x)}
    label_similarity = jaccard(a_labels, b_labels)

    content_similarity = jaccard(a.content_types, b.content_types)
    facet_similarity = jaccard(a.facets, b.facets)

    components = {
        "entity": entity_similarity,
        "silo": silo_similarity,
        "title": title_similarity,
        "label": label_similarity,
        "content_type": content_similarity,
        "facet": facet_similarity,
    }

    weighted = sum(
        FIBONACCI_KNN_WEIGHTS[name] * value
        for name, value in components.items()
    )
    score = (weighted / FIBONACCI_KNN_TOTAL) * 100.0

    reasons = ["fibonacci_knn"]
    if entity_similarity:
        reasons.append("shared_entity")
    if silo_similarity:
        reasons.append("same_silo")
    if title_similarity:
        reasons.append("title_pattern")
    if label_similarity:
        reasons.append("shared_label")
    if content_similarity:
        reasons.append("same_content_type")
    if facet_similarity:
        reasons.append("shared_facet")

    # A known but mismatched content type is a useful conservative penalty.
    if a.content_types and b.content_types and not content_similarity:
        score -= 8.0
        reasons.append("different_content_type")

    return round(max(0.0, min(100.0, score)), 3), reasons


def precompute_related(posts, limit, min_score):
    """Build a deterministic KNN list for every post using Fibonacci distance."""
    output = {}
    k = max(1, int(limit))

    for post in posts:
        ranked = []
        for candidate in posts:
            score, reasons = related_score(post, candidate)
            if score >= min_score:
                ranked.append({
                    "id": candidate.id,
                    "score": score,
                    "distance": round(1.0 - (score / 100.0), 6),
                    "reasons": reasons,
                })

        ranked.sort(key=lambda x: (x["distance"], x["id"]))
        neighbors = ranked[:k]
        for rank, item in enumerate(neighbors, 1):
            item["rank"] = rank
        output[post.id] = neighbors

    return output
'''

FALLBACK_BLOCK = r'''  function fallbackScore(post, ctx) {
    // Fibonacci-KNN Lite: the browser fallback has labels/title but no
    // precomputed entity graph, so it preserves the same ordering philosophy.
    var reasons = ['fibonacci_knn_fallback'];
    var candidateLabels = (post.labels || []).map(normalize).filter(Boolean);
    var ctxLabels = ctx.labels.map(normalize).filter(Boolean);

    var primaryMatch = !!(
      ctxLabels.length && candidateLabels.length &&
      ctxLabels[0] === candidateLabels[0]
    );

    var labelUnion = {};
    ctxLabels.forEach(function (x) { labelUnion[x] = true; });
    candidateLabels.forEach(function (x) { labelUnion[x] = true; });
    var sharedLabels = ctxLabels.filter(function (x) {
      return candidateLabels.indexOf(x) !== -1;
    });
    var labelSimilarity = Object.keys(labelUnion).length
      ? sharedLabels.length / Object.keys(labelUnion).length
      : 0;

    var a = tokens(ctx.title);
    var b = tokens(post.title);
    var tokenUnion = {};
    a.forEach(function (x) { tokenUnion[x] = true; });
    b.forEach(function (x) { tokenUnion[x] = true; });
    var bSet = {};
    b.forEach(function (x) { bSet[x] = true; });
    var sharedTitle = a.filter(function (x) { return bSet[x]; });
    var titleSimilarity = Object.keys(tokenUnion).length
      ? sharedTitle.length / Object.keys(tokenUnion).length
      : 0;

    var weighted =
      (primaryMatch ? 21 : 0) +
      (8 * labelSimilarity) +
      (13 * titleSimilarity);
    var score = (weighted / 42) * 100;

    if (primaryMatch) reasons.push('same_silo');
    if (labelSimilarity) reasons.push('shared_label');
    if (titleSimilarity) reasons.push('title_pattern');

    return { score: Math.round(score * 1000) / 1000, reasons: reasons };
  }
'''


def patch_generator(text: str) -> str:
    if "FIBONACCI_KNN_WEIGHTS" not in text:
        needle = "DEFAULT_PAGE_SIZE = 150\n"
        if needle not in text:
            raise RuntimeError("Generator constants anchor not found")
        text = text.replace(needle, needle + CONSTANTS, 1)

    score_re = re.compile(
        r"def related_score\(a: Post, b: Post\):.*?(?=\ndef add_edge\()",
        re.S,
    )
    if not score_re.search(text):
        raise RuntimeError("Generator related engine block not found")
    text = score_re.sub(RELATED_BLOCK.rstrip() + "\n\n", text, count=1)

    # Add engine metadata to both empty and populated graph outputs.
    if '"related_engine": FIBONACCI_KNN_ENGINE' not in text:
        text = text.replace(
            '"mode": "precomputed-symbolic"\n            },',
            '"mode": "precomputed-symbolic",\n                "related_engine": FIBONACCI_KNN_ENGINE,\n                "related_k": max(1, related_limit),\n                "fibonacci_weights": FIBONACCI_KNN_WEIGHTS\n            },',
            1,
        )
        text = text.replace(
            '"mode": "precomputed-symbolic",\n        },',
            '"mode": "precomputed-symbolic",\n            "related_engine": FIBONACCI_KNN_ENGINE,\n            "related_k": max(1, related_limit),\n            "fibonacci_weights": FIBONACCI_KNN_WEIGHTS,\n        },',
            1,
        )

    return text


def patch_adapter(text: str) -> str:
    fallback_re = re.compile(
        r"  function fallbackScore\(post, ctx\) \{.*?\n  \}\n\n  async function fetchLabelPosts",
        re.S,
    )
    if not fallback_re.search(text):
        raise RuntimeError("Adapter fallbackScore block not found")
    text = fallback_re.sub(
        FALLBACK_BLOCK.rstrip() + "\n\n  async function fetchLabelPosts",
        text,
        count=1,
    )

    text = text.replace(
        " * Priority:\n",
        " * Related engine: SIA Fibonacci-KNN v0.1 (symbolic, deterministic).\n * Priority:\n",
        1,
    )
    return text


def main():
    generator = patch_generator(GENERATOR.read_text(encoding="utf-8"))
    adapter = patch_adapter(ADAPTER.read_text(encoding="utf-8"))

    compile(generator, str(GENERATOR), "exec")
    if "fibonacci_knn_fallback" not in adapter:
        raise RuntimeError("Fibonacci-KNN fallback was not installed")

    GENERATOR.write_text(generator, encoding="utf-8")
    ADAPTER.write_text(adapter, encoding="utf-8")
    print("SIA v0.1 Fibonacci-KNN related engine activated")


if __name__ == "__main__":
    main()
