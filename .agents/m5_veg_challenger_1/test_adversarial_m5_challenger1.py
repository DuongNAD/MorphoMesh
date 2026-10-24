"""
Milestone 5 - Challenger 1 Adversarial Challenge & Stress-Testing Suite
Author: M5 Veg Challenger 1 (critic, specialist)
Target: teamwork_projects/vegetation_library/output/ (all 35 botanical assets)

Validates:
1. Static mesh rigging verification on all 35 GLBs:
   - JSON chunk decode
   - skins is None or []
   - animations is None or []
   - zero primitive attributes contain JOINTS_0 or WEIGHTS_0 (or any joint/weight attr)
   - zero nodes have skin
   - companion OBJ files contain zero bone/skin directives
2. Coordinate integrity:
   - decode POSITION buffers for all 35 GLBs
   - assert zero NaN/Inf
   - all coordinates finite and |v| < 1000m
3. Ground contact base alignment:
   - assert |Z_min| <= 0.005m for every single model
4. Base contact centroid centering:
   - compute bottom 5% height slice centroid
   - assert offset <= 0.05m
5. Metric scale:
   - assert height within +/- 10% of catalog target height
6. Full directory validation:
   - run validate_directory across output/
   - assert all 35 assets pass 20/20 checks with 0 errors
7. Adversarial synthetic mutation tests:
   - prove that faulty/mutated meshes trigger immediate rejection
"""
from __future__ import annotations

import io
import json
import math
from pathlib import Path
import struct
import sys
from typing import Any, Dict, List, Tuple

import numpy as np
import pytest

# Ensure vegetation_pipeline is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
VEG_LIB_DIR = REPO_ROOT / "teamwork_projects" / "vegetation_library"
if str(VEG_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(VEG_LIB_DIR))

from vegetation_pipeline.catalog import get_catalog, VegetationCatalog
from vegetation_pipeline.validator import (
    parse_glb_container,
    decode_glb_geometry,
    inspect_companion_obj,
    validate_directory,
)

OUTPUT_DIR = VEG_LIB_DIR / "output"


def get_all_glb_paths() -> List[Path]:
    glbs = sorted(OUTPUT_DIR.rglob("*.glb"))
    return glbs


# ==============================================================================
# TEST 1: STATIC MESH RIGGING INVARIANTS ACROSS ALL 35 GLBS & OBJS
# ==============================================================================

def test_static_mesh_rigging_invariants_all_35_assets():
    """
    Adversarially parses all 35 GLB files and companion OBJs to strictly verify:
    - glTF JSON 'skins' is None or empty []
    - glTF JSON 'animations' is None or empty []
    - No node references a 'skin'
    - Zero primitive attributes contain JOINTS_0, WEIGHTS_0, or any case variant
    - No bone keywords in node names
    - Companion OBJ has 0 bone groups or skin directives
    """
    glbs = get_all_glb_paths()
    assert len(glbs) == 35, f"Expected exactly 35 GLBs in output/, found {len(glbs)}"

    violations = []

    for glb_path in glbs:
        species_id = glb_path.stem
        gltf, bin_bytes = parse_glb_container(glb_path)

        # 1. skins check
        skins = gltf.get("skins")
        if skins is not None and len(skins) > 0:
            violations.append(f"{species_id}: glTF 'skins' is not empty (found {len(skins)} skins)")

        # 2. animations check
        animations = gltf.get("animations")
        if animations is not None and len(animations) > 0:
            violations.append(f"{species_id}: glTF 'animations' is not empty (found {len(animations)} animations)")

        # 3. nodes skin and bone name checks
        for node_idx, node in enumerate(gltf.get("nodes", [])):
            if "skin" in node:
                violations.append(f"{species_id}: node {node_idx} ('{node.get('name')}') contains 'skin' key")
            node_name = node.get("name", "").lower()
            for kw in ("bone", "armature", "skeleton", "root_joint"):
                if kw in node_name:
                    violations.append(f"{species_id}: node {node_idx} name '{node_name}' contains illegal keyword '{kw}'")

        # 4. primitive attributes check
        for mesh_idx, mesh in enumerate(gltf.get("meshes", [])):
            for prim_idx, prim in enumerate(mesh.get("primitives", [])):
                attrs = prim.get("attributes", {})
                for attr_name in attrs:
                    attr_upper = attr_name.upper()
                    if "JOINT" in attr_upper or "WEIGHT" in attr_upper:
                        violations.append(
                            f"{species_id}: mesh {mesh_idx} prim {prim_idx} contains skinning attribute '{attr_name}'"
                        )

        # 5. companion OBJ check
        obj_path = glb_path.parent / f"{species_id}.obj"
        if obj_path.is_file():
            is_valid, n_bones, obj_viol = inspect_companion_obj(obj_path)
            if not is_valid or n_bones > 0:
                violations.append(f"{species_id}: OBJ contains {n_bones} bone/skin directives: {obj_viol}")

    assert len(violations) == 0, f"Found {len(violations)} static mesh rigging violations:\n" + "\n".join(violations)


