"""
anime_pipeline/animation/retargeting_limits.py
Milestone 3 Feature F12: Joint Rotational Clamping & Retargeting Limits.

Authoritative specification:
- Programmatic attachment of LIMIT_ROTATION bone constraints on pose bones in Pose Mode (owner_space = 'LOCAL'):
    * ForeArms (ForeArm.L, ForeArm.R): Local X flexion clamped strictly to [0°, 145°] (pure hinge, zero hyper-extension);
      local Y twist clamped to [-15°, +15°] (twist handled by twist bones); local Z deviation clamped to [-5°, +5°].
    * Knees (Shin.L, Shin.R): Local X flexion clamped strictly to [0°, 140°] (backward flexion only, zero front hyperextension);
      local Y & Z clamped to [-3°, +3°] (prevents grotesque valgus collapse or inward dislocation).
    * Feet (Foot.L, Foot.R): Pitch clamped to [-45°, +30°], roll clamped to [-8°, +8°] (keeps shoe sole stable on ground),
      yaw clamped to [-10°, +10°].
    * Toes (Toe.L, Toe.R): Pitch clamped to [-5°, +45°] (natural toe-off flexion), roll/yaw clamped to [-2°, +2°].
    * Shoulders & Spine: Bounded ranges preventing torso inversion or clavicle tearing.
- Retargeting Pose Sanitizer:
    * Pure-Python function clamp_pose_rotations(bone_rotations) that takes arbitrary raw mocap/quaternion/Euler rotations
      and clamps them mathematically to physiological limits before keyframing.
- Cross-Standard Retargeting Mapping Table:
    * Complete bidirectional mapping dictionary for VRM 1.0 Humanoid, MMD, Rigify, and Mixamo bone naming conventions.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple, Union

try:
    import bpy
    import mathutils
    from mathutils import Euler, Matrix, Quaternion, Vector
    HAS_BPY = True
except ImportError:
    bpy = None  # type: ignore[assignment]
    mathutils = None  # type: ignore[assignment]
    HAS_BPY = False
    Vector = Any  # type: ignore[misc,assignment]
    Matrix = Any  # type: ignore[misc,assignment]
    Euler = Any  # type: ignore[misc,assignment]
    Quaternion = Any  # type: ignore[misc,assignment]


# ==============================================================================
# 1. Physiological Limit Specification Data Structures
# ==============================================================================

@dataclass(frozen=True)
class LimitSpec:
    """
    Defines 3-axis rotational boundaries in radians for a bone in local coordinate space.
    """
    min_x: float = 0.0
    max_x: float = 0.0
    use_x: bool = False

    min_y: float = 0.0
    max_y: float = 0.0
    use_y: bool = False

    min_z: float = 0.0
    max_z: float = 0.0
    use_z: bool = False

    description: str = ""

    @classmethod
    def from_degrees(
        cls,
        x: Optional[Tuple[float, float]] = None,
        y: Optional[Tuple[float, float]] = None,
        z: Optional[Tuple[float, float]] = None,
        description: str = "",
    ) -> "LimitSpec":
        """Convenience constructor accepting angle bounds in degrees."""
        use_x = x is not None
        min_x = math.radians(x[0]) if use_x else 0.0
        max_x = math.radians(x[1]) if use_x else 0.0

        use_y = y is not None
        min_y = math.radians(y[0]) if use_y else 0.0
        max_y = math.radians(y[1]) if use_y else 0.0

        use_z = z is not None
        min_z = math.radians(z[0]) if use_z else 0.0
        max_z = math.radians(z[1]) if use_z else 0.0

        return cls(
            min_x=min_x, max_x=max_x, use_x=use_x,
            min_y=min_y, max_y=max_y, use_y=use_y,
            min_z=min_z, max_z=max_z, use_z=use_z,
            description=description,
        )

    def to_dict_rad(self) -> Dict[str, Any]:
        """Exports limit dictionary formatted for Blender's LIMIT_ROTATION constraint."""
        return {
            "use_limit_x": self.use_x,
            "min_x": self.min_x,
            "max_x": self.max_x,
            "use_limit_y": self.use_y,
            "min_y": self.min_y,
            "max_y": self.max_y,
            "use_limit_z": self.use_z,
            "min_z": self.min_z,
            "max_z": self.max_z,
        }

    def to_dict_deg(self) -> Dict[str, Any]:
        """Exports limit dictionary formatted in degrees for debugging/logging."""
        return {
            "x": (round(math.degrees(self.min_x), 2), round(math.degrees(self.max_x), 2)) if self.use_x else None,
            "y": (round(math.degrees(self.min_y), 2), round(math.degrees(self.max_y), 2)) if self.use_y else None,
            "z": (round(math.degrees(self.min_z), 2), round(math.degrees(self.max_z), 2)) if self.use_z else None,
            "desc": self.description,
        }


# ==============================================================================
# 2. Authoritative Physiological Limits Clamping Matrix
# ==============================================================================

