#!/usr/bin/env python3
"""
MorphoMesh: Automated Bear Anatomy, Biomechanics & Armor Verification Suite.

Standalone programmatic inspection script executing both in native Python:
    python3 verify_bear_anatomy.py
and in headless Blender 5.2.1 LTS:
    /Applications/Blender.app/Contents/MacOS/Blender --background examples/Armored_War_Bear_HD.blend --python verify_bear_anatomy.py
    /Applications/Blender.app/Contents/MacOS/Blender --background --python verify_bear_anatomy.py

Rigorous Mathematical & Anatomical Assertions:
1. Claw Forward & Downward Curvature Guarantee:
   forall i in [0, 19]: dot(d_claw_i, (0, -1, 0)) > 0.60 and dz_i < 0.
2. Standardized Vertex Group Integrity:
   All 18 facial and anatomical vertex groups present and populated with non-zero vertices:
   'snout', 'nostrils', 'mouth_cavity', 'jaw', 'teeth', 'eyes', 'eyelids', 'ears',
   'claws_front', 'claws_hind', 'pads_front', 'pads_hind', 'torso', 'limbs', 'tail',
   'dorsal_spine', 'armor_mounts_shoulder', 'armor_mounts_wrist'.
3. Volumetric Fur Grooming:
   Active hair particle systems contain >= 10,000 parent guide strands;
   Fur_Density zero-fur mask vertices have strictly 0.0 density weight.
4. War Armor Clearance:
   All 6 armor plates maintain minimum Euclidean clearance d_min >= 0.015m from bear skin mesh,
   with 2-manifold closed shells and positive signed volumes.
5. Export Artifact Integrity:
   Validates existence and file size (> 500 KB) of examples/Armored_War_Bear_HD.blend and
   examples/Armored_War_Bear_HD.glb, plus all 4 beauty renders (> 50 KB each).

Returns exit code 0 on success, non-zero on assertion failure.
"""

from __future__ import annotations

import math
import os
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Project root resolution
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
EXAMPLES_DIR = PROJECT_ROOT / "examples"
RENDERS_DIR = EXAMPLES_DIR / "renders"

# Ensure user site-packages are available when running in Blender Python (3.13)
if sys.version_info >= (3, 13):
    user_site = "/Users/duongnad/.local/lib/python3.13/site-packages"
    if os.path.isdir(user_site) and user_site not in sys.path:
        sys.path.insert(0, user_site)
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

BLEND_PATH = EXAMPLES_DIR / "Armored_War_Bear_HD.blend"
GLB_PATH = EXAMPLES_DIR / "Armored_War_Bear_HD.glb"

REQUIRED_RENDERS = [
    "bear_front_three_quarter.png",
    "bear_head_closeup.png",
    "bear_paw_claws_closeup.png",
    "bear_full_body.png",
]

STANDARDIZED_VERTEX_GROUPS = (
    "snout",
    "nostrils",
    "mouth_cavity",
    "jaw",
    "teeth",
    "eyes",
    "eyelids",
    "ears",
    "claws_front",
    "claws_hind",
    "pads_front",
    "pads_hind",
    "torso",
    "limbs",
    "tail",
    "dorsal_spine",
    "armor_mounts_shoulder",
    "armor_mounts_wrist",
)

ZERO_FUR_GROUPS = (
    "snout",
    "nostrils",
    "mouth_cavity",
    "jaw",
    "teeth",
    "eyes",
    "eyelids",
    "claws_front",
    "claws_hind",
    "pads_front",
    "pads_hind",
)

ARMOR_OBJECTS = (
    "Armor_Pauldron_L",
    "Armor_Pauldron_R",
    "Armor_Gorget",
    "Armor_Bracer_L",
    "Armor_Bracer_R",
    "Armor_Backplate",
)


# Check if running inside Blender
INSIDE_BLENDER = False
try:
    import bpy
    INSIDE_BLENDER = True
except ImportError:
    INSIDE_BLENDER = False


