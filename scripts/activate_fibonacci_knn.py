#!/usr/bin/env python3
"""Activate the faithful SIA v0.1 adaptive Fibonacci-KNN related engine.

SIA separates semantic similarity from Fibonacci recall mechanics:

1. Semantic similarity uses deterministic symbolic signals.
2. Adaptive neighbourhood size uses:
   K(N) = min(N, max_k, max(3, FibFloor(sqrt(N))))
3. The K nearest candidates receive normalized golden-ratio rank weights.
4. recall_score = semantic_similarity * normalized rank weight.

This remains a project-specific symbolic implementation: no paid API, no
embeddings, no vector database, and no claim that "Fibonacci-KNN" is a
standard textbook algorithm.
"""
from pathlib import Path
import re

GENERATOR = Path("generator/generate_graph.py")
ADAPTER = Path("assets/sia-graph-adapter-v0.1.js")

ENGINE = "sia-fibonacci-knn-v0.1"

CONSTANTS = '''\nFIBONACCI_KNN_ENGINE = "sia-fibonacci-knn-v0.1"\nSEMANTIC_SIMILARITY_WEIGHTS = {\n    "entity": 34.0,\n    "silo": 21.0,\n    "title": 13.0,\n    "label": 8.0,\n    "content_type": 5.0,\n    "facet": 3.0,\n}\nSEMANTIC_SIMILARITY_TOTAL = sum(SEMANTIC_SIMILARITY_WEIGHTS.values())\n# Backward-compatible alias retained in graph metadata during v0.1.\nFIBONACCI_KNN_WEIGHTS = SEMANTIC_SIMILARITY_WEIGHTS\nFIBONACCI_KNN_TOTAL = SEMANTIC_SIMILARITY_TOTAL\nPHI = (1.0 + math.sqrt(5.0)) / 2.0\nDEFAULT_RELATED_MAX_K = 55\nDEFAULT_RELATED_DISPLAY_LIMIT = 6\n'''

RELATED_BLOCK = r'''def fibonacci_floor(value: float) -> int:
    """Largest Fibonacci number <= value, using 1, 1, 2, 3, 5..."""
    if value < 1:
        return 0
    a, b = 1, 1
    while b <= value:
        a, b = b, a + b
    return a


def adaptive_fibonacci_k(n: int, max_k: int = DEFAULT_RELATED_MAX_K) -> int:
    """Adaptive SIA neighbourhood size for N available candidate memories."""
    n = max(0, int(n))
    if n == 0:
        return 0
    cap = max(1, min(DEFAULT_RELATED_MAX_K, int(max_k)))
    return min(n, cap, max(3, fibonacci_floor(math.sqrt(n))))


def golden_rank_weights(k: int) -> List[float]:
    """Normalized phi decay: w_r = phi^-(r-1) / sum(phi^-(j-1))."""
    k = max(0, int(k))
    if k == 0:
        return []
    raw = [PHI ** (-index) for index in range(k)]
    total = sum(raw)
    return [value / total for value in raw]


def related_score(a: Post, b: Post):
    """Return deterministic symbolic semantic similarity in the range 0..100."""
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
        SEMANTIC_SIMILARITY_WEIGHTS[name] * value
        for name, value in components.items()
    )
    score = (weighted / SEMANTIC_SIMILARITY_TOTAL) * 100.0

    reasons = ["fibonacci_knn", "semantic_similarity"]
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

    # High similarity is not automatically relevance. A known incompatible
    # content type remains a conservative negative signal.
    if a.content_types and b.content_types and not content_similarity:
        score -= 8.0
        reasons.append("different_content_type")

    return round(max(0.0, min(100.0, score)), 3), reasons


def precompute_related(posts, limit=None, min_score=10.0, max_k=DEFAULT_RELATED_MAX_K):
    """Build adaptive Fibonacci-KNN recall lists for every post.

    `limit` remains accepted for old callers, but the v0.1 adaptive engine uses
    `max_k` as the recall cap. Display count is a separate browser concern.
    """
    output = {}
    candidate_count = max(0, len(posts) - 1)
    adaptive_k = adaptive_fibonacci_k(candidate_count, max_k=max_k)

    for post in posts:
        ranked = []
        for candidate in posts:
            score, reasons = related_score(post, candidate)
            if score < 0:
                continue
            ranked.append({
                "id": candidate.id,
                "score": score,
                "similarity": score,
                "distance": round(1.0 - (score / 100.0), 6),
                "reasons": reasons,
            })

        ranked.sort(key=lambda x: (x["distance"], x["id"]))
        nearest = ranked[:adaptive_k]
        weights = golden_rank_weights(len(nearest))
        neighbors = []

        for rank, (item, rank_weight) in enumerate(zip(nearest, weights), 1):
            item["rank"] = rank
            item["rank_weight"] = round(rank_weight, 8)
            item["recall_score"] = round(item["similarity"] * rank_weight, 6)
            item["reasons"] = item["reasons"] + [
                "adaptive_fibonacci_k",
                "golden_ratio_rank",
            ]
            # Relevance admission happens after recall. This preserves K(N)
            # while refusing very weak related links in the published graph.
            if item["similarity"] >= min_score:
                neighbors.append(item)

        output[post.id] = neighbors

    return output
'''

