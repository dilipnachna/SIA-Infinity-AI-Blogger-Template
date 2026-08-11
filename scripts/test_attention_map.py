#!/usr/bin/env python3
"""Static self-test for the SIA v0.1 Fibonacci Attention Map."""
import importlib.util
from pathlib import Path

MODULE_PATH = Path("scripts/activate_attention_map.py")
spec = importlib.util.spec_from_file_location("sia_attention", MODULE_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

runtime = module.RUNTIME

required = [
    "pointerdown",
    "goldenTop",
    "goldenCenter",
    "goldenBottom",
    "1.61803398875",
    "FIB_PRIOR",
    "dwellMs",
    "Math.pow(PHI, -ageFiveMinuteUnits)",
    "config.attentionMap === true",
    "config.attentionMode === 'recommend'",
    "sia:attention-update",
    "sia:attention-recommendation",
    "autoPlace: false",
    "telemetry: false",
    "storage: 'memory-only'",
    "'.sia-ad-zone'",
    "'.adsbygoogle'",
]
for marker in required:
    assert marker in runtime, marker

for forbidden in (
    "localStorage",
    "sessionStorage",
    "sendBeacon(",
    "XMLHttpRequest(",
    "fetch(",
    "adsbygoogle.push",
):
    assert forbidden not in runtime, forbidden

# Safe recommendation can only name predefined SIA layout zones.
for slot in ("sia-ad-top", "sia-ad-bottom", "sia-ad-feed"):
    assert slot in runtime

# Runtime must not store raw coordinate arrays or identify visitors.
for forbidden in ("visitorId", "fingerprint", "coordinates.push", "clientX:", "clientY:"):
    assert forbidden not in runtime, forbidden

print("SIA Fibonacci Attention Map self-test OK: local, opt-in, non-placement")
