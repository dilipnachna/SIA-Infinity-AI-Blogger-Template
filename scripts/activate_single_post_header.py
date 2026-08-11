#!/usr/bin/env python3
"""Activate the SIA v0.1 editorial single-post header.

The single-post header is inspired by a compact editorial/news layout:
Primary Silo kicker, large H1, author avatar/byline, date + label pills,
compact social sharing, then the featured image.

All content remains dynamic and publisher-neutral. No fake verification badge
is rendered. BreadcrumbList JSON-LD is preserved while the verbose visual
breadcrumb is replaced by the Primary Silo kicker.
"""
from pathlib import Path
import html
import re
import xml.etree.ElementTree as ET

THEME = Path("theme/SIA-Infinity-AI-Blogger-Template-v0.1.xml")
MARKER = "SIA Editorial Single Post Header v0.1"

CSS = r'''
    /* SIA Editorial Single Post Header v0.1 */
    .single-post-kicker { display: flex; align-items: center; gap: 7px; margin: 0 0 14px; font-size: 15px; line-height: 1.35; font-weight: 800; }
    .single-post-kicker-icon { color: #1d4ed8; font-size: 17px; line-height: 1; }
    .single-post-kicker a { color: #1e3a8a; text-decoration: none; }
    .single-post-kicker a:hover { color: #2563eb; text-decoration: underline; }
    .single-post-hero { margin: 0 0 26px; }
    .single-post-hero .post-title { margin: 0 0 24px; color: #0f172a; font-size: 36px; line-height: 1.14; letter-spacing: -0.75px; font-weight: 850; }
    .single-post-byline { display: flex; align-items: center; gap: 12px; min-width: 0; }
    .single-post-author-avatar { width: 50px; height: 50px; flex: 0 0 50px; border-radius: 50%; object-fit: cover; object-position: center; border: 1px solid #94a3b8; background: #f8fafc; }
    .single-post-byline-copy { min-width: 0; }
    .single-post-author-line { color: #0f172a; font-size: 15.5px; line-height: 1.35; font-weight: 700; }
    .single-post-author-line a { color: #0f172a; text-decoration: none; }
    .single-post-author-line a:hover { color: #2563eb; text-decoration: underline; }
    .single-post-detail-line { display: flex; align-items: center; gap: 7px; flex-wrap: wrap; margin-top: 4px; color: #475569; font-size: 13.5px; line-height: 1.45; }
    .single-post-label-pill { display: inline-flex; align-items: center; max-width: 100%; padding: 3px 9px; border-radius: 999px; background: #2563eb; color: #fff; font-size: 12px; line-height: 1.35; font-weight: 800; text-decoration: none; white-space: normal; }
    .single-post-label-pill:hover { background: #1d4ed8; color: #fff; text-decoration: none; }
    .single-post-share-row { display: flex; align-items: center; gap: 9px; flex-wrap: wrap; margin-top: 22px; }
    .single-post-share-label { margin-right: 1px; color: #0f172a; font-size: 16px; line-height: 1; font-weight: 800; }
    .single-post-share-btn { width: 42px; height: 42px; padding: 0; display: inline-flex; align-items: center; justify-content: center; border: 0; border-radius: 50%; color: #fff; font: inherit; font-size: 15px; font-weight: 850; line-height: 1; cursor: pointer; box-shadow: none; }
    .single-post-share-btn:hover { transform: translateY(-1px); filter: brightness(.96); }
    .single-post-share-btn:focus-visible { outline: 3px solid rgba(37, 99, 235, .28); outline-offset: 3px; }
    .single-post-share-btn.facebook { background: #1877f2; }
    .single-post-share-btn.xshare { background: #050505; }
    .single-post-share-btn.whatsapp { background: #22c55e; font-size: 12px; letter-spacing: -0.2px; }
    .single-post-share-btn.native-share { background: #050505; font-size: 18px; }

    @media (max-width: 700px) {
      .single-post-kicker { margin-bottom: 12px; font-size: 14px; }
      .single-post-hero .post-title { margin-bottom: 20px; font-size: 30px; line-height: 1.17; letter-spacing: -0.5px; }
      .single-post-author-avatar { width: 46px; height: 46px; flex-basis: 46px; }
      .single-post-author-line { font-size: 15px; }
      .single-post-detail-line { font-size: 13px; }
      .single-post-label-pill { font-size: 11.5px; }
      .single-post-share-row { margin-top: 19px; gap: 8px; }
      .single-post-share-btn { width: 40px; height: 40px; }
    }
'''

OLD_VISUAL_BREADCRUMB = '''            <b:if cond='data:view.isPost'>
              <div class='breadcrumb'>
                <a expr:href='data:blog.homepageUrl'>Home</a> <span>›</span>
                <b:if cond='data:post.labels'>
                  <a expr:href='data:post.labels.first.url'><data:post.labels.first.name/></a> <span>›</span>
                </b:if>
                <data:post.title/>
              </div>
            </b:if>
'''