PHYSIOLOGICAL_ROTATION_LIMITS: Dict[str, LimitSpec] = {
    # --------------------------------------------------------------------------
    # Forearms / Elbows: Pure hinge flexion, zero hyperextension, clamped twist
    # --------------------------------------------------------------------------
    "ForeArm.L": LimitSpec.from_degrees(
        x=(0.0, 145.0),    # Pure hinge flexion, strictly zero hyperextension
        y=(-15.0, 15.0),   # Clamped axial twist (bulk absorbed by ForeArm_Twist)
        z=(-5.0, 5.0),     # Zero sideways dislocation
        description="Left Elbow Hinge Clamp [0°, 145°]",
    ),
    "ForeArm.R": LimitSpec.from_degrees(
        x=(0.0, 145.0),
        y=(-15.0, 15.0),
        z=(-5.0, 5.0),
        description="Right Elbow Hinge Clamp [0°, 145°]",
    ),

    # --------------------------------------------------------------------------
    # Knees / Shins: Backward flexion only, zero front hyperextension, anti-valgus
    # --------------------------------------------------------------------------
    "Shin.L": LimitSpec.from_degrees(
        x=(0.0, 140.0),    # Backward knee flexion only, zero front hyperextension
        y=(-3.0, 3.0),     # Anti-valgus collapse
        z=(-3.0, 3.0),     # Anti-sideways dislocation
        description="Left Knee Hinge Clamp [0°, 140°] with Anti-Valgus",
    ),
    "Shin.R": LimitSpec.from_degrees(
        x=(0.0, 140.0),
        y=(-3.0, 3.0),
        z=(-3.0, 3.0),
        description="Right Knee Hinge Clamp [0°, 140°] with Anti-Valgus",
    ),

    # --------------------------------------------------------------------------
    # Feet / Ankles: Ground sole leveling & natural plantar/dorsiflexion
    # --------------------------------------------------------------------------
    "Foot.L": LimitSpec.from_degrees(
        x=(-45.0, 30.0),   # Plantarflexion (-45°) to dorsiflexion (+30°)
        y=(-8.0, 8.0),     # Sole flat stability against floor roll
        z=(-10.0, 10.0),   # Ankle yaw / in-turning bound
        description="Left Ankle / Foot Pitch & Sole Stability",
    ),
    "Foot.R": LimitSpec.from_degrees(
        x=(-45.0, 30.0),
        y=(-8.0, 8.0),
        z=(-10.0, 10.0),
        description="Right Ankle / Foot Pitch & Sole Stability",
    ),

    # --------------------------------------------------------------------------
    # Toes: Natural toe-off flexion during locomotion
    # --------------------------------------------------------------------------
    "Toe.L": LimitSpec.from_degrees(
        x=(-5.0, 45.0),    # Step toe-off upward flexion
        y=(-2.0, 2.0),     # Anti-roll twist
        z=(-2.0, 2.0),     # Anti-sideways splay
        description="Left Toe-Off Flexion [-5°, +45°]",
    ),
    "Toe.R": LimitSpec.from_degrees(
        x=(-5.0, 45.0),
        y=(-2.0, 2.0),
        z=(-2.0, 2.0),
        description="Right Toe-Off Flexion [-5°, +45°]",
    ),

    # --------------------------------------------------------------------------
    # Shoulders / Clavicles: Prevents clavicle tearing and neck penetration
    # --------------------------------------------------------------------------
    "Clavicle.L": LimitSpec.from_degrees(
        x=(-15.0, 25.0),   # Shrug elevation / depression
        y=(-5.0, 5.0),     # Axial twist
        z=(-15.0, 15.0),   # Protraction / retraction
        description="Left Clavicle Bounded Range",
    ),
    "Clavicle.R": LimitSpec.from_degrees(
        x=(-15.0, 25.0),
        y=(-5.0, 5.0),
        z=(-15.0, 15.0),
        description="Right Clavicle Bounded Range",
    ),

    # --------------------------------------------------------------------------
    # Upper Arms: Ball-joint envelope preventing unnatural shoulder dislocation
    # --------------------------------------------------------------------------
    "UpperArm.L": LimitSpec.from_degrees(
        x=(-60.0, 160.0),  # Forward / backward pitch reach
        y=(-30.0, 30.0),   # Twist (UpperArm_Twist absorbs 50%)
        z=(-45.0, 115.0),  # Abduction / adduction
        description="Left Upper Arm Ball-Joint Bounded Range",
    ),
    "UpperArm.R": LimitSpec.from_degrees(
        x=(-60.0, 160.0),
        y=(-30.0, 30.0),
        z=(-45.0, 115.0),
        description="Right Upper Arm Ball-Joint Bounded Range",
    ),

    # --------------------------------------------------------------------------
    # Thighs / Upper Legs: Hip joint envelope preventing torso clipping
    # --------------------------------------------------------------------------
    "Thigh.L": LimitSpec.from_degrees(
        x=(-30.0, 110.0),  # Extension backward (-30°) to high kick (+110°)
        y=(-15.0, 15.0),   # Thigh axial rotation
        z=(-25.0, 45.0),   # Inward adduction to outward abduction
        description="Left Hip Ball-Joint Bounded Range",
    ),
    "Thigh.R": LimitSpec.from_degrees(
        x=(-30.0, 110.0),
        y=(-15.0, 15.0),
        z=(-25.0, 45.0),
        description="Right Hip Ball-Joint Bounded Range",
    ),

    # --------------------------------------------------------------------------
    # Spine Chain: Prevents grotesque torso inversion and unnatural snake-bending
    # --------------------------------------------------------------------------
    "Spine": LimitSpec.from_degrees(
        x=(-15.0, 30.0),   # Lumbar extension (-15°) to flexion (+30°)
        y=(-15.0, 15.0),   # Lumbar twist
        z=(-12.0, 12.0),   # Lateral tilt
        description="Lumbar Spine Flexion & Tilt Clamp",
    ),
    "Spine1": LimitSpec.from_degrees(
        x=(-15.0, 20.0),   # Thoracic breathing & flexion
        y=(-15.0, 15.0),   # Thoracic twist
        z=(-10.0, 10.0),   # Thoracic lateral tilt
        description="Thoracic Spine1 (Chest) Clamp",
    ),
    "Spine2": LimitSpec.from_degrees(
        x=(-10.0, 15.0),   # Upper chest flexion
        y=(-10.0, 10.0),   # Upper chest twist
        z=(-8.0, 8.0),     # Upper chest tilt
        description="Upper Thoracic Spine2 Clamp",
    ),
    "Neck": LimitSpec.from_degrees(
        x=(-25.0, 25.0),   # Pitch (nodding forward/backward)
        y=(-35.0, 35.0),   # Neck twist / look side
        z=(-20.0, 20.0),   # Lateral tilt
        description="Neck Articulation Clamp",
    ),
    "Head": LimitSpec.from_degrees(
        x=(-35.0, 30.0),   # Gaze pitch (look down/up)
        y=(-45.0, 45.0),   # Head turn (yaw)
        z=(-25.0, 25.0),   # Aesthetic anime tilt (roll)
        description="Head Gaze & Anime Tilt Clamp",
    ),

    # --------------------------------------------------------------------------
    # Wrists / Hands: Prevents candy-wrapper collapse
    # --------------------------------------------------------------------------
    "Hand.L": LimitSpec.from_degrees(
        x=(-50.0, 50.0),   # Wrist flexion / extension
        y=(-20.0, 20.0),   # Wrist twist (ForeArm_Twist handles bulk)
        z=(-30.0, 25.0),   # Radial / ulnar deviation
        description="Left Wrist Flexion & Deviation Clamp",
    ),
    "Hand.R": LimitSpec.from_degrees(
        x=(-50.0, 50.0),
        y=(-20.0, 20.0),
        z=(-30.0, 25.0),
        description="Right Wrist Flexion & Deviation Clamp",
    ),
}

