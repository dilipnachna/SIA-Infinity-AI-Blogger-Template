#!/usr/bin/env python3
"""Activate publisher-neutral AdSense layout zones for SIA Blogger v0.1.

The universal theme never contains a publisher ID or ad unit ID. Instead it
exposes three optional Blogger Layout sections:

- sia-ad-top: single-item pages, before Blog1 content
- sia-ad-bottom: single-item pages, after Blog1 content
- sia-ad-feed: multiple-item pages, after the feed and before supporting widgets

Owners may place a Blogger AdSense gadget or an HTML/JavaScript gadget in a
zone. Empty zones do not render an Advertisement placeholder. Auto Ads remain
independent of these manual zones.

All three zones are outer layout sections. The proven Blog1 post loop is not
modified or reconstructed.
"""
from pathlib import Path
import html
import re
import xml.etree.ElementTree as ET

THEME = Path("theme/SIA-Infinity-AI-Blogger-Template-v0.1.xml")
MARKER = "SIA Publisher-Neutral Ad Zones v0.1"

CSS = '''
    /* SIA Publisher-Neutral Ad Zones v0.1 */
    .sia-ad-zone { margin: 28px 0; min-height: 0; text-align: center; overflow: hidden; }
    .sia-ad-zone:empty { display: none; margin: 0; }
    .sia-ad-zone .widget { margin: 0; }
    .sia-ad-zone .widget-content { max-width: 100%; overflow: hidden; }
    .sia-ad-zone ins.adsbygoogle { max-width: 100%; }
    .sia-ad-top { margin-top: 0; margin-bottom: 30px; }
    .sia-ad-bottom { margin-top: 30px; margin-bottom: 30px; }
    .sia-ad-feed { margin-top: 24px; margin-bottom: 32px; }
'''

TOP_BLOCK = '''    <!-- SIA Publisher-Neutral Ad Zones v0.1 -->
    <b:if cond='data:view.isSingleItem'>
      <b:section class='sia-ad-zone sia-ad-top' id='sia-ad-top' maxwidgets='1' showaddelement='yes'></b:section>
    </b:if>
'''

AFTER_MAIN_BLOCK = '''
    <b:if cond='data:view.isSingleItem'>
      <b:section class='sia-ad-zone sia-ad-bottom' id='sia-ad-bottom' maxwidgets='1' showaddelement='yes'></b:section>
    </b:if>

    <b:if cond='data:view.isMultipleItems'>
      <b:section class='sia-ad-zone sia-ad-feed' id='sia-ad-feed' maxwidgets='1' showaddelement='yes'></b:section>
    </b:if>
'''


def patch_css(text: str) -> str:
    if MARKER in text:
        return text
    anchor = "    /* Blogger comments */\n"
    if anchor not in text:
        raise RuntimeError("Ad-zone CSS anchor not found")
    return text.replace(anchor, CSS + "\n" + anchor, 1)


def patch_slots(text: str) -> str:
    if "id='sia-ad-top'" not in text:
        anchor = "  <div expr:class='data:view.isSingleItem ? &quot;container single-container&quot; : &quot;container feed-container&quot;'>\n    <b:section id='main-content'>\n"
        replacement = (
            "  <div expr:class='data:view.isSingleItem ? &quot;container single-container&quot; : &quot;container feed-container&quot;'>\n"
            + TOP_BLOCK
            + "    <b:section id='main-content'>\n"
        )
        if anchor not in text:
            raise RuntimeError("Top ad-zone anchor not found")
        text = text.replace(anchor, replacement, 1)

    if "id='sia-ad-bottom'" not in text or "id='sia-ad-feed'" not in text:
        anchor = "      </b:widget>\n    </b:section>\n\n    <div expr:class='data:view.isPost ? &quot;widget-grid&quot; : &quot;widget-grid popular-only-grid&quot;'>\n"
        replacement = (
            "      </b:widget>\n    </b:section>\n"
            + AFTER_MAIN_BLOCK
            + "\n    <div expr:class='data:view.isPost ? &quot;widget-grid&quot; : &quot;widget-grid popular-only-grid&quot;'>\n"
        )
        if anchor not in text:
            raise RuntimeError("Bottom/feed ad-zone anchor not found")
        text = text.replace(anchor, replacement, 1)

    return text


def validate(text: str) -> None:
    required = [
        MARKER,
        "id='sia-ad-top'",
        "id='sia-ad-bottom'",
        "id='sia-ad-feed'",
        "maxwidgets='1'",
        "showaddelement='yes'",
    ]
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise RuntimeError("Missing SIA ad-zone markers: " + ", ".join(missing))

    for slot in ("sia-ad-top", "sia-ad-bottom", "sia-ad-feed"):
        if text.count(f"id='{slot}'") != 1:
            raise RuntimeError(f"Ad zone {slot} must appear exactly once")

    if "ca-pub-" in text.lower():
        raise RuntimeError("Universal theme must not hardcode an AdSense publisher ID")

    top = text.index("id='sia-ad-top'")
    main = text.index("<b:section id='main-content'>")
    bottom = text.index("id='sia-ad-bottom'")
    feed = text.index("id='sia-ad-feed'")
    widgets = text.index("<div expr:class='data:view.isPost ? &quot;widget-grid&quot;")
    if not (top < main < bottom < widgets and main < feed < widgets):
        raise RuntimeError("Ad zones are outside the expected safe layout positions")

    if re.search(r"[\u0900-\u097F]", html.unescape(text)):
        raise RuntimeError("Universal Blogger XML contains Devanagari source text")


def main() -> None:
    text = THEME.read_text(encoding="utf-8")
    text = patch_css(text)
    text = patch_slots(text)
    validate(text)

    THEME.write_text(text, encoding="utf-8")
    ET.parse(THEME)
    print("SIA v0.1 publisher-neutral AdSense layout zones activated")


if __name__ == "__main__":
    main()
