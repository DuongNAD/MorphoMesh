"""
MorphoMesh: Milestone 5 Comprehensive End-to-End Final Pipeline Test Suite.

Target: tests/test_e2e_final_pipeline.py
Milestone: Milestone 5 - End-to-End Demonstrator & Integration Test Suite (R1–R4)

Empirically validates:
1. Multi-angle inspector camera rig setup across all 8 canonical viewpoints:
   ('front', 'three_quarter', 'side', 'back', 'top', 'bottom', 'close_up_head', 'close_up_hands'),
   validating optical framing distance math, subregion ordering, and look-at tracking.
2. Viewport image capture and PNG header validation:
   - Shading modes (SOLID, WIREFRAME, MATERIAL) and coloring schemes (RANDOM, SINGLE, MATERIAL)
   - Resolution scaling (512x512, 1024x1024, 1920x1080)
   - Valid PNG magic bytes (\\x89PNG\\r\\n\\x1a\\n) and Base64 round-trip integrity.
3. Closed-loop visual quality critique and Pydantic v2 serialization:
   - Presets ('stylized_heroine', 'realistic_human', 'chibi_petite')
   - Pydantic v2 model_dump_json() and model_validate_json() round-trip bit-for-bit fidelity
   - Procedural defect injection fixtures (penetration, proportion, skinning, grooming)
   - Canonical benchmark_defect_detection() >= 95% accuracy and <= 5% false positive rate.
4. Offline bridge resilience and fallback artifact generation:
   - Graceful fallback when socket disconnected and Blender binary missing
   - Valid fallback PNG and camera metadata generation without uncaught exceptions.
5. Parameter boundary and enum error enforcement:
   - Viewpoint, focal length, shading mode, color type, resolution, preset, and tolerance bounds.
6. Full end-to-end pipeline execution and artifact inspection.
"""

from __future__ import annotations

import base64
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from morphomesh.blender_bridge import BlenderBridge
from morphomesh.camera_rig import (
    CANONICAL_VIEWPOINTS,
    FALLBACK_PNG_BYTES,
    calculate_character_bounds,
    calculate_optical_framing_distance,
    capture_viewport_image,
    encode_image_to_base64,
    get_anatomical_subregion_center,
    setup_inspector_camera,
)
from morphomesh.models import (
    DefectCategory,
    DefectItem,
    DefectSeverity,
    VisualCritiqueInput,
    VisualCritiqueOutput,
)
from morphomesh.server import (
    blender_bridge,
    morphomesh_capture_viewport,
    morphomesh_critique_visual_quality,
    morphomesh_setup_inspector_camera_rig,
)
from morphomesh.visual_critic import (
    benchmark_defect_detection,
    create_grooming_fixture,
    create_penetration_fixture,
    create_proportion_fixture,
    create_skinning_fixture,
    evaluate_body_proportions,
    evaluate_hair_grooming_intersections,
    evaluate_mesh_penetration,
    evaluate_rig_skinning_deformation,
    run_visual_critique,
)
from scripts.run_e2e_inspection_pipeline import (
    ARTIFACTS_DIR,
    PNG_HEADER,
    run_e2e_pipeline,
    validate_png_file,
)


@pytest.fixture(autouse=True)
def enable_inspection_tools(monkeypatch: pytest.MonkeyPatch):
    """Ensure inspection tools are active across test invocations."""
    monkeypatch.setenv("MORPHOMESH_INCLUDE_INSPECTION_TOOLS", "1")


# ==============================================================================
# 1. MULTI-ANGLE CAMERA RIG SETUP TESTS
# ==============================================================================

