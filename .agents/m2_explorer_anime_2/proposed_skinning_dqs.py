"""
anime_pipeline/rigging/skinning_dqs.py
Milestone 2 Features F06, F09, F10:
- F06: Arm & Forearm Twist Bones (COPY_ROTATION 0.5 local Y constraints).
- F09: Dual Quaternion Skinning Integration (use_deform_preserve_volume = True).
- F10: Smooth Weight Paint Transfer with C1 harmonic cosine falloff and modular isolation.

Author: m2_explorer_anime_2
Compatible with: Blender 4.5.4 LTS & Python 3.10+ / pytest test harness
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

# Try importing bpy for Blender runtime; fall back gracefully for headless testing
try:
    import bpy
    import mathutils
    HAS_BPY = True
except ImportError:
    bpy = None  # type: ignore
    mathutils = None  # type: ignore
    HAS_BPY = False


# ==============================================================================
# 1. Authoritative Constants & Modular Isolation Rules
# ==============================================================================

TWIST_BONES = [
    "UpperArm_Twist.L", "UpperArm_Twist.R",
    "ForeArm_Twist.L", "ForeArm_Twist.R",
]

FINGER_NAMES = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
PHALANGES = ["01", "02", "03"]

ALL_30_FINGER_BONES = [
    f"{f}.{p}.{side}" for side in ["L", "R"] for f in FINGER_NAMES for p in PHALANGES
]

SKIRT_BONES = [f"Skirt_{i:02d}" for i in range(1, 13)]
ALL_10_HAIR_BONES = [f"Hair_L_{i:02d}" for i in range(1, 6)] + [f"Hair_R_{i:02d}" for i in range(1, 6)]

# Strict Modular Vertex Group Isolation Matrix (Feature F10)
# Guarantees zero cross-mesh weight bleeding across air gaps
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
    "Anime_Skirt": {
        # CRITICAL INVARIANT: Thigh.L and Thigh.R are strictly prohibited
        "Hips",
    } | set(SKIRT_BONES),
    "Anime_Hair": {
        "Head",
    } | set(ALL_10_HAIR_BONES),
    "Anime_Shoes": {
        "Shin.L", "Shin.R",
        "Foot.L", "Foot.R",
        "Toe.L", "Toe.R",
    },
}

# Mapping of twist bones to their constraint targets and parameters
TWIST_BONE_CONFIGS = {
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
        # Standalone mock configuration for verification
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

    # Blender Pose Mode execution
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode='POSE')
    pose_bones = armature_obj.pose.bones

    for twist_name, cfg in TWIST_BONE_CONFIGS.items():
        pb = pose_bones.get(twist_name)
        target_pb = pose_bones.get(cfg["target_bone"])
        if not pb:
            continue

        # Remove existing duplicate twist constraints
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
        crc.use_y = True  # Roll axis
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
    """Activates DQS preserve volume across all 7 modular sub-meshes."""
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

            # Filter prohibited bones
            if allowed:
                v_dict = {b: w for b, w in v_dict.items() if b in allowed}

            # Top-4 pruning
            if len(v_dict) > max_influences:
                sorted_items = sorted(v_dict.items(), key=lambda item: item[1], reverse=True)[:max_influences]
                v_dict = dict(sorted_items)

            total_w = sum(v_dict.values())
            if total_w > 1e-9:
                self.weights[v_idx] = {b: (w / total_w) for b, w in v_dict.items()}
            else:
                # Fallback assignment to valid default bone
                fallback = default_bone if (not allowed or default_bone in allowed) else next(iter(allowed))
                self.weights[v_idx] = {fallback: 1.0}

    def to_vertex_groups_dict(self) -> Dict[str, List[Tuple[int, float]]]:
        """Converts to bone -> [(vertex_idx, weight)] mapping."""
        vgroups: Dict[str, List[Tuple[int, float]]] = {}
        for v_idx, b_dict in self.weights.items():
            for bone, w in b_dict.items():
                if bone not in vgroups:
                    vgroups[bone] = []
                vgroups[bone].append((v_idx, round(w, 5)))
        return vgroups


def calculate_submesh_skin_weights(
    mesh_name: str,
    vertices: List[Tuple[float, float, float]],
    bone_landmarks: Optional[Dict[str, Dict[str, Tuple[float, float, float]]]] = None,
) -> Dict[str, List[Tuple[int, float]]]:
    """
    Computes smooth, anti-pinched vertex weights for a modular sub-mesh component.
    Applies C1 harmonic cosine falloff, twist bone gradients, and modular isolation.
    """
    num_verts = len(vertices)
    table = VertexWeightTable(mesh_name=mesh_name, num_vertices=num_verts)
    allowed = MODULAR_ISOLATION_RULES.get(mesh_name, set())

    # --------------------------------------------------------------------------
    # Sub-Mesh 1: Anime_Head
    # --------------------------------------------------------------------------
    if mesh_name == "Anime_Head":
        z_neck_seam = 1.37
        for i, (x, y, z) in enumerate(vertices):
            if z >= 1.42:
                table.add_weight(i, "Head", 1.0)
            elif z <= z_neck_seam:
                table.add_weight(i, "Neck", 1.0)
            else:
                u = (z - z_neck_seam) / (1.42 - z_neck_seam)
                w_head = 1.0 - harmonic_cosine_falloff(u)
                table.add_weight(i, "Head", w_head)
                table.add_weight(i, "Neck", 1.0 - w_head)

    # --------------------------------------------------------------------------
    # Sub-Mesh 2: Anime_Torso
    # --------------------------------------------------------------------------
    elif mesh_name == "Anime_Torso":
        for i, (x, y, z) in enumerate(vertices):
            if z >= 1.32:
                table.add_weight(i, "Neck", 1.0)
            elif z >= 1.18:
                u = (z - 1.18) / (1.32 - 1.18)
                table.add_weight(i, "Spine2", harmonic_cosine_falloff(u))
                table.add_weight(i, "Neck", 1.0 - harmonic_cosine_falloff(u))
            elif z >= 1.02:
                u = (z - 1.02) / (1.18 - 1.02)
                table.add_weight(i, "Spine1", harmonic_cosine_falloff(u))
                table.add_weight(i, "Spine2", 1.0 - harmonic_cosine_falloff(u))
            elif z >= 0.90:
                u = (z - 0.90) / (1.02 - 0.90)
                table.add_weight(i, "Spine", harmonic_cosine_falloff(u))
                table.add_weight(i, "Spine1", 1.0 - harmonic_cosine_falloff(u))
            else:
                table.add_weight(i, "Hips", 1.0)

    # --------------------------------------------------------------------------
    # Sub-Mesh 3: Anime_Arms (With Twist Bone Gradients & Finger Isolation)
    # --------------------------------------------------------------------------
    elif mesh_name == "Anime_Arms":
        for i, (x, y, z) in enumerate(vertices):
            side = "L" if x < 0.0 else "R"

            # 1. Wrist and Finger Articulation (z < 0.60)
            if z < 0.60:
                if y > 0.015:
                    table.add_weight(i, f"Thumb.01.{side}", 1.0)
                elif y > 0.005:
                    table.add_weight(i, f"Index.01.{side}", 1.0)
                elif y > -0.005:
                    table.add_weight(i, f"Middle.01.{side}", 1.0)
                elif y > -0.015:
                    table.add_weight(i, f"Ring.01.{side}", 1.0)
                else:
                    table.add_weight(i, f"Pinky.01.{side}", 1.0)

            # 2. Forearm & Forearm Twist (0.60 <= z < 0.85)
            elif z < 0.85:
                t = (0.85 - z) / (0.85 - 0.60)
                if t < 0.45:
                    table.add_weight(i, f"ForeArm.{side}", 1.0)
                elif t < 0.85:
                    u_tw = (t - 0.45) / 0.40
                    w_tw = 1.0 - harmonic_cosine_falloff(u_tw)
                    table.add_weight(i, f"ForeArm.{side}", 1.0 - w_tw)
                    table.add_weight(i, f"ForeArm_Twist.{side}", w_tw)
                else:
                    u_wr = (t - 0.85) / 0.15
                    w_hand = 1.0 - harmonic_cosine_falloff(u_wr)
                    table.add_weight(i, f"ForeArm_Twist.{side}", 1.0 - w_hand)
                    table.add_weight(i, f"Hand.{side}", w_hand)

            # 3. Upper Arm & Upper Arm Twist (0.85 <= z < 1.15)
            elif z < 1.15:
                if z < 0.87:
                    u_elb = (z - 0.84) / 0.03
                    w_fa = harmonic_cosine_falloff(u_elb)
                    table.add_weight(i, f"ForeArm.{side}", w_fa)
                    table.add_weight(i, f"UpperArm_Twist.{side}", 1.0 - w_fa)
                else:
                    t_up = (1.15 - z) / (1.15 - 0.87)
                    if t_up > 0.50:
                        w_up_tw = (t_up - 0.50) / 0.50
                        table.add_weight(i, f"UpperArm.{side}", 1.0 - w_up_tw)
                        table.add_weight(i, f"UpperArm_Twist.{side}", w_up_tw)
                    else:
                        table.add_weight(i, f"UpperArm_Twist.{side}", 1.0)

            # 4. Shoulder / Deltoid (z >= 1.15)
            else:
                table.add_weight(i, f"UpperArm.{side}", 0.70)
                table.add_weight(i, f"Clavicle.{side}", 0.30)

    # --------------------------------------------------------------------------
    # Sub-Mesh 4: Anime_Legs
    # --------------------------------------------------------------------------
    elif mesh_name == "Anime_Legs":
        for i, (x, y, z) in enumerate(vertices):
            side = "L" if x < 0.0 else "R"
            if z > 0.60:
                table.add_weight(i, f"Thigh.{side}", 1.0)
            elif z > 0.45:
                u_knee = (z - 0.45) / 0.15
                table.add_weight(i, f"Shin.{side}", harmonic_cosine_falloff(u_knee))
                table.add_weight(i, f"Thigh.{side}", 1.0 - harmonic_cosine_falloff(u_knee))
            elif z > 0.10:
                table.add_weight(i, f"Shin.{side}", 1.0)
            else:
                table.add_weight(i, f"Foot.{side}", 1.0)

    # --------------------------------------------------------------------------
    # Sub-Mesh 5: Anime_Skirt (12 Radial Spoke Bones - 0% Thigh Weights!)
    # --------------------------------------------------------------------------
    elif mesh_name == "Anime_Skirt":
        for i, (x, y, z) in enumerate(vertices):
            ang = math.atan2(y, x)
            if ang < 0:
                ang += 2.0 * math.pi
            spoke_idx = int(round((ang / (2.0 * math.pi)) * 12.0)) % 12
            bone_name = f"Skirt_{spoke_idx + 1:02d}"
            table.add_weight(i, bone_name, 1.0)

    # --------------------------------------------------------------------------
    # Sub-Mesh 6: Anime_Hair (Twintail Chains & Scalp)
    # --------------------------------------------------------------------------
    elif mesh_name == "Anime_Hair":
        for i, (x, y, z) in enumerate(vertices):
            if abs(x) < 0.09:
                table.add_weight(i, "Head", 1.0)
            else:
                side = "L" if x < 0.0 else "R"
                seg = min(5, max(1, int((1.55 - z) / 0.12) + 1))
                table.add_weight(i, f"Hair_{side}_{seg:02d}", 1.0)

    # --------------------------------------------------------------------------
    # Sub-Mesh 7: Anime_Shoes (Ankles, Soles & Toes)
    # --------------------------------------------------------------------------
    elif mesh_name == "Anime_Shoes":
        for i, (x, y, z) in enumerate(vertices):
            side = "L" if x < 0.0 else "R"
            if y > 0.02:
                table.add_weight(i, f"Toe.{side}", 1.0)
            else:
                table.add_weight(i, f"Foot.{side}", 1.0)

    table.prune_and_normalize(default_bone="Hips", max_influences=4)
    return table.to_vertex_groups_dict()


# ==============================================================================
# 6. Automated Skinning & Normalization Verification
# ==============================================================================

def verify_skin_weights_normalization(
    mesh_name: str,
    vertex_groups: Dict[str, List[Tuple[int, float]]],
    num_vertices: int,
    tolerance: float = 1e-4,
) -> Tuple[bool, str]:
    """
    Audits skinning data against:
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
    for bname, pairs in vertex_groups.items():
        for v_idx, w in pairs:
            if 0 <= v_idx < num_vertices:
                v_totals[v_idx] += w

    for i, tot in enumerate(v_totals):
        if abs(tot - 1.0) > tolerance:
            return False, f"Vertex {i} in {mesh_name} has unnormalized weight sum: {tot:.6f}"

    return True, f"Mesh {mesh_name} successfully passed all skin weight audits."
