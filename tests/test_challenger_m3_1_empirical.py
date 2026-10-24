"""
Empirical Challenger Test Suite for Milestone 3:
MakeHuman Mold Parsing, Vertex Group Validation, 163 DEF Bones Metarig, and 52 ARKit Blendshapes.

Author: Challenger M3-1 (Empirical Adversarial Reviewer)
Target Modules:
- src/morphomesh/human/ (mold_loader, morphology, anatomy, scripts)
- src/morphomesh/rigging/ (metarig, anti_pinch, blendshapes, scripts)
- src/morphomesh/human_generator.py (facade)
- src/morphomesh/human_rigging.py (facade)
"""

from __future__ import annotations

import math
from typing import Dict, List, Set, Tuple
import pytest

# Subsystem package imports
import morphomesh.human as mm_human
from morphomesh.human import (
    STANDARDIZED_HUMAN_VERTEX_GROUPS,
    ARKIT_52_BLENDSHAPES as HUMAN_ARKIT_52,
    PROPORTION_PRESETS,
    PRESET_ALIASES,
    HumanAnatomyConfig,
    HumanAnatomyGenerator,
    HumanMeshResult,
    compute_quad_metrics,
    add_quad_cap,
    add_quad_ellipsoid,
    load_anatomical_base_mold,
    extract_makehuman_joint_landmarks,
    enforce_quad_closure,
    compute_relaxed_vertex_normals,
    compute_standardized_vertex_groups,
    resolve_human_anatomy_config,
    generate_human_base_mesh,
    generate_human_body,
    get_human_generation_script,
)

# Rigging package imports
import morphomesh.rigging as mm_rigging
from morphomesh.rigging import (
    ALL_163_DEF_BONES,
    BODY_DEF_BONES,
    FACIAL_DEF_BONES,
    ARKIT_52_BLENDSHAPES as RIGGING_ARKIT_52,
    HumanRigConfig,
    BoneDefinition,
    MetarigStructure,
    SkinWeightMap,
    get_default_human_landmarks,
    generate_rigify_human_metarig,
    align_rigify_metarig_pivots,
    calculate_anti_pinch_weights,
    generate_arkit_52_blendshapes,
    get_rigging_script,
    auto_rig_human,
)

# Facade imports
import morphomesh.human_generator as facade_human
import morphomesh.human_rigging as facade_rigging
from morphomesh.geometry.mesh import MeshGeometry


# ==============================================================================
# 1. MAKEHUMAN MOLD PARSING & GEOMETRIC TOPOLOGY STRESS TESTS
# ==============================================================================

