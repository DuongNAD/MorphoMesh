"""
Adversarial tests authored by m1_challenger_anime_2:
1. Seam normal alignment: verify that coincident boundary vertices between
   Anime_Head and Anime_Torso have normal vectors with angular deviation < 0.01 radians.
2. Binary glTF and Blend integrity: run headless Blender 4.5.4 LTS to load
   output/anime_mesh_clean.blend and output/anime_mesh_clean.glb, verifying
   mesh object count == 7, collection presence, and polygon integrity.
"""

from __future__ import annotations

import math
import subprocess
from pathlib import Path
import pytest

BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
BLEND_PATH = Path("output/anime_mesh_clean.blend")
GLB_PATH = Path("output/anime_mesh_clean.glb")


def test_blend_file_integrity():
    """Verify output/anime_mesh_clean.blend has 7 mesh objects, Anime_Character_Meshes collection, and valid polygons."""
    assert BLEND_PATH.exists(), f"File {BLEND_PATH} does not exist"

    script = (
        "import bpy\n"
        "mesh_objs = [obj for obj in bpy.data.objects if obj.type == 'MESH']\n"
        "print(f'MESH_COUNT:{len(mesh_objs)}')\n"
        "assert len(mesh_objs) == 7, f'Expected 7 mesh objects, got {len(mesh_objs)}'\n"
        "char_col = bpy.data.collections.get('Anime_Character_Meshes')\n"
        "assert char_col is not None, 'Collection Anime_Character_Meshes not found'\n"
        "col_mesh_objs = [obj for obj in char_col.objects if obj.type == 'MESH']\n"
        "print(f'COL_MESH_COUNT:{len(col_mesh_objs)}')\n"
        "assert len(col_mesh_objs) == 7, f'Expected 7 mesh objects in collection, got {len(col_mesh_objs)}'\n"
        "for obj in mesh_objs:\n"
        "    v_cnt = len(obj.data.vertices)\n"
        "    p_cnt = len(obj.data.polygons)\n"
        "    print(f'OBJ:{obj.name} V:{v_cnt} P:{p_cnt}')\n"
        "    assert v_cnt > 0, f'{obj.name} has 0 vertices'\n"
        "    assert p_cnt > 0, f'{obj.name} has 0 polygons'\n"
        "    deg = [p.index for p in obj.data.polygons if p.area < 1e-8]\n"
        "    assert len(deg) == 0, f'{obj.name} has degenerate polygons'\n"
        "print('PASS_BLEND_INTEGRITY')\n"
    )

    cmd = [BLENDER_EXE, "--background", str(BLEND_PATH), "--python-expr", script]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert res.returncode == 0, f"Blender blend audit failed:\n{res.stderr}\n{res.stdout}"
    assert "PASS_BLEND_INTEGRITY" in res.stdout


def test_glb_file_integrity():
    """Verify output/anime_mesh_clean.glb loads in Blender with 7 mesh objects and valid polygons."""
    assert GLB_PATH.exists(), f"File {GLB_PATH} does not exist"

    script = (
        "import bpy\n"
        "bpy.ops.wm.read_factory_settings(use_empty=True)\n"
        "res = bpy.ops.import_scene.gltf(filepath=r'output/anime_mesh_clean.glb')\n"
        "mesh_objs = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']\n"
        "print(f'GLB_MESH_COUNT:{len(mesh_objs)}')\n"
        "assert len(mesh_objs) == 7, f'Expected 7 mesh objects in GLB, got {len(mesh_objs)}'\n"
        "for obj in mesh_objs:\n"
        "    v_cnt = len(obj.data.vertices)\n"
        "    p_cnt = len(obj.data.polygons)\n"
        "    print(f'GLB_OBJ:{obj.name} V:{v_cnt} P:{p_cnt}')\n"
        "    assert v_cnt > 0, f'{obj.name} in GLB has 0 vertices'\n"
        "    assert p_cnt > 0, f'{obj.name} in GLB has 0 polygons'\n"
        "    deg = [p.index for p in obj.data.polygons if p.area < 1e-8]\n"
        "    assert len(deg) == 0, f'{obj.name} in GLB has degenerate polygons'\n"
        "print('PASS_GLB_INTEGRITY')\n"
    )

    cmd = [BLENDER_EXE, "--background", "--python-expr", script]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert res.returncode == 0, f"Blender GLB audit failed:\n{res.stderr}\n{res.stdout}"
    assert "PASS_GLB_INTEGRITY" in res.stdout


