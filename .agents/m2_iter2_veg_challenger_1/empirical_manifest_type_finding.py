"""
Empirical Evidence Script: Manifest Type Resilience Finding
Location: E:\\tool\\mcp\\MorphoMesh\\.agents\\m2_iter2_veg_challenger_1\\empirical_manifest_type_finding.py

This script empirically demonstrates the behavior of MeshyGenerator.check_cache
when cache_manifest.json contains valid JSON that is NOT a dictionary (e.g. array, integer, string, null).
"""

import io
import json
from pathlib import Path
import struct
import sys
import tempfile
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "teamwork_projects" / "vegetation_library"))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from vegetation_pipeline.catalog import get_catalog
from vegetation_pipeline.generator import MeshyGenerator

def main():
    cat = get_catalog()
    oak = cat["veg_tree_oak_01"]
    gen = MeshyGenerator()

    cases = [
        ("Array / List", "[1, 2, 3]"),
        ("Scalar Integer", "12345"),
        ("Scalar String", '"corrupt_string"'),
        ("JSON null", "null"),
        ("JSON boolean", "true"),
    ]

    print("=" * 80)
    print("EMPIRICAL FINDING: Manifest Type Validation in MeshyGenerator.check_cache")
    print("=" * 80)

    for name, content in cases:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            # Create valid GLB
            glb_data = struct.pack("<4sII", b"glTF", 2, 12)
            (p / f"{oak.species_id}.glb").write_bytes(glb_data)

            # Create 4 valid textures
            img = Image.new("RGB", (16, 16), (50, 100, 50))
            for t in ["albedo.png", "normal.png", "roughness.png", "metallic.png"]:
                img.save(p / t)

            # Write manifest
            (p / "cache_manifest.json").write_text(content, encoding="utf-8")

            # Test with expected_source="meshy"
            try:
                res = gen.check_cache(oak, target_dir=p, expected_source="meshy")
                print(f"[{name}] with expected_source='meshy': Handled gracefully -> {res}")
            except Exception as e:
                print(f"[{name}] with expected_source='meshy': CRASHED with {type(e).__name__}: {e}")

            # Test with expected_source=None (e.g. auto mode)
            try:
                res = gen.check_cache(oak, target_dir=p, expected_source=None)
                print(f"[{name}] with expected_source=None: Handled gracefully -> {res}")
            except Exception as e:
                print(f"[{name}] with expected_source=None: CRASHED with {type(e).__name__}: {e}")

if __name__ == "__main__":
    main()
