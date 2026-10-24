# Milestone 3 (M3) Software Architecture & Packaging Specification
## Asset Post-Processing, Metric Normalization & Multi-Format Export
**Author**: Explorer 1 (M3 Vegetation Architecture)  
**Target File**: `teamwork_projects/vegetation_library/vegetation_pipeline/post_processor.py`  
**Working Directory**: `E:\tool\mcp\MorphoMesh\.agents\m3_veg_explorer_1`  
**Date**: 2026-09-10  

---

## 1. Observation

### 1.1 Existing Codebase & Interface Analysis
1. **M2 Generator Output Contract (`generator.py`)**:
   - `RawAsset` is defined at lines 117–156 of `teamwork_projects/vegetation_library/vegetation_pipeline/generator.py`:
     ```python
     class RawAsset(BaseModel):
         model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore")
         species_id: str
         glb_path: Path
         mesh: Optional[MeshGeometry] = None
         textures: Dict[str, Image.Image] = Field(default_factory=dict)
         texture_paths: Dict[str, Path] = Field(default_factory=dict)
         source: Literal["meshy", "procedural", "cached"]
         vertex_count: int = 0
         face_count: int = 0
         thumbnail_path: Optional[Path] = None
         metadata: Dict[str, Any] = Field(default_factory=dict)
     ```
   - For procedural generation (`ProceduralBotanicalGenerator.generate`), `raw_asset.mesh` contains a live `MeshGeometry` instance with vertices, normals, uvs, and triangular/quad faces.
   - For Meshy AI generation or disk-cached assets, `raw_asset.mesh` may be `None`, with the primary 3D container located at `raw_asset.glb_path`.
   - `generator.py` provides standalone binary glTF 2.0 parsers: `unpack_glb_header_and_json(glb_path)` (lines 55–82) and `parse_glb_vertex_and_face_counts(glb_path)` (lines 85–111).
   - In `ProceduralBotanicalGenerator._enforce_mesh_invariants` (lines 1327–1350), an initial pivot shift was implemented:
     ```python
     z_min = min(v[2] for v in mesh.vertices)
     mesh.vertices = [(v[0], v[1], v[2] - z_min) for v in mesh.vertices]
     current_h = max(v[2] for v in mesh.vertices)
     base_verts = [v for v in mesh.vertices if v[2] <= 0.05 * current_h]
     cx = sum(v[0] for v in base_verts) / len(base_verts)
     cy = sum(v[1] for v in base_verts) / len(base_verts)
     mesh.vertices = [(v[0] - cx, v[1] - cy, v[2]) for v in mesh.vertices]
     ```

2. **Botanical Taxonomy & Dimensions Contract (`catalog.py`)**:
   - `catalog.py` defines `PlantSpecies` (lines 131–166) with `DimensionsSpec` (lines 42–73):
     - `height_m: float`: mature reference height (e.g., English Oak = 12.0m, Rose Bush = 1.4m, Boston Fern = 0.6m).
     - `canopy_spread_m: float`: crown or foliage spread diameter (e.g., Oak = 10.0m, Rose = 1.2m, Fern = 0.8m).
     - `trunk_stem_diameter_m: float`: base trunk/stem diameter.
   - Property `species.short_category` (line 158–160) maps long category IDs (e.g. `broadleaf_deciduous_trees`, `conifers_evergreens`) to clean directory slugs: `broadleaf_trees`, `conifers`, `tropical`, `shrubs`, `groundcover`, `succulents`, `vines`.

3. **M3 & M4 Project Specification Contracts (`PROJECT.md`)**:
   - `PROJECT.md` line 13–16:
     > "Computes bottom 5% contact centroid to ground root pivot at $Z_{\min} = 0.0$ (Blender) / $Y_{\min} = 0.0$ (glTF). Normalizes metric scale according to catalog height/canopy targets. Exports production `.glb` (glTF 2.0 binary with embedded PBR textures) and companion `.obj`/`.mtl`."
   - `PROJECT.md` line 77–84 (M3 ↔ M4 Contract):
     > `process_and_export(raw_asset: RawAsset, species: PlantSpecies, output_dir: Path) -> ExportedAsset`
     > Outputs:
     > - `<species_id>.glb` (glTF 2.0 binary with embedded PBR textures, $Y_{\min} \approx 0$ / $Z_{\min} \approx 0$)
     > - `<species_id>.obj` + `<species_id>.mtl` (Wavefront OBJ with materials)
     > - `textures/` (`albedo.png`, `normal.png`, `roughness.png`, `metallic.png`)
     > - `asset_manifest.json` (metadata, bounding box, vertex/face count)
     > Returns `ExportedAsset(glb_path, obj_path, texture_paths, manifest_path)`

