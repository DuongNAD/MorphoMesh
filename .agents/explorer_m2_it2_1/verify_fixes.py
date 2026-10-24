import sys
sys.path.insert(0, "E:\\tool\\mcp\\MorphoMesh")
import math
from collections import defaultdict
from typing import Any, Dict, List, Optional
from morphomesh.inference_adapter import MeshGeometry
import morphomesh.wardrobe as wardrobe

orig_skirt_fn = wardrobe.generate_dress_organic_skirt
orig_sash_fn = wardrobe.generate_dress_waist_sash

# Patched skirt: CCW quad winding (v_bl, v_tl, v_tr, v_br)
def patched_organic_skirt(**kwargs):
    mesh = orig_skirt_fn(**kwargs)
    sectors = kwargs.get('sectors', 48)
    rings_count = kwargs.get('rings_count', 16)
    mesh.faces.clear()
    stride = sectors + 1
    rings = [list(range(r * stride, (r + 1) * stride)) for r in range(rings_count)]
    for r in range(rings_count - 1):
        for i in range(sectors):
            v_bl = rings[r][i]
            v_br = rings[r][i + 1]
            v_tr = rings[r + 1][i + 1]
            v_tl = rings[r + 1][i]
            mesh.add_quad(v_bl, v_tl, v_tr, v_br)
    return mesh

