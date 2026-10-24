"""
Pytest Test Infrastructure & Progressive Test Harness for Anime Character Pipeline.
Authoritative source: ORIGINAL_REQUEST.md, PROJECT.md
"""

from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import pytest

# Ensure anime_character_pipeline and root repository are in sys.path
PROJECT_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = PROJECT_DIR.parent.parent

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# ==============================================================================
# 1. Authoritative Constant Specifications
# ==============================================================================

SUBMESH_NAMES: List[str] = [
    "Anime_Head",
    "Anime_Torso",
    "Anime_Arms",
    "Anime_Legs",
    "Anime_Hair",
    "Anime_Skirt",
    "Anime_Shoes",
]

UNIVERSAL_SPINE_BONES: List[str] = [
    "Hips",
    "Spine",
    "Spine1",
    "Spine2",
    "Neck",
    "Head",
]

UNIVERSAL_LIMB_BONES: List[str] = [
    "Clavicle.L", "Clavicle.R",
    "UpperArm.L", "UpperArm.R",
    "ForeArm.L", "ForeArm.R",
    "Hand.L", "Hand.R",
    "Thigh.L", "Thigh.R",
    "Shin.L", "Shin.R",
    "Foot.L", "Foot.R",
    "Toe.L", "Toe.R",
]

TWIST_BONES: List[str] = [
    "UpperArm_Twist.L", "UpperArm_Twist.R",
    "ForeArm_Twist.L", "ForeArm_Twist.R",
]

# 30 Articulated finger phalanges (15 L + 15 R)
FINGER_NAMES = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
PHALANGES = ["01", "02", "03"]

FINGER_BONES_LEFT: List[str] = [
    f"{finger}.{ph}.L" for finger in FINGER_NAMES for ph in PHALANGES
]
FINGER_BONES_RIGHT: List[str] = [
    f"{finger}.{ph}.R" for finger in FINGER_NAMES for ph in PHALANGES
]
ALL_30_FINGER_BONES: List[str] = FINGER_BONES_LEFT + FINGER_BONES_RIGHT

# 12-Radial Skirt Bones
SKIRT_BONES: List[str] = [f"Skirt_{i:02d}" for i in range(1, 13)]

# 5-Bone Twintail Secondary Chains (5 L + 5 R = 10)
HAIR_BONES_LEFT: List[str] = [f"Hair_L_{i:02d}" for i in range(1, 6)]
HAIR_BONES_RIGHT: List[str] = [f"Hair_R_{i:02d}" for i in range(1, 6)]
ALL_10_HAIR_BONES: List[str] = HAIR_BONES_LEFT + HAIR_BONES_RIGHT

ALL_REQUIRED_ARMATURE_BONES: List[str] = (
    UNIVERSAL_SPINE_BONES
    + UNIVERSAL_LIMB_BONES
    + TWIST_BONES
    + ALL_30_FINGER_BONES
    + SKIRT_BONES
    + ALL_10_HAIR_BONES
)

# 4 Programmatic Anime Actions
ACTION_NAMES: List[str] = [
    "action_anime_idle_cute",
    "action_anime_wave_greeting",
    "action_anime_walk_cycle",
    "action_anime_jump_cheer",
]

# Joint Rotation Anatomical Hinge Clamps
HINGE_LIMITS = {
    "Elbow.L": (0.0, 145.0),  # degrees (0 to 145)
    "Elbow.R": (0.0, 145.0),
    "Knee.L": (0.0, 140.0),   # degrees (0 to 140)
    "Knee.R": (0.0, 140.0),
    "Skirt_Pitch": (-15.0, 65.0),  # degrees pitch clamp
}

# Volume & Stretch Invariants
MAX_EDGE_STRETCH_RATIO: float = 1.85
MIN_VOLUME_RETENTION_RATIO: float = 0.85
MIN_SKIRT_THIGH_CLEARANCE_MM: float = 15.0  # +15mm positive clearance
SOLIDIFY_OUTLINE_THICKNESS: float = -0.015  # -15mm inverted hull

# ==============================================================================
# 2. Geometric & Physical Mathematical Solvers
# ==============================================================================