4. **Runtime Environment & Dependency Constraints**:
   - Executed `& "C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe" -c "import trimesh"`:
     Result: `ModuleNotFoundError: No module named 'trimesh'`.
   - Executed `pip list`: verified Python 3.11.9 has `pydantic` (2.12.5), `numpy` (2.2.6), `pillow` (12.3.0), `scipy` (1.16.3), and `pytest` (9.1.0).
   - Executed `pytest teamwork_projects/vegetation_library/tests/`: 148 passed in 5.53 seconds (`test_catalog.py` and `test_generator.py`).
   - `post_processor.py` MUST be written using pure Python standard library (`struct`, `json`, `io`, `pathlib`, `math`) + `numpy`, `PIL.Image`, and `pydantic`. Zero dependency on `trimesh` or external binaries.

---

## 2. Logic Chain

### 2.1 From RawAsset to ExportedAsset: The Normalization Pipeline
1. **Mesh Ingestion & Immutability**:
   - An incoming `RawAsset` may have `raw_asset.mesh` (a `MeshGeometry` instance) or `raw_asset.mesh = None` (with a `.glb` on disk).
   - The post-processor must not mutate the incoming `raw_asset.mesh`. It must create a working copy.
   - If `raw_asset.mesh` is None, `_extract_mesh_from_glb` parses the POSITION, NORMAL, TEXCOORD_0, and index accessors from the binary GLB into a new `MeshGeometry` instance.
2. **Ground Pivot Snapping**:
   - Botanical assets in game engines (Unreal, Unity, Godot) and DCC tools (Blender) must be placed directly on terrain surfaces with zero offset.
   - The lowest vertex coordinate $Z_{\min} = \min_{v \in V} v_z$ is identified.
   - All vertices are translated vertically: $v'_z = v_z - Z_{\min}$, ensuring $Z_{\min} \equiv 0.0000$m within a strict $\pm 0.001$m tolerance.
3. **Base Contact Centering (Bottom 5% Height Slice)**:
   - Plant stems/trunks are not necessarily centered at the overall canopy bounding box center (e.g. leaning trees, asymmetrical crowns, weeping willows).
   - Centering the entire bounding box would cause the trunk base to float off-center, producing unrealistic rotations when placed on terrain.
   - Therefore, the contact slice is calculated: $Z \in [Z_{\min}, Z_{\min} + 0.05 \times (Z_{\max} - Z_{\min})]$.
   - The centroid $(c_x, c_y) = (\frac{1}{K}\sum_{i=1}^K x_i, \frac{1}{K}\sum_{i=1}^K y_i)$ of these base vertices is computed.
   - All vertices are translated horizontally: $v'_x = v_x - c_x$, $v'_y = v_y - c_y$.
   - A final pass reaffirms $Z_{\min} \equiv 0.0000$m.
