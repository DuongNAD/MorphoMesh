"""
Independent Verification Script for M5 Vegetation Library
Executed by Reviewer 2.
"""
import io
import json
import math
from pathlib import Path
import struct
import sys
import numpy as np
from PIL import Image

OUTPUT_DIR = Path("E:/tool/mcp/MorphoMesh/teamwork_projects/vegetation_library/output")

def parse_glb(glb_path: Path):
    with open(glb_path, "rb") as f:
        header = f.read(12)
        magic, version, length = struct.unpack_from("<4sII", header, 0)
        assert magic == b"glTF", f"Invalid magic: {magic}"
        assert version == 2, f"Invalid version: {version}"
        
        c0_hdr = f.read(8)
        c0_len, c0_type = struct.unpack_from("<I4s", c0_hdr, 0)
        assert c0_type == b"JSON", f"Expected JSON chunk, got {c0_type}"
        json_bytes = f.read(c0_len)
        gltf = json.loads(json_bytes.decode("utf-8"))
        
        bin_bytes = b""
        c1_hdr = f.read(8)
        if len(c1_hdr) == 8:
            c1_len, c1_type = struct.unpack_from("<I4s", c1_hdr, 0)
            if c1_type.startswith(b"BIN"):
                bin_bytes = f.read(c1_len)
    return gltf, bin_bytes

def decode_positions(gltf, bin_bytes):
    accessors = gltf.get("accessors", [])
    buffer_views = gltf.get("bufferViews", [])
    
    positions_list = []
    for mesh in gltf.get("meshes", []):
        for prim in mesh.get("primitives", []):
            pos_idx = prim.get("attributes", {}).get("POSITION")
            if pos_idx is not None:
                acc = accessors[pos_idx]
                bv = buffer_views[acc["bufferView"]]
                offset = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
                count = acc["count"]
                raw = bin_bytes[offset : offset + count * 3 * 4]
                pos = np.frombuffer(raw, dtype=np.float32).reshape((count, 3))
                positions_list.append(pos)
    return np.vstack(positions_list) if positions_list else np.empty((0, 3), dtype=np.float32)

