#!/usr/bin/env python3
"""Activate the SIA v0.1 adaptive Blogger system hardening layer.

This script is deliberately idempotent because GitHub Actions runs it hourly.
It preserves the proven Blog1 loop and only patches stable anchors around it.

Adds:
- page-type-aware H1 architecture
- LCP/CLS featured-image hints and responsive srcset
- URL-based featured/body-image dedupe
- encoded social sharing actions
- dynamic footer widget area instead of assumed /p/... pages
- homepage WebSite and post BreadcrumbList structured data
- richer robots preview directives
- per-fork community repository proof marker
- no default empty advertisement placeholder

Universal Blogger XML source remains English-only.
"""
from pathlib import Path
import html
import os
import re
import xml.etree.ElementTree as ET

THEME = Path("theme/SIA-Infinity-AI-Blogger-Template-v0.1.xml")
REPOSITORY = os.environ.get(
    "GITHUB_REPOSITORY",
    "dilipnachna/SIA-Infinity-AI-Blogger-Template",
).strip()

HEADING_MARKER = "SIA Adaptive Heading Architecture v0.1"
WEBSITE_SCHEMA_MARKER = "SIA WebSite JSON-LD v0.1"
BREADCRUMB_SCHEMA_MARKER = "SIA BreadcrumbList JSON-LD v0.1"
SHARE_JS_MARKER = "Share: Encoded social actions"
DEDUPE_MARKER = "SIA Featured Image URL Dedupe"


def patch_head(text: str) -> str:
    text = text.replace(
        "<meta content='max-image-preview:large' name='robots'/>",
        "<meta content='max-image-preview:large,max-snippet:-1,max-video-preview:-1' name='robots'/>",
        1,
    )

    repo_meta = f"  <meta content='{REPOSITORY}' name='sia-community-repository'/>\n"
    repo_re = re.compile(r"  <meta content='[^']*' name='sia-community-repository'/>\n")
    if repo_re.search(text):
        text = repo_re.sub(repo_meta, text, count=1)
    else:
        anchor = "  <meta content='0.1' name='sia-template-version'/>\n"
        if anchor not in text:
            raise RuntimeError("SIA template version meta anchor not found")
        text = text.replace(anchor, anchor + repo_meta, 1)

    if WEBSITE_SCHEMA_MARKER not in text:
        anchor = "  <b:include data='blog' name='all-head-content'/>\n"
        if anchor not in text:
            raise RuntimeError("Blogger all-head-content anchor not found")
        block = '''  <!-- SIA WebSite JSON-LD v0.1 -->
  <b:if cond='data:view.isHomepage'>
    <script type='application/ld+json'>
    {
      &quot;@context&quot;: &quot;https://schema.org&quot;,
      &quot;@type&quot;: &quot;WebSite&quot;,
      &quot;name&quot;: &quot;<data:blog.title.escaped/>&quot;,
      &quot;url&quot;: &quot;<data:blog.homepageUrl/>&quot;
    }
    </script>
  </b:if>
'''
        text = text.replace(anchor, anchor + "\n" + block, 1)

    return text


def patch_heading_architecture(text: str) -> str:
    if HEADING_MARKER not in text:
        old = '''  <header>
    <h1><a expr:href='data:blog.homepageUrl'><data:blog.title/></a></h1>
    <b:if cond='data:blog.metaDescription'>
'''
        new = '''  <header>
    <!-- SIA Adaptive Heading Architecture v0.1 -->
    <b:if cond='data:view.isSingleItem'>
      <div class='site-title'><a expr:href='data:blog.homepageUrl'><data:blog.title/></a></div>
    <b:else/>
      <h1><a expr:href='data:blog.homepageUrl'><data:blog.title/></a></h1>
    </b:if>
    <b:if cond='data:blog.metaDescription'>
'''
        if old not in text:
            raise RuntimeError("Global header anchor not found")
        text = text.replace(old, new, 1)

    text = text.replace(
        "    header h1 a { color: #0f172a; }\n",
        "    header h1 a { color: #0f172a; }\n"
        "    header .site-title { margin: 0; font-size: 32px; font-weight: 800; letter-spacing: -0.5px; }\n"
        "    header .site-title a { color: #0f172a; }\n",
        1,
    ) if "header .site-title {" not in text else text

    text = text.replace(
        "              <h2 class='post-title'><data:post.title/></h2>",
        "              <h1 class='post-title'><data:post.title/></h1>",
        1,
    )
    return text


