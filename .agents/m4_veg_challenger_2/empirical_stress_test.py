"""
MorphoMesh Milestone 4 (M4) - Empirical Adversarial Challenge & Stress-Testing Suite
Author: Challenger 2 (Empirical Challenger)
Working Directory: E:\\tool\\mcp\\MorphoMesh\\.agents\\m4_veg_challenger_2

Scope:
1. Generate and process assets across all 7 biomes (>= 2 species per biome, 14 species total).
2. Validate 100% pass (20/20 checks) on all 14 generated assets.
3. Test render_asset_preview under BOTH Blender 4.5.4 LTS and pure-Python software fallback:
   - 4 turntable views (512x512, non-empty, visual content non-black / non-transparent).
   - thumbnail.png (1024x1024 contact sheet montage, 4 quadrants + banner + footer).
4. Verify static mesh invariants (N_bones = 0, zero skins, zero joints).
5. Verify real-world scale and ground contact base alignment (Z_min = 0.000m +/- 0.005m).
6. Verify global library manifest (output/manifest.json): JSON validity, categories summary, species records.
7. Adversarial fault injection and edge-case stress testing.
"""
from __future__ import annotations

import io
import json
import logging
import math
import os
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import time
from typing import Any, Dict, List, Tuple

import numpy as np
from PIL import Image

# Ensure project imports resolve
REPO_ROOT = Path(r"E:\tool\mcp\MorphoMesh")
VEG_LIB_DIR = REPO_ROOT / "teamwork_projects" / "vegetation_library"
for p in (str(VEG_LIB_DIR), str(REPO_ROOT), str(REPO_ROOT / "src")):
    if p not in sys.path:
        sys.path.insert(0, p)

from vegetation_pipeline.catalog import get_catalog, get_species
from vegetation_pipeline.generator import generate_plant
from vegetation_pipeline.post_processor import process_and_export
from vegetation_pipeline.validator import (
    decode_glb_geometry,
    parse_glb_container,
    validate_asset,
    validate_geometry,
    validate_pbr_textures,
    validate_static_mesh_invariants,
)
from vegetation_pipeline.renderer import (
    DEFAULT_TURNTABLE_ANGLES,
    RenderConfig,
    render_asset_preview,
    render_contact_sheet,
    render_software_fallback,
    resolve_blender_binary,
)

# 14 Target species across all 7 biomes (2 per biome)
TARGET_SPECIES_BY_BIOME = {
    "broadleaf_trees": ["veg_tree_oak_01", "veg_tree_maple_01"],
    "conifers": ["veg_conifer_pine_01", "veg_conifer_spruce_01"],
    "tropical": ["veg_tropical_palm_01", "veg_tropical_monstera_01"],
    "shrubs": ["veg_shrub_rose_01", "veg_shrub_hydrangea_01"],
    "groundcover": ["veg_ground_fern_01", "veg_ground_pampas_01"],
    "succulents": ["veg_succulent_saguaro_01", "veg_succulent_aloe_01"],
    "vines": ["veg_vine_ivy_01", "veg_vine_wisteria_01"],
}

ALL_TARGET_SPECIES = [sid for sids in TARGET_SPECIES_BY_BIOME.values() for sid in sids]
OUTPUT_DIR = VEG_LIB_DIR / "output"


def log_test_header(title: str):
    print(f"\n{'=' * 78}")
    print(f" [TEST STAGE] {title}")
    print(f"{'=' * 78}")


