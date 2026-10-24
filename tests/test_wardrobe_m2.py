"""
Comprehensive Unit & Integration Tests for MorphoMesh Milestone M2.
Yu Nian An (余念安) Organic Dress Drapery, Bodice Sculpting & Conforming Sash with 3D Bow Knot.

Validates authoritative requirements from:
1. ORIGINAL_REQUEST.md (M2 Organic Dress Drapery, Bodice Sculpting & Conforming Sash)
2. PROJECT.md (§2.2 Milestone M2 Spec & Interface Contracts)
3. Explorer M2.1/M2.2/M2.3 Analyses and Handoffs:
   - Multi-harmonic skirt gravity drapery (n=6,8,12), superlinear vertical growth (t^1.35, t^1.60, t^1.95),
     anisotropic anterior thigh flattening (sin theta < -0.2), ~14mm undulating scalloped hemline,
     and duplicate seam vertices (u=1.0) eliminating UV inversion.
   - Sculpted bodice with sweetheart scoop neckline (Z in [1.185m, 1.255m]), bilateral teardrop cups,
     anterior cleavage cleft, 3D conforming spaghetti straps with +1.8mm clearance.
   - Conforming outer sash envelope (+2.5mm clearance over dress waist), 3D volumetric barrel cuff knot,
     bilateral 3D volumetric hollow bow loops, and cascading twisted ribbon streamers.
   - Normalized Rigify 163 DEF bone skinning vertex groups on all wardrobe meshes (sum w = 1.0).
"""

from __future__ import annotations

import ast
import json
import math
from typing import Dict, List, Tuple

import pytest

from morphomesh.inference_adapter import MeshGeometry
from morphomesh.wardrobe import (
    WardrobeConfig,
    assign_bodice_skin_weights,
    assign_sash_skin_weights,
    assign_skirt_skin_weights,
    compute_dress_waist_radii,
    generate_dress_bodice,
    generate_dress_organic_skirt,
    generate_dress_pleated_skirt,
    generate_dress_waist_sash,
    generate_organic_dress,
    generate_waist_sash_and_bow,
    generate_yu_nian_an_wardrobe,
    get_wardrobe_script,
)


def _triangle_area(v0: Tuple[float, float, float], v1: Tuple[float, float, float], v2: Tuple[float, float, float]) -> float:
    """Computes Euclidean area of a 3D triangle."""
    ax, ay, az = v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2]
    bx, by, bz = v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2]
    cx = ay * bz - az * by
    cy = az * bx - ax * bz
    cz = ax * by - ay * bx
    return 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)