# Add 30 Articulated Finger Phalange Limits (Pure +X curls toward palm)
for _side in ["L", "R"]:
    for _finger in ["Thumb", "Index", "Middle", "Ring", "Pinky"]:
        # Proximal (01)
        if _finger == "Thumb":
            PHYSIOLOGICAL_ROTATION_LIMITS[f"{_finger}.01.{_side}"] = LimitSpec.from_degrees(
                x=(-15.0, 60.0), y=(-15.0, 15.0), z=(-25.0, 35.0),
                description=f"{_side} Thumb Metacarpal Opposition Clamp",
            )
        else:
            PHYSIOLOGICAL_ROTATION_LIMITS[f"{_finger}.01.{_side}"] = LimitSpec.from_degrees(
                x=(-10.0, 90.0), y=(-5.0, 5.0), z=(-15.0, 15.0),
                description=f"{_side} {_finger} Proximal Knuckle Flexion & Splay",
            )
        # Intermediate (02) - Pure 1-DOF Hinge
        PHYSIOLOGICAL_ROTATION_LIMITS[f"{_finger}.02.{_side}"] = LimitSpec.from_degrees(
            x=(0.0, 100.0), y=(-2.0, 2.0), z=(-2.0, 2.0),
            description=f"{_side} {_finger} Intermediate Pure Hinge",
        )
        # Distal (03) - Pure 1-DOF Hinge
        PHYSIOLOGICAL_ROTATION_LIMITS[f"{_finger}.03.{_side}"] = LimitSpec.from_degrees(
            x=(0.0, 90.0), y=(-2.0, 2.0), z=(-2.0, 2.0),
            description=f"{_side} {_finger} Distal Pure Hinge",
        )


# Backward-compatible 2-element tuples for test suites (min_deg, max_deg)
HINGE_LIMITS: Dict[str, Tuple[float, float]] = {
    "Elbow.L": (0.0, 145.0),
    "Elbow.R": (0.0, 145.0),
    "Knee.L": (0.0, 140.0),
    "Knee.R": (0.0, 140.0),
    "ForeArm.L": (0.0, 145.0),
    "ForeArm.R": (0.0, 145.0),
    "Shin.L": (0.0, 140.0),
    "Shin.R": (0.0, 140.0),
    "Skirt_Pitch": (-15.0, 65.0),
}


# ==============================================================================
# 3. Cross-Standard Bone Mapping Dictionaries
# ==============================================================================

# VRM 1.0 Humanoid Specification (UniVRM / glTF)
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
    # Left Fingers
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
    # Right Fingers
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

# MMD Specification (MikuMikuDance / PMX Kanji naming)
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
    # Left Fingers
    "Thumb.01.L": "左親指０",
    "Thumb.02.L": "左親指１",
    "Thumb.03.L": "左親指２",
    "Index.01.L": "左人指１",
    "Index.02.L": "左人指２",
    "Index.03.L": "左人指３",
    "Middle.01.L": "左中指１",
    "Middle.02.L": "左中指２",
    "Middle.03.L": "左中指３",
    "Ring.01.L": "左薬指１",
    "Ring.02.L": "左薬指２",
    "Ring.03.L": "左薬指３",
    "Pinky.01.L": "左小指１",
    "Pinky.02.L": "左小指２",
    "Pinky.03.L": "左小指３",
    # Right Fingers
    "Thumb.01.R": "右親指０",
    "Thumb.02.R": "右親指１",
    "Thumb.03.R": "右親指２",
    "Index.01.R": "右人指１",
    "Index.02.R": "右人指２",
    "Index.03.R": "右人指３",
    "Middle.01.R": "右中指１",
    "Middle.02.R": "右中指２",
    "Middle.03.R": "右中指３",
    "Ring.01.R": "右薬指１",
    "Ring.02.R": "右薬指２",
    "Ring.03.R": "右薬指３",
    "Pinky.01.R": "右小指１",
    "Pinky.02.R": "右小指２",
    "Pinky.03.R": "右小指３",
}

