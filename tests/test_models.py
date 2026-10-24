"""
Comprehensive Unit Tests for MorphoMesh Models Subsystem and Facade Parity.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

import morphomesh.models as models_pkg
import morphomesh.models.animation as anim_mod
import morphomesh.models.base as base_mod
import morphomesh.models.creature as creature_mod
import morphomesh.models.critique as critique_mod
import morphomesh.models.enums as enums_mod
import morphomesh.models.errors as errors_mod
import morphomesh.models.human as human_mod
import morphomesh.models.inspection as insp_mod


def test_models_subpackage_exports_count():
    """Verify all 101 authoritative symbols are registered in __all__."""
    assert len(models_pkg.__all__) == 101
    for symbol in models_pkg.__all__:
        assert hasattr(models_pkg, symbol), f"Missing symbol {symbol} in morphomesh.models"


def test_errors_submodule():
    """Verify error constants and MorphoMeshException integrity."""
    assert errors_mod.ERR_PARSE_ERROR == -32700
    assert errors_mod.ERR_INVALID_REQUEST == -32600
    assert errors_mod.ERR_BACKEND_UNAVAILABLE == -32002
    assert errors_mod.ERR_ANATOMY_DETECTION_FAILED == -32010

    exc = errors_mod.MorphoMeshException(
        code=errors_mod.ERR_BACKEND_UNAVAILABLE,
        message="Backend offline",
        details={"retry": False},
    )
    assert exc.code == -32002
    assert exc.message == "Backend offline"
    assert exc.details == {"retry": False}
    assert "[-32002]" in str(exc)


def test_enums_and_aliases():
    """Verify enums, DefectSeverity / DefectCategory normalizers, and aliases."""
    assert enums_mod.CreatureType.QUADRUPED.value == "quadruped"
    assert enums_mod.ViewMode.FRONT.value == "front"
    assert enums_mod.TargetPreset is enums_mod.AnthropometricPreset
    assert "front_three_quarter" in enums_mod.VALID_INSPECTOR_VIEWPOINTS_SET

    # DefectSeverity normalization via _missing_
    assert enums_mod.DefectSeverity("HIGH") == enums_mod.DefectSeverity.CRITICAL
    assert enums_mod.DefectSeverity("WARNING") == enums_mod.DefectSeverity.MAJOR
    assert enums_mod.DefectSeverity("NOTICE") == enums_mod.DefectSeverity.INFO

    # DefectCategory normalization via _missing_
    assert enums_mod.DefectCategory("CLIPPING") == enums_mod.DefectCategory.PENETRATION
    assert enums_mod.DefectCategory("RIG_PINCH") == enums_mod.DefectCategory.SKINNING_PINCH
    assert enums_mod.DefectCategory("HAIR_CLIPPING") == enums_mod.DefectCategory.GROOMING_COLLISION


def test_base_primitives():
    """Verify BoundingBox, SceneObjectInfo, and BoundingBox3D."""
    bbox = base_mod.BoundingBox(
        min_point=[0.0, 0.0, 0.0],
        max_point=[1.0, 2.0, 3.0],
        dimensions=[1.0, 2.0, 3.0],
    )
    assert bbox.dimensions == [1.0, 2.0, 3.0]

    obj_info = base_mod.SceneObjectInfo(name="TestCube", type="MESH", vertex_count=8, face_count=6)
    assert obj_info.name == "TestCube"
    assert obj_info.vertex_count == 8


def test_creature_schemas():
    """Verify Tools 1-7 request and response schemas and dimension step validator."""
    # Test rounding to nearest multiple of 64
    inp = creature_mod.GenerateConceptInput(prompt="An authentic bear creature", width=1000, height=1050)
    assert inp.width == 1024
    assert inp.height == 1024

    # Test backend alias validator on Create3DAssetInput
    asset_inp = creature_mod.Create3DAssetInput(backend="meshy")
    assert asset_inp.model_backend == "meshy"

    # Test engine normalization on RenderPreviewInput
    render_inp = creature_mod.RenderPreviewInput(render_engine="BLENDER_EEVEE_NEXT")
    assert render_inp.render_engine == "BLENDER_EEVEE"


def test_human_schemas_and_aliases():
    """Verify Tools 8-12 schemas, nested anatomy unpacking, and output aliases."""
    anatomy_cfg = human_mod.HumanAnatomyConfig(height=1.70, head_ratio=7.5)
    human_inp = human_mod.CreateHumanAssetInput(config=anatomy_cfg)
    assert human_inp.height == 1.70
    assert human_inp.head_ratio == 7.5

    # Test aliases
    assert human_mod.CreateHumanAssetOutput is human_mod.HumanAssetResult
    assert human_mod.AutoRigHumanOutput is human_mod.HumanRigResult
    assert human_mod.SetupHumanMaterialsOutput is human_mod.HumanMaterialResult
    assert human_mod.GroomHumanOutput is human_mod.HumanGroomingResult
    assert human_mod.DressHumanOutput is human_mod.HumanWardrobeResult


def test_inspection_schemas():
    """Verify inspector camera and viewport capture validation."""
    cam_inp = insp_mod.SetupInspectorCameraInput(viewpoint="Front")
    assert cam_inp.viewpoint == "front"

    with pytest.raises(ValidationError):
        insp_mod.SetupInspectorCameraInput(viewpoint="invalid_viewpoint_xyz")

    vp_inp = insp_mod.CaptureViewportInput(shading_mode="wireframe", color_type="random")
    assert vp_inp.shading_mode == "WIREFRAME"
    assert vp_inp.color_type == "RANDOM"


def test_critique_schemas():
    """Verify DefectItem, ActionableRecommendation, and VisualCritiqueOutput."""
    rec = critique_mod.ActionableRecommendation(action="SMOOTH_WEIGHTS", category="CLIPPING")
    assert rec.category == enums_mod.DefectCategory.PENETRATION
    assert rec.action == "SMOOTH_WEIGHTS"

    defect = critique_mod.DefectItem(
        id="DEF-001",
        category="CLIPPING",
        severity="HIGH",
        object_name="Dress_Mesh",
        description="Garment penetrates body",
    )
    assert defect.defect_id == "DEF-001"
    assert defect.category == enums_mod.DefectCategory.PENETRATION
    assert defect.severity == enums_mod.DefectSeverity.CRITICAL
    assert "Dress_Mesh" in defect.affected_objects

    out = critique_mod.VisualCritiqueOutput(defects=[defect])
    assert out.defect_count == 1
    assert out.passed is False


def test_animation_schemas():
    """Verify animation catalog schemas."""
    item = anim_mod.AnimationItem(
        action_id=101,
        name="Walk Cycle",
        key="walk_cycle_01",
        category="WalkAndRun",
    )
    assert item.action_id == 101
    assert item.name == "Walk Cycle"

    list_out = anim_mod.ListAnimationsOutput(total_count=1, animations=[item])
    assert list_out.total_count == 1