def test_stage_1_generation():
    """Stage 1: Generate and process all 14 species across 7 biomes using pipeline functions."""
    log_test_header("Stage 1: 7-Biome Asset Generation (14 Species)")
    catalog = get_catalog()
    t_start = time.time()

    generated_assets = {}
    for biome, sids in TARGET_SPECIES_BY_BIOME.items():
        print(f"\n--- Biome: {biome} ({len(sids)} species) ---")
        for sid in sids:
            sp = catalog[sid]
            target_dir = OUTPUT_DIR / sp.short_category / sp.species_id
            print(f"  * Generating {sp.species_id} ({sp.common_name})...", end="", flush=True)

            t0 = time.time()
            # Generate procedural asset
            raw = generate_plant(species=sp, mode="procedural", output_dir=target_dir, force_regenerate=True)
            # Post-process and normalize
            exported = process_and_export(raw_asset=raw, species=sp, output_dir=target_dir)
            # Render multi-angle previews with Blender
            rendered = render_asset_preview(exported, output_dir=target_dir)

            elapsed = time.time() - t0
            print(f" DONE in {elapsed:.2f}s | Verts: {exported.vertex_count:,} | Faces: {exported.face_count:,}")

            assert Path(exported.glb_path).is_file(), f"GLB missing: {exported.glb_path}"
            assert Path(exported.obj_path).is_file(), f"OBJ missing: {exported.obj_path}"
            assert Path(exported.manifest_path).is_file(), f"Asset manifest missing: {exported.manifest_path}"
            generated_assets[sid] = exported

    total_time = time.time() - t_start
    print(f"\n>>> Stage 1 PASSED: Generated {len(generated_assets)} assets in {total_time:.2f}s.")
    return generated_assets


def test_stage_2_validation(generated_assets):
    """Stage 2: Run validate_asset on all 14 assets; assert 100% pass (20/20 checks)."""
    log_test_header("Stage 2: 20-Check Invariant Assertion on All 14 Assets")
    catalog = get_catalog()

    expected_20_checks = [
        "zero_nan_inf_coordinates",
        "vertex_count_budget",
        "normals_finite_and_unit",
        "non_degenerate_faces",
        "ground_contact_base_aligned",
        "base_contact_centroid_centered",
        "metric_scale_bounds",
        "static_mesh_no_skins",
        "static_mesh_no_animations",
        "static_mesh_no_joint_weights",
        "static_mesh_no_node_skins",
        "obj_no_bones",
        "n_bones_strictly_zero",
        "textures_channels_present",
        "textures_readable_and_sized",
        "texture_albedo_plausible",
        "texture_normal_plausible",
        "texture_roughness_plausible",
        "texture_metallic_dielectric",
        "glb_container_valid",
    ]

    all_reports = {}
    for sid in ALL_TARGET_SPECIES:
        sp = catalog[sid]
        asset_dir = OUTPUT_DIR / sp.short_category / sp.species_id
        report = validate_asset(asset_dir, catalog=catalog)
        all_reports[sid] = report

        print(f"  * {sid:30s} | Category: {sp.short_category:15s} | Valid: {report.is_valid!s:5s} | "
              f"Checks: {report.passed_checks_count}/{report.total_checks_count}")

        # Assertions
        assert report.is_valid is True, f"Asset {sid} failed validation! Errors: {report.errors}"
        assert report.total_checks_count == 20, f"Asset {sid} evaluated {report.total_checks_count} checks, expected 20"
        assert report.passed_checks_count == 20, f"Asset {sid} passed {report.passed_checks_count}/20 checks"
        assert len(report.errors) == 0, f"Asset {sid} reported errors: {report.errors}"

        # Assert every required check explicitly evaluated to True
        for chk in expected_20_checks:
            assert chk in report.checks, f"Asset {sid} missing check '{chk}' in report"
            assert report.checks[chk] is True, f"Asset {sid} failed check '{chk}'"

    print(f"\n>>> Stage 2 PASSED: All 14 assets passed 100% of validation checks (20/20).")
    return all_reports


