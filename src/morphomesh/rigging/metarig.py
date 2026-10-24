"""
Rigify Human Metarig Generator and Landmark Alignment.

Responsible for:
- Authoritative 163 DEF bone definitions (64 body + 99 facial).
- Bone hierarchy, parent-child relations, and joint pre-bends (elbow +Y, knee -Y).
- align_rigify_metarig_pivots: Biological joint rotation axes and instantaneous centers of rotation.
- generate_rigify_human_metarig: Constructing MetarigStructure with all 163 DEF bones.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

try:
    from morphomesh.anatomy.bone_roll import solve_biomechanical_bone_roll
except (ImportError, ModuleNotFoundError):
    try:
        from ...anatomy.bone_roll import solve_biomechanical_bone_roll  # type: ignore[no-redef]
    except Exception:
        solve_biomechanical_bone_roll = None  # type: ignore[assignment]


BODY_DEF_BONES: Tuple[str, ...] = (
    # Spine, Head & Eyes (10 bones)
    "DEF-spine",
    "DEF-spine.001",
    "DEF-spine.002",
    "DEF-spine.003",
    "DEF-spine.004",
    "DEF-spine.005",
    "DEF-spine.006",
    "DEF-head",
    "DEF-eye.L",
    "DEF-eye.R",
    # Upper Limbs Left (6 bones)
    "DEF-shoulder.L",
    "DEF-upper_arm.L",
    "DEF-upper_arm.L.001",
    "DEF-forearm.L",
    "DEF-forearm.L.001",
    "DEF-hand.L",
    # Upper Limbs Right (6 bones)
    "DEF-shoulder.R",
    "DEF-upper_arm.R",
    "DEF-upper_arm.R.001",
    "DEF-forearm.R",
    "DEF-forearm.R.001",
    "DEF-hand.R",
    # Fingers Left (15 bones)
    "DEF-thumb.01.L", "DEF-thumb.02.L", "DEF-thumb.03.L",
    "DEF-f_index.01.L", "DEF-f_index.02.L", "DEF-f_index.03.L",
    "DEF-f_middle.01.L", "DEF-f_middle.02.L", "DEF-f_middle.03.L",
    "DEF-f_ring.01.L", "DEF-f_ring.02.L", "DEF-f_ring.03.L",
    "DEF-f_pinky.01.L", "DEF-f_pinky.02.L", "DEF-f_pinky.03.L",
    # Fingers Right (15 bones)
    "DEF-thumb.01.R", "DEF-thumb.02.R", "DEF-thumb.03.R",
    "DEF-f_index.01.R", "DEF-f_index.02.R", "DEF-f_index.03.R",
    "DEF-f_middle.01.R", "DEF-f_middle.02.R", "DEF-f_middle.03.R",
    "DEF-f_ring.01.R", "DEF-f_ring.02.R", "DEF-f_ring.03.R",
    "DEF-f_pinky.01.R", "DEF-f_pinky.02.R", "DEF-f_pinky.03.R",
    # Lower Limbs Left (6 bones)
    "DEF-thigh.L",
    "DEF-thigh.L.001",
    "DEF-shin.L",
    "DEF-shin.L.001",
    "DEF-foot.L",
    "DEF-toe.L",
    # Lower Limbs Right (6 bones)
    "DEF-thigh.R",
    "DEF-thigh.R.001",
    "DEF-shin.R",
    "DEF-shin.R.001",
    "DEF-foot.R",
    "DEF-toe.R",
)

FACIAL_DEF_BONES: Tuple[str, ...] = (
    # Brows (16 bones: 4 per quadrant B/T, L/R)
    "DEF-brow.B.L.000", "DEF-brow.B.L.001", "DEF-brow.B.L.002", "DEF-brow.B.L.003",
    "DEF-brow.B.R.000", "DEF-brow.B.R.001", "DEF-brow.B.R.002", "DEF-brow.B.R.003",
    "DEF-brow.T.L.000", "DEF-brow.T.L.001", "DEF-brow.T.L.002", "DEF-brow.T.L.003",
    "DEF-brow.T.R.000", "DEF-brow.T.R.001", "DEF-brow.T.R.002", "DEF-brow.T.R.003",
    # Cheeks (8 bones: 2 per B/T, L/R)
    "DEF-cheek.B.L.000", "DEF-cheek.B.L.001",
    "DEF-cheek.B.R.000", "DEF-cheek.B.R.001",
    "DEF-cheek.T.L.000", "DEF-cheek.T.L.001",
    "DEF-cheek.T.R.000", "DEF-cheek.T.R.001",
    # Chin (4 bones: 2 per L/R)
    "DEF-chin.L.000", "DEF-chin.L.001",
    "DEF-chin.R.000", "DEF-chin.R.001",
    # Ears (10 bones: 5 per L/R)
    "DEF-ear.L.000", "DEF-ear.L.001", "DEF-ear.L.002", "DEF-ear.L.003", "DEF-ear.L.004",
    "DEF-ear.R.000", "DEF-ear.R.001", "DEF-ear.R.002", "DEF-ear.R.003", "DEF-ear.R.004",
    # Forehead (8 bones: 4 per L/R)
    "DEF-forehead.L.000", "DEF-forehead.L.001", "DEF-forehead.L.002", "DEF-forehead.L.003",
    "DEF-forehead.R.000", "DEF-forehead.R.001", "DEF-forehead.R.002", "DEF-forehead.R.003",
    # Jaw (4 bones: 2 per L/R)
    "DEF-jaw.L.000", "DEF-jaw.L.001",
    "DEF-jaw.R.000", "DEF-jaw.R.001",
    # Eyelids (16 bones: 4 per B/T, L/R)
    "DEF-lid.B.L.000", "DEF-lid.B.L.001", "DEF-lid.B.L.002", "DEF-lid.B.L.003",
    "DEF-lid.B.R.000", "DEF-lid.B.R.001", "DEF-lid.B.R.002", "DEF-lid.B.R.003",
    "DEF-lid.T.L.000", "DEF-lid.T.L.001", "DEF-lid.T.L.002", "DEF-lid.T.L.003",
    "DEF-lid.T.R.000", "DEF-lid.T.R.001", "DEF-lid.T.R.002", "DEF-lid.T.R.003",
    # Lips (16 bones: 4 per B/T, L/R)
    "DEF-lip.B.L.000", "DEF-lip.B.L.001", "DEF-lip.B.L.002", "DEF-lip.B.L.003",
    "DEF-lip.B.R.000", "DEF-lip.B.R.001", "DEF-lip.B.R.002", "DEF-lip.B.R.003",
    "DEF-lip.T.L.000", "DEF-lip.T.L.001", "DEF-lip.T.L.002", "DEF-lip.T.L.003",
    "DEF-lip.T.R.000", "DEF-lip.T.R.001", "DEF-lip.T.R.002", "DEF-lip.T.R.003",
    # Nose (8 bones: 4 per L/R)
    "DEF-nose.L.000", "DEF-nose.L.001", "DEF-nose.L.002", "DEF-nose.L.003",
    "DEF-nose.R.000", "DEF-nose.R.001", "DEF-nose.R.002", "DEF-nose.R.003",
    # Temple (2 bones: 1 per L/R)
    "DEF-temple.L.000",
    "DEF-temple.R.000",
    # Tongue (6 bones: 3 per L/R)
    "DEF-tongue.L.000", "DEF-tongue.L.001", "DEF-tongue.L.002",
    "DEF-tongue.R.000", "DEF-tongue.R.001", "DEF-tongue.R.002",
    # Midline Jaw Deformer (1 bone)
    "DEF-jaw.center",
)

ALL_163_DEF_BONES: Tuple[str, ...] = BODY_DEF_BONES + FACIAL_DEF_BONES


class HumanRigConfig(BaseModel):
    """Configuration model governing digital human rigging and blendshape synthesis."""
    model_config = ConfigDict(extra="ignore")

    rig_type: str = Field(default="rigify_human", description="Rig type specification.")
    skinning_method: str = Field(default="automatic_weights", description="Skin binding algorithm.")
    include_face_rig: bool = Field(default=True, description="Include 99 facial DEF bones.")
    include_finger_rig: bool = Field(default=True, description="Include 10-finger skeletal articulation.")
    pose: str = Field(default="puppeteer_pose", description="Rest or initial staging pose.")
    export_format: str = Field(default="fbx", description="Target export asset format.")
    dual_quaternion_skinning: bool = Field(default=True, description="Preserve volume with DQS.")
    anti_pinch_weights: bool = Field(default=True, description="Apply anti-pinching skin weights.")
    elbow_prebend_y: float = Field(default=0.015, description="Elbow posterior +Y pre-bend in meters.")
    knee_prebend_y: float = Field(default=-0.018, description="Knee anterior -Y pre-bend in meters (behind patella at condylar hinge axis).")


@dataclass
class BoneDefinition:
    """Represents a single bone in the metarig or generated armature."""

    name: str
    head: Tuple[float, float, float]
    tail: Tuple[float, float, float]
    parent: Optional[str] = None
    roll: float = 0.0
    use_deform: bool = True
    category: str = "body"  # "body" or "facial"

    @property
    def length(self) -> float:
        dx = self.tail[0] - self.head[0]
        dy = self.tail[1] - self.head[1]
        dz = self.tail[2] - self.head[2]
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    @property
    def vector(self) -> Tuple[float, float, float]:
        return (
            self.tail[0] - self.head[0],
            self.tail[1] - self.head[1],
            self.tail[2] - self.head[2],
        )


@dataclass
class MetarigStructure:
    """Encapsulates the complete 163 DEF bones metarig hierarchy and landmark bindings."""

    bones: Dict[str, BoneDefinition] = field(default_factory=dict)
    body_def_bones: List[str] = field(default_factory=lambda: list(BODY_DEF_BONES))
    facial_def_bones: List[str] = field(default_factory=lambda: list(FACIAL_DEF_BONES))
    total_def_bones: List[str] = field(default_factory=lambda: list(ALL_163_DEF_BONES))
    landmarks: Dict[str, Tuple[float, float, float]] = field(default_factory=dict)
    armature_name: str = "Armature_Yu_Nian_An_Rigify"

    @property
    def bone_count(self) -> int:
        return len(self.bones)

    @property
    def def_bone_count(self) -> int:
        return sum(1 for b in self.bones.values() if b.use_deform and b.name.startswith("DEF-"))

    def get_bone(self, name: str) -> Optional[BoneDefinition]:
        return self.bones.get(name)

    def verify_prebends(self) -> Tuple[bool, Dict[str, float]]:
        """Verifies that elbows have +Y pre-bend and knees have -Y pre-bend symmetrically across Left and Right."""
        metrics: Dict[str, float] = {}
        for side in ["L", "R"]:
            el = self.bones.get(f"DEF-forearm.{side}")
            if el:
                metrics[f"elbow_{side}_y"] = el.head[1]
            kn = self.bones.get(f"DEF-shin.{side}")
            if kn:
                metrics[f"knee_{side}_y"] = kn.head[1]

        elbow_ok = (
            metrics.get("elbow_L_y", 0.0) > 0.0 and
            metrics.get("elbow_R_y", 0.0) > 0.0
        )
        knee_ok = (
            metrics.get("knee_L_y", 0.0) < 0.0 and
            metrics.get("knee_R_y", 0.0) < 0.0
        )
        return (elbow_ok and knee_ok), metrics


def get_default_human_landmarks(height: float = 1.65) -> Dict[str, Tuple[float, float, float]]:
    """Returns canonical reference landmarks for a 1.65m female human."""
    s = height / 1.65
    return {
        "head_top": (0.0, 0.005 * s, 1.650 * s),
        "chin": (0.0, -0.065 * s, 1.427 * s),
        "neck": (0.0, 0.015 * s, 1.390 * s),
        "clavicle_L": (0.045 * s, -0.015 * s, 1.350 * s),
        "clavicle_R": (-0.045 * s, -0.015 * s, 1.350 * s),
        "shoulder_L": (0.175 * s, -0.020 * s, 1.340 * s),
        "shoulder_R": (-0.175 * s, -0.020 * s, 1.340 * s),
        "elbow_L": (0.280 * s, 0.015 * s, 1.070 * s),  # Pre-bend in +Y
        "elbow_R": (-0.280 * s, 0.015 * s, 1.070 * s),
        "wrist_L": (0.360 * s, -0.020 * s, 0.830 * s),
        "wrist_R": (-0.360 * s, -0.020 * s, 0.830 * s),
        "fingers_L": (0.420 * s, -0.040 * s, 0.680 * s),
        "fingers_R": (-0.420 * s, -0.040 * s, 0.680 * s),
        "spine_chest": (0.0, -0.005 * s, 1.250 * s),
        "spine_waist": (0.0, -0.010 * s, 1.050 * s),
        "spine_pelvis": (0.0, 0.000 * s, 0.825 * s),
        # Biological skeletal landmarks (Feature 7)
        "pelvic_crest_L": (0.145 * s, -0.005 * s, 0.945 * s),
        "pelvic_crest_R": (-0.145 * s, -0.005 * s, 0.945 * s),
        # Femoral head hip pivot: raised +0.038m into true acetabular socket
        "hip_L": (0.088 * s, -0.005 * s, 0.863 * s),
        "hip_R": (-0.088 * s, -0.005 * s, 0.863 * s),
        "patella_L": (0.100 * s, -0.038 * s, 0.470 * s),
        "patella_R": (-0.100 * s, -0.038 * s, 0.470 * s),
        # Knee condylar hinge axis: Z = z_patella - 0.025m = 0.445m, Y = -0.018m (recessed behind patella)
        "knee_L": (0.100 * s, -0.018 * s, 0.445 * s),  # Pre-bend in -Y
        "knee_R": (-0.100 * s, -0.018 * s, 0.445 * s),
        # Asymmetric bimalleolar ankle landmarks (Medial higher/anterior, Lateral lower/posterior)
        "malleolus_medial_L": (0.072 * s, 0.002 * s, 0.088 * s),
        "malleolus_lateral_L": (0.106 * s, -0.006 * s, 0.076 * s),
        "malleolus_medial_R": (-0.072 * s, 0.002 * s, 0.088 * s),
        "malleolus_lateral_R": (-0.106 * s, -0.006 * s, 0.076 * s),
        # Ankle center: midpoint of true bimalleolar line connecting medial and lateral malleoli
        "ankle_L": (0.089 * s, -0.002 * s, 0.082 * s),
        "ankle_R": (-0.089 * s, -0.002 * s, 0.082 * s),
        # Oblique MTP break axis & toe tip
        "toe_L": (0.090 * s, -0.145 * s, 0.015 * s),
        "toe_R": (-0.090 * s, -0.145 * s, 0.015 * s),
    }


def generate_rigify_human_metarig(
    landmarks: Optional[Dict[str, Tuple[float, float, float]]] = None,
    config: Optional[HumanRigConfig] = None,
) -> MetarigStructure:
    """
    Constructs the complete Rigify Human Metarig with exactly 163 DEF bones
    (64 body DEF bones + 99 facial DEF bones) snapped to anatomical landmarks.
    """
    cfg = config or HumanRigConfig()
    lm = dict(landmarks or get_default_human_landmarks())

    # Ensure all required landmarks exist
    defaults = get_default_human_landmarks()
    for k, v in defaults.items():
        if k not in lm:
            lm[k] = v

    metarig = MetarigStructure(landmarks=lm)
    bones: Dict[str, BoneDefinition] = {}

    # --------------------------------------------------------------------------
    # 1. SPINE, NECK, HEAD & EYES HIERARCHY (10 DEF BONES)
    # --------------------------------------------------------------------------
    p_pelvis = lm["spine_pelvis"]
    p_waist = lm["spine_waist"]
    p_chest = lm["spine_chest"]
    p_neck = lm["neck"]
    p_chin = lm["chin"]
    p_crown = lm["head_top"]

    # Midpoints for 6-segment spine
    p_s1 = (p_pelvis[0], p_pelvis[1], p_pelvis[2] + 0.5 * (p_waist[2] - p_pelvis[2]))
    p_s2 = p_waist
    p_s3 = (p_waist[0], p_waist[1], p_waist[2] + 0.5 * (p_chest[2] - p_waist[2]))
    p_s4 = p_chest
    p_s5 = (0.0, 0.5 * (p_chest[1] + p_neck[1]), 0.5 * (p_chest[2] + p_neck[2]))
    p_s6 = p_neck

    bones["DEF-spine"] = BoneDefinition("DEF-spine", p_pelvis, p_s1, parent=None, category="body")
    bones["DEF-spine.001"] = BoneDefinition("DEF-spine.001", p_s1, p_s2, parent="DEF-spine", category="body")
    bones["DEF-spine.002"] = BoneDefinition("DEF-spine.002", p_s2, p_s3, parent="DEF-spine.001", category="body")
    bones["DEF-spine.003"] = BoneDefinition("DEF-spine.003", p_s3, p_s4, parent="DEF-spine.002", category="body")
    bones["DEF-spine.004"] = BoneDefinition("DEF-spine.004", p_s4, p_s5, parent="DEF-spine.003", category="body")
    bones["DEF-spine.005"] = BoneDefinition("DEF-spine.005", p_s5, p_s6, parent="DEF-spine.004", category="body")
    bones["DEF-spine.006"] = BoneDefinition("DEF-spine.006", p_s6, p_chin, parent="DEF-spine.005", category="body")
    bones["DEF-head"] = BoneDefinition("DEF-head", p_chin, p_crown, parent="DEF-spine.005", category="body")

    # Eyeball deformers (parented to DEF-spine.006)
    scale = p_crown[2] / 1.65
    eye_z = p_chin[2] + 0.48 * (p_crown[2] - p_chin[2])
    eye_y = -0.035 * scale
    eye_x_l = 0.031 * scale
    eye_x_r = -0.031 * scale

    bones["DEF-eye.L"] = BoneDefinition(
        "DEF-eye.L",
        (eye_x_l, eye_y, eye_z),
        (eye_x_l, eye_y - 0.025 * scale, eye_z),
        parent="DEF-spine.006",
        category="body",
    )
    bones["DEF-eye.R"] = BoneDefinition(
        "DEF-eye.R",
        (eye_x_r, eye_y, eye_z),
        (eye_x_r, eye_y - 0.025 * scale, eye_z),
        parent="DEF-spine.006",
        category="body",
    )

    # --------------------------------------------------------------------------
    # 2. UPPER LIMBS & FINGERS (12 ARMS + 30 FINGERS = 42 BONES)
    # --------------------------------------------------------------------------
    for side, sign in [("L", 1.0), ("R", -1.0)]:
        side_lower = side.lower()
        p_clav = lm.get(f"joint-{side_lower}-clavicle", lm.get(f"clavicle_{side}", (0.045 * scale * sign, -0.015 * scale, 1.348 * scale)))
        p_sh = lm.get(f"joint-{side_lower}-shoulder", lm.get(f"shoulder_{side}", (0.175 * scale * sign, -0.020 * scale, 1.340 * scale)))
        p_el = lm.get(f"joint-{side_lower}-elbow", lm.get(f"elbow_{side}", (0.280 * scale * sign, 0.015 * scale, 1.070 * scale)))
        # Enforce pre-bend +Y on elbow (posterior >= +0.015m)
        el_y = max(p_el[1], p_sh[1] + 0.015 * scale, cfg.elbow_prebend_y * scale, 0.015 * scale)
        p_el = (p_el[0], el_y, p_el[2])

        p_wr = lm.get(f"joint-{side_lower}-hand", lm.get(f"wrist_{side}", (0.360 * scale * sign, -0.020 * scale, 0.830 * scale)))

        # Upper arm midpoint for dual-bone twist
        p_arm_mid = (
            0.5 * (p_sh[0] + p_el[0]),
            0.5 * (p_sh[1] + p_el[1]),
            0.5 * (p_sh[2] + p_el[2]),
        )
        # Forearm midpoint for dual-bone twist
        p_fa_mid = (
            0.5 * (p_el[0] + p_wr[0]),
            0.5 * (p_el[1] + p_wr[1]),
            0.5 * (p_el[2] + p_wr[2]),
        )

        # Closed-form edit bone roll normalization for arm bones (pole target posterior in +Y)
        arm_pole = (p_el[0], p_el[1] + 0.50 * scale, p_el[2])
        roll_ua, roll_ua_twist, roll_fa, roll_fa_twist = 0.0, 0.0, 0.0, 0.0
        if solve_biomechanical_bone_roll is not None:
            try:
                roll_ua = solve_biomechanical_bone_roll(p_sh, p_arm_mid, arm_pole, f"DEF-upper_arm.{side}").roll_radians
                roll_ua_twist = solve_biomechanical_bone_roll(p_arm_mid, p_el, arm_pole, f"DEF-upper_arm.{side}.001").roll_radians
                roll_fa = solve_biomechanical_bone_roll(p_el, p_fa_mid, arm_pole, f"DEF-forearm.{side}").roll_radians
                roll_fa_twist = solve_biomechanical_bone_roll(p_fa_mid, p_wr, arm_pole, f"DEF-forearm.{side}.001").roll_radians
            except Exception:
                pass

        bones[f"DEF-shoulder.{side}"] = BoneDefinition(
            f"DEF-shoulder.{side}", p_clav, p_sh, parent="DEF-spine.003", category="body"
        )
        bones[f"DEF-upper_arm.{side}"] = BoneDefinition(
            f"DEF-upper_arm.{side}", p_sh, p_arm_mid, parent=f"DEF-shoulder.{side}", roll=roll_ua, category="body"
        )
        bones[f"DEF-upper_arm.{side}.001"] = BoneDefinition(
            f"DEF-upper_arm.{side}.001", p_arm_mid, p_el, parent=f"DEF-upper_arm.{side}", roll=roll_ua_twist, category="body"
        )
        bones[f"DEF-forearm.{side}"] = BoneDefinition(
            f"DEF-forearm.{side}", p_el, p_fa_mid, parent=f"DEF-upper_arm.{side}.001", roll=roll_fa, category="body"
        )
        bones[f"DEF-forearm.{side}.001"] = BoneDefinition(
            f"DEF-forearm.{side}.001", p_fa_mid, p_wr, parent=f"DEF-forearm.{side}", roll=roll_fa_twist, category="body"
        )
        p_hand_tail = lm.get(f"joint-{side_lower}-hand-2", (p_wr[0], p_wr[1] - 0.03 * scale, p_wr[2] - 0.04 * scale))
        bones[f"DEF-hand.{side}"] = BoneDefinition(
            f"DEF-hand.{side}", p_wr, p_hand_tail,
            parent=f"DEF-forearm.{side}.001", category="body"
        )

        # 10 Articulated Fingers (5 per hand, 3 phalanges each = 15 bones per side)
        digits_order = ["thumb", "f_index", "f_middle", "f_ring", "f_pinky"]
        has_mh_fingers = all(
            f"joint-{side_lower}-finger-{f_idx}-{ph}" in lm
            for f_idx in range(1, 6)
            for ph in range(1, 5)
        )

        if has_mh_fingers:
            for f_idx, d_name in enumerate(digits_order, start=1):
                b1 = lm[f"joint-{side_lower}-finger-{f_idx}-1"]
                b2 = lm[f"joint-{side_lower}-finger-{f_idx}-2"]
                b3 = lm[f"joint-{side_lower}-finger-{f_idx}-3"]
                b4 = lm[f"joint-{side_lower}-finger-{f_idx}-4"]
                bones[f"DEF-{d_name}.01.{side}"] = BoneDefinition(
                    f"DEF-{d_name}.01.{side}", b1, b2, parent=f"DEF-hand.{side}", category="body"
                )
                bones[f"DEF-{d_name}.02.{side}"] = BoneDefinition(
                    f"DEF-{d_name}.02.{side}", b2, b3, parent=f"DEF-{d_name}.01.{side}", category="body"
                )
                bones[f"DEF-{d_name}.03.{side}"] = BoneDefinition(
                    f"DEF-{d_name}.03.{side}", b3, b4, parent=f"DEF-{d_name}.02.{side}", category="body"
                )
        else:
            palm_center = bones[f"DEF-hand.{side}"].tail
            finger_configs = [
                ("thumb", 0.022 * sign, -0.015, -0.010, 0.052, 45.0),
                ("f_index", 0.012 * sign, -0.008, -0.035, 0.068, 15.0),
                ("f_middle", 0.002 * sign, -0.002, -0.040, 0.074, 5.0),
                ("f_ring", -0.008 * sign, 0.002, -0.036, 0.066, -8.0),
                ("f_pinky", -0.018 * sign, 0.006, -0.028, 0.054, -20.0),
            ]

            for d_name, ox, oy, oz, d_len, d_ang in finger_configs:
                rad_ang = math.radians(d_ang)
                dir_x = math.sin(rad_ang) * 0.15 * sign
                dir_y = -math.sin(rad_ang) * 0.30
                dir_z = -math.cos(rad_ang)
                norm_len = math.sqrt(dir_x * dir_x + dir_y * dir_y + dir_z * dir_z) or 1.0
                dx, dy, dz = dir_x / norm_len, dir_y / norm_len, dir_z / norm_len

                d_base_x = palm_center[0] + ox * scale
                d_base_y = palm_center[1] + oy * scale
                d_base_z = palm_center[2] + oz * scale

                seg_len = (d_len * scale) / 3.0
                prev_parent = f"DEF-hand.{side}"

                for ph in ["01", "02", "03"]:
                    ph_idx = int(ph) - 1
                    b_name = f"DEF-{d_name}.{ph}.{side}"
                    head_pt = (
                        d_base_x + dx * seg_len * ph_idx,
                        d_base_y + dy * seg_len * ph_idx,
                        d_base_z + dz * seg_len * ph_idx,
                    )
                    tail_pt = (
                        d_base_x + dx * seg_len * (ph_idx + 1),
                        d_base_y + dy * seg_len * (ph_idx + 1),
                        d_base_z + dz * seg_len * (ph_idx + 1),
                    )
                    bones[b_name] = BoneDefinition(b_name, head_pt, tail_pt, parent=prev_parent, category="body")
                    prev_parent = b_name

    # --------------------------------------------------------------------------
    # 3. LOWER LIMBS & FEET (12 DEF BONES) - BIOLOGICAL SKELETAL REALIGNMENT
    # --------------------------------------------------------------------------
    for side, sign in [("L", 1.0), ("R", -1.0)]:
        side_lower = side.lower()
        if f"pelvic_crest_{side}" in lm:
            z_pelvic = lm[f"pelvic_crest_{side}"][2]
        elif "spine_pelvis" in lm:
            z_pelvic = lm["spine_pelvis"][2] + 0.120 * scale
        else:
            z_pelvic = 0.945 * scale
        z_hip = z_pelvic - 0.082 * scale
        y_hip = -0.010 * scale
        x_hip = lm.get(f"hip_{side}", (sign * 0.088 * scale, y_hip, z_hip))[0]
        if abs(x_hip) > 0.090 * scale:
            x_hip = sign * 0.088 * scale
        p_hip = (x_hip, y_hip, z_hip)

        # 3b. Knee condylar hinge axis: Z = z_patella - 0.025m, Y = -0.008m (recessed behind patella)
        if f"patella_{side}" in lm:
            z_pat = lm[f"patella_{side}"][2]
        elif f"knee_{side}" in lm:
            z_pat = lm[f"knee_{side}"][2] + 0.025 * scale
        else:
            z_pat = 0.470 * scale
        z_knee = z_pat - 0.025 * scale
        p_kn_raw = lm.get(f"joint-{side_lower}-knee", lm.get(f"knee_{side}", (sign * 0.100 * scale, -0.018 * scale, z_knee)))
        kn_y = min(-0.018 * scale, p_kn_raw[1], cfg.knee_prebend_y * scale)
        p_kn = (p_kn_raw[0], kn_y, z_knee)

        # 3c. Oblique bimalleolar ankle axis: line connecting medial and lateral malleoli
        if f"malleolus_medial_{side}" in lm and f"malleolus_lateral_{side}" in lm:
            p_med = lm[f"malleolus_medial_{side}"]
            p_lat = lm[f"malleolus_lateral_{side}"]
        elif f"joint-{side_lower}-ankle" in lm:
            p_ak_lm = lm[f"joint-{side_lower}-ankle"]
            p_med = (p_ak_lm[0] - sign * 0.017 * scale, p_ak_lm[1] + 0.004 * scale, p_ak_lm[2] + 0.008 * scale)
            p_lat = (p_ak_lm[0] + sign * 0.017 * scale, p_ak_lm[1] - 0.004 * scale, p_ak_lm[2] - 0.004 * scale)
        else:
            p_med = (sign * 0.072 * scale, 0.002 * scale, 0.088 * scale)
            p_lat = (sign * 0.106 * scale, -0.006 * scale, 0.076 * scale)
        p_ak = (
            0.5 * (p_med[0] + p_lat[0]),
            0.5 * (p_med[1] + p_lat[1]),
            0.5 * (p_med[2] + p_lat[2]),
        )
        ankle_roll = sign * -0.156  # -8.95 deg tilt matching bimalleolar slant

        # 3d. Oblique MTP break axis: angled ~65 degrees across metatarsal heads
        p_mtp = (p_ak[0], -0.089 * scale, 0.022 * scale)
        p_toe_raw = lm.get(f"joint-{side_lower}-toe-1-4", lm.get(f"toe_{side}", (sign * 0.090 * scale, -0.145 * scale, 0.015 * scale)))
        p_toe = (p_toe_raw[0], p_toe_raw[1], min(p_toe_raw[2], 0.020 * scale))
        mtp_roll = sign * -0.153  # -8.74 deg roll aligning transverse arch drop

        # Thigh midpoint for dual-bone twist
        p_th_mid = (
            0.5 * (p_hip[0] + p_kn[0]),
            0.5 * (p_hip[1] + p_kn[1]),
            0.5 * (p_hip[2] + p_kn[2]),
        )
        # Shin midpoint for dual-bone twist
        p_sh_mid = (
            0.5 * (p_kn[0] + p_ak[0]),
            0.5 * (p_kn[1] + p_ak[1]),
            0.5 * (p_kn[2] + p_ak[2]),
        )

        # Closed-form edit bone roll normalization for leg bones (pole target anterior in -Y)
        leg_pole = (p_kn[0], p_kn[1] - 0.50 * scale, p_kn[2])
        roll_th, roll_th_twist, roll_sh, roll_sh_twist = 0.0, 0.0, 0.0, 0.0
        if solve_biomechanical_bone_roll is not None:
            try:
                roll_th = solve_biomechanical_bone_roll(p_hip, p_th_mid, leg_pole, f"DEF-thigh.{side}").roll_radians
                roll_th_twist = solve_biomechanical_bone_roll(p_th_mid, p_kn, leg_pole, f"DEF-thigh.{side}.001").roll_radians
                roll_sh = solve_biomechanical_bone_roll(p_kn, p_sh_mid, leg_pole, f"DEF-shin.{side}").roll_radians
                roll_sh_twist = solve_biomechanical_bone_roll(p_sh_mid, p_ak, leg_pole, f"DEF-shin.{side}.001").roll_radians
            except Exception:
                pass

        bones[f"DEF-thigh.{side}"] = BoneDefinition(
            f"DEF-thigh.{side}", p_hip, p_th_mid, parent="DEF-spine", roll=roll_th, category="body"
        )
        bones[f"DEF-thigh.{side}.001"] = BoneDefinition(
            f"DEF-thigh.{side}.001", p_th_mid, p_kn, parent=f"DEF-thigh.{side}", roll=roll_th_twist, category="body"
        )
        bones[f"DEF-shin.{side}"] = BoneDefinition(
            f"DEF-shin.{side}", p_kn, p_sh_mid, parent=f"DEF-thigh.{side}.001", roll=roll_sh, category="body"
        )
        bones[f"DEF-shin.{side}.001"] = BoneDefinition(
            f"DEF-shin.{side}.001", p_sh_mid, p_ak, parent=f"DEF-shin.{side}", roll=roll_sh_twist, category="body"
        )
        bones[f"DEF-foot.{side}"] = BoneDefinition(
            f"DEF-foot.{side}", p_ak, p_mtp, parent=f"DEF-shin.{side}.001", roll=ankle_roll, category="body"
        )
        bones[f"DEF-toe.{side}"] = BoneDefinition(
            f"DEF-toe.{side}",
            p_mtp,
            p_toe,
            parent=f"DEF-foot.{side}",
            roll=mtp_roll,
            category="body",
        )

    # --------------------------------------------------------------------------
    # 4. FACIAL DEFORMERS (99 DEF BONES)
    # --------------------------------------------------------------------------
    # 49 pairs (L & R = 98) + 1 midline jaw center = 99 facial DEF bones
    face_prefix_specs = [
        ("DEF-brow.B", 4, (0.015, -0.050, 0.60)),
        ("DEF-brow.T", 4, (0.015, -0.048, 0.63)),
        ("DEF-cheek.B", 2, (0.035, -0.045, 0.35)),
        ("DEF-cheek.T", 2, (0.038, -0.042, 0.42)),
        ("DEF-chin", 2, (0.015, -0.055, 0.05)),
        ("DEF-ear", 5, (0.075, 0.005, 0.45)),
        ("DEF-forehead", 4, (0.020, -0.035, 0.72)),
        ("DEF-jaw", 2, (0.025, -0.040, 0.12)),
        ("DEF-lid.B", 4, (0.025, -0.042, 0.46)),
        ("DEF-lid.T", 4, (0.025, -0.042, 0.50)),
        ("DEF-lip.B", 4, (0.012, -0.052, 0.18)),
        ("DEF-lip.T", 4, (0.012, -0.052, 0.23)),
        ("DEF-nose", 4, (0.008, -0.060, 0.38)),
        ("DEF-temple", 1, (0.055, -0.015, 0.58)),
        ("DEF-tongue", 3, (0.006, -0.020, 0.20)),
    ]

    h_head = p_crown[2] - p_chin[2]
    for prefix, count, rel_pos in face_prefix_specs:
        rx, ry, rz = rel_pos
        for s_side, s_sign in [("L", 1.0), ("R", -1.0)]:
            for idx in range(count):
                b_name = f"{prefix}.{s_side}.{idx:03d}"
                # Spread multiple indices along arc
                arc_offset_x = (idx - (count - 1.0) / 2.0) * (0.008 * scale * s_sign)
                arc_offset_z = (idx % 2) * (0.004 * scale)

                b_head_pt = (
                    s_sign * rx * scale + arc_offset_x,
                    ry * scale,
                    p_chin[2] + rz * h_head + arc_offset_z,
                )
                b_tail_pt = (
                    b_head_pt[0],
                    b_head_pt[1] - 0.015 * scale,
                    b_head_pt[2],
                )
                bones[b_name] = BoneDefinition(
                    b_name, b_head_pt, b_tail_pt, parent="DEF-head", category="facial"
                )

    # 1 Midline facial deformer: DEF-jaw.center (Total 98 + 1 = 99 facial DEF bones)
    bones["DEF-jaw.center"] = BoneDefinition(
        "DEF-jaw.center",
        (0.0, -0.065 * scale, p_chin[2] + 0.08 * h_head),
        (0.0, -0.075 * scale, p_chin[2] + 0.05 * h_head),
        parent="DEF-head",
        category="facial",
    )

    metarig.bones = bones

    # Assert integrity
    assert metarig.def_bone_count == 163, (
        f"Metarig generation defect: expected 163 DEF bones, got {metarig.def_bone_count}"
    )
    return metarig


def align_rigify_metarig_pivots(
    armature_obj: Any,
    landmarks: Dict[str, Tuple[float, float, float]],
    scale: float = 1.0,
) -> None:
    """
    Realigns 163 DEF Rigify metarig joint pivots to anatomical skeletal centers (Feature 7 of M1):
    - Femoral head hip joint: Z = z_pelvic_crest - 0.082m, Y = -0.010m
    - Condylar knee hinge: Z = z_patella - 0.025m, Y = -0.008m (behind patella)
    - Oblique bimalleolar ankle: connecting medial (Z=0.088m, Y=+0.002m) and lateral (Z=0.076m, Y=-0.006m) malleoli
    - MTP break axis: oblique angle ~65 degrees across metatarsal heads

    Operates polymorphically on:
    - MetarigStructure Python instances
    - Live Blender Armature objects (edit_bones or pose.bones)
    - Metarig bone dictionaries
    """
    s = scale
    for side, sign in [("L", 1.0), ("R", -1.0)]:
        # 1. Femoral head hip joint: raised +0.038m into true acetabular socket
        if f"pelvic_crest_{side}" in landmarks:
            z_pelvic = landmarks[f"pelvic_crest_{side}"][2]
        elif "spine_pelvis" in landmarks:
            z_pelvic = landmarks["spine_pelvis"][2] + 0.120 * s
        else:
            z_pelvic = 0.945 * s
        z_hip = z_pelvic - 0.082 * s
        y_hip = -0.010 * s
        x_hip = landmarks.get(f"hip_{side}", (sign * 0.088 * s, y_hip, z_hip))[0]
        if abs(x_hip) > 0.090 * s:
            x_hip = sign * 0.088 * s
        p_hip = (x_hip, y_hip, z_hip)

        # 2. Condylar knee hinge: recessed behind patella
        if f"patella_{side}" in landmarks:
            z_pat = landmarks[f"patella_{side}"][2]
        elif f"knee_{side}" in landmarks:
            z_pat = landmarks[f"knee_{side}"][2] + 0.025 * s
        else:
            z_pat = 0.470 * s
        z_knee = z_pat - 0.025 * s
        y_knee = landmarks.get(f"knee_{side}", (0, -0.018 * s, 0))[1]
        y_knee = min(y_knee, -0.018 * s)
        x_knee = landmarks.get(f"knee_{side}", (sign * 0.100 * s, y_knee, z_knee))[0]
        p_knee = (x_knee, y_knee, z_knee)

        # 3. Oblique bimalleolar ankle
        if f"malleolus_medial_{side}" in landmarks and f"malleolus_lateral_{side}" in landmarks:
            p_med = landmarks[f"malleolus_medial_{side}"]
            p_lat = landmarks[f"malleolus_lateral_{side}"]
        else:
            p_med = (sign * 0.072 * s, 0.002 * s, 0.088 * s)
            p_lat = (sign * 0.106 * s, -0.006 * s, 0.076 * s)
        p_ankle = (
            0.5 * (p_med[0] + p_lat[0]),
            0.5 * (p_med[1] + p_lat[1]),
            0.5 * (p_med[2] + p_lat[2]),
        )
        ankle_roll = sign * -0.156

        # 4. Oblique MTP break axis (~65 deg)
        p_mtp = (p_ankle[0], -0.089 * s, 0.022 * s)
        toe_tip = landmarks.get(f"toe_{side}", (sign * 0.090 * s, -0.145 * s, 0.015 * s))
        mtp_roll = sign * -0.153

        # Midpoints for dual-bone twist
        p_th_mid = (0.5 * (p_hip[0] + p_knee[0]), 0.5 * (p_hip[1] + p_knee[1]), 0.5 * (p_hip[2] + p_knee[2]))
        p_sh_mid = (0.5 * (p_knee[0] + p_ankle[0]), 0.5 * (p_knee[1] + p_ankle[1]), 0.5 * (p_knee[2] + p_ankle[2]))

        # Polymorphic application
        if isinstance(armature_obj, MetarigStructure):
            bones = armature_obj.bones
            if f"DEF-thigh.{side}" in bones:
                bones[f"DEF-thigh.{side}"].head = p_hip
                bones[f"DEF-thigh.{side}"].tail = p_th_mid
            if f"DEF-thigh.{side}.001" in bones:
                bones[f"DEF-thigh.{side}.001"].head = p_th_mid
                bones[f"DEF-thigh.{side}.001"].tail = p_knee
            if f"DEF-shin.{side}" in bones:
                bones[f"DEF-shin.{side}"].head = p_knee
                bones[f"DEF-shin.{side}"].tail = p_sh_mid
            if f"DEF-shin.{side}.001" in bones:
                bones[f"DEF-shin.{side}.001"].head = p_sh_mid
                bones[f"DEF-shin.{side}.001"].tail = p_ankle
            if f"DEF-foot.{side}" in bones:
                bones[f"DEF-foot.{side}"].head = p_ankle
                bones[f"DEF-foot.{side}"].tail = p_mtp
                bones[f"DEF-foot.{side}"].roll = ankle_roll
            if f"DEF-toe.{side}" in bones:
                bones[f"DEF-toe.{side}"].head = p_mtp
                bones[f"DEF-toe.{side}"].tail = toe_tip
                bones[f"DEF-toe.{side}"].roll = mtp_roll
        elif hasattr(armature_obj, "data") and hasattr(armature_obj.data, "edit_bones"):
            eb = armature_obj.data.edit_bones
            bone_specs = [
                (f"DEF-thigh.{side}", p_hip, p_th_mid, 0.0),
                (f"DEF-thigh.{side}.001", p_th_mid, p_knee, 0.0),
                (f"DEF-shin.{side}", p_knee, p_sh_mid, 0.0),
                (f"DEF-shin.{side}.001", p_sh_mid, p_ankle, 0.0),
                (f"DEF-foot.{side}", p_ankle, p_mtp, ankle_roll),
                (f"DEF-toe.{side}", p_mtp, toe_tip, mtp_roll),
            ]
            for b_n, h_pt, t_pt, r_val in bone_specs:
                if b_n in eb:
                    eb[b_n].head = h_pt
                    eb[b_n].tail = t_pt
                    eb[b_n].roll = r_val
        elif isinstance(armature_obj, dict):
            bone_specs = [
                (f"DEF-thigh.{side}", p_hip, p_th_mid, 0.0),
                (f"DEF-thigh.{side}.001", p_th_mid, p_knee, 0.0),
                (f"DEF-shin.{side}", p_knee, p_sh_mid, 0.0),
                (f"DEF-shin.{side}.001", p_sh_mid, p_ankle, 0.0),
                (f"DEF-foot.{side}", p_ankle, p_mtp, ankle_roll),
                (f"DEF-toe.{side}", p_mtp, toe_tip, mtp_roll),
            ]
            for b_n, h_pt, t_pt, r_val in bone_specs:
                if b_n in armature_obj:
                    armature_obj[b_n]["head"] = [round(c, 5) for c in h_pt]
                    armature_obj[b_n]["tail"] = [round(c, 5) for c in t_pt]
                    armature_obj[b_n]["roll"] = round(r_val, 5)



__all__ = [
    "BODY_DEF_BONES",
    "FACIAL_DEF_BONES",
    "ALL_163_DEF_BONES",
    "HumanRigConfig",
    "BoneDefinition",
    "MetarigStructure",
    "get_default_human_landmarks",
    "generate_rigify_human_metarig",
    "align_rigify_metarig_pivots",
]
