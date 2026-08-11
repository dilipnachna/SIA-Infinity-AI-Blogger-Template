#!/usr/bin/env python3
"""Safe v0.1 adaptive theme activation wrapper.

Uses the stable patch functions from activate_adaptive_system.py, but inserts
BreadcrumbList only after the complete existing BlogPosting script/condition.

The post-detail featured image is intentionally different from feed thumbnails:
feed cards may crop to a presentation ratio, while the main article image keeps
the original image composition and only resizes responsively.

Publisher-neutral Blogger Layout ad zones are also activated without modifying
the proven Blog1 post loop or embedding any AdSense publisher ID.

Single posts use the SIA editorial hero header and editorial footer treatment.
The footer includes dynamic labels, an optional truth-safe disclosure, a large
author card and full-width share actions. No fake author verification or AI
assistance claim is rendered by default.

Bot Integrity keeps human/crawler semantic reality aligned and Evidence-Aware
Relations ensure semantic similarity is never promoted to supporting evidence.

The optional Fibonacci Attention Map measures only coarse in-memory interaction
and dwell buckets. It never transmits telemetry, tracks ad clicks, or moves ads;
it can only recommend an existing publisher-neutral ad zone.
"""
from pathlib import Path
import html
import re
import xml.etree.ElementTree as ET

import activate_adaptive_system as base
import activate_adsense_zones as ads
import activate_attention_map as attention
import activate_single_post_header as editorial
import activate_single_post_bottom as editorial_bottom
import activate_integrity_evidence as integrity

THEME = Path("theme/SIA-Infinity-AI-Blogger-Template-v0.1.xml")


def patch_breadcrumb_schema(text: str) -> str:
    if base.BREADCRUMB_SCHEMA_MARKER in text:
        return text

    marker = "            <!-- ADVANCED BlogPosting JSON-LD SCHEMA -->"
    marker_pos = text.find(marker)
    if marker_pos < 0:
        raise RuntimeError("BlogPosting schema marker not found")

    script_close = text.find("              </script>", marker_pos)
    if script_close < 0:
        raise RuntimeError("BlogPosting script closing tag not found")

    condition_close = text.find("            </b:if>", script_close)
    if condition_close < 0:
        raise RuntimeError("BlogPosting condition closing tag not found")
    insert_pos = condition_close + len("            </b:if>")

    block = '''

            <!-- SIA BreadcrumbList JSON-LD v0.1 -->
            <b:if cond='data:view.isPost'>
              <script type='application/ld+json'>
              {
                &quot;@context&quot;: &quot;https://schema.org&quot;,
                &quot;@type&quot;: &quot;BreadcrumbList&quot;,
                &quot;itemListElement&quot;: [
                  {
                    &quot;@type&quot;: &quot;ListItem&quot;,
                    &quot;position&quot;: 1,
                    &quot;name&quot;: &quot;Home&quot;,
                    &quot;item&quot;: &quot;<data:blog.homepageUrl/>&quot;
                  }<b:if cond='data:post.labels'>,
                  {
                    &quot;@type&quot;: &quot;ListItem&quot;,
                    &quot;position&quot;: 2,
                    &quot;name&quot;: &quot;<data:post.labels.first.name/>&quot;,
                    &quot;item&quot;: &quot;<data:post.labels.first.url/>&quot;
                  },
                  {
                    &quot;@type&quot;: &quot;ListItem&quot;,
                    &quot;position&quot;: 3,
                    &quot;name&quot;: &quot;<data:post.title.escaped/>&quot;,
                    &quot;item&quot;: &quot;<data:post.url.canonical/>&quot;
                  }<b:else/>,
                  {
                    &quot;@type&quot;: &quot;ListItem&quot;,
                    &quot;position&quot;: 2,
                    &quot;name&quot;: &quot;<data:post.title.escaped/>&quot;,
                    &quot;item&quot;: &quot;<data:post.url.canonical/>&quot;
                  }</b:if>
                ]
              }
              </script>
            </b:if>'''
    return text[:insert_pos] + block + text[insert_pos:]


def patch_featured_image_no_crop(text: str) -> str:
    """Keep the article featured image responsive without server-side cropping."""
    cropped = '''                  <img decoding='async'
                       expr:alt='data:post.title'
                       expr:src='resizeImage(data:post.featuredImage, 1200, &quot;1200:675&quot;)'
                       expr:srcset='resizeImage(data:post.featuredImage, 320, &quot;320:180&quot;) + &quot; 320w, &quot; + resizeImage(data:post.featuredImage, 480, &quot;480:270&quot;) + &quot; 480w, &quot; + resizeImage(data:post.featuredImage, 640, &quot;640:360&quot;) + &quot; 640w, &quot; + resizeImage(data:post.featuredImage, 960, &quot;960:540&quot;) + &quot; 960w, &quot; + resizeImage(data:post.featuredImage, 1200, &quot;1200:675&quot;) + &quot; 1200w&quot;'
                       fetchpriority='high'
                       height='675'
                       id='sia-featured-image'
                       loading='eager'
                       sizes='(max-width: 840px) 100vw, 800px'
                       width='1200'/>'''

    no_crop = '''                  <img data-sia-image-mode='no-crop'
                       decoding='async'
                       expr:alt='data:post.title'
                       expr:src='resizeImage(data:post.featuredImage, 1200)'
                       expr:srcset='resizeImage(data:post.featuredImage, 320) + &quot; 320w, &quot; + resizeImage(data:post.featuredImage, 480) + &quot; 480w, &quot; + resizeImage(data:post.featuredImage, 640) + &quot; 640w, &quot; + resizeImage(data:post.featuredImage, 960) + &quot; 960w, &quot; + resizeImage(data:post.featuredImage, 1200) + &quot; 1200w&quot;'
                       fetchpriority='high'
                       height='675'
                       id='sia-featured-image'
                       loading='eager'
                       sizes='(max-width: 840px) 100vw, 800px'
                       width='1200'/>'''

    if cropped in text:
        text = text.replace(cropped, no_crop, 1)
    elif "data-sia-image-mode='no-crop'" not in text:
        raise RuntimeError("Article featured image block did not match expected adaptive source")

    old_css = '''    .featured-img-box img { width: 100%; aspect-ratio: 16/9; object-fit: cover; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.08); display: block; }'''
    new_css = '''    .featured-img-box { background: #f8fafc; border-radius: 12px; overflow: hidden; }
    .featured-img-box img { width: 100%; aspect-ratio: 16/9; object-fit: contain; object-position: center; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.08); display: block; }'''
    if old_css in text:
        text = text.replace(old_css, new_css, 1)
    elif "object-fit: contain" not in text:
        raise RuntimeError("Featured image CSS did not match expected adaptive source")

    return text


