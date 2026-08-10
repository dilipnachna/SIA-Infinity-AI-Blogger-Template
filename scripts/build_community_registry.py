#!/usr/bin/env python3
"""Build the public SIA-Infinity Blogger Community registry.

The registry is intentionally telemetry-free. It discovers opt-in Blogger sites
from public forks of the canonical SIA template repository, reads each fork's
`sia.blogs.json`, and then verifies the live homepage server-side.

A site is listed only when the live HTML identifies both:
- Blogger as the publishing platform; and
- SIA-Infinity-AI-Blogger-Template-v0.1 as the installed template.

No visitor IP, browser identifier, cookie, analytics identifier, or page history
is collected or stored by this registry builder.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

ROOT_REPO = "dilipnachna/SIA-Infinity-AI-Blogger-Template"
REGISTRY_VERSION = "0.1"
SIA_TEMPLATE_PREFIX = "SIA-Infinity-AI-Blogger-Template-v"
USER_AGENT = "SIA-Infinity-Community-Registry/0.1 (+https://sia-infinity.blogspot.com/)"
GITHUB_API = "https://api.github.com"
MAX_HTML_BYTES = 2_000_000


class SiteMetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.sia_template = ""
        self.sia_version = ""
        self.generator = ""
        self._in_title = False
        self._title_parts: List[str] = []

    @property
    def title(self) -> str:
        return " ".join(" ".join(self._title_parts).split()).strip()

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        attrs_map = {
            str(k).lower(): ("" if v is None else str(v))
            for k, v in attrs
            if k is not None
        }
        if tag == "title":
            self._in_title = True
            return
        if tag != "meta":
            return

        name = attrs_map.get("name", "").strip().lower()
        content = attrs_map.get("content", "").strip()
        if name == "sia-template":
            self.sia_template = content
        elif name == "sia-template-version":
            self.sia_version = content
        elif name == "generator":
            self.generator = content

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title and data.strip():
            self._title_parts.append(data.strip())


def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def request_bytes(url: str, headers: Optional[dict] = None, timeout: int = 20) -> bytes:
    merged = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if headers:
        merged.update(headers)
    request = urllib.request.Request(url, headers=merged)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read(MAX_HTML_BYTES + 1)


def request_json(url: str, headers: Optional[dict] = None, timeout: int = 20):
    raw = request_bytes(url, headers=headers, timeout=timeout)
    return json.loads(raw.decode("utf-8"))


def github_headers(token: str) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def canonical_blog_url(value: str) -> Optional[str]:
    value = (value or "").strip()
    if not value:
        return None
    if not re.match(r"^https?://", value, flags=re.I):
        value = "https://" + value
    try:
        parsed = urllib.parse.urlsplit(value)
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    host = parsed.hostname.lower().rstrip(".")
    port = parsed.port
    netloc = host
    if port and not ((parsed.scheme == "https" and port == 443) or (parsed.scheme == "http" and port == 80)):
        netloc = f"{host}:{port}"
    return urllib.parse.urlunsplit((parsed.scheme.lower(), netloc, "", "", ""))


def hostname_from_url(url: str) -> str:
    return (urllib.parse.urlsplit(url).hostname or "").lower().rstrip(".")


def list_repository_network(root_repo: str, token: str, max_forks: int) -> List[Tuple[str, str]]:
    headers = github_headers(token)
    root = request_json(f"{GITHUB_API}/repos/{root_repo}", headers=headers)
    repos: List[Tuple[str, str]] = [
        (root["full_name"], root.get("default_branch") or "main")
    ]

    page = 1
    while len(repos) - 1 < max_forks:
        per_page = min(100, max_forks - (len(repos) - 1))
        if per_page <= 0:
            break
        url = f"{GITHUB_API}/repos/{root_repo}/forks?per_page={per_page}&page={page}&sort=newest"
        items = request_json(url, headers=headers)
        if not items:
            break
        for item in items:
            full_name = item.get("full_name")
            if full_name:
                repos.append((full_name, item.get("default_branch") or "main"))
        if len(items) < per_page:
            break
        page += 1

    seen = set()
    unique = []
    for item in repos:
        if item[0] not in seen:
            seen.add(item[0])
            unique.append(item)
    return unique


def fetch_fork_registry(repo: str, branch: str) -> Optional[dict]:
    branch_q = urllib.parse.quote(branch, safe="")
    raw_url = f"https://raw.githubusercontent.com/{repo}/{branch_q}/sia.blogs.json"
    try:
        return request_json(raw_url, timeout=15)
    except Exception:
        return None


def discover_candidates(repositories: Iterable[Tuple[str, str]]) -> Tuple[Dict[str, dict], int]:
    by_host: Dict[str, dict] = {}
    registry_count = 0

    for repo, branch in repositories:
        payload = fetch_fork_registry(repo, branch)
        if not isinstance(payload, dict):
            continue
        blogs = payload.get("blogs")
        if not isinstance(blogs, list):
            continue
        registry_count += 1

        for item in blogs:
            if not isinstance(item, dict) or item.get("enabled") is False:
                continue
            url = canonical_blog_url(str(item.get("url", "")))
            if not url:
                continue
            host = hostname_from_url(url)
            if not host:
                continue
            record = by_host.setdefault(host, {"url": url, "sources": []})
            if repo not in record["sources"]:
                record["sources"].append(repo)
            # Prefer HTTPS when the same hostname appears more than once.
            if url.startswith("https://"):
                record["url"] = url

    return by_host, registry_count


def decode_html(raw: bytes) -> str:
    if len(raw) > MAX_HTML_BYTES:
        raw = raw[:MAX_HTML_BYTES]
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="replace")


def verify_site(item: Tuple[str, dict]) -> Tuple[str, Optional[dict]]:
    host, candidate = item
    url = candidate["url"]
    try:
        raw = request_bytes(
            url + "/",
            headers={"Accept": "text/html,application/xhtml+xml"},
            timeout=20,
        )
        parser = SiteMetaParser()
        parser.feed(decode_html(raw))
    except Exception:
        return host, None

    template = parser.sia_template.strip()
    generator = parser.generator.strip().lower()
    if not template.startswith(SIA_TEMPLATE_PREFIX):
        return host, None
    if "blogger" not in generator:
        return host, None

    version = parser.sia_version.strip()
    if not version and template.startswith(SIA_TEMPLATE_PREFIX):
        version = template[len(SIA_TEMPLATE_PREFIX):].strip() or REGISTRY_VERSION

    title = parser.title or host
    return host, {
        "hostname": host,
        "url": url + "/",
        "title": title[:180],
        "template": template,
        "version": version or REGISTRY_VERSION,
    }


def load_previous(path: Path) -> Dict[str, dict]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    posts = payload.get("blogs") if isinstance(payload, dict) else None
    if not isinstance(posts, list):
        return {}
    return {
        str(item.get("hostname", "")).lower(): item
        for item in posts
        if isinstance(item, dict) and item.get("hostname")
    }


def build_registry(root_repo: str, output: Path, max_forks: int, workers: int) -> dict:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    now = utc_now_iso()
    previous = load_previous(output)

    repositories = list_repository_network(root_repo, token, max_forks=max_forks)
    candidates, source_registry_count = discover_candidates(repositories)

    verified: List[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = [executor.submit(verify_site, item) for item in candidates.items()]
        for future in concurrent.futures.as_completed(futures):
            host, record = future.result()
            if not record:
                continue
            old = previous.get(host, {})
            record["first_seen"] = old.get("first_seen") or now
            record["last_verified_at"] = now
            verified.append(record)

    verified.sort(key=lambda item: (item["title"].casefold(), item["hostname"]))

    return {
        "sia": {
            "format": "sia-blogger-community-registry",
            "version": REGISTRY_VERSION,
            "generated_at": now,
            "root_repository": root_repo,
            "mode": "verified-public-fork-discovery",
            "privacy": "No visitor telemetry. Candidate blogs come from public sia.blogs.json registries and are verified server-side.",
        },
        "verified_count": len(verified),
        "candidate_count": len(candidates),
        "repository_count": len(repositories),
        "source_registry_count": source_registry_count,
        "blogs": verified,
    }


def render_html(registry: dict) -> str:
    blogs = registry.get("blogs", [])
    count = int(registry.get("verified_count", 0))
    generated = html.escape(str(registry.get("sia", {}).get("generated_at", "")))

    cards = []
    for item in blogs:
        title = html.escape(str(item.get("title") or item.get("hostname") or "SIA Blog"))
        host = html.escape(str(item.get("hostname") or ""))
        url = html.escape(str(item.get("url") or ""), quote=True)
        version = html.escape(str(item.get("version") or REGISTRY_VERSION))
        search = html.escape(f"{title} {host}".lower(), quote=True)
        cards.append(
            f"<article class=\"blog-card\" data-search=\"{search}\">"
            f"<h2><a href=\"{url}\" rel=\"ugc nofollow noopener noreferrer\" target=\"_blank\">{title}</a></h2>"
            f"<p>{host}</p><span>SIA v{version} · Verified</span></article>"
        )

    cards_html = "\n".join(cards) if cards else (
        "<div class=\"empty\">No verified community blogs are listed yet. "
        "Install SIA from a public fork, add your blog to <code>sia.blogs.json</code>, "
        "and the hourly verifier can add it after the live signature is detected.</div>"
    )

    return f"""<!doctype html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<meta name=\"robots\" content=\"index,follow,max-image-preview:large\">
