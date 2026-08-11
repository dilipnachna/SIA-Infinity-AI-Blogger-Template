# SIA-Infinity Fibonacci Attention Map v0.1

The SIA Attention Map is an optional, privacy-safe local attention diagnostic for Blogger pages.

It is not an ad-click tracker and it does not move, inject, hide, refresh or otherwise control AdSense units.

## Design rule

> Measure attention, never chase clicks.

> Attention may recommend a safe predefined zone; it never chooses the user's click target.

## Default state

The runtime is included in the universal theme but remains inactive unless the publisher explicitly enables it:

```html
<script>
window.SIA_CONFIG = window.SIA_CONFIG || {};
window.SIA_CONFIG.attentionMap = true;
window.SIA_CONFIG.attentionMode = "safe";
</script>
```

Supported modes:

- `safe` — local diagnostics and `sia:attention-update` events only.
- `recommend` — local diagnostics plus a recommendation for an existing SIA ad zone.

Example:

```html
<script>
window.SIA_CONFIG = window.SIA_CONFIG || {};
window.SIA_CONFIG.attentionMap = true;
window.SIA_CONFIG.attentionMode = "recommend";
</script>
```

The configuration must be defined before the theme's attention runtime boots.

## What is measured

Only coarse aggregate buckets are kept in JavaScript memory:

- `goldenTop` — document progress up to approximately 38.2%
- `goldenCenter` — approximately 38.2% to 61.8%
- `goldenBottom` — the remaining lower document region

The current v0.1 prior weights are:

```text
goldenTop    = 5
goldenCenter = 13
goldenBottom = 3
```

The score combines:

```text
interaction count × Fibonacci prior
+ dwell seconds / phi
× golden-ratio recency decay
```

This is an SIA-specific heuristic, not a standardized heatmap algorithm.

## Privacy boundary

The runtime does not:

- assign a visitor ID
- fingerprint the browser
- store raw coordinate histories
- use `localStorage` or `sessionStorage`
- call `fetch`, `sendBeacon` or `XMLHttpRequest`
- transmit attention data to SIA, GitHub, Cloudflare or any analytics endpoint

All state disappears when the page is unloaded.

## AdSense safety boundary

The collector ignores interactions inside or on:

- `.sia-ad-zone`
- `.adsbygoogle`
- iframes
- buttons and form controls
- share buttons
- native-share controls
- copy-link controls
- download links

It therefore does not score ad clicks or interactions on major controls.

The attention runtime never calls the AdSense queue and never inserts/moves an ad element.

## Recommendations

In `recommend` mode the runtime may recommend only an ad section that already exists in the SIA layout:

- `sia-ad-top`
- `sia-ad-bottom`
- `sia-ad-feed`

The recommendation is exposed through the browser event:

```js
window.addEventListener("sia:attention-recommendation", function (event) {
  console.log(event.detail);
});
```

A snapshot is also available locally:

```js
console.log(window.SIAAttention.snapshot());
```

Example detail shape:

```json
{
  "version": "0.1.0",
  "mode": "recommend",
  "hotspot": "goldenCenter",
  "scores": {
    "goldenTop": 5.1,
    "goldenCenter": 18.4,
    "goldenBottom": 2.0
  },
  "signals": 8,
  "interactions": 4,
  "dwellMs": 8000,
  "recommendedSlot": "sia-ad-bottom",
  "autoPlace": false,
  "storage": "memory-only",
  "telemetry": false
}
```

A recommendation is diagnostic information only. The publisher remains responsible for actual ad placement and policy compliance.

## Auto Ads

When Google AdSense Auto Ads is enabled, SIA should remain a UX/attention diagnostic. It should not compete with Auto Ads by dynamically moving or injecting units.

## Version

This feature belongs to SIA-Infinity AI Blogger Template **v0.1**. The public version remains v0.1 until the first stable release.
