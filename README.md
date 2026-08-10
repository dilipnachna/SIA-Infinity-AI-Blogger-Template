# SIA-Infinity AI Blogger Template v0.1

An open-source, universal Blogger / Blogspot theme and adaptive symbolic intelligence framework.

**Official project site:** https://sia-infinity.blogspot.com/  
**AI system:** https://sia-infinity.com/

## Current v0.1

The official Blogger theme is:

`theme/SIA-Infinity-AI-Blogger-Template-v0.1.xml`

Current v0.1 capabilities include:

- responsive Blogger post cards for desktop and mobile
- page-type-aware heading architecture: blog H1 on feeds, article/page H1 on single items
- dynamic blog title and Blogger meta description
- English-only universal Blogger template UI/source strings
- canonical Blogger permalink strategy
- first Blogger label as the Primary Semantic Silo
- precomputed symbolic content graphs
- adaptive SIA Fibonacci-KNN related/similar-pattern recall
- optional Cloudflare static edge delivery
- Raw GitHub precomputed fallback
- Blogger JSON-feed runtime fallback
- contextual internal linking from graph relationships
- BlogPosting `articleSection` from the Primary Silo
- homepage WebSite and post BreadcrumbList structured data
- breadcrumbs, TOC, author box, encoded sharing and native comments
- responsive featured-image candidates with explicit LCP/CLS hints
- URL-based featured/body-image deduplication
- Popular Posts on feed/archive-style pages
- Open Graph and Twitter/X metadata
- verified SIA Blogspot Community registry without hidden installation telemetry
- JSON schemas and stdlib configuration validation
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

## Adaptive SIA Fibonacci-KNN v0.1

Related articles and similar patterns use a deterministic SIA-specific symbolic nearest-neighbor method. **Fibonacci-KNN is the project name for this implementation; it is not presented as a standard published algorithm with that exact name.**

### 1. Semantic similarity

Pairwise semantic similarity uses these symbolic weights:

```text
Shared named entities    34
Same Primary Silo        21
Title pattern            13
Shared Blogger labels     8
Shared content type       5
Shared facet              3
                         --
Total                    84
```

Each dimension is normalized, the weighted similarity is normalized to `0..100`, and a known incompatible content type receives a conservative penalty.

### 2. Adaptive Fibonacci neighbourhood

The available candidate count is `N`. Recall depth is calculated by:

```text
K(N) = min(N, 55, max(3, FibFloor(sqrt(N))))
```

Examples:

```text
N = 10       -> K = 3
N = 100      -> K = 8
N = 1,000    -> K = 21
N = 10,000   -> K = 55
```

The configured `related_max_k` can lower the cap, but v0.1 never raises it above 55.

### 3. Golden-ratio rank weighting

For the K nearest candidates:

```text
phi = (1 + sqrt(5)) / 2
w_r = phi^(-(r-1)) / sum(phi^(-(j-1)))
recall_score = similarity * w_r
```

The graph retains backward-compatible `score` while also publishing:

```text
similarity
rank
rank_weight
recall_score
distance
reasons
```

`score` remains an alias of semantic similarity during v0.1 so older consumers do not break. `recall_score` is recall evidence, not a claim that a result is true or currently correct.

The browser fallback uses **Fibonacci-KNN Lite** with the signals available from Blogger feeds: Primary Silo, labels and title-token similarity. It applies the same adaptive K and golden-ratio rank decay before the UI displays the top related items.

## Adaptive related configuration

`related_display_limit` and adaptive recall depth are deliberately separate:

```json
{
  "related_display_limit": 6,
  "related_max_k": 55,
  "related_min_similarity": 10
}
```

- `related_display_limit`: how many related items the theme displays
- `related_max_k`: maximum memory/retrieval neighbourhood, capped at 55
- `related_min_similarity`: conservative admission threshold after recall

Legacy `related_limit` and `related_min_score` remain readable during v0.1 for compatibility, but new configs should use the adaptive names.

## Three-level runtime

The v0.1 runtime priority is:

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

When GitHub Actions runs inside a fork, the normalization scripts read `GITHUB_REPOSITORY` and rewrite the embedded Raw GitHub runtime and public community repository marker to that fork.

This allows each user to own their own graph pipeline rather than depending on the original repository for precomputed data.

## Register one or more Blogger blogs

Edit `sia.blogs.json`:

```json
{
  "version": "0.1",
  "blogs": [
    {
      "url": "https://your-first-blog.blogspot.com",
      "enabled": true,
      "community": true
    },
    {
      "url": "https://your-second-blog.blogspot.com",
      "enabled": true,
      "community": false
    }
  ]
}
```

`enabled` controls graph generation. `community` is a separate explicit opt-in for the public SIA Blogger Community.

