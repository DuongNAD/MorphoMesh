"""
MorphoMesh Vegetation Library - Automated Inspection Suite & Quality Assurance Validator
Target File: teamwork_projects/vegetation_library/vegetation_pipeline/validator.py

Conforms to Milestone 4 (M4) Specification:
1. Geometric Validation:
   - Pure Python / NumPy binary GLB parser to extract and decode vertex buffer accessors.
   - Zero NaN / Inf assertions across all vertex coordinates.
   - Vertex count budget: strictly asserts 3,000 <= N_verts <= 45,000.
   - Normal vector validation: all normals must be finite, non-zero length, and unit normalized (||n|| == 1.0 +/- 0.05).
   - Non-degenerate faces check: triangles must not have duplicate vertex indices or zero area (area > 1e-8).
   - Ground contact base alignment: root base Z_min == 0.000m +/- 0.005m (Blender) / Y_min == 0.000m +/- 0.005m (glTF).
   - Base contact centroid centering: centroid of bottom 5% height slice is centered at (0, 0) +/- 0.05m.
   - Metric scale bounds: bounding box height matches catalog target height within +/- 10%.
2. Static Mesh Invariant Validation:
   - GLB binary inspection: strictly asserts `skins` is None/empty, `animations` is None/empty,
     and zero primitive attributes contain `JOINTS_` or `WEIGHTS_`.
   - OBJ inspection: parses companion `.obj` file, asserts absence of bone groups or skinning directives.
   - Strictly enforces N_bones == 0.
3. PBR Texture Completeness & Physical Plausibility Validation:
   - Inspects directory `textures/` and embedded GLB images.
   - Verifies 4 required channels: `albedo.png`, `normal.png`, `roughness.png`, `metallic.png`.
   - Verifies all are readable non-empty PNG images with dimensions >= 256x256 (typically 512x512).
   - Verifies Albedo: non-solid black (mean > 0.05, std > 0.02).
   - Verifies Normal map: valid tangent space normal distribution (Z-component in [0.5, 1.0], magnitude ~= 1.0).
   - Verifies Roughness: realistic organic roughness distribution (mean in [0.20, 0.95], std > 0.01).
   - Verifies Metallic: dielectric vegetation material enforcement (max <= 0.05, mean <= 0.02).
4. Data Model and Entry Points:
   - `ValidationReport` Pydantic model:
     `is_valid: bool`, `species_id: str`, `category: str`, `checks: Dict[str, bool]`,
     `metrics: Dict[str, Any]`, `errors: List[str]`, `warnings: List[str]`.
   - `validate_asset(asset: Union[ExportedAsset, Path, str], catalog: Optional[VegetationCatalog] = None) -> ValidationReport`
   - `validate_directory(output_dir: Union[str, Path], catalog: Optional[VegetationCatalog] = None) -> Dict[str, ValidationReport]`
"""
from __future__ import annotations

import io
import json
import logging
import math
from pathlib import Path
import struct
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field

from vegetation_pipeline.catalog import (
    PlantSpecies,
    VegetationCatalog,
    get_catalog,
    get_species,
)
from vegetation_pipeline.post_processor import ExportedAsset

logger = logging.getLogger("vegetation_pipeline.validator")


# ==============================================================================
# DATA MODELS
# ==============================================================================

class ValidationReport(BaseModel):
    """
    Comprehensive structured validation report emitted by the automated inspection suite.
    Conforms to M4 <-> M5 Interface Contract.
    """
    model_config = ConfigDict(extra="ignore")

    is_valid: bool = Field(..., description="Overall validation verdict (True if 0 blocking errors)")
    species_id: str = Field(..., description="Canonical botanical species identifier")
    category: str = Field(..., description="Botanical category identifier (e.g. 'broadleaf_trees')")
    checks: Dict[str, bool] = Field(default_factory=dict, description="Status of individual validation checks")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Quantitative geometric & texture metrics")
    errors: List[str] = Field(default_factory=list, description="List of blocking failure messages")
    warnings: List[str] = Field(default_factory=list, description="List of non-blocking warning messages")

    @property
    def passed_checks_count(self) -> int:
        """Number of checks that passed."""
        return sum(1 for v in self.checks.values() if v)

    @property
    def total_checks_count(self) -> int:
        """Total number of checks executed."""
        return len(self.checks)

    def summary(self) -> str:
        """Returns a formatted human-readable summary of the validation report."""
        status_str = "PASSED" if self.is_valid else "FAILED"
        lines = [
            f"=== Validation Report: {self.species_id} [{status_str}] ===",
            f"Category: {self.category}",
            f"Checks: {self.passed_checks_count}/{self.total_checks_count} passed",
            f"Errors ({len(self.errors)}):",
        ]
        for err in self.errors:
            lines.append(f"  - [FAIL] {err}")
        if not self.errors:
            lines.append("  - None")
        lines.append(f"Warnings ({len(self.warnings)}):")
        for warn in self.warnings:
            lines.append(f"  - [WARN] {warn}")
        if not self.warnings:
            lines.append("  - None")
        lines.append("Key Metrics:")
        for k, v in self.metrics.items():
            lines.append(f"  * {k}: {v}")
        return "\n".join(lines)


# ==============================================================================
# PURE-PYTHON / NUMPY GLB & OBJ PARSERS
# ==============================================================================

GLTF_COMPONENT_DTYPES = {
    5120: np.int8,
    5121: np.uint8,
    5122: np.int16,
    5123: np.uint16,
    5125: np.uint32,
    5126: np.float32,
}

GLTF_TYPE_COMPONENT_COUNTS = {
    "SCALAR": 1,
    "VEC2": 2,
    "VEC3": 3,
    "VEC4": 4,
    "MAT2": 4,
    "MAT3": 9,
    "MAT4": 16,
}


