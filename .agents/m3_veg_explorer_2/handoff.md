# Handoff Report: Milestone 3 (M3) Mathematical Algorithms & Multi-Format Exporter Design

**Agent**: Explorer 2 (`m3_veg_explorer_2`)  
**Milestone**: M3 — Asset Post-Processing, Normalization & Multi-Format Export  
**Status**: Investigation & Synthesis Complete  
**Date**: 2026-09-10T06:28:00Z  

---

## 1. Observation

Direct code and specification analysis across the MorphoMesh and Vegetation Library codebases revealed the following concrete interfaces, constraints, and implementations:

1. **User Request & Project Specification Requirements**:
   - `teamwork_projects/vegetation_library/ORIGINAL_REQUEST.md` (lines 601–607, 621–625):
     - Pivot/origin must be strictly at ground contact base ($Z_{\min} \approx 0.000\text{m}$ / $Y_{\min} \approx 0.000\text{m}$).
     - Metric scale normalized according to real-world botanical dimensions (trees 4–12m, shrubs 1–2m, groundcover 0.2–0.8m).
     - Export production-ready `.glb` with embedded PBR textures and companion `.obj` / `.mtl`.
     - Static mesh guarantee: $N_{\text{bones}} = 0$ (zero armatures, zero skins, zero weights).
   - `orchestrator_vegetation_1/PROJECT.md` (lines 13–16, 33–36, 77–85):
     - Contract: `process_and_export(raw_asset: RawAsset, species: PlantSpecies, output_dir: Path) -> ExportedAsset`.
     - Output files: `<species_id>.glb`, `<species_id>.obj`, `<species_id>.mtl`, `textures/` (`albedo.png`, `normal.png`, `roughness.png`, `metallic.png`), and `asset_manifest.json`.

2. **Existing MorphoMesh Geometry Exporters**:
   - `src/morphomesh/geometry/exporters.py`:
     - Line 12–15: `pad_4(b: bytes) -> bytes` aligns binary buffers to 4-byte boundaries.
     - Line 18–36: `export_obj(mesh, filepath)` writes standard vertices `v`, normals `vn`, texture coords `vt`, and 1-based face indices `f v/vt/vn`, but does **not** generate companion `.mtl` material files, nor does it write `mtllib` or `usemtl`.
     - Line 38–176: `export_glb(mesh, filepath)` writes standard binary glTF 2.0 with POSITION, NORMAL, TEXCOORD_0, and indices bufferViews, but lacks material definitions (`materials`), texture samplers (`samplers`), embedded image buffers (`images`), or `"doubleSided": true` foliage support.
   - `src/morphomesh/geometry/mesh.py`:
     - Line 14–87: `MeshGeometry` stores `vertices: List[Tuple[float, float, float]]`, `normals`, `uvs`, `faces`, and provides `compute_bounding_box()`.

3. **Generator Pipeline Data Structures**:
   - `teamwork_projects/vegetation_library/vegetation_pipeline/generator.py`:
     - Line 117–156: `RawAsset` dataclass contains `species_id`, `glb_path`, `mesh: Optional[MeshGeometry]`, `textures: Dict[str, Image.Image]`, `texture_paths: Dict[str, Path]`, `source`, `vertex_count`, `face_count`, `metadata`.
     - Line 571–648: `MeshyGenerator.generate()` returns `RawAsset` with `mesh=None` and a downloaded `.glb`.
     - Line 672–755: `ProceduralBotanicalGenerator.generate()` returns `RawAsset` with `mesh=MeshGeometry` and procedural PBR textures.
     - Line 1327–1350: `_enforce_mesh_invariants` implements an initial prototype of ground snapping ($z - z_{\min}$) and bottom 5% centroid centering.
     - Line 1358–1420: `_generate_pbr_textures` generates a unified texture atlas where $u < 0.5$ is bark and $u \ge 0.5$ is foliage.

4. **Botanical Catalog Dimension Specifications**:
   - `teamwork_projects/vegetation_library/vegetation_pipeline/catalog.py`:
     - Line 42–73: `DimensionsSpec` defines `height_m: float`, `height_range_m: Tuple[float, float]`, `canopy_spread_m: float`, and `trunk_stem_diameter_m: float`.
     - Line 121–128: `VerificationCriteria` specifies vertex budget $[3000, 45000]$, `enforce_zero_armature = True`, `enforce_root_pivot = True`, and mandatory PBR maps `["baseColor", "normal", "roughness", "metallic"]`.

