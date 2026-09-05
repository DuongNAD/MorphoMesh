# MorphoMesh — MCP Interface & Testing Specification Report

**Document ID**: SPEC-REPORT-M3-001  
**Author**: Spec Miner 3 (`spec_miner_survey_3`)  
**Date**: 2026-09-05  
**Target Project**: MorphoMesh (AI-Powered 3D Creature Generation Pipeline & Blender MCP Server)  
**Authoritative Request**: `/Users/duongnad/Documents/tool/MorphoMesh/ORIGINAL_REQUEST.md`  
**Target Documents**: `docs/MCP_SPECIFICATION.md`, `docs/ROADMAP.md`, `tests/` Test Suite  

---

## 1. Executive Summary

This report establishes the complete, production-grade technical specification for the **MorphoMesh Model Context Protocol (MCP) Server** (Requirement R3) and its **Automated Test Suite Architecture & Verification Protocols** (Requirement R4 Acceptance Criteria), along with the **Phase 1 to Production Roadmap** (`docs/ROADMAP.md`).

MorphoMesh bridges Google Antigravity 2.0 with Blender 5.2.1 LTS on macOS (Apple Silicon) via a lightweight, high-performance MCP server built on FastMCP (`mcp` 1.28.1 / Python 3.11+). The MCP Server exposes seven atomic, composable tools covering the full 5-stage creature generation pipeline:
1. `morphomesh_generate_concept`: 2D multi-angle anatomical concept synthesis.
2. `morphomesh_create_3d_asset`: Single-image to 3D geometry and PBR texture generation.
3. `morphomesh_optimize_topology`: Topology optimization, quad-dominant retopology, and polycount budget management.
4. `morphomesh_auto_rig`: Anatomical joint detection, armature synthesis, bone weighting, and test actions.
5. `morphomesh_blender_execute`: Sandboxed, AST-verified `bpy` script execution in Blender.
6. `morphomesh_get_scene_status`: Deep inspection of Blender scene hierarchy, mesh statistics, materials, and rigs.
7. `morphomesh_render_preview`: Automated studio turntable camera rendering returning MCP `ImageContent` and metadata.

All specifications below have been probed and validated against local runtime environments: Python 3.11.8, `mcp` 1.28.1, `pydantic` 2.13.4, `pytest` 9.1.1, and headless Blender 5.2.1 LTS Darwin arm64.

---

## 2. Master Tables: Features Discovered & Edge Cases

### 2.1 Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Concept Gen | 2D Multi-View Synthesis | Generates creature concepts with standardized poses (A/T-pose) and perspectives (front, side, turnaround) | Prompt, creature type, view mode, pose, style, dimensions, seed | Concept ID, image file path, prompt metadata | Raises `ERR_EMPTY_PROMPT`, `ERR_INVALID_DIMENSIONS` | ORIGINAL_REQUEST R3 / Diffusion APIs |
| 2 | 3D Gen | Image-to-3D Geometry & PBR | Converts 2D concept image into textured 3D mesh (.glb/.obj) with albedo, roughness, metallic, normal maps | Image path / concept ID, backend, export format, PBR toggle, resolution | Asset ID, mesh path, texture map paths, vertex/face stats, bounding box | Raises `ERR_IMAGE_NOT_FOUND`, `ERR_BACKEND_UNAVAILABLE` | ORIGINAL_REQUEST R3 / TRELLIS & Hunyuan3D |
| 3 | Retopology | Topology Optimization | Converts high-poly / marching-cubes mesh to clean quad-dominant animation topology matching poly budget | Asset ID / mesh path, target polycount, topology type, edge preservation, algorithm | Optimized asset ID, output mesh path, before/after poly counts, quad ratio | Raises `ERR_INPUT_MESH_NOT_FOUND`, `ERR_INVALID_POLY_COUNT`, `ERR_REMESH_FAILED` | ORIGINAL_REQUEST R3 / QuadriFlow & MeshAnything |
| 4 | Rigging | Automated Creature Rigging | Detects anatomical landmarks, constructs modular armature (quadruped, biped, winged, etc.), binds weights | Asset ID / mesh path, creature type, rig type, skinning method, symmetry | Rigged asset ID, exported rigged FBX/GLB, .blend path, bone list, test action | Raises `ERR_ANATOMY_DETECTION_FAILED`, `ERR_SKINNING_HEAT_FAILURE` | ORIGINAL_REQUEST R3 / Blender Armature API |
| 5 | Execution | Sandboxed Blender Python Execution | Executes custom `bpy` scripts inside Blender runtime with AST security inspection and variable extraction | Script text, timeout seconds, target scene, save options, return variable list | Success flag, stdout, stderr, serialized return variables, execution time | Raises `ERR_SCRIPT_SECURITY_VIOLATION`, `ERR_SCRIPT_SYNTAX_ERROR`, `ERR_SCRIPT_EXECUTION_TIMEOUT` | ORIGINAL_REQUEST R3, R4 / Python AST & Headless bpy |
| 6 | Scene Status | Deep Scene State Inspection | Traverses active Blender scene graph, extracting object stats, geometry counts, materials, armatures, cameras | Scene name, filter flags (stats, hierarchy, materials, armatures, lights) | Object hierarchy tree, total vertices/faces, per-object metadata, material node graph | Raises `ERR_SCENE_NOT_FOUND`, `ERR_BLENDER_OFFLINE` | ORIGINAL_REQUEST R3 / bpy.context.scene |
| 7 | Render | Automated Camera Turntable Render | Sets up studio lighting, frames target creature, renders high-res preview via EEVEE / Cycles | Camera name, resolution, render engine, samples, view angle, transparent bg | Saved PNG path, resolution, render engine, sample count, MCP `ImageContent` | Raises `ERR_NO_CAMERA` (auto-repaired), `ERR_RENDER_FAILED` | ORIGINAL_REQUEST R3 / bpy.ops.render |
| 8 | MCP Transport | Dual stdio & SSE Transports | FastMCP transport supporting both local stdin/stdout piping for Antigravity and HTTP Server-Sent Events | Host, port, transport mode | Connection handle, message stream | Connection reset, EOF, port collision | FastMCP 1.28.1 SDK Runtime Probe |
| 9 | Multi-Content | Hybrid Image & Text Returns | Allows tools like `render_preview` to return binary `ImageContent` along with structured `TextContent` | Image binary buffer, text string | Multipart MCP content array | Malformed MIME type, base64 corruption | FastMCP tool execution probe |
| 10 | Fallback | Offline Mock Inference Adapter | Procedural geometry, deterministic mock images, and decimation for zero-GPU CI/CD testing | Mock flags, seed | Deterministic synthetic assets | Deterministic pseudo-random generation | ORIGINAL_REQUEST R4 / inference_adapter.py |

### 2.2 Edge Cases Probed

| # | Feature | Input | Observed Behavior | Handling Requirement |
|---|---------|-------|-------------------|----------------------|
| 1 | `render_preview` | Scene has 0 cameras | Blender throws `RuntimeError: Error: Cannot render, no camera` (Exit code 1) | Automatically spawn procedural studio camera targeted at creature center-of-mass before rendering. |
| 2 | `render_preview` | Engine set to `'BLENDER_EEVEE_NEXT'` | Blender 5.2.1 throws `TypeError: enum "BLENDER_EEVEE_NEXT" not found in ('BLENDER_EEVEE', 'BLENDER_WORKBENCH', 'CYCLES')` | Bridge must automatically normalize `'BLENDER_EEVEE_NEXT'` to `'BLENDER_EEVEE'`. |
| 3 | `blender_execute` | Script imports `os.system("rm -rf /")` | AST safety analyzer identifies `ast.Import` node with `name == 'os'` | Instantly reject script with `ERR_SCRIPT_SECURITY_VIOLATION` before transmitting to Blender. |
| 4 | `blender_execute` | Script calls `eval()` or `__builtins__.__import__('subprocess')` | AST detects forbidden Call node or dunder attribute traversal | Block execution; raise security violation error. |
| 5 | `blender_execute` | Script enters `while True: pass` | Process hangs indefinitely | Bridge enforces `timeout_seconds` via `subprocess.run(timeout=...)` or socket timeout, killing process and returning `ERR_SCRIPT_EXECUTION_TIMEOUT`. |
| 6 | `create_3d_asset` | Input image does not exist or empty path | File system check fails | Return `ERR_IMAGE_NOT_FOUND` with full attempted path before invoking AI backend. |
| 7 | `optimize_topology`| Target poly count > current mesh poly count (e.g., target 50,000 on a 1,000 poly mesh) | Mesh decimation would result in no-op or unexpected subdivide | Warn and clamp decimate ratio to 1.0; preserve existing topology or return informative status. |
| 8 | `optimize_topology`| Mesh contains non-manifold edges or self-intersections | QuadriFlow solver aborts or creates holes | Pre-clean mesh using Blender `3D-Print Toolbox` / manifold cleanup pass (`bmesh.ops.dissolve_degenerate`). |
| 9 | `auto_rig` | Mesh has multiple disconnected loose parts (e.g. eyes, teeth, armor) | Automatic bone heat weighting fails with `Bone Heat Weighting: failed to find solution for one or more bones` | Merge components into single manifold proxy for weight calculation, or transfer weights via `DataTransfer` modifier. |
| 10 | `generate_concept` | Negative width/height or non-multiple of 8 | Image generative models require multiple of 8 or 16 | Pydantic validator clamps to range [512, 2048] and rounds to nearest multiple of 64. |

