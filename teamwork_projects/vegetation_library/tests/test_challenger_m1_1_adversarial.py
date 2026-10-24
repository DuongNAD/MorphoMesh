"""
Challenger M1-1: Adversarial Engine & Boundary Verification Test Suite
Target Components:
1. validator.py boundary checks:
   - 19,999 vertices (must fail)
   - 20,000 vertices (must pass)
   - 65,000 vertices (must pass)
   - 65,001 vertices (must fail)
2. validator.py ground pivot tolerance:
   - |Z_min| = 0.0050m (+0.0050m and -0.0050m must pass)
   - |Z_min| = 0.0051m (+0.0051m and -0.0051m must fail)
3. validator.py static mesh invariant enforcement:
   - Injected glTF skins array (must fail)
   - Injected glTF animations array (must fail)
   - Injected primitive JOINTS_0 attribute (must fail)
   - Injected primitive WEIGHTS_0 attribute (must fail)
   - Injected node skin reference (must fail)
   - Injected companion OBJ bone/skin directives (must fail)
4. generator.py error handling and strict no-fallback in mode == "meshy":
   - Missing MESHY_API_KEY raises RuntimeError and emits NO procedural mesh
   - API call failure raises Exception and emits NO procedural mesh
   - Contrast with mode == "auto" which falls back gracefully
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import shutil
import struct
import sys
from typing import Any, Dict, List, Tuple
from unittest.mock import MagicMock, patch

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
from vegetation_pipeline.generator import (
    MeshyGenerator,
    MeshyGeneratorConfig,
    RawAsset,
    generate_plant,
    unpack_glb_header_and_json,
)
from vegetation_pipeline.post_processor import (
    export_production_glb,
    process_and_export,
)
from vegetation_pipeline.validator import (
    ValidationReport,
    validate_asset,
    validate_geometry,
    validate_static_mesh_invariants,
)


# ==============================================================================
# SYNTHETIC GEOMETRY & ASSET GENERATORS
# ==============================================================================

def make_exact_test_geometry(
    target_vertices: int,
    height: float = 12.0,
    radius: float = 0.5,
    z_offset: float = 0.0,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Constructs an exact vertex count cylindrical geometry with non-degenerate faces,
    unit-length normals, base contact at z_offset, and base centroid at (0, 0).
    """
    K = 100  # Vertices per complete ring (analytic centroid = (0, 0))
    M = (target_vertices + K - 1) // K
    positions: List[List[float]] = []
    normals: List[List[float]] = []
    triangles: List[List[int]] = []
    v_count = 0
    grid: List[List[int]] = []

    for j in range(M):
        row: List[int] = []
        fraction_z = j / max(M - 1, 1)
        z = z_offset + fraction_z * height
        for k in range(K):
            if v_count >= target_vertices:
                break
            theta = 2.0 * math.pi * k / K
            x = radius * math.cos(theta)
            y = radius * math.sin(theta)
            positions.append([round(x, 5), round(y, 5), round(z, 5)])
            normals.append([math.cos(theta), math.sin(theta), 0.0])
            row.append(v_count)
            v_count += 1
        if row:
            grid.append(row)

    # Triangulate adjacent rings without degenerate faces
    for j in range(len(grid) - 1):
        r1 = grid[j]
        r2 = grid[j + 1]
        c = min(len(r1), len(r2))
        if c >= 3:
            for k in range(c):
                nxt = (k + 1) % c
                i0, i1, i2, i3 = r1[k], r1[nxt], r2[nxt], r2[k]
                triangles.append([i0, i1, i2])
                triangles.append([i0, i2, i3])
        elif len(r2) > 0 and len(r1) >= 2:
            # Fan remainder vertices into preceding full ring
            for v2 in r2:
                triangles.append([r1[0], r1[1], v2])

    pos = np.array(positions, dtype=np.float32)
    norm = np.array(normals, dtype=np.float32)
    tri = np.array(triangles, dtype=np.int32)
    return pos, norm, tri


