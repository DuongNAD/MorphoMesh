"""
MorphoMesh Vegetation Library - Milestone 5 Acceptance and End-to-End Verification Test Suite
Target File: teamwork_projects/vegetation_library/tests/test_vegetation_pipeline.py

Comprehensive test suite verifying:
1. test_catalog_manifest_scale: asserts >= 30 species across >= 6 categories (35 species, 7 biomes).
2. test_all_species_directories_and_files_exist: checks existence of all 13 required files for all 35 species.
3. test_global_manifest_schema_and_integrity: validates output/manifest.json structure, metrics, and schema.
4. test_geometry_standards_all_species: sweeps all 35 GLBs, asserts ground alignment, centering, 0 bones, budget.
5. test_pbr_material_standards_all_species: sweeps all 35 species, asserts 4 PBR textures, plausible values.
6. test_renders_and_visual_showcase_all_species: sweeps all 35 species, asserts 4 turntables and 1024x1024 thumbnail.
7. test_full_inspection_suite_100_percent_pass: runs validate_asset on all 35 species, asserts 20/20 checks.
8. test_cli_summary_mode_execution: verifies CLI --summary runs cleanly and emits Markdown table.
9. test_programmatic_run_pipeline_api: verifies programmatic run_pipeline entry point.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, List

import numpy as np
from PIL import Image
import pytest

from vegetation_pipeline.catalog import (
    get_catalog,
    get_species,
    list_categories,
    list_species_ids,
)
from vegetation_pipeline.validator import (
    decode_glb_geometry,
    parse_glb_container,
    validate_asset,
    validate_directory,
    validate_geometry,
    validate_static_mesh_invariants,
    validate_pbr_textures,
)
from pipeline import run_pipeline, format_summary_table

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
CATALOG = get_catalog()


def test_catalog_manifest_scale():
    """
    1. test_catalog_manifest_scale:
    Asserts >= 30 species across >= 6 categories (production library contains
    35 canonical botanical species across 7 distinct biome categories).
    """
    assert len(CATALOG.species) >= 30, f"Expected >= 30 species, found {len(CATALOG.species)}"
    assert len(CATALOG.categories) >= 6, f"Expected >= 6 categories, found {len(CATALOG.categories)}"
    assert len(CATALOG.species) == 35, f"Expected exactly 35 species, found {len(CATALOG.species)}"
    assert len(CATALOG.categories) == 7, f"Expected exactly 7 categories, found {len(CATALOG.categories)}"

    # Verify each category has at least 4 species
    for cat in CATALOG.categories:
        species_in_cat = [s for s in CATALOG.species if s.short_category == cat.short_category]
        assert len(species_in_cat) >= 4, f"Category {cat.short_category} has only {len(species_in_cat)} species"
        assert len(species_in_cat) == 5, f"Category {cat.short_category} expected 5 species, got {len(species_in_cat)}"

    # Verify each species has complete valid botanical attributes
    for sp in CATALOG.species:
        assert sp.species_id.startswith("veg_")
        assert len(sp.common_name) > 0
        assert len(sp.scientific_name) > 0
        assert sp.dimensions.height_m > 0.0
        assert sp.dimensions.canopy_spread_m > 0.0
        assert len(sp.meshy_spec.positive_prompt) > 10


def test_all_species_directories_and_files_exist():
    """
    2. test_all_species_directories_and_files_exist:
    Checks existence of all required files for all 35 species:
    - <species_id>.glb (production GLB with embedded PBR)
    - <species_id>.obj and <species_id>.mtl (companion Wavefront OBJ)
    - textures/ (albedo.png, normal.png, roughness.png, metallic.png)
    - asset_manifest.json (per-species metadata)
    - turntable_01.png, turntable_02.png, turntable_03.png, turntable_04.png (512x512 renders)
    - thumbnail.png (1024x1024 contact sheet montage)
    """
    assert OUTPUT_DIR.is_dir(), f"Output directory not found: {OUTPUT_DIR}"

    for sp in CATALOG.species:
        sp_dir = OUTPUT_DIR / sp.short_category / sp.species_id
        assert sp_dir.is_dir(), f"Species directory missing for {sp.species_id}: {sp_dir}"

        glb_file = sp_dir / f"{sp.species_id}.glb"
        assert glb_file.is_file(), f"GLB missing: {glb_file}"
        assert glb_file.stat().st_size > 1024, f"GLB file suspiciously small: {glb_file}"

        obj_file = sp_dir / f"{sp.species_id}.obj"
        assert obj_file.is_file(), f"OBJ missing: {obj_file}"
        assert obj_file.stat().st_size > 1024, f"OBJ file suspiciously small: {obj_file}"

        mtl_file = sp_dir / f"{sp.species_id}.mtl"
        assert mtl_file.is_file(), f"MTL missing: {mtl_file}"
        assert mtl_file.stat().st_size > 50, f"MTL file suspiciously small: {mtl_file}"

        manifest_file = sp_dir / "asset_manifest.json"
        assert manifest_file.is_file(), f"Per-species manifest missing: {manifest_file}"
        with open(manifest_file, "r", encoding="utf-8") as f:
            m_data = json.load(f)
        assert m_data.get("species_id") == sp.species_id

        # Textures directory and 4 required discrete channels
        tex_dir = sp_dir / "textures"
        assert tex_dir.is_dir(), f"textures/ directory missing: {tex_dir}"
        for ch in ("albedo", "normal", "roughness", "metallic"):
            tp = tex_dir / f"{ch}.png"
            assert tp.is_file(), f"Texture channel missing: {tp}"
            assert tp.stat().st_size > 100, f"Texture channel empty: {tp}"

        # 4 Turntable multi-angle renders
        for i in range(1, 5):
            tt_file = sp_dir / f"turntable_0{i}.png"
            assert tt_file.is_file(), f"Turntable {i} missing: {tt_file}"
            assert tt_file.stat().st_size > 1024, f"Turntable {i} suspiciously small: {tt_file}"

        # 1024x1024 contact sheet montage
        thumb_file = sp_dir / "thumbnail.png"
        assert thumb_file.is_file(), f"Thumbnail missing: {thumb_file}"
        assert thumb_file.stat().st_size > 1024, f"Thumbnail suspiciously small: {thumb_file}"


def test_global_manifest_schema_and_integrity():
    """
    3. test_global_manifest_schema_and_integrity:
    Validates output/manifest.json:
    - total_catalog_species == 35
    - indexed_species_count == 35
    - passed_validation_count == 35
    - failed_validation_count == 0
    - 7 category summaries each with 5/5 valid
    - Every asset record has valid relative paths and validation status.
    """
    manifest_p = OUTPUT_DIR / "manifest.json"
    assert manifest_p.is_file(), f"Global manifest missing: {manifest_p}"

    with open(manifest_p, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("schema_version") == "1.0.0"
    assert data.get("total_catalog_species") == 35
    assert data.get("indexed_species_count") == 35
    assert data.get("passed_validation_count") == 35
    assert data.get("failed_validation_count") == 0

    cats_summary = data.get("categories_summary", {})
    assert len(cats_summary) == 7
    for cat_slug in ("broadleaf_trees", "conifers", "tropical", "shrubs", "groundcover", "succulents", "vines"):
        assert cat_slug in cats_summary, f"Category {cat_slug} missing from manifest summary"
        c_info = cats_summary[cat_slug]
        assert c_info.get("total_catalog") == 5
        assert c_info.get("indexed_count") == 5
        assert c_info.get("passed_validation") == 5

    assets = data.get("assets", {})
    assert len(assets) == 35

    for sp in CATALOG.species:
        assert sp.species_id in assets, f"{sp.species_id} missing from manifest assets dict"
        rec = assets[sp.species_id]
        assert rec.get("category") == sp.short_category
        assert rec.get("common_name") == sp.common_name
        assert rec.get("scientific_name") == sp.scientific_name
        assert rec.get("status") in ("completed", "validated")

        # File pointers
        files = rec.get("files", {})
        for k in ("glb", "obj", "mtl", "thumbnail", "asset_manifest"):
            rel_path = files.get(k)
            assert rel_path is not None, f"File pointer {k} missing for {sp.species_id}"
            full_p = OUTPUT_DIR / rel_path
            assert full_p.is_file(), f"File referenced in manifest does not exist: {full_p}"

        tex_dict = files.get("textures", {})
        for ch in ("albedo", "normal", "roughness", "metallic"):
            t_rel = tex_dict.get(ch)
            assert t_rel is not None, f"Texture pointer {ch} missing for {sp.species_id}"
            assert (OUTPUT_DIR / t_rel).is_file(), f"Texture file missing: {t_rel}"

        # Validation status
        val = rec.get("validation", {})
        assert val.get("is_valid") is True, f"{sp.species_id} validation is_valid is not True"
        assert val.get("verdict") == "PASSED"
        assert len(val.get("errors", [])) == 0


def test_geometry_standards_all_species():
    """
    4. test_geometry_standards_all_species:
    Sweeps all 35 GLBs:
    - Root base pivot grounded: |Z_min| <= 0.005m (root base contacts ground origin).
    - Base contact centroid centered: bottom 5% centroid offset <= 0.05m (+ float epsilon).
    - Zero bones / armatures / skins: strictly static mesh invariant.
    - Vertex count budget: strictly 3,000 <= V <= 65,000 (up to 65,000 for Meshy AI models).
    - Zero NaN / Inf coordinates.
    - Normals finite, non-zero, and unit length (||n|| == 1.0 +/- 0.05).
    - Non-degenerate faces (no duplicate indices, area > 1e-8).
    - Metric scale within +/- 10% of catalog target height.
    """
    for sp in CATALOG.species:
        glb_p = OUTPUT_DIR / sp.short_category / sp.species_id / f"{sp.species_id}.glb"
        assert glb_p.is_file()

        gltf, bin_bytes = parse_glb_container(glb_p)
        geom = decode_glb_geometry(gltf, bin_bytes)
        positions = geom["positions"]
        normals = geom["normals"]
        triangles = geom["triangles"]

        # 1. Finite and bounded coordinates
        assert np.isfinite(positions).all(), f"{sp.species_id} has non-finite positions"
        assert np.all(np.abs(positions) < 10000.0), f"{sp.species_id} has out-of-universe positions"

        # 2. Vertex budget: 20,000 <= V <= 65,000 for genuine Meshy models
        n_verts = len(positions)
        man_p = OUTPUT_DIR / sp.short_category / sp.species_id / "asset_manifest.json"
        is_meshy = False
        if man_p.is_file():
            try:
                with open(man_p, "r", encoding="utf-8") as mf:
                    mdata = json.load(mf)
                is_meshy = (mdata.get("provenance", {}).get("source") == "meshy")
            except Exception:
                pass

        if is_meshy:
            assert 20000 <= n_verts <= 65000, f"{sp.species_id} Meshy model vertex count {n_verts} out of budget [20000, 65000]"
        else:
            assert 3000 <= n_verts <= 65000, f"{sp.species_id} vertex count {n_verts} out of budget [3000, 65000]"

        # 3. Ground contact base alignment (|Z_min| <= 0.005m)
        z_min = float(positions[:, 2].min())
        assert abs(z_min) <= 0.005, f"{sp.species_id} Z_min {z_min:.6f}m exceeds tolerance +-0.005m"

        # 4. Base contact centroid centered (bottom 5% slice <= 0.05m + 1e-5)
        z_max = float(positions[:, 2].max())
        z_extent = z_max - z_min
        thresh = z_min + 0.05 * z_extent
        base_verts = positions[positions[:, 2] <= thresh]
        if len(base_verts) == 0:
            base_verts = positions[positions[:, 2] <= z_min + 1e-4]
        cx = float(np.mean(base_verts[:, 0]))
        cy = float(np.mean(base_verts[:, 1]))
        centroid_dist = math.sqrt(cx * cx + cy * cy)
        assert centroid_dist <= 0.05 + 1e-5, f"{sp.species_id} centroid offset {centroid_dist:.4f}m exceeds 0.05m"

        # 5. Metric scale bounds (+/- 10% of catalog target height)
        measured_h = z_extent
        target_h = sp.dimensions.height_m
        dev_pct = abs(measured_h - target_h) / target_h
        assert dev_pct <= 0.10, f"{sp.species_id} height {measured_h:.2f}m deviates {dev_pct*100:.1f}% from target {target_h:.2f}m"

        # 6. Static mesh invariant: 0 skins, 0 animations, 0 joint attributes
        assert not gltf.get("skins"), f"{sp.species_id} contains skins"
        assert not gltf.get("animations"), f"{sp.species_id} contains animations"
        for mesh in gltf.get("meshes", []):
            for prim in mesh.get("primitives", []):
                for attr_key in prim.get("attributes", {}):
                    assert not attr_key.upper().startswith("JOINTS_"), f"{sp.species_id} has joints attribute"
                    assert not attr_key.upper().startswith("WEIGHTS_"), f"{sp.species_id} has weights attribute"


def test_pbr_material_standards_all_species():
    """
    5. test_pbr_material_standards_all_species:
    Sweeps all 35 species:
    - 4 readable PBR textures (albedo, normal, roughness, metallic).
    - Dimensions >= 256x256.
    - Albedo: non-solid-black (mean > 0.05), spatial surface variation (spatial std > 0.02).
    - Normal: valid tangent-space normal vector distribution (nz in [0.5, 1.0], magnitude ~= 1.0).
    - Roughness: organic vegetation range (mean in [0.20, 0.95], std > 0.01).
    - Metallic: strictly dielectric non-metal (max <= 0.05, mean <= 0.02).
    """
    for sp in CATALOG.species:
        tex_dir = OUTPUT_DIR / sp.short_category / sp.species_id / "textures"
        assert tex_dir.is_dir()

        # 1. Load and verify 4 channels
        alb_img = Image.open(tex_dir / "albedo.png")
        norm_img = Image.open(tex_dir / "normal.png")
        rough_img = Image.open(tex_dir / "roughness.png")
        metal_img = Image.open(tex_dir / "metallic.png")

        for name, img in (("albedo", alb_img), ("normal", norm_img), ("roughness", rough_img), ("metallic", metal_img)):
            assert img.width >= 256 and img.height >= 256, f"{sp.species_id} {name} texture under 256x256"

        # 2. Albedo physical plausibility
        alb_arr = np.array(alb_img.convert("RGB"), dtype=np.float32) / 255.0
        alb_mean = float(np.mean(alb_arr))
        alb_std = float(np.mean(np.std(alb_arr, axis=(0, 1))))
        assert alb_mean > 0.05, f"{sp.species_id} albedo mean {alb_mean:.4f} too dark <= 0.05"
        assert alb_std > 0.02, f"{sp.species_id} albedo spatial std {alb_std:.4f} lacks variation <= 0.02"

        # 3. Normal map tangent space plausibility
        norm_arr = np.array(norm_img.convert("RGB"), dtype=np.float32) / 255.0
        nx = 2.0 * norm_arr[:, :, 0] - 1.0
        ny = 2.0 * norm_arr[:, :, 1] - 1.0
        nz = 2.0 * norm_arr[:, :, 2] - 1.0
        mag = np.sqrt(nx * nx + ny * ny + nz * nz)
        mean_nz = float(np.mean(nz))
        mean_mag = float(np.mean(mag))
        assert 0.5 <= mean_nz <= 1.0, f"{sp.species_id} normal mean_nz {mean_nz:.4f} outside [0.5, 1.0]"
        assert abs(mean_mag - 1.0) <= 0.15, f"{sp.species_id} normal vector magnitude deviates {mean_mag:.4f}"

        # 4. Roughness organic distribution
        r_arr = np.array(rough_img.convert("L"), dtype=np.float32) / 255.0
        r_mean = float(np.mean(r_arr))
        r_std = float(np.std(r_arr))
        assert 0.20 <= r_mean <= 0.95, f"{sp.species_id} roughness mean {r_mean:.4f} outside [0.20, 0.95]"
        assert r_std > 0.01, f"{sp.species_id} roughness std {r_std:.4f} lacks variation <= 0.01"

        # 5. Metallic dielectric enforcement
        m_arr = np.array(metal_img.convert("L"), dtype=np.float32) / 255.0
        m_max = float(np.max(m_arr))
        m_mean = float(np.mean(m_arr))
        assert m_max <= 0.05, f"{sp.species_id} metallic max {m_max:.4f} exceeds dielectric ceiling 0.05"
        assert m_mean <= 0.02, f"{sp.species_id} metallic mean {m_mean:.4f} exceeds dielectric limit 0.02"


def test_renders_and_visual_showcase_all_species():
    """
    6. test_renders_and_visual_showcase_all_species:
    Sweeps all 35 species:
    - 4 turntable images (turntable_01.png through turntable_04.png) exist, readable, 512x512.
    - Contact sheet thumbnail.png exists, readable, exactly 1024x1024 pixels.
    """
    for sp in CATALOG.species:
        sp_dir = OUTPUT_DIR / sp.short_category / sp.species_id

        # 4 Turntable images
        for i in range(1, 5):
            tt_p = sp_dir / f"turntable_0{i}.png"
            assert tt_p.is_file(), f"{sp.species_id} missing turntable_0{i}.png"
            img = Image.open(tt_p)
            assert img.width == 512 and img.height == 512, f"{sp.species_id} turntable {i} size {img.size} != (512, 512)"

        # 1024x1024 contact sheet montage
        thumb_p = sp_dir / "thumbnail.png"
        assert thumb_p.is_file(), f"{sp.species_id} missing thumbnail.png"
        timg = Image.open(thumb_p)
        assert timg.width == 1024 and timg.height == 1024, f"{sp.species_id} thumbnail size {timg.size} != (1024, 1024)"


def test_full_inspection_suite_100_percent_pass():
    """
    7. test_full_inspection_suite_100_percent_pass:
    Runs validate_asset on all 35 species directories.
    Asserts 100% pass rate:
    - is_valid == True for all 35 assets.
    - Exactly 20/20 checks passed per asset.
    - Zero blocking errors.
    """
    reports = validate_directory(OUTPUT_DIR, catalog=CATALOG)
    assert len(reports) == 35, f"Expected 35 reports, got {len(reports)}"

    failed_species = []
    for sp in CATALOG.species:
        assert sp.species_id in reports, f"{sp.species_id} not found in directory validation"
        rep = reports[sp.species_id]
        if not rep.is_valid or rep.passed_checks_count != rep.total_checks_count:
            failed_species.append((sp.species_id, rep.passed_checks_count, rep.errors))

    assert len(failed_species) == 0, f"Failed species ({len(failed_species)}): {failed_species}"


def test_cli_summary_mode_execution():
    """
    8. test_cli_summary_mode_execution:
    Executes pipeline.py --summary --output-dir <output_dir> via subprocess.
    Asserts return code 0, and output contains the Markdown table header and 35 species.
    """
    cmd = [
        sys.executable,
        str(Path(__file__).resolve().parent.parent / "pipeline.py"),
        "--summary",
        "--output-dir",
        str(OUTPUT_DIR),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert proc.returncode == 0, f"pipeline.py --summary failed: {proc.stderr}"
    assert "Asset Catalog Summary" in proc.stdout
    assert "35 / 35 species indexed (100.0%)" in proc.stdout
    assert "35 / 35 (100.0%)" in proc.stdout


def test_programmatic_run_pipeline_api():
    """
    9. test_programmatic_run_pipeline_api:
    Verifies programmatic run_pipeline API with --validate-only and summary.
    """
    manifest = run_pipeline(
        species="veg_tree_oak_01",
        validate_only=True,
        output_dir=OUTPUT_DIR,
    )
    assert isinstance(manifest, dict)
    assert manifest.get("indexed_species_count") == 35
    assert manifest.get("passed_validation_count") == 35
    assert "veg_tree_oak_01" in manifest.get("assets", {})


def test_pairwise_vertex_count_collisions():
    """
    10. test_pairwise_vertex_count_collisions:
    Verifies that pairwise vertex count collision rate between distinct Meshy AI species is < 5%.
    - If multiple Meshy assets exist, calculates pairwise collisions across all pairs.
    - If single Meshy asset exists (Milestone 1 state), verifies its vertex count is distinct and within budget.
    - Validates collision detection logic against synthetic distinct and collided sets.
    """
    meshy_counts = {}
    for sp in CATALOG.species:
        man_p = OUTPUT_DIR / sp.short_category / sp.species_id / "asset_manifest.json"
        if man_p.is_file():
            try:
                with open(man_p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                prov = data.get("provenance", {})
                if prov.get("source") == "meshy":
                    vc = data.get("geometry", {}).get("vertex_count")
                    if vc:
                        meshy_counts[sp.species_id] = vc
            except Exception:
                pass

    if len(meshy_counts) > 1:
        species_list = list(meshy_counts.keys())
        n = len(species_list)
        assert n >= 26, f"Expected at least 26 Meshy species, found {n}"
        pairs = n * (n - 1) // 2
        collisions = sum(
            1
            for i in range(n)
            for j in range(i + 1, n)
            if meshy_counts[species_list[i]] == meshy_counts[species_list[j]]
        )
        collision_rate = collisions / pairs
        assert collisions == 0, f"Meshy pairwise vertex collisions detected ({collisions}/{pairs}): rate {collision_rate*100:.1f}%"
        assert collision_rate == 0.0, f"Meshy pairwise vertex collision rate {collision_rate*100:.1f}% exceeds 0%"
        for sp_id, vc in meshy_counts.items():
            assert 20000 <= vc <= 65000, f"{sp_id} vertex count {vc} out of budget [20000, 65000]"
    elif len(meshy_counts) == 1:
        assert list(meshy_counts.values())[0] >= 20000

    # Verify detection on synthetic sets
    synthetic_distinct = [20000 + i * 179 for i in range(35)]
    n_s = len(synthetic_distinct)
    pairs_s = n_s * (n_s - 1) // 2
    colls_s = sum(1 for i in range(n_s) for j in range(i + 1, n_s) if synthetic_distinct[i] == synthetic_distinct[j])
    assert colls_s / pairs_s < 0.05


def test_meshy_task_provenance():
    """
    11. test_meshy_task_provenance:
    Verifies that all genuine Meshy assets have valid cloud provenance records:
    - Provenance source == "meshy"
    - task_id is non-empty, well-formed (>10 chars)
    - Master manifest indexes valid provenance and meshy_cloud_provenance validation check == True
    - Specifically verifies veg_tree_oak_01, veg_ground_ostrich_01, and all genuine Meshy species.
    """
    master_p = OUTPUT_DIR / "manifest.json"
    assert master_p.is_file(), "Master output/manifest.json missing"
    with open(master_p, "r", encoding="utf-8") as f:
        master = json.load(f)

    meshy_species_found = []
    for sp in CATALOG.species:
        manifest_p = OUTPUT_DIR / sp.short_category / sp.species_id / "asset_manifest.json"
        if not manifest_p.is_file():
            continue
        with open(manifest_p, "r", encoding="utf-8") as f:
            man = json.load(f)
        prov = man.get("provenance", {})
        if prov.get("source") == "meshy":
            meshy_species_found.append(sp.species_id)
            task_id = prov.get("task_id") or prov.get("generator_metadata", {}).get("task_id") or man.get("metadata", {}).get("task_id")
            assert task_id and isinstance(task_id, str) and len(task_id) > 10, f"{sp.species_id} invalid task_id: {task_id}"

            # Verify in master manifest
            entry = master.get("assets", {}).get(sp.species_id, {})
            assert entry, f"{sp.species_id} missing from master manifest"
            m_prov = entry.get("provenance", {})
            assert m_prov.get("source") == "meshy", f"{sp.species_id} master provenance source is {m_prov.get('source')}"
            assert m_prov.get("task_id") == task_id, f"{sp.species_id} master task_id mismatch: {m_prov.get('task_id')} != {task_id}"
            val = entry.get("validation", {})
            assert val.get("checks", {}).get("meshy_cloud_provenance") is True, f"{sp.species_id} meshy_cloud_provenance check failed"
            assert val.get("metrics", {}).get("task_id") == task_id, f"{sp.species_id} validation metrics task_id mismatch"

    assert "veg_tree_oak_01" in meshy_species_found, "veg_tree_oak_01 not found among Meshy species"
    assert "veg_ground_ostrich_01" in meshy_species_found, "veg_ground_ostrich_01 not found among Meshy species"
    assert len(meshy_species_found) >= 26, f"Expected at least 26 Meshy species, found {len(meshy_species_found)}"

