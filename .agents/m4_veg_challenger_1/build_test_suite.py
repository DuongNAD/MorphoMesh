from pathlib import Path
target_path = Path(r'E:\tool\mcp\MorphoMesh\.agents\m4_veg_challenger_1\test_adversarial_m4.py')
code_parts = []
def add(s): code_parts.append(s)

add("""\"\"\"
Adversarial Stress Test Suite for MorphoMesh Vegetation Library - M4 Quality Assurance
Target: validator.py, pipeline.py
Challenger: M4 Veg Challenger 1
\"\"\"
from __future__ import annotations

import io
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
import warnings

import numpy as np
from PIL import Image
import pytest

CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent.parent
PROJECT_DIR = REPO_ROOT / "teamwork_projects" / "vegetation_library"

for p in (str(PROJECT_DIR), str(REPO_ROOT), str(REPO_ROOT / "src")):
    if p not in sys.path:
        sys.path.insert(0, p)

from morphomesh.geometry.mesh import MeshGeometry
from vegetation_pipeline.catalog import get_catalog, get_species
from vegetation_pipeline.generator import unpack_glb_header_and_json
from vegetation_pipeline.post_processor import export_production_glb
from vegetation_pipeline.validator import (
    ValidationReport,
    parse_glb_container,
    decode_glb_geometry,
    inspect_companion_obj,
    validate_geometry,
    validate_static_mesh_invariants,
    validate_pbr_textures,
    validate_asset,
    validate_directory,
)
""")
add("""
def make_valid_test_textures(size: int = 256) -> Dict[str, Image.Image]:
    np.random.seed(42)
    base_col = np.array([80, 140, 50], dtype=np.float32)
    noise = np.random.uniform(-20, 20, (size, size, 3))
    alb_data = np.clip(base_col + noise, 0, 255).astype(np.uint8)
    albedo = Image.fromarray(alb_data, mode="RGB")

    norm_data = np.full((size, size, 3), [128, 128, 245], dtype=np.uint8)
    norm_noise = np.random.randint(-4, 5, (size, size, 2))
    norm_data[:, :, 0] = np.clip(norm_data[:, :, 0] + norm_noise[:, :, 0], 0, 255)
    norm_data[:, :, 1] = np.clip(norm_data[:, :, 1] + norm_noise[:, :, 1], 0, 255)
    normal = Image.fromarray(norm_data, mode="RGB")

    r_data = np.clip(np.random.normal(150, 15, (size, size)), 50, 240).astype(np.uint8)
    roughness = Image.fromarray(r_data, mode="L")
    metallic = Image.new("L", (size, size), 0)

    return {
        "albedo": albedo,
        "normal": normal,
        "roughness": roughness,
        "metallic": metallic,
    }


def make_synthetic_mesh(
    target_vertices: int,
    height: float = 10.0,
    radius: float = 0.5,
    z_offset: float = 0.0,
    x_offset: float = 0.0,
    y_offset: float = 0.0,
    inject_nan: bool = False,
    inject_pos_inf: bool = False,
    inject_neg_inf: bool = False,
    extreme_coord: Optional[float] = None,
    duplicate_indices_face: bool = False,
    zero_area_face: bool = False,
    zero_normal: bool = False,
    non_unit_normal: bool = False,
    nan_normal: bool = False,
    inf_normal: bool = False,
) -> MeshGeometry:
    mesh = MeshGeometry()
    if target_vertices <= 0:
        return mesh

    nx = max(4, int(math.isqrt(target_vertices)))
    ny = max(2, (target_vertices + nx - 1) // nx)

    verts_added = 0
    grid = []

    for iy in range(ny):
        row = []
        frac = iy / max(ny - 1, 1)
        z = z_offset + frac * height

        for ix in range(nx):
            if verts_added >= target_vertices:
                break
            angle = (ix / nx) * 2.0 * math.pi
            x = x_offset + math.cos(angle) * radius
            y = y_offset + math.sin(angle) * radius

            if inject_nan and verts_added == 0:
                pos = (float("nan"), y, z)
            elif inject_pos_inf and verts_added == 0:
                pos = (float("inf"), y, z)
            elif inject_neg_inf and verts_added == 0:
                pos = (float("-inf"), y, z)
            elif extreme_coord is not None and verts_added == 0:
                pos = (extreme_coord, y, z)
            else:
                pos = (round(x, 5), round(y, 5), round(z, 5))

            if nan_normal and verts_added == 0:
                norm = (float("nan"), 0.0, 1.0)
            elif inf_normal and verts_added == 0:
                norm = (float("inf"), 0.0, 1.0)
            elif zero_normal and verts_added == 0:
                norm = (0.0, 0.0, 0.0)
            elif non_unit_normal and verts_added == 0:
                norm = (2.0, 0.0, 0.0)
            else:
                norm = (math.cos(angle), math.sin(angle), 0.0)

            uv = (ix / nx, frac)
            mesh.add_vertex(pos, norm, uv)
            row.append(verts_added)
            verts_added += 1

        if row:
            grid.append(row)

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

            if duplicate_indices_face and iy == 0 and ix == 0:
                mesh.add_triangle(i0, i0, i2)
            elif zero_area_face and iy == 0 and ix == 0:
                mesh.add_triangle(i0, i0, i0)
            else:
                mesh.add_triangle(i0, i1, i2)
            mesh.add_triangle(i0, i2, i3)

    return mesh
""")
add("""
def repack_glb_json(
    source_glb: Path,
    dest_glb: Path,
    modifier_fn: Callable[[Dict[str, Any]], None],
) -> Path:
    gltf, bin_bytes = unpack_glb_header_and_json(source_glb)
    modifier_fn(gltf)

    json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    json_pad = (4 - (len(json_bytes) % 4)) % 4
    json_bytes += b" " * json_pad

    total_len = 12 + (8 + len(json_bytes)) + (8 + len(bin_bytes))
    hdr = struct.pack("<4sII", b"glTF", 2, total_len)
    c0 = struct.pack("<I4s", len(json_bytes), b"JSON")
    c1 = struct.pack("<I4s", len(bin_bytes), b"BIN\\x00")

    dest_glb.parent.mkdir(parents=True, exist_ok=True)
    with open(dest_glb, "wb") as f:
        f.write(hdr + c0 + json_bytes + c1 + bin_bytes)

    return dest_glb


def save_disk_asset(
    out_dir: Path,
    mesh: MeshGeometry,
    textures: Dict[str, Image.Image],
    species_id: str = "veg_tree_oak_01",
    write_textures_dir: bool = True,
    omit_texture_channel: Optional[str] = None,
    zero_byte_texture_channel: Optional[str] = None,
    companion_obj_lines: Optional[List[str]] = None,
) -> Tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    glb_p = out_dir / f"{species_id}.glb"
    export_production_glb(mesh, glb_p, textures, species_id=species_id)

    if write_textures_dir:
        tex_dir = out_dir / "textures"
        tex_dir.mkdir(parents=True, exist_ok=True)
        for ch, img in textures.items():
            if ch == omit_texture_channel:
                continue
            dest_file = tex_dir / f"{ch}.png"
            if ch == zero_byte_texture_channel:
                dest_file.write_bytes(b"")
            else:
                img.save(dest_file)

    if companion_obj_lines is not None:
        obj_p = out_dir / f"{species_id}.obj"
        with open(obj_p, "w", encoding="utf-8") as f:
            for line in companion_obj_lines:
                f.write(line + "\\n")

    return out_dir, glb_p


def test_corrupt_glb_binaries(tmp_path: Path):
    corrupt_dir = tmp_path / "corrupt_glbs"
    corrupt_dir.mkdir(parents=True, exist_ok=True)

    # 1. Truncated header (0 bytes)
    p0 = corrupt_dir / "zero_bytes.glb"
    p0.write_bytes(b"")
    r0 = validate_asset(p0)
    assert r0.is_valid is False
    assert r0.checks.get("glb_container_valid") is False

    # 2. Truncated header (4 bytes)
    p4 = corrupt_dir / "four_bytes.glb"
    p4.write_bytes(b"glTF")
    r4 = validate_asset(p4)
    assert r4.is_valid is False
    assert r4.checks.get("glb_container_valid") is False

    # 3. Truncated header (11 bytes)
    p11 = corrupt_dir / "eleven_bytes.glb"
    p11.write_bytes(b"glTF\\x02\\x00\\x00\\x00\\x10\\x00\\x00")
    r11 = validate_asset(p11)
    assert r11.is_valid is False
    assert r11.checks.get("glb_container_valid") is False

    # 4. Corrupted magic bytes
    for bad_magic in [b"NOPE", b"gltf", b"\\x00\\x00\\x00\\x00", b"PK\\x03\\x04"]:
        pm = corrupt_dir / f"bad_magic_{bad_magic.hex()}.glb"
        pm.write_bytes(bad_magic + struct.pack("<II", 2, 100) + b"\\x00" * 88)
        rm = validate_asset(pm)
        assert rm.is_valid is False
        assert rm.checks.get("glb_container_valid") is False
        assert any("magic" in err.lower() for err in rm.errors)

    # 5. Header total_len > file_size
    ptl = corrupt_dir / "oversized_declared_len.glb"
    ptl.write_bytes(b"glTF" + struct.pack("<II", 2, 999999) + b"truncated")
    rtl = validate_asset(ptl)
    assert rtl.is_valid is False
    assert rtl.checks.get("glb_container_valid") is False
    assert any("total length" in err.lower() or "file size" in err.lower() for err in rtl.errors)

    # 6. Unsupported version
    for v in (1, 3, 99):
        pv = corrupt_dir / f"version_{v}.glb"
        pv.write_bytes(b"glTF" + struct.pack("<II", v, 20) + b"\\x00" * 8)
        rv = validate_asset(pv)
        assert rv.is_valid is False
        assert rv.checks.get("glb_container_valid") is False
        assert any("version" in err.lower() for err in rv.errors)

    # 7. Truncated Chunk 0 header
    pc0 = corrupt_dir / "truncated_chunk0_hdr.glb"
    pc0.write_bytes(b"glTF" + struct.pack("<II", 2, 16) + b"JSON")
    rc0 = validate_asset(pc0)
    assert rc0.is_valid is False
    assert rc0.checks.get("glb_container_valid") is False

    # 8. Chunk 0 type is not JSON
    pcd = corrupt_dir / "non_json_chunk0.glb"
    pcd.write_bytes(b"glTF" + struct.pack("<II", 2, 28) + struct.pack("<I4s", 8, b"DATA") + b"12345678")
    rcd = validate_asset(pcd)
    assert rcd.is_valid is False
    assert rcd.checks.get("glb_container_valid") is False

    # 9. Truncated JSON chunk payload (total_len=24 matches file_size, but c0_len=50 > 4 bytes remaining)
    ptj = corrupt_dir / "truncated_json_payload.glb"
    ptj.write_bytes(b"glTF" + struct.pack("<II", 2, 24) + struct.pack("<I4s", 50, b"JSON") + b"{abc")
    rtj = validate_asset(ptj)
    assert rtj.is_valid is False
    assert rtj.checks.get("glb_container_valid") is False
    assert any("truncated json" in err.lower() for err in rtj.errors)

    # 10. Malformed JSON syntax
    pmj = corrupt_dir / "malformed_json_syntax.glb"
    bad_json_str = b"{this is not valid json content!!!:;;;}"
    pad = (4 - (len(bad_json_str) % 4)) % 4
    bad_json_padded = bad_json_str + b" " * pad
    pmj.write_bytes(
        b"glTF"
        + struct.pack("<II", 2, 12 + 8 + len(bad_json_padded))
        + struct.pack("<I4s", len(bad_json_padded), b"JSON")
        + bad_json_padded
    )
    rmj = validate_asset(pmj)
    assert rmj.is_valid is False
    assert rmj.checks.get("glb_container_valid") is False

    # 11. Missing BIN chunk
    mesh = make_synthetic_mesh(target_vertices=3200)
    tex = make_valid_test_textures()
    valid_glb = corrupt_dir / "baseline_valid.glb"
    export_production_glb(mesh, valid_glb, tex, species_id="veg_tree_oak_01")

    gltf, _ = unpack_glb_header_and_json(valid_glb)
    json_b = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    jpad = (4 - (len(json_b) % 4)) % 4
    json_b += b" " * jpad
    no_bin_glb = corrupt_dir / "no_bin_chunk.glb"
    tot_len = 12 + 8 + len(json_b)
    with open(no_bin_glb, "wb") as f:
        f.write(struct.pack("<4sII", b"glTF", 2, tot_len) + struct.pack("<I4s", len(json_b), b"JSON") + json_b)

    r_nobin = validate_asset(no_bin_glb)
    assert r_nobin.is_valid is False
    assert r_nobin.checks.get("geometry_valid") is False

    # 12. Truncated BIN chunk
    trun_bin_glb = corrupt_dir / "truncated_bin_chunk.glb"
    with open(trun_bin_glb, "wb") as f:
        f.write(
            struct.pack("<4sII", b"glTF", 2, 12 + 8 + len(json_b) + 8 + 500)
            + struct.pack("<I4s", len(json_b), b"JSON")
            + json_b
            + struct.pack("<I4s", 500, b"BIN\\x00")
            + b"\\x00" * 10
        )
    r_trunbin = validate_asset(trun_bin_glb)
    assert r_trunbin.is_valid is False
    assert r_trunbin.checks.get("glb_container_valid") is False
""")
add("""
def test_vertex_budget_bounds(tmp_path: Path):
    vb_dir = tmp_path / "vertex_budget"
    vb_dir.mkdir(parents=True, exist_ok=True)
    tex = make_valid_test_textures()

    # Case A: 0 vertices
    checks_0, _, errors_0, _ = validate_geometry(
        positions=np.empty((0, 3), dtype=np.float32),
        normals=np.empty((0, 3), dtype=np.float32),
        triangles=np.empty((0, 3), dtype=np.int32),
    )
    assert checks_0.get("vertex_count_budget") is False
    assert checks_0.get("zero_nan_inf_coordinates") is False

    # Case B: 10 vertices
    m_10 = make_synthetic_mesh(target_vertices=10)
    _, p_10 = save_disk_asset(vb_dir / "v10", m_10, tex)
    r_10 = validate_asset(p_10)
    assert r_10.is_valid is False
    assert r_10.checks.get("vertex_count_budget") is False

    # Case C: 2,999 vertices
    m_2999 = make_synthetic_mesh(target_vertices=2999)
    _, p_2999 = save_disk_asset(vb_dir / "v2999", m_2999, tex)
    r_2999 = validate_asset(p_2999)
    assert r_2999.is_valid is False
    assert r_2999.checks.get("vertex_count_budget") is False

    # Case D: 3,000 vertices (exact lower bound)
    m_3000 = make_synthetic_mesh(target_vertices=3000)
    _, p_3000 = save_disk_asset(vb_dir / "v3000", m_3000, tex)
    r_3000 = validate_asset(p_3000)
    assert r_3000.checks.get("vertex_count_budget") is True

    # Case E: 45,000 vertices (exact upper bound)
    m_45000 = make_synthetic_mesh(target_vertices=45000)
    _, p_45000 = save_disk_asset(vb_dir / "v45000", m_45000, tex)
    r_45000 = validate_asset(p_45000)
    assert r_45000.checks.get("vertex_count_budget") is True

    # Case F: 45,001 vertices
    m_45001 = make_synthetic_mesh(target_vertices=45001)
    _, p_45001 = save_disk_asset(vb_dir / "v45001", m_45001, tex)
    r_45001 = validate_asset(p_45001)
    assert r_45001.is_valid is False
    assert r_45001.checks.get("vertex_count_budget") is False

    # Case G: 100,000 vertices
    m_100k = make_synthetic_mesh(target_vertices=100000)
    _, p_100k = save_disk_asset(vb_dir / "v100k", m_100k, tex)
    r_100k = validate_asset(p_100k)
    assert r_100k.is_valid is False
    assert r_100k.checks.get("vertex_count_budget") is False


def test_coordinate_corruptions(tmp_path: Path):
    coord_dir = tmp_path / "coord_corruptions"
    coord_dir.mkdir(parents=True, exist_ok=True)
    tex = make_valid_test_textures()

    # 1. NaN in positions
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m_nan = make_synthetic_mesh(target_vertices=3200, inject_nan=True)
        _, p_nan = save_disk_asset(coord_dir / "nan_pos", m_nan, tex)
        r_nan = validate_asset(p_nan)
    assert r_nan.is_valid is False
    assert r_nan.checks.get("zero_nan_inf_coordinates") is False

    # 2. +Inf in positions
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m_pinf = make_synthetic_mesh(target_vertices=3200, inject_pos_inf=True)
        _, p_pinf = save_disk_asset(coord_dir / "pos_inf_pos", m_pinf, tex)
        r_pinf = validate_asset(p_pinf)
    assert r_pinf.is_valid is False
    assert r_pinf.checks.get("zero_nan_inf_coordinates") is False

    # 3. -Inf in positions
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m_ninf = make_synthetic_mesh(target_vertices=3200, inject_neg_inf=True)
        _, p_ninf = save_disk_asset(coord_dir / "neg_inf_pos", m_ninf, tex)
        r_ninf = validate_asset(p_ninf)
    assert r_ninf.is_valid is False
    assert r_ninf.checks.get("zero_nan_inf_coordinates") is False

    # 4. NaN in normals
    m_norm_nan = make_synthetic_mesh(target_vertices=3200, nan_normal=True)
    _, p_norm_nan = save_disk_asset(coord_dir / "nan_norm", m_norm_nan, tex)
    r_norm_nan = validate_asset(p_norm_nan)
    assert r_norm_nan.is_valid is False
    assert r_norm_nan.checks.get("normals_finite_and_unit") is False

    # 5. Inf in normals
    m_norm_inf = make_synthetic_mesh(target_vertices=3200, inf_normal=True)
    _, p_norm_inf = save_disk_asset(coord_dir / "inf_norm", m_norm_inf, tex)
    r_norm_inf = validate_asset(p_norm_inf)
    assert r_norm_inf.is_valid is False
    assert r_norm_inf.checks.get("normals_finite_and_unit") is False

    # 6. Extreme coordinate (10^12)
    m_extreme = make_synthetic_mesh(target_vertices=3200, extreme_coord=1e12)
    _, p_extreme = save_disk_asset(coord_dir / "extreme_1e12", m_extreme, tex)
    r_extreme = validate_asset(p_extreme)
    assert r_extreme.is_valid is False
    # Empirical finding: zero_nan_inf_coordinates returns True on 1e12 because np.isfinite(1e12) is True.
    # The anomaly is caught by centroid/metric scale checks.
    print(f"\\n[EMPIRICAL NOTE 1] Extreme coord 1e12 check states: zero_nan_inf={r_extreme.checks.get('zero_nan_inf_coordinates')}")
""")
add("""
def test_ground_alignment_bounds(tmp_path: Path):
    ground_dir = tmp_path / "ground_alignment"
    ground_dir.mkdir(parents=True, exist_ok=True)
    tex = make_valid_test_textures()

    # 1. Z_min = 10.0m
    m_10 = make_synthetic_mesh(target_vertices=3200, z_offset=10.0)
    _, p_10 = save_disk_asset(ground_dir / "z_10", m_10, tex)
    r_10 = validate_asset(p_10)
    assert r_10.is_valid is False
    assert r_10.checks.get("ground_contact_base_aligned") is False

    # 2. Z_min = -5.0m
    m_neg5 = make_synthetic_mesh(target_vertices=3200, z_offset=-5.0)
    _, p_neg5 = save_disk_asset(ground_dir / "z_neg5", m_neg5, tex)
    r_neg5 = validate_asset(p_neg5)
    assert r_neg5.is_valid is False
    assert r_neg5.checks.get("ground_contact_base_aligned") is False

    # 3. Z_min = 0.010m (10mm offset, > 5mm tolerance)
    m_010 = make_synthetic_mesh(target_vertices=3200, z_offset=0.010)
    _, p_010 = save_disk_asset(ground_dir / "z_010", m_010, tex)
    r_010 = validate_asset(p_010)
    assert r_010.is_valid is False
    assert r_010.checks.get("ground_contact_base_aligned") is False

    # 4. Z_min = 0.0051m (just outside +0.005m tolerance)
    m_0051 = make_synthetic_mesh(target_vertices=3200, z_offset=0.0051)
    _, p_0051 = save_disk_asset(ground_dir / "z_0051", m_0051, tex)
    r_0051 = validate_asset(p_0051)
    assert r_0051.is_valid is False
    assert r_0051.checks.get("ground_contact_base_aligned") is False

    # 5. Z_min = -0.0051m (just outside -0.005m tolerance)
    m_neg0051 = make_synthetic_mesh(target_vertices=3200, z_offset=-0.0051)
    _, p_neg0051 = save_disk_asset(ground_dir / "z_neg0051", m_neg0051, tex)
    r_neg0051 = validate_asset(p_neg0051)
    assert r_neg0051.is_valid is False
    assert r_neg0051.checks.get("ground_contact_base_aligned") is False

    # 6. Z_min = 0.0050m (exact upper tolerance limit)
    m_0050 = make_synthetic_mesh(target_vertices=3200, z_offset=0.0050)
    _, p_0050 = save_disk_asset(ground_dir / "z_0050", m_0050, tex)
    r_0050 = validate_asset(p_0050)
    assert r_0050.checks.get("ground_contact_base_aligned") is True

    # 7. Z_min = -0.0050m (exact lower tolerance limit)
    m_neg0050 = make_synthetic_mesh(target_vertices=3200, z_offset=-0.0050)
    _, p_neg0050 = save_disk_asset(ground_dir / "z_neg0050", m_neg0050, tex)
    r_neg0050 = validate_asset(p_neg0050)
    assert r_neg0050.checks.get("ground_contact_base_aligned") is True


def test_centroid_centering_bounds(tmp_path: Path):
    cent_dir = tmp_path / "centroid_centering"
    cent_dir.mkdir(parents=True, exist_ok=True)
    tex = make_valid_test_textures()

    # 1. Base centroid at (0.10, 0.0)m -> offset 0.10m > 0.05m
    m_10 = make_synthetic_mesh(target_vertices=3200, x_offset=0.10)
    _, p_10 = save_disk_asset(cent_dir / "x_10", m_10, tex)
    r_10 = validate_asset(p_10)
    assert r_10.is_valid is False
    assert r_10.checks.get("base_contact_centroid_centered") is False

    # 2. Base centroid at (0.0, 0.10)m -> offset 0.10m > 0.05m
    m_y10 = make_synthetic_mesh(target_vertices=3200, y_offset=0.10)
    _, p_y10 = save_disk_asset(cent_dir / "y_10", m_y10, tex)
    r_y10 = validate_asset(p_y10)
    assert r_y10.is_valid is False
    assert r_y10.checks.get("base_contact_centroid_centered") is False

    # 3. Base centroid at 0.051m (> 0.05m tolerance)
    m_051 = make_synthetic_mesh(target_vertices=3200, x_offset=0.051)
    _, p_051 = save_disk_asset(cent_dir / "x_051", m_051, tex)
    r_051 = validate_asset(p_051)
    assert r_051.is_valid is False
    assert r_051.checks.get("base_contact_centroid_centered") is False

    # 4. Base centroid safely within tolerance (0.048m <= 0.05m)
    m_048 = make_synthetic_mesh(target_vertices=3200, x_offset=0.048)
    _, p_048 = save_disk_asset(cent_dir / "x_048", m_048, tex)
    r_048 = validate_asset(p_048)
    assert r_048.checks.get("base_contact_centroid_centered") is True

    # 5. Diagonal (0.035, 0.035) -> dist = 0.0495m <= 0.05m
    m_diag_in = make_synthetic_mesh(target_vertices=3200, x_offset=0.035, y_offset=0.035)
    _, p_diag_in = save_disk_asset(cent_dir / "diag_in", m_diag_in, tex)
    r_diag_in = validate_asset(p_diag_in)
    assert r_diag_in.checks.get("base_contact_centroid_centered") is True

    # 6. Diagonal (0.040, 0.040) -> dist = 0.0566m > 0.05m
    m_diag_out = make_synthetic_mesh(target_vertices=3200, x_offset=0.040, y_offset=0.040)
    _, p_diag_out = save_disk_asset(cent_dir / "diag_out", m_diag_out, tex)
    r_diag_out = validate_asset(p_diag_out)
    assert r_diag_out.is_valid is False
    assert r_diag_out.checks.get("base_contact_centroid_centered") is False

    # EMPIRICAL NUMERICAL FINDING:
    # Notice: In float32 single-precision, 0.050 is represented as 0.05000000447.
    # In validator.py, centroid_dist <= 0.05 evaluates to False on float32 0.050.
    m_050 = make_synthetic_mesh(target_vertices=3200, x_offset=0.050)
    _, p_050 = save_disk_asset(cent_dir / "x_050", m_050, tex)
    r_050 = validate_asset(p_050)
    print(f"\\n[EMPIRICAL NOTE 2] Float32 numerical precision boundary on 0.050m: centroid_centered={r_050.checks.get('base_contact_centroid_centered')}")
""")
add("""
def test_static_mesh_rigging_injections(tmp_path: Path):
    rig_dir = tmp_path / "rigging_injections"
    rig_dir.mkdir(parents=True, exist_ok=True)
    tex = make_valid_test_textures()
    mesh = make_synthetic_mesh(target_vertices=3200)

    base_dir, base_glb = save_disk_asset(rig_dir / "base", mesh, tex)

    # 1. Active skins array in GLB
    def inject_skins(gltf: Dict[str, Any]):
        gltf["skins"] = [{"name": "ArmatureSkin", "joints": [0, 1]}]

    p_skins = repack_glb_json(base_glb, rig_dir / "skins" / "veg_tree_oak_01.glb", inject_skins)
    r_skins = validate_asset(p_skins)
    assert r_skins.is_valid is False
    assert r_skins.checks.get("static_mesh_no_skins") is False
    assert r_skins.checks.get("n_bones_strictly_zero") is False

    # 2. Active animations array in GLB
    def inject_anims(gltf: Dict[str, Any]):
        gltf["animations"] = [{"name": "IdleWind", "samplers": [], "channels": []}]

    p_anims = repack_glb_json(base_glb, rig_dir / "anims" / "veg_tree_oak_01.glb", inject_anims)
    r_anims = validate_asset(p_anims)
    assert r_anims.is_valid is False
    assert r_anims.checks.get("static_mesh_no_animations") is False

    # 3. Primitive attribute JOINTS_0
    def inject_joints(gltf: Dict[str, Any]):
        if "meshes" in gltf and gltf["meshes"]:
            for prim in gltf["meshes"][0].get("primitives", []):
                prim["attributes"]["JOINTS_0"] = 0

    p_joints = repack_glb_json(base_glb, rig_dir / "joints" / "veg_tree_oak_01.glb", inject_joints)
    r_joints = validate_asset(p_joints)
    assert r_joints.is_valid is False
    assert r_joints.checks.get("static_mesh_no_joint_weights") is False
    assert r_joints.checks.get("n_bones_strictly_zero") is False

    # 4. Primitive attribute WEIGHTS_0
    def inject_weights(gltf: Dict[str, Any]):
        if "meshes" in gltf and gltf["meshes"]:
            for prim in gltf["meshes"][0].get("primitives", []):
                prim["attributes"]["WEIGHTS_0"] = 0

    p_weights = repack_glb_json(base_glb, rig_dir / "weights" / "veg_tree_oak_01.glb", inject_weights)
    r_weights = validate_asset(p_weights)
    assert r_weights.is_valid is False
    assert r_weights.checks.get("static_mesh_no_joint_weights") is False
    assert r_weights.checks.get("n_bones_strictly_zero") is False

    # 5. Node skin reference
    def inject_node_skin(gltf: Dict[str, Any]):
        gltf["nodes"] = [{"name": "MeshNode", "skin": 0}]

    p_nodeskin = repack_glb_json(base_glb, rig_dir / "node_skin" / "veg_tree_oak_01.glb", inject_node_skin)
    r_nodeskin = validate_asset(p_nodeskin)
    assert r_nodeskin.is_valid is False
    assert r_nodeskin.checks.get("static_mesh_no_node_skins") is False
    assert r_nodeskin.checks.get("n_bones_strictly_zero") is False

    # 6. Companion OBJ with 'g bone_pelvis'
    dir_obj_bone, _ = save_disk_asset(
        rig_dir / "obj_bone",
        mesh,
        tex,
        companion_obj_lines=["# Companion OBJ", "v 0 0 0", "g bone_pelvis", "f 1 1 1"],
    )
    r_obj_bone = validate_asset(dir_obj_bone)
    assert r_obj_bone.is_valid is False
    assert r_obj_bone.checks.get("obj_no_bones") is False
    assert r_obj_bone.checks.get("n_bones_strictly_zero") is False

    # 7. Companion OBJ with 'o joint_root'
    dir_obj_joint, _ = save_disk_asset(
        rig_dir / "obj_joint",
        mesh,
        tex,
        companion_obj_lines=["# Companion OBJ", "v 0 0 0", "o joint_root", "f 1 1 1"],
    )
    r_obj_joint = validate_asset(dir_obj_joint)
    assert r_obj_joint.is_valid is False
    assert r_obj_joint.checks.get("obj_no_bones") is False
    assert r_obj_joint.checks.get("n_bones_strictly_zero") is False

    # 8. Companion OBJ with 'skin' directive
    dir_obj_skin, _ = save_disk_asset(
        rig_dir / "obj_skin",
        mesh,
        tex,
        companion_obj_lines=["# Companion OBJ", "v 0 0 0", "skin arm_left", "f 1 1 1"],
    )
    r_obj_skin = validate_asset(dir_obj_skin)
    assert r_obj_skin.is_valid is False
    assert r_obj_skin.checks.get("obj_no_bones") is False
    assert r_obj_skin.checks.get("n_bones_strictly_zero") is False

    # 9. Companion OBJ with 'weight' directive
    dir_obj_weight, _ = save_disk_asset(
        rig_dir / "obj_weight",
        mesh,
        tex,
        companion_obj_lines=["# Companion OBJ", "v 0 0 0", "weight 0.5 0.5", "f 1 1 1"],
    )
    r_obj_weight = validate_asset(dir_obj_weight)
    assert r_obj_weight.is_valid is False
    assert r_obj_weight.checks.get("obj_no_bones") is False
    assert r_obj_weight.checks.get("n_bones_strictly_zero") is False
""")
add("""
def test_texture_corruptions(tmp_path: Path):
    tex_dir = tmp_path / "texture_corruptions"
    tex_dir.mkdir(parents=True, exist_ok=True)
    mesh = make_synthetic_mesh(target_vertices=3200)

    # 1. Missing channel tests
    for ch in ("albedo", "normal", "roughness", "metallic"):
        t_dict = make_valid_test_textures()
        ch_dir, _ = save_disk_asset(tex_dir / f"missing_{ch}", mesh, t_dict, omit_texture_channel=ch)
        r = validate_asset(ch_dir)
        assert r.is_valid is False
        assert r.checks.get("textures_channels_present") is False
        assert any(ch in e.lower() or "missing" in e.lower() for e in r.errors)

    # 2. 0-byte single texture image (corrupt image prevents loading channel)
    t_zero = make_valid_test_textures()
    zero_dir, _ = save_disk_asset(tex_dir / "zero_byte", mesh, t_zero, zero_byte_texture_channel="albedo")
    r_zero = validate_asset(zero_dir)
    assert r_zero.is_valid is False
    assert r_zero.checks.get("textures_channels_present") is False

    # 2b. All textures 0-byte -> textures_readable_and_sized strictly False
    all_zero_dir, _ = save_disk_asset(tex_dir / "all_zero_byte", mesh, t_zero)
    for p in (all_zero_dir / "textures").glob("*.png"):
        p.write_bytes(b"")
    r_all_zero = validate_asset(all_zero_dir)
    assert r_all_zero.is_valid is False
    assert r_all_zero.checks.get("textures_readable_and_sized") is False

    # 3. Undersized image (128x128 < 256x256)
    t_under = make_valid_test_textures()
    t_under["albedo"] = t_under["albedo"].resize((128, 128))
    under_dir, _ = save_disk_asset(tex_dir / "undersized", mesh, t_under)
    r_under = validate_asset(under_dir)
    assert r_under.is_valid is False
    assert r_under.checks.get("textures_readable_and_sized") is False
    assert any("256x256" in e.lower() or "below minimum" in e.lower() for e in r_under.errors)

    # 4. Solid-black albedo (mean <= 0.05)
    t_black = make_valid_test_textures()
    t_black["albedo"] = Image.new("RGB", (256, 256), (0, 0, 0))
    black_dir, _ = save_disk_asset(tex_dir / "black_albedo", mesh, t_black)
    r_black = validate_asset(black_dir)
    assert r_black.is_valid is False
    assert r_black.checks.get("texture_albedo_plausible") is False
    assert any("solid black" in e.lower() or "too dark" in e.lower() for e in r_black.errors)

    # 5. Flat zero-variation albedo (std <= 0.02)
    t_flat_alb = make_valid_test_textures()
    t_flat_alb["albedo"] = Image.new("RGB", (256, 256), (80, 140, 50))
    flat_alb_dir, _ = save_disk_asset(tex_dir / "flat_albedo", mesh, t_flat_alb)
    r_flat_alb = validate_asset(flat_alb_dir)
    assert r_flat_alb.is_valid is False
    assert r_flat_alb.checks.get("texture_albedo_plausible") is False
    assert any("surface variation" in e.lower() for e in r_flat_alb.errors)

    # 6. Non-dielectric metallic (metallic = 1.0)
    t_metal = make_valid_test_textures()
    t_metal["metallic"] = Image.new("L", (256, 256), 255)
    metal_dir, _ = save_disk_asset(tex_dir / "pure_metal", mesh, t_metal)
    r_metal = validate_asset(metal_dir)
    assert r_metal.is_valid is False
    assert r_metal.checks.get("texture_metallic_dielectric") is False

    # 7. Roughness too smooth (mean = 0.05 < 0.20)
    t_smooth = make_valid_test_textures()
    t_smooth["roughness"] = Image.fromarray(np.random.randint(5, 20, (256, 256), dtype=np.uint8), mode="L")
    smooth_dir, _ = save_disk_asset(tex_dir / "too_smooth", mesh, t_smooth)
    r_smooth = validate_asset(smooth_dir)
    assert r_smooth.is_valid is False
    assert r_smooth.checks.get("texture_roughness_plausible") is False

    # 8. Roughness too matte (mean = 0.98 > 0.95)
    t_matte = make_valid_test_textures()
    t_matte["roughness"] = Image.fromarray(np.random.randint(245, 255, (256, 256), dtype=np.uint8), mode="L")
    matte_dir, _ = save_disk_asset(tex_dir / "too_matte", mesh, t_matte)
    r_matte = validate_asset(matte_dir)
    assert r_matte.is_valid is False
    assert r_matte.checks.get("texture_roughness_plausible") is False

    # 9. Roughness flat field (std <= 0.01)
    t_flat_r = make_valid_test_textures()
    t_flat_r["roughness"] = Image.new("L", (256, 256), 128)
    flat_r_dir, _ = save_disk_asset(tex_dir / "flat_roughness", mesh, t_flat_r)
    r_flat_r = validate_asset(flat_r_dir)
    assert r_flat_r.is_valid is False
    assert r_flat_r.checks.get("texture_roughness_plausible") is False

    # 10. Normal map with Z-component out of range (flat (128, 128, 128) -> nz = 0.0 < 0.5)
    t_norm_z0 = make_valid_test_textures()
    t_norm_z0["normal"] = Image.new("RGB", (256, 256), (128, 128, 128))
    norm_z0_dir, _ = save_disk_asset(tex_dir / "norm_z0", mesh, t_norm_z0)
    r_norm_z0 = validate_asset(norm_z0_dir)
    assert r_norm_z0.is_valid is False
    assert r_norm_z0.checks.get("texture_normal_plausible") is False

    # 11. Normal map inverted Z ((128, 128, 0) -> nz = -1.0)
    t_norm_inv = make_valid_test_textures()
    t_norm_inv["normal"] = Image.new("RGB", (256, 256), (128, 128, 0))
    norm_inv_dir, _ = save_disk_asset(tex_dir / "norm_inv", mesh, t_norm_inv)
    r_norm_inv = validate_asset(norm_inv_dir)
    assert r_norm_inv.is_valid is False
    assert r_norm_inv.checks.get("texture_normal_plausible") is False

    # 12. Normal map non-unit magnitude ((255, 255, 255) -> mag = 1.732)
    t_norm_mag = make_valid_test_textures()
    t_norm_mag["normal"] = Image.new("RGB", (256, 256), (255, 255, 255))
    norm_mag_dir, _ = save_disk_asset(tex_dir / "norm_mag", mesh, t_norm_mag)
    r_norm_mag = validate_asset(norm_mag_dir)
    assert r_norm_mag.is_valid is False
    assert r_norm_mag.checks.get("texture_normal_plausible") is False

    # EMPIRICAL OBSERVATION ON FLAT NORMAL MAP:
    t_norm_flat = make_valid_test_textures()
    t_norm_flat["normal"] = Image.new("RGB", (256, 256), (128, 128, 255))
    flat_norm_dir, _ = save_disk_asset(tex_dir / "norm_flat_tangent", mesh, t_norm_flat)
    r_norm_flat = validate_asset(flat_norm_dir)
    print(f"\\n[EMPIRICAL NOTE 3] Flat tangent normal map (128, 128, 255) accepted: {r_norm_flat.checks.get('texture_normal_plausible')}")
""")
add("""
def run_cli_command(args: List[str]) -> Tuple[int, str, str]:
    cmd = [sys.executable, str(PROJECT_DIR / "pipeline.py")] + args
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(REPO_ROOT))
    return res.returncode, res.stdout, res.stderr


def test_cli_stress(tmp_path: Path):
    # 1. Invalid species ID -> exit code 2
    code_sp, out_sp, err_sp = run_cli_command(["--species", "invalid_species_xyz"])
    assert code_sp == 2, f"Expected exit code 2 for invalid species, got {code_sp}. Stderr: {err_sp}"
    assert "not found in catalog" in err_sp

    # 2. Invalid category -> exit code 2
    code_cat, out_cat, err_cat = run_cli_command(["--category", "invalid_category_xyz"])
    assert code_cat == 2, f"Expected exit code 2 for invalid category, got {code_cat}. Stderr: {err_cat}"
    assert "not found or has no species" in err_cat

    # 3. Invalid generation mode -> exit code 2
    code_mod, out_mod, err_mod = run_cli_command(["--mode", "invalid_mode_xyz"])
    assert code_mod == 2, f"Expected exit code 2 for invalid mode, got {code_mod}. Stderr: {err_mod}"
    assert "invalid choice" in err_mod

    # 4. No arguments provided -> exit code 2
    code_none, out_none, err_none = run_cli_command([])
    assert code_none == 2, f"Expected exit code 2 for empty arguments, got {code_none}. Stderr: {err_none}"
    assert "no target specified" in err_none.lower()

    # 5. Summary mode with missing manifest directory -> exit code 1
    code_sum_fail, out_sum_fail, err_sum_fail = run_cli_command(
        ["--summary", "--output-dir", str(tmp_path / "nonexistent_directory_xyz")]
    )
    assert code_sum_fail == 1, f"Expected exit code 1 for missing manifest summary, got {code_sum_fail}"
    assert "manifest not found" in err_sum_fail.lower()

    # 6. Summary mode with valid manifest directory -> exit code 0
    code_sum_ok, out_sum_ok, err_sum_ok = run_cli_command(
        ["--summary", "--output-dir", "teamwork_projects/vegetation_library/output"]
    )
    assert code_sum_ok == 0, f"Expected exit code 0 for valid summary, got {code_sum_ok}. Stderr: {err_sum_ok}"
    assert "Asset Catalog Summary" in out_sum_ok

    # 7. Validate-only with valid oak asset -> exit code 0
    code_val_ok, out_val_ok, err_val_ok = run_cli_command(
        ["--validate-only", "--species", "veg_tree_oak_01", "--output-dir", "teamwork_projects/vegetation_library/output"]
    )
    assert code_val_ok == 0, f"Expected exit code 0 for valid oak validate-only, got {code_val_ok}. Stderr: {err_val_ok}"

    # 8. Validate-only with failing defective asset in temp directory -> exit code 1
    defective_root = tmp_path / "cli_defective_root"
    m_bad = make_synthetic_mesh(target_vertices=1200)  # under budget
    t_bad = make_valid_test_textures()
    save_disk_asset(defective_root / "broadleaf_trees" / "veg_tree_oak_01", m_bad, t_bad, species_id="veg_tree_oak_01")

    code_val_fail, out_val_fail, err_val_fail = run_cli_command(
        ["--validate-only", "--species", "veg_tree_oak_01", "--output-dir", str(defective_root)]
    )
    assert code_val_fail == 1, f"Expected exit code 1 for defective asset validate-only, got {code_val_fail}. Stderr: {err_val_fail}"

    # 9. Render-only with valid oak asset -> exit code 0
    code_ren_ok, out_ren_ok, err_ren_ok = run_cli_command(
        ["--render-only", "--species", "veg_tree_oak_01", "--output-dir", "teamwork_projects/vegetation_library/output"]
    )
    assert code_ren_ok == 0, f"Expected exit code 0 for render-only oak, got {code_ren_ok}. Stderr: {err_ren_ok}"


def test_degenerate_faces_and_metric_scale(tmp_path: Path):
    geom_dir = tmp_path / "geom_edge_cases"
    geom_dir.mkdir(parents=True, exist_ok=True)
    tex = make_valid_test_textures()

    # 1. Duplicate vertex indices face
    m_dup = make_synthetic_mesh(target_vertices=3200, duplicate_indices_face=True)
    _, p_dup = save_disk_asset(geom_dir / "dup_indices", m_dup, tex)
    r_dup = validate_asset(p_dup)
    assert r_dup.is_valid is False
    assert r_dup.checks.get("non_degenerate_faces") is False

    # 2. Zero-area face
    m_zero_area = make_synthetic_mesh(target_vertices=3200, zero_area_face=True)
    _, p_zero_area = save_disk_asset(geom_dir / "zero_area", m_zero_area, tex)
    r_zero_area = validate_asset(p_zero_area)
    assert r_zero_area.is_valid is False
    assert r_zero_area.checks.get("non_degenerate_faces") is False

    # 3. Zero-length normal vectors
    m_zero_norm = make_synthetic_mesh(target_vertices=3200, zero_normal=True)
    _, p_zero_norm = save_disk_asset(geom_dir / "zero_normal", m_zero_norm, tex)
    r_zero_norm = validate_asset(p_zero_norm)
    assert r_zero_norm.is_valid is False
    assert r_zero_norm.checks.get("normals_finite_and_unit") is False

    # 4. Non-unit normal vectors
    m_non_unit = make_synthetic_mesh(target_vertices=3200, non_unit_normal=True)
    _, p_non_unit = save_disk_asset(geom_dir / "non_unit_normal", m_non_unit, tex)
    r_non_unit = validate_asset(p_non_unit)
    assert r_non_unit.is_valid is False
    assert r_non_unit.checks.get("normals_finite_and_unit") is False

    # 5. Metric scale violation (+20% vs +10% target)
    checks_bad, _, errors_bad, _ = validate_geometry(
        positions=np.array([[0, 0, 0], [0, 0, 12.0], [0.5, 0.5, 6.0]], dtype=np.float32),
        normals=np.array([[0, 0, 1], [0, 0, 1], [0, 0, 1]], dtype=np.float32),
        triangles=np.array([[0, 1, 2]], dtype=np.int32),
        target_height_m=10.0,
    )
    assert checks_bad.get("metric_scale_bounds") is False

    # 6. Metric scale compliant (+9% <= 10% target)
    checks_good, _, errors_good, _ = validate_geometry(
        positions=np.array([[0, 0, 0], [0, 0, 10.9], [0.5, 0.5, 5.0]], dtype=np.float32),
        normals=np.array([[0, 0, 1], [0, 0, 1], [0, 0, 1]], dtype=np.float32),
        triangles=np.array([[0, 1, 2]], dtype=np.int32),
        target_height_m=10.0,
    )
    assert checks_good.get("metric_scale_bounds") is True
""")
add("""
if __name__ == "__main__":
    print("=" * 80)
    print("STARTING EMPIRICAL ADVERSARIAL CHALLENGER SUITE (M4)")
    print("=" * 80)

    t_start = time.time()
    test_temp = Path(tempfile.mkdtemp(prefix="m4_adversarial_"))

    test_functions = [
        ("Corrupt GLB Binaries", test_corrupt_glb_binaries),
        ("Vertex Budget Bounds", test_vertex_budget_bounds),
        ("Coordinate Corruptions", test_coordinate_corruptions),
        ("Ground Alignment Bounds", test_ground_alignment_bounds),
        ("Centroid Centering Bounds", test_centroid_centering_bounds),
        ("Static Mesh Rigging Injections", test_static_mesh_rigging_injections),
        ("Texture Corruptions", test_texture_corruptions),
        ("CLI Runner Stress", test_cli_stress),
        ("Degenerate Faces & Metric Scale", test_degenerate_faces_and_metric_scale),
    ]

    passed = 0
    failed = 0

    for name, fn in test_functions:
        sub_dir = test_temp / name.replace(" ", "_").lower()
        sub_dir.mkdir(parents=True, exist_ok=True)
        print(f"\\n[RUNNING] {name}...")
        t0 = time.time()
        try:
            fn(sub_dir)
            dt = time.time() - t0
            print(f"[PASS] {name} ({dt:.2f}s)")
            passed += 1
        except Exception as e:
            dt = time.time() - t0
            print(f"[FAIL] {name} ({dt:.2f}s): {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    shutil.rmtree(test_temp, ignore_errors=True)
    total_time = time.time() - t_start

    print("\\n" + "=" * 80)
    print(f"ADVERSARIAL SUITE SUMMARY: {passed} PASSED, {failed} FAILED in {total_time:.2f}s")
    print("=" * 80)

    sys.exit(0 if failed == 0 else 1)
""")

full_code = "".join(code_parts)
target_path.write_text(full_code, encoding="utf-8")
print("SUCCESS: test_adversarial_m4.py generated! Size:", target_path.stat().st_size)
