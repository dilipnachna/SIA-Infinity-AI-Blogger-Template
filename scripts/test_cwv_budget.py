#!/usr/bin/env python3
"""Static self-test for SIA v0.1 CWV performance-budget guards."""
import importlib.util
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

MODULE_PATH = Path("scripts/activate_cwv_budget.py")
spec = importlib.util.spec_from_file_location("sia_cwv_budget", MODULE_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

THEME_PATH = Path("theme/SIA-Infinity-AI-Blogger-Template-v0.1.xml")
THEME = THEME_PATH.read_text(encoding="utf-8")

module.validate(THEME)

required = [
    "SIA CWV Performance Budget v0.1",
    "p75-lcp-2.5s-inp-200ms-cls-0.1",
    "class='single-post-author-avatar-slot'",
    "class='single-post-author-card-avatar-slot'",
    "requestIdleCallback",
    "img.fetchPriority = 'low'",
    "contain-intrinsic-size: auto 420px",
    "@supports selector(.sia-ad-zone:has(.widget))",
    "fetchpriority='high'",
    "className = 'sia-related-card-image'",
    "img.loading = 'lazy'",
]
missing = [item for item in required if item not in THEME]
assert not missing, "Missing CWV markers: " + ", ".join(missing)

# Late author hydration must fill reserved geometry rather than inserting a new
# grid/flex item that would move surrounding content.
assert "slot.appendChild(img);" in THEME
assert "byline.insertBefore(img, copy);" not in THEME
assert "card.insertBefore(img, copy);" not in THEME

# The CWV layer is a structural budget, not a client-side measurement product.
SOURCE = MODULE_PATH.read_text(encoding="utf-8")
for forbidden in ("PerformanceObserver(", "navigator.sendBeacon", "window.SIACWV"):
    assert forbidden not in SOURCE, "CWV layer gained runtime measurement: " + forbidden

ET.parse(THEME_PATH)
print("SIA CWV performance-budget self-test OK: reserved geometry + idle hydration + ad guards")