def make_exact_mesh_geometry(
    target_vertices: int,
    height: float = 12.0,
    radius: float = 0.5,
    z_offset: float = 0.0,
) -> MeshGeometry:
    """Builds a MeshGeometry object containing exactly target_vertices."""
    pos, norm, tri = make_exact_test_geometry(
        target_vertices=target_vertices,
        height=height,
        radius=radius,
        z_offset=z_offset,
    )
    mesh = MeshGeometry()
    for p, n in zip(pos, norm):
        mesh.add_vertex(tuple(p), tuple(n), (0.5, 0.5))
    for t in tri:
        mesh.add_triangle(int(t[0]), int(t[1]), int(t[2]))
    return mesh


def make_synthetic_textures(size: int = 256) -> Dict[str, Image.Image]:
    """Generates standard compliant 256x256 PBR textures."""
    np.random.seed(1337)
    base_col = np.array([80, 140, 50], dtype=np.float32)
    noise = np.random.uniform(-20, 20, (size, size, 3))
    alb_data = np.clip(base_col + noise, 0, 255).astype(np.uint8)
    albedo = Image.fromarray(alb_data, mode="RGB")
    normal = Image.new("RGB", (size, size), (128, 128, 255))
    r_data = np.clip(np.random.normal(150, 15, (size, size)), 50, 240).astype(np.uint8)
    roughness = Image.fromarray(r_data, mode="L")
    metallic = Image.new("L", (size, size), 0)
    return {
        "albedo": albedo,
        "normal": normal,
        "roughness": roughness,
        "metallic": metallic,
    }


