# Technical Investigation Report: Connectors, Bridges & Test Infrastructure Survey

**Author**: Explorer 3 (`explorer_survey_3`)  
**Timestamp**: 2026-09-07T13:29:00Z  
**Target Package**: `src/morphomesh/anatomy/`  
**Affected Modules**: `src/morphomesh/blender_bridge.py`, `src/morphomesh/connectors/animals3d_connector.py`, `tests/`  

---

## Executive Summary

This survey provides a comprehensive audit of the creature rigging bridge in `blender_bridge.py`, the parametric animal connector in `animals3d_connector.py`, the global pytest test infrastructure, and the concrete integration design for the upcoming `src/morphomesh/anatomy/` engine.

### Key Baseline Findings:
1. **Pytest Test Suite Baseline**:
   - Total test cases: **1729** (1720 executed + 9 skipped).
   - Passing tests: **1699 passed**.
   - Failing tests: **21 failed** (all related to outdated `output/yu_nian_an/` assets: missing 163 DEF bones, 52 ARKit FACS morph targets, `TEXCOORD_0` UV channels, and finger string snapping).
   - Total execution runtime: **198.67s (3m 18s)**.
2. **`blender_bridge.py` Creature Auto-Rigging Audit**:
   - `morphomesh.create_armature` in headless script generation (`_generate_headless_script`, lines 1034–1135) employs 100% static, hardcoded coordinates (`sign * 0.3, 0.4, 0.8`, etc.) that completely ignore mesh bounds, morphology, and species posture.
   - Legs are represented by single vertical sticks (no clavicle/scapula, thigh/femur, shin/tibia, hock/ankle, paws/digits).
   - Mesh parenting creates an Armature modifier but **zero vertex groups and zero skin weights**, yet deceptively emits `"has_skin_weights": True`.
   - In interactive socket mode (`_generate_interactive_script`), `morphomesh.create_armature` is unhandled and falls through to a no-op dictionary.
3. **`animals3d_connector.py` SMAL/3DAnimals Connector Audit**:
   - Joint extraction operates solely on 35 canonical rest-pose coordinates (`CANONICAL_SMAL_35_JOINTS`) scaled by `smal.scale`; `mesh_path` and `image_path` are completely ignored.
   - Bone roll alignment uses a static vertical vector `bone.align_roll(Vector((0.0, 0.0, 1.0)))` for all bones. For vertical bones (thighs, shins), this vector is parallel to the bone vector ($\vec{v} \times \vec{t} \approx 0$), inducing numerical gimbal instability and 180° flipping.
   - Output payload sets `skin_weights={}` (empty dictionary). The internal Euclidean helper `compute_longitudinal_skin_weights` is never invoked and suffers from Euclidean distance cross-talk ("weight stealing") between disconnected surfaces.
4. **Integration Blueprint & Test Plan**:
   - Formulated a 5-module structure for `src/morphomesh/anatomy/`: `__init__.py`, `stance.py`, `landmarks.py`, `bone_roll.py`, and `skinning.py`.
   - Detailed integration hooks for both `blender_bridge.py` and `animals3d_connector.py`.
   - Drafted a rigorous test matrix for `tests/test_anatomy.py` spanning Humanoid biped and 3 animal stances (Plantigrade, Digitigrade, Unguligrade), landmark accuracy, ICR estimation, bone roll normalization, and biharmonic skinning.

---

## 1. Test Infrastructure & Global Pytest Audit

### 1.1 Execution Command & Empirical Results
Command executed:
```powershell
uv run pytest -q
```

Output Summary:
- **Total collected**: 1729 items
- **Passed**: 1699
- **Failed**: 21
- **Skipped**: 9
- **Warnings**: 1 (`PytestUnhandledThreadExceptionWarning` on listener thread shutdown)
- **Wall-clock runtime**: 198.67s (0:03:18)