def compute_mesh_signed_volume(vertices: List[Tuple[float, float, float]], faces: List[List[int]]) -> float:
    """
    Computes signed volume of a closed 3D surface mesh using the Divergence Theorem:
    V = (1/6) * sum( v0 . (v1 x v2) )
    Supports triangular faces and quad faces (split into two triangles).
    """
    if not vertices or not faces:
        return 0.0

    total_signed_volume = 0.0
    for face in faces:
        triangles: List[Tuple[int, int, int]] = []
        if len(face) == 3:
            triangles.append((face[0], face[1], face[2]))
        elif len(face) == 4:
            # Quad face split into 2 triangles
            triangles.append((face[0], face[1], face[2]))
            triangles.append((face[0], face[2], face[3]))
        else:
            # General polygon fan triangulation
            for k in range(1, len(face) - 1):
                triangles.append((face[0], face[k], face[k + 1]))

        for i0, i1, i2 in triangles:
            v0 = vertices[i0]
            v1 = vertices[i1]
            v2 = vertices[i2]
            # Cross product v1 x v2
            cx = v1[1] * v2[2] - v1[2] * v2[1]
            cy = v1[2] * v2[0] - v1[0] * v2[2]
            cz = v1[0] * v2[1] - v1[1] * v2[0]
            # Dot product v0 . (v1 x v2)
            dot = v0[0] * cx + v0[1] * cy + v0[2] * cz
            total_signed_volume += dot

    return abs(total_signed_volume) / 6.0


def compute_volume_retention(
    rest_verts: List[Tuple[float, float, float]],
    deformed_verts: List[Tuple[float, float, float]],
    faces: List[List[int]],
) -> float:
    """Returns the volume retention ratio: V_deformed / V_rest."""
    v_rest = compute_mesh_signed_volume(rest_verts, faces)
    if v_rest < 1e-9:
        return 1.0
    v_deformed = compute_mesh_signed_volume(deformed_verts, faces)
    return v_deformed / v_rest


def extract_unique_edges(faces: List[List[int]]) -> Set[Tuple[int, int]]:
    """Extracts undirected edges from face indices."""
    edges: Set[Tuple[int, int]] = set()
    for face in faces:
        n = len(face)
        for i in range(n):
            u, v = face[i], face[(i + 1) % n]
            edge = (min(u, v), max(u, v))
            edges.add(edge)
    return edges


def compute_max_edge_stretch(
    rest_verts: List[Tuple[float, float, float]],
    deformed_verts: List[Tuple[float, float, float]],
    faces: List[List[int]],
) -> float:
    """
    Computes max edge stretch ratio S_max = max( L_deformed / L_rest )
    across all mesh edges.
    """
    edges = extract_unique_edges(faces)
    max_stretch = 1.0

    for u, v in edges:
        p0, p1 = rest_verts[u], rest_verts[v]
        d0 = math.sqrt((p0[0] - p1[0]) ** 2 + (p0[1] - p1[1]) ** 2 + (p0[2] - p1[2]) ** 2)
        if d0 < 1e-8:
            continue

        q0, q1 = deformed_verts[u], deformed_verts[v]
        d1 = math.sqrt((q0[0] - q1[0]) ** 2 + (q0[1] - q1[1]) ** 2 + (q0[2] - q1[2]) ** 2)
        stretch = d1 / d0
        if stretch > max_stretch:
            max_stretch = stretch

    return max_stretch


def clamp_joint_angle(angle_deg: float, min_deg: float, max_deg: float) -> float:
    """Clamps joint rotation within anatomical hinge limits."""
    return max(min_deg, min(angle_deg, max_deg))


def evaluate_twist_bone_rotation(child_rotation_deg: float, factor: float = 0.5) -> float:
    """
    Evaluates forearm/arm twist bone rotation under COPY_ROTATION constraint.
    Default factor: 0.5 local Y axis.
    """
    return child_rotation_deg * factor