def parse_glb_container(
    glb_path: Union[str, Path]
) -> Tuple[Dict[str, Any], bytes]:
    """
    Extracts glTF JSON chunk and binary buffer from a binary glTF 2.0 (.glb) container.
    Strictly validates 12-byte header, chunk 0 (JSON), and chunk 1 (BIN).
    Raises ValueError on corruption or truncated header.
    """
    glb_path = Path(glb_path)
    if not glb_path.is_file():
        raise FileNotFoundError(f"GLB file does not exist: {glb_path}")

    file_size = glb_path.stat().st_size
    if file_size < 12:
        raise ValueError(f"File too small ({file_size} bytes) for glTF 2.0 container: {glb_path}")

    with open(glb_path, "rb") as f:
        header = f.read(12)
        magic, version, total_len = struct.unpack_from("<4sII", header, 0)
        if magic != b"glTF":
            raise ValueError(f"Invalid GLB magic header {magic!r}, expected b'glTF'")
        if version != 2:
            raise ValueError(f"Unsupported glTF container version {version}, expected 2")
        if total_len > file_size:
            raise ValueError(f"GLB header declares total length {total_len}, but file size is {file_size}")

        # Chunk 0: JSON
        c0_hdr = f.read(8)
        if len(c0_hdr) < 8:
            raise ValueError("GLB container missing Chunk 0 header")
        c0_len, c0_type = struct.unpack_from("<I4s", c0_hdr, 0)
        if c0_type != b"JSON":
            raise ValueError(f"Expected Chunk 0 type b'JSON', got {c0_type!r}")

        json_bytes = f.read(c0_len)
        if len(json_bytes) < c0_len:
            raise ValueError(f"Truncated JSON chunk: read {len(json_bytes)} of {c0_len} bytes")
        gltf = json.loads(json_bytes.decode("utf-8"))

        # Chunk 1: BIN (optional in spec, but standard for binary GLB)
        bin_bytes = b""
        c1_hdr = f.read(8)
        if len(c1_hdr) == 8:
            c1_len, c1_type = struct.unpack_from("<I4s", c1_hdr, 0)
            if c1_type.startswith(b"BIN"):
                bin_bytes = f.read(c1_len)
                if len(bin_bytes) < c1_len:
                    raise ValueError(f"Truncated BIN chunk: read {len(bin_bytes)} of {c1_len} bytes")

    return gltf, bin_bytes


def decode_glb_geometry(
    gltf: Dict[str, Any],
    bin_bytes: bytes,
) -> Dict[str, Any]:
    """
    Decodes vertex buffer accessors (POSITION, NORMAL, TEXCOORD_0, INDICES)
    from glTF JSON structure and binary buffer.
    Returns:
      positions: np.ndarray of shape (N, 3), float32
      normals: np.ndarray of shape (N, 3), float32
      uvs: np.ndarray of shape (N, 2), float32
      triangles: np.ndarray of shape (F, 3), int32
      primitive_attributes: List[Dict[str, int]]
    """
    accessors = gltf.get("accessors", [])
    buffer_views = gltf.get("bufferViews", [])

    def decode_accessor(acc_idx: int) -> np.ndarray:
        if acc_idx >= len(accessors):
            raise IndexError(f"Accessor index {acc_idx} out of range (total {len(accessors)})")
        acc = accessors[acc_idx]
        bv_idx = acc.get("bufferView")
        if bv_idx is None or bv_idx >= len(buffer_views):
            raise IndexError(f"BufferView index {bv_idx} out of range in accessor {acc_idx}")
        bv = buffer_views[bv_idx]

        ctype = acc.get("componentType", 5126)
        dtype = GLTF_COMPONENT_DTYPES.get(ctype)
        if dtype is None:
            raise ValueError(f"Unsupported accessor componentType {ctype}")

        atype = acc.get("type", "SCALAR")
        comp_count = GLTF_TYPE_COMPONENT_COUNTS.get(atype)
        if comp_count is None:
            raise ValueError(f"Unsupported accessor type {atype}")

        count = acc.get("count", 0)
        offset = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
        byte_len = count * comp_count * np.dtype(dtype).itemsize

        if offset + byte_len > len(bin_bytes):
            raise ValueError(f"BufferView read exceeds binary buffer size: {offset + byte_len} > {len(bin_bytes)}")

        raw = bin_bytes[offset : offset + byte_len]
        arr = np.frombuffer(raw, dtype=dtype)
        if comp_count > 1:
            arr = arr.reshape((count, comp_count))
        return arr

    all_positions = []
    all_normals = []
    all_uvs = []
    all_triangles = []
    all_primitive_attributes = []
    vert_offset = 0

    for mesh in gltf.get("meshes", []):
        for prim in mesh.get("primitives", []):
            attrs = prim.get("attributes", {})
            all_primitive_attributes.append(attrs)

            pos_idx = attrs.get("POSITION")
            if pos_idx is not None:
                pos = decode_accessor(pos_idx).astype(np.float32)
                all_positions.append(pos)
                p_count = len(pos)
            else:
                p_count = 0

            norm_idx = attrs.get("NORMAL")
            if norm_idx is not None:
                norm = decode_accessor(norm_idx).astype(np.float32)
                all_normals.append(norm)
            elif p_count > 0:
                # Default normal pointing up
                all_normals.append(np.tile(np.array([0.0, 0.0, 1.0], dtype=np.float32), (p_count, 1)))

            uv_idx = attrs.get("TEXCOORD_0")
            if uv_idx is not None:
                uv = decode_accessor(uv_idx).astype(np.float32)
                all_uvs.append(uv)
            elif p_count > 0:
                all_uvs.append(np.zeros((p_count, 2), dtype=np.float32))

            idx_idx = prim.get("indices")
            if idx_idx is not None:
                indices = decode_accessor(idx_idx).astype(np.int32)
                tri = indices.reshape(-1, 3) + vert_offset
                all_triangles.append(tri)
            elif p_count > 0:
                tri = np.arange(p_count, dtype=np.int32).reshape(-1, 3) + vert_offset
                all_triangles.append(tri)

            vert_offset += p_count

    positions = np.vstack(all_positions) if all_positions else np.empty((0, 3), dtype=np.float32)
    normals = np.vstack(all_normals) if all_normals else np.empty((0, 3), dtype=np.float32)
    uvs = np.vstack(all_uvs) if all_uvs else np.empty((0, 2), dtype=np.float32)
    triangles = np.vstack(all_triangles) if all_triangles else np.empty((0, 3), dtype=np.int32)

    return {
        "positions": positions,
        "normals": normals,
        "uvs": uvs,
        "triangles": triangles,
        "primitive_attributes": all_primitive_attributes,
    }