def patch_featured_image(text: str) -> str:
    old = '''                  <img expr:alt='data:post.title' expr:src='resizeImage(data:post.featuredImage, 1200, &quot;1200:675&quot;)'/>'''
    new = '''                  <img decoding='async'
                       expr:alt='data:post.title'
                       expr:src='resizeImage(data:post.featuredImage, 1200, &quot;1200:675&quot;)'
                       expr:srcset='resizeImage(data:post.featuredImage, 320, &quot;320:180&quot;) + &quot; 320w, &quot; + resizeImage(data:post.featuredImage, 480, &quot;480:270&quot;) + &quot; 480w, &quot; + resizeImage(data:post.featuredImage, 640, &quot;640:360&quot;) + &quot; 640w, &quot; + resizeImage(data:post.featuredImage, 960, &quot;960:540&quot;) + &quot; 960w, &quot; + resizeImage(data:post.featuredImage, 1200, &quot;1200:675&quot;) + &quot; 1200w&quot;'
                       fetchpriority='high'
                       height='675'
                       id='sia-featured-image'
                       loading='eager'
                       sizes='(max-width: 840px) 100vw, 800px'
                       width='1200'/>'''
    if old in text:
        text = text.replace(old, new, 1)
    elif "id='sia-featured-image'" not in text:
        raise RuntimeError("Featured image anchor not found")

    blind = '''      let bodyImg = document.querySelector("#post-body-content img");
      if(bodyImg) {
          let parentLink = bodyImg.parentNode;
          if(parentLink.tagName === 'A') {
              parentLink.style.display = 'none';
          } else {
              bodyImg.style.display = 'none';
          }
      }
'''
    safe = '''      // SIA Featured Image URL Dedupe
      function normalizeSiaImageUrl(value) {
          if(!value) return "";
          try {
              let raw = String(value).replace(/=w\\d+(?:-h\\d+)?(?:-[^/?#]+)?$/i, "");
              let u = new URL(raw, window.location.href);
              u.hash = "";
              u.search = "";
              u.pathname = u.pathname
                  .replace(/\\/s\\d+(?:-[^/]+)?\\//i, "/")
                  .replace(/\\/w\\d+(?:-h\\d+)?(?:-[^/]+)?\\//i, "/");
              return (u.origin + u.pathname).replace(/\\/+$/, "");
          } catch(e) {
              return String(value).split("?")[0].split("#")[0]
                  .replace(/\\/s\\d+(?:-[^/]+)?\\//i, "/")
                  .replace(/\\/w\\d+(?:-h\\d+)?(?:-[^/]+)?\\//i, "/")
                  .replace(/=w\\d+(?:-h\\d+)?(?:-[^/?#]+)?$/i, "")
                  .replace(/\\/+$/, "");
          }
      }

      let featuredImg = document.getElementById("sia-featured-image");
      let bodyImg = document.querySelector("#post-body-content img");
      if(featuredImg && bodyImg) {
          let featuredKey = normalizeSiaImageUrl(featuredImg.currentSrc || featuredImg.src);
          let bodyKey = normalizeSiaImageUrl(bodyImg.currentSrc || bodyImg.src);
          if(featuredKey && bodyKey && featuredKey === bodyKey) {
              let parentLink = bodyImg.parentElement;
              if(parentLink && parentLink.tagName === "A" && parentLink.children.length === 1 && !parentLink.textContent.trim()) {
                  parentLink.style.display = "none";
              } else {
                  bodyImg.style.display = "none";
              }
          }
      }
'''
    if blind in text:
        text = text.replace(blind, safe, 1)
    elif DEDUPE_MARKER not in text:
        raise RuntimeError("First-image dedupe anchor not found")
    return text


