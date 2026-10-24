"""
MorphoMesh: Creature Generation Pipeline Schemas (FastMCP Tools 1-7).
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .base import BoundingBox, SceneObjectInfo
from .enums import (
    CreatureType,
    LightingPreset,
    Pose,
    QualityTier,
    RenderEngine,
    RetopoMethod,
    RigType,
    SkinningMethod,
    Style,
    TopologyType,
    ViewMode,
)


class GenerateConceptInput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    prompt: str = Field(..., min_length=3, max_length=2000, description="Natural language description of creature anatomy, species, features.")
    negative_prompt: str = Field(default="", max_length=1000, description="Negative constraints to avoid artifacts, cropping, or occlusions.")
    creature_type: Union[CreatureType, str] = Field(default=CreatureType.CUSTOM, description="Morphological archetype guiding prompt augmentation.")
    view_mode: Union[ViewMode, str] = Field(default=ViewMode.FRONT, description="Camera perspective tailored for 3D reconstruction.")
    pose: Union[Pose, str] = Field(default=Pose.STANDING_NEUTRAL, description="Rest pose preventing limb self-occlusion.")
    style: Union[Style, str] = Field(default=Style.REALISTIC, description="Visual rendering aesthetic.")
    background: str = Field(default="white_neutral", description="Neutral backdrop ensuring clean segmentation.")
    width: int = Field(default=1024, ge=512, le=2048, description="Image width in pixels (multiple of 64).")
    height: int = Field(default=1024, ge=512, le=2048, description="Image height in pixels (multiple of 64).")
    seed: int = Field(default=-1, ge=-1, le=2147483647, description="RNG seed (-1 for random).")
    output_format: str = Field(default="png", description="File format on disk.")
    backend: str = Field(default="default", description="Generator backend engine ('default', 'mock', 'gemini').")

    @field_validator("width", "height")
    @classmethod
    def validate_dimension_step(cls, v: int) -> int:
        if v % 64 != 0:
            return round(v / 64) * 64
        return v


class GenerateConceptOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    concept_id: str = Field(..., description="Unique concept UUID")
    image_path: str = Field(..., description="Absolute path to cached image")
    rgba_image_path: Optional[str] = Field(default=None, description="Path to alpha-isolated image")
    prompt_enhanced: str = Field(..., description="Augmented prompt with anatomical modifiers")
    creature_type: str
    view_mode: str
    dimensions: List[int]
    seed_used: int
    status: Literal["success", "mock_success"]
    views: Dict[str, str] = Field(default_factory=dict, description="Segmented views for turnaround sheets")
    backend_used: Optional[str] = Field(default=None, description="Backend generator used")


class Create3DAssetInput(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    image_path: Optional[str] = Field(default=None, description="Path to local concept image on disk.")
    concept_id: Optional[str] = Field(default=None, description="UUID of concept generated in Stage 1.")
    model_backend: str = Field(default="mock", description="3D AI generator engine backend (mock, meshy, trellis, hunyuan3d_2, tripo, triposr, step1x_3d).")
    backend: Optional[str] = Field(default=None, description="Alias for model_backend allowing backend='meshy' selection.")
    export_format: str = Field(default="glb", description="Target 3D file format (glb, obj, fbx, ply).")
    generate_pbr: bool = Field(default=True, description="Bake PBR textures (albedo, roughness, metallic, normal).")
    texture_resolution: int = Field(default=2048, description="Texture atlas resolution in pixels.")
    remove_background: bool = Field(default=True, description="Perform foreground isolation before 3D reconstruction.")
    guidance_scale: float = Field(default=7.5, ge=1.0, le=20.0, description="Classifier-free guidance strength.")
    seed: int = Field(default=-1, ge=-1, description="RNG seed (-1 for random).")
    prompt: Optional[str] = Field(default=None, description="Direct text prompt for text-to-3D foundation models (e.g. Meshy, Tripo).")
    quality_tier: Optional[str] = Field(default="standard", description="Quality preset tier.")

    @model_validator(mode="before")
    @classmethod
    def resolve_backend_alias(cls, data: Any) -> Any:
        if isinstance(data, dict):
            backend = data.get("backend")
            model_backend = data.get("model_backend")
            if backend and (not model_backend or model_backend == "mock"):
                data["model_backend"] = backend
                data["backend"] = backend
            elif model_backend:
                data["backend"] = model_backend
        return data


class Create3DAssetOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    asset_id: str = Field(..., description="Unique 3D asset UUID")
    mesh_path: str = Field(..., description="Path to generated .glb/.obj file")
    format: str
    vertex_count: int
    face_count: int
    has_pbr_materials: bool
    texture_paths: Dict[str, str] = Field(default_factory=dict)
    bounding_box: BoundingBox
    generation_time_seconds: float
    backend_used: str


class OptimizeTopologyInput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    asset_id: Optional[str] = Field(default=None, description="Asset UUID from Stage 2.")
    input_mesh_path: Optional[str] = Field(default=None, description="Direct file path to 3D mesh.")
    target_poly_count: int = Field(default=10000, ge=500, le=500000, description="Desired polygon (face) count.")
    topology_type: Union[TopologyType, str] = Field(default=TopologyType.QUAD_DOMINANT, description="Preferred polygon topology.")
    preserve_uvs: bool = Field(default=True, description="Preserve UV coordinates.")
    preserve_sharp_edges: bool = Field(default=True, description="Preserve creased feature edges.")
    method: Union[RetopoMethod, str] = Field(default=RetopoMethod.QUADRIFLOW, description="Retopology solver algorithm.")
    output_format: str = Field(default="glb", description="Target file format.")


class OptimizeTopologyOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    optimized_asset_id: str
    output_mesh_path: str
    original_vertex_count: int
    original_face_count: int
    optimized_vertex_count: int
    optimized_face_count: int
    quad_percentage: float = Field(..., ge=0.0, le=100.0)
    reduction_ratio: float
    uv_preserved: bool
    processing_time_seconds: float


class AutoRigInput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    asset_id: Optional[str] = Field(default=None, description="Asset UUID to rig.")
    input_mesh_path: Optional[str] = Field(default=None, description="Direct path to mesh file.")
    creature_type: Union[CreatureType, str] = Field(default=CreatureType.QUADRUPED, description="Morphological archetype guiding metarig selection.")
    rig_type: Union[RigType, str] = Field(default=RigType.RIGIFY_CREATURE, description="Armature control hierarchy.")
    skinning_method: Union[SkinningMethod, str] = Field(default=SkinningMethod.AUTOMATIC_WEIGHTS, description="Vertex skin weighting algorithm.")
    symmetry: bool = Field(default=True, description="Enforce X bilateral symmetry.")
    generate_test_animation: bool = Field(default=True, description="Attach test animation action.")
    load_into_scene: bool = Field(default=True, description="Import into active Blender scene.")
    backend: Optional[str] = Field(default="blender", description="Rigging execution backend: 'blender' or 'meshy'.")
    model_task_id: Optional[str] = Field(default=None, description="Meshy generation task ID to rig via Meshy API.")
    height_meters: Optional[float] = Field(default=1.7, description="Approximate model height in meters for AI rigging.")


class AutoRigOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    rigged_asset_id: str
    blend_file_path: Optional[str] = None
    exported_mesh_path: str
    armature_name: str
    bone_count: int
    bone_hierarchy: List[str] = Field(default_factory=list)
    creature_type: str
    has_skin_weights: bool
    test_action_name: Optional[str] = None
    status: Literal["success", "mock_success"]
    rig_task_id: Optional[str] = Field(default=None, description="Meshy cloud rigging task ID if applicable.")
    downloaded_glb_path: Optional[str] = Field(default=None, description="Path to downloaded rigged GLB.")
    downloaded_fbx_path: Optional[str] = Field(default=None, description="Path to downloaded rigged FBX.")
    basic_animations: Dict[str, str] = Field(default_factory=dict, description="Paths or URLs to basic animations (e.g. walking, running).")


class BlenderExecuteInput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    script: str = Field(..., min_length=1, max_length=10000, description="Python script with bpy commands to execute in Blender.")
    timeout_seconds: int = Field(default=30, ge=1, le=300, description="Execution timeout limit in seconds.")
    target_scene: Optional[str] = Field(default=None, description="Target Blender scene name.")
    save_after: bool = Field(default=False, description="Save scene after execution.")
    save_path: Optional[str] = Field(default=None, description="Destination path for saved .blend file.")
    return_variables: List[str] = Field(default_factory=list, description="Variable names in script scope to serialize into response.")


class BlenderExecuteOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    success: bool
    stdout: str = ""
    stderr: str = ""
    returned_data: Dict[str, Any] = Field(default_factory=dict)
    execution_time_seconds: float = 0.0
    blend_file_path: Optional[str] = None


class SceneStatusInput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    scene_name: Optional[str] = Field(default=None, description="Specific scene name to inspect.")
    include_mesh_stats: bool = Field(default=True, description="Include vertex/face counts.")
    include_hierarchy: bool = Field(default=True, description="Include object parent-child relationships.")
    include_materials: bool = Field(default=True, description="Include Principled BSDF shader materials.")
    include_armatures: bool = Field(default=True, description="Include armature bone structures.")
    include_cameras_lights: bool = Field(default=True, description="Include cameras and lights.")


class SceneStatusOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    scene_name: str
    blender_version: str
    active_object: Optional[str] = None
    object_count: int
    total_vertices: int
    total_faces: int
    objects: List[SceneObjectInfo] = Field(default_factory=list)
    armatures: List[Dict[str, Any]] = Field(default_factory=list)
    cameras: List[Dict[str, Any]] = Field(default_factory=list)
    lights: List[Dict[str, Any]] = Field(default_factory=list)


class RenderPreviewInput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    camera_name: Optional[str] = Field(default=None, description="Camera object name.")
    resolution_width: int = Field(default=1024, ge=256, le=4096, description="Render width in pixels.")
    resolution_height: int = Field(default=1024, ge=256, le=4096, description="Render height in pixels.")
    render_engine: Union[RenderEngine, str] = Field(default=RenderEngine.BLENDER_EEVEE, description="Blender render engine.")
    samples: int = Field(default=64, ge=1, le=1024, description="Render samples.")
    view_angle: Union[ViewMode, str] = Field(default=ViewMode.THREE_QUARTER, description="Camera perspective viewpoint.")
    transparent_background: bool = Field(default=True, description="Transparent alpha background.")
    lighting_preset: Union[LightingPreset, str] = Field(default=LightingPreset.STUDIO_THREE_POINT, description="Studio lighting configuration.")
    save_to_disk: bool = Field(default=True, description="Save rendered image to disk cache.")
    output_dir: Optional[str] = Field(default=None, description="Destination directory for rendered PNG.")

    @field_validator("render_engine")
    @classmethod
    def normalize_engine(cls, v: Union[RenderEngine, str]) -> str:
        val = v.value if isinstance(v, RenderEngine) else str(v)
        # Blender 5.2.1 LTS strictly identifies EEVEE Next as 'BLENDER_EEVEE'
        if val == "BLENDER_EEVEE_NEXT":
            return "BLENDER_EEVEE"
        return val


class RenderPreviewOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    image_path: str
    image_format: str = "png"
    resolution: List[int]
    render_engine: str
    samples: int
    render_time_seconds: float
    view_angle: str
    lighting_preset: str
    base64_image: Optional[str] = None


__all__ = [
    "AutoRigInput",
    "AutoRigOutput",
    "BlenderExecuteInput",
    "BlenderExecuteOutput",
    "Create3DAssetInput",
    "Create3DAssetOutput",
    "GenerateConceptInput",
    "GenerateConceptOutput",
    "OptimizeTopologyInput",
    "OptimizeTopologyOutput",
    "RenderPreviewInput",
    "RenderPreviewOutput",
    "SceneStatusInput",
    "SceneStatusOutput",
]
