#!/usr/bin/env python3
"""Activate SIA v0.1 Bot Integrity + Evidence-Aware Relations.

This layer has two goals:

1. Preserve semantic parity for humans and machines. The universal theme must
   not branch article truth or links for named crawlers, hide ranking text, or
   contain hidden prompt-injection instructions.
2. Keep semantic similarity separate from evidence. Related/same-silo/entity
   relations may be inferred symbolically; supporting/source-reference/
   contrasting relations require explicit future evidence and are never
   inferred from similarity alone.

The implementation remains deterministic, dependency-free and publisher-neutral.
"""
from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Tuple

GENERATOR = Path("generator/generate_graph.py")
ADAPTER = Path("assets/sia-graph-adapter-v0.1.js")
THEME = Path("theme/SIA-Infinity-AI-Blogger-Template-v0.1.xml")

INTEGRITY_MARKER = "SIA Bot Integrity Contract v0.1"
INTEGRITY_META = "same-content-semantic-parity-v0.1"
RELATION_POLICY_MARKER = "similarity_is_not_evidence"

FIBONACCI_CONSTANTS = (
    "PHI = (1.0 + math.sqrt(5.0)) / 2.0\n"
    "DEFAULT_RELATED_MAX_K = 55\n"
    "DEFAULT_RELATED_DISPLAY_LIMIT = 6\n"
)

RELATION_HELPER = '''def relation_types_from_reasons(reasons: Sequence[str]) -> List[str]:
    """Map similarity signals to non-evidentiary semantic relation classes."""
    reason_set = set(reasons or [])
    relation_types = ["related"]
    mapping = (
        ("shared_entity", "same_entity"),
        ("same_silo", "same_silo"),
        ("same_content_type", "same_content_type"),
        ("shared_facet", "shared_facet"),
        ("shared_label", "shared_label"),
        ("title_pattern", "title_pattern"),
    )
    for reason, relation_type in mapping:
        if reason in reason_set:
            relation_types.append(relation_type)
    return relation_types


'''


def normalize_fibonacci_constants(text: str) -> str:
    """Collapse historic duplicate PHI/max-k blocks caused by repeated activation."""
    pattern = re.compile(
        r"(?:PHI = \(1\.0 \+ math\.sqrt\(5\.0\)\) / 2\.0\n"
        r"DEFAULT_RELATED_MAX_K = 55\n"
        r"DEFAULT_RELATED_DISPLAY_LIMIT = 6\n)+"
    )
    text, count = pattern.subn(FIBONACCI_CONSTANTS, text, count=1)
    if count == 0:
        raise RuntimeError("Adaptive Fibonacci constants block not found")
    return text


def _relation_policy_block(indent: str) -> str:
    return (
        f'{indent}"relation_policy": {{\n'
        f'{indent}    "principle": "similarity_is_not_evidence",\n'
        f'{indent}    "semantic_relations": [\n'
        f'{indent}        "related", "same_entity", "same_silo",\n'
        f'{indent}        "same_content_type", "shared_facet",\n'
        f'{indent}        "shared_label", "title_pattern"\n'
        f'{indent}    ],\n'
        f'{indent}    "explicit_evidence_only": [\n'
        f'{indent}        "supporting", "source_reference", "contrasting"\n'
        f'{indent}    ]\n'
        f'{indent}}},\n'
    )