class TestMultiAngleCameraRigE2E:
    """Validates multi-angle camera rig setup across all canonical viewpoints and optical math."""

    CANONICAL_VPS = [
        "front",
        "three_quarter",
        "side",
        "back",
        "top",
        "bottom",
        "close_up_head",
        "close_up_hands",
    ]

    @pytest.mark.parametrize("viewpoint", CANONICAL_VPS)
    def test_all_canonical_viewpoints_setup(self, viewpoint: str):
        """Verify each canonical viewpoint computes valid finite 3D coordinates and metadata."""
        meta = setup_inspector_camera(
            viewpoint=viewpoint,
            camera_name="MorphoMesh_Inspector_Camera",
            resolution=(1024, 1024),
        )

        assert meta["status"] == "success"
        assert meta["viewpoint"] == viewpoint
        assert meta["camera_name"] == "MorphoMesh_Inspector_Camera"

        loc = meta["camera_location"]
        rot = meta["camera_rotation"]
        target = meta["target_center"]

        assert len(loc) == 3 and all(math.isfinite(x) for x in loc)
        assert len(rot) == 3 and all(math.isfinite(r) for r in rot)
        assert len(target) == 3 and all(math.isfinite(t) for t in target)

        dist = meta["framing_distance"]
        radius = meta["bounding_radius"]
        focal = meta["focal_length"]

        assert dist > 0.0 and math.isfinite(dist)
        assert radius > 0.0 and math.isfinite(radius)
        assert focal > 0.0 and math.isfinite(focal)

    @pytest.mark.parametrize("focal", [24.0, 35.0, 50.0, 85.0, 105.0, 135.0])
    def test_optical_framing_distance_formula(self, focal: float):
        """Verify optical distance follows d = (R / sin(alpha_min)) * (1 + margin) monotonically."""
        radius = 1.0
        margin = 0.15
        d = calculate_optical_framing_distance(
            radius=radius,
            focal_length=focal,
            sensor_width=36.0,
            resolution=(1024, 1024),
            margin=margin,
        )

        # Theoretical check
        half_fov = math.atan(36.0 / (2.0 * focal))
        expected_d = (radius / math.sin(half_fov)) * (1.0 + margin)
        assert math.isclose(d, expected_d, rel_tol=1e-4)

    def test_optical_framing_distance_monotonic_growth(self):
        """Larger focal length must strictly increase camera distance to maintain subject scale."""
        focals = [24.0, 35.0, 50.0, 85.0, 135.0, 200.0]
        distances = [
            calculate_optical_framing_distance(1.0, focal_length=f, resolution=(1024, 1024))
            for f in focals
        ]
        for i in range(len(distances) - 1):
            assert distances[i] < distances[i + 1], f"Expected distance growth at focal {focals[i]} -> {focals[i+1]}"

    def test_anatomical_subregion_centers_ordering(self):
        """Verify cranial head center Z > torso center Z > feet center Z, and hands have lateral X."""
        g_center = [0.0, 0.0, 1.0]
        g_radius = 1.0
        min_corner = [-0.5, -0.5, 0.0]
        max_corner = [0.5, 0.5, 2.0]

        c_head, r_head, f_head = get_anatomical_subregion_center("head", g_center, g_radius, min_corner, max_corner)
        c_torso, r_torso, f_torso = get_anatomical_subregion_center("torso", g_center, g_radius, min_corner, max_corner)
        c_feet, r_feet, f_feet = get_anatomical_subregion_center("feet", g_center, g_radius, min_corner, max_corner)
        c_hands, r_hands, f_hands = get_anatomical_subregion_center("hands", g_center, g_radius, min_corner, max_corner)

        # Height ordering
        assert c_head[2] > c_torso[2] > c_feet[2], "Subregion Z coordinates must satisfy Head > Torso > Feet"
        # Hand lateral offset
        assert c_hands[0] > c_torso[0], "Hands framing must have lateral X offset"
        # Portrait focal length standard
        assert f_head >= 85.0, "Portrait / Head framing should default to >= 85mm"


# ==============================================================================
# 2. VIEWPORT IMAGE CAPTURE TESTS
# ==============================================================================

class TestViewportImageCaptureE2E:
    """Validates viewport capture, PNG magic header, shading modes, and base64 encoding."""

    @pytest.mark.parametrize("shading,color", [
        ("SOLID", "RANDOM"),
        ("SOLID", "MATERIAL"),
        ("WIREFRAME", "SINGLE"),
        ("MATERIAL", "MATERIAL"),
    ])
    def test_viewport_capture_png_header_and_shading_modes(self, tmp_path: Path, shading: str, color: str):
        """Verify captured viewport image creates valid PNG file with magic header b'\\x89PNG\\r\\n\\x1a\\n'."""
        out_png = str(tmp_path / f"test_{shading}_{color}.png")
        res_path = capture_viewport_image(
            output_path=out_png,
            shading_mode=shading,
            color_type=color,
            resolution=(1024, 1024),
        )

        assert os.path.isfile(res_path)
        valid, fsize, msg = validate_png_file(res_path)
        assert valid, f"Invalid PNG file: {msg}"
        assert fsize > 0

        # Check raw magic bytes directly
        with open(res_path, "rb") as f:
            header = f.read(8)
        assert header == PNG_HEADER, f"File header mismatch: {header!r} != {PNG_HEADER!r}"

    @pytest.mark.parametrize("res_wh", [(512, 512), (1024, 1024), (1920, 1080)])
    def test_viewport_capture_resolutions(self, tmp_path: Path, res_wh: tuple[int, int]):
        """Verify capture works across standard preview and HD resolutions."""
        out_png = str(tmp_path / f"test_res_{res_wh[0]}x{res_wh[1]}.png")
        res_path = capture_viewport_image(
            output_path=out_png,
            resolution=res_wh,
        )
        assert os.path.isfile(res_path)
        valid, fsize, _ = validate_png_file(res_path)
        assert valid and fsize > 0

    def test_base64_preview_roundtrip_integrity(self, tmp_path: Path):
        """Verify encode_image_to_base64 produces valid base64 decodable to identical PNG header."""
        out_png = str(tmp_path / "test_b64.png")
        capture_viewport_image(output_path=out_png)

        b64_str = encode_image_to_base64(out_png)
        assert b64_str is not None and len(b64_str) > 0

        raw_bytes = base64.b64decode(b64_str.encode("utf-8"))
        assert raw_bytes.startswith(PNG_HEADER)


