"""
M1 Challenger 1: Adversarial Empirical Anatomy & Contours Verification Test Suite.
Author: M1 Challenger 1 (Adversarial Anatomy & Contours Verification)
Target: src/morphomesh/human_generator.py (Anatomical Female Base Mold)

Adversarially tests and measures:
1. Teardrop bust geometry: gravity sag, inframammary fold (IMF depth > 15mm),
   sternal cleavage valley, and inter-nipple distance.
2. Gluteal curvature: waist width vs hip width giving feminine WHR ~0.697 (0.70),
   transverse and circumferential proportions, and posterior gluteal shelf projection.
3. Shoulder contour: relaxed trapezius angle (24.2° ± 2°), elimination of horizontal shelf,
   continuous axillary quad loops, zero disconnections (watertight 2-manifold).
4. 5-toed articulated feet: Greek/Roman toe profile, interdigital cleft gap >= 4.5mm,
   and medial plantar arch elevation >= 6.0mm above floor contact.
5. Invariance across anthropometric scales: height 1.40m, 1.65m, 1.95m.
"""

from __future__ import annotations

import math
from typing import Dict, List, Set, Tuple

import numpy as np
import pytest

from morphomesh.human_generator import (
    HumanAnatomyConfig,
    HumanAnatomyGenerator,
    HumanMeshResult,
    generate_human_base_mesh,
    load_anatomical_base_mold,
)
from morphomesh.inference_adapter import MeshGeometry


# ==============================================================================
# GEOMETRIC AUDIT UTILITIES
# ==============================================================================

def extract_edge_topology(faces: List[Tuple[int, ...]]) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
    """Computes edge incidence: returns (non_manifold_edges, boundary_edges)."""
    edge_counts: Dict[Tuple[int, int], int] = {}
    for face in faces:
        n = len(face)
        for i in range(n):
            a, b = face[i], face[(i + 1) % n]
            e = (min(a, b), max(a, b))
            edge_counts[e] = edge_counts.get(e, 0) + 1
    non_manifold = [e for e, c in edge_counts.items() if c > 2]
    boundary = [e for e, c in edge_counts.items() if c == 1]
    return non_manifold, boundary


def compute_cross_sectional_perimeter(verts: np.ndarray, z_target: float, z_half_width: float = 0.015) -> float:
    """Estimates convex polygon perimeter of a horizontal cross-section at z_target."""
    slice_verts = verts[np.abs(verts[:, 2] - z_target) <= z_half_width]
    if len(slice_verts) < 8:
        return 0.0
    pts_2d = slice_verts[:, :2]
    # Centroid
    cx, cy = np.mean(pts_2d[:, 0]), np.mean(pts_2d[:, 1])
    angles = np.arctan2(pts_2d[:, 1] - cy, pts_2d[:, 0] - cx)
    order = np.argsort(angles)
    sorted_pts = pts_2d[order]
    # Compute perimeter
    diffs = np.diff(sorted_pts, axis=0)
    perim = float(np.sum(np.linalg.norm(diffs, axis=1)))
    perim += float(np.linalg.norm(sorted_pts[-1] - sorted_pts[0]))
    return perim


# ==============================================================================
# ADVERSARIAL ANATOMY & CONTOURS TEST SUITE
# ==============================================================================