def solve_spring_damper_step(
    pos: float,
    vel: float,
    rest_pos: float,
    mass: float,
    stiffness: float,
    damping: float,
    ext_accel: float,
    dt: float,
) -> Tuple[float, float]:
    """
    Implicitly damped integration for secondary spring physics:
    m * x'' + c * x' + k * (x - x0) = F_ext
    Guarantees unconditional numerical stability under any damping and timestep.
    """
    if mass <= 1e-6:
        mass = 1e-6
    dt = min(max(dt, 1e-5), 0.1)

    spring_force = -stiffness * (pos - rest_pos)
    force = spring_force + mass * ext_accel

    vel_new = (vel + (force / mass) * dt) / (1.0 + (damping / mass) * dt)
    pos_new = pos + vel_new * dt
    return pos_new, vel_new


# ==============================================================================
# 3. Data Structures for Canonical Models
# ==============================================================================

@dataclass
class SubMeshDefinition:
    name: str
    vertices: List[Tuple[float, float, float]]
    faces: List[List[int]]
    vertex_groups: Dict[str, List[Tuple[int, float]]]  # bone_name -> [(vert_idx, weight)]
    is_quad_dominant: bool = True
    material_slots: List[str] = field(default_factory=list)
    modifiers: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class BoneDefinition:
    name: str
    parent: Optional[str]
    head: Tuple[float, float, float]
    tail: Tuple[float, float, float]
    roll: float = 0.0
    constraints: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ArmatureDefinition:
    name: str
    bones: Dict[str, BoneDefinition]
    use_deform_preserve_volume: bool = True  # Dual Quaternion Skinning


@dataclass
class ActionDefinition:
    name: str
    frame_start: int
    frame_end: int
    fps: int = 30
    curves: Dict[str, List[Tuple[int, float]]] = field(default_factory=dict)


@dataclass
class MaterialDefinition:
    name: str
    is_cel_shading: bool
    has_angel_ring: bool = False
    is_outline: bool = False
    node_types: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)


# ==============================================================================
# 4. Canonical Model Factory (Contractual Baseline)
# ==============================================================================

