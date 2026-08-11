#!/usr/bin/env python3
"""Activate SIA v0.1 visual Related Silo card grid.

The adaptive relation engine remains unchanged. This layer only enriches graph
post records with a presentation image and renders the existing related results
as responsive visual cards. Primary Silo and Fibonacci-KNN remain the source of
related relevance.

Rules:
- preserve the v0.1 public version
- keep universal theme/runtime English-only
- never fabricate an image; use the post body image or Blogger thumbnail
- keep images lazy-loaded and decorative presentation separate from evidence
- keep Cloudflare/GitHub/Blogger fallback behavior aligned
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Tuple

GENERATOR = Path("generator/generate_graph.py")
ADAPTER = Path("assets/sia-graph-adapter-v0.1.js")
THEME = Path("theme/SIA-Infinity-AI-Blogger-Template-v0.1.xml")

MARKER = "SIA Related Silo Card Grid v0.1"

CSS = r'''
    /* SIA Related Silo Card Grid v0.1 */
    .sia-related-section {
      margin-top: 38px;
      padding-top: 0;
      border-top: 0;
    }
    .sia-related-shell { width: 100%; }
    .sia-related-heading {
      display: flex;
      align-items: center;
      gap: 11px;
      margin: 0 0 25px;
      padding: 11px 15px;
      border: 0;
      border-radius: 6px;
      background: #1f2a86;
      color: #fff;
      font-size: 20px;
      font-weight: 900;
      line-height: 1.35;
      letter-spacing: -.15px;
    }
    .sia-related-heading-icon {
      flex: 0 0 auto;
      font-size: 19px;
      line-height: 1;
      color: #fff;
    }
    .sia-related-status {
      min-height: 0;
      margin: -16px 0 14px;
      color: #64748b;
      font-size: 11px;
    }
    .sia-related-grid {
      list-style: none;
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 26px 24px;
      margin: 0;
      padding: 0;
    }
    .sia-related-card {
      min-width: 0;
      margin: 0;
      padding: 0;
      border: 0;
    }
    .sia-related-card-link {
      display: block;
      color: #1e293b;
      text-decoration: none;
    }
    .sia-related-card-link:hover { text-decoration: none; }
    .sia-related-card-media {
      display: block;
      width: 100%;
      aspect-ratio: 16 / 9;
      overflow: hidden;
      border-radius: 6px;
      background: #e2e8f0;
      box-shadow: 0 1px 2px rgba(15, 23, 42, .08);
    }
    .sia-related-card-image {
      display: block;
      width: 100%;
      height: 100%;
      margin: 0;
      border: 0;
      border-radius: 0;
      object-fit: cover;
      object-position: center;
      transition: transform .22s ease;
    }
    .sia-related-card-link:hover .sia-related-card-image { transform: scale(1.025); }
    .sia-related-card-placeholder {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 100%;
      height: 100%;
      padding: 12px;
      color: #64748b;
      background: linear-gradient(135deg, #f1f5f9, #e2e8f0);
      font-size: 13px;
      font-weight: 800;
      text-align: center;
    }
    .sia-related-card-title {
      display: block;
      margin-top: 9px;
      color: #1e293b;
      font-size: 18px;
      font-weight: 850;
      line-height: 1.28;
      overflow-wrap: anywhere;
    }
    .sia-related-card-link:hover .sia-related-card-title { color: #1d4ed8; }
    .sia-related-empty {
      grid-column: 1 / -1;
      padding: 16px 0;
      color: #64748b;
      font-size: 14px;
    }
    @media (max-width: 700px) {
      .sia-related-heading { font-size: 18px; margin-bottom: 20px; }
      .sia-related-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 22px 16px; }
      .sia-related-card-title { font-size: 16px; }
    }
    @media (max-width: 480px) {
      .sia-related-grid { grid-template-columns: 1fr; gap: 22px; }
      .sia-related-card-title { font-size: 17px; }
    }
'''

OLD_MARKUP = '''              <div class='widget-area'>
                <div class='widget-box' style='border: none; padding: 0; box-shadow: none;'>
                  <h3 id='silo-related-heading'>More From This Silo</h3>
                  <div aria-live='polite' id='sia-hybrid-status' style='font-size:11px;color:#64748b;margin:-6px 0 9px;'></div>
                  <ul class='widget-list' id='related-posts-list'>
                    <li>Loading...</li>
                  </ul>
                </div>
              </div>'''

NEW_MARKUP = '''              <div class='widget-area sia-related-section'>
                <div class='sia-related-shell'>
                  <h3 class='sia-related-heading' id='silo-related-heading'>
                    <span aria-hidden='true' class='sia-related-heading-icon'>&#9776;</span>
                    <span>More From This Silo</span>
                  </h3>
                  <div aria-live='polite' class='sia-related-status' id='sia-hybrid-status'></div>
                  <ul class='sia-related-grid' id='related-posts-list'>
                    <li class='sia-related-empty'>Loading...</li>
                  </ul>
                </div>
              </div>'''


def patch_generator(text: str) -> str:
    if "featured_image: str = \"\"" not in text:
        anchor = "    silo: str\n"
        if anchor not in text:
            raise RuntimeError("Post dataclass silo field not found")
        text = text.replace(anchor, anchor + "    featured_image: str = \"\"\n", 1)

    if "def extract_featured_image(" not in text:
        anchor = '''def parse_entry(entry: dict) -> dict:\n'''
        helper = '''def extract_featured_image(entry: dict, body: str) -> str:\n    # Prefer the first body image so visual cards do not inherit a tiny/square\n    # media thumbnail crop. Fall back to Blogger media$thumbnail when needed.\n    match = re.search(r'''<img\\b[^>]*\\bsrc=[\"\\']([^\"\\']+)[\"\\']''', body or \"\", re.I)\n    if match:\n        return html.unescape(match.group(1)).strip()\n    thumbnail = entry.get(\"media$thumbnail\", {}) or {}\n    return html.unescape(thumbnail.get(\"url\", \"\") or \"\").strip()\n\n\n'''
        if anchor not in text:
            raise RuntimeError("parse_entry anchor not found")
        text = text.replace(anchor, helper + anchor, 1)

    if '"featured_image": extract_featured_image(entry, body),' not in text:
        anchor = '        "updated": entry.get("updated", {}).get("$t", ""),\n        "text": strip_html(body),\n'
        replacement = '        "updated": entry.get("updated", {}).get("$t", ""),\n        "featured_image": extract_featured_image(entry, body),\n        "text": strip_html(body),\n'
        if anchor not in text:
            raise RuntimeError("parse_entry output anchor not found")
        text = text.replace(anchor, replacement, 1)

    if "featured_image=raw.get(\"featured_image\", \"\")," not in text:
        anchor = "            silo=silo,\n"
        if anchor not in text:
            raise RuntimeError("Post construction silo anchor not found")
        text = text.replace(anchor, anchor + '            featured_image=raw.get("featured_image", ""),\n', 1)

    if '"image": p.featured_image,' not in text:
        anchor = '            "entities": p.entities,\n            "related": related.get(p.id, []),\n'
        replacement = '            "entities": p.entities,\n            "image": p.featured_image,\n            "related": related.get(p.id, []),\n'
        if anchor not in text:
            raise RuntimeError("Graph post-map anchor not found")
        text = text.replace(anchor, replacement, 1)

    compile(text, str(GENERATOR), "exec")
    return text


def patch_adapter(text: str) -> str:
    if "function relatedImageUrl(" not in text:
        anchor = "  function renderRelated(items, mode) {\n"
        helper = r'''  function relatedImageUrl(value) {
    var url = String(value || '').replace(/&amp;/g, '&').trim();
    if (!url) return '';
    return url
      .replace(/\/s\d+(?:-[^/]+)?\//i, '/s640/')
      .replace(/\/w\d+(?:-h\d+)?(?:-[^/]+)?\//i, '/s640/')
      .replace(/=w\d+(?:-h\d+)?(?:-[^/?#]+)?$/i, '=w640');
  }

  function entryImage(entry) {
    var body = '';
    if (entry && entry.content && entry.content.$t) body = entry.content.$t;
    else if (entry && entry.summary && entry.summary.$t) body = entry.summary.$t;
    var match = String(body || '').match(/<img\b[^>]*\bsrc=["']([^"']+)["']/i);
    if (match && match[1]) return relatedImageUrl(match[1]);
    var thumb = entry && entry['media$thumbnail'] ? entry['media$thumbnail'].url : '';
    return relatedImageUrl(thumb || '');
  }

'''
        if anchor not in text:
            raise RuntimeError("renderRelated anchor not found")
        text = text.replace(anchor, helper + anchor, 1)

    old_render = '''    list.innerHTML = '';
    if (!items || !items.length) {
      list.innerHTML = '<li>No sufficiently relevant posts found.</li>';
      list.setAttribute('data-sia-mode', mode || 'unknown');
      return;
    }

    items.slice(0, cfg.maxRelated).forEach(function (item) {
      var li = document.createElement('li');
      var a = document.createElement('a');
      a.href = item.url;
      a.textContent = item.title;
      if (item.score !== undefined) a.setAttribute('data-sia-score', item.score);
      if (item.reasons && item.reasons.length) {
        a.setAttribute('data-sia-reasons', item.reasons.join(','));
      }
      if (item.relation_types && item.relation_types.length) {
        a.setAttribute('data-sia-relation-types', item.relation_types.join(','));
      }
      if (item.evidence_status) {
        a.setAttribute('data-sia-evidence-status', item.evidence_status);
      }
      li.appendChild(a);
      list.appendChild(li);
    });'''
    new_render = '''    list.innerHTML = '';
    if (!items || !items.length) {
      var empty = document.createElement('li');
      empty.className = 'sia-related-empty';
      empty.textContent = 'No sufficiently relevant posts found.';
      list.appendChild(empty);
      list.setAttribute('data-sia-mode', mode || 'unknown');
      return;
    }

    items.slice(0, cfg.maxRelated).forEach(function (item) {
      var li = document.createElement('li');
      li.className = 'sia-related-card';

      var a = document.createElement('a');
      a.className = 'sia-related-card-link';
      a.href = item.url;
      a.setAttribute('aria-label', item.title || 'Related article');

      var media = document.createElement('span');
      media.className = 'sia-related-card-media';
      var imageUrl = relatedImageUrl(item.image || '');
      if (imageUrl) {
        var img = document.createElement('img');
        img.className = 'sia-related-card-image';
        img.src = imageUrl;
        img.alt = item.title || 'Related article';
        img.loading = 'lazy';
        img.decoding = 'async';
        media.appendChild(img);
      } else {
        var placeholder = document.createElement('span');
        placeholder.className = 'sia-related-card-placeholder';
        placeholder.textContent = 'Article';
        media.appendChild(placeholder);
      }

      var title = document.createElement('span');
      title.className = 'sia-related-card-title';
      title.textContent = item.title;

      if (item.score !== undefined) a.setAttribute('data-sia-score', item.score);
      if (item.reasons && item.reasons.length) {
        a.setAttribute('data-sia-reasons', item.reasons.join(','));
      }
      if (item.relation_types && item.relation_types.length) {
        a.setAttribute('data-sia-relation-types', item.relation_types.join(','));
      }
      if (item.evidence_status) {
        a.setAttribute('data-sia-evidence-status', item.evidence_status);
      }
      a.appendChild(media);
      a.appendChild(title);
      li.appendChild(a);
      list.appendChild(li);
    });'''
    if "className = 'sia-related-card'" not in text:
        if old_render not in text:
            raise RuntimeError("Existing related-list renderer did not match expected v0.1 source")
        text = text.replace(old_render, new_render, 1)

    if "image: relatedImageUrl(p.image || '')," not in text:
        anchor = "        url: p.url,\n        score: ref.score,\n"
        replacement = "        url: p.url,\n        image: relatedImageUrl(p.image || ''),\n        score: ref.score,\n"
        if anchor not in text:
            raise RuntimeError("Graph hydration image anchor not found")
        text = text.replace(anchor, replacement, 1)

    if "image: entryImage(entry)," not in text:
        anchor = "      url: link ? link.href : '',\n      labels: (entry.category || []).map(function (c) { return c.term || ''; }).filter(Boolean)\n"
        replacement = "      url: link ? link.href : '',\n      image: entryImage(entry),\n      labels: (entry.category || []).map(function (c) { return c.term || ''; }).filter(Boolean)\n"
        if anchor not in text:
            raise RuntimeError("Fallback entry image anchor not found")
        text = text.replace(anchor, replacement, 1)

    if "image: p.image || ''," not in text:
        anchor = "        title: p.title,\n        url: p.url,\n        score: s.score,\n"
        replacement = "        title: p.title,\n        url: p.url,\n        image: p.image || '',\n        score: s.score,\n"
        if anchor not in text:
            raise RuntimeError("Fallback ranked image anchor not found")
        text = text.replace(anchor, replacement, 1)

    return text


def patch_theme(text: str) -> str:
    if MARKER not in text:
        anchor = "    .widget-area { margin-top: 40px; padding-top: 30px; border-top: 2px dashed #e2e8f0; }\n"
        if anchor not in text:
            raise RuntimeError("Related-grid CSS anchor not found")
        text = text.replace(anchor, CSS + "\n" + anchor, 1)

    if NEW_MARKUP not in text:
        if OLD_MARKUP not in text:
            raise RuntimeError("Related-silo markup anchor not found")
        text = text.replace(OLD_MARKUP, NEW_MARKUP, 1)

    text = patch_adapter(text)
    return text


def validate(generator: str, adapter: str, theme: str) -> None:
    required_generator = [
        'featured_image: str = ""',
        "def extract_featured_image(",
        '"featured_image": extract_featured_image(entry, body)',
        '"image": p.featured_image',
    ]
    required_adapter = [
        "function relatedImageUrl(",
        "function entryImage(entry)",
        "className = 'sia-related-card'",
        "className = 'sia-related-card-image'",
        "image: relatedImageUrl(p.image || '')",
        "image: entryImage(entry)",
    ]
    required_theme = [
        MARKER,
        "class='widget-area sia-related-section'",
        "class='sia-related-heading'",
        "class='sia-related-grid'",
        "id='related-posts-list'",
        "className = 'sia-related-card'",
    ]
    missing = [x for x in required_generator if x not in generator]
    missing += [x for x in required_adapter if x not in adapter]
    missing += [x for x in required_theme if x not in theme]
    if missing:
        raise RuntimeError("Missing related-silo grid markers: " + ", ".join(missing))

    if "More From This Silo" not in theme:
        raise RuntimeError("Primary Silo related heading is missing")
    if "object-fit: cover" not in theme:
        raise RuntimeError("Related card image presentation crop is missing")
    if theme.count("id='related-posts-list'") != 1:
        raise RuntimeError("Related posts target must appear exactly once")


def activate_sources() -> Tuple[str, str]:
    generator = patch_generator(GENERATOR.read_text(encoding="utf-8"))
    adapter = patch_adapter(ADAPTER.read_text(encoding="utf-8"))
    GENERATOR.write_text(generator, encoding="utf-8")
    ADAPTER.write_text(adapter, encoding="utf-8")
    return generator, adapter


def main() -> None:
    generator, adapter = activate_sources()
    theme = patch_theme(THEME.read_text(encoding="utf-8"))
    validate(generator, adapter, theme)
    THEME.write_text(theme, encoding="utf-8")
    print("SIA v0.1 visual Related Silo card grid activated")


if __name__ == "__main__":
    main()
