#!/usr/bin/env python3
"""Self-test for the SIA v0.1 visual Related Silo card grid."""
import importlib.util
from pathlib import Path
import sys

GENERATOR = Path("generator/generate_graph.py")
ADAPTER = Path("assets/sia-graph-adapter-v0.1.js")
THEME = Path("theme/SIA-Infinity-AI-Blogger-Template-v0.1.xml")

spec = importlib.util.spec_from_file_location("sia_related_grid_generator", GENERATOR)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

assert hasattr(module, "extract_featured_image")

body_image = "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsExample/s1600/example.jpg"
thumb_image = "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsThumb/s72-c/thumb.jpg"
entry = {"media$thumbnail": {"url": thumb_image}}
body = f'<p>Intro</p><img alt="Example" src="{body_image}"/><p>Body</p>'
assert module.extract_featured_image(entry, body) == body_image
assert module.extract_featured_image(entry, "<p>No image</p>") == thumb_image

post_fields = module.Post.__dataclass_fields__
assert "featured_image" in post_fields
assert post_fields["featured_image"].default == ""

adapter = ADAPTER.read_text(encoding="utf-8")
theme = THEME.read_text(encoding="utf-8")

for marker in (
    "function relatedImageUrl(",
    "function entryImage(entry)",
    "className = 'sia-related-card'",
    "className = 'sia-related-card-image'",
    "img.loading = 'lazy'",
    "img.decoding = 'async'",
    "image: relatedImageUrl(p.image || '')",
    "image: entryImage(entry)",
):
    assert marker in adapter, marker

for marker in (
    "SIA Related Silo Card Grid v0.1",
    "class='widget-area sia-related-section'",
    "class='sia-related-heading'",
    "class='sia-related-grid'",
    "grid-template-columns: repeat(3, minmax(0, 1fr))",
    "aspect-ratio: 16 / 9",
    "object-fit: cover",
    "More From This Silo",
):
    assert marker in theme, marker

# Presentation enhancement must not replace the semantic relation engine.
assert "sia-fibonacci-knn-v0.1" in module.FIBONACCI_KNN_ENGINE
assert "data-sia-relation-types" in adapter
assert "data-sia-evidence-status" in adapter

print("SIA Related Silo visual grid self-test OK: images + 3-column cards + semantic engine preserved")