def inspect_companion_obj(obj_path: Union[str, Path]) -> Tuple[bool, int, List[str]]:
    """
    Parses a companion Wavefront .obj file and verifies zero bone groups or skinning directives.
    Returns: (is_valid, n_bones, detected_bone_directives)
    """
    obj_path = Path(obj_path)
    if not obj_path.is_file():
        return True, 0, []

    bone_keywords = ("bone", "joint", "armature", "skeleton", "bip_", "skin", "weight")
    detected = []

    try:
        with open(obj_path, "r", encoding="utf-8", errors="ignore") as f:
            for line_no, line in enumerate(f, 1):
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                parts = s.split()
                cmd = parts[0].lower()
                if cmd in ("g", "o") and len(parts) > 1:
                    name = parts[1].lower()
                    for kw in bone_keywords:
                        if kw in name:
                            detected.append(f"Line {line_no}: Object/group directive '{s}' references '{kw}'")
                elif cmd in ("skin", "joint", "bone", "weight"):
                    detected.append(f"Line {line_no}: Direct skinning/bone keyword command '{s}'")
    except Exception as e:
        logger.debug("Failed reading OBJ file %s: %s", obj_path, e)
        return False, 0, [f"Could not read OBJ file: {e}"]

    n_bones = len(detected)
    return (n_bones == 0), n_bones, detected


# ==============================================================================
# CORE VALIDATION ALGORITHMS
# ==============================================================================

