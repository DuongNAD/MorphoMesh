import os

with open("src/morphomesh/human_generator.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# lines 1206-1695 (1-indexed) -> lines[1205:1695]
script_body = "".join(lines[1205:1695])

content = '''"""
Blender Runtime Script Generation for Digital Human Base Mesh.

Generates authoritative Python script executable inside Blender 4.5+ LTS to
synthesize digital human mesh, assign 24 standardized vertex groups, configure
52 ARKit FACS shape keys, and attach anatomical landmark coordinates.
"""

from __future__ import annotations

from typing import Any, Optional

try:
    from morphomesh.models import HumanAnatomyConfig
except (ImportError, ModuleNotFoundError):
    from ..models import HumanAnatomyConfig  # type: ignore[no-redef]

from .morphology import resolve_human_anatomy_config


''' + script_body + '''

__all__ = [
    "get_human_generation_script",
]
'''

os.makedirs("src/morphomesh/human", exist_ok=True)
with open("src/morphomesh/human/scripts.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Wrote src/morphomesh/human/scripts.py, lines:", len(content.splitlines()))
