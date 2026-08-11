#!/usr/bin/env python3
"""Harden SIA v0.1 related-media and Blogger author-profile rendering.

This layer fixes progressive-enhancement gaps without changing the
Fibonacci-KNN relation engine:

1. Related-card images:
   - invalidate pre-image graph caches inside the same public v0.1 line
   - if a precomputed relation still lacks an image, hydrate it from the
     current Primary Silo Blogger feed before rendering
   - if an older archive still exposes no feed thumbnail, recover an image
     from that related post's same-origin HTML during browser idle time

2. Blogger author profile:
   - prefer Blogger's flat post profile fields used by classic Blog widgets
   - if the server-side author photo is unavailable, hydrate the avatar and
     profile URL from the current post's same-origin Blogger JSON feed

No external telemetry, paid API, or fabricated profile data is introduced.
"""
from pathlib import Path
import html
import re
import xml.etree.ElementTree as ET

ADAPTER = Path("assets/sia-graph-adapter-v0.1.js")
THEME = Path("theme/SIA-Infinity-AI-Blogger-Template-v0.1.xml")

MEDIA_MARKER = "SIA Related Media Reliability v0.1"
PAGE_RECOVERY_MARKER = "SIA Related Post Image Recovery v0.1"
AUTHOR_MARKER = "SIA Blogger Author Profile Hydration v0.1"
CACHE_PREFIX = "sia_graph_v01_media2:"

MEDIA_HELPER = r'''
  /* SIA Related Media Reliability v0.1 */
  async function enrichRelatedImages(items) {
    if (!Array.isArray(items) || !items.length) return items || [];
    var missing = items.some(function(item) { return !relatedImageUrl(item && item.image); });
    if (!missing) return items;

    var labels = currentLabels();
    var candidates = [];
    if (labels.length) {
      try {
        candidates = await fetchLabelPosts(labels[0]);
      } catch (e) {}
    }

    if (!candidates.length) {
      try {
        var response = await fetch(
          '/feeds/posts/default?alt=json&max-results=' + cfg.fallbackMaxResults,
          { credentials: 'same-origin' }
        );
        if (response.ok) {
          var data = await response.json();
          var entries = data && data.feed && Array.isArray(data.feed.entry) ? data.feed.entry : [];
          candidates = entries.map(entryToPost);
        }
      } catch (e2) {}
    }

    if (!candidates.length) return items;
    var imagesByUrl = {};
    candidates.forEach(function(post) {
      var key = cleanUrl(post && post.url);
      var image = relatedImageUrl(post && post.image);
      if (key && image && !imagesByUrl[key]) imagesByUrl[key] = image;
    });

    items.forEach(function(item) {
      if (!item || relatedImageUrl(item.image)) return;
      var image = imagesByUrl[cleanUrl(item.url)];
      if (image) item.image = image;
    });
    return items;
  }
'''

PAGE_RECOVERY_HELPER = r'''
  /* SIA Related Post Image Recovery v0.1 */
  async function recoverRelatedImageFromHtml(item) {
    if (!item || relatedImageUrl(item.image) || !item.url) return false;

    try {
      var target = new URL(item.url, window.location.href);
      if (target.origin !== window.location.origin) return false;

      var response = await fetch(target.href, {
        method: 'GET',
        credentials: 'same-origin',
        cache: 'force-cache'
      });
      if (!response.ok) return false;

      var source = await response.text();
      var parsed = new DOMParser().parseFromString(source, 'text/html');
      var metaImage = parsed.querySelector('meta[property="og:image"]');
      var image = metaImage && metaImage.content ? metaImage.content : '';

      if (!image) {
        var node = parsed.querySelector('#sia-featured-image, .post-body img, article img');
        if (node) {
          image = node.getAttribute('src') || node.getAttribute('data-src') || '';
        }
      }

      image = relatedImageUrl(image);
      if (!image) return false;
      item.image = image;
      return true;
    } catch (e) {
      return false;
    }
  }

  function scheduleRelatedImageRecovery(items, mode) {
    var targets = (items || []).slice(0, cfg.maxRelated).filter(function(item) {
      return item && item.url && !relatedImageUrl(item.image);
    });
    if (!targets.length) return;

    var recover = function() {
      Promise.all(targets.map(recoverRelatedImageFromHtml)).then(function(results) {
        var changed = results.some(function(value) { return value === true; });
        if (changed) renderRelated(items, mode);
      }).catch(function() {});
    };

    if ('requestIdleCallback' in window) {
      window.requestIdleCallback(recover, { timeout: 1800 });
    } else {
      window.setTimeout(recover, 1200);
    }
  }
'''