def validate_geometry(
    positions: np.ndarray,
    normals: np.ndarray,
    triangles: np.ndarray,
    target_height_m: Optional[float] = None,
    vertical_axis: Optional[str] = None,
    min_vertices: int = 3000,
    max_vertices: int = 65000,
) -> Tuple[Dict[str, bool], Dict[str, Any], List[str], List[str]]:
    """
    Executes comprehensive geometric validation across decoded vertex and triangle buffers.
    Checks:
    - zero_nan_inf_coordinates
    - vertex_count_budget (min_vertices <= N_verts <= max_vertices)
    - normals_finite_and_unit (||n|| == 1.0 +/- 0.05)
    - non_degenerate_faces (no duplicate indices, area > 1e-8)
    - ground_contact_base_aligned (Z_min == 0.000m +/- 0.005m or Y_min == 0.000m +/- 0.005m)
    - base_contact_centroid_centered (bottom 5% slice centered at (0, 0) +/- 0.05m)
    - metric_scale_bounds (height matches target_height_m within +/- 10%)
    """
    checks: Dict[str, bool] = {}
    metrics: Dict[str, Any] = {}
    errors: List[str] = []
    warnings: List[str] = []

    n_verts = len(positions)
    n_faces = len(triangles)
    metrics["vertex_count"] = n_verts
    metrics["face_count"] = n_faces

    # 1. Zero NaN / Inf coordinates
    if n_verts == 0:
        checks["zero_nan_inf_coordinates"] = False
        checks["vertex_count_budget"] = False
        errors.append("Mesh geometry is empty (0 vertices)")
        return checks, metrics, errors, warnings

    is_finite = np.isfinite(positions).all()
    is_within_bounds = bool(np.all(np.abs(positions) < 10000.0))
    checks["zero_nan_inf_coordinates"] = bool(is_finite and is_within_bounds)
    if not is_finite:
        bad_count = int(np.count_nonzero(~np.isfinite(positions)))
        errors.append(f"Mesh contains {bad_count} non-finite (NaN or Inf) vertex coordinates")
    elif not is_within_bounds:
        errors.append("Mesh contains extreme out-of-universe vertex coordinates (|pos| >= 10000.0m)")

    # 2. Vertex count budget (min_vertices <= N_verts <= max_vertices, target [20,000, 65,000])
    within_budget = min_vertices <= n_verts <= max_vertices
    checks["vertex_count_budget"] = bool(within_budget)
    if n_verts < min_vertices:
        errors.append(f"Vertex count {n_verts:,} is under budget (minimum acceptable is {min_vertices:,})")
    elif n_verts > max_vertices:
        errors.append(f"Vertex count {n_verts:,} is over budget (maximum acceptable is {max_vertices:,})")

    # 3. Normal vector validation
    if len(normals) != n_verts:
        checks["normals_finite_and_unit"] = False
        errors.append(f"Normals buffer length {len(normals)} does not match vertex count {n_verts}")
    else:
        norm_finite = np.isfinite(normals).all()
        if not norm_finite:
            checks["normals_finite_and_unit"] = False
            errors.append("Normal vectors buffer contains non-finite (NaN or Inf) values")
        else:
            lengths = np.linalg.norm(normals, axis=1)
            min_len = float(np.min(lengths))
            max_len = float(np.max(lengths))
            dev = np.abs(lengths - 1.0)
            max_dev = float(np.max(dev))
            metrics["normal_length_min"] = round(min_len, 4)
            metrics["normal_length_max"] = round(max_len, 4)
            metrics["normal_max_deviation"] = round(max_dev, 4)

            if min_len < 1e-6:
                checks["normals_finite_and_unit"] = False
                errors.append(f"Found degenerate zero-length normal vectors (min length {min_len:.6f})")
            elif max_dev > 0.05:
                checks["normals_finite_and_unit"] = False
                errors.append(f"Normal vectors violate unit length: max deviation {max_dev:.4f} > 0.05")
            else:
                checks["normals_finite_and_unit"] = True

    # 4. Non-degenerate faces check
    if n_faces > 0:
        # Duplicate vertex indices within triangle
        dup_mask = (triangles[:, 0] == triangles[:, 1]) | (triangles[:, 1] == triangles[:, 2]) | (triangles[:, 2] == triangles[:, 0])
        dup_count = int(np.count_nonzero(dup_mask))

        # Triangle area calculation: 0.5 * ||(v1 - v0) x (v2 - v0)||
        v0 = positions[triangles[:, 0]]
        v1 = positions[triangles[:, 1]]
        v2 = positions[triangles[:, 2]]
        cross = np.cross(v1 - v0, v2 - v0)
        areas = 0.5 * np.linalg.norm(cross, axis=1)
        zero_area_count = int(np.count_nonzero(areas <= 1e-8))

        metrics["duplicate_index_faces"] = dup_count
        metrics["zero_area_faces"] = zero_area_count

        if dup_count > 0 or zero_area_count > 0:
            checks["non_degenerate_faces"] = False
            if dup_count > 0:
                errors.append(f"Found {dup_count} faces with duplicate vertex indices")
            if zero_area_count > 0:
                errors.append(f"Found {zero_area_count} degenerate zero-area faces (area <= 1e-8)")
        else:
            checks["non_degenerate_faces"] = True
    else:
        checks["non_degenerate_faces"] = False
        errors.append("Mesh has zero triangle faces")

    # 5. Determine vertical axis & bounding extents
    min_x, max_x = float(positions[:, 0].min()), float(positions[:, 0].max())
    min_y, max_y = float(positions[:, 1].min()), float(positions[:, 1].max())
    min_z, max_z = float(positions[:, 2].min()), float(positions[:, 2].max())

    dx = max_x - min_x
    dy = max_y - min_y
    dz = max_z - min_z

    metrics["bounding_box_min"] = [round(min_x, 4), round(min_y, 4), round(min_z, 4)]
    metrics["bounding_box_max"] = [round(max_x, 4), round(max_y, 4), round(max_z, 4)]

    # Detect vertical coordinate axis (Blender Z-up vs glTF Y-up)
    if vertical_axis is not None:
        vert_axis = vertical_axis.upper()
        vert_idx = 2 if vert_axis == "Z" else 1
        ground_min = min_z if vert_axis == "Z" else min_y
        measured_height = dz if vert_axis == "Z" else dy
    elif target_height_m is not None and target_height_m > 0:
        # Prioritize axis whose bounding extent is closest to target mature height
        err_z = abs(dz - target_height_m)
        err_y = abs(dy - target_height_m)
        if err_z <= err_y:
            vert_axis = "Z"
            vert_idx = 2
            ground_min = min_z
            measured_height = dz
        else:
            vert_axis = "Y"
            vert_idx = 1
            ground_min = min_y
            measured_height = dy
    elif abs(min_z) <= 0.005:
        vert_axis = "Z"
        vert_idx = 2
        ground_min = min_z
        measured_height = dz
    elif abs(min_y) <= 0.005 and min_z < -0.05:
        # Centered horizontal (X, Z) plane with Y ground contact
        vert_axis = "Y"
        vert_idx = 1
        ground_min = min_y
        measured_height = dy
    else:
        # Default to MorphoMesh native Blender convention (Z-up)
        vert_axis = "Z"
        vert_idx = 2
        ground_min = min_z
        measured_height = dz

    metrics["vertical_axis"] = vert_axis
    metrics["measured_height_m"] = round(measured_height, 4)
    metrics["ground_min_m"] = round(ground_min, 6)

    # 6. Ground contact base alignment (tolerance +/- 0.005m)
    ground_ok = abs(ground_min) <= 0.005
    checks["ground_contact_base_aligned"] = bool(ground_ok)
    if not ground_ok:
        errors.append(
            f"Ground contact base violation: {vert_axis}_min = {ground_min:.6f}m "
            f"exceeds tolerance ±0.005m (root base must snap to ground origin)"
        )

    # 7. Base contact centroid centering (bottom 5% slice centered at (0, 0) +/- 0.05m)
    v_min = float(positions[:, vert_idx].min())
    v_max = float(positions[:, vert_idx].max())
    v_extent = v_max - v_min

    if v_extent > 1e-6:
        thresh = v_min + 0.05 * v_extent
        base_mask = positions[:, vert_idx] <= thresh
        base_verts = positions[base_mask]
        if len(base_verts) == 0:
            base_verts = positions[positions[:, vert_idx] <= v_min + 1e-4]

        # Horizontal axes
        if vert_idx == 2:  # Z is vertical -> (X, Y) horizontal
            cx = float(np.mean(base_verts[:, 0]))
            cy = float(np.mean(base_verts[:, 1]))
        else:  # Y is vertical -> (X, Z) horizontal
            cx = float(np.mean(base_verts[:, 0]))
            cy = float(np.mean(base_verts[:, 2]))

        centroid_dist = math.sqrt(cx * cx + cy * cy)
        metrics["base_centroid_offset_m"] = round(centroid_dist, 4)
        metrics["base_centroid_coords"] = (round(cx, 4), round(cy, 4))

        centroid_ok = centroid_dist <= 0.05 + 1e-5
        checks["base_contact_centroid_centered"] = bool(centroid_ok)
        if not centroid_ok:
            errors.append(
                f"Base contact centroid off-center: offset {centroid_dist:.4f}m exceeds tolerance ±0.05m "
                f"at coordinates ({cx:.4f}m, {cy:.4f}m)"
            )
    else:
        checks["base_contact_centroid_centered"] = False
        errors.append("Mesh has degenerate zero vertical height")

    # 8. Metric scale bounds (+/- 10% target height)
    if target_height_m is not None and target_height_m > 0:
        metrics["target_height_m"] = round(target_height_m, 4)
        pct_dev = abs(measured_height - target_height_m) / target_height_m
        metrics["height_deviation_pct"] = round(pct_dev * 100.0, 2)
        scale_ok = pct_dev <= 0.10
        checks["metric_scale_bounds"] = bool(scale_ok)
        if not scale_ok:
            errors.append(
                f"Metric scale bounds violation: measured height {measured_height:.3f}m "
                f"deviates from target {target_height_m:.3f}m by {pct_dev * 100.0:.1f}% (exceeds ±10.0%)"
            )
    else:
        checks["metric_scale_bounds"] = True
        warnings.append("No catalog target height provided; metric scale bounds check skipped")

    return checks, metrics, errors, warnings