FALLBACK_BLOCK = r'''  var PHI = (1 + Math.sqrt(5)) / 2;

  function fibonacciFloor(value) {
    if (value < 1) return 0;
    var a = 1, b = 1;
    while (b <= value) {
      var next = a + b;
      a = b;
      b = next;
    }
    return a;
  }

  function adaptiveFibonacciK(n, maxK) {
    n = Math.max(0, Number(n) || 0);
    if (!n) return 0;
    maxK = Math.max(1, Math.min(55, Number(maxK) || 55));
    return Math.min(n, maxK, Math.max(3, fibonacciFloor(Math.sqrt(n))));
  }

  function goldenRankWeights(k) {
    k = Math.max(0, Number(k) || 0);
    if (!k) return [];
    var raw = [], total = 0;
    for (var i = 0; i < k; i++) {
      var value = Math.pow(PHI, -i);
      raw.push(value);
      total += value;
    }
    return raw.map(function (value) { return value / total; });
  }

  function fallbackScore(post, ctx) {
    // Fibonacci-KNN Lite: fallback has title/labels but no precomputed entities.
    var reasons = ['fibonacci_knn_fallback', 'semantic_similarity'];
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

FALLBACK_RELATED_BLOCK = r'''  async function fallbackRelated() {
    var ctx = { title: currentTitle(), labels: currentLabels() };
    var batches = [];

    if (ctx.labels.length) {
      for (var i = 0; i < Math.min(4, ctx.labels.length); i++) {
        try {
          batches.push(await fetchLabelPosts(ctx.labels[i]));
        } catch (e) {}
      }
    }

    if (!batches.length) {
      try {
        var res = await fetch(
          '/feeds/posts/default?alt=json&max-results=' + cfg.fallbackMaxResults,
          { credentials: 'same-origin' }
        );
        if (res.ok) {
          var data = await res.json();
          var entries = data && data.feed && Array.isArray(data.feed.entry) ? data.feed.entry : [];
          batches.push(entries.map(entryToPost));
        }
      } catch (e) {}
    }

    var byUrl = {};
    batches.flat().forEach(function (p) {
      var key = cleanUrl(p.url);
      if (key && key !== cleanUrl(window.location.href) && !byUrl[key]) byUrl[key] = p;
    });

    var ranked = Object.keys(byUrl).map(function (key) {
      var p = byUrl[key];
      var s = fallbackScore(p, ctx);
      return {
        title: p.title,
        url: p.url,
        score: s.score,
        similarity: s.score,
        distance: Math.round((1 - (s.score / 100)) * 1000000) / 1000000,
        reasons: s.reasons
      };
    }).sort(function (a, b) {
      return b.similarity - a.similarity || a.title.localeCompare(b.title);
    });

    var k = adaptiveFibonacciK(ranked.length, 55);
    var nearest = ranked.slice(0, k);
    var weights = goldenRankWeights(nearest.length);

    nearest.forEach(function (item, index) {
      item.rank = index + 1;
      item.rank_weight = Math.round(weights[index] * 100000000) / 100000000;
      item.recall_score = Math.round(item.similarity * weights[index] * 1000000) / 1000000;
      item.reasons = item.reasons.concat(['adaptive_fibonacci_k', 'golden_ratio_rank']);
    });

    return nearest.filter(function (item) {
      return item.similarity >= cfg.minFallbackScore;
    }).slice(0, cfg.maxRelated);
  }
