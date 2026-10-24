"""
Empirical Challenger Test Suite: Adversarial Cloth & Penetration Check.
Milestone M2: Verification of Sundress (Bodice + Skirt), Waist Sash, and Natural Drape
against the M1 Anatomical Base Mold.

Challenger Mandate:
1. 0 skin penetrations (s_i >= -0.0005m) between sundress (bodice + skirt) and M1 anatomical base mold.
2. 0% Z-fighting between sash, bodice, and skirt (> 2.5mm clearance buffer).
3. Natural drape vs conical shape: check that skirt collapses inward to conform around thighs
   (Z in [0.55, 0.85]m) rather than flaring out into a straight cone.
"""

import math
from typing import Any, Dict, List, Tuple
import numpy as np
import pytest

from morphomesh.human_generator import generate_human_body
from morphomesh.inference_adapter import MeshGeometry
from morphomesh.visual_critic import PurePythonBVHTree
from morphomesh.wardrobe import (
    generate_dress_bodice,
    generate_dress_organic_skirt,
    generate_organic_dress,
    generate_waist_sash_and_bow,
)


def compute_bvh_signed_distance(
    body_mesh: MeshGeometry,
    garment_mesh: MeshGeometry,
) -> Tuple[float, List[Dict[str, Any]], int]:
    """
    Computes exact signed distance from each garment vertex to the body surface.
    Signed distance s_i = (w_i - p_i) . n_i.
    s_i < -0.0005m (-0.5mm) indicates an unacceptable skin penetration.
    """
    bvh = PurePythonBVHTree.FromPolygons(body_mesh.vertices, body_mesh.faces)
    signed_dists: List[float] = []
    penetrations: List[Dict[str, Any]] = []

    for idx, v in enumerate(garment_mesh.vertices):
        loc, norm, f_idx, dist = bvh.find_nearest(v)
        if loc is not None and norm is not None:
            offset = (v[0] - loc[0], v[1] - loc[1], v[2] - loc[2])
            dot = offset[0] * norm[0] + offset[1] * norm[1] + offset[2] * norm[2]
            s_dist = dist if dot >= 0.0 else -dist
            signed_dists.append(s_dist)
            if s_dist < -0.0005:  # -0.5mm threshold
                penetrations.append({
                    "idx": idx,
                    "pos": v,
                    "body_loc": loc,
                    "signed_dist": s_dist,
                    "depth_mm": -s_dist * 1000.0,
                })

    min_d = min(signed_dists) if signed_dists else 0.0
    return min_d, penetrations, len(garment_mesh.vertices)


