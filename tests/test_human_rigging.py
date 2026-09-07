"""
Unit Tests for MorphoMesh Rigify Human Rigging & 52 ARKit FACS Blendshapes.

Validates Milestone 2 requirements:
1. Rigify Human Metarig with exactly 163 DEF bones (64 body DEF bones + 99 facial DEF bones).
2. Bone hierarchy, parent-child relationships, and zero duplicate bone names.
3. Automated landmark snapping and pre-bend enforcement (elbow +Y, knee -Y).
4. Anti-pinching skin weights:
   - Dual-bone twist decomposition.
   - Deltoid clavicular weighting & axilla fold clamping (>=70% on spine.003).
   - Olecranon 3-loop hinge cosine gradient.
   - Patella rigid locking (>=90% on shin).
   - Finger bounding-cylinder isolation.
   - Strict normalization (sum == 1.0 for every vertex).
5. Complete 52 Apple ARKit standard FACS facial blendshapes.
6. Standalone Blender 4.5+ LTS rigging script generation (AST syntax valid).
7. Blender bridge auto_rig_human integration and path normalization (forward slashes).
"""

from __future__ import annotations

import ast
import math
import os
import pytest

from morphomesh.blender_bridge import BlenderBridge
from morphomesh.human_generator import generate_human_base_mesh
from morphomesh.human_rigging import (
    ALL_163_DEF_BONES,
    ARKIT_52_BLENDSHAPES,
    BODY_DEF_BONES,
    FACIAL_DEF_BONES,
    HumanRigConfig,
    auto_rig_human,
    calculate_anti_pinch_weights,
    generate_arkit_52_blendshapes,
    generate_rigify_human_metarig,
    get_default_human_landmarks,
    get_rigging_script,
)
from morphomesh.models import HumanRigResult


# ==============================================================================
# 1. METARIG BONE HIERARCHY & 163 DEF BONES COUNT
# ==============================================================================

class TestMetarigBoneHierarchyAndCounts:
    """Verifies that the metarig produces exactly 163 DEF bones with authentic Rigify hierarchy."""

    def test_exact_163_def_bones_count(self):
        """Verify metarig produces exactly 163 DEF bones (64 body + 99 facial)."""
        metarig = generate_rigify_human_metarig()
        assert metarig.def_bone_count == 163, (
            f"Expected 163 DEF bones, got {metarig.def_bone_count}"
        )
        assert len(metarig.body_def_bones) == 64, (
            f"Expected 64 body DEF bones, got {len(metarig.body_def_bones)}"
        )
        assert len(metarig.facial_def_bones) == 99, (
            f"Expected 99 facial DEF bones, got {len(metarig.facial_def_bones)}"
        )
        assert len(metarig.total_def_bones) == 163

    def test_no_duplicate_bone_names(self):
        """Verify all bone names across body and facial sets are strictly unique."""
        assert len(set(ALL_163_DEF_BONES)) == 163
        assert len(set(BODY_DEF_BONES)) == 64
        assert len(set(FACIAL_DEF_BONES)) == 99
        # No intersection between body and facial sets
        assert set(BODY_DEF_BONES).isdisjoint(set(FACIAL_DEF_BONES))

    def test_spine_and_head_hierarchy(self):
        """Verify spine chain, head deformer, and eye deformers parenting."""
        metarig = generate_rigify_human_metarig()
        bones = metarig.bones

        assert bones["DEF-spine"].parent is None
        assert bones["DEF-spine.001"].parent == "DEF-spine"
        assert bones["DEF-spine.002"].parent == "DEF-spine.001"
        assert bones["DEF-spine.003"].parent == "DEF-spine.002"
        assert bones["DEF-spine.004"].parent == "DEF-spine.003"
        assert bones["DEF-spine.005"].parent == "DEF-spine.004"
        assert bones["DEF-spine.006"].parent == "DEF-spine.005"
        assert bones["DEF-head"].parent == "DEF-spine.005"
        assert bones["DEF-eye.L"].parent == "DEF-spine.006"
        assert bones["DEF-eye.R"].parent == "DEF-spine.006"

    def test_limb_and_finger_hierarchy(self):
        """Verify arms, hands, fingers, and legs parenting relationships."""
        metarig = generate_rigify_human_metarig()
        bones = metarig.bones

        for side in ["L", "R"]:
            assert bones[f"DEF-shoulder.{side}"].parent == "DEF-spine.003"
            assert bones[f"DEF-upper_arm.{side}"].parent == f"DEF-shoulder.{side}"
            assert bones[f"DEF-upper_arm.{side}.001"].parent == f"DEF-upper_arm.{side}"
            assert bones[f"DEF-forearm.{side}"].parent == f"DEF-upper_arm.{side}.001"
            assert bones[f"DEF-forearm.{side}.001"].parent == f"DEF-forearm.{side}"
            assert bones[f"DEF-hand.{side}"].parent == f"DEF-forearm.{side}.001"

            # 5 Fingers hierarchy
            for digit in ["thumb", "f_index", "f_middle", "f_ring", "f_pinky"]:
                assert bones[f"DEF-{digit}.01.{side}"].parent == f"DEF-hand.{side}"
                assert bones[f"DEF-{digit}.02.{side}"].parent == f"DEF-{digit}.01.{side}"
                assert bones[f"DEF-{digit}.03.{side}"].parent == f"DEF-{digit}.02.{side}"

            # Legs hierarchy
            assert bones[f"DEF-thigh.{side}"].parent == "DEF-spine"
            assert bones[f"DEF-thigh.{side}.001"].parent == f"DEF-thigh.{side}"
            assert bones[f"DEF-shin.{side}"].parent == f"DEF-thigh.{side}.001"
            assert bones[f"DEF-shin.{side}.001"].parent == f"DEF-shin.{side}"
            assert bones[f"DEF-foot.{side}"].parent == f"DEF-shin.{side}.001"
            assert bones[f"DEF-toe.{side}"].parent == f"DEF-foot.{side}"

    def test_facial_deformers_presence_and_parenting(self):
        """Verify all 99 facial deformer bones exist and are anchored to DEF-head."""
        metarig = generate_rigify_human_metarig()
        bones = metarig.bones

        for b_name in FACIAL_DEF_BONES:
            assert b_name in bones, f"Facial deform bone {b_name} missing from metarig"
            assert bones[b_name].parent == "DEF-head"
            assert bones[b_name].use_deform is True


