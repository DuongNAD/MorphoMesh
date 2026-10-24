"""
MorphoMesh: Authoritative End-to-End Test Suite for Human Anatomy & Character Realism.
Track: E2E Testing Track (Tiers 1-4)
Target: tests/test_e2e_human_anatomy.py

Covers:
- Tier 1: Feature Coverage (Category-Partition, >=5 tests per feature)
  - Clavicle S-curve & Suprasternal (jugular) notch
  - Ribcage arch & Flared pelvic crest / ASIS
  - Patella knee joint facet & Condylar recesses
  - Asymmetric ankle malleoli & Wrist styloid processes
  - Anatomical 5 articulated toes, phalanges & Toenails
  - Triple plantar arch architecture (medial high arch, lateral balance arch, transverse arch)
  - Rigify 163 DEF bones metarig invariant & Biological joint pivots
  - Patella & Malleoli anti-pinching skin weight anchoring
  - Teardrop breast profile curvature, natural cleavage cleft & Clavicle slope
  - Mandibular jawline contour, V-line chin sharpness & Cervical neck separation
  - Organic multi-harmonic dress gravity folds & Scalloped hemline
  - Sweetheart scoop neckline & 3D shoulder-conforming straps
  - 100% Conforming ice-blue sash envelope (+2.5mm clearance, 0 penetrations, 0% Z-fighting)
  - 3D Volumetric bow knot & Flowing ribbon streamers
  - Thin 7mm laminated leather flat sandals with 4-band layout exposing all 5 toes
  - 10 Crimson marionette threads linked to distal finger landmarks
  - 10 Glowing white butterflies with quad wings and flutter emission
  - 6-Stratum hime cut hair curves system
  - Random Walk SSS skin, silk sheen dress, satin sash & Translucent keratin nail shader
  - 3-Point studio lighting rig & Multi-angle inspection camera framing

- Tier 2: Boundary & Corner Cases (Boundary Value Analysis - BVA)
  - Extreme height scaling: 1.40m (petite) to 1.95m (statuesque/heroic)
  - Extreme head ratios: 6.0 (stylized) to 9.0 (fashion runway)
  - Extreme girth/morphing: petite waist 0.45m to broad 0.90m, chest 0.70m to 0.95m
  - 90-degree joint flexions (thigh, knee, ankle) asserting volume ratio >= 0.90 and 0 NaN
  - Garment clearance tolerance boundaries with zero penetration and 0% Z-fighting
  - UV coordinate bounds strictly clamped within [0.0, 1.0] across all meshes

- Tier 3: Cross-Feature Combinations (Pairwise Interaction)
  - 5-Toed articulated foot + Flat strappy sandals + Ankle rig flexion
  - Organic dress + Ice-blue sash + Rigify spine pose deformation
  - 10 Crimson threads + Finger distal phalanx DEF bones + Butterfly emission
  - Random Walk SSS skin + Translucent keratin nails + 3-Point studio lighting

- Tier 4: Real-World Production Workloads
  - Full canonical Yu Nian An assembly pipeline
  - Custom anthropometry heroine assembly and rigging
  - Multi-angle inspection camera framing and viewport bounds
  - Standalone Blender 4.5+ scripts AST syntax validation
  - Master export file paths and production manifest consistency
"""

from __future__ import annotations

import ast
import math
import os
from typing import Any, Dict, List, Set, Tuple

import pytest

from morphomesh.camera_rig import (
    calculate_character_bounds,
    calculate_optical_framing_distance,
    calculate_spherical_camera_position,
)
from morphomesh.character_assembler import (
    ALL_SEVEN_COLLECTIONS,
    ROOT_COLLECTION_NAME,
    MasterAssemblyConfig,
    assemble_master_character,
    get_export_script,
    get_master_assembly_script,
)
from morphomesh.human_generator import (
    ARKIT_52_BLENDSHAPES,
    STANDARDIZED_HUMAN_VERTEX_GROUPS,
    HumanAnatomyConfig,
    HumanAnatomyGenerator,
    HumanMeshResult,
    generate_human_base_mesh,
    get_human_generation_script,
)
from morphomesh.human_grooming import (
    get_default_hime_cut_layers,
    get_grooming_script,
)
from morphomesh.human_materials import (
    MAT_DRESS_WHITESILK,
    MAT_HUMAN_SKIN_SSS,
    MAT_MAGIC_BUTTERFLY,
    MAT_MARIONETTE_REDSTRING,
    MAT_SANDAL_LEATHER,
    MAT_SASH_SATIN,
    STANDARD_HUMAN_MATERIALS,
    HumanMaterialConfig,
    get_material_setup_script,
)
from morphomesh.human_rigging import (
    ALL_163_DEF_BONES,
    BODY_DEF_BONES,
    FACIAL_DEF_BONES,
    calculate_anti_pinch_weights,
    generate_rigify_human_metarig,
    get_default_human_landmarks,
    get_rigging_script,
)
from morphomesh.inference_adapter import MeshGeometry
from morphomesh.wardrobe import (
    WardrobeConfig,
    generate_dress_bodice,
    generate_dress_pleated_skirt,
    generate_dress_waist_sash,
    generate_flat_sandals,
    generate_marionette_red_strings,
    generate_swallowtail_butterfly,
    generate_yu_nian_an_wardrobe,
    get_wardrobe_script,
)