# Rigify DEF Specification (Blender Rigify deform bone naming)
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
for _side in ["L", "R"]:
    for _finger in ["Index", "Middle", "Ring", "Pinky"]:
        _fkey = "f_" + _finger.lower()
        for _ph in ["01", "02", "03"]:
            RIGIFY_DEF_BONE_MAP[f"{_finger}.{_ph}.{_side}"] = f"DEF-{_fkey}.{_ph}.{_side}"
    for _ph in ["01", "02", "03"]:
        RIGIFY_DEF_BONE_MAP[f"Thumb.{_ph}.{_side}"] = f"DEF-thumb.{_ph}.{_side}"

# Adobe Mixamo Auto-Rig Specification (mixamorig: prefix)
MIXAMO_BONE_MAP: Dict[str, str] = {
    "Hips": "mixamorig:Hips",
    "Spine": "mixamorig:Spine",
    "Spine1": "mixamorig:Spine1",
    "Spine2": "mixamorig:Spine2",
    "Neck": "mixamorig:Neck",
    "Head": "mixamorig:Head",
    "Clavicle.L": "mixamorig:LeftShoulder",
    "Clavicle.R": "mixamorig:RightShoulder",
    "UpperArm.L": "mixamorig:LeftArm",
    "UpperArm.R": "mixamorig:RightArm",
    "ForeArm.L": "mixamorig:LeftForeArm",
    "ForeArm.R": "mixamorig:RightForeArm",
    "Hand.L": "mixamorig:LeftHand",
    "Hand.R": "mixamorig:RightHand",
    "Thigh.L": "mixamorig:LeftUpLeg",
    "Thigh.R": "mixamorig:RightUpLeg",
    "Shin.L": "mixamorig:LeftLeg",
    "Shin.R": "mixamorig:RightLeg",
    "Foot.L": "mixamorig:LeftFoot",
    "Foot.R": "mixamorig:RightFoot",
    "Toe.L": "mixamorig:LeftToeBase",
    "Toe.R": "mixamorig:RightToeBase",
}
for _side, _side_name in [("L", "Left"), ("R", "Right")]:
    for _finger in ["Thumb", "Index", "Middle", "Ring", "Pinky"]:
        for _k in range(1, 4):
            _canon = f"{_finger}.0{_k}.{_side}"
            _mix = f"mixamorig:{_side_name}Hand{_finger}{_k}"
            MIXAMO_BONE_MAP[_canon] = _mix

# Standard Dictionary Hub
STANDARD_MAPS: Dict[str, Dict[str, str]] = {
    "vrm": VRM_1_0_BONE_MAP,
    "mmd": MMD_BONE_MAP,
    "rigify": RIGIFY_DEF_BONE_MAP,
    "mixamo": MIXAMO_BONE_MAP,
}
BONE_MAPPING_TABLES: Dict[str, Dict[str, str]] = STANDARD_MAPS

# Reverse Alias-To-Canonical Lookup Table
ALIAS_TO_CANONICAL_MAP: Dict[str, str] = {}
for _std_dict in [VRM_1_0_BONE_MAP, MMD_BONE_MAP, RIGIFY_DEF_BONE_MAP, MIXAMO_BONE_MAP]:
    for _canon, _alias in _std_dict.items():
        ALIAS_TO_CANONICAL_MAP[_alias] = _canon
        # Also map without mixamorig: or DEF- prefix
        if ":" in _alias:
            ALIAS_TO_CANONICAL_MAP[_alias.split(":")[-1]] = _canon
        if _alias.startswith("DEF-"):
            ALIAS_TO_CANONICAL_MAP[_alias[4:]] = _canon

# Add self-mappings and common variations
COMMON_ALIASES = {
    # Self-identity
    "Hips": "Hips", "Spine": "Spine", "Spine1": "Spine1", "Spine2": "Spine2", "Neck": "Neck", "Head": "Head",
    "Clavicle.L": "Clavicle.L", "Clavicle.R": "Clavicle.R",
    "UpperArm.L": "UpperArm.L", "UpperArm.R": "UpperArm.R",
    "ForeArm.L": "ForeArm.L", "ForeArm.R": "ForeArm.R",
    "Hand.L": "Hand.L", "Hand.R": "Hand.R",
    "Thigh.L": "Thigh.L", "Thigh.R": "Thigh.R",
    "Shin.L": "Shin.L", "Shin.R": "Shin.R",
    "Foot.L": "Foot.L", "Foot.R": "Foot.R",
    "Toe.L": "Toe.L", "Toe.R": "Toe.R",
    # MMD alternative center/root bones
    "センター": "Hips",
    "全ての親": "Hips",
    # Common mocap nicknames
    "Elbow.L": "ForeArm.L", "Elbow.R": "ForeArm.R",
    "Knee.L": "Shin.L", "Knee.R": "Shin.R",
    "LeftArm": "UpperArm.L", "RightArm": "UpperArm.R",
    "LeftForeArm": "ForeArm.L", "RightForeArm": "ForeArm.R",
    "LeftUpLeg": "Thigh.L", "RightUpLeg": "Thigh.R",
    "LeftLeg": "Shin.L", "RightLeg": "Shin.R",
    "LeftFoot": "Foot.L", "RightFoot": "Foot.R",
    "LeftToe": "Toe.L", "RightToe": "Toe.R",
    "LeftToeBase": "Toe.L", "RightToeBase": "Toe.R",
}
ALIAS_TO_CANONICAL_MAP.update(COMMON_ALIASES)


