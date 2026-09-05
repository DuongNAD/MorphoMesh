"""
MorphoMesh: Pydantic v2 Data Models, Enums, and Error Taxonomy.

This module defines all authoritative data structures, enumeration types,
and error constants conforming to Model Context Protocol (MCP) Specification
MM-R3-SPEC-001 and Architecture Standard MM-R2-ARCH-001.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator, ConfigDict


# ==============================================================================
# AUTHORITATIVE GLOBAL ERROR CODES MATRIX
# ==============================================================================

ERR_PARSE_ERROR = -32700
ERR_INVALID_REQUEST = -32600
ERR_METHOD_NOT_FOUND = -32601
ERR_INVALID_ARGUMENT = -32602
ERR_IMAGE_NOT_FOUND = -32001
ERR_BACKEND_UNAVAILABLE = -32002
ERR_VRAM_EXHAUSTED = -32003
ERR_REMESH_FAILED = -32004
ERR_SKINNING_HEAT_FAILURE = -32005
ERR_SCRIPT_SECURITY_VIOLATION = -32006
ERR_TIMEOUT = -32007
ERR_BLENDER_UNAVAILABLE = -32008
ERR_NO_CAMERA = -32009
ERR_ANATOMY_DETECTION_FAILED = -32010
ERR_INPUT_MESH_NOT_FOUND = -32011
ERR_INVALID_POLY_COUNT = -32012
ERR_NON_MANIFOLD_MESH = -32013
ERR_SCENE_NOT_FOUND = -32014
ERR_RENDER_FAILED = -32015
ERR_OUTPUT_WRITE_FAILED = -32016
ERR_SCRIPT_SYNTAX_ERROR = -32017
ERR_SCRIPT_RUNTIME_EXCEPTION = -32018
ERR_INFERENCE_FAILED = -32019
ERR_DISK_WRITE_FAILED = -32020
ERR_SCRIPT_EXECUTION_TIMEOUT = -32007
ERR_BLENDER_EXECUTION_FAILED = -32021


class MorphoMeshException(Exception):
    """Authoritative base exception for all domain-specific MorphoMesh errors."""

    def __init__(
        self,
        code: Union[int, str],
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{code}] {message}")


# ==============================================================================
# ENUMERATIONS
# ==============================================================================

class CreatureType(str, Enum):
    QUADRUPED = "quadruped"
    BIPED = "biped"
    WINGED = "winged"
    AQUATIC = "aquatic"
    SERPENTINE = "serpentine"
    HYBRID = "hybrid"
    CUSTOM = "custom"
    WINGED_QUADRUPED = "winged_quadruped"
    BIRD = "bird"
    SPIDER_ARTHROPOD = "spider_arthropod"
    FISH_AQUATIC = "fish_aquatic"
    CUSTOM_AUTO = "custom_auto"


class ViewMode(str, Enum):
    FRONT = "front"
    SIDE = "side"
    THREE_QUARTER = "three_quarter"
    TOP = "top"
    TURNAROUND_SHEET = "turnaround_sheet"
    ORTHOGRAPHIC_FRONT_SIDE = "orthographic_front_side"
    TURNTABLE_4VIEWS = "turntable_4views"
    ACTIVE_CAMERA = "active_camera"


class Pose(str, Enum):
    NEUTRAL_T_POSE = "neutral_t_pose"
    NEUTRAL_A_POSE = "neutral_a_pose"
    STANDING_NEUTRAL = "standing_neutral"
    RELAXED = "relaxed"


class Style(str, Enum):
    REALISTIC = "realistic"
    STYLIZED = "stylized"
    DARK_FANTASY = "dark_fantasy"
    SCI_FI = "sci_fi"
    CARTOON = "cartoon"
    SCULPTURE = "sculpture"


class QualityTier(str, Enum):
    DRAFT = "draft"
    STANDARD = "standard"
    PRODUCTION = "production"
    ULTRA = "ultra"


class TopologyType(str, Enum):
    QUAD_DOMINANT = "quad_dominant"
    PURE_QUAD = "pure_quad"
    TRIANGULATED = "triangulated"
    ADAPTIVE = "adaptive"


class RetopoMethod(str, Enum):
    QUADRIFLOW = "quadriflow"
    DECIMATE = "decimate"
    VOXEL_REMESH = "voxel_remesh"
    MESHANYTHING_V2 = "meshanything_v2"
    MOCK = "mock"


class RigType(str, Enum):
    BASIC_FK = "basic_fk"
    RIGIFY_CREATURE = "rigify_creature"
    GAME_ENGINE_ROOT = "game_engine_root"
    DEFORM_ONLY = "deform_only"


class SkinningMethod(str, Enum):
    AUTOMATIC_WEIGHTS = "automatic_weights"
    VOXEL_HEAT_DIFFUSE = "voxel_heat_diffuse"
    GEODESIC_VOXEL = "geodesic_voxel"


class RenderEngine(str, Enum):
    BLENDER_EEVEE = "BLENDER_EEVEE"
    BLENDER_EEVEE_NEXT = "BLENDER_EEVEE_NEXT"
    CYCLES = "CYCLES"
    BLENDER_WORKBENCH = "BLENDER_WORKBENCH"


class LightingPreset(str, Enum):
    STUDIO_THREE_POINT = "studio_three_point"
    DRAMATIC_RIM = "dramatic_rim"
    NEUTRAL_SOFTBOX = "neutral_softbox"
    OUTDOOR_SUN = "outdoor_sun"
    SCENE_DEFAULT = "scene_default"


# ==============================================================================
# COMMON SCHEMAS
# ==============================================================================

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


# ==============================================================================
# TOOL 1: morphomesh_generate_concept
# ==============================================================================

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


# ==============================================================================
# TOOL 2: morphomesh_create_3d_asset
# ==============================================================================

class Create3DAssetInput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    image_path: Optional[str] = Field(default=None, description="Path to local concept image on disk.")
    concept_id: Optional[str] = Field(default=None, description="UUID of concept generated in Stage 1.")
    model_backend: str = Field(default="mock", description="3D AI generator engine backend (mock, trellis, hunyuan3d_2, step1x_3d, triposr).")
    export_format: str = Field(default="glb", description="Target 3D file format (glb, obj, fbx, ply).")
    generate_pbr: bool = Field(default=True, description="Bake PBR textures (albedo, roughness, metallic, normal).")
    texture_resolution: int = Field(default=2048, description="Texture atlas resolution in pixels.")
    remove_background: bool = Field(default=True, description="Perform foreground isolation before 3D reconstruction.")
    guidance_scale: float = Field(default=7.5, ge=1.0, le=20.0, description="Classifier-free guidance strength.")
    seed: int = Field(default=-1, ge=-1, description="RNG seed (-1 for random).")
    quality_tier: Optional[str] = Field(default="standard", description="Quality preset tier.")


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


# ==============================================================================
# TOOL 3: morphomesh_optimize_topology
# ==============================================================================

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


# ==============================================================================
# TOOL 4: morphomesh_auto_rig
# ==============================================================================

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


# ==============================================================================
# TOOL 5: morphomesh_blender_execute
# ==============================================================================

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


# ==============================================================================
# TOOL 6: morphomesh_get_scene_status
# ==============================================================================

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


# ==============================================================================
# TOOL 7: morphomesh_render_preview
# ==============================================================================

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
