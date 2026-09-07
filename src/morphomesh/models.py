"""
MorphoMesh: Pydantic v2 Data Models, Enums, and Error Taxonomy.

This module defines all authoritative data structures, enumeration types,
and error constants conforming to Model Context Protocol (MCP) Specification
MM-R3-SPEC-001 and Architecture Standard MM-R2-ARCH-001.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


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
ERR_HUMAN_GENERATION_FAILED = -32030
ERR_HUMAN_RIGGING_FAILED = -32031
ERR_HUMAN_MATERIALS_FAILED = -32032
ERR_HUMAN_GROOMING_FAILED = -32033
ERR_HUMAN_WARDROBE_FAILED = -32034
ERR_INVALID_LANDMARK = -32035


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


# ==============================================================================
# TOOL 2: morphomesh_create_3d_asset
# ==============================================================================

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


# ==============================================================================
# DIGITAL HUMAN PIPELINE SCHEMAS (MILESTONE 1 - INDUSTRIAL DIGITAL HUMAN ENGINE)
# ==============================================================================

class HumanAnatomyConfig(BaseModel):
    """Anthropometric parametric specification for digital human geometry synthesis."""
    model_config = ConfigDict(extra="ignore")

    height: float = Field(default=1.65, ge=1.0, le=2.5, description="Total standing height in meters (canonical: 1.65m).")
    head_ratio: float = Field(default=7.41, ge=5.0, le=10.0, description="Height-to-head ratio (Yu Nian An: 7.41 heads).")
    chest_girth: float = Field(default=0.82, ge=0.5, le=1.5, description="Chest / bust circumference in meters.")
    waist_girth: float = Field(default=0.58, ge=0.4, le=1.2, description="Waist circumference in meters (cinched waist).")
    hip_girth: float = Field(default=0.86, ge=0.5, le=1.5, description="Hip circumference in meters (0.70 waist-to-hip ratio).")
    shoulder_width: float = Field(default=0.36, ge=0.2, le=0.8, description="Biacromial shoulder diameter in meters.")
    arm_span: float = Field(default=1.62, ge=1.0, le=2.5, description="Fingertip-to-fingertip arm span in meters.")
    leg_length: float = Field(default=0.88, ge=0.5, le=1.5, description="Inseam / leg length in meters.")
    gender: str = Field(default="female", description="Biological gender template ('female' or 'male').")
    style: str = Field(default="stylized_photorealism", description="Visual aesthetic style ('stylized_photorealism', 'realistic').")
    poly_budget: int = Field(default=25000, ge=1000, le=200000, description="Target polygon face budget for body mesh.")


# TOOL 8: morphomesh_create_human_asset
class CreateHumanAssetInput(BaseModel):
    """Input parameters for morphomesh_create_human_asset."""
    model_config = ConfigDict(extra="ignore")

    character_name: str = Field(default="Yu_Nian_An", description="Character identifier name.")
    prompt: str = Field(default="Yu Nian An female semi-realistic character", description="Prompt description.")
    gender: str = Field(default="female", description="Character gender.")
    height: float = Field(default=1.65, ge=1.0, le=2.5, description="Height in meters.")
    head_ratio: float = Field(default=7.41, ge=5.0, le=10.0, description="Head-to-body proportion ratio.")
    style: str = Field(default="stylized_photorealism", description="Visual aesthetic style.")
    chest_girth: float = Field(default=0.82, ge=0.5, le=1.5, description="Chest girth in meters.")
    waist_girth: float = Field(default=0.58, ge=0.4, le=1.2, description="Waist girth in meters.")
    hip_girth: float = Field(default=0.86, ge=0.5, le=1.5, description="Hip girth in meters.")
    poly_budget: int = Field(default=25000, ge=1000, le=200000, description="Target face count.")
    include_blendshapes: bool = Field(default=True, description="Generate 52 Apple ARKit FACS blendshapes.")
    export_format: str = Field(default="glb", description="Export format (glb, obj, fbx).")
    load_into_scene: bool = Field(default=True, description="Load created mesh into active Blender scene.")
    config: Optional[HumanAnatomyConfig] = Field(default=None, description="Optional nested anatomy configuration.")

    @model_validator(mode="before")
    @classmethod
    def resolve_nested_config(cls, data: Any) -> Any:
        if isinstance(data, dict) and data.get("config") is not None:
            cfg = data["config"]
            cfg_dict = cfg.model_dump() if hasattr(cfg, "model_dump") else (cfg if isinstance(cfg, dict) else {})
            for key in ["height", "head_ratio", "gender", "style", "chest_girth", "waist_girth", "hip_girth", "poly_budget"]:
                if key in cfg_dict:
                    default_val = cls.model_fields[key].default
                    if key not in data or data[key] == default_val:
                        data[key] = cfg_dict[key]
        return data


class HumanAssetResult(BaseModel):
    """Authoritative result of digital human mesh generation."""
    model_config = ConfigDict(extra="ignore")

    asset_id: str = Field(..., description="Unique human asset UUID.")
    mesh_path: str = Field(..., description="Path to generated 3D mesh file on disk.")
    character_name: str = Field(default="Yu_Nian_An", description="Character identifier name.")
    gender: str = Field(default="female", description="Character gender.")
    height: float = Field(default=1.65, description="Total standing height in meters.")
    head_ratio: float = Field(default=7.41, description="Height-to-head ratio.")
    vertex_count: int = Field(..., description="Total vertex count.")
    face_count: int = Field(..., description="Total polygon face count.")
    quad_ratio: float = Field(default=0.95, ge=0.0, le=1.0, description="Fraction of quads in mesh (>=0.95 in deforming areas).")
    vertex_groups: List[str] = Field(default_factory=list, description="Populated standardized vertex groups.")
    landmarks: Dict[str, List[float]] = Field(default_factory=dict, description="Anatomical 3D landmark coordinates for Rigify snapping.")
    shape_keys: List[str] = Field(default_factory=list, description="52 ARKit FACS shape key names.")
    bounding_box: BoundingBox = Field(..., description="Calculated 3D bounding box.")
    has_pbr_materials: bool = Field(default=False, description="Whether PBR materials are bound.")
    status: Literal["success", "mock_success"] = Field(default="success", description="Execution status.")


CreateHumanAssetOutput = HumanAssetResult


# TOOL 9: morphomesh_auto_rig_human
class AutoRigHumanInput(BaseModel):
    """Input parameters for morphomesh_auto_rig_human."""
    model_config = ConfigDict(extra="ignore")

    human_asset_id: Optional[str] = Field(default=None, description="Human asset UUID to rig.")
    mesh_object_name: str = Field(default="Human_Base_Mesh", description="Target mesh object name in Blender scene.")
    target_object: Optional[str] = Field(default=None, description="Alias for mesh_object_name.")
    rig_type: str = Field(default="rigify_human", description="Rig type (rigify_human, basic_biped).")
    skinning_method: str = Field(default="automatic_weights", description="Skin binding algorithm.")
    include_face_rig: bool = Field(default=True, description="Include 28 facial deformer bones.")
    include_finger_rig: bool = True
    pose: str = Field(default="puppeteer_pose", description="Initial rest or test pose (puppeteer_pose, a_pose, t_pose).")
    export_format: str = Field(default="fbx", description="Target rigged export format.")


class HumanRigResult(BaseModel):
    """Authoritative result of digital human rigging."""
    model_config = ConfigDict(extra="ignore")

    rigged_asset_id: str = Field(..., description="Unique rigged asset UUID.")
    armature_name: str = Field(..., description="Name of the generated armature in Blender.")
    bone_count: int = Field(..., description="Total bone count in armature.")
    def_bone_count: int = Field(default=163, description="Exact count of DEF deforming bones (163 DEF bones).")
    bone_hierarchy: List[str] = Field(default_factory=list, description="List of primary deform bone names.")
    blend_file_path: Optional[str] = Field(default=None, description="Path to saved .blend file if requested.")
    exported_mesh_path: Optional[str] = Field(default=None, description="Path to exported rigged asset on disk.")
    has_skin_weights: bool = Field(default=True, description="Whether anti-pinch skin weights are bound.")
    pose: str = Field(default="puppeteer_pose", description="Active pose applied to the rig.")
    status: Literal["success", "mock_success"] = Field(default="success", description="Execution status.")


AutoRigHumanOutput = HumanRigResult


# TOOL 10: morphomesh_setup_human_materials
class SetupHumanMaterialsInput(BaseModel):
    """Input parameters for morphomesh_setup_human_materials."""
    model_config = ConfigDict(extra="ignore")

    mesh_object_name: str = Field(default="Human_Base_Mesh", description="Target character body mesh object name.")
    target_object: Optional[str] = Field(default=None, description="Alias for mesh_object_name.")
    material_preset: str = Field(default="yu_nian_an", description="PBR shader preset ('yu_nian_an', 'standard_human').")
    skin_tone: str = Field(default="porcelain_fair", description="Skin tone base color preset.")
    subsurface_scattering: bool = Field(default=True, description="Enable Random Walk SSS on skin shader.")
    refractive_eyes: bool = Field(default=True, description="Configure 2-chamber refractive cornea and concave iris dish.")
    render_engine: str = Field(default="CYCLES", description="Target render engine ('CYCLES', 'BLENDER_EEVEE').")
    save_after: bool = Field(default=False, description="Save .blend file after material assignment.")
    save_path: Optional[str] = Field(default=None, description="Destination path for saved .blend file.")


class HumanMaterialResult(BaseModel):
    """Authoritative result of human PBR material setup."""
    model_config = ConfigDict(extra="ignore")

    material_preset: str = Field(default="yu_nian_an", description="PBR material preset configured.")
    materials_created: List[str] = Field(default_factory=list, description="Names of created materials.")
    assigned_objects: List[str] = Field(default_factory=list, description="Objects receiving material assignments.")
    subsurface_scattering: bool = Field(default=True, description="Subsurface scattering status.")
    refractive_eyes: bool = Field(default=True, description="Dual-chamber eye optics status.")
    socket_version: str = Field(default="Principled BSDF v2", description="Shader socket architecture version.")
    blend_file_path: Optional[str] = Field(default=None, description="Path to saved .blend file if saved.")
    status: Literal["success", "mock_success"] = Field(default="success", description="Execution status.")


SetupHumanMaterialsOutput = HumanMaterialResult


# TOOL 11: morphomesh_groom_human
class GroomHumanInput(BaseModel):
    """Input parameters for morphomesh_groom_human."""
    model_config = ConfigDict(extra="ignore")

    mesh_object_name: str = Field(default="Human_Base_Mesh", description="Target mesh object name in scene.")
    target_object: Optional[str] = Field(default=None, description="Alias for mesh_object_name.")
    hair_style: str = Field(default="hime_cut_long", description="Hairstyle preset ('hime_cut_long', 'straight_bangs').")
    hairstyle: Optional[str] = Field(default=None, description="Alias for hair_style.")
    hair_color: str = Field(default="silky_black", description="Hair melanin and color preset.")
    strand_count: int = Field(default=15000, ge=1000, le=200000, description="Parent/guide hair curves count.")
    include_eyebrows: bool = Field(default=True, description="Include procedural eyebrow groom curves.")
    include_eyelashes: bool = Field(default=True, description="Include procedural eyelash groom curves.")
    generate_ribbons: bool = Field(default=False, description="Generate polygonal quad ribbon mesh for real-time export.")
    save_after: bool = Field(default=False, description="Save .blend file after grooming.")
    save_path: Optional[str] = Field(default=None, description="Destination path for saved .blend file.")


class HumanGroomingResult(BaseModel):
    """Authoritative result of human hair grooming setup."""
    model_config = ConfigDict(extra="ignore")

    hair_style: str = Field(default="hime_cut_long", description="Configured hairstyle preset.")
    hair_color: str = Field(default="silky_black", description="Hair tint and melanin configuration.")
    layers: List[str] = Field(default_factory=list, description="Hair strata layers (bangs, sidelocks, back cascade, etc.).")
    strand_count: int = Field(default=15000, description="Total guide/parent curve strands created.")
    hair_objects: List[str] = Field(default_factory=list, description="Names of created Hair Curves objects in Blender.")
    blend_file_path: Optional[str] = Field(default=None, description="Path to saved .blend file if saved.")
    status: Literal["success", "mock_success"] = Field(default="success", description="Execution status.")


GroomHumanOutput = HumanGroomingResult


# TOOL 12: morphomesh_dress_human
class DressHumanInput(BaseModel):
    """Input parameters for morphomesh_dress_human."""
    model_config = ConfigDict(extra="ignore")

    human_object_name: str = Field(default="Human_Base_Mesh", description="Target character body mesh object name.")
    target_object: Optional[str] = Field(default=None, description="Alias for human_object_name.")
    outfit: str = Field(default="yu_nian_an_dress", description="Costume preset ('yu_nian_an_dress').")
    outfit_preset: Optional[str] = Field(default=None, description="Alias for outfit.")
    include_sandals: bool = Field(default=True, description="Include flat slip-on sandals.")
    include_red_threads: bool = Field(default=True, description="Include 10 taut glowing crimson marionette strings.")
    include_glowing_butterflies: bool = Field(default=True, description="Include instanced luminous white butterflies.")
    butterfly_count: int = Field(default=10, ge=1, le=50, description="Count of luminous white butterflies to stage.")
    clearance_offset: float = Field(default=0.015, ge=0.005, le=0.05, description="Garment body radial clearance offset in meters.")
    save_after: bool = Field(default=False, description="Save .blend file after wardrobe generation.")
    save_path: Optional[str] = Field(default=None, description="Destination path for saved .blend file.")


class HumanWardrobeResult(BaseModel):
    """Authoritative result of human wardrobe and props generation."""
    model_config = ConfigDict(extra="ignore")

    outfit_preset: str = Field(default="yu_nian_an_dress", description="Costume preset configured.")
    garments: List[str] = Field(default_factory=list, description="Names of generated garment meshes (bodice, sash, pleated skirt).")
    accessories: List[str] = Field(default_factory=list, description="Names of generated accessories (sandals, red strings).")
    prop_count: int = Field(default=20, description="Total count of active props (10 strings + 10 butterflies).")
    clearance_offset: float = Field(default=0.015, description="Radial body clearance maintained to eliminate clipping.")
    blend_file_path: Optional[str] = Field(default=None, description="Path to saved .blend file if saved.")
    status: Literal["success", "mock_success"] = Field(default="success", description="Execution status.")


DressHumanOutput = HumanWardrobeResult


# ==============================================================================
# INSPECTOR CAMERA & VIEWPORT CAPTURE SCHEMAS (MILESTONE 2)
# ==============================================================================

class InspectorViewpoint(str, Enum):
    FRONT = "front"
    SIDE = "side"
    SIDE_LEFT = "side_left"
    BACK = "back"
    THREE_QUARTER = "three_quarter"
    TOP = "top"
    BOTTOM = "bottom"
    HEAD = "head"
    CLOSE_UP_HEAD = "close_up_head"
    PORTRAIT = "portrait"
    HANDS = "hands"
    CLOSE_UP_HANDS = "close_up_hands"
    TORSO = "torso"
    FEET = "feet"
    TURNTABLE = "turntable"
    TURNTABLE_4VIEWS = "turntable_4views"


class AnthropometricPreset(str, Enum):
    REALISTIC_HUMAN = "realistic_human"
    STYLIZED_HEROINE = "stylized_heroine"
    CHIBI_PETITE = "chibi_petite"
    REALISTIC_FEMALE = "realistic_female"
    HEROIC_MALE = "heroic_male"
    CHIBI = "chibi"


TargetPreset = AnthropometricPreset


VALID_INSPECTOR_VIEWPOINTS_SET = {e.value for e in InspectorViewpoint} | {
    "view_front", "front_view", "side_right", "view_side", "view_side_left",
    "view_back", "back_view", "front_three_quarter", "three_quarter_left",
    "back_three_quarter", "head_close_up", "hands_close_up", "marionette",
    "bodice", "sandals", "shoes",
}


class DiagnosticShadingMode(str, Enum):
    SOLID = "SOLID"
    FLAT = "FLAT"
    WIREFRAME = "WIREFRAME"
    MATERIAL = "MATERIAL"
    RENDERED = "RENDERED"


class DiagnosticColorType(str, Enum):
    RANDOM = "RANDOM"
    MATERIAL = "MATERIAL"
    SINGLE = "SINGLE"
    OBJECT = "OBJECT"
    TEXTURE = "TEXTURE"


class BoundingBox3D(BaseModel):
    """World-space Axis-Aligned Bounding Box."""
    model_config = ConfigDict(extra="ignore")

    min_point: List[float] = Field(..., description="[min_x, min_y, min_z]")
    max_point: List[float] = Field(..., description="[max_x, max_y, max_z]")
    dimensions: List[float] = Field(..., description="[width, depth, height]")


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


# ==============================================================================
# VISUAL QUALITY CRITIQUE SCHEMAS (MILESTONE 3)
# ==============================================================================

class DefectSeverity(str, Enum):
    """Authoritative defect severity ranking."""
    CRITICAL = "CRITICAL"  # Severe penetration (>5mm), mesh collapse (>50% vol loss), broken anatomy
    MAJOR = "MAJOR"        # Significant penetration (1-5mm), proportion deviation (>15%), pinching
    MINOR = "MINOR"        # Slight clearance breach (<1mm), minor proportion deviation, stray curves
    INFO = "INFO"          # Informational: recommendation or diagnostic observation

    @classmethod
    def _missing_(cls, value: object) -> Any:
        if isinstance(value, str):
            val_upper = value.strip().upper()
            mapping = {
                "HIGH": cls.CRITICAL,
                "MEDIUM": cls.MAJOR,
                "LOW": cls.MINOR,
                "ERROR": cls.CRITICAL,
                "WARNING": cls.MAJOR,
                "NOTICE": cls.INFO,
            }
            if val_upper in mapping:
                return mapping[val_upper]
            for member in cls:
                if member.value.upper() == val_upper or member.name.upper() == val_upper:
                    return member
        return None


class DefectCategory(str, Enum):
    """Categorization of automated visual critique defects."""
    PENETRATION = "PENETRATION"              # Garment/armor clipping through body or intersecting layers
    PROPORTION = "PROPORTION"                # Anthropometric proportion deviation from target archetype
    SKINNING_PINCH = "SKINNING_PINCH"        # Joint skinning deformation, candy-wrapper collapse, acute crease
    GROOMING_COLLISION = "GROOMING_COLLISION" # Hair curves submerged inside scalp, clipping garments/props

    @classmethod
    def _missing_(cls, value: object) -> Any:
        if isinstance(value, str):
            val_upper = value.strip().upper()
            mapping = {
                "CLIPPING": cls.PENETRATION,
                "MESH_PENETRATION": cls.PENETRATION,
                "FACE_OVERLAP": cls.PENETRATION,
                "SKIN_BURST": cls.PENETRATION,
                "PROPORTION_DEVIATION": cls.PROPORTION,
                "BODY_PROPORTION": cls.PROPORTION,
                "SKINNING_ARTIFACT": cls.SKINNING_PINCH,
                "RIG_PINCH": cls.SKINNING_PINCH,
                "PINCHING": cls.SKINNING_PINCH,
                "GROOMING_INTERSECTION": cls.GROOMING_COLLISION,
                "HAIR_CLIPPING": cls.GROOMING_COLLISION,
                "GROOMING_ROOT_SUBMERGED": cls.GROOMING_COLLISION,
                "GROOMING_BODY_COLLISION": cls.GROOMING_COLLISION,
                "GROOMING_GARMENT_COLLISION": cls.GROOMING_COLLISION,
            }
            if val_upper in mapping:
                return mapping[val_upper]
            for member in cls:
                if member.value.upper() == val_upper or member.name.upper() == val_upper:
                    return member
        return None


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