class TestAdversarialAnatomyAndContours:
    """Empirical adversarial challenger suite for M1 Female Base Mold."""

    # --------------------------------------------------------------------------
    # 1. TEARDROP BUST GEOMETRY
    # --------------------------------------------------------------------------

    @pytest.mark.parametrize("height", [1.40, 1.65, 1.95])
    def test_teardrop_bust_geometry_and_sag(self, height: float):
        """
        Adversarially verifies:
        - Gravity sag: lower pole has greater anterior projection than upper pole at equal distance from apex.
        - Inframammary fold (IMF depth > 15mm) relative to ribcage wall.
        - Sternal cleavage valley depression.
        - Inter-nipple distance within anatomical range (14.0cm - 22.0cm at 1.65m scale).
        """
        scale = height / 1.65
        res = generate_human_base_mesh(HumanAnatomyConfig(height=height))
        v = np.array(res.mesh.vertices)

        # Locate bilateral breast apices (nipples)
        chest_verts = v[(v[:, 2] >= 1.10 * scale) & (v[:, 2] <= 1.25 * scale) & (v[:, 1] < -0.05 * scale)]
        assert len(chest_verts) > 50, f"Insufficient chest vertices ({len(chest_verts)})"

        l_breast = chest_verts[chest_verts[:, 0] > 0.04 * scale]
        r_breast = chest_verts[chest_verts[:, 0] < -0.04 * scale]
        assert len(l_breast) > 20 and len(r_breast) > 20, "Missing bilateral breast mounds"

        l_apex = l_breast[np.argmin(l_breast[:, 1])]
        r_apex = r_breast[np.argmin(r_breast[:, 1])]

        # Bilateral symmetry check
        assert abs(l_apex[0] + r_apex[0]) < 0.002 * scale, "Breast apices are not bilaterally symmetric in X"
        assert abs(l_apex[1] - r_apex[1]) < 0.002 * scale, "Breast apices are not bilaterally symmetric in Y"
        assert abs(l_apex[2] - r_apex[2]) < 0.002 * scale, "Breast apices are not bilaterally symmetric in Z"

        # Inter-nipple distance
        inter_nipple_dist = float(np.linalg.norm(l_apex - r_apex))
        normalized_dist = inter_nipple_dist / scale
        assert 0.14 <= normalized_dist <= 0.22, (
            f"Inter-nipple distance {normalized_dist*100:.1f}cm outside anatomical range (14.0 - 22.0cm)"
        )

        # Inframammary fold (IMF) local depth at breast meridian
        # Slice through left breast at X in [l_apex[0] - 0.015*scale, l_apex[0] + 0.015*scale]
        meridian_verts = v[
            (np.abs(v[:, 0] - l_apex[0]) <= 0.015 * scale) &
            (v[:, 2] >= 1.05 * scale) & (v[:, 2] <= 1.12 * scale) &
            (v[:, 1] < 0.0)
        ]
        assert len(meridian_verts) > 0, "No vertices found at inframammary fold meridian"
        imf_chest_wall_y = np.max(meridian_verts[:, 1])
        local_imf_depth_mm = (imf_chest_wall_y - l_apex[1]) * 1000.0 / scale
        assert local_imf_depth_mm > 15.0, (
            f"Local IMF depth {local_imf_depth_mm:.1f}mm is <= 15.0mm requirement"
        )

        # Sternal cleavage valley: depression along midline X ~ 0 at bust level
        sternum_verts = v[
            (np.abs(v[:, 0]) < 0.015 * scale) &
            (np.abs(v[:, 2] - l_apex[2]) < 0.03 * scale)
        ]
        assert len(sternum_verts) > 0, "No sternal midline vertices found"
        sternum_y = np.max(sternum_verts[:, 1])
        cleavage_recession_mm = (sternum_y - l_apex[1]) * 1000.0 / scale
        assert cleavage_recession_mm >= 25.0, (
            f"Sternal cleavage valley depth {cleavage_recession_mm:.1f}mm is too flat (< 25.0mm)"
        )

        # Gravity sag: asymmetric fullness
        # Lower pole (below apex) vs Upper pole (above apex) on anterior breast surface
        dz_test = 0.04 * scale
        upper_pole = v[
            (v[:, 2] >= l_apex[2] + 0.01 * scale) & (v[:, 2] <= l_apex[2] + dz_test) &
            (v[:, 0] > 0.05 * scale) & (v[:, 0] < 0.12 * scale) & (v[:, 1] < -0.05 * scale)
        ]
        lower_pole = v[
            (v[:, 2] <= l_apex[2] - 0.01 * scale) & (v[:, 2] >= l_apex[2] - dz_test) &
            (v[:, 0] > 0.05 * scale) & (v[:, 0] < 0.12 * scale) & (v[:, 1] < -0.05 * scale)
        ]
        assert len(upper_pole) > 0 and len(lower_pole) > 0
        # Lower pole dependent fullness: forward projection (-Y) of lower pole exceeds upper pole slope
        mean_upper_y = np.mean(upper_pole[:, 1])
        mean_lower_y = np.mean(lower_pole[:, 1])
        # In anterior direction (-Y), lower pole extends further forward than upper pole
        assert mean_lower_y < mean_upper_y, (
            f"Breast lacks gravity sag: upper pole Y={mean_upper_y:.4f} vs lower pole Y={mean_lower_y:.4f}"
        )

    # --------------------------------------------------------------------------
    # 2. GLUTEAL CURVATURE & WHR
    # --------------------------------------------------------------------------

    @pytest.mark.parametrize("height", [1.40, 1.65, 1.95])
    def test_gluteal_curvature_whr_and_shelf_projection(self, height: float):
        """
        Adversarially verifies:
        - Transverse waist width vs hip width yields feminine WHR ~0.697 (0.67 - 0.72).
        - Posterior gluteal shelf projection: gluteus maximus protrudes significantly beyond lumbar valley (>= 60mm).
        - Natural lumbar lordosis curve.
        """
        scale = height / 1.65
        res = generate_human_base_mesh(HumanAnatomyConfig(height=height))
        v = np.array(res.mesh.vertices)

        # Waist and Hip transverse widths
        waist_verts = v[(v[:, 2] >= 0.98 * scale) & (v[:, 2] <= 1.04 * scale) & (np.abs(v[:, 0]) < 0.20 * scale)]
        hip_verts = v[(v[:, 2] >= 0.82 * scale) & (v[:, 2] <= 0.88 * scale) & (np.abs(v[:, 0]) < 0.25 * scale)]
        assert len(waist_verts) > 50 and len(hip_verts) > 50

        w_width = float(np.ptp(waist_verts[:, 0]))
        h_width = float(np.ptp(hip_verts[:, 0]))
        whr = w_width / h_width

        assert 0.67 <= whr <= 0.72, (
            f"Waist-to-hip ratio WHR={whr:.4f} deviates from feminine target ~0.697 (allowed [0.67, 0.72])"
        )

        # Posterior gluteal shelf projection
        # Lumbar valley (dorsal midline minimum +Y)
        lumbar_midline = v[
            (v[:, 2] >= 1.00 * scale) & (v[:, 2] <= 1.10 * scale) &
            (np.abs(v[:, 0]) < 0.02 * scale) & (v[:, 1] > 0.0)
        ]
        assert len(lumbar_midline) > 0, "Missing lumbar lordosis midline vertices"
        lumbar_min_y = float(np.min(lumbar_midline[:, 1]))

        # Gluteus maximus apex (+Y posterior peak)
        gluteal_verts = v[
            (v[:, 2] >= 0.80 * scale) & (v[:, 2] <= 0.90 * scale) &
            (v[:, 1] > 0.0)
        ]
        assert len(gluteal_verts) > 50, "Missing gluteal vertices"
        gluteal_max_y = float(np.max(gluteal_verts[:, 1]))

        shelf_projection_mm = (gluteal_max_y - lumbar_min_y) * 1000.0 / scale
        assert shelf_projection_mm >= 60.0, (
            f"Posterior gluteal shelf projection {shelf_projection_mm:.1f}mm is insufficient (< 60.0mm)"
        )

    # --------------------------------------------------------------------------
    # 3. SHOULDER CONTOUR & AXILLARY INTEGRITY
    # --------------------------------------------------------------------------

    def test_shoulder_contour_relaxed_trapezius_and_axilla(self):
        """
        Adversarially verifies:
        - Relaxed trapezius slope angle: landmark vector (neck to joint-l-shoulder) is 24.2° ± 2°.
        - Surface regression confirms downward slope eliminating horizontal shelf (slope angle >= 15°).
        - Axillary loop is continuous, watertight 2-manifold with zero boundary edges and zero non-manifold edges.
        """
        res = generate_human_base_mesh(HumanAnatomyConfig(height=1.65))
        mesh = res.mesh
        v = np.array(mesh.vertices)
        lm = res.landmarks

        # 1. Landmark trapezius vector
        neck_lm = lm["neck"]
        joint_sh_lm = lm["joint-l-shoulder"]
        dx_lm = abs(joint_sh_lm[0] - neck_lm[0])
        dz_lm = neck_lm[2] - joint_sh_lm[2]
        angle_lm = math.degrees(math.atan2(dz_lm, dx_lm))

        assert 22.2 <= angle_lm <= 26.2, (
            f"Landmark trapezius angle {angle_lm:.2f}° deviates from requirement 24.2° ± 2° ([22.2°, 26.2°])"
        )

        # 2. Surface slope: verify elimination of horizontal shelf defect
        # Sample points along trapezius from neck base (X ~ 0.06m) to acromion (X ~ 0.19m)
        p_neck = min(mesh.vertices, key=lambda pt: (pt[0] - 0.0616) ** 2 + pt[1] ** 2 + (pt[2] - 1.4027) ** 2)
        p_acrom = min(mesh.vertices, key=lambda pt: (pt[0] - 0.1872) ** 2 + pt[1] ** 2 + (pt[2] - 1.3463) ** 2)
        dx_surf = p_acrom[0] - p_neck[0]
        dz_surf = p_neck[2] - p_acrom[2]
        angle_surf = math.degrees(math.atan2(dz_surf, dx_surf))

        assert 15.0 <= angle_surf <= 35.0, (
            f"Surface trapezius slope {angle_surf:.2f}° outside natural anatomical range (15°-35°)"
        )

        # 3. Axillary loop: watertight topology (no open armpit holes or pauldron cracks)
        non_manifold, boundary = extract_edge_topology(mesh.faces)
        assert len(boundary) == 0, f"Detected {len(boundary)} open boundary edges in mesh"
        assert len(non_manifold) == 0, f"Detected {len(non_manifold)} non-manifold edges in mesh"

    # --------------------------------------------------------------------------
    # 4. 5-TOED ARTICULATED FEET & PLANTAR ARCH
    # --------------------------------------------------------------------------

    @pytest.mark.parametrize("height", [1.40, 1.65, 1.95])
    def test_5_toed_articulated_feet_profile_and_cleft(self, height: float):
        """
        Adversarially verifies:
        - 5-toed articulated feet: Greek/Roman toe profile (Toe 2 apex aligned with Hallux within 8mm).
        - Interdigital cleft gap between Hallux and Toe 2: 3D Euclidean clearance >= 4.5mm.
        - Medial plantar arch elevated >= 6.0mm above floor contact plane.
        """
        scale = height / 1.65
        res = generate_human_base_mesh(HumanAnatomyConfig(height=height))
        mesh = res.mesh
        v = np.array(mesh.vertices)
        lm = res.landmarks

        foot_L_indices = res.vertex_groups["foot_L"]
        foot_pts = v[foot_L_indices]
        assert len(foot_pts) >= 1000, f"Foot vertex count too low ({len(foot_pts)})"

        # Medial plantar arch elevation
        floor_z = float(np.min(foot_pts[:, 2]))
        # Medial arch bounding region (instep): medial X < cx_ankle, Y in midfoot
        cx_ankle = lm["ankle_L"][0]
        arch_region = foot_pts[
            (foot_pts[:, 1] >= -0.045 * scale) & (foot_pts[:, 1] <= 0.025 * scale) &
            (foot_pts[:, 0] < cx_ankle)
        ]
        assert len(arch_region) > 0, "No arch vertices found in medial instep"
        arch_min_z = float(np.min(arch_region[:, 2]))
        arch_elev_mm = (arch_min_z - floor_z) * 1000.0 / scale
        assert arch_elev_mm >= 6.0, (
            f"Medial plantar arch elevation {arch_elev_mm:.2f}mm is below requirement (>= 6.0mm)"
        )

        # Interdigital cleft between Hallux and Toe 2
        x_split_01 = cx_ankle - 0.0155 * scale
        x_split_12 = cx_ankle + 0.00175 * scale
        hallux_pts = foot_pts[(foot_pts[:, 1] < -0.090 * scale) & (foot_pts[:, 0] < x_split_01)]
        toe2_pts = foot_pts[
            (foot_pts[:, 1] < -0.090 * scale) &
            (foot_pts[:, 0] >= x_split_01) & (foot_pts[:, 0] < x_split_12)
        ]
        assert len(hallux_pts) > 0 and len(toe2_pts) > 0, "Failed to segment Hallux and Toe 2"

        # Greek / Roman toe alignment: Toe 2 tip Y vs Hallux tip Y
        hallux_tip_y = float(np.min(hallux_pts[:, 1]))
        toe2_tip_y = float(np.min(toe2_pts[:, 1]))
        toe_diff_mm = (toe2_tip_y - hallux_tip_y) * 1000.0 / scale
        # Toe 2 should not be significantly recessed behind Hallux (recession <= 8.0mm)
        assert toe_diff_mm <= 8.0, (
            f"Toe 2 is recessed {toe_diff_mm:.2f}mm behind Hallux (exceeds 8.0mm tolerance)"
        )

        # 3D Euclidean clearance between Hallux and Toe 2
        diff_pts = hallux_pts[:, np.newaxis, :] - toe2_pts[np.newaxis, :, :]
        dists_3d = np.linalg.norm(diff_pts, axis=2)
        min_3d_gap_mm = float(np.min(dists_3d)) * 1000.0 / scale
        assert min_3d_gap_mm >= 4.50, (
            f"Interdigital cleft 3D Euclidean gap {min_3d_gap_mm:.2f}mm is below requirement (>= 4.50mm)"
        )

        # Transverse gap
        transverse_gap_mm = (np.min(toe2_pts[:, 0]) - np.max(hallux_pts[:, 0])) * 1000.0 / scale
        assert transverse_gap_mm >= 4.50, (
            f"Interdigital cleft transverse gap {transverse_gap_mm:.2f}mm is below requirement (>= 4.50mm)"
        )


