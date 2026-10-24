"""
Empirical asset metrics extractor for M5 Challenger 1
"""
import io
import json
import math
from pathlib import Path
import struct
import sys
from typing import Any, Dict, List

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
VEG_LIB_DIR = REPO_ROOT / "teamwork_projects" / "vegetation_library"
if str(VEG_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(VEG_LIB_DIR))

from vegetation_pipeline.catalog import get_catalog
from vegetation_pipeline.validator import (
    parse_glb_container,
    decode_glb_geometry,
    inspect_companion_obj,
    validate_directory,
)

OUTPUT_DIR = VEG_LIB_DIR / "output"

def collect_metrics():
    catalog = get_catalog()
    glbs = sorted(OUTPUT_DIR.rglob("*.glb"))
    print(f"Analyzing {len(glbs)} assets...")

    reports = validate_directory(OUTPUT_DIR, catalog=catalog)

    results = []
    for glb_path in glbs:
        species_id = glb_path.stem
        sp = catalog.get(species_id)
        target_h = sp.dimensions.height_m if sp else 0.0
        cat_name = sp.short_category if sp else "unknown"

        gltf, bin_bytes = parse_glb_container(glb_path)
        geom = decode_glb_geometry(gltf, bin_bytes)
        positions = geom["positions"]
        triangles = geom["triangles"]

        # Rigging metrics
        skins = gltf.get("skins")
        n_skins = len(skins) if skins else 0
        anims = gltf.get("animations")
        n_anims = len(anims) if anims else 0
        node_skins = sum(1 for n in gltf.get("nodes", []) if "skin" in n)
        n_joint_weight_attrs = 0
        for m in gltf.get("meshes", []):
            for p in m.get("primitives", []):
                for a in p.get("attributes", {}):
                    if "JOINT" in a.upper() or "WEIGHT" in a.upper():
                        n_joint_weight_attrs += 1

        obj_path = glb_path.parent / f"{species_id}.obj"
        obj_ok, n_obj_bones, _ = inspect_companion_obj(obj_path)

        # Coordinate bounds & height
        min_xyz = np.min(positions, axis=0)
        max_xyz = np.max(positions, axis=0)
        z_min = float(min_xyz[2])
        z_max = float(max_xyz[2])
        measured_h = z_max - z_min
        dev_pct = abs(measured_h - target_h) / target_h * 100.0 if target_h > 0 else 0.0

        # Centroid
        thresh = z_min + 0.05 * measured_h
        base_slice = positions[positions[:, 2] <= thresh]
        if len(base_slice) == 0:
            base_slice = positions[positions[:, 2] <= z_min + 1e-4]
        cx = float(np.mean(base_slice[:, 0]))
        cy = float(np.mean(base_slice[:, 1]))
        offset = math.sqrt(cx * cx + cy * cy)

        # Validation report
        rep = reports.get(species_id)
        checks_passed = rep.passed_checks_count if rep else 0
        total_checks = rep.total_checks_count if rep else 0
        is_valid = rep.is_valid if rep else False

        results.append({
            "species_id": species_id,
            "category": cat_name,
            "target_h": target_h,
            "measured_h": measured_h,
            "dev_pct": dev_pct,
            "z_min": z_min,
            "z_max": z_max,
            "base_cx": cx,
            "base_cy": cy,
            "base_offset": offset,
            "min_xyz": min_xyz.tolist(),
            "max_xyz": max_xyz.tolist(),
            "n_verts": len(positions),
            "n_faces": len(triangles),
            "n_skins": n_skins,
            "n_anims": n_anims,
            "node_skins": node_skins,
            "joint_weight_attrs": n_joint_weight_attrs,
            "obj_bones": n_obj_bones,
            "checks_passed": checks_passed,
            "total_checks": total_checks,
            "is_valid": is_valid,
        })

    # Save to json in working directory
    out_json = Path(__file__).parent / "asset_metrics.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    # Print summary statistics
    print("\n=== SUMMARY STATISTICS ===")
    print(f"Total Assets: {len(results)}")
    all_valid = all(r["is_valid"] and r["checks_passed"] == 20 for r in results)
    print(f"All Valid (20/20 checks): {all_valid}")

    max_z_min = max(abs(r["z_min"]) for r in results)
    print(f"Max |Z_min|: {max_z_min:.6f} m (Tolerance <= 0.005 m)")

    max_offset = max(r["base_offset"] for r in results)
    print(f"Max Base Centroid Offset: {max_offset:.6f} m (Tolerance <= 0.05 m)")

    max_dev_pct = max(r["dev_pct"] for r in results)
    print(f"Max Height Deviation: {max_dev_pct:.2f}% (Tolerance <= 10.0%)")

    total_verts = sum(r["n_verts"] for r in results)
    min_verts = min(r["n_verts"] for r in results)
    max_verts = max(r["n_verts"] for r in results)
    print(f"Vertex Count Range: [{min_verts:,}, {max_verts:,}] (Budget [3,000, 45,000]), Total: {total_verts:,}")

    total_bones = sum(r["n_skins"] + r["n_anims"] + r["node_skins"] + r["joint_weight_attrs"] + r["obj_bones"] for r in results)
    print(f"Total Rigging/Skinning Elements Detected: {total_bones} (Strictly 0 required)")

    abs_max_coord = max(max(abs(c) for c in r["min_xyz"] + r["max_xyz"]) for r in results)
    print(f"Absolute Max Coordinate: {abs_max_coord:.4f} m (Bound < 1000 m)")

if __name__ == "__main__":
    collect_metrics()
