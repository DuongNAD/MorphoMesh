"""
anime_pipeline/rigging/secondary_bones.py
Milestone 2 Features F07 & F08:
- F07: 12-Radial Skirt Secondary Rig (Skirt_01 to Skirt_12) with [-15°, +65°] pitch limits.
- CRITICAL INVARIANT: 0% Thigh Weight Bleeding on Anime_Skirt (strict azimuthal cubic Hermite weighting).
- F08: Dual 5-Bone Twintail Secondary Chains (Hair_L_01..05 & Hair_R_01..05) with calibrated spring dynamics.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

try:
    import bpy
    import mathutils
    HAS_BPY = True
except ImportError:
    bpy = None  # type: ignore[assignment]
    mathutils = None  # type: ignore[assignment]
    HAS_BPY = False


# ==============================================================================
# 1. Authoritative Constants
# ==============================================================================

SKIRT_BONE_COUNT: int = 12
SKIRT_BONE_NAMES: List[str] = [f"Skirt_{i:02d}" for i in range(1, 13)]
SKIRT_PITCH_MIN_DEG: float = -15.0
SKIRT_PITCH_MAX_DEG: float = 65.0

TWINTAIL_SEGMENT_COUNT: int = 5
HAIR_BONES_LEFT: List[str] = [f"Hair_L_{i:02d}" for i in range(1, 6)]
HAIR_BONES_RIGHT: List[str] = [f"Hair_R_{i:02d}" for i in range(1, 6)]
ALL_10_HAIR_BONES: List[str] = HAIR_BONES_LEFT + HAIR_BONES_RIGHT

# Calibrated Physical Spring-Damper Parameters (m, k, c)
SPRING_MASS: float = 0.20        # kg
SPRING_STIFFNESS: float = 150.0  # N/m
SPRING_DAMPING: float = 12.0     # N*s/m
SPRING_REST_POS: float = 0.0     # neutral rest angle/displacement


# ==============================================================================
# 2. Mathematical Utility Solvers
# ==============================================================================

def evaluate_cubic_bezier_3d(
    p0: Tuple[float, float, float],
    p1: Tuple[float, float, float],
    p2: Tuple[float, float, float],
    p3: Tuple[float, float, float],
    t: float,
) -> Tuple[float, float, float]:
    """Evaluates 3D cubic Bézier curve at parameter t in [0, 1]."""
    t = max(0.0, min(1.0, t))
    u = 1.0 - t
    b0 = u ** 3
    b1 = 3.0 * (u ** 2) * t
    b2 = 3.0 * u * (t ** 2)
    b3 = t ** 3
    x = b0 * p0[0] + b1 * p1[0] + b2 * p2[0] + b3 * p3[0]
    y = b0 * p0[1] + b1 * p1[1] + b2 * p2[1] + b3 * p3[1]
    z = b0 * p0[2] + b1 * p1[2] + b2 * p2[2] + b3 * p3[2]
    return (round(x, 6), round(y, 6), round(z, 6))


def clamp_skirt_pitch(pitch_deg: float) -> float:
    """Clamps skirt pitch strictly within [-15°, +65°]."""
    return max(SKIRT_PITCH_MIN_DEG, min(SKIRT_PITCH_MAX_DEG, pitch_deg))


# ==============================================================================
# 3. 12-Radial Skirt Rig Generator
# ==============================================================================

def add_skirt_radial_rig(
    armature_obj: Any,
    skirt_mesh_obj: Optional[Any] = None,
    landmarks: Optional[Dict[str, Tuple[float, float, float]]] = None,
    scale: float = 1.0,
) -> List[str]:
    """
    Builds 12 radial spoke bones (Skirt_01 to Skirt_12) in an ellipse around Hips.
    Applies LIMIT_ROTATION constraint to each skirt bone clamping local pitch to [-15°, +65°].
    """
    if not HAS_BPY:
        return list(SKIRT_BONE_NAMES)

    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode='EDIT')
    eb = armature_obj.data.edit_bones

    hips_bone = eb.get("Hips") or eb.get("DEF-spine")
    if not hips_bone:
        raise RuntimeError("Parent bone 'Hips' not found in armature")
    hips_name = hips_bone.name

    xc = 0.0
    yc = -0.016 * scale
    waist_z = 0.880 * scale
    hem_z = 0.540 * scale
    rx_head = 0.180 * scale
    ry_head = 0.140 * scale
    rx_tail = 0.290 * scale
    ry_tail = 0.230 * scale

    if skirt_mesh_obj and hasattr(skirt_mesh_obj.data, 'vertices'):
        verts = skirt_mesh_obj.data.vertices
        if verts:
            zs = [v.co.z for v in verts]
            waist_z = max(zs)
            hem_z = min(zs)
            waist_verts = [v for v in verts if v.co.z >= waist_z - 0.03 * scale]
            if waist_verts:
                rx_head = max(abs(v.co.x) for v in waist_verts) * 0.95
                ry_head = (max(v.co.y for v in waist_verts) - min(v.co.y for v in waist_verts)) * 0.5 * 0.95
                yc = sum(v.co.y for v in waist_verts) / len(waist_verts)
            hem_verts = [v for v in verts if v.co.z <= hem_z + 0.03 * scale]
            if hem_verts:
                rx_tail = max(abs(v.co.x) for v in hem_verts) * 0.98
                ry_tail = (max(v.co.y for v in hem_verts) - min(v.co.y for v in hem_verts)) * 0.5 * 0.98

    created_bones: List[str] = []

    for i in range(1, SKIRT_BONE_COUNT + 1):
        bname = f"Skirt_{i:02d}"
        ang = (i - 1) * (2.0 * math.pi / SKIRT_BONE_COUNT)

        hx = xc + rx_head * math.cos(ang)
        hy = yc + ry_head * math.sin(ang)
        hz = waist_z

        tx = xc + rx_tail * math.cos(ang)
        ty = yc + ry_tail * math.sin(ang)
        tz = hem_z

        if bname in eb:
            eb.remove(eb[bname])

        b = eb.new(bname)
        b.head = mathutils.Vector((hx, hy, hz))
        b.tail = mathutils.Vector((tx, ty, tz))
        b.parent = eb[hips_name]
        b.use_connect = False
        b.use_deform = True

        tangent = mathutils.Vector((-math.sin(ang), math.cos(ang), 0.0))
        b.align_roll(tangent)
        created_bones.append(bname)

    bpy.ops.object.mode_set(mode='POSE')
    pb = armature_obj.pose.bones

    for bname in created_bones:
        p_bone = pb.get(bname)
        if not p_bone:
            continue

        for c in list(p_bone.constraints):
            if c.type == 'LIMIT_ROTATION':
                p_bone.constraints.remove(c)

        c = p_bone.constraints.new(type='LIMIT_ROTATION')
        c.name = "Skirt_Pitch_Clamp"
        c.owner_space = 'LOCAL'
        c.use_limit_x = True
        c.min_x = math.radians(SKIRT_PITCH_MIN_DEG)
        c.max_x = math.radians(SKIRT_PITCH_MAX_DEG)
        c.use_limit_y = False
        c.use_limit_z = False
        c.influence = 1.0

        p_bone["min_pitch"] = SKIRT_PITCH_MIN_DEG
        p_bone["max_pitch"] = SKIRT_PITCH_MAX_DEG
        p_bone["is_secondary_skirt"] = True

    bpy.ops.object.mode_set(mode='OBJECT')
    return created_bones


# ==============================================================================
# 4. Critical Invariant: 0% Thigh Weight Bleeding Skinning
# ==============================================================================

def apply_skirt_skin_weights(
    skirt_mesh_obj: Any,
    armature_obj: Any,
    scale: float = 1.0,
) -> None:
    """
    Applies the exclusive radial skinning algorithm to Anime_Skirt:
    - Guaranteed 0% thigh weight transfer (w(Thigh.L) == 0, w(Thigh.R) == 0).
    - Removes all non-skirt vertex groups (Thigh, Shin, Foot, Toe, etc.).
    - Vertices weighted strictly to Skirt_01..12 using smooth azimuthal Hermite interpolation.
    - Sum of weights for every vertex == 1.000000.
    """
    if not HAS_BPY or not skirt_mesh_obj:
        return

    bpy.context.view_layer.objects.active = skirt_mesh_obj

    # 1. PURGE PROHIBITED VERTEX GROUPS (Zero Thigh Bleeding Invariant)
    # The skirt is solely driven by Skirt_01..12 radial bones
    for vg in list(skirt_mesh_obj.vertex_groups):
        if not vg.name.startswith("Skirt_"):
            skirt_mesh_obj.vertex_groups.remove(vg)

    # 2. Ensure Skirt_01..12 groups exist
    skirt_vgs: Dict[str, Any] = {}
    for bname in SKIRT_BONE_NAMES:
        vg = skirt_mesh_obj.vertex_groups.get(bname)
        if not vg:
            vg = skirt_mesh_obj.vertex_groups.new(name=bname)
        skirt_vgs[bname] = vg

    verts = skirt_mesh_obj.data.vertices
    if not verts:
        return

    xc = sum(v.co.x for v in verts) / len(verts)
    yc = sum(v.co.y for v in verts) / len(verts)
    sector = 2.0 * math.pi / SKIRT_BONE_COUNT

    # Clear old weights for clean slate
    for vg in skirt_vgs.values():
        for v in verts:
            vg.remove([v.index])

    for v in verts:
        x, y = v.co.x, v.co.y
        phi = math.atan2(y - yc, x - xc)
        if phi < 0.0:
            phi += 2.0 * math.pi

        k0 = int(phi // sector) % SKIRT_BONE_COUNT
        k1 = (k0 + 1) % SKIRT_BONE_COUNT

        t = (phi - (k0 * sector)) / sector
        t = max(0.0, min(1.0, t))

        # Smooth cubic Hermite interpolation
        w1 = 3.0 * (t ** 2) - 2.0 * (t ** 3)
        w0 = 1.0 - w1

        b0_name = f"Skirt_{k0+1:02d}"
        b1_name = f"Skirt_{k1+1:02d}"

        skirt_vgs[b0_name].add([v.index], round(w0, 6), 'REPLACE')
        skirt_vgs[b1_name].add([v.index], round(w1, 6), 'REPLACE')

    # Strict Invariant Validations
    assert "Thigh.L" not in skirt_mesh_obj.vertex_groups, "CRITICAL ERROR: Thigh.L weight group leaked to Anime_Skirt!"
    assert "Thigh.R" not in skirt_mesh_obj.vertex_groups, "CRITICAL ERROR: Thigh.R weight group leaked to Anime_Skirt!"

    for v in skirt_mesh_obj.data.vertices:
        tot_w = sum(g.weight for g in v.groups)
        assert abs(tot_w - 1.0) < 1e-4, f"CRITICAL ERROR: Vertex {v.index} weight sum {tot_w} != 1.0"


# ==============================================================================
# 5. 5-Bone Twintail Secondary Chains Generator
# ==============================================================================

def add_twintail_secondary_chains(
    armature_obj: Any,
    hair_mesh_obj: Optional[Any] = None,
    landmarks: Optional[Dict[str, Tuple[float, float, float]]] = None,
    scale: float = 1.0,
) -> Dict[str, List[str]]:
    """
    Builds dual 5-bone twintail chains (Hair_L_01..05 & Hair_R_01..05) parented to Head.
    Attaches spring dynamics properties (mass, stiffness, damping) to each pose bone.
    """
    if not HAS_BPY:
        return {"L": list(HAIR_BONES_LEFT), "R": list(HAIR_BONES_RIGHT)}

    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode='EDIT')
    eb = armature_obj.data.edit_bones

    head_bone = eb.get("Head") or eb.get("DEF-head")
    if not head_bone:
        raise RuntimeError("Parent bone 'Head' not found in armature")
    head_name = head_bone.name

    created_chains: Dict[str, List[str]] = {"L": [], "R": []}

    for side_code, side_sign in [("L", 1.0), ("R", -1.0)]:
        p0 = (0.088 * side_sign * scale, -0.020 * scale, 1.530 * scale)
        p1 = (0.160 * side_sign * scale, -0.040 * scale, 1.480 * scale)
        p2 = (0.175 * side_sign * scale, -0.050 * scale, 1.320 * scale)
        p3 = (0.150 * side_sign * scale, -0.030 * scale, 1.150 * scale)

        parent_bone_name = head_name

        for j in range(1, TWINTAIL_SEGMENT_COUNT + 1):
            bname = f"Hair_{side_code}_{j:02d}"
            t0 = (j - 1) / float(TWINTAIL_SEGMENT_COUNT)
            t1 = j / float(TWINTAIL_SEGMENT_COUNT)

            head_pos = evaluate_cubic_bezier_3d(p0, p1, p2, p3, t0)
            tail_pos = evaluate_cubic_bezier_3d(p0, p1, p2, p3, t1)

            if bname in eb:
                eb.remove(eb[bname])

            b = eb.new(bname)
            b.head = mathutils.Vector(head_pos)
            b.tail = mathutils.Vector(tail_pos)
            b.parent = eb[parent_bone_name]
            b.use_connect = (j > 1)
            b.use_deform = True

            outward_vec = mathutils.Vector((side_sign, 0.0, 0.0))
            b.align_roll(outward_vec)

            parent_bone_name = bname
            created_chains[side_code].append(bname)

    bpy.ops.object.mode_set(mode='POSE')
    pb = armature_obj.pose.bones

    all_hair_bones = created_chains["L"] + created_chains["R"]
    for bname in all_hair_bones:
        p_bone = pb.get(bname)
        if not p_bone:
            continue

        p_bone["spring_stiffness"] = SPRING_STIFFNESS
        p_bone["spring_damping"] = SPRING_DAMPING
        p_bone["spring_mass"] = SPRING_MASS
        p_bone["spring_rest_pos"] = SPRING_REST_POS
        p_bone["is_secondary_hair"] = True

    bpy.ops.object.mode_set(mode='OBJECT')
    return created_chains


# ==============================================================================
# 6. Hair Mesh Skin Weighting
# ==============================================================================

def apply_hair_skin_weights(
    hair_mesh_obj: Any,
    armature_obj: Any,
) -> None:
    """
    Skins Anime_Hair:
    - Scalp vertices (indices 0..143) weighted 100% to Head.
    - Left Twintail (indices 144..233) weighted smoothly to Hair_L_01..05.
    - Right Twintail (indices 234..323) weighted smoothly to Hair_R_01..05.
    """
    if not HAS_BPY or not hair_mesh_obj:
        return

    bpy.context.view_layer.objects.active = hair_mesh_obj
    verts = hair_mesh_obj.data.vertices
    if not verts:
        return

    required_groups = ["Head"] + ALL_10_HAIR_BONES
    vgs: Dict[str, Any] = {}
    for gname in required_groups:
        vg = hair_mesh_obj.vertex_groups.get(gname)
        if not vg:
            vg = hair_mesh_obj.vertex_groups.new(name=gname)
        vgs[gname] = vg

    for vg in vgs.values():
        for v in verts:
            vg.remove([v.index])

    total_v = len(verts)

    if total_v >= 324:
        # Standard M1 topology: 144 cranial scalp + 90 left twintail + 90 right twintail
        for idx in range(144):
            vgs["Head"].add([idx], 1.0, 'REPLACE')

        # Left Twintail (144..233): 15 rings x 6 angular steps
        for ring in range(15):
            t_seg = (ring / 14.0) * 4.0
            seg_idx = min(3, int(t_seg))
            frac = t_seg - seg_idx
            w_next = 3.0 * (frac ** 2) - 2.0 * (frac ** 3)
            w_curr = 1.0 - w_next

            b_curr = f"Hair_L_{seg_idx + 1:02d}"
            b_next = f"Hair_L_{seg_idx + 2:02d}"

            for step in range(6):
                v_idx = 144 + ring * 6 + step
                vgs[b_curr].add([v_idx], round(w_curr, 6), 'REPLACE')
                vgs[b_next].add([v_idx], round(w_next, 6), 'REPLACE')

        # Right Twintail (234..323): 15 rings x 6 angular steps
        for ring in range(15):
            t_seg = (ring / 14.0) * 4.0
            seg_idx = min(3, int(t_seg))
            frac = t_seg - seg_idx
            w_next = 3.0 * (frac ** 2) - 2.0 * (frac ** 3)
            w_curr = 1.0 - w_next

            b_curr = f"Hair_R_{seg_idx + 1:02d}"
            b_next = f"Hair_R_{seg_idx + 2:02d}"

            for step in range(6):
                v_idx = 234 + ring * 6 + step
                vgs[b_curr].add([v_idx], round(w_curr, 6), 'REPLACE')
                vgs[b_next].add([v_idx], round(w_next, 6), 'REPLACE')
    else:
        # Fallback spatial clustering if non-standard vertex ordering
        for v in verts:
            if abs(v.co.x) < 0.09:
                vgs["Head"].add([v.index], 1.0, 'REPLACE')
            else:
                side = "L" if v.co.x > 0 else "R"
                seg = min(5, max(1, int((1.55 - v.co.z) / 0.08) + 1))
                vgs[f"Hair_{side}_{seg:02d}"].add([v.index], 1.0, 'REPLACE')

    for v in verts:
        tot_w = sum(g.weight for g in v.groups)
        assert abs(tot_w - 1.0) < 1e-4, f"Anime_Hair vertex {v.index} unnormalized weight {tot_w}"


# ==============================================================================
# 7. SecondaryBonesRig Class Orchestrator
# ==============================================================================

class SecondaryBonesRig:
    """
    Orchestrates secondary bone creation and weighting for skirt and hair.
    """

    def __init__(self, scale: float = 1.0):
        self.scale = scale

    def setup_secondary_rig_and_skinning(
        self,
        armature_obj: Any,
        submesh_objs: Dict[str, Any],
        landmarks: Optional[Dict[str, Tuple[float, float, float]]] = None,
    ) -> Dict[str, Any]:
        """
        Builds secondary skirt and hair bones, and applies skin weighting.
        """
        skirt_obj = submesh_objs.get("Anime_Skirt")
        hair_obj = submesh_objs.get("Anime_Hair")

        skirt_bones = add_skirt_radial_rig(
            armature_obj=armature_obj,
            skirt_mesh_obj=skirt_obj,
            landmarks=landmarks,
            scale=self.scale,
        )

        twintail_chains = add_twintail_secondary_chains(
            armature_obj=armature_obj,
            hair_mesh_obj=hair_obj,
            landmarks=landmarks,
            scale=self.scale,
        )

        if skirt_obj:
            apply_skirt_skin_weights(skirt_obj, armature_obj, scale=self.scale)

        if hair_obj:
            apply_hair_skin_weights(hair_obj, armature_obj)

        return {
            "skirt_bones": skirt_bones,
            "twintail_chains": twintail_chains,
            "skirt_skinned": skirt_obj is not None,
            "hair_skinned": hair_obj is not None,
        }
