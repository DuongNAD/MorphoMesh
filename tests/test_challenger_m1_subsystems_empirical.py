"""
MorphoMesh Adversarial Empirical Stress Test Suite (Milestone M1).
Subsystems Under Test:
  1. Models Subsystem (`src/morphomesh/models/` and facade `src/morphomesh/models.py`)
  2. Geometry Subsystem (`src/morphomesh/geometry/` and `MeshGeometry`)
  3. Inference Subsystem (`src/morphomesh/inference/` and `CircuitBreaker`)

Author: Challenger M1-1
"""
from __future__ import annotations

import importlib
import importlib.util
import json
import math
import os
import struct
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple
from unittest.mock import patch

import pytest
from pydantic import ValidationError

# Models
import morphomesh.models as models_pkg
from morphomesh.models import (
    ActionableRecommendation,
    AutoRigHumanInput,
    AutoRigHumanOutput,
    AutoRigInput,
    AutoRigOutput,
    BlenderExecuteInput,
    BlenderExecuteOutput,
    BoundingBox,
    BoundingBox3D,
    CaptureMultiAngleInspectionInput,
    CaptureViewportInput,
    Create3DAssetInput,
    Create3DAssetOutput,
    CreateHumanAssetInput,
    CreateHumanAssetOutput,
    CreatureType,
    DefectCategory,
    DefectItem,
    DefectSeverity,
    DiagnosticColorType,
    DiagnosticShadingMode,
    DressHumanInput,
    DressHumanOutput,
    GenerateConceptInput,
    GenerateConceptOutput,
    GroomHumanInput,
    GroomHumanOutput,
    HumanAnatomyConfig,
    HumanAssetResult,
    HumanGroomingResult,
    HumanMaterialResult,
    HumanRigResult,
    HumanWardrobeResult,
    InspectorViewpoint,
    OptimizeTopologyInput,
    OptimizeTopologyOutput,
    RenderPreviewInput,
    SceneObjectInfo,
    SceneStatusInput,
    SetupHumanMaterialsInput,
    SetupHumanMaterialsOutput,
    SetupInspectorCameraInput,
    TargetPreset,
    AnthropometricPreset,
    VALID_INSPECTOR_VIEWPOINTS_SET,
)

# Geometry
from morphomesh.geometry import (
    MeshGeometry,
    add_quad_cap,
    add_quad_ellipsoid,
    compute_quad_metrics,
    export_glb,
    export_obj,
    pad_4,
)

# Inference
from morphomesh.inference import (
    BaseInferenceAdapter,
    CircuitBreaker as InferenceCircuitBreaker,
    EnhancedCreate3DAssetOutput,
    HuggingFaceInferenceAdapter,
    MockInferenceAdapter,
    ReplicateInferenceAdapter,
    get_inference_adapter,
)
from morphomesh.connectors.registry import (
    CircuitBreaker as ConnectorCircuitBreaker,
    CircuitBreakerState,
)


# ==============================================================================
# SECTION 1: ADVERSARIAL STRESS TESTING - PYDANTIC V2 SCHEMAS & STAR IMPORTS
# ==============================================================================

