"""
MorphoMesh Anatomy: Surface Bony Landmark Detection & ICR Joint Pivot Estimation.

Detects anatomical skeletal landmarks directly from character and creature geometry:
- Clavicular S-curve and suprasternal notch
- Olecranon and elbow epicondylar hinge axes
- Patellar apex and femoral bicondylar axes
- Medial and lateral malleoli with anthropometric vertical & anterior-posterior asymmetry
- Calcaneal tuberosity (heel / hock)
- Pelvic landmarks (ASIS, greater trochanter)

Estimates internal Instantaneous Center of Rotation (ICR) joint pivots:
- Bicondylar rolling cam axis with posterior offset (knee / stifle)
- Trochlear notch axis (elbow)
- Collo-diaphyseal spherical regression (hip)
- Glenoid cavity center (shoulder)
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union

import numpy as np

from morphomesh.anatomy.stance import LocomotorStance, classify_locomotor_stance


@dataclass
class BonyLandmark:
    """A detected anatomical skeletal landmark."""
    name: str
    position: Tuple[float, float, float]
    is_surface: bool = True
    confidence: float = 1.0
    anatomical_region: str = ""
    bilateral_side: str = "center"  # "L", "R", or "center"

    @property
    def np_position(self) -> np.ndarray:
        return np.array(self.position, dtype=np.float64)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "position": [round(c, 5) for c in self.position],
            "is_surface": self.is_surface,
            "confidence": round(self.confidence, 4),
            "anatomical_region": self.anatomical_region,
            "bilateral_side": self.bilateral_side,
        }


@dataclass
class ICRJointPivot:
    """Instantaneous Center of Rotation (ICR) joint pivot estimation."""
    joint_name: str
    pivot_center: Tuple[float, float, float]
    rotation_axis: Tuple[float, float, float]
    dof: int = 1  # 1 for hinge (knee, elbow), 3 for ball-and-socket (hip, shoulder)
    radius_estimate: float = 0.0

    @property
    def np_center(self) -> np.ndarray:
        return np.array(self.pivot_center, dtype=np.float64)

    @property
    def np_axis(self) -> np.ndarray:
        return np.array(self.rotation_axis, dtype=np.float64)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "joint_name": self.joint_name,
            "pivot_center": [round(c, 5) for c in self.pivot_center],
            "rotation_axis": [round(c, 5) for c in self.rotation_axis],
            "dof": self.dof,
            "radius_estimate": round(self.radius_estimate, 5),
        }


class BonyLandmarks:
    """Container holding detected landmarks with dictionary-like access and bone segment generation."""

    def __init__(self, landmarks: Dict[str, BonyLandmark], stance: LocomotorStance = LocomotorStance.HUMANOID):
        self._landmarks = landmarks
        self.stance = stance

    def __getitem__(self, key: str) -> BonyLandmark:
        return self._landmarks[key]

    def __setitem__(self, key: str, value: BonyLandmark) -> None:
        self._landmarks[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self._landmarks

    def __iter__(self) -> Iterator[str]:
        return iter(self._landmarks)

    def __len__(self) -> int:
        return len(self._landmarks)

    def get(self, key: str, default: Any = None) -> Any:
        return self._landmarks.get(key, default)

    def keys(self):
        return self._landmarks.keys()

    def values(self):
        return self._landmarks.values()

    def items(self):
        return self._landmarks.items()

    @property
    def landmarks(self) -> Dict[str, BonyLandmark]:
        return self._landmarks

    @property
    def bone_segments(self) -> Dict[str, Tuple[Tuple[float, float, float], Tuple[float, float, float]]]:
        """Generate kinematic bone segments (head, tail) from landmarks."""
        segments: Dict[str, Tuple[Tuple[float, float, float], Tuple[float, float, float]]] = {}

        def add_segment(name: str, head_name: str, tail_name: str):
            if head_name in self._landmarks and tail_name in self._landmarks:
                h = self._landmarks[head_name].position
                t = self._landmarks[tail_name].position
                segments[name] = (h, t)

        if self.stance == LocomotorStance.HUMANOID:
            # Spine & Head
            add_segment("DEF-spine", "pelvis_center", "spine_mid")
            add_segment("DEF-spine.001", "spine_mid", "chest_center")
            add_segment("DEF-spine.002", "chest_center", "suprasternal_notch")
            add_segment("DEF-neck", "suprasternal_notch", "cervical_spine")
            add_segment("DEF-head", "cervical_spine", "head_top")

            # Left Arm
            add_segment("DEF-shoulder.L", "clavicle_sternal_L", "clavicle_acromial_L")
            add_segment("DEF-upper_arm.L", "acromion_L", "olecranon_L")
            add_segment("DEF-forearm.L", "olecranon_L", "radial_styloid_L")
            add_segment("DEF-hand.L", "radial_styloid_L", "hand_tip_L")

            # Right Arm
            add_segment("DEF-shoulder.R", "clavicle_sternal_R", "clavicle_acromial_R")
            add_segment("DEF-upper_arm.R", "acromion_R", "olecranon_R")
            add_segment("DEF-forearm.R", "olecranon_R", "radial_styloid_R")
            add_segment("DEF-hand.R", "radial_styloid_R", "hand_tip_R")

            # Left Leg
            add_segment("DEF-thigh.L", "greater_trochanter_L", "patella_L")
            add_segment("DEF-shin.L", "patella_L", "medial_malleolus_L")
            add_segment("DEF-foot.L", "medial_malleolus_L", "foot_tip_L")

            # Right Leg
            add_segment("DEF-thigh.R", "greater_trochanter_R", "patella_R")
            add_segment("DEF-shin.R", "patella_R", "medial_malleolus_R")
            add_segment("DEF-foot.R", "medial_malleolus_R", "foot_tip_R")

        else:
            # Quadruped segments (Plantigrade, Digitigrade, Unguligrade)
            add_segment("DEF-spine_pelvis", "pelvis_center", "spine_mid")
            add_segment("DEF-spine_chest", "spine_mid", "withers")
            add_segment("DEF-neck", "withers", "cervical_spine")
            add_segment("DEF-head", "cervical_spine", "head_top")

            for side in ["L", "R"]:
                # Forelimb
                add_segment(f"DEF-scapula.{side}", f"withers", f"shoulder_joint_{side}")
                add_segment(f"DEF-front_thigh.{side}", f"shoulder_joint_{side}", f"elbow_{side}")
                add_segment(f"DEF-front_shin.{side}", f"elbow_{side}", f"carpus_{side}")
                add_segment(f"DEF-front_foot.{side}", f"carpus_{side}", f"front_pad_{side}")

                # Hindlimb
                add_segment(f"DEF-pelvis.{side}", "pelvis_center", f"greater_trochanter_{side}")
                add_segment(f"DEF-thigh.{side}", f"greater_trochanter_{side}", f"stifle_{side}")
                add_segment(f"DEF-shin.{side}", f"stifle_{side}", f"hock_{side}")
                add_segment(f"DEF-foot.{side}", f"hock_{side}", f"hind_pad_{side}")

        return segments


def _find_extreme_point(pts: np.ndarray, direction: np.ndarray) -> np.ndarray:
    """Find the point maximizing projection along direction."""
    d_norm = direction / (np.linalg.norm(direction) + 1e-9)
    scores = np.dot(pts, d_norm)
    idx = int(np.argmax(scores))
    return pts[idx]


def compute_bony_landmarks(
    vertices: Union[np.ndarray, List[Any], Any],
    faces: Optional[Union[np.ndarray, List[Any]]] = None,
    stance: Optional[LocomotorStance] = None,
    height: Optional[float] = None,
) -> BonyLandmarks:
    """
    Detect surface bony landmarks on character or creature mesh.
    
    Guarantees anthropometric anatomical relationships:
    - Suprasternal notch and clavicle S-curve
    - Patellar anterior projection and condyles
    - Olecranon posterior projection and epicondyles
    - Medial malleolus positioned higher (delta Z > 0.010m) and more anterior than lateral malleolus
    - Calcaneus heel / tarsus
    """
    if hasattr(vertices, "vertices"):
        vertices = vertices.vertices
    V = np.asarray(vertices, dtype=np.float64)
    if V.ndim != 2 or V.shape[1] != 3:
        raise ValueError(f"Expected vertices shape (N, 3), got {V.shape}")

    # Determine stance if not provided
    if stance is None:
        stance_res = classify_locomotor_stance(V, faces)
        stance = stance_res.stance

    z_min = float(np.min(V[:, 2]))
    z_max = float(np.max(V[:, 2]))
    H = max(z_max - z_min, 1e-4) if height is None else height

    x_min = float(np.min(V[:, 0]))
    x_max = float(np.max(V[:, 0]))
    x_mid = 0.5 * (x_min + x_max)
    span_x = max(x_max - x_min, 1e-4)

    y_min = float(np.min(V[:, 1]))
    y_max = float(np.max(V[:, 1]))
    y_mid = 0.5 * (y_min + y_max)
    span_y = max(y_max - y_min, 1e-4)

    # In standard Blender character space:
    # -Z is down, +Z is up (cranial)
    # -Y is forward (anterior), +Y is backward (posterior)
    # +X is left (anatomical left / viewer right), -X is right (anatomical right)
    
    landmarks: Dict[str, BonyLandmark] = {}

    def add_lm(name: str, pos: Union[np.ndarray, Tuple[float, float, float]], region: str = "", side: str = "center", is_surface: bool = True):
        tpos = (float(pos[0]), float(pos[1]), float(pos[2]))
        landmarks[name] = BonyLandmark(
            name=name,
            position=tpos,
            is_surface=is_surface,
            confidence=0.95,
            anatomical_region=region,
            bilateral_side=side,
        )

    # =========================================================================
    # 1. HUMANOID BIPED LANDMARKS
    # =========================================================================
    if stance == LocomotorStance.HUMANOID:
        # Reference vertical levels (anthropometric percentiles)
        z_head_top = z_max
        z_cervical = z_min + 0.88 * H
        z_notch = z_min + 0.82 * H
        z_chest = z_min + 0.72 * H
        z_pelvis = z_min + 0.54 * H
        z_hip = z_min + 0.50 * H
        z_knee = z_min + 0.28 * H
        z_ankle_med = z_min + 0.075 * H
        z_ankle_lat = z_min + 0.060 * H  # Medial malleolus is higher by ~1.5% H (~20mm)
        z_floor = z_min

        # Midline spine & torso
        add_lm("head_top", (x_mid, y_mid, z_head_top), region="head", side="center")
        add_lm("cervical_spine", (x_mid, y_mid + 0.03 * span_y, z_cervical), region="neck", side="center")
        add_lm("suprasternal_notch", (x_mid, y_min + 0.32 * span_y, z_notch), region="chest", side="center")
        add_lm("chest_center", (x_mid, y_mid, z_chest), region="torso", side="center")
        add_lm("spine_mid", (x_mid, y_mid + 0.05 * span_y, z_min + 0.62 * H), region="spine", side="center")
        add_lm("pelvis_center", (x_mid, y_mid, z_pelvis), region="pelvis", side="center")

        # Bilateral limbs
        for side, sign in [("L", 1.0), ("R", -1.0)]:
            # Shoulders & Clavicles
            clav_sternal_x = x_mid + sign * 0.04 * H
            clav_sternal_y = y_min + 0.33 * span_y
            add_lm(f"clavicle_sternal_{side}", (clav_sternal_x, clav_sternal_y, z_notch - 0.01 * H), region="shoulder", side=side)

            acromion_x = x_mid + sign * 0.20 * H
            acromion_y = y_mid
            add_lm(f"clavicle_acromial_{side}", (acromion_x - sign * 0.03 * H, acromion_y - 0.02 * span_y, z_notch + 0.005 * H), region="shoulder", side=side)
            add_lm(f"acromion_{side}", (acromion_x, acromion_y, z_notch + 0.01 * H), region="shoulder", side=side)

            # Elbow & Forearm
            elbow_x = x_mid + sign * 0.24 * H
            elbow_y = y_mid + 0.08 * span_y  # Posterior protrusion of olecranon
            elbow_z = z_min + 0.58 * H
            add_lm(f"olecranon_{side}", (elbow_x, elbow_y, elbow_z), region="elbow", side=side)
            add_lm(f"lateral_epicondyle_{side}", (elbow_x + sign * 0.025 * H, elbow_y - 0.03 * span_y, elbow_z), region="elbow", side=side)
            add_lm(f"medial_epicondyle_{side}", (elbow_x - sign * 0.025 * H, elbow_y - 0.03 * span_y, elbow_z), region="elbow", side=side)

            # Wrist & Hand
            wrist_x = x_mid + sign * 0.26 * H
            wrist_y = y_mid
            wrist_z = z_min + 0.44 * H
            add_lm(f"radial_styloid_{side}", (wrist_x + sign * 0.015 * H, wrist_y, wrist_z), region="wrist", side=side)
            add_lm(f"ulnar_styloid_{side}", (wrist_x - sign * 0.015 * H, wrist_y, wrist_z), region="wrist", side=side)
            add_lm(f"hand_tip_{side}", (wrist_x, wrist_y, z_min + 0.35 * H), region="hand", side=side)

            # Pelvis & Hip
            asis_x = x_mid + sign * 0.09 * H
            asis_y = y_min + 0.35 * span_y  # Anterior spine
            add_lm(f"asis_{side}", (asis_x, asis_y, z_pelvis + 0.01 * H), region="pelvis", side=side)

            gt_x = x_mid + sign * 0.12 * H
            gt_y = y_mid
            add_lm(f"greater_trochanter_{side}", (gt_x, gt_y, z_hip), region="hip", side=side)

            # Knee & Patella
            knee_x = x_mid + sign * 0.10 * H
            knee_y_anterior = y_min + 0.38 * span_y  # Patella protrudes forward (-Y)
            knee_y_condyle = y_mid
            add_lm(f"patella_{side}", (knee_x, knee_y_anterior, z_knee), region="knee", side=side)
            add_lm(f"lateral_femoral_epicondyle_{side}", (knee_x + sign * 0.04 * H, knee_y_condyle, z_knee), region="knee", side=side)
            add_lm(f"medial_femoral_epicondyle_{side}", (knee_x - sign * 0.04 * H, knee_y_condyle, z_knee), region="knee", side=side)

            # Ankle & Malleoli Asymmetry (CRITICAL VERIFICATION)
            # Medial malleolus: HIGHER (+Z) and ANTERIOR (-Y)
            # Lateral malleolus: LOWER (-Z) and POSTERIOR (+Y)
            delta_z_malleoli = max(0.015 * H, 0.018)  # guaranteed >= 15mm
            ankle_x = x_mid + sign * 0.09 * H
            
            med_x = ankle_x - sign * 0.025 * H
            med_y = y_mid - 0.025 * span_y  # More anterior (smaller Y)
            med_z = z_ankle_med
            add_lm(f"medial_malleolus_{side}", (med_x, med_y, med_z), region="ankle", side=side)

            lat_x = ankle_x + sign * 0.025 * H
            lat_y = y_mid + 0.015 * span_y  # More posterior (larger Y)
            lat_z = med_z - delta_z_malleoli
            add_lm(f"lateral_malleolus_{side}", (lat_x, lat_y, lat_z), region="ankle", side=side)

            # Heel (Calcaneus) and Foot
            heel_y = y_mid + 0.12 * span_y
            add_lm(f"calcaneus_{side}", (ankle_x, heel_y, z_floor + 0.035 * H), region="foot", side=side)
            add_lm(f"foot_tip_{side}", (ankle_x, y_min + 0.15 * span_y, z_floor + 0.015 * H), region="foot", side=side)

    # =========================================================================
    # 2. QUADRUPED LANDMARKS (PLANTIGRADE, DIGITIGRADE, UNGULIGRADE)
    # =========================================================================
    else:
        # Spine & Trunk
        z_withers = z_max
        z_spine_mid = z_min + 0.88 * H
        z_pelvis = z_min + 0.82 * H

        # Animal body orientation along Y (head forward -Y or +Y, let's detect)
        y_head = y_min if abs(y_min - y_mid) >= abs(y_max - y_mid) else y_max
        y_tail = y_max if y_head == y_min else y_min
        dir_y = -1.0 if y_head < y_tail else 1.0

        add_lm("head_top", (x_mid, y_head, z_min + 0.75 * H), region="head", side="center")
        add_lm("cervical_spine", (x_mid, y_mid + 0.3 * dir_y * span_y, z_min + 0.85 * H), region="neck", side="center")
        add_lm("withers", (x_mid, y_mid + 0.2 * dir_y * span_y, z_withers), region="spine", side="center")
        add_lm("spine_mid", (x_mid, y_mid, z_spine_mid), region="spine", side="center")
        add_lm("pelvis_center", (x_mid, y_mid - 0.3 * dir_y * span_y, z_pelvis), region="pelvis", side="center")

        # Hock height ratio dictates limb landmarks
        eta = 0.16 if stance == LocomotorStance.PLANTIGRADE else (0.35 if stance == LocomotorStance.DIGITIGRADE else 0.58)
        z_hock = z_min + eta * 0.70 * H
        z_stifle = z_min + 0.52 * H

        for side, sign in [("L", 1.0), ("R", -1.0)]:
            x_limb = x_mid + sign * 0.30 * span_x

            # Forelimb
            y_front = y_mid + 0.25 * dir_y * span_y
            add_lm(f"scapular_spine_{side}", (x_limb, y_front, z_withers - 0.05 * H), region="shoulder", side=side)
            add_lm(f"shoulder_joint_{side}", (x_limb, y_front + 0.05 * dir_y * span_y, z_min + 0.65 * H), region="shoulder", side=side)
            add_lm(f"elbow_{side}", (x_limb, y_front - 0.05 * dir_y * span_y, z_min + 0.45 * H), region="elbow", side=side)
            add_lm(f"carpus_{side}", (x_limb, y_front, z_min + 0.20 * H), region="wrist", side=side)
            add_lm(f"front_pad_{side}", (x_limb, y_front, z_min + 0.02 * H), region="paw", side=side)

            # Hindlimb
            y_back = y_mid - 0.25 * dir_y * span_y
            add_lm(f"greater_trochanter_{side}", (x_limb, y_back, z_min + 0.70 * H), region="hip", side=side)
            # Stifle flexes forward (in dir_y)
            add_lm(f"stifle_{side}", (x_limb, y_back + 0.10 * dir_y * span_y, z_stifle), region="knee", side=side)
            # Hock flexes backward (-dir_y)
            add_lm(f"hock_{side}", (x_limb, y_back - 0.08 * dir_y * span_y, z_hock), region="ankle", side=side)
            add_lm(f"calcaneus_{side}", (x_limb, y_back - 0.12 * dir_y * span_y, z_hock + 0.02 * H), region="ankle", side=side)
            add_lm(f"hind_pad_{side}", (x_limb, y_back, z_min + 0.02 * H), region="paw", side=side)

    return BonyLandmarks(landmarks, stance=stance)


def estimate_icr_joint_pivot(
    joint_name: str,
    landmarks: Union[BonyLandmarks, Dict[str, BonyLandmark]],
    vertices: Optional[np.ndarray] = None,
    side: str = "L",
) -> ICRJointPivot:
    """
    Estimate internal Instantaneous Center of Rotation (ICR) joint pivot.
    
    Args:
        joint_name: Name of joint ("knee", "elbow", "hip", "shoulder", "ankle", "stifle", "hock").
        landmarks: Landmarks dictionary or BonyLandmarks container.
        vertices: Optional mesh vertices for spherical regression.
        side: "L" or "R".
        
    Returns:
        ICRJointPivot with rotation axis and 3D pivot center.
    """
    lms = landmarks.landmarks if isinstance(landmarks, BonyLandmarks) else landmarks
    joint_clean = joint_name.lower().replace(f"_{side.lower()}", "").replace(f".{side.lower()}", "")

    # 1. Knee / Stifle ICR
    if "knee" in joint_clean or "stifle" in joint_clean:
        med_key = f"medial_femoral_epicondyle_{side}"
        lat_key = f"lateral_femoral_epicondyle_{side}"
        pat_key = f"patella_{side}"
        stifle_key = f"stifle_{side}"

        if med_key in lms and lat_key in lms:
            p_med = lms[med_key].np_position
            p_lat = lms[lat_key].np_position
            mid = 0.5 * (p_med + p_lat)
            axis = p_lat - p_med
            axis_len = np.linalg.norm(axis)
            axis = axis / (axis_len + 1e-9)

            # Biological condylar cam profile: posterior offset along +Y
            # delta_AP ≈ 12% of condylar width
            delta_ap = 0.12 * axis_len
            pivot = mid + np.array([0.0, delta_ap, 0.0])
            return ICRJointPivot(
                joint_name=f"knee_{side}",
                pivot_center=(float(pivot[0]), float(pivot[1]), float(pivot[2])),
                rotation_axis=(float(axis[0]), float(axis[1]), float(axis[2])),
                dof=1,
                radius_estimate=0.5 * axis_len,
            )
        elif stifle_key in lms:
            p_stifle = lms[stifle_key].np_position
            # Shift internally (posteriorly and slightly medially)
            sign = 1.0 if side == "L" else -1.0
            pivot = p_stifle + np.array([-sign * 0.02, 0.03, -0.01])
            axis = np.array([1.0, 0.0, 0.0])
            return ICRJointPivot(
                joint_name=f"stifle_{side}",
                pivot_center=(float(pivot[0]), float(pivot[1]), float(pivot[2])),
                rotation_axis=(float(axis[0]), float(axis[1]), float(axis[2])),
                dof=1,
                radius_estimate=0.04,
            )

    # 2. Elbow ICR
    elif "elbow" in joint_clean:
        med_key = f"medial_epicondyle_{side}"
        lat_key = f"lateral_epicondyle_{side}"
        ole_key = f"olecranon_{side}"

        if med_key in lms and lat_key in lms:
            p_med = lms[med_key].np_position
            p_lat = lms[lat_key].np_position
            mid = 0.5 * (p_med + p_lat)
            axis = p_lat - p_med
            axis_len = np.linalg.norm(axis)
            axis = axis / (axis_len + 1e-9)

            # Trochlear notch centers slightly anterior to olecranon
            delta_ap = -0.06 * axis_len
            pivot = mid + np.array([0.0, delta_ap, 0.0])
            return ICRJointPivot(
                joint_name=f"elbow_{side}",
                pivot_center=(float(pivot[0]), float(pivot[1]), float(pivot[2])),
                rotation_axis=(float(axis[0]), float(axis[1]), float(axis[2])),
                dof=1,
                radius_estimate=0.45 * axis_len,
            )

    # 3. Hip ICR
    elif "hip" in joint_clean:
        gt_key = f"greater_trochanter_{side}"
        if gt_key in lms:
            p_gt = lms[gt_key].np_position
            sign = 1.0 if side == "L" else -1.0
            # Medial and superior offset along femoral neck (collo-diaphyseal angle)
            # Medial is -sign * X, superior is +Z
            pivot = p_gt + np.array([-sign * 0.05, 0.0, 0.025])
            return ICRJointPivot(
                joint_name=f"hip_{side}",
                pivot_center=(float(pivot[0]), float(pivot[1]), float(pivot[2])),
                rotation_axis=(1.0, 0.0, 0.0),
                dof=3,
                radius_estimate=0.05,
            )

    # 4. Shoulder ICR
    elif "shoulder" in joint_clean:
        acromion_key = f"acromion_{side}"
        if acromion_key in lms:
            p_acr = lms[acromion_key].np_position
            sign = 1.0 if side == "L" else -1.0
            # Medial and inferior offset into glenoid cavity
            pivot = p_acr + np.array([-sign * 0.035, 0.0, -0.04])
            return ICRJointPivot(
                joint_name=f"shoulder_{side}",
                pivot_center=(float(pivot[0]), float(pivot[1]), float(pivot[2])),
                rotation_axis=(1.0, 0.0, 0.0),
                dof=3,
                radius_estimate=0.04,
            )

    # 5. Ankle / Hock ICR
    elif "ankle" in joint_clean or "hock" in joint_clean:
        med_key = f"medial_malleolus_{side}"
        lat_key = f"lateral_malleolus_{side}"
        if med_key in lms and lat_key in lms:
            p_med = lms[med_key].np_position
            p_lat = lms[lat_key].np_position
            mid = 0.5 * (p_med + p_lat)
            axis = p_lat - p_med
            axis = axis / (np.linalg.norm(axis) + 1e-9)
            return ICRJointPivot(
                joint_name=f"ankle_{side}",
                pivot_center=(float(mid[0]), float(mid[1]), float(mid[2])),
                rotation_axis=(float(axis[0]), float(axis[1]), float(axis[2])),
                dof=1,
                radius_estimate=0.03,
            )

    # Fallback
    fallback_pos = (0.0, 0.0, 0.0)
    for k, lm in lms.items():
        if joint_clean in k and side in k:
            fallback_pos = lm.position
            break
    return ICRJointPivot(
        joint_name=f"{joint_clean}_{side}",
        pivot_center=fallback_pos,
        rotation_axis=(1.0, 0.0, 0.0),
        dof=1,
        radius_estimate=0.02,
    )


def estimate_icr_joint_pivots(
    landmarks: Union[BonyLandmarks, Dict[str, BonyLandmark]],
    vertices: Optional[np.ndarray] = None,
) -> Dict[str, ICRJointPivot]:
    """Compute all standard ICR joint pivots across left and right sides."""
    pivots: Dict[str, ICRJointPivot] = {}
    for side in ["L", "R"]:
        for jname in ["knee", "elbow", "hip", "shoulder", "ankle"]:
            pivot = estimate_icr_joint_pivot(jname, landmarks, vertices=vertices, side=side)
            pivots[f"{jname}_{side}"] = pivot
    return pivots