4. **Metric Scale Normalization**:
   - Raw generative AI or procedural meshes may have arbitrary non-physical bounding boxes.
   - The post-processor measures the current height $H_{\text{curr}} = Z_{\max} - Z_{\min}$.
   - The catalog target height $H_{\text{target}} = species.dimensions.height_m$ provides the physical ground truth.
   - Proportional uniform scale factor $s = H_{\text{target}} / H_{\text{curr}}$ is applied uniformly across $X, Y, Z$: $(x'', y'', z'') = (s \cdot x', s \cdot y', s \cdot z')$.
   - Uniform scaling preserves the natural biological aspect ratio (height-to-width ratio) and prevents artificial squashing or stretching.
   - Measured actual dimensions are recorded: $H_{\text{actual}} = Z_{\max} - Z_{\min}$, Canopy Spread $S_{\text{actual}} = \max(X_{\max} - X_{\min}, Y_{\max} - Y_{\min})$.
5. **Dual-Format Production Export**:
   - **Production GLB**:
     - Modern real-time engines demand embedded PBR textures in a single `.glb` file.
     - The glTF 2.0 PBR standard requires BaseColor, Normal, and packed ORM (Occlusion in Red, Roughness in Green, Metallic in Blue).
     - The post-processor packs Roughness and Metallic maps into an ORM image, serializes Albedo, Normal, and ORM PNG buffers, creates glTF bufferViews and images, and emits a self-contained, 4-byte-aligned `.glb` file.
     - Foliage material must explicitly set `"doubleSided": true` so leaf cards render from both sides without backface culling.
     - The glTF container strictly enforces $N_{\text{bones}} = 0$ (no `skins`, no `animations`, no `JOINTS_*`/`WEIGHTS_*` attributes).
   - **Companion Wavefront OBJ & MTL**:
     - Legacy DCC tools and interchange pipelines require standard Wavefront `.obj` and `.mtl`.
     - The post-processor exports 1-indexed vertex positions (`v`), texture coordinates (`vt`), unit normals (`vn`), and faces (`f`).
     - It creates `<species_id>.mtl` linking relative texture paths (`map_Kd textures/albedo.png`, `map_Bump textures/normal.png`, `map_Pr textures/roughness.png`, `map_Pm textures/metallic.png`).
6. **Directory Hierarchy Packaging**:
   - Strict adherence to `output/<short_category>/<species_id>/` layout.
   - Writes `<species_id>.glb`, `<species_id>.obj`, `<species_id>.mtl`, `textures/` (4 PNGs), and `asset_manifest.json`.

---

## 3. Caveats

1. **Orientation Conventions ($Z$-up vs $Y$-up)**:
   - In MorphoMesh core (`MeshGeometry` and `generator.py`), the coordinate system is Blender-standard $Z$-up ($Z$ is vertical height).
   - In standard glTF 2.0 viewer space, $Y$ is typically up. However, `morphomesh.geometry.exporters.export_glb` and all existing tests in `test_generator.py` store vertices in $(X, Y, Z)$ where $Z$ is vertical height ($Z_{\min} = 0.0$).
   - To maintain 100% interoperability with existing M2 tests and Blender bridge, `MeshGeometry` uses $Z$-up, with $Z_{\min} = 0.0$ grounded at the root base.
2. **Double-Sided Material Rendering**:
   - Plant foliage leaf cards (e.g. tree leaves, fern fronds, grass blades) have zero thickness. If glTF `doubleSided` is false, leaves will disappear when viewed from behind in standard glTF viewers.
   - `AssetPostProcessor` must set `"doubleSided": true` on all generated glTF materials by default.
3. **Texture Channel Modes**:
   - Albedo and Normal must be saved in RGB mode (`Image.open(...).convert("RGB")`).
   - Roughness and Metallic are single-channel grayscale maps and should be saved in `L` mode (`Image.open(...).convert("L")`) on disk, while packed into the G and B channels of the ORM texture inside the GLB.
4. **Idempotency**:
   - If an already-grounded and already-normalized asset is passed into `process_asset`, the resulting geometry and files must remain stable within numerical tolerance ($< 1e-6$).

---

## 4. Conclusion & Architectural Specifications

### 4.1 Data Models Specification (`post_processor.py`)

```python
from __future__ import annotations

import json
import logging
import math
import os
from pathlib import Path
import struct
import time
from typing import Any, Dict, List, Literal, Optional, Tuple, Union
from datetime import datetime, timezone

import numpy as np
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field, field_validator


class AssetDimensions(BaseModel):
    """Normalized physical dimensions and bounding box in metric units."""
    model_config = ConfigDict(extra="ignore")

    height_m: float = Field(..., gt=0.0, description="Measured mature height in meters (Z-axis)")
    canopy_spread_m: float = Field(..., gt=0.0, description="Crown or foliage spread diameter (max(width, depth))")
    width_m: float = Field(..., gt=0.0, description="X-axis bounding extent in meters")
    depth_m: float = Field(..., gt=0.0, description="Y-axis bounding extent in meters")
    target_height_m: float = Field(..., gt=0.0, description="Catalog reference height target")
    target_canopy_spread_m: float = Field(..., gt=0.0, description="Catalog reference canopy spread target")
    bbox_min: List[float] = Field(..., description="[x_min, y_min, z_min] bounding box minimum")
    bbox_max: List[float] = Field(..., description="[x_max, y_max, z_max] bounding box maximum")

    def __getitem__(self, item: str) -> Any:
        """Allow dict-style key access for backward compatibility."""
        return getattr(self, item)


class PostProcessorConfig(BaseModel):
    """Configuration options for AssetPostProcessor normalization and export."""
    model_config = ConfigDict(extra="ignore")

    ground_tolerance_m: float = Field(default=0.005, description="Max deviation from Z_min = 0.0 (5mm)")
    base_centroid_ratio: float = Field(default=0.05, description="Bottom height fraction for contact centroid (5%)")
    centering_tolerance_m: float = Field(default=0.05, description="Max horizontal offset for base centroid (5cm)")
    scale_strategy: Literal["height_proportional", "canopy_proportional", "anisotropic", "none"] = Field(
        default="height_proportional",
        description="Scaling strategy to match catalog dimensions"
    )
    double_sided_materials: bool = Field(default=True, description="Enable two-sided leaf rendering in glTF")
    embed_textures_in_glb: bool = Field(default=True, description="Embed all 4 PBR textures in production GLB")
    export_obj_mtl: bool = Field(default=True, description="Export companion Wavefront OBJ and MTL files")
    export_texture_files: bool = Field(default=True, description="Export standalone PNG textures in textures/")
    export_manifest: bool = Field(default=True, description="Generate asset_manifest.json")
    texture_format: Literal["png", "jpeg"] = Field(default="png", description="Format for texture disk files")


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
        description="Dictionary mapping 'albedo', 'normal', 'roughness', 'metallic' to file paths"
    )
    manifest_path: Path = Field(..., description="Path to companion asset_manifest.json")
    dimensions: AssetDimensions = Field(..., description="Normalized metric dimensions and bounding box")
    vertex_count: int = Field(..., ge=0, description="Total normalized vertex count")
    face_count: int = Field(..., ge=0, description="Total normalized face/triangle count")
    source: Literal["meshy", "procedural", "cached"] = Field(..., description="Source generation engine")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Generation metadata and provenance")

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
```

---

### 4.2 AssetPostProcessor Class Architecture

```python
class AssetPostProcessor:
    """
    Production post-processing, metric normalization, and multi-format packaging engine.
    Transforms un-normalized RawAsset into fully standardized ExportedAsset.
    """

    def __init__(self, config: Optional[PostProcessorConfig] = None) -> None:
        self.config = config.model_copy() if config is not None else PostProcessorConfig()

    def process_asset(
        self,
        raw_asset: RawAsset,
        species: Union[PlantSpecies, str],
        output_dir: Optional[Union[str, Path]] = None,
    ) -> ExportedAsset:
        """
        Master normalization and multi-format export entry point.
        
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
        12. Return validated ExportedAsset.
        """
        ...
```

---

### 4.3 Asset Directory Hierarchy Packaging

All botanical assets must strictly follow the directory packaging layout below:

```
output/
└── <short_category>/                       # e.g., broadleaf_trees, conifers, tropical, shrubs, groundcover, succulents, vines
    └── <species_id>/                       # e.g., veg_tree_oak_01
        ├── <species_id>.glb                # Production glTF 2.0 binary with embedded 4-channel PBR textures & doubleSided
        ├── <species_id>.obj                # Companion Wavefront OBJ (1-indexed, v, vt, vn, f)
        ├── <species_id>.mtl                # Wavefront Material Template Library referencing textures/
        ├── textures/
        │   ├── albedo.png                  # BaseColor map (RGB 8-bit, 512x512 or 1024x1024)
        │   ├── normal.png                  # Tangent-space Normal map (RGB 8-bit, dominant +Z)
        │   ├── roughness.png               # Roughness map (Grayscale L 8-bit)
        │   └── metallic.png                # Metallic map (Grayscale L 8-bit, strictly dielectric <= 0.05)
        └── asset_manifest.json             # Rich JSON manifest detailing taxonomy, geometry, dimensions, files
```

---

### 4.4 Exact Schema for `asset_manifest.json`

The file `<output_dir>/<species_id>/asset_manifest.json` must conform to the following schema:

```json
{
  "schema_version": "1.0.0",
  "species_id": "veg_tree_oak_01",
  "taxonomy": {
    "common_name": "English Oak",
    "scientific_name": "Quercus robur",
    "family": "Fagaceae",
    "category_id": "broadleaf_deciduous_trees",
    "category_name": "Broadleaf & Deciduous Trees",
    "short_category": "broadleaf_trees",
    "biome": "Temperate Deciduous Forest",
    "growth_habit": "tree",
    "branching_pattern": "deliquescent",
    "foliage_density": "dense"
  },
  "geometry": {
    "vertex_count": 8420,
    "face_count": 12850,
    "triangle_count": 12850,
    "quad_count": 4210,
    "quad_ratio": 0.655,
    "has_armature": false,
    "has_skins": false,
    "pivot_grounded": true,
    "ground_z_min_m": 0.0,
    "base_contact_centroid": [0.0012, -0.0008],
    "bounding_box": {
      "min_point": [-4.8512, -4.7219, 0.0],
      "max_point": [4.9124, 4.8812, 12.0000]
    },
    "dimensions_m": {
      "height_m": 12.0000,
      "canopy_spread_m": 9.7636,
      "width_m": 9.7636,
      "depth_m": 9.6031,
      "target_height_m": 12.0,
      "target_canopy_spread_m": 10.0
    }
  },
  "materials": {
    "workflow": "Metallic-Roughness PBR",
    "double_sided": true,
    "channels": ["albedo", "normal", "roughness", "metallic"],
    "texture_resolution": [512, 512]
  },
  "files": {
    "glb": "veg_tree_oak_01.glb",
    "obj": "veg_tree_oak_01.obj",
    "mtl": "veg_tree_oak_01.mtl",
    "textures": {
      "albedo": "textures/albedo.png",
      "normal": "textures/normal.png",
      "roughness": "textures/roughness.png",
      "metallic": "textures/metallic.png"
    }
  },
  "source": "procedural",
  "created_at": "2026-09-10T06:25:00Z",
  "generator_metadata": {
    "seed": 42
  }
}
```

---

### 4.5 Step-by-Step Implementation Algorithms

#### Algorithm 1: Pure-Python GLB Geometry Ingestion (`_extract_mesh_from_glb`)
When `raw_asset.mesh` is None, unpack geometry from `raw_asset.glb_path`:
1. Call `unpack_glb_header_and_json(glb_path)` to retrieve `gltf` dict and `bin_bytes`.
2. Locate `gltf["meshes"][0]["primitives"][0]`.
3. Extract `POSITION` accessor -> unpack `count * 3` floats (`<fff`) using `accessors` and `bufferViews` byte offsets.
4. Extract `NORMAL` accessor -> unpack `count * 3` floats (`<fff`). If absent, compute per-vertex averaged surface normals from face triangles.
5. Extract `TEXCOORD_0` accessor -> unpack `count * 2` floats (`<ff>`). If absent, assign default cylindrical coordinates $(u = \text{atan2}(y, x)/(2\pi) + 0.5, v = z/H)$.
6. Extract `indices` accessor -> unpack uint16 (`<H`) or uint32 (`<I`) triangle indices.
7. Construct and return `MeshGeometry`.

#### Algorithm 2: Ground Pivot Snapping & Base Centering (`_snap_and_center`)
```python
def _snap_and_center(
    mesh: MeshGeometry,
    base_ratio: float = 0.05
) -> Tuple[MeshGeometry, List[float], List[float]]:
    if not mesh.vertices:
        return mesh, [0.0, 0.0], [0.0, 0.0, 0.0]

    # Step 1: Snap lowest vertex to Z = 0.000m
    z_min = min(v[2] for v in mesh.vertices)
    mesh.vertices = [(v[0], v[1], v[2] - z_min) for v in mesh.vertices]

    # Step 2: Compute centroid of bottom 5% height slice
    z_max = max(v[2] for v in mesh.vertices)
    h = z_max
    if h > 1e-4:
        cutoff = base_ratio * h
        base_verts = [v for v in mesh.vertices if v[2] <= cutoff]
        if base_verts:
            cx = float(np.mean([v[0] for v in base_verts]))
            cy = float(np.mean([v[1] for v in base_verts]))
            mesh.vertices = [(v[0] - cx, v[1] - cy, v[2]) for v in mesh.vertices]
        else:
            cx, cy = 0.0, 0.0
    else:
        cx, cy = 0.0, 0.0

    # Step 3: Numerical cleanup ensuring exact Z_min = 0.0
    z_min_final = min(v[2] for v in mesh.vertices)
    if abs(z_min_final) > 1e-7:
        mesh.vertices = [(v[0], v[1], v[2] - z_min_final) for v in mesh.vertices]

    return mesh, [round(cx, 4), round(cy, 4)]
```

#### Algorithm 3: Metric Scale Normalization (`_normalize_scale`)
```python
def _normalize_scale(
    mesh: MeshGeometry,
    target_height_m: float,
    strategy: str = "height_proportional"
) -> Tuple[MeshGeometry, float]:
    if not mesh.vertices:
        return mesh, 1.0

    z_vals = [v[2] for v in mesh.vertices]
    curr_h = max(z_vals) - min(z_vals)
    if curr_h < 1e-6:
        return mesh, 1.0

    scale_factor = target_height_m / curr_h
    mesh.vertices = [
        (v[0] * scale_factor, v[1] * scale_factor, v[2] * scale_factor)
        for v in mesh.vertices
    ]

    # Re-verify ground contact at exact 0.0
    z_min = min(v[2] for v in mesh.vertices)
    if abs(z_min) > 1e-7:
        mesh.vertices = [(v[0], v[1], v[2] - z_min) for v in mesh.vertices]

    return mesh, scale_factor
```

#### Algorithm 4: Embedded Production GLB Builder (`_export_embedded_glb`)
1. Geometry data: pack `pos_data` (VEC3 float32), `norm_data` (VEC3 float32), `uv_data` (VEC2 float32), and `idx_data` (SCALAR uint16 or uint32).
2. ORM Texture Synthesis:
   - Merge `roughness` (in G) and `metallic` (in B) with white AO (in R, 255):
     ```python
     orm_img = Image.merge("RGB", (
         Image.new("L", rough_img.size, 255),
         rough_img.convert("L").resize(rough_img.size),
         metal_img.convert("L").resize(rough_img.size)
     ))
     ```
3. Texture binary buffers:
   - Encode `albedo` -> PNG bytes.
   - Encode `normal` -> PNG bytes.
   - Encode `orm` -> PNG bytes.
4. glTF JSON structure:
   - 4 accessors (POSITION, NORMAL, TEXCOORD_0, indices)
   - 7 bufferViews (4 geometry + 3 image buffers: albedo, normal, ORM)
   - 3 images (`mimeType: "image/png"`, pointing to bufferViews 4, 5, 6)
   - 1 sampler (`magFilter: 9729, minFilter: 9987, wrapS: 10497, wrapT: 10497`)
   - 3 textures (referencing images 0, 1, 2)
   - 1 material:
     ```json
     {
       "name": "M_<species_id>",
       "doubleSided": true,
       "pbrMetallicRoughness": {
         "baseColorTexture": {"index": 0},
         "metallicRoughnessTexture": {"index": 2},
         "roughnessFactor": 1.0,
         "metallicFactor": 1.0
       },
       "normalTexture": {"index": 1}
     }
     ```
   - 0 skins, 0 animations, 0 joints/weights attributes.
5. Serialization: Align all chunks with `pad_4`, write 12-byte header (`magic=b'glTF', version=2`), write JSON chunk, write BIN chunk.

#### Algorithm 5: Wavefront OBJ & MTL Exporter (`_export_obj_mtl`)
- Writes `<species_id>.mtl`:
  ```
  # MorphoMesh Vegetation Library Companion Material
  newmtl Material_<species_id>
  Ka 1.000000 1.000000 1.000000
  Kd 1.000000 1.000000 1.000000
  Ks 0.050000 0.050000 0.050000
  Ns 32.000000
  d 1.000000
  illum 2
  map_Kd textures/albedo.png
  map_Bump -bm 1.0 textures/normal.png
  norm textures/normal.png
  map_Pr textures/roughness.png
  map_Pm textures/metallic.png
  ```
- Writes `<species_id>.obj`:
  - `mtllib <species_id>.mtl`
  - `o <species_id>`
  - `v {x:.6f} {y:.6f} {z:.6f}`
  - `vt {u:.6f} {v:.6f}`
  - `vn {nx:.6f} {ny:.6f} {nz:.6f}`
  - `usemtl Material_<species_id>`
  - `s 1`
  - `f {i+1}/{i+1}/{i+1} {j+1}/{j+1}/{j+1} {k+1}/{k+1}/{k+1}`

---

### 4.6 Public API & Module Exports
In `teamwork_projects/vegetation_library/vegetation_pipeline/post_processor.py`:
```python
def process_and_export(
    raw_asset: RawAsset,
    species: Union[PlantSpecies, str],
    output_dir: Optional[Union[str, Path]] = None,
    config: Optional[PostProcessorConfig] = None,
) -> ExportedAsset:
    """Convenience functional interface matching PROJECT.md contract."""
    processor = AssetPostProcessor(config=config)
    return processor.process_asset(raw_asset, species, output_dir=output_dir)


__all__ = [
    "AssetDimensions",
    "PostProcessorConfig",
    "ExportedAsset",
    "AssetPostProcessor",
    "process_and_export",
]
```

And in `teamwork_projects/vegetation_library/vegetation_pipeline/__init__.py`:
Export `AssetDimensions`, `PostProcessorConfig`, `ExportedAsset`, `AssetPostProcessor`, and `process_and_export`.

---

## 5. Verification Method

### 5.1 Independent Test Suite Command
Run all unit tests in the project:
```bash
& "C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe" -m pytest teamwork_projects/vegetation_library/tests/ -v
```

### 5.2 Specific Test Cases for Milestone 3 (`tests/test_normalization.py`)
1. **Pivot Grounding Test**:
   - Verify for all 7 biomes that `min(v[2]) == 0.000` ($\pm 0.005$m) in the exported GLB and OBJ files.
2. **Base Contact Centroid Centering Test**:
   - Verify that the bottom 5% height slice centroid $(c_x, c_y)$ is within $\pm 0.05$m of $(0, 0)$.
3. **Metric Scale Test**:
   - Verify that measured exported height $H_{\text{actual}}$ matches `species.dimensions.height_m` within $\pm 1\%$.
4. **GLB Production Container Test**:
   - Verify valid 12-byte header (`magic == b'glTF'`, `version == 2`).
   - Verify $N_{\text{bones}} = 0$, zero skins, zero armatures.
   - Verify embedded images count == 3 (Albedo, Normal, ORM) and material specifies `"doubleSided": true`.
5. **Companion Wavefront OBJ/MTL Test**:
   - Verify `.obj` and `.mtl` exist, parse without error, and `.mtl` correctly references `textures/albedo.png`, `textures/normal.png`, etc.
6. **Texture Directory Completeness Test**:
   - Verify `textures/` contains all 4 PBR maps (`albedo.png`, `normal.png`, `roughness.png`, `metallic.png`) as readable images with resolution $\ge 256 \times 256$.
7. **Asset Manifest Schema Test**:
   - Verify `asset_manifest.json` parses as valid JSON and contains all required keys (`schema_version`, `species_id`, `taxonomy`, `geometry`, `materials`, `files`).
8. **Idempotency Test**:
   - Passing an already normalized `ExportedAsset` (converted to `RawAsset`) through `process_asset` produces identical vertex coordinates ($< 1e-6$ delta).
9. **Zero Credit Consumption & Offline Isolation**:
   - All tests use `tmp_path` fixtures and procedural fallback with zero Meshy API credit consumption.