def test_seam_normal_alignment_head_torso():
    """Verify that coincident boundary vertices between Anime_Head and Anime_Torso have angular deviation < 0.01 radians."""
    assert BLEND_PATH.exists(), f"File {BLEND_PATH} does not exist"

    script = (
        "import bpy, math\n"
        "head = bpy.data.objects.get('Anime_Head')\n"
        "torso = bpy.data.objects.get('Anime_Torso')\n"
        "assert head is not None, 'Anime_Head not found'\n"
        "assert torso is not None, 'Anime_Torso not found'\n"
        "head_verts = {i: (head.matrix_world @ v.co, (head.matrix_world.to_3x3() @ v.normal).normalized()) for i, v in enumerate(head.data.vertices)}\n"
        "torso_verts = {i: (torso.matrix_world @ v.co, (torso.matrix_world.to_3x3() @ v.normal).normalized()) for i, v in enumerate(torso.data.vertices)}\n"
        "coincident = []\n"
        "for hi, (hco, hno) in head_verts.items():\n"
        "    for ti, (tco, tno) in torso_verts.items():\n"
        "        if (hco - tco).length < 1e-4:\n"
        "            dot = max(-1.0, min(1.0, hno.dot(tno)))\n"
        "            ang = math.acos(dot)\n"
        "            coincident.append((hi, ti, ang))\n"
        "print(f'COINCIDENT_PAIRS_FOUND:{len(coincident)}')\n"
        "assert len(coincident) > 0, 'No coincident boundary vertices found between Head and Torso'\n"
        "max_dev = max(c[2] for c in coincident)\n"
        "avg_dev = sum(c[2] for c in coincident) / len(coincident)\n"
        "violating = [c for c in coincident if c[2] >= 0.01]\n"
        "print(f'MAX_ANGULAR_DEVIATION_RAD:{max_dev:.6f}')\n"
        "print(f'AVG_ANGULAR_DEVIATION_RAD:{avg_dev:.6f}')\n"
        "print(f'VIOLATIONS_COUNT:{len(violating)}/{len(coincident)}')\n"
        "assert max_dev < 0.01, f'Seam normal angular deviation {max_dev:.6f} rad exceeds 0.01 rad (failed on {len(violating)}/{len(coincident)} vertices)'\n"
        "print('PASS_SEAM_NORMAL_ALIGNMENT')\n"
    )

    cmd = [BLENDER_EXE, "--background", str(BLEND_PATH), "--python-expr", script]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    print(res.stdout)
    assert res.returncode == 0, f"Seam normal verification failed:\n{res.stderr}\n{res.stdout}"
    assert "PASS_SEAM_NORMAL_ALIGNMENT" in res.stdout


def test_seam_normal_alignment_head_torso_glb():
    """Verify that coincident boundary vertices between Anime_Head and Anime_Torso in GLB have angular deviation < 0.01 radians."""
    assert GLB_PATH.exists(), f"File {GLB_PATH} does not exist"

    script = (
        "import bpy, math\n"
        "bpy.ops.wm.read_factory_settings(use_empty=True)\n"
        "bpy.ops.import_scene.gltf(filepath=r'output/anime_mesh_clean.glb')\n"
        "objs = {o.name: o for o in bpy.context.scene.objects if o.type == 'MESH'}\n"
        "head = objs.get('Anime_Head')\n"
        "torso = objs.get('Anime_Torso')\n"
        "assert head is not None and torso is not None\n"
        "head_verts = {i: (head.matrix_world @ v.co, (head.matrix_world.to_3x3() @ v.normal).normalized()) for i, v in enumerate(head.data.vertices)}\n"
        "torso_verts = {i: (torso.matrix_world @ v.co, (torso.matrix_world.to_3x3() @ v.normal).normalized()) for i, v in enumerate(torso.data.vertices)}\n"
        "coincident = []\n"
        "for hi, (hco, hno) in head_verts.items():\n"
        "    for ti, (tco, tno) in torso_verts.items():\n"
        "        if (hco - tco).length < 1e-4:\n"
        "            dot = max(-1.0, min(1.0, hno.dot(tno)))\n"
        "            ang = math.acos(dot)\n"
        "            coincident.append((hi, ti, ang))\n"
        "print(f'GLB_COINCIDENT_PAIRS:{len(coincident)}')\n"
        "assert len(coincident) > 0, 'No coincident boundary vertices in GLB'\n"
        "max_dev = max(c[2] for c in coincident)\n"
        "violating = [c for c in coincident if c[2] >= 0.01]\n"
        "print(f'GLB_MAX_ANGULAR_DEVIATION_RAD:{max_dev:.6f}')\n"
        "print(f'GLB_VIOLATIONS_COUNT:{len(violating)}/{len(coincident)}')\n"
        "assert max_dev < 0.01, f'GLB Seam normal angular deviation {max_dev:.6f} rad exceeds 0.01 rad (failed on {len(violating)}/{len(coincident)} vertices)'\n"
        "print('PASS_GLB_SEAM_NORMAL_ALIGNMENT')\n"
    )

    cmd = [BLENDER_EXE, "--background", "--python-expr", script]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    print(res.stdout)
    assert res.returncode == 0, f"GLB Seam normal verification failed:\n{res.stderr}\n{res.stdout}"
    assert "PASS_GLB_SEAM_NORMAL_ALIGNMENT" in res.stdout

