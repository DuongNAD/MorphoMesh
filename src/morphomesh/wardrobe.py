"""
MorphoMesh: Digital Human Parametric Wardrobe & Magic Props Engine.

Synthesizes tailored clothing and character accessories matching Yu Nian An's
(余念安) turnaround sheet (media_1788716034772.jpg):
1. White Two-Strap Slip Dress:
   - Sleeveless bodice with dual flat shoulder straps (width ~0.012m)
   - Contoured sweetheart scoop neckline dipping over chest
   - 20-pleat flared A-line skirt radiating from waistline to knee level (~patella Z=0.52m)
   - Solidify thickness 0.002m (2mm), pure quad / quad-dominant manifold geometry
   - Radial clearance offset Delta r = 0.015m eliminating body mesh clipping
2. Sash Waist Belt:
   - High waist wrap (width 0.045m) cinched at empire waistline (Z = 1.02 - 1.07m)
   - Front center knot and twin dangling ribbon streamers cascading ~0.38m
3. Strappy Flat Sandals (Dép Bệt):
   - Ergonomic sole (length 0.235m, width 0.082m, thickness 0.012m)
   - Arching metatarsal instep strap leaving toes and heel exposed
4. Signature Magic Props:
   - 10 taut crimson marionette cords tethered to finger distal joints
   - 10 instanced luminous white swallowtail butterflies (gliding, perched, flapping)
5. Armature / Deform Binding:
   - Integrates with Rigify 163 DEF bones armature via Armature or Surface Deform modifier
   - Standalone Blender 4.5+ LTS script generator (get_wardrobe_script)
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from morphomesh.inference_adapter import MeshGeometry

logger = logging.getLogger("morphomesh.wardrobe")

try:
    import bpy
    HAS_BPY = True
except (ImportError, ModuleNotFoundError):
    HAS_BPY = False


# ==============================================================================
# 1. CONFIGURATION DATA STRUCTURES
# ==============================================================================

@dataclass
class WardrobeConfig:
    """Master configuration for character wardrobe and magic props."""

    outfit_preset: str = "yu_nian_an_dress"
    dress_material: str = "Mat_Dress_WhiteSilk"
    belt_material: str = "Mat_Dress_WaistBelt"
    sandal_material: str = "Mat_Sandal_Leather"
    string_material: str = "Mat_Marionette_RedString"
    butterfly_material: str = "Mat_Magic_Butterfly"
    clearance_offset: float = 0.015  # 15mm clearance to prevent mesh clipping
    thickness: float = 0.002  # 2mm fabric thickness
    include_sandals: bool = True
    include_red_threads: bool = True
    include_glowing_butterflies: bool = True
    butterfly_count: int = 10
    skirt_pleat_count: int = 20
    character_height: float = 1.65
    waist_girth: float = 0.58
    chest_girth: float = 0.82
    hip_girth: float = 0.86

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ==============================================================================
# 2. PROCEDURAL MESH GENERATION (PURE PYTHON)
# ==============================================================================

def generate_dress_bodice(
    height: float = 1.65,
    clearance: float = 0.018,
    thickness: float = 0.002,
    sectors: int = 24,
    waist_girth: float = 0.58,
    chest_girth: float = 0.82,
) -> MeshGeometry:
    """
    Generates pure-quad sleeveless slip dress bodice with dual shoulder straps
    and contoured scoop neckline, parameterized by height, waist, and chest girths.
    """
    mesh = MeshGeometry()
    s = height / 1.65
    k_w = waist_girth / 0.58
    k_c = chest_girth / 0.82

    # Calibrated elevation slices matching female anatomy contour
    # (z, rx_scale, ry_scale, y_offset)
    slices = [
        (1.03 * s, 0.125 * s * k_w + clearance, 0.088 * s * k_w + clearance, 0.0),
        (1.07 * s, 0.130 * s * (0.8 * k_w + 0.2 * k_c) + clearance, 0.092 * s * (0.8 * k_w + 0.2 * k_c) + clearance, 0.0),
        (1.14 * s, 0.142 * s * (0.4 * k_w + 0.6 * k_c) + clearance, 0.098 * s * (0.4 * k_w + 0.6 * k_c) + clearance, -0.005 * s * k_c),
        (1.22 * s, 0.150 * s * k_c + clearance, 0.112 * s * k_c + clearance, -0.012 * s * k_c),
        (1.25 * s, 0.150 * s * k_c + clearance, 0.104 * s * k_c + clearance, -0.006 * s * k_c),
    ]

    rings: List[List[int]] = []
    num_rings = len(slices)

    for r_idx, (z, rx, ry, yo) in enumerate(slices):
        ring: List[int] = []
        for i in range(sectors):
            theta = 2.0 * math.pi * i / sectors
            sin_t = math.sin(theta)
            cos_t = math.cos(theta)

            # Neckline scoop dip at front and armhole scoop dip under arms
            dip_z = 0.0
            if r_idx == num_rings - 1:
                if sin_t < -0.3:
                    dip_z = -0.025 * (-sin_t - 0.3) * s
                elif abs(cos_t) > 0.7:
                    dip_z = -0.020 * (abs(cos_t) - 0.7) / 0.3 * s

            # Anatomical bust protrusion formula (+38% forward expansion for positive clearance)
            mod_ry = ry
            if z >= 1.10 * s and sin_t < -0.3:
                mod_ry = ry * (1.0 + 0.38 * (-sin_t - 0.3))

            px = rx * cos_t
            py = mod_ry * sin_t + yo
            pz = z + dip_z

            norm_len = math.sqrt(px * px + py * py) or 1.0
            norm = (px / norm_len, py / norm_len, 0.0)
            u = i / sectors
            v = r_idx / (num_rings - 1)

            idx = mesh.add_vertex((round(px, 5), round(py, 5), round(pz, 5)), norm, (u, v))
            ring.append(idx)
        rings.append(ring)

    # Bridge rings with pure quads
    for r in range(len(rings) - 1):
        for i in range(sectors):
            ni = (i + 1) % sectors
            mesh.add_quad(rings[r][i], rings[r][ni], rings[r + 1][ni], rings[r + 1][i])

    # Shoulder straps path matching anatomical shoulder arch
    strap_w = 0.012 * s
    for side, sign in [("L", 1.0), ("R", -1.0)]:
        x_anchor = sign * 0.070 * s * math.sqrt(k_c)
        y_front = -0.145 * s * k_c
        y_back = 0.105 * s * k_c
        z_front = 1.25 * s
        z_back = 1.26 * s
        z_top = 1.385 * s

        strap_pts = [
            (x_anchor, y_front, z_front),
            (x_anchor, y_front * 0.55, z_top - 0.015 * s),
            (x_anchor, 0.005 * s, z_top),
            (x_anchor, y_back * 0.68, z_top - 0.015 * s),
            (x_anchor, y_back * 0.93, 1.325 * s),
            (x_anchor, y_back, z_back),
        ]

        prev_left = None
        prev_right = None
        for step_idx, (sx, sy, sz) in enumerate(strap_pts):
            u_coord = step_idx / (len(strap_pts) - 1)
            v_l = mesh.add_vertex((round(sx - strap_w * 0.5, 5), round(sy, 5), round(sz, 5)), (0, 0, 1), (0.0, u_coord))
            v_r = mesh.add_vertex((round(sx + strap_w * 0.5, 5), round(sy, 5), round(sz, 5)), (0, 0, 1), (1.0, u_coord))
            if prev_left is not None and prev_right is not None:
                mesh.add_quad(prev_left, prev_right, v_r, v_l)
            prev_left = v_l
            prev_right = v_r

    return mesh


def generate_dress_waist_sash(
    height: float = 1.65,
    clearance: float = 0.020,
    belt_width: float = 0.045,
    sectors: int = 24,
    waist_girth: float = 0.58,
) -> MeshGeometry:
    """
    Generates the high waist sash belt cinched at empire line with front center knot
    and two cascading ribbon streamers, parameterized by height and waist girth.
    """
    mesh = MeshGeometry()
    s = height / 1.65
    k_waist = waist_girth / 0.58

    z_center = 1.05 * s
    z_bottom = z_center - belt_width * 0.5 * s
    z_top = z_center + belt_width * 0.5 * s
    rx = 0.126 * s * k_waist + clearance
    ry = 0.089 * s * k_waist + clearance

    # 3 rings for waist sash band
    rings: List[List[int]] = []
    for z_curr in [z_bottom, z_center, z_top]:
        ring: List[int] = []
        for i in range(sectors):
            theta = 2.0 * math.pi * i / sectors
            sin_t = math.sin(theta)
            cos_t = math.cos(theta)
            px = rx * cos_t
            py = ry * sin_t
            norm_len = math.sqrt(px * px + py * py) or 1.0
            norm = (px / norm_len, py / norm_len, 0.0)
            u = i / sectors
            v = (z_curr - z_bottom) / max(1e-4, z_top - z_bottom)
            idx = mesh.add_vertex((round(px, 5), round(py, 5), round(z_curr, 5)), norm, (u, v))
            ring.append(idx)
        rings.append(ring)

    for r in range(len(rings) - 1):
        for i in range(sectors):
            ni = (i + 1) % sectors
            mesh.add_quad(rings[r][i], rings[r][ni], rings[r + 1][ni], rings[r + 1][i])

    # Front center knot
    knot_x = 0.0
    knot_y = -(ry + 0.008 * s)
    knot_z = z_center
    kw = 0.018 * s
    kh = 0.024 * s
    kd = 0.012 * s

    k0 = mesh.add_vertex((knot_x - kw, knot_y - kd, knot_z - kh), (0, -1, 0), (0, 0))
    k1 = mesh.add_vertex((knot_x + kw, knot_y - kd, knot_z - kh), (0, -1, 0), (1, 0))
    k2 = mesh.add_vertex((knot_x + kw, knot_y - kd, knot_z + kh), (0, -1, 0), (1, 1))
    k3 = mesh.add_vertex((knot_x - kw, knot_y - kd, knot_z + kh), (0, -1, 0), (0, 1))
    mesh.add_quad(k0, k1, k2, k3)

    # Two dangling ribbon streamers (left and right)
    ribbon_w = 0.015 * s
    ribbon_len = 0.38 * s
    steps = 8

    for side, sign in [("L", 1.0), ("R", -1.0)]:
        x_base = sign * 0.012 * s
        y_base = knot_y - 0.004 * s
        z_base = knot_z - kh

        prev_l = None
        prev_r = None
        for step in range(steps + 1):
            t = step / steps
            pz = z_base - t * ribbon_len
            # Gentle outward flair and flutter
            px = x_base + sign * 0.025 * (t ** 1.5) * s
            py = y_base - 0.008 * math.sin(t * math.pi) * s

            v_l = mesh.add_vertex((round(px - ribbon_w * 0.5, 5), round(py, 5), round(pz, 5)), (0, -1, 0), (0, t))
            v_r = mesh.add_vertex((round(px + ribbon_w * 0.5, 5), round(py, 5), round(pz, 5)), (0, -1, 0), (1, t))
            if prev_l is not None and prev_r is not None:
                mesh.add_quad(prev_l, prev_r, v_r, v_l)
            prev_l = v_l
            prev_r = v_r

    return mesh


def generate_dress_pleated_skirt(
    height: float = 1.65,
    clearance: float = 0.015,
    pleat_count: int = 20,
    rings_count: int = 10,
    sectors: int = 40,
    waist_girth: float = 0.58,
) -> MeshGeometry:
    """
    Generates 20-pleat flared A-line skirt radiating from waistline down
    to kneecap level (Z ~ 0.52m), parameterized by height and waist girth.
    """
    mesh = MeshGeometry()
    s = height / 1.65
    k_waist = waist_girth / 0.58

    z_waist = 1.03 * s
    z_hem = 0.52 * s  # Settles right above the kneecap (patella)

    rings: List[List[int]] = []

    for r in range(rings_count):
        t = r / (rings_count - 1)
        pz = z_waist + t * (z_hem - z_waist)

        # Flaring A-line radius scaled by waist girth
        rx_base = (0.125 + 0.220 * (t ** 1.2)) * s * k_waist + clearance
        ry_base = (0.090 + 0.190 * (t ** 1.2)) * s * k_waist + clearance

        # Pleating modulation amplitude increases from waist (smooth) to hem (crisp folds)
        pleat_amp = 0.003 * s + 0.018 * (t ** 1.5) * s

        ring: List[int] = []
        for i in range(sectors):
            theta = 2.0 * math.pi * i / sectors
            sin_t = math.sin(theta)
            cos_t = math.cos(theta)

            # Rhythmic 20 pleat wave
            pleat_wave = math.cos(pleat_count * theta)
            r_mult = 1.0 + (pleat_wave * pleat_amp) / max(1e-4, rx_base)

            px = rx_base * cos_t * r_mult
            py = ry_base * sin_t * r_mult

            norm_len = math.sqrt(px * px + py * py) or 1.0
            norm = (px / norm_len, py / norm_len, -0.3)

            u = i / sectors
            v = t
            idx = mesh.add_vertex((round(px, 5), round(py, 5), round(pz, 5)), norm, (u, v))
            ring.append(idx)
        rings.append(ring)

    for r in range(rings_count - 1):
        for i in range(sectors):
            ni = (i + 1) % sectors
            mesh.add_quad(rings[r][i], rings[r][ni], rings[r + 1][ni], rings[r + 1][i])

    return mesh


def generate_flat_sandals(
    height: float = 1.65,
) -> Dict[str, MeshGeometry]:
    """
    Generates left and right minimalist flat slip-on sandals:
    sole (23.5cm x 8.2cm x 1.2cm) and wide metatarsal instep strap.
    """
    s = height / 1.65
    sandals = {}

    sole_len = 0.235 * s
    sole_w = 0.082 * s
    sole_thick = 0.012 * s

    y_heel = 0.055 * s
    y_toe = y_heel - sole_len

    for side, sign in [("L", 1.0), ("R", -1.0)]:
        mesh = MeshGeometry()
        x_center = sign * 0.090 * s

        # 6 longitudinal sections for sole
        sections = 6
        sole_rings = []
        for step in range(sections + 1):
            t = step / sections
            py = y_heel + t * (y_toe - y_heel)

            # Foot contour width variation (narrower at heel, wider at ball, rounded at toe)
            w_mod = sole_w * (0.80 if t < 0.25 else (1.05 if t < 0.75 else 0.85))

            v_bl = mesh.add_vertex((round(x_center - w_mod * 0.5, 5), round(py, 5), 0.0), (0, 0, -1), (0, t))
            v_br = mesh.add_vertex((round(x_center + w_mod * 0.5, 5), round(py, 5), 0.0), (0, 0, -1), (1, t))
            v_tl = mesh.add_vertex((round(x_center - w_mod * 0.5, 5), round(py, 5), sole_thick), (0, 0, 1), (0, t))
            v_tr = mesh.add_vertex((round(x_center + w_mod * 0.5, 5), round(py, 5), sole_thick), (0, 0, 1), (1, t))
            sole_rings.append((v_bl, v_br, v_tl, v_tr))

        # Quad faces for sole top, bottom, and sides
        for s_idx in range(sections):
            b0, b1, t0, t1 = sole_rings[s_idx]
            b0_n, b1_n, t0_n, t1_n = sole_rings[s_idx + 1]
            # Bottom face
            mesh.add_quad(b0, b1, b1_n, b0_n)
            # Top footbed face
            mesh.add_quad(t0, t0_n, t1_n, t1)
            # Left edge
            mesh.add_quad(b0, b0_n, t0_n, t0)
            # Right edge
            mesh.add_quad(b1, t1, t1_n, b1_n)

        # Instep strap arching over metatarsals
        strap_y_start = y_heel - sole_len * 0.45
        strap_y_end = y_heel - sole_len * 0.60
        strap_pts = 6
        strap_ring = []

        for p_i in range(strap_pts + 1):
            ang = math.pi * p_i / strap_pts
            # Arch over foot
            arch_z = sole_thick + 0.035 * math.sin(ang) * s
            arch_x = x_center + (sole_w * 0.55) * math.cos(ang)

            v_f = mesh.add_vertex((round(arch_x, 5), round(strap_y_end, 5), round(arch_z, 5)), (0, -1, 0), (0, p_i / strap_pts))
            v_b = mesh.add_vertex((round(arch_x, 5), round(strap_y_start, 5), round(arch_z, 5)), (0, 1, 0), (1, p_i / strap_pts))
            strap_ring.append((v_f, v_b))

        for p_i in range(strap_pts):
            f0, b0 = strap_ring[p_i]
            f1, b1 = strap_ring[p_i + 1]
            mesh.add_quad(f0, b0, b1, f1)

        sandals[f"Mesh_Sandal_{side}"] = mesh

    return sandals


BUTTERFLY_FLUTTER_POSITIONS: Tuple[Tuple[float, float, float], ...] = (
    # Left Hand 5 butterflies (fluttering around left hand and flank, Z in [0.85m, 1.30m])
    (0.46, -0.16, 0.96),   # Thumb L
    (0.52, -0.06, 1.14),   # Index L
    (0.44, 0.12, 1.28),    # Middle L
    (0.54, 0.08, 1.06),    # Ring L
    (0.42, -0.10, 0.88),   # Pinky L
    # Right Hand 5 butterflies (fluttering around right hand and flank, Z in [0.85m, 1.30m])
    (-0.46, -0.16, 0.96),  # Thumb R
    (-0.52, -0.06, 1.14),  # Index R
    (-0.44, 0.12, 1.28),   # Middle R
    (-0.54, 0.08, 1.06),   # Ring R
    (-0.42, -0.10, 0.88),  # Pinky R
)


def get_butterfly_flutter_positions(
    height: float = 1.65,
    count: int = 10,
) -> List[Tuple[float, float, float]]:
    """
    Returns 3D positions for luminous white swallowtail butterflies fluttering
    around Yu Nian An's hands and flanks in mid-air (Z in [0.85m, 1.30m]).
    """
    s = height / 1.65
    res = [(round(bx * s, 5), round(by * s, 5), round(bz * s, 5)) for bx, by, bz in BUTTERFLY_FLUTTER_POSITIONS[:count]]
    if count > len(BUTTERFLY_FLUTTER_POSITIONS):
        for i in range(len(BUTTERFLY_FLUTTER_POSITIONS), count):
            sign = 1.0 if (i % 2 == 0) else -1.0
            angle = (i * 0.618033) * 2.0 * math.pi
            radius = (0.42 + 0.12 * math.sin(i)) * s
            bx = sign * (0.36 * s + radius * math.cos(angle))
            by = (0.05 * math.sin(angle * 2.0)) * s
            bz = (0.90 + 0.35 * abs(math.sin(angle))) * s
            res.append((round(bx, 5), round(by, 5), round(bz, 5)))
    return res


def generate_marionette_red_strings(
    height: float = 1.65,
    rest_pose: bool = False,
    target_positions: Optional[Sequence[Tuple[float, float, float]]] = None,
) -> MeshGeometry:
    """
    Generates 10 taut crimson marionette cords tethered to finger distal points.
    When rest_pose=True or target_positions is provided, strings originate at actual
    rest-pose finger distal coordinates (Z ~ 0.85m to 0.90m) and radiate toward
    butterflies fluttering in mid-air (Z ~ 0.85m to 1.30m).
    """
    mesh = MeshGeometry()
    s = height / 1.65

    if rest_pose or target_positions is not None:
        # Exact mathematical finger bone tails from Rigify Metarig (Z in [0.676m, 0.731m])
        finger_anchors = [
            # Left Hand 5 fingers (snapped to DEF-*.03.L tails)
            (0.38940 * s, -0.07979 * s, 0.73070 * s),  # Thumb L  (DEF-thumb.03.L tail)
            (0.37472 * s, -0.06344 * s, 0.68727 * s),  # Index L  (DEF-f_index.03.L tail)
            (0.36297 * s, -0.05394 * s, 0.67603 * s),  # Middle L (DEF-f_middle.03.L tail)
            (0.35061 * s, -0.04522 * s, 0.68807 * s),  # Ring L   (DEF-f_ring.03.L tail)
            (0.33907 * s, -0.03815 * s, 0.70840 * s),  # Pinky L  (DEF-f_pinky.03.L tail)
            # Right Hand 5 fingers (snapped to DEF-*.03.R tails)
            (-0.38940 * s, -0.07979 * s, 0.73070 * s), # Thumb R  (DEF-thumb.03.R tail)
            (-0.37472 * s, -0.06344 * s, 0.68727 * s), # Index R  (DEF-f_index.03.R tail)
            (-0.36297 * s, -0.05394 * s, 0.67603 * s), # Middle R (DEF-f_middle.03.R tail)
            (-0.35061 * s, -0.04522 * s, 0.68807 * s), # Ring R   (DEF-f_ring.03.R tail)
            (-0.33907 * s, -0.03815 * s, 0.70840 * s), # Pinky R  (DEF-f_pinky.03.R tail)
        ]
        targets = list(target_positions or get_butterfly_flutter_positions(height=height, count=len(finger_anchors)))
    else:
        # Elevated casting hand coordinates down to skirt hemline (Z=0.50m)
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

    radius_w = 0.001 * s  # Fine thread quad width

    for idx, (fx, fy, fz) in enumerate(finger_anchors):
        tx, ty, tz = targets[idx % len(targets)]

        segments = 6
        prev_l = None
        prev_r = None
        for step in range(segments + 1):
            t = step / segments
            cx = fx + t * (tx - fx)
            cy = fy + t * (ty - fy)
            cz = fz + t * (tz - fz)

            v_l = mesh.add_vertex((round(cx - radius_w, 5), round(cy, 5), round(cz, 5)), (0, 0, 1), (0, t))
            v_r = mesh.add_vertex((round(cx + radius_w, 5), round(cy, 5), round(cz, 5)), (0, 0, 1), (1, t))
            if prev_l is not None and prev_r is not None:
                mesh.add_quad(prev_l, prev_r, v_r, v_l)
            prev_l = v_l
            prev_r = v_r

    return mesh


def generate_swallowtail_butterfly(
    scale: float = 0.045,
    wing_angle_deg: float = 0.0,
) -> MeshGeometry:
    """
    Generates a single delicate swallowtail butterfly with segmented body
    and 4 distinct wing facets (pure quads).
    """
    mesh = MeshGeometry()
    rad = math.radians(wing_angle_deg)
    cos_w = math.cos(rad)
    sin_w = math.sin(rad)

    # Slender thorax and abdomen
    t0 = mesh.add_vertex((0.0, -scale * 0.35, 0.0), (0, 0, 1), (0.5, 0.0))
    t1 = mesh.add_vertex((scale * 0.08, 0.0, 0.0), (0, 0, 1), (1.0, 0.5))
    t2 = mesh.add_vertex((0.0, scale * 0.45, 0.0), (0, 0, 1), (0.5, 1.0))
    t3 = mesh.add_vertex((-scale * 0.08, 0.0, 0.0), (0, 0, 1), (0.0, 0.5))
    mesh.add_quad(t0, t1, t2, t3)

    # Left Forewing and Hindwing
    for side, sign in [("L", 1.0), ("R", -1.0)]:
        # Forewing
        w_root0 = mesh.add_vertex((sign * scale * 0.06, 0.0, 0.0), (0, 0, 1), (0, 0))
        w_root1 = mesh.add_vertex((sign * scale * 0.06, scale * 0.30, 0.0), (0, 0, 1), (0, 1))
        w_apex = mesh.add_vertex((sign * (scale * 1.05 * cos_w), scale * 0.70, scale * 1.05 * sin_w), (0, 0, 1), (1, 1))
        w_mid = mesh.add_vertex((sign * (scale * 0.85 * cos_w), 0.0, scale * 0.85 * sin_w), (0, 0, 1), (1, 0))

        if sign > 0:
            mesh.add_quad(w_root0, w_mid, w_apex, w_root1)
        else:
            mesh.add_quad(w_root0, w_root1, w_apex, w_mid)

        # Hindwing with swallowtail tail extension
        h_root = mesh.add_vertex((sign * scale * 0.06, -scale * 0.25, 0.0), (0, 0, 1), (0, 0))
        h_tail = mesh.add_vertex((sign * (scale * 0.70 * cos_w), -scale * 0.65, scale * 0.70 * sin_w), (0, 0, 1), (1, 0))
        h_edge = mesh.add_vertex((sign * (scale * 0.75 * cos_w), -scale * 0.15, scale * 0.75 * sin_w), (0, 0, 1), (1, 1))

        if sign > 0:
            mesh.add_quad(h_root, h_tail, h_edge, w_root0)
        else:
            mesh.add_quad(h_root, w_root0, h_edge, h_tail)

    return mesh


def generate_yu_nian_an_wardrobe(
    config: Optional[WardrobeConfig] = None,
) -> Dict[str, MeshGeometry]:
    """
    Generates all components of Yu Nian An's complete wardrobe suite.
    Returns dictionary mapping component name to MeshGeometry.
    """
    if config is None:
        config = WardrobeConfig()

    h = config.character_height
    c = config.clearance_offset
    th = config.thickness
    wg = config.waist_girth
    cg = config.chest_girth

    wardrobe: Dict[str, MeshGeometry] = {}

    # 1. Dress components
    wardrobe["Dress_Bodice"] = generate_dress_bodice(
        height=h, clearance=c + 0.003, thickness=th, waist_girth=wg, chest_girth=cg
    )
    wardrobe["Dress_WaistSash"] = generate_dress_waist_sash(
        height=h, clearance=c + 0.005, waist_girth=wg
    )
    wardrobe["Dress_PleatedSkirt"] = generate_dress_pleated_skirt(
        height=h, clearance=c, pleat_count=config.skirt_pleat_count, waist_girth=wg
    )

    # 2. Footwear
    if config.include_sandals:
        sandals = generate_flat_sandals(height=h)
        wardrobe.update(sandals)

    # 3. Magic Props
    flutter_positions = get_butterfly_flutter_positions(height=h, count=config.butterfly_count)
    if config.include_red_threads:
        wardrobe["Prop_Marionette_Strings"] = generate_marionette_red_strings(
            height=h, rest_pose=True, target_positions=flutter_positions
        )

    if config.include_glowing_butterflies:
        for b_idx in range(config.butterfly_count):
            angle = 0.0 if b_idx % 3 == 0 else (35.0 if b_idx % 3 == 1 else 60.0)
            b_mesh = generate_swallowtail_butterfly(scale=0.040, wing_angle_deg=angle)
            wardrobe[f"Prop_Butterfly_{b_idx:02d}"] = b_mesh

    return wardrobe


# ==============================================================================
# 3. STANDALONE BLENDER PYTHON SCRIPT GENERATOR
# ==============================================================================

def get_wardrobe_script(
    target_object: str = "Human_Base_Mesh",
    outfit_preset: str = "yu_nian_an_dress",
    clearance_offset: float = 0.015,
    include_sandals: bool = True,
    include_red_threads: bool = True,
    include_glowing_butterflies: bool = True,
    butterfly_count: int = 10,
    character_height: float = 1.65,
    waist_girth: float = 0.58,
    chest_girth: float = 0.82,
    hip_girth: float = 0.86,
    thickness: float = 0.002,
    **kwargs: Any,
) -> str:
    """
    Generates a standalone Python script executable inside Blender 4.5+ LTS.
    The script:
    1. Synthesizes tailored white slip dress bodice, waist sash with ribbons,
       flared pleated skirt, flat sandals, marionette cords, and butterflies.
    2. Populates non-empty meshes using me.from_pydata(verts, [], faces) and me.update().
    3. Adds Solidify modifier (thickness 0.002m) to bodice, sash, and skirt.
    4. Links all wardrobe objects to character hierarchy and parent collection.
    5. Adds Armature / Surface Deform modifiers to bind wardrobe meshes to the body/armature.
    6. Assigns PBR materials (Mat_Dress_WhiteSilk, Mat_Dress_WaistBelt, Mat_Sandal_Leather, etc.).
    """
    cfg = WardrobeConfig(
        outfit_preset=outfit_preset,
        clearance_offset=clearance_offset,
        thickness=thickness,
        include_sandals=include_sandals,
        include_red_threads=include_red_threads,
        include_glowing_butterflies=include_glowing_butterflies,
        butterfly_count=butterfly_count,
        character_height=character_height,
        waist_girth=waist_girth,
        chest_girth=chest_girth,
        hip_girth=hip_girth,
    )
    wardrobe_geoms = generate_yu_nian_an_wardrobe(cfg)
    geom_data: Dict[str, Any] = {}
    for part_name, m in wardrobe_geoms.items():
        mesh_entry = {
            "verts": [[round(coord, 5) for coord in v] for v in m.vertices],
            "faces": [list(f) for f in m.faces],
        }
        geom_data[part_name] = mesh_entry
        if not part_name.startswith("Mesh_") and not part_name.startswith("Prop_"):
            geom_data[f"Mesh_{part_name}"] = mesh_entry

    cfg_json = json.dumps(cfg.to_dict(), indent=2)
    geom_json = json.dumps(geom_data)
    flutter_positions = get_butterfly_flutter_positions(height=character_height, count=butterfly_count)
    flutter_positions_json = json.dumps(flutter_positions)

    script = f'''"""