---

## 3. Deep-Dive Specification for All 7 MCP Tools

### 3.1 Tool 1: `morphomesh_generate_concept`

#### 3.1.1 Purpose
Synthesizes a high-fidelity 2D concept image of a creature optimized specifically for downstream 3D reconstruction. Applies domain-specific prompt engineering (silhouette isolation, neutral pose, orthographic/neutral perspective, clean backdrop, anatomical clarity) and returns a unique `concept_id` and cached image path.

#### 3.1.2 Parameter Specification

| Parameter | Type | Required | Default | Range / Allowed Values | Description |
|-----------|------|----------|---------|------------------------|-------------|
| `prompt` | `str` | **Yes** | — | Min 3 chars | Natural language description of the creature anatomy, textures, and features. |
| `negative_prompt` | `str` | No | `""` | Any string | Negative constraints (e.g., "blurry, cropped, extreme perspective, text, watermark"). |
| `creature_type` | `str` | No | `"custom"` | `quadruped`, `biped`, `winged`, `aquatic`, `serpentine`, `hybrid`, `custom` | Anatomical archetype used to inject specialized pose and silhouette priors. |
| `view_mode` | `str` | No | `"front"` | `front`, `side`, `three_quarter`, `turnaround_sheet`, `orthographic_front_side` | Camera viewing perspective tailored for 3D reconstruction. |
| `pose` | `str` | No | `"standing_neutral"` | `neutral_t_pose`, `neutral_a_pose`, `standing_neutral`, `relaxed` | Rest pose preventing limb occlusion and facilitating auto-rigging. |
| `style` | `str` | No | `"realistic"` | `realistic`, `stylized`, `dark_fantasy`, `sci_fi`, `cartoon`, `sculpture` | Visual rendering aesthetic. |
| `background` | `str` | No | `"white_neutral"` | `white_neutral`, `black_neutral`, `gray_neutral`, `transparent` | Background type for seamless alpha cutout and NeRF/3DGS isolation. |
| `width` | `int` | No | `1024` | `512` to `2048` (step: 64) | Output image width in pixels. |
| `height` | `int` | No | `1024` | `512` to `2048` (step: 64) | Output image height in pixels. |
| `seed` | `int` | No | `-1` | `-1` to `2147483647` | Deterministic random seed (-1 indicates random generation). |
| `output_format` | `str` | No | `"png"` | `png`, `webp`, `jpeg` | File format for disk storage. |

#### 3.1.3 JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "morphomesh_generate_concept_input",
  "type": "object",
  "properties": {
    "prompt": {
      "type": "string",
      "minLength": 3,
      "description": "Natural language description of the creature anatomy, textures, and features."
    },
    "negative_prompt": {
      "type": "string",
      "default": "",
      "description": "Negative constraints to prevent artifacts, occlusions, or text."
    },
    "creature_type": {
      "type": "string",
      "enum": ["quadruped", "biped", "winged", "aquatic", "serpentine", "hybrid", "custom"],
      "default": "custom",
      "description": "Anatomical archetype used to inject specialized pose priors."
    },
    "view_mode": {
      "type": "string",
      "enum": ["front", "side", "three_quarter", "turnaround_sheet", "orthographic_front_side"],
      "default": "front",
      "description": "Camera viewing perspective tailored for 3D reconstruction."
    },
    "pose": {
      "type": "string",
      "enum": ["neutral_t_pose", "neutral_a_pose", "standing_neutral", "relaxed"],
      "default": "standing_neutral",
      "description": "Rest pose preventing limb self-occlusion."
    },
    "style": {
      "type": "string",
      "enum": ["realistic", "stylized", "dark_fantasy", "sci_fi", "cartoon", "sculpture"],
      "default": "realistic",
      "description": "Visual rendering aesthetic."
    },
    "background": {
      "type": "string",
      "enum": ["white_neutral", "black_neutral", "gray_neutral", "transparent"],
      "default": "white_neutral",
      "description": "Background color/transparency for segmentation."
    },
    "width": {
      "type": "integer",
      "minimum": 512,
      "maximum": 2048,
      "default": 1024,
      "description": "Output image width in pixels."
    },
    "height": {
      "type": "integer",
      "minimum": 512,
      "maximum": 2048,
      "default": 1024,
      "description": "Output image height in pixels."
    },
    "seed": {
      "type": "integer",
      "minimum": -1,
      "maximum": 2147483647,
      "default": -1,
      "description": "Deterministic random seed (-1 for random)."
    },
    "output_format": {
      "type": "string",
      "enum": ["png", "webp", "jpeg"],
      "default": "png",
      "description": "Image file format."
    }
  },
  "required": ["prompt"],
  "additionalProperties": false
}
```

#### 3.1.4 Pydantic v2 Models
```python
from typing import Literal, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

class GenerateConceptInput(BaseModel):
    prompt: str = Field(..., min_length=3, description="Natural language description of creature")
    negative_prompt: str = Field(default="", description="Negative constraints")
    creature_type: Literal["quadruped", "biped", "winged", "aquatic", "serpentine", "hybrid", "custom"] = "custom"
    view_mode: Literal["front", "side", "three_quarter", "turnaround_sheet", "orthographic_front_side"] = "front"
    pose: Literal["neutral_t_pose", "neutral_a_pose", "standing_neutral", "relaxed"] = "standing_neutral"
    style: Literal["realistic", "stylized", "dark_fantasy", "sci_fi", "cartoon", "sculpture"] = "realistic"
    background: Literal["white_neutral", "black_neutral", "gray_neutral", "transparent"] = "white_neutral"
    width: int = Field(default=1024, ge=512, le=2048)
    height: int = Field(default=1024, ge=512, le=2048)
    seed: int = Field(default=-1, ge=-1)
    output_format: Literal["png", "webp", "jpeg"] = "png"

    @field_validator("width", "height")
    @classmethod
    def validate_step(cls, v: int) -> int:
        if v % 64 != 0:
            return round(v / 64) * 64
        return v

class GenerateConceptOutput(BaseModel):
    concept_id: str = Field(..., description="Unique concept UUID")
    image_path: str = Field(..., description="Absolute path to cached image")
    prompt_enhanced: str = Field(..., description="Augmented prompt with anatomical modifiers")
    creature_type: str
    view_mode: str
    dimensions: list[int]
    seed_used: int
    status: Literal["success", "mock_success"]