def resolve_to_canonical(bone_name: str) -> Optional[str]:
    """
    Resolves any arbitrary incoming bone name (from VRM, MMD, Rigify, Mixamo, or raw mocap)
    to the canonical Anime Armature bone name.
    Handles prefixes (mixamorig:, mixamo:, DEF-, b_), casing, and punctuation variants.
    """
    if not bone_name:
        return None

    # 1. Exact match in alias table
    if bone_name in ALIAS_TO_CANONICAL_MAP:
        return ALIAS_TO_CANONICAL_MAP[bone_name]

    # 2. Check if already canonical
    if bone_name in PHYSIOLOGICAL_ROTATION_LIMITS:
        return bone_name

    # 3. Strip common prefixes
    cleaned = bone_name
    for prefix in ["mixamorig:", "mixamo:", "DEF-", "b_", "Bip01_", "Bip001_"]:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break

    if cleaned in ALIAS_TO_CANONICAL_MAP:
        return ALIAS_TO_CANONICAL_MAP[cleaned]
    if cleaned in PHYSIOLOGICAL_ROTATION_LIMITS:
        return cleaned

    # 4. Normalized alphanumeric lowercase matching
    norm_query = re.sub(r"[^a-zA-Z0-9\u4e00-\u9faf\u3040-\u30ff]", "", bone_name).lower()
    for alias, canon in ALIAS_TO_CANONICAL_MAP.items():
        norm_alias = re.sub(r"[^a-zA-Z0-9\u4e00-\u9faf\u3040-\u30ff]", "", alias).lower()
        if norm_query == norm_alias:
            return canon

    return None


def get_standard_bone_name(canonical_name: str, standard: str) -> Optional[str]:
    """
    Returns the bone name in the specified target standard ('vrm', 'mmd', 'rigify', 'mixamo').
    """
    std_key = standard.lower().strip()
    if std_key not in STANDARD_MAPS:
        raise ValueError(f"Unknown standard: {standard}. Supported: {list(STANDARD_MAPS.keys())}")
    return STANDARD_MAPS[std_key].get(canonical_name)


# ==============================================================================
# 4. Pure-Python Mathematical Rotational Utilities
# ==============================================================================

def clamp_angle(angle_rad: float, min_rad: float, max_rad: float) -> float:
    """Clamps an angle in radians between min_rad and max_rad."""
    return max(min_rad, min(angle_rad, max_rad))


def clamp_joint_angle_deg(angle_deg: float, min_deg: float, max_deg: float) -> float:
    """Clamps a joint angle in degrees within physiological bounds."""
    return max(min_deg, min(angle_deg, max_deg))


def normalize_quaternion(w: float, x: float, y: float, z: float) -> Tuple[float, float, float, float]:
    """Normalizes a 4-component quaternion to unit length."""
    norm_sq = w * w + x * x + y * y + z * z
    if norm_sq < 1e-12:
        return (1.0, 0.0, 0.0, 0.0)
    inv_norm = 1.0 / math.sqrt(norm_sq)
    return (w * inv_norm, x * inv_norm, y * inv_norm, z * inv_norm)


def quat_to_euler_xyz(w: float, x: float, y: float, z: float) -> Tuple[float, float, float]:
    """
    Converts a normalized quaternion (w, x, y, z) into extrinsic XYZ Euler angles (alpha, beta, gamma).
    Bit-accurately matches Blender's mathutils.Quaternion.to_euler('XYZ').
    """
    w, x, y, z = normalize_quaternion(w, x, y, z)

    # Blender matrix representation of quaternion:
    # m[0][0] = 1 - 2(y^2 + z^2)
    # m[1][0] = 2(xy + wz)
    # m[2][0] = 2(xz - wy)
    # m[2][1] = 2(yz + wx)
    # m[2][2] = 1 - 2(x^2 + y^2)
    m00 = 1.0 - 2.0 * (y * y + z * z)
    m10 = 2.0 * (x * y + w * z)
    m20 = 2.0 * (x * z - w * y)
    m21 = 2.0 * (y * z + w * x)
    m22 = 1.0 - 2.0 * (x * x + y * y)

    cy = math.sqrt(m00 * m00 + m10 * m10)
    if cy > 1e-6:
        alpha = math.atan2(m21, m22)
        beta = math.atan2(-m20, cy)
        gamma = math.atan2(m10, m00)
    else:
        # Gimbal lock singularity
        m11 = 1.0 - 2.0 * (x * x + z * z)
        m12 = 2.0 * (y * z - w * x)
        alpha = math.atan2(-m12, m11)
        beta = math.atan2(-m20, cy)
        gamma = 0.0

    return (alpha, beta, gamma)


def euler_xyz_to_quat(alpha: float, beta: float, gamma: float) -> Tuple[float, float, float, float]:
    """
    Converts XYZ Euler angles (alpha, beta, gamma in radians) into a quaternion (w, x, y, z).
    Bit-accurately matches Blender's mathutils.Euler.to_quaternion().
    """
    cx = math.cos(alpha * 0.5)
    sx = math.sin(alpha * 0.5)
    cy = math.cos(beta * 0.5)
    sy = math.sin(beta * 0.5)
    cz = math.cos(gamma * 0.5)
    sz = math.sin(gamma * 0.5)

    # R = Rz * Ry * Rx (Blender intrinsic XYZ order)
    w = cz * cy * cx + sz * sy * sx
    qx = cz * cy * sx - sz * sy * cx
    qy = cz * sy * cx + sz * cy * sx
    qz = sz * cy * cx - cz * sy * sx

    return normalize_quaternion(w, qx, qy, qz)