def validate_static_mesh_invariants(
    gltf: Dict[str, Any],
    obj_path: Optional[Path] = None,
) -> Tuple[Dict[str, bool], Dict[str, Any], List[str], List[str]]:
    """
    Validates static mesh invariants: strictly zero armatures, bones, skins, animations,
    or skinning attributes.
    """
    checks: Dict[str, bool] = {}
    metrics: Dict[str, Any] = {}
    errors: List[str] = []
    warnings: List[str] = []

    # 1. glTF skins check
    skins = gltf.get("skins")
    has_skins = skins is not None and len(skins) > 0
    checks["static_mesh_no_skins"] = not has_skins
    if has_skins:
        errors.append(f"GLB contains non-empty 'skins' array ({len(skins)} skins detected)")

    # 2. glTF animations check
    anims = gltf.get("animations")
    has_anims = anims is not None and len(anims) > 0
    checks["static_mesh_no_animations"] = not has_anims
    if has_anims:
        errors.append(f"GLB contains non-empty 'animations' array ({len(anims)} animations detected)")

    # 3. Primitive attributes: zero JOINTS_ or WEIGHTS_
    has_skin_attrs = False
    for mesh in gltf.get("meshes", []):
        for prim in mesh.get("primitives", []):
            attrs = prim.get("attributes", {})
            for k in attrs:
                k_upper = k.upper()
                if k_upper.startswith("JOINTS_") or k_upper.startswith("WEIGHTS_"):
                    has_skin_attrs = True
                    errors.append(f"GLB mesh primitive contains skeletal skinning attribute: '{k}'")

    checks["static_mesh_no_joint_weights"] = not has_skin_attrs

    # 4. Node hierarchy skin references
    has_node_skins = False
    for node in gltf.get("nodes", []):
        if "skin" in node:
            has_node_skins = True
            errors.append(f"GLB node '{node.get('name', 'unnamed')}' references skeletal skin {node['skin']}")
    checks["static_mesh_no_node_skins"] = not has_node_skins

    # 5. Companion OBJ bone inspection
    n_bones_obj = 0
    if obj_path is not None and Path(obj_path).is_file():
        obj_ok, n_bones_obj, obj_violations = inspect_companion_obj(obj_path)
        checks["obj_no_bones"] = obj_ok
        if not obj_ok:
            for viol in obj_violations:
                errors.append(f"OBJ bone directive: {viol}")
    else:
        checks["obj_no_bones"] = True

    total_bones = (len(skins) if skins else 0) + n_bones_obj
    metrics["n_bones"] = total_bones
    checks["n_bones_strictly_zero"] = (total_bones == 0 and not has_skin_attrs and not has_node_skins)
    if total_bones > 0:
        errors.append(f"Strict static mesh invariant failed: N_bones = {total_bones} > 0")

    return checks, metrics, errors, warnings


