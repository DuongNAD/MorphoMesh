"""
MorphoMesh: Inference Adapter and Procedural Geometry Test Suite.

Tests MockInferenceAdapter, procedural MeshGeometry synthesis (GLB & OBJ containers),
PBR texture generation (Albedo, Normal, Roughness, Metallic), CircuitBreaker logic,
cloud adapter fallbacks, and the get_inference_adapter factory.
"""

from __future__ import annotations

import os
import struct
import time
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from morphomesh.inference_adapter import (
    CircuitBreaker,
    HuggingFaceInferenceAdapter,
    MeshGeometry,
    MockInferenceAdapter,
    ReplicateInferenceAdapter,
    get_inference_adapter,
)
from morphomesh.models import (
    Create3DAssetInput,
    Create3DAssetOutput,
    GenerateConceptInput,
    GenerateConceptOutput,
)

# ==============================================================================
# 1. PROCEDURAL MESH GEOMETRY UNIT TESTS
# ==============================================================================

class TestMeshGeometry:
    """Verify in-memory 3D mesh building and export primitives."""

    def test_empty_mesh(self):
        geom = MeshGeometry()
        assert len(geom.vertices) == 0
        assert len(geom.normals) == 0
        assert len(geom.uvs) == 0
        assert len(geom.faces) == 0
        bbox = geom.compute_bounding_box()
        assert bbox.dimensions == [0.0, 0.0, 0.0]

    def test_add_vertex_and_faces(self):
        geom = MeshGeometry()
        v0 = geom.add_vertex((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, 0.0))
        v1 = geom.add_vertex((1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0))
        v2 = geom.add_vertex((1.0, 1.0, 0.0), (0.0, 0.0, 1.0), (1.0, 1.0))
        v3 = geom.add_vertex((0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (0.0, 1.0))

        geom.add_triangle(v0, v1, v2)
        assert len(geom.faces) == 1

        geom.add_quad(v0, v1, v2, v3)
        assert len(geom.faces) == 3  # 1 initial + 2 from quad

    def test_add_box(self):
        geom = MeshGeometry()
        geom.add_box(center=(0.0, 0.0, 0.0), size=(2.0, 2.0, 2.0))
        # A box has 6 faces * 4 vertices = 24 vertices, 6 * 2 triangles = 12 faces
        assert len(geom.vertices) == 24
        assert len(geom.faces) == 12

        bbox = geom.compute_bounding_box()
        assert bbox.min_point == [-1.0, -1.0, -1.0]
        assert bbox.max_point == [1.0, 1.0, 1.0]
        assert bbox.dimensions == [2.0, 2.0, 2.0]

    def test_add_cylinder(self):
        geom = MeshGeometry()
        geom.add_cylinder(base_center=(0.0, 0.0, 0.0), radius=1.0, height=2.0, segments=8, axis="Z")
        assert len(geom.vertices) == 16  # 8 bottom + 8 top
        assert len(geom.faces) == 16  # 8 quads * 2 triangles

        bbox = geom.compute_bounding_box()
        assert bbox.min_point[2] == 0.0
        assert bbox.max_point[2] == 2.0

    def test_add_sphere(self):
        geom = MeshGeometry()
        geom.add_sphere(center=(0.0, 0.0, 1.0), radius=0.5, rings=6, sectors=8)
        assert len(geom.vertices) > 0
        assert len(geom.faces) > 0
        bbox = geom.compute_bounding_box()
        assert pytest.approx(bbox.dimensions[0], abs=0.05) == 1.0
        assert pytest.approx(bbox.dimensions[2], abs=0.05) == 1.0

    def test_export_obj(self, tmp_path: Path):
        obj_file = tmp_path / "test.obj"
        geom = MeshGeometry()
        geom.add_box((0.0, 0.0, 0.0), (1.0, 1.0, 1.0))
        geom.export_obj(str(obj_file))

        assert obj_file.exists()
        content = obj_file.read_text(encoding="utf-8")
        assert "v " in content
        assert "vn " in content
        assert "vt " in content
        assert "f " in content

        # Count vertex and face lines
        lines = content.strip().split("\n")
        v_lines = [l for l in lines if l.startswith("v ")]
        f_lines = [l for l in lines if l.startswith("f ")]
        assert len(v_lines) == 24
        assert len(f_lines) == 12

    def test_export_glb(self, tmp_path: Path):
        glb_file = tmp_path / "test.glb"
        geom = MeshGeometry()
        geom.add_box((0.0, 0.0, 0.0), (1.0, 1.0, 1.0))
        geom.export_glb(str(glb_file))

        assert glb_file.exists()
        data = glb_file.read_bytes()
        assert len(data) > 100

        # glTF 2.0 Binary Header validation
        magic, version, total_length = struct.unpack_from("<4sII", data, 0)
        assert magic == b"glTF"
        assert version == 2
        assert total_length == len(data)

        # First chunk: JSON
        chunk0_len, chunk0_type = struct.unpack_from("<I4s", data, 12)
        assert chunk0_type == b"JSON"

        # Second chunk: BIN
        chunk1_offset = 12 + 8 + chunk0_len
        _chunk1_len, chunk1_type = struct.unpack_from("<I4s", data, chunk1_offset)
        assert chunk1_type == b"BIN\x00"


# ==============================================================================
# 2. MOCK INFERENCE ADAPTER: CONCEPT GENERATION
# ==============================================================================

class TestMockInferenceConceptGeneration:
    """Verify MockInferenceAdapter 2D concept generation."""

    def test_generate_concept_basic(self, mock_adapter: MockInferenceAdapter):
        req = GenerateConceptInput(prompt="Armored direwolf with crystal horn", width=1024, height=1024)
        out = mock_adapter.generate_concept(req)

        assert isinstance(out, GenerateConceptOutput)
        assert out.concept_id.startswith("concept-")
        assert os.path.isfile(out.image_path)
        assert os.path.isfile(out.rgba_image_path)
        assert out.status == "mock_success"
        assert out.dimensions == [1024, 1024]
        assert "direwolf" in out.prompt_enhanced.lower()

        # Validate image content
        with Image.open(out.image_path) as img:
            assert img.format == "PNG"
            assert img.size == (1024, 1024)

        # Validate RGBA image content
        with Image.open(out.rgba_image_path) as rgba:
            assert rgba.format == "PNG"
            assert rgba.mode == "RGBA"

    def test_deterministic_seed(self, mock_adapter: MockInferenceAdapter):
        req1 = GenerateConceptInput(prompt="Chimera creature", seed=9999, width=512, height=512)
        req2 = GenerateConceptInput(prompt="Chimera creature", seed=9999, width=512, height=512)

        out1 = mock_adapter.generate_concept(req1)
        out2 = mock_adapter.generate_concept(req2)

        assert out1.seed_used == 9999
        assert out2.seed_used == 9999

        # Compare pixel arrays
        img1 = np.array(Image.open(out1.image_path))
        img2 = np.array(Image.open(out2.image_path))
        np.testing.assert_array_equal(img1, img2)

    @pytest.mark.parametrize("creature_type", ["quadruped", "biped", "winged", "custom"])
    def test_creature_archetypes_concept(self, mock_adapter: MockInferenceAdapter, creature_type: str):
        req = GenerateConceptInput(prompt=f"A mythical {creature_type}", creature_type=creature_type)
        out = mock_adapter.generate_concept(req)
        assert out.creature_type == creature_type
        assert os.path.isfile(out.image_path)


# ==============================================================================
# 3. MOCK INFERENCE ADAPTER: 3D ASSET GENERATION
# ==============================================================================

class TestMockInference3DAssetGeneration:
    """Verify MockInferenceAdapter 3D mesh reconstruction and PBR texture baking."""

    def test_generate_glb_quadruped(self, mock_adapter: MockInferenceAdapter):
        req = Create3DAssetInput(concept_id="concept-quadruped", export_format="glb", generate_pbr=True)
        out = mock_adapter.generate_3d_asset(req)

        assert isinstance(out, Create3DAssetOutput)
        assert out.format == "glb"
        assert os.path.isfile(out.mesh_path)
        assert out.mesh_path.endswith(".glb")
        assert out.vertex_count > 0
        assert out.face_count > 0
        assert out.backend_used == "mock"

        # Verify GLB file header
        with open(out.mesh_path, "rb") as f:
            magic = f.read(4)
            assert magic == b"glTF"

        # Verify bounding box
        bbox = out.bounding_box
        assert bbox.dimensions[0] > 0.0
        assert bbox.dimensions[1] > 0.0
        assert bbox.dimensions[2] > 0.0

    def test_generate_obj_format(self, mock_adapter: MockInferenceAdapter):
        req = Create3DAssetInput(concept_id="concept-quadruped", export_format="obj")
        out = mock_adapter.generate_3d_asset(req)

        assert out.format == "obj"
        assert os.path.isfile(out.mesh_path)
        assert out.mesh_path.endswith(".obj")

        with open(out.mesh_path, "r", encoding="utf-8") as f:
            first_line = f.readline()
            assert "MorphoMesh" in first_line

    @pytest.mark.parametrize("archetype", ["biped", "winged", "primitive", "quadruped"])
    def test_generate_different_archetypes(self, mock_adapter: MockInferenceAdapter, archetype: str):
        req = Create3DAssetInput(concept_id=f"test-{archetype}", export_format="glb")
        out = mock_adapter.generate_3d_asset(req)
        assert out.vertex_count > 0
        assert out.face_count > 0
        assert os.path.isfile(out.mesh_path)


# ==============================================================================
# 4. PBR TEXTURES GENERATION & VERIFICATION
# ==============================================================================

class TestPbrTextureSynthesis:
    """Verify procedural PBR textures generation (Albedo, Normal, Roughness, Metallic)."""

    def test_all_four_pbr_maps_generated(self, mock_adapter: MockInferenceAdapter):
        res = 512
        req = Create3DAssetInput(
            concept_id="concept-armored-chimera",
            export_format="glb",
            generate_pbr=True,
            texture_resolution=res,
        )
        out = mock_adapter.generate_3d_asset(req)

        assert out.has_pbr_materials is True
        assert "albedo" in out.texture_paths
        assert "normal" in out.texture_paths
        assert "roughness" in out.texture_paths
        assert "metallic" in out.texture_paths

        # Verify each texture is a valid, readable PNG with the expected mode and dimensions
        for tex_key in ["albedo", "normal", "roughness", "metallic"]:
            tex_path = out.texture_paths[tex_key]
            assert os.path.isfile(tex_path), f"Texture {tex_key} missing at {tex_path}"

            with Image.open(tex_path) as img:
                assert img.format == "PNG", f"Texture {tex_key} is not a PNG file."
                assert img.size == (res, res), f"Texture {tex_key} size {img.size} != {(res, res)}"
                if tex_key in ("albedo", "normal"):
                    assert img.mode == "RGB", f"{tex_key} should be RGB, got {img.mode}"
                elif tex_key in ("roughness", "metallic"):
                    assert img.mode == "L", f"{tex_key} should be L, got {img.mode}"

    def test_generate_pbr_false_omits_textures(self, mock_adapter: MockInferenceAdapter):
        req = Create3DAssetInput(concept_id="concept-no-textures", generate_pbr=False)
        out = mock_adapter.generate_3d_asset(req)
        assert out.has_pbr_materials is False
        assert len(out.texture_paths) == 0


# ==============================================================================
# 5. CIRCUIT BREAKER & REMOTE ADAPTER FALLBACKS
# ==============================================================================

class TestCircuitBreakerAndCloudAdapters:
    """Verify CircuitBreaker state transitions and Cloud API fallback behavior."""

    def test_circuit_breaker_transitions(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.2)
        assert cb.state == "CLOSED"
        assert cb.can_attempt() is True

        # 1st & 2nd failure
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "CLOSED"
        assert cb.can_attempt() is True

        # 3rd failure trips the breaker
        cb.record_failure()
        assert cb.state == "OPEN"
        assert cb.can_attempt() is False

        # Wait for recovery timeout
        time.sleep(0.25)
        assert cb.can_attempt() is True
        assert cb.state == "HALF_OPEN"

        # Success resets to CLOSED
        cb.record_success()
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0

    def test_replicate_adapter_fallback_without_token(self, temp_storage_dir: Path):
        adapter = ReplicateInferenceAdapter(api_token=None)
        req = GenerateConceptInput(prompt="Direwolf")
        out = adapter.generate_concept(req)
        assert out.status == "mock_success"

        req_3d = Create3DAssetInput(concept_id="concept-wolf")
        out_3d = adapter.generate_3d_asset(req_3d)
        assert out_3d.backend_used == "mock"

    def test_huggingface_adapter_fallback_without_token(self, temp_storage_dir: Path):
        adapter = HuggingFaceInferenceAdapter(api_token=None)
        req = GenerateConceptInput(prompt="Griffin")
        out = adapter.generate_concept(req)
        assert out.status == "mock_success"

        req_3d = Create3DAssetInput(concept_id="concept-griffin")
        out_3d = adapter.generate_3d_asset(req_3d)
        assert out_3d.backend_used == "mock"


# ==============================================================================
# 6. INFERENCE ADAPTER FACTORY
# ==============================================================================

class TestInferenceAdapterFactory:
    """Verify get_inference_adapter pluggable factory."""

    def test_factory_mock(self):
        adapter = get_inference_adapter("mock")
        assert isinstance(adapter, MockInferenceAdapter)

    def test_factory_replicate(self):
        adapter = get_inference_adapter("replicate")
        assert isinstance(adapter, ReplicateInferenceAdapter)

    def test_factory_huggingface(self):
        adapter_hf = get_inference_adapter("huggingface")
        assert isinstance(adapter_hf, HuggingFaceInferenceAdapter)
        adapter_short = get_inference_adapter("hf")
        assert isinstance(adapter_short, HuggingFaceInferenceAdapter)

    def test_factory_default_fallback(self):
        adapter = get_inference_adapter("unknown_provider_xyz")
        assert isinstance(adapter, MockInferenceAdapter)