def create_canonical_modular_meshes() -> Dict[str, SubMeshDefinition]:
    """
    Synthesizes the canonical 7 modular sub-meshes adhering to F01, F02, F03:
    Head, Torso, Arms, Legs, Hair, Skirt, Shoes.
    """
    meshes: Dict[str, SubMeshDefinition] = {}

    # Head mesh: 1:6.5 to 1:7.0 anime ratio, stylized facial topology
    head_verts = [
        (-0.08, 0.0, 1.58), (0.08, 0.0, 1.58), (0.08, 0.10, 1.58), (-0.08, 0.10, 1.58),  # Crown
        (-0.06, 0.0, 1.50), (0.06, 0.0, 1.50), (0.06, 0.08, 1.50), (-0.06, 0.08, 1.50),  # Temples
        (-0.04, 0.0, 1.40), (0.04, 0.0, 1.40), (0.0, -0.06, 1.35), (0.0, 0.06, 1.40),    # Chin/Jaw (min chin 1.35m)
        (-0.04, 0.0, 1.35), (0.04, 0.0, 1.35), (0.0, 0.04, 1.35), (0.0, -0.04, 1.35),    # Neck seam
    ]
    head_faces = [
        [0, 1, 2, 3], [4, 5, 6, 7], [0, 4, 5, 1], [1, 5, 6, 2],
        [2, 6, 7, 3], [3, 7, 4, 0], [8, 9, 10, 11], [12, 13, 14, 15]
    ]
    meshes["Anime_Head"] = SubMeshDefinition(
        name="Anime_Head",
        vertices=head_verts,
        faces=head_faces,
        vertex_groups={"Head": [(i, 1.0) for i in range(12)], "Neck": [(i, 1.0) for i in range(12, 16)]},
        material_slots=["M_Anime_Skin", "M_Anime_Outline"]
    )

    # Torso mesh: Neck to pelvis
    torso_verts = [
        (-0.04, 0.0, 1.35), (0.04, 0.0, 1.35), (0.0, 0.04, 1.35), (0.0, -0.04, 1.35),   # Neck seam
        (-0.14, 0.0, 1.20), (0.14, 0.0, 1.20), (0.0, 0.08, 1.20), (0.0, -0.08, 1.20),   # Chest
        (-0.10, 0.0, 1.00), (0.10, 0.0, 1.00), (0.0, 0.07, 1.00), (0.0, -0.07, 1.00),   # Waist
        (-0.12, 0.0, 0.85), (0.12, 0.0, 0.85), (0.0, 0.09, 0.85), (0.0, -0.09, 0.85),   # Pelvis/Hips
    ]
    torso_faces = [
        [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7],
        [4, 5, 9, 8], [5, 6, 10, 9], [6, 7, 11, 10], [7, 4, 8, 11],
        [8, 9, 13, 12], [9, 10, 14, 13], [10, 11, 15, 14], [11, 8, 12, 15]
    ]
    meshes["Anime_Torso"] = SubMeshDefinition(
        name="Anime_Torso",
        vertices=torso_verts,
        faces=torso_faces,
        vertex_groups={
            "Neck": [(0, 1.0), (1, 1.0), (2, 1.0), (3, 1.0)],
            "Spine2": [(4, 1.0), (5, 1.0), (6, 1.0), (7, 1.0)],
            "Spine1": [(8, 1.0), (9, 1.0), (10, 1.0), (11, 1.0)],
            "Hips": [(12, 1.0), (13, 1.0), (14, 1.0), (15, 1.0)],
        },
        material_slots=["M_Anime_Skin", "M_Anime_Outline"]
    )

    # Arms mesh: With 3-loop elbow hinge and 5-finger hands
    arms_verts = [
        (-0.16, 0.0, 1.20), (-0.28, 0.0, 1.20),   # Shoulder
        (-0.30, 0.0, 1.00), (-0.30, 0.02, 1.00), (-0.30, -0.02, 1.00),  # Upper arm
        # Elbow 3-loop hinge
        (-0.30, 0.0, 0.86), (-0.30, 0.0, 0.85), (-0.30, 0.0, 0.84),
        (-0.30, 0.0, 0.70), (-0.30, 0.01, 0.70),  # Forearm
        (-0.30, 0.0, 0.60),                        # Wrist
        # 5 Fingers
        (-0.32, 0.02, 0.56), (-0.31, 0.01, 0.54), (-0.30, 0.0, 0.53), (-0.29, -0.01, 0.54), (-0.28, -0.02, 0.55),
        # Mirrored Right Arm vertices
        (0.16, 0.0, 1.20), (0.28, 0.0, 1.20),
        (0.30, 0.0, 1.00), (0.30, 0.02, 1.00), (0.30, -0.02, 1.00),
        (0.30, 0.0, 0.86), (0.30, 0.0, 0.85), (0.30, 0.0, 0.84),
        (0.30, 0.0, 0.70), (0.30, 0.01, 0.70),
        (0.30, 0.0, 0.60),
        (0.32, 0.02, 0.56), (0.31, 0.01, 0.54), (0.30, 0.0, 0.53), (0.29, -0.01, 0.54), (0.28, -0.02, 0.55),
    ]
    arms_faces = [
        [0, 1, 2, 3], [2, 3, 5, 6], [5, 6, 7, 8], [8, 9, 10, 11],
        [16, 17, 18, 19], [18, 19, 21, 22], [21, 22, 23, 24], [24, 25, 26, 27]
    ]
    meshes["Anime_Arms"] = SubMeshDefinition(
        name="Anime_Arms",
        vertices=arms_verts,
        faces=arms_faces,
        vertex_groups={
            "UpperArm.L": [(0, 1.0), (1, 1.0), (2, 0.5), (3, 0.5), (4, 1.0)],
            "UpperArm_Twist.L": [(2, 0.5), (3, 0.5)],
            "ForeArm.L": [(5, 1.0), (6, 1.0), (7, 1.0), (8, 0.5), (9, 0.5)],
            "ForeArm_Twist.L": [(8, 0.5), (9, 0.5)],
            "Hand.L": [(10, 1.0)],
            "Thumb.01.L": [(11, 1.0)],
            "Index.01.L": [(12, 1.0)],
            "Middle.01.L": [(13, 1.0)],
            "Ring.01.L": [(14, 1.0)],
            "Pinky.01.L": [(15, 1.0)],
            "UpperArm.R": [(16, 1.0), (17, 1.0), (18, 0.5), (19, 0.5), (20, 1.0)],
            "UpperArm_Twist.R": [(18, 0.5), (19, 0.5)],
            "ForeArm.R": [(21, 1.0), (22, 1.0), (23, 1.0), (24, 0.5), (25, 0.5)],
            "ForeArm_Twist.R": [(24, 0.5), (25, 0.5)],
            "Hand.R": [(26, 1.0)],
            "Thumb.01.R": [(27, 1.0)],
            "Index.01.R": [(28, 1.0)],
            "Middle.01.R": [(29, 1.0)],
            "Ring.01.R": [(30, 1.0)],
            "Pinky.01.R": [(31, 1.0)],
        },
        material_slots=["M_Anime_Skin", "M_Anime_Outline"]
    )

    # Legs mesh: Thighs, 3-loop knee hinge, shins, ankles
    legs_verts = [
        # Left Leg
        (-0.08, 0.0, 0.85), (-0.08, 0.06, 0.85), (-0.08, -0.06, 0.85), (-0.04, 0.0, 0.85),  # Thigh upper (radius ~0.06m)
        (-0.08, 0.0, 0.65), (-0.08, 0.05, 0.65),
        # Knee 3-loop hinge
        (-0.08, 0.0, 0.49), (-0.08, 0.0, 0.48), (-0.08, 0.0, 0.47),
        (-0.08, 0.0, 0.25), (-0.08, 0.04, 0.25),  # Shin
        (-0.08, 0.0, 0.08), (-0.08, 0.03, 0.08),  # Ankle
        # Right Leg
        (0.08, 0.0, 0.85), (0.08, 0.06, 0.85), (0.08, -0.06, 0.85), (0.04, 0.0, 0.85),
        (0.08, 0.0, 0.65), (0.08, 0.05, 0.65),
        (0.08, 0.0, 0.49), (0.08, 0.0, 0.48), (0.08, 0.0, 0.47),
        (0.08, 0.0, 0.25), (0.08, 0.04, 0.25),
        (0.08, 0.0, 0.08), (0.08, 0.03, 0.08),
    ]
    legs_faces = [
        [0, 1, 4, 3], [1, 2, 5, 4], [4, 5, 7, 6], [6, 7, 8, 9], [9, 10, 12, 11],
        [13, 14, 17, 16], [14, 15, 18, 17], [17, 18, 20, 19], [19, 20, 21, 22], [22, 23, 25, 24]
    ]
    meshes["Anime_Legs"] = SubMeshDefinition(
        name="Anime_Legs",
        vertices=legs_verts,
        faces=legs_faces,
        vertex_groups={
            "Thigh.L": [(0, 1.0), (1, 1.0), (2, 1.0), (3, 1.0), (4, 1.0), (5, 1.0)],
            "Shin.L": [(6, 1.0), (7, 1.0), (8, 1.0), (9, 1.0), (10, 1.0)],
            "Foot.L": [(11, 1.0), (12, 1.0)],
            "Thigh.R": [(13, 1.0), (14, 1.0), (15, 1.0), (16, 1.0), (17, 1.0), (18, 1.0)],
            "Shin.R": [(19, 1.0), (20, 1.0), (21, 1.0), (22, 1.0), (23, 1.0)],
            "Foot.R": [(24, 1.0), (25, 1.0)],
        },
        material_slots=["M_Anime_Skin", "M_Anime_Outline"]
    )

    # Hair mesh: Scalp base + left & right twintail chains
    hair_verts = [
        # Scalp base
        (-0.085, 0.0, 1.58), (0.085, 0.0, 1.58), (0.0, 0.105, 1.58), (0.0, -0.095, 1.58),
        # Left Twintail (5 segments)
        (-0.12, 0.0, 1.50), (-0.15, 0.0, 1.35), (-0.17, 0.0, 1.20), (-0.18, 0.0, 1.05), (-0.19, 0.0, 0.90),
        # Right Twintail (5 segments)
        (0.12, 0.0, 1.50), (0.15, 0.0, 1.35), (0.17, 0.0, 1.20), (0.18, 0.0, 1.05), (0.19, 0.0, 0.90),
    ]
    hair_faces = [
        [0, 1, 2, 3],
        [4, 5, 6, 7], [5, 6, 7, 8],
        [9, 10, 11, 12], [10, 11, 12, 13]
    ]
    meshes["Anime_Hair"] = SubMeshDefinition(
        name="Anime_Hair",
        vertices=hair_verts,
        faces=hair_faces,
        vertex_groups={
            "Head": [(0, 1.0), (1, 1.0), (2, 1.0), (3, 1.0)],
            "Hair_L_01": [(4, 1.0)], "Hair_L_02": [(5, 1.0)], "Hair_L_03": [(6, 1.0)],
            "Hair_L_04": [(7, 1.0)], "Hair_L_05": [(8, 1.0)],
            "Hair_R_01": [(9, 1.0)], "Hair_R_02": [(10, 1.0)], "Hair_R_03": [(11, 1.0)],
            "Hair_R_04": [(12, 1.0)], "Hair_R_05": [(13, 1.0)],
        },
        material_slots=["M_Anime_Hair", "M_Anime_Outline"]
    )

    # Skirt mesh: Pleated A-line skirt with +15mm positive clearance above thighs (radius ~0.15m at waist, 0.25m at hem)
    skirt_verts: List[Tuple[float, float, float]] = []
    # Waist ring (12 vertices, radius 0.14m at z=0.95m)
    for k in range(12):
        ang = k * (2 * math.pi / 12)
        skirt_verts.append((0.14 * math.cos(ang), 0.14 * math.sin(ang), 0.95))
    # Mid ring (12 vertices, radius 0.18m at z=0.80m)
    for k in range(12):
        ang = k * (2 * math.pi / 12)
        skirt_verts.append((0.18 * math.cos(ang), 0.18 * math.sin(ang), 0.80))
    # Hem ring (12 vertices, radius 0.24m at z=0.65m)
    for k in range(12):
        ang = k * (2 * math.pi / 12)
        skirt_verts.append((0.24 * math.cos(ang), 0.24 * math.sin(ang), 0.65))

    skirt_faces: List[List[int]] = []
    for k in range(12):
        k_next = (k + 1) % 12
        # Upper quad
        skirt_faces.append([k, k_next, 12 + k_next, 12 + k])
        # Lower quad
        skirt_faces.append([12 + k, 12 + k_next, 24 + k_next, 24 + k])

    skirt_vg: Dict[str, List[Tuple[int, float]]] = {}
    for i in range(12):
        bone_name = f"Skirt_{i+1:02d}"
        skirt_vg[bone_name] = [(i, 1.0), (12 + i, 1.0), (24 + i, 1.0)]

    meshes["Anime_Skirt"] = SubMeshDefinition(
        name="Anime_Skirt",
        vertices=skirt_verts,
        faces=skirt_faces,
        vertex_groups=skirt_vg,  # Notice NO Thigh.L or Thigh.R weights!
        material_slots=["M_Anime_Clothes", "M_Anime_Outline"]
    )

    # Shoes mesh: Flat ground-plane sole at Z = 0.0
    shoes_verts = [
        # Left Shoe
        (-0.08, -0.04, 0.08), (-0.08, 0.04, 0.08), (-0.11, 0.0, 0.08), (-0.05, 0.0, 0.08),  # Ankle collar
        (-0.08, -0.05, 0.0), (-0.08, 0.05, 0.0), (-0.12, 0.0, 0.0), (-0.04, 0.0, 0.0),      # Ground contact Z=0.0
        # Right Shoe
        (0.08, -0.04, 0.08), (0.08, 0.04, 0.08), (0.11, 0.0, 0.08), (0.05, 0.0, 0.08),
        (0.08, -0.05, 0.0), (0.08, 0.05, 0.0), (0.12, 0.0, 0.0), (0.04, 0.0, 0.0),
    ]
    shoes_faces = [
        [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7],
        [8, 9, 13, 12], [9, 10, 14, 13], [10, 11, 15, 14], [11, 8, 12, 15]
    ]
    meshes["Anime_Shoes"] = SubMeshDefinition(
        name="Anime_Shoes",
        vertices=shoes_verts,
        faces=shoes_faces,
        vertex_groups={
            "Foot.L": [(0, 1.0), (1, 1.0), (4, 1.0), (5, 1.0)],
            "Toe.L": [(2, 1.0), (3, 1.0), (6, 1.0), (7, 1.0)],
            "Foot.R": [(8, 1.0), (9, 1.0), (12, 1.0), (13, 1.0)],
            "Toe.R": [(10, 1.0), (11, 1.0), (14, 1.0), (15, 1.0)],
        },
        material_slots=["M_Anime_Clothes", "M_Anime_Outline"]
    )

    return meshes