# ==============================================================================
# STANDALONE ADVERSARIAL AUDIT EXECUTION
# ==============================================================================

def run_adversarial_empirical_audit():
    """Executes all adversarial audits and prints formatted empirical table."""
    print("=" * 80)
    print("EMPIRICAL CHALLENGER 1: ADVERSARIAL ANATOMY & CONTOURS VERIFICATION")
    print("=" * 80)

    res = generate_human_base_mesh(HumanAnatomyConfig(height=1.65))
    mesh = res.mesh
    v = np.array(mesh.vertices)
    lm = res.landmarks

    # 1. Teardrop Bust
    chest_verts = v[(v[:, 2] >= 1.10) & (v[:, 2] <= 1.25) & (v[:, 1] < -0.05)]
    l_breast = chest_verts[chest_verts[:, 0] > 0.04]
    r_breast = chest_verts[chest_verts[:, 0] < -0.04]
    l_apex = l_breast[np.argmin(l_breast[:, 1])]
    r_apex = r_breast[np.argmin(r_breast[:, 1])]
    inter_nipple_cm = float(np.linalg.norm(l_apex - r_apex)) * 100.0

    meridian_verts = v[
        (np.abs(v[:, 0] - l_apex[0]) <= 0.015) &
        (v[:, 2] >= 1.05) & (v[:, 2] <= 1.12) & (v[:, 1] < 0.0)
    ]
    imf_depth_mm = (np.max(meridian_verts[:, 1]) - l_apex[1]) * 1000.0

    sternum_verts = v[(np.abs(v[:, 0]) < 0.015) & (np.abs(v[:, 2] - l_apex[2]) < 0.03)]
    cleavage_recession_mm = (np.max(sternum_verts[:, 1]) - l_apex[1]) * 1000.0

    dz_test = 0.04
    upper_pole = v[(v[:, 2] >= l_apex[2] + 0.01) & (v[:, 2] <= l_apex[2] + dz_test) & (v[:, 0] > 0.05) & (v[:, 0] < 0.12) & (v[:, 1] < -0.05)]
    lower_pole = v[(v[:, 2] <= l_apex[2] - 0.01) & (v[:, 2] >= l_apex[2] - dz_test) & (v[:, 0] > 0.05) & (v[:, 0] < 0.12) & (v[:, 1] < -0.05)]
    sag_diff_mm = (np.mean(upper_pole[:, 1]) - np.mean(lower_pole[:, 1])) * 1000.0

    # 2. Gluteal & WHR
    waist_verts = v[(v[:, 2] >= 0.98) & (v[:, 2] <= 1.04) & (np.abs(v[:, 0]) < 0.20)]
    hip_verts = v[(v[:, 2] >= 0.82) & (v[:, 2] <= 0.88) & (np.abs(v[:, 0]) < 0.25)]
    whr = float(np.ptp(waist_verts[:, 0])) / float(np.ptp(hip_verts[:, 0]))

    lumbar_midline = v[(v[:, 2] >= 1.00) & (v[:, 2] <= 1.10) & (np.abs(v[:, 0]) < 0.02) & (v[:, 1] > 0.0)]
    gluteal_verts = v[(v[:, 2] >= 0.80) & (v[:, 2] <= 0.90) & (v[:, 1] > 0.0)]
    gluteal_projection_mm = (np.max(gluteal_verts[:, 1]) - np.min(lumbar_midline[:, 1])) * 1000.0

    # 3. Shoulder & Axilla
    neck_lm = lm["neck"]
    joint_sh_lm = lm["joint-l-shoulder"]
    angle_lm = math.degrees(math.atan2(neck_lm[2] - joint_sh_lm[2], abs(joint_sh_lm[0] - neck_lm[0])))

    p_neck = min(mesh.vertices, key=lambda pt: (pt[0] - 0.0616) ** 2 + pt[1] ** 2 + (pt[2] - 1.4027) ** 2)
    p_acrom = min(mesh.vertices, key=lambda pt: (pt[0] - 0.1872) ** 2 + pt[1] ** 2 + (pt[2] - 1.3463) ** 2)
    angle_surf = math.degrees(math.atan2(p_neck[2] - p_acrom[2], p_acrom[0] - p_neck[0]))

    non_manifold, boundary = extract_edge_topology(mesh.faces)

    # 4. Feet
    foot_pts = v[res.vertex_groups["foot_L"]]
    cx_ankle = lm["ankle_L"][0]
    arch_region = foot_pts[(foot_pts[:, 1] >= -0.045) & (foot_pts[:, 1] <= 0.025) & (foot_pts[:, 0] < cx_ankle)]
    arch_elev_mm = (np.min(arch_region[:, 2]) - np.min(foot_pts[:, 2])) * 1000.0

    x_split_01 = cx_ankle - 0.0155
    x_split_12 = cx_ankle + 0.00175
    hallux_pts = foot_pts[(foot_pts[:, 1] < -0.090) & (foot_pts[:, 0] < x_split_01)]
    toe2_pts = foot_pts[(foot_pts[:, 1] < -0.090) & (foot_pts[:, 0] >= x_split_01) & (foot_pts[:, 0] < x_split_12)]

    toe_diff_mm = (np.min(toe2_pts[:, 1]) - np.min(hallux_pts[:, 1])) * 1000.0
    diff_pts = hallux_pts[:, np.newaxis, :] - toe2_pts[np.newaxis, :, :]
    min_3d_gap_mm = float(np.min(np.linalg.norm(diff_pts, axis=2))) * 1000.0
    transverse_gap_mm = (np.min(toe2_pts[:, 0]) - np.max(hallux_pts[:, 0])) * 1000.0

    # Print Table
    results = [
        ("Bust: Inframammary Fold Depth", f"{imf_depth_mm:.1f} mm", "> 15.0 mm", "PASS" if imf_depth_mm > 15.0 else "FAIL"),
        ("Bust: Inter-Nipple Distance", f"{inter_nipple_cm:.1f} cm", "14.0 - 22.0 cm", "PASS" if 14.0 <= inter_nipple_cm <= 22.0 else "FAIL"),
        ("Bust: Sternal Cleavage Recession", f"{cleavage_recession_mm:.1f} mm", ">= 25.0 mm", "PASS" if cleavage_recession_mm >= 25.0 else "FAIL"),
        ("Bust: Gravity Sag Dependent Delta", f"{sag_diff_mm:.1f} mm", "> 0.0 mm", "PASS" if sag_diff_mm > 0.0 else "FAIL"),
        ("Gluteal: Waist-to-Hip Ratio (WHR)", f"{whr:.4f}", "0.67 - 0.72 (~0.697)", "PASS" if 0.67 <= whr <= 0.72 else "FAIL"),
        ("Gluteal: Posterior Shelf Projection", f"{gluteal_projection_mm:.1f} mm", ">= 60.0 mm", "PASS" if gluteal_projection_mm >= 60.0 else "FAIL"),
        ("Shoulder: Relaxed Trapezius Angle", f"{angle_lm:.2f}° (lm) / {angle_surf:.2f}° (surf)", "24.2° ± 2.0° (lm) / 15°-35°", "PASS" if 22.2 <= angle_lm <= 26.2 and 15.0 <= angle_surf <= 35.0 else "FAIL"),
        ("Shoulder: Axillary Loop Topology", f"Bnd={len(boundary)}, NonMan={len(non_manifold)}", "Bnd=0, NonMan=0", "PASS" if len(boundary) == 0 and len(non_manifold) == 0 else "FAIL"),
        ("Feet: Greek Toe Alignment Delta", f"{toe_diff_mm:.2f} mm", "<= 8.0 mm", "PASS" if toe_diff_mm <= 8.0 else "FAIL"),
        ("Feet: Interdigital Cleft 3D Gap", f"{min_3d_gap_mm:.2f} mm", ">= 4.50 mm", "PASS" if min_3d_gap_mm >= 4.50 else "FAIL"),
        ("Feet: Interdigital Cleft Transverse Gap", f"{transverse_gap_mm:.2f} mm", ">= 4.50 mm", "PASS" if transverse_gap_mm >= 4.50 else "FAIL"),
        ("Feet: Medial Plantar Arch Elevation", f"{arch_elev_mm:.2f} mm", ">= 6.00 mm", "PASS" if arch_elev_mm >= 6.00 else "FAIL"),
    ]

    print(f"{'#':<3} | {'Dimension':<38} | {'Measurement':<26} | {'Target / Threshold':<20} | {'Status':<6}")
    print("-" * 105)
    all_pass = True
    for i, (dim, meas, target, status) in enumerate(results, 1):
        print(f"{i:<3} | {dim:<38} | {meas:<26} | {target:<20} | {status:<6}")
        if status != "PASS":
            all_pass = False
    print("-" * 105)

    verdict = "APPROVE" if all_pass else "REQUEST_CHANGES"
    print(f"\n>>> FINAL VERDICT: {verdict} <<<\n")
    return all_pass


if __name__ == "__main__":
    success = run_adversarial_empirical_audit()
    import sys
    sys.exit(0 if success else 1)
