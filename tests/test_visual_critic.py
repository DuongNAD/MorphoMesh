"""
MorphoMesh: Automated Visual Quality Critique & Inspection Engine Test Suite.

Milestone 3 Test Suite.
Tests:
1. Pydantic v2 Models, Enums, Normalizations, and Error Taxonomy
2. PurePythonBVHTree: Eberly point-triangle distance, Moller-Trumbore raycast, Moller triangle overlap
3. Procedural Defect Injection Fixtures: Penetration, Proportions, Skinning, Hair clipping
4. Accuracy Benchmark: Verifies >95% accuracy and 0% false positive rate across all 9 fixture states
5. Blender Bridge & Listener Dispatch Parity: Client method, RPC dispatch, and headless script generation
"""

import math
import pytest
import numpy as np

from morphomesh.models import (
    DefectSeverity,
    DefectCategory,
    ActionableRecommendation,
    DefectItem,
    VisualCritiqueInput,
    VisualCritiqueOutput,
    BoundingBox3D,
)
from morphomesh.visual_critic import (
    PurePythonBVHTree,
    point_to_triangle_distance_eberly,
    ray_triangle_intersection_moller_trumbore,
    triangle_triangle_intersection_moller,
    compute_mesh_signed_volume,
    compute_bounding_slice_volume,
    compute_mesh_dihedral_creases,
    evaluate_mesh_penetration,
    evaluate_hair_grooming_intersections,
    evaluate_body_proportions,
    evaluate_rig_skinning_deformation,
    run_visual_critique,
    create_penetration_fixture,
    create_proportion_fixture,
    create_skinning_fixture,
    create_grooming_fixture,
    run_defect_detection_benchmark,
    benchmark_defect_detection,
    make_procedural_cylinder,
)
from morphomesh.blender_bridge import BlenderBridge


# ==============================================================================
# 1. MODELS AND SCHEMAS TEST CLASS
# ==============================================================================