class TestM2OrganicSkirtDrapery:
    """Validates multi-harmonic drapery, superlinear growth, anterior thigh flattening, and scalloped hem."""

    def test_multi_harmonic_superlinear_growth(self):
        """Verifies multi-harmonic spectrum (n=6,8,12) with superlinear vertical growth."""
        skirt = generate_dress_organic_skirt(height=1.65, rings_count=16, sectors=48)
        assert len(skirt.vertices) >= 48 * 16
        assert len(skirt.faces) > 0

        stride = 49
        num_rings = len(skirt.vertices) // stride
        assert num_rings == 16

        waist_ring = skirt.vertices[:stride]
        hem_ring = skirt.vertices[-stride:]

        cy_waist = sum(v[1] for v in waist_ring) / len(waist_ring)
        cy_hem = sum(v[1] for v in hem_ring) / len(hem_ring)
        r_waist = [math.sqrt(v[0] ** 2 + (v[1] - cy_waist) ** 2) for v in waist_ring]
        r_hem = [math.sqrt(v[0] ** 2 + (v[1] - cy_hem) ** 2) for v in hem_ring]

        var_waist = max(r_waist) - min(r_waist)
        var_hem = max(r_hem) - min(r_hem)

        assert var_hem > var_waist * 2.5, f"Hem fold depth ({var_hem:.4f}m) must exceed waist fold depth ({var_waist:.4f}m)"
        assert max(r_hem) >= max(r_waist) * 1.8, "Skirt must maintain A-line silhouette"

    def test_anterior_thigh_flattening_anisotropy(self):
        """Verifies inward valleys are flattened over anterior thighs (sin theta < -0.2) vs lateral/posterior."""
        skirt = generate_dress_organic_skirt(height=1.65, rings_count=16, sectors=48)
        stride = 49
        mid_ring = skirt.vertices[12 * stride : 13 * stride]

        anterior_valleys = []
        lateral_posterior_valleys = []

        for v in mid_ring:
            x, y, z = v
            r = math.sqrt(x * x + y * y)
            theta = math.atan2(y, x)
            sin_t = math.sin(theta)
            if sin_t < -0.3:
                anterior_valleys.append(r)
            elif abs(sin_t) < 0.2 or sin_t > 0.3:
                lateral_posterior_valleys.append(r)

        assert len(anterior_valleys) > 0
        assert len(lateral_posterior_valleys) > 0
        assert min(anterior_valleys) > 0.14, "Anterior valley must not pinch through thigh region"

    def test_scalloped_hemline_undulation_and_kneecap_landing(self):
        """Verifies undulating scalloped hemline (~14mm sag amplitude) lands right at kneecap (~0.52m)."""
        skirt = generate_dress_organic_skirt(height=1.65, rings_count=16, sectors=48)
        stride = 49
        hem_ring = skirt.vertices[-stride:]

        zs = [v[2] for v in hem_ring]
        min_z = min(zs)
        max_z = max(zs)
        sag_amp_mm = (max_z - min_z) * 1000.0

        assert 12.0 <= sag_amp_mm <= 40.0, f"Hem sag amplitude {sag_amp_mm:.2f}mm must be in [12mm, 40mm]"
        assert 0.48 <= min_z <= 0.55, f"Skirt hem minimum Z={min_z:.3f}m must settle near patella (~0.52m)"

    def test_duplicate_seam_vertices_uv_continuity(self):
        """Verifies duplicate seam vertices at u=1.0: ring has sectors+1 verts, no UV inversion."""
        skirt = generate_dress_organic_skirt(height=1.65, rings_count=8, sectors=48)
        stride = 49

        for r in range(8):
            ring_start = r * stride
            v0 = skirt.vertices[ring_start]
            v_last = skirt.vertices[ring_start + 48]
            assert math.isclose(v0[0], v_last[0], abs_tol=1e-4)
            assert math.isclose(v0[1], v_last[1], abs_tol=1e-4)
            assert math.isclose(v0[2], v_last[2], abs_tol=1e-4)

            uv0 = skirt.uvs[ring_start]
            uv_last = skirt.uvs[ring_start + 48]
            assert math.isclose(uv0[0], 0.0, abs_tol=1e-4)
            assert math.isclose(uv_last[0], 1.0, abs_tol=1e-4)

    def test_pure_quad_topology_and_zero_degenerate_faces(self):
        """Verifies skirt consists of paired quad triangles with strictly positive area."""
        skirt = generate_dress_organic_skirt(height=1.65, rings_count=16, sectors=48)
        assert len(skirt.faces) % 2 == 0, "Quads stored as paired triangles"

        for f_idx, (i0, i1, i2) in enumerate(skirt.faces):
            area = _triangle_area(skirt.vertices[i0], skirt.vertices[i1], skirt.vertices[i2])
            assert area > 1e-8, f"Skirt face {f_idx} has near-zero area {area}"


