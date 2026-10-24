"""
MorphoMesh: Geometric and Scene Primitive Schemas.
"""
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class BoundingBox(BaseModel):
    model_config = ConfigDict(extra="ignore")
    min_point: List[float] = Field(..., description="[min_x, min_y, min_z]")
    max_point: List[float] = Field(..., description="[max_x, max_y, max_z]")
    dimensions: List[float] = Field(..., description="[width, depth, height]")


class SceneObjectInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    type: str
    location: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation_euler: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale: List[float] = Field(default_factory=lambda: [1.0, 1.0, 1.0])
    parent: Optional[str] = None
    children: List[str] = Field(default_factory=list)
    vertex_count: int = 0
    face_count: int = 0
    triangle_count: int = 0
    materials: List[str] = Field(default_factory=list)
    modifiers: List[str] = Field(default_factory=list)


class BoundingBox3D(BaseModel):
    """World-space Axis-Aligned Bounding Box."""
    model_config = ConfigDict(extra="ignore")

    min_point: List[float] = Field(..., description="[min_x, min_y, min_z]")
    max_point: List[float] = Field(..., description="[max_x, max_y, max_z]")
    dimensions: List[float] = Field(..., description="[width, depth, height]")


__all__ = [
    "BoundingBox",
    "BoundingBox3D",
    "SceneObjectInfo",
]