class TestVisualCriticModelsAndSchemas:
    """Tests Pydantic v2 models, enumerations, case normalizations, and alias resolvers."""

    def test_defect_severity_enum_and_normalization(self):
        """Verifies DefectSeverity ranking, case-insensitivity, and legacy token aliases."""
        assert DefectSeverity.CRITICAL == "CRITICAL"
        assert DefectSeverity.MAJOR == "MAJOR"
        assert DefectSeverity.MINOR == "MINOR"
        assert DefectSeverity.INFO == "INFO"

        # Case-insensitivity
        assert DefectSeverity("critical") == DefectSeverity.CRITICAL
        assert DefectSeverity("Major") == DefectSeverity.MAJOR
        assert DefectSeverity("minor") == DefectSeverity.MINOR

        # Legacy aliases mapping
        assert DefectSeverity("HIGH") == DefectSeverity.CRITICAL
        assert DefectSeverity("high") == DefectSeverity.CRITICAL
        assert DefectSeverity("MEDIUM") == DefectSeverity.MAJOR
        assert DefectSeverity("LOW") == DefectSeverity.MINOR
        assert DefectSeverity("ERROR") == DefectSeverity.CRITICAL
        assert DefectSeverity("WARNING") == DefectSeverity.MAJOR
        assert DefectSeverity("NOTICE") == DefectSeverity.INFO

    def test_defect_category_enum_and_normalization(self):
        """Verifies DefectCategory classification, case-insensitivity, and alias mappings."""
        assert DefectCategory.PENETRATION == "PENETRATION"
        assert DefectCategory.PROPORTION == "PROPORTION"
        assert DefectCategory.SKINNING_PINCH == "SKINNING_PINCH"
        assert DefectCategory.GROOMING_COLLISION == "GROOMING_COLLISION"

        # Aliases mapping
        assert DefectCategory("CLIPPING") == DefectCategory.PENETRATION
        assert DefectCategory("clipping") == DefectCategory.PENETRATION
        assert DefectCategory("MESH_PENETRATION") == DefectCategory.PENETRATION
        assert DefectCategory("PROPORTION_DEVIATION") == DefectCategory.PROPORTION
        assert DefectCategory("BODY_PROPORTION") == DefectCategory.PROPORTION
        assert DefectCategory("SKINNING_ARTIFACT") == DefectCategory.SKINNING_PINCH
        assert DefectCategory("RIG_PINCH") == DefectCategory.SKINNING_PINCH
        assert DefectCategory("GROOMING_INTERSECTION") == DefectCategory.GROOMING_COLLISION
        assert DefectCategory("HAIR_CLIPPING") == DefectCategory.GROOMING_COLLISION

    def test_actionable_recommendation_model(self):
        """Verifies ActionableRecommendation structure, auto-IDs, and validators."""
        rec = ActionableRecommendation(
            action="APPLY_SHRINKWRAP",
            category="CLIPPING",
            target_objects=["Dress_Mesh"],
            suggested_modifier="Shrinkwrap",
            parameters={"offset": 0.002, "target": "Body_Mesh"},
            priority="HIGH",
        )
        assert rec.action_id.startswith("REC-")
        assert rec.category == DefectCategory.PENETRATION
        assert rec.priority == DefectSeverity.CRITICAL
        assert rec.parameters["offset"] == 0.002
        assert "Dress_Mesh" in rec.target_objects
        assert rec.description == "APPLY_SHRINKWRAP"

    def test_defect_item_model(self):
        """Verifies DefectItem creation, location coordinates, aliases, and Pydantic serialization."""
        d = DefectItem(
            category="PROPORTION_DEVIATION",
            severity="WARNING",
            object_name="Heroine_Body",
            description="Head ratio deviates from target heroine preset.",
            location=[0.0, 0.0, 1.65],
            confidence=0.98,
            metrics={"head_ratio": 5.2, "target_preset": "stylized_heroine"},
        )
        assert d.defect_id.startswith("DEF-")
        assert d.category == DefectCategory.PROPORTION
        assert d.severity == DefectSeverity.MAJOR
        assert "Heroine_Body" in d.affected_objects
        assert d.location == [0.0, 0.0, 1.65]

        # Serialization to dict
        dumped = d.model_dump()
        assert dumped["category"] == DefectCategory.PROPORTION
        assert dumped["severity"] == DefectSeverity.MAJOR
        assert dumped["metrics"]["head_ratio"] == 5.2

    def test_visual_critique_input_validation_and_aliases(self):
        """Verifies VisualCritiqueInput defaults and backward-compatible alias resolution."""
        inp = VisualCritiqueInput()
        assert inp.target_object == "Human_Base_Mesh"
        assert inp.clearance_tolerance == 0.0005
        assert inp.target_preset == "stylized_heroine"
        assert inp.evaluate_penetration is True

        # Alias resolution
        inp2 = VisualCritiqueInput(
            char_name="Yu_Nian_An",
            clearance_threshold=0.0012,
            viewpoints=["front", "back"],
        )
        assert inp2.character_name == "Yu_Nian_An"
        assert inp2.clearance_tolerance == 0.0012
        assert inp2.camera_angles == ["front", "back"]

    def test_visual_critique_output_model(self):
        """Verifies VisualCritiqueOutput pass/fail logic, quality score, and defect sync."""
        d1 = DefectItem(category="CLIPPING", severity="MINOR", description="Micro clearance breach.")
        out = VisualCritiqueOutput(
            status="success",
            passed=True,
            quality_score=97.0,
            defects=[d1],
            recommendations=["Keep clearance."],
            inspected_objects=["Body", "Dress"],
        )
        assert out.passed is True
        assert out.defect_count == 1
        assert out.quality_score == 97.0

        # Auto sync defect count
        out2 = VisualCritiqueOutput(defects=[d1, d1])
        assert out2.defect_count == 2


# ==============================================================================
# 2. PURE PYTHON BVH TREE & GEOMETRIC SOLVER TEST CLASS
# ==============================================================================