```

#### 3.1.5 Error Conditions & Codes
- `ERR_EMPTY_PROMPT`: Prompt contains only whitespace or is shorter than 3 characters.
- `ERR_INVALID_DIMENSIONS`: Provided dimensions fall outside [512, 2048].
- `ERR_INFERENCE_FAILED`: 2D generative model API failed, timed out, or returned invalid data.
- `ERR_DISK_WRITE_FAILED`: Server could not write the concept image to the cache directory.

#### 3.1.6 Example Request & Response Payloads
**Request:**
```json
{
  "prompt": "A mythical four-legged dragon dog with scaled spine, reptilian horns, and canine muzzle, full body",
  "creature_type": "quadruped",
  "view_mode": "three_quarter",
  "pose": "standing_neutral",
  "style": "dark_fantasy",
  "background": "white_neutral",
  "width": 1024,
  "height": 1024,
  "seed": 42
}
```

**Response:**
```json
{
  "concept_id": "c7a84e29-3f01-44ab-b56e-821e25e9821a",
  "image_path": "/Users/duongnad/Documents/tool/MorphoMesh/.cache/concepts/c7a84e29.png",
  "prompt_enhanced": "A mythical four-legged dragon dog with scaled spine, reptilian horns, and canine muzzle, full body, symmetrical quadruped anatomy, standing neutral pose, studio lighting, neutral solid white background, high geometric fidelity, 8k render",
  "creature_type": "quadruped",
  "view_mode": "three_quarter",
  "dimensions": [1024, 1024],
  "seed_used": 42,
  "status": "success"
}
```

---

### 3.2 Tool 2: `morphomesh_create_3d_asset`

#### 3.2.1 Purpose
Consumes a 2D concept image and reconstructs a complete 3D mesh (GLB/OBJ) with full PBR textures (albedo/diffuse, roughness, metallic, normal maps) using state-of-the-art 3D AI models (TRELLIS, Hunyuan3D-2, Step1X-3D, TripoSR) or a deterministic offline mock adapter.

#### 3.2.2 Parameter Specification

| Parameter | Type | Required | Default | Range / Allowed Values | Description |
|-----------|------|----------|---------|------------------------|-------------|
| `image_path` | `str` | Cond. | `None` | Existing file path | Path to local concept image. (Required if `concept_id` omitted). |
| `concept_id` | `str` | Cond. | `None` | Valid UUID | ID of previously generated concept. |
| `model_backend` | `str` | No | `"mock"` | `mock`, `trellis`, `hunyuan3d_2`, `step1x_3d`, `triposr` | 3D reconstruction engine backend. |
| `export_format` | `str` | No | `"glb"` | `glb`, `obj`, `fbx`, `ply` | Target 3D file format. |
| `generate_pbr` | `bool` | No | `true` | `true`, `false` | Extract and bake PBR material textures (diffuse, rough, metal, normal). |
| `texture_resolution`| `int` | No | `2048` | `512`, `1024`, `2048`, `4096` | Resolution for baked texture atlases. |
| `remove_background`| `bool` | No | `true` | `true`, `false` | Execute rembg segmentation before 3D reconstruction. |
| `guidance_scale` | `float`| No | `7.5` | `1.0` to `20.0` | Diffusion guidance parameter. |
| `seed` | `int` | No | `-1` | `-1` to `2147483647` | Random seed for generative 3D process. |

#### 3.2.3 JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "morphomesh_create_3d_asset_input",
  "type": "object",
  "properties": {
    "image_path": {
      "type": "string",
      "description": "Path to input concept image file on disk."
    },
    "concept_id": {
      "type": "string",
      "description": "Unique ID of concept generated in stage 1."
    },
    "model_backend": {
      "type": "string",
      "enum": ["mock", "trellis", "hunyuan3d_2", "step1x_3d", "triposr"],
      "default": "mock",
      "description": "3D AI generator engine."
    },
    "export_format": {
      "type": "string",
      "enum": ["glb", "obj", "fbx", "ply"],
      "default": "glb",
      "description": "Desired 3D asset file format."
    },
    "generate_pbr": {
      "type": "boolean",
      "default": true,
      "description": "Bake PBR texture maps (albedo, normal, roughness, metallic)."
    },
    "texture_resolution": {
      "type": "integer",
      "enum": [512, 1024, 2048, 4096],
      "default": 2048,
      "description": "Square resolution of output texture atlases."
    },
    "remove_background": {
      "type": "boolean",
      "default": true,
      "description": "Isolate foreground creature before lifting to 3D."
    },
    "guidance_scale": {
      "type": "number",
      "minimum": 1.0,
      "maximum": 20.0,
      "default": 7.5,
      "description": "Classifier-free guidance strength."
    },
    "seed": {
      "type": "integer",
      "minimum": -1,
      "default": -1,
      "description": "RNG seed (-1 for random)."
    }
  },
  "additionalProperties": false
}
```

#### 3.2.4 Pydantic v2 Models
```python
class Create3DAssetInput(BaseModel):
    image_path: Optional[str] = Field(default=None, description="Path to concept image file")
    concept_id: Optional[str] = Field(default=None, description="Concept UUID")
    model_backend: Literal["mock", "trellis", "hunyuan3d_2", "step1x_3d", "triposr"] = "mock"
    export_format: Literal["glb", "obj", "fbx", "ply"] = "glb"
    generate_pbr: bool = True
    texture_resolution: Literal[512, 1024, 2048, 4096] = 2048
    remove_background: bool = True
    guidance_scale: float = Field(default=7.5, ge=1.0, le=20.0)
    seed: int = Field(default=-1, ge=-1)

class BoundingBox(BaseModel):
    min_point: list[float]
    max_point: list[float]
    dimensions: list[float]

class Create3DAssetOutput(BaseModel):
    asset_id: str
    mesh_path: str
    format: str
    vertex_count: int
    face_count: int
    has_pbr_materials: bool
    texture_paths: Dict[str, str] = Field(default_factory=dict)
    bounding_box: BoundingBox
    generation_time_seconds: float
    backend_used: str
```

#### 3.2.5 Error Conditions & Codes
- `ERR_IMAGE_NOT_FOUND`: Neither `image_path` nor `concept_id` was provided, or the resolved image file does not exist on disk.
- `ERR_UNSUPPORTED_IMAGE_FORMAT`: Image file cannot be decoded (invalid header or corrupted data).
- `ERR_BACKEND_UNAVAILABLE`: Selected remote backend (e.g. TRELLIS / Replicate) lacks valid credentials or GPU instance is offline.
- `ERR_MESH_GENERATION_FAILED`: Generative model encountered an internal inference exception or produced 0 vertices.

#### 3.2.6 Example Request & Response Payloads
**Request:**
```json
{
  "concept_id": "c7a84e29-3f01-44ab-b56e-821e25e9821a",
  "model_backend": "mock",
  "export_format": "glb",
  "generate_pbr": true,
  "texture_resolution": 2048
}
```

**Response:**
```json
{
  "asset_id": "a91b2c3d-88f1-47ea-9c02-45e0d192a831",
  "mesh_path": "/Users/duongnad/Documents/tool/MorphoMesh/.cache/assets/a91b2c3d.glb",
  "format": "glb",
  "vertex_count": 48250,
  "face_count": 96400,
  "has_pbr_materials": true,
  "texture_paths": {
    "albedo": "/Users/duongnad/Documents/tool/MorphoMesh/.cache/assets/a91b2c3d_albedo.png",
    "roughness": "/Users/duongnad/Documents/tool/MorphoMesh/.cache/assets/a91b2c3d_roughness.png",
    "metallic": "/Users/duongnad/Documents/tool/MorphoMesh/.cache/assets/a91b2c3d_metallic.png",
    "normal": "/Users/duongnad/Documents/tool/MorphoMesh/.cache/assets/a91b2c3d_normal.png"
  },
  "bounding_box": {
    "min_point": [-1.2, -0.8, 0.0],
    "max_point": [1.2, 0.8, 1.95],
    "dimensions": [2.4, 1.6, 1.95]
  },
  "generation_time_seconds": 1.42,
  "backend_used": "mock"
}
```

---

### 3.3 Tool 3: `morphomesh_optimize_topology`

#### 3.3.1 Purpose
Retopologizes raw 3D mesh geometry into an animation-ready, quad-dominant structure matching a specified polygon budget. Preserves anatomical edge flow, sharp features (teeth, claws, horns), and UV atlas seams.

#### 3.3.2 Parameter Specification

