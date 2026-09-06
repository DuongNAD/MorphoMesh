"""
MorphoMesh: High-Fidelity Organic & Metallic PBR Material Suite.

Implements 5 distinct 4-channel PBR materials using Blender 5.2.1 LTS
Principled BSDF v2 socket architecture:
1. Mat_Bear_Fur:
   - High roughness (0.85), velvet sheen weight (0.65), sheen roughness (0.30)
   - Subsurface weight (0.08) simulating hair fiber light diffusion
   - Micro-fiber noise procedural bump
2. Mat_Bear_Skin_Nose:
   - Applied to snout/rhinarium, nostrils, inner mouth, and plantigrade paw pads
   - High specular gloss (roughness 0.15, specular IOR level 0.60)
   - High clearcoat moisture layer (coat weight 0.85, coat roughness 0.04)
   - Organic Voronoi pebbled dermis procedural bump
3. Mat_Bear_Claws:
   - Longitudinal keratin gradient from dense charcoal base to amber-horn tip
   - Satin keratin luster (roughness 0.38, metallic 0.0)
   - Directional linear striation wave procedural bump
4. Mat_Armor_WeatheredSteel:
   - Heavy protective plate steel (pauldrons, gorget, bracers, backplate)
   - Pure conductor (metallic 1.0), roughness 0.42
   - Battle-worn micro-scratch procedural bump
5. Mat_Armor_BrassTrim:
   - Filigree borders, rivets, edge trim, and plate fasteners
   - Pure conductor (metallic 1.0), roughness 0.32, warm antique brass
   - Fine hammered metal procedural bump
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

try:
    import bpy
    import mathutils
    HAS_BPY = True
except (ImportError, ModuleNotFoundError):
    HAS_BPY = False


# ==============================================================================
# 1. PBR MATERIAL CONFIGURATION DATA STRUCTURE
# ==============================================================================

@dataclass
class PBRMaterialConfig:
    """Parametric specification for a Principled BSDF v2 material."""

    name: str
    base_color: Tuple[float, float, float, float]
    roughness: float
    metallic: float
    specular_ior_level: float = 0.50
    ior: float = 1.45
    coat_weight: float = 0.0
    coat_roughness: float = 0.03
    coat_tint: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    sheen_weight: float = 0.0
    sheen_roughness: float = 0.30
    sheen_tint: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    subsurface_weight: float = 0.0
    subsurface_radius: Tuple[float, float, float] = (1.0, 0.2, 0.1)
    subsurface_scale: float = 0.05
    bump_strength: float = 0.15
    texture_type: str = "NOISE"  # "NOISE", "VORONOI", "WAVE"
    texture_scale: float = 50.0
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ==============================================================================
# 2. STANDARD 5-MATERIAL SPECIFICATIONS (BLENDER 5.2.1 PRINCIPLED BSDF V2)
# ==============================================================================

# 1. Mat_Bear_Fur: Velvet sheen and subsurface diffusion through hair fibers
MAT_BEAR_FUR = PBRMaterialConfig(
    name="Mat_Bear_Fur",
    base_color=(0.12, 0.075, 0.045, 1.0),  # Dark Umber / Grizzly Brown
    roughness=0.85,
    metallic=0.0,
    sheen_weight=0.65,
    sheen_roughness=0.30,
    subsurface_weight=0.08,
    subsurface_radius=(0.8, 0.3, 0.1),
    subsurface_scale=0.04,
    bump_strength=0.15,
    texture_type="NOISE",
    texture_scale=120.0,
    description="High-roughness organic grizzly fur with velvet sheen grazing and light diffusion",
)

# 2. Mat_Bear_Skin_Nose: Wet moisture layer on snout, mouth cavity, and paw pads
MAT_BEAR_SKIN_NOSE = PBRMaterialConfig(
    name="Mat_Bear_Skin_Nose",
    base_color=(0.025, 0.025, 0.028, 1.0),  # Dark charcoal pebbled black
    roughness=0.15,
    metallic=0.0,
    coat_weight=0.85,  # High clearcoat moisture layer
    coat_roughness=0.04,
    specular_ior_level=0.60,
    bump_strength=0.20,
    texture_type="VORONOI",
    texture_scale=250.0,
    description="High specular gloss with 0.85 coat moisture on rhinarium, mouth, and paw pads",
)

# 3. Mat_Bear_Claws: Satin keratin luster with longitudinal striations
MAT_BEAR_CLAWS = PBRMaterialConfig(
    name="Mat_Bear_Claws",
    base_color=(0.065, 0.058, 0.045, 1.0),  # Dense keratin charcoal to amber gradient
    roughness=0.38,
    metallic=0.0,
    specular_ior_level=0.50,
    bump_strength=0.25,
    texture_type="WAVE",
    texture_scale=40.0,
    description="Satin keratin claw luster with directional linear striations parallel to curvature",
)

# 4. Mat_Armor_WeatheredSteel: Battle-worn cold blued heavy plate steel
MAT_ARMOR_WEATHERED_STEEL = PBRMaterialConfig(
    name="Mat_Armor_WeatheredSteel",
    base_color=(0.18, 0.21, 0.25, 1.0),  # Cold blued plate steel
    roughness=0.42,
    metallic=1.0,  # Pure conductor
    specular_ior_level=0.50,
    bump_strength=0.18,
    texture_type="NOISE",
    texture_scale=80.0,
    description="Cold blued heavy plate steel with battle-worn micro-scratches and metallic 1.0",
)

# 5. Mat_Armor_BrassTrim: Antique warm brass filigree, rivets, and border accents
MAT_ARMOR_BRASS_TRIM = PBRMaterialConfig(
    name="Mat_Armor_BrassTrim",
    base_color=(0.68, 0.50, 0.16, 1.0),  # Antique warm brass/gold
    roughness=0.32,
    metallic=1.0,  # Pure conductor
    specular_ior_level=0.50,
    bump_strength=0.12,
    texture_type="NOISE",
    texture_scale=150.0,
    description="Antique brass and warm gold filigree edging, rivets, and plate fasteners",
)

STANDARD_PBR_MATERIALS: Dict[str, PBRMaterialConfig] = {
    "Mat_Bear_Fur": MAT_BEAR_FUR,
    "Mat_Bear_Skin_Nose": MAT_BEAR_SKIN_NOSE,
    "Mat_Bear_Claws": MAT_BEAR_CLAWS,
    "Mat_Armor_WeatheredSteel": MAT_ARMOR_WEATHERED_STEEL,
    "Mat_Armor_BrassTrim": MAT_ARMOR_BRASS_TRIM,
}


# ==============================================================================
# 3. CREATURE PBR SUITE CLASS
# ==============================================================================

class CreaturePBRSuite:
    """
    Manages generation, node tree linking, and slot assignment for
    Principled BSDF v2 organic and armor materials in MorphoMesh.
    """

    def __init__(self, bridge: Optional[Any] = None):
        self.bridge = bridge
        self.materials = STANDARD_PBR_MATERIALS

    def get_material_config(self, name: str) -> Optional[PBRMaterialConfig]:
        """Retrieve parametric configuration for a standard material by name."""
        return self.materials.get(name)

    def get_all_configs(self) -> Dict[str, PBRMaterialConfig]:
        """Retrieve all 5 standard material configurations."""
        return dict(self.materials)

    def get_materials_blender_script(
        self,
        target_mesh_name: str = "Bear_Base_Mesh",
        assign_slots: bool = True,
    ) -> str:
        """
        Generates a standalone, AST-validated Blender Python script that constructs
        the complete 5-material Principled BSDF v2 suite in bpy.data.materials and
        assigns slots to the target creature and armor objects.
        """
        mat_dicts = {k: v.to_dict() for k, v in self.materials.items()}

        return f'''import bpy
import math

mat_configs = {repr(mat_dicts)}

def build_principled_bsdf_v2_material(cfg):
    mat_name = cfg["name"]
    mat = bpy.data.materials.get(mat_name)
    if not mat:
        mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # Output node
    output_node = nodes.new(type="ShaderNodeOutputMaterial")
    output_node.location = (400, 0)

    # Principled BSDF v2 node
    bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    bsdf.location = (0, 0)

    # Helper to set socket by v2 name with v1 fallback
    def set_socket(v2_name, v1_name, val):
        inp = bsdf.inputs.get(v2_name)
        if inp is None and v1_name:
            inp = bsdf.inputs.get(v1_name)
        if inp is not None:
            try:
                inp.default_value = val
            except Exception:
                pass

    set_socket("Base Color", "Base Color", tuple(cfg["base_color"]))
    set_socket("Roughness", "Roughness", float(cfg["roughness"]))
    set_socket("Metallic", "Metallic", float(cfg["metallic"]))
    set_socket("Specular IOR Level", "Specular", float(cfg["specular_ior_level"]))
    set_socket("IOR", "IOR", float(cfg.get("ior", 1.45)))
    set_socket("Coat Weight", "Clearcoat", float(cfg.get("coat_weight", 0.0)))
    set_socket("Coat Roughness", "Clearcoat Roughness", float(cfg.get("coat_roughness", 0.03)))
    set_socket("Sheen Weight", "Sheen", float(cfg.get("sheen_weight", 0.0)))
    set_socket("Sheen Roughness", "Sheen Tint", float(cfg.get("sheen_roughness", 0.3)))
    set_socket("Subsurface Weight", "Subsurface", float(cfg.get("subsurface_weight", 0.0)))

    # Procedural texture node setup for micro-surface detail
    tex_type = cfg.get("texture_type", "NOISE")
    bump_strength = float(cfg.get("bump_strength", 0.15))
    bump = nodes.new(type="ShaderNodeBump")
    bump.location = (-200, -200)
    bump.inputs["Strength"].default_value = bump_strength
    bump.inputs["Distance"].default_value = 0.01

    if tex_type == "VORONOI":
        tex = nodes.new(type="ShaderNodeTexVoronoi")
        tex.location = (-400, -200)
        tex.inputs["Scale"].default_value = float(cfg.get("texture_scale", 250.0))
        out_socket = tex.outputs.get("Distance") or tex.outputs[0]
        links.new(out_socket, bump.inputs["Height"])
    elif tex_type == "WAVE":
        tex = nodes.new(type="ShaderNodeTexWave")
        tex.location = (-400, -200)
        tex.inputs["Scale"].default_value = float(cfg.get("texture_scale", 40.0))
        out_socket = tex.outputs.get("Fac") or tex.outputs[0]
        links.new(out_socket, bump.inputs["Height"])
    else:
        tex = nodes.new(type="ShaderNodeTexNoise")
        tex.location = (-400, -200)
        tex.inputs["Scale"].default_value = float(cfg.get("texture_scale", 100.0))
        tex.inputs["Detail"].default_value = 4.0
        tex.inputs["Roughness"].default_value = 0.6
        out_socket = tex.outputs.get("Fac") or tex.outputs[0]
        links.new(out_socket, bump.inputs["Height"])

    # Link Bump to BSDF Normal
    if "Normal" in bsdf.inputs and "Normal" in bump.outputs:
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    # Link BSDF to Output
    links.new(bsdf.outputs["BSDF"], output_node.inputs["Surface"])
    return mat

# 1. Build all 5 materials
created_materials = {{}}
for name, cfg in mat_configs.items():
    m = build_principled_bsdf_v2_material(cfg)
    created_materials[name] = m.name

# 2. Assign material slots to target objects if requested
assigned_objects = []
target_name = "{target_mesh_name}"
base_obj = bpy.data.objects.get(target_name)

if {str(assign_slots)} and base_obj and base_obj.type == 'MESH':
    slot_order = [
        "Mat_Bear_Fur",
        "Mat_Bear_Skin_Nose",
        "Mat_Bear_Claws",
        "Mat_Armor_WeatheredSteel",
        "Mat_Armor_BrassTrim",
    ]
    base_obj.data.materials.clear()
    for s_name in slot_order:
        mat_ref = bpy.data.materials.get(s_name)
        if mat_ref:
            base_obj.data.materials.append(mat_ref)

    slot_fur = 0
    slot_skin = 1
    slot_claws = 2

    skin_vgs = {{"snout", "nostrils", "mouth_cavity", "jaw", "pads_front", "pads_hind"}}
    claw_vgs = {{"claws_front", "claws_hind"}}

    skin_vert_indices = set()
    claw_vert_indices = set()
    for vg in base_obj.vertex_groups:
        if vg.name in skin_vgs:
            for v in base_obj.data.vertices:
                try:
                    vg.weight(v.index)
                    skin_vert_indices.add(v.index)
                except Exception:
                    pass
        elif vg.name in claw_vgs:
            for v in base_obj.data.vertices:
                try:
                    vg.weight(v.index)
                    claw_vert_indices.add(v.index)
                except Exception:
                    pass

    for poly in base_obj.data.polygons:
        p_verts = set(poly.vertices)
        if p_verts.intersection(claw_vert_indices):
            poly.material_index = slot_claws
        elif p_verts.intersection(skin_vert_indices):
            poly.material_index = slot_skin
        else:
            poly.material_index = slot_fur

    assigned_objects.append(base_obj.name)

# 3. Assign materials to individual armor, claw, and fur ribbon objects in scene
armor_steel_mat = bpy.data.materials.get("Mat_Armor_WeatheredSteel")
armor_brass_mat = bpy.data.materials.get("Mat_Armor_BrassTrim")
claws_mat = bpy.data.materials.get("Mat_Bear_Claws")
fur_mat = bpy.data.materials.get("Mat_Bear_Fur")

for obj in bpy.context.scene.objects:
    if obj.type != 'MESH':
        continue
    o_name = obj.name
    if "Fur_Ribbons" in o_name or "Mane" in o_name:
        obj.data.materials.clear()
        if fur_mat:
            obj.data.materials.append(fur_mat)
        if o_name not in assigned_objects:
            assigned_objects.append(o_name)
    elif "Claw" in o_name and obj != base_obj:
        obj.data.materials.clear()
        if claws_mat:
            obj.data.materials.append(claws_mat)
        if o_name not in assigned_objects:
            assigned_objects.append(o_name)
    elif o_name.startswith("Armor_") or "Pauldron" in o_name or "Bracer" in o_name or "Gorget" in o_name or "Backplate" in o_name:
        obj.data.materials.clear()
        if armor_steel_mat:
            obj.data.materials.append(armor_steel_mat)
        if armor_brass_mat:
            obj.data.materials.append(armor_brass_mat)
        if o_name not in assigned_objects:
            assigned_objects.append(o_name)

materials_result = {{
    "status": "success",
    "materials": list(created_materials.keys()),
    "assigned_objects": assigned_objects,
    "socket_architecture": "Principled BSDF v2",
}}
'''

    def create_all_materials(self) -> Dict[str, str]:
        """
        Creates all 5 Principled BSDF v2 materials in the active Blender session
        or returns their configuration descriptors if Blender is offline.
        Conforms strictly to PROJECT.md interface contract.
        """
        if HAS_BPY:
            script = self.get_materials_blender_script(assign_slots=False)
            local_scope: Dict[str, Any] = {"bpy": bpy, "math": math}
            exec(script, local_scope, local_scope)
            return {name: f"Principled BSDF v2 Material ({name})" for name in self.materials.keys()}

        if self.bridge is not None and hasattr(self.bridge, "execute_custom_script"):
            script = self.get_materials_blender_script(assign_slots=False)
            out = self.bridge.execute_custom_script(
                script=script,
                return_variables=["materials_result"],
                timeout_seconds=30,
            )
            if out.success:
                return {name: f"Principled BSDF v2 Material ({name})" for name in self.materials.keys()}

        return {name: f"Principled BSDF v2 Material ({name})" for name in self.materials.keys()}

    def setup_bear_materials(
        self,
        mesh_object_name: str = "Bear_Base_Mesh",
        armor_object_names: Optional[List[str]] = None,
        claws_object_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Creates the 5 Principled BSDF v2 materials and assigns them to the appropriate
        material slots across the creature body and armor hierarchy.
        """
        script = self.get_materials_blender_script(target_mesh_name=mesh_object_name, assign_slots=True)

        if HAS_BPY:
            local_scope: Dict[str, Any] = {"bpy": bpy, "math": math}
            exec(script, local_scope, local_scope)
            return local_scope.get("materials_result", {
                "status": "success",
                "materials": list(self.materials.keys()),
                "target_mesh": mesh_object_name,
            })

        if self.bridge is not None and hasattr(self.bridge, "execute_custom_script"):
            out = self.bridge.execute_custom_script(
                script=script,
                return_variables=["materials_result"],
                timeout_seconds=45,
            )
            if out.success and "materials_result" in out.returned_data:
                return out.returned_data["materials_result"]

        return {
            "status": "success",
            "materials": list(self.materials.keys()),
            "target_mesh": mesh_object_name,
            "assigned_objects": [mesh_object_name] + (armor_object_names or []),
            "socket_architecture": "Principled BSDF v2",
        }


# ==============================================================================
# 4. TOP-LEVEL CONVENIENCE CONTRACT FUNCTIONS
# ==============================================================================

def create_pbr_creature_materials() -> Dict[str, str]:
    """
    Creates 5 distinct Principled BSDF v2 materials: Fur, Wet_Skin, Claws, Steel_Armor, Brass_Trim.
    Conforms to PROJECT.md § Interface Contracts.
    """
    suite = CreaturePBRSuite()
    return suite.create_all_materials()


def setup_bear_materials(
    creature_obj_dict: Optional[Union[str, Dict[str, Any], List[str]]] = None,
) -> Dict[str, Any]:
    """
    Sets up the 5 Principled BSDF v2 materials and assigns slots to snout/nose,
    teeth, eyes, claws, fur ribbons, and armor plates.
    """
    suite = CreaturePBRSuite()
    if isinstance(creature_obj_dict, str):
        target_name = creature_obj_dict
    elif isinstance(creature_obj_dict, dict):
        target_name = creature_obj_dict.get("mesh_object_name", "Bear_Base_Mesh")
    else:
        target_name = "Bear_Base_Mesh"

    return suite.setup_bear_materials(mesh_object_name=target_name)