# Patched sash with:
# 1. Lower ring flare (dr=0.0020*s, dyo=0.0025*s with smooth flare)
# 2. Barrel knot 3rd quad on caps
# 3. Streamer tip_bias cut fix
def patched_waist_sash(
    height: float = 1.65,
    clearance: float = 0.020,
    belt_width: float = 0.045,
    sectors: int = 24,
    waist_girth: float = 0.58,
    chest_girth: float = 0.82,
    **kwargs: Any,
) -> MeshGeometry:
    mesh = MeshGeometry()
    s = height / 1.65
    k_w = waist_girth / 0.58
    k_c = chest_girth / 0.82

    z_center = 1.050 * s
    z_bottom = z_center - belt_width * 0.5 * s
    z_top = z_center + belt_width * 0.5 * s

    # 1. Conforming 5-Ring Sash Band
    num_rings = 5
    rings: List[List[int]] = []
    z_levels = [
        z_bottom,
        z_bottom + 0.25 * (z_top - z_bottom),
        z_center,  # Exactly 1.050 * s
        z_bottom + 0.75 * (z_top - z_bottom),
        z_top,
    ]

    for r_idx, z_curr in enumerate(z_levels):
        u_z = (z_curr - z_bottom) / max(1e-4, z_top - z_bottom)
        rx_b, ry_b, yo_can = wardrobe.compute_dress_waist_radii(z_curr, s=s, k_w=k_w, k_c=k_c, clearance=clearance)
        
        # Smooth flare adjustment for lower rings transitioning over the flared skirt
        flare = max(0.0, 1.0 - 2.0 * u_z)
        rx = rx_b + 0.0045 * s + 0.0020 * s * flare
        ry = ry_b + 0.0045 * s + 0.0020 * s * flare
        yo = yo_can + 0.0025 * s * flare

        ring: List[int] = []
        for i in range(sectors):
            theta = 2.0 * math.pi * i / sectors
            sin_t = math.sin(theta)
            cos_t = math.cos(theta)
            px = rx * cos_t
            py = ry * sin_t + yo
            pz = z_curr

            norm_len = math.sqrt(px * px + py * py) or 1.0
            norm = (round(px / norm_len, 4), round(py / norm_len, 4), 0.0)
            u = i / sectors
            v = u_z
            idx = mesh.add_vertex((round(px, 5), round(py, 5), round(pz, 5)), norm, (round(u, 5), round(v, 5)))
            ring.append(idx)
        rings.append(ring)

    for r in range(len(rings) - 1):
        for i in range(sectors):
            ni = (i + 1) % sectors
            mesh.add_quad(rings[r][i], rings[r][ni], rings[r + 1][ni], rings[r + 1][i])

    # 2. Central 3D Volumetric Barrel Cuff Knot
    knot_start = len(mesh.vertices)
    rx_mid, ry_mid, yo_mid = wardrobe.compute_dress_waist_radii(z_center, s=s, k_w=k_w, k_c=k_c, clearance=clearance)
    y_band_front = -(ry_mid + 0.0045 * s) + yo_mid
    knot_y = y_band_front - 0.002 * s
    knot_z = z_center - 0.002 * s
    kw_mid = 0.018 * s
    kw_cap = 0.022 * s
    kh = 0.024 * s
    kd = 0.011 * s

    knot_rings: List[List[int]] = []
    knot_z_slices = [
        knot_z - kh,
        knot_z - kh * 0.35,
        knot_z + kh * 0.35,
        knot_z + kh,
    ]

    for k_idx, kz in enumerate(knot_z_slices):
        is_cinch = (k_idx in (1, 2))
        kw = kw_mid if is_cinch else kw_cap
        depth = kd * (0.90 if is_cinch else 1.00)
        k_ring = []
        for m in range(8):
            psi = 2.0 * math.pi * m / 8.0
            cos_p = math.cos(psi)
            sin_p = math.sin(psi)
            kx = kw * cos_p
            pinch = 0.003 * s if (is_cinch and sin_p < -0.3) else 0.0
            ky = knot_y - depth * (1.0 - sin_p) + pinch

            norm_len = math.sqrt(kx * kx + (ky - knot_y) ** 2) or 1.0
            knorm = (round(kx / norm_len, 4), round((ky - knot_y) / norm_len, 4), 0.0)
            u = m / 8.0
            v = k_idx / 3.0
            v_idx = mesh.add_vertex((round(kx, 5), round(ky, 5), round(kz, 5)), knorm, (round(u, 5), round(v, 5)))
            k_ring.append(v_idx)
        knot_rings.append(k_ring)

    for kr in range(len(knot_rings) - 1):
        for m in range(8):
            nm = (m + 1) % 8
            mesh.add_quad(knot_rings[kr][m], knot_rings[kr][nm], knot_rings[kr + 1][nm], knot_rings[kr + 1][m])

    # Closed caps for 3D manifold knot (all 3 quads)
    # Bottom cap
    mesh.add_quad(knot_rings[0][0], knot_rings[0][7], knot_rings[0][6], knot_rings[0][1])
    mesh.add_quad(knot_rings[0][1], knot_rings[0][6], knot_rings[0][5], knot_rings[0][2])
    mesh.add_quad(knot_rings[0][2], knot_rings[0][5], knot_rings[0][4], knot_rings[0][3])
    # Top cap
    mesh.add_quad(knot_rings[3][0], knot_rings[3][1], knot_rings[3][6], knot_rings[3][7])
    mesh.add_quad(knot_rings[3][1], knot_rings[3][2], knot_rings[3][5], knot_rings[3][6])
    mesh.add_quad(knot_rings[3][2], knot_rings[3][3], knot_rings[3][4], knot_rings[3][5])

    knot_count = len(mesh.vertices) - knot_start

    # 3. Bilateral 3D Hollow Bow Loops
    orig = orig_sash_fn(height=height, clearance=clearance, belt_width=belt_width, sectors=sectors, waist_girth=waist_girth, chest_girth=chest_girth, **kwargs)
    loops_start = len(mesh.vertices)
    for v, norm, uv in zip(orig.vertices[152:248], orig.normals[152:248], orig.uvs[152:248]):
        mesh.add_vertex(v, norm, uv)
    for f in orig.faces:
        if all(152 <= idx < 248 for idx in f):
            mesh.faces.append(f)
    loops_count = len(mesh.vertices) - loops_start

    # 4. Streamers with fixed tip_bias
    streamers_start = len(mesh.vertices)
    streamer_steps = 16

    for stream_side, stream_sign, stream_len in [('L', 1.0, 0.38 * s), ('R', -1.0, 0.34 * s)]:
        x_origin = stream_sign * 0.012 * s
        y_origin = knot_y - 0.004 * s
        z_origin = knot_z - kh

        prev_stream_pts = None
        for step in range(streamer_steps + 1):
            t = step / streamer_steps
            pz = z_origin - t * stream_len
            w = (0.024 - 0.005 * t) * s
            px = x_origin + stream_sign * 0.028 * (t ** 1.3) * s

            z_norm = max(0.0, min(1.0, (1.030 * s - pz) / max(1e-4, 0.510 * s)))
            ry_skirt = (0.090 + 0.195 * (z_norm ** 1.15)) * s * k_w + clearance
            py = -(ry_skirt + 0.008 * s + 0.006 * s * math.sin(math.pi * t)) + yo_mid

            twist_ang = math.radians(35.0 * math.sin(1.5 * math.pi * t))
            cos_tw = math.cos(twist_ang)
            sin_tw = math.sin(twist_ang)

            tip_bias = (0.008 * s) if step == streamer_steps else 0.0

            p_left = (
                round(px - 0.5 * w * cos_tw, 5),
                round(py + 0.5 * w * sin_tw, 5),
                round(pz - tip_bias, 5),
            )
            p_mid = (
                round(px, 5),
                round(py, 5),
                round(pz, 5),
            )
            p_right = (
                round(px + 0.5 * w * cos_tw, 5),
                round(py - 0.5 * w * sin_tw, 5),
                round(pz + tip_bias, 5),
            )

            snorm = (round(-sin_tw, 4), round(-cos_tw, 4), 0.0)
            idx_l = mesh.add_vertex(p_left, snorm, (0.0, round(t, 5)))
            idx_m = mesh.add_vertex(p_mid, snorm, (0.5, round(t, 5)))
            idx_r = mesh.add_vertex(p_right, snorm, (1.0, round(t, 5)))
            cur_stream_pts = [idx_l, idx_m, idx_r]

            if prev_stream_pts is not None:
                mesh.add_quad(prev_stream_pts[0], prev_stream_pts[1], cur_stream_pts[1], cur_stream_pts[0])
                mesh.add_quad(prev_stream_pts[1], prev_stream_pts[2], cur_stream_pts[2], cur_stream_pts[1])
            prev_stream_pts = cur_stream_pts

    wardrobe.assign_sash_skin_weights(
        mesh,
        height=height,
        knot_start=knot_start,
        knot_count=knot_count,
        loops_start=loops_start,
        loops_count=loops_count,
        streamers_start=streamers_start,
    )
    return mesh

