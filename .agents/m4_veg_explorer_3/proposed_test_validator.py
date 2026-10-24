"""
MorphoMesh Vegetation Library - Automated QA Validator Test Suite
Target File: teamwork_projects/vegetation_library/tests/test_validator.py

Comprehensive unit and integration test suite covering 12 critical QA scenarios:
1.  test_valid_asset_passes_all_checks
2.  test_vertex_count_under_budget_fails
3.  test_vertex_count_over_budget_fails
4.  test_ungrounded_pivot_fails
5.  test_uncentered_centroid_fails
6.  test_nan_inf_coordinates_fails
7.  test_armature_or_skinning_fails
8.  test_solid_black_texture_fails
9.  test_missing_texture_channel_fails
10. test_non_dielectric_metallic_fails
11. test_corrupt_glb_fails
12. test_validate_directory
"""
from __future__ import annotations

import io
import json
import math
import os
from pathlib import Path
import shutil
import struct
import sys
from typing import Any, Dict, Tuple

import numpy as np
from PIL import Image
import pytest

# Ensure sys.path includes project directories and m4_veg_explorer_1
TEST_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TEST_DIR if (TEST_DIR / "vegetation_pipeline").is_dir() else (TEST_DIR.parent.parent / "teamwork_projects" / "vegetation_library")
REPO_ROOT = PROJECT_DIR.parent.parent

for p in (str(PROJECT_DIR), str(REPO_ROOT), str(REPO_ROOT / "src"), str(REPO_ROOT / ".agents" / "m4_veg_explorer_1")):
    if p not in sys.path:
        sys.path.insert(0, p)

from morphomesh.geometry.mesh import MeshGeometry
from vegetation_pipeline.catalog import get_catalog, get_species
from vegetation_pipeline.generator import (
    RawAsset,
    generate_plant,
    unpack_glb_header_and_json,
)
from vegetation_pipeline.post_processor import (
    AssetDimensions,
    ExportedAsset,
    PostProcessorConfig,
    export_production_glb,
    process_and_export,
)

try:
    from vegetation_pipeline.validator import (
        ValidationReport,
        validate_asset,
        validate_directory,
    )
except ImportError:
    from proposed_validator import (
        ValidationReport,
        validate_asset,
        validate_directory,
    )


# ==============================================================================
# TEST FIXTURES & SYNTHETIC ASSET BUILDERS
# ==============================================================================

def make_valid_test_textures() -> Dict[str, Image.Image]:
    """Generates standard compliant 64x64 PBR texture maps."""
    # Albedo: greenish organic field with standard deviation > 0.02
    np.random.seed(42)
    base_col = np.array([80, 140, 50], dtype=np.float32)
    noise = np.random.uniform(-20, 20, (64, 64, 3))
    alb_data = np.clip(base_col + noise, 0, 255).astype(np.uint8)
    albedo = Image.fromarray(alb_data, mode="RGB")

    # Normal: flat tangent-space (128, 128, 255)
    normal = Image.new("RGB", (64, 64), (128, 128, 255))

    # Roughness: organic mean ~0.60, non-zero variance
    r_data = np.clip(np.random.normal(150, 15, (64, 64)), 50, 240).astype(np.uint8)
    roughness = Image.fromarray(r_data, mode="L")

    # Metallic: strictly dielectric (zeros)
    metallic = Image.new("L", (64, 64), 0)

    return {
        "albedo": albedo,
        "normal": normal,
        "roughness": roughness,
        "metallic": metallic,
    }


