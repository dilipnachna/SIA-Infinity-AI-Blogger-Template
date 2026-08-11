#!/usr/bin/env python3
"""Activate SIA v0.1 social sharing and Blogger community discovery UI.

Rules:
- keep the public version at v0.1
- keep the universal Blogger XML English-only
- do not add visitor registration or hidden telemetry
- keep the existing SIA project attribution
- add only public sharing/discovery functionality
- remain idempotent for hourly GitHub Actions runs
- accept either the legacy full share box or the newer editorial share rail
"""
from pathlib import Path
import html
import re
import xml.etree.ElementTree as ET

THEME = Path("theme/SIA-Infinity-AI-Blogger-Template-v0.1.xml")

SIGNATURE = "  <meta content='SIA-Infinity-AI-Blogger-Template-v0.1' name='sia-template'/>\n  <meta content='0.1' name='sia-template-version'/>\n"

CSS_MARKER = "/* SIA Social Sharing + Community v0.1 */"
CSS_BLOCK = """    /* SIA Social Sharing + Community v0.1 */
    .share-btn.linkedin { border-color: #bfdbfe; background: #eff6ff; color: #1e40af; }
    .share-btn.reddit { border-color: #fed7aa; background: #fff7ed; color: #9a3412; }
    .share-btn.pinterest { border-color: #fecaca; background: #fef2f2; color: #991b1b; }
    .share-btn.email { border-color: #ddd6fe; background: #f5f3ff; color: #5b21b6; }
    .share-btn.native-share { border-color: #cbd5e1; background: #fff; color: #0f172a; }
    .sia-community-row { margin-top: 10px; font-size: 13px; line-height: 1.6; }
    .sia-community-row a { font-weight: 700; }
    .sia-community-count { margin-left: 4px; color: #166534; font-weight: 800; }
    .sia-community-separator { color: #94a3b8; padding: 0 6px; }

"""

OLD_SHARE = """                  <div class='post-share-buttons'>
                    <a class='share-btn whatsapp' expr:href='&quot;https://wa.me/?text=&quot; + data:post.title + &quot;%20&quot; + data:post.url' rel='noopener noreferrer' target='_blank'>WhatsApp</a>
                    <a class='share-btn facebook' expr:href='&quot;https://www.facebook.com/sharer/sharer.php?u=&quot; + data:post.url' rel='noopener noreferrer' target='_blank'>Facebook</a>
                    <a class='share-btn xshare' expr:href='&quot;https://twitter.com/intent/tweet?text=&quot; + data:post.title + &quot;&amp;url=&quot; + data:post.url' rel='noopener noreferrer' target='_blank'>X</a>
                    <a class='share-btn telegram' expr:href='&quot;https://t.me/share/url?url=&quot; + data:post.url + &quot;&amp;text=&quot; + data:post.title' rel='noopener noreferrer' target='_blank'>Telegram</a>
                    <button class='share-btn copy-link-btn' expr:data-url='data:post.url' type='button'>🔗 Copy Link</button>
                  </div>"""

NEW_SHARE = """                  <div class='post-share-buttons'>
                    <a aria-label='Share on WhatsApp' class='share-btn whatsapp' expr:href='&quot;https://wa.me/?text=&quot; + data:post.title + &quot;%20&quot; + data:post.url' rel='nofollow noopener noreferrer' target='_blank'>WhatsApp</a>
                    <a aria-label='Share on Facebook' class='share-btn facebook' expr:href='&quot;https://www.facebook.com/sharer/sharer.php?u=&quot; + data:post.url' rel='nofollow noopener noreferrer' target='_blank'>Facebook</a>
                    <a aria-label='Share on X' class='share-btn xshare' expr:href='&quot;https://twitter.com/intent/tweet?text=&quot; + data:post.title + &quot;&amp;url=&quot; + data:post.url' rel='nofollow noopener noreferrer' target='_blank'>X</a>
                    <a aria-label='Share on Telegram' class='share-btn telegram' expr:href='&quot;https://t.me/share/url?url=&quot; + data:post.url + &quot;&amp;text=&quot; + data:post.title' rel='nofollow noopener noreferrer' target='_blank'>Telegram</a>
                    <a aria-label='Share on LinkedIn' class='share-btn linkedin' expr:href='&quot;https://www.linkedin.com/sharing/share-offsite/?url=&quot; + data:post.url' rel='nofollow noopener noreferrer' target='_blank'>LinkedIn</a>
                    <a aria-label='Share on Reddit' class='share-btn reddit' expr:href='&quot;https://www.reddit.com/submit?url=&quot; + data:post.url + &quot;&amp;title=&quot; + data:post.title' rel='nofollow noopener noreferrer' target='_blank'>Reddit</a>
                    <b:if cond='data:post.featuredImage'>
                      <a aria-label='Share on Pinterest' class='share-btn pinterest' expr:href='&quot;https://www.pinterest.com/pin/create/button/?url=&quot; + data:post.url + &quot;&amp;media=&quot; + resizeImage(data:post.featuredImage, 1200, &quot;1200:675&quot;) + &quot;&amp;description=&quot; + data:post.title' rel='nofollow noopener noreferrer' target='_blank'>Pinterest</a>
                    </b:if>
                    <a aria-label='Share by email' class='share-btn email' expr:href='&quot;mailto:?subject=&quot; + data:post.title + &quot;&amp;body=&quot; + data:post.url'>Email</a>
                    <button aria-label='Open device share menu' class='share-btn native-share native-share-btn' expr:data-title='data:post.title' expr:data-url='data:post.url' type='button'>Share</button>
                    <button aria-label='Copy post link' class='share-btn copy-link-btn' expr:data-url='data:post.url' type='button'>Copy Link</button>
                  </div>"""

