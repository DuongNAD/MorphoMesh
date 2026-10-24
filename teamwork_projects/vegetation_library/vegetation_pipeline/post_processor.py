"""
MorphoMesh Vegetation Library - Asset Post-Processing, Normalization & Multi-Format Export.
Conforms to Milestone 3 (M3) Specification and M3 <-> M4 Interface Contract.

Key Capabilities:
1. Ground Pivot Snapping: Strict ground contact base alignment Z_min = 0.000m (or glTF Y_min = 0.000m).
2. Base Contact Centroid Centering: Centroid of vertices in bottom 5% height slice centered at (0, 0).
3. Metric Scale Normalization: Uniform botanical scale matching catalog.py height_m and canopy_spread_m.
4. Production GLB Export: glTF 2.0 binary container with embedded 4-channel PBR textures, doubleSided foliage, N_bones = 0.
5. Companion Wavefront OBJ & MTL Export: Standard 1-indexed OBJ + MTL with portable relative textures/ paths.
6. Categorized Packaging: output/<short_category>/<species_id>/ hierarchy with asset_manifest.json.
"""
from __future__ import annotations

from datetime import datetime, timezone
import io
import json
import logging
import math
from pathlib import Path
import struct
import subprocess
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import numpy as np
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field

from morphomesh.geometry.mesh import MeshGeometry
from vegetation_pipeline.catalog import PlantSpecies, get_species
from vegetation_pipeline.generator import RawAsset, unpack_glb_header_and_json

logger = logging.getLogger("vegetation_pipeline.post_processor")


# ==============================================================================
# DATA MODELS
# ==============================================================================

class AssetDimensions(BaseModel):
    """Normalized physical dimensions and bounding box in metric units."""
    model_config = ConfigDict(extra="ignore")

    height_m: float = Field(..., gt=0.0, description="Measured mature height in meters (Z-axis)")
    canopy_spread_m: float = Field(..., gt=0.0, description="Crown or foliage spread diameter (max(width, depth))")
    canopy_width_m: float = Field(default=0.0, description="X-axis bounding extent in meters")
    canopy_depth_m: float = Field(default=0.0, description="Y-axis bounding extent in meters")
    bounding_box_min: List[float] = Field(..., description="[x_min, y_min, z_min] bounding box minimum")
    bounding_box_max: List[float] = Field(..., description="[x_max, y_max, z_max] bounding box maximum")

    # Compatibility aliases
    width_m: Optional[float] = Field(default=None, description="Alias for canopy_width_m")
    depth_m: Optional[float] = Field(default=None, description="Alias for canopy_depth_m")
    target_height_m: Optional[float] = Field(default=None, description="Catalog reference height target")
    target_canopy_spread_m: Optional[float] = Field(default=None, description="Catalog reference canopy spread target")
    bbox_min: Optional[List[float]] = Field(default=None, description="Alias for bounding_box_min")
    bbox_max: Optional[List[float]] = Field(default=None, description="Alias for bounding_box_max")

    def __getitem__(self, item: str) -> Any:
        """Allow dict-style key access for backward compatibility."""
        return getattr(self, item)


class PostProcessorConfig(BaseModel):
    """Configuration options for AssetPostProcessor normalization and export."""
    model_config = ConfigDict(extra="ignore")

    target_height_tolerance: float = Field(default=0.05, description="Allowed height tolerance ratio")
    center_contact_base: bool = Field(default=True, description="Enable horizontal base contact centroid centering")
    snap_ground_pivot: bool = Field(default=True, description="Enable ground pivot snapping to Z_min = 0.0")
    export_glb: bool = Field(default=True, description="Export production GLB file")
    export_obj: bool = Field(default=True, description="Export companion Wavefront OBJ file")
    embed_textures_in_glb: bool = Field(default=True, description="Embed all 4 PBR textures into binary GLB")
    double_sided_foliage: bool = Field(default=True, description="Enable two-sided leaf rendering in glTF")
    texture_format: Literal["PNG", "JPEG", "png", "jpeg"] = Field(default="PNG", description="Texture format on disk")

    # Additional options
    ground_tolerance_m: float = Field(default=0.005, description="Max deviation from Z_min = 0.0")
    base_slice_ratio: float = Field(default=0.05, description="Bottom height fraction for contact slice (5%)")
    base_centroid_ratio: float = Field(default=0.05, description="Alias for base_slice_ratio")
    centering_tolerance_m: float = Field(default=0.05, description="Max allowed base centering offset")
    scaling_strategy: Literal["uniform_height", "aspect_constrained", "exact_bounds", "none", "height_proportional"] = Field(
        default="uniform_height", description="Metric scaling strategy"
    )
    aspect_constraint_clamp: float = Field(default=0.15, description="Allowed deviation ratio for aspect constrained scaling")
    export_texture_files: bool = Field(default=True, description="Export discrete texture files to textures/")
    export_manifest: bool = Field(default=True, description="Generate asset_manifest.json")
    enable_double_sided: Optional[bool] = Field(default=None, description="Alias for double_sided_foliage")
    export_obj_mtl: Optional[bool] = Field(default=None, description="Alias for export_obj")


# Alias for backward compatibility
NormalizationConfig = PostProcessorConfig