### 1.2 Inventory of 21 Failing Tests
All 21 failures reside strictly in Master Character Assembly and Production Export test files:
1. `tests/test_adversarial_character_assembler.py::TestAdversarialCharacterAssembler::test_master_blend_arkit_shape_keys_empirical_deltas`
2. `tests/test_adversarial_character_assembler.py::TestAdversarialCharacterAssembler::test_master_blend_def_bones_163_exact_inventory`
3. `tests/test_adversarial_character_assembler.py::TestAdversarialCharacterAssembler::test_master_blend_cameras_50mm_and_ndc_framing`
4. `tests/test_adversarial_character_assembler.py::TestAdversarialCharacterAssembler::test_master_blend_strings_and_clearance_adversarial`
5. `tests/test_adversarial_m2_iter2_empirics.py::TestLiveBlenderBoneRotationDeformation::test_live_bone_rotation_displacement_exceeds_threshold[DEF-forearm.R-euler_xyz1-0.05]`
6. `tests/test_adversarial_rigging.py::TestLiveBlenderHeadlessExecution::test_empirical_blender_vertex_weights_and_shape_keys_defect`
7. `tests/test_challenger_m4_iter4_empirical.py::test_empirical_adversarial_audit_in_blender`
8. `tests/test_challenger_m4_iter6_empirical.py::test_empirical_adversarial_audit_in_blender`
9. `tests/test_challenger_m4_iter7_empirical.py::test_challenger_m4_iter7_empirical_blender`
10. `tests/test_challenger_m5_empirical.py::TestEmpiricalContainersAndTextures::test_glb_container_and_morphs`
11. `tests/test_challenger_m5_empirical.py::TestEmpiricalContainersAndTextures::test_fbx_binary_header_and_bones`
12. `tests/test_character_assembler.py::TestLiveBlenderMasterAssetVerification::test_live_master_blend_content_verification`
13. `tests/test_character_assembler.py::TestLiveBlenderMasterAssetVerification::test_live_camera_fullbody_and_turnaround_ndc_bounds`
14. `tests/test_character_assembler.py::TestLiveBlenderMasterAssetVerification::test_live_marionette_strings_snapped_to_finger_bone_tails`
15. `tests/test_character_assembler.py::TestLiveBlenderMasterAssetVerification::test_live_wardrobe_signed_clearance_and_zero_penetration`
16. `tests/test_character_assembler.py::TestLiveBlenderMasterAssetVerification::test_live_lips_clearance_and_material_slot_distribution`
17. `tests/test_character_assembler.py::TestLiveBlenderMasterAssetVerification::test_live_eye_spheres_hair_armature_binding_and_rotation_kinematics`
18. `tests/test_production_exports.py::TestFBXBinaryIntegrity::test_fbx_contains_def_bones_and_shape_keys`
19. `tests/test_production_exports.py::TestGLBContainerAndMorphTargets::test_glb_body_mesh_has_all_52_arkit_morph_targets`
20. `tests/test_production_exports.py::TestGLBContainerAndMorphTargets::test_glb_all_mesh_primitives_have_texcoord_0`
21. `tests/test_production_exports.py::TestGLBContainerAndMorphTargets::test_glb_uv_semantic_texture_sampling`

**Root Cause Analysis**: The failures stem from outdated physical assets on disk in `output/yu_nian_an/` (`Yu_Nian_An.fbx`, `Yu_Nian_An.glb`, `Yu_Nian_An_Master.blend`). Specifically:
- `Yu_Nian_An.fbx` is missing the full 163 DEF bone hierarchy.
- `Yu_Nian_An.glb` lacks `extras.targetNames` (contains 0 instead of 52 morph targets) and 16 mesh primitives lack the `TEXCOORD_0` attribute.
- `Yu_Nian_An_Master.blend` has unsnapped marionette curve endpoints.
These are currently being remediated in Milestone M1 by Explorer 1 and Worker 1.

### 1.3 Test Conventions & Architectural Patterns in `tests/`
Inspection of `tests/conftest.py`, `tests/test_connectors.py`, and `tests/test_blender_bridge.py` reveals the following standard patterns:
1. **Isolated Ephemeral Environments**:
   - `temp_storage_dir`: Uses pytest's `tmp_path` to isolate cache/assets, setting `MORPHOMESH_STORAGE_DIR`.
   - Dynamic asset generators: `sample_mesh_glb` and `sample_mesh_obj` build procedural test meshes via `MeshGeometry()` in-memory.