class VerificationReport:
    """Collects and formats pass/fail assertions."""

    def __init__(self):
        self.passes: List[str] = []
        self.failures: List[str] = []

    def check(self, condition: bool, description: str, detail: str = ""):
        if condition:
            msg = f"[PASS] {description}"
            if detail:
                msg += f" ({detail})"
            self.passes.append(msg)
            print(msg)
        else:
            msg = f"[FAIL] {description}"
            if detail:
                msg += f" ({detail})"
            self.failures.append(msg)
            print(msg, file=sys.stderr)

    def summarize(self) -> int:
        print("\n" + "=" * 70)
        print(f"VERIFICATION SUMMARY: {len(self.passes)} PASSED, {len(self.failures)} FAILED")
        print("=" * 70)
        if self.failures:
            print("\nFAILED ASSERTIONS:")
            for f in self.failures:
                print(f"  {f}")
            return 1
        print("All anatomical, biomechanical, armor, and export assertions PASSED!")
        return 0


# ==============================================================================
# 1. STANDALONE PYTHON VERIFICATION (FILE ARTIFACTS & PROCEDURAL ENGINE)
# ==============================================================================

def verify_artifacts(report: VerificationReport):
    """Verifies existence and file size of all production deliverables."""
    print("\n--- 1. Production Artifacts & File Integrity ---")

    # .blend file
    blend_exists = BLEND_PATH.is_file()
    blend_size = BLEND_PATH.stat().st_size if blend_exists else 0
    report.check(
        blend_exists and blend_size > 500 * 1024,
        "Master Scene .blend Artifact",
        f"{BLEND_PATH} size: {blend_size:,} bytes (> 500 KB required)" if blend_exists else "File NOT found",
    )

    # .glb file
    glb_exists = GLB_PATH.is_file()
    glb_size = GLB_PATH.stat().st_size if glb_exists else 0
    report.check(
        glb_exists and glb_size > 500 * 1024,
        "Production Export .glb Artifact",
        f"{GLB_PATH} size: {glb_size:,} bytes (> 500 KB required)" if glb_exists else "File NOT found",
    )

    # Validate glTF 2.0 structure
    if glb_exists and glb_size >= 12:
        try:
            with open(GLB_PATH, "rb") as f:
                magic, version, length = struct.unpack("<4sII", f.read(12))
                is_valid_gltf = (magic == b"glTF" and version == 2 and length == glb_size)
                report.check(
                    is_valid_gltf,
                    "glTF 2.0 Binary Header Validation",
                    f"magic={magic!r}, version={version}, declared_len={length:,}, actual_size={glb_size:,}",
                )
        except Exception as e:
            report.check(False, "glTF 2.0 Header Parsing", str(e))

    # Beauty renders
    print("\n--- 2. Cycles Beauty Renders ---")
    for render_name in REQUIRED_RENDERS:
        r_path = RENDERS_DIR / render_name
        r_exists = r_path.is_file()
        r_size = r_path.stat().st_size if r_exists else 0
        report.check(
            r_exists and r_size > 50 * 1024,
            f"Beauty Render: {render_name}",
            f"size: {r_size:,} bytes (> 50 KB required)" if r_exists else "File NOT found",
        )