def export_synthetic_meshy_asset(
    target_dir: Path,
    species_id: str,
    n_vertices: int,
    z_offset: float = 0.0,
    height: float = 12.0,
    task_id: str = "msy_empirical_task_12345",
) -> Path:
    """Exports a fully formed synthetic asset directory with Meshy cloud provenance."""
    target_dir.mkdir(parents=True, exist_ok=True)
    mesh = make_exact_mesh_geometry(target_vertices=n_vertices, height=height, z_offset=z_offset)
    textures = make_synthetic_textures()

    glb_path = target_dir / f"{species_id}.glb"
    export_production_glb(mesh, glb_path, textures, species_id=species_id)

    # Export companion obj
    obj_path = target_dir / f"{species_id}.obj"
    with open(obj_path, "w", encoding="utf-8") as f:
        f.write(f"# Wavefront OBJ: {species_id}\n")
        f.write(f"mtllib {species_id}.mtl\no {species_id}\n")
        for v in mesh.vertices:
            f.write(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}\n")
        for t in mesh.faces:
            f.write(f"f {t[0]+1} {t[1]+1} {t[2]+1}\n")

    # Export textures
    tex_dir = target_dir / "textures"
    tex_dir.mkdir(parents=True, exist_ok=True)
    for name, img in textures.items():
        img.save(tex_dir / f"{name}.png")

    # Write asset manifest with Meshy provenance
    manifest = {
        "species_id": species_id,
        "provenance": {
            "source": "meshy",
            "task_id": task_id,
            "generator_metadata": {
                "task_id": task_id,
            },
        },
        "taxonomy": {
            "short_category": "broadleaf_trees",
        },
    }
    with open(target_dir / "asset_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return target_dir


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
# OBJECTIVE 1: BOUNDARY TESTING ON VALIDATOR.PY (19999, 20000, 65000, 65001)
# ==============================================================================

class TestValidatorVertexBoundaries:
    """
    Stress-tests the vertex budget boundary conditions in validator.py:
    - 19,999 vertices: strictly under budget for Meshy -> MUST FAIL
    - 20,000 vertices: minimum acceptable boundary for Meshy -> MUST PASS
    - 65,000 vertices: maximum acceptable boundary for Meshy -> MUST PASS
    - 65,001 vertices: strictly over budget for Meshy -> MUST FAIL
    """

    @pytest.mark.parametrize(
        "vertex_count,expected_pass",
        [
            (19999, False),
            (20000, True),
            (65000, True),
            (65001, False),
        ],
    )
    def test_direct_validate_geometry_vertex_boundaries(self, vertex_count: int, expected_pass: bool):
        """Direct mathematical boundary assertion on validate_geometry()."""
        pos, norm, tri = make_exact_test_geometry(
            target_vertices=vertex_count,
            height=12.0,
            radius=0.5,
            z_offset=0.0,
        )
        assert len(pos) == vertex_count, f"Geometry builder emitted {len(pos)} vertices, expected {vertex_count}"

        checks, metrics, errors, warnings = validate_geometry(
            positions=pos,
            normals=norm,
            triangles=tri,
            target_height_m=12.0,
            min_vertices=20000,
            max_vertices=65000,
        )

        assert checks["vertex_count_budget"] is expected_pass, (
            f"Vertex budget check for N={vertex_count} yielded {checks['vertex_count_budget']}, "
            f"expected {expected_pass}. Errors: {errors}"
        )

        if not expected_pass:
            if vertex_count < 20000:
                assert any("under budget" in e.lower() for e in errors), f"Expected 'under budget' in errors: {errors}"
            else:
                assert any("over budget" in e.lower() for e in errors), f"Expected 'over budget' in errors: {errors}"
        else:
            assert not any("budget" in e.lower() for e in errors), f"Unexpected budget error for N={vertex_count}: {errors}"

    @pytest.mark.parametrize(
        "vertex_count,expected_pass",
        [
            (19999, False),
            (20000, True),
            (65000, True),
            (65001, False),
        ],
    )
    def test_asset_validate_asset_meshy_vertex_boundaries(self, tmp_path: Path, vertex_count: int, expected_pass: bool):
        """End-to-end container boundary assertion on validate_asset() with Meshy cloud provenance."""
        asset_dir = tmp_path / f"asset_{vertex_count}"
        export_synthetic_meshy_asset(
            target_dir=asset_dir,
            species_id="veg_tree_oak_01",
            n_vertices=vertex_count,
            height=12.0,
            z_offset=0.0,
        )

        report: ValidationReport = validate_asset(asset_dir)

        assert report.checks.get("vertex_count_budget") is expected_pass, (
            f"validate_asset vertex_count_budget for N={vertex_count} failed: "
            f"got {report.checks.get('vertex_count_budget')}, expected {expected_pass}. "
            f"Errors: {report.errors}"
        )

        if expected_pass:
            assert report.is_valid is True, f"Asset with valid vertex count {vertex_count} failed: {report.errors}"
        else:
            assert report.is_valid is False, f"Asset with invalid vertex count {vertex_count} unexpectedly passed"
            if vertex_count < 20000:
                assert any("under budget" in e.lower() for e in report.errors)
            else:
                assert any("over budget" in e.lower() for e in report.errors)


# ==============================================================================
# OBJECTIVE 2: GROUND PIVOT TOLERANCE (|Z_MIN| = 0.0050m vs 0.0051m)
# ==============================================================================

class TestValidatorGroundPivotTolerance:
    """
    Stress-tests the ground pivot alignment tolerance in validator.py:
    Tolerance is strictly |Z_min| <= 0.0050m.
    - Z_min = +0.0050m: boundary contact -> MUST PASS
    - Z_min = -0.0050m: boundary contact -> MUST PASS
    - Z_min = +0.0051m: 0.1mm above tolerance -> MUST FAIL
    - Z_min = -0.0051m: 0.1mm below tolerance -> MUST FAIL
    """

    @pytest.mark.parametrize(
        "z_offset,expected_pass",
        [
            (+0.0050, True),
            (-0.0050, True),
            (+0.0051, False),
            (-0.0051, False),
        ],
    )
    def test_direct_validate_geometry_ground_pivot_tolerance(self, z_offset: float, expected_pass: bool):
        """Direct verification of validate_geometry ground contact check across +/- 0.0050m and +/- 0.0051m."""
        pos, norm, tri = make_exact_test_geometry(
            target_vertices=20000,
            height=12.0,
            radius=0.5,
            z_offset=z_offset,
        )

        checks, metrics, errors, warnings = validate_geometry(
            positions=pos,
            normals=norm,
            triangles=tri,
            target_height_m=12.0,
            min_vertices=20000,
            max_vertices=65000,
        )

        assert checks["ground_contact_base_aligned"] is expected_pass, (
            f"Ground contact check for Z_min={z_offset:+.4f} yielded "
            f"{checks['ground_contact_base_aligned']}, expected {expected_pass}. Errors: {errors}"
        )

        if not expected_pass:
            assert any("ground contact" in e.lower() for e in errors), f"Expected ground contact error: {errors}"
        else:
            assert not any("ground contact" in e.lower() for e in errors), f"Unexpected ground contact error: {errors}"

    @pytest.mark.parametrize(
        "z_offset,expected_pass",
        [
            (+0.0050, True),
            (-0.0050, True),
            (+0.0051, False),
            (-0.0051, False),
        ],
    )
    def test_asset_validate_asset_ground_pivot_tolerance(self, tmp_path: Path, z_offset: float, expected_pass: bool):
        """End-to-end asset verification of validate_asset ground contact check."""
        tag = f"p_{abs(int(z_offset*10000))}" if z_offset >= 0 else f"m_{abs(int(z_offset*10000))}"
        asset_dir = tmp_path / f"asset_pivot_{tag}"
        export_synthetic_meshy_asset(
            target_dir=asset_dir,
            species_id="veg_tree_oak_01",
            n_vertices=20000,
            height=12.0,
            z_offset=z_offset,
        )

        report: ValidationReport = validate_asset(asset_dir)

        assert report.checks.get("ground_contact_base_aligned") is expected_pass, (
            f"Asset ground contact check for Z_min={z_offset:+.4f} failed: "
            f"got {report.checks.get('ground_contact_base_aligned')}, expected {expected_pass}. "
            f"Errors: {report.errors}"
        )

        if expected_pass:
            assert report.is_valid is True, f"Asset at Z_min={z_offset} failed unexpectedly: {report.errors}"
        else:
            assert report.is_valid is False, f"Asset at Z_min={z_offset} passed unexpectedly"
            assert any("ground contact" in e.lower() for e in report.errors)


# ==============================================================================
# OBJECTIVE 3: STATIC MESH INVARIANT VERIFICATION & STRICT REJECTION
# ==============================================================================

class TestValidatorStaticMeshRejection:
    """
    Adversarially injects armature bones, joints, skin weights, animations, and companion OBJ
    bone directives, verifying that validator.py strictly rejects all non-static artifacts.
    """

    def test_rejection_of_glb_with_skins_array(self, tmp_path: Path):
        """Injects non-empty skins array into GLB container and asserts rejection."""
        base_dir = tmp_path / "base_skins"
        export_synthetic_meshy_asset(base_dir, "veg_tree_oak_01", n_vertices=20000)
        base_glb = base_dir / "veg_tree_oak_01.glb"

        def inject_skins(gltf: Dict[str, Any]):
            gltf["skins"] = [{"joints": [0, 1], "name": "Armature_Trunk"}]

        rigged_glb = tmp_path / "rigged_skins" / "veg_tree_oak_01.glb"
        repack_glb_json(base_glb, rigged_glb, inject_skins)

        report = validate_asset(rigged_glb)
        assert report.is_valid is False
        assert report.checks.get("static_mesh_no_skins") is False
        assert report.checks.get("n_bones_strictly_zero") is False
        assert any("skins" in e.lower() or "bones" in e.lower() for e in report.errors)

    def test_rejection_of_glb_with_animations_array(self, tmp_path: Path):
        """Injects non-empty animations array into GLB container and asserts rejection."""
        base_dir = tmp_path / "base_anims"
        export_synthetic_meshy_asset(base_dir, "veg_tree_oak_01", n_vertices=20000)
        base_glb = base_dir / "veg_tree_oak_01.glb"

        def inject_anims(gltf: Dict[str, Any]):
            gltf["animations"] = [{"name": "Foliage_WindSway", "channels": [], "samplers": []}]

        rigged_glb = tmp_path / "rigged_anims" / "veg_tree_oak_01.glb"
        repack_glb_json(base_glb, rigged_glb, inject_anims)

        report = validate_asset(rigged_glb)
        assert report.is_valid is False
        assert report.checks.get("static_mesh_no_animations") is False
        assert any("animations" in e.lower() for e in report.errors)

    def test_rejection_of_glb_with_joints_attribute(self, tmp_path: Path):
        """Injects JOINTS_0 primitive attribute into GLB mesh and asserts rejection."""
        base_dir = tmp_path / "base_joints"
        export_synthetic_meshy_asset(base_dir, "veg_tree_oak_01", n_vertices=20000)
        base_glb = base_dir / "veg_tree_oak_01.glb"

        def inject_joints(gltf: Dict[str, Any]):
            for mesh in gltf.get("meshes", []):
                for prim in mesh.get("primitives", []):
                    prim["attributes"]["JOINTS_0"] = 0

        rigged_glb = tmp_path / "rigged_joints" / "veg_tree_oak_01.glb"
        repack_glb_json(base_glb, rigged_glb, inject_joints)

        report = validate_asset(rigged_glb)
        assert report.is_valid is False
        assert report.checks.get("static_mesh_no_joint_weights") is False
        assert any("joints_0" in e.lower() for e in report.errors)

    def test_rejection_of_glb_with_weights_attribute(self, tmp_path: Path):
        """Injects WEIGHTS_0 primitive attribute into GLB mesh and asserts rejection."""
        base_dir = tmp_path / "base_weights"
        export_synthetic_meshy_asset(base_dir, "veg_tree_oak_01", n_vertices=20000)
        base_glb = base_dir / "veg_tree_oak_01.glb"

        def inject_weights(gltf: Dict[str, Any]):
            for mesh in gltf.get("meshes", []):
                for prim in mesh.get("primitives", []):
                    prim["attributes"]["WEIGHTS_0"] = 0

        rigged_glb = tmp_path / "rigged_weights" / "veg_tree_oak_01.glb"
        repack_glb_json(base_glb, rigged_glb, inject_weights)

        report = validate_asset(rigged_glb)
        assert report.is_valid is False
        assert report.checks.get("static_mesh_no_joint_weights") is False
        assert any("weights_0" in e.lower() for e in report.errors)

    def test_rejection_of_glb_with_node_skin_reference(self, tmp_path: Path):
        """Injects node-level skin reference into GLB and asserts rejection."""
        base_dir = tmp_path / "base_node_skin"
        export_synthetic_meshy_asset(base_dir, "veg_tree_oak_01", n_vertices=20000)
        base_glb = base_dir / "veg_tree_oak_01.glb"

        def inject_node_skin(gltf: Dict[str, Any]):
            if gltf.get("nodes"):
                gltf["nodes"][0]["skin"] = 0

        rigged_glb = tmp_path / "rigged_node_skin" / "veg_tree_oak_01.glb"
        repack_glb_json(base_glb, rigged_glb, inject_node_skin)

        report = validate_asset(rigged_glb)
        assert report.is_valid is False
        assert report.checks.get("static_mesh_no_node_skins") is False
        assert any("skin" in e.lower() for e in report.errors)

    def test_rejection_of_companion_obj_bone_directives(self, tmp_path: Path):
        """Injects bone and skinning directives into companion OBJ and asserts rejection."""
        asset_dir = tmp_path / "asset_obj_bone"
        export_synthetic_meshy_asset(asset_dir, "veg_tree_oak_01", n_vertices=20000)
        obj_path = asset_dir / "veg_tree_oak_01.obj"

        # Inject bone / skin keywords into OBJ file
        with open(obj_path, "a", encoding="utf-8") as f:
            f.write("\n# Injected bone hierarchy\n")
            f.write("g bone_trunk_root\n")
            f.write("skin 1 0.5 2 0.5\n")

        report = validate_asset(asset_dir)
        assert report.is_valid is False
        assert report.checks.get("obj_no_bones") is False
        assert report.checks.get("n_bones_strictly_zero") is False
        assert any("bone" in e.lower() or "skin" in e.lower() for e in report.errors)


# ==============================================================================
# OBJECTIVE 4: GENERATOR ERROR HANDLING & STRICT NO-FALLBACK IN MESHY MODE
# ==============================================================================

class TestGeneratorMeshyErrorHandling:
    """
    Verifies that when mode == 'meshy', any missing API key or generation failure
    strictly raises RuntimeError/Exception and NEVER emits a procedural fallback mesh.
    """

    def test_meshy_mode_missing_api_key_raises_runtime_error_and_emits_no_mesh(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Asserts RuntimeError is raised and NO procedural mesh is written when MESHY_API_KEY is unset."""
        monkeypatch.delenv("MESHY_API_KEY", raising=False)
        species = get_species("veg_tree_oak_01")
        target_dir = tmp_path / "meshy_no_key"

        with pytest.raises(RuntimeError) as exc_info:
            generate_plant(
                species=species,
                mode="meshy",
                output_dir=target_dir,
                force_regenerate=True,
            )

        assert "MESHY_API_KEY" in str(exc_info.value), f"Unexpected exception message: {exc_info.value}"

        # Assert strictly NO procedural fallback mesh or GLB was emitted
        glb_files = list(target_dir.glob("*.glb"))
        assert len(glb_files) == 0, f"Expected 0 GLB files, but found procedural fallback: {glb_files}"

        manifest_files = list(target_dir.glob("*manifest*.json"))
        assert len(manifest_files) == 0, f"Expected 0 manifest files, but found: {manifest_files}"

    def test_meshy_mode_api_failure_raises_and_emits_no_mesh(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Asserts Exception bubbles up and NO procedural mesh is written when Meshy API call fails."""
        monkeypatch.setenv("MESHY_API_KEY", "msy_fake_adversarial_key_12345")
        species = get_species("veg_tree_oak_01")
        target_dir = tmp_path / "meshy_api_fail"

        # Mock MeshyGenerator._submit_preview to simulate 500 server error
        with patch.object(
            MeshyGenerator,
            "_submit_preview",
            side_effect=RuntimeError("Meshy HTTP 500 Internal Server Error: Gateway Timeout"),
        ):
            with pytest.raises(RuntimeError) as exc_info:
                generate_plant(
                    species=species,
                    mode="meshy",
                    output_dir=target_dir,
                    force_regenerate=True,
                )

            assert "Meshy HTTP 500" in str(exc_info.value)

        # Assert strictly NO procedural fallback mesh or GLB was emitted
        glb_files = list(target_dir.glob("*.glb"))
        assert len(glb_files) == 0, f"Expected 0 GLB files, but found procedural fallback: {glb_files}"

    def test_auto_mode_falls_back_whereas_meshy_mode_strictly_refuses(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """
        Directly compares mode == 'auto' vs mode == 'meshy' under missing credentials:
        - mode == 'auto' gracefully falls back to procedural generator
        - mode == 'meshy' strictly refuses and raises RuntimeError
        """
        monkeypatch.delenv("MESHY_API_KEY", raising=False)
        species = get_species("veg_tree_oak_01")

        # 1. auto mode test
        auto_dir = tmp_path / "auto_fallback"
        auto_asset = generate_plant(
            species=species,
            mode="auto",
            output_dir=auto_dir,
            force_regenerate=True,
        )
        assert auto_asset is not None
        assert auto_asset.source == "procedural"
        assert (auto_dir / f"{species.species_id}.glb").is_file()

        # 2. meshy mode test
        meshy_dir = tmp_path / "meshy_strict"
        with pytest.raises(RuntimeError):
            generate_plant(
                species=species,
                mode="meshy",
                output_dir=meshy_dir,
                force_regenerate=True,
            )

        assert not (meshy_dir / f"{species.species_id}.glb").exists(), (
            "Meshy mode emitted a GLB file despite failure — silent fallback detected!"
        )
