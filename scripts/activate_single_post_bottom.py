#!/usr/bin/env python3
"""Activate the SIA v0.1 editorial single-post bottom experience.

Inspired by a modern newsroom/article footer:
- compact post-label row
- optional, truth-safe editorial disclosure panel
- large dynamic author card
- full-width social share rail
- existing Primary Silo and related intelligence remain below

The disclosure is hidden by default. A site owner may opt in by setting
window.SIA_CONFIG.editorialDisclosureText (and optionally title/badge). The
universal template never hardcodes an AI-assistance or human-review claim.
"""
from pathlib import Path
import html
import re
import xml.etree.ElementTree as ET

THEME = Path("theme/SIA-Infinity-AI-Blogger-Template-v0.1.xml")
MARKER = "SIA Editorial Single Post Bottom v0.1"
DISCLOSURE_JS_MARKER = "SIA Optional Editorial Disclosure v0.1"

CSS = r'''
    /* SIA Editorial Single Post Bottom v0.1 */
    .single-post-bottom { margin-top: 34px; }
    .single-post-bottom-labels { display: flex; align-items: flex-start; gap: 8px; flex-wrap: wrap; margin: 0 0 28px; color: #172554; font-size: 13.5px; line-height: 1.55; font-weight: 800; }
    .single-post-bottom-label-icon { color: #1e3a8a; line-height: 1.55; }
    .single-post-bottom-labels a { color: #172554; text-decoration: none; }
    .single-post-bottom-labels a:hover { color: #2563eb; text-decoration: underline; }
    .single-post-bottom-label-separator { color: #64748b; }

    .single-post-disclosure { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 16px; margin: 0 0 36px; padding: 18px 20px; border-left: 5px solid #1473e6; border-radius: 11px; background: #f3f7fd; color: #0f172a; }
    .single-post-disclosure[hidden] { display: none !important; }
    .single-post-disclosure-badge { align-self: start; padding: 8px 12px; border-radius: 8px; background: #1473e6; color: #fff; font-size: 12px; line-height: 1.2; font-weight: 850; text-transform: uppercase; box-shadow: 0 2px 5px rgba(20,115,230,.18); }
    .single-post-disclosure-badge:empty { display: none; }
    .single-post-disclosure-title { margin-right: 4px; font-weight: 850; }
    .single-post-disclosure-text { font-size: 15px; line-height: 1.55; }

    .single-post-author-card { display: grid; grid-template-columns: 150px minmax(0, 1fr); gap: 28px; align-items: center; margin: 0 0 34px; padding: 28px 34px; border: 1px solid #dbe1e8; border-radius: 14px; background: #fff; }
    .single-post-author-card.no-avatar { grid-template-columns: 1fr; }
    .single-post-author-card-avatar { width: 124px; height: 124px; justify-self: center; border-radius: 50%; object-fit: cover; object-position: center; border: 1px solid #1e3a8a; background: #f8fafc; }
    .single-post-author-card-copy { min-width: 0; }
    .single-post-author-card-name { margin: 0 0 10px; color: #1f2937; font-size: 24px; line-height: 1.25; font-weight: 850; }
    .single-post-author-card-name a { color: inherit; text-decoration: none; }
    .single-post-author-card-name a:hover { color: #2563eb; text-decoration: underline; }
    .single-post-author-card-bio { margin: 0; color: #1f2937; font-size: 16px; line-height: 1.7; }

    .single-post-bottom-share { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; margin: 0 0 34px; }
    .single-post-bottom-share-btn { min-height: 50px; display: inline-flex; align-items: center; justify-content: center; border: 0; border-radius: 4px; color: #fff; font: inherit; font-size: 17px; line-height: 1; font-weight: 850; cursor: pointer; }
    .single-post-bottom-share-btn:hover { filter: brightness(.95); transform: translateY(-1px); }
    .single-post-bottom-share-btn:focus-visible { outline: 3px solid rgba(37,99,235,.28); outline-offset: 3px; }
    .single-post-bottom-share-btn.facebook { background: #4267a9; }
    .single-post-bottom-share-btn.xshare { background: #050505; }
    .single-post-bottom-share-btn.whatsapp { background: #20c86a; }
    .single-post-bottom-share-btn.telegram { background: #168ac0; }
    .single-post-bottom-share-btn.native-share { background: #050505; }

    @media (max-width: 700px) {
      .single-post-bottom { margin-top: 28px; }
      .single-post-disclosure { grid-template-columns: 1fr; gap: 10px; padding: 16px; }
      .single-post-disclosure-badge { justify-self: start; }
      .single-post-author-card { grid-template-columns: 88px minmax(0, 1fr); gap: 16px; padding: 20px; }
      .single-post-author-card-avatar { width: 78px; height: 78px; }
      .single-post-author-card-name { margin-bottom: 6px; font-size: 20px; }
      .single-post-author-card-bio { font-size: 14.5px; line-height: 1.6; }
      .single-post-bottom-share { grid-template-columns: repeat(5, 1fr); gap: 6px; }
      .single-post-bottom-share-btn { min-height: 44px; font-size: 14px; }
    }
'''