def point_to_triangle_sq_dist(
    p: Sequence[float], a: Sequence[float], b: Sequence[float], c: Sequence[float]
) -> float:
    """Computes minimum squared Euclidean distance from point p to 3D triangle (a, b, c)."""
    ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    ac = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    ap = (p[0] - a[0], p[1] - a[1], p[2] - a[2])
    d1 = ab[0] * ap[0] + ab[1] * ap[1] + ab[2] * ap[2]
    d2 = ac[0] * ap[0] + ac[1] * ap[1] + ac[2] * ap[2]
    if d1 <= 0.0 and d2 <= 0.0:
        return ap[0] ** 2 + ap[1] ** 2 + ap[2] ** 2
    bp = (p[0] - b[0], p[1] - b[1], p[2] - b[2])
    d3 = ab[0] * bp[0] + ab[1] * bp[1] + ab[2] * bp[2]
    d4 = ac[0] * bp[0] + ac[1] * bp[1] + ac[2] * bp[2]
    if d3 >= 0.0 and d4 <= d3:
        return bp[0] ** 2 + bp[1] ** 2 + bp[2] ** 2
    vc = d1 * d4 - d3 * d2
    if vc <= 0.0 and d1 >= 0.0 and d3 <= 0.0:
        v = d1 / (d1 - d3)
        return (a[0] + v * ab[0] - p[0]) ** 2 + (a[1] + v * ab[1] - p[1]) ** 2 + (a[2] + v * ab[2] - p[2]) ** 2
    cp = (p[0] - c[0], p[1] - c[1], p[2] - c[2])
    d5 = ab[0] * cp[0] + ab[1] * cp[1] + ab[2] * cp[2]
    d6 = ac[0] * cp[0] + ac[1] * cp[1] + ac[2] * cp[2]
    if d6 >= 0.0 and d5 <= d6:
        return cp[0] ** 2 + cp[1] ** 2 + cp[2] ** 2
    vb = d5 * d2 - d1 * d6
    if vb <= 0.0 and d2 >= 0.0 and d6 <= 0.0:
        w = d2 / (d2 - d6)
        return (a[0] + w * ac[0] - p[0]) ** 2 + (a[1] + w * ac[1] - p[1]) ** 2 + (a[2] + w * ac[2] - p[2]) ** 2
    va = d3 * d6 - d5 * d4
    if va <= 0.0 and (d4 - d3) >= 0.0 and (d5 - d6) >= 0.0:
        w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        return (b[0] + w * (c[0] - b[0]) - p[0]) ** 2 + (b[1] + w * (c[1] - b[1]) - p[1]) ** 2 + (b[2] + w * (c[2] - b[2]) - p[2]) ** 2
    denom = 1.0 / (va + vb + vc)
    v = vb * denom
    w = vc * denom
    return (a[0] + ab[0] * v + ac[0] * w - p[0]) ** 2 + (a[1] + ab[1] * v + ac[1] * w - p[1]) ** 2 + (a[2] + ab[2] * v + ac[2] * w - p[2]) ** 2


