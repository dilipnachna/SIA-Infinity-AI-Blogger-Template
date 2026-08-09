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
- precomputed symbolic content graph with safe Blogger-feed fallback
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

## Hybrid intelligence runtime

v0.1 now uses a self-contained hybrid runtime:

1. The Blogger XML derives the graph path from the current blog hostname.
2. It requests that blog's precomputed `sia-graph.json` from the public GitHub repository.
3. If the graph exists and contains the current post, the related engine uses precomputed scores and reasons.
4. If the graph is unavailable, invalid, or does not contain the current post, the engine falls back to Blogger JSON feeds.

The browser adapter is embedded inside the official Blogger XML, so the live template does not depend on an externally hosted JavaScript file.

## Precomputed graph pipeline

Main components:

- `generator/generate_graph.py`
- `assets/sia-graph-adapter-v0.1.js`
- `scripts/activate_hybrid_graph.py`
- `.github/workflows/sia-cron.yml`

The workflow runs on schedule, manual dispatch, and relevant source changes. It reads the public Blogger JSON feed, generates the graph, validates the graph and Blogger XML, and commits the current graph back to the repository.

Graph files use a hostname-based layout:

```text
public/graphs/<blog-hostname>/sia-graph.json
```

Example test graph:

```text
public/graphs/dilipnachna.blogspot.com/sia-graph.json
```

This keeps the Blogger theme universal: the current hostname selects its own graph. If a hostname does not yet have a graph, Blogger fallback mode remains available.

## Configure a blog graph

Edit `sia.config.json`:

```json
{
  "blog_url": "https://yourblog.blogspot.com",
  "output": "public/graphs/yourblog.blogspot.com/sia-graph.json"
}
```

Run locally:

```bash
python generator/generate_graph.py --config sia.config.json
```

## GitHub Pages

GitHub Pages is an optional mirror, not a runtime requirement. The workflow detects whether Pages is enabled. If it is enabled, the `public/` directory can also be deployed through Pages; if it is not enabled, the committed Raw GitHub graph remains the primary graph source.

## Current test status

The current test source is `dilipnachna.blogspot.com`. Its graph is generated successfully. With only one published post currently present in the public feed, the graph can validate precomputed mode but cannot yet produce sibling related-post relationships. As more posts are published, scheduled graph refreshes can populate those relationships automatically.

## Version policy

All public components remain **v0.1** until the first stable public release is complete.

## License

MIT
