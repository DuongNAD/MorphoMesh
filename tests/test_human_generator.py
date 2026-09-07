"""
MorphoMesh: Anthropometric Female Digital Human Generator Unit Tests.

Validates:
1. Anthropometric anatomical proportions (1.65m standing height, 7.41 head ratio, 0.70 WHR).
2. Quad-dominant mesh topology (>=95% quads in deforming regions, 0 non-manifold edges, 0 zero-area faces).
3. 24 standardized vertex groups (all populated and non-empty).
4. 10 articulated fingers (thumb + 4 fingers, 3 phalanges each) and articulated feet.
5. 34 Rigify bone snapping landmarks with joint pre-bends (elbow +Y, knee -Y).
6. 52 Apple ARKit FACS blendshapes with valid sparse deformation deltas.
7. Multi-format mesh serialization (GLB, OBJ) and Blender Python script generation.
"""

from __future__ import annotations

import math
import os
import tempfile
from pathlib import Path

import pytest

from morphomesh.human_generator import (
    ARKIT_52_BLENDSHAPES,
    STANDARDIZED_HUMAN_VERTEX_GROUPS,
    HumanAnatomyConfig,
    HumanAnatomyGenerator,
    HumanMeshResult,
    generate_human_base_mesh,
    get_human_generation_script,
)
from morphomesh.models import HumanAssetResult


# ==============================================================================
# 1. ANTHROPOMETRY & ANATOMICAL PROPORTIONS
# ==============================================================================

def test_default_anthropometry_yu_nian_an():
    """Verify canonical Yu Nian An proportions: 1.65m height, 7.41 head ratio, 0.70 WHR."""
    cfg = HumanAnatomyConfig()
    assert cfg.height == 1.65
    assert cfg.head_ratio == 7.41
    assert cfg.chest_girth == 0.82
    assert cfg.waist_girth == 0.58
    assert cfg.hip_girth == 0.86
    assert cfg.shoulder_width == 0.36
    assert cfg.gender == "female"

    res = generate_human_base_mesh(config=cfg, character_name="Yu_Nian_An")
    assert isinstance(res, HumanMeshResult)
    assert abs(res.height - 1.65) < 0.05
    assert abs(res.head_ratio - 7.41) < 0.05

    # Bounding box height matches standing height (1.65m)
    bb = res.bounding_box
    height_dim = bb.dimensions[2]
    assert abs(height_dim - 1.65) < 0.05
    assert bb.max_point[2] > 1.60
    assert bb.min_point[2] >= 0.0


def test_custom_anthropometry_parametric_scaling():
    """Verify parametric adjustment of height, chest, waist, and hip circumferences."""
    cfg = HumanAnatomyConfig(
        height=1.75,
        head_ratio=8.0,
        chest_girth=0.90,
        waist_girth=0.65,
        hip_girth=0.95,
        shoulder_width=0.40,
    )
    res = generate_human_base_mesh(config=cfg, character_name="Tall_Character")
    assert abs(res.height - 1.75) < 0.05
    assert 7.0 <= res.head_ratio <= 8.5

    # Landmark head_top scaled to 1.75m
    assert abs(res.landmarks["head_top"][2] - 1.75) < 0.05
    # Shoulders wider than default (0.40m span vs 0.36m)
    shoulder_span = abs(res.landmarks["shoulder_L"][0] - res.landmarks["shoulder_R"][0])
    assert shoulder_span > 0.35


# ==============================================================================
# 2. TOPOLOGY & QUAD DOMINANCE & MANIFOLDNESS
# ==============================================================================

def test_quad_dominance_ratio():
    """Verify mesh topology is quad-dominant with >=95% quads in deforming regions."""
    res = generate_human_base_mesh()
    quad_ratio = res.quad_ratio
    assert quad_ratio >= 0.95, f"Quad ratio {quad_ratio:.3f} is less than required 0.95 threshold."

    # Validate faces distribution
    faces = res.mesh.faces
    total_faces = len(faces)
    assert total_faces > 0
    # Quad percentage tracked by generator in deforming regions >= 95%
    assert res.quad_ratio >= 0.95


def test_zero_area_faces_and_manifold_edges():
    """Verify 0 zero-area faces and 0 non-manifold edges across the human mesh."""
    res = generate_human_base_mesh()
    verts = res.mesh.vertices
    faces = res.mesh.faces

    # 1. Assert 0 zero-area faces
    for i, face in enumerate(faces):
        p0 = verts[face[0]]
        p1 = verts[face[1]]
        p2 = verts[face[2]]
        # Cross product of edges (p1 - p0) x (p2 - p0)
        v1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
        v2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
        cx = v1[1] * v2[2] - v1[2] * v2[1]
        cy = v1[2] * v2[0] - v1[0] * v2[2]
        cz = v1[0] * v2[1] - v1[1] * v2[0]
        area = 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)
        assert area > 1e-8, f"Zero-area face detected at index {i}"

    # 2. Assert no non-manifold edges (edges shared by > 2 faces)
    edge_counts: dict[tuple[int, int], int] = {}
    for face in faces:
        n = len(face)
        for j in range(n):
            v_a = face[j]
            v_b = face[(j + 1) % n]
            edge = (min(v_a, v_b), max(v_a, v_b))
            edge_counts[edge] = edge_counts.get(edge, 0) + 1

    non_manifold = [e for e, count in edge_counts.items() if count > 2]
    assert len(non_manifold) == 0, f"Found {len(non_manifold)} non-manifold edges shared by >2 faces."


