"""
Adversarial Stress Test Suite: Milestone 3 Procedural Benchmark, Anthropometry & Skinning Fuzzer.

Challenger M3_2 Test Suite.
Tests:
1. Procedural Defect Benchmark Verification & Sensitivity Margins:
   - Evaluates benchmark accuracy (>= 95%, target 100%) and FPR (0.0%).
   - Detects missing symbol benchmark_defect_detection vs run_defect_detection_benchmark.
   - Perturbed variations of all 4 defect fixtures (penetration, proportions, skinning, hair).
2. Anthropometric Proportion Fuzzing:
   - Transition points across presets (7.0, 8.0, 6.5, 5.0 heads).
   - Extreme proportions (giant 15.0 heads, dwarf 1.5 heads).
   - Zero-length limbs, inverted landmarks, degenerate flat meshes.
3. Skinning Volume Conservation & Creasing:
   - Analytical volume validation via divergence theorem on cubes, spheres, cylinders.
   - Acute dihedral creasing on sharp folds (cos theta < -0.85, fold angle < 30 deg) vs obtuse folds.
   - Boundary conditions (non-manifold edges, single face edges).
4. Pydantic v2 Serialization Round-Trip:
   - Full JSON serialization and deserialization of VisualCritiqueOutput.
   - Schema robustness under alias mappings and extra ignored fields.
"""

from __future__ import annotations

import json
import math
from typing import Any, Dict, List, Tuple

import numpy as np
import pytest

from morphomesh.models import (
    ActionableRecommendation,
    BoundingBox3D,
    DefectCategory,
    DefectItem,
    DefectSeverity,
    MultiAngleCaptureFrame,
    VisualCritiqueInput,
    VisualCritiqueOutput,
)
from morphomesh.visual_critic import (
    compute_bounding_slice_volume,
    compute_mesh_dihedral_creases,
    compute_mesh_signed_volume,
    create_grooming_fixture,
    create_penetration_fixture,
    create_proportion_fixture,
    create_skinning_fixture,
    evaluate_body_proportions,
    evaluate_hair_grooming_intersections,
    evaluate_mesh_penetration,
    evaluate_rig_skinning_deformation,
    make_procedural_cylinder,
    run_defect_detection_benchmark,
    run_visual_critique,
)


# ==============================================================================
# SECTION 1: PROCEDURAL DEFECT BENCHMARK VERIFICATION & SENSITIVITY MARGINS
# ==============================================================================