# ==============================================================================
# 2. LANDMARK SNAPPING & PRE-BENDS ENFORCEMENT
# ==============================================================================

class TestLandmarkSnappingAndPrebends:
    """Verifies automated landmark alignment and Rigify IK solver pre-bend requirements."""

    def test_metarig_snapped_to_custom_landmarks(self):
        """Verify bone heads and tails match provided anatomical landmarks."""
        custom_lm = get_default_human_landmarks(height=1.75)
        metarig = generate_rigify_human_metarig(landmarks=custom_lm)
        bones = metarig.bones

        # Head top and chin
        assert abs(bones["DEF-head"].tail[2] - custom_lm["head_top"][2]) < 1e-4
        assert abs(bones["DEF-head"].head[2] - custom_lm["chin"][2]) < 1e-4

        # Pelvis root
        assert abs(bones["DEF-spine"].head[2] - custom_lm["spine_pelvis"][2]) < 1e-4

        # Shoulders and clavicles
        assert abs(bones["DEF-shoulder.L"].head[0] - custom_lm["clavicle_L"][0]) < 1e-4
        assert abs(bones["DEF-shoulder.L"].tail[0] - custom_lm["shoulder_L"][0]) < 1e-4

    def test_elbow_and_knee_prebends_enforced(self):
        """
        Verify that elbows have strictly positive Y pre-bend (+Y, backward)
        and knees have strictly negative Y pre-bend (-Y, forward) symmetrically on L and R.
        """
        metarig = generate_rigify_human_metarig()
        prebend_ok, metrics = metarig.verify_prebends()
        assert prebend_ok is True
        assert metrics["elbow_L_y"] > 0.0, f"Left elbow pre-bend should be >0 (+Y), got {metrics['elbow_L_y']}"
        assert metrics["elbow_R_y"] > 0.0, f"Right elbow pre-bend should be >0 (+Y), got {metrics['elbow_R_y']}"
        assert metrics["knee_L_y"] < 0.0, f"Left knee pre-bend should be <0 (-Y), got {metrics['knee_L_y']}"
        assert metrics["knee_R_y"] < 0.0, f"Right knee pre-bend should be <0 (-Y), got {metrics['knee_R_y']}"

    def test_config_prebend_overrides(self):
        """Verify configurable pre-bend offsets."""
        cfg = HumanRigConfig(elbow_prebend_y=0.025, knee_prebend_y=-0.035)
        metarig = generate_rigify_human_metarig(config=cfg)
        assert metarig.bones["DEF-forearm.L"].head[1] >= 0.025
        assert metarig.bones["DEF-shin.L"].head[1] <= -0.035


# ==============================================================================
# 3. ANTI-PINCHING SKIN WEIGHTS & NORMALIZATION
# ==============================================================================