The hourly workflow creates one graph per enabled hostname:

```text
public/graphs/your-first-blog.blogspot.com/sia-graph.json
public/graphs/your-second-blog.blogspot.com/sia-graph.json
```

The current Blogger hostname automatically selects its own graph.

## SIA Blogger Community v0.1

The community registry is a discovery directory, not an automatic blog-to-blog backlink exchange.

A blog is eligible only when all of these are true:

1. It is listed in a public SIA repository's `sia.blogs.json`.
2. The item has `enabled: true` and `community: true`.
3. The live site is an HTTPS `*.blogspot.com` hostname in community v0.1.
4. The live page identifies Blogger and the SIA template.
5. The live `sia-community-repository` marker matches the repository that opted the hostname in.

The central verifier runs server-side. The theme does not send an installation heartbeat, visitor ID, cookie, browsing history or analytics profile to the registry.

A previously verified site can remain in a short grace state for up to 72 hours after a transient verification failure so an hourly timeout does not make the directory flap. Community member links use `ugc nofollow` discovery semantics.

Custom Blogger domains can still use the SIA theme and graph engine; the public community verifier intentionally limits v0.1 membership verification to Blogspot hostnames while its SSRF surface is kept narrow.

See `COMMUNITY.md` for eligibility, abuse and removal rules.

## Adaptive Blogger theme layer

The hourly normalizer preserves these release-critical rules:

- feed pages use the blog name as H1
- post/static-page views use the article/page title as H1 and render the blog name as branding rather than a competing H1
- the featured post image has explicit `1200x675` dimensions, eager loading, `fetchpriority=high`, and responsive Blogger image candidates
- the first body image is hidden only when its normalized Blogger image URL matches the featured image
- share destinations are assembled with `encodeURIComponent`
- the footer exposes a Blogger Layout widget area rather than assuming `/p/about.html`, `/p/contact.html`, `/p/privacy-policy.html` or `/p/disclaimer.html` exist
- no empty Advertisement placeholder is rendered by default
- robots preview directives allow large image, unlimited snippet and video preview eligibility
- WebSite and BreadcrumbList structured data are server-rendered alongside the existing BlogPosting data

## Graph generation

Main components:

- `generator/generate_graph.py`
- `scripts/generate_all_graphs.py`
- `scripts/activate_fibonacci_knn.py`
- `assets/sia-graph-adapter-v0.1.js`
- `scripts/activate_hybrid_graph.py`
- `scripts/activate_social_community.py`
- `scripts/activate_adaptive_system_v2.py`
- `scripts/build_community_registry.py`
- `scripts/validate_configs.py`
- `.github/workflows/sia-cron.yml`

The workflow runs hourly, by manual dispatch, and after relevant source changes. It normalizes the theme/runtime, validates config, tests exact adaptive Fibonacci-KNN examples and golden-ratio behavior, builds the verified community registry, generates all graphs, performs forensic XML/JSON checks, and then deploys static intelligence to Cloudflare when configured.

## Configuration schemas

Machine-readable schemas are included at:

```text
schemas/sia-config.schema.json
schemas/sia-blogs.schema.json
```

CI also runs a Python-stdlib validator, so no third-party JSON Schema package is required for the repository pipeline.

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
  community/
    index.html
    sia-community.json
  graphs/
    <blog-hostname>/
      sia-graph.json
```

## Install flow for a fork

1. Fork this repository.
2. Edit `sia.blogs.json` and add your Blogger URL or URLs.
3. Set `community: true` only for blogs you explicitly want in the public directory.
4. Run **Build SIA Intelligence Graph** once from GitHub Actions.
5. Copy `theme/SIA-Infinity-AI-Blogger-Template-v0.1.xml` from your fork **after** that normalization run.
6. Install that normalized XML in Blogger.
7. Run the workflow again if you want the community verifier to see the newly installed repository marker promptly.
8. Optional: add Cloudflare repository secrets and run the workflow again.

Without Cloudflare, precomputed graphs still work from Raw GitHub. Without a current graph, Blogger fallback remains available immediately.

## Blogger robots.txt

The theme can set page-level robots preview directives, but Blogger Custom robots.txt is controlled from Blogger settings. Do not broadly block `/search` if you want Primary Silo label URLs under `/search/label/...` to remain crawlable.

See `docs/BLOGGER-ROBOTS.md`.

## Local graph generation

For all registered blogs:

```bash
python scripts/validate_configs.py
python scripts/activate_fibonacci_knn.py
python scripts/generate_all_graphs.py
```

For one manually configured graph, `generator/generate_graph.py` can still be used with `sia.config.json`.

## Version policy

All public components remain **v0.1** until the first stable public release is complete.

## License

MIT
