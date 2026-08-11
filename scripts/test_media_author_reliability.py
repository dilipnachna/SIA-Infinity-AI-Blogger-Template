#!/usr/bin/env python3
"""Static self-test for SIA v0.1 media and Blogger author reliability."""
from pathlib import Path
import xml.etree.ElementTree as ET

ADAPTER = Path("assets/sia-graph-adapter-v0.1.js").read_text(encoding="utf-8")
THEME_PATH = Path("theme/SIA-Infinity-AI-Blogger-Template-v0.1.xml")
THEME = THEME_PATH.read_text(encoding="utf-8")

required_adapter = [
    "SIA Related Media Reliability v0.1",
    "sia_graph_v01_media2:",
    "async function enrichRelatedImages(items)",
    "fetchLabelPosts(labels[0])",
    "items = await enrichRelatedImages(items)",
]
required_theme = [
    "SIA Related Media Reliability v0.1",
    "SIA Blogger Author Profile Hydration v0.1",
    "id='sia-author-profile-runtime'",
    "data:post.authorPhoto.url",
    "data:post.authorProfileUrl",
    "data:post.authorAboutMe",
    "expr:data-sia-post-id='data:post.id'",
    "author['gd$image']",
    "'/feeds/posts/default/' + encodeURIComponent(postId) + '?alt=json'",
]

missing = [x for x in required_adapter if x not in ADAPTER]
missing += [x for x in required_theme if x not in THEME]
assert not missing, "Missing media/author reliability markers: " + ", ".join(missing)

for retired in (
    "return 'sia_graph_v01:' + url;",
    "data:post.author.authorPhoto.url",
    "data:post.author.profileUrl",
    "data:post.author.aboutMe",
):
    assert retired not in THEME, "Retired binding remains: " + retired

# The author fallback may call only the same-origin Blogger post feed. It must
# not introduce browser storage, beacon telemetry, or a third-party fetch.
author_runtime = THEME.split("SIA Blogger Author Profile Hydration v0.1", 1)[1]
author_runtime = author_runtime.split("SIA Fibonacci Attention Map v0.1", 1)[0]
assert "fetch('/feeds/posts/default/'" in author_runtime
assert "localStorage" not in author_runtime
assert "sessionStorage" not in author_runtime
assert "sendBeacon(" not in author_runtime
assert "XMLHttpRequest(" not in author_runtime
assert "fetch('http://" not in author_runtime
assert "fetch('https://" not in author_runtime
assert 'fetch("http://' not in author_runtime
assert 'fetch("https://' not in author_runtime

ET.parse(THEME_PATH)
print("SIA media/author reliability self-test OK: cache-safe images + Blogger profile fallback")
