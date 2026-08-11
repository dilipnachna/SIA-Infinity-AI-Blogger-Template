#!/usr/bin/env python3
"""Small stdlib-only Blogger API v3 client for SIA v0.1.

The client is intentionally read-only. It supports either:

1. OAuth 2.0 refresh-token credentials (preferred for an authenticated owner
   connection), or
2. a Google API key for public Blogger data.

Secrets are read only from environment variables and are never written to the
repository or emitted in logs.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Dict, List, Optional

API_BASE = "https://www.googleapis.com/blogger/v3"
TOKEN_URL = "https://oauth2.googleapis.com/token"
READONLY_SCOPE = "https://www.googleapis.com/auth/blogger.readonly"
USER_AGENT = "SIA-Infinity-Blogger-API/0.1"
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
IMAGE_RE = re.compile(r'<img\b[^>]*\bsrc=["\']([^"\']+)["\']', re.I)


class BloggerAPIError(RuntimeError):
    """Raised when the Blogger API cannot satisfy a requested operation."""


def _clean_text(value: str) -> str:
    return SPACE_RE.sub(" ", html.unescape(TAG_RE.sub(" ", value or ""))).strip()


def _first_image(post: dict) -> str:
    for image in post.get("images") or []:
        url = str((image or {}).get("url") or "").strip()
        if url:
            return html.unescape(url)
    match = IMAGE_RE.search(str(post.get("content") or ""))
    return html.unescape(match.group(1)).strip() if match else ""


def normalize_api_post(post: dict) -> dict:
    """Convert a Blogger API v3 Post resource to the generator raw-post shape."""
    content = str(post.get("content") or "")
    author = post.get("author") or {}
    author_image = author.get("image") or {}
    return {
        "id": str(post.get("id") or ""),
        "title": str(post.get("title") or "").strip(),
        "url": str(post.get("url") or "").strip(),
        "labels": [str(x).strip() for x in (post.get("labels") or []) if str(x).strip()],
        "published": str(post.get("published") or ""),
        "updated": str(post.get("updated") or ""),
        "featured_image": _first_image(post),
        "text": _clean_text(content),
        "author": {
            "id": str(author.get("id") or ""),
            "display_name": str(author.get("displayName") or "").strip(),
            "url": str(author.get("url") or "").strip(),
            "image": str(author_image.get("url") or "").strip(),
        },
        "source": "blogger-api-v3",
    }


@dataclass
class BloggerAPIClient:
    api_key: str = ""
    client_id: str = ""
    client_secret: str = ""
    refresh_token: str = ""
    timeout: int = 30
    retries: int = 3
    _access_token: str = ""
    _access_token_expires_at: float = 0.0

    @classmethod
    def from_env(cls) -> "BloggerAPIClient":
        return cls(
            api_key=os.getenv("BLOGGER_API_KEY", "").strip(),
            client_id=os.getenv("BLOGGER_CLIENT_ID", "").strip(),
            client_secret=os.getenv("BLOGGER_CLIENT_SECRET", "").strip(),
            refresh_token=os.getenv("BLOGGER_REFRESH_TOKEN", "").strip(),
        )

    @property
    def oauth_configured(self) -> bool:
        # Desktop OAuth clients can refresh with client_id + refresh_token;
        # client_secret is accepted when Google issued one but is not required
        # by this integration contract.
        return bool(self.client_id and self.refresh_token)

    @property
    def api_key_configured(self) -> bool:
        return bool(self.api_key)

    @property
    def configured(self) -> bool:
        return self.oauth_configured or self.api_key_configured

    @property
    def credential_mode(self) -> str:
        if self.oauth_configured:
            return "oauth-readonly"
        if self.api_key_configured:
            return "api-key-public"
        return "none"

    def _decode_response(self, response) -> dict:
        raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else {}

    def _urlopen_json(self, request: urllib.request.Request) -> dict:
        last_error: Optional[Exception] = None
        for attempt in range(self.retries):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    return self._decode_response(response)
            except urllib.error.HTTPError as exc:
                last_error = exc
                try:
                    detail = exc.read().decode("utf-8", errors="replace")[:500]
                except Exception:
                    detail = ""
                # Do not retry ordinary credential/permission failures.
                if exc.code in {400, 401, 403, 404}:
                    raise BloggerAPIError(
                        f"Blogger API HTTP {exc.code}: {detail or exc.reason}"
                    ) from exc
            except Exception as exc:  # network/transient errors
                last_error = exc
            if attempt + 1 < self.retries:
                time.sleep(1.25 * (attempt + 1))
        raise BloggerAPIError(f"Blogger API request failed: {last_error}")

    def _refresh_access_token(self) -> str:
        if not self.oauth_configured:
            raise BloggerAPIError("OAuth refresh credentials are not configured")
        if self._access_token and time.time() < self._access_token_expires_at - 60:
            return self._access_token

        form: Dict[str, str] = {
            "client_id": self.client_id,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        }
        if self.client_secret:
            form["client_secret"] = self.client_secret

        request = urllib.request.Request(
            TOKEN_URL,
            data=urllib.parse.urlencode(form).encode("utf-8"),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": USER_AGENT,
            },
            method="POST",
        )
        payload = self._urlopen_json(request)
        token = str(payload.get("access_token") or "").strip()
        if not token:
            raise BloggerAPIError("OAuth token refresh returned no access token")
        expires_in = int(payload.get("expires_in") or 3600)
        self._access_token = token
        self._access_token_expires_at = time.time() + max(60, expires_in)
        return token

    def _request(self, path: str, params: Optional[dict] = None) -> dict:
        if not self.configured:
            raise BloggerAPIError("Blogger API credentials are not configured")

        query = dict(params or {})
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        if self.oauth_configured:
            headers["Authorization"] = "Bearer " + self._refresh_access_token()
        else:
            query["key"] = self.api_key

        url = API_BASE + path
        if query:
            url += "?" + urllib.parse.urlencode(query)
        request = urllib.request.Request(url, headers=headers, method="GET")
        return self._urlopen_json(request)

    def get_blog_by_url(self, blog_url: str) -> dict:
        payload = self._request("/blogs/byurl", {"url": blog_url.rstrip("/") + "/"})
        if not payload.get("id"):
            raise BloggerAPIError("Blogger API did not return a blog id")
        return payload

    def list_posts(self, blog_url: str, max_posts: int) -> List[dict]:
        max_posts = max(0, int(max_posts))
        if max_posts == 0:
            return []
        blog = self.get_blog_by_url(blog_url)
        blog_id = str(blog["id"])
        posts: List[dict] = []
        page_token = ""

        while len(posts) < max_posts:
            params = {
                "fetchBodies": "true",
                "fetchImages": "true",
                "maxResults": min(500, max_posts - len(posts)),
                "orderBy": "published",
            }
            if page_token:
                params["pageToken"] = page_token

            payload = self._request(
                "/blogs/" + urllib.parse.quote(blog_id, safe="") + "/posts",
                params,
            )
            items = payload.get("items") or []
            if not isinstance(items, list):
                raise BloggerAPIError("Blogger API posts response has invalid items")
            posts.extend(normalize_api_post(item) for item in items)
            page_token = str(payload.get("nextPageToken") or "")
            if not page_token or not items:
                break

        return posts[:max_posts]


def describe_environment() -> str:
    client = BloggerAPIClient.from_env()
    if client.oauth_configured:
        return "oauth-readonly"
    if client.api_key_configured:
        return "api-key-public"
    return "feed-fallback"


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect SIA Blogger API v3 configuration.")
    parser.add_argument("--check-env", action="store_true")
    args = parser.parse_args()
    if args.check_env:
        print("SIA Blogger API v3 source mode:", describe_environment())
        return
    parser.print_help()


if __name__ == "__main__":
    main()