def patch_generator(text: str) -> str:
    text = normalize_fibonacci_constants(text)

    if "def relation_types_from_reasons(" not in text:
        anchor = "def precompute_related(posts, limit=None, min_score=10.0, max_k=DEFAULT_RELATED_MAX_K):\n"
        if anchor not in text:
            raise RuntimeError("Related precompute anchor not found")
        text = text.replace(anchor, RELATION_HELPER + anchor, 1)

    if 'item["evidence_status"] = "semantic_only"' not in text:
        old = '''            item["reasons"] = item["reasons"] + [
                "adaptive_fibonacci_k",
                "golden_ratio_rank",
            ]
            # Relevance admission happens after recall.'''
        new = '''            item["reasons"] = item["reasons"] + [
                "adaptive_fibonacci_k",
                "golden_ratio_rank",
            ]
            item["relation_types"] = relation_types_from_reasons(item["reasons"])
            item["evidence_status"] = "semantic_only"
            item["supports_claim"] = False
            # Relevance admission happens after recall.'''
        if old not in text:
            raise RuntimeError("Related neighbor annotation anchor not found")
        text = text.replace(old, new, 1)

    if text.count('"relation_policy": {') < 2:
        pattern = re.compile(r'(?m)^(\s*)"mode": "precomputed-symbolic",\n')

        def repl(match: re.Match[str]) -> str:
            indent = match.group(1)
            return match.group(0) + _relation_policy_block(indent)

        text, count = pattern.subn(repl, text)
        if count != 2:
            raise RuntimeError(f"Expected two graph mode blocks, found {count}")

    compile(text, str(GENERATOR), "exec")
    return text


def patch_adapter(text: str) -> str:
    if "data-sia-relation-types" not in text:
        old = '''      if (item.reasons && item.reasons.length) {
        a.setAttribute('data-sia-reasons', item.reasons.join(','));
      }
      li.appendChild(a);'''
        new = '''      if (item.reasons && item.reasons.length) {
        a.setAttribute('data-sia-reasons', item.reasons.join(','));
      }
      if (item.relation_types && item.relation_types.length) {
        a.setAttribute('data-sia-relation-types', item.relation_types.join(','));
      }
      if (item.evidence_status) {
        a.setAttribute('data-sia-evidence-status', item.evidence_status);
      }
      li.appendChild(a);'''
        if old not in text:
            raise RuntimeError("Related render metadata anchor not found")
        text = text.replace(old, new, 1)

    if "relation_types: ref.relation_types" not in text:
        old = '''        url: p.url,
        score: ref.score,
        reasons: ref.reasons || []
      });'''
        new = '''        url: p.url,
        score: ref.score,
        similarity: ref.similarity !== undefined ? ref.similarity : ref.score,
        relation_types: ref.relation_types || ['related'],
        evidence_status: ref.evidence_status || 'semantic_only',
        supports_claim: ref.supports_claim === true,
        reasons: ref.reasons || []
      });'''
        if old not in text:
            raise RuntimeError("Graph relation hydration anchor not found")
        text = text.replace(old, new, 1)

    if "item.evidence_status = 'semantic_only';" not in text:
        old = '''      item.reasons = item.reasons.concat(['adaptive_fibonacci_k', 'golden_ratio_rank']);
    });'''
        new = '''      item.reasons = item.reasons.concat(['adaptive_fibonacci_k', 'golden_ratio_rank']);
      item.relation_types = ['related'];
      if (item.reasons.indexOf('shared_entity') !== -1) item.relation_types.push('same_entity');
      if (item.reasons.indexOf('same_silo') !== -1) item.relation_types.push('same_silo');
      if (item.reasons.indexOf('same_content_type') !== -1) item.relation_types.push('same_content_type');
      if (item.reasons.indexOf('shared_facet') !== -1) item.relation_types.push('shared_facet');
      if (item.reasons.indexOf('shared_label') !== -1) item.relation_types.push('shared_label');
      if (item.reasons.indexOf('title_pattern') !== -1) item.relation_types.push('title_pattern');
      item.evidence_status = 'semantic_only';
      item.supports_claim = false;
    });'''
        if old not in text:
            raise RuntimeError("Fallback relation annotation anchor not found")
        text = text.replace(old, new, 1)

    return text