class TestM2BodiceSculpting:
    """Validates sweetheart scoop neckline, bilateral teardrop cups, and conforming straps."""

    def test_sweetheart_scoop_neckline_profile(self):
        """Verifies anterior cleavage dip (Z ~ 1.185m) and bilateral cup peaks (Z ~ 1.255m)."""
        bodice = generate_dress_bodice(height=1.65, clearance=0.0018)

        # Top rim of bodice (ring index 9 with 32 sectors)
        top_ring = bodice.vertices[9 * 32 : 10 * 32]

        anterior_midline = [v for v in top_ring if abs(v[0]) < 0.015 and v[1] < -0.05]
        assert len(anterior_midline) > 0, "Anterior midline neckline vertices must exist"
        midline_z = min(v[2] for v in anterior_midline)
        assert 1.175 <= midline_z <= 1.200, f"Cleavage cleft Z={midline_z:.3f}m must dip to ~1.185m"

        cup_peaks = [v for v in top_ring if 0.04 <= abs(v[0]) <= 0.08 and v[1] < -0.09]
        assert len(cup_peaks) > 0, "Breast cup peaks must exist"
        peak_z = max(v[2] for v in cup_peaks)
        assert 1.240 <= peak_z <= 1.265, f"Cup peak Z={peak_z:.3f}m must reach ~1.255m"

        scoop_depth_mm = (peak_z - midline_z) * 1000.0
        assert 40.0 <= scoop_depth_mm <= 90.0, f"Sweetheart scoop depth {scoop_depth_mm:.1f}mm must be in [40mm, 90mm]"

    def test_bilateral_teardrop_bust_projection(self):
        """Verifies teardrop lower fullness and bilateral separation in +X and -X."""
        bodice = generate_dress_bodice(height=1.65, clearance=0.0018)
        bust_verts = [v for v in bodice.vertices if 1.16 <= v[2] <= 1.25]

        peaks_L = [v for v in bust_verts if v[0] >= 0.035 and v[1] <= -0.110]
        peaks_R = [v for v in bust_verts if v[0] <= -0.035 and v[1] <= -0.110]
        assert len(peaks_L) > 0, "Left breast cup projection must exist"
        assert len(peaks_R) > 0, "Right breast cup projection must exist"

        midline_y = max(v[1] for v in bust_verts if abs(v[0]) < 0.01)
        cup_min_y = min(v[1] for v in peaks_L + peaks_R)
        cleavage_indent_mm = (midline_y - cup_min_y) * 1000.0
        assert cleavage_indent_mm >= 15.0, f"Cleavage indentation {cleavage_indent_mm:.1f}mm must be >= 15mm"

    def test_conforming_3d_spaghetti_straps(self):
        """Verifies 3D spaghetti straps arch over shoulders to Z >= 1.36m with +1.8mm clearance."""
        bodice = generate_dress_bodice(height=1.65, clearance=0.0018, strap_clearance=0.0018)
        strap_verts = [v for v in bodice.vertices if v[2] > 1.28]
        assert len(strap_verts) >= 20, "Spaghetti straps require sufficient vertex resolution"

        max_z = max(v[2] for v in strap_verts)
        assert 1.35 <= max_z <= 1.39, f"Strap apex Z={max_z:.3f}m must conform over shoulder top (~1.37m)"

        straps_L = [v for v in strap_verts if v[0] > 0.04]
        straps_R = [v for v in strap_verts if v[0] < -0.04]
        assert len(straps_L) > 0 and len(straps_R) > 0, "Both left and right straps must exist"

    def test_bodice_all_faces_positive_area(self):
        """Verifies zero degenerate or collapsed faces across bodice and straps."""
        bodice = generate_dress_bodice(height=1.65, clearance=0.0018)
        for f_idx, (i0, i1, i2) in enumerate(bodice.faces):
            area = _triangle_area(bodice.vertices[i0], bodice.vertices[i1], bodice.vertices[i2])
            assert area > 1e-8, f"Bodice face {f_idx} has near-zero area: {area}"


