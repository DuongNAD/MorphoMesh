"""
MorphoMesh: Open-Source Connectors Integration Test Suite.

Comprehensive offline unit and integration tests covering:
  1. CircuitBreaker state machine transitions and fallback routing.
  2. ConnectorRegistry auto-registration, health/dependency diagnostics, and fallback execution.
  3. TrellisConnector (O-Voxel DiT, 4-channel PBR texture baking, GLB export, REST parsing).
  4. Animals3DConnector (SMAL 35 landmarks, Rx(+90) transform, Rigify Wolf mapping, skin weights).
  5. AnyCreatureConnector (NLP BodyGraph DAG compilation, procedural mesh synthesis, gait bindings).
  6. MeshAnythingConnector (Autoregressive retopology, <1600 quad face budget, QuadriFlow fallback).
  7. HunyuanConnector (2-stage shape & multi-view PBR texture baking, network boundary isolation).
  8. InferenceAdapter & FastMCP Server integration and resilient fallback mechanisms.

100% Offline: zero external network calls, zero external API keys required.
"""

from __future__ import annotations

import io
import json
import os
import struct
import time
from unittest.mock import patch

import numpy as np
import pytest
from PIL import Image

from morphomesh.connectors import (
    AnimalPoseInput,
    Animals3DConnector,
    Animals3DOutput,
    AnyCreatureConnector,
    AnyCreatureOutput,
    BaseConnector,
    CircuitBreaker,
    CircuitBreakerState,
    ConnectorRegistry,
    DependencyCheckResult,
    HealthCheckResult,
    HunyuanConnector,
    HunyuanInput,
    HunyuanOutput,
    MeshAnythingConnector,
    MeshAnythingInput,
    MeshAnythingOutput,
    PBRTextureMaps,
    RetopologyConfig,
    RX_90_SMAL_TO_BLENDER,
    SMAL_TO_RIGIFY_WOLF,
    TrellisConnector,
    TrellisInput,
    TrellisOutput,
    transform_smal_to_blender,
)
from morphomesh.inference_adapter import (
    EnhancedCreate3DAssetOutput,
    MeshGeometry,
    get_inference_adapter,
)
from morphomesh.models import (
    ERR_BACKEND_UNAVAILABLE,
    ERR_IMAGE_NOT_FOUND,
    ERR_INPUT_MESH_NOT_FOUND,
    ERR_INVALID_ARGUMENT,
    Create3DAssetInput,
    MorphoMeshException,
)


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture(autouse=True)
def reset_registry():
    """Ensure registry state is reset before and after each test."""
    ConnectorRegistry.reset_all()
    yield
    ConnectorRegistry.reset_all()


@pytest.fixture
def sample_concept_image(tmp_path) -> str:
    """Create a temporary concept RGBA image for connector testing."""
    img = Image.new("RGBA", (512, 512), (255, 255, 255, 255))
    # Draw simple creature shape
    arr = np.array(img)
    arr[100:400, 100:400, :3] = [80, 90, 110]
    img = Image.fromarray(arr, mode="RGBA")
    img_path = str(tmp_path / "concept_creature.png")
    img.save(img_path)
    return img_path


@pytest.fixture
def sample_dense_mesh(tmp_path) -> str:
    """Create a temporary 3D mesh container (GLB) for retopology testing."""
    geom = MeshGeometry()
    geom.add_box((0.0, 0.0, 0.5), (0.8, 1.2, 0.6))
    geom.add_cylinder((0.0, 0.5, 0.8), 0.2, 0.4, axis="Z")
    geom.add_sphere((0.0, 0.65, 1.1), 0.25)
    mesh_path = str(tmp_path / "dense_input.glb")
    geom.export_glb(mesh_path)
    return mesh_path


# ==============================================================================
# 1. CIRCUIT BREAKER STATE MACHINE TESTS
# ==============================================================================