class TestModelsSchemaStress:
    """Adversarial validation stress testing for morphomesh.models schemas."""

    def test_star_import_exports_and_no_collisions(self):
        """Verify star import loads exact 101 symbols without builtin collisions or dropped symbols."""
        ns: Dict[str, Any] = {}
        exec("from morphomesh.models import *", ns)
        imported_keys = {k for k in ns if not k.startswith("_")}

        # 1. Total exported count must match exactly 101
        assert len(models_pkg.__all__) == 101
        assert len(imported_keys) == 101

        # 2. Set equality: no dropped symbols and no unauthorized extras
        assert imported_keys == set(models_pkg.__all__)

        # 3. Facade parity check
        spec = importlib.util.spec_from_file_location("models_facade", "src/morphomesh/models.py")
        assert spec is not None and spec.loader is not None
        facade_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(facade_mod)
        assert set(facade_mod.__all__) == set(models_pkg.__all__)

        # 4. Zero collisions with Python builtins
        import builtins
        collisions = set(models_pkg.__all__) & set(dir(builtins))
        assert not collisions, f"Symbols collide with builtins: {collisions}"

    @pytest.mark.parametrize("invalid_kwargs,expected_err_field", [
        ({}, "prompt"),  # Missing required prompt
        ({"prompt": "ab"}, "prompt"),  # Shorter than min_length=3
        ({"prompt": "x" * 2001}, "prompt"),  # Longer than max_length=2000
        ({"prompt": "Valid prompt", "width": 256}, "width"),  # ge=512 violation
        ({"prompt": "Valid prompt", "width": 4096}, "width"),  # le=2048 violation
        ({"prompt": "Valid prompt", "height": 100}, "height"),  # ge=512 violation
        ({"prompt": "Valid prompt", "height": 3000}, "height"),  # le=2048 violation
        ({"prompt": "Valid prompt", "seed": -10}, "seed"),  # ge=-1 violation
        ({"prompt": "Valid prompt", "width": "not_an_int"}, "width"),  # Invalid type
    ])
    def test_generate_concept_input_validation(self, invalid_kwargs: Dict[str, Any], expected_err_field: str):
        """Adversarial boundary and type errors on GenerateConceptInput."""
        with pytest.raises(ValidationError) as exc_info:
            GenerateConceptInput(**invalid_kwargs)
        err_fields = [e["loc"][0] for e in exc_info.value.errors()]
        assert expected_err_field in err_fields

    def test_generate_concept_dimension_auto_step_rounding(self):
        """Test that dimensions not divisible by 64 are auto-rounded to nearest multiple of 64."""
        inp = GenerateConceptInput(prompt="A test creature", width=1000, height=1050)
        assert inp.width == 1024  # round(1000/64)*64 = 16*64 = 1024
        assert inp.height == 1024  # round(1050/64)*64 = 16*64 = 1024

        inp2 = GenerateConceptInput(prompt="A test creature", width=512, height=768)
        assert inp2.width == 512
        assert inp2.height == 768

    @pytest.mark.parametrize("invalid_kwargs,expected_err_field", [
        ({"guidance_scale": 0.5}, "guidance_scale"),  # ge=1.0 violation
        ({"guidance_scale": 25.0}, "guidance_scale"),  # le=20.0 violation
        ({"seed": -5}, "seed"),  # ge=-1 violation
        ({"texture_resolution": "bad_res"}, "texture_resolution"),  # type error
    ])
    def test_create_3d_asset_input_validation(self, invalid_kwargs: Dict[str, Any], expected_err_field: str):
        """Adversarial boundary errors on Create3DAssetInput."""
        with pytest.raises(ValidationError) as exc_info:
            Create3DAssetInput(**invalid_kwargs)
        err_fields = [e["loc"][0] for e in exc_info.value.errors()]
        assert expected_err_field in err_fields

    def test_create_3d_asset_input_backend_aliasing(self):
        """Verify mutual aliasing and precedence between backend and model_backend."""
        # 1. Specifying backend sets model_backend
        inp1 = Create3DAssetInput(backend="meshy")
        assert inp1.model_backend == "meshy"
        assert inp1.backend == "meshy"

        # 2. Specifying model_backend sets backend
        inp2 = Create3DAssetInput(model_backend="trellis")
        assert inp2.backend == "trellis"
        assert inp2.model_backend == "trellis"

        # 3. Explicit non-mock model_backend takes precedence
        inp3 = Create3DAssetInput(backend="mock", model_backend="hunyuan")
        assert inp3.model_backend == "hunyuan"

    @pytest.mark.parametrize("invalid_kwargs,expected_err_field", [
        ({"target_poly_count": 200}, "target_poly_count"),  # ge=500 violation
        ({"target_poly_count": 600000}, "target_poly_count"),  # le=500000 violation
        ({"target_poly_count": "string_poly"}, "target_poly_count"),  # type error
    ])
    def test_optimize_topology_input_validation(self, invalid_kwargs: Dict[str, Any], expected_err_field: str):
        """Verify polygon count constraints on OptimizeTopologyInput."""
        with pytest.raises(ValidationError) as exc_info:
            OptimizeTopologyInput(**invalid_kwargs)
        err_fields = [e["loc"][0] for e in exc_info.value.errors()]
        assert expected_err_field in err_fields

    @pytest.mark.parametrize("invalid_kwargs,expected_err_field", [
        ({"script": ""}, "script"),  # min_length=1 violation
        ({"script": "print('hello')", "timeout_seconds": 0}, "timeout_seconds"),  # ge=1 violation
        ({"script": "print('hello')", "timeout_seconds": 500}, "timeout_seconds"),  # le=300 violation
        ({"script": "x" * 10001}, "script"),  # max_length=10000 violation
        ({"script": "ok", "return_variables": "not_a_list"}, "return_variables"),  # type error
    ])
    def test_blender_execute_input_validation(self, invalid_kwargs: Dict[str, Any], expected_err_field: str):
        """Verify script constraints and timeouts on BlenderExecuteInput."""
        with pytest.raises(ValidationError) as exc_info:
            BlenderExecuteInput(**invalid_kwargs)
        err_fields = [e["loc"][0] for e in exc_info.value.errors()]
        assert expected_err_field in err_fields

    @pytest.mark.parametrize("invalid_kwargs,expected_err_field", [
        ({"height": 0.5}, "height"),  # ge=1.0 violation
        ({"height": 3.0}, "height"),  # le=2.5 violation
        ({"head_ratio": 4.0}, "head_ratio"),  # ge=5.0 violation
        ({"head_ratio": 12.0}, "head_ratio"),  # le=10.0 violation
        ({"chest_girth": 0.2}, "chest_girth"),  # ge=0.5 violation
        ({"waist_girth": 1.5}, "waist_girth"),  # le=1.2 violation
        ({"poly_budget": 500}, "poly_budget"),  # ge=1000 violation
        ({"poly_budget": 300000}, "poly_budget"),  # le=200000 violation
    ])
    def test_human_anatomy_config_constraints(self, invalid_kwargs: Dict[str, Any], expected_err_field: str):
        """Verify anthropometric boundary checks on HumanAnatomyConfig."""
        with pytest.raises(ValidationError) as exc_info:
            HumanAnatomyConfig(**invalid_kwargs)
        err_fields = [e["loc"][0] for e in exc_info.value.errors()]
        assert expected_err_field in err_fields

    def test_create_human_asset_nested_config_unpacking(self):
        """Verify nested HumanAnatomyConfig is properly unpacked into CreateHumanAssetInput."""
        cfg = HumanAnatomyConfig(height=1.75, head_ratio=8.0, poly_budget=35000, waist_girth=0.62)
        inp = CreateHumanAssetInput(character_name="CustomHero", config=cfg)
        assert inp.height == 1.75
        assert inp.head_ratio == 8.0
        assert inp.poly_budget == 35000
        assert inp.waist_girth == 0.62

        # Output alias verification
        assert CreateHumanAssetOutput is HumanAssetResult
        assert AutoRigHumanOutput is HumanRigResult
        assert SetupHumanMaterialsOutput is HumanMaterialResult
        assert GroomHumanOutput is HumanGroomingResult
        assert DressHumanOutput is HumanWardrobeResult
        assert TargetPreset is AnthropometricPreset

    def test_inspector_camera_viewpoint_casing_and_errors(self):
        """Verify SetupInspectorCameraInput viewpoint normalization and adversarial failure."""
        # 1. Normalization of casing and whitespace
        cam1 = SetupInspectorCameraInput(viewpoint="FRONT")
        assert cam1.viewpoint == "front"

        cam2 = SetupInspectorCameraInput(viewpoint="  Three_Quarter  ")
        assert cam2.viewpoint == "three_quarter"

        cam3 = SetupInspectorCameraInput(viewpoint="TURNTABLE_4VIEWS")
        assert cam3.viewpoint == "turntable_4views"

        # 2. Invalid viewpoints raise ValidationError
        for invalid_vp in ["", "   ", "isometric_xyz", "diagonal_top", "45deg"]:
            with pytest.raises(ValidationError):
                SetupInspectorCameraInput(viewpoint=invalid_vp)

        # 3. Focal length bounds
        with pytest.raises(ValidationError):
            SetupInspectorCameraInput(focal_length=5.0)  # ge=10.0
        with pytest.raises(ValidationError):
            SetupInspectorCameraInput(focal_length=400.0)  # le=300.0

    def test_capture_viewport_shading_and_color_casing(self):
        """Verify CaptureViewportInput case normalization and rejection of illegal modes."""
        vp1 = CaptureViewportInput(shading_mode="solid", color_type="random")
        assert vp1.shading_mode == "SOLID"
        assert vp1.color_type == "RANDOM"

        vp2 = CaptureViewportInput(shading_mode="wireframe", color_type="material")
        assert vp2.shading_mode == "WIREFRAME"
        assert vp2.color_type == "MATERIAL"

        with pytest.raises(ValidationError):
            CaptureViewportInput(shading_mode="RAYTRACED_UNKNOWN")

        with pytest.raises(ValidationError):
            CaptureViewportInput(color_type="NEON_GLOW")

    def test_critique_normalizations_and_aliases(self):
        """Verify DefectSeverity, DefectCategory, and DefectItem field synchronization."""
        # Enum missing normalizations
        assert DefectSeverity("HIGH") == DefectSeverity.CRITICAL
        assert DefectSeverity("WARNING") == DefectSeverity.MAJOR
        assert DefectSeverity("NOTICE") == DefectSeverity.INFO

        assert DefectCategory("CLIPPING") == DefectCategory.PENETRATION
        assert DefectCategory("RIG_PINCH") == DefectCategory.SKINNING_PINCH
        assert DefectCategory("HAIR_CLIPPING") == DefectCategory.GROOMING_COLLISION

        # DefectItem ID synchronization
        d1 = DefectItem(id="DEF-TEST-99", category="CLIPPING", severity="HIGH", description="Mesh puncture")
        assert d1.defect_id == "DEF-TEST-99"
        assert d1.id == "DEF-TEST-99"
        assert d1.category == DefectCategory.PENETRATION
        assert d1.severity == DefectSeverity.CRITICAL

        d2 = DefectItem(defect_id="DEF-TEST-100", category=DefectCategory.PROPORTION, description="Short arms")
        assert d2.id == "DEF-TEST-100"
        assert d2.category == DefectCategory.PROPORTION

        # Test string normalization for PROPORTION
        d3 = DefectItem(defect_id="DEF-TEST-101", category="BODY_PROPORTION", description="Broad shoulders")
        assert d3.category == DefectCategory.PROPORTION

        # Actionable recommendation auto-align
        rec = ActionableRecommendation(action="RELAX_VERTS", category="CLIPPING", priority="HIGH")
        assert rec.description == "RELAX_VERTS"
        assert rec.priority == DefectSeverity.CRITICAL
        assert rec.category == DefectCategory.PENETRATION


