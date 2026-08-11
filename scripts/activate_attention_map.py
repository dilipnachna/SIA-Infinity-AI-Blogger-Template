#!/usr/bin/env python3
"""Activate the SIA v0.1 privacy-safe Fibonacci Attention Map.

This runtime measures coarse, in-memory attention signals only. It never stores
raw coordinates, never reads or scores ad clicks, never transmits telemetry and
never moves/injects AdSense units. It can only recommend one of the predefined
publisher-neutral SIA ad zones.

The feature is opt-in through window.SIA_CONFIG.attentionMap = true.
Modes:
- safe: local diagnostics/events only
- recommend: local diagnostics plus a safe predefined-slot recommendation
"""
from pathlib import Path
import html
import re
import xml.etree.ElementTree as ET

THEME = Path("theme/SIA-Infinity-AI-Blogger-Template-v0.1.xml")
MARKER = "SIA Fibonacci Attention Map v0.1"
META_VALUE = "privacy-safe-local-recommendation-v0.1"

RUNTIME = r'''  <!-- SIA Fibonacci Attention Map v0.1 -->
  <meta content='privacy-safe-local-recommendation-v0.1' name='sia-attention-map'/>
  <script id='sia-attention-map-runtime'>
  //<![CDATA[
  (function(window, document) {
    'use strict';

    var PHI = 1.61803398875;
    var FIB_PRIOR = {
      goldenTop: 5,
      goldenCenter: 13,
      goldenBottom: 3
    };
    var SAMPLE_MS = 2000;
    var ACTIVE_WINDOW_MS = 15000;
    var MIN_SIGNALS = 3;
    var EXCLUDED_SELECTOR = [
      '.sia-ad-zone',
      '.adsbygoogle',
      'iframe',
      'a',
      'button',
      'input',
      'textarea',
      'select',
      'option',
      '[role="button"]',
      '[contenteditable="true"]',
      '.single-post-share-row',
      '.single-post-bottom-share',
      '.post-share-box',
      '.share-btn',
      '.native-share-btn',
      '.copy-link-btn'
    ].join(',');

    var config = window.SIA_CONFIG || {};
    var enabled = config.attentionMap === true;
    var mode = config.attentionMode === 'recommend' ? 'recommend' : 'safe';
    var started = false;
    var intervalId = null;
    var lastActivityAt = 0;
    var state = {
      goldenTop: { interactions: 0, dwellMs: 0, lastAt: 0 },
      goldenCenter: { interactions: 0, dwellMs: 0, lastAt: 0 },
      goldenBottom: { interactions: 0, dwellMs: 0, lastAt: 0 }
    };

    function documentHeight() {
      var root = document.documentElement;
      var body = document.body;
      return Math.max(
        root ? root.scrollHeight : 0,
        root ? root.offsetHeight : 0,
        body ? body.scrollHeight : 0,
        body ? body.offsetHeight : 0,
        window.innerHeight || 1
      );
    }

    function zoneForDocumentY(documentY) {
      var normalized = Math.max(0, Math.min(1, documentY / Math.max(1, documentHeight())));
      if (normalized <= (1 / (PHI * PHI))) return 'goldenTop';
      if (normalized <= (1 / PHI)) return 'goldenCenter';
      return 'goldenBottom';
    }

    function viewportCenterZone() {
      var scrollY = window.pageYOffset || document.documentElement.scrollTop || 0;
      var centerY = scrollY + ((window.innerHeight || 1) / 2);
      return zoneForDocumentY(centerY);
    }

    function isEligibleTarget(target) {
      if (!target || !target.closest) return false;
      if (target.closest(EXCLUDED_SELECTOR)) return false;
      return !!target.closest('#post-body-content, .single-post-hero, .single-post-bottom, .feed-card-layout');
    }

    function touchZone(zone, interactionDelta, dwellDelta) {
      var bucket = state[zone];
      if (!bucket) return;
      bucket.interactions += interactionDelta || 0;
      bucket.dwellMs += dwellDelta || 0;
      bucket.lastAt = Date.now();
    }

    function scoreBucket(zone, now) {
      var bucket = state[zone];
      var dwellSeconds = bucket.dwellMs / 1000;
      var base = (bucket.interactions * FIB_PRIOR[zone]) + (dwellSeconds / PHI);
      if (!bucket.lastAt || !base) return 0;
      var ageFiveMinuteUnits = Math.max(0, now - bucket.lastAt) / 300000;
      var recency = Math.pow(PHI, -ageFiveMinuteUnits);
      return Math.round(base * recency * 1000) / 1000;
    }

    function existingAdSlots() {
      return ['sia-ad-top', 'sia-ad-bottom', 'sia-ad-feed'].filter(function(id) {
        return !!document.getElementById(id);
      });
    }

    function recommendSlot(hotspot) {
      var slots = existingAdSlots();
      if (!slots.length) return null;
      if (slots.indexOf('sia-ad-feed') !== -1) return 'sia-ad-feed';
      if (hotspot === 'goldenTop' && slots.indexOf('sia-ad-top') !== -1) return 'sia-ad-top';
      if (slots.indexOf('sia-ad-bottom') !== -1) return 'sia-ad-bottom';
      return slots[0];
    }

    function snapshot() {
      var now = Date.now();
      var scores = {
        goldenTop: scoreBucket('goldenTop', now),
        goldenCenter: scoreBucket('goldenCenter', now),
        goldenBottom: scoreBucket('goldenBottom', now)
      };
      var hotspot = Object.keys(scores).reduce(function(best, key) {
        return scores[key] > scores[best] ? key : best;
      }, 'goldenTop');
      var totalInteractions = state.goldenTop.interactions + state.goldenCenter.interactions + state.goldenBottom.interactions;
      var totalDwellMs = state.goldenTop.dwellMs + state.goldenCenter.dwellMs + state.goldenBottom.dwellMs;
      var signalCount = totalInteractions + Math.floor(totalDwellMs / SAMPLE_MS);
      return {
        version: '0.1.0',
        mode: mode,
        hotspot: hotspot,
        scores: scores,
        signals: signalCount,
        interactions: totalInteractions,
        dwellMs: totalDwellMs,
        recommendedSlot: mode === 'recommend' && signalCount >= MIN_SIGNALS ? recommendSlot(hotspot) : null,
        autoPlace: false,
        storage: 'memory-only',
        telemetry: false
      };
    }

    function publish() {
      var detail = snapshot();
      window.dispatchEvent(new CustomEvent('sia:attention-update', { detail: detail }));
      if (detail.recommendedSlot) {
        window.dispatchEvent(new CustomEvent('sia:attention-recommendation', { detail: detail }));
      }
      return detail;
    }

    function onPointerDown(event) {
      if (event.isTrusted === false || !isEligibleTarget(event.target)) return;
      var scrollY = window.pageYOffset || document.documentElement.scrollTop || 0;
      var zone = zoneForDocumentY(scrollY + event.clientY);
      lastActivityAt = Date.now();
      touchZone(zone, 1, 0);
      publish();
    }

    function onScroll() {
      lastActivityAt = Date.now();
    }

    function sampleDwell() {
      if (document.hidden || !document.hasFocus()) return;
      var now = Date.now();
      if (!lastActivityAt || (now - lastActivityAt) > ACTIVE_WINDOW_MS) return;
      touchZone(viewportCenterZone(), 0, SAMPLE_MS);
      publish();
    }

    function start() {
      if (started) return true;
      started = true;
      lastActivityAt = Date.now();
      window.addEventListener('pointerdown', onPointerDown, { passive: true });
      window.addEventListener('scroll', onScroll, { passive: true });
      intervalId = window.setInterval(sampleDwell, SAMPLE_MS);
      window.dispatchEvent(new CustomEvent('sia:attention-ready', {
        detail: { version: '0.1.0', mode: mode, autoPlace: false, telemetry: false }
      }));
      return true;
    }

    function stop() {
      if (!started) return;
      started = false;
      window.removeEventListener('pointerdown', onPointerDown);
      window.removeEventListener('scroll', onScroll);
      if (intervalId) window.clearInterval(intervalId);
      intervalId = null;
    }

    window.SIAAttention = {
      version: '0.1.0',
      start: start,
      stop: stop,
      snapshot: snapshot
    };

    if (enabled) {
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', start, { once: true });
      } else {
        start();
      }
    }
  })(window, document);
  //]]>
  </script>
'''