class TestPurePythonBVHTree:
    """Tests offline pure-Python spatial index and foundational 3D geometric solvers."""

    def test_point_to_triangle_distance_eberly_regions(self):
        """Tests David Eberly's point-triangle distance across Voronoi interior and edge regions."""
        v0 = (0.0, 0.0, 0.0)
        v1 = (1.0, 0.0, 0.0)
        v2 = (0.0, 1.0, 0.0)

        # Region 0: Point directly above triangle center
        p_interior = (0.2, 0.2, 1.5)
        cp, norm, dist = point_to_triangle_distance_eberly(p_interior, v0, v1, v2)
        assert math.isclose(dist, 1.5, abs_tol=1e-6)
        assert math.isclose(cp[0], 0.2, abs_tol=1e-6)
        assert math.isclose(cp[1], 0.2, abs_tol=1e-6)
        assert math.isclose(cp[2], 0.0, abs_tol=1e-6)
        assert math.isclose(norm[2], 1.0, abs_tol=1e-6)

        # Region 4: Point closest to vertex v0 (origin)
        p_v0 = (-1.0, -1.0, 0.0)
        cp, _, dist = point_to_triangle_distance_eberly(p_v0, v0, v1, v2)
        assert math.isclose(dist, math.sqrt(2.0), abs_tol=1e-6)
        assert math.isclose(cp[0], 0.0, abs_tol=1e-6)
        assert math.isclose(cp[1], 0.0, abs_tol=1e-6)

        # Region 5: Point closest to edge v0 -> v1 (X-axis)
        p_edge = (0.5, -0.5, 0.0)
        cp, _, dist = point_to_triangle_distance_eberly(p_edge, v0, v1, v2)
        assert math.isclose(dist, 0.5, abs_tol=1e-6)
        assert math.isclose(cp[0], 0.5, abs_tol=1e-6)
        assert math.isclose(cp[1], 0.0, abs_tol=1e-6)

    def test_ray_triangle_intersection_moller_trumbore(self):
        """Tests Moller-Trumbore raycast hitting, missing, and backwards rays."""
        v0 = (-1.0, -1.0, 0.0)
        v1 = (1.0, -1.0, 0.0)
        v2 = (0.0, 1.0, 0.0)

        # Direct hit
        hit = ray_triangle_intersection_moller_trumbore(
            origin=(0.0, -0.2, 5.0),
            direction=(0.0, 0.0, -1.0),
            v0=v0, v1=v1, v2=v2,
        )
        assert hit is not None
        hit_pt, norm, dist = hit
        assert math.isclose(dist, 5.0, abs_tol=1e-6)
        assert math.isclose(hit_pt[2], 0.0, abs_tol=1e-6)

        # Ray missing triangle
        miss = ray_triangle_intersection_moller_trumbore(
            origin=(5.0, 5.0, 5.0),
            direction=(0.0, 0.0, -1.0),
            v0=v0, v1=v1, v2=v2,
        )
        assert miss is None

        # Ray pointing in opposite direction
        away = ray_triangle_intersection_moller_trumbore(
            origin=(0.0, 0.0, 5.0),
            direction=(0.0, 0.0, 1.0),
            v0=v0, v1=v1, v2=v2,
        )
        assert away is None

    def test_triangle_triangle_intersection_moller(self):
        """Tests Tomas Moller triangle-triangle intersection algorithm."""
        # Two piercing perpendicular triangles
        t1_v0, t1_v1, t1_v2 = (-1.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 2.0)
        t2_v0, t2_v1, t2_v2 = (0.0, -1.0, 1.0), (0.0, 1.0, 1.0), (0.0, 0.0, 3.0)
        assert triangle_triangle_intersection_moller(t1_v0, t1_v1, t1_v2, t2_v0, t2_v1, t2_v2) is True

        # Separated parallel triangles
        t3_v0, t3_v1, t3_v2 = (-1.0, 0.0, 5.0), (1.0, 0.0, 5.0), (0.0, 0.0, 7.0)
        assert triangle_triangle_intersection_moller(t1_v0, t1_v1, t1_v2, t3_v0, t3_v1, t3_v2) is False

    def test_pure_python_bvh_nearest_query_on_cube(self):
        """Tests PurePythonBVHTree on unit cube geometry."""
        # 8 vertices of unit cube [-1, 1]
        cube_verts = [
            (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
            (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1),
        ]
        cube_faces = [
            (0, 1, 2, 3), (4, 5, 6, 7),
            (0, 1, 5, 4), (2, 3, 7, 6),
            (0, 3, 7, 4), (1, 2, 6, 5),
        ]
        bvh = PurePythonBVHTree.FromPolygons(cube_verts, cube_faces)

        # Query point above top face: (0.2, 0.3, 3.0)
        loc, norm, idx, dist = bvh.find_nearest((0.2, 0.3, 3.0))
        assert loc is not None
        assert math.isclose(dist, 2.0, abs_tol=1e-5)
        assert math.isclose(loc[0], 0.2, abs_tol=1e-5)
        assert math.isclose(loc[1], 0.3, abs_tol=1e-5)
        assert math.isclose(loc[2], 1.0, abs_tol=1e-5)
        assert math.isclose(norm[2], 1.0, abs_tol=1e-5)

    def test_pure_python_bvh_overlap_cubes(self):
        """Tests PurePythonBVHTree overlap between overlapping and separated cubes."""
        cube_verts_1 = [
            (0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
            (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1),
        ]
        cube_faces = [
            (0, 1, 2, 3), (4, 5, 6, 7),
            (0, 1, 5, 4), (2, 3, 7, 6),
            (0, 3, 7, 4), (1, 2, 6, 5),
        ]
        bvh1 = PurePythonBVHTree.FromPolygons(cube_verts_1, cube_faces)

        # Overlapping cube shifted by 0.5 in X and Y
        cube_verts_2 = [(v[0] + 0.5, v[1] + 0.5, v[2]) for v in cube_verts_1]
        bvh2 = PurePythonBVHTree.FromPolygons(cube_verts_2, cube_faces)
        overlaps = bvh1.overlap(bvh2)
        assert len(overlaps) > 0

        # Disjoint separated cube shifted by 10 in X
        cube_verts_3 = [(v[0] + 10.0, v[1], v[2]) for v in cube_verts_1]
        bvh3 = PurePythonBVHTree.FromPolygons(cube_verts_3, cube_faces)
        assert len(bvh1.overlap(bvh3)) == 0


# ==============================================================================
# 3. PROCEDURAL DEFECT INJECTION FIXTURES TEST CLASS
# ==============================================================================

class TestProceduralDefectInjectionFixtures:
    """Tests the 4 procedural defect injection fixtures against clean baselines."""

    def test_fixture_1_garment_penetration_clean_and_defective(self):
        """Tests garment cylinder over body cylinder with clean +20mm clearance vs -15mm penetration."""
        # Clean Baseline
        b_clean, g_clean = create_penetration_fixture(defective=False)
        defs_clean = evaluate_mesh_penetration("Body", ["Skirt"], body_geo=b_clean, garment_geos={"Skirt": g_clean})
        assert len(defs_clean) == 0

        # Defective: front sector pushed inward by 35mm (penetrates body by 15mm)
        b_def, g_def = create_penetration_fixture(defective=True)
        defs_def = evaluate_mesh_penetration("Body", ["Skirt"], body_geo=b_def, garment_geos={"Skirt": g_def})
        assert len(defs_def) > 0
        crit_pen = next(d for d in defs_def if d.category == DefectCategory.PENETRATION)
        assert crit_pen.severity == DefectSeverity.CRITICAL
        assert crit_pen.penetration_depth_mm is not None
        assert crit_pen.penetration_depth_mm >= 14.0
        assert crit_pen.recommendation is not None
        assert "Shrinkwrap" in crit_pen.recommendation.suggested_modifier

    def test_fixture_2_proportion_skew_clean_and_defective(self):
        """Tests anthropometric heroine proportions (7.41) vs giant (10.0) and chibi (2.33)."""
        # Clean Baseline
        v_clean, f_clean, lm_clean = create_proportion_fixture("clean")
        metrics_clean, defs_clean = evaluate_body_proportions(
            "Body", target_preset="stylized_heroine", landmarks=lm_clean, body_geo=(v_clean, f_clean)
        )
        assert len(defs_clean) == 0
        assert math.isclose(metrics_clean.head_ratio, 7.41, abs_tol=0.05)

        # Defective Giant (10.0 heads -> head too small)
        v_giant, f_giant, lm_giant = create_proportion_fixture("giant")
        metrics_giant, defs_giant = evaluate_body_proportions(
            "Body", target_preset="stylized_heroine", landmarks=lm_giant, body_geo=(v_giant, f_giant)
        )
        assert len(defs_giant) > 0
        giant_def = next(d for d in defs_giant if d.defect_id == "PROP_HEAD_TOO_SMALL")
        assert giant_def.severity == DefectSeverity.CRITICAL
        assert math.isclose(metrics_giant.head_ratio, 10.0, abs_tol=0.05)

        # Defective Chibi (2.33 heads -> head too large for heroine preset)
        v_chibi, f_chibi, lm_chibi = create_proportion_fixture("chibi")
        metrics_chibi, defs_chibi = evaluate_body_proportions(
            "Body", target_preset="stylized_heroine", landmarks=lm_chibi, body_geo=(v_chibi, f_chibi)
        )
        assert len(defs_chibi) > 0
        chibi_def = next(d for d in defs_chibi if d.defect_id == "PROP_HEAD_TOO_LARGE")
        assert chibi_def.severity == DefectSeverity.CRITICAL
        assert math.isclose(metrics_chibi.head_ratio, 2.33, abs_tol=0.05)

    def test_fixture_3_joint_skinning_collapse_clean_and_defective(self):
        """Tests 90-degree bent limb with smooth volume conservation vs candy-wrapper collapse."""
        # Clean Baseline
        r_clean, p_clean, f_s, j_s = create_skinning_fixture(defective=False)
        res_clean, defs_clean = evaluate_rig_skinning_deformation(r_clean, p_clean, f_s, j_s, "Arm")
        assert len(defs_clean) == 0
        assert 0.80 <= res_clean[0].volume_ratio <= 1.25
        assert res_clean[0].is_volume_conserved
        assert res_clean[0].is_crease_free

        # Defective Candy-wrapper collapse & acute dihedral crease
        r_def, p_def, _, _ = create_skinning_fixture(defective=True)
        res_def, defs_def = evaluate_rig_skinning_deformation(r_def, p_def, f_s, j_s, "Arm")
        assert len(defs_def) > 0
        assert res_def[0].volume_ratio < 0.75
        assert any(d.defect_type == "SKINNING_VOLUME_COLLAPSE" for d in defs_def)
        assert any(d.defect_type == "SKINNING_ACUTE_CREASE" for d in defs_def)

    def test_fixture_4_hair_root_clipping_clean_and_defective(self):
        """Tests hair curve roots at +2mm surface clearance vs -40mm submerged inside cranium."""
        # Clean Baseline
        b_clean, hair_clean = create_grooming_fixture(defective=False)
        defs_clean = evaluate_hair_grooming_intersections(["Hair_Curves"], "Scalp", hair_splines=hair_clean, body_geo=b_clean)
        assert len(defs_clean) == 0

        # Defective: 15 submerged roots
        b_def, hair_def = create_grooming_fixture(defective=True)
        defs_def = evaluate_hair_grooming_intersections(["Hair_Curves"], "Scalp", hair_splines=hair_def, body_geo=b_def)
        assert len(defs_def) > 0
        root_def = next(d for d in defs_def if d.defect_type == "GROOMING_ROOT_SUBMERGED")
        assert root_def.severity == DefectSeverity.CRITICAL
        assert root_def.metrics["submerged_roots_count"] == 15
        assert root_def.recommendation is not None


# ==============================================================================
# 4. BENCHMARK ACCURACY TEST CLASS
# ==============================================================================

class TestDefectDetectionBenchmarkAndAccuracy:
    """Verifies that the automated critic achieves >95% accuracy and 0% false positives."""

    def test_benchmark_accuracy_exceeds_95_percent(self):
        """Asserts benchmark evaluates all 9 states with >= 95% accuracy and 0% FPR."""
        results = run_defect_detection_benchmark()
        assert results["tests_run"] == 9
        assert results["total_states"] == 9
        assert results["true_positives"] == 5
        assert results["true_negatives"] == 4
        assert results["false_positives"] == 0
        assert results["false_negatives"] == 0
        assert results["correct_classifications"] == 9
        assert results["clean_states_tested"] == 4
        assert results["defective_states_tested"] == 5
        assert results["accuracy"] >= 95.0
        assert results["accuracy"] == 100.0
        assert results["accuracy_percentage"] == 100.0
        assert results["accuracy_ratio"] == 1.0
        assert results["false_positive_rate"] == 0.0
        assert results["false_positive_rate_ratio"] == 0.0

    def test_benchmark_defect_detection_canonical_export(self):
        """Verifies exported benchmark_defect_detection function and audit assertion criteria."""
        stats = benchmark_defect_detection()
        # Authoritative audit criteria check
        assert stats["accuracy"] >= 0.95
        assert stats["accuracy"] >= 95.0
        assert stats["false_positive_rate"] == 0.0
        # Field completeness
        assert stats["total_states"] == 9
        assert stats["correct_classifications"] == 9
        assert stats["clean_states_tested"] == 4
        assert stats["defective_states_tested"] == 5
        assert stats["tests_run"] == 9
        assert stats["accuracy_ratio"] == 1.0

    def test_benchmark_functions_parity(self):
        """Verifies run_defect_detection_benchmark and benchmark_defect_detection return identical results."""
        res1 = run_defect_detection_benchmark()
        res2 = benchmark_defect_detection()
        assert res1 == res2

    def test_visual_critic_module_all_exports(self):
        """Verifies __all__ exports both benchmark functions and core primitives."""
        import morphomesh.visual_critic as vc
        assert hasattr(vc, "__all__")
        assert "benchmark_defect_detection" in vc.__all__
        assert "run_defect_detection_benchmark" in vc.__all__
        assert "evaluate_mesh_penetration" in vc.__all__
        assert "triangle_triangle_intersection_moller" in vc.__all__
        assert "compute_mesh_signed_volume" in vc.__all__

    def test_exposed_anatomy_skin_burst_zero_false_positive(self):
        """Verifies that exposed anatomy outside an open garment produces ZERO skin burst defects."""
        b_verts, b_faces = make_procedural_cylinder(radius=0.20, height=1.0, num_rings=20, num_segments=24, center_z=0.0)
        # Flare exposed shoulders above neckline z=0.20
        for i, v in enumerate(b_verts):
            if v[2] > 0.20:
                b_verts[i][0] *= 1.25
                b_verts[i][1] *= 1.25
        g_verts, g_faces = make_procedural_cylinder(radius=0.22, height=0.7, num_rings=10, num_segments=24, center_z=-0.15)
        defs = evaluate_mesh_penetration("Body", ["Dress"], body_geo=(b_verts, b_faces), garment_geos={"Dress": (g_verts, g_faces)})
        bursts = [d for d in defs if d.defect_type == "SKIN_BURST"]
        assert len(bursts) == 0, f"Exposed shoulders must not trigger skin burst! Found: {bursts}"
        assert len(defs) == 0

    def test_authentic_skin_burst_detection(self):
        """Verifies that genuine skin burst (body piercing through garment) is correctly detected."""
        b_verts, b_faces = make_procedural_cylinder(radius=0.20, height=1.0, num_rings=20, num_segments=24, center_z=0.0)
        # Authentic burst: covered region at z=0.0 penetrates outward through garment R=0.22
        for i, v in enumerate(b_verts):
            if abs(v[2]) < 0.05:
                b_verts[i][0] *= 1.25
                b_verts[i][1] *= 1.25
        g_verts, g_faces = make_procedural_cylinder(radius=0.22, height=0.7, num_rings=10, num_segments=24, center_z=-0.15)
        defs = evaluate_mesh_penetration("Body", ["Dress"], body_geo=(b_verts, b_faces), garment_geos={"Dress": (g_verts, g_faces)})
        bursts = [d for d in defs if d.defect_type == "SKIN_BURST"]
        assert len(bursts) >= 1
        assert bursts[0].severity == DefectSeverity.CRITICAL

    def test_shrinkwrap_recommendation_exact_formula_and_smoothing(self):
        """Verifies Shrinkwrap modifier recommendation formula d_rec = 1.25 * d_pen + 1mm and weight smoothing."""
        b_def, g_def = create_penetration_fixture(defective=True)
        defs = evaluate_mesh_penetration("Body", ["Skirt"], body_geo=b_def, garment_geos={"Skirt": g_def})
        assert len(defs) >= 1
        pen = defs[0]
        assert pen.recommendation is not None
        rec = pen.recommendation
        assert rec.action == "APPLY_SHRINKWRAP_CLEARANCE"
        assert rec.suggested_modifier == "Shrinkwrap"
        expected_offset_m = round(1.25 * (pen.penetration_depth_mm / 1000.0) + 0.001, 4)
        assert rec.parameters["offset"] == expected_offset_m
        assert rec.parameters["smooth_weights"] is True
        assert "Laplacian smoothing" in rec.guidance or "smoothing" in rec.guidance

    def test_hair_grooming_comb_brush_recommendation(self):
        """Verifies hair grooming CURVE_SCULPT_COMB_DEFLECTION recommendations with 2.0mm collision clearance."""
        b_g_def, h_g_def = create_grooming_fixture(defective=True)
        defs = evaluate_hair_grooming_intersections(["Hair_Curves"], "Scalp", hair_splines=h_g_def, body_geo=b_g_def)
        assert len(defs) >= 1
        # Check that shaft collision prescribes CURVE_SCULPT_COMB_DEFLECTION with 2.0mm clearance
        shaft_defs = [d for d in defs if d.defect_type == "GROOMING_BODY_COLLISION"]
        assert len(shaft_defs) >= 1
        shaft_rec = shaft_defs[0].recommendation
        assert shaft_rec is not None
        assert shaft_rec.action == "CURVE_SCULPT_COMB_DEFLECTION"
        assert shaft_rec.parameters["collision_distance_mm"] == 2.0
        assert "Comb Brush" in shaft_rec.guidance

    def test_coplanar_triangle_triangle_intersection(self):
        """Verifies authentic 2D coplanar triangle-triangle intersection testing."""
        t1 = ((0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.0, 2.0, 0.0))
        # Overlapping coplanar
        t2_overlap = ((0.5, 0.5, 0.0), (2.5, 0.5, 0.0), (0.5, 2.5, 0.0))
        assert triangle_triangle_intersection_moller(*t1, *t2_overlap) is True
        # Contained coplanar
        t2_contained = ((0.2, 0.2, 0.0), (0.6, 0.2, 0.0), (0.2, 0.6, 0.0))
        assert triangle_triangle_intersection_moller(*t1, *t2_contained) is True
        # Disjoint coplanar
        t2_disjoint = ((5.0, 5.0, 0.0), (7.0, 5.0, 0.0), (5.0, 7.0, 0.0))
        assert triangle_triangle_intersection_moller(*t1, *t2_disjoint) is False
        # Parallel separated
        t2_parallel = ((0.0, 0.0, 1.0), (2.0, 0.0, 1.0), (0.0, 2.0, 1.0))
        assert triangle_triangle_intersection_moller(*t1, *t2_parallel) is False

    def test_quad_mesh_signed_volume_exact(self):
        """Verifies divergence theorem signed volume integration for quad mesh."""
        cube_verts = [(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1), (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]
        cube_faces_quad = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (0, 4, 7, 3), (1, 2, 6, 5)]
        vol = compute_mesh_signed_volume(cube_verts, cube_faces_quad)
        assert math.isclose(vol, 8.0, abs_tol=1e-6)


# ==============================================================================
# 5. BLENDER BRIDGE & CRITIQUE INTEGRATION TEST CLASS
# ==============================================================================

class TestBlenderBridgeAndCriticIntegration:
    """Tests client-side BlenderBridge critique dispatch and offline execution."""

    def test_run_visual_critique_offline_execution(self):
        """Verifies master run_visual_critique executes cleanly in offline test environments."""
        inp = VisualCritiqueInput(
            target_object="Human_Base_Mesh",
            target_preset="stylized_heroine",
        )
        out = run_visual_critique(inp)
        assert isinstance(out, VisualCritiqueOutput)
        assert out.status == "success"
        assert out.passed is True
        assert out.quality_score == 100.0
        assert out.defect_count == 0
        assert len(out.recommendations) >= 1

    def test_run_visual_critique_with_kwargs(self):
        """Verifies run_visual_critique accepts direct keyword arguments."""
        out = run_visual_critique(
            char_name="Yu_Nian_An",
            clearance_threshold=0.001,
            target_preset="stylized_heroine",
        )
        assert out.status == "success"
        assert out.passed is True
        assert out.scene_stats.get("target_object") == "Yu_Nian_An_Base_Mesh"

    def test_blender_bridge_critique_visual_quality_params_and_call(self):
        """Verifies BlenderBridge.critique_visual_quality parameter packing and forwarding."""
        bridge = BlenderBridge(port=9999)
        # Mock execute to intercept outgoing parameters
        captured = {}
        def mock_execute(method, params, timeout=120.0):
            captured["method"] = method
            captured["params"] = params
            return {"status": "success", "method": method, "params": params, "defects": []}

        bridge.execute = mock_execute
        res = bridge.critique_visual_quality(
            character_name="Yu_Nian_An",
            target_preset="stylized_heroine",
            clearance_threshold=0.0008,
            camera_angles=["front", "side", "three_quarter"],
        )

        assert captured["method"] == "morphomesh.critique_visual_quality"
        assert captured["params"]["character_name"] == "Yu_Nian_An"
        assert captured["params"]["target_preset"] == "stylized_heroine"
        assert captured["params"]["clearance_tolerance"] == 0.0008
        assert captured["params"]["camera_angles"] == ["front", "side", "three_quarter"]
        assert res["status"] == "success"
