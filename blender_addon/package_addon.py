"""
MorphoMesh: Blender Addon Packaging Script.

Zips the `blender_addon/morphomesh/` directory into a distribution package
ready for Blender 5.2.1 LTS installation.
"""

from __future__ import annotations

import os
import zipfile
from pathlib import Path


def package_addon(output_zip: str | None = None) -> str:
    """Package the addon into a zip file."""
    base_dir = Path(__file__).resolve().parent
    addon_src_dir = base_dir / "morphomesh"

    if output_zip is None:
        output_zip = str(base_dir / "morphomesh_addon.zip")

    if not addon_src_dir.is_dir():
        raise FileNotFoundError(f"Addon source directory not found: {addon_src_dir}")

    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(addon_src_dir):
            # Skip __pycache__ and hidden files
            dirs[:] = [d for d in dirs if d != "__pycache__" and not d.startswith(".")]
            for file in files:
                if file.endswith((".pyc", ".pyo")) or file.startswith("."):
                    continue
                file_path = Path(root) / file
                arcname = Path("morphomesh") / file_path.relative_to(addon_src_dir)
                zf.write(file_path, arcname)

    return output_zip


if __name__ == "__main__":
    out = package_addon()
    print(f"MorphoMesh Blender Addon packaged successfully at: {out}")