class TestProceduralDefectBenchmarkVerification:
    """Verifies defect benchmark execution, accuracy, false positive rate, and sensitivity."""

    def test_benchmark_defect_detection_symbol_and_metrics(self):
        """
        Empirically verifies benchmark defect detection.
        Checks for benchmark_defect_detection symbol vs run_defect_detection_benchmark.
        Asserts accuracy >= 95% (target 100%) and false positive rate == 0.0%.
        """
        import morphomesh.visual_critic as vc_mod

        # Empirical Check: Did the worker expose benchmark_defect_detection?
        has_symbol = hasattr(vc_mod, "benchmark_defect_detection")
        bench_func = getattr(vc_mod, "benchmark_defect_detection", getattr(vc_mod, "run_defect_detection_benchmark", None))
        assert bench_func is not None, "Neither benchmark_defect_detection nor run_defect_detection_benchmark found!"

        results = bench_func()
        assert isinstance(results, dict)
        assert results["tests_run"] == 9
        assert results["true_positives"] == 5
        assert results["true_negatives"] == 4
        assert results["false_positives"] == 0
        assert results["false_negatives"] == 0

        # Strict acceptance criteria: accuracy >= 95.0% and FPR == 0.0%
        assert results["accuracy"] >= 95.0, f"Accuracy {results['accuracy']}% below 95% threshold"
        assert results["accuracy"] == 100.0, "Target accuracy is 100.0%"
        assert results["false_positive_rate"] == 0.0, f"False positive rate {results['false_positive_rate']}% must be strictly 0.0%"

    def test_garment_penetration_sensitivity_margins(self):
        """
        Stress-tests garment penetration sensitivity around the 0.5mm clearance threshold:
        - Clean +20mm clearance -> 0 defects
        - Sub-threshold inward displacement (+0.1mm clearance) -> 0 defects
        - Tangential contact (0.0mm clearance) -> 0 defects
        - Mild penetration (-0.8mm depth > 0.5mm tolerance) -> detects PENETRATION
        - Severe penetration (-15mm depth) -> detects CRITICAL PENETRATION
        """
        b_verts, b_faces = make_procedural_cylinder(radius=0.20, height=0.60, num_rings=12, num_segments=24)

        # Case A: Clean +20mm clearance
        g_clean, g_faces = make_procedural_cylinder(radius=0.22, height=0.50, num_rings=12, num_segments=24)
        d_clean = evaluate_mesh_penetration("Body", ["Skirt"], clearance_tolerance=0.0005, body_geo=(b_verts, b_faces), garment_geos={"Skirt": (g_clean, g_faces)})
        assert len(d_clean) == 0, "Clean garment must yield 0 defects"

        # Case B: Sub-threshold clearance (+0.1mm)
        g_sub, _ = make_procedural_cylinder(radius=0.2001, height=0.50, num_rings=12, num_segments=24)
        d_sub = evaluate_mesh_penetration("Body", ["Skirt"], clearance_tolerance=0.0005, body_geo=(b_verts, b_faces), garment_geos={"Skirt": (g_sub, g_faces)})
        assert len(d_sub) == 0, "Sub-threshold (+0.1mm) clearance must not trigger false positive"

        # Case C: Tangential coplanar contact (0.0mm) -> detects surface FACE_OVERLAP (Z-fighting prevention)
        g_tang, _ = make_procedural_cylinder(radius=0.2000, height=0.50, num_rings=12, num_segments=24)
        d_tang = evaluate_mesh_penetration("Body", ["Skirt"], clearance_tolerance=0.0005, body_geo=(b_verts, b_faces), garment_geos={"Skirt": (g_tang, g_faces)})
        assert len(d_tang) == 1, "Tangential coplanar contact must detect 1 FACE_OVERLAP defect"
        assert d_tang[0].defect_type == "FACE_OVERLAP"
        assert d_tang[0].severity == DefectSeverity.MINOR

        # Case D: Mild penetration (-0.8mm > 0.5mm threshold)
        g_mild, _ = make_procedural_cylinder(radius=0.205, height=0.50, num_rings=12, num_segments=24)
        for i, v in enumerate(g_mild):
            if abs(math.atan2(v[1], v[0])) <= math.pi / 4.0 and abs(v[2]) <= 0.15:
                g_mild[i][0] *= (0.1992 / 0.205)  # R=0.1992m penetrates by 0.8mm
                g_mild[i][1] *= (0.1992 / 0.205)
        d_mild = evaluate_mesh_penetration("Body", ["Skirt"], clearance_tolerance=0.0005, body_geo=(b_verts, b_faces), garment_geos={"Skirt": (g_mild, g_faces)})
        assert len(d_mild) > 0, "Mild penetration of 0.8mm must be detected"
        assert any(d.category == DefectCategory.PENETRATION for d in d_mild)

        # Case E: Severe penetration (-15mm)
        b_def, g_def = create_penetration_fixture(defective=True)
        d_sev = evaluate_mesh_penetration("Body", ["Skirt"], body_geo=b_def, garment_geos={"Skirt": g_def})
        assert len(d_sev) > 0
        pen_item = next(d for d in d_sev if d.category == DefectCategory.PENETRATION)
        assert pen_item.severity == DefectSeverity.CRITICAL
        assert pen_item.penetration_depth_mm >= 14.0
        assert pen_item.recommendation is not None
        assert "Shrinkwrap" in pen_item.recommendation.suggested_modifier

    def test_proportion_skew_sensitivity_margins(self):
        """
        Stress-tests anthropometric proportion analysis around threshold boundaries:
        Preset 'stylized_heroine': valid range is [6.0, 7.6] heads.
        - Nominal 7.41 heads -> Valid (0 defects)
        - 7.55 heads (sub-boundary) -> Valid (0 defects)
        - 7.65 heads (over-boundary) -> Invalid (PROP_HEAD_TOO_SMALL)
        - 6.05 heads (sub-boundary) -> Valid (0 defects)
        - 5.95 heads (under-boundary) -> Invalid (PROP_HEAD_TOO_LARGE)
        """
        H = 1.65
        v, f = make_procedural_cylinder(radius=0.15, height=H, num_rings=8, num_segments=16, center_z=H / 2.0)

        def _evaluate_at_ratio(r: float) -> Tuple[Any, List[DefectItem]]:
            h_head = H / r
            lm = {
                "head_top": (0.0, 0.0, H),
                "chin": (0.0, 0.0, H - h_head),
                "shoulder_L": (-0.175, 0.0, 1.35),
                "shoulder_R": (0.175, 0.0, 1.35),
                "elbow_L": (-0.45, 0.0, 1.35),
                "elbow_R": (0.45, 0.0, 1.35),
                "wrist_L": (-0.70, 0.0, 1.35),
                "wrist_R": (0.70, 0.0, 1.35),
                "fingers_L": (-0.81, 0.0, 1.35),
                "fingers_R": (0.81, 0.0, 1.35),
            }
            return evaluate_body_proportions("Body", target_preset="stylized_heroine", landmarks=lm, body_geo=(v, f))

        # Nominal 7.41 -> 0 defects
        m_nom, d_nom = _evaluate_at_ratio(7.41)
        assert len(d_nom) == 0
        assert m_nom.is_head_ratio_valid is True

        # 7.55 -> 0 defects
        m_high_ok, d_high_ok = _evaluate_at_ratio(7.55)
        assert len(d_high_ok) == 0
        assert m_high_ok.is_head_ratio_valid is True

        # 7.65 -> invalid (too small head)
        m_high_fail, d_high_fail = _evaluate_at_ratio(7.65)
        assert len(d_high_fail) > 0
        assert any(d.defect_id == "PROP_HEAD_TOO_SMALL" for d in d_high_fail)

        # 6.05 -> 0 defects
        m_low_ok, d_low_ok = _evaluate_at_ratio(6.05)
        assert len(d_low_ok) == 0
        assert m_low_ok.is_head_ratio_valid is True

        # 5.95 -> invalid (too large head)
        m_low_fail, d_low_fail = _evaluate_at_ratio(5.95)
        assert len(d_low_fail) > 0
        assert any(d.defect_id == "PROP_HEAD_TOO_LARGE" for d in d_low_fail)

    def test_skinning_collapse_and_bulge_sensitivity_margins(self):
        """
        Stress-tests joint volume retention and acute creasing:
        - Clean smooth skinning -> volume_ratio ~0.935, 0 creases, conserved
        - Collapsed single joint -> volume_ratio < 0.75, detects collapse & crease
        - Dilated joint bulging (volume_ratio > 1.25) -> detects abnormal bulge
        """
        r_clean, p_clean, f_s, j_s = create_skinning_fixture(defective=False)

        # Clean baseline
        res_clean, defs_clean = evaluate_rig_skinning_deformation(r_clean, p_clean, f_s, j_s, "Arm")
        assert len(defs_clean) == 0
        assert 0.80 <= res_clean[0].volume_ratio <= 1.25
        assert res_clean[0].is_volume_conserved is True
        assert res_clean[0].is_crease_free is True

        # Defective collapse
        r_def, p_def, _, _ = create_skinning_fixture(defective=True)
        res_def, defs_def = evaluate_rig_skinning_deformation(r_def, p_def, f_s, j_s, "Arm")
        assert len(defs_def) > 0
        assert res_def[0].volume_ratio < 0.75
        assert any(d.defect_type == "SKINNING_VOLUME_COLLAPSE" for d in defs_def)
        assert any(d.defect_type == "SKINNING_ACUTE_CREASE" for d in defs_def)

        # Abnormal bulge (scaled up 20% -> volume ratio > 1.25)
        p_bulge = np.copy(p_clean) * 1.20
        res_bulge, defs_bulge = evaluate_rig_skinning_deformation(r_clean, p_bulge, f_s, j_s, "Arm")
        assert res_bulge[0].volume_ratio > 1.25
        assert any(d.defect_type == "SKINNING_ABNORMAL_BULGE" for d in defs_bulge)

    def test_hair_grooming_submergence_and_floating_sensitivity(self):
        """
        Stress-tests hair curve root evaluation:
        - Roots at +2.0mm -> Clean (0 defects)
        - Sub-threshold submergence at -0.8mm (within 1.0mm tolerance) -> Clean (0 defects)
        - Submerged roots at -1.5mm (> 1.0mm threshold) -> detects GROOMING_ROOT_SUBMERGED
        - Floating roots at +3.5mm (within 4.0mm tolerance) -> Clean (0 defects)
        - Floating roots at +4.5mm (> 4.0mm threshold) -> detects GROOMING_ROOT_DETACHED
        - Degenerate empty splines -> handles gracefully without unhandled exceptions
        """
        s_verts, s_faces = make_procedural_cylinder(radius=0.10, height=0.15, num_rings=8, num_segments=16, center_z=1.60)

        # Case A: Clean +2.0mm clearance
        hair_clean = {"Hair": [{"points": [(0.102, 0.0, 1.60), (0.13, 0.0, 1.55)], "radii": [0.001, 0.001]}]}
        d_clean = evaluate_hair_grooming_intersections(["Hair"], "Scalp", hair_splines=hair_clean, body_geo=(s_verts, s_faces))
        assert len(d_clean) == 0

        # Case B: Sub-threshold submergence (-0.8mm, within 1mm tolerance)
        hair_sub_ok = {"Hair": [{"points": [(0.0992, 0.0, 1.60), (0.12, 0.0, 1.55)], "radii": [0.001, 0.001]}]}
        d_sub_ok = evaluate_hair_grooming_intersections(["Hair"], "Scalp", hair_splines=hair_sub_ok, body_geo=(s_verts, s_faces))
        assert len(d_sub_ok) == 0, "-0.8mm submergence is within -1.0mm tolerance"

        # Case C: Submerged (-1.5mm > 1.0mm tolerance)
        hair_sub = {"Hair": [{"points": [(0.0985, 0.0, 1.60), (0.12, 0.0, 1.55)], "radii": [0.001, 0.001]}]}
        d_sub = evaluate_hair_grooming_intersections(["Hair"], "Scalp", hair_splines=hair_sub, body_geo=(s_verts, s_faces))
        assert len(d_sub) > 0
        assert any(d.defect_type == "GROOMING_ROOT_SUBMERGED" for d in d_sub)

        # Case D: Floating ok (+3.5mm <= 4.0mm tolerance)
        hair_fl_ok = {"Hair": [{"points": [(0.1035, 0.0, 1.60), (0.13, 0.0, 1.55)], "radii": [0.001, 0.001]}]}
        d_fl_ok = evaluate_hair_grooming_intersections(["Hair"], "Scalp", hair_splines=hair_fl_ok, body_geo=(s_verts, s_faces))
        assert len(d_fl_ok) == 0

        # Case E: Floating detached (+4.5mm > 4.0mm tolerance)
        hair_fl = {"Hair": [{"points": [(0.1045, 0.0, 1.60), (0.13, 0.0, 1.55)], "radii": [0.001, 0.001]}]}
        d_fl = evaluate_hair_grooming_intersections(["Hair"], "Scalp", hair_splines=hair_fl, body_geo=(s_verts, s_faces))
        assert len(d_fl) > 0
        assert any(d.defect_type == "GROOMING_ROOT_DETACHED" for d in d_fl)

        # Case F: Degenerate splines (0 points or 1 point)
        hair_degen = {"Hair": [{"points": [], "radii": []}, {"points": [(0.102, 0.0, 1.60)], "radii": [0.001]}]}
        d_degen = evaluate_hair_grooming_intersections(["Hair"], "Scalp", hair_splines=hair_degen, body_geo=(s_verts, s_faces))
        assert isinstance(d_degen, list)


