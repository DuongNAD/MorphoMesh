"""
Empirical Challenger Test Suite for MorphoMesh Milestone M2.
Challenger M2.2: Sandals, Sash and Multi-Scale Stress Audit (1.40m to 1.95m).

Authoritative Mandates:
1. Sandals sole length <= 0.25m across scales (1.40m to 1.95m).
2. Sole height <= 50.0mm.
3. 100% bare toes exposure: toe clearance >= 7.0mm from metatarsal strap to distal toe tips per media_1788785935849.jpg.
4. 0 skin penetrations between sandal straps and 5-toed foot mesh.
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple
import pytest
import numpy as np

from morphomesh.human_generator import generate_human_base_mesh, HumanAnatomyConfig
from morphomesh.wardrobe import (
    generate_flat_strappy_sandals,
    generate_organic_dress,
    generate_waist_sash_and_bow,
)
from tests.test_challenger_m3_sandals import compute_signed_distance_to_foot


class TestSandalsMultiScaleStress:
    """Stress-tests sandals across full human scale spectrum H in [1.40m, 1.95m]."""

    @pytest.mark.parametrize("H", [1.40, 1.50, 1.65, 1.80, 1.90, 1.95])
    def test_sandals_sole_length_bound_across_scales(self, H: float):
        """Sandals sole length <= 0.25m across scales (1.40m to 1.95m)."""
        sandals = generate_flat_strappy_sandals(height=H, scale=1.0)
        for side in ["L", "R"]:
            mesh = sandals[f"Mesh_Sandal_{side}"]
            ys = [v[1] for v in mesh.vertices]
            total_len = max(ys) - min(ys)
            assert total_len <= 0.25, (
                f"Sandal length violation at H={H:.2f}m: length is {total_len:.4f}m > 0.25m"
            )

    @pytest.mark.parametrize("H", [1.40, 1.50, 1.65, 1.80, 1.90, 1.95])
    def test_sandals_height_bound_across_scales(self, H: float):
        """Sole/footwear height <= 50.0mm across scales (1.40m to 1.95m)."""
        sandals = generate_flat_strappy_sandals(height=H, scale=1.0)
        for side in ["L", "R"]:
            mesh = sandals[f"Mesh_Sandal_{side}"]
            zs = [v[2] for v in mesh.vertices]
            height_mm = (max(zs) - min(zs)) * 1000.0
            assert height_mm <= 50.0, (
                f"Sandal height violation at H={H:.2f}m: height is {height_mm:.2f}mm > 50.0mm"
            )

    @pytest.mark.parametrize("H", [1.40, 1.50, 1.65, 1.80, 1.90, 1.95])
    def test_sandals_toes_exposure_and_clearance(self, H: float):
        """100% bare toes exposure: toe clearance >= 7.0mm from metatarsal strap to distal toe tips."""
        cfg = HumanAnatomyConfig(height=H)
        res = generate_human_base_mesh(config=cfg)
        sandals = generate_flat_strappy_sandals(foot_landmarks=res.landmarks, height=H, scale=1.0)
        mesh_l = sandals["Mesh_Sandal_L"]

        strap_y = [v[1] for v in mesh_l.vertices[170:]]
        min_strap_y = min(strap_y)

        foot_v_indices = set(res.mesh.vertex_groups.get("foot_L", []))
        foot_pts = [res.mesh.vertices[vi] for vi in foot_v_indices]
        scale_ratio = H / 1.65
        tb_y = min(v[1] for v in foot_pts if v[0] < 0.08 * scale_ratio)
        t5_y = min(v[1] for v in foot_pts if v[0] > 0.11 * scale_ratio)

        big_toe_clearance_mm = (min_strap_y - tb_y) * 1000.0
        pinky_toe_clearance_mm = (min_strap_y - t5_y) * 1000.0

        assert big_toe_clearance_mm >= 7.0, (
            f"Big toe clearance failure at H={H:.2f}m: {big_toe_clearance_mm:.2f}mm < 7.0mm"
        )
        assert pinky_toe_clearance_mm >= 7.0, (
            f"Pinky toe clearance failure at H={H:.2f}m: {pinky_toe_clearance_mm:.2f}mm < 7.0mm"
        )

    @pytest.mark.parametrize("H", [1.40, 1.50, 1.65, 1.80, 1.90, 1.95])
    def test_sandals_zero_skin_penetration(self, H: float):
        """0 skin penetrations between sandal straps and 5-toed foot mesh."""
        cfg = HumanAnatomyConfig(height=H)
        res = generate_human_base_mesh(config=cfg)
        sandals = generate_flat_strappy_sandals(foot_landmarks=res.landmarks, height=H, scale=1.0)
        mesh_l = sandals["Mesh_Sandal_L"]

        dists = compute_signed_distance_to_foot(mesh_l.vertices[170:], res.mesh, "foot_L")
        penetrations = [(i, d, loc) for (i, d, loc, norm) in dists if d < 0.0]
        min_signed_dist = min(d[1] for d in dists) * 1000.0

        assert len(penetrations) == 0, (
            f"Skin penetration failure at H={H:.2f}m: {len(penetrations)} penetrating vertices detected. "
            f"Min signed distance: {min_signed_dist:.2f}mm."
        )


class TestSashMultiScaleStress:
    """Stress-tests waist sash clearance across full scale spectrum."""

    @pytest.mark.parametrize("H", [1.40, 1.65, 1.95])
    @pytest.mark.parametrize("kw", [0.85, 1.00, 1.20])
    def test_sash_clearance_bodice_and_skirt(self, H: float, kw: float):
        """Waist sash maintains positive clearance >= 2.0mm over bodice and skirt."""
        s = H / 1.65
        dress = generate_organic_dress(scale=s, k_waist=kw)
        bodice = dress["Dress_Bodice"]
        skirt = dress["Dress_OrganicSkirt"]
        sash = generate_waist_sash_and_bow(scale=s, k_waist=kw)["Dress_WaistSash"]

        b_pts = bodice.vertices
        sk_pts = skirt.vertices
        band_verts = sash.vertices[:120]

        d_bodice = min(min(math.dist(sv, bv) for bv in b_pts) for sv in band_verts) * 1000.0
        d_skirt = min(min(math.dist(sv, sk) for sk in sk_pts) for sv in band_verts) * 1000.0

        assert d_bodice >= 2.0, f"Sash bodice clearance failure at H={H:.2f}m, kw={kw}: {d_bodice:.2f}mm < 2.0mm"
        assert d_skirt >= 2.0, f"Sash skirt clearance failure at H={H:.2f}m, kw={kw}: {d_skirt:.2f}mm < 2.0mm"
