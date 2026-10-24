"""
Empirical Adversarial Stress Test Suite for Milestone 3 (M3)
Vegetation Asset Post-Processing, Normalization & Multi-Format Export

Author: Challenger 2 (m3_veg_challenger_2)
Execution: uv run python test_m3_empirical_stress.py
"""
import io
import json
from pathlib import Path
import struct
import sys
import time
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
VEG_ROOT = REPO_ROOT / "teamwork_projects" / "vegetation_library"
SRC_ROOT = REPO_ROOT / "src"
if str(VEG_ROOT) not in sys.path:
    sys.path.insert(0, str(VEG_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import numpy as np
from PIL import Image

from morphomesh.geometry.mesh import MeshGeometry
from vegetation_pipeline.catalog import get_species
from vegetation_pipeline.generator import ProceduralBotanicalGenerator
from vegetation_pipeline.post_processor import (
    AssetPostProcessor,
    ExportedAsset,
    extract_textures_from_glb,
    load_mesh_from_glb,
    snap_ground_pivot_and_center,
)

# 7 Botanical Biome Representative Species
BIOME_REPRESENTATIVES: Dict[str, str] = {
    "broadleaf_deciduous_trees": "veg_tree_oak_01",
    "conifers_evergreens": "veg_conifer_pine_01",
    "tropical_foliage_palms": "veg_tropical_palm_01",
    "flowering_shrubs_ornamentals": "veg_shrub_rose_01",
    "ferns_grasses_groundcover": "veg_ground_fern_01",
    "succulents_cacti": "veg_succulent_saguaro_01",
    "climbing_vines_epiphytes": "veg_vine_ivy_01",
}

OUTPUT_ROOT = Path("E:/tool/mcp/MorphoMesh/.agents/m3_veg_challenger_2/empirical_test_output")


class TestFailure(Exception):
    pass


class TestReporter:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors: List[Tuple[str, str]] = []
        self.records: List[Dict[str, Any]] = []

    def assert_true(self, condition: bool, test_name: str, message: str):
        if condition:
            self.passed += 1
            print(f"  [PASS] {test_name}: {message}")
        else:
            self.failed += 1
            err_msg = f"[FAIL] {test_name}: {message}"
            print(f"  {err_msg}")
            self.errors.append((test_name, message))
            raise TestFailure(err_msg)

    def summary(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "failed": self.failed,
            "total": self.passed + self.failed,
            "errors": self.errors,
        }


def parse_raw_glb(glb_path: Path) -> Tuple[Dict[str, Any], bytes, Dict[str, Any]]:
    """Strict low-level binary parser for glTF 2.0 GLB containers."""
    file_bytes = glb_path.read_bytes()
    file_len = len(file_bytes)
    
    if file_len < 12:
        raise ValueError(f"GLB container too small for header: {file_len} bytes")
    
    magic, version, declared_len = struct.unpack_from("<4sII", file_bytes, 0)
    
    header_info = {
        "magic": magic,
        "version": version,
        "declared_length": declared_len,
        "actual_file_length": file_len,
    }
    
    # Parse Chunk 0 (JSON)
    if declared_len > file_len:
        raise ValueError(f"Declared GLB length ({declared_len}) exceeds file size ({file_len})")
    
    c0_len, c0_type = struct.unpack_from("<I4s", file_bytes, 12)
    c0_data = file_bytes[20 : 20 + c0_len]
    
    gltf_json = json.loads(c0_data.decode("utf-8").strip())
    
    # Parse Chunk 1 (BIN)
    c1_offset = 20 + c0_len
    if c1_offset + 8 <= file_len:
        c1_len, c1_type = struct.unpack_from("<I4s", file_bytes, c1_offset)
        c1_data = file_bytes[c1_offset + 8 : c1_offset + 8 + c1_len]
    else:
        c1_len, c1_type, c1_data = 0, b"", b""

    chunks_info = {
        "chunk0_len": c0_len,
        "chunk0_type": c0_type,
        "chunk0_aligned_4": (c0_len % 4 == 0),
        "chunk1_offset": c1_offset,
        "chunk1_len": c1_len,
        "chunk1_type": c1_type,
        "chunk1_aligned_4": (c1_len % 4 == 0),
    }
    
    return gltf_json, c1_data, {**header_info, **chunks_info}


def parse_obj_file(obj_path: Path) -> Dict[str, Any]:
    """Parse Wavefront OBJ geometry and verify 1-indexing."""
    vertices = []
    normals = []
    uvs = []
    faces = []
    mtllib = None
    usemtl = None
    o_name = None
    
    with open(obj_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            cmd = parts[0]
            
            if cmd == "mtllib":
                mtllib = parts[1] if len(parts) > 1 else None
            elif cmd == "usemtl":
                usemtl = parts[1] if len(parts) > 1 else None
            elif cmd == "o":
                o_name = parts[1] if len(parts) > 1 else None
            elif cmd == "v":
                vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
            elif cmd == "vn":
                normals.append([float(parts[1]), float(parts[2]), float(parts[3])])
            elif cmd == "vt":
                uvs.append([float(parts[1]), float(parts[2])])
            elif cmd == "f":
                face_v_indices = []
                for token in parts[1:]:
                    elems = token.split("/")
                    v_idx = int(elems[0])
                    # Strict 1-index assertion
                    if v_idx <= 0:
                        raise ValueError(f"Zero or negative 1-index found in OBJ face at line {line_num}: {token}")
                    face_v_indices.append(v_idx)
                faces.append(face_v_indices)

    v_arr = np.array(vertices, dtype=np.float32) if vertices else np.empty((0, 3), dtype=np.float32)
    
    all_v_indices = [idx for face in faces for idx in face]
    
    return {
        "vertices": v_arr,
        "vertex_count": len(vertices),
        "normal_count": len(normals),
        "uv_count": len(uvs),
        "face_count": len(faces),
        "min_v_idx": min(all_v_indices) if all_v_indices else 0,
        "max_v_idx": max(all_v_indices) if all_v_indices else 0,
        "mtllib": mtllib,
        "usemtl": usemtl,
        "object_name": o_name,
        "min_coords": v_arr.min(axis=0).tolist() if len(v_arr) > 0 else [0, 0, 0],
        "max_coords": v_arr.max(axis=0).tolist() if len(v_arr) > 0 else [0, 0, 0],
    }


def parse_mtl_file(mtl_path: Path) -> Dict[str, Any]:
    """Parse Wavefront MTL material library."""
    materials = {}
    current_mat = None
    
    with open(mtl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(maxsplit=1)
            cmd = parts[0]
            val = parts[1] if len(parts) > 1 else ""
            
            if cmd == "newmtl":
                current_mat = val
                materials[current_mat] = {}
            elif current_mat:
                materials[current_mat][cmd] = val
                
    return materials


# ==============================================================================
# EMPIRICAL STRESS TEST SUITE
# ==============================================================================

def run_empirical_stress_tests():
    reporter = TestReporter()
    generator = ProceduralBotanicalGenerator()
    processor = AssetPostProcessor()
    
    print("=" * 80)
    print("STARTING EMPIRICAL ADVERSARIAL STRESS TEST SUITE (M3)")
    print(f"Output Directory: {OUTPUT_ROOT}")
    print("=" * 80)
    
    generated_assets: Dict[str, ExportedAsset] = {}
    
    # STEP 1: Generate & Post-Process All 7 Biome Species
    print("\n--- [STAGE 1] Generating and Post-Processing 7 Botanical Biome Assets ---")
    for biome_cat, species_id in BIOME_REPRESENTATIVES.items():
        t0 = time.time()
        species = get_species(species_id)
        raw_asset = generator.generate(species)
        exported = processor.process_asset(raw_asset, species, output_dir=OUTPUT_ROOT)
        dt = time.time() - t0
        
        generated_assets[species_id] = exported
        reporter.assert_true(
            exported.is_valid(),
            f"AssetGeneration[{species_id}]",
            f"Successfully generated & exported in {dt:.2f}s, is_valid() == True"
        )
        reporter.assert_true(
            exported.glb_path.is_file(),
            f"FileExistence[{species_id}.glb]",
            f"GLB exists at {exported.glb_path.relative_to(OUTPUT_ROOT)}"
        )
        reporter.assert_true(
            exported.obj_path.is_file() and exported.mtl_path.is_file(),
            f"FileExistence[{species_id}.obj/mtl]",
            f"OBJ & MTL exist at {exported.obj_path.name}, {exported.mtl_path.name}"
        )
        reporter.assert_true(
            exported.manifest_path.is_file(),
            f"FileExistence[{species_id}/manifest]",
            f"Manifest exists at {exported.manifest_path.name}"
        )

    # STEP 2: Production GLB Binary Container Stress
    print("\n--- [STAGE 2] Production GLB Binary Container Stress Testing ---")
    for biome_cat, species_id in BIOME_REPRESENTATIVES.items():
        exported = generated_assets[species_id]
        glb_path = exported.glb_path
        
        # 1. Header stress
        gltf_json, bin_data, meta = parse_raw_glb(glb_path)
        
        reporter.assert_true(
            meta["magic"] == b"glTF",
            f"GLBHeaderMagic[{species_id}]",
            f"Magic matches b'glTF' exactly (got {meta['magic']})"
        )
        reporter.assert_true(
            meta["version"] == 2,
            f"GLBHeaderVersion[{species_id}]",
            f"glTF Version == 2 (got {meta['version']})"
        )
        reporter.assert_true(
            meta["declared_length"] == meta["actual_file_length"],
            f"GLBHeaderLength[{species_id}]",
            f"Header length ({meta['declared_length']}) equals file length ({meta['actual_file_length']})"
        )
        
        # 2. 4-byte chunk boundary alignment
        reporter.assert_true(
            meta["chunk0_aligned_4"],
            f"GLBChunk0Alignment[{species_id}]",
            f"JSON Chunk 0 length ({meta['chunk0_len']}) is 4-byte aligned"
        )
        reporter.assert_true(
            meta["chunk0_type"] == b"JSON",
            f"GLBChunk0Type[{species_id}]",
            f"Chunk 0 type is b'JSON' (got {meta['chunk0_type']})"
        )
        reporter.assert_true(
            meta["chunk1_aligned_4"],
            f"GLBChunk1Alignment[{species_id}]",
            f"BIN Chunk 1 length ({meta['chunk1_len']}) is 4-byte aligned"
        )
        reporter.assert_true(
            meta["chunk1_type"] == b"BIN\x00",
            f"GLBChunk1Type[{species_id}]",
            f"Chunk 1 type is b'BIN\\x00' (got {meta['chunk1_type']})"
        )
        
        # 3. Static Mesh / Zero-Armature Verification (N_bones = 0)
        has_skins = "skins" in gltf_json and len(gltf_json["skins"]) > 0
        has_anims = "animations" in gltf_json and len(gltf_json["animations"]) > 0
        reporter.assert_true(
            not has_skins,
            f"GLBZeroSkins[{species_id}]",
            "'skins' field omitted or empty (N_bones = 0)"
        )
        reporter.assert_true(
            not has_anims,
            f"GLBZeroAnimations[{species_id}]",
            "'animations' field omitted or empty"
        )
        
        # Verify no JOINTS_ or WEIGHTS_ in attributes
        for m_idx, mesh in enumerate(gltf_json.get("meshes", [])):
            for p_idx, prim in enumerate(mesh.get("primitives", [])):
                attrs = prim.get("attributes", {})
                joint_attrs = [k for k in attrs if k.startswith("JOINTS_") or k.startswith("WEIGHTS_")]
                reporter.assert_true(
                    len(joint_attrs) == 0,
                    f"GLBNoRiggingAttributes[{species_id}:m{m_idx}:p{p_idx}]",
                    f"No JOINTS_ or WEIGHTS_ attributes found (found {joint_attrs})"
                )
                
        # 4. Foliage Material doubleSided: True
        materials = gltf_json.get("materials", [])
        reporter.assert_true(
            len(materials) > 0,
            f"GLBMaterialsPresent[{species_id}]",
            f"At least 1 material defined (found {len(materials)})"
        )
        for m_idx, mat in enumerate(materials):
            reporter.assert_true(
                mat.get("doubleSided") is True,
                f"GLBDoubleSidedFoliage[{species_id}:mat_{mat.get('name')}]",
                f"Material {mat.get('name')} has doubleSided == True"
            )
            
        # 5. Embedded PNG Textures in bufferViews
        images = gltf_json.get("images", [])
        buffer_views = gltf_json.get("bufferViews", [])
        reporter.assert_true(
            len(images) >= 4,
            f"GLBEmbeddedImageCount[{species_id}]",
            f"At least 4 PBR texture images embedded (found {len(images)})"
        )
        
        png_magic = b"\x89PNG\r\n\x1a\n"
        for img in images:
            img_name = img.get("name")
            bv_idx = img.get("bufferView")
            mime = img.get("mimeType")
            reporter.assert_true(
                mime == "image/png",
                f"GLBImageMime[{species_id}:{img_name}]",
                f"Image mimeType is image/png (got {mime})"
            )
            bv = buffer_views[bv_idx]
            b_offset = bv.get("byteOffset", 0)
            b_len = bv.get("byteLength", 0)
            
            # Verify 4-byte alignment of bufferView
            reporter.assert_true(
                b_offset % 4 == 0,
                f"GLBBufferViewOffsetAlignment[{species_id}:bv{bv_idx}]",
                f"BufferView {bv_idx} byteOffset {b_offset} is 4-byte aligned"
            )
            
            img_raw = bin_data[b_offset : b_offset + b_len]
            reporter.assert_true(
                img_raw.startswith(png_magic),
                f"GLBPngMagicHeader[{species_id}:{img_name}]",
                "Image buffer starts with valid PNG magic header \\x89PNG"
            )
            
            # Verify decodable by PIL and dimensions >= 256x256
            pil_img = Image.open(io.BytesIO(img_raw))
            reporter.assert_true(
                pil_img.width >= 256 and pil_img.height >= 256,
                f"GLBPngImageDecodable[{species_id}:{img_name}]",
                f"Image decodable, valid dimensions {pil_img.size}"
            )

    # STEP 3: Wavefront OBJ / MTL Stress Testing
    print("\n--- [STAGE 3] Wavefront OBJ / MTL Multi-Format Stress Testing ---")
    for biome_cat, species_id in BIOME_REPRESENTATIVES.items():
        exported = generated_assets[species_id]
        obj_path = exported.obj_path
        mtl_path = exported.mtl_path
        
        # 1. OBJ syntax, 1-indexing, mtllib reference
        obj_data = parse_obj_file(obj_path)
        reporter.assert_true(
            obj_data["vertex_count"] > 0,
            f"OBJVertexCount[{species_id}]",
            f"OBJ contains {obj_data['vertex_count']} vertices"
        )
        reporter.assert_true(
            obj_data["face_count"] > 0,
            f"OBJFaceCount[{species_id}]",
            f"OBJ contains {obj_data['face_count']} faces"
        )
        reporter.assert_true(
            obj_data["mtllib"] == mtl_path.name,
            f"OBJMtllibReference[{species_id}]",
            f"OBJ references mtllib '{obj_data['mtllib']}' matching {mtl_path.name}"
        )
        reporter.assert_true(
            obj_data["usemtl"] == f"M_{species_id}",
            f"OBJUseMtlReference[{species_id}]",
            f"OBJ references usemtl '{obj_data['usemtl']}' matching M_{species_id}"
        )
        reporter.assert_true(
            obj_data["min_v_idx"] == 1,
            f"OBJFaceIndexMin1[{species_id}]",
            f"All face vertex indices are strictly 1-indexed (min index = {obj_data['min_v_idx']})"
        )
        reporter.assert_true(
            obj_data["max_v_idx"] == obj_data["vertex_count"],
            f"OBJFaceIndexMaxMatches[{species_id}]",
            f"Max face index ({obj_data['max_v_idx']}) equals vertex count ({obj_data['vertex_count']})"
        )
        
        # 2. MTL syntax and relative texture paths
        mtl_data = parse_mtl_file(mtl_path)
        expected_mat = f"M_{species_id}"
        reporter.assert_true(
            expected_mat in mtl_data,
            f"MTLMaterialDefined[{species_id}]",
            f"Material {expected_mat} defined in MTL file"
        )
        mat_entry = mtl_data[expected_mat]
        
        # Check relative texture links
        expected_texture_channels = {
            "map_Kd": "textures/albedo.png",
            "norm": "textures/normal.png",
            "map_Pr": "textures/roughness.png",
            "map_Pm": "textures/metallic.png",
        }
        for key, expected_rel in expected_texture_channels.items():
            link_val = mat_entry.get(key)
            reporter.assert_true(
                link_val is not None and expected_rel in link_val,
                f"MTLRelativeTextureLink[{species_id}:{key}]",
                f"{key} binds relative path '{expected_rel}' (got '{link_val}')"
            )
            # Verify not absolute path (no C: or /)
            reporter.assert_true(
                not (link_val.startswith("/") or ":" in link_val),
                f"MTLStrictlyRelativePath[{species_id}:{key}]",
                f"Path '{link_val}' is strictly relative (no root / or drive :)"
            )
            # Verify file actually exists at resolved relative path from mtl
            resolved_p = mtl_path.parent / expected_rel
            reporter.assert_true(
                resolved_p.is_file(),
                f"MTLTextureFileExists[{species_id}:{expected_rel}]",
                f"Referenced texture exists on disk at {resolved_p.name}"
            )
            
        # 3. Discrete PNG Texture stress in textures/ directory
        tex_dir = obj_path.parent / "textures"
        for channel in ("albedo", "normal", "roughness", "metallic"):
            tex_file = tex_dir / f"{channel}.png"
            reporter.assert_true(
                tex_file.is_file(),
                f"DiscreteTextureExists[{species_id}:{channel}]",
                f"Discrete texture exists at {tex_file.name}"
            )
            file_size = tex_file.stat().st_size
            reporter.assert_true(
                file_size > 0,
                f"DiscreteTextureNonZero[{species_id}:{channel}]",
                f"Texture {channel}.png size is {file_size} bytes (> 0)"
            )
            raw_tex_bytes = tex_file.read_bytes()
            reporter.assert_true(
                raw_tex_bytes.startswith(b"\x89PNG\r\n\x1a\n"),
                f"DiscreteTexturePngMagic[{species_id}:{channel}]",
                "Texture file on disk starts with PNG magic header \\x89PNG"
            )
            # Verify PIL readable and dimensions 512x512
            img = Image.open(tex_file)
            reporter.assert_true(
                img.size == (512, 512),
                f"DiscreteTextureDimensions[{species_id}:{channel}]",
                f"Texture dimensions are exact 512x512 (got {img.size})"
            )

    # STEP 4: Synchronization Verification (GLB vs OBJ vs Manifest vs In-Memory)
    print("\n--- [STAGE 4] Cross-Format Geometry & Bounding Box Synchronization ---")
    for biome_cat, species_id in BIOME_REPRESENTATIVES.items():
        exported = generated_assets[species_id]
        
        # 1. Manifest data
        with open(exported.manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
            
        # 2. GLB data
        gltf_json, bin_data, _ = parse_raw_glb(exported.glb_path)
        pos_acc = gltf_json["accessors"][0]
        idx_acc = gltf_json["accessors"][3]
        glb_verts = pos_acc["count"]
        glb_faces = idx_acc["count"] // 3
        glb_min = pos_acc["min"]
        glb_max = pos_acc["max"]
        
        # 3. OBJ data
        obj_data = parse_obj_file(exported.obj_path)
        obj_verts = obj_data["vertex_count"]
        obj_faces = obj_data["face_count"]
        obj_min = obj_data["min_coords"]
        obj_max = obj_data["max_coords"]
        
        # 4. Manifest numbers
        man_verts = manifest["geometry"]["vertex_count"]
        man_faces = manifest["geometry"]["face_count"]
        man_bbox_min = manifest["geometry"]["bounding_box"]["min_point"]
        man_bbox_max = manifest["geometry"]["bounding_box"]["max_point"]
        
        # Strict Vertex Count Synchronization
        reporter.assert_true(
            glb_verts == obj_verts == man_verts == exported.vertex_count,
            f"SyncVertexCount[{species_id}]",
            f"Vertex counts match exactly across all formats: GLB={glb_verts}, OBJ={obj_verts}, Manifest={man_verts}, Asset={exported.vertex_count}"
        )
        
        # Strict Face Count Synchronization
        reporter.assert_true(
            glb_faces == obj_faces == man_faces == exported.face_count,
            f"SyncFaceCount[{species_id}]",
            f"Face counts match exactly across all formats: GLB={glb_faces}, OBJ={obj_faces}, Manifest={man_faces}, Asset={exported.face_count}"
        )
        
        # Strict Ground Pivot Snapping (Z_min == 0.000m)
        reporter.assert_true(
            abs(glb_min[2]) <= 1e-4,
            f"SyncGLBGroundContact[{species_id}]",
            f"GLB Z_min is grounded at {glb_min[2]:.6f}m (<= 0.0001m)"
        )
        reporter.assert_true(
            abs(obj_min[2]) <= 1e-4,
            f"SyncOBJGroundContact[{species_id}]",
            f"OBJ Z_min is grounded at {obj_min[2]:.6f}m (<= 0.0001m)"
        )
        reporter.assert_true(
            manifest["geometry"]["pivot_grounded"] is True and abs(manifest["geometry"]["ground_contact_z"]) <= 1e-4,
            f"SyncManifestGroundContact[{species_id}]",
            f"Manifest records pivot_grounded=True, ground_contact_z={manifest['geometry']['ground_contact_z']:.6f}m"
        )
        
        # Strict Bounding Box Synchronization (GLB vs OBJ vs Manifest)
        max_diff_min = max(abs(a - b) for a, b in zip(glb_min, obj_min))
        max_diff_max = max(abs(a - b) for a, b in zip(glb_max, obj_max))
        max_diff_man_min = max(abs(a - b) for a, b in zip(glb_min, man_bbox_min))
        max_diff_man_max = max(abs(a - b) for a, b in zip(glb_max, man_bbox_max))
        reporter.assert_true(
            max_diff_min <= 1e-3 and max_diff_max <= 1e-3 and max_diff_man_min <= 1e-3 and max_diff_man_max <= 1e-3,
            f"SyncBoundingBoxGLBvsOBJvsManifest[{species_id}]",
            f"GLB vs OBJ vs Manifest max discrepancy <= 0.001m (obj_min_diff={max_diff_min:.6f}m, man_min_diff={max_diff_man_min:.6f}m)"
        )
        
        # Base Contact Centroid Centering (Bottom 5% slice centered at (0, 0) ± 0.05m)
        obj_verts_np = obj_data["vertices"]
        z_min = float(obj_verts_np[:, 2].min())
        z_max = float(obj_verts_np[:, 2].max())
        slice_thresh = z_min + 0.05 * (z_max - z_min)
        base_verts = obj_verts_np[obj_verts_np[:, 2] <= slice_thresh]
        reporter.assert_true(
            len(base_verts) > 0,
            f"BaseVertsExist[{species_id}]",
            f"Bottom 5% slice contains {len(base_verts)} vertices"
        )
        cx = float(base_verts[:, 0].mean())
        cy = float(base_verts[:, 1].mean())
        reporter.assert_true(
            abs(cx) <= 0.05 and abs(cy) <= 0.05,
            f"BaseContactCentering[{species_id}]",
            f"Base centroid ({cx:.4f}, {cy:.4f}) is centered within ±0.05m of (0, 0)"
        )
        
        # Metric Height Conformance (within 5% of catalog target)
        target_h = manifest["normalization"]["target_height_m"]
        actual_h = glb_max[2] - glb_min[2]
        err_pct = abs(actual_h - target_h) / target_h
        reporter.assert_true(
            err_pct <= 0.05,
            f"MetricHeightTolerance[{species_id}]",
            f"Actual height {actual_h:.3f}m matches catalog target {target_h:.3f}m within 5% (err={err_pct*100:.2f}%)"
        )
        
        # Round-Trip GLB Mesh and Texture Reloading
        reloaded_mesh = load_mesh_from_glb(exported.glb_path)
        reporter.assert_true(
            len(reloaded_mesh.vertices) == glb_verts,
            f"GLBRoundTripVertices[{species_id}]",
            f"Reloaded mesh vertices ({len(reloaded_mesh.vertices)}) == GLB vertices ({glb_verts})"
        )
        reporter.assert_true(
            len(reloaded_mesh.faces) == glb_faces,
            f"GLBRoundTripFaces[{species_id}]",
            f"Reloaded mesh faces ({len(reloaded_mesh.faces)}) == GLB faces ({glb_faces})"
        )
        extracted_tex = extract_textures_from_glb(exported.glb_path)
        reporter.assert_true(
            "albedo" in extracted_tex and "normal" in extracted_tex and "roughness" in extracted_tex and "metallic" in extracted_tex,
            f"GLBRoundTripTextures[{species_id}]",
            f"Extracted all 4 discrete channels from GLB binary container: {list(extracted_tex.keys())}"
        )

    # STEP 5: Adversarial Boundary & Stress Cases
    print("\n--- [STAGE 5] Adversarial Stress & Edge Case Resilience Testing ---")
    
    # Adversarial Case 1: Floating subterranean mesh normalization
    species = get_species("veg_tree_oak_01")
    mesh_float = MeshGeometry()
    mesh_float.vertices = [
        (-1.0, -1.0, 10.0), (1.0, -1.0, 10.0), (1.0, 1.0, 10.0), (-1.0, 1.0, 10.0),
        (-0.5, -0.5, 15.0), (0.5, -0.5, 15.0), (0.5, 0.5, 15.0), (-0.5, 0.5, 15.0),
    ]
    mesh_float.normals = [(0.0, 0.0, 1.0)] * 8
    mesh_float.uvs = [(0.0, 0.0)] * 8
    mesh_float.faces = [(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7)]
    
    snapped, (cx, cy), gz = snap_ground_pivot_and_center(mesh_float)
    min_z_snapped = min(v[2] for v in snapped.vertices)
    reporter.assert_true(
        abs(min_z_snapped) <= 1e-7,
        "AdversarialFloatingMeshGrounding",
        f"Floating mesh snapped from Z_min=10.0 to Z_min={min_z_snapped:.8f}m"
    )
    reporter.assert_true(
        abs(cx) <= 1e-6 and abs(cy) <= 1e-6,
        "AdversarialFloatingMeshCentering",
        f"Symmetric box base centered to ({cx:.6f}, {cy:.6f})"
    )

    # Adversarial Case 2: Leaning asymmetric crown
    mesh_lean = MeshGeometry()
    # Trunk base at (2.0, -3.0, 0.0), leaning crown at (10.0, 8.0, 10.0)
    mesh_lean.vertices = [
        # Base ring (Z=0 to 0.5)
        (1.9, -3.1, 0.0), (2.1, -3.1, 0.0), (2.1, -2.9, 0.0), (1.9, -2.9, 0.0),
        (1.9, -3.1, 0.4), (2.1, -3.1, 0.4), (2.1, -2.9, 0.4), (1.9, -2.9, 0.4),
        # Leaning crown (Z=8 to 10)
        (9.0, 7.0, 8.0), (11.0, 7.0, 8.0), (11.0, 9.0, 8.0), (9.0, 9.0, 8.0),
        (9.0, 7.0, 10.0), (11.0, 7.0, 10.0), (11.0, 9.0, 10.0), (9.0, 9.0, 10.0),
    ]
    mesh_lean.normals = [(0.0, 0.0, 1.0)] * 16
    mesh_lean.uvs = [(0.0, 0.0)] * 16
    mesh_lean.faces = [(0, 1, 2), (0, 2, 3), (8, 9, 10), (8, 10, 11)]
    
    snapped_lean, _, _ = snap_ground_pivot_and_center(mesh_lean)
    # Check bottom slice (Z <= 0.5) is centered at (0, 0)
    base_lean = [v for v in snapped_lean.vertices if v[2] <= 0.5]
    bx = float(np.mean([v[0] for v in base_lean]))
    by = float(np.mean([v[1] for v in base_lean]))
    reporter.assert_true(
        abs(bx) <= 1e-4 and abs(by) <= 1e-4,
        "AdversarialLeaningTrunkCentering",
        f"Trunk contact base centered to ({bx:.6f}, {by:.6f}) despite massive crown offset"
    )

    # Adversarial Case 3: Degenerate zero-height mesh rejection
    mesh_degen = MeshGeometry()
    mesh_degen.vertices = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
    mesh_degen.normals = [(0.0, 0.0, 1.0)] * 3
    mesh_degen.uvs = [(0.0, 0.0)] * 3
    mesh_degen.faces = [(0, 1, 2)]
    try:
        snap_ground_pivot_and_center(mesh_degen)
        reporter.assert_true(False, "AdversarialZeroHeightRejection", "Failed to raise ValueError for zero-height mesh")
    except ValueError as ve:
        reporter.assert_true(True, "AdversarialZeroHeightRejection", f"Cleanly rejected zero-height mesh: {ve}")

    # Adversarial Case 4: Non-finite coordinate rejection
    mesh_nan = MeshGeometry()
    mesh_nan.vertices = [(0.0, 0.0, 0.0), (1.0, float("nan"), 0.0), (0.0, 1.0, 1.0)]
    mesh_nan.normals = [(0.0, 0.0, 1.0)] * 3
    mesh_nan.uvs = [(0.0, 0.0)] * 3
    mesh_nan.faces = [(0, 1, 2)]
    try:
        snap_ground_pivot_and_center(mesh_nan)
        reporter.assert_true(False, "AdversarialNaNRejection", "Failed to raise ValueError for NaN coordinates")
    except ValueError as ve:
        reporter.assert_true(True, "AdversarialNaNRejection", f"Cleanly rejected NaN coordinates: {ve}")

    # STEP 6: Final Results Summary
    summary = reporter.summary()
    print("\n" + "=" * 80)
    print("EMPIRICAL ADVERSARIAL STRESS TEST SUMMARY")
    print(f"Total Tests Executed: {summary['total']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print("=" * 80)
    
    if summary["failed"] > 0:
        print("\nFAILURES:")
        for name, msg in summary["errors"]:
            print(f" - {name}: {msg}")
        return False
    else:
        print("\nALL 7 BOTANICAL CATEGORIES PASSED 100% OF EMPIRICAL ADVERSARIAL STRESS TESTS.")
        return True


if __name__ == "__main__":
    success = run_empirical_stress_tests()
    sys.exit(0 if success else 1)
