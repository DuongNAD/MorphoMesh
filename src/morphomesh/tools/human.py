"""
MorphoMesh Tools Subsystem: Digital Human Engine Tools.

Implements the 7 authoritative MCP tools for AAA digital human generation:
1. morphomesh_create_human_asset
2. morphomesh_auto_rig_human
3. morphomesh_setup_human_materials
4. morphomesh_groom_human
5. morphomesh_dress_human
6. morphomesh_assemble_master_character
7. morphomesh_export_production_character
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context
from mcp.server.fastmcp.exceptions import ToolError

from morphomesh.models import (
    AutoRigHumanInput,
    CreateHumanAssetInput,
    DressHumanInput,
    GroomHumanInput,
    HumanAnatomyConfig,
    MorphoMeshException,
    SetupHumanMaterialsInput,
)
from morphomesh.tools.base import _safe_ctx_info, _safe_ctx_progress
from morphomesh.tools.dependencies import blender_bridge


# ==============================================================================
# TOOL 8: morphomesh_create_human_asset
# ==============================================================================

async def morphomesh_create_human_asset(
    character_name: str = "Yu_Nian_An",
    prompt: str = "Yu Nian An female semi-realistic character",
    gender: str = "female",
    height: float = 1.65,
    head_ratio: float = 7.41,
    style: str = "stylized_photorealism",
    chest_girth: float = 0.82,
    waist_girth: float = 0.58,
    hip_girth: float = 0.86,
    poly_budget: int = 25000,
    include_blendshapes: bool = True,
    export_format: str = "glb",
    load_into_scene: bool = True,
    assemble_master: bool = False,
    config: Optional[HumanAnatomyConfig] = None,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Stage 1 Human Engine: Generate an anthropometrically accurate 3D female human mesh.

    Synthesizes watertight, quad-dominant human body mesh (>=95% quads) based on Yu Nian An
    canonical proportions (1.65m height, 7.41 head ratio, cinched waist, 0.70 WHR).
    Constructs 24 standardized vertex groups, 10 articulated fingers (3 phalanges each),
    feet geometry, 34 Rigify bone snapping landmarks with pre-bends, and 52 ARKit FACS shape keys.
    Can also orchestrate full character master assembly when assemble_master=True.
    """
    await _safe_ctx_info(ctx, "Initializing Digital Human Parametric Mesh Synthesis...")
    await _safe_ctx_progress(ctx, 15, 100)

    try:
        if assemble_master:
            await _safe_ctx_info(ctx, f"Triggering full character master assembly for {character_name}...")
            return await morphomesh_assemble_master_character(
                character_name=character_name,
                height=height,
                head_ratio=head_ratio,
                ctx=ctx,
            )

        if config is not None:
            cfg_dict = config.model_dump() if hasattr(config, "model_dump") else (config if isinstance(config, dict) else {})
            if height == 1.65 and "height" in cfg_dict:
                height = cfg_dict["height"]
            if head_ratio == 7.41 and "head_ratio" in cfg_dict:
                head_ratio = cfg_dict["head_ratio"]
            if chest_girth == 0.82 and "chest_girth" in cfg_dict:
                chest_girth = cfg_dict["chest_girth"]
            if waist_girth == 0.58 and "waist_girth" in cfg_dict:
                waist_girth = cfg_dict["waist_girth"]
            if hip_girth == 0.86 and "hip_girth" in cfg_dict:
                hip_girth = cfg_dict["hip_girth"]
            if gender == "female" and "gender" in cfg_dict:
                gender = cfg_dict["gender"]
            if style == "stylized_photorealism" and "style" in cfg_dict:
                style = cfg_dict["style"]
            if poly_budget == 25000 and "poly_budget" in cfg_dict:
                poly_budget = cfg_dict["poly_budget"]

        req = CreateHumanAssetInput(
            character_name=character_name,
            prompt=prompt,
            gender=gender,
            height=height,
            head_ratio=head_ratio,
            style=style,
            chest_girth=chest_girth,
            waist_girth=waist_girth,
            hip_girth=hip_girth,
            poly_budget=poly_budget,
            include_blendshapes=include_blendshapes,
            export_format=export_format,
            load_into_scene=load_into_scene,
            config=config,
        )

        res = blender_bridge.create_human_asset(
            character_name=req.character_name,
            prompt=req.prompt,
            gender=req.gender,
            height=req.height,
            head_ratio=req.head_ratio,
            style=req.style,
            chest_girth=req.chest_girth,
            waist_girth=req.waist_girth,
            hip_girth=req.hip_girth,
            poly_budget=req.poly_budget,
            include_blendshapes=req.include_blendshapes,
            export_format=req.export_format,
            load_into_scene=req.load_into_scene,
            config=req.config,
        )

        await _safe_ctx_progress(ctx, 100, 100)
        await _safe_ctx_info(ctx, f"Digital human asset generated successfully: {res.get('asset_id')}")

        return res
    except MorphoMeshException as e:
        raise ToolError(f"MorphoMesh Tool Error: [{e.code}] {e.message}")
    except Exception as e:
        raise ToolError(f"Unexpected Tool Failure in morphomesh_create_human_asset: {str(e)}")


