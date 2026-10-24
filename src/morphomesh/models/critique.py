"""
MorphoMesh: Closed-Loop Visual Quality Critique Schemas (Milestone 3).
"""
from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .base import BoundingBox3D
from .enums import AnthropometricPreset, DefectCategory, DefectSeverity
from .inspection import MultiAngleCaptureFrame


class ActionableRecommendation(BaseModel):
    """Structured actionable prescription for automated or manual remediation."""
    model_config = ConfigDict(extra="ignore")

    action_id: str = Field(default_factory=lambda: f"REC-{uuid.uuid4().hex[:6]}", description="Unique recommendation ID.")
    action: Optional[str] = Field(default=None, description="Action name/verb (e.g. RESCALE_HEAD, SMOOTH_WEIGHTS).")
    category: Optional[Union[DefectCategory, str]] = Field(default=None, description="Target defect category.")
    target_objects: List[str] = Field(default_factory=list, description="Mesh/curve objects requiring remediation.")
    description: Optional[str] = Field(default=None, description="Human and agent-readable instructions.")
    guidance: Optional[str] = Field(default=None, description="Detailed guidance instructions.")
    suggested_modifier: Optional[str] = Field(default=None, description="Recommended Blender modifier (Shrinkwrap, Smooth, Displace).")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Concrete parameters for automated remediation.")
    priority: Union[DefectSeverity, str] = Field(default=DefectSeverity.MAJOR, description="Remediation priority.")

    @model_validator(mode="before")
    @classmethod
    def align_description_and_action(cls, data: Any) -> Any:
        if isinstance(data, dict):
            desc = data.get("description")
            act = data.get("action")
            guide = data.get("guidance")
            if not desc:
                data["description"] = guide or act or "Remediation recommended."
            if not act:
                data["action"] = desc or "REMEDIATE"
        return data

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, v: Any) -> Any:
        if isinstance(v, str):
            res = DefectCategory._missing_(v)
            if res:
                return res
        return v

    @field_validator("priority", mode="before")
    @classmethod
    def normalize_priority(cls, v: Any) -> Any:
        if isinstance(v, str):
            res = DefectSeverity._missing_(v)
            if res:
                return res
        return v