def verify_procedural_engine(report: VerificationReport):
    """Verifies procedural generator math and vertex group definitions via src/morphomesh/."""
    print("\n--- 3. Procedural Anatomy Engine & Biomechanics ---")

    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))

    try:
        from morphomesh.creature_generator import generate_bear_base_mesh
        from morphomesh.grooming import CreatureGroomingEngine
        from morphomesh.materials import CreaturePBRSuite, STANDARD_PBR_MATERIALS
        from morphomesh.armor import ProceduralArmorEngine

        # Generate base mesh
        res = generate_bear_base_mesh()
        report.check(
            res.is_anatomically_valid,
            "Procedural Anatomy Synthesis",
            f"archetype={res.archetype}, verts={len(res.mesh.vertices)}, faces={len(res.mesh.faces)}",
        )

        # Assert all 20 claws
        report.check(len(res.claws) == 20, "20 Functional Claws Synthesized", f"count={len(res.claws)}")
        all_claws_forward = all(c.forward_dot > 0.60 for c in res.claws)
        all_claws_downward = all(c.downward_pitch < 0.0 for c in res.claws)
        min_fwd = min(c.forward_dot for c in res.claws) if res.claws else 0.0
        max_dz = max(c.downward_pitch for c in res.claws) if res.claws else 0.0
        report.check(
            all_claws_forward,
            "All 20 Claws Forward Curvature (dot > 0.60)",
            f"min forward dot = {min_fwd:.4f} > 0.60",
        )
        report.check(
            all_claws_downward,
            "All 20 Claws Downward Pitch (dz < 0)",
            f"max dz = {max_dz:.4f} < 0",
        )

        # Assert all 18 standardized vertex groups
        report.check(
            len(res.vertex_groups) == 18,
            "18 Standardized Vertex Groups Present",
            f"groups={list(res.vertex_groups.keys())}",
        )
        empty_vgs = [k for k, v in res.vertex_groups.items() if len(v) == 0]
        report.check(
            len(empty_vgs) == 0,
            "All 18 Vertex Groups Populated (Non-Zero Counts)",
            f"empty groups: {empty_vgs}" if empty_vgs else "All 18 non-empty",
        )

        # Assert Volumetric Fur specs
        grooming = CreatureGroomingEngine()
        spec = grooming.setup_volumetric_fur("Bear_Base_Mesh")
        report.check(
            spec["total_parent_strands"] >= 10000,
            "Volumetric Fur Strand Count (>= 10,000 guide strands)",
            f"total parent strands = {spec['total_parent_strands']:,} >= 10,000",
        )
        report.check(
            spec["total_render_strands"] > 100000,
            "Volumetric Fur Render Density (> 100,000 render strands)",
            f"total render strands = {spec['total_render_strands']:,} > 100,000",
        )

        # Assert PBR Materials
        report.check(
            len(STANDARD_PBR_MATERIALS) == 5,
            "5 Principled BSDF v2 PBR Materials Present",
            f"mats={list(STANDARD_PBR_MATERIALS.keys())}",
        )

        # Assert Armor Clearance Math
        armor = ProceduralArmorEngine()
        b_triangles = []
        for f in res.mesh.faces:
            vs = [res.mesh.vertices[idx] for idx in f]
            if any(v[2] >= 0.70 for v in vs):
                for k in range(1, len(f) - 1):
                    b_triangles.append((vs[0], vs[k], vs[k + 1]))

        for side in ["L", "R"]:
            p = armor.generate_pauldron(side)
            is_m, nm = armor.verify_2_manifold(p)
            report.check(
                is_m and nm == 0,
                f"Procedural Pauldron {side} Watertight 2-Manifold",
                f"non-manifold edge count = {nm}",
            )
            vol = sum(
                (p.vertices[f[0]][0] * (p.vertices[f[k]][1] * p.vertices[f[k+1]][2] - p.vertices[f[k]][2] * p.vertices[f[k+1]][1])
                 + p.vertices[f[0]][1] * (p.vertices[f[k]][2] * p.vertices[f[k+1]][0] - p.vertices[f[k]][0] * p.vertices[f[k+1]][2])
                 + p.vertices[f[0]][2] * (p.vertices[f[k]][0] * p.vertices[f[k+1]][1] - p.vertices[f[k]][1] * p.vertices[f[k+1]][0])) / 6.0
                for f in p.faces for k in range(1, len(f) - 1)
            )
            report.check(
                vol > 0.0,
                f"Procedural Pauldron {side} Positive Signed Volume",
                f"signed volume = {vol:.6f} m^3 > 0",
            )
            min_sq = min(min(point_to_triangle_sq_dist(v, tri[0], tri[1], tri[2]) for tri in b_triangles) for v in p.vertices)
            min_d = math.sqrt(min_sq)
            report.check(
                min_d >= 0.015,
                f"Procedural Pauldron {side} Surface Clearance (>= 0.015m)",
                f"measured minimum clearance d_min = {min_d:.4f}m >= 0.015m",
            )

    except Exception as e:
        report.check(False, "Procedural Generator Verification Exception", str(e))


# ==============================================================================
# 2. HEADLESS BLENDER SCENE INSPECTION (BPY MODE)
# ==============================================================================