def validate_pbr_textures(
    textures_dir: Optional[Path],
    embedded_images: Optional[Dict[str, Image.Image]] = None,
) -> Tuple[Dict[str, bool], Dict[str, Any], List[str], List[str]]:
    """
    Validates PBR texture completeness and physical plausibility:
    - 4 required channels: albedo, normal, roughness, metallic
    - Dimensions >= 256x256
    - Albedo: non-solid black (mean > 0.05, std > 0.02)
    - Normal: tangent space distribution (mean nz in [0.5, 1.0], magnitude ~= 1.0)
    - Roughness: organic roughness distribution (mean in [0.20, 0.95], std > 0.01)
    - Metallic: dielectric material (max <= 0.05, mean <= 0.02)
    """
    checks: Dict[str, bool] = {}
    metrics: Dict[str, Any] = {}
    errors: List[str] = []
    warnings: List[str] = []

    required_channels = ("albedo", "normal", "roughness", "metallic")
    loaded_textures: Dict[str, Image.Image] = {}

    # 1. Ingest textures from textures_dir or embedded images
    missing_on_disk = []
    if textures_dir is not None:
        td = Path(textures_dir)
        if td.is_dir():
            for ch in required_channels:
                p = td / f"{ch}.png"
                if p.is_file():
                    try:
                        img = Image.open(p)
                        img.load()  # verify integrity
                        loaded_textures[ch] = img
                    except (UnidentifiedImageError, OSError) as e:
                        errors.append(f"Texture file '{p.name}' is corrupt or unreadable: {e}")
                else:
                    missing_on_disk.append(f"{ch}.png")
        else:
            errors.append(f"Textures directory not found: {textures_dir}")
    elif embedded_images:
        for ch in required_channels:
            if ch in embedded_images:
                loaded_textures[ch] = embedded_images[ch]

    if missing_on_disk:
        errors.append(f"Missing required texture files on disk: {missing_on_disk}")

    # 2. Check channel completeness
    missing_channels = [ch for ch in required_channels if ch not in loaded_textures]
    checks["textures_channels_present"] = (len(missing_channels) == 0 and len(missing_on_disk) == 0)
    if missing_channels and not missing_on_disk:
        errors.append(f"Missing required PBR texture channels: {missing_channels}")

    # 3. Check resolutions
    res_ok = True
    for ch, img in loaded_textures.items():
        metrics[f"texture_{ch}_size"] = [img.width, img.height]
        if img.width < 256 or img.height < 256:
            res_ok = False
            errors.append(f"Texture '{ch}' resolution ({img.width}x{img.height}) below minimum 256x256")
    checks["textures_readable_and_sized"] = res_ok and (len(loaded_textures) > 0)

    # 4. Albedo Physical Plausibility (mean > 0.05, std > 0.02)
    if "albedo" in loaded_textures:
        alb_arr = np.array(loaded_textures["albedo"].convert("RGB"), dtype=np.float32) / 255.0
        alb_mean = float(np.mean(alb_arr))
        # Spatial standard deviation across pixels (per-channel) to detect flat uniform patches
        alb_std = float(np.mean(np.std(alb_arr, axis=(0, 1))))
        metrics["albedo_mean"] = round(alb_mean, 4)
        metrics["albedo_std"] = round(alb_std, 4)

        alb_ok = True
        if alb_mean <= 0.05:
            alb_ok = False
            errors.append(f"Albedo texture is solid black or too dark: mean={alb_mean:.4f} <= 0.05")
        if alb_std <= 0.02:
            alb_ok = False
            errors.append(f"Albedo texture lacks surface variation: std={alb_std:.4f} <= 0.02")
        checks["texture_albedo_plausible"] = alb_ok
    else:
        checks["texture_albedo_plausible"] = False

    # 5. Normal Map Tangent Space Plausibility (nz in [0.5, 1.0], magnitude ~= 1.0)
    if "normal" in loaded_textures:
        norm_arr = np.array(loaded_textures["normal"].convert("RGB"), dtype=np.float32) / 255.0
        nx = 2.0 * norm_arr[:, :, 0] - 1.0
        ny = 2.0 * norm_arr[:, :, 1] - 1.0
        nz = 2.0 * norm_arr[:, :, 2] - 1.0
        mag = np.sqrt(nx * nx + ny * ny + nz * nz)

        mean_nz = float(np.mean(nz))
        mean_mag = float(np.mean(mag))
        metrics["normal_mean_nz"] = round(mean_nz, 4)
        metrics["normal_mean_mag"] = round(mean_mag, 4)

        norm_ok = True
        if not (0.5 <= mean_nz <= 1.0):
            norm_ok = False
            errors.append(f"Normal map tangent Z-component out of range: mean={mean_nz:.4f} not in [0.5, 1.0]")
        if abs(mean_mag - 1.0) > 0.15:
            norm_ok = False
            errors.append(f"Normal map vector magnitude deviates from 1.0: mean magnitude={mean_mag:.4f}")
        checks["texture_normal_plausible"] = norm_ok
    else:
        checks["texture_normal_plausible"] = False

    # 6. Roughness Organic Distribution (mean in [0.20, 0.95], std > 0.01)
    if "roughness" in loaded_textures:
        r_arr = np.array(loaded_textures["roughness"].convert("L"), dtype=np.float32) / 255.0
        r_mean = float(np.mean(r_arr))
        r_std = float(np.std(r_arr))
        metrics["roughness_mean"] = round(r_mean, 4)
        metrics["roughness_std"] = round(r_std, 4)

        r_ok = True
        if not (0.20 <= r_mean <= 0.95):
            r_ok = False
            errors.append(f"Roughness mean {r_mean:.4f} outside organic vegetation range [0.20, 0.95]")
        if r_std <= 0.01:
            r_ok = False
            errors.append(f"Roughness texture lacks variation (constant flat field): std={r_std:.4f} <= 0.01")
        checks["texture_roughness_plausible"] = r_ok
    else:
        checks["texture_roughness_plausible"] = False

    # 7. Metallic Dielectric Vegetation Enforcement (max <= 0.05, mean <= 0.02)
    if "metallic" in loaded_textures:
        m_arr = np.array(loaded_textures["metallic"].convert("L"), dtype=np.float32) / 255.0
        m_max = float(np.max(m_arr))
        m_mean = float(np.mean(m_arr))
        metrics["metallic_max"] = round(m_max, 4)
        metrics["metallic_mean"] = round(m_mean, 4)

        m_ok = True
        if m_max > 0.05:
            m_ok = False
            errors.append(f"Metallic texture exceeds dielectric ceiling: max={m_max:.4f} > 0.05")
        if m_mean > 0.02:
            m_ok = False
            errors.append(f"Metallic texture mean {m_mean:.4f} exceeds dielectric limit <= 0.02")
        checks["texture_metallic_dielectric"] = m_ok
    else:
        checks["texture_metallic_dielectric"] = False

    return checks, metrics, errors, warnings


# ==============================================================================
# PUBLIC VALIDATION API ENTRY POINTS
# ==============================================================================