2. **Determinism & Offline Execution**:
   - 100% offline; zero external network requests or proprietary API keys.
   - Exact mathematical assertions: dot product checks (`> 0.60`), coordinate ranges, orthogonal rotation matrix determinants (`det(R) == 1.0 \pm 1e-6`).
3. **Pydantic v2 Schema Validation**:
   - Inputs and outputs validated via Pydantic models (`AnimalPoseInput`, `Animals3DOutput`, `AutoRigOutput`).
4. **Adversarial & Fuzzing Resilience**:
   - Boundary tests for degenerate triangles, zero-length bones, NaN coordinates, and monkeypatched bridge failures.

---

## 2. Connector & Bridge Implementations Survey

### 2.1 Inspection of `src/morphomesh/blender_bridge.py`

#### A. Headless Creature Rigging Implementation (`_generate_headless_script`)
Located at lines 1034–1135:
```python
    elif method == "morphomesh.create_armature":
        creature_type = params.get("creature_type", "quadruped")
        mesh_path = params.get("input_mesh_path", "")
        ...
        root = eb.new("root")
        root.head = (0.0, 0.0, 0.0)
        root.tail = (0.0, 0.0, 0.5)

        spine = eb.new("spine_01")
        spine.head = (0.0, 0.0, 0.5)
        spine.tail = (0.0, 0.0, 1.0)
        ...
        if creature_type in ("quadruped", "winged_quadruped", "hybrid"):
            for side, sign in [("L", 1.0), ("R", -1.0)]:
                fl = eb.new(f"front_leg.{side}")
                fl.head = (sign * 0.3, 0.4, 0.8)
                fl.tail = (sign * 0.3, 0.4, 0.0)
                fl.parent = spine

                bl = eb.new(f"back_leg.{side}")
                bl.head = (sign * 0.3, -0.4, 0.8)
                bl.tail = (sign * 0.3, -0.4, 0.0)
                bl.parent = root
```

#### Deficiencies Identified:
1. **Mock / Static Coordinates**:
   - All joint locations are hardcoded magic numbers (`(sign * 0.3, 0.4, 0.8)`).
   - If a 0.5m fox or a 3.0m war bear mesh is imported, the armature is created at the exact same fixed coordinates, ignoring mesh bounds, height, and scale.
2. **Gross Anatomical Inaccuracy**:
   - Quadruped limbs are represented by a single vertical bone per limb (`front_leg.L`, `back_leg.L`).
   - Missing anatomical articulation: Scapula, Humerus, Radius/Ulna, Carpus, Metacarpals, Phalanges for forelimbs; Pelvis, Femur, Tibia, Tarsus/Calcaneus, Metatarsals, Phalanges for hindlimbs.
3. **Cheating / Deceptive Skin Weights**:
   - Lines 1116–1121 parent the mesh and attach an `ARMATURE` modifier:
     ```python
     if mesh_obj:
         mesh_obj.parent = arm_obj
         mod = mesh_obj.modifiers.new(name="Armature", type='ARMATURE')
         mod.object = arm_obj
     ```
   - **Zero vertex groups are created! Zero weights are assigned!**
   - Line 1131 emits `"has_skin_weights": True`. This is completely fake: moving any bone in pose mode will deform 0 vertices.
4. **Zero Bone Roll & Pre-Bend**:
   - Bone roll is uninitialized (defaults to 0.0 radians).
   - Bone axes do not follow joint hinge bending planes, leading to extreme candy-wrapper collapse.
   - Limbs are collinear vertical lines without joint pre-bends (causing IK singularities).
5. **Interactive Socket Parity Missing**:
   - In `_generate_interactive_script` (lines 566–631), `morphomesh.create_armature` has no handling branch. Calling it through an active socket returns an empty `{}` without performing any operations.

---

### 2.2 Inspection of `src/morphomesh/connectors/animals3d_connector.py`