class ExportedAsset(BaseModel):
    """
    Normalized, production-ready botanical asset with multi-format deliverables.
    Conforms to M3 <-> M4 Interface Contract.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore")

    species_id: str = Field(..., description="Canonical species ID (e.g. 'veg_tree_oak_01')")
    glb_path: Path = Field(..., description="Path to production binary .glb asset")
    obj_path: Path = Field(..., description="Path to companion Wavefront .obj file")
    mtl_path: Path = Field(..., description="Path to companion Wavefront .mtl file")
    texture_paths: Dict[str, Path] = Field(
        ...,
        description="Map of channel names ('albedo', 'normal', 'roughness', 'metallic') to file paths"
    )
    manifest_path: Path = Field(..., description="Path to companion asset_manifest.json")
    dimensions: AssetDimensions = Field(..., description="Normalized metric dimensions and bounding box")
    vertex_count: int = Field(..., ge=0, description="Total normalized vertex count")
    face_count: int = Field(..., ge=0, description="Total normalized face count")
    source: Literal["meshy", "procedural", "cached"] = Field(..., description="Source generation engine")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata dictionary")
    category_id: Optional[str] = Field(default=None, description="Botanical category identifier")
    ground_pivot_z: float = Field(default=0.0, description="Lowest Z coordinate after grounding")
    base_centroid: Tuple[float, float] = Field(default=(0.0, 0.0), description="Base contact centroid (x, y)")

    @property
    def albedo_path(self) -> Optional[Path]:
        return self.texture_paths.get("albedo")

    @property
    def normal_path(self) -> Optional[Path]:
        return self.texture_paths.get("normal")

    @property
    def roughness_path(self) -> Optional[Path]:
        return self.texture_paths.get("roughness")

    @property
    def metallic_path(self) -> Optional[Path]:
        return self.texture_paths.get("metallic")

    @property
    def height_m(self) -> float:
        return self.dimensions.height_m

    @property
    def canopy_spread_m(self) -> float:
        return self.dimensions.canopy_spread_m

    def is_valid(self) -> bool:
        """Quick verification that all expected export files exist on disk."""
        return (
            self.glb_path.is_file()
            and self.obj_path.is_file()
            and self.mtl_path.is_file()
            and self.manifest_path.is_file()
            and all(p.is_file() for p in self.texture_paths.values())
        )


# ==============================================================================
# PURE-PYTHON GEOMETRY & UTILITY ALGORITHMS
# ==============================================================================

def pad_4(b: bytes) -> bytes:
    """Aligns byte buffer to a 4-byte boundary with null padding."""
    rem = len(b) % 4
    return b + (b"\x00" * ((4 - rem) % 4)) if rem != 0 else b


def compute_mesh_extents(mesh: MeshGeometry) -> Dict[str, float]:
    """Computes tight axis-aligned bounding box coordinates and extents."""
    if not mesh.vertices:
        return {
            "min_x": 0.0, "max_x": 0.0,
            "min_y": 0.0, "max_y": 0.0,
            "min_z": 0.0, "max_z": 0.0,
            "dx": 0.0, "dy": 0.0, "dz": 0.0,
            "spread": 0.0,
        }

    xs = [v[0] for v in mesh.vertices]
    ys = [v[1] for v in mesh.vertices]
    zs = [v[2] for v in mesh.vertices]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    min_z, max_z = min(zs), max(zs)

    dx = max_x - min_x
    dy = max_y - min_y
    dz = max_z - min_z
    spread = max(dx, dy)

    return {
        "min_x": min_x, "max_x": max_x,
        "min_y": min_y, "max_y": max_y,
        "min_z": min_z, "max_z": max_z,
        "dx": dx, "dy": dy, "dz": dz,
        "spread": spread,
    }


def load_mesh_from_glb(glb_path: Union[str, Path]) -> MeshGeometry:
    """Extracts vertex positions, normals, UVs, and faces from a binary GLB container."""
    gltf, bin_bytes = unpack_glb_header_and_json(glb_path)
    accessors = gltf.get("accessors", [])
    buffer_views = gltf.get("bufferViews", [])

    mesh = MeshGeometry()

    for m in gltf.get("meshes", []):
        for prim in m.get("primitives", []):
            attrs = prim.get("attributes", {})
            pos_idx = attrs.get("POSITION")
            norm_idx = attrs.get("NORMAL")
            uv_idx = attrs.get("TEXCOORD_0")
            idx_idx = prim.get("indices")

            if pos_idx is None or pos_idx >= len(accessors):
                continue

            pos_acc = accessors[pos_idx]
            pos_bv = buffer_views[pos_acc["bufferView"]]
            pos_offset = pos_bv.get("byteOffset", 0) + pos_acc.get("byteOffset", 0)
            count = pos_acc["count"]
            pos_floats = struct.unpack_from(f"<{count * 3}f", bin_bytes, pos_offset)
            positions = [(pos_floats[i * 3], pos_floats[i * 3 + 1], pos_floats[i * 3 + 2]) for i in range(count)]

            if norm_idx is not None and norm_idx < len(accessors):
                norm_acc = accessors[norm_idx]
                norm_bv = buffer_views[norm_acc["bufferView"]]
                norm_offset = norm_bv.get("byteOffset", 0) + norm_acc.get("byteOffset", 0)
                norm_floats = struct.unpack_from(f"<{count * 3}f", bin_bytes, norm_offset)
                normals = [(norm_floats[i * 3], norm_floats[i * 3 + 1], norm_floats[i * 3 + 2]) for i in range(count)]
            else:
                normals = [(0.0, 0.0, 1.0)] * count

            if uv_idx is not None and uv_idx < len(accessors):
                uv_acc = accessors[uv_idx]
                uv_bv = buffer_views[uv_acc["bufferView"]]
                uv_offset = uv_bv.get("byteOffset", 0) + uv_acc.get("byteOffset", 0)
                uv_floats = struct.unpack_from(f"<{count * 2}f", bin_bytes, uv_offset)
                uvs = [(uv_floats[i * 2], uv_floats[i * 2 + 1]) for i in range(count)]
            else:
                uvs = [(0.0, 0.0)] * count

            v_offset = len(mesh.vertices)
            for i in range(count):
                mesh.add_vertex(positions[i], normals[i], uvs[i])

            if idx_idx is not None and idx_idx < len(accessors):
                idx_acc = accessors[idx_idx]
                idx_bv = buffer_views[idx_acc["bufferView"]]
                idx_offset = idx_bv.get("byteOffset", 0) + idx_acc.get("byteOffset", 0)
                idx_count = idx_acc["count"]
                ctype = idx_acc.get("componentType", 5123)
                fmt = "H" if ctype == 5123 else "I"
                indices = struct.unpack_from(f"<{idx_count}{fmt}", bin_bytes, idx_offset)
                for i in range(0, idx_count - 2, 3):
                    mesh.add_triangle(indices[i] + v_offset, indices[i + 1] + v_offset, indices[i + 2] + v_offset)
            else:
                for i in range(0, count - 2, 3):
                    mesh.add_triangle(v_offset + i, v_offset + i + 1, v_offset + i + 2)

    return mesh


def extract_textures_from_glb(glb_path: Union[str, Path]) -> Dict[str, Image.Image]:
    """Extracts embedded images from a binary GLB container if available."""
    textures: Dict[str, Image.Image] = {}
    try:
        gltf, bin_bytes = unpack_glb_header_and_json(glb_path)
        buffer_views = gltf.get("bufferViews", [])
        images = gltf.get("images", [])
        loaded_imgs: Dict[int, Image.Image] = {}
        for idx, img_info in enumerate(images):
            bv_idx = img_info.get("bufferView")
            if bv_idx is not None and bv_idx < len(buffer_views):
                bv = buffer_views[bv_idx]
                b_off = bv.get("byteOffset", 0)
                b_len = bv.get("byteLength", 0)
                raw_bytes = bin_bytes[b_off : b_off + b_len]
                img = Image.open(io.BytesIO(raw_bytes))
                loaded_imgs[idx] = img
                name = str(img_info.get("name", "")).lower()
                if "albedo" in name or "base" in name:
                    textures["albedo"] = img
                elif "normal" in name:
                    textures["normal"] = img
                elif "rough" in name:
                    textures["roughness"] = img
                elif "metal" in name:
                    textures["metallic"] = img

        # Fallback to glTF material and texture bindings when image names are absent (e.g. Meshy AI models)
        materials = gltf.get("materials", [])
        gltf_textures = gltf.get("textures", [])
        if materials:
            mat = materials[0]
            pbr = mat.get("pbrMetallicRoughness", {})
            if "albedo" not in textures and "baseColorTexture" in pbr:
                t_idx = pbr["baseColorTexture"].get("index", 0)
                if t_idx < len(gltf_textures):
                    s_idx = gltf_textures[t_idx].get("source", 0)
                    if s_idx in loaded_imgs:
                        textures["albedo"] = loaded_imgs[s_idx]
            if "normal" not in textures and "normalTexture" in mat:
                t_idx = mat["normalTexture"].get("index", 0)
                if t_idx < len(gltf_textures):
                    s_idx = gltf_textures[t_idx].get("source", 0)
                    if s_idx in loaded_imgs:
                        textures["normal"] = loaded_imgs[s_idx]
            if "metallicRoughnessTexture" in pbr:
                t_idx = pbr["metallicRoughnessTexture"].get("index", 0)
                if t_idx < len(gltf_textures):
                    s_idx = gltf_textures[t_idx].get("source", 0)
                    if s_idx in loaded_imgs:
                        orm = loaded_imgs[s_idx]
                        if orm.mode != "RGB":
                            orm = orm.convert("RGB")
                        chans = orm.split()
                        if "roughness" not in textures and len(chans) >= 2:
                            textures["roughness"] = chans[1]
                        if "metallic" not in textures and len(chans) >= 3:
                            textures["metallic"] = chans[2]

        # Positional fallback if material mapping was absent
        if "albedo" not in textures and 0 in loaded_imgs:
            textures["albedo"] = loaded_imgs[0]
        if 1 in loaded_imgs:
            orm = loaded_imgs[1]
            if orm.mode != "RGB":
                orm = orm.convert("RGB")
            chans = orm.split()
            if "roughness" not in textures and len(chans) >= 2:
                textures["roughness"] = chans[1]
            if "metallic" not in textures and len(chans) >= 3:
                textures["metallic"] = chans[2]
        if "normal" not in textures and 2 in loaded_imgs:
            textures["normal"] = loaded_imgs[2]
    except Exception as e:
        logger.debug("GLB texture extraction skipped for %s: %s", glb_path, e)
    return textures


def snap_ground_pivot_and_center(
    mesh: MeshGeometry,
    base_slice_ratio: float = 0.05,
) -> Tuple[MeshGeometry, Tuple[float, float], float]:
    """
    1. Snaps lowest vertex to Z_min = 0.000m ground contact.
    2. Calculates horizontal centroid of bottom 5% height slice.
    3. Translates (X, Y) so base centroid is exactly at (0.000, 0.000).
    4. Guarantees Z_min == 0.000m within floating point precision.
    """
    if not mesh.vertices:
        return mesh, (0.0, 0.0), 0.0

    # Validate finite coordinates
    for i, v in enumerate(mesh.vertices):
        if not (math.isfinite(v[0]) and math.isfinite(v[1]) and math.isfinite(v[2])):
            raise ValueError(f"Mesh vertex {i} contains non-finite coordinates (NaN or Inf): {v}")

    # Check for degenerate zero-height mesh
    zs = [v[2] for v in mesh.vertices]
    h_init = max(zs) - min(zs)
    if h_init <= 1e-6:
        raise ValueError(f"Degenerate mesh with zero height: {h_init:.6f}m")

    # Step 1: Ground contact shift
    min_z = min(zs)
    mesh.vertices = [(v[0], v[1], v[2] - min_z) for v in mesh.vertices]

    # Step 2: Base slice centroid calculation
    current_h = max(v[2] for v in mesh.vertices)
    slice_h = max(1e-4, base_slice_ratio * current_h)
    base_verts = [v for v in mesh.vertices if v[2] <= slice_h]
    if not base_verts:
        base_verts = [v for v in mesh.vertices if v[2] <= min(v[2] for v in mesh.vertices) + 1e-4]

    cx = float(np.mean([v[0] for v in base_verts]))
    cy = float(np.mean([v[1] for v in base_verts]))

    # Step 3: Base centering translation
    mesh.vertices = [(v[0] - cx, v[1] - cy, v[2]) for v in mesh.vertices]

    # Step 4: Numerical precision clamp to guarantee Z_min = 0.000m
    final_min_z = min(v[2] for v in mesh.vertices)
    if abs(final_min_z) > 1e-7:
        mesh.vertices = [(v[0], v[1], v[2] - final_min_z) for v in mesh.vertices]

    return mesh, (cx, cy), float(min(v[2] for v in mesh.vertices))


def normalize_metric_scale(
    mesh: MeshGeometry,
    species: PlantSpecies,
    strategy: str = "uniform_height",
    aspect_clamp: float = 0.15,
) -> Tuple[MeshGeometry, float, float, float]:
    """
    Scales mesh geometry to match botanical dimensions from catalog.py.
    Default: Uniform height scaling (preserves botanical aspect ratio,
    trunk circularity, and unskewed normal vectors).
    """
    if not mesh.vertices:
        return mesh, 0.0, 0.0, 1.0

    ext = compute_mesh_extents(mesh)
    curr_h = ext["dz"]
    if curr_h <= 1e-6:
        raise ValueError(f"Degenerate mesh with zero height: {curr_h:.6f}m")

    target_h = species.dimensions.height_m
    target_spread = species.dimensions.canopy_spread_m

    scale_z = target_h / curr_h

    if strategy in ("uniform_height", "height_proportional"):
        scale_x = scale_y = scale_z
    elif strategy == "aspect_constrained":
        curr_spread = max(1e-5, ext["spread"])
        raw_spread_scale = target_spread / curr_spread
        ratio = raw_spread_scale / scale_z
        clamped_ratio = float(np.clip(ratio, 1.0 - aspect_clamp, 1.0 + aspect_clamp))
        scale_x = scale_y = scale_z * clamped_ratio
    elif strategy == "exact_bounds":
        dx = max(1e-5, ext["dx"])
        dy = max(1e-5, ext["dy"])
        scale_x = target_spread / dx
        scale_y = target_spread / dy
    elif strategy == "none":
        scale_x = scale_y = scale_z = 1.0
    else:
        scale_x = scale_y = scale_z

    # Apply scaling transformation
    mesh.vertices = [(v[0] * scale_x, v[1] * scale_y, v[2] * scale_z) for v in mesh.vertices]

    # Re-snap to Z_min = 0.000m
    z_min_final = min(v[2] for v in mesh.vertices)
    if abs(z_min_final) > 1e-7:
        mesh.vertices = [(v[0], v[1], v[2] - z_min_final) for v in mesh.vertices]

    # Re-normalize normal vectors
    new_normals = []
    anisotropic = abs(scale_x - scale_z) > 1e-4 or abs(scale_y - scale_z) > 1e-4
    for n in mesh.normals:
        if anisotropic:
            tx = n[0] / scale_x
            ty = n[1] / scale_y
            tz = n[2] / scale_z
        else:
            tx, ty, tz = n[0], n[1], n[2]
        norm_len = math.sqrt(tx * tx + ty * ty + tz * tz)
        if norm_len > 1e-6:
            new_normals.append((tx / norm_len, ty / norm_len, tz / norm_len))
        else:
            new_normals.append((0.0, 0.0, 1.0))
    mesh.normals = new_normals

    new_ext = compute_mesh_extents(mesh)
    return mesh, new_ext["dz"], new_ext["spread"], scale_z


def clean_mesh_geometry(mesh: MeshGeometry) -> MeshGeometry:
    """
    Removes duplicate vertex indices within triangles, degenerate zero-area faces (area <= 1e-8),
    and purges unreferenced vertices, re-indexing faces cleanly.
    """
    if not mesh.faces or not mesh.vertices:
        return mesh

    pos = np.array(mesh.vertices, dtype=np.float32)
    valid_faces = []
    referenced = set()

    for f in mesh.faces:
        if len(f) != 3:
            continue
        i0, i1, i2 = int(f[0]), int(f[1]), int(f[2])
        if i0 == i1 or i1 == i2 or i2 == i0:
            continue
        v0, v1, v2 = pos[i0], pos[i1], pos[i2]
        cross = np.cross(v1 - v0, v2 - v0)
        area = 0.5 * float(np.linalg.norm(cross))
        if area > 1e-8:
            valid_faces.append((i0, i1, i2))
            referenced.add(i0)
            referenced.add(i1)
            referenced.add(i2)

    if len(valid_faces) == len(mesh.faces) and len(referenced) == len(mesh.vertices):
        return mesh

    sorted_ref = sorted(referenced)
    old_to_new = {old_i: new_i for new_i, old_i in enumerate(sorted_ref)}
    mesh.vertices = [mesh.vertices[i] for i in sorted_ref]
    mesh.normals = [mesh.normals[i] if i < len(mesh.normals) else (0.0, 0.0, 1.0) for i in sorted_ref]
    mesh.uvs = [mesh.uvs[i] if i < len(mesh.uvs) else (0.0, 0.0) for i in sorted_ref]
    mesh.faces = [(old_to_new[f[0]], old_to_new[f[1]], old_to_new[f[2]]) for f in valid_faces]
    return mesh


def decimate_glb_with_blender(
    glb_path: Union[str, Path],
    target_vertices: int = 58000,
) -> Optional[Path]:
    """
    Decimates a dense glTF binary asset using Headless Blender 4.5.
    Preserves UV mapping, normals, and materials while reducing vertex count to within budget.
    """
    try:
        from vegetation_pipeline.renderer import resolve_blender_binary
        blender_bin = resolve_blender_binary()
    except Exception as e:
        logger.debug("resolve_blender_binary import error: %s", e)
        blender_bin = None

    if not blender_bin:
        logger.warning("Blender binary not found for decimation; skipping.")
        return None

    glb_p = Path(glb_path).resolve()
    if not glb_p.is_file():
        return None

    tmp_out = glb_p.parent / f"_decimated_{glb_p.stem}.glb"

    script = (
        "import bpy\n"
        "bpy.ops.wm.read_factory_settings(use_empty=True)\n"
        f"bpy.ops.import_scene.gltf(filepath=r'{glb_p}')\n"
        "mesh_objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']\n"
        "if mesh_objs:\n"
        "    obj = mesh_objs[0]\n"
        "    bpy.context.view_layer.objects.active = obj\n"
        "    nv = len(obj.data.vertices)\n"
        f"    if nv > {target_vertices}:\n"
        f"        ratio = max(0.05, min(0.95, (float({target_vertices}) / float(nv)) * 0.75))\n"
        "        mod = obj.modifiers.new('Decim', 'DECIMATE')\n"
        "        mod.ratio = ratio\n"
        "        bpy.ops.object.modifier_apply(modifier='Decim')\n"
        f"        if len(obj.data.vertices) > {target_vertices}:\n"
        f"            ratio2 = max(0.05, min(0.95, (float({target_vertices}) / float(len(obj.data.vertices))) * 0.85))\n"
        "            mod2 = obj.modifiers.new('Decim2', 'DECIMATE')\n"
        "            mod2.ratio = ratio2\n"
        "            bpy.ops.object.modifier_apply(modifier='Decim2')\n"
        f"bpy.ops.export_scene.gltf(filepath=r'{tmp_out}', export_format='GLB')\n"
    )

    try:
        res = subprocess.run(
            [str(blender_bin), "--background", "--factory-startup", "--python-expr", script],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if res.returncode == 0 and tmp_out.is_file():
            logger.info("Blender decimation succeeded for %s -> %s", glb_p.name, tmp_out.name)
            return tmp_out
        else:
            logger.warning("Blender decimation failed: %s", res.stderr)
            return None
    except Exception as e:
        logger.warning("Blender decimation invocation error: %s", e)
        return None


def pack_metallic_roughness(roughness: Image.Image, metallic: Image.Image) -> Image.Image:
    """Packs Occlusion (R=255), Roughness (G), and Metallic (B) into glTF 2.0 ORM texture."""
    target_size = roughness.size
    r_img = roughness.convert("L")
    m_img = metallic.convert("L").resize(target_size, Image.Resampling.BILINEAR)

    r_arr = np.array(r_img, dtype=np.uint8)
    m_arr = np.array(m_img, dtype=np.uint8)
    h, w = r_arr.shape
    occ_arr = np.full((h, w), 255, dtype=np.uint8)

    packed = np.dstack([occ_arr, r_arr, m_arr])
    return Image.fromarray(packed, mode="RGB")


# ==============================================================================
# MULTI-FORMAT EXPORTERS
# ==============================================================================

def export_production_glb(
    mesh: MeshGeometry,
    filepath: Union[str, Path],
    textures: Dict[str, Image.Image],
    species_id: str = "botanical_asset",
    double_sided: bool = True,
) -> Path:
    """
    Exports production GLB with embedded 4-channel PBR textures, doubleSided foliage,
    and strictly ZERO skeletal armatures (N_bones = 0).
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    num_verts = len(mesh.vertices)
    num_indices = len(mesh.faces) * 3

    # Flatten geometric buffers
    pos_data = struct.pack(f"<{num_verts * 3}f", *[c for v in mesh.vertices for c in v])
    norm_data = struct.pack(f"<{num_verts * 3}f", *[c for vn in mesh.normals for c in vn])
    uv_data = struct.pack(f"<{num_verts * 2}f", *[c for vt in mesh.uvs for c in vt])

    use_uint32 = num_verts > 65535
    idx_fmt = f"<{num_indices}I" if use_uint32 else f"<{num_indices}H"
    idx_type = 5125 if use_uint32 else 5123
    flat_indices = [idx for face in mesh.faces for idx in face]
    idx_data = struct.pack(idx_fmt, *flat_indices)

    # Encode textures to PNG bytes
    def _to_png_bytes(img: Image.Image) -> bytes:
        bio = io.BytesIO()
        img.save(bio, format="PNG")
        return bio.getvalue()

    albedo_img = textures["albedo"]
    normal_img = textures["normal"]
    roughness_img = textures["roughness"]
    metallic_img = textures["metallic"]

    orm_img = pack_metallic_roughness(roughness_img, metallic_img)

    b_albedo = _to_png_bytes(albedo_img)
    b_orm = _to_png_bytes(orm_img)
    b_normal = _to_png_bytes(normal_img)
    b_roughness = _to_png_bytes(roughness_img)
    b_metallic = _to_png_bytes(metallic_img)

    # Pack bufferViews with 4-byte padding
    buffers_data = [
        (pos_data, 34962),      # BV 0: Position (ARRAY_BUFFER)
        (norm_data, 34962),     # BV 1: Normal (ARRAY_BUFFER)
        (uv_data, 34962),       # BV 2: UV (ARRAY_BUFFER)
        (idx_data, 34963),      # BV 3: Indices (ELEMENT_ARRAY_BUFFER)
        (b_albedo, None),       # BV 4: Image Albedo
        (b_orm, None),          # BV 5: Image MetallicRoughness
        (b_normal, None),       # BV 6: Image Normal
        (b_roughness, None),    # BV 7: Image Roughness
        (b_metallic, None),     # BV 8: Image Metallic
    ]

    bin_chunks = []
    buffer_views = []
    cur_offset = 0

    for raw_b, target in buffers_data:
        raw_len = len(raw_b)
        bv_dict: Dict[str, Any] = {
            "buffer": 0,
            "byteOffset": cur_offset,
            "byteLength": raw_len,
        }
        if target is not None:
            bv_dict["target"] = target
        buffer_views.append(bv_dict)

        padded_b = pad_4(raw_b)
        bin_chunks.append(padded_b)
        cur_offset += len(padded_b)

    bin_buffer = b"".join(bin_chunks)

    # Accessors
    min_x = float(min(v[0] for v in mesh.vertices)) if mesh.vertices else 0.0
    max_x = float(max(v[0] for v in mesh.vertices)) if mesh.vertices else 0.0
    min_y = float(min(v[1] for v in mesh.vertices)) if mesh.vertices else 0.0
    max_y = float(max(v[1] for v in mesh.vertices)) if mesh.vertices else 0.0
    min_z = float(min(v[2] for v in mesh.vertices)) if mesh.vertices else 0.0
    max_z = float(max(v[2] for v in mesh.vertices)) if mesh.vertices else 0.0

    accessors = [
        {
            "bufferView": 0,
            "componentType": 5126,
            "count": num_verts,
            "type": "VEC3",
            "min": [min_x, min_y, min_z],
            "max": [max_x, max_y, max_z],
        },
        {"bufferView": 1, "componentType": 5126, "count": num_verts, "type": "VEC3"},
        {"bufferView": 2, "componentType": 5126, "count": num_verts, "type": "VEC2"},
        {"bufferView": 3, "componentType": idx_type, "count": num_indices, "type": "SCALAR"},
    ]

    images = [
        {"bufferView": 4, "mimeType": "image/png", "name": "albedo"},
        {"bufferView": 5, "mimeType": "image/png", "name": "metallicRoughness"},
        {"bufferView": 6, "mimeType": "image/png", "name": "normal"},
        {"bufferView": 7, "mimeType": "image/png", "name": "roughness"},
        {"bufferView": 8, "mimeType": "image/png", "name": "metallic"},
    ]

    samplers = [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}]

    textures_meta = [
        {"sampler": 0, "source": 0, "name": "AlbedoTexture"},
        {"sampler": 0, "source": 1, "name": "MetallicRoughnessTexture"},
        {"sampler": 0, "source": 2, "name": "NormalTexture"},
    ]

    materials = [
        {
            "name": f"M_{species_id}",
            "doubleSided": double_sided,
            "pbrMetallicRoughness": {
                "baseColorTexture": {"index": 0},
                "metallicRoughnessTexture": {"index": 1},
                "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
                "metallicFactor": 1.0,
                "roughnessFactor": 1.0,
            },
            "normalTexture": {"index": 2, "scale": 1.0},
        }
    ]

    gltf_dict: Dict[str, Any] = {
        "asset": {"version": "2.0", "generator": "MorphoMesh Botanical PostProcessor"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": species_id}],
        "meshes": [
            {
                "primitives": [
                    {
                        "attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2},
                        "indices": 3,
                        "mode": 4,
                        "material": 0,
                    }
                ],
                "name": f"{species_id}_mesh",
            }
        ],
        "materials": materials,
        "textures": textures_meta,
        "images": images,
        "samplers": samplers,
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"byteLength": len(bin_buffer)}],
    }

    json_bytes = json.dumps(gltf_dict, separators=(",", ":")).encode("utf-8")
    json_pad = (4 - (len(json_bytes) % 4)) % 4
    json_bytes += b" " * json_pad

    json_len = len(json_bytes)
    bin_len = len(bin_buffer)
    total_len = 12 + (8 + json_len) + (8 + bin_len)

    header = struct.pack("<4sII", b"glTF", 2, total_len)
    chunk0_hdr = struct.pack("<I4s", json_len, b"JSON")
    chunk1_hdr = struct.pack("<I4s", bin_len, b"BIN\x00")

    with open(filepath, "wb") as f:
        f.write(header)
        f.write(chunk0_hdr)
        f.write(json_bytes)
        f.write(chunk1_hdr)
        f.write(bin_buffer)

    return filepath