# ==============================================================================
# SECTION 2: ADVERSARIAL STRESS TESTING - GEOMETRY SUBSYSTEM & EXPORTERS
# ==============================================================================

class TestGeometrySubsystemStress:
    """Empirical verification and stress testing of MeshGeometry, glTF, and OBJ algorithms."""

    def test_pad_4_direct_alignment(self):
        """Empirically test pad_4 utility across multiple buffer lengths."""
        for length in range(32):
            raw = b"X" * length
            padded = pad_4(raw)
            assert len(padded) % 4 == 0, f"Length {length} padded to {len(padded)}, not divisible by 4"
            assert padded.startswith(raw)
            if length % 4 != 0:
                assert padded[length:] == b"\x00" * ((4 - (length % 4)) % 4)

    @pytest.mark.parametrize("ring_size", [4, 6, 8, 10, 12, 16, 24, 32, 64, 128])
    def test_add_quad_cap_even_rings(self, ring_size: int):
        """Test that add_quad_cap produces strictly pure quads with (N-2)//2 quads and 0 triangles."""
        mesh = MeshGeometry()
        ring = [mesh.add_vertex((math.cos(2*math.pi*i/ring_size), math.sin(2*math.pi*i/ring_size), 0.0)) for i in range(ring_size)]

        add_quad_cap(mesh, ring, flip_normal=False)
        expected_quads = (ring_size - 2) // 2
        q_count, t_count, ratio = compute_quad_metrics(mesh)

        assert q_count == expected_quads
        assert t_count == 0
        assert ratio == 1.0
        assert len(mesh.faces) == expected_quads * 2

    @pytest.mark.parametrize("odd_or_invalid_size", [0, 1, 2, 3, 5, 7, 9, 15, 33])
    def test_add_quad_cap_invalid_rings(self, odd_or_invalid_size: int):
        """Test that add_quad_cap asserts on odd-sized rings or rings with size < 4."""
        mesh = MeshGeometry()
        ring = [mesh.add_vertex((float(i), 0.0, 0.0)) for i in range(odd_or_invalid_size)]
        with pytest.raises(AssertionError):
            add_quad_cap(mesh, ring)

    def test_add_quad_cap_normal_flipping(self):
        """Verify flip_normal parameter inverts winding order."""
        mesh_forward = MeshGeometry()
        r1 = [mesh_forward.add_vertex((float(i), 0.0, 0.0)) for i in range(4)]
        add_quad_cap(mesh_forward, r1, flip_normal=False)

        mesh_flipped = MeshGeometry()
        r2 = [mesh_flipped.add_vertex((float(i), 0.0, 0.0)) for i in range(4)]
        add_quad_cap(mesh_flipped, r2, flip_normal=True)

        f_fwd = mesh_forward.faces
        f_flip = mesh_flipped.faces
        assert len(f_fwd) == 2
        assert len(f_flip) == 2
        # Verify winding inversion: forward quad (0, 1, 2, 3) -> flipped (0, 3, 2, 1)
        assert f_fwd[0] == (0, 1, 2)
        assert f_flip[0] == (0, 3, 2)

    @pytest.mark.parametrize("rings,sectors,radii", [
        (2, 4, (1.0, 1.0, 1.0)),      # Minimal configuration
        (4, 8, (2.0, 1.5, 0.8)),      # Standard ellipsoid
        (6, 12, (0.2, 5.0, 1.0)),     # Highly anisotropic spindle
        (8, 16, (1.0, 1.0, 1.0)),     # High-resolution sphere
        (5, 7, (1.0, 1.0, 1.0)),      # Odd sector input (auto-rounded to even)
    ])
    def test_add_quad_ellipsoid_topology_and_metrics(self, rings: int, sectors: int, radii: Tuple[float, float, float]):
        """Verify quad ellipsoid creates a 100% pure quad, closed, non-degenerate manifold mesh."""
        mesh = MeshGeometry()
        added = add_quad_ellipsoid(mesh, (0.0, 0.0, 0.0), radii, rings=rings, sectors=sectors)

        adj_sectors = max(4, sectors if sectors % 2 == 0 else sectors + 1)
        adj_rings = max(2, rings)
        assert len(added) == adj_rings * adj_sectors

        # Check quad dominance
        quads, tris, ratio = compute_quad_metrics(mesh)
        assert ratio == 1.0, f"Expected 1.0 quad ratio, got {ratio}"
        assert tris == 0, f"Expected 0 isolated triangles, got {tris}"

        # Check normal vectors: all normals must be finite, non-zero, normalized unit vectors
        for i, norm in enumerate(mesh.normals):
            length = math.sqrt(norm[0]**2 + norm[1]**2 + norm[2]**2)
            assert not math.isnan(length) and not math.isinf(length)
            assert abs(length - 1.0) < 1e-4, f"Vertex normal {i} is not normalized: {norm} len={length}"

        # Topological manifoldness test:
        # In a closed 2-manifold surface, every edge must be shared by exactly 2 triangles
        edge_counts: Dict[Tuple[int, int], int] = {}
        for f in mesh.faces:
            edges = [
                (min(f[0], f[1]), max(f[0], f[1])),
                (min(f[1], f[2]), max(f[1], f[2])),
                (min(f[2], f[0]), max(f[2], f[0])),
            ]
            for e in edges:
                edge_counts[e] = edge_counts.get(e, 0) + 1

        for e, count in edge_counts.items():
            assert count == 2, f"Edge {e} has count {count} != 2 (mesh has holes or non-manifold junctions)"

        # Euler characteristic: V - E + F = 2 for closed genus-0 spherical surface
        V = len(mesh.vertices)
        E = len(edge_counts)
        F = len(mesh.faces)
        chi = V - E + F
        assert chi == 2, f"Euler characteristic chi={chi} != 2 (V={V}, E={E}, F={F})"

    def test_gltf_2_binary_chunk_padding_and_alignment(self, tmp_path: Path):
        """Empirically test glTF 2.0 chunk padding (4-byte alignment) on adversarial meshes."""
        test_cases = [
            ("empty", MeshGeometry()),
            ("single_tri", None),
            ("single_quad", None),
            ("odd_verts_7", None),
            ("dense_ellipsoid", None),
        ]

        # Populate single_tri
        m_tri = MeshGeometry()
        m_tri.add_vertex((0.1, 0.2, 0.3), (0, 0, 1), (0, 0))
        m_tri.add_vertex((1.1, 0.2, 0.3), (0, 0, 1), (1, 0))
        m_tri.add_vertex((0.1, 1.2, 0.3), (0, 0, 1), (0, 1))
        m_tri.add_triangle(0, 1, 2)
        test_cases[1] = ("single_tri", m_tri)

        # Populate single_quad
        m_quad = MeshGeometry()
        m_quad.add_vertex((0, 0, 0), (0, 0, 1), (0, 0))
        m_quad.add_vertex((1, 0, 0), (0, 0, 1), (1, 0))
        m_quad.add_vertex((1, 1, 0), (0, 0, 1), (1, 1))
        m_quad.add_vertex((0, 1, 0), (0, 0, 1), (0, 1))
        m_quad.add_quad(0, 1, 2, 3)
        test_cases[2] = ("single_quad", m_quad)

        # Populate odd_verts_7
        m_odd = MeshGeometry()
        for i in range(7):
            m_odd.add_vertex((float(i), float(i*2), 0.5), (0, 1, 0), (i/7.0, 0.5))
        m_odd.add_triangle(0, 1, 2)
        m_odd.add_triangle(2, 3, 4)
        m_odd.add_triangle(4, 5, 6)
        test_cases[3] = ("odd_verts_7", m_odd)

        # Populate dense_ellipsoid
        m_dense = MeshGeometry()
        add_quad_ellipsoid(m_dense, (0, 0, 0), (1, 2, 3), rings=8, sectors=16)
        test_cases[4] = ("dense_ellipsoid", m_dense)

        for label, mesh in test_cases:
            out_file = tmp_path / f"{label}.glb"
            mesh.export_glb(str(out_file))

            assert out_file.exists()
            raw_bytes = out_file.read_bytes()
            total_size = len(raw_bytes)

            # 1. Total file size must be 4-byte aligned
            assert total_size % 4 == 0, f"{label}: total size {total_size} not 4-byte aligned"

            # 2. glTF Header: 12 bytes
            magic, version, header_len = struct.unpack_from("<4sII", raw_bytes, 0)
            assert magic == b"glTF", f"{label}: invalid magic {magic}"
            assert version == 2, f"{label}: invalid version {version}"
            assert header_len == total_size, f"{label}: header len {header_len} != total size {total_size}"

            # 3. Chunk 0: JSON Chunk
            c0_len, c0_type = struct.unpack_from("<I4s", raw_bytes, 12)
            assert c0_type == b"JSON", f"{label}: chunk 0 type is not JSON: {c0_type}"
            assert c0_len % 4 == 0, f"{label}: JSON chunk length {c0_len} is not a multiple of 4"

            # Verify JSON chunk padding is spaces (0x20)
            c0_data = raw_bytes[20 : 20 + c0_len]
            # Strip trailing spaces and parse JSON
            json_text = c0_data.decode("utf-8")
            gltf_dict = json.loads(json_text)
            assert "asset" in gltf_dict
            assert "buffers" in gltf_dict

            # 4. Chunk 1: BIN Chunk
            c1_offset = 12 + 8 + c0_len
            assert c1_offset % 4 == 0, f"{label}: BIN chunk offset {c1_offset} not 4-byte aligned"

            c1_len, c1_type = struct.unpack_from("<I4s", raw_bytes, c1_offset)
            assert c1_type == b"BIN\x00", f"{label}: chunk 1 type is not BIN: {c1_type}"
            assert c1_len % 4 == 0, f"{label}: BIN chunk length {c1_len} is not a multiple of 4"

            # 5. BufferViews byteOffset alignment
            buffer_views = gltf_dict.get("bufferViews", [])
            for bv_idx, bv in enumerate(buffer_views):
                b_offset = bv.get("byteOffset", 0)
                b_len = bv.get("byteLength", 0)
                assert b_offset % 4 == 0, f"{label}: bufferView[{bv_idx}] byteOffset {b_offset} not 4-byte aligned"
                assert b_offset + b_len <= c1_len, f"{label}: bufferView[{bv_idx}] exceeds BIN chunk size"

    def test_gltf_index_format_threshold_uint16_vs_uint32(self, tmp_path: Path):
        """Verify export_glb switches from unsigned short (5123) to unsigned int (5125) when num_verts > 65535."""
        # 1. Mesh under threshold
        m_small = MeshGeometry()
        m_small.add_vertex((0, 0, 0))
        m_small.add_vertex((1, 0, 0))
        m_small.add_vertex((0, 1, 0))
        m_small.add_triangle(0, 1, 2)
        p_small = tmp_path / "small.glb"
        m_small.export_glb(str(p_small))

        data_small = p_small.read_bytes()
        c0_len = struct.unpack_from("<I", data_small, 12)[0]
        json_small = json.loads(data_small[20 : 20 + c0_len].decode("utf-8"))
        idx_accessor_small = json_small["accessors"][3]
        assert idx_accessor_small["componentType"] == 5123  # UNSIGNED_SHORT

        # 2. Mock high-vertex count mesh exceeding 65535
        m_large = MeshGeometry()
        # Add 65537 dummy vertices
        m_large.vertices = [(0.0, 0.0, 0.0)] * 65537
        m_large.normals = [(0.0, 0.0, 1.0)] * 65537
        m_large.uvs = [(0.0, 0.0)] * 65537
        m_large.faces = [(0, 1, 65536)]
        p_large = tmp_path / "large.glb"
        m_large.export_glb(str(p_large))

        data_large = p_large.read_bytes()
        c0_len_large = struct.unpack_from("<I", data_large, 12)[0]
        json_large = json.loads(data_large[20 : 20 + c0_len_large].decode("utf-8"))
        idx_accessor_large = json_large["accessors"][3]
        assert idx_accessor_large["componentType"] == 5125  # UNSIGNED_INT

    def test_obj_string_export_syntax_and_indexing(self, tmp_path: Path):
        """Adversarially verify Wavefront OBJ export format, 1-based indexing, normals and UVs."""
        mesh = MeshGeometry()
        add_quad_ellipsoid(mesh, (10.0, -5.0, 2.5), (1.5, 2.0, 0.5), rings=4, sectors=8)
        obj_path = tmp_path / "adversarial_ellipsoid.obj"
        mesh.export_obj(str(obj_path))

        assert obj_path.exists()
        lines = obj_path.read_text(encoding="utf-8").strip().split("\n")

        v_lines = [l for l in lines if l.startswith("v ")]
        vn_lines = [l for l in lines if l.startswith("vn ")]
        vt_lines = [l for l in lines if l.startswith("vt ")]
        f_lines = [l for l in lines if l.startswith("f ")]

        assert len(v_lines) == len(mesh.vertices)
        assert len(vn_lines) == len(mesh.normals)
        assert len(vt_lines) == len(mesh.uvs)
        assert len(f_lines) == len(mesh.faces)

        # 1. Parse and verify vertex coordinate syntax: "v x y z"
        for idx, line in enumerate(v_lines):
            parts = line.split()[1:]
            assert len(parts) == 3, f"Line {idx}: {line} does not have 3 floats"
            coords = [float(p) for p in parts]
            assert all(not math.isnan(c) and not math.isinf(c) for c in coords)

        # 2. Parse and verify normals: "vn nx ny nz" normalized
        for idx, line in enumerate(vn_lines):
            parts = line.split()[1:]
            assert len(parts) == 3
            norms = [float(p) for p in parts]
            length = math.sqrt(sum(c**2 for c in norms))
            assert abs(length - 1.0) < 1e-4, f"Normal {idx} not normalized: {norms} len={length}"

        # 3. Parse and verify UVs: "vt u v"
        for idx, line in enumerate(vt_lines):
            parts = line.split()[1:]
            assert len(parts) == 2
            uvs = [float(p) for p in parts]
            assert all(not math.isnan(u) and not math.isinf(u) for u in uvs)

        # 4. Parse and verify faces: strictly 1-indexed "f v/vt/vn v/vt/vn v/vt/vn"
        num_v = len(v_lines)
        num_vn = len(vn_lines)
        num_vt = len(vt_lines)
        for idx, line in enumerate(f_lines):
            tokens = line.split()[1:]
            assert len(tokens) == 3, f"Face {idx} is not a triangle: {line}"
            for token in tokens:
                elem = token.split("/")
                assert len(elem) == 3, f"Invalid token '{token}' in face {idx}"
                v_i, vt_i, vn_i = int(elem[0]), int(elem[1]), int(elem[2])
                # 1-indexed bounds check!
                assert 1 <= v_i <= num_v, f"v index {v_i} out of bounds [1, {num_v}]"
                assert 1 <= vt_i <= num_vt, f"vt index {vt_i} out of bounds [1, {num_vt}]"
                assert 1 <= vn_i <= num_vn, f"vn index {vn_i} out of bounds [1, {num_vn}]"