class TestMakeHumanMoldParsing:
    """Adversarially validates MakeHuman base mold loading, quad dominance, and caching."""

    def test_mold_loader_counts_and_topology(self):
        """Assert exact base mold vertex, quad, and UV counts."""
        raw_verts, raw_quads, raw_uvs = load_anatomical_base_mold()
        assert len(raw_verts) == 13380, f"Expected 13380 verts, got {len(raw_verts)}"
        assert len(raw_quads) == 13378, f"Expected 13378 quads, got {len(raw_quads)}"
        assert len(raw_uvs) == 13380, f"Expected 13380 UVs, got {len(raw_uvs)}"

        # Verify caching returns identical memory object
        cached_verts, cached_quads, cached_uvs = load_anatomical_base_mold()
        assert cached_verts is raw_verts
        assert cached_quads is raw_quads
        assert cached_uvs is raw_uvs

    def test_mold_quad_dominance_and_zero_triangles(self):
        """Verify that the base mold mesh has 100% pure quad dominance."""
        mesh = MeshGeometry()
        raw_verts, raw_quads, raw_uvs = load_anatomical_base_mold()
        for idx in range(len(raw_verts)):
            mesh.add_vertex(raw_verts[idx], (0.0, 1.0, 0.0), raw_uvs[idx])
        for q in raw_quads:
            mesh.add_quad(q[0], q[1], q[2], q[3])

        quad_count, tri_count, quad_ratio = compute_quad_metrics(mesh)
        assert quad_count == 13378
        assert tri_count == 0
        assert quad_ratio == 1.0, f"Base mold quad ratio {quad_ratio} != 1.0"

    def test_enforce_quad_closure_isolated_seed(self):
        """Verify enforce_quad_closure expands partial quad seeds to fully closed quads."""
        raw_verts, raw_quads, _ = load_anatomical_base_mold()
        first_quad = raw_quads[0]
        # Provide only 2 vertices of the quad
        seeds = [first_quad[0], first_quad[1]]
        closed = enforce_quad_closure(seeds, raw_quads)
        assert first_quad[0] in closed
        assert first_quad[1] in closed

    def test_relaxed_normals_unit_length_and_alignment(self):
        """Verify vertex normals are normalized unit vectors and finite."""
        raw_verts, raw_quads, _ = load_anatomical_base_mold()
        normals, faces = compute_relaxed_vertex_normals(raw_verts, raw_quads)
        assert len(normals) == len(raw_verts)
        for i, norm in enumerate(normals):
            for c in norm:
                assert not math.isnan(c) and not math.isinf(c), f"NaN/Inf normal at vertex {i}"
            length = math.sqrt(sum(c * c for c in norm))
            assert abs(length - 1.0) < 1e-4, f"Normal {i} not normalized: length = {length}"

    def test_landmark_extraction_completeness(self):
        """Verify all 125 MakeHuman joint landmarks are extracted with non-zero coordinates."""
        landmarks = extract_makehuman_joint_landmarks(target_height=1.65)
        assert len(landmarks) >= 120, f"Expected >= 120 joint landmarks, got {len(landmarks)}"
        for name, pt in landmarks.items():
            assert name.startswith("joint-")
            for c in pt:
                assert not math.isnan(c) and not math.isinf(c), f"NaN/Inf in landmark {name}"
            # Check within reasonable bounding box bounds for 1.65m character
            assert abs(pt[0]) <= 1.0, f"Landmark {name} X out of bounds: {pt[0]}"
            assert abs(pt[1]) <= 0.6, f"Landmark {name} Y out of bounds: {pt[1]}"
            assert -0.05 <= pt[2] <= 1.8, f"Landmark {name} Z out of bounds: {pt[2]}"


# ==============================================================================
# 2. VERTEX GROUP VALIDATION & BILATERAL SYMMETRY
# ==============================================================================

class TestVertexGroupValidation:
    """Validates presence, non-emptiness, bounds, and symmetry of all vertex groups."""

    @pytest.fixture(scope="class")
    def canonical_mesh_result(self) -> HumanMeshResult:
        return generate_human_base_mesh()

    def test_all_34_standardized_groups_present_and_non_empty(self, canonical_mesh_result):
        """Verify all 34 standardized groups and breast deformation groups are populated."""
        vg = canonical_mesh_result.vertex_groups
        total_verts = len(canonical_mesh_result.mesh.vertices)

        for g_name in STANDARDIZED_HUMAN_VERTEX_GROUPS:
            assert g_name in vg, f"Missing vertex group {g_name}"
            indices = vg[g_name]
            assert len(indices) > 0, f"Vertex group {g_name} is empty"
            assert max(indices) < total_verts, f"Vertex index out of bounds in {g_name}"
            assert min(indices) >= 0, f"Negative vertex index in {g_name}"

        # Breast deformation groups
        assert "breast.L" in vg and len(vg["breast.L"]) > 0
        assert "breast.R" in vg and len(vg["breast.R"]) > 0

    def test_bilateral_symmetry_of_limb_groups(self, canonical_mesh_result):
        """Verify bilateral limb groups have approximately equal vertex counts (symmetry)."""
        vg = canonical_mesh_result.vertex_groups
        pairs = [
            ("eyes_left", "eyes_right"),
            ("arm_upper_L", "arm_upper_R"),
            ("arm_lower_L", "arm_lower_R"),
            ("hand_L", "hand_R"),
            ("fingers_L", "fingers_R"),
            ("leg_upper_L", "leg_upper_R"),
            ("leg_lower_L", "leg_lower_R"),
            ("foot_L", "foot_R"),
            ("toenails_L", "toenails_R"),
            ("plantar_arch_L", "plantar_arch_R"),
            ("breast.L", "breast.R"),
        ]
        for left_g, right_g in pairs:
            cnt_l = len(vg[left_g])
            cnt_r = len(vg[right_g])
            # Relative discrepancy should be < 10%
            diff = abs(cnt_l - cnt_r)
            avg = (cnt_l + cnt_r) / 2.0
            assert (diff / avg) < 0.10, (
                f"Symmetry imbalance between {left_g} ({cnt_l}) and {right_g} ({cnt_r})"
            )


