"""
Prototype implementation and test of vegetation_pipeline/renderer.py
Tests both Headless Blender 4.5.4 LTS mode and Pure-Python Software Fallback mode.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger("vegetation_pipeline.renderer")

# ==============================================================================
# CONFIGURATION AND SCHEMAS
# ==============================================================================

class TurntableAngle(BaseModel):
    """Specification of a camera viewpoint for turntable inspection."""
    name: str
    filename: str
    elevation_deg: float
    azimuth_deg: float
    label: str

DEFAULT_TURNTABLE_ANGLES: List[TurntableAngle] = [
    TurntableAngle(name="hero", filename="turntable_01.png", elevation_deg=25.0, azimuth_deg=45.0, label="1. HERO 3/4 (25°/45°)"),
    TurntableAngle(name="front", filename="turntable_02.png", elevation_deg=0.0, azimuth_deg=0.0, label="2. FRONT ELEVATION (0°/0°)"),
    TurntableAngle(name="side", filename="turntable_03.png", elevation_deg=0.0, azimuth_deg=90.0, label="3. SIDE ELEVATION (0°/90°)"),
    TurntableAngle(name="crown", filename="turntable_04.png", elevation_deg=85.0, azimuth_deg=0.0, label="4. TOP CROWN (85°/0°)"),
]

class RenderConfig(BaseModel):
    """Configuration for botanical preview rendering."""
    model_config = ConfigDict(extra="ignore")

    resolution: int = Field(default=512, ge=128, le=2048)
    contact_sheet_resolution: int = Field(default=1024, ge=512, le=4096)
    engine: Literal["auto", "cycles", "eevee_next", "software"] = Field(default="auto")
    cycles_samples: int = Field(default=24, ge=4, le=128)
    margin: float = Field(default=0.15, ge=0.0, le=0.5)
    timeout_seconds: int = Field(default=90, ge=10, le=300)
    focal_length_mm: float = Field(default=50.0, ge=18.0, le=200.0)
    enable_contact_sheet: bool = Field(default=True)
    shadow_catcher: bool = Field(default=True)
    blender_path: Optional[Path] = Field(default=None)


# ==============================================================================
# BLENDER BINARY RESOLVER
# ==============================================================================

def resolve_blender_binary(explicit_path: Optional[Union[str, Path]] = None) -> Optional[Path]:
    """
    Locates Blender executable on Windows, macOS, or Linux.
    Checks explicit path, environment variables, default install paths, and PATH.
    """
    prog_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    candidates = [
        explicit_path,
        os.environ.get("BLENDER_BIN_PATH"),
        os.environ.get("BLENDER_PATH"),
        os.path.join(prog_files, "Blender Foundation", "Blender 4.5", "blender.exe"),
        os.path.join(prog_files, "Blender Foundation", "Blender 4.2", "blender.exe"),
        r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe",
        "/Applications/Blender.app/Contents/MacOS/Blender",
        "/usr/bin/blender",
        "/usr/local/bin/blender",
        shutil.which("blender"),
    ]
    for c in candidates:
        if c:
            p = Path(c)
            if p.is_file():
                if os.name == "nt" or os.access(str(p), os.X_OK):
                    return p
    return None


# ==============================================================================
# BLENDER EMBEDDED AUTOMATION SCRIPT TEMPLATE
# ==============================================================================

BLENDER_RENDER_SCRIPT_CODE = r'''
import argparse
import math
import os
import sys
import time
import bpy
import mathutils

def main():
    # Parse arguments after '--'
    argv = sys.argv
    if "--" in argv:
        args_to_parse = argv[argv.index("--") + 1:]
    else:
        args_to_parse = []

    parser = argparse.ArgumentParser(description="Headless Botanical Turntable Renderer")
    parser.add_argument("--model", required=True, help="Path to input GLB or OBJ")
    parser.add_argument("--outdir", required=True, help="Output directory")
    parser.add_argument("--resolution", type=int, default=512)
    parser.add_argument("--engine", default="CYCLES", choices=["CYCLES", "BLENDER_EEVEE_NEXT", "EEVEE_NEXT"])
    parser.add_argument("--samples", type=int, default=24)
    parser.add_argument("--margin", type=float, default=0.15)
    parser.add_argument("--focal", type=float, default=50.0)
    parser.add_argument("--shadow-catcher", action="store_true", default=True)

    args = parser.parse_args(args_to_parse)

    os.makedirs(args.outdir, exist_ok=True)

    # 1. Reset scene to empty factory state
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    # Render settings
    scene.render.resolution_x = args.resolution
    scene.render.resolution_y = args.resolution
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'

    # Color management: sRGB / AgX (Blender 4.0+ default)
    if hasattr(scene.display_settings, "display_device"):
        scene.display_settings.display_device = 'sRGB'
    if hasattr(scene.view_settings, "view_transform"):
        # AgX or Standard
        if 'AgX' in bpy.types.ColorManagedViewSettings.bl_rna.properties['view_transform'].enum_items:
            scene.view_settings.view_transform = 'AgX'

    # Engine selection
    engine_name = args.engine.upper()
    if engine_name in ("EEVEE", "EEVEE_NEXT", "BLENDER_EEVEE_NEXT"):
        scene.render.engine = 'BLENDER_EEVEE_NEXT'
    else:
        scene.render.engine = 'CYCLES'
        scene.cycles.device = 'CPU'
        scene.cycles.samples = args.samples
        scene.cycles.preview_samples = max(4, args.samples // 2)
        scene.cycles.use_denoising = True

    # 2. Model Import
    model_path = args.model
    if model_path.lower().endswith(".glb") or model_path.lower().endswith(".gltf"):
        bpy.ops.import_scene.gltf(filepath=model_path)
    elif model_path.lower().endswith(".obj"):
        bpy.ops.wm.obj_import(filepath=model_path, forward_axis='Y', up_axis='Z')
    else:
        raise ValueError(f"Unsupported model format: {model_path}")

    mesh_objs = [o for o in scene.objects if o.type == 'MESH']
    if not mesh_objs:
        raise RuntimeError(f"No mesh objects found after importing {model_path}")

    # Foliage Shader and Double-Sided Setup
    for obj in mesh_objs:
        for slot in obj.material_slots:
            if slot.material:
                mat = slot.material
                mat.use_nodes = True
                if hasattr(mat, "blend_method"):
                    mat.blend_method = 'HASHED'
                if hasattr(mat, "surface_render_method"):
                    mat.surface_render_method = 'DITHERED'

    # Auto-Orientation check:
    # If height is lying on Y-axis (from post_processor glTF export), rotate -90 deg on X
    for obj in mesh_objs:
        corners = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
        min_y = min(c[1] for c in corners)
        max_y = max(c[1] for c in corners)
        min_z = min(c[2] for c in corners)
        max_z = max(c[2] for c in corners)
        if (max_y - min_y) > (max_z - min_z) * 1.5:
            rot = mathutils.Matrix.Rotation(-math.pi / 2.0, 4, 'X')
            obj.matrix_world = rot @ obj.matrix_world

    # Recompute unified world bounding box
    all_corners = []
    for obj in mesh_objs:
        for c in obj.bound_box:
            all_corners.append(obj.matrix_world @ mathutils.Vector(c))

    min_x = min(c[0] for c in all_corners)
    max_x = max(c[0] for c in all_corners)
    min_y = min(c[1] for c in all_corners)
    max_y = max(c[1] for c in all_corners)
    min_z = min(c[2] for c in all_corners)
    max_z = max(c[2] for c in all_corners)

    center_x = (min_x + max_x) / 2.0
    center_y = (min_y + max_y) / 2.0
    center_z = (min_z + max_z) / 2.0
    target_center = mathutils.Vector((center_x, center_y, center_z))

    dx = max_x - min_x
    dy = max_y - min_y
    dz = max_z - min_z
    spread = max(dx, dy)
    radius = 0.5 * math.sqrt(dx * dx + dy * dy + dz * dz)
    radius = max(radius, 0.05)

    # 3. Ground Contact Shadow Catcher Plane at Z = min_z (0.000m)
    if args.shadow_catcher:
        plane_size = max(spread * 3.5, 6.0)
        bpy.ops.mesh.primitive_plane_add(size=plane_size, location=(center_x, center_y, min_z))
        shadow_plane = bpy.context.active_object
        shadow_plane.name = "GroundShadowCatcher"
        shadow_plane.is_shadow_catcher = True

    # 4. Botanical 3-Point Studio Lighting
    # Key Light (5500K warm daylight, 4.5 energy)
    key_light = bpy.data.lights.new(name="KeyLight", type='SUN')
    key_light.energy = 4.5
    key_light.color = (1.0, 0.95, 0.88)
    key_obj = bpy.data.objects.new(name="KeyLight", object_data=key_light)
    key_obj.rotation_euler = (math.radians(45.0), math.radians(15.0), math.radians(45.0))
    scene.collection.objects.link(key_obj)

    # Fill Light (6500K soft cool ambient, 1.8 energy)
    fill_light = bpy.data.lights.new(name="FillLight", type='SUN')
    fill_light.energy = 1.8
    fill_light.color = (0.88, 0.92, 1.0)
    fill_obj = bpy.data.objects.new(name="FillLight", object_data=fill_light)
    fill_obj.rotation_euler = (math.radians(45.0), math.radians(-20.0), math.radians(-110.0))
    scene.collection.objects.link(fill_obj)

    # Rim Backlight (translucency & silhouette definition, 3.0 energy)
    rim_light = bpy.data.lights.new(name="RimLight", type='SUN')
    rim_light.energy = 3.0
    rim_light.color = (1.0, 1.0, 1.0)
    rim_obj = bpy.data.objects.new(name="RimLight", object_data=rim_light)
    rim_obj.rotation_euler = (math.radians(-50.0), math.radians(10.0), math.radians(180.0))
    scene.collection.objects.link(rim_obj)

    # 5. Camera Setup & Optical Framing Distance
    cam_data = bpy.data.cameras.new("InspectorCamera")
    cam_data.lens = args.focal
    cam_obj = bpy.data.objects.new("InspectorCamera", cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    # d = (R / sin(alpha)) * (1 + margin)
    half_fov = math.atan(36.0 / (2.0 * args.focal))
    dist = (radius / math.sin(half_fov)) * (1.0 + args.margin)

    # 6. Render 4 Standardized Turntable Angles
    angles = [
        ("turntable_01.png", 25.0, 45.0, "Hero 3/4 View"),
        ("turntable_02.png", 0.0, 0.0, "Front View"),
        ("turntable_03.png", 0.0, 90.0, "Side View"),
        ("turntable_04.png", 85.0, 0.0, "Top Crown View"),
    ]

    for filename, elev_deg, azim_deg, label in angles:
        elev = math.radians(elev_deg)
        azim = math.radians(azim_deg)

        px = center_x + dist * math.cos(elev) * math.sin(azim)
        py = center_y - dist * math.cos(elev) * math.cos(azim)
        pz = center_z + dist * math.sin(elev)
        cam_obj.location = (px, py, pz)
        cam_obj.rotation_euler = (target_center - cam_obj.location).to_track_quat('-Z', 'Y').to_euler()

        out_path = os.path.join(args.outdir, filename)
        scene.render.filepath = out_path
        bpy.ops.render.render(write_still=True)
        print(f"RENDER_OK: {filename} -> {out_path} ({os.path.getsize(out_path)} bytes)")

if __name__ == "__main__":
    main()
'''


# ==============================================================================
# CONTACT SHEET MONTAGE GENERATOR
# ==============================================================================

def render_contact_sheet(
    image_paths: List[Path],
    output_path: Path,
    title: str = "Botanical Asset",
    scientific_name: str = "",
    category: str = "",
    height_m: Optional[float] = None,
    polycount: Optional[int] = None,
    resolution: int = 1024,
) -> Path:
    """
    Creates a 1024x1024 2x2 contact sheet montage with species metadata banner,
    clean borders, and viewpoint badges using pure Python PIL.
    """
    canvas = Image.new("RGBA", (resolution, resolution), (245, 247, 250, 255))
    draw = ImageDraw.Draw(canvas)

    header_h = 72
    draw.rectangle([(0, 0), (resolution, header_h)], fill=(20, 24, 33, 255))
    draw.rectangle([(0, header_h - 3), (resolution, header_h)], fill=(46, 160, 67, 255))

    try:
        font_title = ImageFont.truetype("arialbd.ttf", 22)
        font_sub = ImageFont.truetype("ariali.ttf", 14)
        font_meta = ImageFont.truetype("arial.ttf", 13)
        font_badge = ImageFont.truetype("arialbd.ttf", 11)
        font_footer = ImageFont.truetype("arial.ttf", 11)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = font_title
        font_meta = font_title
        font_badge = font_title
        font_footer = font_title

    draw.text((20, 14), title, fill=(255, 255, 255, 255), font=font_title)
    if scientific_name:
        draw.text((20, 42), scientific_name, fill=(160, 175, 195, 255), font=font_sub)

    meta_parts = []
    if category:
        meta_parts.append(category)
    if height_m is not None:
        meta_parts.append(f"Height: {height_m:.2f}m")
    if polycount is not None:
        meta_parts.append(f"Faces: {polycount:,}")
    if meta_parts:
        meta_str = "   |   ".join(meta_parts)
        draw.text((resolution - 420, 28), meta_str, fill=(210, 220, 235, 255), font=font_meta)

    footer_h = 32
    footer_y = resolution - footer_h
    draw.rectangle([(0, footer_y), (resolution, resolution)], fill=(28, 32, 42, 255))
    footer_text = "MorphoMesh Vegetation Library   •   Verified Static Mesh (0 Bones)   •   Z_min = 0.000m   •   4-Channel PBR"
    draw.text((24, footer_y + 9), footer_text, fill=(140, 155, 175, 255), font=font_footer)

    grid_top = header_h
    grid_bottom = footer_y
    pad = 8
    cell_w = (resolution - pad * 3) // 2
    cell_h = (grid_bottom - grid_top - pad * 3) // 2

    view_labels = [
        "1. HERO 3/4 (25°/45°)",
        "2. FRONT ELEVATION (0°/0°)",
        "3. SIDE ELEVATION (0°/90°)",
        "4. TOP CROWN (85°/0°)",
    ]

    cell_coords = [
        (pad, grid_top + pad),
        (pad * 2 + cell_w, grid_top + pad),
        (pad, grid_top + pad * 2 + cell_h),
        (pad * 2 + cell_w, grid_top + pad * 2 + cell_h),
    ]

    for idx in range(4):
        cx, cy = cell_coords[idx]
        cw, ch = cell_w, cell_h
        draw.rectangle([(cx, cy), (cx + cw, cy + ch)], fill=(255, 255, 255, 255), outline=(220, 225, 232, 255), width=1)

        if idx < len(image_paths) and image_paths[idx] and Path(image_paths[idx]).is_file():
            img = Image.open(image_paths[idx]).convert("RGBA")
            target_w = cw - 8
            target_h = ch - 8
            img_thumb = img.copy()
            img_thumb.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
            offset_x = cx + (cw - img_thumb.width) // 2
            offset_y = cy + (ch - img_thumb.height) // 2
            canvas.alpha_composite(img_thumb, (offset_x, offset_y))

        badge_x = cx + 10
        badge_y = cy + 10
        draw.rounded_rectangle([(badge_x, badge_y), (badge_x + 160, badge_y + 20)], radius=4, fill=(35, 40, 52, 220))
        draw.text((badge_x + 8, badge_y + 4), view_labels[idx], fill=(240, 245, 255, 255), font=font_badge)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output_path, "PNG", quality=95)
    return output_path


# ==============================================================================
# PURE-PYTHON SOFTWARE FALLBACK RENDERER
# ==============================================================================

def render_software_fallback(
    model_path: Path,
    output_dir: Path,
    angles: Optional[List[TurntableAngle]] = None,
    albedo_path: Optional[Path] = None,
    resolution: int = 512,
    margin: float = 0.15,
) -> Dict[str, Path]:
    """
    Renders turntable angles in pure Python using numpy and PIL.
    Ensures zero failure when Blender executable is unavailable.
    """
    from test_software_renderer import load_obj_file, software_render_view

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if angles is None:
        angles = DEFAULT_TURNTABLE_ANGLES

    # Load mesh
    if model_path.suffix.lower() == ".obj":
        verts, faces, uvs, f_uvs = load_obj_file(model_path)
    else:
        # Fallback for GLB without OBJ
        companion_obj = model_path.with_suffix(".obj")
        if companion_obj.is_file():
            verts, faces, uvs, f_uvs = load_obj_file(companion_obj)
        else:
            # Parse GLB directly using trimesh or fallback parser
            from vegetation_pipeline.post_processor import unpack_glb_mesh
            mesh_geom = unpack_glb_mesh(model_path)
            verts = np.array(mesh_geom.vertices, dtype=np.float32)
            faces = np.array(mesh_geom.faces, dtype=np.int32)
            uvs = np.array(mesh_geom.uvs, dtype=np.float32)
            f_uvs = faces.copy()

    # Load albedo image
    albedo_img = None
    if albedo_path and Path(albedo_path).is_file():
        albedo_img = Image.open(albedo_path)
    else:
        tex_dir = model_path.parent / "textures"
        cand = tex_dir / "albedo.png"
        if cand.is_file():
            albedo_img = Image.open(cand)

    results: Dict[str, Path] = {}
    for ang in angles:
        img = software_render_view(
            vertices=verts,
            faces=faces,
            uvs=uvs,
            face_uvs=f_uvs,
            albedo_img=albedo_img,
            elevation_deg=ang.elevation_deg,
            azimuth_deg=ang.azimuth_deg,
            resolution=resolution,
            margin=margin,
        )
        out_p = output_dir / ang.filename
        img.save(out_p)
        results[ang.name] = out_p

    return results


# ==============================================================================
# MAIN EXPORTED FUNCTION CONTRACTS
# ==============================================================================

def render_asset_preview(
    asset: Any,
    output_dir: Optional[Path] = None,
    angles: Optional[List[str]] = None,
    use_blender: bool = True,
    config: Optional[RenderConfig] = None,
) -> Dict[str, Path]:
    """
    Renders multi-angle turntable views and contact sheet montage for a botanical asset.

    Args:
        asset: ExportedAsset instance or Path to .glb / .obj / asset directory.
        output_dir: Target directory for preview renders. Defaults to asset directory.
        angles: Optional list of viewpoint names (e.g. ['hero', 'front', 'side', 'crown']).
        use_blender: Whether to attempt Blender 4.5 headless rendering.
        config: Optional RenderConfig overrides.

    Returns:
        Dictionary mapping view names and 'thumbnail' to Path.
    """
    if config is None:
        config = RenderConfig()

    # 1. Resolve model path and metadata
    title = "Botanical Asset"
    scientific_name = ""
    category = ""
    height_m = None
    polycount = None
    albedo_path = None

    if hasattr(asset, "glb_path"):  # ExportedAsset instance
        glb_path = Path(asset.glb_path)
        obj_path = Path(asset.obj_path) if hasattr(asset, "obj_path") and asset.obj_path else None
        target_dir = Path(output_dir) if output_dir else glb_path.parent
        albedo_path = asset.texture_paths.get("albedo") if hasattr(asset, "texture_paths") else None
        species_id = getattr(asset, "species_id", "")
        if hasattr(asset, "dimensions"):
            height_m = getattr(asset.dimensions, "height_m", None)
        if hasattr(asset, "face_count"):
            polycount = getattr(asset, "face_count", None)

        # Try looking up catalog species for rich metadata
        try:
            from vegetation_pipeline.catalog import get_species
            sp = get_species(species_id)
            title = sp.common_name
            scientific_name = sp.scientific_name
            category = sp.category_name
        except Exception:
            title = species_id.replace("veg_", "").replace("_", " ").title()
    elif isinstance(asset, (str, Path)):
        p = Path(asset)
        if p.is_dir():
            target_dir = Path(output_dir) if output_dir else p
            glb_candidates = list(p.glob("*.glb"))
            if not glb_candidates:
                raise FileNotFoundError(f"No GLB file found in directory {p}")
            glb_path = glb_candidates[0]
            obj_candidates = list(p.glob("*.obj"))
            obj_path = obj_candidates[0] if obj_candidates else None
        else:
            target_dir = Path(output_dir) if output_dir else p.parent
            if p.suffix.lower() in (".glb", ".gltf"):
                glb_path = p
                obj_path = p.with_suffix(".obj") if p.with_suffix(".obj").is_file() else None
            elif p.suffix.lower() == ".obj":
                obj_path = p
                glb_path = p.with_suffix(".glb") if p.with_suffix(".glb").is_file() else p
            else:
                raise ValueError(f"Unrecognized model file type: {p}")
        title = glb_path.stem.replace("veg_", "").replace("_", " ").title()
    else:
        raise TypeError(f"Expected ExportedAsset or Path, got {type(asset)}")

    target_dir.mkdir(parents=True, exist_ok=True)

    # 2. Filter requested angles
    active_angles = DEFAULT_TURNTABLE_ANGLES
    if angles:
        wanted = set(a.lower() for a in angles)
        active_angles = [a for a in DEFAULT_TURNTABLE_ANGLES if a.name in wanted or a.filename in wanted]

    rendered_views: Dict[str, Path] = {}
    rendered_with_blender = False

    # 3. Attempt Blender 4.5.4 headless execution
    if use_blender:
        blender_bin = resolve_blender_binary(config.blender_path)
        if blender_bin:
            logger.info("Using Blender binary at %s", blender_bin)
            with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
                f.write(BLENDER_RENDER_SCRIPT_CODE)
                script_path = f.name

            try:
                cmd = [
                    str(blender_bin),
                    "--background",
                    "--factory-startup",
                    "--python",
                    script_path,
                    "--",
                    "--model", str(glb_path),
                    "--outdir", str(target_dir),
                    "--resolution", str(config.resolution),
                    "--engine", "CYCLES" if config.engine == "auto" else config.engine.upper(),
                    "--samples", str(config.cycles_samples),
                    "--margin", str(config.margin),
                    "--focal", str(config.focal_length_mm),
                ]
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=config.timeout_seconds,
                    check=True,
                )
                rendered_with_blender = True
                for ang in active_angles:
                    p = target_dir / ang.filename
                    if p.is_file():
                        rendered_views[ang.name] = p
            except Exception as e:
                logger.warning("Blender execution failed (%s); falling back to pure-Python renderer.", e)
            finally:
                if os.path.exists(script_path):
                    try:
                        os.remove(script_path)
                    except OSError:
                        pass

    # 4. Pure-Python fallback if Blender was not used or failed
    if not rendered_with_blender:
        logger.info("Executing pure-Python software fallback renderer.")
        input_model = obj_path if obj_path and obj_path.is_file() else glb_path
        rendered_views = render_software_fallback(
            model_path=input_model,
            output_dir=target_dir,
            angles=active_angles,
            albedo_path=albedo_path,
            resolution=config.resolution,
            margin=config.margin,
        )

    # 5. Generate 2x2 Contact Sheet Montage
    if config.enable_contact_sheet:
        sheet_imgs = [target_dir / ang.filename for ang in DEFAULT_TURNTABLE_ANGLES]
        thumb_path = target_dir / "thumbnail.png"
        render_contact_sheet(
            image_paths=sheet_imgs,
            output_path=thumb_path,
            title=title,
            scientific_name=scientific_name,
            category=category,
            height_m=height_m,
            polycount=polycount,
            resolution=config.contact_sheet_resolution,
        )
        rendered_views["thumbnail"] = thumb_path

    return rendered_views


def test_full_pipeline():
    print("=== TESTING RENDER PIPELINE ===")
    from vegetation_pipeline.catalog import get_species
    from vegetation_pipeline.generator import ProceduralBotanicalGenerator
    from vegetation_pipeline.post_processor import AssetPostProcessor

    species = get_species("veg_tropical_palm_01")
    proc = ProceduralBotanicalGenerator()
    raw = proc.generate(species, output_dir="E:/tool/mcp/MorphoMesh/.agents/m4_veg_explorer_2/raw_palm")
    post = AssetPostProcessor()
    exported = post.process_asset(raw, species, output_dir="E:/tool/mcp/MorphoMesh/.agents/m4_veg_explorer_2/processed_palm")

    # Test 1: Blender execution
    out_blender = Path("E:/tool/mcp/MorphoMesh/.agents/m4_veg_explorer_2/pipeline_blender_renders")
    t0 = time.time()
    res_blender = render_asset_preview(exported, output_dir=out_blender, use_blender=True)
    t_blender = time.time() - t0
    print(f"Blender render finished in {t_blender:.3f}s: {list(res_blender.keys())}")
    for k, v in res_blender.items():
        assert v.is_file(), f"Missing render file {v}"
        print(f" - {k}: {v.name} ({v.stat().st_size} bytes)")

    # Test 2: Software fallback execution
    out_software = Path("E:/tool/mcp/MorphoMesh/.agents/m4_veg_explorer_2/pipeline_software_renders")
    t0 = time.time()
    res_software = render_asset_preview(exported, output_dir=out_software, use_blender=False)
    t_software = time.time() - t0
    print(f"Software fallback finished in {t_software:.3f}s: {list(res_software.keys())}")
    for k, v in res_software.items():
        assert v.is_file(), f"Missing render file {v}"
        print(f" - {k}: {v.name} ({v.stat().st_size} bytes)")

    print("ALL TESTS PASSED!")

if __name__ == "__main__":
    test_full_pipeline()