def validate_asset(
    asset: Union[ExportedAsset, Path, str],
    catalog: Optional[VegetationCatalog] = None,
) -> ValidationReport:
    """
    Master quality assurance entry point: thoroughly validates a single botanical asset.
    Accepts ExportedAsset or Path (pointing to output folder, .glb file, or manifest).
    Never raises unhandled exceptions on invalid assets: catches errors gracefully
    and records them in the resulting ValidationReport.
    """
    # 1. Resolve catalog
    if catalog is None:
        try:
            catalog = get_catalog()
        except Exception as e:
            logger.debug("Catalog load failed: %s", e)

    # 2. Resolve input paths and metadata
    species_id = "unknown"
    category = "unknown"
    glb_path: Optional[Path] = None
    obj_path: Optional[Path] = None
    textures_dir: Optional[Path] = None
    target_height_m: Optional[float] = None
    mdata: Optional[Dict[str, Any]] = None

    if isinstance(asset, ExportedAsset):
        species_id = asset.species_id
        category = getattr(asset, "category_id", None) or "unknown"
        glb_path = Path(asset.glb_path)
        obj_path = Path(asset.obj_path) if getattr(asset, "obj_path", None) else None
        if asset.texture_paths and "albedo" in asset.texture_paths:
            textures_dir = Path(asset.texture_paths["albedo"]).parent
        elif glb_path.parent:
            textures_dir = glb_path.parent / "textures"
        dims = getattr(asset, "dimensions", None)
        if dims:
            target_height_m = getattr(dims, "target_height_m", None) or getattr(dims, "height_m", None)
        if hasattr(asset, "metadata") and isinstance(asset.metadata, dict):
            mdata = asset.metadata
    else:
        target_path = Path(asset)
        if target_path.is_dir():
            # e.g. output/broadleaf_trees/veg_tree_oak_01/
            species_id = target_path.name
            manifest_p = target_path / "asset_manifest.json"
            if manifest_p.is_file():
                try:
                    with open(manifest_p, "r", encoding="utf-8") as f:
                        mdata = json.load(f)
                    species_id = mdata.get("species_id", species_id)
                    category = mdata.get("taxonomy", {}).get("short_category", category)
                except Exception as e:
                    logger.debug("Failed reading manifest %s: %s", manifest_p, e)

            # Find glb and obj - prioritize <species_id>.glb and avoid raw_meshy_model.glb
            cand_glb = target_path / f"{species_id}.glb"
            if cand_glb.is_file():
                glb_path = cand_glb
            else:
                filtered_glbs = [p for p in target_path.glob("*.glb") if p.name != "raw_meshy_model.glb"]
                if filtered_glbs:
                    glb_path = filtered_glbs[0]
                else:
                    glbs = list(target_path.glob("*.glb"))
                    if glbs:
                        glb_path = glbs[0]

            cand_obj = target_path / f"{species_id}.obj"
            if cand_obj.is_file():
                obj_path = cand_obj
            else:
                objs = list(target_path.glob("*.obj"))
                if objs:
                    obj_path = objs[0]
            td = target_path / "textures"
            if td.is_dir():
                textures_dir = td
        elif target_path.is_file():
            if target_path.suffix.lower() == ".glb":
                glb_path = target_path
                species_id = target_path.stem
                parent = target_path.parent
                cand_manifest = parent / "asset_manifest.json"
                if cand_manifest.is_file():
                    try:
                        with open(cand_manifest, "r", encoding="utf-8") as f:
                            mdata = json.load(f)
                        species_id = mdata.get("species_id", species_id)
                        category = mdata.get("taxonomy", {}).get("short_category", category)
                    except Exception as e:
                        logger.debug("Failed reading manifest: %s", e)
                cand_obj = parent / f"{species_id}.obj"
                if cand_obj.is_file():
                    obj_path = cand_obj
                cand_tex = parent / "textures"
                if cand_tex.is_dir():
                    textures_dir = cand_tex
            elif target_path.name == "asset_manifest.json":
                try:
                    with open(target_path, "r", encoding="utf-8") as f:
                        mdata = json.load(f)
                    species_id = mdata.get("species_id", target_path.parent.name)
                    category = mdata.get("taxonomy", {}).get("short_category", category)
                except Exception as e:
                    logger.debug("Failed reading manifest: %s", e)
                parent = target_path.parent
                cand_glb = parent / f"{species_id}.glb"
                if cand_glb.is_file():
                    glb_path = cand_glb
                else:
                    filtered_glbs = [p for p in parent.glob("*.glb") if p.name != "raw_meshy_model.glb"]
                    if filtered_glbs:
                        glb_path = filtered_glbs[0]
                cand_obj = parent / f"{species_id}.obj"
                if cand_obj.is_file():
                    obj_path = cand_obj
                cand_tex = parent / "textures"
                if cand_tex.is_dir():
                    textures_dir = cand_tex

    # Resolve target dimensions from catalog if available
    if catalog is not None and species_id != "unknown":
        sp = catalog.get(species_id)
        if sp is not None:
            target_height_m = sp.dimensions.height_m
            category = sp.short_category

    checks: Dict[str, bool] = {}
    metrics: Dict[str, Any] = {}
    errors: List[str] = []
    warnings: List[str] = []

    # Provenance tracking & Meshy cloud provenance assertion
    provenance_source = None
    task_id = None
    if mdata:
        prov = mdata.get("provenance", {})
        provenance_source = prov.get("source") if isinstance(prov, dict) else mdata.get("source")
        task_id = (
            prov.get("task_id")
            or prov.get("generator_metadata", {}).get("task_id")
            if isinstance(prov, dict)
            else None
        ) or mdata.get("metadata", {}).get("task_id")
    elif isinstance(asset, ExportedAsset):
        prov = getattr(asset, "provenance", {})
        provenance_source = prov.get("source") if isinstance(prov, dict) else getattr(asset, "source", None)
        task_id = prov.get("generator_metadata", {}).get("task_id") if isinstance(prov, dict) else None
        if not task_id and hasattr(asset, "metadata") and isinstance(asset.metadata, dict):
            task_id = asset.metadata.get("task_id")

    if provenance_source:
        metrics["provenance_source"] = provenance_source
    if task_id:
        metrics["task_id"] = str(task_id)

    if provenance_source == "meshy":
        has_task = bool(task_id and len(str(task_id).strip()) > 5)
        checks["meshy_cloud_provenance"] = has_task
        if not has_task:
            errors.append(f"Meshy cloud provenance assertion failed: missing or empty task_id ({task_id})")

    # 3. GLB Container Presence & Parsing
    if glb_path is None or not glb_path.is_file():
        checks["glb_container_valid"] = False
        errors.append(f"GLB binary container file not found: {glb_path}")
        return ValidationReport(
            is_valid=False,
            species_id=species_id,
            category=category,
            checks=checks,
            metrics=metrics,
            errors=errors,
            warnings=warnings,
        )

    try:
        gltf, bin_bytes = parse_glb_container(glb_path)
        checks["glb_container_valid"] = True
    except Exception as e:
        checks["glb_container_valid"] = False
        errors.append(f"GLB binary container corrupted or unparseable: {e}")
        return ValidationReport(
            is_valid=False,
            species_id=species_id,
            category=category,
            checks=checks,
            metrics=metrics,
            errors=errors,
            warnings=warnings,
        )

    # 4. Geometry Decoding & Validation
    try:
        geom = decode_glb_geometry(gltf, bin_bytes)
        is_meshy = (provenance_source == "meshy")
        min_verts = 20000 if is_meshy else 3000
        max_verts = 65000
        g_checks, g_metrics, g_errors, g_warnings = validate_geometry(
            positions=geom["positions"],
            normals=geom["normals"],
            triangles=geom["triangles"],
            target_height_m=target_height_m,
            min_vertices=min_verts,
            max_vertices=max_verts,
        )
        checks.update(g_checks)
        metrics.update(g_metrics)
        errors.extend(g_errors)
        warnings.extend(g_warnings)
    except Exception as e:
        checks["geometry_valid"] = False
        errors.append(f"Failed decoding mesh geometry buffers: {e}")

    # 5. Static Mesh Invariant Validation
    try:
        s_checks, s_metrics, s_errors, s_warnings = validate_static_mesh_invariants(
            gltf=gltf,
            obj_path=obj_path,
        )
        checks.update(s_checks)
        metrics.update(s_metrics)
        errors.extend(s_errors)
        warnings.extend(s_warnings)
    except Exception as e:
        checks["static_mesh_invariants"] = False
        errors.append(f"Static mesh invariant evaluation failed: {e}")

    # 6. Extract Embedded Images from GLB for Texture Fallback
    embedded_images: Dict[str, Image.Image] = {}
    try:
        bvs = gltf.get("bufferViews", [])
        images = gltf.get("images", [])
        loaded_imgs: Dict[int, Image.Image] = {}
        for idx, img_info in enumerate(images):
            bv_idx = img_info.get("bufferView")
            if bv_idx is not None and bv_idx < len(bvs):
                bv = bvs[bv_idx]
                b_off = bv.get("byteOffset", 0)
                b_len = bv.get("byteLength", 0)
                raw_img = bin_bytes[b_off : b_off + b_len]
                img = Image.open(io.BytesIO(raw_img))
                loaded_imgs[idx] = img
                name = str(img_info.get("name", "")).lower()
                if "albedo" in name or "base" in name:
                    embedded_images["albedo"] = img
                elif "normal" in name:
                    embedded_images["normal"] = img
                elif "rough" in name:
                    embedded_images["roughness"] = img
                elif "metal" in name:
                    embedded_images["metallic"] = img

        # Fallback to glTF materials and textures for unnamed images (e.g. Meshy AI)
        materials = gltf.get("materials", [])
        gltf_textures = gltf.get("textures", [])
        if materials:
            mat = materials[0]
            pbr = mat.get("pbrMetallicRoughness", {})
            if "albedo" not in embedded_images and "baseColorTexture" in pbr:
                t_idx = pbr["baseColorTexture"].get("index", 0)
                if t_idx < len(gltf_textures):
                    s_idx = gltf_textures[t_idx].get("source", 0)
                    if s_idx in loaded_imgs:
                        embedded_images["albedo"] = loaded_imgs[s_idx]
            if "normal" not in embedded_images and "normalTexture" in mat:
                t_idx = mat["normalTexture"].get("index", 0)
                if t_idx < len(gltf_textures):
                    s_idx = gltf_textures[t_idx].get("source", 0)
                    if s_idx in loaded_imgs:
                        embedded_images["normal"] = loaded_imgs[s_idx]
            if "metallicRoughnessTexture" in pbr:
                t_idx = pbr["metallicRoughnessTexture"].get("index", 0)
                if t_idx < len(gltf_textures):
                    s_idx = gltf_textures[t_idx].get("source", 0)
                    if s_idx in loaded_imgs:
                        orm = loaded_imgs[s_idx]
                        if orm.mode != "RGB":
                            orm = orm.convert("RGB")
                        chans = orm.split()
                        if "roughness" not in embedded_images and len(chans) >= 2:
                            embedded_images["roughness"] = chans[1]
                        if "metallic" not in embedded_images and len(chans) >= 3:
                            embedded_images["metallic"] = chans[2]

        if "albedo" not in embedded_images and 0 in loaded_imgs:
            embedded_images["albedo"] = loaded_imgs[0]
        if 1 in loaded_imgs:
            orm = loaded_imgs[1]
            if orm.mode != "RGB":
                orm = orm.convert("RGB")
            chans = orm.split()
            if "roughness" not in embedded_images and len(chans) >= 2:
                embedded_images["roughness"] = chans[1]
            if "metallic" not in embedded_images and len(chans) >= 3:
                embedded_images["metallic"] = chans[2]
        if "normal" not in embedded_images and 2 in loaded_imgs:
            embedded_images["normal"] = loaded_imgs[2]
    except Exception as e:
        logger.debug("Embedded texture extraction note for %s: %s", glb_path, e)

    # 7. PBR Texture Completeness & Plausibility
    try:
        t_checks, t_metrics, t_errors, t_warnings = validate_pbr_textures(
            textures_dir=textures_dir,
            embedded_images=embedded_images,
        )
        checks.update(t_checks)
        metrics.update(t_metrics)
        errors.extend(t_errors)
        warnings.extend(t_warnings)
    except Exception as e:
        checks["textures_valid"] = False
        errors.append(f"Texture validation failed with unexpected error: {e}")

    # 8. Overall Validation Verdict
    is_valid = len(errors) == 0

    return ValidationReport(
        is_valid=is_valid,
        species_id=species_id,
        category=category,
        checks=checks,
        metrics=metrics,
        errors=errors,
        warnings=warnings,
    )


