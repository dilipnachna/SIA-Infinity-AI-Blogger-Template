# Blogger robots guidance for SIA v0.1

The SIA theme sets page-level preview directives in HTML:

```text
max-image-preview:large
max-snippet:-1
max-video-preview:-1
```

Blogger Custom robots.txt is configured separately in Blogger settings. SIA does not rewrite it from the theme.

## Primary Silo warning

Blogger label archives use URLs such as:

```text
/search/label/AI
/search/label/Technology
```

Because the first Blogger label is the SIA Primary Silo, a broad rule such as:

```text
User-agent: *
Disallow: /search
```

can also block crawler access to Primary Silo label pages.

If you intentionally block generic search URLs, keep label paths crawlable. A conservative starting pattern is:

```text
User-agent: *
Disallow: /search
Allow: /search/label/
Allow: /
```

Blogger behavior and search-engine crawling rules can change, so verify the generated robots.txt and important label URLs in your own Search Console setup before relying on a rule globally.

## SIA indexing intent

The framework is designed around these conceptual defaults:

```text
Homepage       index, follow
Posts          index, follow
Static pages   index, follow
Primary labels crawlable
Query search   normally not a target landing page
Archive pages  normally not a target landing page
Error pages    not a target landing page
```

Do not add a theme condition that blindly treats every `/search/...` view as noindex because Blogger label silos live under the same path family.