def test_stage_3_rendering_verification():
    """Stage 3: Comprehensive preview visual testing for Blender 4.5.4 LTS and software fallback."""
    log_test_header("Stage 3: Preview Visuals & Contact Sheet Verification")
    catalog = get_catalog()

    # Part A: Blender 4.5.4 LTS outputs verification
    print("\n--- Part A: Verifying Blender 4.5.4 LTS Renders on All 14 Species ---")
    blender_bin = resolve_blender_binary()
    print(f"  Blender Executable: {blender_bin}")
    assert blender_bin is not None, "Blender binary not detected!"

    for sid in ALL_TARGET_SPECIES:
        sp = catalog[sid]
        asset_dir = OUTPUT_DIR / sp.short_category / sp.species_id

        # 1. Verify 4 turntable angles
        turntable_files = ["turntable_01.png", "turntable_02.png", "turntable_03.png", "turntable_04.png"]
        for t_file in turntable_files:
            img_path = asset_dir / t_file
            assert img_path.is_file(), f"{sid} missing render: {img_path}"
            f_size = img_path.stat().st_size
            assert f_size > 1000, f"{sid} {t_file} file size too small ({f_size} bytes)"

            # Image inspection
            with Image.open(img_path) as im:
                assert im.size == (512, 512), f"{sid} {t_file} resolution is {im.size}, expected (512, 512)"
                im_rgba = im.convert("RGBA")
                arr = np.array(im_rgba)

                # Non-empty visual content: check alpha channel
                alpha = arr[:, :, 3]
                opaque_pixels = int(np.count_nonzero(alpha > 20))
                assert opaque_pixels > 500, f"{sid} {t_file} has only {opaque_pixels} non-transparent pixels"

                # Non-black visual content: check mean RGB of opaque pixels
                mask = alpha > 20
                rgb_mean = float(np.mean(arr[:, :, :3][mask]))
                assert rgb_mean > 10.0, f"{sid} {t_file} visual content is solid black (mean RGB {rgb_mean:.2f})"

        # 2. Verify thumbnail.png contact sheet
        thumb_path = asset_dir / "thumbnail.png"
        assert thumb_path.is_file(), f"{sid} missing thumbnail.png: {thumb_path}"
        assert thumb_path.stat().st_size > 5000, f"{sid} thumbnail file size too small"

        with Image.open(thumb_path) as thumb_im:
            assert thumb_im.size == (1024, 1024), f"{sid} thumbnail size is {thumb_im.size}, expected (1024, 1024)"
            t_arr = np.array(thumb_im.convert("RGB"))

            # Check header banner background: dark charcoal #141821 -> approx (20, 24, 33)
            header_sample = t_arr[5, 5, :3]
            assert np.all(header_sample < 50), f"{sid} header banner not dark: {header_sample}"

            # Check emerald accent bar at y=70: #2EA043 -> approx (46, 160, 67)
            accent_sample = t_arr[70, 50, :3]
            assert accent_sample[1] > accent_sample[0] and accent_sample[1] > accent_sample[2], (
                f"{sid} accent bar not green: {accent_sample}"
            )

            # Check footer bar background (y=995, x=10): dark charcoal #1C202A -> approx (28, 32, 42)
            footer_sample = t_arr[995, 10, :3]
            assert np.all(footer_sample < 50), f"{sid} footer bar not dark: {footer_sample}"

            # Check 4 quadrants have visual plant content (non-white pixels on white cell)
            # Q1 (top-left): y in [150, 450], x in [50, 450]
            # Q2 (top-right): y in [150, 450], x in [550, 950]
            # Q3 (bottom-left): y in [550, 950], x in [50, 450]
            # Q4 (bottom-right): y in [550, 950], x in [550, 950]
            q1 = t_arr[150:450, 50:450]
            q2 = t_arr[150:450, 550:950]
            q3 = t_arr[550:950, 50:450]
            q4 = t_arr[550:950, 550:950]

            for q_idx, q in enumerate([q1, q2, q3, q4], 1):
                plant_pixels = int(np.count_nonzero(np.any(q < 240, axis=-1)))
                assert plant_pixels > 1000, f"{sid} thumbnail Q{q_idx} lacks content ({plant_pixels} plant px)"

        print(f"  * {sid:30s} | 4x 512x512 Turntables: OK | 1024x1024 Contact Sheet: OK")

    # Part B: Pure-Python Software Fallback Verification
    print("\n--- Part B: Verifying Pure-Python Software Fallback Rendering ---")
    with tempfile.TemporaryDirectory(prefix="morpho_sw_render_test_") as tmpdir:
        tmp_dir = Path(tmpdir)
        # Test 1 species from each category under pure software mode
        sample_species_ids = [sids[0] for sids in TARGET_SPECIES_BY_BIOME.values()]
        for sid in sample_species_ids:
            sp = catalog[sid]
            src_asset_dir = OUTPUT_DIR / sp.short_category / sp.species_id
            sw_out = tmp_dir / sid

            # Force pure-Python software fallback via use_blender=False
            sw_results = render_asset_preview(
                src_asset_dir,
                output_dir=sw_out,
                use_blender=False,
                config=RenderConfig(use_blender=False, engine="software"),
            )

            # Verify 4 views + thumbnail
            for ang in ["hero", "front", "side", "crown"]:
                assert ang in sw_results, f"Missing {ang} in software render"
                p = sw_results[ang]
                assert p.is_file(), f"Software render file missing: {p}"
                with Image.open(p) as sw_im:
                    assert sw_im.size == (512, 512), f"Software render {ang} size {sw_im.size}"
                    sw_arr = np.array(sw_im.convert("RGBA"))
                    opaque = int(np.count_nonzero(sw_arr[:, :, 3] > 20))
                    assert opaque > 200, f"Software render {ang} for {sid} empty ({opaque} px)"

            # Verify thumbnail
            thumb_sw = sw_results["thumbnail"]
            assert thumb_sw.is_file(), f"Software thumbnail missing: {thumb_sw}"
            with Image.open(thumb_sw) as sthumb:
                assert sthumb.size == (1024, 1024), f"Software thumbnail size {sthumb.size}"

            print(f"  * [Software Fallback] {sid:25s} | 4x 512x512 Turntables: OK | 1024x1024 Montage: OK")

    print("\n>>> Stage 3 PASSED: Visual renders and contact sheets verified across both engines.")