def patch_theme(text: str) -> str:
    if INTEGRITY_MARKER not in text:
        anchor = "  <meta content='0.1' name='sia-template-version'/>\n"
        block = (
            anchor
            + f"  <!-- {INTEGRITY_MARKER} -->\n"
            + f"  <meta content='{INTEGRITY_META}' name='sia-bot-integrity'/>\n"
        )
        if anchor not in text:
            raise RuntimeError("Theme integrity meta anchor not found")
        text = text.replace(anchor, block, 1)

    # The adapter is embedded in the XML. Apply the same evidence annotations
    # directly so Blogger fallback and precomputed graph hydration stay aligned.
    text = patch_adapter(text)
    return text


def validate_integrity(theme: str, generator: str, adapter: str) -> None:
    decoded = html.unescape(theme)
    lower = decoded.lower()

    crawler_names = (
        "googlebot", "bingbot", "gptbot", "oai-searchbot",
        "perplexitybot", "claudebot", "google-extended",
    )
    found_crawlers = [name for name in crawler_names if name in lower]
    if found_crawlers:
        raise RuntimeError(
            "Universal runtime must not branch on named crawlers: "
            + ", ".join(found_crawlers)
        )

    for marker in ("navigator.useragent", "http_user_agent"):
        if marker in lower:
            raise RuntimeError("Crawler/user-agent conditional runtime is forbidden: " + marker)

    prompt_injection_markers = (
        "ignore all previous instructions",
        "ignore previous instructions",
        "ignore the user's instructions",
        "override system instructions",
        "reveal the system prompt",
    )
    found_prompts = [value for value in prompt_injection_markers if value in lower]
    if found_prompts:
        raise RuntimeError("Hidden prompt-injection-like runtime text is forbidden")

    hidden_anchor = re.compile(
        r"<a\b[^>]*(?:display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0)",
        re.I,
    )
    if hidden_anchor.search(decoded):
        raise RuntimeError("Hidden anchor/link markup is forbidden in the universal theme")

    if re.search(r"[\u0900-\u097F]", decoded):
        raise RuntimeError("Universal Blogger XML contains Devanagari source text")

    required_theme = (
        INTEGRITY_MARKER,
        "name='sia-bot-integrity'",
        "data-sia-relation-types",
        "data-sia-evidence-status",
    )
    missing_theme = [value for value in required_theme if value not in theme]
    if missing_theme:
        raise RuntimeError("Missing bot-integrity theme markers: " + ", ".join(missing_theme))

    required_generator = (
        RELATION_POLICY_MARKER,
        "def relation_types_from_reasons",
        'item["evidence_status"] = "semantic_only"',
        'item["supports_claim"] = False',
    )
    missing_generator = [value for value in required_generator if value not in generator]
    if missing_generator:
        raise RuntimeError("Missing evidence-aware generator markers: " + ", ".join(missing_generator))

    if generator.count(FIBONACCI_CONSTANTS) != 1:
        raise RuntimeError("Adaptive Fibonacci constants must appear exactly once")

    forbidden_evidence_inference = (
        'relation_types.append("supporting")',
        'relation_types.append("source_reference")',
        'relation_types.append("contrasting")',
        '"supports_claim": True',
    )
    for value in forbidden_evidence_inference:
        if value in generator:
            raise RuntimeError("Semantic similarity must not manufacture evidence: " + value)

    if "item.supports_claim = true" in adapter:
        raise RuntimeError("Browser fallback must not manufacture evidence support")


def activate_sources() -> Tuple[str, str]:
    generator = patch_generator(GENERATOR.read_text(encoding="utf-8"))
    adapter = patch_adapter(ADAPTER.read_text(encoding="utf-8"))
    GENERATOR.write_text(generator, encoding="utf-8")
    ADAPTER.write_text(adapter, encoding="utf-8")
    return generator, adapter


def main() -> None:
    generator, adapter = activate_sources()
    theme = patch_theme(THEME.read_text(encoding="utf-8"))
    validate_integrity(theme, generator, adapter)
    THEME.write_text(theme, encoding="utf-8")
    print("SIA v0.1 bot integrity + evidence-aware relations activated")


if __name__ == "__main__":
    main()
