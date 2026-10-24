"""
anime_pipeline/rigging/skinning_dqs.py
Milestone 2 Features F06, F09, F10:
- F06: Forearm and UpperArm Twist Bones (COPY_ROTATION 0.5 local Y anti-pinch constraints).
- F09: Dual Quaternion Skinning Integration (use_deform_preserve_volume = True).
- F10: Smooth Weight Paint Transfer with C1 harmonic cosine falloff and modular isolation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import bpy
    import mathutils
    HAS_BPY = True
except ImportError:
    bpy = None  # type: ignore[assignment]
    mathutils = None  # type: ignore[assignment]
    HAS_BPY = False


# ==============================================================================
# 1. Authoritative Constants & Modular Isolation Rules
# ==============================================================================

TWIST_BONES: List[str] = [
    "UpperArm_Twist.L", "UpperArm_Twist.R",
    "ForeArm_Twist.L", "ForeArm_Twist.R",
]

FINGER_NAMES: List[str] = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
PHALANGES: List[str] = ["01", "02", "03"]

ALL_30_FINGER_BONES: List[str] = [
    f"{f}.{p}.{side}" for side in ["L", "R"] for f in FINGER_NAMES for p in PHALANGES
]

SKIRT_BONES: List[str] = [f"Skirt_{i:02d}" for i in range(1, 13)]
ALL_10_HAIR_BONES: List[str] = [f"Hair_L_{i:02d}" for i in range(1, 6)] + [f"Hair_R_{i:02d}" for i in range(1, 6)]

# Strict Modular Vertex Group Isolation Matrix (Feature F10)
# Guarantees zero cross-mesh weight bleeding across air gaps.
# CRITICAL: Anime_Skirt has strictly NO Thigh.L or Thigh.R weights!
MODULAR_ISOLATION_RULES: Dict[str, Set[str]] = {
    "Anime_Head": {
        "Head", "Neck",
    },
    "Anime_Torso": {
        "Hips", "Spine", "Spine1", "Spine2", "Neck",
        "Clavicle.L", "Clavicle.R",
    },
    "Anime_Arms": {
        "Clavicle.L", "Clavicle.R",
        "UpperArm.L", "UpperArm.R",
        "UpperArm_Twist.L", "UpperArm_Twist.R",
        "ForeArm.L", "ForeArm.R",
        "ForeArm_Twist.L", "ForeArm_Twist.R",
        "Hand.L", "Hand.R",
    } | set(ALL_30_FINGER_BONES),
    "Anime_Legs": {
        "Hips",
        "Thigh.L", "Thigh.R",
        "Shin.L", "Shin.R",
        "Foot.L", "Foot.R",
        "Toe.L", "Toe.R",
    },
    "Anime_Skirt": set(SKIRT_BONES),
    "Anime_Hair": {
        "Head",
    } | set(ALL_10_HAIR_BONES),
    "Anime_Shoes": {
        "Shin.L", "Shin.R",
        "Foot.L", "Foot.R",
        "Toe.L", "Toe.R",
    },
}

TWIST_BONE_CONFIGS: Dict[str, Dict[str, Any]] = {
    "ForeArm_Twist.L": {"target_bone": "Hand.L", "axis": "Y", "factor": 0.50, "parent": "ForeArm.L"},
    "ForeArm_Twist.R": {"target_bone": "Hand.R", "axis": "Y", "factor": 0.50, "parent": "ForeArm.R"},
    "UpperArm_Twist.L": {"target_bone": "ForeArm.L", "axis": "Y", "factor": 0.50, "parent": "UpperArm.L"},
    "UpperArm_Twist.R": {"target_bone": "ForeArm.R", "axis": "Y", "factor": 0.50, "parent": "UpperArm.R"},
}


# ==============================================================================
# 2. Mathematical Utility Solvers
# ==============================================================================

def point_to_segment_distance_and_proj(
    p: Tuple[float, float, float],
    a: Tuple[float, float, float],
    b: Tuple[float, float, float],
) -> Tuple[float, float, Tuple[float, float, float]]:
    """
    Computes:
    1. Distance from point p to line segment a-b.
    2. Normalized longitudinal projection parameter t in [0.0, 1.0].
    3. Projected 3D point on the line segment.
    """
    ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    l2 = ab[0] ** 2 + ab[1] ** 2 + ab[2] ** 2
    if l2 < 1e-12:
        dist = math.sqrt((p[0] - a[0]) ** 2 + (p[1] - a[1]) ** 2 + (p[2] - a[2]) ** 2)
        return dist, 0.0, a

    ap = (p[0] - a[0], p[1] - a[1], p[2] - a[2])
    dot = ap[0] * ab[0] + ap[1] * ab[1] + ap[2] * ab[2]
    t = max(0.0, min(1.0, dot / l2))
    proj = (a[0] + t * ab[0], a[1] + t * ab[1], a[2] + t * ab[2])
    dist = math.sqrt((p[0] - proj[0]) ** 2 + (p[1] - proj[1]) ** 2 + (p[2] - proj[2]) ** 2)
    return dist, t, proj


def harmonic_cosine_falloff(u: float) -> float:
    """
    C1-continuous harmonic cosine falloff: f(u) = 0.5 * (1 + cos(pi * u)).
    Guarantees zero first-derivative at u=0 and u=1, eliminating skin creases.
    """
    u_clamped = max(0.0, min(1.0, u))
    return 0.5 * (1.0 + math.cos(math.pi * u_clamped))


# ==============================================================================
# 3. Feature F06: Twist Bone Constraints Setup
# ==============================================================================

def setup_twist_bone_constraints(armature_obj: Any) -> Dict[str, Dict[str, Any]]:
    """
    Configures COPY_ROTATION constraints on ForeArm_Twist.[L/R] and UpperArm_Twist.[L/R].
    - Target: Hand.[L/R] (for forearm twist) or ForeArm.[L/R] (for upperarm twist)
    - Space: target_space='LOCAL', owner_space='LOCAL'
    - Axis: Local Y (longitudinal roll) only
    - Influence: 0.50
    """
    results: Dict[str, Dict[str, Any]] = {}

    if not HAS_BPY or armature_obj is None or not hasattr(armature_obj, "pose"):
        for twist_name, cfg in TWIST_BONE_CONFIGS.items():
            results[twist_name] = {
                "type": "COPY_ROTATION",
                "target": cfg["target_bone"],
                "axis": cfg["axis"],
                "factor": cfg["factor"],
                "target_space": "LOCAL",
                "owner_space": "LOCAL",
            }
        return results

    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode='POSE')
    pose_bones = armature_obj.pose.bones

    for twist_name, cfg in TWIST_BONE_CONFIGS.items():
        pb = pose_bones.get(twist_name)
        if not pb:
            continue

        for c in list(pb.constraints):
            if c.type == 'COPY_ROTATION' and "Twist" in c.name:
                pb.constraints.remove(c)

        crc = pb.constraints.new(type='COPY_ROTATION')
        crc.name = f"{twist_name}_AntiPinch_Y"
        crc.target = armature_obj
        crc.subtarget = cfg["target_bone"]
        crc.target_space = 'LOCAL'
        crc.owner_space = 'LOCAL'
        crc.use_x = False
        crc.use_y = True
        crc.use_z = False
        crc.influence = cfg["factor"]
        crc.mix_mode = 'REPLACE'

        results[twist_name] = {
            "type": "COPY_ROTATION",
            "target": cfg["target_bone"],
            "axis": "Y",
            "factor": cfg["factor"],
            "target_space": "LOCAL",
            "owner_space": "LOCAL",
        }

    bpy.ops.object.mode_set(mode='OBJECT')
    return results


# ==============================================================================
# 4. Feature F09: Dual Quaternion Skinning (DQS) Setup
# ==============================================================================

def apply_dual_quaternion_skinning(mesh_obj: Any, armature_obj: Any) -> Any:
    """
    Applies the Armature modifier with Dual Quaternion Skinning enabled:
    use_deform_preserve_volume = True.
    Eliminates joint volume loss and candy-wrapper collapse.
    """
    if not HAS_BPY or mesh_obj is None:
        return None

    arm_mod = None
    for m in mesh_obj.modifiers:
        if m.type == 'ARMATURE':
            arm_mod = m
            break

    if not arm_mod:
        arm_mod = mesh_obj.modifiers.new(name="Armature", type='ARMATURE')

    arm_mod.object = armature_obj
    arm_mod.use_deform_preserve_volume = True
    arm_mod.use_vertex_groups = True
    return arm_mod


def configure_all_submeshes_dqs(mesh_objects: List[Any], armature_obj: Any) -> int:
    """Activates DQS preserve volume across all modular sub-meshes."""
    count = 0
    for obj in mesh_objects:
        if obj and (not hasattr(obj, "type") or obj.type == 'MESH'):
            apply_dual_quaternion_skinning(obj, armature_obj)
            count += 1
    return count


# ==============================================================================
# 5. Feature F10: Smooth Weight Paint Transfer & Normalization
# ==============================================================================

@dataclass
class VertexWeightTable:
    """Manages normalized vertex skin weights with modular bone isolation."""
    mesh_name: str
    num_vertices: int
    weights: Dict[int, Dict[str, float]] = field(default_factory=dict)

    def add_weight(self, v_idx: int, bone: str, w: float) -> None:
        if w <= 1e-6:
            return
        if v_idx not in self.weights:
            self.weights[v_idx] = {}
        self.weights[v_idx][bone] = self.weights[v_idx].get(bone, 0.0) + w

    def prune_and_normalize(self, default_bone: str = "Hips", max_influences: int = 4) -> None:
        """
        Enforces:
        1. Modular isolation filtering (prohibits non-allowed bones).
        2. Top-4 influence pruning for game engine / VRM compatibility.
        3. Strict partition of unity: sum of weights == 1.000000.
        """
        allowed = MODULAR_ISOLATION_RULES.get(self.mesh_name, set())

        for v_idx in range(self.num_vertices):
            v_dict = self.weights.get(v_idx, {})

            if allowed:
                v_dict = {b: w for b, w in v_dict.items() if b in allowed}

            if len(v_dict) > max_influences:
                sorted_items = sorted(v_dict.items(), key=lambda item: item[1], reverse=True)[:max_influences]
                v_dict = dict(sorted_items)

            total_w = sum(v_dict.values())
            if total_w > 1e-9:
                self.weights[v_idx] = {b: (w / total_w) for b, w in v_dict.items()}
            else:
                fallback = default_bone if (not allowed or default_bone in allowed) else next(iter(allowed))
                self.weights[v_idx] = {fallback: 1.0}

    def to_vertex_groups_dict(self) -> Dict[str, List[Tuple[int, float]]]:
        """Converts to bone -> [(vertex_idx, weight)] mapping."""
        vgroups: Dict[str, List[Tuple[int, float]]] = {}
        for v_idx, b_dict in self.weights.items():
            for bone, w in b_dict.items():
                if bone not in vgroups:
                    vgroups[bone] = []
                vgroups[bone].append((v_idx, round(w, 6)))
        return vgroups


def calculate_submesh_skin_weights(
    mesh_name: str,
    vertices: List[Tuple[float, float, float]],
    landmarks: Optional[Dict[str, Any]] = None,
) -> Dict[str, List[Tuple[int, float]]]:
    """
    Computes smooth, anti-pinched vertex weights for a modular sub-mesh component.
    Applies C1 harmonic cosine falloff, twist bone gradients, and modular isolation.
    """
    num_verts = len(vertices)
    table = VertexWeightTable(mesh_name=mesh_name, num_vertices=num_verts)

    # 1. Anime_Head
    if mesh_name == "Anime_Head":
        for i, (x, y, z) in enumerate(vertices):
            if z >= 1.43:
                table.add_weight(i, "Head", 1.0)
            elif z <= 1.40:
                table.add_weight(i, "Neck", 1.0)
            else:
                u = (z - 1.40) / 0.03
                w_head = 1.0 - harmonic_cosine_falloff(u)
                table.add_weight(i, "Head", w_head)
                table.add_weight(i, "Neck", 1.0 - w_head)

    # 2. Anime_Torso
    elif mesh_name == "Anime_Torso":
        for i, (x, y, z) in enumerate(vertices):
            side = "L" if x > 0.0 else "R"
            abs_x = abs(x)

            if z >= 1.35:
                if abs_x > 0.10:
                    table.add_weight(i, f"Clavicle.{side}", 0.7)
                    table.add_weight(i, "Neck", 0.3)
                else:
                    table.add_weight(i, "Neck", 1.0)
            elif z >= 1.18:
                u = (z - 1.18) / (1.35 - 1.18)
                w_top = 1.0 - harmonic_cosine_falloff(u)
                w_spine2 = 1.0 - w_top
                if abs_x > 0.11:
                    table.add_weight(i, f"Clavicle.{side}", w_top * 0.7)
                    table.add_weight(i, "Neck", w_top * 0.3)
                else:
                    table.add_weight(i, "Neck", w_top)
                table.add_weight(i, "Spine2", w_spine2)
            elif z >= 1.02:
                u = (z - 1.02) / (1.18 - 1.02)
                w_s2 = 1.0 - harmonic_cosine_falloff(u)
                table.add_weight(i, "Spine2", w_s2)
                table.add_weight(i, "Spine1", 1.0 - w_s2)
            elif z >= 0.88:
                u = (z - 0.88) / (1.02 - 0.88)
                w_s1 = 1.0 - harmonic_cosine_falloff(u)
                table.add_weight(i, "Spine1", w_s1)
                table.add_weight(i, "Spine", 1.0 - w_s1)
            elif z >= 0.80:
                u = (z - 0.80) / (0.88 - 0.80)
                w_sp = 1.0 - harmonic_cosine_falloff(u)
                table.add_weight(i, "Spine", w_sp)
                table.add_weight(i, "Hips", 1.0 - w_sp)
            else:
                table.add_weight(i, "Hips", 1.0)

    # 3. Anime_Arms (Bilateral: Left x > 0, Right x < 0)
    elif mesh_name == "Anime_Arms":
        for i, (x, y, z) in enumerate(vertices):
            side = "L" if x > 0.0 else "R"
            abs_x = abs(x)

            # Hand & Fingers (x > 0.40 or y < -0.19)
            if abs_x > 0.38 and y < -0.18:
                # Finger assignment based on Y coordinate
                # Thumb: y > -0.23, Index: -0.27 to -0.23, Middle: -0.29 to -0.27, Ring: -0.31 to -0.29, Pinky: < -0.31
                if y > -0.225:
                    f_name = "Thumb"
                    f_ph = "01" if y > -0.21 else ("02" if y > -0.25 else "03")
                elif y > -0.265:
                    f_name = "Index"
                    f_ph = "01" if z > 1.00 else ("02" if z > 0.98 else "03")
                elif y > -0.285:
                    f_name = "Middle"
                    f_ph = "01" if z > 0.98 else ("02" if z > 0.96 else "03")
                elif y > -0.305:
                    f_name = "Ring"
                    f_ph = "01" if z > 0.97 else ("02" if z > 0.95 else "03")
                else:
                    f_name = "Pinky"
                    f_ph = "01" if z > 0.96 else ("02" if z > 0.95 else "03")

                table.add_weight(i, f"{f_name}.{f_ph}.{side}", 0.85)
                table.add_weight(i, f"Hand.{side}", 0.15)

            # Wrist transition (abs_x ~ 0.35 to 0.43, y ~ -0.12 to -0.19)
            elif y < -0.13:
                u_wr = (-0.13 - y) / 0.05
                w_hd = 1.0 - harmonic_cosine_falloff(u_wr)
                table.add_weight(i, f"Hand.{side}", w_hd)
                table.add_weight(i, f"ForeArm_Twist.{side}", 1.0 - w_hd)

            # ForeArm & ForeArm Twist
            elif abs_x > 0.28:
                if y < -0.06:
                    u_tw = (-y) / 0.13
                    w_fatw = 1.0 - harmonic_cosine_falloff(u_tw)
                    table.add_weight(i, f"ForeArm_Twist.{side}", w_fatw)
                    table.add_weight(i, f"ForeArm.{side}", 1.0 - w_fatw)
                else:
                    table.add_weight(i, f"ForeArm.{side}", 1.0)

            # Elbow hinge transition (abs_x 0.22 to 0.28)
            elif abs_x > 0.22:
                u_elb = (abs_x - 0.22) / 0.06
                w_fa = 1.0 - harmonic_cosine_falloff(u_elb)
                table.add_weight(i, f"ForeArm.{side}", w_fa)
                table.add_weight(i, f"UpperArm_Twist.{side}", 1.0 - w_fa)

            # UpperArm & UpperArm Twist (abs_x 0.16 to 0.22)
            elif abs_x > 0.16:
                u_up = (abs_x - 0.16) / 0.06
                w_uptw = 1.0 - harmonic_cosine_falloff(u_up)
                table.add_weight(i, f"UpperArm_Twist.{side}", w_uptw)
                table.add_weight(i, f"UpperArm.{side}", 1.0 - w_uptw)

            # Shoulder & Clavicle (abs_x <= 0.16)
            else:
                table.add_weight(i, f"UpperArm.{side}", 0.70)
                table.add_weight(i, f"Clavicle.{side}", 0.30)

    # 4. Anime_Legs (Bilateral: Left x > 0, Right x < 0)
    elif mesh_name == "Anime_Legs":
        for i, (x, y, z) in enumerate(vertices):
            side = "L" if x > 0.0 else "R"

            if z > 0.75:
                u_hip = (z - 0.75) / 0.05
                w_hp = 1.0 - harmonic_cosine_falloff(u_hip)
                table.add_weight(i, "Hips", w_hp)
                table.add_weight(i, f"Thigh.{side}", 1.0 - w_hp)
            elif z > 0.48:
                table.add_weight(i, f"Thigh.{side}", 1.0)
            elif z > 0.42:
                # Knee hinge transition
                u_knee = (z - 0.42) / 0.06
                w_th = 1.0 - harmonic_cosine_falloff(u_knee)
                table.add_weight(i, f"Thigh.{side}", w_th)
                table.add_weight(i, f"Shin.{side}", 1.0 - w_th)
            elif z > 0.09:
                table.add_weight(i, f"Shin.{side}", 1.0)
            elif z > 0.04:
                # Ankle transition
                u_ank = (z - 0.04) / 0.05
                w_sh = 1.0 - harmonic_cosine_falloff(u_ank)
                table.add_weight(i, f"Shin.{side}", w_sh)
                table.add_weight(i, f"Foot.{side}", 1.0 - w_sh)
            else:
                # Foot & Toe
                if y < -0.10:
                    table.add_weight(i, f"Toe.{side}", 1.0)
                else:
                    table.add_weight(i, f"Foot.{side}", 1.0)

    # 5. Anime_Skirt (12 Radial Spoke Bones - 0% Thigh Weights!)
    elif mesh_name == "Anime_Skirt":
        xc, yc = 0.0, -0.016
        sector = 2.0 * math.pi / 12.0
        for i, (x, y, z) in enumerate(vertices):
            phi = math.atan2(y - yc, x - xc)
            if phi < 0.0:
                phi += 2.0 * math.pi
            k0 = int(phi // sector) % 12
            k1 = (k0 + 1) % 12
            t = (phi - (k0 * sector)) / sector
            t = max(0.0, min(1.0, t))
            w1 = 3.0 * (t ** 2) - 2.0 * (t ** 3)
            w0 = 1.0 - w1
            table.add_weight(i, f"Skirt_{k0+1:02d}", w0)
            table.add_weight(i, f"Skirt_{k1+1:02d}", w1)

    # 6. Anime_Hair (Head scalp + Twintail chains)
    elif mesh_name == "Anime_Hair":
        for i, (x, y, z) in enumerate(vertices):
            if abs(x) < 0.09:
                table.add_weight(i, "Head", 1.0)
            else:
                side = "L" if x > 0.0 else "R"
                seg = min(5, max(1, int((1.55 - z) / 0.08) + 1))
                table.add_weight(i, f"Hair_{side}_{seg:02d}", 1.0)

    # 7. Anime_Shoes
    elif mesh_name == "Anime_Shoes":
        for i, (x, y, z) in enumerate(vertices):
            side = "L" if x > 0.0 else "R"
            if y < -0.10:
                table.add_weight(i, f"Toe.{side}", 1.0)
            elif z > 0.04:
                table.add_weight(i, f"Shin.{side}", 0.3)
                table.add_weight(i, f"Foot.{side}", 0.7)
            else:
                table.add_weight(i, f"Foot.{side}", 1.0)

    table.prune_and_normalize(default_bone="Hips", max_influences=4)
    return table.to_vertex_groups_dict()


# ==============================================================================
# 6. Blender Vertex Group Application & Verification
# ==============================================================================

def apply_vertex_weights_to_blender_mesh(
    mesh_obj: Any,
    vertex_groups_dict: Dict[str, List[Tuple[int, float]]],
    clear_existing: bool = True,
) -> None:
    """Applies computed vertex weights to a live Blender mesh object."""
    if not HAS_BPY or mesh_obj is None:
        return

    bpy.context.view_layer.objects.active = mesh_obj

    if clear_existing:
        for vg in list(mesh_obj.vertex_groups):
            mesh_obj.vertex_groups.remove(vg)

    for bone_name, pairs in vertex_groups_dict.items():
        vg = mesh_obj.vertex_groups.get(bone_name)
        if not vg:
            vg = mesh_obj.vertex_groups.new(name=bone_name)

        for v_idx, w in pairs:
            vg.add([v_idx], w, 'REPLACE')


def verify_skin_weights_normalization(
    mesh_name: str,
    vertex_groups: Dict[str, List[Tuple[int, float]]],
    num_vertices: int,
    tolerance: float = 1e-3,
) -> Tuple[bool, str]:
    """
    Audits skinning data:
    1. Normalization: sum of weights for each vertex == 1.0000 +- tolerance.
    2. Zero orphans: all vertices have at least 1 bone influence.
    3. Modular isolation: no prohibited bone weights present.
    """
    allowed = MODULAR_ISOLATION_RULES.get(mesh_name, set())

    if allowed:
        for bname in vertex_groups.keys():
            if bname not in allowed:
                return False, f"Prohibited vertex group '{bname}' found in {mesh_name}"

    v_totals = [0.0] * num_vertices
    for _, pairs in vertex_groups.items():
        for v_idx, w in pairs:
            if 0 <= v_idx < num_vertices:
                v_totals[v_idx] += w

    for i, tot in enumerate(v_totals):
        if tot == 0.0:
            return False, f"Vertex {i} in {mesh_name} has zero skin weight (orphan)"
        if abs(tot - 1.0) > tolerance:
            return False, f"Vertex {i} in {mesh_name} has unnormalized weight sum: {tot:.6f}"

    return True, f"Mesh {mesh_name} successfully passed all skin weight audits."


# ==============================================================================
# 7. SkinningDQS Class Orchestrator
# ==============================================================================

class SkinningDQS:
    """
    Master orchestrator for Dual Quaternion Skinning and modular weight assignment.
    """

    def __init__(self, armature_obj: Optional[Any] = None):
        self.armature_obj = armature_obj

    def setup_twist_bone_constraints(self, armature_obj: Optional[Any] = None) -> Dict[str, Dict[str, Any]]:
        arm = armature_obj or self.armature_obj
        return setup_twist_bone_constraints(arm)

    def apply_dual_quaternion_skinning(self, mesh_obj: Any, armature_obj: Optional[Any] = None) -> Any:
        arm = armature_obj or self.armature_obj
        return apply_dual_quaternion_skinning(mesh_obj, arm)

    def configure_all_submeshes_dqs(self, mesh_objects: List[Any], armature_obj: Optional[Any] = None) -> int:
        arm = armature_obj or self.armature_obj
        return configure_all_submeshes_dqs(mesh_objects, arm)

    def calculate_skin_weights(
        self,
        mesh_name: str,
        vertices: List[Tuple[float, float, float]],
        landmarks: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, List[Tuple[int, float]]]:
        return calculate_submesh_skin_weights(mesh_name, vertices, landmarks)

    def bind_and_skin_all_submeshes(
        self,
        submesh_objs: Dict[str, Any],
        armature_obj: Optional[Any] = None,
        landmarks: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Binds all sub-meshes to armature:
        1. Configures twist constraints on armature.
        2. Applies DQS Armature modifier (use_deform_preserve_volume = True).
        3. Computes and assigns smooth normalized skin weights.
        """
        arm = armature_obj or self.armature_obj
        twist_results = self.setup_twist_bone_constraints(arm)
        dqs_count = self.configure_all_submeshes_dqs(list(submesh_objs.values()), arm)

        weights_summary: Dict[str, Any] = {}
        for name, mesh_obj in submesh_objs.items():
            if not HAS_BPY or mesh_obj is None or not hasattr(mesh_obj, "data"):
                continue

            verts = [(v.co.x, v.co.y, v.co.z) for v in mesh_obj.data.vertices]
            vgroups = self.calculate_skin_weights(name, verts, landmarks)
            apply_vertex_weights_to_blender_mesh(mesh_obj, vgroups, clear_existing=True)

            valid, msg = verify_skin_weights_normalization(name, vgroups, len(verts))
            weights_summary[name] = {"valid": valid, "message": msg, "group_count": len(vgroups)}

        return {
            "twist_constraints": twist_results,
            "dqs_modifiers_count": dqs_count,
            "weights_summary": weights_summary,
        }