# ==============================================================================
# SECTION 2: ANTHROPOMETRIC PROPORTION FUZZING & BOUNDARY CONDITIONS
# ==============================================================================

class TestAnthropometricProportionFuzzing:
    """Stress-tests anthropometric proportion evaluator under extreme and degenerate inputs."""

    @pytest.mark.parametrize(
        "preset,ratio,expected_valid",
        [
            ("stylized_heroine", 7.0, True),
            ("stylized_heroine", 6.5, True),
            ("stylized_heroine", 8.0, False),
            ("stylized_heroine", 5.0, False),
            ("chibi_petite", 5.0, True),
            ("chibi_petite", 7.0, False),
            ("chibi_petite", 8.0, False),
            ("chibi_petite", 6.5, False),
        ],
    )
    def test_preset_transition_points(self, preset: str, ratio: float, expected_valid: bool):
        """Fuzzes body proportions at preset transition points (7.0, 8.0, 6.5, 5.0 heads)."""
        H = 1.65
        h_head = H / ratio
        lm = {
            "head_top": (0.0, 0.0, H),
            "chin": (0.0, 0.0, H - h_head),
        }
        v = [(0.0, 0.0, 0.0), (0.0, 0.0, H)]
        metrics, defs = evaluate_body_proportions("Body", target_preset=preset, landmarks=lm, body_geo=(v, []))
        head_defs = [d for d in defs if "HEAD" in d.defect_id]
        if expected_valid:
            assert len(head_defs) == 0, f"Expected ratio {ratio} to be valid for {preset}, but got {head_defs}"
        else:
            assert len(head_defs) > 0, f"Expected ratio {ratio} to be invalid for {preset}"

    def test_realistic_human_boundary_quantization(self):
        """
        Tests realistic_human preset boundaries (7.0 to 8.0 heads).
        Documents quantization sensitivity when H/ratio produces fractional millimeters.
        """
        # For H=1.60: 1.60 / 8.0 = 0.200 exact millimeters
        lm_8_clean = {"head_top": (0.0, 0.0, 1.60), "chin": (0.0, 0.0, 1.40)}
        v_160 = [(0.0, 0.0, 0.0), (0.0, 0.0, 1.60)]
        m8, d8 = evaluate_body_proportions("Body", target_preset="realistic_human", landmarks=lm_8_clean, body_geo=(v_160, []))
        head_defs_8 = [d for d in d8 if "HEAD" in d.defect_id]
        assert len(head_defs_8) == 0, "Exact 8.0 heads with integer millimeters must be valid"
        assert math.isclose(m8.head_ratio, 8.00, abs_tol=1e-2)

        # For H=1.70: 1.70 / 7.0 = 0.242857 -> round(0.243) -> 1.70 / 0.243 = 6.9958 -> round(7.00)
        lm_7_clean = {"head_top": (0.0, 0.0, 1.70), "chin": (0.0, 0.0, 1.457143)}
        v_170 = [(0.0, 0.0, 0.0), (0.0, 0.0, 1.70)]
        m7, d7 = evaluate_body_proportions("Body", target_preset="realistic_human", landmarks=lm_7_clean, body_geo=(v_170, []))
        head_defs_7 = [d for d in d7 if "HEAD" in d.defect_id]
        assert len(head_defs_7) == 0, "Exact 7.0 heads at H=1.70m must be valid"
        assert math.isclose(m7.head_ratio, 7.00, abs_tol=1e-2)

    def test_extreme_proportions_giant_and_dwarf(self):
        """Tests extreme proportions: giant (15.0 heads) and dwarf/chibi (1.5 heads)."""
        H = 1.65
        v = [(0.0, 0.0, 0.0), (0.0, 0.0, H)]

        # Giant (15.0 heads)
        lm_giant = {"head_top": (0.0, 0.0, H), "chin": (0.0, 0.0, H - H / 15.0)}
        m_g, defs_g = evaluate_body_proportions("Body", target_preset="stylized_heroine", landmarks=lm_giant, body_geo=(v, []))
        assert math.isclose(m_g.head_ratio, 15.0, abs_tol=0.1)
        giant_def = next(d for d in defs_g if d.defect_id == "PROP_HEAD_TOO_SMALL")
        assert giant_def.severity == DefectSeverity.CRITICAL

        # Dwarf (1.5 heads)
        lm_dwarf = {"head_top": (0.0, 0.0, H), "chin": (0.0, 0.0, H - H / 1.5)}
        m_d, defs_d = evaluate_body_proportions("Body", target_preset="stylized_heroine", landmarks=lm_dwarf, body_geo=(v, []))
        assert math.isclose(m_d.head_ratio, 1.5, abs_tol=0.1)
        dwarf_def = next(d for d in defs_d if d.defect_id == "PROP_HEAD_TOO_LARGE")
        assert dwarf_def.severity == DefectSeverity.CRITICAL

    def test_zero_length_limbs_fuzzing(self):
        """Tests degenerate zero-length limbs (all arm landmarks collapsed onto a single point)."""
        lm_zero_arm = {
            "head_top": (0.0, 0.0, 1.65),
            "chin": (0.0, 0.0, 1.4273),
            "shoulder_L": (0.0, 0.0, 1.35),
            "shoulder_R": (0.0, 0.0, 1.35),
            "elbow_L": (0.0, 0.0, 1.35),
            "elbow_R": (0.0, 0.0, 1.35),
            "wrist_L": (0.0, 0.0, 1.35),
            "wrist_R": (0.0, 0.0, 1.35),
            "fingers_L": (0.0, 0.0, 1.35),
            "fingers_R": (0.0, 0.0, 1.35),
        }
        v = [(0.0, 0.0, 0.0), (0.0, 0.0, 1.65)]
        metrics, defs = evaluate_body_proportions(landmarks=lm_zero_arm, body_geo=(v, []))

        assert metrics.arm_span == 0.0
        assert metrics.arm_span_ratio == 0.0
        assert metrics.shoulder_breadth == 0.0
        assert any(d.defect_id == "PROP_ARM_SPAN_TOO_SHORT" for d in defs)
        assert any(d.defect_id == "PROP_SHOULDER_TO_HIP_SKEW" for d in defs)

    def test_inverted_landmarks_and_degenerate_bounding_box(self):
        """
        Tests inverted landmarks (chin above head_top) and flat 2D geometry (total_height = 0).
        Verifies division-by-zero protection via max(1e-4, ...).
        """
        # Case A: Inverted chin and head_top
        lm_inverted = {"head_top": (0.0, 0.0, 1.0), "chin": (0.0, 0.0, 1.65)}
        v = [(0.0, 0.0, 0.0), (0.0, 0.0, 1.65)]
        m_inv, d_inv = evaluate_body_proportions(landmarks=lm_inverted, body_geo=(v, []))
        assert m_inv.head_height < 0.0  # Inverted height recorded
        assert any(d.defect_id == "PROP_HEAD_TOO_SMALL" for d in d_inv)

        # Case B: Flat mesh at origin (total_height = 0.0)
        v_flat = [(0.0, 0.0, 0.0), (0.1, 0.1, 0.0), (-0.1, -0.1, 0.0)]
        f_flat = [(0, 1, 2)]
        m_flat, d_flat = evaluate_body_proportions(body_geo=(v_flat, f_flat))
        assert m_flat.total_height == 0.0
        assert len(d_flat) >= 2  # Discovers proportion anomalies without crashing

        # Case C: Empty vertex geometry fallback
        m_empty, d_empty = evaluate_body_proportions(body_geo=([], []))
        assert m_empty.total_height == 1.65
        assert len(d_empty) == 0