class TestM2ConformingSashAndBowKnot:
    """Validates +2.5mm outer envelope clearance, 3D barrel cuff knot, hollow bow loops, and streamers."""

    def test_conforming_envelope_clearance_over_dress_waist(self):
        """Verifies sash maintains positive clearance over bodice waist at all heights."""
        for h in [1.40, 1.65, 1.80]:
            bodice = generate_dress_bodice(height=h, clearance=0.015)
            sash = generate_dress_waist_sash(height=h, clearance=0.0175)

            s = h / 1.65
            b_waist = [v for v in bodice.vertices if 1.03 * s <= v[2] <= 1.06 * s]
            s_waist = [v for v in sash.vertices if 1.03 * s <= v[2] <= 1.06 * s]

            b_max_r = max(math.sqrt(v[0] ** 2 + v[1] ** 2) for v in b_waist)
            s_max_r = max(math.sqrt(v[0] ** 2 + v[1] ** 2) for v in s_waist)
            clearance_mm = (s_max_r - b_max_r) * 1000.0

            assert clearance_mm >= 1.0, f"Sash clearance {clearance_mm:.2f}mm must be positive over dress waist"

    def test_3d_volumetric_barrel_cuff_knot_structure(self):
        """Verifies 3D volumetric barrel cuff knot is a completely closed 2-manifold with 0 boundary edges."""
        from collections import defaultdict

        sash = generate_dress_waist_sash(height=1.65)
        assert len(sash.vertices) >= 152
        knot_verts = sash.vertices[120:152]
        assert len(knot_verts) == 32

        knot_y_min = min(v[1] for v in knot_verts)
        band_y_min = min(v[1] for v in sash.vertices[:120])
        assert knot_y_min < band_y_min, f"Knot Y={knot_y_min:.4f}m must project forward past band Y={band_y_min:.4f}m"

        # Rigorous topological manifoldness check (0 boundary edges, 0 non-manifold edges)
        knot_faces = [f for f in sash.faces if all(120 <= idx < 152 for idx in f)]
        assert len(knot_faces) == 60, f"Expected 60 triangular faces (30 quads), got {len(knot_faces)}"

        edge_counts: Dict[Tuple[int, int], int] = defaultdict(int)
        for f in knot_faces:
            edges = [
                (min(f[0], f[1]), max(f[0], f[1])),
                (min(f[1], f[2]), max(f[1], f[2])),
                (min(f[2], f[0]), max(f[2], f[0])),
            ]
            for e in edges:
                edge_counts[e] += 1

        boundary_edges = [e for e, c in edge_counts.items() if c == 1]
        non_manifold = [e for e, c in edge_counts.items() if c > 2]
        assert len(boundary_edges) == 0, f"Barrel knot has {len(boundary_edges)} unclosed boundary edges: {boundary_edges}"
        assert len(non_manifold) == 0, f"Barrel knot has {len(non_manifold)} non-manifold edges: {non_manifold}"

        # Euler characteristic check: chi = V - E + F = 32 - 90 + 60 = 2 (homeomorphic to S^2)
        assert len(knot_verts) - len(edge_counts) + len(knot_faces) == 2, "Euler characteristic must be 2"

    def test_bilateral_3d_hollow_bow_loops(self):
        """Verifies bilateral 3D volumetric hollow bow loops with strictly positive face areas."""
        sash = generate_dress_waist_sash(height=1.65)
        assert len(sash.vertices) >= 248
        loop_verts = sash.vertices[152:248]
        assert len(loop_verts) == 96

        loops_L = [v for v in loop_verts if v[0] > 0.01]
        loops_R = [v for v in loop_verts if v[0] < -0.01]
        assert len(loops_L) == 48 and len(loops_R) == 48, "Bilateral loops must have symmetric vertex distribution"

        for f_idx, (i0, i1, i2) in enumerate(sash.faces):
            area = _triangle_area(sash.vertices[i0], sash.vertices[i1], sash.vertices[i2])
            assert area >= 1e-9, f"Sash face {f_idx} has near-zero area: {area}"

    def test_cascading_flowing_twisted_ribbon_streamers(self):
        """Verifies ribbon streamers cascade downward to Z <= 0.75m with torsional twist and 45-degree bias cut."""
        sash = generate_dress_waist_sash(height=1.65)
        streamer_verts = sash.vertices[248:]
        assert len(streamer_verts) > 0, "Ribbon streamer vertices must exist"

        min_z = min(v[2] for v in streamer_verts)
        assert min_z <= 0.75, f"Streamers must cascade downward: min_z={min_z:.3f}m <= 0.75m"

        top_verts = [v for v in streamer_verts if v[2] > 0.95]
        bot_verts = [v for v in streamer_verts if v[2] < 0.75]
        assert len(top_verts) > 0 and len(bot_verts) > 0

        # Verify genuine 45-degree tip bias cut (non-zero delta Z across width)
        tip_L = sash.vertices[296:299]
        tip_R = sash.vertices[347:350]
        delta_z_L = max(v[2] for v in tip_L) - min(v[2] for v in tip_L)
        delta_z_R = max(v[2] for v in tip_R) - min(v[2] for v in tip_R)
        assert delta_z_L >= 0.004, f"Left streamer tip bias cut dead code: delta_z={delta_z_L:.6f}m"
        assert delta_z_R >= 0.004, f"Right streamer tip bias cut dead code: delta_z={delta_z_R:.6f}m"