def audit_library():
    print(f"Auditing output directory: {OUTPUT_DIR}")
    assert OUTPUT_DIR.is_dir(), f"Output dir {OUTPUT_DIR} does not exist!"
    
    global_manifest_path = OUTPUT_DIR / "manifest.json"
    assert global_manifest_path.is_file(), "Global manifest.json missing!"
    with open(global_manifest_path, "r", encoding="utf-8") as f:
        global_manifest = json.load(f)
    
    assets_catalog = global_manifest.get("assets", {})
    print(f"Total assets in global manifest: {len(assets_catalog)}")
    
    glb_files = sorted(list(OUTPUT_DIR.rglob("*.glb")))
    print(f"Total GLB files found on disk: {len(glb_files)}")
    assert len(glb_files) == 35, f"Expected 35 GLBs, found {len(glb_files)}"
    
    audit_results = []
    failed_species = []
    
    for glb_path in glb_files:
        species_id = glb_path.stem
        species_dir = glb_path.parent
        
        # 1. Check all 13 required files
        req_files = [
            f"{species_id}.glb",
            f"{species_id}.obj",
            f"{species_id}.mtl",
            "asset_manifest.json",
            "textures/albedo.png",
            "textures/normal.png",
            "textures/roughness.png",
            "textures/metallic.png",
            "turntable_01.png",
            "turntable_02.png",
            "turntable_03.png",
            "turntable_04.png",
            "thumbnail.png"
        ]
        missing = []
        for rf in req_files:
            p = species_dir / rf
            if not p.is_file():
                missing.append(rf)
                
        # 2. GLB geometry & static mesh inspection
        gltf, bin_bytes = parse_glb(glb_path)
        
        # Check skins, animations, joints/weights, nodes
        skins = gltf.get("skins", [])
        has_skins = bool(skins)
        anims = gltf.get("animations", [])
        has_anims = bool(anims)
        
        has_joint_weight_attrs = False
        for mesh in gltf.get("meshes", []):
            for prim in mesh.get("primitives", []):
                for k in prim.get("attributes", {}).keys():
                    if k.upper().startswith("JOINTS") or k.upper().startswith("WEIGHTS"):
                        has_joint_weight_attrs = True
                        
        has_node_skins = any("skin" in node for node in gltf.get("nodes", []))
        n_bones = len(skins)
        
        # Decode positions
        pos = decode_positions(gltf, bin_bytes)
        n_verts = len(pos)
        
        has_nan_inf = bool(np.isnan(pos).any() or np.isinf(pos).any())
        extreme_coords = bool((np.abs(pos) >= 10000.0).any())
        
        z_min = float(pos[:, 2].min()) if n_verts > 0 else 0.0
        z_max = float(pos[:, 2].max()) if n_verts > 0 else 0.0
        y_min = float(pos[:, 1].min()) if n_verts > 0 else 0.0
        y_max = float(pos[:, 1].max()) if n_verts > 0 else 0.0
        
        # Contact centroid bottom 5%
        # Determine height along Z
        z_extent = z_max - z_min
        if z_extent > 1e-5:
            thresh = z_min + 0.05 * z_extent
            base_verts = pos[pos[:, 2] <= thresh]
            cx = float(np.mean(base_verts[:, 0]))
            cy = float(np.mean(base_verts[:, 1]))
            centroid_offset = math.sqrt(cx * cx + cy * cy)
        else:
            centroid_offset = 999.0
            
        # 3. Material & Texture fidelity
        tex_dir = species_dir / "textures"
        tex_ok = True
        tex_errors = []
        
        alb_mean, alb_std = 0.0, 0.0
        met_max, met_mean = 0.0, 0.0
        
        try:
            alb_img = Image.open(tex_dir / "albedo.png")
            alb_arr = np.array(alb_img.convert("RGB"), dtype=np.float32) / 255.0
            alb_mean = float(np.mean(alb_arr))
            alb_std = float(np.mean(np.std(alb_arr, axis=(0, 1))))
            if alb_mean <= 0.05:
                tex_errors.append(f"Albedo solid black: mean={alb_mean:.4f}")
            if alb_std <= 0.02:
                tex_errors.append(f"Albedo lack of variation: std={alb_std:.4f}")
                
            norm_img = Image.open(tex_dir / "normal.png")
            norm_arr = np.array(norm_img.convert("RGB"), dtype=np.float32) / 255.0
            nz = 2.0 * norm_arr[:, :, 2] - 1.0
            mean_nz = float(np.mean(nz))
            if not (0.5 <= mean_nz <= 1.0):
                tex_errors.append(f"Normal nz out of range: {mean_nz:.4f}")
                
            rough_img = Image.open(tex_dir / "roughness.png")
            rough_arr = np.array(rough_img.convert("L"), dtype=np.float32) / 255.0
            rough_mean = float(np.mean(rough_arr))
            if not (0.20 <= rough_mean <= 0.95):
                tex_errors.append(f"Roughness mean out of range: {rough_mean:.4f}")
                
            met_img = Image.open(tex_dir / "metallic.png")
            met_arr = np.array(met_img.convert("L"), dtype=np.float32) / 255.0
            met_max = float(np.max(met_arr))
            met_mean = float(np.mean(met_arr))
            if met_max > 0.05:
                tex_errors.append(f"Metallic exceeds dielectric ceiling: max={met_max:.4f}")
            if met_mean > 0.05:
                tex_errors.append(f"Metallic mean exceeds dielectric limit: mean={met_mean:.4f}")
        except Exception as e:
            tex_errors.append(f"Texture read error: {e}")
            
        tex_ok = (len(tex_errors) == 0)
        
        # Check criteria
        crit_bones = (n_bones == 0 and not has_skins and not has_anims and not has_joint_weight_attrs and not has_node_skins)
        crit_z_min = abs(z_min) <= 0.005
        crit_centroid = centroid_offset <= 0.05 + 1e-5
        crit_verts = (3000 <= n_verts <= 45000)
        crit_coords = (not has_nan_inf and not extreme_coords)
        crit_missing = (len(missing) == 0)
        
        all_passed = (crit_bones and crit_z_min and crit_centroid and crit_verts and crit_coords and crit_missing and tex_ok)
        
        if not all_passed:
            failed_species.append({
                "species_id": species_id,
                "crit_bones": crit_bones,
                "crit_z_min": crit_z_min,
                "z_min": z_min,
                "crit_centroid": crit_centroid,
                "centroid_offset": centroid_offset,
                "crit_verts": crit_verts,
                "n_verts": n_verts,
                "crit_coords": crit_coords,
                "missing": missing,
                "tex_errors": tex_errors
            })
            
        audit_results.append({
            "species_id": species_id,
            "category": species_dir.parent.name,
            "n_verts": n_verts,
            "z_min": round(z_min, 6),
            "z_max": round(z_max, 4),
            "centroid_offset": round(centroid_offset, 4),
            "n_bones": n_bones,
            "alb_mean": round(alb_mean, 4),
            "alb_std": round(alb_std, 4),
            "met_max": round(met_max, 4),
            "met_mean": round(met_mean, 4),
            "passed": all_passed
        })
        
    print(f"\n--- AUDIT COMPLETE ---")
    print(f"Total Species Audited: {len(audit_results)}")
    print(f"Passed: {len([r for r in audit_results if r['passed']])}")
    print(f"Failed: {len(failed_species)}")
    
    if failed_species:
        print("\nFailures:")
        for f in failed_species:
            print(f)
    else:
        print("\nAll 35 species passed ALL criteria!")
        
    # Save full audit log to JSON
    with open("E:/tool/mcp/MorphoMesh/.agents/m5_veg_reviewer_2/audit_summary.json", "w") as f:
        json.dump(audit_results, f, indent=2)
        
    return len(failed_species) == 0

if __name__ == "__main__":
    success = audit_library()
    sys.exit(0 if success else 1)