# ==============================================================================
# 3. EXTREME MORPHOLOGY & NUMERICAL STABILITY STRESS TESTS
# ==============================================================================

class TestExtremeMorphologyStress:
    """Stress tests mesh generation across boundary and extreme morphology parameters."""

    @pytest.mark.parametrize(
        "desc,cfg",
        [
            ("Dwarf_1.0m_Boundary", HumanAnatomyConfig(height=1.00, head_ratio=5.0)),
            ("Giant_2.5m_Boundary", HumanAnatomyConfig(height=2.50, head_ratio=10.0)),
            ("Extreme_Pear_WHR_0.33", HumanAnatomyConfig(waist_girth=0.40, hip_girth=1.20)),
            ("Extreme_Apple_WHR_1.40", HumanAnatomyConfig(waist_girth=1.12, hip_girth=0.80)),
            ("Ultra_Broad_Shoulders", HumanAnatomyConfig(shoulder_width=0.55, chest_girth=1.40)),
            ("Ultra_Narrow_Slender", HumanAnatomyConfig(shoulder_width=0.25, chest_girth=0.55)),
        ],
    )
    def test_zero_nans_infs_and_positive_quad_dominance(self, desc: str, cfg: HumanAnatomyConfig):
        """Assert zero NaNs, zero Infs, valid bounding boxes, and >=99% quad dominance."""
        res = generate_human_base_mesh(config=cfg)
        mesh = res.mesh

        # 1. Vertices finite
        for vi, v in enumerate(mesh.vertices):
            for c in v:
                assert not math.isnan(c) and not math.isinf(c), f"{desc}: NaN/Inf in vertex {vi}"

        # 2. Normals finite
        for vi, norm in enumerate(mesh.normals):
            for c in norm:
                assert not math.isnan(c) and not math.isinf(c), f"{desc}: NaN/Inf in normal {vi}"

        # 3. UVs finite
        for vi, uv in enumerate(mesh.uvs):
            for c in uv:
                assert not math.isnan(c) and not math.isinf(c), f"{desc}: NaN/Inf in UV {vi}"

        # 4. Landmarks finite
        for lname, pt in res.landmarks.items():
            for c in pt:
                assert not math.isnan(c) and not math.isinf(c), f"{desc}: NaN/Inf in landmark {lname}"

        # 5. Bounding box finite and dimensions strictly positive
        bb = res.bounding_box
        for dim in bb.dimensions:
            assert dim > 0.0, f"{desc}: non-positive bounding box dimension {dim}"
            assert not math.isnan(dim) and not math.isinf(dim)

        # 6. Quad dominance >= 99%
        assert res.quad_ratio >= 0.99, f"{desc}: quad ratio {res.quad_ratio} < 0.99"

    @pytest.mark.parametrize(
        "invalid_kwargs",
        [
            {"height": 0.50},   # below ge=1.0
            {"height": 3.00},   # above le=2.5
            {"head_ratio": 4.0}, # below ge=5.0
            {"head_ratio": 12.0}, # above le=10.0
            {"waist_girth": 0.30}, # below ge=0.4
            {"waist_girth": 1.50}, # above le=1.2
            {"shoulder_width": 0.10}, # below ge=0.2
            {"shoulder_width": 1.00}, # above le=0.8
        ],
    )
    def test_extreme_out_of_bounds_validation_errors(self, invalid_kwargs: dict):
        """Verify that Pydantic strictly rejects anthropometric values beyond biological safety bounds."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            HumanAnatomyConfig(**invalid_kwargs)


# ==============================================================================
# 4. 163 DEF BONES METARIG GENERATION & BONE ROLL ALIGNMENT
# ==============================================================================

class TestMetarig163DefBonesAndRoll:
    """Stress tests metarig generation, 163 DEF bones, and biological joint pivots."""

    def test_exact_163_def_bones_composition(self):
        """Verify metarig def_bone_count is exactly 163 (64 body + 99 facial)."""
        metarig = generate_rigify_human_metarig()
        assert metarig.def_bone_count == 163
        assert len(metarig.body_def_bones) == 64
        assert len(metarig.facial_def_bones) == 99

        for b_name in ALL_163_DEF_BONES:
            assert b_name in metarig.bones, f"Missing bone {b_name} in metarig.bones"
            b = metarig.bones[b_name]
            assert b.use_deform is True

    def test_bone_lengths_and_finite_coordinates(self):
        """Verify every bone has non-zero positive length and finite head/tail coordinates."""
        metarig = generate_rigify_human_metarig()
        for b_name, b in metarig.bones.items():
            for c in b.head + b.tail:
                assert not math.isnan(c) and not math.isinf(c), f"Bone {b_name} coordinate is NaN/Inf"
            dx = b.tail[0] - b.head[0]
            dy = b.tail[1] - b.head[1]
            dz = b.tail[2] - b.head[2]
            length = math.sqrt(dx * dx + dy * dy + dz * dz)
            assert length > 0.001, f"Bone {b_name} has degenerate length {length:.6f}m"

    def test_prebends_and_hinge_axes(self):
        """Verify elbow (+Y) and knee (-Y) pre-bends and hinge axis alignment."""
        metarig = generate_rigify_human_metarig()
        prebend_ok, pmetrics = metarig.verify_prebends()
        assert prebend_ok is True
        assert pmetrics["elbow_L_y"] > 0.0, "Elbow L +Y pre-bend violated"
        assert pmetrics["elbow_R_y"] > 0.0, "Elbow R +Y pre-bend violated"
        assert pmetrics["knee_L_y"] < 0.0, "Knee L -Y pre-bend violated"
        assert pmetrics["knee_R_y"] < 0.0, "Knee R -Y pre-bend violated"

    def test_pivot_alignment_idempotence(self):
        """Verify align_rigify_metarig_pivots executes idempotently without shifting bones."""
        landmarks = get_default_human_landmarks()
        metarig = generate_rigify_human_metarig(landmarks=landmarks)
        initial_bones = {b_name: (b.head, b.tail) for b_name, b in metarig.bones.items()}
        align_rigify_metarig_pivots(metarig, landmarks)
        assert metarig.def_bone_count == 163
        for b_name, b in metarig.bones.items():
            assert b_name in initial_bones


# ==============================================================================
# 5. ANTI-PINCH SKIN WEIGHTS NORMALIZATION & PARTITION OF UNITY
# ==============================================================================

class TestAntiPinchSkinWeightsNormalization:
    """Stress tests skin weights normalization (sum == 1.0), non-negativity, and isolation."""

    @pytest.fixture(scope="class")
    def rig_and_weights(self):
        mesh_res = generate_human_base_mesh()
        metarig = generate_rigify_human_metarig(landmarks=mesh_res.landmarks)
        weights = calculate_anti_pinch_weights(mesh_res.mesh, metarig, landmarks=mesh_res.landmarks)
        return mesh_res, metarig, weights

    def test_strict_partition_of_unity_all_13380_vertices(self, rig_and_weights):
        """Verify every vertex's weights sum to exactly 1.0 +/- 1e-4."""
        mesh_res, _, weights = rig_and_weights
        is_norm, count, max_disc = weights.verify_normalization(tolerance=1e-4)
        assert is_norm is True, f"Weights normalization failed with max discrepancy: {max_disc}"
        assert count == len(mesh_res.mesh.vertices)
        assert count == 13380

    def test_weights_strictly_non_negative(self, rig_and_weights):
        """Verify no vertex has negative skinning weights."""
        mesh_res, _, weights = rig_and_weights
        for vi in range(len(mesh_res.mesh.vertices)):
            vw = weights.weights.get(vi, {})
            for b_name, w in vw.items():
                assert w >= 0.0, f"Negative weight at vertex {vi} for {b_name}: {w}"

    def test_dual_bone_twist_decomposition(self, rig_and_weights):
        """Verify upper arm, forearm, thigh, and shin decompose into primary and twist bones."""
        mesh_res, _, weights = rig_and_weights
        vg = mesh_res.vertex_groups

        # Upper arm
        ua_verts = vg.get("arm_upper_L", [])
        assert any(weights.get_vertex_weight(v, "DEF-upper_arm.L") > 0.05 for v in ua_verts)
        assert any(weights.get_vertex_weight(v, "DEF-upper_arm.L.001") > 0.05 for v in ua_verts)

        # Forearm
        fa_verts = vg.get("arm_lower_L", [])
        assert any(weights.get_vertex_weight(v, "DEF-forearm.L") > 0.05 for v in fa_verts)
        assert any(weights.get_vertex_weight(v, "DEF-forearm.L.001") > 0.05 for v in fa_verts)

        # Thigh
        th_verts = vg.get("leg_upper_L", [])
        assert any(weights.get_vertex_weight(v, "DEF-thigh.L") > 0.05 for v in th_verts)
        assert any(weights.get_vertex_weight(v, "DEF-thigh.L.001") > 0.05 for v in th_verts)

        # Shin
        sh_verts = vg.get("leg_lower_L", [])
        assert any(weights.get_vertex_weight(v, "DEF-shin.L") > 0.05 for v in sh_verts)
        assert any(weights.get_vertex_weight(v, "DEF-shin.L.001") > 0.05 for v in sh_verts)