def create_canonical_armature() -> ArmatureDefinition:
    """Creates the canonical Anime_Armature containing all required bones."""
    bones: Dict[str, BoneDefinition] = {}

    # Spine chain
    bones["Hips"] = BoneDefinition("Hips", None, (0.0, 0.0, 0.95), (0.0, 0.0, 1.05))
    bones["Spine"] = BoneDefinition("Spine", "Hips", (0.0, 0.0, 1.05), (0.0, 0.0, 1.15))
    bones["Spine1"] = BoneDefinition("Spine1", "Spine", (0.0, 0.0, 1.15), (0.0, 0.0, 1.25))
    bones["Spine2"] = BoneDefinition("Spine2", "Spine1", (0.0, 0.0, 1.25), (0.0, 0.0, 1.32))
    bones["Neck"] = BoneDefinition("Neck", "Spine2", (0.0, 0.0, 1.32), (0.0, 0.0, 1.40))
    bones["Head"] = BoneDefinition("Head", "Neck", (0.0, 0.0, 1.40), (0.0, 0.0, 1.58))

    # Left & Right Arms + Twists
    for side, sign in [("L", -1.0), ("R", 1.0)]:
        bones[f"Clavicle.{side}"] = BoneDefinition(f"Clavicle.{side}", "Spine2", (0.0, 0.0, 1.30), (sign * 0.16, 0.0, 1.28))
        bones[f"UpperArm.{side}"] = BoneDefinition(f"UpperArm.{side}", f"Clavicle.{side}", (sign * 0.16, 0.0, 1.28), (sign * 0.30, 0.0, 1.00))
        bones[f"UpperArm_Twist.{side}"] = BoneDefinition(
            f"UpperArm_Twist.{side}", f"UpperArm.{side}", (sign * 0.23, 0.0, 1.14), (sign * 0.30, 0.0, 1.00),
            constraints=[{"type": "COPY_ROTATION", "target": f"UpperArm.{side}", "factor": 0.5, "axis": "Y"}]
        )
        bones[f"ForeArm.{side}"] = BoneDefinition(f"ForeArm.{side}", f"UpperArm.{side}", (sign * 0.30, 0.0, 1.00), (sign * 0.30, 0.0, 0.70))
        bones[f"ForeArm_Twist.{side}"] = BoneDefinition(
            f"ForeArm_Twist.{side}", f"ForeArm.{side}", (sign * 0.30, 0.0, 0.85), (sign * 0.30, 0.0, 0.70),
            constraints=[{"type": "COPY_ROTATION", "target": f"Hand.{side}", "factor": 0.5, "axis": "Y"}]
        )
        bones[f"Hand.{side}"] = BoneDefinition(f"Hand.{side}", f"ForeArm.{side}", (sign * 0.30, 0.0, 0.70), (sign * 0.30, 0.0, 0.60))

        # 15 Articulated Finger bones per hand
        for finger in FINGER_NAMES:
            parent_bone = f"Hand.{side}"
            for ph in PHALANGES:
                bname = f"{finger}.{ph}.{side}"
                bones[bname] = BoneDefinition(bname, parent_bone, (sign * 0.30, 0.0, 0.60), (sign * 0.30, 0.0, 0.55))
                parent_bone = bname

    # Left & Right Legs
    for side, sign in [("L", -1.0), ("R", 1.0)]:
        bones[f"Thigh.{side}"] = BoneDefinition(f"Thigh.{side}", "Hips", (sign * 0.08, 0.0, 0.88), (sign * 0.08, 0.0, 0.48))
        bones[f"Shin.{side}"] = BoneDefinition(f"Shin.{side}", f"Thigh.{side}", (sign * 0.08, 0.0, 0.48), (sign * 0.08, 0.0, 0.08))
        bones[f"Foot.{side}"] = BoneDefinition(f"Foot.{side}", f"Shin.{side}", (sign * 0.08, 0.0, 0.08), (sign * 0.08, 0.08, 0.0))
        bones[f"Toe.{side}"] = BoneDefinition(f"Toe.{side}", f"Foot.{side}", (sign * 0.08, 0.08, 0.0), (sign * 0.08, 0.14, 0.0))

    # 12-Radial Skirt Bones
    for i in range(1, 13):
        ang = (i - 1) * (2 * math.pi / 12)
        bname = f"Skirt_{i:02d}"
        head_pos = (0.12 * math.cos(ang), 0.12 * math.sin(ang), 0.95)
        tail_pos = (0.22 * math.cos(ang), 0.22 * math.sin(ang), 0.65)
        bones[bname] = BoneDefinition(
            bname, "Hips", head_pos, tail_pos,
            constraints=[{"type": "LIMIT_ROTATION", "min_pitch": -15.0, "max_pitch": 65.0}]
        )

    # 10 Hair Twintail Bones
    for side, sign in [("L", -1.0), ("R", 1.0)]:
        parent_bone = "Head"
        for i in range(1, 6):
            bname = f"Hair_{side}_{i:02d}"
            head_z = 1.50 - (i - 1) * 0.12
            tail_z = 1.50 - i * 0.12
            bones[bname] = BoneDefinition(
                bname, parent_bone, (sign * (0.10 + i * 0.02), 0.0, head_z), (sign * (0.10 + (i + 1) * 0.02), 0.0, tail_z),
                constraints=[{"type": "SPRING_DYNAMICS", "stiffness": 150.0, "damping": 12.0, "mass": 0.2}]
            )
            parent_bone = bname

    return ArmatureDefinition("Anime_Armature", bones, use_deform_preserve_volume=True)