'''


def patch_generator(text: str) -> str:
    # Replace every previous Fibonacci constants block with the separated
    # semantic-similarity + adaptive recall constants.
    constants_re = re.compile(
        r'\nFIBONACCI_KNN_ENGINE = .*?FIBONACCI_KNN_TOTAL = .*?\n',
        re.S,
    )
    if constants_re.search(text):
        text = constants_re.sub(CONSTANTS, text, count=1)
    elif "SEMANTIC_SIMILARITY_WEIGHTS" not in text:
        needle = "DEFAULT_PAGE_SIZE = 150\n"
        if needle not in text:
            raise RuntimeError("Generator constants anchor not found")
        text = text.replace(needle, needle + CONSTANTS, 1)

    score_re = re.compile(
        r"def (?:fibonacci_floor|related_score)\(.*?(?=\ndef add_edge\()",
        re.S,
    )
    if not score_re.search(text):
        raise RuntimeError("Generator related engine block not found")
    text = score_re.sub(RELATED_BLOCK.rstrip() + "\n\n", text, count=1)

    # CLI: preserve old flags and add explicit adaptive controls.
    if 'p.add_argument("--related-max-k"' not in text:
        text = text.replace(
            '    p.add_argument("--related-min-score", type=float)\n',
            '    p.add_argument("--related-min-score", type=float)\n'
            '    p.add_argument("--related-max-k", type=int)\n'
            '    p.add_argument("--related-min-similarity", type=float)\n',
            1,
        )

    old_config = '''    related_limit = args.related_limit or int(config.get("related_limit", 8))
    related_min_score = (
        args.related_min_score
        if args.related_min_score is not None
        else float(config.get("related_min_score", 10))
    )
'''
    new_config = '''    # v0.1 migration: display count is separate from adaptive recall depth.
    related_display_limit = int(config.get("related_display_limit", 6))
    related_max_k = (
        args.related_max_k
        if args.related_max_k is not None
        else int(config.get("related_max_k", DEFAULT_RELATED_MAX_K))
    )
    related_max_k = max(1, min(DEFAULT_RELATED_MAX_K, related_max_k))
    related_min_similarity = (
        args.related_min_similarity
        if args.related_min_similarity is not None
        else (
            args.related_min_score
            if args.related_min_score is not None
            else float(config.get("related_min_similarity", config.get("related_min_score", 10)))
        )
    )
    # Legacy related_limit remains readable for old configs but no longer caps
    # adaptive recall. The browser display remains controlled separately.
    legacy_related_limit = int(config.get("related_limit", related_display_limit))
'''
    if old_config in text:
        text = text.replace(old_config, new_config, 1)
    elif "related_max_k = (" not in text:
        raise RuntimeError("Generator related config block not found")

    old_call = '''    related = precompute_related(
        posts,
        limit=max(1, related_limit),
        min_score=related_min_score,
    )
'''
    new_call = '''    related = precompute_related(
        posts,
        min_score=related_min_similarity,
        max_k=related_max_k,
    )