#### A. Parametric Landmark & Script Generation (`execute`)
Located at lines 334–407:
```python
        for joint_name, canonical_pt in CANONICAL_SMAL_35_JOINTS.items():
            scaled_pt = [c * smal.scale for c in canonical_pt]
            blender_coords = transform_smal_to_blender(scaled_pt)
            ...
            for target_bone in rigify_targets:
                blender_script_lines.extend([
                    f"    bone = ebones.get('{target_bone}')",
                    "    if bone:",
                    f"        bone.head = Vector(({blender_coords[0]}, {blender_coords[1]}, {blender_coords[2]}))",
                    "        bone.align_roll(Vector((0.0, 0.0, 1.0)))",
                ])
        ...
        return Animals3DOutput(
            ...
            skin_weights={},
        )
```

#### Deficiencies Identified:
1. **Decoupled Landmark Extraction**:
   - Joints are sourced strictly from `CANONICAL_SMAL_35_JOINTS` (static dictionary).
   - `AnimalPoseInput.mesh_path` and `image_path` are never read or processed. The connector cannot adapt joints to custom creature meshes.
2. **Defective Static Bone Roll Alignment**:
   - Uses `bone.align_roll(Vector((0.0, 0.0, 1.0)))` indiscriminately.
   - For vertical limb bones (where bone vector $\vec{b} \approx [0, 0, -L]$), the cross product $\vec{b} \times [0, 0, 1] \approx \vec{0}$, causing degenerate projection, erratic roll flipping, and pole-target inversion in Rigify Wolf.
3. **Empty Skin Weights in Output**:
   - `Animals3DOutput.skin_weights` is hardcoded to `{}`.
4. **Flawed Longitudinal Skin Weight Helper**:
   - `compute_longitudinal_skin_weights` (lines 299–332) uses Euclidean distance projection:
     $$d = \|\vec{v} - (\vec{h} + u(\vec{t} - \vec{h}))\|,\quad w = \exp(-3.0 \cdot d)$$
   - Problems:
     - Causes severe weight stealing between adjacent but anatomically disconnected meshes (inner thighs, chest to paws).
     - Does not enforce partition-of-unity ($\sum_b w_b(v) = 1.0$).
     - Has no biharmonic or Laplacian smoothing.

---

## 3. Architecture of `src/morphomesh/anatomy/`

The new anatomy engine will reside in `src/morphomesh/anatomy/` and expose a unified, mathematically rigorous API.

```
src/morphomesh/anatomy/
├── __init__.py          # Authoritative exports
├── stance.py            # Locomotor stance classifier & biomechanics
├── landmarks.py         # Bony landmark extraction & Instantaneous Center of Rotation (ICR)
├── bone_roll.py         # Biomechanical hinge normal solver & 1-DOF pre-bend
└── skinning.py          # Volumetric geodesic voxel biharmonic skinning solver
```

### 3.1 Public Interface in `__init__.py`
```python
from morphomesh.anatomy.stance import (
    StanceType,
    LocomotorStanceResult,
    classify_locomotor_stance,
)
from morphomesh.anatomy.landmarks import (
    BonyLandmark,
    AnatomicalLandmarkSet,
    compute_bony_landmarks,
    estimate_joint_icr,
)
from morphomesh.anatomy.bone_roll import (
    HingePlaneNormal,
    BoneRollSolution,
    solve_biomechanical_bone_roll,
    apply_joint_prebend,
)
from morphomesh.anatomy.skinning import (
    BiharmonicSkinningConfig,
    compute_geodesic_skin_weights,
)
```

---

## 4. Integration Design for Connectors & Bridges

### 4.1 Integration into `src/morphomesh/blender_bridge.py`

#### A. Architecture
```
BlenderBridge.create_armature()
   │
   ├─► 1. Mesh Ingestion: Load vertices & faces from input_mesh_path
   │
   ├─► 2. Stance Classification: classify_locomotor_stance(verts, faces)
   │        └─► Returns: Humanoid | Plantigrade | Digitigrade | Unguligrade
   │
   ├─► 3. Landmark & ICR Detection: compute_bony_landmarks(verts, faces, stance)
   │        └─► Generates multi-segment limb joints + ICR rotation pivots
   │
   ├─► 4. Biomechanical Pre-Bend & Roll: solve_biomechanical_bone_roll(...)
   │        └─► Applies elbow/knee/stifle/hock pre-bends & hinge normal roll
   │
   ├─► 5. Biharmonic Skinning: compute_geodesic_skin_weights(verts, faces, bones)
   │        └─► Generates normalized vertex groups (partition-of-unity)
   │
   └─► 6. Script Generation (Headless & Interactive Parity):
            - Creates edit bones matching computed joints and rolls
            - Populates vertex groups and genuine weights on mesh object
            - Returns AutoRigOutput with verified has_skin_weights=True
```