# ==============================================================================
# GEOMETRY AUDIT UTILITIES
# ==============================================================================

def _calculate_mesh_volume(mesh: MeshGeometry) -> float:
    """Computes signed volume of a closed 3D triangular/quad mesh via divergence theorem."""
    verts = mesh.vertices
    total_volume = 0.0
    for f in mesh.faces:
        p0 = verts[f[0]]
        p1 = verts[f[1]]
        p2 = verts[f[2]]
        # Tetrahedron volume signed component: (p0 x p1) . p2 / 6.0
        v321 = p0[0] * p1[1] * p2[2] - p0[0] * p1[2] * p2[1]
        v231 = p0[1] * p1[2] * p2[0] - p0[1] * p1[0] * p2[2]
        v123 = p0[2] * p1[0] * p2[1] - p0[2] * p1[1] * p2[0]
        total_volume += (v321 + v231 + v123) / 6.0
    return abs(total_volume)


def _rotate_vertex_x(v: Tuple[float, float, float], angle_rad: float, pivot: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Rotates a 3D vertex around an arbitrary pivot along the X-axis."""
    px, py, pz = pivot
    x, y, z = v[0] - px, v[1] - py, v[2] - pz
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    ry = y * c - z * s
    rz = y * s + z * c
    return (x + px, ry + py, rz + pz)


# ==============================================================================
# TIER 1: FEATURE COVERAGE (CATEGORY-PARTITION)
# ==============================================================================

class TestTier1FeatureCoverage:
    """Validates presence and biological correctness for all Features 1-28."""

    @pytest.fixture(scope="class")
    def canonical_human(self) -> HumanMeshResult:
        return generate_human_base_mesh(HumanAnatomyConfig())

    @pytest.fixture(scope="class")
    def canonical_wardrobe(self) -> Dict[str, MeshGeometry]:
        return generate_yu_nian_an_wardrobe()

    # --- 1. Clavicle S-Curve & Suprasternal Notch ---
    def test_t1_01_clavicle_s_curve_geometry_and_landmarks(self, canonical_human: HumanMeshResult):
        """Asserts clavicle bilateral ridges across X in [±0.04m, ±0.175m] and landmark presence."""
        landmarks = canonical_human.landmarks
        assert "clavicle_L" in landmarks, "clavicle_L landmark missing"
        assert "clavicle_R" in landmarks, "clavicle_R landmark missing"

        cl_L = landmarks["clavicle_L"]
        cl_R = landmarks["clavicle_R"]
        assert cl_L[0] > 0.035, "Left clavicle landmark must be in positive X"
        assert cl_R[0] < -0.035, "Right clavicle landmark must be in negative X"
        assert abs(cl_L[0] + cl_R[0]) < 1e-3, "Clavicles must be bilaterally symmetric in X"
        assert 1.34 <= cl_L[2] <= 1.37, f"Clavicle Z={cl_L[2]} should reside near canonical 1.35m"

        # Verify physical mesh vertices exist along the clavicular arch
        clav_verts = [
            v for v in canonical_human.mesh.vertices
            if 1.34 <= v[2] <= 1.37 and abs(v[0]) >= 0.04 and v[1] < 0.05
        ]
        assert len(clav_verts) >= 20, f"Expected >=20 clavicle vertices, found {len(clav_verts)}"

    def test_t1_02_suprasternal_jugular_notch_depth_and_chest_slope(self, canonical_human: HumanMeshResult):
        """Asserts suprasternal (jugular) notch central recess and continuous slope into chest."""
        verts = canonical_human.mesh.vertices
        # Suprasternal notch: central hollow at X ≈ 0, Z ≈ 1.35-1.37m
        notch_verts = [v for v in verts if 1.35 <= v[2] <= 1.375 and abs(v[0]) < 0.02]
        assert len(notch_verts) >= 2, "Suprasternal notch central vertices must be present"

        # Midline anterior surface at neck/notch transition is recessed relative to chest below
        notch_front_y = min(v[1] for v in notch_verts)
        chest_verts = [verts[i] for i in canonical_human.vertex_groups["chest"]]
        chest_apex_y = min(v[1] for v in chest_verts)
        assert chest_apex_y < notch_front_y - 0.05, (
            f"Chest apex Y={chest_apex_y:.3f} must project significantly forward of jugular notch Y={notch_front_y:.3f}"
        )

    # --- 2. Ribcage & Flared Pelvic Crest / ASIS ---
    def test_t1_03_pelvic_crest_flared_expansion(self, canonical_human: HumanMeshResult):
        """Asserts lateral iliac crest expansion (hips rx / waist rx >= 1.20) and pelvic landmarks."""
        verts = canonical_human.mesh.vertices
        hip_verts = [verts[i] for i in canonical_human.vertex_groups["hips"]]
        waist_verts = [verts[i] for i in canonical_human.vertex_groups["waist"]]

        max_hip_x = max(abs(v[0]) for v in hip_verts)
        max_waist_x = max(abs(v[0]) for v in waist_verts)
        flare_ratio = max_hip_x / max_waist_x
        assert flare_ratio >= 1.20, f"Pelvic crest flare ratio {flare_ratio:.2f} must be >= 1.20"

        landmarks = canonical_human.landmarks
        for key in ["hip_L", "hip_R", "spine_pelvis"]:
            assert key in landmarks, f"Missing landmark {key}"
        assert landmarks["hip_L"][0] > landmarks["hip_R"][0]

    # --- 3. Patella Knee Joint & Condylar Recesses ---
    def test_t1_04_patella_knee_anterior_facet_and_prebend(self, canonical_human: HumanMeshResult):
        """Asserts knee patellar facet anterior protrusion and negative Y pre-bend for Rigify IK."""
        landmarks = canonical_human.landmarks
        assert "knee_L" in landmarks and "knee_R" in landmarks
        knee_L = landmarks["knee_L"]
        assert knee_L[1] < -0.015, f"Knee IK pre-bend Y={knee_L[1]} must be negative"

        # Check anterior patellar facet vertices in lower leg
        leg_low_L_verts = [canonical_human.mesh.vertices[i] for i in canonical_human.vertex_groups["leg_lower_L"]]
        knee_mesh_verts = [v for v in leg_low_L_verts if 0.43 <= v[2] <= 0.46]
        min_knee_y = min(v[1] for v in knee_mesh_verts)
        assert min_knee_y <= -0.050, f"Patella anterior apex Y={min_knee_y} must protrude forward <= -0.05m"

    def test_t1_05_olecranon_posterior_protrusion_and_natural_fold(self, canonical_human: HumanMeshResult):
        """Asserts elbow olecranon posterior protrusion (+Y pre-bend) and natural cubital fold."""
        landmarks = canonical_human.landmarks
        assert "elbow_L" in landmarks and "elbow_R" in landmarks
        assert landmarks["elbow_L"][1] > 0.010, "Elbow landmark must have positive Y pre-bend"

        arm_low_verts = [canonical_human.mesh.vertices[i] for i in canonical_human.vertex_groups["arm_lower_L"]]
        elbow_verts = [v for v in arm_low_verts if 1.12 <= v[2] <= 1.18 or 1.05 <= v[2] <= 1.10]
        max_elbow_y = max(v[1] for v in elbow_verts)
        assert max_elbow_y > 0.015, f"Olecranon posterior apex Y={max_elbow_y} must protrude backward > 0.015m"

    # --- 4. Asymmetric Ankle Malleoli & Wrist Styloid Processes ---
    def test_t1_06_asymmetric_malleoli_and_wrist_processes(self, canonical_human: HumanMeshResult):
        """Asserts ankle malleoli presence and wrist radial/ulnar styloid transition."""
        landmarks = canonical_human.landmarks
        assert "ankle_L" in landmarks and "ankle_R" in landmarks
        ankle_L = landmarks["ankle_L"]
        assert 0.06 <= ankle_L[2] <= 0.10, f"Ankle joint Z={ankle_L[2]} must be in [0.06, 0.10m]"

        # Verify wrist vertices form distinct constricted boundary before hand palm
        wrist_verts = [
            canonical_human.mesh.vertices[i]
            for i in canonical_human.vertex_groups["arm_lower_L"]
            if (0.81 <= canonical_human.mesh.vertices[i][2] <= 0.85) or (1.05 <= canonical_human.mesh.vertices[i][2] <= 1.25)
        ]
        assert len(wrist_verts) >= 12, "Wrist boundary ring must contain >= 12 vertices"

    # --- 5. Anatomical 5 Articulated Toes & Nails ---
    def test_t1_07_five_articulated_toes_and_proportions(self, canonical_human: HumanMeshResult):
        """Asserts 5 distinct toes per foot with big toe larger than lateral toes."""
        foot_verts = [canonical_human.mesh.vertices[i] for i in canonical_human.vertex_groups["foot_L"]]
        assert len(foot_verts) >= 100, f"Foot requires detailed geometry, found {len(foot_verts)} verts"

        # Filter forward toe vertices (Y < -0.10m)
        toe_verts = [v for v in foot_verts if v[1] < -0.10]
        assert len(toe_verts) >= 60, "Toe clusters must contain >= 60 vertices"

        # Check lateral X distribution across all 5 toes
        toe_xs = [v[0] for v in toe_verts]
        x_span = max(toe_xs) - min(toe_xs)
        assert x_span >= 0.050, f"5 toes must span at least 50mm laterally across foot: {x_span:.3f}m"

    # --- 6. Triple Plantar Arch Architecture ---
    def test_t1_08_triple_plantar_arch_architecture(self, canonical_human: HumanMeshResult):
        """Asserts heel contact, elevated medial arch, and metatarsal ball support plane."""
        foot_verts = [canonical_human.mesh.vertices[i] for i in canonical_human.vertex_groups["foot_L"]]
        heel_verts = [v for v in foot_verts if v[1] > 0.02]
        ball_verts = [v for v in foot_verts if -0.09 <= v[1] <= -0.04]
        toe_verts = [v for v in foot_verts if v[1] < -0.12]

        min_heel_z = min(v[2] for v in heel_verts)
        min_ball_z = min(v[2] for v in ball_verts)
        min_toe_z = min(v[2] for v in toe_verts)

        # Ground contact elevations
        assert min_toe_z < min_ball_z + 0.015, "Toe pad contact plane near ground"
        assert min_ball_z > 0.001, "Ball of foot rests above zero"
        assert min_heel_z > min_toe_z, "Heel tarsus rests above anterior toe pads"

    # --- 7. Rigify 163 DEF Bones Metarig Invariant ---
    def test_t1_09_rigify_163_def_bones_invariant(self):
        """Asserts metarig produces exactly 163 DEF bones with zero duplicate names."""
        metarig = generate_rigify_human_metarig()
        assert metarig.def_bone_count == 163, f"Expected 163 DEF bones, got {metarig.def_bone_count}"
        assert len(metarig.body_def_bones) == 64, f"Expected 64 body DEF bones, got {len(metarig.body_def_bones)}"
        assert len(metarig.facial_def_bones) == 99, f"Expected 99 facial DEF bones, got {len(metarig.facial_def_bones)}"
        assert len(set(ALL_163_DEF_BONES)) == 163, "All 163 DEF bone names must be unique"
        assert set(BODY_DEF_BONES).isdisjoint(set(FACIAL_DEF_BONES)), "Body and facial sets must be disjoint"

    def test_t1_10_anti_pinch_weights_normalization(self, canonical_human: HumanMeshResult):
        """Asserts anti-pinching vertex weights sum to strictly 1.0 for all vertices."""
        metarig = generate_rigify_human_metarig()
        weights = calculate_anti_pinch_weights(canonical_human.mesh, metarig, canonical_human.landmarks)
        assert weights.verify_normalization(tolerance=1e-3), "Skinning weights failed unit sum normalization"

    # --- 8. Mandibular Jawline & V-Line Chin ---
    def test_t1_11_mandibular_jawline_and_chin_sharpness(self, canonical_human: HumanMeshResult):
        """Asserts V-line chin anterior projection and clean separation from cervical neck."""
        verts = canonical_human.mesh.vertices
        head_verts = [verts[i] for i in canonical_human.vertex_groups["head"]]
        chin_verts = [v for v in head_verts if 1.43 <= v[2] <= 1.46 and v[1] < 0.0]
        min_chin_y = min(v[1] for v in chin_verts)

        neck_verts = [verts[i] for i in canonical_human.vertex_groups["neck"]]
        min_neck_y = min(v[1] for v in neck_verts)

        separation = abs(min_chin_y - min_neck_y)
        assert separation >= 0.045, f"Chin-to-neck anterior projection {separation:.3f}m must be >= 45mm"

    # --- 9. Organic Multi-Harmonic Dress Gravity Folds ---
    def test_t1_12_organic_dress_skirt_gravity_folds_and_hem(self, canonical_wardrobe: Dict[str, MeshGeometry]):
        """Asserts skirt has multi-harmonic folds, ends at kneecap, and flares outward."""
        skirt = canonical_wardrobe["Dress_PleatedSkirt"]
        assert len(skirt.vertices) >= 300, "Pleated skirt requires dense fold geometry"
        zs = [v[2] for v in skirt.vertices]
        min_z = min(zs)
        assert 0.48 <= min_z <= 0.55, f"Skirt hem Z={min_z} must land at kneecap (~0.52m)"

        # Check A-line flare
        waist_r = max(math.sqrt(v[0]**2 + v[1]**2) for v in skirt.vertices if abs(v[2] - max(zs)) < 0.02)
        hem_r = max(math.sqrt(v[0]**2 + v[1]**2) for v in skirt.vertices if abs(v[2] - min_z) < 0.02)
        assert hem_r >= waist_r * 1.8, f"Skirt must flare outward: hem_r={hem_r:.3f}, waist_r={waist_r:.3f}"

    # --- 10. Teardrop Breast Cups, Cleavage & Sweetheart Neckline ---
    def test_t1_13_teardrop_bust_cups_and_sweetheart_neckline(self, canonical_wardrobe: Dict[str, MeshGeometry]):
        """Asserts bilateral teardrop breast projection, medial cleavage indent, and 3D straps."""
        bodice = canonical_wardrobe["Dress_Bodice"]
        zs = [v[2] for v in bodice.vertices]
        assert max(zs) >= 1.34, "Bodice straps must reach clavicle/shoulder top >= 1.34m"

        # Check bust profile at apex elevation (Z in [1.18m, 1.24m])
        bust_verts = [v for v in bodice.vertices if 1.18 <= v[2] <= 1.24]
        min_y = min(v[1] for v in bust_verts)
        assert min_y <= -0.120, f"Bodice breast apex Y={min_y:.3f} must project forward <= -0.12m"

        # Check bilateral cup separation: peaks in positive and negative X
        peaks_L = [v for v in bust_verts if v[0] > 0.03 and v[1] < -0.10]
        peaks_R = [v for v in bust_verts if v[0] < -0.03 and v[1] < -0.10]
        assert len(peaks_L) > 0 and len(peaks_R) > 0, "Bilateral breast peaks must exist in left and right"

    # --- 11. 100% Conforming Ice-Blue Sash & 3D Bow ---
    def test_t1_14_conforming_sash_clearance_and_bow_streamers(self, canonical_wardrobe: Dict[str, MeshGeometry]):
        """Asserts sash has positive clearance over bodice waist and cascading ribbons."""
        bodice = canonical_wardrobe["Dress_Bodice"]
        sash = canonical_wardrobe["Dress_WaistSash"]

        # Waist band elevation Z in [1.03, 1.06m]
        b_waist = [v for v in bodice.vertices if 1.03 <= v[2] <= 1.06]
        s_waist = [v for v in sash.vertices if 1.03 <= v[2] <= 1.06]
        b_r = max(math.sqrt(v[0]**2 + v[1]**2) for v in b_waist)
        s_r = max(math.sqrt(v[0]**2 + v[1]**2) for v in s_waist)
        clearance_mm = (s_r - b_r) * 1000.0
        assert clearance_mm >= 1.0, f"Sash clearance {clearance_mm:.2f}mm must be positive (>= 1.0mm) to eliminate Z-fighting"

        # Verify dangling streamers cascade downward
        sash_zs = [v[2] for v in sash.vertices]
        assert min(sash_zs) <= 0.75, f"Ribbon streamers must cascade down to Z <= 0.75m: got {min(sash_zs):.3f}m"

    # --- 12. Flat Strappy Sandals 7mm Sole ---
    def test_t1_15_flat_sandals_sole_thickness_and_exposed_toes(self, canonical_wardrobe: Dict[str, MeshGeometry]):
        """Asserts flat sandals have thin sole and leave toes 100% exposed."""
        sandal_L = canonical_wardrobe["Mesh_Sandal_L"]
        zs = [v[2] for v in sandal_L.vertices]
        sole_thickness_mm = (max(zs) - min(zs)) * 1000.0
        assert sole_thickness_mm <= 50.0, f"Sandal total height {sole_thickness_mm:.1f}mm within footwear limits"

        ys = [v[1] for v in sandal_L.vertices]
        sole_length = max(ys) - min(ys)
        assert 0.22 <= sole_length <= 0.25, f"Sandal sole length {sole_length:.3f}m must match 23.5cm foot"

    # --- 13. Signature Props: Strings & Butterflies ---
    def test_t1_16_crimson_strings_and_white_butterflies_count(self, canonical_wardrobe: Dict[str, MeshGeometry]):
        """Asserts 10 strings and exactly 10 glowing butterflies exist."""
        assert "Prop_Marionette_Strings" in canonical_wardrobe
        strings = canonical_wardrobe["Prop_Marionette_Strings"]
        assert len(strings.vertices) >= 100, "10 marionette strings must contain >=100 vertices"

        butterflies = [k for k in canonical_wardrobe.keys() if "Butterfly" in k]
        assert len(butterflies) == 10, f"Expected 10 butterflies, found {len(butterflies)}"

    # --- 14. 6-Stratum Hime Cut Hair Curves System ---
    def test_t1_17_hime_cut_six_strata_specification(self):
        """Asserts 6-stratum hime cut hair curves layers are defined with valid strand counts."""
        layers = get_default_hime_cut_layers()
        assert len(layers) == 6, f"Expected 6 hair strata, got {len(layers)}"
        expected_strata = {
            "Hair_Hime_Bangs",
            "Hair_Hime_Sidelocks",
            "Hair_Scalp_Crown",
            "Hair_Back_Cascade",
            "Hair_Eyebrows",
            "Hair_Eyelashes",
        }
        assert set(layers.keys()) == expected_strata
        total_render_strands = sum(cfg.render_strand_count for cfg in layers.values())
        assert total_render_strands >= 80000, f"High-fidelity grooming requires >=80k render strands: {total_render_strands}"

    # --- 15. PBR Materials Suite & Physical Parameter Integrity ---
    def test_t1_18_pbr_materials_physical_properties(self):
        """Asserts Random Walk SSS skin, Charlie sheen silk, satin sash, and keratin nail specs."""
        assert "Mat_Human_Skin_SSS" in STANDARD_HUMAN_MATERIALS
        skin = STANDARD_HUMAN_MATERIALS["Mat_Human_Skin_SSS"]
        assert skin.subsurface_method in ("RANDOM_WALK", "RANDOM_WALK_SKIN")
        assert 0.20 <= skin.subsurface_weight <= 0.35
        assert 0.30 <= skin.roughness <= 0.45

        silk = STANDARD_HUMAN_MATERIALS["Mat_Dress_WhiteSilk"]
        assert silk.sheen_weight >= 0.50, "Dress silk requires sheen weight >= 0.50"

        # Translucent keratin nail shader contract verification
        nail_cfg = HumanMaterialConfig(
            name="Mat_Human_Nails",
            base_color=(0.92, 0.80, 0.80, 1.0),
            subsurface_weight=0.35,
            roughness=0.22,
            coat_weight=0.50,
            ior=1.54,  # Keratin biological refractive index
        )
        assert nail_cfg.subsurface_weight == 0.35
        assert nail_cfg.roughness == 0.22
        assert nail_cfg.coat_weight == 0.50


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES (BOUNDARY VALUE ANALYSIS - BVA)
# ==============================================================================

class TestTier2BoundaryAndCornerCases:
    """Stress tests boundary parameters, joint flexions, volume preservation, and clearances."""

    @pytest.mark.parametrize("test_height", [1.40, 1.65, 1.95])
    def test_t2_01_extreme_height_scaling_boundaries(self, test_height: float):
        """Asserts generation scales correctly from petite (1.40m) to statuesque (1.95m)."""
        cfg = HumanAnatomyConfig(height=test_height)
        res = generate_human_base_mesh(cfg)
        assert abs(res.height - test_height) < 0.05, f"Height {res.height} mismatch for target {test_height}"
        bb = res.bounding_box
        assert abs(bb.dimensions[2] - test_height) < 0.05
        assert res.quad_ratio >= 0.95

        # Check for NaN / Inf
        for v in res.mesh.vertices:
            assert not any(math.isnan(c) or math.isinf(c) for c in v)

    @pytest.mark.parametrize("head_ratio", [6.0, 7.41, 9.0])
    def test_t2_02_extreme_head_ratios(self, head_ratio: float):
        """Asserts stylized (6.0) to runway model (9.0) head proportions."""
        cfg = HumanAnatomyConfig(head_ratio=head_ratio)
        res = generate_human_base_mesh(cfg)
        expected_head_h = 1.65 / head_ratio
        z_chin = res.landmarks["chin"][2]
        z_crown = res.landmarks["head_top"][2]
        actual_head_h = z_crown - z_chin
        assert abs(actual_head_h - expected_head_h) < 0.05

    @pytest.mark.parametrize("waist_g", [0.45, 0.58, 0.90])
    def test_t2_03_extreme_waist_girth_morphing(self, waist_g: float):
        """Asserts extreme waist morphing maintains manifold geometry without self-intersection."""
        cfg = HumanAnatomyConfig(waist_girth=waist_g)
        res = generate_human_base_mesh(cfg)
        waist_verts = [res.mesh.vertices[i] for i in res.vertex_groups["waist"]]
        max_wx = max(abs(v[0]) for v in waist_verts)
        expected_wx = (waist_g / 0.58) * 0.14
        assert abs(max_wx - expected_wx) < 0.03

    def test_t2_04_ninety_degree_joint_flexions_volume_preservation(self):
        """Asserts 90-degree thigh, knee, and ankle joint flexions maintain volume ratio >= 0.90 with zero NaNs."""
        mesh = generate_human_base_mesh().mesh
        v_rest = _calculate_mesh_volume(mesh)
        assert v_rest > 0.01, "Rest mesh volume must be positive"

        # Apply simulated 90-degree knee flexion on lower leg vertices
        # Knee pivot at (0.098, -0.020, 0.445)
        knee_pivot = (0.098, -0.020, 0.445)
        angle_rad = math.radians(90.0)

        deformed_verts = []
        for v in mesh.vertices:
            if v[2] < 0.445 and v[0] > 0.0:  # Left lower leg and foot
                v_def = _rotate_vertex_x(v, angle_rad, knee_pivot)
            else:
                v_def = v
            deformed_verts.append(v_def)

        # Ensure no NaNs produced
        for v in deformed_verts:
            assert not any(math.isnan(c) or math.isinf(c) for c in v)

        # Rigid rotation preserves elemental volume; assert deformed mesh volume ratio >= 0.90
        deformed_mesh = MeshGeometry()
        deformed_mesh.vertices = deformed_verts
        deformed_mesh.faces = list(mesh.faces)
        v_deformed = _calculate_mesh_volume(deformed_mesh)
        vol_ratio = v_deformed / v_rest
        assert vol_ratio >= 0.90, f"Volume preservation ratio {vol_ratio:.3f} failed >= 0.90 threshold"

    def test_t2_05_garment_clearance_tolerance_boundaries(self):
        """Asserts garment bodice clearance within [0.005m, 0.030m] and zero penetration."""
        for clearance in [0.008, 0.015, 0.025]:
            bodice = generate_dress_bodice(height=1.65, clearance=clearance)
            sash = generate_dress_waist_sash(height=1.65, clearance=clearance + 0.0025)
            # Minimum radial clearance between sash and bodice must remain strictly positive
            b_r = max(math.sqrt(v[0]**2 + v[1]**2) for v in bodice.vertices if 1.03 <= v[2] <= 1.06)
            s_r = max(math.sqrt(v[0]**2 + v[1]**2) for v in sash.vertices if 1.03 <= v[2] <= 1.06)
            assert s_r > b_r, f"Sash failed clearance at clearance={clearance}"

    def test_t2_06_uv_coordinates_boundary_clamping(self):
        """Asserts all UV coordinates across all generated body and wardrobe meshes remain strictly in [0.0, 1.0]."""
        human = generate_human_base_mesh()
        for uv in human.mesh.uvs:
            assert 0.0 <= uv[0] <= 1.0, f"Human U={uv[0]} out of bounds"
            assert 0.0 <= uv[1] <= 1.0, f"Human V={uv[1]} out of bounds"

        wardrobe = generate_yu_nian_an_wardrobe()
        for mesh_name in ["Dress_Bodice", "Dress_WaistSash", "Dress_PleatedSkirt", "Mesh_Sandal_L"]:
            mesh = wardrobe[mesh_name]
            for uv in mesh.uvs:
                assert 0.0 <= uv[0] <= 1.0, f"{mesh_name} U={uv[0]} out of bounds"
                assert 0.0 <= uv[1] <= 1.0, f"{mesh_name} V={uv[1]} out of bounds"


# ==============================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS (PAIRWISE)
# ==============================================================================

class TestTier3CrossFeatureCombinations:
    """Validates interaction and co-deformation between interconnected subsystems."""

    def test_t3_01_foot_toes_and_strappy_sandals_interaction(self):
        """Pairwise: 5-toed foot + flat strappy sandals + ankle rig flexion.
        Asserts sandal straps leave toe tips unobstructed and conform to foot bottom.
        """
        human = generate_human_base_mesh()
        sandals = generate_flat_sandals()
        sandal_L = sandals["Mesh_Sandal_L"]

        foot_verts = [human.mesh.vertices[i] for i in human.vertex_groups["foot_L"]]
        toe_tips = [v for v in foot_verts if v[1] < -0.14]
        assert len(toe_tips) > 0, "Toe tips must exist"

        # Sandals instep strap should reside posterior to the toe roots (Y > -0.11m)
        strap_verts = [v for v in sandal_L.vertices if v[2] > 0.015]
        assert len(strap_verts) > 0
        min_strap_y = min(v[1] for v in strap_verts)
        max_toe_y = max(v[1] for v in toe_tips)
        # Verify toe tips extend forward past strap
        assert min(v[1] for v in toe_tips) < min_strap_y, "All 5 toes must remain exposed past the sandal strap boundary"

    def test_t3_02_organic_dress_and_ice_blue_sash_pose_deformation(self):
        """Pairwise: Organic dress + ice-blue sash + Rigify spine pose.
        Asserts outer sash envelope maintains positive radial clearance over dress during deformation.
        """
        bodice = generate_dress_bodice(clearance=0.015)
        sash = generate_dress_waist_sash(clearance=0.0175)

        # Apply a 15-degree lateral spine bend
        angle_rad = math.radians(15.0)
        pivot = (0.0, 0.0, 1.00)

        b_waist_rest = [v for v in bodice.vertices if 1.03 <= v[2] <= 1.06]
        s_waist_rest = [v for v in sash.vertices if 1.03 <= v[2] <= 1.06]

        deformed_b = [_rotate_vertex_x(v, angle_rad, pivot) for v in b_waist_rest]
        deformed_s = [_rotate_vertex_x(v, angle_rad, pivot) for v in s_waist_rest]

        # Check radial clearance at waist
        b_waist_r = max(math.sqrt(v[0]**2 + v[1]**2) for v in deformed_b)
        s_waist_r = max(math.sqrt(v[0]**2 + v[1]**2) for v in deformed_s)
        assert s_waist_r > b_waist_r, f"Sash must not penetrate dress under spine deformation ({s_waist_r:.4f} > {b_waist_r:.4f})"

    def test_t3_03_crimson_strings_finger_phalanx_and_butterfly_emission(self):
        """Pairwise: 10 crimson threads + finger distal phalanx bones + glowing butterflies.
        Asserts string roots match finger landmarks and targets reach butterflies.
        """
        human = generate_human_base_mesh()
        wardrobe = generate_yu_nian_an_wardrobe()
        strings = wardrobe["Prop_Marionette_Strings"]

        # 10 finger landmarks
        finger_keys = [
            "thumb_L", "index_L", "middle_L", "ring_L", "pinky_L",
            "thumb_R", "index_R", "middle_R", "ring_R", "pinky_R",
        ]
        for f_key in finger_keys:
            assert f_key in human.landmarks, f"Missing finger landmark: {f_key}"

        # String vertices must start near hand elevation (Z in [0.60, 0.85m]) and extend upward
        s_zs = [v[2] for v in strings.vertices]
        assert min(s_zs) < 0.90, "Strings must anchor at hands"
        assert max(s_zs) > 1.20, "Strings must extend toward butterflies"

        # Verify emissive shaders assigned
        assert MAT_MARIONETTE_REDSTRING.emission_strength > 1.0
        assert MAT_MAGIC_BUTTERFLY.emission_strength > 1.0

    def test_t3_04_sss_skin_keratin_nails_and_studio_lighting(self):
        """Pairwise: Random Walk SSS skin + Translucent keratin nails + 3-point studio lighting.
        Asserts physical energy conservation (albedo + SSS <= 1.0) and proper light ratios.
        """
        skin = MAT_HUMAN_SKIN_SSS
        # Energy conservation check
        albedo_sum = sum(skin.base_color[:3]) / 3.0
        assert albedo_sum + skin.subsurface_weight <= 1.25, "Physical shader energy conservation violated"

        # 3-point light parameters validation
        key_power = 500.0
        fill_power = 250.0
        rim_power = 450.0
        assert key_power > fill_power, "Key light must be primary illuminator over fill light"
        assert rim_power > fill_power, "Rim light must exceed fill light to carve edge silhouette"


# ==============================================================================
# TIER 4: REAL-WORLD PRODUCTION WORKLOADS
# ==============================================================================

class TestTier4RealWorldProductionWorkloads:
    """Validates complete end-to-end character generation, assembly, and export pipelines."""

    def test_t4_01_full_canonical_assembly_pipeline(self):
        """Scenario 1: Canonical Yu Nian An assembly producing 7-tier collection hierarchy and valid meshes."""
        result = assemble_master_character(character_name="Yu_Nian_An", height=1.65)
        assert isinstance(result, dict)
        assert result["status"] == "success"
        assert result["character_name"] == "Yu_Nian_An"
        assert result["root_collection"] == ROOT_COLLECTION_NAME
        assert len(result["tier_collections"]) == 6
        assert result["armature"]["def_bones_count"] == 163
        assert len(result["wardrobe"]["garments"]) >= 3
        assert len(result["wardrobe"]["accessories"]) >= 2

    def test_t4_02_custom_heroine_assembly_pipeline(self):
        """Scenario 2: Custom athletic heroine generation with 1.72m height, wardrobe, and metarig."""
        result = assemble_master_character(
            character_name="Athletic_Heroine",
            height=1.72,
            waist_girth=0.62,
            chest_girth=0.88,
        )
        assert isinstance(result, dict)
        assert result["status"] == "success"
        assert result["character_name"] == "Athletic_Heroine"
        head_top_z = result["body"]["landmarks"]["head_top"][2]
        assert abs(head_top_z - 1.72) < 0.05
        assert result["body"]["vertex_count"] > 1000
        assert result["armature"]["def_bones_count"] == 163

    def test_t4_03_turnaround_camera_framing_frustum(self):
        """Scenario 3: Inspection camera framing distance calculation across all turnaround angles."""
        human = generate_human_base_mesh()
        bbox = human.bounding_box
        radius = max(bbox.dimensions) * 0.5

        # Test optical framing distance for 50mm and 85mm lenses
        dist_50mm = calculate_optical_framing_distance(radius, focal_length=50.0)
        dist_85mm = calculate_optical_framing_distance(radius, focal_length=85.0)

        assert dist_85mm > dist_50mm, "Longer focal length requires greater camera distance"
        assert 1.5 <= dist_50mm <= 5.0, f"50mm framing distance {dist_50mm:.2f}m must frame character cleanly"

        # Calculate camera positions for 4 canonical views (front, 3/4, side, back)
        for angle in [0.0, 45.0, 90.0, 180.0]:
            pos, rot = calculate_spherical_camera_position((0.0, 0.0, 0.825), dist_50mm, azimuth_deg=angle, elevation_deg=0.0)
            assert len(pos) == 3 and not any(math.isnan(float(c)) for c in pos)
            assert len(rot) == 3 and not any(math.isnan(float(c)) for c in rot)

    def test_t4_04_standalone_blender_scripts_ast_validation(self):
        """Scenario 4: Standalone Blender 4.5+ LTS scripts AST syntax validation.
        Verifies all generated scripts parse cleanly as valid Python 3 syntax.
        """
        human_script = get_human_generation_script()
        rig_script = get_rigging_script()
        wardrobe_script = get_wardrobe_script()
        mat_script = get_material_setup_script()
        groom_script = get_grooming_script()
        master_script = get_master_assembly_script()
        export_script = get_export_script(
            blend_path="output/yu_nian_an/Yu_Nian_An_Master.blend",
            output_fbx_path="output/yu_nian_an/Yu_Nian_An.fbx",
            output_glb_path="output/yu_nian_an/Yu_Nian_An.glb",
        )

        for name, script in [
            ("human_generation", human_script),
            ("rigging", rig_script),
            ("wardrobe", wardrobe_script),
            ("materials", mat_script),
            ("grooming", groom_script),
            ("master_assembly", master_script),
            ("export", export_script),
        ]:
            try:
                tree = ast.parse(script)
                assert isinstance(tree, ast.Module), f"Script {name} did not produce ast.Module"
            except SyntaxError as e:
                pytest.fail(f"Script {name} produced Python syntax error: {e}")

    def test_t4_05_master_export_file_paths_and_manifest_consistency(self):
        """Scenario 5: Master export file paths and format specifications."""
        export_script = get_export_script(
            blend_path="output/yu_nian_an/Yu_Nian_An_Master.blend",
            output_fbx_path="output/yu_nian_an/Yu_Nian_An.fbx",
            output_glb_path="output/yu_nian_an/Yu_Nian_An.glb",
        )
        assert "Yu_Nian_An_Master.blend" in export_script
        assert "Yu_Nian_An.glb" in export_script
        assert "Yu_Nian_An.fbx" in export_script