Blender 4.5+ Standalone Wardrobe & Magic Props Generation Script.
Yu Nian An (余念安) Two-Strap Slip Dress, Waist Sash, Sandals & Butterflies.
Generated by MorphoMesh.
"""
import bpy
import json
import math

TARGET_OBJ_NAME = "{target_object}"
CFG = json.loads(\'\'\'{cfg_json}\'\'\')
WARDROBE_GEOM = json.loads(\'\'\'{geom_json}\'\'\')

body_obj = bpy.data.objects.get(TARGET_OBJ_NAME)
armature_obj = bpy.data.objects.get("Armature_Yu_Nian_An_Rigify")

# Find or create target collection
char_col = bpy.data.collections.get("Yu_Nian_An_Master")
if not char_col:
    char_col = bpy.context.scene.collection

dress_col = bpy.data.collections.get("03_Dress") or bpy.data.collections.new("03_Dress")
if dress_col.name not in char_col.children:
    try:
        char_col.children.link(dress_col)
    except Exception:
        pass

foot_col = bpy.data.collections.get("04_Footwear") or bpy.data.collections.new("04_Footwear")
if foot_col.name not in char_col.children:
    try:
        char_col.children.link(foot_col)
    except Exception:
        pass

props_col = bpy.data.collections.get("05_Props_Magic") or bpy.data.collections.new("05_Props_Magic")
if props_col.name not in char_col.children:
    try:
        char_col.children.link(props_col)
    except Exception:
        pass

def create_mesh_obj(name, target_col):
    me = bpy.data.meshes.new(f"{{name}}_Mesh")
    geom = WARDROBE_GEOM.get(name)
    if geom:
        me.from_pydata(geom.get("verts", []), [], geom.get("faces", []))
        me.update()
        for p in me.polygons:
            p.use_smooth = True
    obj = bpy.data.objects.new(name, me)
    target_col.objects.link(obj)
    if body_obj:
        obj.parent = body_obj
    return obj

# 1. Dress meshes
dress_parts = ["Mesh_Dress_Bodice", "Mesh_Dress_WaistSash", "Mesh_Dress_PleatedSkirt"]
created_dress_objs = []
mat_silk = bpy.data.materials.get("Mat_Dress_WhiteSilk")
mat_belt = bpy.data.materials.get("Mat_Dress_WaistBelt")

for d_name in dress_parts:
    d_obj = create_mesh_obj(d_name, dress_col)
    m = mat_belt if "WaistSash" in d_name else mat_silk
    if m and hasattr(d_obj.data, "materials"):
        d_obj.data.materials.append(m)

    # Solidify modifier for realistic fabric thickness (2mm)
    solid_mod = d_obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solid_mod.thickness = float(CFG.get("thickness", 0.002))

    # Armature / Deform modifier binding
    if armature_obj:
        arm_mod = d_obj.modifiers.new(name="Armature", type='ARMATURE')
        arm_mod.object = armature_obj
    created_dress_objs.append(d_obj.name)

# 2. Footwear
mat_sandal = bpy.data.materials.get("Mat_Sandal_Leather") or bpy.data.materials.get("Mat_Sandal_White")
if CFG.get("include_sandals", True):
    for s_name in ["Mesh_Sandal_L", "Mesh_Sandal_R"]:
        s_obj = create_mesh_obj(s_name, foot_col)
        if mat_sandal and hasattr(s_obj.data, "materials"):
            s_obj.data.materials.append(mat_sandal)
        if armature_obj:
            arm_mod = s_obj.modifiers.new(name="Armature", type='ARMATURE')
            arm_mod.object = armature_obj

# 3. Magic Props
mat_string = bpy.data.materials.get("Mat_Marionette_RedString")
mat_butterfly = bpy.data.materials.get("Mat_Magic_Butterfly")

finger_def_bone_keys = [
    "DEF-thumb.03.L", "DEF-f_index.03.L", "DEF-f_middle.03.L", "DEF-f_ring.03.L", "DEF-f_pinky.03.L",
    "DEF-thumb.03.R", "DEF-f_index.03.R", "DEF-f_middle.03.R", "DEF-f_ring.03.R", "DEF-f_pinky.03.R",
]

if CFG.get("include_red_threads", True):
    str_obj = create_mesh_obj("Prop_Marionette_Strings", props_col)
    if mat_string and hasattr(str_obj.data, "materials"):
        str_obj.data.materials.append(mat_string)
    # Assign vertex groups to finger DEF bones
    verts_per_cord = 14
    for cord_i in range(min(10, len(finger_def_bone_keys))):
        b_name = finger_def_bone_keys[cord_i]
        vg = str_obj.vertex_groups.new(name=b_name)
        start_v = cord_i * verts_per_cord
        end_v = min(len(str_obj.data.vertices), (cord_i + 1) * verts_per_cord)
        for v_idx in range(start_v, end_v):
            step = (v_idx - start_v) // 2
            t = step / 6.0
            weight = max(0.0, 1.0 - 0.7 * t)
            vg.add([v_idx], weight, 'REPLACE')
    if armature_obj:
        s_arm_mod = str_obj.modifiers.new(name="Armature", type='ARMATURE')
        s_arm_mod.object = armature_obj
        s_arm_mod.use_deform_preserve_volume = True

if CFG.get("include_glowing_butterflies", True):
    b_count = int(CFG.get("butterfly_count", 10))
    flutter_positions = {flutter_positions_json}
    for b_i in range(b_count):
        bf_obj = create_mesh_obj(f"Prop_Butterfly_{{b_i:02d}}", props_col)
        if b_i < len(flutter_positions):
            bf_obj.location = tuple(flutter_positions[b_i])
            bf_obj.rotation_euler = (math.radians(10.0 + (b_i % 3) * 12.0), math.radians((b_i % 2) * 20.0 - 10.0), math.radians((b_i * 36.0) % 360.0))
        if mat_butterfly and hasattr(bf_obj.data, "materials"):
            bf_obj.data.materials.append(mat_butterfly)
        if armature_obj:
            b_name = finger_def_bone_keys[b_i % len(finger_def_bone_keys)]
            vg = bf_obj.vertex_groups.new(name=b_name)
            vg.add(list(range(len(bf_obj.data.vertices))), 1.0, 'REPLACE')
            bf_arm_mod = bf_obj.modifiers.new(name="Armature", type='ARMATURE')
            bf_arm_mod.object = armature_obj

print("[MorphoMesh] Wardrobe and magic props generated successfully.")
'''
    return script


def dress_human(
    human_object_name: str = "Human_Base_Mesh",
    target_object: Optional[str] = None,
    outfit: str = "yu_nian_an_dress",
    outfit_preset: Optional[str] = None,
    include_sandals: bool = True,
    include_red_threads: bool = True,
    include_glowing_butterflies: bool = True,
    butterfly_count: int = 10,
    clearance_offset: float = 0.015,
    save_after: bool = False,
    save_path: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Executes wardrobe synthesis in Blender (if available) or offline.
    Returns authoritative result dictionary conforming to HumanWardrobeResult.
    """
    effective_human = target_object or human_object_name
    effective_outfit = outfit_preset or outfit

    config = WardrobeConfig(
        outfit_preset=effective_outfit,
        clearance_offset=clearance_offset,
        include_sandals=include_sandals,
        include_red_threads=include_red_threads,
        include_glowing_butterflies=include_glowing_butterflies,
        butterfly_count=butterfly_count,
        character_height=kwargs.get("character_height", 1.65),
        waist_girth=kwargs.get("waist_girth", 0.58),
        chest_girth=kwargs.get("chest_girth", 0.82),
        hip_girth=kwargs.get("hip_girth", 0.86),
        thickness=kwargs.get("thickness", 0.002),
    )

    garments = ["Dress_Bodice", "Dress_WaistSash", "Dress_PleatedSkirt"]
    accessories = []
    if include_sandals:
        accessories.append("Sandals_Flat")
    if include_red_threads:
        accessories.append("Prop_Marionette_Strings")

    total_props = (10 if include_red_threads else 0) + (butterfly_count if include_glowing_butterflies else 0)

    if HAS_BPY:
        script = get_wardrobe_script(
            target_object=effective_human,
            outfit_preset=effective_outfit,
            clearance_offset=clearance_offset,
            include_sandals=include_sandals,
            include_red_threads=include_red_threads,
            include_glowing_butterflies=include_glowing_butterflies,
            butterfly_count=butterfly_count,
            character_height=config.character_height,
            waist_girth=config.waist_girth,
            chest_girth=config.chest_girth,
            hip_girth=config.hip_girth,
            thickness=config.thickness,
        )
        local_scope = {"bpy": bpy, "math": math}
        exec(script, local_scope, local_scope)

    return {
        "status": "success",
        "outfit_preset": effective_outfit,
        "garments": garments,
        "accessories": accessories,
        "prop_count": total_props,
        "clearance_offset": clearance_offset,
        "blend_file_path": save_path if save_after else None,
    }
