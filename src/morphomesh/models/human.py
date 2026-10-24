"""
MorphoMesh: Digital Human Pipeline Schemas (FastMCP Tools 8-12).
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .base import BoundingBox


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


__all__ = [
    "AutoRigHumanInput",
    "AutoRigHumanOutput",
    "CreateHumanAssetInput",
    "CreateHumanAssetOutput",
    "DressHumanInput",
    "DressHumanOutput",
    "GroomHumanInput",
    "GroomHumanOutput",
    "HumanAnatomyConfig",
    "HumanAssetResult",
    "HumanGroomingResult",
    "HumanMaterialResult",
    "HumanRigResult",
    "HumanWardrobeResult",
    "SetupHumanMaterialsInput",
    "SetupHumanMaterialsOutput",
]