| Parameter | Type | Required | Default | Range / Allowed Values | Description |
|-----------|------|----------|---------|------------------------|-------------|
| `asset_id` | `str` | Cond. | `None` | Valid UUID | 3D Asset ID from stage 2. |
| `input_mesh_path` | `str` | Cond. | `None` | File path | Direct path to mesh file. (Required if `asset_id` omitted). |
| `target_poly_count`| `int` | No | `10000` | `500` to `500000` | Target face/polygon count. |
| `topology_type` | `str` | No | `"quad_dominant"` | `quad_dominant`, `pure_quad`, `triangulated`, `adaptive` | Geometric element preference. |
| `preserve_uvs` | `bool` | No | `true` | `true`, `false` | Transfer or re-project existing UV maps. |
| `preserve_sharp_edges`| `bool`| No | `true`| `true`, `false` | Maintain crease angles and high-frequency anatomical edges. |
| `method` | `str` | No | `"quadriflow"` | `quadriflow`, `decimate`, `voxel_remesh`, `meshanything_v2`, `mock` | Retopology algorithm. |
| `output_format` | `str` | No | `"glb"` | `glb`, `obj`, `fbx` | Output mesh format. |

#### 3.3.3 JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "morphomesh_optimize_topology_input",
  "type": "object",
  "properties": {
    "asset_id": { "type": "string", "description": "Asset ID from stage 2." },
    "input_mesh_path": { "type": "string", "description": "Direct path to 3D mesh." },
    "target_poly_count": {
      "type": "integer",
      "minimum": 500,
      "maximum": 500000,
      "default": 10000,
      "description": "Target face budget."
    },
    "topology_type": {
      "type": "string",
      "enum": ["quad_dominant", "pure_quad", "triangulated", "adaptive"],
      "default": "quad_dominant",
      "description": "Preferred polygon topology."
    },
    "preserve_uvs": { "type": "boolean", "default": true, "description": "Preserve UV seams." },
    "preserve_sharp_edges": { "type": "boolean", "default": true, "description": "Preserve creased edges." },
    "method": {
      "type": "string",
      "enum": ["quadriflow", "decimate", "voxel_remesh", "meshanything_v2", "mock"],
      "default": "quadriflow",
      "description": "Algorithm for topology transformation."
    },
    "output_format": {
      "type": "string",
      "enum": ["glb", "obj", "fbx"],
      "default": "glb",
      "description": "Output mesh format."
    }
  },
  "additionalProperties": false
}
```

#### 3.3.4 Pydantic v2 Models
```python
class OptimizeTopologyInput(BaseModel):
    asset_id: Optional[str] = None
    input_mesh_path: Optional[str] = None
    target_poly_count: int = Field(default=10000, ge=500, le=500000)
    topology_type: Literal["quad_dominant", "pure_quad", "triangulated", "adaptive"] = "quad_dominant"
    preserve_uvs: bool = True
    preserve_sharp_edges: bool = True
    method: Literal["quadriflow", "decimate", "voxel_remesh", "meshanything_v2", "mock"] = "quadriflow"
    output_format: Literal["glb", "obj", "fbx"] = "glb"

class OptimizeTopologyOutput(BaseModel):
    optimized_asset_id: str
    output_mesh_path: str
    original_vertex_count: int
    original_face_count: int
    optimized_vertex_count: int
    optimized_face_count: int
    quad_percentage: float = Field(..., ge=0.0, le=100.0)
    reduction_ratio: float
    uv_preserved: bool
    processing_time_seconds: float
```

#### 3.3.5 Error Conditions & Codes
- `ERR_INPUT_MESH_NOT_FOUND`: Target mesh file not found.
- `ERR_INVALID_POLY_COUNT`: Budget requested is invalid.
- `ERR_NON_MANIFOLD_MESH`: Mesh contains degenerate topology that QuadriFlow cannot resolve without pre-cleaning.
- `ERR_REMESH_FAILED`: Retopology solver failed to terminate or crashed.

#### 3.3.6 Example Request & Response Payloads
**Request:**
```json
{
  "asset_id": "a91b2c3d-88f1-47ea-9c02-45e0d192a831",
  "target_poly_count": 8000,
  "topology_type": "quad_dominant",
  "method": "quadriflow"
}
```

**Response:**
```json
{
  "optimized_asset_id": "opt-e83c21a0-4b21-46bb-b31a-637dc49d1052",
  "output_mesh_path": "/Users/duongnad/Documents/tool/MorphoMesh/.cache/assets/opt_e83c21a0.glb",
  "original_vertex_count": 48250,
  "original_face_count": 96400,
  "optimized_vertex_count": 8120,
  "optimized_face_count": 7980,
  "quad_percentage": 94.6,
  "reduction_ratio": 0.0827,
  "uv_preserved": true,
  "processing_time_seconds": 2.15
}
```

---

### 3.4 Tool 4: `morphomesh_auto_rig`

#### 3.4.1 Purpose
Analyzes the 3D creature geometry, identifies anatomical landmarks (spine, pelvis, limbs, neck, head, tail, wings), constructs a modular armature compatible with Blender Rigify, computes automatic bone heat weights across vertex groups, and binds the armature to the mesh with standard test animation actions.

#### 3.4.2 Parameter Specification

| Parameter | Type | Required | Default | Range / Allowed Values | Description |
|-----------|------|----------|---------|------------------------|-------------|
| `asset_id` | `str` | Cond. | `None` | Valid UUID | Asset ID from stage 2 or 3. |
| `input_mesh_path` | `str` | Cond. | `None` | File path | Direct mesh path. (Required if `asset_id` omitted). |
| `creature_type` | `str` | No | `"quadruped"` | `quadruped`, `biped`, `winged_quadruped`, `serpentine`, `bird`, `spider_arthropod`, `fish_aquatic`, `custom_auto` | Morphological archetype guiding bone placement. |
| `rig_type` | `str` | No | `"rigify_creature"` | `basic_fk`, `rigify_creature`, `game_engine_root`, `deform_only` | Rig hierarchy and controller configuration. |
| `skinning_method` | `str` | No | `"automatic_weights"` | `automatic_weights`, `voxel_heat_diffuse`, `geodesic_voxel` | Vertex weighting algorithm. |
| `symmetry` | `bool` | No | `true` | `true`, `false` | Force X-axis bilateral symmetry for limb joints. |
| `generate_test_animation`| `bool`| No| `true` | `true`, `false` | Attach an idle walk / pose test animation action. |
| `load_into_scene` | `bool` | No | `true` | `true`, `false` | Instantiate rigged character directly in active Blender scene. |

#### 3.4.3 JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "morphomesh_auto_rig_input",
  "type": "object",
  "properties": {
    "asset_id": { "type": "string", "description": "Asset ID to rig." },
    "input_mesh_path": { "type": "string", "description": "Direct path to mesh." },
    "creature_type": {
      "type": "string",
      "enum": ["quadruped", "biped", "winged_quadruped", "serpentine", "bird", "spider_arthropod", "fish_aquatic", "custom_auto"],
      "default": "quadruped",
      "description": "Anatomical morphology."
    },
    "rig_type": {
      "type": "string",
      "enum": ["basic_fk", "rigify_creature", "game_engine_root", "deform_only"],
      "default": "rigify_creature",
      "description": "Armature control type."
    },
    "skinning_method": {
      "type": "string",
      "enum": ["automatic_weights", "voxel_heat_diffuse", "geodesic_voxel"],
      "default": "automatic_weights",
      "description": "Skin weighting method."
    },
    "symmetry": { "type": "boolean", "default": true, "description": "Enforce X symmetry." },
    "generate_test_animation": { "type": "boolean", "default": true, "description": "Add test animation action." },
    "load_into_scene": { "type": "boolean", "default": true, "description": "Import into active Blender scene." }
  },
  "additionalProperties": false
}
```

#### 3.4.4 Pydantic v2 Models
```python
class AutoRigInput(BaseModel):
    asset_id: Optional[str] = None
    input_mesh_path: Optional[str] = None
    creature_type: Literal["quadruped", "biped", "winged_quadruped", "serpentine", "bird", "spider_arthropod", "fish_aquatic", "custom_auto"] = "quadruped"
    rig_type: Literal["basic_fk", "rigify_creature", "game_engine_root", "deform_only"] = "rigify_creature"
    skinning_method: Literal["automatic_weights", "voxel_heat_diffuse", "geodesic_voxel"] = "automatic_weights"
    symmetry: bool = True
    generate_test_animation: bool = True
    load_into_scene: bool = True

class AutoRigOutput(BaseModel):
    rigged_asset_id: str
    blend_file_path: Optional[str]
    exported_mesh_path: str
    armature_name: str
    bone_count: int
    bone_hierarchy: list[str]
    creature_type: str
    has_skin_weights: bool
    test_action_name: Optional[str]
    status: Literal["success", "mock_success"]
```