COMMUNITY_MARKER = "class='sia-community-row'"
COMMUNITY_BLOCK = """      <div class='sia-community-row'>
        <a class='sia-community-link' href='https://sia-infinity.blogspot.com/' id='sia-community-link' referrerpolicy='no-referrer' rel='nofollow noopener noreferrer' target='_blank'>Explore the SIA Blogger Community<span aria-live='polite' class='sia-community-count' id='sia-community-count'></span></a>
        <span aria-hidden='true' class='sia-community-separator'>&#8226;</span>
        <a href='https://github.com/dilipnachna/SIA-Infinity-AI-Blogger-Template' rel='noopener noreferrer' target='_blank'>GitHub</a>
      </div>
"""

OLD_COMMUNITY_LINKS = [
    "<a class='sia-community-link' href='https://sia-infinity.blogspot.com/' rel='noopener noreferrer' target='_blank'>Explore the SIA Blogger Community</a>",
    "<a class='sia-community-link' href='https://sia-infinity.blogspot.com/' rel='nofollow noopener noreferrer' target='_blank'>Explore the SIA Blogger Community</a>",
]
NEW_COMMUNITY_LINK = "<a class='sia-community-link' href='https://sia-infinity.blogspot.com/' id='sia-community-link' referrerpolicy='no-referrer' rel='nofollow noopener noreferrer' target='_blank'>Explore the SIA Blogger Community<span aria-live='polite' class='sia-community-count' id='sia-community-count'></span></a>"

NATIVE_MARKER = "// Share: Native Web Share"
NATIVE_JS = """      // Share: Native Web Share
      document.querySelectorAll(\".native-share-btn\").forEach(function(btn) {
          if (!navigator.share) {
              btn.style.display = \"none\";
              return;
          }
          btn.addEventListener(\"click\", function() {
              navigator.share({
                  title: btn.getAttribute(\"data-title\") || document.title,
                  url: btn.getAttribute(\"data-url\") || window.location.href
              }).catch(function() {});
          });
      });

"""

COMMUNITY_RUNTIME_MARKER = "id='sia-community-runtime'"
COMMUNITY_RUNTIME = """  <script id='sia-community-runtime'>
  //<![CDATA[
  (function() {
    var link = document.getElementById('sia-community-link');
    var countNode = document.getElementById('sia-community-count');
    if (!link || !countNode) return;

    var rawBase = 'https://raw.githubusercontent.com/dilipnachna/SIA-Infinity-AI-Blogger-Template/main/public';
    var manifestUrl = rawBase + '/sia-edge.json';
    var rawRegistryUrl = rawBase + '/community/sia-community.json';
    var cacheKey = 'sia-community-registry-v0.1';
    var cacheTtl = 6 * 60 * 60 * 1000;

    function applyCommunity(data) {
      if (!data || typeof data !== 'object') return;
      var count = Number(data.count || 0);
      if (count > 0) {
        countNode.textContent = ' · ' + count + ' verified blog' + (count === 1 ? '' : 's');
      }
      if (data.href) link.href = data.href;
    }

    function readCache() {
      try {
        var cached = JSON.parse(localStorage.getItem(cacheKey) || 'null');
        if (!cached || !cached.savedAt || Date.now() - cached.savedAt > cacheTtl) return null;
        return cached;
      } catch (e) {
        return null;
      }
    }

    function writeCache(data) {
      try {
        localStorage.setItem(cacheKey, JSON.stringify(data));
      } catch (e) {}
    }

    async function fetchJson(url) {
      var response = await fetch(url, {
        method: 'GET',
        mode: 'cors',
        credentials: 'omit',
        cache: 'no-cache',
        referrerPolicy: 'no-referrer'
      });
      if (!response.ok) throw new Error('community-http-' + response.status);
      return response.json();
    }

    async function loadCommunity() {
      var cached = readCache();
      if (cached) {
        applyCommunity(cached);
        return;
      }

      var edgeBase = '';
      try {
        var manifest = await fetchJson(manifestUrl);
        if (manifest && manifest.cloudflare_base_url) {
          edgeBase = String(manifest.cloudflare_base_url).replace(/\/$/, '');
        }
      } catch (e) {}

      var registry = null;
      var href = '';
      if (edgeBase) {
        try {
          registry = await fetchJson(edgeBase + '/community/sia-community.json');
          href = edgeBase + '/community/index.html';
        } catch (e) {}
      }

      if (!registry) {
        try {
          registry = await fetchJson(rawRegistryUrl);
        } catch (e) {
          return;
        }
      }

      var count = Number(registry && registry.verified_count || 0);
      var data = { savedAt: Date.now(), count: count, href: href };
      applyCommunity(data);
      writeCache(data);
    }

    if ('requestIdleCallback' in window) {
      window.requestIdleCallback(function() { loadCommunity(); }, { timeout: 1800 });
    } else {
      window.setTimeout(loadCommunity, 900);
    }
  })();
  //]]>
  </script>

"""