wardrobe.generate_dress_waist_sash = patched_waist_sash
wardrobe.generate_dress_organic_skirt = patched_organic_skirt

# Now let's test ALL 4 challenger test classes directly!
from tests.test_challenger_m2_sash import (
    TestSashClearanceAndZFighting,
    TestBowKnotAndRibbonGeometry,
    TestOrganicSkirtNormalsOrientation,
    TestRigifyDEFSkinningIntegrity,
)

t1 = TestSashClearanceAndZFighting()
t1.test_contract_sash_clearance_parameter_sweep()
t1.test_default_wardrobe_sash_bodice_clearance_all_angles()
t1.test_empirical_posterior_skirt_sash_penetration_discovery()
t1.test_costal_margin_flare_clearance_narrowing()
print('TestSashClearanceAndZFighting: ALL 4 TESTS PASSED!')

t2 = TestBowKnotAndRibbonGeometry()
t2.test_bow_loops_strictly_positive_volume()
t2.test_bow_loops_closed_2_manifold()
t2.test_barrel_knot_manifold_closed_caps()
t2.test_ribbon_streamer_cascade_trajectory()
t2.test_ribbon_streamer_tip_bias_cut()
print('TestBowKnotAndRibbonGeometry: ALL 5 TESTS PASSED!')

t3 = TestOrganicSkirtNormalsOrientation()
t3.test_organic_skirt_faces_outward_normals()
print('TestOrganicSkirtNormalsOrientation: ALL TESTS PASSED!')

t4 = TestRigifyDEFSkinningIntegrity()
t4.test_bodice_skin_weights_normalization_and_orphans()
t4.test_skirt_skin_weights_normalization_and_orphans()
t4.test_sash_skin_weights_normalization_and_orphans()
t4.test_rigify_def_bones_schema_compliance()
print('TestRigifyDEFSkinningIntegrity: ALL 4 TESTS PASSED!')

print('\n*** ALL 14 TESTS IN CHALLENGER TEST SUITE PASSED 100% WITH ZERO FAILURES! ***')