NEW_KICKER = '''            <b:if cond='data:view.isPost and data:post.labels'>
              <div class='single-post-kicker'>
                <span aria-hidden='true' class='single-post-kicker-icon'>&#9889;</span>
                <a expr:href='data:post.labels.first.url'><data:post.labels.first.name/></a>
              </div>
            </b:if>
'''

OLD_SINGLE_HEADER = '''            <b:if cond='data:view.isSingleItem'>
              <!-- Full content only on an individual Post/Page -->
              <h1 class='post-title'><data:post.title/></h1>

              <div class='post-meta'>
                <b:if cond='data:post.author.name'>
                  Author: <b><data:post.author.name/></b>  • 
                </b:if>
                <data:post.date/>
              </div>

'''

NEW_SINGLE_HEADER = '''            <b:if cond='data:view.isSingleItem'>
              <!-- Full content only on an individual Post/Page -->
              <b:if cond='data:view.isPost'>
                <header class='single-post-hero'>
                  <h1 class='post-title'><data:post.title/></h1>

                  <div class='single-post-byline'>
                    <b:if cond='data:post.author.authorPhoto.url'>
                      <img class='single-post-author-avatar'
                           decoding='async'
                           expr:alt='data:post.author.name'
                           expr:src='data:post.author.authorPhoto.url'
                           height='50'
                           width='50'/>
                    </b:if>
                    <div class='single-post-byline-copy'>
                      <div class='single-post-author-line'>
                        By
                        <b:if cond='data:post.author.profileUrl'>
                          <a expr:href='data:post.author.profileUrl' rel='author'><data:post.author.name/></a>
                        <b:else/>
                          <data:post.author.name/>
                        </b:if>
                      </div>
                      <div class='single-post-detail-line'>
                        <span class='single-post-date'>On: <data:post.date/></span>
                        <b:if cond='data:post.labels'>
                          <b:loop values='data:post.labels' var='label'>
                            <a class='single-post-label-pill' expr:href='data:label.url'><data:label.name/></a>
                          </b:loop>
                        </b:if>
                      </div>
                    </div>
                  </div>

                  <div class='single-post-share-row'>
                    <span class='single-post-share-label'>Share:</span>
                    <button aria-label='Share on Facebook' class='single-post-share-btn facebook' data-sia-share='facebook' expr:data-title='data:post.title' expr:data-url='data:post.url' type='button'>f</button>
                    <button aria-label='Share on X' class='single-post-share-btn xshare' data-sia-share='x' expr:data-title='data:post.title' expr:data-url='data:post.url' type='button'>X</button>
                    <button aria-label='Share on WhatsApp' class='single-post-share-btn whatsapp' data-sia-share='whatsapp' expr:data-title='data:post.title' expr:data-url='data:post.url' type='button'>WA</button>
                    <button aria-label='Open device share menu' class='single-post-share-btn native-share native-share-btn' expr:data-title='data:post.title' expr:data-url='data:post.url' type='button'>&#8599;</button>
                  </div>
                </header>
              <b:else/>
                <h1 class='post-title'><data:post.title/></h1>
              </b:if>

'''


def patch_css(text: str) -> str:
    if MARKER in text:
        return text
    anchor = "    /* Post sharing */\n"
    if anchor not in text:
        raise RuntimeError("Single-post header CSS anchor not found")
    return text.replace(anchor, CSS + "\n" + anchor, 1)


def patch_markup(text: str) -> str:
    if "class='single-post-kicker'" not in text:
        if OLD_VISUAL_BREADCRUMB not in text:
            raise RuntimeError("Visual breadcrumb block not found")
        text = text.replace(OLD_VISUAL_BREADCRUMB, NEW_KICKER, 1)

    if "class='single-post-hero'" not in text:
        if OLD_SINGLE_HEADER not in text:
            raise RuntimeError("Single-item header block not found")
        text = text.replace(OLD_SINGLE_HEADER, NEW_SINGLE_HEADER, 1)

    return text


def validate(text: str) -> None:
    required = [
        MARKER,
        "class='single-post-kicker'",
        "class='single-post-hero'",
        "class='single-post-byline'",
        "class='single-post-author-avatar'",
        "class='single-post-label-pill'",
        "class='single-post-share-row'",
        "data-sia-share='facebook'",
        "data-sia-share='x'",
        "data-sia-share='whatsapp'",
        "class='single-post-share-btn native-share native-share-btn'",
        "By\n",
        "On: <data:post.date/>",
    ]
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise RuntimeError("Missing single-post header markers: " + ", ".join(missing))

    if OLD_VISUAL_BREADCRUMB in text:
        raise RuntimeError("Verbose visual breadcrumb is still present")

    if text.count("class='single-post-hero'") != 1:
        raise RuntimeError("Single-post hero must appear exactly once")

    if re.search(r"[\u0900-\u097F]", html.unescape(text)):
        raise RuntimeError("Universal Blogger XML contains Devanagari source text")


def main() -> None:
    text = THEME.read_text(encoding="utf-8")
    text = patch_css(text)
    text = patch_markup(text)
    validate(text)
    THEME.write_text(text, encoding="utf-8")
    ET.parse(THEME)
    print("SIA v0.1 editorial single-post header activated")


if __name__ == "__main__":
    main()