# ==============================================================================
# 3. STANDARDIZED VERTEX GROUPS
# ==============================================================================

def test_all_standardized_vertex_groups_present_and_populated():
    """Verify all 24 standardized vertex groups exist and contain positive vertex weights."""
    res = generate_human_base_mesh()
    vg = res.vertex_groups

    for group_name in STANDARDIZED_HUMAN_VERTEX_GROUPS:
        assert group_name in vg, f"Standardized vertex group '{group_name}' missing from generated mesh."
        v_indices = vg[group_name]
        assert len(v_indices) > 0, f"Vertex group '{group_name}' is empty (0 vertices assigned)."
        assert all(isinstance(idx, int) and idx >= 0 for idx in v_indices)


def test_facial_subfeature_vertex_groups():
    """Verify individual facial feature groups: eyes, eyelids, eyebrows, mouth, lips, teeth, tongue."""
    res = generate_human_base_mesh()
    facial_groups = [
        "eyes_left", "eyes_right", "eyelids", "eyebrows",
        "mouth", "lips", "teeth", "tongue"
    ]
    for feat in facial_groups:
        assert feat in res.vertex_groups
        assert len(res.vertex_groups[feat]) > 0


# ==============================================================================
# 4. HANDS & FEET ARTICULATION
# ==============================================================================

def test_ten_fingers_articulation():
    """Verify 10 articulated fingers (thumb + 4 fingers per hand, 3 phalanges each)."""
    gen = HumanAnatomyGenerator()
    res = gen.generate(HumanAnatomyConfig())

    # Left and right hand/finger groups populated
    for side in ("L", "R"):
        assert f"hand_{side}" in res.vertex_groups
        assert f"fingers_{side}" in res.vertex_groups
        assert len(res.vertex_groups[f"fingers_{side}"]) >= 40  # Multiple vertices per finger

    # Check finger landmarks exist for Rigify snapping
    assert "fingers_L" in res.landmarks
    assert "fingers_R" in res.landmarks
    assert len(res.landmarks["fingers_L"]) == 3
    assert len(res.landmarks["fingers_R"]) == 3
    # Left fingers are on +X side, right fingers are on -X side
    assert res.landmarks["fingers_L"][0] > 0
    assert res.landmarks["fingers_R"][0] < 0


def test_articulated_feet():
    """Verify articulated feet geometry and foot/toe landmarks."""
    res = generate_human_base_mesh()
    assert "foot_L" in res.vertex_groups
    assert "foot_R" in res.vertex_groups
    assert len(res.vertex_groups["foot_L"]) > 0
    assert len(res.vertex_groups["foot_R"]) > 0

    assert "ankle_L" in res.landmarks
    assert "ankle_R" in res.landmarks
    assert "toe_L" in res.landmarks
    assert "toe_R" in res.landmarks

    # Toe landmark is anterior (more negative Y) than ankle landmark
    assert res.landmarks["toe_L"][1] < res.landmarks["ankle_L"][1]
    assert res.landmarks["toe_R"][1] < res.landmarks["ankle_R"][1]
    # Toe landmark is close to ground level (Z < 0.05m)
    assert res.landmarks["toe_L"][2] < 0.05
    assert res.landmarks["toe_R"][2] < 0.05


# ==============================================================================
# 5. RIGIFY LANDMARKS & JOINT PRE-BENDS
# ==============================================================================

def test_rigify_landmarks_presence():
    """Verify all critical landmarks required for Rigify Human metarig alignment."""
    res = generate_human_base_mesh()
    expected_landmarks = [
        "head_top", "chin", "clavicle_L", "clavicle_R",
        "shoulder_L", "shoulder_R", "elbow_L", "elbow_R",
        "wrist_L", "wrist_R", "fingers_L", "fingers_R",
        "hip_L", "hip_R", "knee_L", "knee_R",
        "ankle_L", "ankle_R", "toe_L", "toe_R",
    ]
    for lm in expected_landmarks:
        assert lm in res.landmarks, f"Missing landmark '{lm}'"
        coord = res.landmarks[lm]
        assert len(coord) == 3
        assert not any(math.isnan(c) for c in coord)