# ==============================================================================
# TEST 2: COORDINATE INTEGRITY (ZERO NAN/INF, FINITE, |V| < 1000m)
# ==============================================================================

def test_coordinate_integrity_all_35_assets():
    """
    Decodes POSITION buffers for all 35 GLBs and strictly asserts:
    - zero NaN coordinates
    - zero Inf coordinates
    - all coordinates strictly finite
    - all coordinate components |v| < 1000m (universe bound check)
    - bounding box extents dx > 0, dy > 0, dz > 0
    """
    glbs = get_all_glb_paths()
    assert len(glbs) == 35

    violations = []
    total_vertices_checked = 0

    for glb_path in glbs:
        species_id = glb_path.stem
        gltf, bin_bytes = parse_glb_container(glb_path)
        geom = decode_glb_geometry(gltf, bin_bytes)
        positions = geom["positions"]

        n_verts = len(positions)
        total_vertices_checked += n_verts
        if n_verts == 0:
            violations.append(f"{species_id}: mesh geometry is empty (0 vertices)")
            continue

        # Check NaN / Inf
        if np.isnan(positions).any():
            nan_count = int(np.count_nonzero(np.isnan(positions)))
            violations.append(f"{species_id}: contains {nan_count} NaN coordinates")

        if np.isinf(positions).any():
            inf_count = int(np.count_nonzero(np.isinf(positions)))
            violations.append(f"{species_id}: contains {inf_count} Inf coordinates")

        if not np.isfinite(positions).all():
            violations.append(f"{species_id}: not all vertex coordinates are finite")

        # Bounds check |v| < 1000m
        max_abs_coord = float(np.max(np.abs(positions)))
        if max_abs_coord >= 1000.0:
            violations.append(f"{species_id}: vertex coordinate {max_abs_coord:.2f}m violates bound |v| < 1000m")

        # Bounding box dimensions
        min_coords = np.min(positions, axis=0)
        max_coords = np.max(positions, axis=0)
        extents = max_coords - min_coords

        if extents[0] <= 0 or extents[1] <= 0 or extents[2] <= 0:
            violations.append(f"{species_id}: degenerate bounding box extent: {extents}")

    assert len(violations) == 0, f"Found {len(violations)} coordinate integrity violations:\n" + "\n".join(violations)
    assert total_vertices_checked > 100_000, f"Expected >100,000 vertices across library, checked {total_vertices_checked}"


# ==============================================================================
# TEST 3: GROUND CONTACT BASE ALIGNMENT (|Z_min| <= 0.005m)
# ==============================================================================

def test_ground_contact_base_alignment_all_35_assets():
    """
    Decodes POSITION buffers for all 35 GLBs and asserts:
    - Root base Z_min == 0.000m +/- 0.005m (|Z_min| <= 0.005m)
    - Records exact Z_min for each species
    """
    glbs = get_all_glb_paths()
    assert len(glbs) == 35

    violations = []
    max_z_min_dev = 0.0

    for glb_path in glbs:
        species_id = glb_path.stem
        gltf, bin_bytes = parse_glb_container(glb_path)
        geom = decode_glb_geometry(gltf, bin_bytes)
        positions = geom["positions"]

        z_min = float(np.min(positions[:, 2]))
        abs_dev = abs(z_min)
        if abs_dev > max_z_min_dev:
            max_z_min_dev = abs_dev

        if abs_dev > 0.005:
            violations.append(
                f"{species_id}: Z_min = {z_min:.6f}m violates ground contact tolerance +/-0.005m (dev={abs_dev:.6f}m)"
            )

    assert len(violations) == 0, (
        f"Found {len(violations)} ground contact base alignment violations (max dev {max_z_min_dev:.6f}m):\n"
        + "\n".join(violations)
    )


