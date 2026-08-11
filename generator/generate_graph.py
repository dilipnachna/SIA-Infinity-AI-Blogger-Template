#!/usr/bin/env python3
"""
SIA-Infinity Precomputed Graph Generator
========================================
Builds a static symbolic intelligence graph from a Blogger/Blogspot JSON feed.

No paid API.
No embeddings.
No vector database.
No third-party Python dependency.

Usage:
    python generator/generate_graph.py --config sia.config.json

Direct:
    python generator/generate_graph.py \
      --blog-url "https://example.blogspot.com" \
      --output public/sia-graph.json
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import html
import json
import math
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

VERSION = "0.1.0"
USER_AGENT = f"SIA-Infinity-Graph-Generator/{VERSION}"
DEFAULT_PAGE_SIZE = 150

FIBONACCI_KNN_ENGINE = "sia-fibonacci-knn-v0.1"
SEMANTIC_SIMILARITY_WEIGHTS = {
    "entity": 34.0,
    "silo": 21.0,
    "title": 13.0,
    "label": 8.0,
    "content_type": 5.0,
    "facet": 3.0,
}
SEMANTIC_SIMILARITY_TOTAL = sum(SEMANTIC_SIMILARITY_WEIGHTS.values())
# Backward-compatible alias retained in graph metadata during v0.1.
FIBONACCI_KNN_WEIGHTS = SEMANTIC_SIMILARITY_WEIGHTS
FIBONACCI_KNN_TOTAL = SEMANTIC_SIMILARITY_TOTAL
PHI = (1.0 + math.sqrt(5.0)) / 2.0
DEFAULT_RELATED_MAX_K = 55
DEFAULT_RELATED_DISPLAY_LIMIT = 6
PHI = (1.0 + math.sqrt(5.0)) / 2.0
DEFAULT_RELATED_MAX_K = 55
DEFAULT_RELATED_DISPLAY_LIMIT = 6
PHI = (1.0 + math.sqrt(5.0)) / 2.0
DEFAULT_RELATED_MAX_K = 55
DEFAULT_RELATED_DISPLAY_LIMIT = 6
PHI = (1.0 + math.sqrt(5.0)) / 2.0
DEFAULT_RELATED_MAX_K = 55
DEFAULT_RELATED_DISPLAY_LIMIT = 6
PHI = (1.0 + math.sqrt(5.0)) / 2.0
DEFAULT_RELATED_MAX_K = 55
DEFAULT_RELATED_DISPLAY_LIMIT = 6
PHI = (1.0 + math.sqrt(5.0)) / 2.0
DEFAULT_RELATED_MAX_K = 55
DEFAULT_RELATED_DISPLAY_LIMIT = 6
PHI = (1.0 + math.sqrt(5.0)) / 2.0
DEFAULT_RELATED_MAX_K = 55
DEFAULT_RELATED_DISPLAY_LIMIT = 6
PHI = (1.0 + math.sqrt(5.0)) / 2.0
DEFAULT_RELATED_MAX_K = 55
DEFAULT_RELATED_DISPLAY_LIMIT = 6
PHI = (1.0 + math.sqrt(5.0)) / 2.0
DEFAULT_RELATED_MAX_K = 55
DEFAULT_RELATED_DISPLAY_LIMIT = 6
PHI = (1.0 + math.sqrt(5.0)) / 2.0
DEFAULT_RELATED_MAX_K = 55
DEFAULT_RELATED_DISPLAY_LIMIT = 6
PHI = (1.0 + math.sqrt(5.0)) / 2.0
DEFAULT_RELATED_MAX_K = 55
DEFAULT_RELATED_DISPLAY_LIMIT = 6
PHI = (1.0 + math.sqrt(5.0)) / 2.0
DEFAULT_RELATED_MAX_K = 55
DEFAULT_RELATED_DISPLAY_LIMIT = 6
PHI = (1.0 + math.sqrt(5.0)) / 2.0
DEFAULT_RELATED_MAX_K = 55
DEFAULT_RELATED_DISPLAY_LIMIT = 6

CONTENT_TYPE_ALIASES = {
    "poems": {
        "poem", "poems", "poetry", "kavita", "कविता", "कविताएँ",
        "कवितायें", "काव्य",
    },
    "stories": {
        "story", "stories", "kahani", "कहानी", "कहानियाँ", "कहानियां", "कथा",
    },
    "quotes": {
        "quote", "quotes", "quotation", "sayings", "suvichar", "thoughts",
        "सुविचार", "उद्धरण", "विचार", "अनमोल वचन", "anmol vachan",
    },
    "dialogues": {
        "dialogue", "dialogues", "dialog", "dialogs", "संवाद", "डायलॉग", "डायलॉग्स",
    },
    "lyrics": {
        "lyrics", "lyric", "song lyrics", "गीत", "गाने के बोल", "गाना",
    },
    "recipes": {
        "recipe", "recipes", "रेसिपी", "व्यंजन", "खाना बनाने की विधि",
    },
    "tutorials": {
        "tutorial", "tutorials", "how to", "guide", "guides", "कैसे करें", "मार्गदर्शिका",
    },
    "news": {
        "news", "समाचार", "खबर", "ख़बर", "खबरें", "ख़बरें",
    },
}

FACET_ALIASES = {
    "hindi": {"hindi", "हिंदी", "हिन्दी"},
    "english": {"english", "अंग्रेजी", "अंग्रेज़ी"},
    "rajasthani": {"rajasthani", "राजस्थानी"},
    "marwadi": {"marwadi", "marwari", "मारवाड़ी", "मारवाड़ी"},
    "bollywood": {"bollywood", "बॉलीवुड"},
    "technology": {"technology", "tech", "तकनीक", "टेक्नोलॉजी"},
}

STOPWORDS = {
    "a","an","the","and","or","but","of","in","on","for","to","from","with","by",
    "at","as","is","are","was","were","be","been","being","this","that","these",
    "those","it","its","your","you","we","our","best","top","new","latest","full",
    "complete","famous","most","all","about","how","what","why","when","where",
    "का","की","के","और","या","में","पर","से","को","है","हैं","था","थे","थी",
    "यह","ये","वह","वे","एक","इस","उस","अपने","अपना","अपनी","सबसे","प्रमुख",
    "प्रसिद्ध","बेहतरीन","पूरी","पूरा","नया","नई","नयी","लिए","द्वारा","एवं",
    "hindi",
}

TOKEN_RE = re.compile(r"[A-Za-z0-9\u0900-\u097F]+(?:['’\-][A-Za-z0-9\u0900-\u097F]+)*")
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


@dataclass
class Post:
    id: str
    title: str
    url: str
    labels: List[str]
    published: str
    updated: str
    tokens: List[str]
    title_tokens: List[str]
    content_types: List[str]
    facets: List[str]
    entities: List[str]
    silo: str


def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def normalize_text(value: str) -> str:
    value = html.unescape(value or "")
    value = unicodedata.normalize("NFKC", value)
    value = value.replace("–", "-").replace("—", "-")
    return SPACE_RE.sub(" ", value).strip().lower()


def strip_html(value: str) -> str:
    return SPACE_RE.sub(" ", html.unescape(TAG_RE.sub(" ", value or ""))).strip()


def tokenize(value: str) -> List[str]:
    out = []
    for token in TOKEN_RE.findall(normalize_text(value)):
        token = token.strip("-'’")
        if len(token) < 2 or token in STOPWORDS:
            continue
        out.append(token)
    return out


def canonical_phrase(value: str) -> str:
    return " ".join(tokenize(value))


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9\u0900-\u097F]+", "-", canonical_phrase(value)).strip("-")


def make_alias_lookup(groups: Dict[str, Set[str]]) -> Dict[str, str]:
    lookup: Dict[str, str] = {}
    for canonical, aliases in groups.items():
        lookup[canonical_phrase(canonical)] = canonical
        for alias in aliases:
            key = canonical_phrase(alias)
            if key:
                lookup[key] = canonical
    return lookup


def merge_alias_config(content_types, facets, config):
    entity_aliases: Dict[str, str] = {}
    aliases = config.get("aliases", {}) if config else {}

    for canonical, values in aliases.get("content_types", {}).items():
        content_types.setdefault(canonical, set()).update(values)
    for canonical, values in aliases.get("facets", {}).items():
        facets.setdefault(canonical, set()).update(values)
    for alias, canonical in aliases.get("entities", {}).items():
        entity_aliases[canonical_phrase(alias)] = canonical.strip()

    return content_types, facets, entity_aliases


def extract_link(entry: dict, rel: str = "alternate") -> str:
    for link in entry.get("link", []):
        if link.get("rel") == rel:
            return link.get("href", "")
    return ""


def parse_entry(entry: dict) -> dict:
    labels = [
        c.get("term", "").strip()
        for c in entry.get("category", [])
        if c.get("term", "").strip()
    ]
    body = ""
    if "content" in entry:
        body = entry["content"].get("$t", "")
    elif "summary" in entry:
        body = entry["summary"].get("$t", "")

    return {
        "id": entry.get("id", {}).get("$t", ""),
        "title": entry.get("title", {}).get("$t", "").strip(),
        "url": extract_link(entry),
        "labels": labels,
        "published": entry.get("published", {}).get("$t", ""),
        "updated": entry.get("updated", {}).get("$t", ""),
        "text": strip_html(body),
    }


def fetch_json(url: str, timeout: int = 30, retries: int = 3) -> dict:
    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Unable to fetch {url}: {last_error}")


def fetch_posts(blog_url: str, max_posts: int) -> List[dict]:
    base = blog_url.rstrip("/") + "/feeds/posts/default"
    posts: List[dict] = []
    start_index = 1

    while len(posts) < max_posts:
        size = min(DEFAULT_PAGE_SIZE, max_posts - len(posts))
        query = urllib.parse.urlencode({
            "alt": "json",
            "start-index": start_index,
            "max-results": size,
        })
        payload = fetch_json(base + "?" + query)
        entries = payload.get("feed", {}).get("entry", []) or []
        if not entries:
            break

        posts.extend(parse_entry(e) for e in entries)

        if len(entries) < size:
            break
        start_index += len(entries)

    return posts


def detect_groups(text: str, lookup: Dict[str, str]) -> List[str]:
    normalized = " " + canonical_phrase(text) + " "
    hits: Set[str] = set()
    for alias, canonical in lookup.items():
        if alias and f" {alias} " in normalized:
            hits.add(canonical)
    return sorted(hits)


def title_ngrams(title: str, min_n: int = 2, max_n: int = 4) -> Set[str]:
    toks = tokenize(title)
    grams: Set[str] = set()
    for n in range(min_n, max_n + 1):
        for i in range(len(toks) - n + 1):
            gram = " ".join(toks[i:i+n])
            if not any(t in STOPWORDS for t in gram.split()):
                grams.add(gram)
    return grams


def smart_title(value: str) -> str:
    parts = []
    for p in value.split():
        parts.append(p[:1].upper() + p[1:] if re.search(r"[A-Za-z]", p) else p)
    return " ".join(parts)


def discover_entity_candidates(
    raw_posts: Sequence[dict],
    content_lookup: Dict[str, str],
    facet_lookup: Dict[str, str],
    custom_entity_aliases: Dict[str, str],
    min_occurrences: int,
):
    counts = collections.Counter()
    preferred: Dict[str, str] = {}

    def excluded(value: str) -> bool:
        key = canonical_phrase(value)
        return not key or key in content_lookup or key in facet_lookup

    for post in raw_posts:
        for label in post.get("labels", []):
            if excluded(label):
                continue
            key = canonical_phrase(label)
            canonical = custom_entity_aliases.get(key, label.strip())
            ckey = canonical_phrase(canonical)
            if ckey:
                counts[ckey] += 1
                preferred.setdefault(ckey, canonical)

        for gram in title_ngrams(post.get("title", "")):
            if excluded(gram):
                continue
            if gram in custom_entity_aliases:
                canonical = custom_entity_aliases[gram]
                ckey = canonical_phrase(canonical)
                counts[ckey] += 2
                preferred.setdefault(ckey, canonical)
            else:
                counts[gram] += 1
                preferred.setdefault(gram, smart_title(gram))

    return (
        {k: v for k, v in counts.items() if v >= min_occurrences},
        preferred,
    )


def detect_entities(post, candidates, preferred, custom_aliases):
    hay = " " + canonical_phrase(
        post.get("title", "") + " " + " ".join(post.get("labels", []))
    ) + " "
    ranked = []

    for alias, canonical in custom_aliases.items():
        if alias and f" {alias} " in hay:
            ranked.append((999, canonical))

    for key, count in candidates.items():
        if f" {key} " in hay:
            ranked.append((count, preferred.get(key, smart_title(key))))

    seen, out = set(), []
    for _, name in sorted(ranked, key=lambda x: (-x[0], -len(x[1]))):
        key = canonical_phrase(name)
        if key and key not in seen:
            seen.add(key)
            out.append(name)

    return out[:8]


def choose_silo(labels, content_types, facets, content_lookup, facet_lookup):
    # v0.1 contract: the first Blogger label is always the Primary Silo.
    # Content types and facets are semantic supporting signals only.
    if labels:
        return labels[0].strip()
    if content_types:
        return content_types[0]
    if facets:
        return facets[0]
    return "general"


def build_posts(raw_posts, content_lookup, facet_lookup, candidates, preferred, custom_aliases):
    posts = []

    for idx, raw in enumerate(raw_posts, 1):
        title = raw.get("title", "").strip()
        labels = [x.strip() for x in raw.get("labels", []) if x.strip()]
        text = raw.get("text", "")
        semantic_text = " ".join([title, " ".join(labels), text[:3000]])

        content_types = detect_groups(semantic_text, content_lookup)
        facets = detect_groups(" ".join([title, " ".join(labels)]), facet_lookup)
        entities = detect_entities(raw, candidates, preferred, custom_aliases)
        silo = choose_silo(labels, content_types, facets, content_lookup, facet_lookup)

        raw_id = raw.get("id", "")
        pid = raw_id.rsplit("post-", 1)[-1] if "post-" in raw_id else ""
        if not pid:
            pid = slugify(title) or str(idx)

        posts.append(Post(
            id=pid,
            title=title,
            url=raw.get("url", ""),
            labels=labels,
            published=raw.get("published", ""),
            updated=raw.get("updated", ""),
            tokens=tokenize(text),
            title_tokens=tokenize(title),
            content_types=content_types,
            facets=facets,
            entities=entities,
            silo=silo,
        ))

    return posts


def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def fibonacci_floor(value: float) -> int:
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


def add_edge(counter, a, b):
    if not a or not b or a == b:
        return
    x, y = sorted([a, b])
    counter[(x, y)] += 1


def build_graph(posts):
    silo_counts = collections.Counter()
    entity_counts = collections.Counter()
    facet_counts = collections.Counter()
    label_counts = collections.Counter()
    edges = collections.Counter()

    for p in posts:
        silo_counts[p.silo] += 1

        for e in p.entities:
            entity_counts[e] += 1
            add_edge(edges, f"silo:{p.silo}", f"entity:{e}")

        for f in p.facets:
            facet_counts[f] += 1
            add_edge(edges, f"silo:{p.silo}", f"facet:{f}")

        for label in p.labels:
            label_counts[label] += 1
            add_edge(edges, f"silo:{p.silo}", f"label:{label}")

        for i, e1 in enumerate(p.entities):
            for e2 in p.entities[i+1:]:
                add_edge(edges, f"entity:{e1}", f"entity:{e2}")
            for f in p.facets:
                add_edge(edges, f"entity:{e1}", f"facet:{f}")

    return {
        "silos": [
            {"id": slugify(name), "name": name, "posts": count}
            for name, count in silo_counts.most_common()
        ],
        "entities": [
            {"id": slugify(name), "name": name, "posts": count, "type": "candidate"}
            for name, count in entity_counts.most_common()
        ],
        "facets": [
            {"id": slugify(name), "name": name, "posts": count}
            for name, count in facet_counts.most_common()
        ],
        "labels": [
            {"id": slugify(name), "name": name, "posts": count}
            for name, count in label_counts.most_common()
        ],
        "edges": [
            {"a": a, "b": b, "weight": weight}
            for (a, b), weight in sorted(
                edges.items(), key=lambda kv: (-kv[1], kv[0][0], kv[0][1])
            )
            if weight >= 2
        ],
    }


def load_config(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def parse_args():
    p = argparse.ArgumentParser(description="Build sia-graph.json from a Blogger blog.")
    p.add_argument("--config", help="Path to sia.config.json")
    p.add_argument("--blog-url", help="Blogger/Blogspot root URL")
    p.add_argument("--output", help="Output path")
    p.add_argument("--max-posts", type=int)
    p.add_argument("--entity-min-occurrences", type=int)
    p.add_argument("--related-limit", type=int)
    p.add_argument("--related-min-score", type=float)
    p.add_argument("--related-max-k", type=int)
    p.add_argument("--related-min-similarity", type=float)
    p.add_argument("--compact", action="store_true")
    return p.parse_args()


def main():
    args = parse_args()
    config = load_config(args.config) if args.config else {}

    blog_url = (args.blog_url or config.get("blog_url") or "").rstrip("/")
    if not blog_url:
        raise SystemExit("Missing blog URL. Set blog_url in sia.config.json or use --blog-url.")

    output_path = args.output or config.get("output", "public/sia-graph.json")
    max_posts = args.max_posts or int(config.get("max_posts", 1000))
    min_occ = args.entity_min_occurrences or int(config.get("entity_min_occurrences", 2))
    # v0.1 migration: display count is separate from adaptive recall depth.
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

    content_types = {k: set(v) for k, v in CONTENT_TYPE_ALIASES.items()}
    facets = {k: set(v) for k, v in FACET_ALIASES.items()}
    content_types, facets, custom_aliases = merge_alias_config(
        content_types, facets, config
    )

    content_lookup = make_alias_lookup(content_types)
    facet_lookup = make_alias_lookup(facets)

    print(f"[SIA] Fetching: {blog_url}", file=sys.stderr)
    raw_posts = fetch_posts(blog_url, max_posts=max_posts)

    # A brand-new Blogger project may have zero posts. Do not fail the
    # GitHub Pages build; publish a valid empty graph and let future runs
    # populate it automatically after posts are published.
    if not raw_posts:
        empty_output = {
            "sia": {
                "format": "sia-symbolic-graph",
                "version": VERSION,
                "generated_at": utc_now_iso(),
                "blog_url": blog_url,
                "post_count": 0,
                "mode": "precomputed-symbolic",
                "related_engine": FIBONACCI_KNN_ENGINE,
                "related_k": adaptive_fibonacci_k(0, related_max_k),
                "related_max_k": related_max_k,
                "related_display_limit": related_display_limit,
                "semantic_similarity_weights": SEMANTIC_SIMILARITY_WEIGHTS,
                "fibonacci_weights": FIBONACCI_KNN_WEIGHTS,
                "fibonacci_knn": {
                    "k_rule": "min(N,55,max(3,FibFloor(sqrt(N))))",
                    "phi": round(PHI, 12),
                    "rank_weighting": "normalized_phi_decay",
                    "max_k": related_max_k,
                    "display_limit": related_display_limit
                },
            },
            "graph": {
                "silos": [],
                "entities": [],
                "facets": [],
                "labels": [],
                "edges": []
            },
            "posts": {}
        }
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        compact = bool(args.compact or config.get("compact", False))
        out.write_text(
            json.dumps(
                empty_output,
                ensure_ascii=False,
                separators=(",", ":") if compact else None,
                indent=None if compact else 2
            ),
            encoding="utf-8"
        )
        print(f"[SIA] Built empty graph: {out} (0 posts).", file=sys.stderr)
        return

    candidates, preferred = discover_entity_candidates(
        raw_posts,
        content_lookup,
        facet_lookup,
        custom_aliases,
        min_occurrences=max(2, min_occ),
    )

    posts = build_posts(
        raw_posts,
        content_lookup,
        facet_lookup,
        candidates,
        preferred,
        custom_aliases,
    )

    related = precompute_related(
        posts,
        min_score=related_min_similarity,
        max_k=related_max_k,
    )

    graph = build_graph(posts)

    post_map = {}
    for p in posts:
        post_map[p.id] = {
            "title": p.title,
            "url": p.url,
            "labels": p.labels,
            "published": p.published,
            "updated": p.updated,
            "silo": p.silo,
            "content_types": p.content_types,
            "facets": p.facets,
            "entities": p.entities,
            "related": related.get(p.id, []),
        }

    output = {
        "sia": {
            "format": "sia-symbolic-graph",
            "version": VERSION,
            "generated_at": utc_now_iso(),
            "blog_url": blog_url,
            "post_count": len(posts),
            "mode": "precomputed-symbolic",
            "related_engine": FIBONACCI_KNN_ENGINE,
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
        },
        "graph": graph,
        "posts": post_map,
    }

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    compact = bool(args.compact or config.get("compact", False))
    if compact:
        out.write_text(
            json.dumps(output, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
    else:
        out.write_text(
            json.dumps(output, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print(
        f"[SIA] Built {out}: {len(posts)} posts, "
        f"{len(graph['entities'])} entities, {len(graph['silos'])} silos.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