def export_companion_obj_mtl(
    mesh: MeshGeometry,
    obj_filepath: Union[str, Path],
    textures: Dict[str, Image.Image],
    species_id: str = "botanical_asset",
) -> Tuple[Path, Path, Dict[str, Path]]:
    """
    Exports companion Wavefront OBJ and MTL files, linking to discrete texture maps.
    """
    obj_filepath = Path(obj_filepath)
    out_dir = obj_filepath.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    mtl_filepath = out_dir / f"{species_id}.mtl"
    tex_dir = out_dir / "textures"
    tex_dir.mkdir(parents=True, exist_ok=True)

    # 1. Save discrete PNG textures to disk
    texture_paths: Dict[str, Path] = {}
    for key in ("albedo", "normal", "roughness", "metallic"):
        img = textures[key]
        p = tex_dir / f"{key}.png"
        if key in ("roughness", "metallic"):
            img.convert("L").save(p, format="PNG")
        else:
            img.convert("RGB").save(p, format="PNG")
        texture_paths[key] = p

    # 2. Write MTL Material File
    mat_name = f"M_{species_id}"
    with open(mtl_filepath, "w", encoding="utf-8") as f:
        f.write("# MorphoMesh Botanical Material Library\n")
        f.write(f"# Species: {species_id}\n\n")
        f.write(f"newmtl {mat_name}\n")
        f.write("Ka 1.000000 1.000000 1.000000\n")
        f.write("Kd 1.000000 1.000000 1.000000\n")
        f.write("Ks 0.200000 0.200000 0.200000\n")
        f.write("Ns 128.000000\n")
        f.write("d 1.000000\n")
        f.write("illum 2\n\n")
        f.write("map_Kd textures/albedo.png\n")
        f.write("map_Bump -bm 1.0 textures/normal.png\n")
        f.write("norm textures/normal.png\n")
        f.write("map_Pr textures/roughness.png\n")
        f.write("map_Pm textures/metallic.png\n")

    # 3. Write OBJ Geometry File
    with open(obj_filepath, "w", encoding="utf-8") as f:
        f.write("# MorphoMesh Botanical Asset Library\n")
        f.write(f"# Species: {species_id}\n")
        f.write(f"mtllib {mtl_filepath.name}\n")
        f.write(f"o {species_id}\n\n")

        for v in mesh.vertices:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        for vn in mesh.normals:
            f.write(f"vn {vn[0]:.6f} {vn[1]:.6f} {vn[2]:.6f}\n")
        for vt in mesh.uvs:
            f.write(f"vt {vt[0]:.6f} {vt[1]:.6f}\n")

        f.write(f"\nusemtl {mat_name}\n")
        f.write("s 1\n")
        for face in mesh.faces:
            f.write(
                f"f {face[0] + 1}/{face[0] + 1}/{face[0] + 1} "
                f"{face[1] + 1}/{face[1] + 1}/{face[1] + 1} "
                f"{face[2] + 1}/{face[2] + 1}/{face[2] + 1}\n"
            )

    return obj_filepath, mtl_filepath, texture_paths