# ==============================================================================
# SECTION 3: ADVERSARIAL STRESS TESTING - INFERENCE CIRCUIT BREAKER & FALLBACKS
# ==============================================================================

class TestInferenceCircuitBreakerAndFallbacks:
    """Stress test CircuitBreaker state transitions and procedural generation fallbacks."""

    def test_inference_circuit_breaker_full_state_lifecycle(self):
        """
        Adversarially verify complete state machine:
        CLOSED -> (failures reach threshold) -> OPEN -> (timeout) -> HALF_OPEN -> (failure) -> OPEN
        -> (timeout) -> HALF_OPEN -> (success) -> CLOSED.
        """
        cb = InferenceCircuitBreaker(failure_threshold=3, recovery_timeout=0.1)

        # 1. Initial CLOSED state
        assert cb.state == "CLOSED"
        assert cb.can_attempt() is True
        assert cb.failure_count == 0

        # 2. Failures under threshold stay CLOSED
        cb.record_failure()
        assert cb.state == "CLOSED"
        assert cb.failure_count == 1
        assert cb.can_attempt() is True

        cb.record_failure()
        assert cb.state == "CLOSED"
        assert cb.failure_count == 2
        assert cb.can_attempt() is True

        # 3. Reaching threshold trips to OPEN
        cb.record_failure()
        assert cb.state == "OPEN"
        assert cb.failure_count == 3
        assert cb.can_attempt() is False

        # 4. Fast-rejection while timeout has not elapsed
        assert cb.can_attempt() is False
        assert cb.state == "OPEN"

        # 5. Recovery timeout triggers transition to HALF_OPEN
        time.sleep(0.12)
        assert cb.can_attempt() is True
        assert cb.state == "HALF_OPEN"

        # 6. Failure in HALF_OPEN immediately re-trips back to OPEN
        cb.record_failure()
        assert cb.state == "OPEN"
        assert cb.can_attempt() is False

        # 7. Recovery timeout triggers transition to HALF_OPEN again
        time.sleep(0.12)
        assert cb.can_attempt() is True
        assert cb.state == "HALF_OPEN"

        # 8. Success in HALF_OPEN recovers to CLOSED and clears counter
        cb.record_success()
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0
        assert cb.can_attempt() is True

    def test_connectors_circuit_breaker_concurrency_and_probe_gating(self):
        """Test multi-threaded stress and probe gating on morphomesh.connectors CircuitBreaker."""
        cb = ConnectorCircuitBreaker(failure_threshold=5, recovery_timeout=0.1, half_open_max_attempts=1)
        assert cb.state == CircuitBreakerState.CLOSED

        # Multi-threaded failure spam
        def worker_record():
            for _ in range(10):
                cb.record_failure(RuntimeError("worker thread failure"))

        threads = [threading.Thread(target=worker_record) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert cb.state == CircuitBreakerState.OPEN
        assert cb.can_attempt() is False

        # Sleep past timeout
        time.sleep(0.12)
        # First attempt transitions to HALF_OPEN and returns True
        assert cb.can_attempt() is True
        assert cb.state == CircuitBreakerState.HALF_OPEN

        # Second attempt before resolution blocked because half_open_max_attempts=1
        assert cb.can_attempt() is False

        # Resolution with success
        cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.can_attempt() is True

    def test_replicate_adapter_circuit_breaker_fallback(self):
        """Verify ReplicateInferenceAdapter routes to procedural fallback on tripped breaker."""
        adapter = ReplicateInferenceAdapter(api_token="valid_simulated_token")
        # Force breaker trip
        for _ in range(3):
            adapter.circuit_breaker.record_failure()
        assert adapter.circuit_breaker.state == "OPEN"

        # Concept generation fallback
        req_c = GenerateConceptInput(prompt="Armored Bear")
        out_c = adapter.generate_concept(req_c)
        assert isinstance(out_c, GenerateConceptOutput)
        assert out_c.status == "mock_success"

        # 3D asset generation fallback
        req_a = Create3DAssetInput(concept_id="test-replicate", export_format="glb")
        out_a = adapter.generate_3d_asset(req_a)
        assert isinstance(out_a, Create3DAssetOutput)
        assert out_a.backend_used == "mock"
        assert os.path.isfile(out_a.mesh_path)

    def test_huggingface_adapter_circuit_breaker_fallback(self):
        """Verify HuggingFaceInferenceAdapter routes to procedural fallback on tripped breaker."""
        adapter = HuggingFaceInferenceAdapter(api_token="valid_simulated_token")
        # Force breaker trip
        for _ in range(3):
            adapter.circuit_breaker.record_failure()
        assert adapter.circuit_breaker.state == "OPEN"

        req_c = GenerateConceptInput(prompt="Celestial Phoenix")
        out_c = adapter.generate_concept(req_c)
        assert out_c.status == "mock_success"

        req_a = Create3DAssetInput(concept_id="test-hf", export_format="glb")
        out_a = adapter.generate_3d_asset(req_a)
        assert out_a.backend_used == "mock"
        assert os.path.isfile(out_a.mesh_path)

    @pytest.mark.parametrize("backend_name", ["trellis", "hunyuan", "anycreature", "meshy", "tripo"])
    def test_mock_adapter_catastrophic_connector_failure_fallback(self, backend_name: str):
        """Verify MockInferenceAdapter catches connector crashes and reliably triggers procedural fallback."""
        adapter = MockInferenceAdapter()
        req = Create3DAssetInput(concept_id=f"test-{backend_name}", model_backend=backend_name, export_format="glb")

        with patch("morphomesh.inference.mock.get_connector_registry") as mock_reg:
            conn = mock_reg.return_value.get.return_value
            conn.execute.side_effect = ConnectionError("Simulated remote server down")
            conn.execute_with_resilience.side_effect = ConnectionError("Simulated remote server down")

            out = adapter.generate_3d_asset(req)
            assert isinstance(out, Create3DAssetOutput)
            assert out.vertex_count > 0
            assert out.face_count > 0
            assert os.path.isfile(out.mesh_path)
            assert out.bounding_box.dimensions[0] > 0.0
            assert out.bounding_box.dimensions[1] > 0.0
            assert out.bounding_box.dimensions[2] > 0.0