#### 3.4.5 Error Conditions & Codes
- `ERR_INPUT_MESH_NOT_FOUND`: Target mesh does not exist.
- `ERR_ANATOMY_DETECTION_FAILED`: Morphological analysis cannot find key points (head, feet, spine).
- `ERR_SKINNING_HEAT_FAILURE`: Blender automatic heat weighting failed due to mesh non-manifold geometry.
- `ERR_BLENDER_PROCESS_FAILED`: Subprocess execution or socket transmission failed during rigging.

#### 3.4.6 Example Request & Response Payloads
**Request:**
```json
{
  "asset_id": "opt-e83c21a0-4b21-46bb-b31a-637dc49d1052",
  "creature_type": "quadruped",
  "rig_type": "rigify_creature",
  "generate_test_animation": true
}
```

**Response:**
```json
{
  "rigged_asset_id": "rig-341a99f1-a1e0-410d-8519-72c0cba95011",
  "blend_file_path": "/Users/duongnad/Documents/tool/MorphoMesh/.cache/scenes/rig_341a99f1.blend",
  "exported_mesh_path": "/Users/duongnad/Documents/tool/MorphoMesh/.cache/assets/rig_341a99f1.fbx",
  "armature_name": "Armature_Quadruped_DragonDog",
  "bone_count": 42,
  "bone_hierarchy": [
    "root", "pelvis", "spine_01", "spine_02", "neck", "head",
    "thigh.L", "shin.L", "foot.L", "toe.L",
    "thigh.R", "shin.R", "foot.R", "toe.R",
    "shoulder.L", "upper_arm.L", "forearm.L", "hand.L",
    "shoulder.R", "upper_arm.R", "forearm.R", "hand.R",
    "tail_01", "tail_02", "tail_03", "tail_04"
  ],
  "creature_type": "quadruped",
  "has_skin_weights": true,
  "test_action_name": "Action_Quadruped_IdlePose",
  "status": "success"
}
```

---

### 3.5 Tool 5: `morphomesh_blender_execute`

#### 3.5.1 Purpose
Executes custom, fine-grained Python scripts directly inside the active Blender instance or headless runner. Enforces strict AST security filters to prohibit arbitrary OS command execution, filesystem corruption, or unauthorized network calls, while permitting full access to `bpy`, `mathutils`, `bmesh`, `math`, and scene manipulation.

#### 3.5.2 Parameter Specification

| Parameter | Type | Required | Default | Range / Allowed Values | Description |
|-----------|------|----------|---------|------------------------|-------------|
| `script` | `str` | **Yes** | — | Valid Python code | Python script containing `bpy` commands. |
| `timeout_seconds` | `int` | No | `30` | `1` to `300` | Maximum execution time in seconds. |
| `target_scene` | `str` | No | `None` | Scene name | Target Blender scene (defaults to active scene). |
| `save_after` | `bool` | No | `false` | `true`, `false` | Save current Blender session to disk upon script completion. |
| `save_path` | `str` | No | `None` | File path | File path if `save_after` is True (defaults to autosave path). |
| `return_variables`| `list[str]`| No| `[]` | List of var names | Variable names in script scope to serialize and return. |

#### 3.5.3 JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "morphomesh_blender_execute_input",
  "type": "object",
  "properties": {
    "script": {
      "type": "string",
      "description": "Python script with bpy commands to execute."
    },
    "timeout_seconds": {
      "type": "integer",
      "minimum": 1,
      "maximum": 300,
      "default": 30,
      "description": "Execution timeout limit."
    },
    "target_scene": { "type": "string", "description": "Specific scene name." },
    "save_after": { "type": "boolean", "default": false, "description": "Save scene after execution." },
    "save_path": { "type": "string", "description": "Path for saved .blend file." },
    "return_variables": {
      "type": "array",
      "items": { "type": "string" },
      "default": [],
      "description": "Names of variables in script scope to serialize into JSON response."
    }
  },
  "required": ["script"],
  "additionalProperties": false
}
```

#### 3.5.4 Pydantic v2 Models
```python
class BlenderExecuteInput(BaseModel):
    script: str = Field(..., description="Python script with bpy commands to execute")
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    target_scene: Optional[str] = None
    save_after: bool = False
    save_path: Optional[str] = None
    return_variables: list[str] = Field(default_factory=list)

class BlenderExecuteOutput(BaseModel):
    success: bool
    stdout: str
    stderr: str
    returned_data: Dict[str, Any] = Field(default_factory=dict)
    execution_time_seconds: float
    blend_file_path: Optional[str] = None
```

#### 3.5.5 Security & AST Validation Specification
Before transmission to Blender, the bridge parses the script into an Abstract Syntax Tree (`ast.parse`) and verifies:
1. **Forbidden Module Imports**:
   `os`, `sys`, `subprocess`, `shutil`, `socket`, `http`, `urllib`, `requests`, `ctypes`, `multiprocessing`, `threading`, `signal`, `pty`, `importlib`, `builtins`.
2. **Forbidden Builtin Calls**:
   `eval`, `exec`, `compile`, `__import__`, `open`, `input`, `breakpoint`, `globals`, `locals`.
3. **Forbidden Dunder Attribute Accesses**:
   `__subclasses__`, `__globals__`, `__code__`, `__dict__`, `__bases__`, `__mro__`.
4. **Permitted Modules**:
   `bpy`, `bmesh`, `mathutils`, `math`, `random`, `json`, `time`, `collections`, `itertools`.

#### 3.5.6 Error Conditions & Codes
- `ERR_SCRIPT_SECURITY_VIOLATION`: Script contains forbidden imports, builtins, or dunder tricks.
- `ERR_SCRIPT_SYNTAX_ERROR`: Script fails `ast.parse` due to Python syntax errors.
- `ERR_SCRIPT_EXECUTION_TIMEOUT`: Script run exceeded `timeout_seconds`.
- `ERR_SCRIPT_RUNTIME_EXCEPTION`: Unhandled exception during `bpy` execution (stack trace returned in `stderr`).
- `ERR_BLENDER_COMMUNICATION_FAILURE`: Blender socket connection severed or headless process terminated abnormally.

#### 3.5.7 Example Request & Response Payloads
**Request:**
```json
{
  "script": "import bpy\nobj = bpy.context.active_object\nif obj:\n    obj.location.z += 1.0\n    new_z = obj.location.z\nelse:\n    new_z = 0.0\nresult_msg = f'Adjusted {obj.name if obj else None} to Z={new_z}'",
  "return_variables": ["new_z", "result_msg"],
  "timeout_seconds": 15
}
```

**Response:**
```json
{
  "success": true,
  "stdout": "Info: Object translation applied\n",
  "stderr": "",
  "returned_data": {
    "new_z": 2.95,
    "result_msg": "Adjusted Armature_Quadruped_DragonDog to Z=2.95"
  },
  "execution_time_seconds": 0.048,
  "blend_file_path": null
}
```

---

### 3.6 Tool 6: `morphomesh_get_scene_status`

#### 3.6.1 Purpose
Provides an authoritative inspection of the Blender scene environment. Extracts active object names, object types, mesh geometry statistics (vertex, edge, polygon, triangle counts), parent-child relationships, material shaders, armatures, cameras, and light sources.

#### 3.6.2 Parameter Specification

| Parameter | Type | Required | Default | Range / Allowed Values | Description |
|-----------|------|----------|---------|------------------------|-------------|
| `scene_name` | `str` | No | `None` | Scene name | Specific scene to inspect (defaults to active scene). |
| `include_mesh_stats` | `bool` | No | `true` | `true`, `false` | Return vertex, edge, and polygon counts for all meshes. |
| `include_hierarchy` | `bool` | No | `true` | `true`, `false` | Return parent-child relationships. |
| `include_materials` | `bool` | No | `true` | `true`, `false` | Inspect Principled BSDF materials and node connections. |
| `include_armatures` | `bool` | No | `true` | `true`, `false` | Inspect armatures, bone names, and parent hierarchies. |
| `include_cameras_lights`| `bool`| No | `true` | `true`, `false` | List camera lenses and light power/types. |

#### 3.6.3 JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "morphomesh_get_scene_status_input",
  "type": "object",
  "properties": {
    "scene_name": { "type": "string", "description": "Specific scene to inspect." },
    "include_mesh_stats": { "type": "boolean", "default": true },
    "include_hierarchy": { "type": "boolean", "default": true },
    "include_materials": { "type": "boolean", "default": true },
    "include_armatures": { "type": "boolean", "default": true },
    "include_cameras_lights": { "type": "boolean", "default": true }
  },
  "additionalProperties": false
}
```