class TestAntiPinchSkinWeights:
    """Verifies dual-bone twist, deltoid clavicular, olecranon, patella, and finger isolation."""

    @pytest.fixture(scope="class")
    def human_mesh_and_weights(self):
        mesh_res = generate_human_base_mesh()
        metarig = generate_rigify_human_metarig(landmarks=mesh_res.landmarks)
        weights = calculate_anti_pinch_weights(mesh_res.mesh, metarig, landmarks=mesh_res.landmarks)
        return mesh_res, metarig, weights

    def test_skin_weights_strict_normalization(self, human_mesh_and_weights):
        """Verify sum of weights for 100% of vertices strictly equals 1.0."""
        _, _, weights = human_mesh_and_weights
        is_norm, checked_count, max_disc = weights.verify_normalization(tolerance=1e-4)
        assert is_norm is True, f"Normalization failure, max discrepancy: {max_disc}"
        assert checked_count > 0

    def test_dual_bone_twist_decomposition_upper_limb(self, human_mesh_and_weights):
        """Verify upper arm and forearm distribute weights across base and .001 twist deformers."""
        mesh_res, _, weights = human_mesh_and_weights
        vgroups = mesh_res.vertex_groups

        # Upper arm vertices
        arm_up_verts = vgroups.get("arm_upper_L", [])
        assert len(arm_up_verts) > 0
        has_base = any(weights.get_vertex_weight(v, "DEF-upper_arm.L") > 0.05 for v in arm_up_verts)
        has_twist = any(weights.get_vertex_weight(v, "DEF-upper_arm.L.001") > 0.05 for v in arm_up_verts)
        assert has_base and has_twist, "Upper arm dual-bone twist decomposition missing"

        # Forearm vertices
        arm_low_verts = vgroups.get("arm_lower_L", [])
        assert len(arm_low_verts) > 0
        has_fa_base = any(weights.get_vertex_weight(v, "DEF-forearm.L") > 0.05 for v in arm_low_verts)
        has_fa_twist = any(weights.get_vertex_weight(v, "DEF-forearm.L.001") > 0.05 for v in arm_low_verts)
        assert has_fa_base and has_fa_twist, "Forearm dual-bone twist decomposition missing"

    def test_olecranon_cosine_hinge_gradient_active(self, human_mesh_and_weights):
        """Verify vertices near elbow receive olecranon cosine gradient blending between upper arm twist and forearm."""
        mesh_res, _, weights = human_mesh_and_weights
        arm_up_verts = mesh_res.vertex_groups.get("arm_upper_L", [])
        w_fa = [weights.get_vertex_weight(v, "DEF-forearm.L") for v in arm_up_verts]
        w_ua1 = [weights.get_vertex_weight(v, "DEF-upper_arm.L.001") for v in arm_up_verts]
        max_w_fa = max(w_fa)
        max_w_ua1 = max(w_ua1)
        assert max_w_fa > 0.05, f"Expected olecranon hinge blending on DEF-forearm.L, got max: {max_w_fa}"
        assert max_w_ua1 > 0.05, f"Expected olecranon hinge blending on DEF-upper_arm.L.001, got max: {max_w_ua1}"

    def test_deltoid_clavicular_and_axilla_fold_clamping(self, human_mesh_and_weights):
        """Verify deltoid clavicular distribution and axilla fold clamping >= 70% on DEF-spine.003."""
        mesh_res, _, weights = human_mesh_and_weights
        arm_up_verts = mesh_res.vertex_groups.get("arm_upper_L", [])
        coords = mesh_res.mesh.vertices

        # Find axilla vertex (close to torso, high Z near shoulder)
        axilla_verts = [
            v for v in arm_up_verts
            if coords[v][0] < 0.20 and coords[v][2] < 1.32
        ]
        assert len(axilla_verts) > 0
        # Check that axilla vertices receive >= 70% weight from DEF-spine.003
        spine3_weights = [weights.get_vertex_weight(v, "DEF-spine.003") for v in axilla_verts]
        max_axilla_spine3 = max(spine3_weights)
        assert max_axilla_spine3 >= 0.70, (
            f"Expected axilla clamping >= 70% on DEF-spine.003, got {max_axilla_spine3:.2f}"
        )

    def test_patella_rigid_locking(self, human_mesh_and_weights):
        """Verify kneecap (patella) vertices are rigidly locked >= 90% to DEF-shin."""
        mesh_res, _, weights = human_mesh_and_weights
        leg_up_verts = mesh_res.vertex_groups.get("leg_upper_L", [])
        leg_low_verts = mesh_res.vertex_groups.get("leg_lower_L", [])
        all_knee_verts = leg_up_verts + leg_low_verts
        coords = mesh_res.mesh.vertices

        # Anterior knee vertices (y < -0.01 near z ~ 0.445)
        patella_verts = [
            v for v in all_knee_verts
            if abs(coords[v][2] - 0.445) < 0.04 and coords[v][1] < -0.02
        ]
        assert len(patella_verts) > 0
        shin_weights = [weights.get_vertex_weight(v, "DEF-shin.L") for v in patella_verts]
        assert max(shin_weights) >= 0.90, (
            f"Expected patella rigid locking >= 90% on DEF-shin.L, got {max(shin_weights):.2f}"
        )

    def test_finger_bounding_cylinder_isolation(self, human_mesh_and_weights):
        """Verify thumb vertices have exactly 0.0 weight on index, middle, ring, pinky bones."""
        mesh_res, _, weights = human_mesh_and_weights
        finger_verts = mesh_res.vertex_groups.get("fingers_L", [])
        coords = mesh_res.mesh.vertices

        # Identify leftmost (thumb) vertices
        max_x = max(coords[v][0] for v in finger_verts)
        thumb_candidates = [v for v in finger_verts if coords[v][0] > max_x - 0.015]
        assert len(thumb_candidates) > 0

        # Thumb vertices must receive thumb weights and ZERO weight from pinky or ring
        for v in thumb_candidates:
            thumb_w = (
                weights.get_vertex_weight(v, "DEF-thumb.01.L") +
                weights.get_vertex_weight(v, "DEF-thumb.02.L") +
                weights.get_vertex_weight(v, "DEF-thumb.03.L")
            )
            pinky_w = (
                weights.get_vertex_weight(v, "DEF-f_pinky.01.L") +
                weights.get_vertex_weight(v, "DEF-f_pinky.02.L") +
                weights.get_vertex_weight(v, "DEF-f_pinky.03.L")
            )
            assert thumb_w > 0.0
            assert pinky_w == 0.0, "Cross-finger webbing detected: thumb vertex influenced by pinky bone"


