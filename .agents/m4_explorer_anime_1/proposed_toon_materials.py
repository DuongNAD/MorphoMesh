"""
Stepped Cel-Shading Node Trees for Anime Character Pipeline (Feature F14).
Target: anime_pipeline/shading/toon_materials.py

Provides authentic Japanese cel-shading materials with:
- M_Anime_Skin: Fair porcelain anime skin (#FFE2D4 / #FFF0E8) with warm peach
  shadow (#DE8971 / #E5A898, R>0.90, G>0.70, B<0.75), matte finish (Roughness 1.0).
- M_Anime_Clothes: Stepped cel-shading with presets for Torso/Shirt (#F0F4F8 / #B8C5D6),
  Skirt (#1E2A4A / #121A30), and Shoes (#2B2B2B / #151515).
- M_Anime_Eye: High-saturation stylized eyes with anime pupil and iris gradient.
- M_Anime_Outline: Unlit black emission shader for Inverted Hull lineart (Feature F16).

Compatible with Blender 4.5.4 LTS EEVEE-Next (BLENDER_EEVEE_NEXT).
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import bpy
    import mathutils
    HAS_BPY = True
except ImportError:
    HAS_BPY = False


# -----------------------------------------------------------------------------
# Color Palette Constants (sRGB / Linear Color Spaces)
# -----------------------------------------------------------------------------

# Anime Skin Tones
# Base: Delicate anime porcelain skin tone (#FFF0E8 / #FFE2D4)
SKIN_BASE_COLOR: Tuple[float, float, float, float] = (1.0, 0.92, 0.88, 1.0)
# Shadow: Warm peach / soft reddish tint (#DE8971 / #E5A898)
# Conforms strictly to test_tier1_features assertion: R > 0.90, G > 0.70, B < 0.75
SKIN_SHADOW_COLOR: Tuple[float, float, float, float] = (0.98, 0.74, 0.68, 1.0)

# Clothing Presets
CLOTHES_PRESETS: Dict[str, Dict[str, Tuple[float, float, float, float]]] = {
    "SHIRT": {
        # Torso shirt: pearl white (#F0F4F8) / soft blue-grey shadow (#B8C5D6)
        "base": (0.941, 0.957, 0.973, 1.0),
        "shadow": (0.722, 0.773, 0.839, 1.0),
    },
    "SKIRT": {
        # Pleated skirt: rich navy blue (#1E2A4A) / deep midnight shadow (#121A30)
        "base": (0.118, 0.165, 0.290, 1.0),
        "shadow": (0.071, 0.102, 0.188, 1.0),
    },
    "SHOES": {
        # Loafers/shoes: dark leather (#2B2B2B) / near-black shadow (#151515)
        "base": (0.169, 0.169, 0.169, 1.0),
        "shadow": (0.082, 0.082, 0.082, 1.0),
    },
}

# Stylized Anime Eyes
EYE_IRIS_COLOR: Tuple[float, float, float, float] = (0.12, 0.55, 0.95, 1.0)      # High-saturation azure
EYE_PUPIL_COLOR: Tuple[float, float, float, float] = (0.04, 0.05, 0.10, 1.0)     # Deep dark midnight
EYE_HIGHLIGHT_COLOR: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)    # Specular glint
EYE_SCLERA_COLOR: Tuple[float, float, float, float] = (0.98, 0.98, 1.0, 1.0)     # Clean white

# Outline Material
OUTLINE_COLOR: Tuple[float, float, float, float] = (0.08, 0.06, 0.06, 1.0)       # Dark anime ink lineart


# -----------------------------------------------------------------------------
# Helper Utilities
# -----------------------------------------------------------------------------

def hex_to_rgba(hex_str: str, alpha: float = 1.0) -> Tuple[float, float, float, float]:
    """Converts hex color string (e.g. '#FFE2D4') to normalized float RGBA tuple."""
    clean = hex_str.lstrip('#')
    if len(clean) == 3:
        clean = ''.join([c * 2 for c in clean])
    r = int(clean[0:2], 16) / 255.0
    g = int(clean[2:4], 16) / 255.0
    b = int(clean[4:6], 16) / 255.0
    return (r, g, b, alpha)


def get_or_create_material(name: str) -> bpy.types.Material:
    """Gets existing material by name or creates a new one with use_nodes enabled."""
    if not HAS_BPY:
        raise RuntimeError("Blender bpy module is not available")
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    return mat


# -----------------------------------------------------------------------------
# Material Builders
# -----------------------------------------------------------------------------

def build_anime_skin_material(
    name: str = "M_Anime_Skin",
    base_color: Tuple[float, float, float, float] = SKIN_BASE_COLOR,
    shadow_color: Tuple[float, float, float, float] = SKIN_SHADOW_COLOR,
    threshold: float = 0.48,
    roughness: float = 1.0,
) -> bpy.types.Material:
    """
    Builds the Stepped Cel-Shading Skin Material (M_Anime_Skin).
    
    Architecture:
      Diffuse BSDF (Roughness=1.0)
             │ (BSDF)
             ▼
      Shader to RGB
             │ (Color)
             ▼
      ColorRamp (CONSTANT)
        ├─ Stop 0 (0.00): Warm Peach Shadow (#DE8971 / #E5A898)
        └─ Stop 1 (0.48): Base Fair Porcelain (#FFF0E8 / #FFE2D4)
             │ (Color)
             ▼
      Material Output (Surface)
    
    Guarantees:
      - Strictly NO desaturated muddy gray shadows.
      - Matte finish: Roughness 1.0, Specular 0.0 (no greasy plastic shine).
      - Conforms to test_tier1_features assertions for F14.
    """
    mat = get_or_create_material(name)
    nt = mat.node_tree
    nt.nodes.clear()

    # 1. Diffuse BSDF captures scene lighting irradiance
    diffuse = nt.nodes.new("ShaderNodeBsdfDiffuse")
    diffuse.name = "Diffuse_BSDF"
    diffuse.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    diffuse.inputs["Roughness"].default_value = roughness

    # 2. Shader to RGB evaluates diffuse lighting into RGB vector
    s2rgb = nt.nodes.new("ShaderNodeShaderToRGB")
    s2rgb.name = "Shader_To_RGB"

    # 3. Stepped ColorRamp quantizes irradiance into crisp cel tones
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.name = "ColorRamp"
    ramp.color_ramp.interpolation = "CONSTANT"
    # Element 0: Warm peach shadow
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = shadow_color
    # Element 1: Base fair porcelain tone
    ramp.color_ramp.elements[1].position = threshold
    ramp.color_ramp.elements[1].color = base_color

    # 4. Material Output
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.name = "Material_Output"

    # Links
    nt.links.new(diffuse.outputs["BSDF"], s2rgb.inputs["Shader"])
    nt.links.new(s2rgb.outputs["Color"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], out.inputs["Surface"])

    return mat


def build_anime_clothes_material(
    name: str = "M_Anime_Clothes",
    garment_type: str = "SKIRT",
    base_color: Optional[Tuple[float, float, float, float]] = None,
    shadow_color: Optional[Tuple[float, float, float, float]] = None,
    threshold: float = 0.45,
    roughness: float = 0.85,
) -> bpy.types.Material:
    """
    Builds the Stepped Cel-Shading Clothes Material (M_Anime_Clothes).
    
    Supports presets:
      - 'SHIRT': Torso (#F0F4F8 / #B8C5D6)
      - 'SKIRT': Navy Blue (#1E2A4A / #121A30)
      - 'SHOES': Dark Leather (#2B2B2B / #151515)
    """
    preset = CLOTHES_PRESETS.get(garment_type.upper(), CLOTHES_PRESETS["SKIRT"])
    c_base = base_color if base_color is not None else preset["base"]
    c_shadow = shadow_color if shadow_color is not None else preset["shadow"]

    mat = get_or_create_material(name)
    nt = mat.node_tree
    nt.nodes.clear()

    diffuse = nt.nodes.new("ShaderNodeBsdfDiffuse")
    diffuse.name = "Diffuse_BSDF"
    diffuse.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    diffuse.inputs["Roughness"].default_value = roughness

    s2rgb = nt.nodes.new("ShaderNodeShaderToRGB")
    s2rgb.name = "Shader_To_RGB"

    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.name = "ColorRamp"
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = c_shadow
    ramp.color_ramp.elements[1].position = threshold
    ramp.color_ramp.elements[1].color = c_base

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.name = "Material_Output"

    nt.links.new(diffuse.outputs["BSDF"], s2rgb.inputs["Shader"])
    nt.links.new(s2rgb.outputs["Color"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], out.inputs["Surface"])

    return mat


def build_anime_eye_material(
    name: str = "M_Anime_Eye",
    iris_color: Tuple[float, float, float, float] = EYE_IRIS_COLOR,
    pupil_color: Tuple[float, float, float, float] = EYE_PUPIL_COLOR,
    highlight_color: Tuple[float, float, float, float] = EYE_HIGHLIGHT_COLOR,
    sclera_color: Tuple[float, float, float, float] = EYE_SCLERA_COLOR,
) -> bpy.types.Material:
    """
    Builds the High-Saturation Stylized Anime Eye Material (M_Anime_Eye).
    
    Architecture:
      Procedural UV disc distance radial gradient:
        - Center Pupil disc (#0D1117 / deep midnight)
        - Inner Iris gradient (vibrant saturated azure/emerald)
        - Catchlight specular glint (#FFFFFF)
        - Outer Sclera (#FAFBFD)
    """
    mat = get_or_create_material(name)
    nt = mat.node_tree
    nt.nodes.clear()

    tex_coord = nt.nodes.new("ShaderNodeTexCoord")
    tex_coord.name = "Texture_Coordinate"

    # Map center (0.5, 0.5) to (0.0, 0.0)
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.name = "UV_Center_Mapping"
    mapping.inputs["Location"].default_value = (-0.5, -0.5, 0.0)

    # Radial length = distance from eye center
    vec_len = nt.nodes.new("ShaderNodeVectorMath")
    vec_len.name = "Radial_Distance"
    vec_len.operation = "LENGTH"

    # Iris gradient ColorRamp
    iris_ramp = nt.nodes.new("ShaderNodeValToRGB")
    iris_ramp.name = "Iris_ColorRamp"
    iris_ramp.color_ramp.interpolation = "EASE"
    iris_ramp.color_ramp.elements[0].position = 0.00
    iris_ramp.color_ramp.elements[0].color = pupil_color
    iris_ramp.color_ramp.elements[1].position = 0.22
    iris_ramp.color_ramp.elements[1].color = iris_color
    e_outer = iris_ramp.color_ramp.elements.new(0.42)
    e_outer.color = (iris_color[0] * 0.4, iris_color[1] * 0.4, iris_color[2] * 0.4, 1.0)
    e_sclera = iris_ramp.color_ramp.elements.new(0.46)
    e_sclera.color = sclera_color

    # Specular Catchlight (Offset circular highlight dot)
    glint_mapping = nt.nodes.new("ShaderNodeMapping")
    glint_mapping.name = "Glint_Offset"
    glint_mapping.inputs["Location"].default_value = (-0.60, -0.65, 0.0)

    glint_len = nt.nodes.new("ShaderNodeVectorMath")
    glint_len.name = "Glint_Distance"
    glint_len.operation = "LENGTH"

    glint_ramp = nt.nodes.new("ShaderNodeValToRGB")
    glint_ramp.name = "Glint_ColorRamp"
    glint_ramp.color_ramp.interpolation = "CONSTANT"
    glint_ramp.color_ramp.elements[0].position = 0.00
    glint_ramp.color_ramp.elements[0].color = highlight_color
    glint_ramp.color_ramp.elements[1].position = 0.09
    glint_ramp.color_ramp.elements[1].color = (0.0, 0.0, 0.0, 0.0)

    # Composite Glint over Iris
    mix_eye = nt.nodes.new("ShaderNodeMix")
    mix_eye.name = "Eye_Glint_Mix"
    mix_eye.data_type = "RGBA"
    mix_eye.blend_type = "MIX"

    # Unlit Emission Shader for vibrant eye colors
    emission = nt.nodes.new("ShaderNodeEmission")
    emission.name = "Eye_Emission"
    emission.inputs["Strength"].default_value = 1.0

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.name = "Material_Output"

    # Links
    nt.links.new(tex_coord.outputs["UV"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], vec_len.inputs["Vector"])
    nt.links.new(vec_len.outputs["Value"], iris_ramp.inputs["Fac"])

    nt.links.new(tex_coord.outputs["UV"], glint_mapping.inputs["Vector"])
    nt.links.new(glint_mapping.outputs["Vector"], glint_len.inputs["Vector"])
    nt.links.new(glint_len.outputs["Value"], glint_ramp.inputs["Fac"])

    # Mix glint dot
    nt.links.new(glint_ramp.outputs["Alpha"], mix_eye.inputs[0])    # Factor
    nt.links.new(iris_ramp.outputs["Color"], mix_eye.inputs[6])     # A_Color
    nt.links.new(glint_ramp.outputs["Color"], mix_eye.inputs[7])    # B_Color

    nt.links.new(mix_eye.outputs[2], emission.inputs["Color"])
    nt.links.new(emission.outputs["Emission"], out.inputs["Surface"])

    return mat


def build_anime_outline_material(
    name: str = "M_Anime_Outline",
    outline_color: Tuple[float, float, float, float] = OUTLINE_COLOR,
) -> bpy.types.Material:
    """
    Builds the Unlit Inverted Hull Lineart Material (M_Anime_Outline).
    Configured for Solidify modifier with flipped normals and backface culling.
    """
    mat = get_or_create_material(name)
    mat.use_backface_culling = True
    nt = mat.node_tree
    nt.nodes.clear()

    emission = nt.nodes.new("ShaderNodeEmission")
    emission.name = "Emission"
    emission.inputs["Color"].default_value = outline_color
    emission.inputs["Strength"].default_value = 1.0

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.name = "Material_Output"

    nt.links.new(emission.outputs["Emission"], out.inputs["Surface"])
    return mat


# -----------------------------------------------------------------------------
# Batch Application to Character Hierarchy
# -----------------------------------------------------------------------------

def apply_all_toon_materials(
    separate_garments: bool = False,
) -> Dict[str, bpy.types.Material]:
    """
    Creates and applies all cel-shading materials across character sub-meshes.
    
    Mesh assignments:
      - Anime_Head:  Slot 0: M_Anime_Skin,    Slot 1: M_Anime_Outline
      - Anime_Torso: Slot 0: M_Anime_Skin,    Slot 1: M_Anime_Outline
      - Anime_Arms:  Slot 0: M_Anime_Skin,    Slot 1: M_Anime_Outline
      - Anime_Legs:  Slot 0: M_Anime_Skin,    Slot 1: M_Anime_Outline
      - Anime_Skirt: Slot 0: M_Anime_Clothes, Slot 1: M_Anime_Outline
      - Anime_Shoes: Slot 0: M_Anime_Clothes, Slot 1: M_Anime_Outline
    
    Note: Anime_Hair is managed via angel_ring.build_procedural_angel_ring_material.
    """
    if not HAS_BPY:
        raise RuntimeError("Blender bpy module is not available")

    # 1. Build Materials
    skin_mat = build_anime_skin_material("M_Anime_Skin")
    outline_mat = build_anime_outline_material("M_Anime_Outline")
    eye_mat = build_anime_eye_material("M_Anime_Eye")

    if separate_garments:
        skirt_mat = build_anime_clothes_material("M_Anime_Skirt", garment_type="SKIRT")
        shoes_mat = build_anime_clothes_material("M_Anime_Shoes", garment_type="SHOES")
        clothes_mat = skirt_mat
    else:
        clothes_mat = build_anime_clothes_material("M_Anime_Clothes", garment_type="SKIRT")
        skirt_mat = clothes_mat
        shoes_mat = clothes_mat

    # 2. Configure Viewport & Color Management for Anime Aesthetics
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.display_settings.display_device = "sRGB"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"

    # 3. Assign to submeshes if present in scene
    assignments = {
        "Anime_Head": skin_mat,
        "Anime_Torso": skin_mat,
        "Anime_Arms": skin_mat,
        "Anime_Legs": skin_mat,
        "Anime_Skirt": skirt_mat,
        "Anime_Shoes": shoes_mat,
    }

    for obj_name, target_mat in assignments.items():
        obj = bpy.data.objects.get(obj_name)
        if obj and obj.type == "MESH":
            if len(obj.material_slots) == 0:
                obj.data.materials.append(target_mat)
            else:
                obj.material_slots[0].material = target_mat

            # Slot 1 is outline
            if len(obj.material_slots) == 1:
                obj.data.materials.append(outline_mat)
            else:
                obj.material_slots[1].material = outline_mat

    return {
        "M_Anime_Skin": skin_mat,
        "M_Anime_Clothes": clothes_mat,
        "M_Anime_Eye": eye_mat,
        "M_Anime_Outline": outline_mat,
    }