OLD_SHARE_BLOCK = '''              <b:if cond='data:view.isPost'>
                <div class='post-share-box'>
                  <div class='post-share-title'>📤 Share This Post</div>
                  <div class='post-share-buttons'>
                    <button aria-label='Share on WhatsApp' class='share-btn whatsapp' data-sia-share='whatsapp' expr:data-title='data:post.title' expr:data-url='data:post.url' type='button'>WhatsApp</button>
                    <button aria-label='Share on Facebook' class='share-btn facebook' data-sia-share='facebook' expr:data-title='data:post.title' expr:data-url='data:post.url' type='button'>Facebook</button>
                    <button aria-label='Share on X' class='share-btn xshare' data-sia-share='x' expr:data-title='data:post.title' expr:data-url='data:post.url' type='button'>X</button>
                    <button aria-label='Share on Telegram' class='share-btn telegram' data-sia-share='telegram' expr:data-title='data:post.title' expr:data-url='data:post.url' type='button'>Telegram</button>
                    <button aria-label='Share on LinkedIn' class='share-btn linkedin' data-sia-share='linkedin' expr:data-title='data:post.title' expr:data-url='data:post.url' type='button'>LinkedIn</button>
                    <button aria-label='Share on Reddit' class='share-btn reddit' data-sia-share='reddit' expr:data-title='data:post.title' expr:data-url='data:post.url' type='button'>Reddit</button>
                    <b:if cond='data:post.featuredImage'>
                      <button aria-label='Share on Pinterest' class='share-btn pinterest' data-sia-share='pinterest' expr:data-image='resizeImage(data:post.featuredImage, 1200, &quot;1200:675&quot;)' expr:data-title='data:post.title' expr:data-url='data:post.url' type='button'>Pinterest</button>
                    </b:if>
                    <button aria-label='Share by email' class='share-btn email' data-sia-share='email' expr:data-title='data:post.title' expr:data-url='data:post.url' type='button'>Email</button>
                    <button aria-label='Open device share menu' class='share-btn native-share native-share-btn' expr:data-title='data:post.title' expr:data-url='data:post.url' type='button'>Share</button>
                    <button aria-label='Copy post link' class='share-btn copy-link-btn' expr:data-url='data:post.url' type='button'>Copy Link</button>
                  </div>
                  <div class='share-copy-status'>Link copied ✓</div>
                </div>
              </b:if>
'''

OLD_AUTHOR_BLOCK = '''              <div class='author-box'>
                <b:if cond='data:post.author.authorPhoto.url'>
                  <img class='author-avatar' expr:alt='data:post.author.name' expr:src='data:post.author.authorPhoto.url'/>
                </b:if>
                <div class='author-info'>
                  <h3><data:post.author.name/></h3>
                  <b:if cond='data:post.author.aboutMe'>
                    <p><data:post.author.aboutMe/></p>
                  <b:else/>
                    <p>Author of <data:blog.title/>.</p>
                  </b:if>
                </div>
              </div>

'''

NEW_BOTTOM_BLOCK = '''              <b:if cond='data:view.isPost'>
                <div class='single-post-bottom'>
                  <b:if cond='data:post.labels'>
                    <div class='single-post-bottom-labels'>
                      <span aria-hidden='true' class='single-post-bottom-label-icon'>&#128278;</span>
                      <b:loop values='data:post.labels' var='label'>
                        <a expr:href='data:label.url'><data:label.name/></a><b:if cond='not data:label.isLast'><span class='single-post-bottom-label-separator'>,</span></b:if>
                      </b:loop>
                    </div>
                  </b:if>

                  <aside class='single-post-disclosure' hidden='hidden' id='sia-editorial-disclosure'>
                    <div class='single-post-disclosure-badge' id='sia-editorial-disclosure-badge'></div>
                    <div class='single-post-disclosure-text'>
                      <span class='single-post-disclosure-title' id='sia-editorial-disclosure-title'>Editorial Disclosure:</span>
                      <span id='sia-editorial-disclosure-text'></span>
                    </div>
                  </aside>

                  <div expr:class='data:post.author.authorPhoto.url ? &quot;single-post-author-card&quot; : &quot;single-post-author-card no-avatar&quot;'>
                    <b:if cond='data:post.author.authorPhoto.url'>
                      <img class='single-post-author-card-avatar'
                           decoding='async'
                           expr:alt='data:post.author.name'
                           expr:src='data:post.author.authorPhoto.url'
                           height='124'
                           loading='lazy'
                           width='124'/>
                    </b:if>
                    <div class='single-post-author-card-copy'>
                      <h3 class='single-post-author-card-name'>
                        <b:if cond='data:post.author.profileUrl'>
                          <a expr:href='data:post.author.profileUrl' rel='author'><data:post.author.name/></a>
                        <b:else/>
                          <data:post.author.name/>
                        </b:if>
                      </h3>
                      <b:if cond='data:post.author.aboutMe'>
                        <p class='single-post-author-card-bio'><data:post.author.aboutMe/></p>
                      <b:else/>
                        <p class='single-post-author-card-bio'>Author of <data:blog.title/>.</p>
                      </b:if>
                    </div>
                  </div>

                  <div aria-label='Share this article' class='single-post-bottom-share'>
                    <button aria-label='Share on Facebook' class='single-post-bottom-share-btn facebook' data-sia-share='facebook' expr:data-title='data:post.title' expr:data-url='data:post.url' type='button'>f</button>
                    <button aria-label='Share on X' class='single-post-bottom-share-btn xshare' data-sia-share='x' expr:data-title='data:post.title' expr:data-url='data:post.url' type='button'>X</button>
                    <button aria-label='Share on WhatsApp' class='single-post-bottom-share-btn whatsapp' data-sia-share='whatsapp' expr:data-title='data:post.title' expr:data-url='data:post.url' type='button'>WA</button>
                    <button aria-label='Share on Telegram' class='single-post-bottom-share-btn telegram' data-sia-share='telegram' expr:data-title='data:post.title' expr:data-url='data:post.url' type='button'>TG</button>
                    <button aria-label='Open device share menu' class='single-post-bottom-share-btn native-share native-share-btn' expr:data-title='data:post.title' expr:data-url='data:post.url' type='button'>&#8599;</button>
                  </div>
                </div>
              </b:if>
'''