#### 3.6.4 Pydantic v2 Models
```python
class GetSceneStatusInput(BaseModel):
    scene_name: Optional[str] = None
    include_mesh_stats: bool = True
    include_hierarchy: bool = True
    include_materials: bool = True
    include_armatures: bool = True
    include_cameras_lights: bool = True

class SceneObjectInfo(BaseModel):
    name: str
    type: str
    location: list[float]
    rotation_euler: list[float]
    scale: list[float]
    parent: Optional[str] = None
    children: list[str] = Field(default_factory=list)
    vertex_count: int = 0
    face_count: int = 0
    triangle_count: int = 0
    materials: list[str] = Field(default_factory=list)
    modifiers: list[str] = Field(default_factory=list)

class SceneStatusOutput(BaseModel):
    scene_name: str
    blender_version: str
    active_object: Optional[str] = None
    object_count: int
    total_vertices: int
    total_faces: int
    objects: list[SceneObjectInfo]
    armatures: list[Dict[str, Any]] = Field(default_factory=list)
    cameras: list[Dict[str, Any]] = Field(default_factory=list)
    lights: list[Dict[str, Any]] = Field(default_factory=list)
```

#### 3.6.5 Error Conditions & Codes
- `ERR_SCENE_NOT_FOUND`: Specified `scene_name` does not exist in the Blender blend data.
- `ERR_BLENDER_OFFLINE`: Blender bridge unable to connect to active socket or spawn headless instance.

#### 3.6.6 Example Request & Response Payloads
**Request:**
```json
{
  "include_mesh_stats": true,
  "include_armatures": true
}
```

**Response:**
```json
{
  "scene_name": "Scene",
  "blender_version": "5.2.1",
  "active_object": "Armature_Quadruped_DragonDog",
  "object_count": 4,
  "total_vertices": 8120,
  "total_faces": 7980,
  "objects": [
    {
      "name": "DragonDog_Mesh",
      "type": "MESH",
      "location": [0.0, 0.0, 0.0],
      "rotation_euler": [0.0, 0.0, 0.0],
      "scale": [1.0, 1.0, 1.0],
      "parent": "Armature_Quadruped_DragonDog",
      "children": [],
      "vertex_count": 8120,
      "face_count": 7980,
      "triangle_count": 15960,
      "materials": ["M_DragonDog_PBR"],
      "modifiers": ["Armature"]
    },
    {
      "name": "Armature_Quadruped_DragonDog",
      "type": "ARMATURE",
      "location": [0.0, 0.0, 0.0],
      "rotation_euler": [0.0, 0.0, 0.0],
      "scale": [1.0, 1.0, 1.0],
      "parent": null,
      "children": ["DragonDog_Mesh"],
      "vertex_count": 0,
      "face_count": 0,
      "triangle_count": 0,
      "materials": [],
      "modifiers": []
    }
  ],
  "armatures": [
    {
      "name": "Armature_Quadruped_DragonDog",
      "bone_count": 42,
      "root_bones": ["root"]
    }
  ],
  "cameras": [
    { "name": "StudioCamera", "lens_focal_length": 50.0, "type": "PERSP" }
  ],
  "lights": [
    { "name": "KeyLight", "type": "AREA", "energy": 500.0, "color": [1.0, 0.95, 0.9] }
  ]
}
```

---

### 3.7 Tool 7: `morphomesh_render_preview`

#### 3.7.1 Purpose
Renders a preview image of the creature in the Blender scene. Automatically verifies camera presence, sets up standard 3-point studio lighting if needed, frames the subject bounding box, renders using EEVEE (mapped to `BLENDER_EEVEE` in Blender 5.2.1) or Cycles, and returns both an MCP standard `ImageContent` and a structured `TextContent` summary.

#### 3.7.2 Parameter Specification

| Parameter | Type | Required | Default | Range / Allowed Values | Description |
|-----------|------|----------|---------|------------------------|-------------|
| `camera_name` | `str` | No | `None` | Camera object name | Specific camera to render from (auto-frames if omitted). |
| `resolution_width` | `int` | No | `1024` | `256` to `4096` | Output render width. |
| `resolution_height`| `int` | No | `1024` | `256` to `4096` | Output render height. |
| `render_engine` | `str` | No | `"BLENDER_EEVEE"`| `BLENDER_EEVEE`, `BLENDER_EEVEE_NEXT`, `CYCLES`, `BLENDER_WORKBENCH` | Rendering engine (auto-normalized). |
| `samples` | `int` | No | `64` | `1` to `1024` | Number of render samples. |
| `view_angle` | `str` | No | `"three_quarter"` | `front`, `side`, `three_quarter`, `top`, `turntable_4views`, `active_camera` | Perspective orientation for auto-framing camera. |
| `transparent_background`| `bool`| No | `true` | `true`, `false` | Enable RGBA transparency. |
| `lighting_preset` | `str` | No | `"studio_three_point"` | `studio_three_point`, `dramatic_rim`, `neutral_softbox`, `outdoor_sun`, `scene_default` | Lighting environment setup. |
| `save_to_disk` | `bool` | No | `true` | `true`, `false` | Save PNG to persistent cache. |
| `output_dir` | `str` | No | `None` | Directory path | Custom save destination directory. |

#### 3.7.3 JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "morphomesh_render_preview_input",
  "type": "object",
  "properties": {
    "camera_name": { "type": "string", "description": "Camera object name." },
    "resolution_width": { "type": "integer", "minimum": 256, "maximum": 4096, "default": 1024 },
    "resolution_height": { "type": "integer", "minimum": 256, "maximum": 4096, "default": 1024 },
    "render_engine": {
      "type": "string",
      "enum": ["BLENDER_EEVEE", "BLENDER_EEVEE_NEXT", "CYCLES", "BLENDER_WORKBENCH"],
      "default": "BLENDER_EEVEE"
    },
    "samples": { "type": "integer", "minimum": 1, "maximum": 1024, "default": 64 },
    "view_angle": {
      "type": "string",
      "enum": ["front", "side", "three_quarter", "top", "turntable_4views", "active_camera"],
      "default": "three_quarter"
    },
    "transparent_background": { "type": "boolean", "default": true },
    "lighting_preset": {
      "type": "string",
      "enum": ["studio_three_point", "dramatic_rim", "neutral_softbox", "outdoor_sun", "scene_default"],
      "default": "studio_three_point"
    },
    "save_to_disk": { "type": "boolean", "default": true },
    "output_dir": { "type": "string" }
  },
  "additionalProperties": false
}
```

#### 3.7.4 Pydantic v2 Models & MCP Multi-Content Handling
```python
class RenderPreviewInput(BaseModel):
    camera_name: Optional[str] = None
    resolution_width: int = Field(default=1024, ge=256, le=4096)
    resolution_height: int = Field(default=1024, ge=256, le=4096)
    render_engine: Literal["BLENDER_EEVEE", "BLENDER_EEVEE_NEXT", "CYCLES", "BLENDER_WORKBENCH"] = "BLENDER_EEVEE"
    samples: int = Field(default=64, ge=1, le=1024)
    view_angle: Literal["front", "side", "three_quarter", "top", "turntable_4views", "active_camera"] = "three_quarter"
    transparent_background: bool = True
    lighting_preset: Literal["studio_three_point", "dramatic_rim", "neutral_softbox", "outdoor_sun", "scene_default"] = "studio_three_point"
    save_to_disk: bool = True
    output_dir: Optional[str] = None

    @field_validator("render_engine")
    @classmethod
    def normalize_engine(cls, v: str) -> str:
        # Blender 5.2.1 expects 'BLENDER_EEVEE'
        if v == "BLENDER_EEVEE_NEXT":
            return "BLENDER_EEVEE"
        return v