def test_stage_4_static_mesh_invariants():
    """Stage 4: Verify static mesh invariants directly on GLB binaries."""
    log_test_header("Stage 4: Static Mesh Invariants Verification (N_bones = 0)")
    catalog = get_catalog()

    for sid in ALL_TARGET_SPECIES:
        sp = catalog[sid]
        glb_path = OUTPUT_DIR / sp.short_category / sp.species_id / f"{sid}.glb"
        obj_path = OUTPUT_DIR / sp.short_category / sp.species_id / f"{sid}.obj"

        assert glb_path.is_file(), f"GLB not found: {glb_path}"
        gltf, bin_bytes = parse_glb_container(glb_path)

        # 1. glTF JSON checks
        assert "skins" not in gltf or gltf["skins"] is None or len(gltf["skins"]) == 0, (
            f"{sid} contains skins: {gltf.get('skins')}"
        )
        assert "animations" not in gltf or gltf["animations"] is None or len(gltf["animations"]) == 0, (
            f"{sid} contains animations: {gltf.get('animations')}"
        )

        # 2. Primitive attributes checks: no JOINTS_ or WEIGHTS_
        for mesh_idx, mesh in enumerate(gltf.get("meshes", [])):
            for prim_idx, prim in enumerate(mesh.get("primitives", [])):
                attrs = prim.get("attributes", {})
                for k in attrs:
                    k_up = k.upper()
                    assert not k_up.startswith("JOINTS_"), f"{sid} mesh {mesh_idx} prim {prim_idx} has joints: {k}"
                    assert not k_up.startswith("WEIGHTS_"), f"{sid} mesh {mesh_idx} prim {prim_idx} has weights: {k}"

        # 3. Node skin references
        for node in gltf.get("nodes", []):
            assert "skin" not in node, f"{sid} node references skin: {node}"

        # 4. Companion OBJ check
        if obj_path.is_file():
            with open(obj_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    s = line.strip().lower()
                    if s.startswith("g ") or s.startswith("o "):
                        for bad in ("bone", "joint", "armature", "skin", "weight"):
                            assert bad not in s, f"{sid} OBJ group/object name references '{bad}': {line.strip()}"
                    elif any(s.startswith(cmd + " ") for cmd in ("bone", "joint", "skin", "weight")):
                        raise AssertionError(f"{sid} OBJ command references skinning: {line.strip()}")

        print(f"  * {sid:30s} | skins: 0 | anims: 0 | joints/weights: 0 | N_bones: strictly 0")

    print("\n>>> Stage 4 PASSED: Static mesh invariants verified for all 14 GLB files.")


def test_stage_5_scale_and_grounding():
    """Stage 5: Verify real-world metric scale and ground contact base alignment."""
    log_test_header("Stage 5: Real-World Metric Scale & Ground Contact Base Alignment")
    catalog = get_catalog()

    for sid in ALL_TARGET_SPECIES:
        sp = catalog[sid]
        glb_path = OUTPUT_DIR / sp.short_category / sp.species_id / f"{sid}.glb"
        gltf, bin_bytes = parse_glb_container(glb_path)
        geom = decode_glb_geometry(gltf, bin_bytes)
        positions = geom["positions"]

        min_pt = np.min(positions, axis=0)
        max_pt = np.max(positions, axis=0)
        dims = max_pt - min_pt

        # Determine vertical axis: Blender Z-up vs glTF Y-up
        # PostProcessor aligns ground contact at Z_min = 0 (or Y_min = 0)
        if abs(float(min_pt[2])) <= 0.005:
            vert_axis = "Z"
            ground_min = float(min_pt[2])
            height = float(dims[2])
            vert_idx = 2
        elif abs(float(min_pt[1])) <= 0.005:
            vert_axis = "Y"
            ground_min = float(min_pt[1])
            height = float(dims[1])
            vert_idx = 1
        else:
            vert_axis = "Z"
            ground_min = float(min_pt[2])
            height = float(dims[2])
            vert_idx = 2

        # Invariant 1: Ground contact base alignment (|ground_min| <= 0.005m)
        assert abs(ground_min) <= 0.005, (
            f"{sid} ground contact violation: {vert_axis}_min = {ground_min:.6f}m exceeds tolerance ±0.005m"
        )

        # Invariant 2: Metric height bounds (+/- 10% target mature height)
        target_h = sp.dimensions.height_m
        height_err_pct = abs(height - target_h) / target_h * 100.0
        assert height_err_pct <= 10.0, (
            f"{sid} height error {height_err_pct:.2f}% exceeds ±10.0% (target: {target_h:.3f}m, measured: {height:.3f}m)"
        )

        # Invariant 3: Base contact centroid centering (bottom 5% slice <= 0.05m)
        v_extent = float(max_pt[vert_idx] - min_pt[vert_idx])
        base_mask = positions[:, vert_idx] <= (min_pt[vert_idx] + 0.05 * v_extent)
        base_verts = positions[base_mask]
        if vert_idx == 2:
            cx, cy = float(np.mean(base_verts[:, 0])), float(np.mean(base_verts[:, 1]))
        else:
            cx, cy = float(np.mean(base_verts[:, 0])), float(np.mean(base_verts[:, 2]))
        dist_c = math.sqrt(cx * cx + cy * cy)
        assert dist_c <= 0.05, f"{sid} base centroid offset {dist_c:.4f}m exceeds tolerance ±0.05m"

        print(f"  * {sid:30s} | {vert_axis}_min = {ground_min:+.5f}m | "
              f"Height: {height:5.2f}m (Target: {target_h:5.2f}m, dev {height_err_pct:.1f}%) | Centroid: {dist_c:.4f}m")

    print("\n>>> Stage 5 PASSED: All 14 assets strictly aligned at Z_min = 0.000m ± 0.005m with correct scale.")


def test_stage_6_manifest_aggregation():
    """Stage 6: Verify global library manifest (output/manifest.json) integrity."""
    log_test_header("Stage 6: Global Library Manifest Verification")
    from pipeline import aggregate_manifest

    # Run aggregate manifest across all current output assets
    from pipeline import execute_species_pipeline
    catalog = get_catalog()
    records = []
    for sid in ALL_TARGET_SPECIES:
        sp = catalog[sid]
        rec = execute_species_pipeline(
            species=sp,
            output_dir=OUTPUT_DIR,
            validate_only=True,
        )
        records.append(rec)

    manifest_path = aggregate_manifest(OUTPUT_DIR, records)
    print(f"  Manifest written to: {manifest_path}")

    assert manifest_path.is_file(), f"Manifest file missing: {manifest_path}"
    with open(manifest_path, "r", encoding="utf-8") as f:
        mdata = json.load(f)

    # Verify JSON Schema & Top-Level Fields
    assert mdata.get("project") == "MorphoMesh Vegetation Library"
    assert mdata.get("schema_version") == "1.0.0"
    assert mdata.get("total_catalog_species") == 35

    indexed_count = mdata.get("indexed_species_count", 0)
    passed_count = mdata.get("passed_validation_count", 0)
    failed_count = mdata.get("failed_validation_count", 0)

    print(f"  Indexed: {indexed_count} | Passed: {passed_count} | Failed: {failed_count}")
    assert indexed_count >= 14, f"Expected at least 14 indexed species, got {indexed_count}"
    assert passed_count >= 14, f"Expected at least 14 passed species, got {passed_count}"
    assert failed_count == 0, f"Expected 0 failed species, got {failed_count}"

    # Verify categories_summary
    cat_summary = mdata.get("categories_summary", {})
    assert len(cat_summary) == 7, f"Expected 7 categories in summary, got {len(cat_summary)}"

    for biome, sids in TARGET_SPECIES_BY_BIOME.items():
        assert biome in cat_summary, f"Category '{biome}' missing from categories_summary"
        stats = cat_summary[biome]
        assert stats["total_catalog"] == 5, f"Category '{biome}' total_catalog should be 5, got {stats['total_catalog']}"
        assert stats["indexed_count"] >= 2, f"Category '{biome}' indexed_count < 2: {stats['indexed_count']}"
        assert stats["passed_validation"] >= 2, f"Category '{biome}' passed_validation < 2: {stats['passed_validation']}"
        print(f"  - Category '{biome:15s}': {stats['indexed_count']}/5 indexed, {stats['passed_validation']} passed")

    # Verify all 14 species exist in assets dictionary
    assets_dict = mdata.get("assets", {})
    for sid in ALL_TARGET_SPECIES:
        assert sid in assets_dict, f"Species {sid} missing from manifest assets"
        entry = assets_dict[sid]
        assert entry["species_id"] == sid
        assert entry["validation"]["is_valid"] is True, f"{sid} validation in manifest is not True"
        assert entry["validation"]["verdict"] == "PASSED"

        # Verify relative files exist
        files = entry["files"]
        for fkey in ["glb", "obj", "mtl", "thumbnail", "asset_manifest"]:
            rel = files.get(fkey)
            assert rel is not None, f"{sid} missing file key {fkey}"
            full_p = OUTPUT_DIR / rel
            assert full_p.is_file(), f"{sid} declared file not on disk: {full_p}"

        # Verify texture files
        for tch, trel in files.get("textures", {}).items():
            assert (OUTPUT_DIR / trel).is_file(), f"{sid} texture {tch} missing: {trel}"

    print(f"\n>>> Stage 6 PASSED: Global manifest is 100% valid with complete schemas and files.")


def test_stage_7_adversarial_fault_injection():
    """Stage 7: Adversarial fault injection and stress-testing edge cases."""
    log_test_header("Stage 7: Adversarial Defect Injection & Fault Tolerance Stress Tests")

    # 1. NaN coordinate injection
    print("\n--- Test 7.1: Injecting NaN Coordinates into Geometry ---")
    bad_pos = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, np.nan], [0.0, 1.0, 0.0]], dtype=np.float32)
    bad_pos = np.tile(bad_pos, (1100, 1))  # 3300 verts
    bad_norm = np.tile(np.array([0.0, 0.0, 1.0], dtype=np.float32), (len(bad_pos), 1))
    bad_tri = np.arange(len(bad_pos), dtype=np.int32).reshape(-1, 3)
    chk, met, errs, warns = validate_geometry(bad_pos, bad_norm, bad_tri)
    assert chk["zero_nan_inf_coordinates"] is False, "Validator failed to catch NaN coordinates!"
    print("  [OK] NaN coordinate correctly rejected with check=False")

    # 2. Skeletal skinning / bone injection into glTF
    print("\n--- Test 7.2: Injecting Skeletal Armature & Joints into glTF Structure ---")
    poisoned_gltf = {
        "asset": {"version": "2.0"},
        "skins": [{"joints": [0, 1], "name": "ArmatureSkin"}],
        "animations": [{"name": "Idle"}],
        "meshes": [{
            "primitives": [{"attributes": {"POSITION": 0, "JOINTS_0": 1, "WEIGHTS_0": 2}}]
        }],
        "nodes": [{"name": "Pelvis", "skin": 0}],
    }
    s_chk, s_met, s_errs, _ = validate_static_mesh_invariants(poisoned_gltf)
    assert s_chk["static_mesh_no_skins"] is False, "Failed to reject glTF skins!"
    assert s_chk["static_mesh_no_animations"] is False, "Failed to reject glTF animations!"
    assert s_chk["static_mesh_no_joint_weights"] is False, "Failed to reject JOINTS_/WEIGHTS_ attributes!"
    assert s_chk["static_mesh_no_node_skins"] is False, "Failed to reject node skin references!"
    assert s_chk["n_bones_strictly_zero"] is False, "Failed to reject N_bones > 0!"
    print("  [OK] Armature, skins, animations, and joint weights correctly rejected (5/5 checks failed)")

    # 3. Elevated ground pivot injection
    print("\n--- Test 7.3: Injecting Elevated Root Pivot (Z_min = 1.250m) ---")
    floating_pos = np.tile(np.array([[0.0, 0.0, 1.25], [0.5, 0.0, 3.0], [0.0, 0.5, 3.0]], dtype=np.float32), (1200, 1))
    floating_norm = np.tile(np.array([0.0, 0.0, 1.0], dtype=np.float32), (len(floating_pos), 1))
    floating_tri = np.arange(len(floating_pos), dtype=np.int32).reshape(-1, 3)
    f_chk, f_met, f_errs, _ = validate_geometry(floating_pos, floating_norm, floating_tri, vertical_axis="Z")
    assert f_chk["ground_contact_base_aligned"] is False, "Failed to reject floating mesh!"
    print("  [OK] Floating ground pivot (Z_min=1.25m) correctly rejected with check=False")

    # 4. Off-center base contact centroid
    print("\n--- Test 7.4: Injecting Off-Center Root Centroid (X = 0.50m) ---")
    shifted_pos = np.tile(np.array([[0.50, 0.0, 0.0], [0.55, 0.0, 2.0], [0.50, 0.55, 2.0]], dtype=np.float32), (1200, 1))
    shifted_norm = np.tile(np.array([0.0, 0.0, 1.0], dtype=np.float32), (len(shifted_pos), 1))
    shifted_tri = np.arange(len(shifted_pos), dtype=np.int32).reshape(-1, 3)
    c_chk, c_met, c_errs, _ = validate_geometry(shifted_pos, shifted_norm, shifted_tri, vertical_axis="Z")
    assert c_chk["base_contact_centroid_centered"] is False, "Failed to reject off-center centroid!"
    print("  [OK] Off-center base centroid (0.50m) correctly rejected with check=False")

    # 5. Out-of-bounds metric scale (+50% deviation)
    print("\n--- Test 7.5: Injecting Extreme Height Deviation (+50%) ---")
    scaled_pos = np.tile(np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 15.0], [0.0, 1.0, 15.0]], dtype=np.float32), (1200, 1))
    scaled_norm = np.tile(np.array([0.0, 0.0, 1.0], dtype=np.float32), (len(scaled_pos), 1))
    scaled_tri = np.arange(len(scaled_pos), dtype=np.int32).reshape(-1, 3)
    # Target height 10.0m, measured height 15.0m (+50% dev)
    sc_chk, sc_met, sc_errs, _ = validate_geometry(scaled_pos, scaled_norm, scaled_tri, target_height_m=10.0, vertical_axis="Z")
    assert sc_chk["metric_scale_bounds"] is False, "Failed to reject +50% scale deviation!"
    print("  [OK] Out-of-bounds metric scale (+50%) correctly rejected with check=False")

    # 6. Metallic vegetation violation (metallic = 0.95)
    print("\n--- Test 7.6: Injecting Metallic Plant Material Violation ---")
    metallic_img = Image.new("L", (256, 256), 240)  # ~0.94 metallic
    embedded_tex = {
        "albedo": Image.new("RGB", (256, 256), (100, 150, 80)),
        "normal": Image.new("RGB", (256, 256), (128, 128, 255)),
        "roughness": Image.new("L", (256, 256), 128),
        "metallic": metallic_img,
    }
    t_chk, t_met, t_errs, _ = validate_pbr_textures(textures_dir=None, embedded_images=embedded_tex)
    assert t_chk["texture_metallic_dielectric"] is False, "Failed to reject non-dielectric metallic texture!"
    print("  [OK] Metallic texture (0.94) correctly rejected with check=False")

    # 7. Solid black albedo texture injection
    print("\n--- Test 7.7: Injecting Solid Black Albedo Texture ---")
    black_albedo = Image.new("RGB", (256, 256), (0, 0, 0))
    embedded_tex["albedo"] = black_albedo
    embedded_tex["metallic"] = Image.new("L", (256, 256), 0)
    tb_chk, tb_met, tb_errs, _ = validate_pbr_textures(textures_dir=None, embedded_images=embedded_tex)
    assert tb_chk["texture_albedo_plausible"] is False, "Failed to reject solid black albedo!"
    print("  [OK] Solid black albedo correctly rejected with check=False")

    # 8. Corrupt GLB container handling
    print("\n--- Test 7.8: Injecting Truncated / Corrupted GLB Binary ---")
    with tempfile.NamedTemporaryFile("wb", suffix=".glb", delete=False) as f:
        f.write(b"glTF\x02\x00\x00\x00\x10\x00\x00\x00corrupted_bytes")
        corrupt_glb_path = f.name
    try:
        report = validate_asset(corrupt_glb_path)
        assert report.is_valid is False
        assert report.checks.get("glb_container_valid") is False
        print("  [OK] Corrupt GLB safely intercepted without unhandled exception")
    finally:
        if os.path.exists(corrupt_glb_path):
            os.remove(corrupt_glb_path)

    # 9. Contact sheet resilience to partial images
    print("\n--- Test 7.9: Contact Sheet Resilience to Missing / Partial Images ---")
    with tempfile.TemporaryDirectory(prefix="sheet_test_") as s_dir:
        out_sheet = Path(s_dir) / "partial_sheet.png"
        img1 = Path(s_dir) / "img1.png"
        Image.new("RGBA", (512, 512), (200, 100, 50, 255)).save(img1)
        # Supply only 1 image out of 4
        res_sheet = render_contact_sheet([img1], out_sheet, title="Partial Test Plant")
        assert res_sheet.is_file()
        with Image.open(res_sheet) as sheet_im:
            assert sheet_im.size == (1024, 1024)
        print("  [OK] Contact sheet generator survived partial images gracefully")

    print("\n>>> Stage 7 PASSED: All 9 adversarial injection scenarios verified and rejected as expected.")


def main():
    print("=" * 78)
    print(" MORPHOMESH MILESTONE 4 - EMPIRICAL ADVERSARIAL CHALLENGER VERIFICATION")
    print("=" * 78)

    t_start = time.time()
    generated_assets = test_stage_1_generation()
    reports = test_stage_2_validation(generated_assets)
    test_stage_3_rendering_verification()
    test_stage_4_static_mesh_invariants()
    test_stage_5_scale_and_grounding()
    test_stage_6_manifest_aggregation()
    test_stage_7_adversarial_fault_injection()

    total_time = time.time() - t_start
    print("\n" + "=" * 78)
    print(f" ALL 7 EMPIRICAL STAGES COMPLETED SUCCESSFULLY IN {total_time:.2f}s!")
    print(" FINAL VERDICT: APPROVE")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