def patch_theme(text: str) -> str:
    if "name='sia-template'" not in text:
        viewport = "  <meta content='width=device-width, initial-scale=1' name='viewport'/>\n"
        if viewport not in text:
            raise RuntimeError("Viewport marker not found")
        text = text.replace(viewport, viewport + SIGNATURE, 1)

    if CSS_MARKER not in text:
        css_anchor = "    /* Blogger comments */\n"
        if css_anchor not in text:
            raise RuntimeError("Sharing CSS anchor not found")
        text = text.replace(css_anchor, CSS_BLOCK + css_anchor, 1)
    elif ".sia-community-count" not in text:
        text = text.replace(
            "    .sia-community-row a { font-weight: 700; }\n",
            "    .sia-community-row a { font-weight: 700; }\n    .sia-community-count { margin-left: 4px; color: #166534; font-weight: 800; }\n",
            1,
        )

    # Legacy themes may still have the original full share box. Newer SIA
    # themes use the editorial bottom share rail, which is already wired to the
    # same encoded runtime and must not be reconstructed here.
    editorial_share_ready = "class='single-post-bottom-share'" in text
    if "class='share-btn linkedin'" not in text and not editorial_share_ready:
        if OLD_SHARE not in text:
            raise RuntimeError("Existing share block did not match expected v0.1 source")
        text = text.replace(OLD_SHARE, NEW_SHARE, 1)

    if COMMUNITY_MARKER not in text:
        footer_anchor = "      </div>\n    </div>\n  </footer>"
        if footer_anchor not in text:
            raise RuntimeError("Footer anchor not found")
        text = text.replace(
            footer_anchor,
            "      </div>\n" + COMMUNITY_BLOCK + "    </div>\n  </footer>",
            1,
        )

    if "id='sia-community-link'" not in text:
        replaced = False
        for old in OLD_COMMUNITY_LINKS:
            if old in text:
                text = text.replace(old, NEW_COMMUNITY_LINK, 1)
                replaced = True
                break
        if not replaced:
            raise RuntimeError("Existing community link did not match expected v0.1 source")

    if COMMUNITY_RUNTIME_MARKER not in text:
        runtime_anchor = "  </footer>\n\n  <b:if cond='data:view.isPost'>"
        if runtime_anchor not in text:
            raise RuntimeError("Community runtime anchor not found")
        text = text.replace(
            runtime_anchor,
            "  </footer>\n\n" + COMMUNITY_RUNTIME + "  <b:if cond='data:view.isPost'>",
            1,
        )

    if NATIVE_MARKER not in text:
        js_anchor = "      let postBody = document.getElementById(\"post-body-content\");\n"
        if js_anchor not in text:
            raise RuntimeError("Post script anchor not found")
        text = text.replace(js_anchor, NATIVE_JS + js_anchor, 1)

    return text


def main() -> None:
    text = THEME.read_text(encoding="utf-8")
    text = patch_theme(text)

    if re.search(r"[\u0900-\u097F]", html.unescape(text)):
        raise RuntimeError("Universal Blogger XML contains Devanagari source text")

    THEME.write_text(text, encoding="utf-8")
    ET.parse(THEME)

    required = [
        "name='sia-template'",
        "id='sia-community-link'",
        "id='sia-community-count'",
        "id='sia-community-runtime'",
        "Explore the SIA Blogger Community",
        "// Share: Native Web Share",
    ]
    final = THEME.read_text(encoding="utf-8")
    missing = [item for item in required if item not in final]
    if missing:
        raise RuntimeError("Missing social/community markers: " + ", ".join(missing))

    legacy_share_ready = all(
        marker in final
        for marker in (
            "class='share-btn linkedin'",
            "class='share-btn reddit'",
            "class='share-btn pinterest'",
            "class='share-btn native-share native-share-btn'",
        )
    )
    editorial_share_ready = all(
        marker in final
        for marker in (
            "class='single-post-bottom-share'",
            "data-sia-share='facebook'",
            "data-sia-share='x'",
            "data-sia-share='whatsapp'",
            "data-sia-share='telegram'",
            "class='single-post-bottom-share-btn native-share native-share-btn'",
        )
    )
    if not (legacy_share_ready or editorial_share_ready):
        raise RuntimeError("No valid SIA post sharing surface found")

    print("SIA v0.1 social sharing and verified Blogger community UI activated")


if __name__ == "__main__":
    main()
