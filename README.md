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
- English-only template UI/source strings
- canonical Blogger permalink strategy
- primary semantic silo based on the first Blogger label
- same-silo related posts and contextual internal linking
- BlogPosting `articleSection` from the primary silo
- breadcrumbs, TOC, author box, sharing and native comments
- Popular Posts on feed/archive-style pages
- social metadata and image SEO foundations
- optional precomputed symbolic graph generator

## Silo rule in v0.1

The first Blogger label is treated as the **Primary Silo**.

```text
Clean Blogger Permalink
        +
Primary Label / Silo
        +
Same-Silo Internal Links
        +
Breadcrumb
        +
articleSection Schema
```

The theme does not fake or rewrite Blogger permalinks with JavaScript.

## Optional precomputed intelligence

The repository also contains an experimental, fully free symbolic graph pipeline:

- `generator/generate_graph.py`
- `assets/sia-graph-adapter-v0.1.js`
- `.github/workflows/sia-cron.yml`

The generator reads the public Blogger JSON feed and can publish `public/sia-graph.json` through GitHub Pages. No paid AI API, embeddings, vector database, Node.js server, or private runtime is required.

The current stable theme works without this graph. Graph integration is progressive enhancement and must always fall back safely to Blogger-native data.

## Configure the graph generator

Edit `sia.config.json`:

```json
{
  "blog_url": "https://yourblog.blogspot.com",
  "output": "public/sia-graph.json"
}
```

Run locally:

```bash
python generator/generate_graph.py --config sia.config.json
```

## GitHub Pages

The included workflow can generate and deploy:

`public/sia-graph.json`

A typical Pages URL is:

`https://USERNAME.github.io/REPOSITORY/sia-graph.json`

## Version policy

All public components remain **v0.1** until the first stable public release is complete.

## License

MIT