<title>SIA-Infinity Blogger Community</title>
<meta name=\"description\" content=\"Verified Blogger and Blogspot sites using the SIA-Infinity AI Blogger Template.\">
<style>
:root{{color-scheme:light dark;font-family:system-ui,-apple-system,BlinkMacSystemFont,\"Segoe UI\",sans-serif}}
body{{margin:0;background:#f8fafc;color:#0f172a}}main{{max-width:980px;margin:auto;padding:48px 20px 72px}}
a{{color:#1d4ed8}}.hero{{padding:28px;border:1px solid #dbeafe;border-radius:18px;background:#fff;box-shadow:0 8px 30px rgba(15,23,42,.06)}}
h1{{margin:0 0 10px;font-size:clamp(30px,5vw,48px)}}.count{{font-size:20px;font-weight:800;color:#166534}}.meta{{color:#64748b;line-height:1.7}}
.search{{width:100%;box-sizing:border-box;margin:24px 0 18px;padding:13px 15px;border:1px solid #cbd5e1;border-radius:10px;background:#fff;color:#0f172a;font:inherit}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}}.blog-card{{padding:18px;border:1px solid #e2e8f0;border-radius:14px;background:#fff}}
.blog-card h2{{margin:0 0 7px;font-size:18px}}.blog-card p{{margin:0 0 10px;color:#475569;overflow-wrap:anywhere}}.blog-card span{{font-size:12px;font-weight:800;color:#166534}}
.empty{{padding:22px;border:1px dashed #cbd5e1;border-radius:12px;background:#fff;color:#475569}}footer{{margin-top:36px;color:#64748b;font-size:13px;line-height:1.7}}
@media(prefers-color-scheme:dark){{body{{background:#020617;color:#e2e8f0}}.hero,.blog-card,.empty{{background:#0f172a;border-color:#334155}}.meta,.blog-card p,footer{{color:#94a3b8}}.search{{background:#0f172a;color:#e2e8f0;border-color:#475569}}.count,.blog-card span{{color:#86efac}}a{{color:#93c5fd}}}}
</style>
</head>
<body>
<main>
<section class=\"hero\">
<h1>SIA-Infinity Blogger Community</h1>
<div class=\"count\">{count} verified SIA blog{'' if count == 1 else 's'}</div>
<p class=\"meta\">This directory is built from public SIA repository registries and verified against each live Blogger site. It does not collect visitor analytics or hidden installation telemetry.</p>
<input class=\"search\" id=\"community-search\" type=\"search\" placeholder=\"Search verified blogs\" aria-label=\"Search verified blogs\">
<div class=\"grid\" id=\"community-grid\">{cards_html}</div>
</section>
<footer>Updated {generated}. Community links are discovery references and use <code>ugc nofollow</code>. · <a href=\"https://sia-infinity.blogspot.com/\">SIA-Infinity AI Blogger Template</a> · <a href=\"https://github.com/dilipnachna/SIA-Infinity-AI-Blogger-Template\">GitHub</a></footer>
</main>
<script>
(function(){{
  var input=document.getElementById('community-search');
  if(!input)return;
  input.addEventListener('input',function(){{
    var q=input.value.trim().toLowerCase();
    document.querySelectorAll('.blog-card').forEach(function(card){{
      card.hidden=!!q && (card.getAttribute('data-search')||'').indexOf(q)===-1;
    }});
  }});
}})();
</script>
</body>
</html>
"""


def parse_args():
    parser = argparse.ArgumentParser(description="Build verified SIA Blogger community registry")
    parser.add_argument("--root-repo", default=ROOT_REPO)
    parser.add_argument("--output", default="public/community/sia-community.json")
    parser.add_argument("--html-output", default="public/community/index.html")
    parser.add_argument("--max-forks", type=int, default=5000)
    parser.add_argument("--workers", type=int, default=12)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = Path(args.output)
    html_output = Path(args.html_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    html_output.parent.mkdir(parents=True, exist_ok=True)

    registry = build_registry(
        root_repo=args.root_repo,
        output=output,
        max_forks=max(0, args.max_forks),
        workers=max(1, args.workers),
    )
    output.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    html_output.write_text(render_html(registry), encoding="utf-8")

    print(
        f"[SIA Community] {registry['verified_count']} verified / "
        f"{registry['candidate_count']} candidates from "
        f"{registry['repository_count']} repositories.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