class RenderPreviewOutput(BaseModel):
    image_path: str
    image_format: str = "png"
    resolution: list[int]
    render_engine: str
    samples: int
    render_time_seconds: float
    view_angle: str
    lighting_preset: str
```

#### 3.7.5 Error Conditions & Codes
- `ERR_NO_CAMERA`: No active camera in the scene and automatic procedural camera creation failed.
- `ERR_RENDER_FAILED`: Blender internal render operator failed or GPU buffer crashed.
- `ERR_OUTPUT_WRITE_FAILED`: Image file cannot be saved to the destination path.

#### 3.7.6 Example Request & Response Payloads
**Request:**
```json
{
  "resolution_width": 1024,
  "resolution_height": 1024,
  "render_engine": "BLENDER_EEVEE",
  "view_angle": "three_quarter",
  "lighting_preset": "studio_three_point",
  "transparent_background": true
}
```

**Response (MCP Protocol Level - Multipart ImageContent + TextContent):**
```json
[
  {
    "type": "image",
    "data": "iVBORw0KGgoAAAANSUhEUgAABAAAAAQACA...",
    "mimeType": "image/png"
  },
  {
    "type": "text",
    "text": "{\n  \"image_path\": \"/Users/duongnad/Documents/tool/MorphoMesh/.cache/renders/preview_three_quarter.png\",\n  \"image_format\": \"png\",\n  \"resolution\": [1024, 1024],\n  \"render_engine\": \"BLENDER_EEVEE\",\n  \"samples\": 64,\n  \"render_time_seconds\": 0.716,\n  \"view_angle\": \"three_quarter\",\n  \"lighting_preset\": \"studio_three_point\"\n}"
  }
]
```

---

## 4. FastMCP / MCP SDK Integration Requirements

### 4.1 Server Architecture & Transport Layer
The MorphoMesh server is instantiated using FastMCP from the official `mcp` package (`from mcp.server.fastmcp import FastMCP, Image, Context`).

```python
# src/morphomesh/server.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="MorphoMeshServer",
    instructions="Authoritative MCP Server connecting Google Antigravity 2.0 to Blender 5.2 for 3D Creature Generation.",
    host="127.0.0.1",
    port=8765
)
```

#### Transports Supported
1. **Standard I/O (`stdio`)**: The default transport when spawned as a subprocess by Antigravity (`python -m morphomesh.server`). Messages pass as JSON-RPC over stdin/stdout.
2. **Server-Sent Events (`sse`)**: Used for remote GPU / Docker deployments (`mcp.run_sse_async()` or CLI `--transport sse`).

### 4.2 Tool Registration & Context Injection
Every tool is registered using `@mcp.tool(name=..., description=...)`. Function parameters must use explicit type annotations and Pydantic field constraints to guarantee that FastMCP generates accurate JSON Schema definitions.

Tools that perform long-running operations (such as 3D generation, remeshing, or rendering) take `ctx: Context` as an injected argument:
```python
from mcp.server.fastmcp import Context

@mcp.tool(name="morphomesh_create_3d_asset")
async def create_3d_asset(
    image_path: Optional[str] = None,
    concept_id: Optional[str] = None,
    model_backend: str = "mock",
    ctx: Context = None
) -> dict:
    if ctx:
        await ctx.info(f"Starting 3D asset generation using backend {model_backend}...")
        await ctx.report_progress(25, 100)
    ...
```

### 4.3 Error Mapping & Exception Handling
All custom exceptions inherit from a base `MorphoMeshError` and are mapped to `mcp.server.fastmcp.exceptions.ToolError` with clear error codes:
```python
from mcp.server.fastmcp.exceptions import ToolError

class MorphoMeshError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")

def handle_tool_exceptions(func):
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except MorphoMeshError as e:
            raise ToolError(f"MorphoMesh Tool Error: [{e.code}] {e.message}")
        except Exception as e:
            raise ToolError(f"Unexpected Tool Execution Failure: {str(e)}")
    return wrapper