#### B. Code Integration Blueprint for `blender_bridge.py`
In `_generate_headless_script` (method `"morphomesh.create_armature"`):
```python
# Import anatomy engine
from morphomesh.anatomy import (
    classify_locomotor_stance,
    compute_bony_landmarks,
    solve_biomechanical_bone_roll,
    compute_geodesic_skin_weights,
)

# Extract mesh geometry
mesh_geom = MeshGeometry.from_file(mesh_path)
stance_res = classify_locomotor_stance(mesh_geom.vertices, mesh_geom.faces)
landmarks = compute_bony_landmarks(mesh_geom.vertices, mesh_geom.faces, stance=stance_res.stance)
skin_weights = compute_geodesic_skin_weights(mesh_geom.vertices, mesh_geom.faces, landmarks.bone_segments)

# Serialized into the generated bpy script to construct real bones and vertex groups
```

### 4.2 Integration into `src/morphomesh/connectors/animals3d_connector.py`

#### A. Architecture
```
Animals3DConnector.execute(request)
   │
   ├─► Has input mesh_path?
   │     ├─ YES: Extract vertices/faces -> classify_locomotor_stance -> compute_bony_landmarks
   │     └─ NO:  Fallback to CANONICAL_SMAL_35_JOINTS adapted to species stance
   │
   ├─► Bone Roll Calculation:
   │     └─ For each target_bone:
   │          roll = solve_biomechanical_bone_roll(head, tail, parent, child, stance)
   │          bone.roll = roll.roll_radians
   │
   ├─► Skin Weights Computation:
   │     └─ If mesh provided:
   │          skin_weights = compute_geodesic_skin_weights(verts, faces, bones)
   │
   └─► Output: Populates Animals3DOutput.skin_weights with real weights
```

---

## 5. Comprehensive Test Plan for `tests/test_anatomy.py`

The test suite will be structured into 5 dedicated test classes covering all functional and biomechanical requirements:

