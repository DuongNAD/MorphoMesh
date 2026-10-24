# MorphoMesh: Model Context Protocol (MCP) Server Specification

**Document ID**: `MM-R3-SPEC-002`  
**Milestone**: M5 (FastMCP 19-Tool Authoritative Specification)  
**Author**: MorphoMesh Core Protocol & Architecture Team  
**Date**: September 2026  
**Status**: Authoritative Protocol Specification / Publication-Grade Standard  
**Protocol Version**: Model Context Protocol (MCP) 2024-11-05 / FastMCP 1.28.1  
**Target Environments**: Google Antigravity 2.0, Claude Desktop, Python 3.10+, Pydantic v2.10+, Blender 4.x / 5.x LTS  
**Repository Path**: `docs/MCP_SPECIFICATION.md`  

---

## Table of Contents

1. [Executive Summary & System Boundary](#1-executive-summary--system-boundary)
2. [Protocol Architecture & Transport Layer](#2-protocol-architecture--transport-layer)
   - [2.1 FastMCP 1.28.1 SDK Architecture](#21-fastmcp-1281-sdk-architecture)
   - [2.2 Transport Modes: `stdio` vs `sse`](#22-transport-modes-stdio-vs-sse)
   - [2.3 JSON-RPC 2.0 Framing & Envelope Specification](#23-json-rpc-20-framing--envelope-specification)
   - [2.4 Asynchronous Progress Streaming (`Context`)](#24-asynchronous-progress-streaming-context)
3. [Environment Tool Gating & Matrix Filtering](#3-environment-tool-gating--matrix-filtering)
   - [3.1 Tool Gating Architecture](#31-tool-gating-architecture)
   - [3.2 Gating Environment Variables](#32-gating-environment-variables)
   - [3.3 Dual-Layer Gating Mechanism](#33-dual-layer-gating-mechanism)
   - [3.4 Tool Domain Breakdown (19 Tools)](#34-tool-domain-breakdown-19-tools)
4. [Comprehensive Specification of the 19 FastMCP Tools](#4-comprehensive-specification-of-the-19-fastmcp-tools)
   - [Domain 1: 3D Creature Generation & Scene Assembly (7 Tools)](#domain-1-3d-creature-generation--scene-assembly-7-tools)
     - [4.1 `morphomesh_generate_concept`](#41-morphomesh_generate_concept)
     - [4.2 `morphomesh_create_3d_asset`](#42-morphomesh_create_3d_asset)
     - [4.3 `morphomesh_optimize_topology`](#43-morphomesh_optimize_topology)
     - [4.4 `morphomesh_auto_rig`](#44-morphomesh_auto_rig)
     - [4.5 `morphomesh_blender_execute`](#45-morphomesh_blender_execute)
     - [4.6 `morphomesh_get_scene_status`](#46-morphomesh_get_scene_status)
     - [4.7 `morphomesh_render_preview`](#47-morphomesh_render_preview)
   - [Domain 2: Photorealistic Digital Human Pipeline (7 Tools)](#domain-2-photorealistic-digital-human-pipeline-7-tools)
     - [4.8 `morphomesh_create_human_asset`](#48-morphomesh_create_human_asset)
     - [4.9 `morphomesh_auto_rig_human`](#49-morphomesh_auto_rig_human)
     - [4.10 `morphomesh_setup_human_materials`](#410-morphomesh_setup_human_materials)
     - [4.11 `morphomesh_groom_human`](#411-morphomesh_groom_human)
     - [4.12 `morphomesh_dress_human`](#412-morphomesh_dress_human)
     - [4.13 `morphomesh_assemble_master_character`](#413-morphomesh_assemble_master_character)
     - [4.14 `morphomesh_export_production_character`](#414-morphomesh_export_production_character)
   - [Domain 3: Multi-Angle Inspection & Visual Quality Critique (3 Tools)](#domain-3-multi-angle-inspection--visual-quality-critique-3-tools)
     - [4.15 `morphomesh_setup_inspector_camera_rig`](#415-morphomesh_setup_inspector_camera_rig)
     - [4.16 `morphomesh_capture_viewport`](#416-morphomesh_capture_viewport)
     - [4.17 `morphomesh_critique_visual_quality`](#417-morphomesh_critique_visual_quality)
   - [Domain 4: Skeletal Animation & Retargeting (2 Tools)](#domain-4-skeletal-animation--retargeting-2-tools)
     - [4.18 `morphomesh_animate_asset`](#418-morphomesh_animate_asset)
     - [4.19 `morphomesh_list_animations`](#419-morphomesh_list_animations)
5. [Error Taxonomy, Models & Fault Recovery](#5-error-taxonomy-models--fault-recovery)
   - [5.1 Standardized Error Codes (`ErrorCodes`)](#51-standardized-error-codes-errorcodes)
   - [5.2 Error Response Model (`MCPErrorResponse`)](#52-error-response-model-mcperrorresponse)
   - [5.3 ToolError Protocol Serialization](#53-toolerror-protocol-serialization)
6. [Complete JSON-RPC 2.0 Interaction Examples](#6-complete-json-rpc-20-interaction-examples)
   - [6.1 Tool Discovery (`tools/list`) with Gating](#61-tool-discovery-toolslist-with-gating)
   - [6.2 Creature Generation Request & Multipart Response](#62-creature-generation-request--multipart-response)
   - [6.3 Human Character Master Assembly Request](#63-human-character-master-assembly-request)
   - [6.4 Closed-Loop Visual Critique QA Diagnostic Request](#64-closed-loop-visual-critique-qa-diagnostic-request)

---

## 1. Executive Summary & System Boundary

The **MorphoMesh Model Context Protocol (MCP) Server** establishes an authoritative, type-safe API boundary between autonomous AI agents (**Google Antigravity 2.0**, **Claude Desktop**) and digital content creation engines (**Blender 4.x / 5.x LTS**).

MorphoMesh provides exactly **19 atomic, deterministic tools** divided into 4 specialized domains:
1. **Creature Generation & Scene Assembly** (7 tools): Prompt engineering, image-to-3D diffusion, quad retopology, quadruped/chimera auto-rigging, and scene rendering.
2. **Photorealistic Digital Human Pipeline** (7 tools): Base mold morphology, 163 DEF bone Rigify Metarig, 52 ARKit FACS blendshapes, SSS skin materials, Geometry Nodes hair curves, dynamic garments, and master scene packaging.
3. **Inspection & Closed-Loop Visual Critique** (3 tools): Auto-framing camera rigs, fast viewport capture, and mathematical defect critique (>95% benchmark detection for penetration, proportion skew, skinning pinch, and hair collisions).
4. **Skeletal Animation & Retargeting** (2 tools): 340+ action motion library retargeting, idle/walk/run/action clips.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 MORPHOMESH MCP BOUNDARY                                │
└────────────────────────────────────────────────────────────────────────────────────────┘
     Google Antigravity 2.0 / Claude Desktop (Autonomous Agent)
                                │
                                │ JSON-RPC 2.0 over stdio or SSE Transport
                                ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ FastMCP Server (src/morphomesh/server.py / src/morphomesh/tools/)                      │
│  ├── Pydantic v2 Schema Validation Engine                                              │
│  ├── Dual-Layer Tool Gating Matrix (MORPHOMESH_INCLUDE_* flags)                        │
│  ├── Context Lifecycle Manager (Progress streaming, logging, cancellation)            │
│  ├── AST Static Security Sandbox (BpyCodeValidator)                                    │
│  └── Dual Bridge / Inference Dispatcher                                                │
└──────────────────────────────────┬─────────────────────────────────────────────────────┘
                                   │
         ┌─────────────────────────┴─────────────────────────┐
         ▼ (IPC / HTTPS)                                     ▼ (Localhost TCP 9876 / Subprocess)
┌─────────────────────────────────┐                 ┌────────────────────────────────────┐
│ AI Inference Subsystem          │                 │ Blender 4.x / 5.x LTS Environment  │
│ • Mock Adapter (Zero VRAM, CI)  │                 │ • TCP Listener (127.0.0.1:9876)    │
│ • Replicate / HuggingFace APIs  │                 │ • Headless CLI Runner (blender -b) │
│ • Open-Source Hub (TRELLIS)     │                 │ • Rigify 163 DEF Armature Engine   │
│ • Meshy Animation Library       │                 │ • EEVEE / Cycles PBR Raytracing    │
└─────────────────────────────────┘                 └────────────────────────────────────┘
```

---

## 2. Protocol Architecture & Transport Layer

### 2.1 FastMCP 1.28.1 SDK Architecture

MorphoMesh uses the official FastMCP SDK (`mcp.server.fastmcp`). FastMCP manages JSON-RPC request serialization, schema exposure, async dispatch, and multipart artifact handling.

Server instantiation and configuration:
```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="MorphoMeshServer",
    instructions=(
        "Authoritative 3D creation pipeline and Blender MCP bridge. "
        "Coordinates creature generation, digital human synthesis, quad retopology, "
        "Rigify auto-rigging, hair grooming, wardrobe draping, visual QA critique, "
        "and production scene packaging."
    ),
    host="127.0.0.1",
    port=8765,
)
```

### 2.2 Transport Modes: `stdio` vs `sse`

1. **Standard I/O (`stdio`)**: The default and recommended transport for local agent execution. Antigravity or Claude Desktop launches `uv run morphomesh serve` as a child process and communicates via JSON-RPC messages separated by newlines on `stdin`/`stdout`.
2. **Server-Sent Events (`sse`)**: Used for remote or containerized deployment where the server listens on HTTP (`127.0.0.1:8765/sse`) and receives POST RPC commands on `/messages`.

### 2.3 JSON-RPC 2.0 Framing & Envelope Specification

Every exchange adheres to JSON-RPC 2.0:
- **Request**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": "req-101",
    "method": "tools/call",
    "params": {
      "name": "morphomesh_get_scene_status",
      "arguments": {
        "include_objects": true,
        "include_materials": true
      }
    }
  }
  ```
- **Success Response**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": "req-101",
    "result": {
      "content": [
        {
          "type": "text",
          "text": "{\"scene_name\": \"Scene\", \"object_count\": 5, \"status\": \"connected\"}"
        }
      ],
      "isError": false
    }
  }
  ```

### 2.4 Asynchronous Progress Streaming (`Context`)

Tools accept an optional `ctx: Optional[Context]` parameter. When running within an MCP session that supports progress tokens, MorphoMesh emits real-time progress notifications:

```python
await ctx.info("Synthesizing anatomical quad mesh...")
await ctx.report_progress(progress=45, total=100)
```

---

## 3. Environment Tool Gating & Matrix Filtering

### 3.1 Tool Gating Architecture

To prevent context window saturation and allow agents to focus on specific domains, MorphoMesh implements a **Tool Gating Matrix** in `src/morphomesh/tools/gating.py`.

### 3.2 Gating Environment Variables

| Variable | Values | Effect |
|---|---|---|
| *(No flags set)* | Default | Exposes **7 Creature Tools** only (minimal token footprint) |
| `MORPHOMESH_INCLUDE_HUMAN_TOOLS` | `1`, `true`, `yes`, `all` | Exposes **7 Digital Human Tools** (Total: 14 tools) |
| `MORPHOMESH_INCLUDE_INSPECTION_TOOLS` | `1`, `true`, `yes`, `all` | Exposes **3 Inspection & Critic Tools** (Total: 10 tools) |
| `MORPHOMESH_INCLUDE_ALL_TOOLS` | `1`, `true`, `yes`, `all` | Exposes all **17 Core Tools** (Creature + Human + Inspection) |
| `MORPHOMESH_INCLUDE_ANIMATION_TOOLS` | `1`, `true`, `yes`, `all` | Adds **2 Animation Tools** (Total: up to 19 tools) |

### 3.3 Dual-Layer Gating Mechanism

Gating is enforced at two distinct protocol layers:
1. **High-Level FastMCP Layer**: Wraps `mcp.list_tools()` to filter exposed tools returned to agent capabilities queries.
2. **Low-Level JSON-RPC Protocol Layer**: Wraps `mcp._mcp_server.request_handlers[mcp_types.ListToolsRequest]` to filter the raw protocol response.
3. **Execution Invariance**: Direct tool execution via `mcp.call_tool()` remains 100% permitted for all 19 tools regardless of gating flags.

### 3.4 Tool Domain Breakdown (19 Tools)

```
Total Registered Tools: 19
├── Creature Subsystem (7):
│   ├── morphomesh_generate_concept
│   ├── morphomesh_create_3d_asset
│   ├── morphomesh_optimize_topology
│   ├── morphomesh_auto_rig
│   ├── morphomesh_blender_execute
│   ├── morphomesh_get_scene_status
│   └── morphomesh_render_preview
├── Human Subsystem (7):
│   ├── morphomesh_create_human_asset
│   ├── morphomesh_auto_rig_human
│   ├── morphomesh_setup_human_materials
│   ├── morphomesh_groom_human
│   ├── morphomesh_dress_human
│   ├── morphomesh_assemble_master_character
│   └── morphomesh_export_production_character
├── Inspection Subsystem (3):
│   ├── morphomesh_setup_inspector_camera_rig
│   ├── morphomesh_capture_viewport
│   └── morphomesh_critique_visual_quality
└── Animation Subsystem (2):
    ├── morphomesh_animate_asset
    └── morphomesh_list_animations
```

---

## 4. Comprehensive Specification of the 19 FastMCP Tools

### Domain 1: 3D Creature Generation & Scene Assembly (7 Tools)

#### 4.1 `morphomesh_generate_concept`
- **Purpose**: Generates a standardized 2D concept image with anatomical view conditioning (front, side, orthographic turnaround).
- **Gating**: Active by default.
- **Input Schema (`GenerateConceptInput`)**:
  - `prompt` (str, required): Text description of the creature.
  - `negative_prompt` (str, optional, default=""): Negative visual tokens.
  - `view_mode` (ViewMode, default="turnaround_sheet"): `front`, `side`, `three_quarter`, `turnaround_sheet`.
  - `pose` (Pose, default="standing_neutral"): `neutral_t_pose`, `neutral_a_pose`, `standing_neutral`.
  - `style` (Style, default="realistic"): `realistic`, `stylized`, `dark_fantasy`, `sci_fi`.
  - `creature_type` (CreatureType, default="quadruped"): Biological stance archetype.
  - `width` (int, default=1024): Image width in pixels.
  - `height` (int, default=1024): Image height in pixels.
- **Output Schema (`GenerateConceptOutput`)**:
  - `concept_id` (str): Unique UUID identifier.
  - `image_path` (str): Local absolute filesystem path to generated PNG.
  - `image_base64` (str, optional): Base64 image encoding.
  - `view_mode` (str): Resolved view mode.
  - `quality_tier` (str): Execution tier (`draft`, `production`).

#### 4.2 `morphomesh_create_3d_asset`
- **Purpose**: Reconstructs a full 3D textured mesh (OBJ/GLB) with PBR materials from a concept image.
- **Input Schema (`Create3DAssetInput`)**:
  - `concept_image_path` (str, required): Path to 2D concept image.
  - `creature_name` (str, default="creature"): Entity naming prefix.
  - `export_format` (ExportFormat, default="glb"): Output container (`glb`, `obj`, `blend`).
  - `target_polycount` (int, default=50000): Target face budget.
  - `texture_resolution` (int, default=2048): Resolution of PBR maps (Albedo/Normal/Roughness/Metallic).
- **Output Schema (`Create3DAssetOutput`)**:
  - `asset_id` (str): Unique asset identifier.
  - `mesh_path` (str): Absolute path to output 3D geometry file.
  - `polycount` (int): Actual polygon count.
  - `vertex_count` (int): Total vertices.
  - `has_pbr_textures` (bool): True if multi-channel textures were generated.

#### 4.3 `morphomesh_optimize_topology`
- **Purpose**: Retopologizes dense AI meshes into clean, quad-dominant geometry suitable for animation.
- **Input Schema (`OptimizeTopologyInput`)**:
  - `input_mesh_path` (str, required): Source mesh path.
  - `target_polycount` (int, default=10000): Desired polygon budget.
  - `topology_type` (TopologyType, default="quad_dominant"): `quad_dominant`, `pure_quads`, `triangulated`.
  - `preserve_sharp_edges` (bool, default=True): Preserve geometric feature edges.
- **Output Schema (`OptimizeTopologyOutput`)**:
  - `optimized_mesh_path` (str): Path to retopologized mesh.
  - `original_polycount` (int): Pre-optimization face count.
  - `final_polycount` (int): Post-optimization face count.
  - `quad_percentage` (float): Percentage of faces that are quads (>=95% target).

#### 4.4 `morphomesh_auto_rig`
- **Purpose**: Generates an anatomical armature and calculates skin weights for creatures.
- **Input Schema (`AutoRigInput`)**:
  - `mesh_path` (str, required): Path to creature mesh.
  - `creature_type` (CreatureType, default="quadruped"): Anatomical archetype.
  - `rig_type` (RigType, default="rigify_quadruped"): Armature template.
  - `symmetry` (bool, default=True): Enforce bilateral symmetry across X-axis.
- **Output Schema (`AutoRigOutput`)**:
  - `rigged_mesh_path` (str): Output mesh path with armature modifiers.
  - `bone_count` (int): Total deformation bones.
  - `has_skin_weights` (bool): True if skin weights are bound.

#### 4.5 `morphomesh_blender_execute`
- **Purpose**: Executes arbitrary Python scripts securely inside Blender with AST security validation.
- **Input Schema (`BlenderExecuteInput`)**:
  - `code` (str, required): Python code to execute in Blender's interpreter.
  - `timeout` (float, default=30.0): Maximum execution time in seconds.
- **Output Schema (`BlenderExecuteOutput`)**:
  - `success` (bool): Execution outcome.
  - `stdout` (str): Captured standard output.
  - `stderr` (str): Captured standard error.
  - `execution_time` (float): Wall-clock execution time.

#### 4.6 `morphomesh_get_scene_status`
- **Purpose**: Queries current scene statistics, objects, materials, cameras, and polycounts.
- **Input Schema (`SceneStatusInput`)**:
  - `include_objects` (bool, default=True): Include object metadata list.
  - `include_materials` (bool, default=True): Include material names.
  - `include_lights` (bool, default=True): Include light sources.
- **Output Schema (`SceneStatusOutput`)**:
  - `scene_name` (str): Active scene name.
  - `object_count` (int): Total objects in scene.
  - `total_polycount` (int): Aggregated polygon count.
  - `objects` (List[Dict[str, Any]]): Individual object attributes.

#### 4.7 `morphomesh_render_preview`
- **Purpose**: Renders the active Blender camera to an image file and returns multipart ImageContent.
- **Input Schema (`RenderPreviewInput`)**:
  - `camera_name` (str, optional): Target camera name (or active camera if omitted).
  - `resolution_x` (int, default=1280): Viewport width.
  - `resolution_y` (int, default=720): Viewport height.
  - `engine` (RenderEngine, default="BLENDER_EEVEE"): `BLENDER_EEVEE` or `CYCLES`.
  - `samples` (int, default=64): Render sample count.
- **Output Schema (`RenderPreviewOutput`)**:
  - `image_path` (str): Path to saved render PNG.
  - `render_time_seconds` (float): Render duration.

---

### Domain 2: Photorealistic Digital Human Pipeline (7 Tools)

#### 4.8 `morphomesh_create_human_asset`
- **Purpose**: Synthesizes an anthropometrically authentic 3D female human base mold (Yu Nian An proportions: 1.65m height, 7.41 head ratio, 0.70 WHR, teardrop bust, 5-toed feet, 24 vertex groups).
- **Gating**: `MORPHOMESH_INCLUDE_HUMAN_TOOLS=1` or `MORPHOMESH_INCLUDE_ALL_TOOLS=1`.
- **Parameters**: `character_name`, `height`, `head_ratio`, `chest_girth`, `waist_girth`, `hip_girth`, `poly_budget`, `include_blendshapes`, `assemble_master`.

#### 4.9 `morphomesh_auto_rig_human`
- **Purpose**: Generates and binds the industry-standard 163 DEF bone Rigify Human Metarig with geodesic anti-pinch weights and 52 ARKit FACS morph targets.
- **Parameters**: `character_name`, `mesh_path`, `anti_pinch_weights`, `generate_blendshapes`.

#### 4.10 `morphomesh_setup_human_materials`
- **Purpose**: Sets up photorealistic Principled BSDF 2.0 shaders: Random Walk Subsurface Scattering (SSS) skin, 2-chamber refractive corneas, and tear-duct specular wetness.
- **Parameters**: `character_name`, `skin_tone`, `sss_radius`, `eye_color`, `roughness`.

#### 4.11 `morphomesh_groom_human`
- **Purpose**: Synthesizes volumetric Geometry Nodes Hair Curves with natural gravity flow (straight hime bangs, temple sidelocks, back cascade).
- **Parameters**: `character_name`, `hair_style`, `strand_count`, `hair_length`, `hair_color`.

#### 4.12 `morphomesh_dress_human`
- **Purpose**: Creates draped one-piece sundress with sweetheart neckline, ice-blue satin waist sash with bow knot, strappy flat sandals, and cloth physics pin weights (0% Z-fighting).
- **Parameters**: `character_name`, `outfit_preset`, `fabric_type`, `include_sandals`, `clearance_offset`.

#### 4.13 `morphomesh_assemble_master_character`
- **Purpose**: Orchestrates end-to-end master assembly: attaches body, hair, dress, sandals, 10 marionette red threads, 10 glowing butterflies, and sets up 3-point studio lighting.
- **Parameters**: `character_name`, `height`, `head_ratio`, `render_beauty_shots`.

#### 4.14 `morphomesh_export_production_character`
- **Purpose**: Packages and validates production binary deliverables: `Yu_Nian_An_Master.blend`, `Yu_Nian_An.glb` (52 FACS targets in `extras.targetNames`), and `Yu_Nian_An.fbx` (163 DEF bones).
- **Parameters**: `character_name`, `output_dir`, `export_blend`, `export_glb`, `export_fbx`.

---

### Domain 3: Multi-Angle Inspection & Visual Quality Critique (3 Tools)

#### 4.15 `morphomesh_setup_inspector_camera_rig`
- **Purpose**: Computes character 3D bounding box and sets up an automated inspection camera rig with standard viewpoints (`front`, `side`, `three_quarter`, `turntable_4views`, `head_closeup`, `paw_closeup`).
- **Gating**: `MORPHOMESH_INCLUDE_INSPECTION_TOOLS=1` or `MORPHOMESH_INCLUDE_ALL_TOOLS=1`.
- **Parameters**: `target_object`, `viewpoints`, `margin_ratio`, `lens_focal_length`.

#### 4.16 `morphomesh_capture_viewport`
- **Purpose**: Executes high-speed OpenGL/Workbench viewport capture and returns base64 PNG preview.
- **Parameters**: `viewpoint`, `width`, `height`, `shading_mode` (`MATERIAL`, `SOLID`, `WIREFRAME`).

#### 4.17 `morphomesh_critique_visual_quality`
- **Purpose**: Closed-loop automated visual QA inspection. Evaluates cloth-body mesh penetration, body anthropometric proportions, joint deformation pinch/volume loss, and hair-scalp grooming collisions. Returns structured defect diagnosis and pass/fail score.
- **Parameters**: `body_object`, `garment_objects`, `hair_objects`, `target_preset`, `confidence_threshold`.

---

### Domain 4: Skeletal Animation & Retargeting (2 Tools)

#### 4.18 `morphomesh_animate_asset`
- **Purpose**: Retargets skeletal motion clips (Idle, Walk, Run, Attack, Spell Cast, etc.) from the Meshy 340+ action library onto a rigged character.
- **Gating**: `MORPHOMESH_INCLUDE_ANIMATION_TOOLS=1`.
- **Parameters**: `asset_id`, `rig_task_id`, `action_id`, `action_name`, `fps`, `output_format`.

#### 4.19 `morphomesh_list_animations`
- **Purpose**: Searches and lists available animation library presets with category filtering.
- **Parameters**: `category`, `search_query`, `limit`.

---

## 5. Error Taxonomy, Models & Fault Recovery

### 5.1 Standardized Error Codes (`ErrorCodes`)

MorphoMesh enforces 32 standardized error codes across 8 categories.

> **Note on Protocol Error Mapping**: The 1xxx–6xxx error codes listed below represent the internal application error taxonomy. Over the wire, JSON-RPC protocol errors use the negative `-32xxx` series defined in `morphomesh.models.errors` (e.g. `ERR_INVALID_REQUEST = -32600`, `ERR_BACKEND_UNAVAILABLE = -32002`).

```
Error Taxonomy:
├── Client & Validation:
│   ├── INVALID_INPUT (1001)
│   ├── SCHEMA_VALIDATION_ERROR (1002)
│   └── UNSUPPORTED_VIEW_MODE (1003)
├── Blender Bridge:
│   ├── BRIDGE_CONNECTION_ERROR (2001)
│   ├── BRIDGE_TIMEOUT (2002)
│   ├── SCRIPT_EXECUTION_FAILED (2003)
│   ├── AST_SECURITY_VIOLATION (2004)
│   └── SCENE_NOT_FOUND (2005)
├── Generative Inference:
│   ├── INFERENCE_TIMEOUT (3001)
│   ├── MODEL_UNAVAILABLE (3002)
│   └── CIRCUIT_BREAKER_OPEN (3003)
├── Topology & Rigging:
│   ├── RETOPOLOGY_FAILED (4001)
│   ├── NON_MANIFOLD_GEOMETRY (4002)
│   ├── RIGIFY_GENERATION_FAILED (4003)
│   └── WEIGHT_SOLVER_DIVERGENCE (4004)
├── Human & Wardrobe:
│   ├── BASE_MOLD_LOAD_ERROR (5001)
│   ├── CLOTH_COLLISION_FAILED (5002)
│   └── BLENDSHAPE_DELTA_ERROR (5003)
└── Visual Critique QA:
    ├── PENETRATION_DETECTED (6001)
    ├── PROPORTION_DEVIATION (6002)
    └── JOINT_PINCH_COLLAPSE (6003)
```

### 5.2 Error Response Model (`MCPErrorResponse`)

```python
class MCPErrorResponse(BaseModel):
    error_code: str
    message: str
    component: str
    details: Dict[str, Any] = Field(default_factory=dict)
    retryable: bool = False
    remediation_hint: Optional[str] = None
```

### 5.3 ToolError Protocol Serialization

Whenever an internal exception occurs, tools wrap it into FastMCP's native `ToolError`:
```python
from mcp.server.fastmcp.exceptions import ToolError
raise ToolError(f"MorphoMesh Tool Error: [{e.code}] {e.message}")
```

---

## 6. Complete JSON-RPC 2.0 Interaction Examples

### 6.1 Tool Discovery (`tools/list`) with Gating

#### Request:
```json
{
  "jsonrpc": "2.0",
  "id": "list-001",
  "method": "tools/list",
  "params": {}
}
```

#### Response (Default: Creature Tools Only):
```json
{
  "jsonrpc": "2.0",
  "id": "list-001",
  "result": {
    "tools": [
      {
        "name": "morphomesh_generate_concept",
        "description": "Synthesizes 2D concept image for 3D creature generation.",
        "inputSchema": {
          "type": "object",
          "properties": {
            "prompt": {"type": "string", "description": "Text description of creature."}
          },
          "required": ["prompt"]
        }
      },
      {
        "name": "morphomesh_create_3d_asset",
        "description": "Reconstruct 3D textured mesh from 2D concept image."
      },
      {
        "name": "morphomesh_optimize_topology",
        "description": "Optimize mesh topology to quad-dominant animation mesh."
      },
      {
        "name": "morphomesh_auto_rig",
        "description": "Generate biological armature and skin weights."
      },
      {
        "name": "morphomesh_blender_execute",
        "description": "Execute secure bpy script in Blender."
      },
      {
        "name": "morphomesh_get_scene_status",
        "description": "Query Blender scene objects and statistics."
      },
      {
        "name": "morphomesh_render_preview",
        "description": "Render viewport preview image."
      }
    ]
  }
}
```

### 6.2 Creature Generation Request & Multipart Response

#### Request:
```json
{
  "jsonrpc": "2.0",
  "id": "gen-002",
  "method": "tools/call",
  "params": {
    "name": "morphomesh_create_3d_asset",
    "arguments": {
      "concept_image_path": "output/concepts/bear_warrior.png",
      "creature_name": "Armored_War_Bear",
      "target_polycount": 35000,
      "export_format": "glb"
    }
  }
}
```

#### Response:
```json
{
  "jsonrpc": "2.0",
  "id": "gen-002",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"asset_id\": \"asset_7b8a1c\", \"mesh_path\": \"output/Armored_War_Bear.glb\", \"polycount\": 34820, \"vertex_count\": 17412, \"has_pbr_textures\": true}"
      }
    ],
    "isError": false
  }
}
```

### 6.3 Closed-Loop Visual Critique QA Diagnostic Request

#### Request:
```json
{
  "jsonrpc": "2.0",
  "id": "critique-003",
  "method": "tools/call",
  "params": {
    "name": "morphomesh_critique_visual_quality",
    "arguments": {
      "body_object": "Yu_Nian_An_Body",
      "garment_objects": ["Dress_Bodice", "Dress_Skirt"],
      "target_preset": "stylized_heroine",
      "confidence_threshold": 0.85
    }
  }
}
```

#### Response:
```json
{
  "jsonrpc": "2.0",
  "id": "critique-003",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"passed\": true, \"quality_score\": 0.985, \"defects_found\": 0, \"penetration_depth_max\": 0.0, \"whr_ratio\": 0.698, \"recommendations\": []}"
      }
    ],
    "isError": false
  }
}
```