'''
    if old_call in text:
        text = text.replace(old_call, new_call, 1)
    elif "max_k=related_max_k" not in text:
        raise RuntimeError("Generator related call not found")

    # Replace old graph metadata in both empty and populated outputs.
    text = re.sub(
        r'"related_engine": FIBONACCI_KNN_ENGINE,\n\s*"related_k": max\(1, related_limit\),\n\s*"fibonacci_weights": FIBONACCI_KNN_WEIGHTS,?',
        '"related_engine": FIBONACCI_KNN_ENGINE,\n'
        '                "related_k": adaptive_fibonacci_k(0, related_max_k),\n'
        '                "related_max_k": related_max_k,\n'
        '                "related_display_limit": related_display_limit,\n'
        '                "semantic_similarity_weights": SEMANTIC_SIMILARITY_WEIGHTS,\n'
        '                "fibonacci_weights": FIBONACCI_KNN_WEIGHTS,\n'
        '                "fibonacci_knn": {\n'
        '                    "k_rule": "min(N,55,max(3,FibFloor(sqrt(N))))",\n'
        '                    "phi": round(PHI, 12),\n'
        '                    "rank_weighting": "normalized_phi_decay",\n'
        '                    "max_k": related_max_k,\n'
        '                    "display_limit": related_display_limit\n'
        '                },',
        text,
        count=1,
    )

    # Populated metadata has different indentation; normalize explicitly.
    populated_old = '''            "related_engine": FIBONACCI_KNN_ENGINE,
            "related_k": max(1, related_limit),
            "fibonacci_weights": FIBONACCI_KNN_WEIGHTS,
'''
    populated_new = '''            "related_engine": FIBONACCI_KNN_ENGINE,
            "related_k": adaptive_fibonacci_k(max(0, len(posts) - 1), related_max_k),
            "related_max_k": related_max_k,
            "related_display_limit": related_display_limit,
            "semantic_similarity_weights": SEMANTIC_SIMILARITY_WEIGHTS,
            "fibonacci_weights": FIBONACCI_KNN_WEIGHTS,
            "fibonacci_knn": {
                "k_rule": "min(N,55,max(3,FibFloor(sqrt(N))))",
                "phi": round(PHI, 12),
                "rank_weighting": "normalized_phi_decay",
                "max_k": related_max_k,
                "display_limit": related_display_limit,
                "legacy_related_limit": legacy_related_limit,
            },
'''
    if populated_old in text:
        text = text.replace(populated_old, populated_new, 1)
    elif '"semantic_similarity_weights": SEMANTIC_SIMILARITY_WEIGHTS' not in text:
        raise RuntimeError("Generator populated metadata block not found")

    return text


def patch_adapter(text: str) -> str:
    fallback_re = re.compile(
        r"  (?:var PHI = .*?\n\n  )?function fallbackScore\(post, ctx\) \{.*?\n  \}\n\n  async function fetchLabelPosts",
        re.S,
    )
    if not fallback_re.search(text):
        raise RuntimeError("Adapter fallbackScore block not found")
    text = fallback_re.sub(
        FALLBACK_BLOCK.rstrip() + "\n\n  async function fetchLabelPosts",
        text,
        count=1,
    )

    related_re = re.compile(
        r"  async function fallbackRelated\(\) \{.*?\n  \}\n\n  async function boot",
        re.S,
    )
    if not related_re.search(text):
        raise RuntimeError("Adapter fallbackRelated block not found")
    text = related_re.sub(
        FALLBACK_RELATED_BLOCK.rstrip() + "\n\n  async function boot",
        text,
        count=1,
    )

    # Collapse historic duplicate header lines from repeated activations.
    text = re.sub(
        r"(?: \* Related engine: SIA Fibonacci-KNN v0\.1 \(symbolic, deterministic\)\.\n)+",
        " * Related engine: SIA Fibonacci-KNN v0.1 (adaptive symbolic recall).\n",
        text,
        count=1,
    )
    return text


def main():
    generator = patch_generator(GENERATOR.read_text(encoding="utf-8"))
    adapter = patch_adapter(ADAPTER.read_text(encoding="utf-8"))

    compile(generator, str(GENERATOR), "exec")
    for marker in (
        "adaptive_fibonacci_k",
        "golden_rank_weights",
        "semantic_similarity_weights",
    ):
        if marker not in generator:
            raise RuntimeError(f"Adaptive Fibonacci-KNN marker missing: {marker}")
    for marker in ("adaptiveFibonacciK", "goldenRankWeights", "fibonacci_knn_fallback"):
        if marker not in adapter:
            raise RuntimeError(f"Adaptive browser fallback marker missing: {marker}")

    GENERATOR.write_text(generator, encoding="utf-8")
    ADAPTER.write_text(adapter, encoding="utf-8")
    print("SIA v0.1 adaptive Fibonacci-KNN recall engine activated")


if __name__ == "__main__":
    main()