# ==============================================================================
# POST-PROCESSOR ENGINE CLASS & DISPATCH
# ==============================================================================

def resolve_target_output_dir(
    output_dir: Optional[Union[str, Path]],
    species: PlantSpecies,
) -> Path:
    """
    Resolves standard packaging hierarchy: output/<short_category>/<species_id>/.
    Handles custom paths cleanly.
    """
    if output_dir is None:
        return Path("output") / species.short_category / species.species_id

    target = Path(output_dir)
    # If target already points directly to the species directory
    if target.name == species.species_id:
        return target

    # If target points to category directory
    if target.name == species.short_category or target.name == species.category_id:
        return target / species.species_id

    # Otherwise route under base_dir / <short_category> / <species_id>
    return target / species.short_category / species.species_id


class AssetPostProcessor:
    """
    Production post-processing, metric normalization, and multi-format packaging engine.
    Transforms un-normalized RawAsset into fully standardized ExportedAsset.
    """

    def __init__(self, config: Optional[PostProcessorConfig] = None) -> None:
        self.config = config.model_copy() if config is not None else PostProcessorConfig()
        if self.config.enable_double_sided is not None:
            self.config.double_sided_foliage = self.config.enable_double_sided
        if self.config.export_obj_mtl is not None:
            self.config.export_obj = self.config.export_obj_mtl

    def process_asset(
        self,
        raw_asset: RawAsset,
        species: Union[PlantSpecies, str],
        output_dir: Optional[Union[str, Path]] = None,
    ) -> ExportedAsset:
        """
        Master normalization and multi-format export pipeline.
        
        Execution Pipeline:
        1. Resolve species input and target output directory.
        2. Ingest or unpack 3D mesh geometry into an isolated MeshGeometry working instance.
        3. Snap lowest contact vertex to Z_min = 0.000m.
        4. Center horizontal (X, Y) base contact centroid to (0, 0) using bottom 5% height slice.
        5. Normalize metric dimensions to match catalog height target proportionally.
        6. Recalculate/normalize unit vertex normals.
        7. Ingest, validate, or synthesize complete 4-channel PBR texture maps.
        8. Write textures to <output_dir>/textures/.
        9. Build and export production .glb with embedded PBR textures, doubleSided foliage, and 0 armatures.
        10. Build and export companion Wavefront .obj and .mtl referencing textures/.
        11. Generate structured asset_manifest.json.
        12. Return validated ExportedAsset conforming to M3 <-> M4 contract.
        """
        # 1. Resolve species
        if isinstance(species, str):
            species_obj = get_species(species)
        elif isinstance(species, PlantSpecies):
            species_obj = species
        else:
            raise TypeError(f"Expected species as PlantSpecies or str, got {type(species)}")

        # 2. Resolve target output directory
        target_dir = resolve_target_output_dir(output_dir, species_obj)
        target_dir.mkdir(parents=True, exist_ok=True)

        # 3. Ingest MeshGeometry (isolated copy)
        glb_to_load = raw_asset.glb_path
        tmp_decimated = None
        if raw_asset.mesh is None and glb_to_load and Path(glb_to_load).is_file():
            try:
                gltf_hdr, _ = unpack_glb_header_and_json(glb_to_load)
                accs = gltf_hdr.get("accessors", [])
                for m in gltf_hdr.get("meshes", []):
                    for p in m.get("primitives", []):
                        pos_acc_idx = p.get("attributes", {}).get("POSITION")
                        if pos_acc_idx is not None and pos_acc_idx < len(accs):
                            v_count = accs[pos_acc_idx].get("count", 0)
                            if v_count > 63500:
                                target_v = 52000 + (abs(hash(species_obj.species_id)) % 10000)
                                tmp_dec = decimate_glb_with_blender(glb_to_load, target_vertices=target_v)
                                if tmp_dec and tmp_dec.is_file():
                                    glb_to_load = tmp_dec
                                    tmp_decimated = tmp_dec
                            break
                    if tmp_decimated:
                        break
            except Exception as e:
                logger.debug("GLB decimation check note: %s", e)

        if raw_asset.mesh is not None:
            mesh = MeshGeometry()
            mesh.vertices = list(raw_asset.mesh.vertices)
            mesh.normals = list(raw_asset.mesh.normals)
            mesh.uvs = list(raw_asset.mesh.uvs)
            mesh.faces = list(raw_asset.mesh.faces)
            mesh.vertex_groups = {k: list(v) for k, v in raw_asset.mesh.vertex_groups.items()}
        else:
            mesh = load_mesh_from_glb(glb_to_load)

        if tmp_decimated and tmp_decimated.is_file():
            try:
                tmp_decimated.unlink()
            except OSError:
                pass

        # Validate finite coordinates
        for i, v in enumerate(mesh.vertices):
            if not (math.isfinite(v[0]) and math.isfinite(v[1]) and math.isfinite(v[2])):
                raise ValueError(f"Mesh vertex {i} contains non-finite coordinates (NaN or Inf): {v}")

        # Clean degenerate zero-area faces and duplicate indices
        mesh = clean_mesh_geometry(mesh)

        # Check degenerate height
        zs = [v[2] for v in mesh.vertices]
        if not zs or (max(zs) - min(zs)) <= 1e-6:
            raise ValueError("Degenerate mesh with zero height")

        # 4. Ground Pivot Snapping & Base Centering
        if self.config.snap_ground_pivot or self.config.center_contact_base:
            mesh, shift_centroid, ground_z = snap_ground_pivot_and_center(
                mesh, base_slice_ratio=self.config.base_slice_ratio
            )
        else:
            ground_z = float(min(v[2] for v in mesh.vertices))

        # 5. Metric Scale Normalization
        mesh, final_h, final_spread, scale_factor = normalize_metric_scale(
            mesh,
            species=species_obj,
            strategy=self.config.scaling_strategy,
            aspect_clamp=self.config.aspect_constraint_clamp,
        )

        # Re-clean mesh to guarantee zero degenerate faces after scaling
        mesh = clean_mesh_geometry(mesh)

        # Re-verify ground contact at exact 0.000m
        z_min_final = min(v[2] for v in mesh.vertices)
        if abs(z_min_final) > 1e-7:
            mesh.vertices = [(v[0], v[1], v[2] - z_min_final) for v in mesh.vertices]
            ground_z = 0.0
        else:
            ground_z = float(z_min_final)

        # Compute post-normalization base centroid
        h_extent = max(v[2] for v in mesh.vertices) - min(v[2] for v in mesh.vertices)
        slice_thresh = min(v[2] for v in mesh.vertices) + self.config.base_slice_ratio * h_extent
        post_base_verts = [v for v in mesh.vertices if v[2] <= slice_thresh]
        if post_base_verts:
            base_cx = float(np.mean([v[0] for v in post_base_verts]))
            base_cy = float(np.mean([v[1] for v in post_base_verts]))
        else:
            base_cx, base_cy = 0.0, 0.0

        # 6. Ingest or synthesize 4-channel PBR textures
        raw_tex: Dict[str, Image.Image] = {}
        if raw_asset.textures:
            for k, img in raw_asset.textures.items():
                if img is not None:
                    raw_tex[k.lower()] = img

        if raw_asset.texture_paths:
            for k, p in raw_asset.texture_paths.items():
                k_lower = k.lower()
                if k_lower not in raw_tex and p is not None:
                    p_path = Path(p)
                    if p_path.is_file():
                        try:
                            raw_tex[k_lower] = Image.open(p_path)
                        except Exception as e:
                            logger.debug("Failed opening texture %s: %s", p_path, e)

        if not raw_tex and raw_asset.glb_path and Path(raw_asset.glb_path).is_file():
            raw_tex.update(extract_textures_from_glb(raw_asset.glb_path))

        # Channel resolution and fallback synthesis
        albedo_img = raw_tex.get("albedo") or raw_tex.get("basecolor")
        if albedo_img is None:
            albedo_img = Image.new("RGB", (512, 512), (45, 95, 35))
        else:
            albedo_img = albedo_img.convert("RGB")

        normal_img = raw_tex.get("normal")
        if normal_img is None:
            normal_img = Image.new("RGB", (512, 512), (128, 128, 255))
        else:
            normal_img = normal_img.convert("RGB")

        roughness_img = raw_tex.get("roughness")
        if roughness_img is None:
            roughness_img = Image.new("L", (512, 512), 180)
        else:
            roughness_img = roughness_img.convert("L")

        metallic_img = raw_tex.get("metallic")
        if metallic_img is None:
            metallic_img = Image.new("L", (512, 512), 0)
        else:
            metallic_img = metallic_img.convert("L")
            # Botanical dielectric enforcement: clamp metallic max <= 10 (<= 0.0392, strictly within dielectric ceiling 0.05)
            m_data = np.array(metallic_img, dtype=np.uint8)
            m_data = np.clip(m_data, 0, 10)
            metallic_img = Image.fromarray(m_data, mode="L")

        # Guarantee minimum 256x256 resolution
        min_res = 256
        res_tex: Dict[str, Image.Image] = {}
        for name, img in [
            ("albedo", albedo_img),
            ("normal", normal_img),
            ("roughness", roughness_img),
            ("metallic", metallic_img),
        ]:
            if img.width < min_res or img.height < min_res:
                nw = max(min_res, img.width)
                nh = max(min_res, img.height)
                img = img.resize((nw, nh), Image.Resampling.BILINEAR)
            res_tex[name] = img

        # 7. Dual-Format Export: Production GLB
        glb_path = target_dir / f"{species_obj.species_id}.glb"
        export_production_glb(
            mesh=mesh,
            filepath=glb_path,
            textures=res_tex,
            species_id=species_obj.species_id,
            double_sided=self.config.double_sided_foliage,
        )

        # 8. Dual-Format Export: Companion Wavefront OBJ & MTL
        obj_path = target_dir / f"{species_obj.species_id}.obj"
        obj_p, mtl_p, tex_paths = export_companion_obj_mtl(
            mesh=mesh,
            obj_filepath=obj_path,
            textures=res_tex,
            species_id=species_obj.species_id,
        )

        # 9. Compute Final Extents and Dimensions
        ext = compute_mesh_extents(mesh)
        dimensions = AssetDimensions(
            height_m=round(final_h, 4),
            canopy_spread_m=round(final_spread, 4),
            canopy_width_m=round(ext["dx"], 4),
            canopy_depth_m=round(ext["dy"], 4),
            width_m=round(ext["dx"], 4),
            depth_m=round(ext["dy"], 4),
            target_height_m=species_obj.dimensions.height_m,
            target_canopy_spread_m=species_obj.dimensions.canopy_spread_m,
            bounding_box_min=[round(ext["min_x"], 4), round(ext["min_y"], 4), round(ext["min_z"], 4)],
            bounding_box_max=[round(ext["max_x"], 4), round(ext["max_y"], 4), round(ext["max_z"], 4)],
            bbox_min=[round(ext["min_x"], 4), round(ext["min_y"], 4), round(ext["min_z"], 4)],
            bbox_max=[round(ext["max_x"], 4), round(ext["max_y"], 4), round(ext["max_z"], 4)],
        )

        # 10. Generate Asset Manifest
        manifest_path = target_dir / "asset_manifest.json"
        manifest_data: Dict[str, Any] = {
            "schema_version": "1.0.0",
            "species_id": species_obj.species_id,
            "taxonomy": {
                "common_name": species_obj.common_name,
                "scientific_name": species_obj.scientific_name,
                "family": species_obj.family,
                "category": species_obj.category,
                "category_id": species_obj.category_id,
                "category_name": species_obj.category_name,
                "short_category": species_obj.short_category,
                "biome": species_obj.biome,
                "growth_habit": species_obj.morphology.growth_habit,
                "branching_pattern": species_obj.morphology.branching_pattern,
                "foliage_density": species_obj.morphology.foliage_density,
            },
            "geometry": {
                "vertex_count": len(mesh.vertices),
                "face_count": len(mesh.faces),
                "triangle_count": len(mesh.faces),
                "has_armature": False,
                "has_skins": False,
                "pivot_grounded": True,
                "ground_contact_z": round(ground_z, 6),
                "ground_z_min_m": round(ground_z, 6),
                "base_centroid_xy": [round(base_cx, 6), round(base_cy, 6)],
                "bounding_box": {
                    "min_point": [round(ext["min_x"], 4), round(ext["min_y"], 4), round(ext["min_z"], 4)],
                    "max_point": [round(ext["max_x"], 4), round(ext["max_y"], 4), round(ext["max_z"], 4)],
                    "dimensions": [round(ext["dx"], 4), round(ext["dy"], 4), round(ext["dz"], 4)],
                },
                "dimensions_m": {
                    "height_m": round(final_h, 4),
                    "canopy_spread_m": round(final_spread, 4),
                    "width_m": round(ext["dx"], 4),
                    "depth_m": round(ext["dy"], 4),
                    "target_height_m": species_obj.dimensions.height_m,
                    "target_canopy_spread_m": species_obj.dimensions.canopy_spread_m,
                },
            },
            "normalization": {
                "target_height_m": species_obj.dimensions.height_m,
                "target_canopy_spread_m": species_obj.dimensions.canopy_spread_m,
                "scale_factor": round(scale_factor, 6),
                "normalized_height_m": round(final_h, 4),
                "normalized_canopy_spread_m": round(final_spread, 4),
                "strategy": self.config.scaling_strategy,
            },
            "materials": {
                "workflow": "Metallic-Roughness PBR",
                "double_sided": self.config.double_sided_foliage,
                "channels": ["albedo", "normal", "roughness", "metallic"],
                "texture_format": self.config.texture_format,
            },
            "files": {
                "glb": f"{species_obj.species_id}.glb",
                "obj": f"{species_obj.species_id}.obj",
                "mtl": f"{species_obj.species_id}.mtl",
                "textures": {
                    "albedo": "textures/albedo.png",
                    "normal": "textures/normal.png",
                    "roughness": "textures/roughness.png",
                    "metallic": "textures/metallic.png",
                },
            },
            "provenance": {
                **(raw_asset.metadata.get("provenance", {}) if isinstance(raw_asset.metadata, dict) and isinstance(raw_asset.metadata.get("provenance"), dict) else {}),
                "source": (raw_asset.metadata.get("provenance", {}).get("source") if isinstance(raw_asset.metadata, dict) and isinstance(raw_asset.metadata.get("provenance"), dict) else None) or raw_asset.source or "meshy",
                "export_timestamp": datetime.now(timezone.utc).isoformat(),
                "task_id": (raw_asset.metadata.get("provenance", {}).get("task_id") if isinstance(raw_asset.metadata, dict) and isinstance(raw_asset.metadata.get("provenance"), dict) else None) or (raw_asset.metadata.get("task_id") if isinstance(raw_asset.metadata, dict) else None),
                "generator_metadata": raw_asset.metadata,
            },
            "metadata": {
                "scale_factor": scale_factor,
                **raw_asset.metadata,
            },
        }

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        # 11. Return validated ExportedAsset
        return ExportedAsset(
            species_id=species_obj.species_id,
            category_id=species_obj.category_id,
            glb_path=glb_path,
            obj_path=obj_p,
            mtl_path=mtl_p,
            texture_paths=tex_paths,
            manifest_path=manifest_path,
            dimensions=dimensions,
            vertex_count=len(mesh.vertices),
            face_count=len(mesh.faces),
            source=raw_asset.source,
            ground_pivot_z=round(ground_z, 6),
            base_centroid=(round(base_cx, 6), round(base_cy, 6)),
            metadata={
                "scale_factor": scale_factor,
                **manifest_data,
            },
        )

    def process_and_export(
        self,
        raw_asset: RawAsset,
        species: Union[PlantSpecies, str],
        output_dir: Optional[Union[str, Path]] = None,
    ) -> ExportedAsset:
        """Alias for process_asset."""
        return self.process_asset(raw_asset, species, output_dir=output_dir)


def process_and_export(
    raw_asset: RawAsset,
    species: Union[PlantSpecies, str],
    output_dir: Optional[Union[str, Path]] = None,
    config: Optional[PostProcessorConfig] = None,
) -> ExportedAsset:
    """Convenience standalone dispatch conforming to PROJECT.md interface contract."""
    processor = AssetPostProcessor(config=config)
    return processor.process_asset(raw_asset, species, output_dir=output_dir)


__all__ = [
    "AssetDimensions",
    "PostProcessorConfig",
    "NormalizationConfig",
    "ExportedAsset",
    "AssetPostProcessor",
    "process_and_export",
    "load_mesh_from_glb",
    "snap_ground_pivot_and_center",
    "normalize_metric_scale",
    "export_production_glb",
    "export_companion_obj_mtl",
]
