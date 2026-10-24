import os
import math
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
from PIL import Image, ImageDraw

def load_obj_file(obj_path: Union[str, Path]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Parse Wavefront OBJ file into vertices, normals, uvs, and triangular faces."""
    vertices = []
    normals = []
    uvs = []
    faces = []
    face_uvs = []
    face_normals = []

    with open(obj_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            tag = parts[0]
            if tag == "v" and len(parts) >= 4:
                vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
            elif tag == "vn" and len(parts) >= 4:
                normals.append([float(parts[1]), float(parts[2]), float(parts[3])])
            elif tag == "vt" and len(parts) >= 3:
                uvs.append([float(parts[1]), float(parts[2])])
            elif tag == "f" and len(parts) >= 4:
                # Triangle or quad
                face_v = []
                face_vt = []
                face_vn = []
                for p in parts[1:]:
                    sub = p.split("/")
                    face_v.append(int(sub[0]) - 1)
                    if len(sub) > 1 and sub[1]:
                        face_vt.append(int(sub[1]) - 1)
                    if len(sub) > 2 and sub[2]:
                        face_vn.append(int(sub[2]) - 1)
                # Fan triangulate if quad/ngon
                for i in range(1, len(face_v) - 1):
                    faces.append([face_v[0], face_v[i], face_v[i + 1]])
                    if face_vt and len(face_vt) == len(face_v):
                        face_uvs.append([face_vt[0], face_vt[i], face_vt[i + 1]])
                    if face_vn and len(face_vn) == len(face_v):
                        face_normals.append([face_vn[0], face_vn[i], face_vn[i + 1]])

    v_arr = np.array(vertices, dtype=np.float32) if vertices else np.zeros((0, 3), dtype=np.float32)
    f_arr = np.array(faces, dtype=np.int32) if faces else np.zeros((0, 3), dtype=np.int32)
    uv_arr = np.array(uvs, dtype=np.float32) if uvs else np.zeros((0, 2), dtype=np.float32)
    f_uv_arr = np.array(face_uvs, dtype=np.int32) if face_uvs else np.zeros((0, 3), dtype=np.int32)

    return v_arr, f_arr, uv_arr, f_uv_arr


def software_render_view(
    vertices: np.ndarray,
    faces: np.ndarray,
    uvs: np.ndarray,
    face_uvs: np.ndarray,
    albedo_img: Optional[Image.Image],
    elevation_deg: float,
    azimuth_deg: float,
    resolution: int = 512,
    margin: float = 0.15,
) -> Image.Image:
    """
    Renders 3D mesh to 2D image via pure Python orthographic projection,
    depth-sorted painter's algorithm, and directional diffuse lighting.
    """
    if len(vertices) == 0 or len(faces) == 0:
        return Image.new("RGBA", (resolution, resolution), (245, 247, 250, 255))

    # Center and scale
    min_pt = np.min(vertices, axis=0)
    max_pt = np.max(vertices, axis=0)
    center = (min_pt + max_pt) / 2.0
    radius = 0.5 * np.linalg.norm(max_pt - min_pt)
    radius = max(radius, 0.05)

    # Angles in radians
    theta = math.radians(elevation_deg)
    phi = math.radians(azimuth_deg)

    # Camera direction (from center to camera)
    # Azimuth 0 is front along -Y looking towards +Y
    cam_dir = np.array([
        math.cos(theta) * math.sin(phi),
        -math.cos(theta) * math.cos(phi),
        math.sin(theta)
    ], dtype=np.float32)

    # Camera coordinate system:
    # forward: pointing from camera to center = -cam_dir
    fwd = -cam_dir / np.linalg.norm(cam_dir)

    # world up is +Z (unless fwd is collinear with Z)
    world_up = np.array([0.0, 0.0, 1.0], dtype=np.float32)
    if abs(np.dot(fwd, world_up)) > 0.999:
        # Singularity: top-down view looking down along -Z
        world_up = np.array([0.0, 1.0, 0.0], dtype=np.float32)

    # right = fwd x world_up
    right = np.cross(fwd, world_up)
    right /= np.linalg.norm(right)

    # cam_up = right x fwd
    cam_up = np.cross(right, fwd)
    cam_up /= np.linalg.norm(cam_up)

    # Transform vertices relative to center into camera coordinates
    centered_v = vertices - center  # (N, 3)
    x_cam = np.dot(centered_v, right)     # (N,)
    y_cam = np.dot(centered_v, cam_up)    # (N,)
    z_cam = np.dot(centered_v, fwd)       # (N,) depth along view ray

    # Orthographic projection to screen coordinates
    # Extent with margin
    extent = radius * (1.0 + margin)
    half_res = resolution / 2.0
    x_screen = (x_cam / extent) * half_res + half_res
    y_screen = (-y_cam / extent) * half_res + half_res

    # Triangles screen coordinates
    tri_x = x_screen[faces]  # (M, 3)
    tri_y = y_screen[faces]  # (M, 3)
    tri_z = z_cam[faces]     # (M, 3)
    face_depths = np.mean(tri_z, axis=1)  # (M,)

    # Compute face normals for lighting
    v0 = vertices[faces[:, 0]]
    v1 = vertices[faces[:, 1]]
    v2 = vertices[faces[:, 2]]
    edge1 = v1 - v0
    edge2 = v2 - v0
    cross = np.cross(edge1, edge2)
    norm = np.linalg.norm(cross, axis=1, keepdims=True)
    norm[norm == 0] = 1.0
    face_normals = cross / norm

    # Directional Key Light (angled from top-front-right)
    light_dir = np.array([0.5, -0.6, 0.6], dtype=np.float32)
    light_dir /= np.linalg.norm(light_dir)

    # Shading factor: ambient 0.35 + diffuse 0.65 (two-sided lighting for foliage)
    dot = np.abs(np.dot(face_normals, light_dir))
    shading = 0.35 + 0.65 * dot  # (M,)

    # Sample albedo texture if available
    has_albedo = albedo_img is not None and len(uvs) > 0 and len(face_uvs) == len(faces)
    if has_albedo:
        albedo_rgba = np.array(albedo_img.convert("RGBA"))
        tex_h, tex_w = albedo_rgba.shape[:2]
        # UV centroid per face
        u0 = uvs[face_uvs[:, 0]]
        u1 = uvs[face_uvs[:, 1]]
        u2 = uvs[face_uvs[:, 2]]
        mid_uv = (u0 + u1 + u2) / 3.0
        u_px = np.clip((mid_uv[:, 0] * (tex_w - 1)).astype(np.int32), 0, tex_w - 1)
        v_px = np.clip(((1.0 - mid_uv[:, 1]) * (tex_h - 1)).astype(np.int32), 0, tex_h - 1)
        face_colors = albedo_rgba[v_px, u_px, :3]  # (M, 3)
    else:
        # Botanical palette default (leaf green)
        face_colors = np.full((len(faces), 3), [60, 135, 65], dtype=np.uint8)

    # Modulate colors with shading
    lit_colors = np.clip(face_colors.astype(np.float32) * shading[:, None], 0, 255).astype(np.uint8)

    # Sort triangles from furthest to closest (depth ascending)
    sort_idx = np.argsort(face_depths)

    # Create canvas (transparent background for compositing)
    canvas = Image.new("RGBA", (resolution, resolution), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    for i in sort_idx:
        p0 = (float(tri_x[i, 0]), float(tri_y[i, 0]))
        p1 = (float(tri_x[i, 1]), float(tri_y[i, 1]))
        p2 = (float(tri_x[i, 2]), float(tri_y[i, 2]))
        col = (int(lit_colors[i, 0]), int(lit_colors[i, 1]), int(lit_colors[i, 2]), 255)
        draw.polygon([p0, p1, p2], fill=col)

    return canvas


def test_pure_python_renderer():
    obj_path = Path(r"E:\tool\mcp\MorphoMesh\.agents\m4_veg_explorer_2\processed_palm\tropical\veg_tropical_palm_01\veg_tropical_palm_01.obj")
    albedo_path = Path(r"E:\tool\mcp\MorphoMesh\.agents\m4_veg_explorer_2\processed_palm\tropical\veg_tropical_palm_01\textures\albedo.png")
    out_dir = Path(r"E:\tool\mcp\MorphoMesh\.agents\m4_veg_explorer_2\test_software_renders")
    out_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    verts, faces, uvs, f_uvs = load_obj_file(obj_path)
    print(f"Loaded OBJ in {time.time() - t0:.3f}s: {len(verts)} vertices, {len(faces)} faces")

    albedo_img = Image.open(albedo_path) if albedo_path.is_file() else None

    angles = [
        ("turntable_01.png", 25.0, 45.0, "Hero 3/4"),
        ("turntable_02.png", 0.0, 0.0, "Front"),
        ("turntable_03.png", 0.0, 90.0, "Side"),
        ("turntable_04.png", 85.0, 0.0, "Top Crown"),
    ]

    rendered_paths = []
    for fname, elev, azim, label in angles:
        t_view = time.time()
        img = software_render_view(verts, faces, uvs, f_uvs, albedo_img, elev, azim, resolution=512)
        out_p = out_dir / fname
        img.save(out_p)
        print(f"Software rendered {label} in {time.time() - t_view:.3f}s -> {out_p}")
        rendered_paths.append(out_p)

    # Also generate contact sheet using the software renders
    from test_contact_sheet import create_contact_sheet
    thumb_path = out_dir / "thumbnail.png"
    create_contact_sheet(rendered_paths, thumb_path, title="Fan Palm (Software Fallback)", polycount=len(faces))
    print("Pure Python fallback test complete!")

if __name__ == "__main__":
    test_pure_python_renderer()