class TestCircuitBreaker:
    """Validate 3-state finite state machine, threshold transitions, and fallback."""

    def test_initial_state_closed(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0
        assert cb.can_attempt() is True

    def test_record_success_resets_failures(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
        cb.record_failure(RuntimeError("Temporary error 1"))
        assert cb.failure_count == 1
        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == CircuitBreakerState.CLOSED

    def test_trips_to_open_after_threshold_failures(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
        cb.record_failure(RuntimeError("Fail 1"))
        assert cb.state == CircuitBreakerState.CLOSED
        cb.record_failure(RuntimeError("Fail 2"))
        assert cb.state == CircuitBreakerState.CLOSED
        cb.record_failure(RuntimeError("Fail 3"))
        assert cb.state == CircuitBreakerState.OPEN
        assert cb.can_attempt() is False

    def test_open_rejects_and_routes_to_fallback(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60.0)
        cb.trip()
        assert cb.state == CircuitBreakerState.OPEN

        def primary_func(x):
            return x * 2

        def fallback_func(x):
            return f"fallback_{x}"

        # Without fallback -> raises MorphoMeshException
        with pytest.raises(MorphoMeshException) as exc_info:
            cb.call(primary_func, 10)
        assert exc_info.value.code == ERR_BACKEND_UNAVAILABLE

        # With fallback -> executes fallback cleanly
        result = cb.call(primary_func, 10, fallback=fallback_func)
        assert result == "fallback_10"

    def test_transitions_to_half_open_after_recovery_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        cb.trip()
        assert cb.state == CircuitBreakerState.OPEN

        # Before timeout
        assert cb.can_attempt() is False

        # Sleep past recovery timeout (min clamped to 0.1s in CircuitBreaker)
        time.sleep(0.15)
        assert cb.can_attempt() is True
        assert cb.state == CircuitBreakerState.HALF_OPEN

    def test_half_open_success_closes_breaker(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        cb.trip()
        time.sleep(0.15)

        def recover_func():
            return "recovered"

        res = cb.call(recover_func)
        assert res == "recovered"
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0

    def test_half_open_failure_reopens_breaker(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        cb.trip()
        time.sleep(0.15)

        def failing_func():
            raise ConnectionError("Still unreachable")

        with pytest.raises(ConnectionError):
            cb.call(failing_func)

        assert cb.state == CircuitBreakerState.OPEN

    def test_manual_trip_and_reset(self):
        cb = CircuitBreaker()
        cb.trip()
        assert cb.state == CircuitBreakerState.OPEN
        cb.reset()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0


# ==============================================================================
# 2. CONNECTOR REGISTRY TESTS
# ==============================================================================

class TestConnectorRegistry:
    """Validate ConnectorRegistry auto-discovery, lifecycle, and health auditing."""

    def test_all_five_canonical_connectors_registered(self):
        connectors = ConnectorRegistry.list_connectors()
        expected = ["animals3d", "anycreature", "hunyuan", "meshanything", "trellis"]
        assert sorted(connectors) == expected

    def test_get_instantiates_singleton(self):
        c1 = ConnectorRegistry.get("trellis")
        c2 = ConnectorRegistry.get("trellis")
        assert c1 is c2
        assert isinstance(c1, TrellisConnector)
        assert c1.is_initialized is True

    def test_unregistered_connector_raises_error(self):
        with pytest.raises(MorphoMeshException) as exc_info:
            ConnectorRegistry.get("non_existent_connector_xyz")
        assert exc_info.value.code == ERR_INVALID_ARGUMENT

    def test_health_check_all_returns_valid_models(self):
        health_map = ConnectorRegistry.health_check_all()
        assert len(health_map) == 5
        for cid, health in health_map.items():
            assert isinstance(health, HealthCheckResult)
            assert health.status in ("healthy", "degraded", "unhealthy", "offline", "unknown")
            assert health.latency_ms >= 0.0
            assert isinstance(health.dependencies_met, bool)

    def test_check_dependencies_all(self):
        dep_map = ConnectorRegistry.check_dependencies_all()
        assert len(dep_map) == 5
        for cid, dep in dep_map.items():
            assert isinstance(dep, DependencyCheckResult)
            assert isinstance(dep.satisfied, bool)
            assert isinstance(dep.missing_packages, list)

    def test_execute_with_fallback_success(self, sample_concept_image, tmp_path):
        inp = TrellisInput(
            image_path=sample_concept_image,
            output_dir=str(tmp_path / "reg_test"),
        )
        out = ConnectorRegistry.execute_with_fallback(
            "trellis",
            lambda req: "fallback_result",
            inp,
        )
        assert isinstance(out, TrellisOutput)
        assert os.path.exists(out.glb_path)

    def test_execute_with_fallback_on_failure(self):
        def fallback_fn(*args, **kwargs):
            return "invoked_fallback"

        # Force connector to fail by tripping its circuit breaker
        trellis = ConnectorRegistry.get("trellis")
        trellis.circuit_breaker.trip()

        out = ConnectorRegistry.execute_with_fallback(
            "trellis",
            fallback_fn,
            {"image_path": "dummy.png"},
        )
        assert out == "invoked_fallback"

    def test_get_all_returns_all_instances(self):
        all_conns = ConnectorRegistry.get_all()
        assert set(all_conns.keys()) == {"animals3d", "anycreature", "hunyuan", "meshanything", "trellis"}
        for inst in all_conns.values():
            assert isinstance(inst, BaseConnector)


# ==============================================================================
# 3. MICROSOFT TRELLIS CONNECTOR TESTS
# ==============================================================================

class TestTrellisConnector:
    """Validate TrellisConnector offline mesh generation, PBR maps, and REST parsing."""

    def test_mock_generation_glb_and_pbr(self, sample_concept_image, tmp_path):
        connector = TrellisConnector(config={"mode": "mock"})
        out_dir = str(tmp_path / "trellis_out")
        inp = TrellisInput(
            image_path=sample_concept_image,
            generate_pbr=True,
            texture_resolution=512,
            output_dir=out_dir,
        )
        output = connector.execute(inp)

        assert isinstance(output, TrellisOutput)
        assert os.path.exists(output.glb_path)
        assert output.vertex_count > 0
        assert output.face_count > 0
        assert output.execution_mode == "mock_procedural"

        # Verify valid GLB container header
        with open(output.glb_path, "rb") as f:
            magic, version, length = struct.unpack("<4sII", f.read(12))
            assert magic == b"glTF"
            assert version == 2
            assert length > 0

        # Verify all 4 PBR texture maps exist
        pbr = output.pbr_textures
        assert pbr.albedo_path and os.path.exists(pbr.albedo_path)
        assert pbr.normal_path and os.path.exists(pbr.normal_path)
        assert pbr.roughness_path and os.path.exists(pbr.roughness_path)
        assert pbr.metallic_path and os.path.exists(pbr.metallic_path)

        # Verify PIL can load each texture and inspect color space properties
        with Image.open(pbr.albedo_path) as img:
            assert img.mode == "RGB"
            assert img.size == (512, 512)
        with Image.open(pbr.normal_path) as img:
            assert img.mode == "RGB"
            # Tangent space normal Z component should be strong (blue-ish)
            normal_sample = np.array(img)[256, 256]
            assert normal_sample[2] >= 200  # High +Z (upward normal)
        with Image.open(pbr.roughness_path) as img:
            assert img.mode == "L"
        with Image.open(pbr.metallic_path) as img:
            assert img.mode == "L"

    def test_pbr_color_spaces(self, sample_concept_image, tmp_path):
        connector = TrellisConnector()
        inp = TrellisInput(
            image_path=sample_concept_image,
            output_dir=str(tmp_path / "cs_test"),
            texture_resolution=512,
        )
        out = connector.execute(inp)
        color_maps = out.pbr_textures.color_space_map
        assert color_maps["albedo"] == "sRGB"
        assert color_maps["normal"] == "Non-Color"
        assert color_maps["roughness"] == "Non-Color"
        assert color_maps["metallic"] == "Non-Color"

    def test_missing_image_raises_error(self, tmp_path):
        connector = TrellisConnector()
        inp = TrellisInput(
            image_path=str(tmp_path / "non_existent_image_123.png"),
            output_dir=str(tmp_path),
        )
        with pytest.raises(MorphoMeshException) as exc_info:
            connector.execute(inp)
        assert exc_info.value.code == ERR_IMAGE_NOT_FOUND

    def test_simulated_remote_rest_api_parsing(self, sample_concept_image, tmp_path):
        connector = TrellisConnector(
            config={
                "mode": "remote",
                "endpoint_url": "http://mock-trellis-service:8002/v1",
                "timeout_seconds": 10.0,
            }
        )

        mock_response_data = {
            "vertex_count": 4200,
            "face_count": 8400,
            "status": "success",
        }
        mock_resp = io.BytesIO(json.dumps(mock_response_data).encode("utf-8"))

        with patch("urllib.request.urlopen", return_value=mock_resp):
            inp = TrellisInput(
                image_path=sample_concept_image,
                output_dir=str(tmp_path / "remote_out"),
                texture_resolution=512,
            )
            out = connector.execute(inp)

            assert out.execution_mode == "remote_api"
            assert out.vertex_count == 4200
            assert out.face_count == 8400
            assert out.glb_path.endswith(".glb")
            assert out.pbr_textures.albedo_path and os.path.exists(out.pbr_textures.albedo_path)

    def test_resilience_fallback_on_remote_failure(self, sample_concept_image, tmp_path):
        breaker = CircuitBreaker(failure_threshold=1)
        connector = TrellisConnector(
            config={"mode": "remote", "endpoint_url": "http://invalid-host-999:8002"},
            circuit_breaker=breaker,
        )

        def fallback_handler(inp, **kwargs):
            return TrellisOutput(
                asset_id="trellis_fb_fallback",
                glb_path=str(tmp_path / "fb.glb"),
                vertex_count=500,
                face_count=1000,
                pbr_textures=PBRTextureMaps(),
                execution_mode="fallback_procedural",
                duration_seconds=0.01,
            )

        connector.register_fallback(fallback_handler)
        inp = TrellisInput(image_path=sample_concept_image)

        # Should invoke fallback smoothly instead of crashing
        out = connector.execute_with_resilience(inp)
        assert out.asset_id == "trellis_fb_fallback"
        assert out.execution_mode == "fallback_procedural"


# ==============================================================================
# 4. 3DANIMALS / SMAL CONNECTOR TESTS
# ==============================================================================

class TestAnimals3DConnector:
    """Validate Animals3D SMAL 35 landmarks, Rx(+90) transform, and Rigify mapping."""

    def test_coordinate_transformation_matrix_properties(self):
        # Authoritative Rx(+90) rotation: [[1, 0, 0], [0, 0, -1], [0, 1, 0]]
        R = np.array(RX_90_SMAL_TO_BLENDER)
        det = np.linalg.det(R)
        # Proper SO(3) rotation has det = +1.0 (not reflection)
        assert det == pytest.approx(1.0)
        # Must be orthogonal: R^T * R == I
        assert np.allclose(np.dot(R.T, R), np.eye(3))

    def test_coordinate_transformation_mapping(self):
        # Canonical point [1.0, 2.0, 3.0] -> Blender [1.0, -3.0, 2.0]
        transformed = transform_smal_to_blender([1.0, 2.0, 3.0])
        assert transformed == [1.0, -3.0, 2.0]

        # Origin stays at origin
        assert transform_smal_to_blender([0.0, 0.0, 0.0]) == [0.0, 0.0, 0.0]

        # Negative components
        assert transform_smal_to_blender([-0.5, -1.5, 2.5]) == [-0.5, -2.5, -1.5]

    def test_smal_35_joint_landmarks_extracted(self):
        connector = Animals3DConnector()
        inp = AnimalPoseInput(species="canine")
        out = connector.execute(inp)

        assert isinstance(out, Animals3DOutput)
        assert out.landmark_count == 35
        assert len(out.landmarks) == 35

        # Check essential joints exist and have valid Blender coordinates
        expected_core_joints = [
            "root", "spine1", "spine2", "spine3", "neck1", "neck2", "head", "jaw",
            "left_collar", "left_shoulder", "left_elbow", "left_wrist", "left_hand",
            "right_collar", "right_shoulder", "right_elbow", "right_wrist", "right_hand",
            "left_hip", "left_knee", "left_ankle", "left_foot",
            "right_hip", "right_knee", "right_ankle", "right_foot",
            "tail1", "tail2", "tail3", "tail4", "tail5", "tail6"
        ]
        for jname in expected_core_joints:
            assert jname in out.landmarks
            lm = out.landmarks[jname]
            assert len(lm.coordinates) == 3
            assert lm.confidence > 0.9
            assert len(lm.rigify_bone_targets) > 0

    def test_smal_to_rigify_wolf_mapping_integrity(self):
        # Every mapped Rigify target must adhere to standard 'DEF-*' deformation bone naming
        for smal_joint, targets in SMAL_TO_RIGIFY_WOLF.items():
            assert len(targets) >= 1
            for target in targets:
                assert target.startswith("DEF-"), f"Target {target} for joint {smal_joint} must start with DEF-"

        # Check key kinematic chains
        assert "DEF-spine.004" in SMAL_TO_RIGIFY_WOLF["root"]
        assert "DEF-spine.011" in SMAL_TO_RIGIFY_WOLF["head"]
        assert any("front_thigh" in t for t in SMAL_TO_RIGIFY_WOLF["left_shoulder"])
        assert any("thigh" in t for t in SMAL_TO_RIGIFY_WOLF["left_hip"])
        assert any("spine" in t for t in SMAL_TO_RIGIFY_WOLF["tail1"])

    def test_vertex_blend_weights_computation(self):
        connector = Animals3DConnector()
        vertices = [(0.0, 0.0, 0.5), (0.0, 0.1, 0.6), (0.5, 0.5, 0.5)]
        heads = {"DEF-spine.005": (0.0, 0.0, 0.4)}
        tails = {"DEF-spine.005": (0.0, 0.0, 0.8)}

        weights = connector.compute_longitudinal_skin_weights(vertices, heads, tails)
        assert "DEF-spine.005" in weights
        bone_w = weights["DEF-spine.005"]
        # Vertices close to segment should have weights > 0
        assert len(bone_w) > 0
        for w in bone_w.values():
            assert 0.0 <= w <= 1.0

    def test_rigify_script_generation(self):
        connector = Animals3DConnector()
        out = connector.execute(AnimalPoseInput(species="wolf"))
        script = out.blender_script
        assert "import bpy" in script
        assert "from mathutils import Vector" in script
        assert "align_roll" in script
        assert "metarig" in script
        assert "DEF-spine.004" in script


# ==============================================================================
# 5. ANYCREATURE PROCEDURAL ENGINE CONNECTOR TESTS
# ==============================================================================

class TestAnyCreatureConnector:
    """Validate NLP prompt parsing into BodyGraph DAG and procedural mesh export."""

    def test_prompt_parsing_winged_dragon(self):
        connector = AnyCreatureConnector()
        prompt = "Mythical fire-breathing winged dragon with twin shoulder horns"
        spec = connector.parse_prompt(prompt)

        assert spec.inferred_type == "winged_quadruped"
        assert spec.body_graph.archetype == "winged_quadruped"

        # Check wings and legs
        wing_limbs = [limb for limb in spec.body_graph.limbs if limb.limb_type == "wing"]
        leg_limbs = [limb for limb in spec.body_graph.limbs if limb.limb_type == "leg"]
        assert len(wing_limbs) == 2
        assert len(leg_limbs) == 4

        # Check horns in parts
        assert "left_horn" in spec.body_graph.parts
        assert "right_horn" in spec.body_graph.parts

        # Check animation clips include fly cycle
        actions = [b.action_name for b in spec.animation_bindings]
        assert "idle" in actions
        assert "walk_cycle" in actions
        assert "fly_cycle" in actions

    def test_prompt_parsing_dire_wolf_quadruped(self):
        connector = AnyCreatureConnector()
        spec = connector.parse_prompt("Armored dire wolf predator")
        assert spec.inferred_type == "quadruped"
        leg_limbs = [limb for limb in spec.body_graph.limbs if limb.limb_type == "leg"]
        assert len(leg_limbs) == 4
        # Tail must exist for quadruped
        assert "tail" in spec.body_graph.parts

    def test_prompt_parsing_biped(self):
        connector = AnyCreatureConnector()
        spec = connector.parse_prompt("Fierce bipedal humanoid orc berserker")
        assert spec.inferred_type == "biped"
        arm_limbs = [limb for limb in spec.body_graph.limbs if limb.limb_type == "arm"]
        leg_limbs = [limb for limb in spec.body_graph.limbs if limb.limb_type == "leg"]
        assert len(arm_limbs) == 2
        assert len(leg_limbs) == 2

    def test_body_graph_structure_and_json_export(self, tmp_path):
        connector = AnyCreatureConnector()
        out_dir = str(tmp_path / "creature_dag")
        prompt = "Mythical chimera beast"
        output = connector.execute(prompt, output_dir=out_dir)

        assert isinstance(output, AnyCreatureOutput)
        assert os.path.exists(output.json_spec_path)
        assert os.path.exists(output.generated_mesh_path)

        # Inspect exported JSON
        with open(output.json_spec_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert data["raw_prompt"] == prompt
            assert "body_graph" in data
            assert data["body_graph"]["root_id"] == "pelvis"
            assert "parts" in data["body_graph"]
            assert "limbs" in data["body_graph"]

    def test_animation_gait_phase_offsets(self):
        connector = AnyCreatureConnector()
        spec = connector.parse_prompt("Quadruped wolf")
        walk_binding = next(b for b in spec.animation_bindings if b.action_name == "walk_cycle")

        # Diagonal trot gait check: front_left (0.0) -> rear_right (0.25) -> front_right (0.5) -> rear_left (0.75)
        offsets = walk_binding.phase_offsets
        assert offsets["front_left"] == 0.0
        assert offsets["rear_right"] == 0.25
        assert offsets["front_right"] == 0.5
        assert offsets["rear_left"] == 0.75


# ==============================================================================
# 6. MESHANYTHING V2 RETOPOLOGY CONNECTOR TESTS
# ==============================================================================

class TestMeshAnythingConnector:
    """Validate MeshAnything retopology, <1600 polygon budget, and QuadriFlow fallback."""

    def test_target_face_count_budget_strictly_under_1600(self, sample_dense_mesh, tmp_path):
        connector = MeshAnythingConnector()
        inp = MeshAnythingInput(
            input_mesh_path=sample_dense_mesh,
            config=RetopologyConfig(target_face_count=1200, enforce_pure_quad=True),
            output_dir=str(tmp_path / "retopo_test"),
        )
        out = connector.execute(inp)

        assert isinstance(out, MeshAnythingOutput)
        assert os.path.exists(out.optimized_mesh_path)
        # Strict enforcement: output face count must be < 1600 for game engine readiness
        assert out.optimized_face_count <= 1600
        assert out.quad_ratio >= 0.90
        assert out.reduction_ratio < 0.1
        assert out.solver_used == "meshanything_v2"

    def test_budget_clamping_for_large_requested_counts(self, sample_dense_mesh, tmp_path):
        connector = MeshAnythingConnector()
        # Even if user requests 5000, game-ready budget must stay strictly under 1600
        inp = MeshAnythingInput(
            input_mesh_path=sample_dense_mesh,
            config=RetopologyConfig(target_face_count=5000),
            output_dir=str(tmp_path / "retopo_clamp"),
        )
        out = connector.execute(inp)
        assert out.optimized_face_count <= 1600

    def test_missing_input_mesh_raises_error(self, tmp_path):
        connector = MeshAnythingConnector()
        inp = MeshAnythingInput(
            input_mesh_path=str(tmp_path / "missing_mesh.glb"),
        )
        with pytest.raises(MorphoMeshException) as exc_info:
            connector.execute(inp)
        assert exc_info.value.code == ERR_INPUT_MESH_NOT_FOUND

    def test_remote_failure_triggers_quadriflow_fallback(self, sample_dense_mesh, tmp_path):
        connector = MeshAnythingConnector()
        # Provide failing remote endpoint
        inp = MeshAnythingInput(
            input_mesh_path=sample_dense_mesh,
            config=RetopologyConfig(
                remote_endpoint="http://invalid-endpoint-meshanything:9999",
                target_face_count=1400,
            ),
            output_dir=str(tmp_path / "fallback_retopo"),
        )
        # Should gracefully fall back to local quadriflow synthesizer
        out = connector.execute(inp)
        assert "fallback" in out.solver_used
        assert out.optimized_face_count <= 1600
        assert os.path.exists(out.optimized_mesh_path)

    def test_remote_service_response_parsing(self, sample_dense_mesh, tmp_path):
        connector = MeshAnythingConnector()
        mock_resp_data = {
            "original_face_count": 50000,
            "original_vertex_count": 25000,
            "optimized_face_count": 1450,
            "optimized_vertex_count": 750,
            "quad_ratio": 0.96,
            "reduction_ratio": 0.029,
        }
        mock_resp = io.BytesIO(json.dumps(mock_resp_data).encode("utf-8"))

        with patch("urllib.request.urlopen", return_value=mock_resp):
            inp = MeshAnythingInput(
                input_mesh_path=sample_dense_mesh,
                config=RetopologyConfig(
                    remote_endpoint="http://mock-retopo-server:8003",
                    target_face_count=1450,
                ),
                output_dir=str(tmp_path / "remote_retopo"),
            )
            out = connector.execute(inp)
            assert out.solver_used == "meshanything_v2_remote"
            assert out.optimized_face_count == 1450
            assert out.quad_ratio == 0.96


# ==============================================================================
# 7. TENCENT HUNYUAN3D-2.1 CONNECTOR TESTS
# ==============================================================================

class TestHunyuanConnector:
    """Validate HunyuanConnector 2-stage DiT/Paint-PBR and network boundary isolation."""

    def test_hunyuan_mock_execution(self, sample_concept_image, tmp_path):
        connector = HunyuanConnector(config={"mode": "mock", "texture_resolution": 1024})
        inp = HunyuanInput(
            image_path=sample_concept_image,
            generate_pbr=True,
            output_format="glb",
        )
        out = connector.execute(inp, output_dir=str(tmp_path / "hunyuan_out"))

        assert isinstance(out, HunyuanOutput)
        assert os.path.exists(out.mesh_path)
        assert out.vertex_count > 0
        assert out.face_count > 0

        # Check all 4 PBR textures in dictionary
        assert "albedo" in out.pbr_textures and os.path.exists(out.pbr_textures["albedo"])
        assert "normal" in out.pbr_textures and os.path.exists(out.pbr_textures["normal"])
        assert "roughness" in out.pbr_textures and os.path.exists(out.pbr_textures["roughness"])
        assert "metallic" in out.pbr_textures and os.path.exists(out.pbr_textures["metallic"])

    def test_hunyuan_missing_image_error(self, tmp_path):
        connector = HunyuanConnector()
        inp = HunyuanInput(image_path=str(tmp_path / "absent_img.png"))
        with pytest.raises(MorphoMeshException) as exc_info:
            connector.execute(inp)
        assert exc_info.value.code == ERR_IMAGE_NOT_FOUND

    def test_hunyuan_remote_boundary_isolation_mock(self, sample_concept_image, tmp_path):
        connector = HunyuanConnector(
            config={"mode": "remote", "endpoint_url": "http://mock-hunyuan:8001/v1"}
        )
        mock_resp_data = {
            "vertex_count": 6200,
            "face_count": 12400,
            "pbr_textures": {"albedo": "mock_albedo.png"},
            "status": "completed",
        }
        mock_resp = io.BytesIO(json.dumps(mock_resp_data).encode("utf-8"))

        with patch("urllib.request.urlopen", return_value=mock_resp):
            inp = HunyuanInput(image_path=sample_concept_image)
            out = connector.execute(inp, output_dir=str(tmp_path / "hunyuan_rem"))
            assert out.backend_service == "hunyuan3d-2.1_remote"
            assert out.vertex_count == 6200
            assert out.face_count == 12400


# ==============================================================================
# 8. INFERENCE ADAPTER & SERVER INTEGRATION TESTS
# ==============================================================================

class TestInferenceAdapterIntegration:
    """Validate InferenceAdapter connector dispatching, retopology, and rig helpers."""

    def test_generate_3d_asset_routes_trellis(self, sample_concept_image):
        adapter = get_inference_adapter("production")
        req = Create3DAssetInput(
            image_path=sample_concept_image,
            model_backend="trellis",
            generate_pbr=True,
            texture_resolution=512,
        )
        res = adapter.generate_3d_asset(req)

        assert isinstance(res, EnhancedCreate3DAssetOutput)
        assert res.backend_used == "trellis"
        assert res.has_pbr_materials is True
        assert "albedo" in res.pbr_textures
        assert "normal" in res.pbr_textures
        assert res.metadata.get("connector") == "trellis"

    def test_generate_3d_asset_routes_hunyuan(self, sample_concept_image):
        adapter = get_inference_adapter("production")
        req = Create3DAssetInput(
            image_path=sample_concept_image,
            model_backend="hunyuan",
            generate_pbr=True,
        )
        res = adapter.generate_3d_asset(req)

        assert isinstance(res, EnhancedCreate3DAssetOutput)
        assert res.backend_used == "hunyuan"
        assert res.has_pbr_materials is True
        assert "albedo" in res.pbr_textures
        assert res.metadata.get("connector") == "hunyuan"

    def test_generate_3d_asset_routes_anycreature(self):
        adapter = get_inference_adapter("production")
        req = Create3DAssetInput(
            concept_id="concept-winged-pegasus",
            model_backend="anycreature",
            generate_pbr=True,
        )
        res = adapter.generate_3d_asset(req)

        assert isinstance(res, EnhancedCreate3DAssetOutput)
        assert res.backend_used == "anycreature"
        assert res.metadata.get("connector") == "anycreature"
        assert res.metadata.get("total_parts", 0) > 0

    def test_optimize_topology_with_connector(self, sample_dense_mesh):
        adapter = get_inference_adapter("production")
        retopo = adapter.optimize_topology_with_connector(
            mesh_path=sample_dense_mesh,
            method="meshanything_v2",
            target_faces=1300,
        )
        assert retopo["optimized_face_count"] <= 1600
        assert retopo["quad_ratio"] >= 0.90
        assert os.path.exists(retopo["optimized_mesh_path"])

    def test_create_animal_rig_with_connector(self, sample_dense_mesh):
        adapter = get_inference_adapter("production")
        rig_data = adapter.create_animal_rig_with_connector(
            mesh_path=sample_dense_mesh,
            creature_type="quadruped",
            species="canine",
        )
        assert rig_data["landmark_count"] == 35
        assert len(rig_data["landmarks"]) == 35
        assert len(rig_data["rigify_mapping"]) >= 35
        assert rig_data["transformation_matrix"] == RX_90_SMAL_TO_BLENDER

    def test_connector_failure_falls_back_to_mock(self, sample_concept_image):
        adapter = get_inference_adapter("production")
        # Simulate connector failure
        with patch.object(TrellisConnector, "execute", side_effect=RuntimeError("GPU Out of Memory")):
            req = Create3DAssetInput(
                image_path=sample_concept_image,
                model_backend="trellis",
            )
            res = adapter.generate_3d_asset(req)
            # Must fall back gracefully to procedural generation without raising
            assert isinstance(res, EnhancedCreate3DAssetOutput)
            assert os.path.exists(res.mesh_path)
            assert res.vertex_count > 0

    def test_get_connector_status(self):
        adapter = get_inference_adapter("production")
        status = adapter.get_connector_status()
        assert "connectors" in status
        assert "health" in status
        assert "dependencies" in status
        assert len(status["connectors"]) == 5
        assert set(status["health"].keys()) == set(status["connectors"])