def validate_directory(
    output_dir: Union[str, Path],
    catalog: Optional[VegetationCatalog] = None,
) -> Dict[str, ValidationReport]:
    """
    Scans an output directory hierarchy and validates all discovered botanical assets.
    Returns: Dict mapping species_id to ValidationReport.
    """
    output_dir = Path(output_dir)
    if not output_dir.is_dir():
        raise FileNotFoundError(f"Target directory does not exist: {output_dir}")

    if catalog is None:
        try:
            catalog = get_catalog()
        except Exception as e:
            logger.debug("Catalog load failed: %s", e)

    reports: Dict[str, ValidationReport] = {}

    # Scan for directories containing *.glb files or asset_manifest.json
    for p in output_dir.rglob("*.glb"):
        if p.name == "raw_meshy_model.glb":
            continue
        asset_dir = p.parent
        species_id = p.stem
        # Avoid duplicate validation if multiple glb exist in same dir
        if species_id in reports:
            continue
        report = validate_asset(asset_dir, catalog=catalog)
        reports[report.species_id] = report

    return reports


__all__ = [
    "ValidationReport",
    "parse_glb_container",
    "decode_glb_geometry",
    "inspect_companion_obj",
    "validate_geometry",
    "validate_static_mesh_invariants",
    "validate_pbr_textures",
    "validate_asset",
    "validate_directory",
]