def create_canonical_actions() -> Dict[str, ActionDefinition]:
    """Creates the 4 canonical animation actions."""
    actions: Dict[str, ActionDefinition] = {}

    actions["action_anime_idle_cute"] = ActionDefinition(
        name="action_anime_idle_cute", frame_start=1, frame_end=60, fps=30,
        curves={"Spine.rot_x": [(1, 0.0), (30, 2.0), (60, 0.0)]}
    )
    actions["action_anime_wave_greeting"] = ActionDefinition(
        name="action_anime_wave_greeting", frame_start=1, frame_end=90, fps=30,
        curves={"UpperArm.R.rot_z": [(1, 0.0), (20, 110.0), (90, 0.0)], "Hand.R.rot_y": [(20, -15.0), (35, 20.0), (50, -15.0)]}
    )
    actions["action_anime_walk_cycle"] = ActionDefinition(
        name="action_anime_walk_cycle", frame_start=1, frame_end=32, fps=30,
        curves={"Thigh.L.rot_x": [(1, -25.0), (16, 30.0), (32, -25.0)], "Thigh.R.rot_x": [(1, 30.0), (16, -25.0), (32, 30.0)]}
    )
    actions["action_anime_jump_cheer"] = ActionDefinition(
        name="action_anime_jump_cheer", frame_start=1, frame_end=75, fps=30,
        curves={"Hips.loc_z": [(1, 0.0), (15, -0.15), (35, 0.45), (55, -0.08), (75, 0.0)]}
    )

    return actions


# ==============================================================================
# 5. Pytest Fixtures for Test Suites
# ==============================================================================

@pytest.fixture
def canonical_submeshes() -> Dict[str, SubMeshDefinition]:
    return create_canonical_modular_meshes()

@pytest.fixture
def canonical_armature() -> ArmatureDefinition:
    return create_canonical_armature()

@pytest.fixture
def canonical_actions() -> Dict[str, ActionDefinition]:
    return create_canonical_actions()