def verify_blender_scene(report: VerificationReport):
    """Inspects live Blender scene (or loaded .blend) via bpy."""
    print("\n--- 4. Blender 5.2.1 LTS Scene Topology & Clearance Audit ---")

    # If Armored_War_Bear_HD.blend exists and not already loaded, open it
    if BLEND_PATH.is_file():
        current_file = bpy.data.filepath
        if not current_file or Path(current_file).resolve() != BLEND_PATH.resolve():
            try:
                bpy.ops.wm.open_mainfile(filepath=str(BLEND_PATH))
                print(f"Loaded master scene: {BLEND_PATH}")
            except Exception as e:
                print(f"Note: Could not reopen file ({e}), auditing active Blender scene.")

    # 1. Bear Base Mesh
    bear_obj = bpy.data.objects.get("Bear_Base_Mesh")
    report.check(bear_obj is not None, "Object 'Bear_Base_Mesh' Exists in Scene")
    if not bear_obj or bear_obj.type != "MESH":
        report.check(False, "Bear_Base_Mesh is valid mesh", "Object missing or not a mesh")
        return

    m_data = bear_obj.data
    report.check(
        len(m_data.vertices) >= 2000,
        "Bear_Base_Mesh Vertex Count",
        f"count = {len(m_data.vertices):,} vertices",
    )
    report.check(
        len(m_data.polygons) >= 3000,
        "Bear_Base_Mesh Polygon Count",
        f"count = {len(m_data.polygons):,} polygons",
    )

    # 2. All 18 Vertex Groups
    vgs_in_obj = {vg.name: vg for vg in bear_obj.vertex_groups}
    missing_vgs = [vg for vg in STANDARDIZED_VERTEX_GROUPS if vg not in vgs_in_obj]
    report.check(
        len(missing_vgs) == 0,
        "All 18 Standardized Vertex Groups Exist in Bear_Base_Mesh",
        f"missing: {missing_vgs}" if missing_vgs else "All 18 present",
    )

    empty_blender_vgs = []
    for vg_name in STANDARDIZED_VERTEX_GROUPS:
        if vg_name in vgs_in_obj:
            vg = vgs_in_obj[vg_name]
            v_count = 0
            for v in m_data.vertices:
                try:
                    if vg.weight(v.index) > 0.0:
                        v_count += 1
                except Exception:
                    pass
            if v_count == 0:
                empty_blender_vgs.append(vg_name)
    report.check(
        len(empty_blender_vgs) == 0,
        "All 18 Vertex Groups Populated in Blender Scene",
        f"empty: {empty_blender_vgs}" if empty_blender_vgs else "All 18 have non-zero assigned vertices",
    )

    # 3. Volumetric Fur Particle Systems
    psys_list = list(bear_obj.particle_systems)
    tot_guide_strands = sum(ps.settings.count for ps in psys_list if ps.settings.type == "HAIR")
    report.check(
        len(psys_list) >= 2,
        "Multi-layer Volumetric Fur Particle Systems Present",
        f"systems: {[ps.name for ps in psys_list]}",
    )
    report.check(
        tot_guide_strands >= 10000,
        "Volumetric Fur Guide Strand Count (>= 10,000)",
        f"total guide strands = {tot_guide_strands:,} >= 10,000",
    )

    # Zero-fur density mask verification
    vg_density = vgs_in_obj.get("Fur_Density")
    if vg_density:
        zero_indices = set()
        for zg in ZERO_FUR_GROUPS:
            if zg in vgs_in_obj:
                gid = vgs_in_obj[zg].index
                for v in m_data.vertices:
                    for g in v.groups:
                        if g.group == gid and g.weight > 0.1:
                            zero_indices.add(v.index)

        non_zero_in_mask = []
        for v_idx in zero_indices:
            try:
                w = vg_density.weight(v_idx)
                if w > 0.001:
                    non_zero_in_mask.append((v_idx, w))
            except Exception:
                pass

        report.check(
            len(non_zero_in_mask) == 0,
            "Zero-Fur Density Mask Integrity (Snout, Claws, Pads have 0.0 fur)",
            f"{len(non_zero_in_mask)} vertices have non-zero fur density" if non_zero_in_mask else "Strictly 0.0 on naked features",
        )
    else:
        report.check(False, "Fur_Density Vertex Group Present", "Missing Fur_Density group")

    # 4. Fur Ribbon Mesh
    ribbon_obj = bpy.data.objects.get("Bear_Fur_Ribbons") or bpy.data.objects.get("Bear_Base_Mesh_Fur_Ribbons")
    report.check(ribbon_obj is not None, "Evaluated Fur Ribbon Mesh Exists (Bear_Fur_Ribbons)")
    if ribbon_obj:
        report.check(
            len(ribbon_obj.data.vertices) >= 5000,
            "Fur Ribbon Mesh Polygon Density",
            f"verts={len(ribbon_obj.data.vertices):,}, faces={len(ribbon_obj.data.polygons):,}",
        )
        has_uv = len(ribbon_obj.data.uv_layers) > 0
        report.check(has_uv, "Fur Ribbon Mesh UV Texture Coordinates Present", f"UV layers={len(ribbon_obj.data.uv_layers)}")

    # 5. War Armor Plates & BVH Surface Clearance >= 0.015m + Zero Penetration
    from mathutils.bvhtree import BVHTree
    bear_coords = [v.co for v in m_data.vertices]
    bear_faces = [p.vertices for p in m_data.polygons]
    bear_bvh = BVHTree.FromPolygons(bear_coords, bear_faces)

    for a_name in ARMOR_OBJECTS:
        ao = bpy.data.objects.get(a_name)
        report.check(ao is not None, f"War Armor Plate Exists: {a_name}")
        if ao and ao.type == "MESH":
            # True BVH point-to-surface distance and signed penetration audit
            min_surface_dist = float("inf")
            inside_vertices = []
            signed_distances = []
            for v in ao.data.vertices:
                loc, norm, face_idx, dist = bear_bvh.find_nearest(v.co)
                if loc is not None:
                    signed_dist = (v.co - loc).dot(norm)
                    signed_distances.append(signed_dist)
                    if signed_dist < -0.001:
                        inside_vertices.append((v.index, v.co, signed_dist))
                    if dist < min_surface_dist:
                        min_surface_dist = dist

            report.check(
                min_surface_dist >= 0.015,
                f"Armor Plate Surface Clearance: {a_name} (>= 0.015m)",
                f"measured minimum surface clearance d_min = {min_surface_dist:.4f}m >= 0.015m",
            )
            report.check(
                len(inside_vertices) == 0,
                f"Armor Plate Non-Penetrating (0 Inside Vertices): {a_name}",
                f"inside count = {len(inside_vertices)}, min signed dist = {min(signed_distances):.4f}m" if signed_distances else "N/A",
            )
            # Watertightness / 2-manifold check
            import bmesh
            bm = bmesh.new()
            bm.from_mesh(ao.data)
            nm_edges = sum(1 for e in bm.edges if len(e.link_faces) != 2)
            bm.free()
            report.check(
                nm_edges == 0,
                f"Armor Plate 2-Manifold Watertight: {a_name}",
                f"non-manifold edge count = {nm_edges}",
            )
            # Positive signed volume check
            vol = 0.0
            for p in ao.data.polygons:
                v0 = ao.data.vertices[p.vertices[0]].co
                for k in range(1, len(p.vertices) - 1):
                    v1 = ao.data.vertices[p.vertices[k]].co
                    v2 = ao.data.vertices[p.vertices[k + 1]].co
                    vol += v0.dot(v1.cross(v2)) / 6.0
            report.check(
                vol > 0.0,
                f"Armor Plate Positive Signed Volume: {a_name}",
                f"signed volume = {vol:.6f} m^3 > 0",
            )

    # 6. Materials Assigned
    report.check(
        len(bear_obj.data.materials) >= 5,
        "Bear_Base_Mesh 5 Material Slots Assigned",
        f"materials={[m.name for m in bear_obj.data.materials]}",
    )


