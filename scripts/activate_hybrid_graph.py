#!/usr/bin/env python3
"""Normalize the stable SIA-Infinity Blogger v0.1 hybrid graph runtime.

Design rules:
- first Blogger label = Primary Silo
- adapter is embedded in the Blogger XML (no external JS runtime dependency)
- graph JSON is loaded from Raw GitHub by current blog hostname
- graph failure automatically falls back to Blogger feeds
- a valid graph with zero related posts is still valid precomputed mode
"""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

THEME = Path("theme/SIA-Infinity-AI-Blogger-Template-v0.1.xml")
GENERATOR = Path("generator/generate_graph.py")
ADAPTER = Path("assets/sia-graph-adapter-v0.1.js")

RAW_GRAPH_BASE = (
    "https://raw.githubusercontent.com/dilipnachna/"
    "SIA-Infinity-AI-Blogger-Template/main/public/graphs/"
)
MARKER = "SIA HYBRID GRAPH RUNTIME v0.1"


def patch_generator(text: str) -> str:
    old = '''def choose_silo(labels, content_types, facets, content_lookup, facet_lookup):
    if content_types:
        return content_types[0]

    for label in labels:
        key = canonical_phrase(label)
        if key and key not in content_lookup and key not in facet_lookup:
            return label.strip()

    if labels:
        return labels[0].strip()
    if facets:
        return facets[0]
    return "general"
'''
    new = '''def choose_silo(labels, content_types, facets, content_lookup, facet_lookup):
    # v0.1 contract: the first Blogger label is always the Primary Silo.
    # Content types and facets are semantic supporting signals only.
    if labels:
        return labels[0].strip()
    if content_types:
        return content_types[0]
    if facets:
        return facets[0]
    return "general"
'''
    if old in text:
        return text.replace(old, new, 1)
    if "# v0.1 contract: the first Blogger label is always the Primary Silo." in text:
        return text
    raise RuntimeError("Generator silo function did not match expected v0.1 source")


def patch_adapter(text: str) -> str:
    text = text.replace(
        "        if (!items.length) throw new Error('no-precomputed-related');\n\n",
        ""
    )
    return text


def runtime_block(adapter_source: str) -> str:
    return f'''\n  <b:if cond='data:view.isPost'>
    <!-- {MARKER} -->
    <script>
    //<![CDATA[
    window.SIA_CONFIG = window.SIA_CONFIG || {{}};
    window.SIA_CONFIG.graphUrl = '{RAW_GRAPH_BASE}' + window.location.hostname + '/sia-graph.json';
    window.SIA_CONFIG.maxRelated = 6;
    window.SIA_CONFIG.relatedTarget = 'related-posts-list';
    window.SIA_CONFIG.statusTarget = 'sia-hybrid-status';
    window.SIA_CONFIG.currentLabelsTarget = 'post-labels-data';

    window.addEventListener('sia:hybrid-ready', function(event) {{
      var detail = event && event.detail ? event.detail : {{}};
      var related = Array.isArray(detail.related) ? detail.related : [];
      if (!related.length) return;

      var body = document.getElementById('post-body-content');
      if (!body || body.querySelector('.sia-contextual-link')) return;
      var paragraphs = body.querySelectorAll('p');
      if (paragraphs.length < 2) return;

      var labels = document.getElementById('post-labels-data');
      var primarySilo = labels && labels.textContent
        ? labels.textContent.split(',')[0].trim()
        : 'Related';
      var item = related[0];

      var box = document.createElement('div');
      box.className = 'in-article-link sia-contextual-link';
      box.setAttribute('data-sia-mode', detail.mode || 'unknown');

      var prefix = document.createTextNode('More in ' + primarySilo + ': ');
      var link = document.createElement('a');
      link.href = item.url;
      link.textContent = item.title;
      if (item.score !== undefined) link.setAttribute('data-sia-score', item.score);
      if (item.reasons && item.reasons.length) link.setAttribute('data-sia-reasons', item.reasons.join(','));

      box.appendChild(prefix);
      box.appendChild(link);
      paragraphs[1].insertAdjacentElement('afterend', box);
    }});
    //]]>
    </script>

    <script>
    //<![CDATA[
{adapter_source}
    //]]>
    </script>
  </b:if>
'''


def patch_theme(text: str, adapter_source: str) -> str:
    start = '      let labelsNode = document.getElementById("post-labels-data");'
    end = '      fetch("/feeds/posts/default?alt=json&max-results=5")'
    if start in text and end in text:
        before, rest = text.split(start, 1)
        _legacy, after = rest.split(end, 1)
        replacement = '''      let labelsNode = document.getElementById("post-labels-data");
      let labelsText = labelsNode ? labelsNode.innerText.trim() : "";
      if(labelsText !== "") {
          let primarySilo = labelsText.split(",")[0].trim();
          let relatedHeading = document.getElementById("silo-related-heading");
          if(relatedHeading) relatedHeading.textContent = "More From " + primarySilo;
      }

'''
        text = before + replacement + end + after

    old_heading = "                  <h3 id='silo-related-heading'>More From This Silo</h3>\n                  <ul class='widget-list' id='related-posts-list'>"
    new_heading = "                  <h3 id='silo-related-heading'>More From This Silo</h3>\n                  <div aria-live='polite' id='sia-hybrid-status' style='font-size:11px;color:#64748b;margin:-6px 0 9px;'></div>\n                  <ul class='widget-list' id='related-posts-list'>"
    if old_heading in text:
        text = text.replace(old_heading, new_heading, 1)

    runtime_re = re.compile(
        r"\n  <b:if cond='data:view\.isPost'>\n    <!-- SIA HYBRID GRAPH RUNTIME v0\.1 -->.*?\n  </b:if>\n(?=\n</body>)",
        re.S,
    )
    block = runtime_block(adapter_source)
    if runtime_re.search(text):
        text = runtime_re.sub(lambda _m: block, text, count=1)
    else:
        text = text.replace("</body>", block + "\n</body>", 1)

    text = text.replace(
        "Primary Silo + canonical permalink strategy + English-only source",
        "Primary Silo + hybrid precomputed graph + safe Blogger fallback + canonical permalink strategy + English-only source",
    )
    return text


def main():
    generator = patch_generator(GENERATOR.read_text(encoding="utf-8"))
    adapter = patch_adapter(ADAPTER.read_text(encoding="utf-8"))
    theme = patch_theme(THEME.read_text(encoding="utf-8"), adapter)

    GENERATOR.write_text(generator, encoding="utf-8")
    ADAPTER.write_text(adapter, encoding="utf-8")
    THEME.write_text(theme, encoding="utf-8")

    ET.parse(THEME)
    compile(generator, str(GENERATOR), "exec")
    if "no-precomputed-related" in adapter:
        raise RuntimeError("Adapter still downgrades empty valid graphs")
    print("SIA v0.1 self-contained hybrid graph runtime validated")


if __name__ == "__main__":
    main()
