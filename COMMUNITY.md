# SIA-Infinity Blogger Community v0.1

The SIA Blogger Community is an optional discovery directory for public Blogspot sites that use the SIA-Infinity AI Blogger Template. It is not a private blog network, backlink exchange, ranking service, or traffic guarantee.

## Eligibility

A community entry must:

- use an HTTPS `*.blogspot.com` hostname in community v0.1
- be listed in a public SIA repository `sia.blogs.json`
- set `enabled: true`
- set `community: true`
- expose the live SIA template signature
- expose a `sia-community-repository` marker that matches the public repository that opted the hostname in
- remain publicly reachable enough for periodic verification

Using the SIA theme does not automatically enroll a blog. Graph generation and public community membership are separate controls.

## Live proof markers

The normalized theme exposes public, non-secret markers such as:

```html
<meta name="sia-template" content="SIA-Infinity-AI-Blogger-Template-v0.1">
<meta name="sia-template-version" content="0.1">
<meta name="sia-community-repository" content="owner/SIA-Infinity-AI-Blogger-Template">
```

The repository marker is rewritten by GitHub Actions for each fork. The central verifier accepts a candidate only when the live repository marker matches a public repository that explicitly opted that hostname into the community.

## Privacy

The registry does not require a browser heartbeat. It does not intentionally collect or store:

- visitor IP addresses
- visitor IDs
- cookies
- browser fingerprints
- Google account identifiers
- email addresses
- page-view history
- analytics profiles

Candidate blog URLs are read from public repository configuration and verified by GitHub Actions server-side.

The footer count request is read-only, uses `credentials: omit` and `referrerPolicy: no-referrer`, and does not register the current blog.

## Links

Community member links are directory/discovery references and are rendered with `ugc nofollow`. SIA does not automatically inject community member links into articles or create reciprocal cross-blog linking patterns.

## Verification states

- `current`: the blog passed the latest verification run
- `grace`: the blog was previously verified but the latest checks failed; it may remain listed for up to 72 hours to tolerate temporary network or Blogger failures

A blog that no longer qualifies is removed after the grace window.

## Abuse and removal

A blog can be excluded or removed for reasons including:

- malware or deceptive downloads
- phishing or impersonation
- automated spam intended to abuse the directory
- deliberately falsified SIA verification markers
- attempts to use the community as a backlink exchange or ranking-manipulation system
- behavior that creates a material security risk for the directory verifier

Repository maintainers may temporarily disable community verification when a platform-level security issue is being investigated.

## Leave the community

Set the blog entry to:

```json
{
  "url": "https://example.blogspot.com",
  "enabled": true,
  "community": false
}
```

The blog can continue using SIA graphs while opting out of the public directory.

## Published files

```text
public/community/sia-community.json
public/community/index.html
```

The JSON file powers the verified count. The HTML file is the human-readable directory deployed with the same optional Cloudflare static edge used by SIA graphs.

## Version scope

Community verification remains v0.1 until the first stable public release. Custom Blogger domains are intentionally not accepted by the central community verifier in v0.1; the SIA theme and graph runtime can still work on them independently.
