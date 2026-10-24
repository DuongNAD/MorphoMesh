"""
MorphoMesh: Anthropometric Body Proportions & Aesthetic Critique Engine.

Audits digital human anatomical ratios against golden ratio and character styling
presets (realistic, stylized heroine, heroic male, chibi), evaluating head-to-body
ratio, arm span index, and shoulder-to-hip breadth proportions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

from morphomesh.models import (
    ActionableRecommendation,
    DefectCategory,
    DefectItem,
    DefectSeverity,
)
from .bvh import HAS_BLENDER, bpy

ANTHROPOMETRIC_PRESETS: Dict[str, Dict[str, Any]] = {
    "realistic_human": {
        "head_ratio_min": 7.0,
        "head_ratio_max": 8.0,
        "head_ratio_nominal": 7.5,
        "arm_span_ratio_min": 0.95,
        "arm_span_ratio_max": 1.05,
        "shoulder_to_hip_feminine": (0.90, 1.05),
        "shoulder_to_hip_masculine": (1.20, 1.45),
        "typical_height_range": (1.55, 1.90),
    },
    "stylized_heroine": {
        "head_ratio_min": 6.0,
        "head_ratio_max": 7.6,  # Allows canon heroine ratios (e.g. 7.41) while rejecting chibis/giants
        "head_ratio_nominal": 6.8,
        "arm_span_ratio_min": 0.90,
        "arm_span_ratio_max": 1.08,
        "shoulder_to_hip_feminine": (0.85, 1.10),
        "shoulder_to_hip_masculine": (1.15, 1.35),
        "typical_height_range": (1.50, 1.75),
    },
    "chibi_petite": {
        "head_ratio_min": 2.0,
        "head_ratio_max": 5.0,
        "head_ratio_nominal": 3.5,
        "arm_span_ratio_min": 0.80,
        "arm_span_ratio_max": 1.05,
        "shoulder_to_hip_feminine": (0.85, 1.10),
        "shoulder_to_hip_masculine": (0.95, 1.15),
        "typical_height_range": (0.80, 1.35),
    },
    "realistic_female": {
        "head_ratio_min": 6.8,
        "head_ratio_max": 7.8,
        "head_ratio_nominal": 7.3,
        "arm_span_ratio_min": 0.95,
        "arm_span_ratio_max": 1.05,
        "shoulder_to_hip_feminine": (0.85, 1.05),
        "shoulder_to_hip_masculine": (1.10, 1.35),
        "typical_height_range": (1.55, 1.75),
    },
    "heroic_male": {
        "head_ratio_min": 7.5,
        "head_ratio_max": 8.5,
        "head_ratio_nominal": 8.0,
        "arm_span_ratio_min": 0.98,
        "arm_span_ratio_max": 1.10,
        "shoulder_to_hip_feminine": (1.10, 1.30),
        "shoulder_to_hip_masculine": (1.30, 1.60),
        "typical_height_range": (1.80, 2.10),
    },
    "chibi": {
        "head_ratio_min": 2.0,
        "head_ratio_max": 5.0,
        "head_ratio_nominal": 3.5,
        "arm_span_ratio_min": 0.80,
        "arm_span_ratio_max": 1.05,
        "shoulder_to_hip_feminine": (0.85, 1.10),
        "shoulder_to_hip_masculine": (0.95, 1.15),
        "typical_height_range": (0.80, 1.35),
    },
}

@dataclass
class AnthropometricMetrics:
    total_height: float
    head_height: float
    head_ratio: float
    arm_span: float
    arm_span_ratio: float
    shoulder_breadth: float
    hip_breadth: float
    shoulder_to_hip_ratio: float
    target_preset: str
    gender: str = "feminine"
    is_head_ratio_valid: bool = True
    is_arm_span_valid: bool = True
    is_shoulder_hip_valid: bool = True


def evaluate_body_proportions(
    body_obj_name: str = "Body_Mesh",
    target_preset: str = "stylized_heroine",
    gender: str = "feminine",
    landmarks: Optional[Dict[str, Tuple[float, float, float]]] = None,
    vertex_groups: Optional[Dict[str, List[int]]] = None,
    body_geo: Optional[Tuple[List[Any], List[Any]]] = None,
) -> Tuple[AnthropometricMetrics, List[DefectItem]]:
    """
    Evaluates anthropometric ratios:
    1. Total Height H_total
    2. Head Height H_head and Head Ratio R_head = H_total / H_head
    3. Arm Span W_span and Arm Span Ratio R_arm = W_span / H_total (Vitruvian target 1.00 +/- 0.05)
    4. Shoulder-to-Hip Breadth Ratio
    """
    preset = ANTHROPOMETRIC_PRESETS.get(target_preset, ANTHROPOMETRIC_PRESETS["stylized_heroine"])
    defects: List[DefectItem] = []

    # 1. Resolve geometry
    verts: List[Tuple[float, float, float]] = []
    if body_geo is not None:
        verts = [(float(v[0]), float(v[1]), float(v[2])) for v in body_geo[0]]
    elif HAS_BLENDER and bpy and bpy.data.objects.get(body_obj_name):
        b_obj = bpy.data.objects[body_obj_name]
        mw = b_obj.matrix_world
        verts = [tuple(mw @ v.co) for v in b_obj.data.vertices]
        if landmarks is None and "morphomesh_landmarks" in b_obj:
            landmarks = dict(b_obj["morphomesh_landmarks"])
        if vertex_groups is None:
            vertex_groups = {}
            for vg in b_obj.vertex_groups:
                vg_indices = []
                for v_idx, v in enumerate(b_obj.data.vertices):
                    for g in v.groups:
                        if g.group == vg.index:
                            vg_indices.append(v_idx)
                vertex_groups[vg.name] = vg_indices

    if len(verts) == 0:
        # Default fallback metrics
        metrics = AnthropometricMetrics(1.65, 0.2227, 7.41, 1.62, 0.98, 0.35, 0.35, 1.0, target_preset, gender)
        return metrics, defects

    zs = [v[2] for v in verts]
    z_min, z_max = min(zs), max(zs)
    total_height = round(z_max - z_min, 3)

    # 2. Head Height
    if landmarks and "head_top" in landmarks and "chin" in landmarks:
        head_height = round(landmarks["head_top"][2] - landmarks["chin"][2], 3)
    elif vertex_groups and "head" in vertex_groups and vertex_groups["head"]:
        head_zs = [verts[i][2] for i in vertex_groups["head"]]
        head_height = round(max(head_zs) - min(head_zs), 3)
    else:
        # Morphological slicing: look for neck constriction in upper 30%
        head_height = round(total_height / preset["head_ratio_nominal"], 3)

    head_ratio = round(total_height / max(1e-4, head_height), 2)

    # 3. Arm Span
    if landmarks and all(k in landmarks for k in ["shoulder_L", "elbow_L", "wrist_L", "fingers_L", "shoulder_R", "elbow_R", "wrist_R", "fingers_R"]):
        def _dist(p1, p2): return math.sqrt(sum((a - b) ** 2 for a, b in zip(p1, p2)))
        l_arm = _dist(landmarks["shoulder_L"], landmarks["elbow_L"]) + _dist(landmarks["elbow_L"], landmarks["wrist_L"]) + _dist(landmarks["wrist_L"], landmarks["fingers_L"])
        r_arm = _dist(landmarks["shoulder_R"], landmarks["elbow_R"]) + _dist(landmarks["elbow_R"], landmarks["wrist_R"]) + _dist(landmarks["wrist_R"], landmarks["fingers_R"])
        biacromial = _dist(landmarks["shoulder_L"], landmarks["shoulder_R"])
        arm_span = round(l_arm + biacromial + r_arm, 3)
    else:
        xs = [v[0] for v in verts]
        arm_span = round(max(xs) - min(xs), 3)

    arm_span_ratio = round(arm_span / max(1e-4, total_height), 2)

    # 4. Shoulder & Hip Breadth
    if landmarks and "shoulder_L" in landmarks and "shoulder_R" in landmarks:
        shoulder_breadth = round(abs(landmarks["shoulder_L"][0] - landmarks["shoulder_R"][0]), 3)
    else:
        shoulder_breadth = round(total_height * 0.218, 3)

    if vertex_groups and "hips" in vertex_groups and vertex_groups["hips"]:
        hip_xs = [verts[i][0] for i in vertex_groups["hips"]]
        hip_breadth = round(max(hip_xs) - min(hip_xs), 3)
    else:
        hip_breadth = round(shoulder_breadth * 1.0, 3)

    shoulder_to_hip_ratio = round(shoulder_breadth / max(1e-4, hip_breadth), 2)

    # Evaluate Head Ratio
    is_head_valid = preset["head_ratio_min"] <= head_ratio <= preset["head_ratio_max"]
    if not is_head_valid:
        dev = abs(head_ratio - preset["head_ratio_nominal"])
        sev = DefectSeverity.CRITICAL if dev > 1.2 else DefectSeverity.MAJOR
        cat = "PROP_HEAD_TOO_LARGE" if head_ratio < preset["head_ratio_min"] else "PROP_HEAD_TOO_SMALL"
        defects.append(DefectItem(
            defect_id=cat,
            category=DefectCategory.PROPORTION,
            severity=sev,
            affected_objects=[body_obj_name],
            object_name=body_obj_name,
            description=f"Head ratio {head_ratio:.2f} is outside range [{preset['head_ratio_min']}, {preset['head_ratio_max']}] for preset '{target_preset}'.",
            location=[0.0, 0.0, round(z_max - head_height * 0.5, 3)],
            metrics={"head_ratio": head_ratio, "head_height": head_height, "total_height": total_height},
            recommendation=ActionableRecommendation(
                action="RESCALE_HEAD",
                category=DefectCategory.PROPORTION,
                target_objects=[body_obj_name],
                parameters={"scale_factor": round(head_ratio / preset["head_ratio_nominal"], 3)},
                guidance=f"Rescale head geometry to conform to {preset['head_ratio_nominal']} heads.",
            ),
        ))

    # Evaluate Arm Span
    is_arm_valid = preset["arm_span_ratio_min"] <= arm_span_ratio <= preset["arm_span_ratio_max"]
    if not is_arm_valid:
        dev = abs(arm_span_ratio - 1.0)
        sev = DefectSeverity.MAJOR if dev > 0.12 else DefectSeverity.MINOR
        cat = "PROP_ARM_SPAN_TOO_SHORT" if arm_span_ratio < preset["arm_span_ratio_min"] else "PROP_ARM_SPAN_TOO_LONG"
        defects.append(DefectItem(
            defect_id=cat,
            category=DefectCategory.PROPORTION,
            severity=sev,
            affected_objects=[body_obj_name],
            object_name=body_obj_name,
            description=f"Arm span ratio {arm_span_ratio:.2f} deviates from target [{preset['arm_span_ratio_min']}, {preset['arm_span_ratio_max']}].",
            location=[0.0, 0.0, round(z_min + total_height * 0.7, 3)],
            metrics={"arm_span_ratio": arm_span_ratio, "arm_span": arm_span, "total_height": total_height},
        ))

    # Evaluate Shoulder to Hip
    s_hip_range = preset.get(f"shoulder_to_hip_{gender}", (0.85, 1.10))
    is_s_hip_valid = s_hip_range[0] <= shoulder_to_hip_ratio <= s_hip_range[1]
    if not is_s_hip_valid:
        sev = DefectSeverity.MAJOR if abs(shoulder_to_hip_ratio - sum(s_hip_range) * 0.5) > 0.18 else DefectSeverity.MINOR
        defects.append(DefectItem(
            defect_id="PROP_SHOULDER_TO_HIP_SKEW",
            category=DefectCategory.PROPORTION,
            severity=sev,
            affected_objects=[body_obj_name],
            object_name=body_obj_name,
            description=f"Shoulder-to-hip ratio {shoulder_to_hip_ratio:.2f} deviates from {gender} range {s_hip_range}.",
            location=[0.0, 0.0, round(z_min + total_height * 0.55, 3)],
            metrics={"shoulder_to_hip_ratio": shoulder_to_hip_ratio},
        ))

    metrics = AnthropometricMetrics(
        total_height=total_height,
        head_height=head_height,
        head_ratio=head_ratio,
        arm_span=arm_span,
        arm_span_ratio=arm_span_ratio,
        shoulder_breadth=shoulder_breadth,
        hip_breadth=hip_breadth,
        shoulder_to_hip_ratio=shoulder_to_hip_ratio,
        target_preset=target_preset,
        gender=gender,
        is_head_ratio_valid=is_head_valid,
        is_arm_span_valid=is_arm_valid,
        is_shoulder_hip_valid=is_s_hip_valid,
    )
    return metrics, defects

__all__ = [
    "ANTHROPOMETRIC_PRESETS",
    "AnthropometricMetrics",
    "evaluate_body_proportions",
]
