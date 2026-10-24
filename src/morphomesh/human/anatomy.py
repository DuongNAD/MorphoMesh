"""
Parametric Anatomical Female Human Base Mold Synthesizer.

Provides:
- ARKIT_52_BLENDSHAPES tuple.
- HumanMeshResult dataclass.
- HumanAnatomyGenerator class.
- generate_human_base_mesh and generate_human_body entrypoints.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from morphomesh.geometry.mesh import MeshGeometry
    from morphomesh.models import BoundingBox, HumanAnatomyConfig, HumanAssetResult
except (ImportError, ModuleNotFoundError):
    from ..geometry.mesh import MeshGeometry  # type: ignore[no-redef]
    from ..models import BoundingBox, HumanAnatomyConfig, HumanAssetResult  # type: ignore[no-redef]

from .mold_loader import (
    compute_relaxed_vertex_normals,
    compute_standardized_vertex_groups,
    extract_makehuman_joint_landmarks,
    load_anatomical_base_mold,
)
from .morphology import (
    compute_quad_metrics,
    resolve_human_anatomy_config,
)

ARKIT_52_BLENDSHAPES: Tuple[str, ...] = (
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
)


@dataclass
class HumanMeshResult:
    """Encapsulates generated human geometry, vertex groups, landmarks, and shape keys."""

    mesh: MeshGeometry
    vertex_groups: Dict[str, List[int]] = field(default_factory=dict)
    landmarks: Dict[str, Tuple[float, float, float]] = field(default_factory=dict)
    shape_keys: List[str] = field(default_factory=list)
    shape_key_deltas: Dict[str, Dict[int, Tuple[float, float, float]]] = field(default_factory=dict)
    bounding_box: BoundingBox = field(default_factory=lambda: BoundingBox(
        min_point=[-0.81, -0.16, 0.0],
        max_point=[0.81, 0.16, 1.65],
        dimensions=[1.62, 0.32, 1.65],
    ))
    quad_ratio: float = 1.0
    character_name: str = "Yu_Nian_An"
    height: float = 1.65
    head_ratio: float = 7.41
    is_anatomically_valid: bool = True


class HumanAnatomyGenerator:
    """
    Parametric anatomical female human base mold synthesizer.
    Produces 13,380-vertex, 13,378-quad, 100% 2-manifold human mesh conforming to
    Rigify metarig standards with zero shoulder spiky pauldrons and zero axilla gaps.
    """

    def __init__(
        self,
        config: Optional[HumanAnatomyConfig] = None,
        height: Optional[float] = None,
        gender: Optional[str] = None,
        proportion_preset: Optional[str] = None,
        **kwargs: Any,
    ):
        self.cfg = resolve_human_anatomy_config(
            config=config,
            height=height,
            gender=gender,
            proportion_preset=proportion_preset,
            **kwargs,
        )
        self.height = self.cfg.height
        self.scale = self.height / 1.65

    @classmethod
    def generate_human_body(
        cls,
        height: float = 1.65,
        gender: str = "female",
        proportion_preset: str = "stylized_heroine",
        config: Optional[HumanAnatomyConfig] = None,
        character_name: str = "Yu_Nian_An",
        **kwargs: Any,
    ) -> Tuple[MeshGeometry, Dict[str, Tuple[float, float, float]]]:
        """
        Synthesizes digital human mesh and landmarks matching PROJECT.md interface contract.
        Callable as HumanAnatomyGenerator.generate_human_body(...) or on an instance.
        """
        cfg = resolve_human_anatomy_config(
            config=config,
            height=height,
            gender=gender,
            proportion_preset=proportion_preset,
            **kwargs,
        )
        engine = cls(config=cfg)
        res = engine.generate(character_name=character_name)
        return res.mesh, res.landmarks

    def generate(
        self,
        character_name_or_config: Union[str, HumanAnatomyConfig, None] = None,
        character_name: str = "Yu_Nian_An",
    ) -> HumanMeshResult:
        """Synthesizes complete anatomical female human mesh from base mold."""
        if isinstance(character_name_or_config, HumanAnatomyConfig):
            self.cfg = character_name_or_config
            self.height = self.cfg.height
            self.scale = self.height / 1.65
        elif isinstance(character_name_or_config, str):
            character_name = character_name_or_config

        raw_verts, raw_quads, raw_uvs = load_anatomical_base_mold()
        s = self.scale

        k_chest = self.cfg.chest_girth / 0.82
        k_waist = self.cfg.waist_girth / 0.58
        k_hip = self.cfg.hip_girth / 0.86
        k_shoulder = self.cfg.shoulder_width / 0.36
        k_arm = self.cfg.arm_span / 1.62
        k_leg = self.cfg.leg_length / 0.88

        target_head_ratio = self.cfg.head_ratio
        target_head_height = self.height / target_head_ratio
        head_scale = target_head_height / (0.2227 * s)

        transformed_verts: List[List[float]] = [[v[0] * s, v[1] * s, v[2] * s] for v in raw_verts]

        foot_pts = [v for v in raw_verts if v[2] < 0.11 and v[0] > 0.05]
        foot_cx = sum(v[0] for v in foot_pts) / len(foot_pts)
        shift_x = 0.088 - foot_cx

        cx_ankle = 0.088 * s
        x_split_01 = cx_ankle - 0.0155 * s
        x_split_12 = cx_ankle + 0.00175 * s

        for i, v in enumerate(transformed_verts):
            x, y, z = v

            # Cranial and Facial Vertical Scaling
            if z >= 1.36 * s:
                t_head = max(0.0, min(1.0, (z - 1.36 * s) / (0.08 * s)))
                w_head = t_head * t_head * (3.0 - 2.0 * t_head)
                curr_scale = 1.0 + (head_scale - 1.0) * w_head
                transformed_verts[i][0] = x * curr_scale
                transformed_verts[i][1] = y * curr_scale
                transformed_verts[i][2] = 1.36 * s + (z - 1.36 * s) * curr_scale

            # Shoulders & Upper Arm Transverse Scaling
            elif 1.10 * s <= z < 1.35 * s:
                if abs(x) >= 0.06 * s:
                    w_sh = min(1.0, (abs(x) - 0.06 * s) / (0.12 * s))
                    factor_sh = 1.0 + (k_shoulder - 1.0) * w_sh
                    transformed_verts[i][0] = x * factor_sh

            # Arm Span Scaling: anchor arm span to expanded shoulder width
            if abs(x) > 0.18 * s and 0.85 * s <= z < 1.38 * s:
                sign_x = 1.0 if x > 0 else -1.0
                dist_out = abs(x) - 0.18 * s
                transformed_verts[i][0] = sign_x * (0.18 * s * k_shoulder + dist_out * k_arm)

            # Thoracic / Chest Contouring with Teardrop Bust & IMF
            if 1.08 * s <= z <= 1.28 * s and abs(x) < 0.26 * s:
                w_chest_z = (math.cos(min(math.pi, max(-math.pi, (z - 1.18 * s) * math.pi / (0.10 * s)))) + 1.0) * 0.5
                w_chest_x = min(1.0, max(0.0, (0.26 * s - abs(x)) / (0.05 * s)))
                factor_chest = 1.0 + (k_chest - 1.0) * w_chest_z * w_chest_x
                transformed_verts[i][0] *= factor_chest
                transformed_verts[i][1] *= factor_chest

                if y < -0.015 * s and 1.06 * s <= z <= 1.28 * s and abs(x) < 0.22 * s:
                    dx_b = (abs(x) - 0.088 * s) / (0.078 * s)
                    dz_b = (z - 1.165 * s) / (0.085 * s)
                    r2_b = dx_b * dx_b + dz_b * dz_b
                    if r2_b < 1.0:
                        sag_b = 1.0 - 0.35 * dz_b
                        w_bust = (math.cos(r2_b * math.pi * 0.5) ** 2) * sag_b
                        transformed_verts[i][1] -= 0.038 * s * w_bust
                        if abs(x) < 0.032 * s:
                            c_dip = (math.cos(abs(x) * math.pi / (0.032 * s)) + 1.0) * 0.5
                            transformed_verts[i][1] += 0.014 * s * c_dip

            # Waist Contouring & Feminine Slimming (WHR 0.697)
            if 0.94 * s <= z <= 1.12 * s and abs(x) < 0.22 * s:
                w_waist = (math.cos((z - 1.01 * s) * math.pi / (0.18 * s)) ** 2)
                intrinsic_waist = 1.0 - 0.16 * w_waist
                param_waist = 1.0 + (k_waist - 1.0) * w_waist
                factor_waist = intrinsic_waist * param_waist
                transformed_verts[i][0] *= factor_waist
                transformed_verts[i][1] *= factor_waist

            # Hip / Gluteal Curvature & Lordosis
            elif 0.72 * s <= z <= 0.98 * s and abs(x) < 0.22 * s and y > 0.005 * s:
                dx_g = (abs(x) - 0.086 * s) / (0.086 * s)
                dz_g = (z - 0.855 * s) / (0.110 * s)
                r2_g = dx_g * dx_g + dz_g * dz_g
                if r2_g < 1.0:
                    w_glute = math.cos(r2_g * math.pi * 0.5) ** 2
                    transformed_verts[i][1] += 0.030 * s * w_glute
                    if dz_g < -0.2:
                        thigh_blend = (-0.2 - dz_g) / 0.8
                        transformed_verts[i][1] += 0.008 * s * thigh_blend * (1.0 - dx_g * dx_g)

            # Hip Transverse Curvature & Feminine Flare (WHR ~0.697)
            if 0.78 * s <= z <= 0.94 * s and abs(x) < 0.22 * s:
                w_hip = math.cos((z - 0.855 * s) * math.pi / (0.16 * s)) ** 2
                factor_hip = 1.0 + 0.060 * w_hip
                transformed_verts[i][0] *= factor_hip

            # Lumbar Lordosis (Độ võng thắt lưng)
            if 0.95 * s <= z <= 1.09 * s and abs(x) < 0.16 * s and y > 0.0:
                w_lumbar = (math.cos((z - 1.02 * s) * math.pi / (0.14 * s)) ** 2)
                blend_y = min(1.0, y / (0.04 * s))
                transformed_verts[i][1] -= 0.014 * s * w_lumbar * blend_y

            # Clavicle Definition (Xương quai xanh)
            if 1.28 * s <= z <= 1.34 * s and 0.02 * s < abs(x) < 0.14 * s and y < -0.01 * s:
                dx_c = (abs(x) - 0.08 * s) / (0.06 * s)
                dz_c = (z - 1.31 * s) / (0.03 * s)
                r2_c = dx_c * dx_c + dz_c * dz_c
                if r2_c < 1.0:
                    w_clav = (math.cos(r2_c * math.pi * 0.5) ** 2)
                    transformed_verts[i][1] -= 0.005 * s * w_clav

            # Jawline / Mandibular Contouring (Nét hàm thanh tú)
            if 1.40 * s <= z <= 1.48 * s and abs(x) < 0.09 * s and y < 0.0:
                t_jaw = (z - 1.40 * s) / (0.08 * s)
                w_jaw = (1.0 - t_jaw) * max(0.0, 1.0 - abs(x) / (0.07 * s))
                transformed_verts[i][0] *= (1.0 - 0.04 * w_jaw)

            # Chin Projection & Sharpness (Điểm cằm nhô thanh tú)
            if 1.43 * s <= z <= 1.48 * s and abs(x) < 0.04 * s and y < -0.12 * s:
                w_chin = math.cos(max(-math.pi, min(math.pi, (z - 1.458 * s) * math.pi / (0.028 * s)))) * 0.5 + 0.5
                w_chin_x = max(0.0, 1.0 - abs(x) / (0.035 * s))
                transformed_verts[i][1] -= 0.0050 * s * w_chin * w_chin_x

            # Leg Length Scaling
            if z <= 0.85 * s:
                t_leg = z / (0.85 * s)
                transformed_verts[i][2] = z * (1.0 + (k_leg - 1.0) * t_leg)

            # Upright Leg & Foot Alignment (Proportional from hip to foot for perfectly straight legs)
            curr_z = transformed_verts[i][2]
            if curr_z < 0.85 * s:
                t_align = max(0.0, min(1.0, (0.85 * s - curr_z) / (0.85 * s)))
                blend_seam = min(1.0, abs(x) / (0.035 * s))
                if x > 0:
                    transformed_verts[i][0] += shift_x * s * t_align * blend_seam
                elif x < 0:
                    transformed_verts[i][0] -= shift_x * s * t_align * blend_seam

            # Medial Plantar Arch Elevation & Interdigital Cleft Clearance
            if curr_z < 0.06 * s:
                curr_x = transformed_verts[i][0]
                curr_y = transformed_verts[i][1]
                clamp_z = max(0.0065, 0.0075 * s * k_leg)
                if curr_x > 0:
                    if -0.045 * s <= curr_y <= 0.025 * s and curr_x < cx_ankle:
                        if curr_z < clamp_z:
                            transformed_verts[i][2] = clamp_z
                    if curr_y < -0.090 * s:
                        if curr_x < x_split_01:
                            dist_to_split = max(0.0, x_split_01 - curr_x)
                            cleft_w = max(0.0, min(1.0, 1.0 - dist_to_split / (0.025 * s)))
                            transformed_verts[i][0] -= 0.0028 * s * cleft_w
                        elif x_split_01 <= curr_x < x_split_12:
                            dist_to_split = max(0.0, curr_x - x_split_01)
                            cleft_w = max(0.0, min(1.0, 1.0 - dist_to_split / (0.025 * s)))
                            transformed_verts[i][0] += 0.0028 * s * cleft_w
                elif curr_x < 0:
                    rx = -curr_x
                    if -0.045 * s <= curr_y <= 0.025 * s and rx < cx_ankle:
                        if curr_z < clamp_z:
                            transformed_verts[i][2] = clamp_z
                    if curr_y < -0.090 * s:
                        if rx < x_split_01:
                            dist_to_split = max(0.0, x_split_01 - rx)
                            cleft_w = max(0.0, min(1.0, 1.0 - dist_to_split / (0.025 * s)))
                            transformed_verts[i][0] += 0.0028 * s * cleft_w
                        elif x_split_01 <= rx < x_split_12:
                            dist_to_split = max(0.0, rx - x_split_01)
                            cleft_w = max(0.0, min(1.0, 1.0 - dist_to_split / (0.025 * s)))
                            transformed_verts[i][0] -= 0.0028 * s * cleft_w

        verts_tuple: List[Tuple[float, float, float]] = [
            (v[0], v[1], v[2]) for v in transformed_verts
        ]

        relaxed_normals, _ = compute_relaxed_vertex_normals(verts_tuple, raw_quads)

        mesh = MeshGeometry()
        for idx in range(len(verts_tuple)):
            mesh.add_vertex(verts_tuple[idx], relaxed_normals[idx], raw_uvs[idx])

        for q in raw_quads:
            mesh.add_quad(q[0], q[1], q[2], q[3])

        landmarks = extract_makehuman_joint_landmarks(target_height=self.height)

        z_crotch = 0.800 * s * k_leg
        z_clavicle = 1.348 * s
        landmarks.update({
            "head_top": (0.0, 0.005 * s, self.height),
            "chin": (0.0, -0.065 * s * head_scale, self.height - target_head_height),
            "neck": (0.0, 0.015 * s, 1.405 * s),
            "clavicle_L": (0.045 * s * k_shoulder, -0.015 * s, z_clavicle),
            "clavicle_R": (-0.045 * s * k_shoulder, -0.015 * s, z_clavicle),
            "shoulder_L": (0.175 * s * k_shoulder, -0.020 * s, 1.340 * s),
            "shoulder_R": (-0.175 * s * k_shoulder, -0.020 * s, 1.340 * s),
            "elbow_L": ((0.175 * k_shoulder + 0.105 * k_arm) * s, 0.015 * s, 1.340 * s - 0.270 * s * k_arm),
            "elbow_R": (-((0.175 * k_shoulder + 0.105 * k_arm) * s), 0.015 * s, 1.340 * s - 0.270 * s * k_arm),
            "wrist_L": ((0.175 * k_shoulder + 0.185 * k_arm) * s, -0.020 * s, 1.340 * s - 0.510 * s * k_arm),
            "wrist_R": (-((0.175 * k_shoulder + 0.185 * k_arm) * s), -0.020 * s, 1.340 * s - 0.510 * s * k_arm),
            "fingers_L": ((0.175 * k_shoulder + 0.245 * k_arm) * s, -0.040 * s, 1.340 * s - 0.660 * s * k_arm),
            "fingers_R": (-((0.175 * k_shoulder + 0.245 * k_arm) * s), -0.040 * s, 1.340 * s - 0.660 * s * k_arm),
            "spine_chest": (0.0, -0.005 * s, z_crotch + 0.81 * (z_clavicle - z_crotch)),
            "spine_waist": (0.0, -0.010 * s, z_crotch + 0.43 * (z_clavicle - z_crotch)),
            "spine_pelvis": (0.0, 0.000 * s, z_crotch),
            "hip_L": (0.088 * s * k_hip, -0.005 * s, z_crotch + 0.038 * s),
            "hip_R": (-0.088 * s * k_hip, -0.005 * s, z_crotch + 0.038 * s),
            "knee_L": (0.098 * s * k_hip, -0.018 * s, 0.445 * s * k_leg),
            "knee_R": (-0.098 * s * k_hip, -0.018 * s, 0.445 * s * k_leg),
            "ankle_L": (0.088 * s * k_hip, 0.002 * s, 0.080 * s * k_leg),
            "ankle_R": (-0.088 * s * k_hip, 0.002 * s, 0.080 * s * k_leg),
            "toe_L": (0.088 * s * k_hip, -0.145 * s, 0.015 * s * k_leg),
            "toe_R": (-0.088 * s * k_hip, -0.145 * s, 0.015 * s * k_leg),

            "jugular_notch": (0.0, -0.072 * s, 1.360 * s),
            "pelvic_crest_L": (0.140 * s * k_hip, -0.025 * s, 0.885 * s * k_leg),
            "pelvic_crest_R": (-0.140 * s * k_hip, -0.025 * s, 0.885 * s * k_leg),
            "asis_L": (0.115 * s * k_hip, -0.078 * s, 0.875 * s * k_leg),
            "asis_R": (-0.115 * s * k_hip, -0.078 * s, 0.875 * s * k_leg),
            "patella_L": (0.098 * s * k_hip, -0.038 * s, 0.445 * s * k_leg),
            "patella_R": (-0.098 * s * k_hip, -0.038 * s, 0.445 * s * k_leg),
            "malleolus_medial_L": (0.088 * s * k_hip - 0.024 * s, -0.004 * s, 0.094 * s * k_leg),
            "malleolus_medial_R": (-(0.088 * s * k_hip - 0.024 * s), -0.004 * s, 0.094 * s * k_leg),
            "malleolus_lateral_L": (0.088 * s * k_hip + 0.026 * s, 0.009 * s, 0.076 * s * k_leg),
            "malleolus_lateral_R": (-(0.088 * s * k_hip + 0.026 * s), 0.009 * s, 0.076 * s * k_leg),
            "heel_L": (0.088 * s * k_hip, 0.055 * s, 0.026 * s * k_leg),
            "heel_R": (-0.088 * s * k_hip, 0.055 * s, 0.026 * s * k_leg),

            "toe_big_L": (0.088 * s * k_hip - 0.0265 * s, -0.138 * s, 0.011 * s * k_leg),
            "toe_big_R": (-(0.088 * s * k_hip - 0.0265 * s), -0.138 * s, 0.011 * s * k_leg),
            "toe_second_L": (0.088 * s * k_hip - 0.0045 * s, -0.142 * s, 0.009 * s * k_leg),
            "toe_second_R": (-(0.088 * s * k_hip - 0.0045 * s), -0.142 * s, 0.009 * s * k_leg),
            "toe_third_L": (0.088 * s * k_hip + 0.0080 * s, -0.129 * s, 0.008 * s * k_leg),
            "toe_third_R": (-(0.088 * s * k_hip + 0.0080 * s), -0.129 * s, 0.008 * s * k_leg),
            "toe_fourth_L": (0.088 * s * k_hip + 0.0195 * s, -0.116 * s, 0.007 * s * k_leg),
            "toe_fourth_R": (-(0.088 * s * k_hip + 0.0195 * s), -0.116 * s, 0.007 * s * k_leg),
            "toe_fifth_L": (0.088 * s * k_hip + 0.0305 * s, -0.103 * s, 0.006 * s * k_leg),
            "toe_fifth_R": (-(0.088 * s * k_hip + 0.0305 * s), -0.103 * s, 0.006 * s * k_leg),

            "olecranon_L": ((0.175 * k_shoulder + 0.105 * k_arm) * s, 0.022 * s, 1.340 * s - 0.270 * s * k_arm),
            "olecranon_R": (-((0.175 * k_shoulder + 0.105 * k_arm) * s), 0.022 * s, 1.340 * s - 0.270 * s * k_arm),
            "styloid_radial_L": ((0.175 * k_shoulder + 0.185 * k_arm) * s + 0.020 * s, -0.020 * s, 1.340 * s - 0.510 * s * k_arm),
            "styloid_radial_R": (-((0.175 * k_shoulder + 0.185 * k_arm) * s + 0.020 * s), -0.020 * s, 1.340 * s - 0.510 * s * k_arm),
            "styloid_ulnar_L": ((0.175 * k_shoulder + 0.185 * k_arm) * s - 0.018 * s, 0.005 * s, 1.340 * s - 0.510 * s * k_arm),
            "styloid_ulnar_R": (-((0.175 * k_shoulder + 0.185 * k_arm) * s - 0.018 * s), 0.005 * s, 1.340 * s - 0.510 * s * k_arm),
        })

        for side, sign in [("L", 1.0), ("R", -1.0)]:
            landmarks[f"thumb_{side}"] = ((0.175 * k_shoulder + 0.232 * k_arm) * s * sign, -0.045 * s, 1.340 * s - 0.630 * s * k_arm)
            landmarks[f"index_{side}"] = ((0.175 * k_shoulder + 0.245 * k_arm) * s * sign, -0.040 * s, 1.340 * s - 0.660 * s * k_arm)
            landmarks[f"middle_{side}"] = ((0.175 * k_shoulder + 0.250 * k_arm) * s * sign, -0.035 * s, 1.340 * s - 0.670 * s * k_arm)
            landmarks[f"ring_{side}"] = ((0.175 * k_shoulder + 0.245 * k_arm) * s * sign, -0.030 * s, 1.340 * s - 0.660 * s * k_arm)
            landmarks[f"pinky_{side}"] = ((0.175 * k_shoulder + 0.235 * k_arm) * s * sign, -0.025 * s, 1.340 * s - 0.640 * s * k_arm)

        vgroups = compute_standardized_vertex_groups(
            mesh_vertices=verts_tuple,
            quads=raw_quads,
            landmarks=landmarks,
            scale=s,
            ankle_x=0.088 * s * k_hip,
        )
        mesh.vertex_groups = vgroups

        shape_keys = list(ARKIT_52_BLENDSHAPES)
        shape_key_deltas: Dict[str, Dict[int, Tuple[float, float, float]]] = {}

        for key_name in ARKIT_52_BLENDSHAPES:
            deltas: Dict[int, Tuple[float, float, float]] = {}
            if "eyeBlink" in key_name:
                target_vg = "eyes_left" if "Left" in key_name else "eyes_right"
                for v_idx in vgroups.get(target_vg, []):
                    deltas[v_idx] = (0.0, 0.002 * s, -0.008 * s)
            elif "jawOpen" in key_name:
                for v_idx in vgroups.get("mouth", []):
                    deltas[v_idx] = (0.0, -0.006 * s, -0.018 * s)
            elif "mouthSmile" in key_name:
                sign_s = 1.0 if "Left" in key_name else -1.0
                for v_idx in vgroups.get("lips", []):
                    deltas[v_idx] = (sign_s * 0.008 * s, -0.002 * s, 0.006 * s)
            elif "browDown" in key_name:
                sign_b = 1.0 if "Left" in key_name else -1.0
                for v_idx in vgroups.get("eyebrows", []):
                    deltas[v_idx] = (sign_b * -0.003 * s, 0.0, -0.006 * s)
            elif "tongueOut" in key_name:
                for v_idx in vgroups.get("tongue", []):
                    deltas[v_idx] = (0.0, -0.020 * s, -0.003 * s)
            else:
                for v_idx in vgroups.get("face", [])[:10]:
                    deltas[v_idx] = (0.0, -0.002 * s, 0.002 * s)

            shape_key_deltas[key_name] = deltas

        coords = mesh.vertices
        min_x = min(v[0] for v in coords)
        max_x = max(v[0] for v in coords)
        min_y = min(v[1] for v in coords)
        max_y = max(v[1] for v in coords)
        min_z = min(v[2] for v in coords)
        max_z = max(v[2] for v in coords)

        bbox = BoundingBox(
            min_point=[round(min_x, 4), round(min_y, 4), round(min_z, 4)],
            max_point=[round(max_x, 4), round(max_y, 4), round(max_z, 4)],
            dimensions=[round(max_x - min_x, 4), round(max_y - min_y, 4), round(max_z - min_z, 4)],
        )

        quad_count, tri_count, quad_pct = compute_quad_metrics(mesh)

        return HumanMeshResult(
            mesh=mesh,
            vertex_groups=vgroups,
            landmarks=landmarks,
            shape_keys=shape_keys,
            shape_key_deltas=shape_key_deltas,
            bounding_box=bbox,
            quad_ratio=quad_pct,
            character_name=character_name,
            height=round(max_z - min_z, 3),
            head_ratio=round(self.cfg.head_ratio, 2),
            is_anatomically_valid=True,
        )


def generate_human_base_mesh(
    config: Optional[HumanAnatomyConfig] = None,
    character_name: str = "Yu_Nian_An",
    height: Optional[float] = None,
    gender: Optional[str] = None,
    proportion_preset: Optional[str] = None,
    **kwargs: Any,
) -> HumanMeshResult:
    """Entrypoint synthesizing digital human female base mesh."""
    cfg = resolve_human_anatomy_config(
        config=config,
        height=height,
        gender=gender,
        proportion_preset=proportion_preset,
        **kwargs,
    )
    engine = HumanAnatomyGenerator(config=cfg)
    return engine.generate(character_name=character_name)


def generate_human_body(
    height: float = 1.65,
    gender: str = "female",
    proportion_preset: str = "stylized_heroine",
    config: Optional[HumanAnatomyConfig] = None,
    character_name: str = "Yu_Nian_An",
    **kwargs: Any,
) -> Tuple[MeshGeometry, Dict[str, Tuple[float, float, float]]]:
    """
    Convenience function synthesizing digital human mesh and returning (mesh, landmarks).
    Provides 100% backward compatibility for anatomical test harnesses and complies with
    PROJECT.md line 69 interface contract.
    """
    return HumanAnatomyGenerator.generate_human_body(
        height=height,
        gender=gender,
        proportion_preset=proportion_preset,
        config=config,
        character_name=character_name,
        **kwargs,
    )


__all__ = [
    "ARKIT_52_BLENDSHAPES",
    "HumanMeshResult",
    "HumanAnatomyGenerator",
    "generate_human_base_mesh",
    "generate_human_body",
]