# ==============================================================================
# MAIN ENTRYPOINT
# ==============================================================================

def main() -> int:
    report = VerificationReport()
    print("=" * 70)
    print("MORPHOMESH: ARMORED WAR BEAR AUTOMATED ANATOMY VERIFICATION SUITE")
    print("=" * 70)

    if INSIDE_BLENDER:
        print("[Execution Environment: Blender 5.2.1 LTS Headless Runtime]")
        verify_artifacts(report)
        verify_procedural_engine(report)
        verify_blender_scene(report)
    else:
        print("[Execution Environment: Standalone Python 3 Runtime]")
        verify_artifacts(report)
        verify_procedural_engine(report)

        # If Blender binary is available, run headless Blender verification pass
        blender_bin = "/Applications/Blender.app/Contents/MacOS/Blender"
        if os.path.isfile(blender_bin) and BLEND_PATH.is_file():
            print("\n--- 5. Invoking Headless Blender Scene Verification Pass ---")
            cmd = [blender_bin, "--background", str(BLEND_PATH), "--python", str(__file__)]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            report.check(
                proc.returncode == 0,
                "Headless Blender Full Scene Verification Pass",
                f"exit_code={proc.returncode}",
            )
            if proc.returncode != 0:
                print("Blender STDERR:\n", proc.stderr)
                print("Blender STDOUT:\n", proc.stdout)

    return report.summarize()


if __name__ == "__main__":
    sys.exit(main())