# ==============================================================================
# 3. CLOSED-LOOP VISUAL QUALITY CRITIQUE & PYDANTIC V2 TESTS
# ==============================================================================

class TestVisualCritiqueEvaluationAndPydanticE2E:
    """Validates visual quality critique across presets, Pydantic v2 serialization, and defect detection."""

    @pytest.mark.parametrize("preset", ["stylized_heroine", "realistic_human", "chibi_petite"])
    def test_critique_evaluation_across_all_presets(self, preset: str):
        """Verify run_visual_critique executes cleanly across all standard anthropometric presets."""
        inp = VisualCritiqueInput(
            character_name="Yu_Nian_An",
            target_object="Human_Base_Mesh",
            camera_angles=["front", "three_quarter", "side", "back"],
            clearance_tolerance=0.0005,
            target_preset=preset,
        )

        out = run_visual_critique(inp)
        assert isinstance(out, VisualCritiqueOutput)
        assert out.status == "success"
        assert isinstance(out.passed, bool)
        assert 0.0 <= out.quality_score <= 100.0
        assert out.defect_count == len(out.defects)
        assert len(out.recommendations) > 0
        assert out.execution_time_seconds >= 0.0

    def test_pydantic_v2_json_roundtrip_serialization(self, tmp_path: Path):
        """Verify VisualCritiqueOutput preserves 100% field fidelity across JSON dump and load."""
        inp = VisualCritiqueInput(
            character_name="Yu_Nian_An",
            target_preset="stylized_heroine",
        )
        original_output = run_visual_critique(inp)

        # Dump to JSON
        json_path = tmp_path / "critique_test.json"
        json_content = original_output.model_dump_json(indent=2)
        json_path.write_text(json_content, encoding="utf-8")

        # Load back via model_validate_json
        reloaded = VisualCritiqueOutput.model_validate_json(json_content)

        assert reloaded.status == original_output.status
        assert reloaded.passed == original_output.passed
        assert reloaded.quality_score == original_output.quality_score
        assert reloaded.defect_count == original_output.defect_count
        assert reloaded.recommendations == original_output.recommendations
        assert reloaded.evaluated_angles == original_output.evaluated_angles
        assert reloaded.scene_stats == original_output.scene_stats

    def test_critique_intentional_defect_detection_fixtures(self):
        """Verify that procedural fixtures with injected defects are accurately classified."""
        # 1. Penetration Fixture (defective)
        b_pen, g_pen = create_penetration_fixture(defective=True)
        defects_pen = evaluate_mesh_penetration("Body", ["Dress"], clearance_tolerance=0.0005, body_geo=b_pen, garment_geos={"Dress": g_pen})
        assert len(defects_pen) > 0, "Failed to detect injected garment penetration"
        assert any(d.category == DefectCategory.PENETRATION for d in defects_pen)

        # 2. Proportion Fixture (giant)
        v_giant, f_giant, lm_giant = create_proportion_fixture("giant")
        _, defs_prop = evaluate_body_proportions("Body", target_preset="stylized_heroine", landmarks=lm_giant, body_geo=(v_giant, f_giant))
        assert any(d.category == DefectCategory.PROPORTION for d in defs_prop), "Failed to detect proportion anomaly"

        # 3. Skinning Fixture (pinched)
        r_v, p_v, f_s, j_specs = create_skinning_fixture(defective=True)
        _, defs_skin = evaluate_rig_skinning_deformation(r_v, p_v, f_s, j_specs, "Arm")
        assert any(d.category == DefectCategory.SKINNING_PINCH for d in defs_skin), "Failed to detect skinning pinch"

        # 4. Grooming Fixture (colliding)
        b_groom, h_groom = create_grooming_fixture(defective=True)
        defs_groom = evaluate_hair_grooming_intersections(["Hair_Curves"], "Scalp", hair_splines=h_groom, body_geo=b_groom)
        assert any(d.category == DefectCategory.GROOMING_COLLISION for d in defs_groom), "Failed to detect grooming collision"

    def test_canonical_benchmark_defect_detection_accuracy(self):
        """Verify canonical benchmark demonstrates >= 95.0% accuracy and <= 5.0% false positive rate."""
        metrics = benchmark_defect_detection()
        acc = metrics.get("accuracy_percentage", metrics.get("accuracy", 0.0))
        fpr = metrics.get("false_positive_rate", 0.0)
        tp = metrics.get("true_positives", 0)
        tn = metrics.get("true_negatives", 0)
        fp = metrics.get("false_positives", 0)
        fn = metrics.get("false_negatives", 0)

        assert acc >= 95.0, f"Benchmark accuracy {acc}% < 95%"
        assert fpr <= 5.0, f"Benchmark FPR {fpr}% > 5%"
        assert fp == 0, f"Expected 0 false positives, got {fp}"
        assert fn == 0, f"Expected 0 false negatives, got {fn}"
        assert tp + tn == 9, f"Expected 9 clean/defective state evaluations, got {tp + tn}"