# ==============================================================================
# SECTION 3: SKINNING VOLUME CONSERVATION & CREASING
# ==============================================================================

class TestSkinningVolumeConservationAndCreasing:
    """Verifies watertight divergence volume on analytical primitives and dihedral creases."""

    def test_watertight_divergence_volume_analytical_cube(self):
        """
        Tests compute_mesh_signed_volume on analytical cube [-1, 1]^3.
        Side L = 2.0 -> Analytical Volume V = L^3 = 8.0.
        """
        cube_verts = [
            (-1.0, -1.0, -1.0), (1.0, -1.0, -1.0), (1.0, 1.0, -1.0), (-1.0, 1.0, -1.0),
            (-1.0, -1.0, 1.0), (1.0, -1.0, 1.0), (1.0, 1.0, 1.0), (-1.0, 1.0, 1.0),
        ]
        cube_faces = [
            (0, 2, 1), (0, 3, 2),  # Bottom (z = -1)
            (4, 5, 6), (4, 6, 7),  # Top (z = 1)
            (0, 1, 5), (0, 5, 4),  # Front (y = -1)
            (2, 3, 7), (2, 7, 6),  # Back (y = 1)
            (0, 4, 7), (0, 7, 3),  # Left (x = -1)
            (1, 2, 6), (1, 6, 5),  # Right (x = 1)
        ]
        vol = compute_mesh_signed_volume(cube_verts, cube_faces)
        assert math.isclose(vol, 8.0, abs_tol=1e-6), f"Expected 8.0, got {vol}"

    def test_watertight_divergence_volume_analytical_sphere(self):
        """
        Tests compute_mesh_signed_volume on UV sphere with R=1.0.
        Analytical Volume V = 4/3 * pi * R^3 = 4.188790. Discretization error < 0.3%.
        """
        R = 1.0
        num_lat, num_lon = 40, 80
        verts = [(0.0, 0.0, -R)]
        for i in range(1, num_lat):
            phi = -math.pi / 2.0 + math.pi * i / num_lat
            z = R * math.sin(phi)
            r_xy = R * math.cos(phi)
            for j in range(num_lon):
                theta = 2.0 * math.pi * j / num_lon
                verts.append((r_xy * math.cos(theta), r_xy * math.sin(theta), z))
        verts.append((0.0, 0.0, R))
        north_idx = len(verts) - 1

        faces = []
        for j in range(num_lon):
            nj = (j + 1) % num_lon
            faces.append((0, 1 + j, 1 + nj))
        for i in range(num_lat - 2):
            r1 = 1 + i * num_lon
            r2 = 1 + (i + 1) * num_lon
            for j in range(num_lon):
                nj = (j + 1) % num_lon
                faces.append((r1 + j, r2 + j, r2 + nj))
                faces.append((r1 + j, r2 + nj, r1 + nj))
        last_ring = 1 + (num_lat - 2) * num_lon
        for j in range(num_lon):
            nj = (j + 1) % num_lon
            faces.append((north_idx, last_ring + nj, last_ring + j))

        vol = compute_mesh_signed_volume(verts, faces)
        expected = 4.0 / 3.0 * math.pi * (R ** 3)
        err_pct = abs(vol - expected) / expected * 100.0
        assert err_pct < 0.3, f"Sphere volume error {err_pct:.3f}% exceeds 0.3% limit"

    def test_watertight_divergence_volume_analytical_cylinder(self):
        """
        Tests compute_mesh_signed_volume on analytical cylinder R=1.0, H=2.0.
        Analytical Volume V = pi * R^2 * H = 2 * pi = 6.283185. Discretization error < 0.1%.
        """
        R, H, N = 1.0, 2.0, 100
        verts = [(0.0, 0.0, -1.0)]
        for i in range(N):
            th = 2.0 * math.pi * i / N
            verts.append((R * math.cos(th), R * math.sin(th), -1.0))
        verts.append((0.0, 0.0, 1.0))
        for i in range(N):
            th = 2.0 * math.pi * i / N
            verts.append((R * math.cos(th), R * math.sin(th), 1.0))

        faces = []
        for i in range(N):
            ni = (i + 1) % N
            faces.append((0, 1 + ni, 1 + i))
            b1 = 1 + i
            b2 = 1 + ni
            t1 = N + 2 + i
            t2 = N + 2 + ni
            faces.append((b1, b2, t2))
            faces.append((b1, t2, t1))
        top_c = N + 1
        for i in range(N):
            ni = (i + 1) % N
            faces.append((top_c, N + 2 + i, N + 2 + ni))

        vol = compute_mesh_signed_volume(verts, faces)
        expected = math.pi * (R ** 2) * H
        err_pct = abs(vol - expected) / expected * 100.0
        assert err_pct < 0.1, f"Cylinder volume error {err_pct:.3f}% exceeds 0.1% limit"

    @pytest.mark.parametrize("fold_angle_deg", [5.0, 15.0, 25.0, 29.0])
    def test_acute_dihedral_creasing_sharp_folds(self, fold_angle_deg: float):
        """
        Tests acute dihedral creasing on sharp folds: fold_angle < 30 deg -> cos theta < -0.85.
        Must be detected as acute creases.
        """
        gamma = math.radians(fold_angle_deg / 2.0)
        v_edge_a = (0.0, -1.0, 0.0)
        v_edge_b = (0.0, 1.0, 0.0)
        w1 = (math.cos(gamma), 0.0, math.sin(gamma))
        w2 = (math.cos(gamma), 0.0, -math.sin(gamma))

        verts = [v_edge_a, v_edge_b, w1, w2]
        faces = [(0, 1, 2), (1, 0, 3)]

        creases = compute_mesh_dihedral_creases(verts, faces, cos_threshold=-0.85)
        assert len(creases) == 1, f"Fold angle {fold_angle_deg} deg must trigger acute crease"
        c = creases[0]
        assert c["cos_theta"] < -0.85
        assert math.isclose(c["fold_angle_deg"], fold_angle_deg, abs_tol=1e-3)
        assert c["edge"] == (0, 1)

    @pytest.mark.parametrize("fold_angle_deg", [35.0, 45.0, 90.0, 120.0, 180.0])
    def test_obtuse_smooth_folds_no_creases(self, fold_angle_deg: float):
        """
        Tests obtuse smooth folds: fold_angle > 30 deg -> cos theta > -0.85.
        Must NOT be detected as acute creases (0 creases).
        """
        gamma = math.radians(fold_angle_deg / 2.0)
        v_edge_a = (0.0, -1.0, 0.0)
        v_edge_b = (0.0, 1.0, 0.0)
        w1 = (math.cos(gamma), 0.0, math.sin(gamma))
        w2 = (math.cos(gamma), 0.0, -math.sin(gamma))

        verts = [v_edge_a, v_edge_b, w1, w2]
        faces = [(0, 1, 2), (1, 0, 3)]

        creases = compute_mesh_dihedral_creases(verts, faces, cos_threshold=-0.85)
        assert len(creases) == 0, f"Fold angle {fold_angle_deg} deg must NOT trigger acute crease"

    def test_dihedral_creases_non_manifold_and_boundary_edges(self):
        """Tests that single-face boundary edges and non-manifold edges (>2 faces) do not crash."""
        v_edge_a = (0.0, -1.0, 0.0)
        v_edge_b = (0.0, 1.0, 0.0)
        w1 = (1.0, 0.0, 0.0)
        w2 = (-1.0, 0.0, 0.0)
        w3 = (0.0, 0.0, 1.0)

        # 3 faces sharing edge (0, 1) -> non-manifold
        verts = [v_edge_a, v_edge_b, w1, w2, w3]
        faces = [(0, 1, 2), (1, 0, 3), (0, 1, 4)]
        creases = compute_mesh_dihedral_creases(verts, faces, cos_threshold=-0.85)
        # Non-manifold edge has len(f_list) == 3 != 2, safely skipped
        assert isinstance(creases, list)