def patch_theme(text: str) -> str:
    if MARKER in text:
        return text
    anchor = "\n</body>\n</html>"
    if anchor not in text:
        raise RuntimeError("Theme body closing anchor not found")
    return text.replace(anchor, "\n" + RUNTIME + anchor, 1)


def validate(text: str) -> None:
    required = [
        MARKER,
        "name='sia-attention-map'",
        "id='sia-attention-map-runtime'",
        "window.SIAAttention",
        "pointerdown",
        "sia:attention-update",
        "sia:attention-recommendation",
        "autoPlace: false",
        "telemetry: false",
        "storage: 'memory-only'",
        "config.attentionMap === true",
        "config.attentionMode === 'recommend'",
        "'.sia-ad-zone'",
        "'.adsbygoogle'",
        "'a',",
    ]
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise RuntimeError("Missing SIA attention-map markers: " + ", ".join(missing))

    forbidden = [
        "localStorage",
        "sessionStorage",
        "sendBeacon(",
        "XMLHttpRequest(",
        "fetch(",
        ".appendChild(ad",
        ".insertBefore(ad",
        "adsbygoogle.push",
    ]
    runtime = text[text.index(MARKER):]
    present = [marker for marker in forbidden if marker in runtime]
    if present:
        raise RuntimeError("Attention map must remain local and non-placement: " + ", ".join(present))

    if text.count("id='sia-attention-map-runtime'") != 1:
        raise RuntimeError("Attention map runtime must appear exactly once")

    if re.search(r"[\u0900-\u097F]", html.unescape(RUNTIME)):
        raise RuntimeError("Universal attention-map runtime contains Devanagari source text")


def main() -> None:
    text = THEME.read_text(encoding="utf-8")
    text = patch_theme(text)
    validate(text)
    THEME.write_text(text, encoding="utf-8")
    ET.parse(THEME)
    print("SIA v0.1 privacy-safe Fibonacci attention map activated")


if __name__ == "__main__":
    main()