# ==============================================================================
# 4. OFFLINE BRIDGE RESILIENCE TESTS
# ==============================================================================

class TestOfflineBridgeResilienceE2E:
    """Validates graceful offline fallback behavior when Blender is unavailable."""

    @pytest.mark.asyncio
    async def test_offline_viewport_capture_fallback(self, tmp_path: Path):
        """When socket and CLI are offline, morphomesh_capture_viewport returns valid fallback PNG."""
        out_png = str(tmp_path / "offline_fallback.png")
        with patch.object(blender_bridge, "is_interactive_connected", return_value=False), \
             patch.object(blender_bridge, "blender_bin_path", None):
            res = await morphomesh_capture_viewport(
                output_path=out_png,
                camera_name="MorphoMesh_Inspector_Camera",
                resolution=[1024, 1024],
                shading_mode="SOLID",
                color_type="RANDOM",
            )

        assert res["status"] == "success"
        assert res.get("offline_fallback") is True
        assert os.path.isfile(out_png)

        valid, fsize, msg = validate_png_file(out_png)
        assert valid, f"Fallback PNG invalid: {msg}"
        assert res.get("base64_preview") is not None
        decoded = base64.b64decode(res["base64_preview"])
        assert decoded.startswith(PNG_HEADER)

    @pytest.mark.asyncio
    async def test_offline_camera_rig_setup_fallback(self):
        """When socket and CLI are offline, morphomesh_setup_inspector_camera_rig returns valid metadata."""
        with patch.object(blender_bridge, "is_interactive_connected", return_value=False), \
             patch.object(blender_bridge, "blender_bin_path", None):
            res = await morphomesh_setup_inspector_camera_rig(
                viewpoint="three_quarter",
                camera_name="MorphoMesh_Inspector_Camera",
                focal_length=50.0,
            )

        assert res["status"] == "success"
        assert res.get("offline_fallback") is True
        pos = res.get("camera_location") or res.get("location")
        rot = res.get("camera_rotation") or res.get("rotation_euler")
        assert len(pos) == 3 and all(math.isfinite(x) for x in pos)
        assert len(rot) == 3 and all(math.isfinite(r) for r in rot)

    def test_offline_bridge_client_methods_direct(self, tmp_path: Path):
        """BlenderBridge methods directly handle offline state without unhandled exception."""
        test_bridge = BlenderBridge(host="127.0.0.1", port=9999)
        out_png = str(tmp_path / "bridge_direct_offline.png")

        with patch.object(test_bridge, "is_interactive_connected", return_value=False), \
             patch.object(test_bridge, "blender_bin_path", None):
            # 1. Camera setup
            cam_res = test_bridge.setup_inspector_camera(viewpoint="front")
            assert cam_res["status"] == "success"
            assert cam_res.get("offline_fallback") is True

            # 2. Viewport capture
            cap_res = test_bridge.capture_viewport(output_path=out_png)
            assert cap_res["status"] == "success"
            assert os.path.isfile(out_png)


# ==============================================================================
# 5. PARAMETER BOUNDARY AND ENUM ERROR RAISING TESTS
# ==============================================================================