# ==============================================================================
# 5. Retargeting Pose Sanitizer Implementation
# ==============================================================================

def clamp_single_bone_rotation(
    rotation: Any,
    limit_spec: LimitSpec,
    order: str = "XYZ",
) -> Any:
    """
    Clamps a single rotation (Quaternion, Euler, or Sequence) according to limit_spec.
    Preserves input types: if input is mathutils.Quaternion or mathutils.Euler, returns the same type.
    """
    is_mathutils_quat = False
    is_mathutils_euler = False
    is_tuple_quat = False
    is_tuple_euler = False

    if HAS_BPY and isinstance(rotation, mathutils.Quaternion):
        is_mathutils_quat = True
        w, x, y, z = rotation.w, rotation.x, rotation.y, rotation.z
        alpha, beta, gamma = quat_to_euler_xyz(w, x, y, z)
    elif HAS_BPY and isinstance(rotation, mathutils.Euler):
        is_mathutils_euler = True
        alpha, beta, gamma = rotation.x, rotation.y, rotation.z
    elif isinstance(rotation, (tuple, list)):
        if len(rotation) == 4:
            is_tuple_quat = True
            w, x, y, z = rotation[0], rotation[1], rotation[2], rotation[3]
            alpha, beta, gamma = quat_to_euler_xyz(w, x, y, z)
        elif len(rotation) == 3:
            is_tuple_euler = True
            alpha, beta, gamma = rotation[0], rotation[1], rotation[2]
        else:
            raise ValueError(f"Invalid rotation sequence length: {len(rotation)}")
    else:
        # Unrecognized format, return as is
        return rotation

    # Apply physiological limits
    c_alpha = clamp_angle(alpha, limit_spec.min_x, limit_spec.max_x) if limit_spec.use_x else alpha
    c_beta = clamp_angle(beta, limit_spec.min_y, limit_spec.max_y) if limit_spec.use_y else beta
    c_gamma = clamp_angle(gamma, limit_spec.min_z, limit_spec.max_z) if limit_spec.use_z else gamma

    # Reconstruct in original format
    if is_mathutils_quat:
        qw, qx, qy, qz = euler_xyz_to_quat(c_alpha, c_beta, c_gamma)
        return mathutils.Quaternion((qw, qx, qy, qz))
    elif is_mathutils_euler:
        return mathutils.Euler((c_alpha, c_beta, c_gamma), order)
    elif is_tuple_quat:
        qw, qx, qy, qz = euler_xyz_to_quat(c_alpha, c_beta, c_gamma)
        return (qw, qx, qy, qz) if isinstance(rotation, tuple) else [qw, qx, qy, qz]
    elif is_tuple_euler:
        return (c_alpha, c_beta, c_gamma) if isinstance(rotation, tuple) else [c_alpha, c_beta, c_gamma]

    return rotation


def clamp_pose_rotations(
    bone_rotations: Dict[str, Any],
    limits_dict: Optional[Dict[str, LimitSpec]] = None,
    sanitize_quaternions: bool = True,
) -> Dict[str, Any]:
    """
    Pure-Python Retargeting Pose Sanitizer.
    Takes arbitrary raw mocap/quaternion/Euler rotations across standard humanoid naming conventions
    and clamps them mathematically to physiological limits before keyframing.

    Arguments:
        bone_rotations: Dict mapping bone names (canonical or standard aliases) to rotations
                        (Quaternion, Euler, tuple, or list).
        limits_dict: Optional custom limit matrix. Defaults to PHYSIOLOGICAL_ROTATION_LIMITS.
        sanitize_quaternions: If True, ensures unconstrained quaternions are unit-normalized.

    Returns:
        Dict mapping input bone names to sanitized, clamped rotations in identical representation format.
    """
    limits = limits_dict if limits_dict is not None else PHYSIOLOGICAL_ROTATION_LIMITS
    sanitized: Dict[str, Any] = {}

    for raw_name, rot_val in bone_rotations.items():
        canonical_name = resolve_to_canonical(raw_name)
        limit_spec = limits.get(canonical_name) if canonical_name else None

        if limit_spec is not None:
            # Clamp to physiological limits
            clamped_rot = clamp_single_bone_rotation(rot_val, limit_spec)
            sanitized[raw_name] = clamped_rot
        else:
            # No limit defined; optionally normalize if quaternion
            if sanitize_quaternions and isinstance(rot_val, (tuple, list)) and len(rot_val) == 4:
                nw, nx, ny, nz = normalize_quaternion(rot_val[0], rot_val[1], rot_val[2], rot_val[3])
                sanitized[raw_name] = (nw, nx, ny, nz) if isinstance(rot_val, tuple) else [nw, nx, ny, nz]
            elif sanitize_quaternions and HAS_BPY and isinstance(rot_val, mathutils.Quaternion):
                q_copy = rot_val.copy()
                q_copy.normalize()
                sanitized[raw_name] = q_copy
            else:
                sanitized[raw_name] = rot_val

    return sanitized


# ==============================================================================
# 6. Live Armature Constraint Attachment in Blender 4.5+ LTS
# ==============================================================================