def main() -> None:
    generator, adapter = integrity.activate_sources()

    text = THEME.read_text(encoding="utf-8")
    text = base.patch_head(text)
    text = base.patch_heading_architecture(text)
    text = base.patch_featured_image(text)
    text = patch_featured_image_no_crop(text)
    if "<div class='post-share-buttons'>" in text:
        text = base.patch_sharing(text)
    elif base.SHARE_JS_MARKER not in text:
        raise RuntimeError("Editorial share rail requires the encoded social action runtime")
    text = base.patch_footer_and_ads(text)
    text = patch_breadcrumb_schema(text)
    text = editorial.patch_css(text)
    text = editorial.patch_markup(text)
    editorial.validate(text)
    text = editorial_bottom.patch_css(text)
    text = editorial_bottom.patch_markup(text)
    text = editorial_bottom.patch_script(text)
    editorial_bottom.validate(text)
    text = ads.patch_css(text)
    text = ads.patch_slots(text)
    ads.validate(text)
    text = integrity.patch_theme(text)
    integrity.validate_integrity(text, generator, adapter)
    text = attention.patch_theme(text)
    attention.validate(text)

    if re.search(r"[\u0900-\u097F]", html.unescape(text)):
        raise RuntimeError("Universal Blogger XML contains Devanagari source text")

    THEME.write_text(text, encoding="utf-8")
    ET.parse(THEME)

    required = [
        base.HEADING_MARKER,
        base.WEBSITE_SCHEMA_MARKER,
        base.BREADCRUMB_SCHEMA_MARKER,
        "name='sia-community-repository'",
        "id='sia-featured-image'",
        "data-sia-image-mode='no-crop'",
        "expr:src='resizeImage(data:post.featuredImage, 1200)'",
        "object-fit: contain",
        "fetchpriority='high'",
        "expr:srcset=",
        base.DEDUPE_MARKER,
        base.SHARE_JS_MARKER,
        "encodeURIComponent",
        "<h1 class='post-title'><data:post.title/></h1>",
        "id='footer-links'",
        "max-snippet:-1",
        editorial.MARKER,
        "class='single-post-kicker'",
        "class='single-post-hero'",
        "class='single-post-byline'",
        "class='single-post-share-row'",
        editorial_bottom.MARKER,
        "class='single-post-bottom'",
        "id='sia-editorial-disclosure'",
        "class='single-post-author-card",
        "class='single-post-bottom-share'",
        editorial_bottom.DISCLOSURE_JS_MARKER,
        ads.MARKER,
        "id='sia-ad-top'",
        "id='sia-ad-bottom'",
        "id='sia-ad-feed'",
        integrity.INTEGRITY_MARKER,
        "name='sia-bot-integrity'",
        "data-sia-relation-types",
        "data-sia-evidence-status",
        attention.MARKER,
        "name='sia-attention-map'",
        "id='sia-attention-map-runtime'",
        "window.SIAAttention",
        "sia:attention-recommendation",
        "autoPlace: false",
        "telemetry: false",
    ]
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise RuntimeError("Missing adaptive Blogger markers: " + ", ".join(missing))
    if "expr:src='resizeImage(data:post.featuredImage, 1200, &quot;1200:675&quot;)'" in text:
        raise RuntimeError("Article featured image still requests a server-side crop")
    if 'let parentLink = bodyImg.parentNode;' in text:
        raise RuntimeError("Blind first-image hiding is still present")
    if "href='/p/about.html'" in text or "href='/p/privacy-policy.html'" in text:
        raise RuntimeError("Hardcoded footer legal pages are still present")
    if "                  Advertisement\n" in text:
        raise RuntimeError("Empty advertisement placeholder is still present")
    if "ca-pub-" in text.lower():
        raise RuntimeError("Universal Blogger XML must remain publisher-neutral")

    print("SIA v0.1 adaptive Blogger system hardening activated for " + base.REPOSITORY)
    print("SIA v0.1 article featured image mode: responsive no-crop")
    print("SIA v0.1 editorial single-post header: primary silo, byline, labels and compact sharing")
    print("SIA v0.1 editorial single-post bottom: labels, optional disclosure, author card and share rail")
    print("SIA v0.1 bot integrity: same-content semantic parity + no crawler-specific manipulation")
    print("SIA v0.1 evidence policy: semantic similarity is not supporting evidence")
    print("SIA v0.1 attention map: opt-in, memory-only, no telemetry, no automatic ad placement")
    print("SIA v0.1 ad zones: publisher-neutral top, bottom and feed layout sections")


if __name__ == "__main__":
    main()