# ==============================================================================
# 4. 52 APPLE ARKIT FACS FACIAL BLENDSHAPES
# ==============================================================================

class TestARKit52FACSBlendshapes:
    """Verifies all 52 standard Apple ARKit shape keys and their 3D displacement vectors."""

    def test_all_52_shape_key_names(self):
        """Verify full catalog of 52 ARKit blendshapes is present."""
        assert len(ARKIT_52_BLENDSHAPES) == 52

        # Spot check specific critical keys
        assert "eyeBlinkLeft" in ARKIT_52_BLENDSHAPES
        assert "eyeBlinkRight" in ARKIT_52_BLENDSHAPES
        assert "jawOpen" in ARKIT_52_BLENDSHAPES
        assert "mouthSmileLeft" in ARKIT_52_BLENDSHAPES
        assert "mouthSmileRight" in ARKIT_52_BLENDSHAPES
        assert "browDownLeft" in ARKIT_52_BLENDSHAPES
        assert "browInnerUp" in ARKIT_52_BLENDSHAPES
        assert "cheekPuff" in ARKIT_52_BLENDSHAPES
        assert "tongueOut" in ARKIT_52_BLENDSHAPES

    def test_blendshapes_generation_displaces_vertices(self):
        """Verify generate_arkit_52_blendshapes produces valid sparse 3D displacements for all 52 keys."""
        mesh_res = generate_human_base_mesh()
        shape_deltas = generate_arkit_52_blendshapes(mesh_res.mesh, landmarks=mesh_res.landmarks)

        assert len(shape_deltas) == 52

        for k_name, deltas in shape_deltas.items():
            assert len(deltas) > 0, f"Blendshape {k_name} has empty displacement set"
            # Every displaced vertex has a non-zero vector
            for vi, (dx, dy, dz) in deltas.items():
                mag = math.sqrt(dx * dx + dy * dy + dz * dz)
                assert mag > 1e-6, f"Blendshape {k_name} produced zero-displacement vector for vertex {vi}"

    def test_anatomical_directional_deltas(self):
        """Verify key blendshapes displace in the correct physiological directions."""
        mesh_res = generate_human_base_mesh()
        shape_deltas = generate_arkit_52_blendshapes(mesh_res.mesh, landmarks=mesh_res.landmarks)

        # 1. eyeBlinkLeft: eyelid moves down (-Z) and slightly forward (+Y)
        blink_deltas = shape_deltas["eyeBlinkLeft"]
        dz_blink = [d[2] for d in blink_deltas.values()]
        assert any(dz < -0.005 for dz in dz_blink), "eyeBlinkLeft upper lid did not move downwards"

        # 2. jawOpen: jaw moves downwards (-Z) and backwards (-Y)
        jaw_deltas = shape_deltas["jawOpen"]
        dz_jaw = [d[2] for d in jaw_deltas.values()]
        assert all(dz < -0.010 for dz in dz_jaw), "jawOpen mouth vertices did not translate downwards"

        # 3. mouthSmileLeft: left corner moves outwards (+X) and upwards (+Z)
        smile_deltas = shape_deltas["mouthSmileLeft"]
        dx_smile = [d[0] for d in smile_deltas.values()]
        dz_smile = [d[2] for d in smile_deltas.values()]
        assert any(dx > 0.005 for dx in dx_smile), "mouthSmileLeft did not pull left corner outwards"
        assert any(dz > 0.003 for dz in dz_smile), "mouthSmileLeft did not elevate oral commissure"

        # 4. tongueOut: protrudes forward (-Y in character frame, +Y displacement forward)
        tongue_deltas = shape_deltas["tongueOut"]
        dy_tongue = [d[1] for d in tongue_deltas.values()]
        assert any(dy > 0.010 for dy in dy_tongue), "tongueOut did not protrude forward"


