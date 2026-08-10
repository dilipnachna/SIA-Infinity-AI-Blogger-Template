# SIA-Infinity Blogger Community v0.1

The SIA-Infinity Blogger Community is a public, verified discovery directory for Blogger / Blogspot sites using the SIA-Infinity AI Blogger Template.

## How a blog becomes eligible

A blog is considered an opt-in community candidate when:

1. the owner uses a public fork of `dilipnachna/SIA-Infinity-AI-Blogger-Template`;
2. the blog URL is enabled in that fork's `sia.blogs.json`; and
3. the live site exposes the SIA v0.1 template signature and Blogger generator metadata.

The canonical repository scans its public fork network hourly. Candidate sites are fetched server-side and only verified installations are published.

## Live template signature

```html
<meta name="sia-template" content="SIA-Infinity-AI-Blogger-Template-v0.1">
<meta name="sia-template-version" content="0.1">
```

The registry also requires the live page to identify Blogger as its generator.

## Published files

```text
public/community/sia-community.json
public/community/index.html
```

The JSON file contains the verified count and public blog directory. The HTML file is the human-readable community page deployed with the same optional Cloudflare static edge used by SIA graphs.

## Footer behavior

Participating SIA themes contain a community link. The browser reads the public registry after initial page rendering and can display the current verified count. It first tries the canonical SIA Cloudflare edge and falls back to Raw GitHub data.

The community count request uses `credentials: omit` and `referrerPolicy: no-referrer`. It does not register the current blog and does not send a visitor identifier to the SIA registry.

Community directory member links use `rel="ugc nofollow"`. The separate SIA template attribution remains the project credit.

## Privacy

The registry does not intentionally collect or store visitor IP addresses, cookies, browser identifiers, page history, email addresses, analytics identifiers, or Google account information.

There is no hidden browser installation beacon. Discovery comes from public GitHub fork configuration, and verification is performed by GitHub Actions against the public live blog.

## Refresh cadence

The canonical `Build SIA Intelligence Graph` workflow runs at minute 17 of every hour and refreshes both SIA intelligence graphs and the verified Blogger community registry. Cloudflare remains optional; Raw GitHub is the fallback source.

## Current limitation

A site that is running an older SIA XML without the public v0.1 signature is not counted until the updated template is installed. This conservative rule prevents unverified sites from entering the directory.

All public components remain v0.1 until the first stable release.
