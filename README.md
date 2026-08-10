# SIA-Infinity AI Blogger Template v0.1

An open-source, universal Blogger / Blogspot theme and symbolic intelligence framework.

**Official project site:** https://sia-infinity.blogspot.com/  
**AI system:** https://sia-infinity.com/

## Current v0.1

The official Blogger theme is:

`theme/SIA-Infinity-AI-Blogger-Template-v0.1.xml`

Current stable capabilities include:

- responsive Blogger post cards for desktop and mobile
- dynamic blog title and Blogger meta description
- English-only Blogger template UI/source strings
- canonical Blogger permalink strategy
- first Blogger label as the Primary Semantic Silo
- precomputed symbolic content graphs
- optional Cloudflare edge delivery
- Raw GitHub precomputed fallback
- Blogger JSON-feed runtime fallback
- contextual internal linking from graph relationships
- BlogPosting `articleSection` from the Primary Silo
- breadcrumbs, TOC, author box, sharing and native comments
- Popular Posts on feed/archive-style pages
- social metadata and image SEO foundations
- no paid AI API, embeddings or vector database required

## Silo rule in v0.1

The first Blogger label is always treated as the **Primary Silo**.

```text
Clean Blogger Permalink
        +
Primary Label / Silo
        +
Precomputed Relationships
        +
Contextual Internal Links
        +
Breadcrumb
        +
articleSection Schema
```

Content types, facets and entity candidates are supporting semantic signals. They do not replace the Primary Silo.

The theme does not fake or rewrite Blogger permalinks with JavaScript.

## Three-level runtime

The v0.1 runtime uses this priority:

```text
Cloudflare Static Edge
        ↓ unavailable / stale / post missing
Raw GitHub Graph
        ↓ unavailable / post missing
Blogger Feed Fallback
```

A valid precomputed graph with zero related posts remains valid precomputed mode. The system does not downgrade just because a new or small blog has no sibling relationship yet.

The browser adapter is embedded inside the official Blogger XML, so the live template does not depend on an externally hosted JavaScript runtime.

## Fork-safe architecture

When the GitHub Action runs inside a fork, `scripts/activate_hybrid_graph.py` reads `GITHUB_REPOSITORY` and rewrites the embedded runtime to that fork's own Raw GitHub path.

This allows each user to own their own graph pipeline instead of depending on the original repository for precomputed data.

## Register one or more Blogger blogs

Edit `sia.blogs.json`:

```json
{
  "version": "0.1",
  "blogs": [
    {
      "url": "https://your-first-blog.blogspot.com",
      "enabled": true
    },
    {
      "url": "https://your-second-blog.blogspot.com",
      "enabled": true
    }
  ]
}
```

The hourly workflow creates one graph per hostname:

```text
public/graphs/your-first-blog.blogspot.com/sia-graph.json
public/graphs/your-second-blog.blogspot.com/sia-graph.json
```

The current Blogger hostname automatically selects its own graph.

## Graph generation

Main components:

- `generator/generate_graph.py`
- `scripts/generate_all_graphs.py`
- `assets/sia-graph-adapter-v0.1.js`
- `scripts/activate_hybrid_graph.py`
- `.github/workflows/sia-cron.yml`

The workflow runs hourly, by manual dispatch, and after relevant source changes. It generates all enabled graphs, validates the JSON and Blogger XML, and commits the current graphs back to the fork.

## Optional Cloudflare edge

SIA v0.1 uses **Cloudflare Workers Static Assets** as an optional static edge layer. The repository contains:

- `wrangler.jsonc`
- `public/_headers`
- `public/sia-edge.json`
- `scripts/update_edge_manifest.py`

Cloudflare is not required. If Cloudflare credentials are absent or an edge request fails, the runtime automatically tries Raw GitHub and then Blogger feeds.

### GitHub repository secrets

To activate Cloudflare deployment, add these two Actions secrets to your fork:

```text
CLOUDFLARE_ACCOUNT_ID
CLOUDFLARE_API_TOKEN
```

Use a Cloudflare API token scoped to the account used for the Worker deployment. Do not commit the token to the repository.

After a successful Wrangler deployment, the workflow stores the returned HTTPS deployment base URL in:

```text
public/sia-edge.json
```

The Blogger runtime discovers that manifest automatically and tries the Cloudflare graph first.

## Cloudflare static asset layout

The same `public/` directory is deployed to Cloudflare:

```text
public/
  _headers
  sia-edge.json
  sia-graph-adapter-v0.1.js
  graphs/
    <blog-hostname>/
      sia-graph.json
```

Graph responses are configured for public CORS and short edge/browser caching so hourly graph updates can become visible without a long client-side cache delay.

## Install flow for a fork

1. Fork this repository.
2. Edit `sia.blogs.json` and add your Blogger URL or URLs.
3. Run **Build SIA Intelligence Graph** once from GitHub Actions.
4. Download or copy `theme/SIA-Infinity-AI-Blogger-Template-v0.1.xml` from your fork after that run.
5. Install that XML in Blogger.
6. Optional: add `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` repository secrets, then run the workflow again.

Without Cloudflare, precomputed graphs still work from Raw GitHub. Without a current graph, Blogger fallback remains available immediately.

## Local graph generation

For all registered blogs:

```bash
python scripts/generate_all_graphs.py
```

For one manually configured graph, `generator/generate_graph.py` can still be used with `sia.config.json`.

## Current test status

The current test registry contains `dilipnachna.blogspot.com`. Its graph generation is working. A blog with only one public post can validate the precomputed pipeline but naturally has no sibling related-post relationship until additional posts exist.

## Version policy

All public components remain **v0.1** until the first stable public release is complete.

## License

MIT