class DefectItem(BaseModel):
    """Individual structural defect diagnosed by visual critic."""
    model_config = ConfigDict(extra="ignore")

    defect_id: str = Field(default_factory=lambda: f"DEF-{uuid.uuid4().hex[:6]}", description="Unique defect ID.")
    id: Optional[str] = Field(default=None, description="Alias for defect_id.")
    category: Union[DefectCategory, str] = Field(..., description="Defect classification category.")
    defect_type: Optional[str] = Field(default=None, description="Legacy/convenience defect string type.")
    severity: Union[DefectSeverity, str] = Field(default=DefectSeverity.MAJOR, description="Defect severity.")
    affected_objects: List[str] = Field(default_factory=list, description="Object names involved in defect.")
    object_name: Optional[str] = Field(default=None, description="Primary affected object name.")
    source_object: Optional[str] = Field(default=None, description="Source object involved in collision.")
    target_object: Optional[str] = Field(default=None, description="Target object involved in collision.")
    description: str = Field(..., description="Diagnostic textual description.")
    confidence: float = Field(default=0.95, ge=0.0, le=1.0, description="Confidence score of detection (0.0 to 1.0).")
    location: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0], description="Primary 3D world coordinate [x, y, z] of defect centroid.")
    sample_locations: List[List[float]] = Field(default_factory=list, description="Additional sample 3D points where defect occurs.")
    bounding_box: Optional[BoundingBox3D] = Field(default=None, description="Local 3D bounding box enclosing defect.")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Quantitative diagnostic metrics.")
    penetration_depth_mm: Optional[float] = Field(default=None, description="Max penetration depth in mm if category is PENETRATION.")
    penetration_count: int = Field(default=0, description="Number of penetrating vertices or samples.")
    penetrated_triangles: List[int] = Field(default_factory=list, description="Indices of penetrating triangles.")
    affected_vertices: List[int] = Field(default_factory=list, description="Indices of affected vertices.")
    affected_faces: List[int] = Field(default_factory=list, description="Indices of affected faces.")
    recommendation: Optional[Union[ActionableRecommendation, str]] = Field(default=None, description="Remediation recommendation.")
    actionable_recommendation: Optional[str] = Field(default=None, description="Textual summary recommendation.")

    @model_validator(mode="before")
    @classmethod
    def align_defect_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # ID sync
            d_id = data.get("defect_id")
            s_id = data.get("id")
            if not d_id and s_id:
                data["defect_id"] = s_id
                data["id"] = s_id
            elif d_id and not s_id:
                data["id"] = d_id
            elif not d_id and not s_id:
                new_id = f"DEF-{uuid.uuid4().hex[:6]}"
                data["defect_id"] = new_id
                data["id"] = new_id

            # Category sync
            cat = data.get("category")
            dtype = data.get("defect_type")
            if not cat and dtype:
                data["category"] = dtype
            elif cat and not dtype:
                data["defect_type"] = cat.value if isinstance(cat, Enum) else str(cat)

            # Object name & affected_objects sync
            aff = data.get("affected_objects") or []
            obj_name = data.get("object_name")
            src_obj = data.get("source_object")
            tgt_obj = data.get("target_object")
            combined_objs = list(aff)
            if obj_name and obj_name not in combined_objs:
                combined_objs.append(obj_name)
            if src_obj and src_obj not in combined_objs:
                combined_objs.append(src_obj)
            if tgt_obj and tgt_obj not in combined_objs:
                combined_objs.append(tgt_obj)
            data["affected_objects"] = combined_objs
            if not obj_name and combined_objs:
                data["object_name"] = combined_objs[0]

            # Recommendation sync
            rec = data.get("recommendation")
            act_rec = data.get("actionable_recommendation")
            if not rec and act_rec:
                data["recommendation"] = act_rec
            elif not act_rec and isinstance(rec, str):
                data["actionable_recommendation"] = rec
            elif not act_rec and hasattr(rec, "description"):
                data["actionable_recommendation"] = getattr(rec, "description", str(rec))
        return data

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, v: Any) -> Any:
        if isinstance(v, str):
            res = DefectCategory._missing_(v)
            if res:
                return res
        return v

    @field_validator("severity", mode="before")
    @classmethod
    def normalize_severity(cls, v: Any) -> Any:
        if isinstance(v, str):
            res = DefectSeverity._missing_(v)
            if res:
                return res
        return v


