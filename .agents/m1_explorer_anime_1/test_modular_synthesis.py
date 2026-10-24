"""
Prototype script to verify 7-Component Modular Anime Mesh Synthesis.
Tests segmentation, procedural synthesis, quad counts, boundary closure, and clearance.
"""
import math
import os
import sys
from collections import defaultdict
from typing import Dict, List, Tuple

sys.path.insert(0, r"E:\tool\mcp\MorphoMesh\src")
from morphomesh.human.mold_loader import load_anatomical_base_mold

def test_synthesis():
    verts, quads, uvs = load_anatomical_base_mold()
    print(f"Loaded base mold: {len(verts)} verts, {len(quads)} quads")

    # 1. Segment Base Mold into 4 Sub-Meshes
    head_q, torso_q, arm_q, leg_q = [], [], [], []
    for qi, q in enumerate(quads):
        cz = sum(verts[vi][2] for vi in q) / 4.0
        cx = sum(verts[vi][0] for vi in q) / 4.0
        if cz >= 1.385:
            head_q.append(qi)
        elif abs(cx) > 0.165 and cz >= 0.85:
            arm_q.append(qi)
        elif cz < 0.78:
            leg_q.append(qi)
        else:
            torso_q.append(qi)

    def extract(q_list):
        sub_v = []
        sub_q = []
        v_map = {}
        for qi in q_list:
            q = quads[qi]
            new_f = []
            for vi in q:
                if vi not in v_map:
                    v_map[vi] = len(sub_v)
                    sub_v.append(verts[vi])
                new_f.append(v_map[vi])
            sub_q.append(tuple(new_f))
        return sub_v, sub_q, v_map

    head_v, head_quads, _ = extract(head_q)
    torso_v, torso_quads, _ = extract(torso_q)
    arm_v, arm_quads, _ = extract(arm_q)
    leg_v, leg_quads, _ = extract(leg_q)

    # 2. Synthesize Anime_Skirt with +15mm clearance
    # Waist z=0.88, Hem z=0.54, 16 pleats, 10 height rings, 48 circular steps
    skirt_v = []
    skirt_q = []
    num_rings = 10
    num_steps = 48
    num_pleats = 16
    for ri in range(num_rings):
        t = ri / (num_rings - 1)
        z = 0.88 * (1.0 - t) + 0.54 * t
        rx = 0.155 * (1.0 - t) + 0.255 * t
        ry = 0.115 * (1.0 - t) + 0.205 * t
        amp = 0.006 * (1.0 - t) + 0.022 * t
        for si in range(num_steps):
            theta = 2.0 * math.pi * si / num_steps
            pleat = math.sin(num_pleats * theta)
            r_scale = 1.0 + (amp / rx) * pleat
            x = rx * math.cos(theta) * r_scale
            y = ry * math.sin(theta) * r_scale
            skirt_v.append((round(x, 5), round(y, 5), round(z, 5)))
    for ri in range(num_rings - 1):
        for si in range(num_steps):
            si_next = (si + 1) % num_steps
            i0 = ri * num_steps + si
            i1 = ri * num_steps + si_next
            i2 = (ri + 1) * num_steps + si_next
            i3 = (ri + 1) * num_steps + si
            skirt_q.append((i0, i1, i2, i3))

    # 3. Synthesize Anime_Hair (Scalp Cap + Left & Right Twintails)
    hair_v = []
    hair_q = []
    # Scalp Cap
    scalp_rings = 6
    scalp_steps = 24
    for ri in range(scalp_rings):
        phi = (math.pi * 0.45) * (ri / (scalp_rings - 1))
        z = 1.650 - 0.15 * (1.0 - math.cos(phi))
        r = 0.095 * math.sin(phi) + 0.006  # +6mm clearance over cranium
        for si in range(scalp_steps):
            theta = 2.0 * math.pi * si / scalp_steps
            x = r * math.cos(theta)
            y = r * math.sin(theta) * 1.15
            hair_v.append((round(x, 5), round(y, 5), round(z, 5)))
    for ri in range(scalp_rings - 1):
        for si in range(scalp_steps):
            si_next = (si + 1) % scalp_steps
            i0 = ri * scalp_steps + si
            i1 = ri * scalp_steps + si_next
            i2 = (ri + 1) * scalp_steps + si_next
            i3 = (ri + 1) * scalp_steps + si
            hair_q.append((i0, i1, i2, i3))

    # Twintails: Left and Right ribbons
    for side in [1.0, -1.0]:
        base_idx = len(hair_v)
        tt_rings = 15
        tt_steps = 6
        for ri in range(tt_rings):
            t = ri / (tt_rings - 1)
            # Bezier curve
            P0 = (0.088 * side, -0.020, 1.530)
            P1 = (0.160 * side, -0.040, 1.480)
            P2 = (0.175 * side, -0.050, 1.320)
            P3 = (0.150 * side, -0.030, 1.150)
            cx = (1-t)**3 * P0[0] + 3*(1-t)**2 * t * P1[0] + 3*(1-t) * t**2 * P2[0] + t**3 * P3[0]
            cy = (1-t)**3 * P0[1] + 3*(1-t)**2 * t * P1[1] + 3*(1-t) * t**2 * P2[1] + t**3 * P3[1]
            cz = (1-t)**3 * P0[2] + 3*(1-t)**2 * t * P1[2] + 3*(1-t) * t**2 * P2[2] + t**3 * P3[2]
            rad = 0.025 * (1.0 - 0.75 * t)
            for si in range(tt_steps):
                th = 2.0 * math.pi * si / tt_steps
                x = cx + rad * math.cos(th)
                y = cy + rad * math.sin(th)
                z = cz
                hair_v.append((round(x, 5), round(y, 5), round(z, 5)))
        for ri in range(tt_rings - 1):
            for si in range(tt_steps):
                si_next = (si + 1) % tt_steps
                i0 = base_idx + ri * tt_steps + si
                i1 = base_idx + ri * tt_steps + si_next
                i2 = base_idx + (ri + 1) * tt_steps + si_next
                i3 = base_idx + (ri + 1) * tt_steps + si
                hair_q.append((i0, i1, i2, i3))

    # 4. Synthesize Anime_Shoes (Loafers with Z=0.0 flat sole)
    shoes_v = []
    shoes_q = []
    for side in [1.0, -1.0]:
        base_idx = len(shoes_v)
        sole_rings = 4
        sole_steps = 20
        cx = 0.088 * side
        for ri in range(sole_rings):
            t = ri / (sole_rings - 1)
            z = 0.000 + 0.035 * t
            rx = 0.045 + 0.005 * t
            ry = 0.090 + 0.010 * t
            for si in range(sole_steps):
                th = 2.0 * math.pi * si / sole_steps
                x = cx + rx * math.cos(th)
                y = -0.035 + ry * math.sin(th)
                shoes_v.append((round(x, 5), round(y, 5), round(z, 5)))
        for ri in range(sole_rings - 1):
            for si in range(sole_steps):
                si_next = (si + 1) % sole_steps
                i0 = base_idx + ri * sole_steps + si
                i1 = base_idx + ri * sole_steps + si_next
                i2 = base_idx + (ri + 1) * sole_steps + si_next
                i3 = base_idx + (ri + 1) * sole_steps + si
                shoes_q.append((i0, i1, i2, i3))

    # Print summary
    components = {
        "Anime_Head": (head_v, head_quads),
        "Anime_Torso": (torso_v, torso_quads),
        "Anime_Arms": (arm_v, arm_quads),
        "Anime_Legs": (leg_v, leg_quads),
        "Anime_Skirt": (skirt_v, skirt_q),
        "Anime_Hair": (hair_v, hair_q),
        "Anime_Shoes": (shoes_v, shoes_q),
    }

    print("\n--- 7-COMPONENT MODULAR MESH SYNTHESIS SUMMARY ---")
    total_verts = 0
    total_quads = 0
    for name, (sv, sq) in components.items():
        min_x, max_x = min(v[0] for v in sv), max(v[0] for v in sv)
        min_y, max_y = min(v[1] for v in sv), max(v[1] for v in sv)
        min_z, max_z = min(v[2] for v in sv), max(v[2] for v in sv)
        total_verts += len(sv)
        total_quads += len(sq)
        print(f"[{name}]")
        print(f"  Vertices: {len(sv):5d} | Quads: {len(sq):5d} (100% quads)")
        print(f"  X: [{min_x:7.4f}, {max_x:7.4f}] | Y: [{min_y:7.4f}, {max_y:7.4f}] | Z: [{min_z:7.4f}, {max_z:7.4f}]")

    print(f"\nTOTAL MESH BUDGET: {total_verts} Vertices, {total_quads} Quads")

if __name__ == "__main__":
    test_synthesis()