# ==============================================================================
# TOOL 9: morphomesh_auto_rig_human
# ==============================================================================

async def morphomesh_auto_rig_human(
    human_asset_id: Optional[str] = None,
    mesh_object_name: str = "Human_Base_Mesh",
    target_object: Optional[str] = None,
    rig_type: str = "rigify_human",
    skinning_method: str = "automatic_weights",
    include_face_rig: bool = True,
    include_finger_rig: bool = True,
    pose: str = "puppeteer_pose",
    export_format: str = "fbx",
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Stage 2 Human Engine: Rig digital human body mesh using Blender Rigify Human Armature.

    Snaps 163 DEF deforming bones to anatomical landmark points with explicit joint pre-bends
    (elbows +Y, knees -Y). Implements anti-pinch vertex skin weights across shoulders, elbows,
    and patella, and applies initial marionette puppeteer staging pose.
    """
    await _safe_ctx_info(ctx, "Initializing Rigify Human Auto-Rigging (163 DEF bones)...")
    await _safe_ctx_progress(ctx, 25, 100)

    try:
        effective_mesh = target_object or mesh_object_name
        req = AutoRigHumanInput(
            human_asset_id=human_asset_id,
            mesh_object_name=effective_mesh,
            target_object=target_object,
            rig_type=rig_type,
            skinning_method=skinning_method,
            include_face_rig=include_face_rig,
            include_finger_rig=include_finger_rig,
            pose=pose,
            export_format=export_format,
        )

        res = blender_bridge.auto_rig_human(
            human_asset_id=req.human_asset_id,
            mesh_object_name=req.mesh_object_name,
            target_object=req.target_object,
            rig_type=req.rig_type,
            skinning_method=req.skinning_method,
            include_face_rig=req.include_face_rig,
            include_finger_rig=req.include_finger_rig,
            pose=req.pose,
            export_format=req.export_format,
        )

        await _safe_ctx_progress(ctx, 100, 100)
        await _safe_ctx_info(ctx, f"Digital human rig generated successfully: {res.get('armature_name')}")

        return res
    except MorphoMeshException as e:
        raise ToolError(f"MorphoMesh Tool Error: [{e.code}] {e.message}")
    except Exception as e:
        raise ToolError(f"Unexpected Tool Failure in morphomesh_auto_rig_human: {str(e)}")


# ==============================================================================
# TOOL 10: morphomesh_setup_human_materials
# ==============================================================================

async def morphomesh_setup_human_materials(
    mesh_object_name: str = "Human_Base_Mesh",
    target_object: Optional[str] = None,
    material_preset: str = "yu_nian_an",
    skin_tone: str = "porcelain_fair",
    subsurface_scattering: bool = True,
    refractive_eyes: bool = True,
    render_engine: str = "CYCLES",
    save_after: bool = False,
    save_path: Optional[str] = None,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Stage 3 Human Engine: Setup photorealistic PBR materials for digital human character.

    Constructs Blender Principled BSDF v2 shaders with Random Walk Subsurface Scattering
    (radius [1.0, 0.22, 0.11]), dual-chamber refractive eye optics (cornea IOR 1.376, concave iris dish
    with tear meniscus IOR 1.333), silky dark hair shader, and translucent white silk fabric.
    """
    await _safe_ctx_info(ctx, "Setting up Principled BSDF v2 SSS Skin and Refractive Eye Optics...")
    await _safe_ctx_progress(ctx, 30, 100)

    try:
        effective_mesh = target_object or mesh_object_name
        req = SetupHumanMaterialsInput(
            mesh_object_name=effective_mesh,
            target_object=target_object,
            material_preset=material_preset,
            skin_tone=skin_tone,
            subsurface_scattering=subsurface_scattering,
            refractive_eyes=refractive_eyes,
            render_engine=render_engine,
            save_after=save_after,
            save_path=save_path,
        )

        res = blender_bridge.setup_human_materials(
            mesh_object_name=req.mesh_object_name,
            target_object=req.target_object,
            material_preset=req.material_preset,
            skin_tone=req.skin_tone,
            subsurface_scattering=req.subsurface_scattering,
            refractive_eyes=req.refractive_eyes,
            render_engine=req.render_engine,
            save_after=req.save_after,
            save_path=req.save_path,
        )

        await _safe_ctx_progress(ctx, 100, 100)
        await _safe_ctx_info(ctx, f"Materials configured successfully: {res.get('material_preset')}")

        return res
    except MorphoMeshException as e:
        raise ToolError(f"MorphoMesh Tool Error: [{e.code}] {e.message}")
    except Exception as e:
        raise ToolError(f"Unexpected Tool Failure in morphomesh_setup_human_materials: {str(e)}")


# ==============================================================================
# TOOL 11: morphomesh_groom_human
# ==============================================================================

async def morphomesh_groom_human(
    mesh_object_name: str = "Human_Base_Mesh",
    target_object: Optional[str] = None,
    hair_style: str = "hime_cut_long",
    hairstyle: Optional[str] = None,
    hair_color: str = "silky_black",
    strand_count: int = 15000,
    include_eyebrows: bool = True,
    include_eyelashes: bool = True,
    generate_ribbons: bool = False,
    save_after: bool = False,
    save_path: Optional[str] = None,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Stage 4 Human Engine: Generate procedural Geometry Nodes Hair Curves grooming.

    Creates 6 structural hair layers: eyebrow curves, eyelash arcs, straight blunt bangs
    brow-grazing hime cut, face-framing cheek sidelocks, crown scalp parting, and cascading
    back hair down to mid-thigh with anisotropic silky sheen. Optionally evaluates polygonal
    quad ribbons for real-time FBX/glTF export.
    """
    await _safe_ctx_info(ctx, "Generating Geometry Nodes Hair Curves (Hime Cut & Layers)...")
    await _safe_ctx_progress(ctx, 35, 100)

    try:
        effective_mesh = target_object or mesh_object_name
        effective_style = hairstyle or hair_style
        req = GroomHumanInput(
            mesh_object_name=effective_mesh,
            target_object=target_object,
            hair_style=effective_style,
            hairstyle=hairstyle,
            hair_color=hair_color,
            strand_count=strand_count,
            include_eyebrows=include_eyebrows,
            include_eyelashes=include_eyelashes,
            generate_ribbons=generate_ribbons,
            save_after=save_after,
            save_path=save_path,
        )

        res = blender_bridge.groom_human(
            mesh_object_name=req.mesh_object_name,
            target_object=req.target_object,
            hair_style=req.hair_style,
            hairstyle=req.hairstyle,
            hair_color=req.hair_color,
            strand_count=req.strand_count,
            include_eyebrows=req.include_eyebrows,
            include_eyelashes=req.include_eyelashes,
            generate_ribbons=req.generate_ribbons,
            save_after=req.save_after,
            save_path=req.save_path,
        )

        await _safe_ctx_progress(ctx, 100, 100)
        await _safe_ctx_info(ctx, f"Hair groom generated successfully: {res.get('hair_style')}")

        return res
    except MorphoMeshException as e:
        raise ToolError(f"MorphoMesh Tool Error: [{e.code}] {e.message}")
    except Exception as e:
        raise ToolError(f"Unexpected Tool Failure in morphomesh_groom_human: {str(e)}")


# ==============================================================================
# TOOL 12: morphomesh_dress_human
# ==============================================================================

async def morphomesh_dress_human(
    human_object_name: str = "Human_Base_Mesh",
    target_object: Optional[str] = None,
    outfit: str = "yu_nian_an_dress",
    outfit_preset: Optional[str] = None,
    include_sandals: bool = True,
    include_red_threads: bool = True,
    include_glowing_butterflies: bool = True,
    butterfly_count: int = 10,
    clearance_offset: float = 0.015,
    save_after: bool = False,
    save_path: Optional[str] = None,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Stage 5 Human Engine: Synthesize tailored wardrobe and character magic props.

    Generates sleeveless white strap slip dress bodice, cinched high-waist sash with hanging
    ribbon streamers, 20-pleat flared skirt with collision offset (0.015m) to eliminate clipping,
    flat slip-on sandals, 10 taut glowing crimson marionette strings tethered to finger distal heads,
    and 10 instanced luminous white butterflies.
    """
    await _safe_ctx_info(ctx, "Generating Yu Nian An Wardrobe, Sandals, Strings & Magic Butterflies...")
    await _safe_ctx_progress(ctx, 40, 100)

    try:
        effective_human = target_object or human_object_name
        effective_outfit = outfit_preset or outfit
        req = DressHumanInput(
            human_object_name=effective_human,
            target_object=target_object,
            outfit=effective_outfit,
            outfit_preset=outfit_preset,
            include_sandals=include_sandals,
            include_red_threads=include_red_threads,
            include_glowing_butterflies=include_glowing_butterflies,
            butterfly_count=butterfly_count,
            clearance_offset=clearance_offset,
            save_after=save_after,
            save_path=save_path,
        )

        res = blender_bridge.dress_human(
            human_object_name=req.human_object_name,
            target_object=req.target_object,
            outfit=req.outfit,
            outfit_preset=req.outfit_preset,
            include_sandals=req.include_sandals,
            include_red_threads=req.include_red_threads,
            include_glowing_butterflies=req.include_glowing_butterflies,
            butterfly_count=req.butterfly_count,
            clearance_offset=req.clearance_offset,
            save_after=req.save_after,
            save_path=req.save_path,
        )

        await _safe_ctx_progress(ctx, 100, 100)
        await _safe_ctx_info(ctx, f"Wardrobe generated successfully: {res.get('outfit_preset')}")

        return res
    except MorphoMeshException as e:
        raise ToolError(f"MorphoMesh Tool Error: [{e.code}] {e.message}")
    except Exception as e:
        raise ToolError(f"Unexpected Tool Failure in morphomesh_dress_human: {str(e)}")


# ==============================================================================
# TOOL 13: morphomesh_assemble_master_character
# ==============================================================================

async def morphomesh_assemble_master_character(
    character_name: str = "Yu_Nian_An",
    height: float = 1.65,
    head_ratio: float = 7.41,
    include_hair: bool = True,
    include_wardrobe: bool = True,
    include_props: bool = True,
    include_armature: bool = True,
    include_lighting: bool = True,
    render_engine: str = "CYCLES",
    samples: int = 128,
    save_blend: bool = True,
    output_path: Optional[str] = None,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Stage 6 Master Assembly: Orchestrate complete digital human scene in Blender 4.5+ LTS.

    Constructs 7-tier collection hierarchy (Yu_Nian_An_Master, 01_Body, 02_Hair, 03_Wardrobe,
    04_Props, 05_Armature, 06_Lights_Camera), integrates 100% pure quad body mesh with 29 vertex
    groups and 34 landmarks, builds Rigify 163 DEF bones armature with anti-pinch weights,
    parents 6 strata hair curves with Melanin shader, fits white slip dress and sandals with
    Solidify 0.002m and armature binding, tethers 10 crimson marionette strings to fingers and
    10 luminous white butterflies, configures 3-point studio lighting and 85mm portrait camera,
    applies Cycles Random Walk SSS and AgX color management, and saves output master .blend.
    """
    await _safe_ctx_info(ctx, f"Assembling master digital human scene for {character_name}...")
    await _safe_ctx_progress(ctx, 30, 100)

    try:
        res = blender_bridge.assemble_master_character(
            character_name=character_name,
            height=height,
            head_ratio=head_ratio,
            include_hair=include_hair,
            include_wardrobe=include_wardrobe,
            include_props=include_props,
            include_armature=include_armature,
            include_lighting=include_lighting,
            render_engine=render_engine,
            samples=samples,
            save_blend=save_blend,
            output_path=output_path,
        )

        await _safe_ctx_progress(ctx, 100, 100)
        await _safe_ctx_info(ctx, f"Master character scene assembled: {res.get('blend_file_path')}")
        return res
    except MorphoMeshException as e:
        raise ToolError(f"MorphoMesh Tool Error: [{e.code}] {e.message}")
    except Exception as e:
        raise ToolError(f"Unexpected Tool Failure in morphomesh_assemble_master_character: {str(e)}")


# ==============================================================================
# TOOL 14: morphomesh_export_production_character
# ==============================================================================

async def morphomesh_export_production_character(
    character_name: str = "Yu_Nian_An",
    blend_path: Optional[str] = None,
    output_dir: Optional[str] = None,
    export_fbx: bool = True,
    export_glb: bool = True,
    generate_textures: bool = True,
    generate_docs: bool = True,
    texture_resolution: int = 4096,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Stage 7 Production Export: Multi-format packaging and 4K PBR texture generation.

    Exports rigged production FBX (with 163 DEF bones, vertex groups, 52 ARKit FACS
    shape keys, and deformers), glTF 2.0 GLB (with PBR Principled BSDF materials,
    skinning, and 52 morph targets), synthesizes complete 4K PBR texture suite
    (BaseColor, Normal, Roughness, Metallic, SSS, Alpha, Height), and produces engine
    import documentation for Unreal Engine 5.4+, Unity 6, and Three.js.
    """
    await _safe_ctx_info(ctx, f"Initializing production multi-format exports for {character_name}...")
    await _safe_ctx_progress(ctx, 25, 100)

    try:
        from morphomesh.character_assembler import export_production_assets
        target_blend = blend_path or f"output/{character_name.lower()}/{character_name}_Master.blend"
        target_dir = output_dir or os.path.dirname(target_blend) or f"output/{character_name.lower()}"

        res = export_production_assets(
            blend_path=target_blend,
            output_dir=target_dir,
            character_name=character_name,
            export_fbx=export_fbx,
            export_glb=export_glb,
            generate_textures=generate_textures,
            generate_docs=generate_docs,
            texture_resolution=texture_resolution,
        )

        await _safe_ctx_progress(ctx, 100, 100)
        await _safe_ctx_info(ctx, f"Production export packages created in {target_dir}")
        return res
    except MorphoMeshException as e:
        raise ToolError(f"MorphoMesh Tool Error: [{e.code}] {e.message}")
    except Exception as e:
        raise ToolError(f"Unexpected Tool Failure in morphomesh_export_production_character: {str(e)}")


__all__ = [
    "morphomesh_create_human_asset",
    "morphomesh_auto_rig_human",
    "morphomesh_setup_human_materials",
    "morphomesh_groom_human",
    "morphomesh_dress_human",
    "morphomesh_assemble_master_character",
    "morphomesh_export_production_character",
]
