#!/usr/bin/env python3
"""Safe v0.1 adaptive theme activation wrapper.

Uses the stable patch functions from activate_adaptive_system.py, but inserts
BreadcrumbList only after the complete existing BlogPosting script/condition.
"""
from pathlib import Path
import html
import re
import xml.etree.ElementTree as ET

import activate_adaptive_system as base

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


def main() -> None:
    text = THEME.read_text(encoding="utf-8")
    text = base.patch_head(text)
    text = base.patch_heading_architecture(text)
    text = base.patch_featured_image(text)
    text = base.patch_sharing(text)
    text = base.patch_footer_and_ads(text)
    text = patch_breadcrumb_schema(text)

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
        "fetchpriority='high'",
        "expr:srcset=",
        base.DEDUPE_MARKER,
        base.SHARE_JS_MARKER,
        "encodeURIComponent",
        "<h1 class='post-title'><data:post.title/></h1>",
        "id='footer-links'",
        "max-snippet:-1",
    ]
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise RuntimeError("Missing adaptive Blogger markers: " + ", ".join(missing))
    if 'let parentLink = bodyImg.parentNode;' in text:
        raise RuntimeError("Blind first-image hiding is still present")
    if "href='/p/about.html'" in text or "href='/p/privacy-policy.html'" in text:
        raise RuntimeError("Hardcoded footer legal pages are still present")
    if "                  Advertisement\n" in text:
        raise RuntimeError("Empty advertisement placeholder is still present")

    print("SIA v0.1 adaptive Blogger system hardening activated for " + base.REPOSITORY)


if __name__ == "__main__":
    main()
