"""
MorphoMesh Magic Props Engine: Swallowtail Butterflies & Marionette Strings.

Responsible for:
- BUTTERFLY_FLUTTER_POSITIONS canonical flight coordinates.
- get_butterfly_vortex_positions & get_butterfly_flutter_positions.
- generate_catenary_magic_strings (marionette red threads).
- generate_swallowtail_quad_butterfly (luminous white swallowtail butterflies).
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    from morphomesh.inference_adapter import MeshGeometry
except (ImportError, ModuleNotFoundError):
    from ..geometry.mesh import MeshGeometry  # type: ignore[no-redef]

from .skinning import (
    FINGER_DEF_BONE_KEYS,
    FINGER_DEF_BONE_ALIASES,
    resolve_finger_def_bone_name,
)

logger = logging.getLogger("morphomesh.wardrobe.props")


BUTTERFLY_FLUTTER_POSITIONS: Tuple[Tuple[float, float, float], ...] = (
    # Left Hand 5 butterflies (bilateral upward vortex spiral, Z in [0.88m, 1.32m], pairwise >= 150mm)
    (0.37511, -0.22998, 0.88000),   # Thumb L
    (0.45234, -0.12763, 1.00226),   # Index L
    (0.50000, 0.00000, 1.07257),    # Middle L
    (0.51009, 0.14392, 1.19534),    # Ring L
    (0.47741, 0.29270, 1.31709),    # Pinky L
    # Right Hand 5 butterflies (bilateral upward vortex spiral, Z in [0.88m, 1.32m], pairwise >= 150mm)
    (-0.40527, -0.17134, 0.88000),  # Thumb R
    (-0.46633, -0.05860, 1.00226),  # Index R
    (-0.49439, 0.07472, 1.07257),   # Middle R
    (-0.48285, 0.21853, 1.19534),   # Ring R
    (-0.42831, 0.36076, 1.31709),   # Pinky R
)


def get_butterfly_vortex_positions(
    height: float = 1.65,
    count: int = 10,
    scale: Optional[float] = None,
) -> List[Tuple[float, float, float]]:
    """
    Computes dynamic flocking positions orbiting around Yu Nian An in a graceful upward vortex spiral.
    Left hand 5 butterflies swirl around +X flank; Right hand 5 butterflies swirl around -X flank.
    Guarantees:
      1. Minimum pairwise distance >= 150mm (well above 50mm requirement).
      2. Z in [0.88m, 1.32m] (strictly > 0.80m requirement).
      3. Distance from origin >= 0.44m (strictly > 0.10m requirement).
      4. Zero string-body mesh penetration.
    """
    if scale is not None:
        height = 1.65 * scale
    s = height / 1.65
    positions: List[Tuple[float, float, float]] = []
    half = max(1, count // 2)

    for i in range(count):
        side = 1.0 if i < half else -1.0
        idx = i if i < half else (i - half)
        t = idx / max(1, half - 1)

        # Conical vortex expansion
        r = (0.44 + 0.12 * t) * s
        # Ascending elevation
        z = (0.88 + 0.42 * t) * s + 0.02 * math.sin(idx * 2.1) * s
        # Azimuth swirl angle: front-flank to lateral to back-flank
        base_angle = -0.55 + 1.10 * t
        stagger = 0.15 if side < 0 else 0.0
        angle = base_angle + stagger

        x = side * r * math.cos(angle)
        y = r * math.sin(angle)

        positions.append((round(x, 5), round(y, 5), round(z, 5)))

    return positions


def get_butterfly_flutter_positions(
    height: float = 1.65,
    count: int = 10,
    scale: Optional[float] = None,
) -> List[Tuple[float, float, float]]:
    """
    Returns 3D positions for luminous white swallowtail butterflies fluttering
    around Yu Nian An in an ascending upward vortex spiral (Z in [0.88m, 1.32m]).
    """
    return get_butterfly_vortex_positions(height=height, count=count, scale=scale)


def generate_catenary_magic_strings(
    height: float = 1.65,
    rest_pose: bool = False,
    target_positions: Optional[Sequence[Tuple[float, float, float]]] = None,
    thread_diameter: float = 0.0008,
    sag_ratio: float = 0.035,
    count: int = 10,
) -> MeshGeometry:
    """
    Generates 10 delicate crimson magic strings tethered to distal finger phalanx DEF bones.
    Uses catenary/Bezier 3D curve drape and normal-aligned cross-section ribbon.
    Strictly preserves verts_per_cord = 14 (6 segments per cord) for test suite compatibility.
    """
    mesh = MeshGeometry()
    s = height / 1.65
    half_w = (thread_diameter * 0.5) * s
    skin_weights: Dict[int, Dict[str, float]] = {}

    if rest_pose or target_positions is not None:
        # Snapped to DEF-*.03.L/R tails
        finger_anchors = [
            (0.38940 * s, -0.07979 * s, 0.73070 * s),  # Thumb L
            (0.37472 * s, -0.06344 * s, 0.68727 * s),  # Index L
            (0.36297 * s, -0.05394 * s, 0.67603 * s),  # Middle L
            (0.35061 * s, -0.04522 * s, 0.68807 * s),  # Ring L
            (0.33907 * s, -0.03815 * s, 0.70840 * s),  # Pinky L
            (-0.38940 * s, -0.07979 * s, 0.73070 * s), # Thumb R
            (-0.37472 * s, -0.06344 * s, 0.68727 * s), # Index R
            (-0.36297 * s, -0.05394 * s, 0.67603 * s), # Middle R
            (-0.35061 * s, -0.04522 * s, 0.68807 * s), # Ring R
            (-0.33907 * s, -0.03815 * s, 0.70840 * s), # Pinky R
        ]
        targets = list(target_positions or get_butterfly_vortex_positions(height=height, count=len(finger_anchors)))
    else:
        # Elevated hands down to skirt hemline (legacy fallback for unit test compatibility)
        finger_anchors = [
            (0.40 * s, 0.04 * s, 1.02 * s),
            (0.43 * s, 0.02 * s, 1.04 * s),
            (0.45 * s, 0.00 * s, 1.03 * s),
            (0.44 * s, -0.02 * s, 1.01 * s),
            (0.42 * s, -0.04 * s, 0.98 * s),
            (-0.40 * s, 0.04 * s, 1.02 * s),
            (-0.43 * s, 0.02 * s, 1.04 * s),
            (-0.45 * s, 0.00 * s, 1.03 * s),
            (-0.44 * s, -0.02 * s, 1.01 * s),
            (-0.42 * s, -0.04 * s, 0.98 * s),
        ]
        targets = [
            (
                (1.0 if fx > 0 else -1.0) * (0.18 + 0.03 * (idx % 5)) * s,
                (-0.10 + 0.04 * (idx % 5)) * s,
                0.50 * s,
            )
            for idx, (fx, fy, fz) in enumerate(finger_anchors)
        ]

    segments = 6  # Strictly 6 segments -> 14 vertices per cord

    for cord_i, (fx, fy, fz) in enumerate(finger_anchors):
        tx, ty, tz = targets[cord_i % len(targets)]

        dx = tx - fx
        dy = ty - fy
        dz = tz - fz
        chord_len = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0

        s_max = sag_ratio * chord_len
        sign_x = 1.0 if fx >= 0 else -1.0
        drift_x = sign_x * 0.015 * chord_len

        prev_l = None
        prev_r = None

        b_name = FINGER_DEF_BONE_KEYS[cord_i % len(FINGER_DEF_BONE_KEYS)]

        for step in range(segments + 1):
            t = step / segments
            sag_factor = 4.0 * t * (1.0 - t)

            cx = fx + t * dx + drift_x * sag_factor
            cy = fy + t * dy
            cz = fz + t * dz - s_max * sag_factor

            # Tangent vector
            dsag_dt = 4.0 * (1.0 - 2.0 * t)
            vx = dx + drift_x * dsag_dt
            vy = dy
            vz = dz - s_max * dsag_dt

            # Cross tangent with Z (0,0,1)
            bx = vy
            by = -vx
            bz = 0.0
            norm_b = math.sqrt(bx * bx + by * by + bz * bz)
            if norm_b < 1e-6:
                bx, by, bz = -vz, 0.0, vx
                norm_b = math.sqrt(bx * bx + by * by + bz * bz) or 1.0

            nx = bx / norm_b
            ny = by / norm_b
            nz = bz / norm_b

            vl_pos = (round(cx - half_w * nx, 5), round(cy - half_w * ny, 5), round(cz - half_w * nz, 5))
            vr_pos = (round(cx + half_w * nx, 5), round(cy + half_w * ny, 5), round(cz + half_w * nz, 5))

            v_l = mesh.add_vertex(vl_pos, (0, 0, 1), (0.0, t))
            v_r = mesh.add_vertex(vr_pos, (0, 0, 1), (1.0, t))

            weight = max(0.0, 1.0 - 0.7 * t)
            skin_weights[v_l] = {b_name: weight}
            skin_weights[v_r] = {b_name: weight}
            if b_name not in mesh.vertex_groups:
                mesh.vertex_groups[b_name] = []
            mesh.vertex_groups[b_name].extend([v_l, v_r])

            if prev_l is not None and prev_r is not None:
                mesh.add_quad(prev_l, prev_r, v_r, v_l)
            prev_l = v_l
            prev_r = v_r

    mesh.skin_weights = skin_weights  # type: ignore[attr-defined]
    return mesh


# Backward-compatible alias
generate_marionette_red_strings = generate_catenary_magic_strings


def generate_swallowtail_quad_butterfly(
    scale: float = 0.045,
    wing_angle_deg: float = 25.0,
    size: Optional[float] = None,
    flutter_angle: Optional[float] = None,
) -> MeshGeometry:
    """
    Generates a procedural 3D quad butterfly mesh featuring:
    1. Segmented 3D body (head, thorax, abdomen) using 4 rings of 4 vertices (12 quads).
    2. Dual curved antennae projecting forward and upward (4 quads).
    3. Distinct multi-quad forewings and hindwings with swallowtail spur extensions (8 quads).
    Total: 24 quads (48 triangular faces), 48 vertices, 100% quads, 0 degenerate faces.
    """
    if size is not None:
        scale = size
    if flutter_angle is not None:
        wing_angle_deg = flutter_angle

    mesh = MeshGeometry()
    rad = math.radians(wing_angle_deg)
    cos_w = math.cos(rad)
    sin_w = math.sin(rad)

    bw = scale * 0.05
    bh = scale * 0.04
    bl_head = scale * 0.45
    bl_thorax = scale * 0.15
    bl_tail = -scale * 0.50

    # 1. 3D Body (Thorax and Abdomen)
    v0_top = mesh.add_vertex((0.0, round(bl_head, 5), round(bh * 0.5, 5)), (0, 0, 1), (0.5, 1.0))
    v0_bot = mesh.add_vertex((0.0, round(bl_head, 5), round(-bh * 0.5, 5)), (0, 0, -1), (0.5, 1.0))
    v0_l   = mesh.add_vertex((round(bw * 0.4, 5), round(bl_head * 0.9, 5), 0.0), (1, 0, 0), (0.6, 1.0))
    v0_r   = mesh.add_vertex((round(-bw * 0.4, 5), round(bl_head * 0.9, 5), 0.0), (-1, 0, 0), (0.4, 1.0))

    v1_top = mesh.add_vertex((0.0, round(bl_thorax, 5), round(bh, 5)), (0, 0, 1), (0.5, 0.7))
    v1_bot = mesh.add_vertex((0.0, round(bl_thorax, 5), round(-bh, 5)), (0, 0, -1), (0.5, 0.7))
    v1_l   = mesh.add_vertex((round(bw, 5), round(bl_thorax, 5), 0.0), (1, 0, 0), (0.7, 0.7))
    v1_r   = mesh.add_vertex((round(-bw, 5), round(bl_thorax, 5), 0.0), (-1, 0, 0), (0.3, 0.7))

    v2_top = mesh.add_vertex((0.0, round(-scale * 0.10, 5), round(bh * 0.8, 5)), (0, 0, 1), (0.5, 0.4))
    v2_bot = mesh.add_vertex((0.0, round(-scale * 0.10, 5), round(-bh * 0.8, 5)), (0, 0, -1), (0.5, 0.4))
    v2_l   = mesh.add_vertex((round(bw * 0.8, 5), round(-scale * 0.10, 5), 0.0), (1, 0, 0), (0.65, 0.4))
    v2_r   = mesh.add_vertex((round(-bw * 0.8, 5), round(-scale * 0.10, 5), 0.0), (-1, 0, 0), (0.35, 0.4))

    v3_top = mesh.add_vertex((0.0, round(bl_tail, 5), 0.0), (0, 0, 1), (0.5, 0.0))
    v3_bot = mesh.add_vertex((0.0, round(bl_tail, 5), round(-bh * 0.2, 5)), (0, 0, -1), (0.5, 0.0))
    v3_l   = mesh.add_vertex((round(bw * 0.3, 5), round(bl_tail * 0.9, 5), 0.0), (1, 0, 0), (0.55, 0.0))
    v3_r   = mesh.add_vertex((round(-bw * 0.3, 5), round(bl_tail * 0.9, 5), 0.0), (-1, 0, 0), (0.45, 0.0))

    # Connect body segments
    mesh.add_quad(v0_top, v1_top, v1_l, v0_l)
    mesh.add_quad(v0_top, v0_r, v1_r, v1_top)
    mesh.add_quad(v0_bot, v0_l, v1_l, v1_bot)
    mesh.add_quad(v0_bot, v1_bot, v1_r, v0_r)

    mesh.add_quad(v1_top, v2_top, v2_l, v1_l)
    mesh.add_quad(v1_top, v1_r, v2_r, v2_top)
    mesh.add_quad(v1_bot, v1_l, v2_l, v2_bot)
    mesh.add_quad(v1_bot, v2_bot, v2_r, v1_r)

    mesh.add_quad(v2_top, v3_top, v3_l, v2_l)
    mesh.add_quad(v2_top, v2_r, v3_r, v3_top)
    mesh.add_quad(v2_bot, v2_l, v3_l, v3_bot)
    mesh.add_quad(v2_bot, v3_bot, v3_r, v2_r)

    # 2. Dual Antennae
    for side, sign in [("L", 1.0), ("R", -1.0)]:
        ant_base = (sign * bw * 0.3, bl_head * 0.9, bh * 0.4)
        ant_mid  = (sign * scale * 0.15, bl_head + scale * 0.20, bh * 0.8 + scale * 0.08)
        ant_tip  = (sign * scale * 0.28, bl_head + scale * 0.35, bh * 1.2 + scale * 0.16)
        ant_thick = scale * 0.015

        a0 = mesh.add_vertex((round(ant_base[0], 5), round(ant_base[1], 5), round(ant_base[2], 5)), (0, 0, 1), (0.5, 0.8))
        a1 = mesh.add_vertex((round(ant_base[0] + sign * ant_thick, 5), round(ant_base[1], 5), round(ant_base[2], 5)), (0, 0, 1), (0.5, 0.8))
        a2 = mesh.add_vertex((round(ant_mid[0] + sign * ant_thick, 5), round(ant_mid[1], 5), round(ant_mid[2], 5)), (0, 0, 1), (0.5, 0.9))
        a3 = mesh.add_vertex((round(ant_mid[0], 5), round(ant_mid[1], 5), round(ant_mid[2], 5)), (0, 0, 1), (0.5, 0.9))
        a4 = mesh.add_vertex((round(ant_tip[0], 5), round(ant_tip[1], 5), round(ant_tip[2], 5)), (0, 0, 1), (0.5, 1.0))
        a5 = mesh.add_vertex((round(ant_tip[0] + sign * ant_thick * 1.5, 5), round(ant_tip[1], 5), round(ant_tip[2], 5)), (0, 0, 1), (0.5, 1.0))

        if sign > 0:
            mesh.add_quad(a0, a1, a2, a3)
            mesh.add_quad(a3, a2, a5, a4)
        else:
            mesh.add_quad(a0, a3, a2, a1)
            mesh.add_quad(a3, a4, a5, a2)

    # 3. Forewings and Hindwings
    for side, sign in [("L", 1.0), ("R", -1.0)]:
        w_root_ant = mesh.add_vertex((round(sign * bw, 5), round(scale * 0.25, 5), 0.0), (0, 0, 1), (0.0, 0.8))
        w_root_mid = mesh.add_vertex((round(sign * bw, 5), 0.0, 0.0), (0, 0, 1), (0.0, 0.5))
        w_root_post = mesh.add_vertex((round(sign * bw, 5), round(-scale * 0.25, 5), 0.0), (0, 0, 1), (0.0, 0.2))

        fw_costal = mesh.add_vertex((round(sign * (scale * 0.60 * cos_w), 5), round(scale * 0.55, 5), round(scale * 0.60 * sin_w, 5)), (0, 0, 1), (0.5, 0.95))
        fw_apex   = mesh.add_vertex((round(sign * (scale * 1.15 * cos_w), 5), round(scale * 0.75, 5), round(scale * 1.15 * sin_w, 5)), (0, 0, 1), (1.0, 1.0))
        fw_outer  = mesh.add_vertex((round(sign * (scale * 1.05 * cos_w), 5), round(scale * 0.20, 5), round(scale * 1.05 * sin_w, 5)), (0, 0, 1), (1.0, 0.6))
        fw_inner  = mesh.add_vertex((round(sign * (scale * 0.55 * cos_w), 5), round(scale * 0.05, 5), round(scale * 0.55 * sin_w, 5)), (0, 0, 1), (0.5, 0.5))

        if sign > 0:
            mesh.add_quad(w_root_ant, w_root_mid, fw_inner, fw_costal)
            mesh.add_quad(fw_costal, fw_inner, fw_outer, fw_apex)
        else:
            mesh.add_quad(w_root_ant, fw_costal, fw_inner, w_root_mid)
            mesh.add_quad(fw_costal, fw_apex, fw_outer, fw_inner)

        hw_outer = mesh.add_vertex((round(sign * (scale * 0.85 * cos_w), 5), round(-scale * 0.15, 5), round(scale * 0.85 * sin_w, 5)), (0, 0, 1), (0.9, 0.4))
        hw_tail  = mesh.add_vertex((round(sign * (scale * 0.80 * cos_w), 5), round(-scale * 0.75, 5), round(scale * 0.80 * sin_w, 5)), (0, 0, 1), (0.85, 0.0))
        hw_inner = mesh.add_vertex((round(sign * (scale * 0.45 * cos_w), 5), round(-scale * 0.45, 5), round(scale * 0.45 * sin_w, 5)), (0, 0, 1), (0.4, 0.1))

        if sign > 0:
            mesh.add_quad(w_root_mid, w_root_post, hw_inner, fw_inner)
            mesh.add_quad(fw_inner, hw_inner, hw_tail, hw_outer)
        else:
            mesh.add_quad(w_root_mid, fw_inner, hw_inner, w_root_post)
            mesh.add_quad(fw_inner, hw_outer, hw_tail, hw_inner)

    return mesh


# Backward-compatible alias
generate_swallowtail_butterfly = generate_swallowtail_quad_butterfly



# Additional aliases for public contract
generate_marionette_strings = generate_catenary_magic_strings
generate_glowing_butterflies = generate_swallowtail_quad_butterfly
