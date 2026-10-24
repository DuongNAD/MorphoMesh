"""
MorphoMesh: Inspector Camera & Viewport Capture Schemas (Milestone 2).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .enums import (
    DiagnosticColorType,
    DiagnosticShadingMode,
    VALID_INSPECTOR_VIEWPOINTS_SET,
)


class SetupInspectorCameraInput(BaseModel):
    """Input parameters for morphomesh.setup_inspector_camera."""
    model_config = ConfigDict(extra="ignore")

    viewpoint: str = Field(default="three_quarter", description="Viewing angle preset ('front', 'side', 'three_quarter', etc.).")
    target_object: Optional[str] = Field(default=None, description="Optional target character mesh object name.")
    target_center: Optional[List[float]] = Field(default=None, description="Explicit [x, y, z] target center.")
    framing_radius: Optional[float] = Field(default=None, description="Explicit framing bounding sphere radius.")
    focal_length: float = Field(default=50.0, ge=10.0, le=300.0, description="Camera lens focal length in mm.")
    camera_name: str = Field(default="MorphoMesh_Inspector_Camera", description="Name of inspector camera in Blender.")
    margin: float = Field(default=0.15, ge=0.0, le=1.0, description="Safety framing margin factor.")
    resolution: List[int] = Field(default_factory=lambda: [1024, 1024], description="Target image resolution [width, height].")

    @field_validator("viewpoint")
    @classmethod
    def validate_viewpoint(cls, v: str) -> str:
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError("viewpoint cannot be empty")
        v_clean = v.lower().strip()
        if v_clean not in VALID_INSPECTOR_VIEWPOINTS_SET:
            raise ValueError(f"Invalid viewpoint '{v}'. Allowed: {sorted(list(VALID_INSPECTOR_VIEWPOINTS_SET))}")
        return v_clean


class SetupInspectorCameraOutput(BaseModel):
    """Result of morphomesh.setup_inspector_camera."""
    model_config = ConfigDict(extra="ignore")

    status: str = "success"
    camera_name: str
    viewpoint: str
    focal_length: float
    camera_location: List[float]
    camera_rotation: List[float]
    target_center: List[float]
    framing_distance: float
    bounding_radius: float
    bounding_box: Optional[Dict[str, Any]] = None


class CaptureViewportInput(BaseModel):
    """Input parameters for morphomesh.capture_viewport."""
    model_config = ConfigDict(extra="ignore")

    output_path: Optional[str] = Field(default=None, description="Destination path for captured PNG.")
    camera_name: str = Field(default="MorphoMesh_Inspector_Camera", description="Camera object to capture through.")
    resolution: List[int] = Field(default_factory=lambda: [1024, 1024], description="[width, height] resolution.")
    resolution_width: Optional[int] = Field(default=None, description="Alternative width parameter.")
    resolution_height: Optional[int] = Field(default=None, description="Alternative height parameter.")
    shading_mode: str = Field(default="SOLID", description="Viewport shading ('SOLID', 'FLAT', 'WIREFRAME', 'MATERIAL').")
    color_type: str = Field(default="RANDOM", description="Solid color mode ('RANDOM', 'MATERIAL', 'SINGLE', 'OBJECT').")
    output_dir: Optional[str] = Field(default=None, description="Optional directory to store output if output_path is None.")

    @field_validator("shading_mode")
    @classmethod
    def validate_shading_mode(cls, v: str) -> str:
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError("shading_mode cannot be empty")
        v_upper = v.upper().strip()
        valid_shading = {e.value for e in DiagnosticShadingMode}
        if v_upper not in valid_shading:
            raise ValueError(f"Invalid shading_mode '{v}'. Allowed: {sorted(list(valid_shading))}")
        return v_upper

    @field_validator("color_type")
    @classmethod
    def validate_color_type(cls, v: str) -> str:
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError("color_type cannot be empty")
        v_upper = v.upper().strip()
        valid_colors = {e.value for e in DiagnosticColorType}
        if v_upper not in valid_colors:
            raise ValueError(f"Invalid color_type '{v}'. Allowed: {sorted(list(valid_colors))}")
        return v_upper


class CaptureViewportOutput(BaseModel):
    """Result of morphomesh.capture_viewport."""
    model_config = ConfigDict(extra="ignore")

    status: str = "success"
    image_path: str
    image_format: str = "png"
    resolution: List[int]
    shading_mode: str
    color_type: str
    camera_name: str
    base64_preview: Optional[str] = None
    capture_time_seconds: float = 0.0


class MultiAngleCaptureFrame(BaseModel):
    """Metadata for a single captured angle within batch inspection."""
    model_config = ConfigDict(extra="ignore")

    viewpoint: str
    image_path: str
    image_format: str = "png"
    resolution: List[int]
    shading_mode: str
    color_type: str
    camera_location: Optional[List[float]] = None
    camera_rotation: Optional[List[float]] = None
    target_center: Optional[List[float]] = None
    framing_distance: Optional[float] = None
    bounding_radius: Optional[float] = None
    capture_time_seconds: float = 0.0
    base64_image: Optional[str] = None


class CaptureMultiAngleInspectionInput(BaseModel):
    """Input parameters for morphomesh.capture_multi_angle_inspection."""
    model_config = ConfigDict(extra="ignore")

    viewpoints: Optional[List[str]] = Field(
        default=None,
        description="List of viewpoints (defaults to ['front', 'three_quarter', 'side', 'back', 'close_up_head']).",
    )
    target_object: Optional[str] = Field(default=None, description="Name of character mesh to frame.")
    output_dir: Optional[str] = Field(default=None, description="Directory to save rendered frames.")
    resolution: List[int] = Field(default_factory=lambda: [1024, 1024], description="[width, height] resolution.")
    resolution_width: Optional[int] = Field(default=None, description="Alternative width parameter.")
    resolution_height: Optional[int] = Field(default=None, description="Alternative height parameter.")
    shading_mode: str = Field(default="SOLID", description="Viewport shading mode ('SOLID', 'FLAT', 'WIREFRAME').")
    color_type: str = Field(default="RANDOM", description="Color mode ('RANDOM', 'MATERIAL', 'OBJECT').")
    focal_length: float = Field(default=50.0, ge=10.0, le=300.0, description="Camera focal length in mm.")
    camera_name: str = Field(default="MorphoMesh_Inspector_Camera", description="Inspector camera name.")
    include_base64: bool = Field(default=True, description="Whether to embed base64 image strings.")


class CaptureMultiAngleInspectionOutput(BaseModel):
    """Result of morphomesh.capture_multi_angle_inspection."""
    model_config = ConfigDict(extra="ignore")

    status: str = "success"
    capture_count: int
    viewpoints: List[str] = Field(default_factory=list)
    captures: List[MultiAngleCaptureFrame] = Field(default_factory=list)


__all__ = [
    "CaptureMultiAngleInspectionInput",
    "CaptureMultiAngleInspectionOutput",
    "CaptureViewportInput",
    "CaptureViewportOutput",
    "MultiAngleCaptureFrame",
    "SetupInspectorCameraInput",
    "SetupInspectorCameraOutput",
]
