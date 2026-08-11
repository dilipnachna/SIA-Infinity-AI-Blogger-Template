#!/usr/bin/env python3
"""Activate SIA v0.1 Core Web Vitals performance-budget guards.

This layer is intentionally structural rather than telemetry-driven. It does not
claim or measure a PageSpeed score. It protects the universal Blogger theme from
avoidable layout shifts and priority inversions while preserving useful UI.

Budget targets are documentation/CI contracts for real-user p75 monitoring:
- LCP <= 2.5s
- INP <= 200ms
- CLS <= 0.10

Runtime rules:
- reserve author-avatar geometry before late Blogger profile hydration
- keep article featured image as the high-priority visual request
- keep related-card media lazy and layout-contained
- reserve modest ad geometry only when a Blogger ad/widget actually exists
- schedule non-critical author feed hydration during browser idle time
- no CWV telemetry, fingerprinting, beaconing, or score manipulation
"""
from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from pathlib import Path

THEME = Path("theme/SIA-Infinity-AI-Blogger-Template-v0.1.xml")

META_MARKER = "SIA CWV Performance Budget v0.1"
CSS_MARKER = "SIA CWV CLS Guards v0.1"
BUDGET_VALUE = "p75-lcp-2.5s-inp-200ms-cls-0.1"

CSS = r'''
    /* SIA CWV CLS Guards v0.1 */
    .single-post-author-avatar-slot {
      width: 50px;
      height: 50px;
      flex: 0 0 50px;
      display: block;
      overflow: hidden;
      border: 1px solid #94a3b8;
      border-radius: 50%;
      background: #f1f5f9;
      box-sizing: border-box;
    }
    .single-post-author-avatar-slot .single-post-author-avatar {
      width: 100%;
      height: 100%;
      margin: 0;
      border: 0;
      border-radius: 0;
      display: block;
      object-fit: cover;
      object-position: center;
    }
    .single-post-author-card,
    .single-post-author-card.no-avatar {
      grid-template-columns: 150px minmax(0, 1fr);
    }
    .single-post-author-card-avatar-slot {
      width: 124px;
      height: 124px;
      display: block;
      justify-self: center;
      overflow: hidden;
      border: 1px solid #1e3a8a;
      border-radius: 50%;
      background: #f1f5f9;
      box-sizing: border-box;
    }
    .single-post-author-card-avatar-slot .single-post-author-card-avatar {
      width: 100%;
      height: 100%;
      margin: 0;
      border: 0;
      border-radius: 0;
      display: block;
      object-fit: cover;
      object-position: center;
    }
    .sia-related-card-media {
      contain: layout paint;
    }
    .sia-related-card-image {
      aspect-ratio: 16 / 9;
    }
    .sia-related-section {
      content-visibility: auto;
      contain-intrinsic-size: auto 420px;
    }
    @supports selector(.sia-ad-zone:has(.widget)) {
      .sia-ad-zone:has(.widget) {
        min-height: 250px;
      }
      .sia-ad-top:has(.widget) {
        min-height: 100px;
      }
    }
    @media (max-width: 700px) {
      .single-post-author-avatar-slot {
        width: 46px;
        height: 46px;
        flex-basis: 46px;
      }
      .single-post-author-card,
      .single-post-author-card.no-avatar {
        grid-template-columns: 88px minmax(0, 1fr);
      }
      .single-post-author-card-avatar-slot {
        width: 78px;
        height: 78px;
      }
      .sia-related-section {
        contain-intrinsic-size: auto 720px;
      }
    }
'''

HEADER_OLD = '''                  <div class='single-post-byline'>
                    <b:if cond='data:post.authorPhoto.url'>
                      <img class='single-post-author-avatar'
                           decoding='async'
                           expr:alt='data:post.author.name'
                           expr:src='data:post.authorPhoto.url'
                           height='50'
                           width='50'/>
                    </b:if>
                    <div class='single-post-byline-copy'>'''

