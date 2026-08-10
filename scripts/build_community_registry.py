#!/usr/bin/env python3
"""Build the public SIA-Infinity Blogger Community registry v0.1.

Privacy and trust model
-----------------------
- No browser registration beacon and no hidden installation telemetry.
- Candidate blogs come only from public SIA repository `sia.blogs.json` files.
- A candidate must explicitly set `community: true`.
- v0.1 community verification accepts only HTTPS `*.blogspot.com` hosts.
- The live page must expose Blogger + SIA template markers.
- The live `sia-community-repository` marker must match one of the public
  repositories that opted the hostname into the registry.
- A previously verified blog receives a 72-hour grace window on transient
  verification failures to avoid hourly directory flapping.

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
GRACE_HOURS = 72
BLOGSPOT_SUFFIX = ".blogspot.com"


class SiteMetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.sia_template = ""
        self.sia_version = ""
        self.sia_repository = ""
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
        elif name == "sia-community-repository":
            self.sia_repository = content
        elif name == "generator":
            self.generator = content

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title and data.strip():
            self._title_parts.append(data.strip())


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def parse_iso(value: str) -> Optional[dt.datetime]:
    try:
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc)
    except Exception:
        return None


def is_safe_blogspot_host(host: str) -> bool:
    host = (host or "").strip().lower().rstrip(".")
    if not host.endswith(BLOGSPOT_SUFFIX):
        return False
    label = host[: -len(BLOGSPOT_SUFFIX)]
    return bool(label) and "." not in label and re.fullmatch(r"[a-z0-9-]+", label) is not None


def canonical_blog_url(value: str) -> Optional[str]:
    value = (value or "").strip()
    if not value:
        return None
    if not re.match(r"^https?://", value, flags=re.I):
        value = "https://" + value
    try:
        parsed = urllib.parse.urlsplit(value)
        port = parsed.port
    except ValueError:
        return None
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme.lower() not in {"http", "https"}:
        return None
    if port not in (None, 80, 443):
        return None
    if not is_safe_blogspot_host(host):
        return None
    # Community v0.1 always verifies canonical HTTPS Blogspot roots.
    return f"https://{host}"


def hostname_from_url(url: str) -> str:
    return (urllib.parse.urlsplit(url).hostname or "").lower().rstrip(".")


class SafeBlogspotRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects away from HTTPS Blogspot hosts."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = canonical_blog_url(newurl)
        if not target:
            raise urllib.error.HTTPError(newurl, code, "Unsafe redirect target", headers, fp)
        parsed_new = urllib.parse.urlsplit(newurl)
        parsed_target = urllib.parse.urlsplit(target)
        if parsed_new.hostname and parsed_new.hostname.lower() != parsed_target.hostname:
            raise urllib.error.HTTPError(newurl, code, "Unsafe redirect target", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, target + "/")


def request_bytes(url: str, headers: Optional[dict] = None, timeout: int = 20, blogspot_only: bool = False) -> bytes:
    merged = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if headers:
        merged.update(headers)
    request = urllib.request.Request(url, headers=merged)
    opener = urllib.request.build_opener(SafeBlogspotRedirectHandler()) if blogspot_only else urllib.request.build_opener()
    with opener.open(request, timeout=timeout) as response:
        raw = response.read(MAX_HTML_BYTES + 1)
    return raw[:MAX_HTML_BYTES]


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


def list_repository_network(root_repo: str, token: str, max_forks: int) -> List[Tuple[str, str]]:
    headers = github_headers(token)
    root = request_json(f"{GITHUB_API}/repos/{root_repo}", headers=headers)
    repos: List[Tuple[str, str]] = [(root["full_name"], root.get("default_branch") or "main")]
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
    seen, unique = set(), []
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
            if not isinstance(item, dict):
                continue
            if item.get("enabled") is False or item.get("community") is not True:
                continue
            url = canonical_blog_url(str(item.get("url", "")))
            if not url:
                continue
            host = hostname_from_url(url)
            record = by_host.setdefault(host, {"url": url, "sources": []})
            if repo not in record["sources"]:
                record["sources"].append(repo)
    return by_host, registry_count


def decode_html(raw: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="replace")


def verify_site(item: Tuple[str, dict]) -> Tuple[str, Optional[dict]]:
    host, candidate = item
    if not is_safe_blogspot_host(host):
        return host, None
    try:
        raw = request_bytes(
            candidate["url"] + "/",
            headers={"Accept": "text/html,application/xhtml+xml"},
            timeout=20,
            blogspot_only=True,
        )
        parser = SiteMetaParser()
        parser.feed(decode_html(raw))
    except Exception:
        return host, None

    template = parser.sia_template.strip()
    generator = parser.generator.strip().lower()
    repository = parser.sia_repository.strip()
    if not template.startswith(SIA_TEMPLATE_PREFIX):
        return host, None
    if "blogger" not in generator:
        return host, None
    if not repository or repository not in candidate.get("sources", []):
        return host, None

    version = parser.sia_version.strip()
    if not version:
        version = template[len(SIA_TEMPLATE_PREFIX):].strip() or REGISTRY_VERSION

    return host, {
        "hostname": host,
        "url": candidate["url"] + "/",
        "title": (parser.title or host)[:180],
        "template": template,
        "version": version or REGISTRY_VERSION,
        "source_repository": repository,
        "status": "verified",
        "verification_state": "current",
        "consecutive_failures": 0,
    }


def load_previous(path: Path) -> Dict[str, dict]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    blogs = payload.get("blogs") if isinstance(payload, dict) else None
    if not isinstance(blogs, list):
        return {}
    return {
        str(item.get("hostname", "")).lower(): item
        for item in blogs
        if isinstance(item, dict) and item.get("hostname")
    }


def within_grace(record: dict, now: dt.datetime) -> bool:
    last = parse_iso(record.get("last_verified_at", ""))
    if not last:
        return False
    return now - last <= dt.timedelta(hours=GRACE_HOURS)


def build_registry(root_repo: str, output: Path, max_forks: int, workers: int) -> dict:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    now_dt = utc_now()
    now = now_dt.isoformat()
    previous = load_previous(output)
    repositories = list_repository_network(root_repo, token, max_forks=max_forks)
    candidates, source_registry_count = discover_candidates(repositories)

    results: Dict[str, Optional[dict]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        future_map = {executor.submit(verify_site, item): item[0] for item in candidates.items()}
        for future in concurrent.futures.as_completed(future_map):
            host, record = future.result()
            results[host] = record

    listed: List[dict] = []
    current_count = 0
    grace_count = 0
    for host, candidate in candidates.items():
        record = results.get(host)
        old = previous.get(host, {})
        if record:
            record["first_seen"] = old.get("first_seen") or now
            record["last_verified_at"] = now
            listed.append(record)
            current_count += 1
            continue

        if old and old.get("source_repository") in candidate.get("sources", []) and within_grace(old, now_dt):
            kept = dict(old)
            kept["status"] = "verified"
            kept["verification_state"] = "grace"
            kept["consecutive_failures"] = int(old.get("consecutive_failures", 0)) + 1
            listed.append(kept)
            grace_count += 1

    listed.sort(key=lambda item: (str(item.get("title", "")).casefold(), item["hostname"]))
    return {
        "sia": {
            "format": "sia-blogger-community-registry",
            "version": REGISTRY_VERSION,
            "generated_at": now,
            "root_repository": root_repo,
            "mode": "opt-in-repository-bound-blogspot-verification",
            "verification_grace_hours": GRACE_HOURS,
            "privacy": "No visitor telemetry. Membership is explicit in public sia.blogs.json and verified against live repository-bound SIA markers.",
        },
        "verified_count": len(listed),
        "current_verified_count": current_count,
        "grace_verified_count": grace_count,
        "candidate_count": len(candidates),
        "repository_count": len(repositories),
        "source_registry_count": source_registry_count,
        "blogs": listed,
    }


def render_html(registry: dict) -> str:
    blogs = registry.get("blogs", [])
    count = int(registry.get("verified_count", 0))
    current = int(registry.get("current_verified_count", 0))
    generated = html.escape(str(registry.get("sia", {}).get("generated_at", "")))
    cards = []
    for item in blogs:
        title = html.escape(str(item.get("title") or item.get("hostname") or "SIA Blog"))
        host = html.escape(str(item.get("hostname") or ""))
        url = html.escape(str(item.get("url") or ""), quote=True)
        version = html.escape(str(item.get("version") or REGISTRY_VERSION))
        state = str(item.get("verification_state") or "current")
        badge = "Verified" if state == "current" else "Recently verified"
        search = html.escape(f"{title} {host}".lower(), quote=True)
        cards.append(
            f"<article class=\"blog-card\" data-search=\"{search}\">"
            f"<h2><a href=\"{url}\" rel=\"ugc nofollow noopener noreferrer\" target=\"_blank\">{title}</a></h2>"
            f"<p>{host}</p><span>SIA v{version} · {badge}</span></article>"
        )
    cards_html = "\n".join(cards) if cards else (
        "<div class=\"empty\">No verified community blogs are listed yet. "
        "Set <code>community: true</code> in your public SIA fork, run its normalization workflow, "
        "install that fork's normalized SIA theme, and the hourly verifier can add the Blogspot site.</div>"
    )
    return f"""<!doctype html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<meta name=\"robots\" content=\"index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1\">
