#!/usr/bin/env python3
"""Apply the stable v0.1 hybrid graph integration to the Blogger theme.

This patch is intentionally idempotent. It also keeps the v0.1 silo contract:
the first Blogger label is the Primary Silo. Content types/facets remain
supporting semantic signals, not replacements for the primary silo.
"""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

THEME = Path("theme/SIA-Infinity-AI-Blogger-Template-v0.1.xml")
GENERATOR = Path("generator/generate_graph.py")

PAGES_BASE = "https://dilipnachna.github.io/SIA-Infinity-AI-Blogger-Template"
ADAPTER_URL = PAGES_BASE + "/sia-graph-adapter-v0.1.js"
GRAPH_BASE = PAGES_BASE + "/graphs/"


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


def patch_theme(text: str) -> str:
    # Remove the older direct same-label related-post fetch. The hybrid adapter
    # now owns related rendering and provides its own Blogger fallback.
    start = '      let labelsNode = document.getElementById("post-labels-data");'
    end = '      fetch("/feeds/posts/default?alt=json&max-results=5")'
    if start in text and end in text:
        before, rest = text.split(start, 1)
        legacy, after = rest.split(end, 1)
        replacement = '''      let labelsNode = document.getElementById("post-labels-data");
      let labelsText = labelsNode ? labelsNode.innerText.trim() : "";
      if(labelsText !== "") {
          let primarySilo = labelsText.split(",")[0].trim();
          let relatedHeading = document.getElementById("silo-related-heading");
          if(relatedHeading) relatedHeading.textContent = "More From " + primarySilo;
      }

'''
        text = before + replacement + end + after

    # Add a lightweight runtime status target for debugging/verification.
    old_heading = "                  <h3 id='silo-related-heading'>More From This Silo</h3>\n                  <ul class='widget-list' id='related-posts-list'>"
    new_heading = "                  <h3 id='silo-related-heading'>More From This Silo</h3>\n                  <div aria-live='polite' id='sia-hybrid-status' style='font-size:11px;color:#64748b;margin:-6px 0 9px;'></div>\n                  <ul class='widget-list' id='related-posts-list'>"
    if old_heading in text:
        text = text.replace(old_heading, new_heading, 1)

    marker = "SIA HYBRID GRAPH RUNTIME v0.1"
    if marker not in text:
        runtime = f'''\n  <b:if cond='data:view.isPost'>
    <!-- {marker} -->
    <script>
    //<![CDATA[
    window.SIA_CONFIG = window.SIA_CONFIG || {{}};
    window.SIA_CONFIG.graphUrl = '{GRAPH_BASE}' + window.location.hostname + '/sia-graph.json';
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
    <script defer='defer' src='{ADAPTER_URL}'></script>
  </b:if>
'''
        text = text.replace("</body>", runtime + "\n</body>", 1)

    # Keep the source marker factual.
    text = text.replace(
        "Primary Silo + canonical permalink strategy + English-only source",
        "Primary Silo + hybrid precomputed graph + safe Blogger fallback + canonical permalink strategy + English-only source"
    )
    return text


def main():
    theme = patch_theme(THEME.read_text(encoding="utf-8"))
    generator = patch_generator(GENERATOR.read_text(encoding="utf-8"))

    THEME.write_text(theme, encoding="utf-8")
    GENERATOR.write_text(generator, encoding="utf-8")

    ET.parse(THEME)
    compile(generator, str(GENERATOR), "exec")
    print("SIA v0.1 hybrid graph patch applied and validated")


if __name__ == "__main__":
    main()
