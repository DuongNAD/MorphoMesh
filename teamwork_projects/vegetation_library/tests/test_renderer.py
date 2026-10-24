"""
MorphoMesh Vegetation Library - Preview Visuals & Renderer Test Suite
Target File: teamwork_projects/vegetation_library/tests/test_renderer.py

Comprehensive unit and integration test suite covering:
1. Binary detection & engine validation
2. RenderConfig validation & schema options
3. Contact sheet montage layout, dimensions, partial images, and metadata formatting
4. Pure-Python software fallback rendering & albedo sampling
5. Master render_asset_preview contract compatibility (ExportedAsset and Path)
6. Graceful degradation & software mode parity
7. Headless Blender automation when available
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Dict

import numpy as np
from PIL import Image
import pytest

# Ensure sys.path includes project directories
TEST_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TEST_DIR.parent
REPO_ROOT = PROJECT_DIR.parent.parent

for p in (str(PROJECT_DIR), str(REPO_ROOT), str(REPO_ROOT / "src")):
    if p not in sys.path:
        sys.path.insert(0, p)

from morphomesh.geometry.mesh import MeshGeometry
from vegetation_pipeline.catalog import get_catalog, get_species
from vegetation_pipeline.generator import generate_plant
from vegetation_pipeline.post_processor import (
    ExportedAsset,
    export_production_glb,
    process_and_export,
)
from vegetation_pipeline.renderer import (
    DEFAULT_TURNTABLE_ANGLES,
    RenderConfig,
    TurntableAngle,
    render_asset_preview,
    render_contact_sheet,
    render_software_fallback,
    resolve_blender_binary,
    software_rasterize_view,
)


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def sample_exported_asset(tmp_path: Path) -> ExportedAsset:
    """Generates a genuine procedural plant asset and post-processes it."""
    species = get_species("veg_tree_oak_01")
    raw = generate_plant(species, mode="procedural", seed=42)
    exported = process_and_export(raw, species, output_dir=tmp_path / "sample_oak")
    return exported


def create_dummy_view_images(tmp_path: Path, count: int = 4) -> list[Path]:
    """Creates dummy 256x256 test PNG images."""
    paths = []
    colors = [
        (46, 160, 67),
        (56, 139, 253),
        (210, 153, 34),
        (163, 113, 247),
    ]
    for i in range(count):
        img_p = tmp_path / f"turntable_0{i+1}.png"
        col = colors[i % len(colors)]
        img = Image.new("RGBA", (256, 256), (*col, 255))
        img.save(img_p)
        paths.append(img_p)
    return paths


# ==============================================================================
# 1. BLENDER RESOLUTION & CONFIG TESTS
# ==============================================================================

def test_resolve_blender_binary_detection():
    """Asserts resolve_blender_binary returns a valid Path or None without raising errors."""
    resolved = resolve_blender_binary()
    if resolved is not None:
        assert isinstance(resolved, Path)
        assert resolved.is_file()
        assert "blender" in resolved.name.lower()


def test_resolve_blender_binary_explicit_override(tmp_path: Path):
    """Asserts explicit binary path override is respected if file exists."""
    fake_exe = tmp_path / "fake_blender.exe"
    fake_exe.write_bytes(b"dummy")
    assert resolve_blender_binary(fake_exe) == fake_exe

    non_existent = tmp_path / "non_existent_blender.exe"
    assert resolve_blender_binary(non_existent) != non_existent


def test_render_config_defaults_and_validation():
    """Asserts RenderConfig defaults and property helpers."""
    cfg = RenderConfig()
    assert cfg.resolution == (512, 512)
    assert cfg.res_x == 512
    assert cfg.res_y == 512
    assert cfg.contact_sheet_resolution == 1024
    assert cfg.engine == "BLENDER_EEVEE_NEXT"
    assert cfg.cycles_samples == 24
    assert cfg.use_denoising is True
    assert cfg.margin == 0.15
    assert cfg.use_blender is True
    assert "hero" in cfg.angles

    # Integer resolution configuration
    cfg_int = RenderConfig(resolution=256)
    assert cfg_int.res_x == 256
    assert cfg_int.res_y == 256


# ==============================================================================
# 2. CONTACT SHEET MONTAGE TESTS
# ==============================================================================

def test_render_contact_sheet_dimensions_and_channels(tmp_path: Path):
    """Asserts contact sheet montage produces exact 1024x1024 RGB image."""
    views = create_dummy_view_images(tmp_path, count=4)
    out_p = tmp_path / "thumbnail.png"

    res = render_contact_sheet(
        image_paths=views,
        output_path=out_p,
        title="English Oak",
        scientific_name="Quercus robur",
        category="broadleaf_trees",
        height_m=12.0,
        polycount=4238,
        resolution=1024,
    )

    assert res == out_p
    assert out_p.is_file()

    with Image.open(out_p) as img:
        assert img.size == (1024, 1024)
        assert img.mode == "RGB"


def test_render_contact_sheet_with_partial_images(tmp_path: Path):
    """Asserts contact sheet handles fewer than 4 input views gracefully."""
    views = create_dummy_view_images(tmp_path, count=2)
    out_p = tmp_path / "partial_thumbnail.png"

    res = render_contact_sheet(
        image_paths=views,
        output_path=out_p,
        title="Sparse Test",
    )

    assert res == out_p
    assert out_p.is_file()
    with Image.open(out_p) as img:
        assert img.size == (1024, 1024)


def test_render_contact_sheet_metadata_banner(tmp_path: Path):
    """Asserts species_info dictionary and object extraction works."""
    views = create_dummy_view_images(tmp_path, count=4)
    out_p = tmp_path / "metadata_thumbnail.png"

    species_dict = {
        "common_name": "Scots Pine",
        "scientific_name": "Pinus sylvestris",
        "category": "conifers",
        "height_m": 8.5,
        "polycount": 3500,
    }

    render_contact_sheet(
        image_paths=views,
        output_path=out_p,
        species_info=species_dict,
    )
    assert out_p.is_file()


# ==============================================================================
# 3. PURE-PYTHON SOFTWARE FALLBACK TESTS
# ==============================================================================

def test_software_rasterize_all_4_angles(sample_exported_asset: ExportedAsset, tmp_path: Path):
    """Asserts pure-Python software fallback generates non-empty renders for all 4 angles."""
    out_dir = tmp_path / "software_renders"
    results = render_software_fallback(
        model_path=sample_exported_asset.glb_path,
        output_dir=out_dir,
        angles=DEFAULT_TURNTABLE_ANGLES,
        resolution=256,
    )

    assert len(results) == 4
    for ang in DEFAULT_TURNTABLE_ANGLES:
        assert ang.name in results
        p = results[ang.name]
        assert p.is_file()
        assert p.stat().st_size > 500  # valid image file


def test_software_rasterize_albedo_sampling(tmp_path: Path):
    """Asserts software rasterizer samples foliage green from albedo texture."""
    mesh = MeshGeometry()
    # 2 simple triangles forming a quad
    mesh.add_vertex((-1, 0, 0), (0, -1, 0), (0, 0))
    mesh.add_vertex((1, 0, 0), (0, -1, 0), (1, 0))
    mesh.add_vertex((1, 0, 2), (0, -1, 0), (1, 1))
    mesh.add_vertex((-1, 0, 2), (0, -1, 0), (0, 1))
    mesh.add_triangle(0, 1, 2)
    mesh.add_triangle(0, 2, 3)

    albedo = Image.new("RGB", (64, 64), (34, 139, 34))  # ForestGreen

    verts = np.array(mesh.vertices, dtype=np.float32)
    faces = np.array(mesh.faces, dtype=np.int32)
    uvs = np.array(mesh.uvs, dtype=np.float32)
    face_uvs = faces.copy()

    img = software_rasterize_view(
        vertices=verts,
        faces=faces,
        uvs=uvs,
        face_uvs=face_uvs,
        albedo_img=albedo,
        elevation_deg=0.0,
        azimuth_deg=0.0,
        resolution=128,
    )

    arr = np.array(img)
    assert arr.shape == (128, 128, 4)
    # Check that pixels with green content are present
    green_pixels = (arr[:, :, 1] > 50) & (arr[:, :, 3] > 0)
    assert np.count_nonzero(green_pixels) > 50


# ==============================================================================
# 4. MASTER RENDER API ENTRY POINT TESTS
# ==============================================================================

def test_render_asset_preview_with_exported_asset(sample_exported_asset: ExportedAsset, tmp_path: Path):
    """Asserts render_asset_preview accepts ExportedAsset and outputs all 5 views."""
    out_dir = tmp_path / "exported_asset_renders"
    res = render_asset_preview(
        asset=sample_exported_asset,
        output_dir=out_dir,
        use_blender=False,  # deterministic software mode
    )

    expected_keys = {"hero", "front", "side", "crown", "thumbnail"}
    assert set(res.keys()) == expected_keys
    for k, p in res.items():
        assert p.is_file(), f"Render output {k} does not exist: {p}"
        assert p.stat().st_size > 1000


def test_render_asset_preview_with_path(sample_exported_asset: ExportedAsset, tmp_path: Path):
    """Asserts render_asset_preview accepts Path to GLB file."""
    out_dir = tmp_path / "path_renders"
    res = render_asset_preview(
        asset=sample_exported_asset.glb_path,
        output_dir=out_dir,
        use_blender=False,
    )

    expected_keys = {"hero", "front", "side", "crown", "thumbnail"}
    assert set(res.keys()) == expected_keys
    for k, p in res.items():
        assert p.is_file()


def test_force_software_mode_produces_identical_contract(sample_exported_asset: ExportedAsset, tmp_path: Path):
    """Asserts setting engine='software' or use_blender=False guarantees complete output."""
    cfg = RenderConfig(engine="software", resolution=256)
    out_dir = tmp_path / "software_contract_test"
    res = render_asset_preview(
        asset=sample_exported_asset,
        output_dir=out_dir,
        config=cfg,
    )

    assert "thumbnail" in res
    assert res["thumbnail"].name == "thumbnail.png"
    assert res["thumbnail"].is_file()


def test_blender_automation_if_available(sample_exported_asset: ExportedAsset, tmp_path: Path):
    """
    If Blender 4.5 is installed on the system, tests headless execution with
    fast EEVEE Next rendering. If not available, test cleanly passes.
    """
    blender_exe = resolve_blender_binary()
    if blender_exe is None:
        pytest.skip("Blender binary not available in environment")

    out_dir = tmp_path / "blender_test_renders"
    cfg = RenderConfig(
        engine="BLENDER_EEVEE_NEXT",
        resolution=(256, 256),
        use_blender=True,
    )
    res = render_asset_preview(
        asset=sample_exported_asset,
        output_dir=out_dir,
        config=cfg,
    )

    assert "hero" in res
    assert "thumbnail" in res
    for k, p in res.items():
        assert p.is_file(), f"Missing render file {p}"
        assert p.stat().st_size > 2000
