# SIA Blogger API v3 Integration (v0.1)

SIA can use the official Blogger API v3 as the preferred graph-content source while keeping the public Blogger JSON feed as a zero-credential fallback.

## Source priority

```text
OAuth read-only Blogger API v3
        ↓ unavailable
Public Blogger API key
        ↓ unavailable
Public Blogger JSON feed
```

This integration does **not** upload or modify the Blogger theme. Blogger API v3 has resources for blogs, posts, pages, comments, users and related data, but no Theme/Template resource. Theme XML installation remains a Blogger dashboard action.

## Security model

The universal Blogger XML and browser JavaScript never receive Google credentials. OAuth refresh happens only in the GitHub Actions / generator environment.

Supported environment variables:

- `BLOGGER_CLIENT_ID` — Google OAuth desktop client ID.
- `BLOGGER_CLIENT_SECRET` — optional client secret if Google issued one for the client.
- `BLOGGER_REFRESH_TOKEN` — OAuth refresh token granted with `blogger.readonly`.
- `BLOGGER_API_KEY` — optional public-data API key fallback.
- `BLOGGER_API_MODE` — `auto` (default), `oauth`, `api-key`, `required`, `feed`, or `off`.

Never commit any credential value to the repository.

## Recommended setup: OAuth read-only

1. Create/select a Google Cloud project.
2. Enable **Blogger API v3**.
3. Configure the OAuth consent screen for your account/testing users.
4. Create an OAuth client with application type **Desktop app**.
5. On a trusted local computer, set the client ID (and client secret if present) in your shell.
6. Run:

```bash
python scripts/blogger_oauth_setup.py
```

The helper uses a local loopback redirect, PKCE, `access_type=offline`, and the scope:

```text
https://www.googleapis.com/auth/blogger.readonly
```

After consent, store the printed refresh token as a GitHub Actions secret named `BLOGGER_REFRESH_TOKEN`.

Add these repository Actions secrets as applicable:

```text
BLOGGER_CLIENT_ID
BLOGGER_CLIENT_SECRET
BLOGGER_REFRESH_TOKEN
BLOGGER_API_KEY
```

For the authenticated owner connection, the first three are the normal set. `BLOGGER_API_KEY` is optional.

## GitHub Actions behavior

The workflow uses:

```text
BLOGGER_API_MODE=auto
```

When OAuth credentials are available, the generator refreshes an access token server-side and calls Blogger API v3. If OAuth is not configured but an API key is present, it uses public API requests. If neither is present, generation continues using the existing public Blogger feed.

This fallback behavior keeps forks and fresh installations functional without Google credentials.

## Why API v3 improves SIA graph acquisition

`posts.list` supports full post bodies and image metadata. SIA requests:

```text
fetchBodies=true
fetchImages=true
orderBy=published
```

The normalized record can carry:

- post ID
- canonical Blogger URL
- title
- labels
- published / updated timestamps
- full text
- display image metadata
- author display name
- author profile URL
- author avatar URL

The current v0.1 graph algorithm still uses the same deterministic symbolic/Fibonacci-KNN ranking. Blogger API changes the **content acquisition source**, not the semantic scoring rules.

## Local checks

Inspect which source would be selected:

```bash
python scripts/blogger_api.py --check-env
```

Run the offline integration test:

```bash
python scripts/test_blogger_api.py
```

Generate the configured graph with API-aware fallback:

```bash
python scripts/generate_graph_with_blogger_api.py --config sia.config.json
```

Generate all registered blogs:

```bash
python scripts/generate_all_graphs.py --registry sia.blogs.json --base-config sia.config.json
```

## Strict modes

For CI or local diagnostics, `BLOGGER_API_MODE` may be changed:

- `auto`: API when configured, feed fallback on absence/failure.
- `oauth`: require OAuth credentials and fail if OAuth cannot be used.
- `api-key`: require the public API key.
- `required`: require either OAuth or API-key mode.
- `feed` / `off`: intentionally bypass the API.

Use `auto` for the universal open-source workflow; use `oauth` temporarily when verifying that a newly added OAuth connection is actually working.