5. **Existing Validation Tests**:
   - `teamwork_projects/vegetation_library/tests/test_generator.py`:
     - Line 649–670 (`test_ground_pivot_root_alignment_across_7_biomes`): asserts $|Z_{\min}| \le 0.005\text{m}$, bottom 5% centroid $|X| \le 0.05\text{m}$, $|Y| \le 0.05\text{m}$.
     - Line 680–686 (`test_zero_skeletal_armatures_in_glb_across_7_biomes`): strictly asserts zero skins, zero animations, zero `JOINTS_`, zero `WEIGHTS_`.
     - Line 1005–1019 (`test_glb_accessors_and_bufferviews_bounds`): asserts glTF accessor bound `pos_acc["min"][2] <= 0.005` (confirming Z is the vertical coordinate axis in MorphoMesh glTF containers).

---

## 2. Logic Chain

### 2.1 Ground Pivot Snapping & Centering Mathematics

Let vertex positions be $\mathbf{v}_i = (x_i, y_i, z_i)^{\top}$ for $i = 0, \dots, N-1$.

1. **Tight Axis-Aligned Bounding Box (AABB)**:
   $$X_{\min} = \min_{i} x_i, \quad X_{\max} = \max_{i} x_i, \quad \Delta X = X_{\max} - X_{\min}$$
   $$Y_{\min} = \min_{i} y_i, \quad Y_{\max} = \max_{i} y_i, \quad \Delta Y = Y_{\max} - Y_{\min}$$
   $$Z_{\min} = \min_{i} z_i, \quad Z_{\max} = \max_{i} z_i, \quad \Delta Z = Z_{\max} - Z_{\min}$$

2. **Ground Contact Alignment ($Z_{\min} \equiv 0.000\text{m}$)**:
   Shift all vertices along the $Z$-axis:
   $$z_i^{(1)} = z_i - Z_{\min}$$
   This guarantees $\min_i z_i^{(1)} = 0.000\text{m}$ and $z_i^{(1)} \in [0, \Delta Z]$.

3. **Bottom 5% Height Slice Base Centroid Extraction**:
   Define slice height threshold:
   $$h_{\text{slice}} = 0.05 \times \Delta Z$$
   Base contact vertex set:
   $$\mathcal{S}_{\text{base}} = \left\{ \mathbf{v}_i^{(1)} \;\middle|\; z_i^{(1)} \le h_{\text{slice}} \right\}$$
   If $|\mathcal{S}_{\text{base}}| = 0$ (degenerate slice), fallback to $\mathcal{S}_{\text{base}} = \{ \mathbf{v}_i^{(1)} \mid z_i^{(1)} = \min_j z_j^{(1)} \}$.
   Compute the empirical horizontal centroid:
   $$C_x = \frac{1}{|\mathcal{S}_{\text{base}}|} \sum_{\mathbf{v} \in \mathcal{S}_{\text{base}}} x_v^{(1)}, \quad C_y = \frac{1}{|\mathcal{S}_{\text{base}}|} \sum_{\mathbf{v} \in \mathcal{S}_{\text{base}}} y_v^{(1)}$$

4. **Base Centering Translation**:
   $$x_i^{(2)} = x_i^{(1)} - C_x, \quad y_i^{(2)} = y_i^{(1)} - C_y, \quad z_i^{(2)} = z_i^{(1)}$$
   The root base trunk is now centered precisely at $(0.000, 0.000, 0.000)$.

5. **Analytical Re-check & Tolerance Guarantee**:
   $$z_{\text{drift}} = \min_{i} z_i^{(2)}$$
   If $|z_{\text{drift}}| > 10^{-7}\text{m}$, apply $z_i^* = z_i^{(2)} - z_{\text{drift}}$ to guarantee $Z_{\min} \equiv 0.000\text{m}$ to machine epsilon precision.

---

### 2.2 Metric Scale Normalization Strategy

Let raw mesh height after pivot snapping be $H_{\text{raw}} = \max_i z_i^* - \min_i z_i^* = \max_i z_i^*$.  
Let target height be $H_{\text{target}} = \text{species.dimensions.height_m}$.  
Let target spread be $D_{\text{target}} = \text{species.dimensions.canopy_spread_m}$.  
Current spread $D_{\text{raw}} = \max(\Delta X, \Delta Y)$.

#### Mathematical Comparison of Strategies:

| Dimension | Uniform Height Scaling ($S_x=S_y=S_z=S_h$) | Anisotropic Bounds Scaling ($S_x \ne S_y \ne S_z$) | Aspect-Constrained Blended Scaling |
|---|---|---|---|
| **Height Accuracy** | Exact ($H' \equiv H_{\text{target}}$) | Exact ($H' \equiv H_{\text{target}}$) | Exact ($H' \equiv H_{\text{target}}$) |
| **Canopy Spread** | Proportional to model morphology | Exact ($D' \equiv D_{\text{target}}$) | Bounded within $\pm 15\%$ of ground truth |
| **Trunk Cross-Section** | Circular (preserves $r_x = r_y$) | Elliptical/Distorted | Circular (preserves $r_x = r_y$) |
| **Surface Normals** | $\mathbf{n}' = \mathbf{n}$ (unaffected) | Sheared: $\mathbf{n}' = \frac{\mathbf{S}^{-1}\mathbf{n}}{\|\mathbf{S}^{-1}\mathbf{n}\|}$ | Re-normalized on vertical axis |
| **Texture Distortions** | 0% texture stretching | Severe stretching along squashed axis | Max 15% stretching |
| **Natural Morphology** | High photorealism, organic integrity | Unnatural boxy/flattened shapes | Balanced |

#### Optimal Strategy Determination:
- **Default Strategy**: `scaling_strategy="uniform_height"`.  
  Scaling factor:
  $$S = \frac{H_{\text{target}}}{H_{\text{raw}}}$$
  All vertices $\mathbf{v}_i' = S \cdot \mathbf{v}_i^*$.  
  Guarantees exact botanical height matching `catalog.py` ground truth, 0% normal shear, 0% texture stretching, and perfect trunk circularity.
- **Secondary Strategy (Option)**: `scaling_strategy="aspect_constrained"`.  
  Allows bounded horizontal adaptation with clamp $\rho \in [0.85, 1.15]$ while keeping $S_x = S_y$ to prevent elliptical trunk distortion.

---

### 2.3 Dual-Format Production Export Architecture

#### 1. Production GLB (`.glb`):
- **Container Structure**: 12-byte header, JSON chunk (padded with spaces `0x20`), BIN chunk (padded with `0x00`).
- **Binary Buffer Components**:
  1. `POSITION`: float32 vec3 (`pos_data`), bufferView 0, accessor 0 (with exact min/max bounds).
  2. `NORMAL`: float32 vec3 (`norm_data`), bufferView 1, accessor 1.
  3. `TEXCOORD_0`: float32 vec2 (`uv_data`), bufferView 2, accessor 2.
  4. `INDICES`: uint16 (`<H`) if $N \le 65535$ else uint32 (`<I`), bufferView 3, accessor 3.
  5. `ALBEDO_PNG`: encoded PNG bytes, bufferView 4, image 0, texture 0.
  6. `METALLIC_ROUGHNESS_PNG`: encoded ORM PNG bytes (R=255, G=Roughness, B=Metallic), bufferView 5, image 1, texture 1.
  7. `NORMAL_PNG`: encoded Normal map PNG bytes, bufferView 6, image 2, texture 2.
  8. `ROUGHNESS_PNG`: encoded discrete Roughness map PNG bytes, bufferView 7, image 3.
  9. `METALLIC_PNG`: encoded discrete Metallic map PNG bytes, bufferView 8, image 4.
- **Material Specification**:
  ```json
  {
    "name": "Botanical_PBR_Material",
    "doubleSided": true,
    "pbrMetallicRoughness": {
      "baseColorTexture": {"index": 0},
      "metallicRoughnessTexture": {"index": 1},
      "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
      "metallicFactor": 1.0,
      "roughnessFactor": 1.0
    },
    "normalTexture": {"index": 2, "scale": 1.0}
  }
  ```
- **Static Mesh Invariant ($N_{\text{bones}} = 0$)**:
  - `skins`: completely omitted.
  - `animations`: completely omitted.
  - Primitive attributes: zero `JOINTS_0` or `WEIGHTS_0`.

#### 2. Companion Wavefront OBJ (`.obj` + `.mtl`):
- `<species_id>.obj`:
  - Header with species metadata, height, spread, and date.
  - `mtllib <species_id>.mtl` reference.
  - Vertices `v x y z`.
  - Normals `vn nx ny nz`.
  - Texture coordinates `vt u v`.
  - Material invocation `usemtl Botanical_PBR_Material`.
  - Face indices `f v1/vt1/vn1 v2/vt2/vn2 v3/vt3/vn3`.
- `<species_id>.mtl`:
  - `newmtl Botanical_PBR_Material`.
  - `Ka 1.0 1.0 1.0`, `Kd 1.0 1.0 1.0`, `Ks 0.2 0.2 0.2`, `Ns 128.0`, `d 1.0`, `illum 2`.
  - `map_Kd textures/albedo.png`.
  - `map_Bump -bm 1.0 textures/normal.png` and `norm textures/normal.png`.
  - `map_Pr textures/roughness.png`.
  - `map_Pm textures/metallic.png`.
- Texture Directory: `<output_dir>/textures/` storing discrete PNGs:
  - `albedo.png`
  - `normal.png`
  - `roughness.png`
  - `metallic.png`

#### 3. Asset Manifest (`asset_manifest.json`):
- Contains canonical metadata, taxonomy, bounding box metrics, polygon stats, texture paths, and verification status.

---

## 3. Caveats

1. **Degenerate or Flat Height Profile ($H_{\text{raw}} < 0.02\text{m}$)**:
   - For prostrate moss, lichen, or microscopic groundcover, $5\%$ of height ($h_{\text{slice}} = 0.05 \times \Delta Z$) may be less than $1\text{mm}$, potentially containing only 1 or 2 vertices.
   - *Mitigation*: If $|\mathcal{S}_{\text{base}}| < 3$, expand candidate window to $z_i \le \max(h_{\text{slice}}, 0.20 \times \Delta Z)$ or fallback to lowest vertex slice.
2. **glTF vs OBJ Coordinate Axes**:
   - In MorphoMesh, geometry is kept natively in Blender $Z$-up convention. GLB accessor bounds test `pos_acc["min"][2] <= 0.005` confirms that $Z$ is exported as coordinate index 2.
   - For third-party engines requiring glTF $Y$-up, an optional flag `export_y_up: bool = False` can be supported via 90-degree X-rotation matrix $\begin{pmatrix} 1 & 0 & 0 \\ 0 & 0 & -1 \\ 0 & 1 & 0 \end{pmatrix}$, but default remains native $Z$-up to match existing test suites.
3. **PBR Texture Channel Packing**:
   - glTF standard packs Occlusion (R), Roughness (G), Metallic (B). When generating the standalone GLB, we embed both the standard packed ORM map (for glTF engines) and individual channels (for discrete map checkers).
   - In discrete OBJ/MTL, separate textures are linked directly to `textures/roughness.png` and `textures/metallic.png`.
4. **Normal Map Format**:
   - Tangent-space normal maps synthesized or extracted follow OpenGL convention ($+X$ right, $+Y$ up, $+Z$ outward). DirectX format (inverted green) is not used.

---

## 4. Conclusion & Implementation Blueprints

### 4.1 Data Models & Interface Contracts

```python
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Union
from pydantic import BaseModel, ConfigDict, Field
from PIL import Image

class NormalizationConfig(BaseModel):
    """Configuration options for asset normalization and export."""
    model_config = ConfigDict(extra="ignore")

    scaling_strategy: Literal["uniform_height", "aspect_constrained", "exact_bounds"] = "uniform_height"
    aspect_constraint_clamp: float = 0.15
    base_slice_ratio: float = 0.05
    tolerance_ground_m: float = 1e-4
    enable_double_sided: bool = True
    embed_all_pbr_textures: bool = True
    up_axis: Literal["Z", "Y"] = "Z"


class ExportedAsset(BaseModel):
    """Post-processed and normalized botanical asset conforming to M3 <-> M4 Contract."""
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore")

    species_id: str
    category_id: str
    glb_path: Path
    obj_path: Path
    mtl_path: Path
    texture_paths: Dict[str, Path]
    manifest_path: Path
    vertex_count: int = Field(ge=0)
    face_count: int = Field(ge=0)
    height_m: float = Field(gt=0.0)
    canopy_spread_m: float = Field(gt=0.0)
    ground_pivot_z: float = Field(default=0.0)
    base_centroid: Tuple[float, float] = Field(default=(0.0, 0.0))
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

### 4.2 Complete Reference Code Implementation (`vegetation_pipeline/post_processor.py`)

The Worker should create `teamwork_projects/vegetation_library/vegetation_pipeline/post_processor.py` based on the following modular implementation:

```python
"""
Vegetation Library - Asset Post-Processing, Normalization & Multi-Format Export
File: teamwork_projects/vegetation_library/vegetation_pipeline/post_processor.py
"""
from __future__ import annotations

import io
import json
import logging
import math
import os
from pathlib import Path
import struct
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import numpy as np
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field

from morphomesh.geometry.mesh import MeshGeometry
from morphomesh.geometry.exporters import pad_4
from vegetation_pipeline.catalog import PlantSpecies, get_species
from vegetation_pipeline.generator import RawAsset, unpack_glb_header_and_json

logger = logging.getLogger("vegetation_pipeline.post_processor")


# ==============================================================================
# DATA MODELS
# ==============================================================================

class NormalizationConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    scaling_strategy: Literal["uniform_height", "aspect_constrained", "exact_bounds"] = "uniform_height"
    aspect_constraint_clamp: float = 0.15
    base_slice_ratio: float = 0.05
    tolerance_ground_m: float = 1e-4
    enable_double_sided: bool = True
    embed_all_pbr_textures: bool = True


class ExportedAsset(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore")

    species_id: str
    category_id: str
    glb_path: Path
    obj_path: Path
    mtl_path: Path
    texture_paths: Dict[str, Path]
    manifest_path: Path
    vertex_count: int = Field(ge=0)
    face_count: int = Field(ge=0)
    height_m: float = Field(gt=0.0)
    canopy_spread_m: float = Field(gt=0.0)
    ground_pivot_z: float = Field(default=0.0)
    base_centroid: Tuple[float, float] = Field(default=(0.0, 0.0))
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ==============================================================================
# GEOMETRY MATHEMATICAL ALGORITHMS
# ==============================================================================

def compute_mesh_extents(mesh: MeshGeometry) -> Dict[str, float]:
    """Computes tight axis-aligned bounding box coordinates and dimensions."""
    if not mesh.vertices:
        return {"min_x": 0.0, "max_x": 0.0, "min_y": 0.0, "max_y": 0.0, "min_z": 0.0, "max_z": 0.0,
                "dx": 0.0, "dy": 0.0, "dz": 0.0, "spread": 0.0}

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

    # Step 1: Ground contact shift
    min_z = min(v[2] for v in mesh.vertices)
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
) -> Tuple[MeshGeometry, float, float]:
    """
    Scales mesh geometry to match botanical dimensions from catalog.py.
    Default: Uniform height scaling (preserves 100% natural organic morphology,
    trunk circularity, and normal vector orthogonality).
    """
    if not mesh.vertices:
        return mesh, 0.0, 0.0

    ext = compute_mesh_extents(mesh)
    current_h = ext["dz"]
    if current_h < 1e-5:
        return mesh, 0.0, 0.0

    target_h = species.dimensions.height_m
    target_spread = species.dimensions.canopy_spread_m

    scale_z = target_h / current_h

    if strategy == "uniform_height":
        scale_x = scale_y = scale_z
    elif strategy == "aspect_constrained":
        current_spread = max(1e-5, ext["spread"])
        raw_spread_scale = target_spread / current_spread
        ratio = raw_spread_scale / scale_z
        clamped_ratio = float(np.clip(ratio, 1.0 - aspect_clamp, 1.0 + aspect_clamp))
        scale_x = scale_y = scale_z * clamped_ratio
    elif strategy == "exact_bounds":
        dx = max(1e-5, ext["dx"])
        dy = max(1e-5, ext["dy"])
        scale_x = target_spread / dx
        scale_y = target_spread / dy
    else:
        scale_x = scale_y = scale_z

    # Apply scaling transformation
    mesh.vertices = [(v[0] * scale_x, v[1] * scale_y, v[2] * scale_z) for v in mesh.vertices]

    # Re-normalize normal vectors if anisotropic scaling was used
    if abs(scale_x - scale_z) > 1e-4 or abs(scale_y - scale_z) > 1e-4:
        new_normals = []
        for n in mesh.normals:
            # Transform normal by inverse transpose: (nx/sx, ny/sy, nz/sz)
            tx = n[0] / scale_x
            ty = n[1] / scale_y
            tz = n[2] / scale_z
            norm_len = math.sqrt(tx * tx + ty * ty + tz * tz)
            if norm_len > 1e-6:
                new_normals.append((tx / norm_len, ty / norm_len, tz / norm_len))
            else:
                new_normals.append((0.0, 0.0, 1.0))
        mesh.normals = new_normals

    new_ext = compute_mesh_extents(mesh)
    return mesh, new_ext["dz"], new_ext["spread"]


# ==============================================================================
# GLB IMPORT / PARSING UTILITY
# ==============================================================================

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
            positions = [(pos_floats[i*3], pos_floats[i*3+1], pos_floats[i*3+2]) for i in range(count)]

            if norm_idx is not None and norm_idx < len(accessors):
                norm_acc = accessors[norm_idx]
                norm_bv = buffer_views[norm_acc["bufferView"]]
                norm_offset = norm_bv.get("byteOffset", 0) + norm_acc.get("byteOffset", 0)
                norm_floats = struct.unpack_from(f"<{count * 3}f", bin_bytes, norm_offset)
                normals = [(norm_floats[i*3], norm_floats[i*3+1], norm_floats[i*3+2]) for i in range(count)]
            else:
                normals = [(0.0, 0.0, 1.0)] * count

            if uv_idx is not None and uv_idx < len(accessors):
                uv_acc = accessors[uv_idx]
                uv_bv = buffer_views[uv_acc["bufferView"]]
                uv_offset = uv_bv.get("byteOffset", 0) + uv_acc.get("byteOffset", 0)
                uv_floats = struct.unpack_from(f"<{count * 2}f", bin_bytes, uv_offset)
                uvs = [(uv_floats[i*2], uv_floats[i*2+1]) for i in range(count)]
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
                    mesh.add_triangle(indices[i] + v_offset, indices[i+1] + v_offset, indices[i+2] + v_offset)
            else:
                for i in range(0, count - 2, 3):
                    mesh.add_triangle(v_offset + i, v_offset + i + 1, v_offset + i + 2)

    return mesh


# ==============================================================================
# MULTI-FORMAT EXPORTERS
# ==============================================================================

def pack_metallic_roughness(roughness: Image.Image, metallic: Image.Image) -> Image.Image:
    """Packs Roughness (G) and Metallic (B) into glTF 2.0 ORM texture."""
    target_size = roughness.size
    r_img = roughness.convert("L")
    m_img = metallic.convert("L").resize(target_size, Image.Resampling.BILINEAR)

    r_arr = np.array(r_img, dtype=np.uint8)
    m_arr = np.array(m_img, dtype=np.uint8)
    h, w = r_arr.shape
    occ_arr = np.full((h, w), 255, dtype=np.uint8)

    packed = np.dstack([occ_arr, r_arr, m_arr])
    return Image.fromarray(packed, mode="RGB")


def export_production_glb(
    mesh: MeshGeometry,
    filepath: Union[str, Path],
    textures: Dict[str, Image.Image],
    species_id: str = "botanical_asset",
    double_sided: bool = True,
) -> Path:
    """
    Exports production GLB with embedded PBR textures, doubleSided foliage,
    and strictly ZERO skeletal armatures (N_bones = 0).
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    num_verts = len(mesh.vertices)
    num_indices = len(mesh.faces) * 3

    # Flatten geometric data
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

    albedo_img = textures.get("albedo") or textures.get("baseColor") or Image.new("RGB", (512, 512), (45, 105, 35))
    normal_img = textures.get("normal") or Image.new("RGB", (512, 512), (128, 128, 255))
    roughness_img = textures.get("roughness") or Image.new("L", (512, 512), 178)
    metallic_img = textures.get("metallic") or Image.new("L", (512, 512), 0)

    orm_img = pack_metallic_roughness(roughness_img, metallic_img)

    b_albedo = _to_png_bytes(albedo_img)
    b_orm = _to_png_bytes(orm_img)
    b_normal = _to_png_bytes(normal_img)
    b_roughness = _to_png_bytes(roughness_img)
    b_metallic = _to_png_bytes(metallic_img)

    # Pack bufferViews with 4-byte padding
    buffers_data = [
        (pos_data, 34962),      # BV 0: Position
        (norm_data, 34962),     # BV 1: Normal
        (uv_data, 34962),       # BV 2: UV
        (idx_data, 34963),      # BV 3: Indices
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
    min_x = min(v[0] for v in mesh.vertices) if mesh.vertices else 0.0
    max_x = max(v[0] for v in mesh.vertices) if mesh.vertices else 0.0
    min_y = min(v[1] for v in mesh.vertices) if mesh.vertices else 0.0
    max_y = max(v[1] for v in mesh.vertices) if mesh.vertices else 0.0
    min_z = min(v[2] for v in mesh.vertices) if mesh.vertices else 0.0
    max_z = max(v[2] for v in mesh.vertices) if mesh.vertices else 0.0

    accessors = [
        {"bufferView": 0, "componentType": 5126, "count": num_verts, "type": "VEC3",
         "min": [min_x, min_y, min_z], "max": [max_x, max_y, max_z]},
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
            "name": f"{species_id}_PBR_Material",
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

    # 1. Save discrete PNG textures
    texture_paths: Dict[str, Path] = {}
    for key in ("albedo", "normal", "roughness", "metallic"):
        img = textures.get(key)
        if img is None:
            if key == "albedo":
                img = textures.get("baseColor") or Image.new("RGB", (512, 512), (45, 105, 35))
            elif key == "normal":
                img = Image.new("RGB", (512, 512), (128, 128, 255))
            elif key == "roughness":
                img = Image.new("L", (512, 512), 178)
            else:
                img = Image.new("L", (512, 512), 0)
        p = tex_dir / f"{key}.png"
        img.save(p)
        texture_paths[key] = p

    # 2. Write MTL Material File
    mat_name = f"{species_id}_Material"
    with open(mtl_filepath, "w", encoding="utf-8") as f:
        f.write(f"# MorphoMesh Botanical Material Library\n")
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
        f.write(f"# MorphoMesh Botanical Asset Library\n")
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
                f"f {face[0]+1}/{face[0]+1}/{face[0]+1} "
                f"{face[1]+1}/{face[1]+1}/{face[1]+1} "
                f"{face[2]+1}/{face[2]+1}/{face[2]+1}\n"
            )

    return obj_filepath, mtl_filepath, texture_paths


# ==============================================================================
# MASTER POST-PROCESSOR PIPELINE
# ==============================================================================

class AssetPostProcessor:
    """Coordinates ground pivot snapping, metric scaling, and multi-format export."""

    def __init__(self, config: Optional[NormalizationConfig] = None) -> None:
        self.config = config if config is not None else NormalizationConfig()

    def process_and_export(
        self,
        raw_asset: RawAsset,
        species: PlantSpecies,
        output_dir: Optional[Union[str, Path]] = None,
    ) -> ExportedAsset:
        """Executes full normalization and dual-format export workflow."""
        out_path = Path(output_dir) if output_dir is not None else (
            Path("./output") / species.short_category / species.species_id
        )
        out_path.mkdir(parents=True, exist_ok=True)

        # 1. Acquire MeshGeometry
        if raw_asset.mesh is not None:
            mesh = raw_asset.mesh
        else:
            mesh = load_mesh_from_glb(raw_asset.glb_path)

        # 2. Acquire Textures
        textures = dict(raw_asset.textures)
        if not textures and raw_asset.texture_paths:
            for k, p in raw_asset.texture_paths.items():
                if p.exists():
                    textures[k] = Image.open(p)

        # Fallback defaults for missing channels
        if "albedo" not in textures and "baseColor" not in textures:
            textures["albedo"] = Image.new("RGB", (512, 512), (45, 105, 35))
        if "normal" not in textures:
            textures["normal"] = Image.new("RGB", (512, 512), (128, 128, 255))
        if "roughness" not in textures:
            textures["roughness"] = Image.new("L", (512, 512), 178)
        if "metallic" not in textures:
            textures["metallic"] = Image.new("L", (512, 512), 0)

        # 3. Ground Pivot Snapping & Centering
        mesh, base_centroid, ground_z = snap_ground_pivot_and_center(
            mesh, base_slice_ratio=self.config.base_slice_ratio
        )

        # 4. Metric Scale Normalization
        mesh, final_h, final_spread = normalize_metric_scale(
            mesh,
            species=species,
            strategy=self.config.scaling_strategy,
            aspect_clamp=self.config.aspect_constraint_clamp,
        )

        # Guarantee post-scaling ground pivot remains strictly at Z_min = 0.000m
        z_min_recheck = min(v[2] for v in mesh.vertices) if mesh.vertices else 0.0
        if abs(z_min_recheck) > 1e-7:
            mesh.vertices = [(v[0], v[1], v[2] - z_min_recheck) for v in mesh.vertices]
            ground_z = 0.0

        # 5. Dual-Format Export
        glb_path = out_path / f"{species.species_id}.glb"
        export_production_glb(
            mesh=mesh,
            filepath=glb_path,
            textures=textures,
            species_id=species.species_id,
            double_sided=self.config.enable_double_sided,
        )

        obj_path = out_path / f"{species.species_id}.obj"
        obj_p, mtl_p, tex_paths = export_companion_obj_mtl(
            mesh=mesh,
            obj_filepath=obj_path,
            textures=textures,
            species_id=species.species_id,
        )

        # 6. Generate Asset Manifest
        manifest_path = out_path / "asset_manifest.json"
        manifest_data = {
            "species_id": species.species_id,
            "category_id": species.category_id,
            "common_name": species.common_name,
            "scientific_name": species.scientific_name,
            "vertex_count": len(mesh.vertices),
            "face_count": len(mesh.faces),
            "dimensions_m": {
                "height": round(final_h, 4),
                "canopy_spread": round(final_spread, 4),
            },
            "ground_pivot_z": round(ground_z, 6),
            "base_centroid": [round(base_centroid[0], 6), round(base_centroid[1], 6)],
            "files": {
                "glb": str(glb_path.name),
                "obj": str(obj_p.name),
                "mtl": str(mtl_p.name),
                "textures": {k: str(p.relative_to(out_path)) for k, p in tex_paths.items()},
            },
            "source_provenance": raw_asset.source,
            "double_sided_material": self.config.enable_double_sided,
            "static_mesh_guarantee": True,
        }
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        return ExportedAsset(
            species_id=species.species_id,
            category_id=species.category_id,
            glb_path=glb_path,
            obj_path=obj_p,
            mtl_path=mtl_p,
            texture_paths=tex_paths,
            manifest_path=manifest_path,
            vertex_count=len(mesh.vertices),
            face_count=len(mesh.faces),
            height_m=final_h,
            canopy_spread_m=final_spread,
            ground_pivot_z=ground_z,
            base_centroid=base_centroid,
            metadata=manifest_data,
        )


def process_and_export(
    raw_asset: RawAsset,
    species: PlantSpecies,
    output_dir: Optional[Union[str, Path]] = None,
    config: Optional[NormalizationConfig] = None,
) -> ExportedAsset:
    """Convenience standalone dispatch conforming to PROJECT.md interface contract."""
    processor = AssetPostProcessor(config=config)
    return processor.process_and_export(raw_asset, species, output_dir=output_dir)
```

---

## 5. Verification Method

To independently verify the mathematical formulas and exporter implementations:

1. **Ground Pivot Snapping & Centering**:
   - Run test assertions:
     ```python
     zs = [v[2] for v in exported_mesh.vertices]
     assert abs(min(zs)) <= 0.0001, "Ground pivot Z_min must be 0.0 within 0.1mm"
     
     h = max(zs) - min(zs)
     base_slice = [v for v in exported_mesh.vertices if v[2] <= 0.05 * h]
     mean_x = np.mean([v[0] for v in base_slice])
     mean_y = np.mean([v[1] for v in base_slice])
     assert abs(mean_x) <= 0.005, f"Base centroid X={mean_x} exceeds 5mm"
     assert abs(mean_y) <= 0.005, f"Base centroid Y={mean_y} exceeds 5mm"
     ```
2. **Metric Scale Normalization**:
   - Check that `abs(max(zs) - species.dimensions.height_m) < 1e-4` under uniform scaling.
   - Assert that ratio $\frac{x_{\max} - x_{\min}}{y_{\max} - y_{\min}}$ is identical before and after uniform scaling.
3. **GLB Production Container Inspection**:
   - Parse GLB via `unpack_glb_header_and_json(glb_path)`:
     - `assert gltf.get("skins") is None` (zero bones/armatures).
     - `assert gltf.get("animations") is None`.
     - `assert gltf["materials"][0]["doubleSided"] is True`.
     - `assert len(gltf["images"]) >= 4`.
     - `assert gltf["accessors"][0]["min"][2] <= 0.0001`.
4. **OBJ + MTL Companion Verification**:
   - Verify that `<species_id>.obj` contains `mtllib <species_id>.mtl` and `usemtl <species_id>_Material`.
   - Verify that `<species_id>.mtl` contains `map_Kd textures/albedo.png`, `norm textures/normal.png`, `map_Pr textures/roughness.png`, `map_Pm textures/metallic.png`.
   - Verify all 4 referenced PNG files exist on disk in `textures/` and are readable PIL images.
5. **Execution Command**:
   ```powershell
   pytest teamwork_projects/vegetation_library/tests/test_normalization.py -v
   ```
