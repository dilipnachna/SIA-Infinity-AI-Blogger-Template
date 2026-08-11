#!/usr/bin/env python3
"""Local desktop OAuth helper for SIA Blogger API v3 read-only access.

Run this script on a trusted local computer, never in GitHub Actions. It opens
Google's consent screen using a loopback redirect and PKCE, then prints the
refresh token once so it can be stored as a GitHub Actions secret.

Required environment:
  BLOGGER_CLIENT_ID
Optional environment:
  BLOGGER_CLIENT_SECRET

The OAuth client should be created as a Google "Desktop app" client.
"""
from __future__ import annotations

import base64
import hashlib
import html
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import secrets
import threading
import urllib.parse
import urllib.request
import webbrowser

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/blogger.readonly"


def pkce_pair():
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


def exchange_code(client_id: str, client_secret: str, code: str, redirect_uri: str, verifier: str) -> dict:
    form = {
        "client_id": client_id,
        "code": code,
        "code_verifier": verifier,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }
    if client_secret:
        form["client_secret"] = client_secret
    request = urllib.request.Request(
        TOKEN_URL,
        data=urllib.parse.urlencode(form).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    client_id = os.getenv("BLOGGER_CLIENT_ID", "").strip()
    client_secret = os.getenv("BLOGGER_CLIENT_SECRET", "").strip()
    if not client_id:
        raise SystemExit("BLOGGER_CLIENT_ID is required")

    state = secrets.token_urlsafe(24)
    verifier, challenge = pkce_pair()
    result = {"code": "", "error": ""}
    done = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed.query)
            incoming_state = (query.get("state") or [""])[0]
            if incoming_state != state:
                result["error"] = "OAuth state mismatch"
            elif query.get("error"):
                result["error"] = str(query["error"][0])
            else:
                result["code"] = str((query.get("code") or [""])[0])
                if not result["code"]:
                    result["error"] = "Authorization code missing"

            body = (
                "<!doctype html><meta charset='utf-8'><title>SIA Blogger OAuth</title>"
                "<h1>SIA Blogger OAuth</h1><p>Authorization received. You can close this tab.</p>"
            )
            encoded = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
            done.set()

        def log_message(self, format, *args):
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    redirect_uri = f"http://127.0.0.1:{port}"

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    authorization_url = AUTH_URL + "?" + urllib.parse.urlencode(params)

    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    print("Opening Google authorization in your browser...")
    print("If the browser does not open, visit this URL locally:")
    print(authorization_url)
    webbrowser.open(authorization_url)
    done.wait(timeout=300)
    server.server_close()

    if result["error"]:
        raise SystemExit("OAuth failed: " + result["error"])
    if not result["code"]:
        raise SystemExit("OAuth timed out before an authorization code was received")

    token = exchange_code(client_id, client_secret, result["code"], redirect_uri, verifier)
    refresh_token = str(token.get("refresh_token") or "").strip()
    if not refresh_token:
        raise SystemExit(
            "Google returned no refresh token. Revoke the existing grant if needed and rerun with prompt=consent."
        )

    print("\nAuthorization complete.")
    print("Store the following value as the GitHub Actions secret BLOGGER_REFRESH_TOKEN.")
    print("Do not commit it to the repository or paste it into public issues/logs.\n")
    print(refresh_token)


if __name__ == "__main__":
    main()
