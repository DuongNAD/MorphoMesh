"""
anime_pipeline/rigging/armature_builder.py
Milestone 2 Features F04 & F05: Universal Humanoid Armature & 30-Phalange Articulated Fingers.

Authoritative specification:
- F04: Universal Humanoid hierarchy (Spine, Neck, Head, Clavicles, Limbs).
- F05: Exactly 30 articulated finger phalanges (Thumb, Index, Middle, Ring, Pinky x 3 phalanges x 2 hands)
       with segment cross-product flexion normal bone roll so positive local X curls fingers toward palm with zero twist.
- Cross-standard bone name mapping properties (VRM 1.0, Rigify DEF, MMD, Unity Humanoid).
- Dynamic landmark scaling from M1 sub-mesh vertex coordinates (supporting 1.45m to 1.75m).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

try:
    import bpy
    import mathutils
    from mathutils import Euler, Matrix, Vector
    HAS_BPY = True
except ImportError:
    bpy = None  # type: ignore[assignment]
    mathutils = None  # type: ignore[assignment]
    HAS_BPY = False
    Vector = Any  # type: ignore[misc,assignment]
    Matrix = Any  # type: ignore[misc,assignment]
    Euler = Any  # type: ignore[misc,assignment]


# ==============================================================================
# 1. Authoritative Constants & Cross-Standard Mappings
# ==============================================================================

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

FINGER_NAMES: List[str] = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
PHALANGES: List[str] = ["01", "02", "03"]

FINGER_BONES_LEFT: List[str] = [
    f"{finger}.{ph}.L" for finger in FINGER_NAMES for ph in PHALANGES
]
FINGER_BONES_RIGHT: List[str] = [
    f"{finger}.{ph}.R" for finger in FINGER_NAMES for ph in PHALANGES
]
ALL_30_FINGER_BONES: List[str] = FINGER_BONES_LEFT + FINGER_BONES_RIGHT

SKIRT_BONES: List[str] = [f"Skirt_{i:02d}" for i in range(1, 13)]

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

# 1-to-1 Cross-Standard Equivalence Mappings
VRM_1_0_BONE_MAP: Dict[str, str] = {
    "Hips": "hips",
    "Spine": "spine",
    "Spine1": "chest",
    "Spine2": "upperChest",
    "Neck": "neck",
    "Head": "head",
    "Clavicle.L": "leftShoulder",
    "Clavicle.R": "rightShoulder",
    "UpperArm.L": "leftUpperArm",
    "UpperArm.R": "rightUpperArm",
    "ForeArm.L": "leftLowerArm",
    "ForeArm.R": "rightLowerArm",
    "Hand.L": "leftHand",
    "Hand.R": "rightHand",
    "Thigh.L": "leftUpperLeg",
    "Thigh.R": "rightUpperLeg",
    "Shin.L": "leftLowerLeg",
    "Shin.R": "rightLowerLeg",
    "Foot.L": "leftFoot",
    "Foot.R": "rightFoot",
    "Toe.L": "leftToes",
    "Toe.R": "rightToes",
    # Fingers Left
    "Thumb.01.L": "leftThumbMetacarpal",
    "Thumb.02.L": "leftThumbProximal",
    "Thumb.03.L": "leftThumbDistal",
    "Index.01.L": "leftIndexProximal",
    "Index.02.L": "leftIndexIntermediate",
    "Index.03.L": "leftIndexDistal",
    "Middle.01.L": "leftMiddleProximal",
    "Middle.02.L": "leftMiddleIntermediate",
    "Middle.03.L": "leftMiddleDistal",
    "Ring.01.L": "leftRingProximal",
    "Ring.02.L": "leftRingIntermediate",
    "Ring.03.L": "leftRingDistal",
    "Pinky.01.L": "leftLittleProximal",
    "Pinky.02.L": "leftLittleIntermediate",
    "Pinky.03.L": "leftLittleDistal",
    # Fingers Right
    "Thumb.01.R": "rightThumbMetacarpal",
    "Thumb.02.R": "rightThumbProximal",
    "Thumb.03.R": "rightThumbDistal",
    "Index.01.R": "rightIndexProximal",
    "Index.02.R": "rightIndexIntermediate",
    "Index.03.R": "rightIndexDistal",
    "Middle.01.R": "rightMiddleProximal",
    "Middle.02.R": "rightMiddleIntermediate",
    "Middle.03.R": "rightMiddleDistal",
    "Ring.01.R": "rightRingProximal",
    "Ring.02.R": "rightRingIntermediate",
    "Ring.03.R": "rightRingDistal",
    "Pinky.01.R": "rightLittleProximal",
    "Pinky.02.R": "rightLittleIntermediate",
    "Pinky.03.R": "rightLittleDistal",
}

RIGIFY_DEF_BONE_MAP: Dict[str, str] = {
    "Hips": "DEF-spine",
    "Spine": "DEF-spine.001",
    "Spine1": "DEF-spine.002",
    "Spine2": "DEF-spine.003",
    "Neck": "DEF-spine.004",
    "Head": "DEF-head",
    "Clavicle.L": "DEF-shoulder.L",
    "Clavicle.R": "DEF-shoulder.R",
    "UpperArm.L": "DEF-upper_arm.L",
    "UpperArm.R": "DEF-upper_arm.R",
    "UpperArm_Twist.L": "DEF-upper_arm.L.001",
    "UpperArm_Twist.R": "DEF-upper_arm.R.001",
    "ForeArm.L": "DEF-forearm.L",
    "ForeArm.R": "DEF-forearm.R",
    "ForeArm_Twist.L": "DEF-forearm.L.001",
    "ForeArm_Twist.R": "DEF-forearm.R.001",
    "Hand.L": "DEF-hand.L",
    "Hand.R": "DEF-hand.R",
    "Thigh.L": "DEF-thigh.L",
    "Thigh.R": "DEF-thigh.R",
    "Shin.L": "DEF-shin.L",
    "Shin.R": "DEF-shin.R",
    "Foot.L": "DEF-foot.L",
    "Foot.R": "DEF-foot.R",
    "Toe.L": "DEF-toe.L",
    "Toe.R": "DEF-toe.R",
}
for side in ["L", "R"]:
    for finger in ["Index", "Middle", "Ring", "Pinky"]:
        f_key = (
            "f_index" if finger == "Index"
            else ("f_middle" if finger == "Middle"
            else ("f_ring" if finger == "Ring" else "f_pinky"))
        )
        for ph in PHALANGES:
            RIGIFY_DEF_BONE_MAP[f"{finger}.{ph}.{side}"] = f"DEF-{f_key}.{ph}.{side}"
    for ph in PHALANGES:
        RIGIFY_DEF_BONE_MAP[f"Thumb.{ph}.{side}"] = f"DEF-thumb.{ph}.{side}"

MMD_BONE_MAP: Dict[str, str] = {
    "Hips": "下半身",
    "Spine": "上半身",
    "Spine1": "上半身2",
    "Spine2": "上半身3",
    "Neck": "首",
    "Head": "頭",
    "Clavicle.L": "左肩",
    "Clavicle.R": "右肩",
    "UpperArm.L": "左腕",
    "UpperArm.R": "右腕",
    "UpperArm_Twist.L": "左腕捩",
    "UpperArm_Twist.R": "右腕捩",
    "ForeArm.L": "左ひじ",
    "ForeArm.R": "右ひじ",
    "ForeArm_Twist.L": "左手捩",
    "ForeArm_Twist.R": "右手捩",
    "Hand.L": "左手首",
    "Hand.R": "右手首",
    "Thigh.L": "左足",
    "Thigh.R": "右足",
    "Shin.L": "左ひざ",
    "Shin.R": "右ひざ",
    "Foot.L": "左足首",
    "Foot.R": "右足首",
    "Toe.L": "左つま先",
    "Toe.R": "右つま先",
}


# ==============================================================================
# 2. Pure-Python Compatible Data Structures
# ==============================================================================

@dataclass
class BoneSpec:
    """Specification of a single bone in the humanoid armature."""
    name: str
    parent: Optional[str]
    head: Tuple[float, float, float]
    tail: Tuple[float, float, float]
    roll: float = 0.0
    use_connect: bool = False
    constraints: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ArmatureSpec:
    """Specification of the entire Anime_Armature."""
    name: str = "Anime_Armature"
    bones: Dict[str, BoneSpec] = field(default_factory=dict)
    use_deform_preserve_volume: bool = True

    @property
    def total_bones(self) -> int:
        return len(self.bones)


# ==============================================================================
# 3. Armature Builder Implementation
# ==============================================================================

class ArmatureBuilder:
    """
    Constructs the canonical 78-bone Anime_Armature.
    Features:
    - 6-bone spine chain (Hips -> Spine -> Spine1 -> Spine2 -> Neck -> Head).
    - Bilateral limbs (Clavicles, UpperArms, ForeArms, Hands, Thighs, Shins, Feet, Toes).
    - 4 Twist bones with 0.5 local Y copy-rotation constraints.
    - 30 Articulated finger phalanges with palmar bone roll alignment for pure +X flexion.
    - 12-radial skirt spoke bones parented to Hips with [-15°, +65°] pitch limits.
    - 10-bone twintail secondary chains with calibrated spring dynamics.
    - Dynamic landmark scaling from 1.45m to 1.75m.
    """

    def __init__(
        self,
        height: float = 1.650,
        ground_sole_z: float = 0.000,
        submeshes: Optional[Dict[str, Any]] = None,
        landmarks: Optional[Dict[str, Tuple[float, float, float]]] = None,
    ):
        self.target_height = height
        self.ground_sole_z = ground_sole_z
        self.submeshes = submeshes or {}
        self.landmarks = landmarks or {}
        self.scale_factor = self._compute_scale_factor()
        self.resolved_landmarks = self._resolve_landmarks()

    def _compute_scale_factor(self) -> float:
        """Derives scaling factor from submesh bounds or target height."""
        if self.submeshes:
            all_zs: List[float] = []
            for _, mesh in self.submeshes.items():
                if hasattr(mesh, "vertices"):
                    if mesh.vertices and hasattr(mesh.vertices[0], "co"):
                        all_zs.extend(v.co.z for v in mesh.vertices)
                    elif mesh.vertices and isinstance(mesh.vertices[0], (list, tuple)):
                        all_zs.extend(v[2] for v in mesh.vertices)
                elif isinstance(mesh, list) and mesh and len(mesh[0]) == 3:
                    all_zs.extend(v[2] for v in mesh)
            if all_zs:
                min_z = min(all_zs)
                max_z = max(all_zs)
                span = max_z - min_z
                if 1.40 <= span <= 1.80:
                    self.target_height = span
                    self.ground_sole_z = min_z
                    return span / 1.650

        return max(1.45, min(1.75, self.target_height)) / 1.650

    def _resolve_landmarks(self) -> Dict[str, Tuple[float, float, float]]:
        """
        Calculates authoritative 3D joint landmarks scaled to target height.
        Based on canonical anime anatomical proportions and verified M1 coordinates.
        """
        s = self.scale_factor
        gz = self.ground_sole_z

        base_lm: Dict[str, Tuple[float, float, float]] = {
            # Spine & Head chain
            "Hips": (0.0, -0.01431 * s, 0.88096 * s + gz),
            "Spine": (0.0, 0.00953 * s, 0.92652 * s + gz),
            "Spine1": (0.0, -0.02570 * s, 1.08597 * s + gz),
            "Spine2": (0.0, 0.00706 * s, 1.23770 * s + gz),
            "Neck": (0.0, -0.00674 * s, 1.39238 * s + gz),
            "Head": (0.0, -0.01592 * s, 1.49981 * s + gz),
            "Head_Top": (0.0, -0.00817 * s, 1.64139 * s + gz),

            # Left Arm (Canonical Left = +X or MakeHuman standard)
            # Note: In Blender standard anatomical coordinates, Left arm has X > 0
            "Clavicle.L": (0.02630 * s, -0.06876 * s, 1.32315 * s + gz),
            "UpperArm.L": (0.16611 * s, -0.01447 * s, 1.32855 * s + gz),
            "ForeArm.L": (0.30995 * s, -0.01308 * s, 1.15496 * s + gz),
            "Hand.L": (0.42707 * s, -0.17398 * s, 1.05181 * s + gz),
            "Palm.L": (0.43550 * s, -0.18575 * s, 1.01439 * s + gz),

            # Right Arm (Mirrored X < 0)
            "Clavicle.R": (-0.02630 * s, -0.06876 * s, 1.32315 * s + gz),
            "UpperArm.R": (-0.16611 * s, -0.01447 * s, 1.32855 * s + gz),
            "ForeArm.R": (-0.30995 * s, -0.01308 * s, 1.15496 * s + gz),
            "Hand.R": (-0.42707 * s, -0.17398 * s, 1.05181 * s + gz),
            "Palm.R": (-0.43550 * s, -0.18575 * s, 1.01439 * s + gz),

            # Left Leg
            "Thigh.L": (0.10931 * s, -0.01218 * s, 0.85712 * s + gz),
            "Shin.L": (0.15661 * s, -0.03172 * s, 0.44301 * s + gz),
            "Foot.L": (0.21753 * s, 0.00090 * s, 0.07129 * s + gz),
            "Toe.L": (0.21776 * s, -0.11969 * s, 0.00655 * s + gz),
            "Toe_Tip.L": (0.21774 * s, -0.20116 * s, 0.01402 * s + gz),

            # Right Leg
            "Thigh.R": (-0.10931 * s, -0.01218 * s, 0.85712 * s + gz),
            "Shin.R": (-0.15661 * s, -0.03172 * s, 0.44301 * s + gz),
            "Foot.R": (-0.21753 * s, 0.00090 * s, 0.07129 * s + gz),
            "Toe.R": (-0.21776 * s, -0.11969 * s, 0.00655 * s + gz),
            "Toe_Tip.R": (-0.21774 * s, -0.20116 * s, 0.01402 * s + gz),
        }

        # 30 Articulated Finger Phalange joint coordinates
        finger_coords_L = {
            "Thumb": [
                (0.41551 * s, -0.21140 * s, 1.03735 * s + gz),
                (0.40558 * s, -0.23507 * s, 1.03239 * s + gz),
                (0.39458 * s, -0.26566 * s, 1.01792 * s + gz),
                (0.38794 * s, -0.28486 * s, 1.00707 * s + gz),
            ],
            "Index": [
                (0.44527 * s, -0.26189 * s, 1.01006 * s + gz),
                (0.44883 * s, -0.28266 * s, 0.99668 * s + gz),
                (0.44906 * s, -0.29947 * s, 0.98184 * s + gz),
                (0.44864 * s, -0.31638 * s, 0.96636 * s + gz),
            ],
            "Middle": [
                (0.45643 * s, -0.24553 * s, 0.99579 * s + gz),
                (0.46675 * s, -0.26651 * s, 0.97461 * s + gz),
                (0.47015 * s, -0.28286 * s, 0.95637 * s + gz),
                (0.47385 * s, -0.29859 * s, 0.93800 * s + gz),
            ],
            "Ring": [
                (0.46516 * s, -0.22874 * s, 0.98973 * s + gz),
                (0.47655 * s, -0.24377 * s, 0.96917 * s + gz),
                (0.48128 * s, -0.25672 * s, 0.95018 * s + gz),
                (0.48685 * s, -0.26908 * s, 0.93008 * s + gz),
            ],
            "Pinky": [
                (0.47001 * s, -0.21036 * s, 0.98366 * s + gz),
                (0.47612 * s, -0.22000 * s, 0.96566 * s + gz),
                (0.47838 * s, -0.22596 * s, 0.95312 * s + gz),
                (0.48105 * s, -0.23303 * s, 0.93667 * s + gz),
            ],
        }

        for f_name, pts in finger_coords_L.items():
            for idx, pt in enumerate(pts):
                base_lm[f"{f_name}_{idx+1}.L"] = pt
                base_lm[f"{f_name}_{idx+1}.R"] = (-pt[0], pt[1], pt[2])

        return base_lm

    def generate_armature_spec(self) -> ArmatureSpec:
        """Constructs a pure-Python ArmatureSpec containing all 78 required bones."""
        spec = ArmatureSpec(name="Anime_Armature", use_deform_preserve_volume=True)
        lm = self.resolved_landmarks
        s = self.scale_factor
        gz = self.ground_sole_z

        # 1. Spine chain (Hips root -> Spine -> Spine1 -> Spine2 -> Neck -> Head)
        spec.bones["Hips"] = BoneSpec("Hips", None, lm["Hips"], lm["Spine"])
        spec.bones["Spine"] = BoneSpec("Spine", "Hips", lm["Spine"], lm["Spine1"], use_connect=True)
        spec.bones["Spine1"] = BoneSpec("Spine1", "Spine", lm["Spine1"], lm["Spine2"], use_connect=True)
        spec.bones["Spine2"] = BoneSpec("Spine2", "Spine1", lm["Spine2"], lm["Neck"], use_connect=True)
        spec.bones["Neck"] = BoneSpec("Neck", "Spine2", lm["Neck"], lm["Head"], use_connect=True)
        spec.bones["Head"] = BoneSpec("Head", "Neck", lm["Head"], lm["Head_Top"], use_connect=True)

        # 2. Limbs, Twist bones, Fingers (Bilateral L & R)
        for side in ["L", "R"]:
            clav_head = lm[f"Clavicle.{side}"]
            shoulder = lm[f"UpperArm.{side}"]
            elbow = lm[f"ForeArm.{side}"]
            wrist = lm[f"Hand.{side}"]

            spec.bones[f"Clavicle.{side}"] = BoneSpec(f"Clavicle.{side}", "Spine2", clav_head, shoulder)
            spec.bones[f"UpperArm.{side}"] = BoneSpec(f"UpperArm.{side}", f"Clavicle.{side}", shoulder, elbow)

            # UpperArm Twist (mid-way along upper arm, copy-rotation Y 0.5)
            mid_upper = (
                (shoulder[0] + elbow[0]) * 0.5,
                (shoulder[1] + elbow[1]) * 0.5,
                (shoulder[2] + elbow[2]) * 0.5,
            )
            spec.bones[f"UpperArm_Twist.{side}"] = BoneSpec(
                f"UpperArm_Twist.{side}", f"UpperArm.{side}", mid_upper, elbow,
                constraints=[{"type": "COPY_ROTATION", "target": f"UpperArm.{side}", "factor": 0.5, "axis": "Y"}]
            )

            spec.bones[f"ForeArm.{side}"] = BoneSpec(f"ForeArm.{side}", f"UpperArm.{side}", elbow, wrist, use_connect=True)

            # ForeArm Twist (mid-way along forearm, copy-rotation Y 0.5 targeting Hand)
            mid_forearm = (
                (elbow[0] + wrist[0]) * 0.5,
                (elbow[1] + wrist[1]) * 0.5,
                (elbow[2] + wrist[2]) * 0.5,
            )
            spec.bones[f"ForeArm_Twist.{side}"] = BoneSpec(
                f"ForeArm_Twist.{side}", f"ForeArm.{side}", mid_forearm, wrist,
                constraints=[{"type": "COPY_ROTATION", "target": f"Hand.{side}", "factor": 0.5, "axis": "Y"}]
            )

            # Hand bone
            middle_mcp = lm[f"Middle_1.{side}"]
            spec.bones[f"Hand.{side}"] = BoneSpec(f"Hand.{side}", f"ForeArm.{side}", wrist, middle_mcp, use_connect=True)

            # 30 Articulated Fingers (15 L + 15 R)
            for finger in FINGER_NAMES:
                parent = f"Hand.{side}"
                for i, ph in enumerate(PHALANGES):
                    bname = f"{finger}.{ph}.{side}"
                    h = lm[f"{finger}_{i+1}.{side}"]
                    t = lm[f"{finger}_{i+2}.{side}"]
                    spec.bones[bname] = BoneSpec(bname, parent, h, t, use_connect=(i > 0))
                    parent = bname

            # Legs
            thigh = lm[f"Thigh.{side}"]
            knee = lm[f"Shin.{side}"]
            ankle = lm[f"Foot.{side}"]
            toe_ball = lm[f"Toe.{side}"]
            toe_tip = lm[f"Toe_Tip.{side}"]

            spec.bones[f"Thigh.{side}"] = BoneSpec(f"Thigh.{side}", "Hips", thigh, knee)
            spec.bones[f"Shin.{side}"] = BoneSpec(f"Shin.{side}", f"Thigh.{side}", knee, ankle, use_connect=True)
            spec.bones[f"Foot.{side}"] = BoneSpec(f"Foot.{side}", f"Shin.{side}", ankle, toe_ball)
            spec.bones[f"Toe.{side}"] = BoneSpec(f"Toe.{side}", f"Foot.{side}", toe_ball, toe_tip, use_connect=True)

        # 3. 12-Radial Skirt Spoke Bones parented to Hips with [-15°, +65°] pitch limits
        waist_z = 0.880 * s + gz
        hem_z = 0.540 * s + gz
        rx = 0.180 * s
        ry = 0.140 * s
        for i in range(1, 13):
            ang = (i - 1) * (2.0 * math.pi / 12.0)
            hx = rx * math.cos(ang)
            hy = -0.016 * s + ry * math.sin(ang)
            tx = (rx + 0.110 * s) * math.cos(ang)
            ty = -0.016 * s + (ry + 0.090 * s) * math.sin(ang)
            bname = f"Skirt_{i:02d}"
            spec.bones[bname] = BoneSpec(
                bname, "Hips", (hx, hy, waist_z), (tx, ty, hem_z),
                constraints=[{"type": "LIMIT_ROTATION", "min_pitch": -15.0, "max_pitch": 65.0}]
            )

        # 4. 10 Hair Twintail Bones (5 Left + 5 Right) parented to Head
        for side in ["L", "R"]:
            sign = 1.0 if side == "L" else -1.0
            parent = "Head"
            for i in range(1, 6):
                bname = f"Hair_{side}_{i:02d}"
                hz = (1.530 - (i - 1) * 0.075) * s + gz
                tz = (1.530 - i * 0.075) * s + gz
                hx = sign * (0.090 + (i - 1) * 0.015) * s
                tx = sign * (0.090 + i * 0.015) * s
                hy = -0.020 * s
                ty = -0.020 * s
                spec.bones[bname] = BoneSpec(
                    bname, parent, (hx, hy, hz), (tx, ty, tz), use_connect=(i > 1),
                    constraints=[{"type": "SPRING_DYNAMICS", "stiffness": 150.0, "damping": 12.0, "mass": 0.2}]
                )
                parent = bname

        return spec

    def build_in_blender(self, target_collection: Optional[str] = "Anime_Character_Meshes") -> Any:
        """
        Builds the live Armature Object in Blender 4.5+ LTS.
        Applies anatomical bone rolls and attaches constraints.
        """
        if not HAS_BPY:
            raise RuntimeError("Blender Python (bpy) is not available in current execution context.")

        spec = self.generate_armature_spec()

        # Remove existing armature object if already present
        if "Anime_Armature" in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects["Anime_Armature"], do_unlink=True)
        if "Anime_Armature" in bpy.data.armatures:
            bpy.data.armatures.remove(bpy.data.armatures["Anime_Armature"], do_unlink=True)

        arm_data = bpy.data.armatures.new(name="Anime_Armature")
        arm_data.display_type = 'OCTAHEDRAL'
        arm_data.show_axes = True

        arm_obj = bpy.data.objects.new(name="Anime_Armature", object_data=arm_data)
        arm_obj.show_in_front = True

        col = bpy.data.collections.get(target_collection) if target_collection else None
        if not col:
            col = bpy.context.scene.collection
        col.objects.link(arm_obj)

        bpy.context.view_layer.objects.active = arm_obj
        bpy.ops.object.mode_set(mode='EDIT')
        eb = arm_data.edit_bones

        # 1. Create Edit Bones
        created_bones: Dict[str, Any] = {}
        for bname, bspec in spec.bones.items():
            b = eb.new(bname)
            b.head = Vector(bspec.head)
            b.tail = Vector(bspec.tail)
            b.use_deform = True
            created_bones[bname] = b

        # 2. Parenting & Connection
        for bname, bspec in spec.bones.items():
            if bspec.parent and bspec.parent in created_bones:
                b = created_bones[bname]
                b.parent = created_bones[bspec.parent]
                if bspec.use_connect:
                    dist = (b.parent.tail - b.head).length
                    if dist < 1e-4:
                        b.use_connect = True

        # 3. Anatomical Bone Rolls
        # F05: Segment cross-product flexion normal bone roll so positive local X curls fingers toward palm
        lm = self.resolved_landmarks
        for side in ["L", "R"]:
            sign = 1.0 if side == "L" else -1.0
            palm = Vector(lm[f"Palm.{side}"])

            hand_b = created_bones.get(f"Hand.{side}")
            if hand_b:
                to_palm = (palm - hand_b.head).normalized()
                v_axis = (hand_b.tail - hand_b.head).normalized()
                p_norm = (to_palm - to_palm.dot(v_axis) * v_axis).normalized()
                hand_b.align_roll(p_norm)

            for finger in FINGER_NAMES:
                for k in range(3):
                    bname = f"{finger}.0{k+1}.{side}"
                    fb = created_bones.get(bname)
                    if fb:
                        v_bone = (fb.tail - fb.head).normalized()
                        to_p = (palm - fb.head).normalized()
                        palmar_norm = (to_p - to_p.dot(v_bone) * v_bone).normalized()
                        fb.align_roll(palmar_norm)

        # Standard rolls for spine, limbs, skirt, hair
        for bname, b in created_bones.items():
            if "Thigh" in bname or "Shin" in bname:
                b.align_roll(Vector((0.0, 1.0, 0.0)))
            elif "Foot" in bname or "Toe" in bname:
                b.align_roll(Vector((0.0, 0.0, 1.0)))
            elif "Spine" in bname or "Neck" in bname or "Head" in bname:
                b.align_roll(Vector((0.0, 1.0, 0.0)))
            elif bname.startswith("Skirt_"):
                idx = int(bname.split("_")[1]) - 1
                ang = idx * (2.0 * math.pi / 12.0)
                tangent = Vector((-math.sin(ang), math.cos(ang), 0.0))
                b.align_roll(tangent)
            elif bname.startswith("Hair_"):
                side_sign = 1.0 if "_L_" in bname else -1.0
                b.align_roll(Vector((side_sign, 0.0, 0.0)))

        # 4. Pose Mode Constraints
        bpy.ops.object.mode_set(mode='POSE')
        pb = arm_obj.pose.bones

        # F06: Twist bones (0.5 local Y copy-rotation)
        for side in ["L", "R"]:
            twist_up = pb.get(f"UpperArm_Twist.{side}")
            up_arm = f"UpperArm.{side}"
            if twist_up and up_arm in pb:
                c = twist_up.constraints.new(type='COPY_ROTATION')
                c.name = "UpperArm_Twist_Distribution"
                c.target = arm_obj
                c.subtarget = up_arm
                c.target_space = 'LOCAL'
                c.owner_space = 'LOCAL'
                c.use_x = False
                c.use_y = True
                c.use_z = False
                c.influence = 0.50

            twist_fore = pb.get(f"ForeArm_Twist.{side}")
            hand_name = f"Hand.{side}"
            if twist_fore and hand_name in pb:
                c = twist_fore.constraints.new(type='COPY_ROTATION')
                c.name = "ForeArm_Twist_AntiPinch"
                c.target = arm_obj
                c.subtarget = hand_name
                c.target_space = 'LOCAL'
                c.owner_space = 'LOCAL'
                c.use_x = False
                c.use_y = True
                c.use_z = False
                c.influence = 0.50

        # F07: Skirt pitch limit constraints [-15°, +65°]
        for bname in SKIRT_BONES:
            skirt_p = pb.get(bname)
            if skirt_p:
                lim = skirt_p.constraints.new(type='LIMIT_ROTATION')
                lim.name = "Skirt_Pitch_Clamp"
                lim.owner_space = 'LOCAL'
                lim.use_limit_x = True
                lim.min_x = math.radians(-15.0)
                lim.max_x = math.radians(65.0)
                lim.use_limit_y = False
                lim.use_limit_z = False
                lim.influence = 1.0
                skirt_p["min_pitch"] = -15.0
                skirt_p["max_pitch"] = 65.0
                skirt_p["is_secondary_skirt"] = True

        # F08: Twintail hair spring parameters
        for bname in ALL_10_HAIR_BONES:
            hair_p = pb.get(bname)
            if hair_p:
                hair_p["spring_stiffness"] = 150.0
                hair_p["spring_damping"] = 12.0
                hair_p["spring_mass"] = 0.20
                hair_p["spring_rest_pos"] = 0.0
                hair_p["is_secondary_hair"] = True

        # Store cross-standard mapping metadata on the Armature data block
        arm_data["vrm_1_0_bone_map"] = VRM_1_0_BONE_MAP
        arm_data["rigify_def_bone_map"] = RIGIFY_DEF_BONE_MAP
        arm_data["mmd_bone_map"] = MMD_BONE_MAP

        bpy.ops.object.mode_set(mode='OBJECT')
        return arm_obj


def build_anime_armature(
    height: float = 1.650,
    submeshes: Optional[Dict[str, Any]] = None,
    output_blend: Optional[Union[str, Path]] = None,
) -> Any:
    """Master entry point to build Anime_Armature."""
    builder = ArmatureBuilder(height=height, submeshes=submeshes)
    if HAS_BPY:
        arm_obj = builder.build_in_blender()
        if output_blend:
            bpy.ops.wm.save_as_mainfile(filepath=str(output_blend))
        return arm_obj
    else:
        return builder.generate_armature_spec()