DISCLOSURE_SCRIPT = r'''
  <b:if cond='data:view.isPost'>
    <script>
    //<![CDATA[
    /* SIA Optional Editorial Disclosure v0.1 */
    document.addEventListener('DOMContentLoaded', function() {
      var cfg = window.SIA_CONFIG || {};
      var disclosureText = String(cfg.editorialDisclosureText || '').trim();
      if (!disclosureText) return;

      var box = document.getElementById('sia-editorial-disclosure');
      var text = document.getElementById('sia-editorial-disclosure-text');
      var title = document.getElementById('sia-editorial-disclosure-title');
      var badge = document.getElementById('sia-editorial-disclosure-badge');
      if (!box || !text || !title || !badge) return;

      text.textContent = disclosureText;
      title.textContent = String(cfg.editorialDisclosureTitle || 'Editorial Disclosure:');
      badge.textContent = String(cfg.editorialDisclosureBadge || '').trim();
      box.hidden = false;
    });
    //]]>
    </script>
  </b:if>
'''


def patch_css(text: str) -> str:
    if MARKER in text:
        return text
    anchor = "    /* SIA Publisher-Neutral Ad Zones v0.1 */\n"
    if anchor not in text:
        raise RuntimeError("Single-post bottom CSS anchor not found")
    return text.replace(anchor, CSS + "\n" + anchor, 1)


def patch_markup(text: str) -> str:
    if "class='single-post-bottom'" not in text:
        if OLD_SHARE_BLOCK not in text:
            raise RuntimeError("Existing post share block not found")
        text = text.replace(OLD_SHARE_BLOCK, NEW_BOTTOM_BLOCK, 1)

    if OLD_AUTHOR_BLOCK in text:
        text = text.replace(OLD_AUTHOR_BLOCK, "", 1)
    elif "class='author-box'" in text and "class='single-post-author-card'" in text:
        raise RuntimeError("Legacy author box still present after bottom activation")

    return text


def patch_script(text: str) -> str:
    if DISCLOSURE_JS_MARKER in text:
        return text
    anchor = "</body>"
    if anchor not in text:
        raise RuntimeError("Body closing tag not found")
    return text.replace(anchor, DISCLOSURE_SCRIPT + "\n" + anchor, 1)


def validate(text: str) -> None:
    required = [
        MARKER,
        "class='single-post-bottom'",
        "class='single-post-bottom-labels'",
        "id='sia-editorial-disclosure'",
        "class='single-post-author-card",
        "class='single-post-bottom-share'",
        "data-sia-share='facebook'",
        "data-sia-share='x'",
        "data-sia-share='whatsapp'",
        "data-sia-share='telegram'",
        DISCLOSURE_JS_MARKER,
        "editorialDisclosureText",
    ]
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise RuntimeError("Missing single-post bottom markers: " + ", ".join(missing))

    if OLD_SHARE_BLOCK in text:
        raise RuntimeError("Legacy full post share box is still present")
    if OLD_AUTHOR_BLOCK in text:
        raise RuntimeError("Legacy author box is still present")
    if text.count("id='sia-editorial-disclosure'") != 1:
        raise RuntimeError("Editorial disclosure container must appear exactly once")
    if re.search(r"[\u0900-\u097F]", html.unescape(text)):
        raise RuntimeError("Universal Blogger XML contains Devanagari source text")


def main() -> None:
    text = THEME.read_text(encoding="utf-8")
    text = patch_css(text)
    text = patch_markup(text)
    text = patch_script(text)
    validate(text)
    THEME.write_text(text, encoding="utf-8")
    ET.parse(THEME)
    print("SIA v0.1 editorial single-post bottom activated")


if __name__ == "__main__":
    main()
