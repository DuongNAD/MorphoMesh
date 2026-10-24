"""
MorphoMesh: Animation & Meshy Library Models.
"""
from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class AnimationItem(BaseModel):
    """Preset animation metadata from Meshy Animation Library."""
    model_config = ConfigDict(extra="ignore")

    action_id: int = Field(..., description="Unique integer ID for the animation action.")
    name: str = Field(..., description="Human-readable animation name.")
    key: str = Field(..., description="Unique stable slug identifier.")
    category: str = Field(..., description="Top-level category: WalkAndRun, BodyMovements, DailyActions, Fighting, Dancing.")
    sub_category: Optional[str] = Field(default=None, description="Sub-category grouping.")
    preview_url: Optional[str] = Field(default=None, description="Direct URL to animated GIF preview.")


class ListAnimationsInput(BaseModel):
    """Filter parameters for querying available animations."""
    model_config = ConfigDict(extra="ignore")

    category: Optional[str] = Field(default=None, description="Filter by category: WalkAndRun, BodyMovements, DailyActions, Fighting, Dancing.")
    sub_category: Optional[str] = Field(default=None, description="Filter by sub-category.")
    search: Optional[str] = Field(default=None, description="Search term matching name or key.")
    action_ids: Optional[List[int]] = Field(default=None, description="Specific action IDs to fetch.")
    limit: Optional[int] = Field(default=50, ge=1, le=500, description="Max items to return.")


class ListAnimationsOutput(BaseModel):
    """Response containing matched animation presets."""
    model_config = ConfigDict(extra="ignore")

    total_count: int = Field(..., description="Total animations matching the criteria.")
    animations: List[AnimationItem] = Field(default_factory=list, description="List of matched animations.")
    categories: List[str] = Field(default_factory=list, description="Available category names.")


class AnimateAssetInput(BaseModel):
    """Workload request parameters to retarget an animation onto a rigged character."""
    model_config = ConfigDict(extra="ignore")

    asset_id: Optional[str] = Field(default=None, description="Rigged asset ID or mesh ID.")
    rig_task_id: Optional[str] = Field(default=None, description="Meshy cloud rigging task ID.")
    input_mesh_path: Optional[str] = Field(default=None, description="Local path to rigged GLB/FBX.")
    action_id: Optional[int] = Field(default=None, description="Preset animation action ID from library.")
    action_name: Optional[str] = Field(default=None, description="Action name or keyword to search if action_id is not specified.")
    fps: int = Field(default=30, description="Target animation frame rate: 24, 25, 30, 60.")
    output_format: str = Field(default="glb", description="Desired 3D file format: glb or fbx.")
    backend: Literal["meshy", "blender"] = Field(default="meshy", description="Animation engine backend: 'meshy' (cloud retargeting) or 'blender' (local procedural/pose).")


class AnimateAssetOutput(BaseModel):
    """Result of retargeting an animation onto a character."""
    model_config = ConfigDict(extra="ignore")

    animated_asset_id: str = Field(..., description="Unique identifier for the animated asset.")
    animation_task_id: Optional[str] = Field(default=None, description="Meshy animation cloud task ID.")
    rig_task_id: Optional[str] = Field(default=None, description="Source rigging task ID.")
    action_id: Optional[int] = Field(default=None, description="Applied animation action ID.")
    action_name: Optional[str] = Field(default=None, description="Applied animation action name.")
    animated_glb_path: Optional[str] = Field(default=None, description="Local path to animated GLB file.")
    animated_fbx_path: Optional[str] = Field(default=None, description="Local path to animated FBX file.")
    preview_url: Optional[str] = Field(default=None, description="URL of animated GIF preview.")
    status: Literal["success", "mock_success"] = Field(default="success", description="Execution status.")
    duration_seconds: float = Field(default=0.0, description="Execution time in seconds.")


__all__ = [
    "AnimateAssetInput",
    "AnimateAssetOutput",
    "AnimationItem",
    "ListAnimationsInput",
    "ListAnimationsOutput",
]