```python
"""
MorphoMesh: Anatomical Skeletal Estimation & Biomechanical Rigging Test Suite.
File: tests/test_anatomy.py
"""

# ==============================================================================
# 1. LOCOMOTOR STANCE CLASSIFICATION TESTS
# ==============================================================================
class TestLocomotorStanceClassification:
    """Tests classification across Humanoid and 3 biological animal stances."""

    def test_humanoid_biped_classification(self):
        """Upright mesh with vertical spine and dual lower limbs -> Humanoid."""

    def test_plantigrade_ursine_classification(self):
        """Quadruped with calcaneus resting on ground plane (z_heel ≈ z_pad) -> Plantigrade."""

    def test_digitigrade_canine_classification(self):
        """Quadruped with elevated hock (z_calcaneus > 0.15 * leg_height) -> Digitigrade."""

    def test_unguligrade_equine_classification(self):
        """Quadruped walking on terminal hooves with elongated metapodials -> Unguligrade."""

    def test_noisy_mesh_and_scale_invariance(self):
        """Classification remains invariant under uniform scaling (0.1x to 10x) and mild noise."""


# ==============================================================================
# 2. BONY LANDMARK & ICR PIVOT DETECTION TESTS
# ==============================================================================
class TestBonyLandmarksAndICR:
    """Verifies surface landmark detection and Instantaneous Center of Rotation."""

    def test_humanoid_bony_landmarks_accuracy(self):
        """Accurately detects clavicle S-curve, suprasternal notch, patella, and olecranon."""

    def test_asymmetric_malleoli_landmarks(self):
        """Medial malleolus is positioned higher than lateral malleolus on ankle meshes."""

    def test_quadruped_landmarks_across_stances(self):
        """Extracts scapular spine, withers, stifle, hock/calcaneus across stances."""

    def test_icr_offset_from_geometric_centroid(self):
        """Knee/elbow ICR is offset toward biological rolling condyle surface rather than bbox center."""

    def test_icr_rigid_transform_covariance(self):
        """R * ICR(v) + t == ICR(R * v + t) under SE(3) transformations."""


# ==============================================================================
# 3. BIOMECHANICAL BONE ROLL & PRE-BEND TESTS
# ==============================================================================
class TestBoneRollAndPreBend:
    """Verifies hinge normal calculation, 1-DOF pre-bends, and anti-twist roll."""

    def test_hinge_plane_normal_vector(self):
        """Computes n_hinge = (p_joint - p_parent) x (p_child - p_joint) aligned with flexion axis."""

    def test_collinear_limb_prebend_injection(self):
        """Straight limbs get subtle natural flexion pre-bend (>= 3 deg) preventing IK singularity."""

    def test_human_vs_quadruped_prebend_directions(self):
        """Human knee pre-bends backward (-Y), elbow forward (+Y); Quadruped stifle forward (+Y), hock backward (-Y)."""

    def test_bone_roll_eliminates_candy_wrapper_and_pole_flip(self):
        """Bone roll primary axis aligns with hinge normal, preventing Rigify 180 deg flips."""


# ==============================================================================
# 4. VOLUMETRIC GEODESIC BIHARMONIC SKINNING TESTS
# ==============================================================================
class TestBiharmonicSkinning:
    """Validates volume-preserving geodesic biharmonic weight diffusion."""

    def test_partition_of_unity(self):
        """For every vertex v, sum(w_b(v)) == 1.0 +- 1e-5 and 0 <= w_b(v) <= 1."""

    def test_anti_weight_stealing_axilla_chest(self):
        """Lateral chest vertices have < 5% influence from upper arm / humerus bones."""

    def test_anti_weight_stealing_inner_thighs(self):
        """Left inner thigh vertices have 0.0% weight from right leg bones."""

    def test_smooth_laplacian_continuity(self):
        """Weights vary continuously without jagged discrete seams across adjacent vertices."""

    def test_weight_matrix_sparsity(self):
        """Enforces max 4 or 8 dominant bones per vertex for real-time GPU/game export."""


# ==============================================================================
# 5. CONNECTOR & BRIDGE INTEGRATION VERIFICATION TESTS
# ==============================================================================
class TestBridgeAndConnectorIntegration:
    """Ensures bridge and connector successfully utilize the anatomy engine."""

    def test_blender_bridge_create_armature_with_anatomy(self):
        """create_armature generates genuine multi-segment bones and real skin weights."""

    def test_animals3d_connector_mesh_aware_execution(self):
        """Animals3DConnector extracts real landmarks and non-empty skin_weights when mesh provided."""
```

---

## 6. Implementation Recommendations & Milestones Roadmap

1. **Milestone M1 (Current)**:
   - Complete Yu Nian An production assets export (`Yu_Nian_An.fbx` with 163 DEF bones, `Yu_Nian_An.glb` with 52 ARKit blendshapes + `TEXCOORD_0`, `Yu_Nian_An_Master.blend` with marionette curve snapping).
   - Resolve all 21 failing tests to reach 100% pass rate.
2. **Milestone M2 (Stance & Landmarks Engine)**:
   - Implement `src/morphomesh/anatomy/stance.py` and `landmarks.py`.
3. **Milestone M3 (Bone Roll & Pre-Bend Solver)**:
   - Implement `src/morphomesh/anatomy/bone_roll.py`.
4. **Milestone M4 (Biharmonic Geodesic Skinning)**:
   - Implement `src/morphomesh/anatomy/skinning.py`.
5. **Milestone M5 (Integration & Verification)**:
   - Wire `blender_bridge.py` and `animals3d_connector.py` into `morphomesh.anatomy`.
   - Write `tests/test_anatomy.py` and verify `uv run pytest -q` passes with 0 failures across all 1729+ tests.