def make_synthetic_mesh(
    target_vertices: int,
    height: float = 3.0,
    radius: float = 0.5,
    z_offset: float = 0.0,
    x_offset: float = 0.0,
    inject_nan: bool = False,
) -> MeshGeometry:
    """
    Constructs a deterministic synthetic cylindrical/prismatic mesh with an exact or
    approximate vertex count, grounded at Z_min = z_offset.
    """
    mesh = MeshGeometry()
    nx = max(4, int(math.isqrt(target_vertices)))
    ny = max(2, (target_vertices + nx - 1) // nx)

    verts_added = 0
    grid = []

    for iy in range(ny):
        row = []
        fraction_y = iy / max(ny - 1, 1)
        z = z_offset + fraction_y * height
        theta_ring = fraction_y * 2.0 * math.pi

        for ix in range(nx):
            if verts_added >= target_vertices:
                break
            angle = (ix / nx) * 2.0 * math.pi
            x = x_offset + math.cos(angle) * radius
            y = math.sin(angle) * radius

            if inject_nan and verts_added == 0:
                pos = (float("nan"), y, z)
            else:
                pos = (round(x, 5), round(y, 5), round(z, 5))

            norm = (math.cos(angle), math.sin(angle), 0.0)
            uv = (ix / nx, fraction_y)
            mesh.add_vertex(pos, norm, uv)
            row.append(verts_added)
            verts_added += 1

        if row:
            grid.append(row)

    # Triangulate grid rings
    for iy in range(len(grid) - 1):
        r1 = grid[iy]
        r2 = grid[iy + 1]
        common_len = min(len(r1), len(r2))
        for ix in range(common_len):
            nxt = (ix + 1) % common_len
            i0 = r1[ix]
            i1 = r1[nxt]
            i2 = r2[nxt]
            i3 = r2[ix]
            mesh.add_triangle(i0, i1, i2)
            mesh.add_triangle(i0, i2, i3)

    return mesh


def repack_glb_json(
    source_glb: Path,
    dest_glb: Path,
    modifier_fn,
) -> Path:
    """Unpacks GLB, modifies its JSON chunk dictionary, and repacks it."""
    gltf, bin_bytes = unpack_glb_header_and_json(source_glb)
    modifier_fn(gltf)

    json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    json_pad = (4 - (len(json_bytes) % 4)) % 4
    json_bytes += b" " * json_pad

    total_len = 12 + (8 + len(json_bytes)) + (8 + len(bin_bytes))
    hdr = struct.pack("<4sII", b"glTF", 2, total_len)
    c0 = struct.pack("<I4s", len(json_bytes), b"JSON")
    c1 = struct.pack("<I4s", len(bin_bytes), b"BIN\x00")

    dest_glb.parent.mkdir(parents=True, exist_ok=True)
    with open(dest_glb, "wb") as f:
        f.write(hdr + c0 + json_bytes + c1 + bin_bytes)

    return dest_glb


# ==============================================================================
# 12 QA TEST SCENARIOS
# ==============================================================================

def test_valid_asset_passes_all_checks(tmp_path: Path):
    """
    1. test_valid_asset_passes_all_checks:
    Generates a genuine procedural plant asset, post-processes it, and asserts that
    validate_asset returns is_valid == True, 0 errors, and all checks pass.
    """
    species = get_species("veg_tree_oak_01")
    raw = generate_plant(species, mode="procedural", seed=42)
    exported = process_and_export(raw, species, output_dir=tmp_path / "valid_oak")

    report = validate_asset(exported)

    assert report.is_valid is True, f"Valid asset failed validation with errors: {report.errors}"
    assert len(report.errors) == 0
    assert report.species_id == "veg_tree_oak_01"
    assert report.checks.get("vertex_count_budget") is True
    assert report.checks.get("ground_contact_base_aligned") is True
    assert report.checks.get("base_contact_centroid_centered") is True
    assert report.checks.get("zero_nan_inf_coordinates") is True
    assert report.checks.get("n_bones_strictly_zero") is True
    assert report.checks.get("textures_channels_present") is True
    assert report.checks.get("texture_metallic_dielectric") is True

    # Assert validating by path directory also passes
    dir_report = validate_asset(exported.glb_path.parent)
    assert dir_report.is_valid is True


def test_vertex_count_under_budget_fails(tmp_path: Path):
    """
    2. test_vertex_count_under_budget_fails:
    Mocks a mesh with 1,500 vertices (< 3,000 budget), asserts validation fails
    with descriptive error mentioning vertex budget.
    """
    mesh = make_synthetic_mesh(target_vertices=1500, height=12.0)
    textures = make_valid_test_textures()
    glb_p = export_production_glb(mesh, tmp_path / "under_budget" / "veg_tree_oak_01.glb", textures, species_id="veg_tree_oak_01")

    report = validate_asset(glb_p)

    assert report.is_valid is False
    assert report.checks.get("vertex_count_budget") is False
    assert any("under budget" in err.lower() or "minimum" in err.lower() for err in report.errors)


def test_vertex_count_over_budget_fails(tmp_path: Path):
    """
    3. test_vertex_count_over_budget_fails:
    Mocks a mesh with 50,000 vertices (> 45,000 budget), asserts validation fails.
    """
    mesh = make_synthetic_mesh(target_vertices=50000, height=12.0)
    textures = make_valid_test_textures()
    glb_p = export_production_glb(mesh, tmp_path / "over_budget" / "veg_tree_oak_01.glb", textures, species_id="veg_tree_oak_01")

    report = validate_asset(glb_p)

    assert report.is_valid is False
    assert report.checks.get("vertex_count_budget") is False
    assert any("over budget" in err.lower() or "maximum" in err.lower() for err in report.errors)


def test_ungrounded_pivot_fails(tmp_path: Path):
    """
    4. test_ungrounded_pivot_fails:
    Shifts mesh vertices up by +1.0m (Z_min = 1.0m > 0.005m tolerance), asserts
    ground contact pivot check fails.
    """
    mesh = make_synthetic_mesh(target_vertices=4000, height=12.0, z_offset=1.0)
    textures = make_valid_test_textures()
    glb_p = export_production_glb(mesh, tmp_path / "ungrounded" / "veg_tree_oak_01.glb", textures, species_id="veg_tree_oak_01")

    report = validate_asset(glb_p)

    assert report.is_valid is False
    assert report.checks.get("ground_contact_base_aligned") is False
    assert any("ground" in err.lower() or "pivot" in err.lower() for err in report.errors)


def test_uncentered_centroid_fails(tmp_path: Path):
    """
    5. test_uncentered_centroid_fails:
    Shifts mesh horizontally by +0.5m (base contact centroid X = 0.5m > 0.05m tolerance),
    asserts base contact centroid centering check fails.
    """
    mesh = make_synthetic_mesh(target_vertices=4000, height=12.0, x_offset=0.5)
    textures = make_valid_test_textures()
    glb_p = export_production_glb(mesh, tmp_path / "uncentered" / "veg_tree_oak_01.glb", textures, species_id="veg_tree_oak_01")

    report = validate_asset(glb_p)

    assert report.is_valid is False
    assert report.checks.get("base_contact_centroid_centered") is False
    assert any("centroid" in err.lower() or "center" in err.lower() for err in report.errors)


def test_nan_inf_coordinates_fails(tmp_path: Path):
    """
    6. test_nan_inf_coordinates_fails:
    Injects NaN into vertex coordinates, asserts validation fails with NaN/Inf detection.
    """
    mesh = make_synthetic_mesh(target_vertices=4000, height=12.0, inject_nan=True)
    textures = make_valid_test_textures()
    glb_p = export_production_glb(mesh, tmp_path / "nan_coords" / "veg_tree_oak_01.glb", textures, species_id="veg_tree_oak_01")

    report = validate_asset(glb_p)

    assert report.is_valid is False
    assert report.checks.get("zero_nan_inf_coordinates") is False
    assert any("nan" in err.lower() or "inf" in err.lower() for err in report.errors)


def test_armature_or_skinning_fails(tmp_path: Path):
    """
    7. test_armature_or_skinning_fails:
    Injects joint/weight/skin data into GLB container, asserts zero-armature check fails.
    """
    # 1. Create a valid baseline GLB
    mesh = make_synthetic_mesh(target_vertices=4000, height=12.0)
    textures = make_valid_test_textures()
    base_glb = export_production_glb(mesh, tmp_path / "base" / "veg_tree_oak_01.glb", textures, species_id="veg_tree_oak_01")

    # 2. Repack with skeletal skinning and JOINTS_0 attribute
    def inject_rig(gltf: Dict[str, Any]):
        gltf["skins"] = [{"joints": [0, 1], "name": "FakeArmature"}]
        if "meshes" in gltf and gltf["meshes"]:
            for prim in gltf["meshes"][0].get("primitives", []):
                prim["attributes"]["JOINTS_0"] = 0
                prim["attributes"]["WEIGHTS_0"] = 0

    rigged_glb = tmp_path / "rigged" / "veg_tree_oak_01.glb"
    repack_glb_json(base_glb, rigged_glb, inject_rig)

    report = validate_asset(rigged_glb)

    assert report.is_valid is False
    assert (
        report.checks.get("static_mesh_no_skins") is False
        or report.checks.get("n_bones_strictly_zero") is False
        or report.checks.get("static_mesh_no_joint_weights") is False
    )
    assert any("skin" in err.lower() or "armature" in err.lower() or "joint" in err.lower() for err in report.errors)


def test_solid_black_texture_fails(tmp_path: Path):
    """
    8. test_solid_black_texture_fails:
    Replaces albedo map with solid black image (mean = 0.0 <= 0.05), asserts
    albedo physical plausibility check fails.
    """
    out_dir = tmp_path / "black_albedo"
    mesh = make_synthetic_mesh(target_vertices=4000, height=12.0)
    textures = make_valid_test_textures()
    # Replace albedo with solid black
    textures["albedo"] = Image.new("RGB", (64, 64), (0, 0, 0))
    glb_p = export_production_glb(mesh, out_dir / "veg_tree_oak_01.glb", textures, species_id="veg_tree_oak_01")

    # Also save discrete texture
    tex_dir = out_dir / "textures"
    tex_dir.mkdir(parents=True, exist_ok=True)
    textures["albedo"].save(tex_dir / "albedo.png")

    report = validate_asset(out_dir)

    assert report.is_valid is False
    assert report.checks.get("texture_albedo_plausible") is False
    assert any("black" in err.lower() or "dark" in err.lower() for err in report.errors)


def test_missing_texture_channel_fails(tmp_path: Path):
    """
    9. test_missing_texture_channel_fails:
    Creates an asset directory missing normal.png, asserts PBR channel completeness check fails.
    """
    out_dir = tmp_path / "missing_normal"
    mesh = make_synthetic_mesh(target_vertices=4000, height=12.0)
    textures = make_valid_test_textures()
    glb_p = export_production_glb(mesh, out_dir / "veg_tree_oak_01.glb", textures, species_id="veg_tree_oak_01")

    # Save only 3 of 4 channels to textures/
    tex_dir = out_dir / "textures"
    tex_dir.mkdir(parents=True, exist_ok=True)
    textures["albedo"].save(tex_dir / "albedo.png")
    textures["roughness"].save(tex_dir / "roughness.png")
    textures["metallic"].save(tex_dir / "metallic.png")
    # normal.png is deliberately omitted

    # Also unpack and strip normal texture from glb to test embedded fallback
    def strip_normal(gltf: Dict[str, Any]):
        for mat in gltf.get("materials", []):
            mat.pop("normalTexture", None)

    stripped_glb = out_dir / "veg_tree_oak_01.glb"
    repack_glb_json(glb_p, stripped_glb, strip_normal)

    report = validate_asset(out_dir)

    assert report.is_valid is False
    assert report.checks.get("textures_channels_present") is False
    assert any("normal" in err.lower() or "missing" in err.lower() for err in report.errors)


def test_non_dielectric_metallic_fails(tmp_path: Path):
    """
    10. test_non_dielectric_metallic_fails:
    Replaces metallic map with 1.0 (pure metal, e.g. pixel value 255), asserts
    dielectric vegetation material rule fails.
    """
    out_dir = tmp_path / "metallic_plant"
    mesh = make_synthetic_mesh(target_vertices=4000, height=12.0)
    textures = make_valid_test_textures()
    # Replace metallic with 255 (metal)
    textures["metallic"] = Image.new("L", (64, 64), 255)
    glb_p = export_production_glb(mesh, out_dir / "veg_tree_oak_01.glb", textures, species_id="veg_tree_oak_01")

    tex_dir = out_dir / "textures"
    tex_dir.mkdir(parents=True, exist_ok=True)
    textures["albedo"].save(tex_dir / "albedo.png")
    textures["normal"].save(tex_dir / "normal.png")
    textures["roughness"].save(tex_dir / "roughness.png")
    textures["metallic"].save(tex_dir / "metallic.png")

    report = validate_asset(out_dir)

    assert report.is_valid is False
    assert report.checks.get("texture_metallic_dielectric") is False
    assert any("metallic" in err.lower() or "dielectric" in err.lower() for err in report.errors)


def test_corrupt_glb_fails(tmp_path: Path):
    """
    11. test_corrupt_glb_fails:
    Passes a truncated and invalid binary file, asserts validation fails gracefully
    without unhandled crashes or exceptions.
    """
    corrupt_p = tmp_path / "corrupt_species" / "corrupt_plant.glb"
    corrupt_p.parent.mkdir(parents=True, exist_ok=True)
    corrupt_p.write_bytes(b"glTF\x02\x00\x00\x00truncated_garbage_data")

    report = validate_asset(corrupt_p)

    assert report.is_valid is False
    assert report.checks.get("glb_container_valid") is False
    assert len(report.errors) > 0
    assert any("corrupted" in err.lower() or "unparseable" in err.lower() or "container" in err.lower() for err in report.errors)


def test_validate_directory(tmp_path: Path):
    """
    12. test_validate_directory:
    Tests batch validation across multiple species directories:
    - 2 valid species (English Oak, Scots Pine)
    - 1 invalid species (under-budget vertex count)
    Asserts validate_directory returns correctly mapped ValidationReport dictionary.
    """
    root_dir = tmp_path / "multi_species_batch"

    # Asset 1: Valid English Oak
    sp1 = get_species("veg_tree_oak_01")
    raw1 = generate_plant(sp1, mode="procedural", seed=42)
    process_and_export(raw1, sp1, output_dir=root_dir / "broadleaf_trees" / "veg_tree_oak_01")

    # Asset 2: Valid Scots Pine
    sp2 = get_species("veg_conifer_pine_01")
    raw2 = generate_plant(sp2, mode="procedural", seed=43)
    process_and_export(raw2, sp2, output_dir=root_dir / "conifers" / "veg_conifer_pine_01")

    # Asset 3: Defective species (under-budget)
    defective_dir = root_dir / "shrubs" / "veg_shrub_boxwood_01"
    defective_dir.mkdir(parents=True, exist_ok=True)
    m_bad = make_synthetic_mesh(target_vertices=1200, height=1.5)
    tex = make_valid_test_textures()
    export_production_glb(m_bad, defective_dir / "veg_shrub_boxwood_01.glb", tex, species_id="veg_shrub_boxwood_01")

    # Execute batch validation
    reports = validate_directory(root_dir)

    assert len(reports) >= 3
    assert "veg_tree_oak_01" in reports
    assert "veg_conifer_pine_01" in reports
    assert "veg_shrub_boxwood_01" in reports

    assert reports["veg_tree_oak_01"].is_valid is True
    assert reports["veg_conifer_pine_01"].is_valid is True
    assert reports["veg_shrub_boxwood_01"].is_valid is False