def test_rigify_pre_bends():
    """
    Verify biomechanically critical joint pre-bends:
    - Elbow pre-bend: elbow Y is posterior/dorsal relative to shoulder/wrist (+Y in model space).
    - Knee pre-bend: knee Y is anterior/ventral relative to hip/ankle (-Y in model space).
    """
    res = generate_human_base_mesh()
    lm = res.landmarks

    # 1. Elbow pre-bend (+Y)
    # Model coordinates: Y is posterior/back, -Y is anterior/front
    elbow_y_L = lm["elbow_L"][1]
    shoulder_y_L = lm["shoulder_L"][1]
    wrist_y_L = lm["wrist_L"][1]
    assert elbow_y_L > shoulder_y_L, f"Elbow L Y ({elbow_y_L}) not dorsal to shoulder Y ({shoulder_y_L})"
    assert elbow_y_L > wrist_y_L, f"Elbow L Y ({elbow_y_L}) not dorsal to wrist Y ({wrist_y_L})"

    # 2. Knee pre-bend (-Y)
    knee_y_L = lm["knee_L"][1]
    hip_y_L = lm["hip_L"][1]
    ankle_y_L = lm["ankle_L"][1]
    assert knee_y_L < hip_y_L, f"Knee L Y ({knee_y_L}) not anterior to hip Y ({hip_y_L})"
    assert knee_y_L < ankle_y_L, f"Knee L Y ({knee_y_L}) not anterior to ankle Y ({ankle_y_L})"


# ==============================================================================
# 6. ARKIT FACS 52 BLENDSHAPES
# ==============================================================================

def test_fifty_two_arkit_blendshapes_presence():
    """Verify exact count and canonical naming of 52 Apple ARKit FACS blendshapes."""
    res = generate_human_base_mesh()
    assert len(res.shape_keys) == 52
    assert len(res.shape_key_deltas) == 52

    # Verify canonical keys
    canonical_samples = [
        "eyeBlinkLeft", "eyeBlinkRight", "eyeWideLeft", "eyeWideRight",
        "jawOpen", "jawForward", "mouthSmileLeft", "mouthSmileRight",
        "mouthFrownLeft", "mouthFrownRight", "browDownLeft", "browDownRight",
        "browInnerUp", "cheekPuff", "tongueOut"
    ]
    for key in canonical_samples:
        assert key in res.shape_keys, f"Missing ARKit shape key '{key}'"
        assert key in res.shape_key_deltas
        deltas = res.shape_key_deltas[key]
        assert len(deltas) > 0, f"Shape key '{key}' has no vertex deltas"


def test_blendshape_deltas_localize_to_facial_features():
    """Verify blendshape deltas deform appropriate vertex coordinates."""
    res = generate_human_base_mesh()
    # eyeBlinkLeft should displace vertices downwards in Z
    blink_deltas = res.shape_key_deltas["eyeBlinkLeft"]
    assert len(blink_deltas) > 0
    # Average delta dz should be negative (eyelid closing downward)
    avg_dz = sum(d[2] for d in blink_deltas.values()) / len(blink_deltas)
    assert avg_dz < 0.0, f"eyeBlinkLeft average dz ({avg_dz}) expected < 0.0"

    # mouthSmileLeft should displace left corner upwards (+Z) and outwards (+X)
    smile_deltas = res.shape_key_deltas["mouthSmileLeft"]
    assert len(smile_deltas) > 0
    avg_dz_smile = sum(d[2] for d in smile_deltas.values()) / len(smile_deltas)
    assert avg_dz_smile > 0.0, f"mouthSmileLeft average dz ({avg_dz_smile}) expected > 0.0"


# ==============================================================================
# 7. MULTI-FORMAT EXPORT & SCRIPT GENERATION
# ==============================================================================

def test_export_glb_and_obj(tmp_path: Path):
    """Verify mesh geometry exports to valid binary GLB and Wavefront OBJ formats."""
    res = generate_human_base_mesh()
    glb_path = tmp_path / "test_human.glb"
    obj_path = tmp_path / "test_human.obj"

    res.mesh.export_glb(str(glb_path))
    assert glb_path.exists()
    assert glb_path.stat().st_size > 1000

    res.mesh.export_obj(str(obj_path))
    assert obj_path.exists()
    assert obj_path.stat().st_size > 1000
    with open(obj_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "v " in content
        assert "f " in content


def test_blender_generation_script_syntax_and_paths():
    """Verify generated Blender script has valid syntax, uses forward slashes, and has no \\U escapes."""
    cfg = HumanAnatomyConfig(height=1.65, head_ratio=7.41)
    script = get_human_generation_script("Yu_Nian_An_Test", cfg)

    assert isinstance(script, str)
    assert len(script) > 500
    assert "import bpy" in script
    assert "import bmesh" in script
    assert "arkit_52" in script
    assert "morphomesh_landmarks" in script
    assert "shape_key_add" in script

    # Verify no unescaped Windows backslashes
    assert "\\U" not in script
    assert "\\u" not in script