def patch_sharing(text: str) -> str:
    block = '''                  <div class='post-share-buttons'>
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
                  </div>'''

    share_re = re.compile(
        r"                  <div class='post-share-buttons'>.*?                  </div>(?=\n                  <div class='share-copy-status'>)",
        re.S,
    )
    if not share_re.search(text):
        raise RuntimeError("Post sharing block not found")
    text = share_re.sub(block, text, count=1)

    if SHARE_JS_MARKER not in text:
        anchor = "      // Share: Native Web Share\n"
        if anchor not in text:
            raise RuntimeError("Native share JS anchor not found")
        js = '''      // Share: Encoded social actions
      document.querySelectorAll("[data-sia-share]").forEach(function(btn) {
          btn.addEventListener("click", function() {
              let network = btn.getAttribute("data-sia-share") || "";
              let title = btn.getAttribute("data-title") || document.title;
              let url = btn.getAttribute("data-url") || window.location.href;
              let image = btn.getAttribute("data-image") || "";
              let encodedTitle = encodeURIComponent(title);
              let encodedUrl = encodeURIComponent(url);
              let encodedImage = encodeURIComponent(image);
              let target = "";

              if(network === "whatsapp") target = "https://wa.me/?text=" + encodeURIComponent(title + " " + url);
              else if(network === "facebook") target = "https://www.facebook.com/sharer/sharer.php?u=" + encodedUrl;
              else if(network === "x") target = "https://twitter.com/intent/tweet?text=" + encodedTitle + "&url=" + encodedUrl;
              else if(network === "telegram") target = "https://t.me/share/url?url=" + encodedUrl + "&text=" + encodedTitle;
              else if(network === "linkedin") target = "https://www.linkedin.com/sharing/share-offsite/?url=" + encodedUrl;
              else if(network === "reddit") target = "https://www.reddit.com/submit?url=" + encodedUrl + "&title=" + encodedTitle;
              else if(network === "pinterest") target = "https://www.pinterest.com/pin/create/button/?url=" + encodedUrl + "&media=" + encodedImage + "&description=" + encodedTitle;
              else if(network === "email") {
                  window.location.href = "mailto:?subject=" + encodedTitle + "&body=" + encodedUrl;
                  return;
              }

              if(target) {
                  let opened = window.open(target, "_blank", "noopener,noreferrer");
                  if(opened) opened.opener = null;
              }
          });
      });

'''
        text = text.replace(anchor, js + anchor, 1)
    return text


def patch_footer_and_ads(text: str) -> str:
    footer_re = re.compile(
        r"    <div class='footer-links'>\n.*?    </div>\n\n    <div class='footer-credits'>",
        re.S,
    )
    if footer_re.search(text):
        replacement = "    <b:section class='footer-links' id='footer-links' maxwidgets='1' showaddelement='yes'></b:section>\n\n    <div class='footer-credits'>"
        text = footer_re.sub(replacement, text, count=1)
    elif "id='footer-links'" not in text:
        raise RuntimeError("Footer links anchor not found")

    ad_re = re.compile(
        r"\n              <!-- Manual AdSense Placeholder Above Content: posts only -->\n              <b:if cond='data:view\.isPost'>\n                <div class='ad-container'>\n                  <!-- Optional manual ad unit can be placed here -->\n                  Advertisement\n                </div>\n              </b:if>\n",
        re.S,
    )
    text = ad_re.sub("\n", text, count=1)
    return text


def patch_breadcrumb_schema(text: str) -> str:
    if BREADCRUMB_SCHEMA_MARKER in text:
        return text

    schema_marker = "            <!-- ADVANCED BlogPosting JSON-LD SCHEMA -->"
    marker_pos = text.find(schema_marker)
    if marker_pos < 0:
        raise RuntimeError("BlogPosting schema marker not found")
    close = "            </b:if>"
    close_pos = text.find(close, marker_pos)
    if close_pos < 0:
        raise RuntimeError("BlogPosting schema closing anchor not found")
    insert_pos = close_pos + len(close)

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
    text = patch_head(text)
    text = patch_heading_architecture(text)
    text = patch_featured_image(text)
    text = patch_sharing(text)
    text = patch_footer_and_ads(text)
    text = patch_breadcrumb_schema(text)

    if re.search(r"[\u0900-\u097F]", html.unescape(text)):
        raise RuntimeError("Universal Blogger XML contains Devanagari source text")

    THEME.write_text(text, encoding="utf-8")
    ET.parse(THEME)

    required = [
        HEADING_MARKER,
        WEBSITE_SCHEMA_MARKER,
        BREADCRUMB_SCHEMA_MARKER,
        "name='sia-community-repository'",
        "id='sia-featured-image'",
        "fetchpriority='high'",
        "expr:srcset=",
        DEDUPE_MARKER,
        SHARE_JS_MARKER,
        "encodeURIComponent",
        "<h1 class='post-title'><data:post.title/></h1>",
        "id='footer-links'",
        "max-snippet:-1",
    ]
    final = THEME.read_text(encoding="utf-8")
    missing = [marker for marker in required if marker not in final]
    if missing:
        raise RuntimeError("Missing adaptive Blogger markers: " + ", ".join(missing))
    if 'let parentLink = bodyImg.parentNode;' in final:
        raise RuntimeError("Blind first-image hiding is still present")
    if "href='/p/about.html'" in final or "href='/p/privacy-policy.html'" in final:
        raise RuntimeError("Hardcoded footer legal pages are still present")
    if "                  Advertisement\n" in final:
        raise RuntimeError("Empty advertisement placeholder is still present")

    print("SIA v0.1 adaptive Blogger system hardening activated for " + REPOSITORY)


if __name__ == "__main__":
    main()