```

---

## 5. Test Suite Structure & Test Case Definitions (`tests/`)

The automated test suite is structured under `tests/` and runs with `pytest` (`pytest -v tests/`). It covers 100% of the acceptance criteria defined in R4.

### 5.1 Test Directory Structure
```
tests/
├── __init__.py
├── conftest.py                       # Global fixtures (event loop, mock adapters, temp cache, test meshes)
├── test_tools_schema.py              # Schema validation & FastMCP registration for all 7 tools
├── test_inference_adapter.py         # Mock & fallback logic for 2D, 3D, remesh, and rig adapters
├── test_blender_bridge.py            # Serialization, script AST safety analyzer, headless runner
└── test_e2e_offline.py               # Complete 5-stage pipeline invocation in offline mode
```

### 5.2 Fixtures (`tests/conftest.py`)
- `mock_server`: Instantiates the FastMCP server with all 7 tools registered.
- `temp_cache_dir`: Isolated temporary directory for generated mock images, meshes, and blend files.
- `sample_concept_png`: Generates a valid 64x64 PNG in memory for testing image inputs.
- `sample_cube_glb`: Generates a minimal valid binary GLB cube for testing topology and rigging tools.

### 5.3 Test Suite 1: `tests/test_tools_schema.py`
**Objective**: Verify that all 7 tools are registered, schemas match JSON Schema specifications, required fields are enforced, and invalid types/bounds trigger validation errors.

**Key Test Cases**:
1. `test_all_seven_tools_registered()`: Asserts `len(await mcp.list_tools()) == 7` and checks tool names match exact required names.
2. `test_generate_concept_schema()`: Validates required `prompt`, enum restrictions for `creature_type`, `view_mode`, `pose`, `style`, and bounds for `width`/`height`.
3. `test_create_3d_asset_schema()`: Verifies `model_backend` enums and ensures default `export_format == "glb"`.
4. `test_optimize_topology_schema()`: Verifies `target_poly_count` default 10,000 and range bounds [500, 500,000].
5. `test_auto_rig_schema()`: Verifies `creature_type` enums (`quadruped`, `biped`, etc.) and default `skinning_method`.
6. `test_blender_execute_schema()`: Asserts `script` is required, `timeout_seconds` bounded between [1, 300].
7. `test_get_scene_status_schema()`: Asserts all boolean flags default to `True`.
8. `test_render_preview_schema()`: Asserts `render_engine` enums and dimension bounds [256, 4096].
9. `test_invalid_argument_rejection()`: Calls tools with invalid types (e.g. `width="huge"`) and verifies schema validation rejection.

### 5.4 Test Suite 2: `tests/test_inference_adapter.py`
**Objective**: Verify the deterministic mock generation engine, asset synthesis, texture generation, and backend fallback mechanics.

**Key Test Cases**:
1. `test_mock_concept_generation_determinism()`: Calling `generate_concept` with the same seed produces identical file hashes and metadata.
2. `test_mock_concept_generation_custom_params()`: Custom width, height, and style are reflected in generated mock PNG metadata.
3. `test_mock_3d_asset_generation()`: Ingests mock concept image and outputs a valid `.glb` file with non-zero size, valid GLTF header (`b"glTF"`), vertex count > 0, and 4 mock PBR texture paths.
4. `test_mock_topology_optimization()`: Decimates mock mesh to target polycount (e.g., 5,000 faces) and verifies face count reduction.
5. `test_mock_auto_rig_generation()`: Takes mesh asset and outputs rigged model with bone hierarchy (spine, limbs, head) and vertex weight groups.
6. `test_backend_fallback_on_missing_api_key()`: Ensures that if remote GPU backend (e.g. TRELLIS) is requested without API keys, it gracefully raises `ERR_BACKEND_UNAVAILABLE` or falls back to mock mode if configured.

### 5.5 Test Suite 3: `tests/test_blender_bridge.py`
**Objective**: Verify JSON-RPC serialization, AST-based script security filtering, and execution safety.

**Key Test Cases**:
1. `test_command_serialization()`: Verifies commands sent to Blender bridge are properly serialized with action type, parameters, and unique request ID.
2. `test_script_safety_safe_script()`: AST validator approves scripts importing `bpy`, `bmesh`, `mathutils`, and `math`.
3. `test_script_safety_blocks_os_import()`: Rejects `import os` with `ERR_SCRIPT_SECURITY_VIOLATION`.
4. `test_script_safety_blocks_subprocess_import()`: Rejects `import subprocess` with `ERR_SCRIPT_SECURITY_VIOLATION`.
5. `test_script_safety_blocks_eval_exec()`: Rejects calls to `eval("...")` or `exec("...")`.
6. `test_script_safety_blocks_dunder_traversal()`: Rejects expressions like `().__class__.__bases__[0].__subclasses__()`.
7. `test_script_syntax_error_handling()`: Rejects invalid Python code with `ERR_SCRIPT_SYNTAX_ERROR`.
8. `test_blender_execute_mock_and_headless()`: Executes safe script returning variable values (`new_z = 2.0`), verifying stdout capture and variable deserialization.
9. `test_execution_timeout()`: Simulates an infinite loop script and verifies it is killed after timeout with `ERR_SCRIPT_EXECUTION_TIMEOUT`.

### 5.6 Test Suite 4: `tests/test_e2e_offline.py`
**Objective**: Verify the entire 5-stage pipeline can be invoked sequentially through the MCP tools in 100% offline/mock mode without requiring external GPU APIs.

**Key Test Cases**:
1. `test_full_pipeline_offline_sequence()`:
   - Step 1: Call `morphomesh_generate_concept` -> Receive `concept_id` and image path.
   - Step 2: Call `morphomesh_create_3d_asset` with `concept_id` -> Receive `asset_id` and `.glb` path.
   - Step 3: Call `morphomesh_optimize_topology` with `asset_id` -> Receive `optimized_asset_id` (face count reduced).
   - Step 4: Call `morphomesh_auto_rig` with `optimized_asset_id` -> Receive `rigged_asset_id` and bone hierarchy.
   - Step 5: Call `morphomesh_get_scene_status` -> Verify scene contains the rigged creature object.
   - Step 6: Call `morphomesh_blender_execute` -> Apply a safe scale/transform to the creature.
   - Step 7: Call `morphomesh_render_preview` -> Receive rendered image and verify image data buffer.
2. `test_pipeline_idempotency_and_cleanup()`: Verifies that multiple sequential runs do not corrupt scene state and temporary files are cleaned up properly.

---

## 6. Phase 1 PoC to Production Roadmap (`docs/ROADMAP.md` Specification)

The MorphoMesh roadmap spans four distinct phases, guiding the project from the current runnable PoC to an enterprise-grade, real-time creature generation studio.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       MORPHOMESH PRODUCTION ROADMAP                          │
└─────────────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: Runnable PoC & Mock Pipeline Foundation (Current Scope)            │
│ • FastMCP Server with all 7 tools & Pydantic v2 schemas                     │
│ • Headless Blender Bridge (bpy script runner & JSON serialization)          │
│ • Deterministic Mock Inference Adapter (Image, Mesh, Decimate, Rig)         │
│ • AST Script Safety Validator (zero arbitrary code execution)               │
│ • 100% Passing Automated Pytest Suite (tests/)                              │
└─────────────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: Remote GPU AI Inference Integration (Cloud Endpoints)              │
│ • Remote adapters for TRELLIS / TRELLIS.2 and Hunyuan3D-2.1 APIs            │
│ • FLUX / SDXL Creature Concept Gen with LoRA support                        │
│ • High-resolution PBR texture baking (Albedo, Normal, Roughness, Metal)     │
│ • TripoSR / Stable Fast 3D local fallback on Apple Silicon Metal (MPS)      │
│ • Async task queuing with webhook / progress reporting in FastMCP           │
└─────────────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 3: Advanced Topology & Articulation Engine                            │
│ • MeshAnything V2 integration for pure-quad autoregressive retopology       │
│ • Blender QuadriFlow native integration with curvature weighting            │
│ • Deep anatomical landmark prediction (3D keypoint heatmaps for creatures)  │
│ • Rigify Modular Creature Metarigs (Quadruped, Dragon, Bird, Arachnid)      │
│ • Automated Skin Weight Smoothing & Geodesic Voxel fallback                 │
└─────────────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 4: Production Hardening, Live Blender Addon & Studio Orchestration    │
│ • Interactive Blender Addon with live localhost TCP socket server (port 9876)│
│ • Bidirectional viewport camera synchronization & real-time previewing      │
│ • Multi-Agent Antigravity orchestration (Director, Sculptor, Animator agents)│
│ • Procedural Animation Library (walk cycles, wing flaps, idle tail swishes) │
│ • Dockerized deployment & Cloud Render Farm integration                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.1 Phase Breakdown Details

#### Phase 1: Runnable PoC & Mock Pipeline Foundation (Current Target)
- **Goal**: Establish the complete developer architecture, MCP tool schemas, Blender bridge, and 100% passing automated test suite in offline mode.
- **Key Deliverables**:
  - `src/morphomesh/server.py`: FastMCP server registering all 7 tools.
  - `src/morphomesh/blender_bridge.py`: Headless Blender launcher, JSON-RPC communication, AST safety validator.
  - `src/morphomesh/inference_adapter.py`: Mock generation engine producing valid PNGs, GLBs, and rigs.
  - `blender_addon/`: Starter addon template for Blender.
  - `tests/`: Complete pytest test suite.
  - Documentation: `README.md`, `SETUP_GUIDE.md`, `docs/RESEARCH_BENCHMARK.md`, `docs/ARCHITECTURE.md`, `docs/MCP_SPECIFICATION.md`, `docs/ROADMAP.md`.
- **Exit Criteria**: `pytest -v tests/` passes with 0 failures and exit code 0.

#### Phase 2: Remote GPU AI Inference Integration
- **Goal**: Connect real generative AI models hosted on cloud GPU endpoints (Replicate, Hugging Face Inference Endpoints, or custom Linux servers).
- **Key Deliverables**:
  - Replicate / HF adapters for TRELLIS / Hunyuan3D-2.
  - Automatic rembg foreground cutout.
  - Texture unwrapping and PBR material synthesis.
  - Local MPS (Metal Performance Shaders) acceleration for TripoSR on Apple Silicon.
- **Dependencies**: Replicate / HF API keys; Cloud GPU instances.

#### Phase 3: Advanced Topology & Articulation Engine
- **Goal**: Elevate mesh quality from raw AI meshes to animation-ready assets with professional quad topology and custom creature rigs.
- **Key Deliverables**:
  - Auto-retopology via MeshAnything V2 and QuadriFlow with edge crease preservation.
  - Anatomical landmark locator predicting joints for 8 creature archetypes.
  - Automatic Rigify metarig generation and automatic skin weight binding.
  - Deform action library (test walk, run, fly cycles).
- **Dependencies**: Blender Python `bmesh` and `mathutils`; MeshAnything weights.

#### Phase 4: Production Hardening & Interactive Studio Addon
- **Goal**: Enable real-time interactive multi-agent creature generation inside Blender UI with live viewport feedback.
- **Key Deliverables**:
  - Blender GUI panel (`MorphoMesh Addon`) with live socket connection.
  - Real-time EEVEE viewport rendering streamed to Antigravity.
  - Multi-agent collaboration protocols (Art Director, Modeler, Rigger).
  - Production packaging (wheel package, Blender extension zip).

---

## 7. Conclusion & Recommendations for Implementation Track

1. **Strict FastMCP Parameter Unpacking**: In FastMCP, declaring parameters as individual keyword arguments in tool functions (rather than a single nested Pydantic parameter) exposes properties directly at the top level of `inputSchema`. This simplifies LLM tool-calling and prevents nested payload issues.
2. **Blender 5.2.1 LTS Compatibility**: Probing confirms that Blender 5.2.1 LTS is installed at `/Applications/Blender.app/Contents/MacOS/Blender` and runs headless scripts seamlessly. Ensure the render engine string is normalized from `'BLENDER_EEVEE_NEXT'` to `'BLENDER_EEVEE'`.
3. **AST Security Layer**: The AST script safety validator must be implemented in `blender_bridge.py` and tested thoroughly in `tests/test_blender_bridge.py` before executing any script in Blender.
4. **Offline Mock Mode**: The mock inference adapter enables the entire test suite to pass in zero-GPU environments (like CI/CD), while providing the exact interface required for live remote GPU backends in Phase 2.