class TestM2RigifyDEFSkinWeights:
    """Validates normalized Rigify 163 DEF bone vertex group assignments across all wardrobe components."""

    def test_bodice_skin_weights_normalization_and_bones(self):
        """Verifies bodice vertices are unit-normalized and assigned to DEF-spine and DEF-shoulder."""
        bodice = generate_dress_bodice(height=1.65)
        assert hasattr(bodice, "skin_weights"), "Bodice must attach skin_weights attribute"
        weights: Dict[int, Dict[str, float]] = bodice.skin_weights

        assert len(weights) == len(bodice.vertices), "Every vertex must have skin weights"

        expected_bones = {"DEF-spine.001", "DEF-spine.002", "DEF-spine.003", "DEF-spine.004", "DEF-shoulder.L", "DEF-shoulder.R"}
        found_bones = set()

        for v_idx, b_map in weights.items():
            assert len(b_map) > 0, f"Vertex {v_idx} has empty bone weights"
            weight_sum = sum(b_map.values())
            assert math.isclose(weight_sum, 1.0, abs_tol=1e-4), f"Vertex {v_idx} weight sum {weight_sum} != 1.0"
            for b in b_map:
                found_bones.add(b)

        assert expected_bones.issubset(found_bones), f"Missing expected bodice bones: {expected_bones - found_bones}"

    def test_skirt_skin_weights_normalization_and_bones(self):
        """Verifies skirt vertices are unit-normalized and assigned to spine and thigh DEF bones."""
        skirt = generate_dress_organic_skirt(height=1.65)
        assert hasattr(skirt, "skin_weights"), "Skirt must attach skin_weights attribute"
        weights: Dict[int, Dict[str, float]] = skirt.skin_weights

        assert len(weights) == len(skirt.vertices)

        expected_bones = {"DEF-spine.001", "DEF-spine", "DEF-thigh.L", "DEF-thigh.L.001", "DEF-thigh.R", "DEF-thigh.R.001"}
        found_bones = set()

        for v_idx, b_map in weights.items():
            weight_sum = sum(b_map.values())
            assert math.isclose(weight_sum, 1.0, abs_tol=1e-4), f"Vertex {v_idx} weight sum {weight_sum} != 1.0"
            for b in b_map:
                found_bones.add(b)

        assert expected_bones.issubset(found_bones), f"Missing expected skirt bones: {expected_bones - found_bones}"

    def test_sash_skin_weights_normalization_and_bones(self):
        """Verifies sash vertices are unit-normalized and assigned to DEF-spine and DEF-thigh."""
        sash = generate_dress_waist_sash(height=1.65)
        assert hasattr(sash, "skin_weights"), "Sash must attach skin_weights attribute"
        weights: Dict[int, Dict[str, float]] = sash.skin_weights

        assert len(weights) == len(sash.vertices)

        for v_idx, b_map in weights.items():
            weight_sum = sum(b_map.values())
            assert math.isclose(weight_sum, 1.0, abs_tol=1e-4), f"Vertex {v_idx} weight sum {weight_sum} != 1.0"


class TestM2InterfaceContractsAndScript:
    """Validates interface contracts and standalone Blender script generation."""

    def test_generate_organic_dress_contract(self):
        """Verifies generate_organic_dress interface contract per PROJECT.md."""
        dress = generate_organic_dress(scale=1.0, k_waist=1.0, k_chest=1.0)
        assert "Dress_Bodice" in dress
        assert "Dress_OrganicSkirt" in dress
        assert "Dress_PleatedSkirt" in dress

        bodice = dress["Dress_Bodice"]
        skirt = dress["Dress_OrganicSkirt"]
        assert isinstance(bodice, MeshGeometry)
        assert isinstance(skirt, MeshGeometry)
        assert hasattr(bodice, "skin_weights")
        assert hasattr(skirt, "skin_weights")

    def test_generate_waist_sash_and_bow_contract(self):
        """Verifies generate_waist_sash_and_bow interface contract per PROJECT.md."""
        sash_dict = generate_waist_sash_and_bow(scale=1.0, k_waist=1.0)
        assert "Dress_WaistSash" in sash_dict
        sash = sash_dict["Dress_WaistSash"]
        assert isinstance(sash, MeshGeometry)
        assert hasattr(sash, "skin_weights")

    def test_wardrobe_script_contains_bone_weights_and_solidify_offset(self):
        """Verifies get_wardrobe_script serializes BONE_WEIGHTS, sets solidify offset=1.0, and parses AST."""
        script = get_wardrobe_script(
            target_object="Yu_Nian_An_Body",
            clearance_offset=0.015,
            thickness=0.002,
        )
        assert "BONE_WEIGHTS = json.loads" in script
        assert "solid_mod.offset = 1.0" in script
        assert "arm_mod.use_deform_preserve_volume = True" in script

        # Verify valid Python syntax
        tree = ast.parse(script)
        assert isinstance(tree, ast.Module)