# ==============================================================================
# SECTION 4: PYDANTIC V2 SERIALIZATION ROUND-TRIP
# ==============================================================================

class TestPydanticV2SerializationRoundTrip:
    """Verifies complete round-trip JSON serialization and deserialization of critique models."""

    def test_visual_critique_output_full_roundtrip(self):
        """
        Validates full round-trip JSON serialization and deserialization of VisualCritiqueOutput
        containing multiple defects across categories, recommendations, BoundingBox3D,
        MultiAngleCaptureFrame, and scene_stats.
        """
        bbox = BoundingBox3D(min_point=[0.0, 0.0, 0.0], max_point=[0.2, 0.3, 0.4], dimensions=[0.2, 0.3, 0.4])

        rec1 = ActionableRecommendation(
            action="APPLY_SHRINKWRAP",
            suggested_modifier="Shrinkwrap",
            parameters={"offset": 0.005, "target": "Body_Mesh"},
            priority=DefectSeverity.CRITICAL,
            target_objects=["Dress_Mesh"],
            description="Apply Shrinkwrap modifier with 5mm offset.",
        )

        d1 = DefectItem(
            defect_id="DEF-PEN-001",
            category=DefectCategory.PENETRATION,
            severity=DefectSeverity.CRITICAL,
            affected_objects=["Dress_Mesh", "Body_Mesh"],
            description="Severe garment penetration detected.",
            confidence=0.98,
            location=[0.1, 0.2, 0.3],
            sample_locations=[[0.1, 0.2, 0.3], [0.11, 0.21, 0.31]],
            bounding_box=bbox,
            penetration_depth_mm=14.5,
            penetration_count=48,
            recommendation=rec1,
        )

        d2 = DefectItem(
            defect_id="DEF-PROP-002",
            category=DefectCategory.PROPORTION,
            severity=DefectSeverity.MAJOR,
            affected_objects=["Body_Mesh"],
            description="Head-to-body ratio skew.",
            confidence=0.95,
            location=[0.0, 0.0, 1.6],
            metrics={"head_ratio": 9.5, "nominal": 6.8},
        )

        d3 = DefectItem(
            defect_id="DEF-SKIN-003",
            category=DefectCategory.SKINNING_PINCH,
            severity=DefectSeverity.MAJOR,
            affected_objects=["Body_Mesh"],
            description="Candy-wrapper volume collapse at elbow.",
            confidence=0.91,
            location=[0.3, 0.0, 1.2],
            metrics={"volume_ratio": 0.72},
        )

        d4 = DefectItem(
            defect_id="DEF-GROOM-004",
            category=DefectCategory.GROOMING_COLLISION,
            severity=DefectSeverity.MINOR,
            affected_objects=["Hair_Curves"],
            description="Floating hair roots.",
            confidence=0.88,
            location=[0.0, 0.0, 1.7],
            metrics={"detached_roots_count": 5},
        )

        frame = MultiAngleCaptureFrame(
            viewpoint="three_quarter",
            image_path="cache/preview_34.png",
            resolution=[1024, 1024],
            shading_mode="SOLID",
            color_type="RANDOM",
            capture_time_seconds=0.085,
            base64_image="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        )

        original_output = VisualCritiqueOutput(
            status="success",
            passed=False,
            quality_score=52.0,
            defect_count=4,
            defects=[d1, d2, d3, d4],
            recommendations=[
                "Apply Shrinkwrap modifier with 5mm offset.",
                "Rescale head geometry to nominal 6.8 heads.",
            ],
            actionable_recommendations=[rec1],
            inspected_objects=["Body_Mesh", "Dress_Mesh", "Hair_Curves"],
            scene_stats={
                "total_vertices": 28450,
                "total_faces": 27900,
                "mesh_count": 3,
                "ratios": {"head_ratio": 9.5, "arm_span_ratio": 0.98},
            },
            evaluated_angles=["front", "side", "three_quarter", "back"],
            capture_previews=[frame],
            execution_time_seconds=0.198,
        )

        # 1. Serialize to JSON
        json_str = original_output.model_dump_json(indent=2)
        assert isinstance(json_str, str)
        assert len(json_str) > 0

        # Verify raw JSON parsing
        raw_dict = json.loads(json_str)
        assert raw_dict["status"] == "success"
        assert raw_dict["passed"] is False
        assert raw_dict["defect_count"] == 4
        assert len(raw_dict["defects"]) == 4

        # 2. Deserialize back from JSON
        restored = VisualCritiqueOutput.model_validate_json(json_str)

        # 3. Assert deep equality
        assert restored.status == original_output.status
        assert restored.passed == original_output.passed
        assert math.isclose(restored.quality_score, original_output.quality_score, abs_tol=1e-5)
        assert restored.defect_count == original_output.defect_count
        assert len(restored.defects) == 4
        assert len(restored.actionable_recommendations) == 1
        assert restored.scene_stats["total_vertices"] == 28450
        assert restored.scene_stats["ratios"]["head_ratio"] == 9.5
        assert restored.capture_previews[0].viewpoint == "three_quarter"

        # Check Defect 1 fields
        r_d1 = restored.defects[0]
        assert r_d1.defect_id == "DEF-PEN-001"
        assert r_d1.category == DefectCategory.PENETRATION
        assert r_d1.severity == DefectSeverity.CRITICAL
        assert r_d1.penetration_depth_mm == 14.5
        assert r_d1.bounding_box is not None
        assert r_d1.bounding_box.dimensions == [0.2, 0.3, 0.4]
        assert isinstance(r_d1.recommendation, ActionableRecommendation)
        assert r_d1.recommendation.action == "APPLY_SHRINKWRAP"

    def test_defect_item_alias_and_normalization_roundtrip(self):
        """Verifies DefectItem field synchronization with legacy aliases and case normalization."""
        # Using legacy aliases 'id' and 'defect_type'
        d = DefectItem(
            id="DEF-ALIAS-1",
            defect_type="CLIPPING",
            severity="warning",
            object_name="Dress",
            description="Legacy alias test",
            location=[0.0, 1.0, 2.0],
            actionable_recommendation="Fix mesh",
        )
        assert d.defect_id == "DEF-ALIAS-1"
        assert d.category == DefectCategory.PENETRATION
        assert d.severity == DefectSeverity.MAJOR
        assert "Dress" in d.affected_objects
        assert d.recommendation == "Fix mesh"

        # Roundtrip
        j_str = d.model_dump_json()
        restored = DefectItem.model_validate_json(j_str)
        assert restored.defect_id == "DEF-ALIAS-1"
        assert restored.category == DefectCategory.PENETRATION
        assert restored.severity == DefectSeverity.MAJOR

    def test_extra_fields_ignored_during_deserialization(self):
        """Verifies ConfigDict(extra='ignore') accommodates external tool extensions."""
        payload = {
            "status": "success",
            "passed": True,
            "quality_score": 98.0,
            "defect_count": 0,
            "defects": [],
            "extra_custom_metadata": {"worker": "worker_m3", "build_id": 1234},
            "unexpected_token": "IGNORE_ME",
        }
        json_str = json.dumps(payload)
        out = VisualCritiqueOutput.model_validate_json(json_str)
        assert out.status == "success"
        assert out.passed is True
        assert out.quality_score == 98.0