class TestParameterBoundaryAndEnumValidationE2E:
    """Validates that invalid parameter boundaries and enum values raise FastMCP ToolError cleanly."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_vp", [
        "nadir_flipped",
        "diagonal_underneath",
        "zenith_hyper",
        "",
        "   ",
        "UPPER_INVALID_VIEWPOINT",
    ])
    async def test_invalid_viewpoints_raise_tool_error(self, invalid_vp: str):
        """Invalid viewpoints must raise ToolError."""
        with pytest.raises(ToolError, match=r"(?i)(viewpoint|validation|invalid|preset)"):
            await morphomesh_setup_inspector_camera_rig(viewpoint=invalid_vp)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_focal", [0.0, -15.0, 5.0, 350.0, 1000.0])
    async def test_focal_length_boundary_validation(self, invalid_focal: float):
        """Focal lengths outside [10.0, 300.0] must raise ToolError."""
        with pytest.raises(ToolError, match=r"(?i)(focal_length|validation|between 10.0 and 300.0)"):
            await morphomesh_setup_inspector_camera_rig(focal_length=invalid_focal)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_shading", ["RAYTRACED", "PATH_TRACING", "CYCLES_PATHTRACE", ""])
    async def test_shading_mode_enum_validation(self, invalid_shading: str):
        """Invalid shading modes must raise ToolError."""
        with pytest.raises(ToolError, match=r"(?i)(shading_mode|validation|allowed shading modes)"):
            await morphomesh_capture_viewport(shading_mode=invalid_shading)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_color", ["RAINBOW", "NEON", "SPECTRAL", ""])
    async def test_color_type_enum_validation(self, invalid_color: str):
        """Invalid color types must raise ToolError."""
        with pytest.raises(ToolError, match=r"(?i)(color_type|validation|allowed color types)"):
            await morphomesh_capture_viewport(color_type=invalid_color)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_res", [[0, 0], [-1024, 1024], [1024], [1024, -512]])
    async def test_resolution_boundary_validation(self, invalid_res: list[int]):
        """Zero or negative resolutions must raise ToolError."""
        with pytest.raises(ToolError, match=r"(?i)(resolution|positive integers)"):
            await morphomesh_capture_viewport(resolution=invalid_res)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_preset", ["alien_hydra", "draconic_quadruped", "cyborg_mech", ""])
    async def test_target_preset_enum_validation(self, invalid_preset: str):
        """Invalid target presets must raise ToolError."""
        with pytest.raises(ToolError, match=r"(?i)(target_preset|validation|allowed target presets)"):
            await morphomesh_critique_visual_quality(target_preset=invalid_preset)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_tolerance", [-0.001, -1.0, -0.00001])
    async def test_clearance_tolerance_boundary_validation(self, invalid_tolerance: float):
        """Negative clearance tolerance must raise ToolError."""
        with pytest.raises(ToolError, match=r"(?i)(clearance_tolerance|non-negative)"):
            await morphomesh_critique_visual_quality(clearance_tolerance=invalid_tolerance)


# ==============================================================================
# 6. END-TO-END PIPELINE SCRIPT EXECUTION INTEGRATION TESTS
# ==============================================================================

class TestEndToEndPipelineExecutionIntegration:
    """Validates programmatic execution of the pipeline script and artifacts integrity."""

    def test_pipeline_script_function_call_e2e(self):
        """Verify run_e2e_pipeline() returns exit code 0."""
        exit_code = run_e2e_pipeline()
        assert exit_code == 0

    def test_generated_preview_artifacts_integrity(self):
        """Verify all generated PNG and JSON artifacts exist in artifacts/inspector_previews/."""
        expected_pngs = [
            "preview_front_solid_random.png",
            "preview_three_quarter_solid_random.png",
            "preview_side_wireframe.png",
            "preview_back_solid_random.png",
            "preview_top_solid_random.png",
            "preview_bottom_solid_random.png",
            "preview_closeup_head_material.png",
            "preview_closeup_hands_wireframe.png",
        ]
        for fname in expected_pngs:
            p = ARTIFACTS_DIR / fname
            assert p.is_file(), f"Missing expected preview PNG: {p}"
            valid, size, msg = validate_png_file(p)
            assert valid, f"Corrupt PNG {fname}: {msg}"
            assert size > 0

        expected_jsons = [
            "critique_stylized_heroine.json",
            "critique_realistic_human.json",
            "critique_chibi_petite.json",
            "benchmark_metrics.json",
        ]
        for jname in expected_jsons:
            jp = ARTIFACTS_DIR / jname
            assert jp.is_file(), f"Missing expected critique JSON: {jp}"
            raw = jp.read_text(encoding="utf-8")
            data = json.loads(raw)
            assert isinstance(data, dict)
            if jname != "benchmark_metrics.json":
                revalidated = VisualCritiqueOutput.model_validate(data)
                assert revalidated.status == "success"