AUTHOR_RUNTIME = r'''
  <!-- SIA Blogger Author Profile Hydration v0.1 -->
  <b:if cond='data:view.isPost'>
    <script id='sia-author-profile-runtime'>
    //<![CDATA[
    (function(window, document) {
      'use strict';

      function textValue(node) {
        return node && node.$t ? String(node.$t).trim() : '';
      }

      function safeImage(value) {
        return String(value || '').trim().replace(/^http:\/\//i, 'https://');
      }

      function addHeaderAvatar(image, name) {
        var byline = document.querySelector('.single-post-byline');
        if (!byline || byline.querySelector('.single-post-author-avatar')) return;
        var copy = byline.querySelector('.single-post-byline-copy');
        var img = document.createElement('img');
        img.className = 'single-post-author-avatar';
        img.src = image;
        img.alt = name || 'Author';
        img.width = 50;
        img.height = 50;
        img.decoding = 'async';
        if (copy) byline.insertBefore(img, copy);
        else byline.insertBefore(img, byline.firstChild);
      }

      function addCardAvatar(image, name) {
        var card = document.querySelector('.single-post-author-card');
        if (!card || card.querySelector('.single-post-author-card-avatar')) return;
        var copy = card.querySelector('.single-post-author-card-copy');
        var img = document.createElement('img');
        img.className = 'single-post-author-card-avatar';
        img.src = image;
        img.alt = name || 'Author';
        img.width = 124;
        img.height = 124;
        img.loading = 'lazy';
        img.decoding = 'async';
        card.classList.remove('no-avatar');
        if (copy) card.insertBefore(img, copy);
        else card.insertBefore(img, card.firstChild);
      }

      function linkAuthor(profileUrl) {
        if (!profileUrl) return;
        var selectors = ['.single-post-author-line', '.single-post-author-card-name'];
        selectors.forEach(function(selector) {
          var box = document.querySelector(selector);
          if (!box || box.querySelector('a')) return;
          var text = String(box.textContent || '').trim();
          var prefix = selector === '.single-post-author-line' && /^By\s+/i.test(text) ? 'By ' : '';
          var name = prefix ? text.replace(/^By\s+/i, '') : text;
          if (!name) return;
          box.textContent = prefix;
          var a = document.createElement('a');
          a.href = profileUrl;
          a.rel = 'author';
          a.textContent = name;
          box.appendChild(a);
        });
      }

      function hydrate() {
        var hero = document.querySelector('.single-post-hero[data-sia-post-id]');
        var card = document.querySelector('.single-post-author-card[data-sia-post-id]');
        var postId = hero ? hero.getAttribute('data-sia-post-id') : (card ? card.getAttribute('data-sia-post-id') : '');
        if (!postId) return;

        var headerHasAvatar = !!document.querySelector('.single-post-author-avatar');
        var cardHasAvatar = !!document.querySelector('.single-post-author-card-avatar');
        if (headerHasAvatar && cardHasAvatar) return;

        fetch('/feeds/posts/default/' + encodeURIComponent(postId) + '?alt=json', {
          credentials: 'same-origin',
          cache: 'no-cache'
        }).then(function(response) {
          if (!response.ok) throw new Error('author-feed-' + response.status);
          return response.json();
        }).then(function(payload) {
          var entry = payload && payload.entry ? payload.entry : null;
          var author = entry && Array.isArray(entry.author) && entry.author.length ? entry.author[0] : null;
          if (!author) return;

          var image = safeImage(author['gd$image'] && author['gd$image'].src);
          var name = textValue(author.name);
          var profileUrl = textValue(author.uri);
          if (image) {
            addHeaderAvatar(image, name);
            addCardAvatar(image, name);
          }
          if (profileUrl) linkAuthor(profileUrl);
        }).catch(function() {
          // Server-rendered Blogger author name remains the fallback.
        });
      }

      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', hydrate, { once: true });
      } else {
        hydrate();
      }
    })(window, document);
    //]]>
    </script>
  </b:if>
'''


def patch_adapter(text: str) -> str:
    text = text.replace("return 'sia_graph_v01:' + url;", f"return '{CACHE_PREFIX}' + url;")

    anchor = "\n  async function boot() {\n"
    if MEDIA_MARKER not in text:
        if anchor not in text:
            raise RuntimeError("Hybrid boot anchor not found")
        text = text.replace(anchor, "\n" + MEDIA_HELPER + anchor, 1)

    if PAGE_RECOVERY_MARKER not in text:
        if anchor not in text:
            raise RuntimeError("Hybrid boot anchor not found for page-image recovery")
        text = text.replace(anchor, "\n" + PAGE_RECOVERY_HELPER + anchor, 1)

    old = "      var items = hydrateGraphRelated(loaded.graph, loaded.current);\n"
    new = "      var items = hydrateGraphRelated(loaded.graph, loaded.current);\n      items = await enrichRelatedImages(items);\n"
    if new not in text:
        if old not in text:
            raise RuntimeError("Precomputed related hydration anchor not found")
        text = text.replace(old, new, 1)

    precomputed_render = "      renderRelated(items, mode);\n      setStatus(\n"
    precomputed_recovery = "      renderRelated(items, mode);\n      scheduleRelatedImageRecovery(items, mode);\n      setStatus(\n"
    if precomputed_recovery not in text:
        if precomputed_render not in text:
            raise RuntimeError("Precomputed related render anchor not found")
        text = text.replace(precomputed_render, precomputed_recovery, 1)

    fallback_render = "      renderRelated(fallback, 'fallback');\n      setStatus('SIA Blogger Fallback Mode', 'fallback');\n"
    fallback_recovery = "      renderRelated(fallback, 'fallback');\n      scheduleRelatedImageRecovery(fallback, 'fallback');\n      setStatus('SIA Blogger Fallback Mode', 'fallback');\n"
    if fallback_recovery not in text:
        if fallback_render not in text:
            raise RuntimeError("Fallback related render anchor not found")
        text = text.replace(fallback_render, fallback_recovery, 1)
    return text