<title>SIA-Infinity Blogger Community</title>
<meta name=\"description\" content=\"Verified Blogspot sites using the SIA-Infinity AI Blogger Template.\">
<style>
:root{{color-scheme:light dark;font-family:system-ui,-apple-system,BlinkMacSystemFont,\"Segoe UI\",sans-serif}}
body{{margin:0;background:#f8fafc;color:#0f172a}}main{{max-width:980px;margin:auto;padding:48px 20px 72px}}a{{color:#1d4ed8}}
.hero{{padding:28px;border:1px solid #dbeafe;border-radius:18px;background:#fff;box-shadow:0 8px 30px rgba(15,23,42,.06)}}h1{{margin:0 0 10px;font-size:clamp(30px,5vw,48px)}}
.count{{font-size:20px;font-weight:800;color:#166534}}.meta{{color:#64748b;line-height:1.7}}.search{{width:100%;box-sizing:border-box;margin:24px 0 18px;padding:13px 15px;border:1px solid #cbd5e1;border-radius:10px;background:#fff;color:#0f172a;font:inherit}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}}.blog-card{{padding:18px;border:1px solid #e2e8f0;border-radius:14px;background:#fff}}.blog-card h2{{margin:0 0 7px;font-size:18px}}.blog-card p{{margin:0 0 10px;color:#475569;overflow-wrap:anywhere}}.blog-card span{{font-size:12px;font-weight:800;color:#166534}}
.empty{{padding:22px;border:1px dashed #cbd5e1;border-radius:12px;background:#fff;color:#475569}}footer{{margin-top:36px;color:#64748b;font-size:13px;line-height:1.7}}
@media(prefers-color-scheme:dark){{body{{background:#020617;color:#e2e8f0}}.hero,.blog-card,.empty{{background:#0f172a;border-color:#334155}}.meta,.blog-card p,footer{{color:#94a3b8}}.search{{background:#0f172a;color:#e2e8f0;border-color:#475569}}.count,.blog-card span{{color:#86efac}}a{{color:#93c5fd}}}}
</style>
</head>
<body><main><section class=\"hero\">
<h1>SIA-Infinity Blogger Community</h1>
<div class=\"count\">{count} verified SIA blog{'' if count == 1 else 's'}</div>
<p class=\"meta\">{current} verified in the latest run. Membership is explicit, repository-bound, and checked against the live Blogger template. No hidden installation or visitor telemetry is collected.</p>
<input class=\"search\" id=\"community-search\" type=\"search\" placeholder=\"Search verified blogs\" aria-label=\"Search verified blogs\">
<div class=\"grid\" id=\"community-grid\">{cards_html}</div>
</section>
<footer>Updated {generated}. Member links are discovery references and use <code>ugc nofollow</code>. · <a href=\"https://sia-infinity.blogspot.com/\">SIA-Infinity AI Blogger Template</a> · <a href=\"https://github.com/dilipnachna/SIA-Infinity-AI-Blogger-Template\">GitHub</a></footer>
</main><script>(function(){{var input=document.getElementById('community-search');if(!input)return;input.addEventListener('input',function(){{var q=input.value.trim().toLowerCase();document.querySelectorAll('.blog-card').forEach(function(card){{card.hidden=!!q&&(card.getAttribute('data-search')||'').indexOf(q)===-1;}});}});}})();</script></body></html>
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
        f"[SIA Community] {registry['verified_count']} listed / "
        f"{registry['current_verified_count']} current / "
        f"{registry['candidate_count']} candidates from "
        f"{registry['repository_count']} repositories.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