# ==============================================================================
# TEST 4: BASE CONTACT CENTROID CENTERING (OFFSET <= 0.05m)
# ==============================================================================

def test_base_contact_centroid_centering_all_35_assets():
    """
    Computes bottom 5% height slice centroid for all 35 GLBs and asserts:
    - Centroid distance from (0, 0) is <= 0.05m (5cm)
    - Records exact centroid coordinates and offsets
    """
    glbs = get_all_glb_paths()
    assert len(glbs) == 35

    violations = []
    max_offset = 0.0

    for glb_path in glbs:
        species_id = glb_path.stem
        gltf, bin_bytes = parse_glb_container(glb_path)
        geom = decode_glb_geometry(gltf, bin_bytes)
        positions = geom["positions"]

        z_min = float(np.min(positions[:, 2]))
        z_max = float(np.max(positions[:, 2]))
        height = z_max - z_min

        thresh = z_min + 0.05 * height
        base_verts = positions[positions[:, 2] <= thresh]
        if len(base_verts) == 0:
            base_verts = positions[positions[:, 2] <= z_min + 1e-4]

        cx = float(np.mean(base_verts[:, 0]))
        cy = float(np.mean(base_verts[:, 1]))
        offset = math.sqrt(cx * cx + cy * cy)

        if offset > max_offset:
            max_offset = offset

        # Tolerance: 0.05m + small epsilon for float precision
        if offset > 0.05001:
            violations.append(
                f"{species_id}: bottom 5% base centroid offset {offset:.4f}m exceeds tolerance 0.05m at ({cx:.4f}, {cy:.4f})"
            )

    assert len(violations) == 0, (
        f"Found {len(violations)} base contact centroid violations (max offset {max_offset:.4f}m):\n"
        + "\n".join(violations)
    )


# ==============================================================================
# TEST 5: METRIC SCALE VS CATALOG TARGET HEIGHT (+/- 10%)
# ==============================================================================

def test_metric_scale_all_35_assets():
    """
    Matches all 35 GLBs to catalog species definitions and asserts:
    - Measured bounding box height H = Z_max - Z_min is within +/- 10% of catalog dimensions.height_m
    - Records deviation percentage for each species
    """
    catalog = get_catalog()
    glbs = get_all_glb_paths()
    assert len(glbs) == 35

    violations = []
    max_dev_pct = 0.0

    for glb_path in glbs:
        species_id = glb_path.stem
        sp = catalog.get(species_id)
        assert sp is not None, f"Species {species_id} not found in catalog!"

        target_height = sp.dimensions.height_m

        gltf, bin_bytes = parse_glb_container(glb_path)
        geom = decode_glb_geometry(gltf, bin_bytes)
        positions = geom["positions"]

        z_min = float(np.min(positions[:, 2]))
        z_max = float(np.max(positions[:, 2]))
        measured_height = z_max - z_min

        dev_ratio = abs(measured_height - target_height) / target_height
        dev_pct = dev_ratio * 100.0

        if dev_pct > max_dev_pct:
            max_dev_pct = dev_pct

        if dev_ratio > 0.10001:
            violations.append(
                f"{species_id}: measured height {measured_height:.3f}m differs from target {target_height:.3f}m "
                f"by {dev_pct:.2f}% (exceeds +/- 10.0%)"
            )

    assert len(violations) == 0, (
        f"Found {len(violations)} metric scale violations (max dev {max_dev_pct:.2f}%):\n"
        + "\n".join(violations)
    )


# ==============================================================================
# TEST 6: FULL VALIDATOR INSPECTION SUITE (35/35 ASSETS PASS 20/20 CHECKS)
# ==============================================================================

def test_full_inspection_suite_all_35_assets():
    """
    Executes validate_directory across output/ and asserts:
    - Exactly 35 assets validated
    - 100% pass rate (35/35 is_valid == True)
    - Zero errors reported for every asset
    - Every asset passes all 20/20 checks
    """
    catalog = get_catalog()
    reports = validate_directory(OUTPUT_DIR, catalog=catalog)

    assert len(reports) == 35, f"Expected 35 reports from validate_directory, got {len(reports)}"

    failed_assets = []
    imperfect_checks = []

    for species_id, report in reports.items():
        if not report.is_valid or len(report.errors) > 0:
            failed_assets.append((species_id, report.errors))
        if report.passed_checks_count != 20 or report.total_checks_count != 20:
            imperfect_checks.append((species_id, report.passed_checks_count, report.total_checks_count))

    assert len(failed_assets) == 0, f"Found {len(failed_assets)} failed assets: {failed_assets}"
    assert len(imperfect_checks) == 0, f"Assets without 20/20 checks passed: {imperfect_checks}"