HEADER_NEW = '''                  <div class='single-post-byline'>
                    <span aria-hidden='true' class='single-post-author-avatar-slot'>
                      <b:if cond='data:post.authorPhoto.url'>
                        <img class='single-post-author-avatar'
                             decoding='async'
                             expr:alt='data:post.author.name'
                             expr:src='data:post.authorPhoto.url'
                             fetchpriority='low'
                             height='50'
                             loading='lazy'
                             width='50'/>
                      </b:if>
                    </span>
                    <div class='single-post-byline-copy'>'''

CARD_OLD = '''                  <div expr:class='data:post.authorPhoto.url ? &quot;single-post-author-card&quot; : &quot;single-post-author-card no-avatar&quot;' expr:data-sia-post-id='data:post.id'>
                    <b:if cond='data:post.authorPhoto.url'>
                      <img class='single-post-author-card-avatar'
                           decoding='async'
                           expr:alt='data:post.author.name'
                           expr:src='data:post.authorPhoto.url'
                           height='124'
                           loading='lazy'
                           width='124'/>
                    </b:if>
                    <div class='single-post-author-card-copy'>'''

CARD_NEW = '''                  <div expr:class='data:post.authorPhoto.url ? &quot;single-post-author-card&quot; : &quot;single-post-author-card no-avatar&quot;' expr:data-sia-post-id='data:post.id'>
                    <span aria-hidden='true' class='single-post-author-card-avatar-slot'>
                      <b:if cond='data:post.authorPhoto.url'>
                        <img class='single-post-author-card-avatar'
                             decoding='async'
                             expr:alt='data:post.author.name'
                             expr:src='data:post.authorPhoto.url'
                             fetchpriority='low'
                             height='124'
                             loading='lazy'
                             width='124'/>
                      </b:if>
                    </span>
                    <div class='single-post-author-card-copy'>'''

HEADER_JS = r'''      function addHeaderAvatar(image, name) {
        var byline = document.querySelector('.single-post-byline');
        if (!byline || byline.querySelector('.single-post-author-avatar')) return;
        var slot = byline.querySelector('.single-post-author-avatar-slot');
        if (!slot) return;
        var img = document.createElement('img');
        img.className = 'single-post-author-avatar';
        img.src = image;
        img.alt = name || 'Author';
        img.width = 50;
        img.height = 50;
        img.loading = 'lazy';
        img.decoding = 'async';
        img.fetchPriority = 'low';
        slot.appendChild(img);
      }

'''

CARD_JS = r'''      function addCardAvatar(image, name) {
        var card = document.querySelector('.single-post-author-card');
        if (!card || card.querySelector('.single-post-author-card-avatar')) return;
        var slot = card.querySelector('.single-post-author-card-avatar-slot');
        if (!slot) return;
        var img = document.createElement('img');
        img.className = 'single-post-author-card-avatar';
        img.src = image;
        img.alt = name || 'Author';
        img.width = 124;
        img.height = 124;
        img.loading = 'lazy';
        img.decoding = 'async';
        img.fetchPriority = 'low';
        slot.appendChild(img);
      }

'''

IDLE_JS = r'''      function scheduleHydrate() {
        if ('requestIdleCallback' in window) {
          window.requestIdleCallback(hydrate, { timeout: 1200 });
        } else {
          window.setTimeout(hydrate, 0);
        }
      }

      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', scheduleHydrate, { once: true });
      } else {
        scheduleHydrate();
      }
'''


def patch_head(text: str) -> str:
    if META_MARKER in text:
        return text
    anchor = "  <meta content='0.1' name='sia-template-version'/>\n"
    if anchor not in text:
        raise RuntimeError("CWV meta insertion anchor not found")
    block = (
        anchor
        + f"  <!-- {META_MARKER} -->\n"
        + f"  <meta content='{BUDGET_VALUE}' name='sia-cwv-budget'/>\n"
    )
    return text.replace(anchor, block, 1)


def patch_css(text: str) -> str:
    if CSS_MARKER in text:
        return text
    anchor = "  ]]></b:skin>"
    if anchor not in text:
        raise RuntimeError("CWV CSS closing anchor not found")
    return text.replace(anchor, "\n" + CSS + "\n" + anchor, 1)