def patch_author_fields(text: str) -> str:
    replacements = {
        "data:post.author.authorPhoto.url": "data:post.authorPhoto.url",
        "data:post.author.profileUrl": "data:post.authorProfileUrl",
        "data:post.author.aboutMe": "data:post.authorAboutMe",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    hero = "<header class='single-post-hero'>"
    hero_new = "<header class='single-post-hero' expr:data-sia-post-id='data:post.id'>"
    if hero_new not in text:
        if hero not in text:
            raise RuntimeError("Single-post hero anchor not found")
        text = text.replace(hero, hero_new, 1)

    card = "<div expr:class='data:post.authorPhoto.url ? &quot;single-post-author-card&quot; : &quot;single-post-author-card no-avatar&quot;'>"
    card_new = "<div expr:class='data:post.authorPhoto.url ? &quot;single-post-author-card&quot; : &quot;single-post-author-card no-avatar&quot;' expr:data-sia-post-id='data:post.id'>"
    if card_new not in text:
        if card not in text:
            raise RuntimeError("Single-post author card anchor not found")
        text = text.replace(card, card_new, 1)
    return text


def patch_theme(text: str) -> str:
    text = patch_adapter(text)
    text = patch_author_fields(text)
    if AUTHOR_MARKER not in text:
        anchor = "\n</body>\n</html>"
        if anchor not in text:
            raise RuntimeError("Theme body closing anchor not found")
        text = text.replace(anchor, "\n" + AUTHOR_RUNTIME + anchor, 1)
    return text


def validate(adapter: str, theme: str) -> None:
    required_adapter = [
        MEDIA_MARKER,
        PAGE_RECOVERY_MARKER,
        CACHE_PREFIX,
        "async function enrichRelatedImages(items)",
        "async function recoverRelatedImageFromHtml(item)",
        "function scheduleRelatedImageRecovery(items, mode)",
        "items = await enrichRelatedImages(items)",
        "scheduleRelatedImageRecovery(items, mode)",
        "scheduleRelatedImageRecovery(fallback, 'fallback')",
        "fetchLabelPosts(labels[0])",
        "target.origin !== window.location.origin",
        "new DOMParser().parseFromString(source, 'text/html')",
    ]
    required_theme = [
        MEDIA_MARKER,
        PAGE_RECOVERY_MARKER,
        CACHE_PREFIX,
        AUTHOR_MARKER,
        "id='sia-author-profile-runtime'",
        "data:post.authorPhoto.url",
        "data:post.authorProfileUrl",
        "data:post.authorAboutMe",
        "expr:data-sia-post-id='data:post.id'",
        "'/feeds/posts/default/' + encodeURIComponent(postId) + '?alt=json'",
        "author['gd$image']",
        "scheduleRelatedImageRecovery(items, mode)",
    ]
    missing = [x for x in required_adapter if x not in adapter]
    missing += [x for x in required_theme if x not in theme]
    if missing:
        raise RuntimeError("Missing media/author reliability markers: " + ", ".join(missing))

    retired = [
        "data:post.author.authorPhoto.url",
        "data:post.author.profileUrl",
        "data:post.author.aboutMe",
        "return 'sia_graph_v01:' + url;",
    ]
    present = [x for x in retired if x in theme]
    if present:
        raise RuntimeError("Retired media/author bindings remain: " + ", ".join(present))

    runtime = theme[theme.index(AUTHOR_MARKER):]
    for forbidden in ("localStorage", "sendBeacon(", "XMLHttpRequest("):
        if forbidden in runtime:
            raise RuntimeError("Author hydration must stay same-origin and telemetry-free: " + forbidden)

    if re.search(r"[\u0900-\u097F]", html.unescape(AUTHOR_RUNTIME)):
        raise RuntimeError("Universal author runtime contains Devanagari source text")


def activate_sources() -> str:
    adapter = patch_adapter(ADAPTER.read_text(encoding="utf-8"))
    ADAPTER.write_text(adapter, encoding="utf-8")
    return adapter


def main() -> None:
    adapter = activate_sources()
    theme = patch_theme(THEME.read_text(encoding="utf-8"))
    validate(adapter, theme)
    THEME.write_text(theme, encoding="utf-8")
    ET.parse(THEME)
    print("SIA v0.1 related-media and Blogger author-profile reliability activated")


if __name__ == "__main__":
    main()