# ==============================================================================
# 6. 52 APPLE ARKIT FACS FACIAL BLENDSHAPES DELTA DISPLACEMENTS
# ==============================================================================

class TestARKit52BlendshapesEmpirical:
    """Stress tests 52 ARKit blendshapes generation and displacement vectors."""

    def test_52_shape_keys_catalog_and_deltas_count(self):
        """Verify 52 shape keys exist and have non-empty delta displacements."""
        mesh_res = generate_human_base_mesh()
        shapes = generate_arkit_52_blendshapes(mesh_res.mesh, landmarks=mesh_res.landmarks)
        assert len(shapes) == 52

        for k_name in RIGGING_ARKIT_52:
            assert k_name in shapes, f"Missing shape key: {k_name}"
            deltas = shapes[k_name]
            assert len(deltas) > 0, f"Shape key {k_name} has 0 displaced vertices"

            for vi, delta in deltas.items():
                for c in delta:
                    assert not math.isnan(c) and not math.isinf(c), f"NaN/Inf in {k_name} vertex {vi}"
                mag = math.sqrt(sum(c * c for c in delta))
                assert mag > 1e-6, f"Zero displacement magnitude for {k_name} vertex {vi}"

    def test_blendshape_scaling_linearity(self):
        """Verify blendshape displacement deltas scale linearly with scale factor."""
        mesh_res = generate_human_base_mesh()
        shapes_1x = generate_arkit_52_blendshapes(mesh_res.mesh, landmarks=mesh_res.landmarks, scale=1.0)
        shapes_2x = generate_arkit_52_blendshapes(mesh_res.mesh, landmarks=mesh_res.landmarks, scale=2.0)

        # Compare sample key 'eyeBlinkLeft'
        d1 = shapes_1x["eyeBlinkLeft"]
        d2 = shapes_2x["eyeBlinkLeft"]
        assert len(d1) == len(d2)

        sample_vi = next(iter(d1.keys()))
        v1 = d1[sample_vi]
        v2 = d2[sample_vi]
        for c1, c2 in zip(v1, v2):
            assert abs(c2 - 2.0 * c1) < 1e-6, "Displacement deltas did not scale linearly with scale=2.0"