class VisualCritiqueInput(BaseModel):
    """Input parameters for morphomesh.critique_visual_quality."""
    model_config = ConfigDict(extra="ignore")

    target_object: Optional[str] = Field(default="Human_Base_Mesh", description="Target character body mesh name.")
    character_name: Optional[str] = Field(default=None, description="Character root or identifier name.")
    body_obj_name: Optional[str] = Field(default=None, description="Explicit body mesh name.")
    garment_obj_names: Optional[List[str]] = Field(default=None, description="List of garment mesh names.")
    hair_obj_names: Optional[List[str]] = Field(default=None, description="List of hair curve/mesh names.")
    armature_obj_name: Optional[str] = Field(default=None, description="Armature object name.")
    camera_angles: Optional[List[str]] = Field(
        default_factory=lambda: ["front", "side", "three_quarter", "back"],
        description="Camera viewing angles for visual inspection.",
    )
    viewpoints: Optional[List[str]] = Field(default=None, description="Alias for camera_angles.")
    target_preset: str = Field(default="stylized_heroine", description="Anthropometric target preset.")
    clearance_tolerance: float = Field(default=0.0005, ge=0.0, description="Penetration clearance threshold in meters (0.5mm).")
    clearance_threshold: Optional[float] = Field(default=None, description="Alias for clearance_tolerance.")
    evaluate_penetration: bool = Field(default=True, description="Evaluate garment/armor mesh penetration.")
    evaluate_proportions: bool = Field(default=True, description="Evaluate body proportions against preset.")
    evaluate_skinning: bool = Field(default=True, description="Evaluate rig deformation and pinching.")
    evaluate_grooming: bool = Field(default=True, description="Evaluate hair curve intersections.")
    capture_images: bool = Field(default=False, description="Whether to capture multi-angle viewport PNGs.")
    resolution: List[int] = Field(default_factory=lambda: [1024, 1024], description="Viewport render resolution.")

    @field_validator("target_preset")
    @classmethod
    def validate_target_preset(cls, v: str) -> str:
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError("target_preset cannot be empty")
        v_clean = v.lower().strip()
        valid_presets = {e.value for e in AnthropometricPreset}
        if v_clean not in valid_presets:
            raise ValueError(f"Invalid target_preset '{v}'. Allowed: {sorted(list(valid_presets))}")
        return v_clean

    @model_validator(mode="before")
    @classmethod
    def resolve_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "char_name" in data and "character_name" not in data:
                data["character_name"] = data["char_name"]
            if "clearance_threshold" in data and "clearance_tolerance" not in data:
                data["clearance_tolerance"] = data["clearance_threshold"]
            elif "clearance_tolerance" in data and "clearance_threshold" not in data:
                data["clearance_threshold"] = data["clearance_tolerance"]
            if "character_name" in data and ("target_object" not in data or data["target_object"] == "Human_Base_Mesh"):
                data["target_object"] = f"{data['character_name']}_Base_Mesh" if not data.get("target_object") else data["target_object"]
            if "body_obj_name" in data and ("target_object" not in data or data["target_object"] == "Human_Base_Mesh"):
                data["target_object"] = data["body_obj_name"]
            elif "target_object" in data and "body_obj_name" not in data:
                data["body_obj_name"] = data["target_object"]
            if "viewpoints" in data and ("camera_angles" not in data or not data["camera_angles"]):
                data["camera_angles"] = data["viewpoints"]
            elif "camera_angles" in data and "viewpoints" not in data:
                data["viewpoints"] = data["camera_angles"]
        return data


class VisualCritiqueOutput(BaseModel):
    """Diagnostic critique report returned by closed-loop visual QA engine."""
    model_config = ConfigDict(extra="ignore")

    status: str = Field(default="success", description="Critique execution status ('success' or 'error').")
    passed: bool = Field(default=True, description="Overall pass/fail verdict (True if no CRITICAL or excessive MAJOR defects).")
    quality_score: float = Field(default=100.0, ge=0.0, le=100.0, description="Overall quality score (0.0 to 100.0).")
    defect_count: int = Field(default=0, description="Total number of diagnosed defects.")
    defects: List[DefectItem] = Field(default_factory=list, description="List of structured defect items.")
    recommendations: List[str] = Field(default_factory=list, description="Human-readable remediation recommendations.")
    actionable_recommendations: List[ActionableRecommendation] = Field(default_factory=list, description="Structured actionable remediation tasks.")
    inspected_objects: List[str] = Field(default_factory=list, description="List of mesh/curve object names inspected.")
    scene_stats: Dict[str, Any] = Field(default_factory=dict, description="Geometric statistics (vertices, faces, dimensions, ratios).")
    evaluated_angles: List[str] = Field(default_factory=list, description="Camera angles evaluated.")
    capture_previews: List[MultiAngleCaptureFrame] = Field(default_factory=list, description="Viewport preview frames if requested.")
    execution_time_seconds: float = Field(default=0.0, description="Evaluation run duration in seconds.")

    @model_validator(mode="before")
    @classmethod
    def sync_defect_count(cls, data: Any) -> Any:
        if isinstance(data, dict):
            defs = data.get("defects") or []
            if "defect_count" not in data:
                data["defect_count"] = len(defs)
            if "passed" not in data:
                has_critical = any(
                    (d.get("severity") in ("CRITICAL", DefectSeverity.CRITICAL) if isinstance(d, dict) else d.severity == DefectSeverity.CRITICAL)
                    for d in defs
                )
                data["passed"] = not has_critical
        return data


__all__ = [
    "ActionableRecommendation",
    "DefectItem",
    "VisualCritiqueInput",
    "VisualCritiqueOutput",
]