def apply_retargeting_limits(
    armature_obj: Any,
    limits_dict: Optional[Dict[str, LimitSpec]] = None,
    replace_existing: bool = True,
    target_bones: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """
    Attaches LIMIT_ROTATION constraints to pose bones of Anime_Armature in Pose Mode.
    Owner space is strictly set to 'LOCAL' so that hinge and physiological limits apply
    relative to the bone's rest orientation regardless of character world transform.

    Arguments:
        armature_obj: Blender Armature Object.
        limits_dict: Custom limit specification dictionary. Defaults to PHYSIOLOGICAL_ROTATION_LIMITS.
        replace_existing: If True, updates or replaces existing Physiological_Limit_Rotation constraints.
        target_bones: Optional list of specific bone names to limit. If None, applies to all known bones.

    Returns:
        Summary dict containing counts of applied, updated, and skipped bones.
    """
    if not HAS_BPY:
        raise RuntimeError("Blender Python (bpy) is required to apply armature constraints.")

    if not armature_obj or armature_obj.type != 'ARMATURE':
        raise TypeError(f"Expected ARMATURE object, got {type(armature_obj)}")

    limits = limits_dict if limits_dict is not None else PHYSIOLOGICAL_ROTATION_LIMITS
    pose_bones = armature_obj.pose.bones

    applied_bones: List[str] = []
    updated_bones: List[str] = []
    skipped_bones: List[str] = []

    bones_to_process = target_bones if target_bones is not None else limits.keys()

    for bname in bones_to_process:
        canonical_name = resolve_to_canonical(bname) or bname
        spec = limits.get(canonical_name)
        if not spec:
            skipped_bones.append(bname)
            continue

        # Find pose bone by canonical name or alias
        pb = pose_bones.get(canonical_name)
        if not pb:
            pb = pose_bones.get(bname)
        if not pb:
            # Search aliases
            for alias, canon in ALIAS_TO_CANONICAL_MAP.items():
                if canon == canonical_name and alias in pose_bones:
                    pb = pose_bones[alias]
                    break

        if not pb:
            skipped_bones.append(bname)
            continue

        # Check existing constraint
        existing_c = None
        for c in pb.constraints:
            if c.type == 'LIMIT_ROTATION' and (c.name == "Physiological_Limit_Rotation" or "Limit Rotation" in c.name):
                existing_c = c
                break

        if existing_c and not replace_existing:
            skipped_bones.append(pb.name)
            continue

        c = existing_c if existing_c else pb.constraints.new(type='LIMIT_ROTATION')
        c.name = "Physiological_Limit_Rotation"
        c.owner_space = 'LOCAL'
        c.euler_order = 'XYZ'
        c.use_transform_limit = True
        c.influence = 1.0

        # Assign axis clamps
        c.use_limit_x = spec.use_x
        c.min_x = spec.min_x
        c.max_x = spec.max_x

        c.use_limit_y = spec.use_y
        c.min_y = spec.min_y
        c.max_y = spec.max_y

        c.use_limit_z = spec.use_z
        c.min_z = spec.min_z
        c.max_z = spec.max_z

        if existing_c:
            updated_bones.append(pb.name)
        else:
            applied_bones.append(pb.name)

    return {
        "applied_count": len(applied_bones),
        "updated_count": len(updated_bones),
        "skipped_count": len(skipped_bones),
        "applied_bones": applied_bones,
        "updated_bones": updated_bones,
        "skipped_bones": skipped_bones,
    }


def remove_retargeting_limits(
    armature_obj: Any,
    target_bones: Optional[Iterable[str]] = None,
) -> int:
    """
    Removes all Physiological_Limit_Rotation constraints from the given armature.
    Returns the count of constraints removed.
    """
    if not HAS_BPY:
        raise RuntimeError("Blender Python (bpy) is required.")

    if not armature_obj or armature_obj.type != 'ARMATURE':
        return 0

    removed = 0
    pose_bones = armature_obj.pose.bones
    bones = [pose_bones[b] for b in target_bones if b in pose_bones] if target_bones else pose_bones

    for pb in bones:
        to_remove = [c for c in pb.constraints if c.type == 'LIMIT_ROTATION' and c.name == "Physiological_Limit_Rotation"]
        for c in to_remove:
            pb.constraints.remove(c)
            removed += 1

    return removed


def verify_retargeting_limits(
    armature_obj: Any,
    limits_dict: Optional[Dict[str, LimitSpec]] = None,
) -> Dict[str, Any]:
    """
    Audits an armature to verify that all physiological rotational constraints are present,
    properly configured with owner_space = 'LOCAL', and match required angular bounds.

    Returns:
        Dict report with pass_status (bool), verified_count (int), and discrepancies list.
    """
    if not HAS_BPY:
        raise RuntimeError("Blender Python (bpy) is required.")

    limits = limits_dict if limits_dict is not None else PHYSIOLOGICAL_ROTATION_LIMITS
    pose_bones = armature_obj.pose.bones

    discrepancies: List[str] = []
    verified_count = 0

    for bname, spec in limits.items():
        pb = pose_bones.get(bname)
        if not pb:
            # Check aliases
            for alias, canon in ALIAS_TO_CANONICAL_MAP.items():
                if canon == bname and alias in pose_bones:
                    pb = pose_bones[alias]
                    break

        if not pb:
            discrepancies.append(f"Bone {bname} not found in armature pose bones")
            continue

        # Find LIMIT_ROTATION constraint
        lim_c = next((c for c in pb.constraints if c.type == 'LIMIT_ROTATION' and c.name == "Physiological_Limit_Rotation"), None)
        if not lim_c:
            lim_c = next((c for c in pb.constraints if c.type == 'LIMIT_ROTATION'), None)

        if not lim_c:
            discrepancies.append(f"Bone {bname} has no LIMIT_ROTATION constraint")
            continue

        if lim_c.owner_space != 'LOCAL':
            discrepancies.append(f"Bone {bname} constraint owner_space is '{lim_c.owner_space}', expected 'LOCAL'")

        # Verify X limits
        if spec.use_x:
            if not lim_c.use_limit_x:
                discrepancies.append(f"Bone {bname} use_limit_x is False, expected True")
            elif abs(lim_c.min_x - spec.min_x) > 1e-4 or abs(lim_c.max_x - spec.max_x) > 1e-4:
                discrepancies.append(
                    f"Bone {bname} X bounds mismatch: got [{lim_c.min_x:.3f}, {lim_c.max_x:.3f}], "
                    f"expected [{spec.min_x:.3f}, {spec.max_x:.3f}]"
                )

        # Verify Y limits
        if spec.use_y:
            if not lim_c.use_limit_y:
                discrepancies.append(f"Bone {bname} use_limit_y is False, expected True")
            elif abs(lim_c.min_y - spec.min_y) > 1e-4 or abs(lim_c.max_y - spec.max_y) > 1e-4:
                discrepancies.append(
                    f"Bone {bname} Y bounds mismatch: got [{lim_c.min_y:.3f}, {lim_c.max_y:.3f}], "
                    f"expected [{spec.min_y:.3f}, {spec.max_y:.3f}]"
                )

        # Verify Z limits
        if spec.use_z:
            if not lim_c.use_limit_z:
                discrepancies.append(f"Bone {bname} use_limit_z is False, expected True")
            elif abs(lim_c.min_z - spec.min_z) > 1e-4 or abs(lim_c.max_z - spec.max_z) > 1e-4:
                discrepancies.append(
                    f"Bone {bname} Z bounds mismatch: got [{lim_c.min_z:.3f}, {lim_c.max_z:.3f}], "
                    f"expected [{spec.min_z:.3f}, {spec.max_z:.3f}]"
                )

        verified_count += 1

    return {
        "pass_status": len(discrepancies) == 0,
        "verified_count": verified_count,
        "discrepancies_count": len(discrepancies),
        "discrepancies": discrepancies,
    }


def clamp_animation_action_keyframes(
    action: Any,
    armature_obj: Optional[Any] = None,
    limits_dict: Optional[Dict[str, LimitSpec]] = None,
) -> Dict[str, int]:
    """
    Sanitizes an existing Blender Action's f-curves by clamping keyframe points directly.
    Supports rotation_euler (data_path = 'pose.bones["..."].rotation_euler', array_index 0, 1, 2).

    Returns:
        Dict with total_keyframes_scanned and total_keyframes_clamped.
    """
    if not HAS_BPY or not action:
        return {"total_keyframes_scanned": 0, "total_keyframes_clamped": 0}

    limits = limits_dict if limits_dict is not None else PHYSIOLOGICAL_ROTATION_LIMITS
    scanned = 0
    clamped = 0

    bone_regex = re.compile(r'pose\.bones\["([^"]+)"\]\.rotation_euler')

    for fc in action.fcurves:
        match = bone_regex.match(fc.data_path)
        if not match:
            continue

        raw_bname = match.group(1)
        canonical_name = resolve_to_canonical(raw_bname)
        spec = limits.get(canonical_name) if canonical_name else None
        if not spec:
            continue

        axis_idx = fc.array_index
        min_v = 0.0
        max_v = 0.0
        use_lim = False

        if axis_idx == 0 and spec.use_x:
            min_v, max_v = spec.min_x, spec.max_x
            use_lim = True
        elif axis_idx == 1 and spec.use_y:
            min_v, max_v = spec.min_y, spec.max_y
            use_lim = True
        elif axis_idx == 2 and spec.use_z:
            min_v, max_v = spec.min_z, spec.max_z
            use_lim = True

        if not use_lim:
            continue

        for kp in fc.keyframe_points:
            scanned += 1
            orig_val = kp.co[1]
            c_val = clamp_angle(orig_val, min_v, max_v)
            if abs(c_val - orig_val) > 1e-6:
                kp.co[1] = c_val
                clamped += 1

        fc.update()

    return {"total_keyframes_scanned": scanned, "total_keyframes_clamped": clamped}


# Aliases for cross-module compatibility
setup_retargeting_constraints = apply_retargeting_limits

__all__ = [
    "LimitSpec",
    "PHYSIOLOGICAL_ROTATION_LIMITS",
    "HINGE_LIMITS",
    "VRM_1_0_BONE_MAP",
    "MMD_BONE_MAP",
    "RIGIFY_DEF_BONE_MAP",
    "MIXAMO_BONE_MAP",
    "STANDARD_MAPS",
    "BONE_MAPPING_TABLES",
    "ALIAS_TO_CANONICAL_MAP",
    "clamp_angle",
    "clamp_joint_angle_deg",
    "normalize_quaternion",
    "quat_to_euler_xyz",
    "euler_xyz_to_quat",
    "resolve_to_canonical",
    "get_standard_bone_name",
    "clamp_single_bone_rotation",
    "clamp_pose_rotations",
    "apply_retargeting_limits",
    "setup_retargeting_constraints",
    "remove_retargeting_limits",
    "verify_retargeting_limits",
    "clamp_animation_action_keyframes",
]