def patch_markup(text: str) -> str:
    if "class='single-post-author-avatar-slot'" not in text:
        if HEADER_OLD not in text:
            raise RuntimeError("Header author avatar markup did not match expected source")
        text = text.replace(HEADER_OLD, HEADER_NEW, 1)

    if "class='single-post-author-card-avatar-slot'" not in text:
        if CARD_OLD not in text:
            raise RuntimeError("Author card avatar markup did not match expected source")
        text = text.replace(CARD_OLD, CARD_NEW, 1)
    return text


def replace_function(text: str, start: str, end: str, replacement: str) -> str:
    start_pos = text.find(start)
    if start_pos < 0:
        raise RuntimeError("CWV runtime start anchor missing: " + start.strip())
    end_pos = text.find(end, start_pos)
    if end_pos < 0:
        raise RuntimeError("CWV runtime end anchor missing: " + end.strip())
    return text[:start_pos] + replacement + text[end_pos:]


def patch_runtime(text: str) -> str:
    if "var slot = byline.querySelector('.single-post-author-avatar-slot');" not in text:
        text = replace_function(
            text,
            "      function addHeaderAvatar(image, name) {\n",
            "      function addCardAvatar(image, name) {\n",
            HEADER_JS,
        )

    if "var slot = card.querySelector('.single-post-author-card-avatar-slot');" not in text:
        text = replace_function(
            text,
            "      function addCardAvatar(image, name) {\n",
            "      function linkAuthor(profileUrl) {\n",
            CARD_JS,
        )

    if "function scheduleHydrate()" not in text:
        old = '''      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', hydrate, { once: true });
      } else {
        hydrate();
      }
'''
        if old not in text:
            raise RuntimeError("Author hydration scheduling block did not match expected source")
        text = text.replace(old, IDLE_JS, 1)
    return text


def patch_theme(text: str) -> str:
    text = patch_head(text)
    text = patch_css(text)
    text = patch_markup(text)
    text = patch_runtime(text)
    return text


def validate(text: str) -> None:
    required = [
        META_MARKER,
        CSS_MARKER,
        "name='sia-cwv-budget'",
        BUDGET_VALUE,
        "class='single-post-author-avatar-slot'",
        "class='single-post-author-card-avatar-slot'",
        "fetchpriority='low'",
        "function scheduleHydrate()",
        "requestIdleCallback",
        "img.fetchPriority = 'low'",
        "contain-intrinsic-size: auto 420px",
        "@supports selector(.sia-ad-zone:has(.widget))",
        ".sia-ad-zone:has(.widget)",
        "min-height: 250px",
        "min-height: 100px",
    ]
    missing = [item for item in required if item not in text]
    if missing:
        raise RuntimeError("Missing CWV performance-budget guards: " + ", ".join(missing))

    if text.count("class='single-post-author-avatar-slot'") != 1:
        raise RuntimeError("Header avatar slot must appear exactly once")
    if text.count("class='single-post-author-card-avatar-slot'") != 1:
        raise RuntimeError("Author-card avatar slot must appear exactly once")

    # Critical article image keeps high priority; secondary author/media stays low/lazy.
    if "id='sia-featured-image'" not in text or "fetchpriority='high'" not in text:
        raise RuntimeError("Article featured image lost high fetch priority")
    if "className = 'sia-related-card-image'" not in text or "img.loading = 'lazy'" not in text:
        raise RuntimeError("Related card images lost lazy progressive rendering")

    # Performance budget must not add measurement/telemetry overhead.
    cwv_source = CSS + HEADER_JS + CARD_JS + IDLE_JS
    for forbidden in ("PerformanceObserver", "sendBeacon(", "localStorage", "sessionStorage", "fetch("):
        if forbidden in cwv_source:
            raise RuntimeError("CWV guard must remain telemetry-free: " + forbidden)

    if re.search(r"[\u0900-\u097F]", html.unescape(CSS + HEADER_JS + CARD_JS + IDLE_JS)):
        raise RuntimeError("Universal CWV source contains Devanagari text")


def main() -> None:
    text = THEME.read_text(encoding="utf-8")
    text = patch_theme(text)
    validate(text)
    THEME.write_text(text, encoding="utf-8")
    ET.parse(THEME)
    print("SIA v0.1 CWV performance budget activated: p75 LCP/INP/CLS guards")


if __name__ == "__main__":
    main()