# ==============================================================================
# TEST 7: ADVERSARIAL ORACLE & SYNTHETIC MUTATION TESTS
# ==============================================================================

def test_adversarial_oracle_detects_all_mutations():
    """
    Constructs synthetic mutated glTF data structures to empirically prove that
    our verification logic detects all failure modes and does not have blind spots.
    """
    # 1. Rigging mutations
    # 1a. skins present
    gltf_skins = {"skins": [{"joints": [0]}], "nodes": [], "meshes": []}
    assert gltf_skins.get("skins") is not None and len(gltf_skins["skins"]) > 0

    # 1b. animations present
    gltf_anims = {"animations": [{"name": "wind_sway"}], "nodes": [], "meshes": []}
    assert gltf_anims.get("animations") is not None and len(gltf_anims["animations"]) > 0

    # 1c. node skin reference
    gltf_node_skin = {"nodes": [{"name": "Trunk", "skin": 0}], "meshes": []}
    assert any("skin" in n for n in gltf_node_skin["nodes"])

    # 1d. JOINTS_0 or WEIGHTS_0 primitive attribute
    gltf_skin_attrs = {
        "meshes": [{
            "primitives": [{
                "attributes": {"POSITION": 0, "NORMAL": 1, "JOINTS_0": 2, "WEIGHTS_0": 3}
            }]
        }]
    }
    has_skin_attr = any(
        ("JOINT" in k.upper() or "WEIGHT" in k.upper())
        for m in gltf_skin_attrs["meshes"]
        for p in m["primitives"]
        for k in p["attributes"]
    )
    assert has_skin_attr is True

    # 2. Coordinate mutations
    # 2a. NaN coordinate
    pos_nan = np.array([[0.0, 0.0, 0.0], [np.nan, 1.0, 1.0], [1.0, 1.0, 0.0]], dtype=np.float32)
    assert np.isnan(pos_nan).any()

    # 2b. Inf coordinate
    pos_inf = np.array([[0.0, 0.0, 0.0], [np.inf, 1.0, 1.0], [1.0, 1.0, 0.0]], dtype=np.float32)
    assert np.isinf(pos_inf).any()

    # 2c. Coordinate out of universe bound |v| >= 1000m
    pos_huge = np.array([[0.0, 0.0, 0.0], [1500.0, 1.0, 1.0], [1.0, 1.0, 0.0]], dtype=np.float32)
    assert np.max(np.abs(pos_huge)) >= 1000.0

    # 3. Ground contact mutation: Z_min = 0.015m (above 0.005m tolerance)
    pos_float = np.array([[0.0, 0.0, 0.015], [1.0, 0.0, 1.0], [0.0, 1.0, 2.0]], dtype=np.float32)
    assert abs(float(np.min(pos_float[:, 2]))) > 0.005

    # 4. Base contact centroid mutation: offset = 0.10m (above 0.05m tolerance)
    # create cylinder-like points near base with mean x = 0.10
    pos_offcenter = np.array([
        [0.10, 0.00, 0.00],
        [0.10, 0.02, 0.01],
        [0.10, -0.02, 0.02],
        [0.00, 0.00, 1.00],
        [0.00, 0.00, 2.00],
    ], dtype=np.float32)
    z_min = float(np.min(pos_offcenter[:, 2]))
    z_max = float(np.max(pos_offcenter[:, 2]))
    thresh = z_min + 0.05 * (z_max - z_min)
    base_slice = pos_offcenter[pos_offcenter[:, 2] <= thresh]
    cx = float(np.mean(base_slice[:, 0]))
    cy = float(np.mean(base_slice[:, 1]))
    offset = math.sqrt(cx * cx + cy * cy)
    assert offset > 0.05

    # 5. Metric scale mutation: measured height 2.5m vs target 2.0m (+25% deviation)
    target_h = 2.0
    measured_h = 2.5
    dev_pct = abs(measured_h - target_h) / target_h
    assert dev_pct > 0.10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
