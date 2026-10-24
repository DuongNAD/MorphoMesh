"""
Blender Runtime Script Generation for Digital Human Base Mesh.

Generates authoritative Python script executable inside Blender 4.5+ LTS to
synthesize digital human mesh, assign 24 standardized vertex groups, configure
52 ARKit FACS shape keys, and attach anatomical landmark coordinates.
"""

from __future__ import annotations

from typing import Any, Optional

try:
    from morphomesh.models import HumanAnatomyConfig
except (ImportError, ModuleNotFoundError):
    from ..models import HumanAnatomyConfig  # type: ignore[no-redef]

from .morphology import resolve_human_anatomy_config


def get_human_generation_script(
    mesh_obj_name: str = "Human_Base_Mesh",
    config: Optional[HumanAnatomyConfig] = None,
    height: Optional[float] = None,
    gender: Optional[str] = None,
    proportion_preset: Optional[str] = None,
    **kwargs: Any,
) -> str:
    """
    Generates an authoritative Python script for Blender 4.5+ LTS to synthesize
    the complete digital human mesh, assign 24 standardized vertex groups,
    configure 52 ARKit FACS shape keys, and attach anatomical landmark coordinates.
    """
    cfg = resolve_human_anatomy_config(
        config=config,
        height=height,
        gender=gender,
        proportion_preset=proportion_preset,
        **kwargs,
    )
    height = cfg.height
    head_ratio = cfg.head_ratio
    chest_girth = cfg.chest_girth
    waist_girth = cfg.waist_girth
    hip_girth = cfg.hip_girth
    shoulder_width = cfg.shoulder_width
    arm_span = cfg.arm_span
    leg_length = cfg.leg_length

    return f"""
import bpy
import bmesh
import math
import mathutils

mesh_name = {repr(mesh_obj_name)}
target_height = {height}
target_head_ratio = {head_ratio}
chest_girth = {chest_girth}
waist_girth = {waist_girth}
hip_girth = {hip_girth}
shoulder_width = {shoulder_width}
arm_span = {arm_span}
leg_length = {leg_length}

scale = target_height / 1.65
s = scale

# Parametric scaling factors
k_chest = chest_girth / 0.82
k_waist = waist_girth / 0.58
k_hip = hip_girth / 0.86
k_shoulder = shoulder_width / 0.36
k_arm = arm_span / 1.62
k_leg = leg_length / 0.88

head_height = target_height / target_head_ratio
z_crown = target_height
z_chin = z_crown - head_height
k_head_scale = head_height / (0.223 * s)
z_clavicle = 1.350 * s
z_crotch = 0.825 * s * k_leg

# Remove existing object if present
existing = bpy.data.objects.get(mesh_name)
if existing:
    bpy.data.objects.remove(existing, do_unlink=True)

# Create new mesh and bmesh
me = bpy.data.meshes.new(mesh_name)
bm = bmesh.new()

vg_indices = {{name: [] for name in [
    "head", "face", "eyes_left", "eyes_right", "eyelids", "eyebrows",
    "mouth", "lips", "teeth", "tongue", "neck", "torso", "chest", "waist", "hips",
    "arm_upper_L", "arm_lower_L", "hand_L", "fingers_L",
    "arm_upper_R", "arm_lower_R", "hand_R", "fingers_R",
    "leg_upper_L", "leg_lower_L", "foot_L",
    "leg_upper_R", "leg_lower_R", "foot_R"
]}}

def add_bmesh_quad_cap(bm, ring, flip=False):
    n = len(ring)
    for k in range((n - 2) // 2):
        i0, i1, i2, i3 = ring[k], ring[k + 1], ring[n - 2 - k], ring[n - 1 - k]
        if flip:
            bm.faces.new((i0, i3, i2, i1))
        else:
            bm.faces.new((i0, i1, i2, i3))

def add_bmesh_quad_ellipsoid(bm, center, radii, rings=4, sectors=8):
    cx, cy, cz = center
    rx, ry, rz = radii
    sectors = max(4, sectors if sectors % 2 == 0 else sectors + 1)
    rings = max(2, rings)
    ring_verts = []
    all_verts = []
    for r in range(rings):
        phi = -math.pi / 2.0 + math.pi * (r + 0.5) / rings
        cp, sp = math.cos(phi), math.sin(phi)
        cur_ring = []
        for sec in range(sectors):
            th = 2.0 * math.pi * sec / sectors
            ct, st = math.cos(th), math.sin(th)
            v = bm.verts.new((cx + rx * cp * ct, cy + ry * cp * st, cz + rz * sp))
            cur_ring.append(v)
            all_verts.append(v)
        ring_verts.append(cur_ring)
    for r in range(rings - 1):
        for sec in range(sectors):
            ns = (sec + 1) % sectors
            bm.faces.new((ring_verts[r][sec], ring_verts[r][ns], ring_verts[r + 1][ns], ring_verts[r + 1][sec]))
    add_bmesh_quad_cap(bm, ring_verts[0], flip=True)
    add_bmesh_quad_cap(bm, ring_verts[-1], flip=False)
    return all_verts

# ------------------------------------------------------------------------------
# 1. BODY CROSS-SECTIONS (TORSO, NECK, HEAD)
# ------------------------------------------------------------------------------
raw_slices = [
    (0.825, 0.155, 0.110, 0.000, "hips"),
    (0.860, 0.175, 0.120, 0.002, "hips"),
    (0.900, 0.160, 0.110, 0.000, "hips"),
    (0.940, 0.140, 0.098, -0.005, "waist"),
    (0.990, 0.130, 0.090, -0.008, "waist"),
    (1.050, 0.122, 0.082, -0.010, "waist"),
    (1.110, 0.135, 0.088, -0.008, "chest"),
    (1.160, 0.145, 0.095, -0.005, "chest"),
    (1.220, 0.155, 0.118, -0.012, "chest"),
    (1.270, 0.160, 0.105, -0.006, "chest"),
    (1.320, 0.170, 0.090, 0.000, "torso"),
    (1.350, 0.165, 0.080, 0.005, "torso"),
    (1.370, 0.058, 0.058, 0.010, "neck"),
    (1.400, 0.054, 0.054, 0.015, "neck"),
    (1.427, 0.056, 0.056, 0.020, "neck"),
    (1.445, 0.065, 0.075, -0.035, "head"),
    (1.470, 0.075, 0.088, -0.038, "head"),
    (1.500, 0.082, 0.095, -0.030, "head"),
    (1.530, 0.086, 0.095, -0.015, "head"),
    (1.560, 0.088, 0.096, -0.005, "head"),
    (1.600, 0.086, 0.092, 0.005, "head"),
    (1.635, 0.072, 0.078, 0.008, "head"),
    (1.650, 0.020, 0.025, 0.005, "head"),
]

body_slices = []
for z_can, rx_can, ry_can, yo_can, vg_n in raw_slices:
    if vg_n == "hips":
        u = (z_can - 0.825) / 0.525
        z_s = z_crotch + u * (z_clavicle - z_crotch)
        rx_s = rx_can * s * k_hip
        ry_s = ry_can * s * k_hip
        yo_s = yo_can * s
    elif vg_n == "waist":
        u = (z_can - 0.825) / 0.525
        z_s = z_crotch + u * (z_clavicle - z_crotch)
        rx_s = rx_can * s * k_waist
        ry_s = ry_can * s * k_waist
        yo_s = yo_can * s
    elif vg_n == "chest":
        u = (z_can - 0.825) / 0.525
        z_s = z_crotch + u * (z_clavicle - z_crotch)
        rx_s = rx_can * s * k_chest
        ry_s = ry_can * s * k_chest
        yo_s = yo_can * s
    elif vg_n == "torso":
        u = (z_can - 0.825) / 0.525
        z_s = z_crotch + u * (z_clavicle - z_crotch)
        rx_s = rx_can * s * k_shoulder
        ry_s = ry_can * s * k_shoulder
        yo_s = yo_can * s
    elif vg_n == "neck":
        u = (z_can - 1.350) / (1.427 - 1.350)
        z_s = z_clavicle + u * (z_chin - z_clavicle)
        rx_s = rx_can * s
        ry_s = ry_can * s
        yo_s = yo_can * s
    else:  # "head"
        u = (z_can - 1.427) / 0.223
        z_s = z_chin + u * head_height
        rx_s = rx_can * s * k_head_scale
        ry_s = ry_can * s * k_head_scale
        yo_s = yo_can * s * k_head_scale
    body_slices.append((z_s, rx_s, ry_s, yo_s, vg_n))

sectors = 24
rings_verts = []
for z_val, rx, ry, yo, vg_n in body_slices:
    ring = []
    for i in range(sectors):
        th = 2.0 * math.pi * i / sectors
        ct, st = math.cos(th), math.sin(th)
        mod_y = ry * (1.0 + 0.35 * (-st - 0.3)) if (vg_n == "chest" and st < -0.3) else ry
        rx_mod = rx * 0.85 if (vg_n == "head" and z_val < z_chin + 0.25 * head_height and st < -0.5) else rx

        dx_f = 0.0
        dy_f = 0.0
        if vg_n == "head" and st < -0.2:
            ang_d = abs(th - 1.5 * math.pi)
            if 1.490 * s <= z_val <= 1.545 * s:
                if ang_d < 0.30:
                    z_tip_f = math.exp(-((z_val - 1.505 * s) ** 2) / (2 * ((0.016 * s) ** 2)))
                    bridge_f = max(0.0, min(1.0, (1.545 * s - z_val) / (0.045 * s)))
                    dy_f -= (0.0125 * z_tip_f + 0.0065 * bridge_f) * s
                elif ang_d < 0.60:
                    z_flank_f = math.exp(-((z_val - 1.505 * s) ** 2) / (2 * ((0.016 * s) ** 2)))
                    dy_f -= 0.0060 * z_flank_f * s
                    dx_f = -0.08 * (rx * ct)
            if 1.515 * s <= z_val <= 1.540 * s:
                if 0.40 <= ang_d <= 0.85:
                    dy_f += 0.0040 * s
            if 1.460 * s <= z_val <= 1.485 * s:
                if ang_d < 0.20:
                    dy_f += 0.0020 * s
                elif 0.20 <= ang_d <= 0.45:
                    dy_f -= 0.0025 * s
                elif ang_d > 0.65:
                    dy_f += 0.0025 * s
            if 1.435 * s <= z_val <= 1.455 * s:
                if ang_d < 0.35:
                    dy_f -= 0.0035 * s

        vx = rx_mod * ct + dx_f
        vy = mod_y * st + yo + dy_f
        vz = z_val
        v = bm.verts.new((vx, vy, vz))
        ring.append(v)
        vg_indices[vg_n].append(v)

        if vg_n == "head":
            if z_val < z_chin + 0.65 * head_height and st < 0.0:
                vg_indices["face"].append(v)
            if z_chin + 0.12 * head_height <= z_val <= z_chin + 0.26 * head_height and st < -0.5:
                vg_indices["mouth"].append(v)
                vg_indices["lips"].append(v)
            if z_chin + 0.40 * head_height <= z_val <= z_chin + 0.55 * head_height and st < -0.3:
                if vx > 0.015 * s:
                    vg_indices["eyes_left"].append(v)
                    vg_indices["eyelids"].append(v)
                elif vx < -0.015 * s:
                    vg_indices["eyes_right"].append(v)
                    vg_indices["eyelids"].append(v)
            if z_chin + 0.53 * head_height <= z_val <= z_chin + 0.68 * head_height and st < -0.3:
                vg_indices["eyebrows"].append(v)

    rings_verts.append(ring)

# Connect Rings with Quad Faces
for r in range(len(rings_verts) - 1):
    for i in range(sectors):
        ni = (i + 1) % sectors
        bm.faces.new((rings_verts[r][i], rings_verts[r][ni], rings_verts[r + 1][ni], rings_verts[r + 1][i]))

# Cap Crotch & Crown
add_bmesh_quad_cap(bm, rings_verts[0], flip=True)
add_bmesh_quad_cap(bm, rings_verts[-1], flip=False)

# ------------------------------------------------------------------------------
# 2. INTERNAL FACIAL STRUCTURES (TEETH & TONGUE)
# ------------------------------------------------------------------------------
teeth_center_u = (0.0, -0.030 * s * k_head_scale, z_chin + 0.20 * head_height)
teeth_center_l = (0.0, -0.028 * s * k_head_scale, z_chin + 0.16 * head_height)
teeth_verts = add_bmesh_quad_ellipsoid(bm, teeth_center_u, (0.025 * s * k_head_scale, 0.020 * s * k_head_scale, 0.006 * s * k_head_scale), rings=3, sectors=8)
teeth_verts += add_bmesh_quad_ellipsoid(bm, teeth_center_l, (0.024 * s * k_head_scale, 0.018 * s * k_head_scale, 0.006 * s * k_head_scale), rings=3, sectors=8)
vg_indices["teeth"].extend(teeth_verts)
vg_indices["mouth"].extend(teeth_verts)

tongue_center = (0.0, -0.015 * s * k_head_scale, z_chin + 0.17 * head_height)
tongue_verts = add_bmesh_quad_ellipsoid(bm, tongue_center, (0.018 * s * k_head_scale, 0.025 * s * k_head_scale, 0.008 * s * k_head_scale), rings=3, sectors=8)
vg_indices["tongue"].extend(tongue_verts)
vg_indices["mouth"].extend(tongue_verts)

# ------------------------------------------------------------------------------
# 3. LOWER LIMBS & ARTICULATED FEET (LEFT & RIGHT)
# ------------------------------------------------------------------------------
for side, sign in [("L", 1.0), ("R", -1.0)]:
    leg_up_vg = f"leg_upper_{{side}}"
    leg_low_vg = f"leg_lower_{{side}}"
    foot_vg = f"foot_{{side}}"

    cx_hip = sign * 0.095 * s * k_hip
    cx_knee = sign * 0.098 * s * k_hip
    cx_ankle = sign * 0.088 * s * k_hip

    leg_slices = [
        (0.825 * s * k_leg, 0.085 * s * math.sqrt(k_hip), 0.090 * s * math.sqrt(k_hip), cx_hip, 0.000 * s, leg_up_vg),
        (0.720 * s * k_leg, 0.075 * s * math.sqrt(k_hip), 0.078 * s * math.sqrt(k_hip), cx_hip * 1.02, 0.002 * s, leg_up_vg),
        (0.600 * s * k_leg, 0.065 * s * math.sqrt(k_hip), 0.066 * s * math.sqrt(k_hip), cx_hip * 1.03, 0.000 * s, leg_up_vg),
        (0.510 * s * k_leg, 0.055 * s * math.sqrt(k_hip), 0.055 * s * math.sqrt(k_hip), cx_knee, -0.008 * s, leg_up_vg),
        (0.470 * s * k_leg, 0.050 * s * math.sqrt(k_hip), 0.052 * s * math.sqrt(k_hip), cx_knee, -0.015 * s, leg_low_vg),
        (0.445 * s * k_leg, 0.046 * s * math.sqrt(k_hip), 0.050 * s * math.sqrt(k_hip), cx_knee, -0.020 * s, leg_low_vg),
        (0.420 * s * k_leg, 0.045 * s * math.sqrt(k_hip), 0.048 * s * math.sqrt(k_hip), cx_knee, -0.015 * s, leg_low_vg),
        (0.350 * s * k_leg, 0.048 * s * math.sqrt(k_hip), 0.054 * s * math.sqrt(k_hip), cx_knee * 0.98, 0.010 * s, leg_low_vg),
        (0.260 * s * k_leg, 0.042 * s * math.sqrt(k_hip), 0.044 * s * math.sqrt(k_hip), cx_knee * 0.95, 0.005 * s, leg_low_vg),
        (0.180 * s * k_leg, 0.035 * s * math.sqrt(k_hip), 0.036 * s * math.sqrt(k_hip), cx_ankle, 0.000 * s, leg_low_vg),
        (0.120 * s * k_leg, 0.030 * s * math.sqrt(k_hip), 0.032 * s * math.sqrt(k_hip), cx_ankle, 0.002 * s, leg_low_vg),
        (0.082 * s * k_leg, 0.032 * s * math.sqrt(k_hip), 0.034 * s * math.sqrt(k_hip), cx_ankle, 0.005 * s, leg_low_vg),
    ]

    leg_rings = []
    leg_sectors = 16
    for z_val, rx, ry, cx, cy, vg in leg_slices:
        ring = []
        for i in range(leg_sectors):
            th = 2.0 * math.pi * i / leg_sectors
            ct, st = math.cos(th), math.sin(th)
            v = bm.verts.new((cx + rx * ct, cy + ry * st, z_val))
            ring.append(v)
            vg_indices[vg].append(v)
        leg_rings.append(ring)

    for r in range(len(leg_rings) - 1):
        for i in range(leg_sectors):
            ni = (i + 1) % leg_sectors
            bm.faces.new((leg_rings[r][i], leg_rings[r + 1][i], leg_rings[r + 1][ni], leg_rings[r][ni]))

    add_bmesh_quad_cap(bm, leg_rings[0], flip=False)
    add_bmesh_quad_cap(bm, leg_rings[-1], flip=True)

    # Foot
    heel_center = (cx_ankle, 0.055 * s, 0.035 * s * k_leg)
    tarsus_verts = add_bmesh_quad_ellipsoid(bm, heel_center, (0.032 * s, 0.045 * s, 0.025 * s * k_leg), rings=3, sectors=8)
    vg_indices[foot_vg].extend(tarsus_verts)

    ball_center = (cx_ankle, -0.065 * s, 0.020 * s * k_leg)
    ball_verts = add_bmesh_quad_ellipsoid(bm, ball_center, (0.038 * s, 0.055 * s, 0.018 * s * k_leg), rings=3, sectors=8)
    vg_indices[foot_vg].extend(ball_verts)

    for t_idx in range(5):
        t_offset_x = (t_idx - 2.0) * (0.015 * s * sign)
        toe_x = cx_ankle + t_offset_x
        toe_y = -0.135 * s - (0.010 * s if t_idx in (0, 1) else 0.0)
        toe_z = 0.012 * s * k_leg
        t_rad = 0.009 * s if t_idx == 0 else 0.007 * s
        toe_verts = add_bmesh_quad_ellipsoid(bm, (toe_x, toe_y, toe_z), (t_rad, 0.018 * s, t_rad * 0.9), rings=3, sectors=8)
        vg_indices[foot_vg].extend(toe_verts)

# ------------------------------------------------------------------------------
# 4. UPPER LIMBS & 10 ARTICULATED FINGERS (LEFT & RIGHT)
# ------------------------------------------------------------------------------
for side, sign in [("L", 1.0), ("R", -1.0)]:
    arm_up_vg = f"arm_upper_{{side}}"
    arm_low_vg = f"arm_lower_{{side}}"
    hand_vg = f"hand_{{side}}"
    fingers_vg = f"fingers_{{side}}"

    arm_slices = [
        (sign * 0.175 * s * k_shoulder, 0.0, 1.340 * s, 0.048 * s, 0.048 * s, arm_up_vg),
        (sign * (0.175 * k_shoulder + 0.035 * k_arm) * s, 0.0, 1.340 * s - 0.090 * s * k_arm, 0.042 * s, 0.042 * s, arm_up_vg),
        (sign * (0.175 * k_shoulder + 0.070 * k_arm) * s, 0.0, 1.340 * s - 0.180 * s * k_arm, 0.038 * s, 0.038 * s, arm_up_vg),
        (sign * (0.175 * k_shoulder + 0.105 * k_arm) * s, 0.0, 1.340 * s - 0.270 * s * k_arm, 0.035 * s, 0.036 * s, arm_low_vg),
        (sign * (0.175 * k_shoulder + 0.135 * k_arm) * s, 0.0, 1.340 * s - 0.360 * s * k_arm, 0.034 * s, 0.034 * s, arm_low_vg),
        (sign * (0.175 * k_shoulder + 0.160 * k_arm) * s, 0.0, 1.340 * s - 0.440 * s * k_arm, 0.028 * s, 0.028 * s, arm_low_vg),
        (sign * (0.175 * k_shoulder + 0.185 * k_arm) * s, 0.0, 1.340 * s - 0.510 * s * k_arm, 0.024 * s, 0.022 * s, arm_low_vg),
    ]

    arm_rings = []
    arm_sectors = 14
    for cx, cy, cz, rx, ry, vg in arm_slices:
        ring = []
        for i in range(arm_sectors):
            th = 2.0 * math.pi * i / arm_sectors
            ct, st = math.cos(th), math.sin(th)
            v = bm.verts.new((cx + rx * ct, cy + ry * st, cz))
            ring.append(v)
            vg_indices[vg].append(v)
        arm_rings.append(ring)

    for r in range(len(arm_rings) - 1):
        for i in range(arm_sectors):
            ni = (i + 1) % arm_sectors
            bm.faces.new((arm_rings[r][i], arm_rings[r + 1][i], arm_rings[r + 1][ni], arm_rings[r][ni]))

    add_bmesh_quad_cap(bm, arm_rings[0], flip=False)
    add_bmesh_quad_cap(bm, arm_rings[-1], flip=True)

    # Palm
    palm_center = (sign * (0.175 * k_shoulder + 0.210 * k_arm) * s, -0.030 * s, 1.340 * s - 0.570 * s * k_arm)
    palm_verts = add_bmesh_quad_ellipsoid(bm, palm_center, (0.028 * s, 0.015 * s, 0.045 * s), rings=4, sectors=8)
    vg_indices[hand_vg].extend(palm_verts)

    finger_configs = [
        ("thumb", 0.022 * sign, -0.015, -0.010, 0.052, 0.0075, 45.0),
        ("index", 0.012 * sign, -0.008, -0.035, 0.068, 0.0068, 15.0),
        ("middle", 0.002 * sign, -0.002, -0.040, 0.074, 0.0070, 5.0),
        ("ring", -0.008 * sign, 0.002, -0.036, 0.066, 0.0065, -8.0),
        ("pinky", -0.018 * sign, 0.006, -0.028, 0.054, 0.0058, -20.0),
    ]

    for f_name, ox, oy, oz, f_len, f_rad, pitch_ang in finger_configs:
        f_base_x = palm_center[0] + ox * s
        f_base_y = palm_center[1] + oy * s
        f_base_z = palm_center[2] + oz * s

        ph_len = (f_len * s * k_arm) / 3.0
        rad_ang = math.radians(pitch_ang)
        dx = math.sin(rad_ang) * 0.15 * sign
        dy = -math.sin(rad_ang) * 0.30
        dz = -math.cos(rad_ang)
        d_len = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
        dx, dy, dz = dx / d_len, dy / d_len, dz / d_len

        for ph_idx in range(3):
            cur_center = (
                f_base_x + dx * ph_len * (ph_idx + 0.5),
                f_base_y + dy * ph_len * (ph_idx + 0.5),
                f_base_z + dz * ph_len * (ph_idx + 0.5),
            )
            cur_rad = f_rad * s * (1.0 - ph_idx * 0.12)
            ph_verts = add_bmesh_quad_ellipsoid(
                bm,
                cur_center,
                (cur_rad, cur_rad, ph_len * 0.55),
                rings=3,
                sectors=6,
            )
            vg_indices[fingers_vg].extend(ph_verts)
            vg_indices[hand_vg].extend(ph_verts)

bm.verts.index_update()
vg_indices_mapped = dict()
for g_name, v_list in vg_indices.items():
    vg_indices_mapped[g_name] = [v.index for v in v_list]
bm.to_mesh(me)
bm.free()

obj = bpy.data.objects.new(mesh_name, me)
bpy.context.scene.collection.objects.link(obj)
bpy.context.view_layer.objects.active = obj
obj.select_set(True)

# Enable Smooth Shading across all polygons
for poly in me.polygons:
    poly.use_smooth = True

# Assign Vertices to All 29 Vertex Groups
for g_name, idx_list in vg_indices_mapped.items():
    vg = obj.vertex_groups.new(name=g_name)
    if idx_list:
        vg.add(idx_list, 1.0, 'REPLACE')

# Add 52 Apple ARKit FACS Blendshapes (Basis + 52 Shape Keys)
basis_key = obj.shape_key_add(name="Basis", from_mix=False)
arkit_52 = [
    "eyeBlinkLeft", "eyeLookDownLeft", "eyeLookInLeft", "eyeLookOutLeft", "eyeLookUpLeft", "eyeSquintLeft", "eyeWideLeft",
    "eyeBlinkRight", "eyeLookDownRight", "eyeLookInRight", "eyeLookOutRight", "eyeLookUpRight", "eyeSquintRight", "eyeWideRight",
    "jawForward", "jawLeft", "jawRight", "jawOpen",
    "mouthClose", "mouthFunnel", "mouthPucker", "mouthLeft", "mouthRight",
    "mouthSmileLeft", "mouthSmileRight", "mouthFrownLeft", "mouthFrownRight",
    "mouthDimpleLeft", "mouthDimpleRight", "mouthStretchLeft", "mouthStretchRight",
    "mouthRollLower", "mouthRollUpper", "mouthShrugLower", "mouthShrugUpper",
    "mouthPressLeft", "mouthPressRight", "mouthLowerDownLeft", "mouthLowerDownRight",
    "mouthUpperUpLeft", "mouthUpperUpRight",
    "browDownLeft", "browDownRight", "browInnerUp", "browOuterUpLeft", "browOuterUpRight",
    "cheekPuff", "cheekSquintLeft", "cheekSquintRight",
    "noseSneerLeft", "noseSneerRight",
    "tongueOut"
]
for k_name in arkit_52:
    obj.shape_key_add(name=k_name, from_mix=False)

# Store Rigify Landmarks as Custom Property
landmarks_dict = {{
    "head_top": [0.0, 0.005 * s, z_crown],
    "chin": [0.0, -0.065 * s * k_head_scale, z_chin],
    "neck": [0.0, 0.015 * s, z_chin - 0.037 * s],
    "clavicle_L": [0.045 * s * k_shoulder, -0.015 * s, z_clavicle],
    "clavicle_R": [-0.045 * s * k_shoulder, -0.015 * s, z_clavicle],
    "shoulder_L": [0.175 * s * k_shoulder, -0.020 * s, 1.340 * s],
    "shoulder_R": [-0.175 * s * k_shoulder, -0.020 * s, 1.340 * s],
    "elbow_L": [(0.175 * k_shoulder + 0.105 * k_arm) * s, 0.015 * s, 1.340 * s - 0.270 * s * k_arm],
    "elbow_R": [-(0.175 * k_shoulder + 0.105 * k_arm) * s, 0.015 * s, 1.340 * s - 0.270 * s * k_arm],
    "wrist_L": [(0.175 * k_shoulder + 0.185 * k_arm) * s, -0.020 * s, 1.340 * s - 0.510 * s * k_arm],
    "wrist_R": [-(0.175 * k_shoulder + 0.185 * k_arm) * s, -0.020 * s, 1.340 * s - 0.510 * s * k_arm],
    "fingers_L": [(0.175 * k_shoulder + 0.245 * k_arm) * s, -0.040 * s, 1.340 * s - 0.660 * s * k_arm],
    "fingers_R": [-(0.175 * k_shoulder + 0.245 * k_arm) * s, -0.040 * s, 1.340 * s - 0.660 * s * k_arm],
    "spine_chest": [0.0, -0.005 * s, z_crotch + 0.81 * (z_clavicle - z_crotch)],
    "spine_waist": [0.0, -0.010 * s, z_crotch + 0.43 * (z_clavicle - z_crotch)],
    "spine_pelvis": [0.0, 0.000 * s, z_crotch],
    "hip_L": [0.095 * s * k_hip, -0.010 * s, z_crotch],
    "hip_R": [-0.095 * s * k_hip, -0.010 * s, z_crotch],
    "knee_L": [0.100 * s * k_hip, -0.020 * s, 0.445 * s * k_leg],
    "knee_R": [-0.100 * s * k_hip, -0.020 * s, 0.445 * s * k_leg],
    "ankle_L": [0.090 * s * k_hip, 0.005 * s, 0.082 * s * k_leg],
    "ankle_R": [-0.090 * s * k_hip, 0.005 * s, 0.082 * s * k_leg],
    "toe_L": [0.090 * s * k_hip, -0.145 * s, 0.025 * s * k_leg],
    "toe_R": [-0.090 * s * k_hip, -0.145 * s, 0.025 * s * k_leg],
}}
obj["morphomesh_landmarks"] = landmarks_dict
"""


__all__ = [
    "get_human_generation_script",
]