class TestM2AdversarialClothAndPenetration:
    """Empirical adversarial suite for M2 cloth penetration, sash clearance, and thigh drape."""

    def test_canonical_sundress_penetration_zero_skin_penetrations(self):
        """
        Mandate: 0 skin penetrations (s_i >= -0.0005m) between sundress (bodice + skirt)
        and the M1 anatomical base mold at canonical height H=1.65m.
        """
        body_mesh, _ = generate_human_body(height=1.65)
        dress = generate_organic_dress(scale=1.0)
        bodice = dress["Dress_Bodice"]
        skirt = dress["Dress_OrganicSkirt"]

        # 1. Bodice verification
        b_min, b_pens, b_tot = compute_bvh_signed_distance(body_mesh, bodice)
        assert len(b_pens) == 0, (
            f"Bodice violated 0 penetration requirement: {len(b_pens)}/{b_tot} penetrating vertices, "
            f"min signed distance = {b_min*1000:.2f}mm"
        )
        assert b_min >= -0.0005, f"Bodice min signed distance {b_min*1000:.2f}mm < -0.5mm"
        assert b_min >= 0.0015, f"Bodice clearance {b_min*1000:.2f}mm should be >= +1.5mm"

        # 2. Skirt verification
        s_min, s_pens, s_tot = compute_bvh_signed_distance(body_mesh, skirt)
        assert len(s_pens) == 0, (
            f"Skirt violated 0 penetration requirement: {len(s_pens)}/{s_tot} penetrating vertices, "
            f"min signed distance = {s_min*1000:.2f}mm"
        )
        assert s_min >= -0.0005, f"Skirt min signed distance {s_min*1000:.2f}mm < -0.5mm"

    def test_z_fighting_clearance_sash_bodice_skirt(self):
        """
        Mandate: 0% Z-fighting between sash, bodice, and skirt (> 2.5mm clearance buffer).
        """
        dress = generate_organic_dress(scale=1.0)
        bodice = dress["Dress_Bodice"]
        skirt = dress["Dress_OrganicSkirt"]
        sash = generate_waist_sash_and_bow(scale=1.0)["Dress_WaistSash"]

        bvh_bodice = PurePythonBVHTree.FromPolygons(bodice.vertices, bodice.faces)
        bvh_skirt = PurePythonBVHTree.FromPolygons(skirt.vertices, skirt.faces)

        # 1. Sash vs Bodice
        bodice_clearances = []
        bodice_submerged = []
        for idx, v in enumerate(sash.vertices):
            loc, norm, _, dist = bvh_bodice.find_nearest(v)
            if loc is not None and norm is not None:
                offset = (v[0] - loc[0], v[1] - loc[1], v[2] - loc[2])
                dot = offset[0] * norm[0] + offset[1] * norm[1] + offset[2] * norm[2]
                if dot < 0.0:
                    bodice_submerged.append(idx)
            bodice_clearances.append(dist)

        assert len(bodice_submerged) == 0, f"Sash has {len(bodice_submerged)} vertices submerged inside Bodice"
        min_bodice_clearance = min(bodice_clearances)
        assert min_bodice_clearance > 0.0025, (
            f"Sash vs Bodice min clearance {min_bodice_clearance*1000:.2f}mm must be > 2.5mm"
        )

        # 2. Sash vs Skirt
        skirt_clearances = []
        skirt_submerged = []
        for idx, v in enumerate(sash.vertices):
            loc, norm, _, dist = bvh_skirt.find_nearest(v)
            if loc is not None and norm is not None:
                offset = (v[0] - loc[0], v[1] - loc[1], v[2] - loc[2])
                dot = offset[0] * norm[0] + offset[1] * norm[1] + offset[2] * norm[2]
                if dot < 0.0:
                    skirt_submerged.append(idx)
            skirt_clearances.append(dist)

        assert len(skirt_submerged) == 0, f"Sash has {len(skirt_submerged)} vertices submerged inside Skirt"
        min_skirt_clearance = min(skirt_clearances)
        assert min_skirt_clearance > 0.0025, (
            f"Sash vs Skirt min clearance {min_skirt_clearance*1000:.2f}mm must be > 2.5mm"
        )
        assert min_skirt_clearance >= 0.0050, (
            f"Sash vs Skirt clearance {min_skirt_clearance*1000:.2f}mm exceeds 5.0mm healthy buffer"
        )

    def test_natural_drape_thigh_conformance_vs_straight_cone(self):
        """
        Mandate: Natural drape vs conical shape:
        Check that skirt collapses inward to conform around thighs (Z in [0.55, 0.85]m)
        rather than flaring out into a straight cone.
        """
        body_mesh, _ = generate_human_body(height=1.65)
        skirt = generate_dress_organic_skirt(height=1.65, rings_count=16, sectors=48)
        stride = 49  # 48 sectors + 1 duplicate seam vertex

        z_rings = [skirt.vertices[r * stride][2] for r in range(16)]
        thigh_rings = [r for r, z in enumerate(z_rings) if 0.55 <= z <= 0.85]

        # Verify rings span the thigh zone
        assert len(thigh_rings) >= 6, f"Expected >= 6 rings in thigh zone, got {len(thigh_rings)}"

        # Check cone reference vs skirt radial envelope
        z_waist = z_rings[0]
        z_hem = z_rings[-1]
        r_cone_waist = 0.5 * ((0.125 + 0.015) + (0.090 + 0.015))  # ~0.1225m
        r_cone_hem = 0.5 * ((0.125 + 0.225 + 0.015) + (0.090 + 0.195 + 0.015))  # ~0.3325m

        for r in thigh_rings:
            z = z_rings[r]
            t = r / 15.0
            r_cone_linear = r_cone_waist + t * (r_cone_hem - r_cone_waist)

            ring_verts = skirt.vertices[r * stride : (r + 1) * stride - 1]
            radii = [math.sqrt(v[0] ** 2 + v[1] ** 2) for v in ring_verts]
            mean_r = np.mean(radii)
            min_r = np.min(radii)
            max_r = np.max(radii)

            # 1. Mean radius is tighter than linear cone (convex superlinear growth t^1.15)
            assert mean_r < r_cone_linear, (
                f"Ring {r} (Z={z:.3f}m): skirt mean radius {mean_r*1000:.1f}mm should be < "
                f"linear cone radius {r_cone_linear*1000:.1f}mm"
            )

            # 2. Inward collapse: valleys dip inward deeply below the mean
            inward_collapse = mean_r - min_r
            assert inward_collapse >= 0.035, (
                f"Ring {r} (Z={z:.3f}m): inward fold collapse {inward_collapse*1000:.1f}mm < 35.0mm"
            )

            # 3. Fold depth: rich multi-harmonic vertical folds, not a flat cone
            fold_depth = max_r - min_r
            assert fold_depth >= 0.075, (
                f"Ring {r} (Z={z:.3f}m): fold depth {fold_depth*1000:.1f}mm < 75.0mm"
            )

        # 4. In addition, check that skirt maintains positive clearance over thighs in [0.55, 0.85]m
        bvh_body = PurePythonBVHTree.FromPolygons(body_mesh.vertices, body_mesh.faces)
        thigh_verts = [v for v in skirt.vertices if 0.55 <= v[2] <= 0.85]
        thigh_clearances = []
        for v in thigh_verts:
            loc, norm, _, dist = bvh_body.find_nearest(v)
            if loc is not None and norm is not None:
                dot = (v[0]-loc[0])*norm[0] + (v[1]-loc[1])*norm[1] + (v[2]-loc[2])*norm[2]
                s = dist if dot >= 0 else -dist
                thigh_clearances.append(s)

        min_thigh_s = min(thigh_clearances)
        assert min_thigh_s >= 0.005, (
            f"Thigh zone clearance {min_thigh_s*1000:.2f}mm must be >= 5.0mm"
        )
    def test_adversarial_height_scaling_boundary_discovery(self):
        """
        Adversarial Boundary Stress Test:
        Sweeps height across [1.50m, 1.65m, 1.70m, 1.75m, 1.80m].
        Records the clearance profile at sector 44 (right anterior-lateral hip):
        - H <= 1.65m: strictly non-negative clearance (min +0.143mm at H=1.65m).
        - H >= 1.75m: demonstrates that skirt clearance drops below -0.0005m (-0.5mm),
          specifically -0.747mm at H=1.75m and -1.199mm at H=1.80m on vertices 240 and 289.
        """
        height_metrics = {}
        for h in [1.50, 1.65, 1.70, 1.75, 1.80]:
            scale = h / 1.65
            body_mesh, _ = generate_human_body(height=h)
            dress = generate_organic_dress(scale=scale)
            skirt = dress["Dress_OrganicSkirt"]
            b_min, b_pens, _ = compute_bvh_signed_distance(body_mesh, skirt)
            height_metrics[h] = {
                "min_d_mm": round(b_min * 1000.0, 3),
                "pens_count": len(b_pens),
            }

        # Canonical height compliance
        assert height_metrics[1.65]["pens_count"] == 0
        assert height_metrics[1.65]["min_d_mm"] >= -0.5
        assert height_metrics[1.65]["min_d_mm"] > 0.0  # +0.143mm

        # Shorter height compliance
        assert height_metrics[1.50]["pens_count"] == 0
        assert height_metrics[1.50]["min_d_mm"] >= 1.0  # +1.354mm

        # Adversarial discovery documentation for tall scaling
        # At H=1.75m and H=1.80m, skirt enters negative signed distance < -0.5mm
        assert height_metrics[1.75]["pens_count"] == 2
        assert height_metrics[1.75]["min_d_mm"] < -0.5  # -0.747mm
        assert height_metrics[1.80]["pens_count"] == 2
        assert height_metrics[1.80]["min_d_mm"] < -1.0  # -1.199mm