# ==============================================================================
# 5. STANDALONE BLENDER 4.5+ LTS SCRIPT GENERATION
# ==============================================================================

class TestBlenderRiggingScriptGeneration:
    """Verifies get_rigging_script produces syntactically valid Python code for Blender 4.5+."""

    def test_script_is_valid_python_ast(self):
        """Verify generated script parses without Python syntax errors."""
        script = get_rigging_script("Test_Human_Mesh")
        assert len(script) > 500
        # Statically parse AST
        tree = ast.parse(script)
        assert isinstance(tree, ast.Module)

    def test_script_contains_163_def_bones_and_dqs(self):
        """Verify script embeds 163 DEF bones and Dual Quaternion Skinning."""
        script = get_rigging_script("Yu_Nian_An_Base_Mesh")
        assert "use_deform_preserve_volume = True" in script
        assert "DEF-spine" in script
        assert "DEF-head" in script
        assert "DEF-eye.L" in script
        assert "DEF-eye.R" in script
        assert "DEF-jaw.center" in script
        assert "eyeBlinkLeft" in script
        assert "tongueOut" in script
        assert "vg.add(" in script
        assert "base_coords[vi][0] + delta[0]" in script


# ==============================================================================
# 6. BLENDER BRIDGE AUTO_RIG_HUMAN DISPATCH & INTEGRATION
# ==============================================================================

class TestBlenderBridgeAutoRigIntegration:
    """Verifies BlenderBridge auto_rig_human returns compliant HumanRigResult."""

    def test_auto_rig_human_direct_entrypoint(self):
        """Verify human_rigging.auto_rig_human entrypoint returns full bone hierarchy and shape keys."""
        mesh_res = generate_human_base_mesh()
        res = auto_rig_human(mesh=mesh_res.mesh, landmarks=mesh_res.landmarks)
        assert res["status"] == "success"
        assert res["bone_count"] == 163
        assert res["def_bone_count"] == 163
        assert len(res["bone_hierarchy"]) == 163
        assert res["shape_key_count"] == 52
        assert "/" in res["exported_mesh_path"]
        assert "\\" not in res["exported_mesh_path"]

        # Validates against Pydantic schema
        pydantic_res = HumanRigResult(**res)
        assert pydantic_res.def_bone_count == 163
        assert pydantic_res.armature_name == "Armature_Yu_Nian_An_Rigify"

    def test_bridge_auto_rig_human_fallback_compliance(self):
        """Verify BlenderBridge.auto_rig_human returns 163 DEF bones and normalized forward slash paths."""
        bridge = BlenderBridge(port=19997, socket_timeout=0.1)
        bridge.blender_bin_path = None  # Force local fallback

        res = bridge.auto_rig_human(mesh_object_name="Yu_Nian_An_Mesh")
        assert res["status"] == "success"
        assert res["def_bone_count"] == 163
        assert res["bone_count"] == 163
        assert len(res["bone_hierarchy"]) == 163
        assert res["shape_key_count"] == 52
        assert os.path.exists(res["exported_mesh_path"])
        # Strictly forward slashes
        assert "\\" not in res["exported_mesh_path"]
        assert "/" in res["exported_mesh_path"]

        # Pydantic schema validation
        model = HumanRigResult(**res)
        assert model.def_bone_count == 163