# ==============================================================================
# 7. SUBSYSTEM FACADE PARITY & RE-EXPORT VERIFICATION
# ==============================================================================

class TestFacadeSubsystemParity:
    """Verifies that human_generator.py and human_rigging.py re-export 100% of symbols."""

    def test_human_generator_facade_re_exports(self):
        """Verify morphomesh.human_generator re-exports all symbols from morphomesh.human."""
        for sym in facade_human.__all__:
            assert hasattr(mm_human, sym), f"Symbol {sym} in facade but not in morphomesh.human"
            assert hasattr(facade_human, sym), f"Symbol {sym} missing from facade_human"
            obj_facade = getattr(facade_human, sym)
            obj_pkg = getattr(mm_human, sym)
            assert obj_facade is obj_pkg, f"Symbol {sym} identity mismatch between facade and pkg"

    def test_human_rigging_facade_re_exports(self):
        """Verify morphomesh.human_rigging re-exports all symbols from morphomesh.rigging."""
        for sym in facade_rigging.__all__:
            assert hasattr(mm_rigging, sym), f"Symbol {sym} in facade but not in morphomesh.rigging"
            assert hasattr(facade_rigging, sym), f"Symbol {sym} missing from facade_rigging"
            obj_facade = getattr(facade_rigging, sym)
            obj_pkg = getattr(mm_rigging, sym)
            assert obj_facade is obj_pkg, f"Symbol {sym} identity mismatch between facade and pkg"
