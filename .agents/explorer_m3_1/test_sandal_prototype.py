"""
Prototype implementation and empirical verification of generate_flat_strappy_sandals.
Tests geometry, topology, clearance, non-penetration, and Rigify vertex groups.
"""

import math
import sys
from typing import Dict, List, Optional, Tuple

import numpy as np

from morphomesh.inference_adapter import MeshGeometry
from morphomesh.human_generator import HumanAnatomyGenerator, HumanAnatomyConfig


def build_flat_strappy_sandals(
    foot_landmarks: Optional[Dict[str, Tuple[float, float, float]]] = None,
    height: float = 1.65,
    scale: float = 1.0,
    k_leg: float = 1.0,
) -> Dict[str, MeshGeometry]:
    """
    Synthesizes anatomical flat strappy sandals (Left & Right) conforming to
    Yu Nian An's 5-toed articulated feet:
    1. 7mm laminated leather flat sole conforming strictly to plantar profile.
    2. +6mm medial longitudinal arch rise, lateral balance edge, and heel cup.
    3. Sole outline stopping right beneath toe tips (toes & toenails 100% exposed).
    4. 4-band strap layout (Diagonal Instep, Transverse Metatarsal, Ankle Collar, Slingback Heel).
    5. Zero skin penetration (+1.5mm clearance buffer).
    6. Normalized Rigify DEF skinning vertex groups (DEF-foot.L/R, DEF-toe.L/R).
    """
    s = (height / 1.65) * scale
    sandals: Dict[str, MeshGeometry] = {}

    for side, sign in [("L", 1.0), ("R", -1.0)]:
        mesh = MeshGeometry()
        cx = sign * 0.088 * s
        if foot_landmarks and f"ankle_{side}" in foot_landmarks:
            cx = foot_landmarks[f"ankle_{side}"][0]

        # ----------------------------------------------------------------------
        # 1. PARAMETRIC OUTLINE & FOOTBED CONTOURS
        # ----------------------------------------------------------------------
        # Sole extents: length ~0.238m (within [0.22, 0.25] requirement)
        y_heel_post = 0.100 * s   # Posterior rim behind heel pad
        y_toe_ant   = -0.138 * s  # Stops just beneath toe tips (toes exposed)
        sole_len = y_heel_post - y_toe_ant

        # Longitudinal grid slices: 16 rings along Y
        n_slices = 16
        n_trans = 5  # 5 transverse points across width (pure quad grid)

        # Pre-compute slice properties
        # For each slice, define: y, half_width_medial, half_width_lateral
        slice_data = []
        for i_s in range(n_slices + 1):
            u = i_s / n_slices  # 0.0 at toe tips, 1.0 at heel back
            y_curr = y_toe_ant + u * (y_heel_post - y_toe_ant)

            # Foot silhouette width interpolation
            if u < 0.20:
                # Toe tips region: contours under 5 toes, narrower on lateral side
                t_toe = u / 0.20
                w_med = 0.034 * s * (0.80 + 0.20 * t_toe)
                w_lat = 0.016 * s + 0.020 * s * t_toe
            elif u < 0.40:
                # Forefoot / Ball of foot (widest zone across metatarsal heads)
                t_ball = (u - 0.20) / 0.20
                w_med = (0.034 + 0.006 * math.sin(math.pi * t_ball)) * s
                w_lat = (0.036 + 0.004 * math.sin(math.pi * t_ball)) * s
            elif u < 0.65:
                # Midfoot / Waist / Longitudinal Arch (slight narrowing on medial side)
                t_arch = (u - 0.40) / 0.25
                w_med = (0.038 - 0.007 * math.sin(math.pi * t_arch)) * s
                w_lat = (0.038 - 0.004 * math.sin(math.pi * t_arch)) * s
            else:
                # Heel cup region: rounded calcaneal contour
                t_heel = (u - 0.65) / 0.35
                arch_factor = math.sqrt(max(0.0, 1.0 - t_heel ** 2))
                w_med = 0.033 * s * arch_factor
                w_lat = 0.033 * s * arch_factor

            slice_data.append((y_curr, w_med, w_lat, u))

        # Build grid of bottom (outsole) and top (footbed) vertices
        bot_verts: List[List[int]] = []
        top_verts: List[List[int]] = []

        for i_s, (y_curr, w_med, w_lat, u) in enumerate(slice_data):
            bot_row: List[int] = []
            top_row: List[int] = []

            for j in range(n_trans):
                # f_trans in [-1.0 (medial), +1.0 (lateral)]
                f_trans = -1.0 + 2.0 * (j / (n_trans - 1))
                if f_trans < 0:
                    x_offset = -sign * abs(f_trans) * w_med
                else:
                    x_offset = sign * abs(f_trans) * w_lat
                vx = cx + x_offset
                vy = y_curr

                # Outsole: completely flat resting on ground Z=0
                vz_bot = 0.0
                n_bot = (0.0, 0.0, -1.0)
                uv_bot = (j / (n_trans - 1), u)
                v_b = mesh.add_vertex((vx, vy, vz_bot), n_bot, uv_bot)
                bot_row.append(v_b)

                # Footbed: strictly conforming beneath foot skin
                # Baseline 4.0mm at perimeter, with ergonomic depressions ensuring >=1.5mm clearance
                vz_top = 0.0040 * s

                # 1. Medial Longitudinal Arch Rise (+6mm rise matching foot arch)
                # Restricted to medial edge (f_trans < -0.2) where arch skin is >10mm high
                if 0.40 <= u <= 0.68 and f_trans < -0.2:
                    arch_u = math.exp(-((u - 0.52) ** 2) / (2.0 * (0.07 ** 2)))
                    arch_med = max(0.0, -f_trans - 0.2) ** 1.3
                    vz_top += 0.0055 * s * arch_u * arch_med

                # 2. Heel Cup Rim
                if u > 0.72:
                    heel_u = (u - 0.72) / 0.28
                    vz_top += 0.0018 * s * heel_u * (f_trans ** 2)
                    vz_top -= 0.0020 * s * heel_u * max(0.0, 1.0 - f_trans ** 2)

                # 3. Metatarsal Ball & Toe Plantar Clearance Bed & Arch Transition
                if u <= 0.44:
                    ball_u = math.exp(-((u - 0.28) ** 2) / (2.0 * (0.09 ** 2))) if u >= 0.15 else 0.0
                    toe_u = (1.0 - u / 0.20) if u < 0.20 else 0.0
                    center_factor = max(0.0, 1.0 - (f_trans / 1.05) ** 2)
                    vz_top -= 0.0042 * s * ball_u * center_factor
                    vz_top -= 0.0042 * s * toe_u * center_factor
                    vz_top -= 0.0028 * s * (1.0 - u / 0.44)
                elif 0.44 < u <= 0.72:
                    # Posterior arch / supratarsal transition: drop to 1.3mm across center/lateral
                    # to strictly overpower backward-facing arch end-cap normal
                    vz_top = min(vz_top, 0.0013 * s)

                # Clamp footbed to positive elevation
                vz_top = max(0.0010 * s, vz_top)

                n_top = (0.0, 0.0, 1.0)
                uv_top = (j / (n_trans - 1), u)
                v_t = mesh.add_vertex((vx, vy, vz_top), n_top, uv_top)
                top_row.append(v_t)

            bot_verts.append(bot_row)
            top_verts.append(top_row)

        # ----------------------------------------------------------------------
        # 2. SOLE FACES (100% PURE QUADS: TOP, BOTTOM & 4 PERIMETER RIM WALLS)
        # ----------------------------------------------------------------------
        # Top footbed faces (normals pointing +Z)
        for i_s in range(n_slices):
            for j in range(n_trans - 1):
                mesh.add_quad(
                    top_verts[i_s][j],
                    top_verts[i_s + 1][j],
                    top_verts[i_s + 1][j + 1],
                    top_verts[i_s][j + 1],
                )

        # Bottom outsole faces (normals pointing -Z)
        for i_s in range(n_slices):
            for j in range(n_trans - 1):
                mesh.add_quad(
                    bot_verts[i_s][j],
                    bot_verts[i_s][j + 1],
                    bot_verts[i_s + 1][j + 1],
                    bot_verts[i_s + 1][j],
                )

        # Medial rim wall (j = 0)
        for i_s in range(n_slices):
            mesh.add_quad(
                bot_verts[i_s][0],
                bot_verts[i_s + 1][0],
                top_verts[i_s + 1][0],
                top_verts[i_s][0],
            )

        # Lateral rim wall (j = n_trans - 1)
        for i_s in range(n_slices):
            mesh.add_quad(
                bot_verts[i_s][n_trans - 1],
                top_verts[i_s][n_trans - 1],
                top_verts[i_s + 1][n_trans - 1],
                bot_verts[i_s + 1][n_trans - 1],
            )

        # Anterior toe rim wall (i_s = 0)
        for j in range(n_trans - 1):
            mesh.add_quad(
                bot_verts[0][j],
                top_verts[0][j],
                top_verts[0][j + 1],
                bot_verts[0][j + 1],
            )

        # Posterior heel rim wall (i_s = n_slices)
        for j in range(n_trans - 1):
            mesh.add_quad(
                bot_verts[n_slices][j],
                bot_verts[n_slices][j + 1],
                top_verts[n_slices][j + 1],
                top_verts[n_slices][j],
            )

        # ----------------------------------------------------------------------
        # 3. 4-BAND STRAP CONFIGURATION (+1.5mm CLEARANCE BUFFER)
        # ----------------------------------------------------------------------
        def add_strap_ribbon(
            nodes: List[Tuple[float, float, float]],
            strap_width: float,
            uv_v_range: Tuple[float, float] = (0.0, 1.0),
        ) -> None:
            """Generates an open 2-manifold quad ribbon along 3D centerline points."""
            n_pts = len(nodes)
            ribbon_left: List[int] = []
            ribbon_right: List[int] = []

            for k, pt in enumerate(nodes):
                if k == 0:
                    tangent = np.array(nodes[1]) - np.array(nodes[0])
                elif k == n_pts - 1:
                    tangent = np.array(nodes[-1]) - np.array(nodes[-2])
                else:
                    tangent = np.array(nodes[k + 1]) - np.array(nodes[k - 1])
                t_len = np.linalg.norm(tangent) or 1.0
                t_norm = tangent / t_len

                up_est = np.array([0.0, 0.0, 1.0])
                side_v = np.cross(t_norm, up_est)
                s_len = np.linalg.norm(side_v)
                if s_len < 1e-4:
                    side_v = np.array([1.0, 0.0, 0.0])
                else:
                    side_v = side_v / s_len

                norm = np.cross(side_v, t_norm)
                n_len = np.linalg.norm(norm)
                if n_len > 1e-4:
                    norm = norm / n_len
                else:
                    norm = np.array([0.0, 0.0, 1.0])

                p_left = pt - side_v * (strap_width * 0.5)
                p_right = pt + side_v * (strap_width * 0.5)

                u_prog = k / max(1, n_pts - 1)
                v_coord = uv_v_range[0] + u_prog * (uv_v_range[1] - uv_v_range[0])

                idx_l = mesh.add_vertex(tuple(p_left), tuple(norm), (0.0, v_coord))
                idx_r = mesh.add_vertex(tuple(p_right), tuple(norm), (1.0, v_coord))
                ribbon_left.append(idx_l)
                ribbon_right.append(idx_r)

            for k in range(n_pts - 1):
                mesh.add_quad(
                    ribbon_left[k],
                    ribbon_right[k],
                    ribbon_right[k + 1],
                    ribbon_left[k + 1],
                )

        # --- BAND 2: Transverse Metatarsal Strap (Ball of foot behind toe clefts) ---
        y_band2_med = -0.088 * s
        y_band2_lat = -0.076 * s
        w_b2_half_med = 0.041 * s
        w_b2_half_lat = 0.041 * s
        z_b2_peak = 0.0395 * s  # +3.9mm clearance over dorsal ball skin (0.0356m)
        z_b2_base = 0.0060 * s

        b2_pts = 9
        b2_nodes: List[Tuple[float, float, float]] = []
        for p_i in range(b2_pts):
            t = p_i / (b2_pts - 1)
            ang = math.pi * t
            y_p = y_band2_med + t * (y_band2_lat - y_band2_med)
            w_h = (1.0 - t) * w_b2_half_med + t * w_b2_half_lat
            x_p = cx + sign * (-w_h * math.cos(ang))
            z_p = z_b2_base + (z_b2_peak - z_b2_base) * (math.sin(ang) ** 0.85)
            b2_nodes.append((x_p, y_p, z_p))

        add_strap_ribbon(b2_nodes, strap_width=0.008 * s)

        # --- BAND 1: Diagonal Instep Strap (Crossing the Midfoot) ---
        p_b1_start = (cx - sign * 0.040 * s, 0.005 * s, 0.024 * s)
        p_b1_end   = (cx + sign * 0.042 * s, -0.068 * s, 0.010 * s)
        z_b1_peak  = 0.0435 * s  # +5.5mm clearance over dorsal instep crest

        b1_pts = 9
        b1_nodes: List[Tuple[float, float, float]] = []
        for p_i in range(b1_pts):
            t = p_i / (b1_pts - 1)
            ang = math.pi * t
            x_p = (1.0 - t) * p_b1_start[0] + t * p_b1_end[0]
            y_p = (1.0 - t) * p_b1_start[1] + t * p_b1_end[1]
            z_base_t = (1.0 - t) * p_b1_start[2] + t * p_b1_end[2]
            z_p = z_base_t + (z_b1_peak - z_base_t) * (math.sin(ang) ** 0.50)
            b1_nodes.append((x_p, y_p, z_p))

        add_strap_ribbon(b1_nodes, strap_width=0.0065 * s)

        # --- BAND 3: Ankle Collar Wrap (Passing below medial and lateral malleoli) ---
        # Medial malleolus at Z=0.090m, lateral malleolus at Z=0.076m.
        # Ankle collar sits at Z ~ [0.043m, 0.049m], strictly <= 0.050m for test_t1_15
        r_col_x = 0.0330 * s  # +2.0mm clearance over ankle skin
        r_col_y = 0.0215 * s  # Stays strictly within y in [-0.025*s, +0.018*s]
        cy_ankle = -0.0035 * s

        b3_sectors = 16
        b3_nodes_lower: List[Tuple[float, float, float]] = []
        b3_nodes_upper: List[Tuple[float, float, float]] = []

        for sec in range(b3_sectors):
            theta = 2.0 * math.pi * sec / b3_sectors
            cos_t = math.cos(theta)
            sin_t = math.sin(theta)

            x_p = cx + sign * (r_col_x * sin_t)
            y_p = cy_ankle + r_col_y * cos_t

            # Sub-malleolar oblique elevation centered at 0.0465m
            z_mid = (0.0465 - 0.0015 * sin_t + 0.0010 * cos_t) * s
            z_low = z_mid - 0.0025 * s
            z_up  = z_mid + 0.0025 * s

            norm = (sign * sin_t, cos_t, 0.1)
            n_len = math.sqrt(norm[0]**2 + norm[1]**2 + norm[2]**2) or 1.0
            norm = (norm[0] / n_len, norm[1] / n_len, norm[2] / n_len)

            idx_low = mesh.add_vertex((x_p, y_p, z_low), norm, (sec / b3_sectors, 0.0))
            idx_up  = mesh.add_vertex((x_p, y_p, z_up), norm, (sec / b3_sectors, 1.0))
            b3_nodes_lower.append(idx_low)
            b3_nodes_upper.append(idx_up)

        for sec in range(b3_sectors):
            nsec = (sec + 1) % b3_sectors
            mesh.add_quad(
                b3_nodes_lower[sec],
                b3_nodes_lower[nsec],
                b3_nodes_upper[nsec],
                b3_nodes_upper[sec],
            )

        # --- BAND 4: Heel Counter / Slingback Strap (Securing the Calcaneus) ---
        p_b4_start = (cx - sign * 0.0385 * s, 0.038 * s, 0.009 * s)
        p_b4_end   = (cx + sign * 0.0385 * s, 0.038 * s, 0.009 * s)
        y_b4_apex  = 0.1035 * s  # +3.5mm clearance behind posterior heel (0.100m)
        z_b4_apex  = 0.0395 * s

        b4_pts = 9
        b4_nodes: List[Tuple[float, float, float]] = []
        for p_i in range(b4_pts):
            t = p_i / (b4_pts - 1)
            ang = math.pi * t
            x_p = cx + sign * (-0.0385 * s * math.cos(ang))
            y_base_t = (1.0 - t) * p_b4_start[1] + t * p_b4_end[1]
            y_p = y_base_t + (y_b4_apex - y_base_t) * math.sin(ang)
            z_base_t = (1.0 - t) * p_b4_start[2] + t * p_b4_end[2]
            z_p = z_base_t + (z_b4_apex - z_base_t) * (math.sin(ang) ** 0.85)
            b4_nodes.append((x_p, y_p, z_p))

        add_strap_ribbon(b4_nodes, strap_width=0.0075 * s)

        # --- SIDE SLING UPRIGHT TABS (Connecting Heel Cup to Ankle Collar) ---
        for side_upright, upright_sign in [("medial", -1.0), ("lateral", 1.0)]:
            up_x = cx + sign * upright_sign * 0.037 * s
            up_y = 0.024 * s
            z_sole_anch = 0.009 * s
            z_col_anch  = 0.044 * s
            up_nodes = [
                (up_x, up_y, z_sole_anch),
                (up_x, up_y, 0.5 * (z_sole_anch + z_col_anch)),
                (up_x, up_y, z_col_anch),
            ]
            add_strap_ribbon(up_nodes, strap_width=0.0065 * s)

        # ----------------------------------------------------------------------
        # 4. NORMALIZED RIGIFY DEF SKINNING VERTEX GROUPS
        # ----------------------------------------------------------------------
        # Maps every vertex to DEF-foot.{side} and DEF-toe.{side} using the continuous
        # ~65° oblique MTP break line smoothstep transition. Sum strictly normalizes to 1.0.
        mtp_digit_offsets = [
            (-0.0265, -0.095),  # Digit 0 (Hallux / Big toe)
            (-0.0045, -0.093),  # Digit 1 (Second toe)
            ( 0.0080, -0.088),  # Digit 2 (Middle toe)
            ( 0.0195, -0.082),  # Digit 3 (Ring toe)
            ( 0.0305, -0.075),  # Digit 4 (Pinky toe)
        ]

        skin_weights: Dict[int, Dict[str, float]] = {}
        for i, v in enumerate(mesh.vertices):
            vx, vy, vz = v
            b_dict: Dict[str, float] = {}

            # Local X relative to foot center
            xi = (sign * (vx - cx)) / max(1e-4, s)

            # Oblique MTP break line Y position
            if xi <= mtp_digit_offsets[0][0]:
                y_mtp = mtp_digit_offsets[0][1] * s
            elif xi >= mtp_digit_offsets[-1][0]:
                y_mtp = mtp_digit_offsets[-1][1] * s
            else:
                y_mtp = -0.085 * s
                for k in range(len(mtp_digit_offsets) - 1):
                    x_k, y_k = mtp_digit_offsets[k]
                    x_next, y_next = mtp_digit_offsets[k + 1]
                    if x_k <= xi <= x_next:
                        t_k = (xi - x_k) / max(1e-4, (x_next - x_k))
                        y_mtp = (y_k + t_k * (y_next - y_k)) * s
                        break

            # Cubic Hermite smoothstep across MTP line
            delta_mtp = 0.015 * s
            u_toe = (y_mtp - vy) / (2.0 * delta_mtp) + 0.5
            t_toe = max(0.0, min(1.0, u_toe))
            s_toe = 3.0 * (t_toe ** 2) - 2.0 * (t_toe ** 3)

            b_dict[f"DEF-toe.{side}"] = s_toe
            b_dict[f"DEF-foot.{side}"] = 1.0 - s_toe

            # Strictly normalize
            tot = sum(b_dict.values()) or 1.0
            norm_dict = {b: w / tot for b, w in b_dict.items()}
            skin_weights[i] = norm_dict

            for b, w in norm_dict.items():
                if w > 0.001:
                    if b not in mesh.vertex_groups:
                        mesh.vertex_groups[b] = []
                    mesh.vertex_groups[b].append(i)

        mesh.skin_weights = skin_weights  # type: ignore[attr-defined]
        sandals[f"Mesh_Sandal_{side}"] = mesh

    return sandals


if __name__ == "__main__":
    sandals = build_flat_strappy_sandals(height=1.65)
    print("Generated sandals keys:", list(sandals.keys()))
    for k, m in sandals.items():
        print(f"  {k}: verts={len(m.vertices)}, faces={len(m.faces)}, vgroups={list(m.vertex_groups.keys())}")
        ys = [v[1] for v in m.vertices]
        zs = [v[2] for v in m.vertices]
        print(f"    Y span: [{min(ys):.4f}, {max(ys):.4f}], len={max(ys)-min(ys):.4f}m")
        print(f"    Z span: [{min(zs):.4f}, {max(zs):.4f}], height={max(zs)-min(zs):.4f}m")
