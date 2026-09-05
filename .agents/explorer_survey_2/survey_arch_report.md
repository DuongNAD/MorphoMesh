# MorphoMesh Architectural Survey & Technical Specification
**Requirements Focus**: R2 (System Architecture & Pipeline Specification) & R4 (Runnable PoC & Blender Bridge)  
**Author**: Survey Explorer 2  
**Date**: 2026-09-05  
**Target Environment**: macOS (Apple Silicon M-series, Darwin aarch64), Blender 5.2.1 LTS, FastMCP / Python 3.11+, Remote GPU Backends (CUDA 12.x)

---

## 1. Executive Summary

MorphoMesh is an automated pipeline and Model Context Protocol (MCP) server connecting Google Antigravity 2.0 with Blender, specialized in text-to-3D creature generation (quadrupeds, bipeds, winged beasts, serpents, and fantasy entities). 

This architectural survey delivers the technical design and implementation blueprint for:
1. **Hybrid Execution Topology**: Seamlessly partitioning work between an Apple Silicon client workstation (coordination, UI, Blender scene assembly, real-time rendering) and Remote GPU clusters (heavy multi-billion-parameter 3D diffusion and autoregressive mesh generation).
2. **Dual-Mode Blender Communication Bridge**: Supporting both interactive session synchronization via non-blocking localhost TCP sockets (`bpy.app.timers`) and unattended batch operations via headless CLI invocation (`blender --background --python`).
3. **Rigorous Multi-Layer Security**: Preventing arbitrary code execution in Blender through strict AST static analysis, module blacklisting, and a typed JSON-RPC 2.0 action protocol.
4. **Plug-and-Play Inference Layer**: Designing `inference_adapter.py` to enable instant offline testing with deterministic procedural mock assets (0 VRAM, 0 API cost, 100% unit-testable) while providing production adapters for Replicate, HuggingFace, and custom Linux GPU servers.
5. **5-Stage End-to-End Creature Dataflow**: From anatomically constrained concept art to quad-retopologized, skinned, rigged, and studio-lit assets inside Blender.
6. **Production-Ready Blender Addon Structure**: Modular packaging of `blender_addon/morphomesh` with a 1-click zip builder.

---

## 2. macOS Client Environment & Hybrid Architectural Topology

### 2.1 Hardware Context & Apple Silicon Realities
Development and client execution take place on macOS Apple Silicon (ARM64 / aarch64, M1/M2/M3/M4 series).

| Dimension | Apple Silicon Client (macOS) | Remote GPU Backend (Linux x86_64) |
|---|---|---|
| **Hardware** | M-series SoC (Unified Memory: 16GB–128GB) | NVIDIA RTX 4090 (24GB) / A100 (80GB) / H100 |
| **Compute APIs** | Apple Metal, Metal Performance Shaders (MPS) | NVIDIA CUDA 12.x, TensorRT, FlashAttention |
| **3D GenAI Limitations** | Incompatible with custom CUDA C++ extensions (`diff-gaussian-rasterization`, `nvdiffrast`, `spconv`, `cuda-rasterizer`). Unified memory subject to OS process limits (`sysctl iogpu.wired_mem_limit`). | Native support for all SOTA 3D diffusion, NeRF, and Gaussian Splatting kernels. |
| **Optimal Roles** | FastMCP Server, Antigravity Agent coordination, Blender UI manipulation, EEVEE-Next Metal rendering, local QuadriFlow remeshing, image preprocessing (CoreML/ONNX). | TRELLIS.2 (4B), Hunyuan3D 2.1, FLUX.1, MeshAnything V2, high-VRAM texture diffusion. |

### 2.2 The Hybrid Architectural Solution
Because porting custom CUDA kernels to Apple Metal is non-viable for heavy 3D diffusion models, MorphoMesh implements a **Hybrid Tiered Architecture**:

```
+-----------------------------------------------------------------------------------+
|                           MACOS WORKSTATION (Apple Silicon)                       |
|                                                                                   |
|  +------------------------+              JSON-RPC 2.0 / Stdio                     |
|  | Google Antigravity 2.0 | <=====================================>+             |
|  | Agent Host             |                                        |             |
|  +------------------------+                                        v             |
|                                                     +--------------------------+  |
|                                                     |   MorphoMesh MCP Server  |  |
|                                                     |    (FastMCP / Python)    |  |
|                                                     +------------+-------------+  |
|                                                                  |                |
|                    +---------------------------------------------+                |
|                    |                                             |                |
|                    v (Dual-Mode Bridge)                          v (Adapter API)  |
|      +-----------------------------+               +--------------------------+  |
|      |       Blender Bridge        |               |    Inference Adapter     |  |
|      |      (blender_bridge.py)    |               |  (inference_adapter.py)  |  |
|      +--------------+--------------+               +-------------+------------+  |
|                     |                                            |                |
|         +-----------+-----------+                     +----------+----------+     |
|         |                       |                     |                     |     |
|         v                       v                     v                     v     |
|  [Interactive Mode]     [Headless Mode]         [Mock / Dev Mode]    [Local Fallback]
|  Localhost TCP Socket    CLI Subprocess         Deterministic Gen    ONNX Rembg / |
|  Port 9876 (Addon)       blender -b -P          0 VRAM, 0 API Cost   QuadriFlow   |
|         |                       |                     |                     |     |
|         v                       v                     |                     |     |
|  +-------------------------------------+              |                     |     |
|  |       Blender 5.2.1 LTS             |              |                     |     |
|  | - Viewport & Metal EEVEE-Next       |              |                     |     |
|  | - Armature & Auto-Weights           |              |                     |     |
|  | - QuadriFlow & PBR Materials        |              |                     |     |
|  +-------------------------------------+              |                     |     |
+-------------------------------------------------------|---------------------|-----+
                                                        | (HTTPS / REST)      |
                                                        v                     v
                             +------------------------------------------------------+
                             |                REMOTE GPU CLOUD CLUSTER              |
                             |  - Replicate API (FLUX, TripoSR, Hunyuan3D-2)        |
                             |  - Hugging Face Inference Endpoints / Spaces         |
                             |  - Custom Linux GPU Server (TRELLIS.2 4B,            |
                             |    MeshAnything V2, 1x/2x RTX 4090 / A100)           |
                             +------------------------------------------------------+
```

---

## 3. Blender Communication Layer Architecture

### 3.1 IPC Mechanism Comparison & Dual-Mode Strategy
To support both real-time interactive workflows (where a 3D artist watches the creature appear in Blender's 3D viewport) and automated, headless CI/CD testing, MorphoMesh implements a **Dual-Mode Blender Bridge**.

| Mechanism | Latency | Interactivity | Reliability in CI/CD | Cross-Platform | Evaluation |
|---|---|---|---|---|---|
| **Localhost TCP Socket** (`127.0.0.1:9876`) | < 2 ms | High (Live 3D Viewport) | Requires active process | Excellent (macOS/Linux/Win) | **Primary Mode**: Real-time interactive session via Blender Addon |
| **Unix Domain Socket** (`/tmp/blender.sock`) | < 1 ms | High | Broken if file locks linger | POSIX only | Not cross-platform, higher operational friction |
| **Headless CLI Execution** (`blender -b -P script.py`) | 800–1500 ms (startup overhead) | None (Background) | 100% deterministic, zero state leaks | Excellent | **Secondary / Fallback Mode**: Ideal for batch jobs, CI test suite (`pytest`) |

#### Operational Flow of Dual-Mode Bridge:
1. When an MCP tool calls `BlenderBridge.execute_command(method, params)`:
2. The bridge first attempts a TCP handshake to `127.0.0.1:9876` (timeout: 500ms).
3. **If connected**: Transmits JSON-RPC payload to the running Blender instance. Blender executes the command on its main thread and returns the result.
4. **If connection refused**: The bridge transparently falls back to `BlenderHeadlessRunner`, spawning `/Applications/Blender.app/Contents/MacOS/Blender --background --python <runner_script>` passing parameters via temporary JSON files or CLI arguments, capturing structured output from stdout between sentinel tokens (`MORPHOMESH_START_JSON` ... `MORPHOMESH_END_JSON`).

### 3.2 Blender Threading & Non-Blocking Event Loop
Blender's internal C/Python architecture is strictly single-threaded with respect to data mutations (`bpy.data`, `bpy.ops`). Calling `bpy.ops` from an asynchronous background thread causes memory corruption or immediate segmentation faults.

#### The Safe Synchronization Pattern:
1. **Background Socket Thread**: Accepts client connections and receives incoming JSON-RPC data packets. It parses frames and pushes requests to a thread-safe Python `queue.Queue`.
2. **Main Thread Timer Hook**: Inside Blender, `bpy.app.timers.register(process_queue, first_interval=0.05)` registers a high-frequency polling callback.
3. Every 50ms, `process_queue` dequeues pending requests, executes them within Blender's valid main-thread execution context, gathers results, and places the response onto a response queue.
4. The background socket thread picks up the response and transmits it back over the TCP socket.

```python
# Conceptual Addon Synchronization Pattern
import bpy
import queue
import threading

request_queue = queue.Queue()
response_queue = queue.Queue()

def process_queue_timer():
    while not request_queue.empty():
        req_id, method, params = request_queue.get()
        try:
            handler = METHOD_REGISTRY.get(method)
            if not handler:
                raise ValueError(f"Unknown method: {method}")
            # Executes safely in Blender main thread!
            result = handler(**params)
            response_queue.put((req_id, {"status": "success", "data": result}))
        except Exception as e:
            response_queue.put((req_id, {"status": "error", "message": str(e)}))
    return 0.05  # Re-run every 50ms without blocking Blender UI
```

### 3.3 Security Validation Architecture
Allowing an external MCP client or AI agent to execute code inside Blender presents significant security risks (remote code execution, data exfiltration, deletion of user files).

MorphoMesh enforces a **Two-Tier Security Sandbox**:

#### Tier 1: Typed Structured Action Protocol (Whitelisted Methods)
95% of all operations never pass raw Python code. All standard pipeline steps use predefined JSON-RPC methods (`morphomesh.import_mesh`, `morphomesh.retopology`, `morphomesh.auto_rig`, `morphomesh.setup_materials`, `morphomesh.render_preview`). The parameters are strictly typed using Pydantic models.

#### Tier 2: AST Static Analysis Validator for `morphomesh_blender_execute`
When the Antigravity agent needs custom procedural flexibility via `morphomesh_blender_execute`, the code is subjected to strict Abstract Syntax Tree (AST) validation before transmission and before execution:

1. **Module Whitelist**: Only `bpy`, `math`, `mathutils`, `bmesh`, and `numpy` are permitted. Any `Import` or `ImportFrom` referencing `os`, `sys`, `subprocess`, `shutil`, `socket`, `http`, `urllib`, `requests`, `multiprocessing`, `threading`, `ctypes`, `importlib`, `builtins`, `posix`, or `inspect` is rejected immediately with a security violation error.
2. **Call Blacklist**: Direct calls to `eval()`, `exec()`, `__import__()`, `compile()`, `open()`, `input()`, `globals()`, `locals()`, `getattr()`, `setattr()`, or `delattr()` are strictly forbidden.
3. **Dunder Reflection Defense**: Inspecting attributes starting and ending with `__` (such as `__subclasses__`, `__globals__`, `__code__`, `__class__`, `__dict__`) is blocked to thwart Python sandbox escape exploits.
4. **Execution Safeguards**: Code length is capped at 10,000 characters; execution timeout is strictly enforced (default: 15.0 seconds).

```python
# AST Security Validator
import ast

class SecurityException(Exception):
    pass

class BpyCodeValidator(ast.NodeVisitor):
    ALLOWED_MODULES = {"bpy", "math", "mathutils", "bmesh", "numpy"}
    FORBIDDEN_CALLS = {"eval", "exec", "__import__", "compile", "open", "input"}
    
    def visit_Import(self, node):
        for alias in node.names:
            base = alias.name.split(".")[0]
            if base not in self.ALLOWED_MODULES:
                raise SecurityException(f"Forbidden module import: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            base = node.module.split(".")[0]
            if base not in self.ALLOWED_MODULES:
                raise SecurityException(f"Forbidden module import from: {node.module}")
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id in self.FORBIDDEN_CALLS:
            raise SecurityException(f"Forbidden function call: {node.func.id}()")
        self.generic_visit(node)

    def visit_Attribute(self, node):
        if node.attr.startswith("__") and node.attr.endswith("__"):
            raise SecurityException(f"Forbidden dunder attribute access: {node.attr}")
        self.generic_visit(node)
```

### 3.4 Command Serialization Format (JSON-RPC 2.0)
Communication across the socket uses standard **JSON-RPC 2.0** with newline-delimited framing (`ndjson`):

#### Request Schema:
```json
{
  "jsonrpc": "2.0",
  "id": "req-9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "method": "morphomesh.optimize_topology",
  "params": {
    "target_faces": 5000,
    "preserve_boundary": true,
    "use_symmetry": true,
    "smooth_normals": true
  }
}
```

#### Success Response Schema:
```json
{
  "jsonrpc": "2.0",
  "id": "req-9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "result": {
    "status": "success",
    "object_name": "Creature_Mesh_Quad",
    "vertex_count": 2502,
    "polygon_count": 5000,
    "topology_type": "quad_dominant",
    "elapsed_seconds": 1.42
  }
}
```

#### Error Response Schema:
```json
{
  "jsonrpc": "2.0",
  "id": "req-9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "error": {
    "code": -32602,
    "message": "Invalid params: target_faces must be between 100 and 500000",
    "data": {"provided": 0}
  }
}
```

#### Method Registry Table:
| Method | Description | Key Parameters |
|---|---|---|
| `morphomesh.ping` | Healthcheck and latency probe | None |
| `morphomesh.get_scene_status` | Inspect scene hierarchy, active objects, mesh metrics | `detailed: bool` |
| `morphomesh.import_asset` | Import `.glb` / `.obj` file into specified collection | `filepath: str`, `collection_name: str` |
| `morphomesh.optimize_topology` | Run QuadriFlow / Voxel remeshing on active mesh | `target_faces: int`, `preserve_boundary: bool` |
| `morphomesh.create_armature` | Generate anatomical creature rig and bind skin weights | `creature_type: str`, `scale: float` |
| `morphomesh.setup_materials` | Configure Principled BSDF node network with PBR textures | `object_name: str`, `texture_paths: dict` |
| `morphomesh.render_preview` | Auto-frame camera, configure lighting, and render PNG | `resolution: list`, `engine: str`, `filepath: str` |
| `morphomesh.execute_custom_script` | Run validated Python `bpy` script | `code: str`, `timeout: float` |

---

## 4. AI Inference Layer (`inference_adapter.py`)

### 4.1 Plug-and-Play Architecture
The inference layer decouples the MCP tool contracts from specific AI models or cloud vendors using the Abstract Factory and Strategy patterns:

```
                      +-----------------------------+
                      |    BaseInferenceAdapter     |
                      |   (Abstract Base Class)     |
                      +--------------+--------------+
                                     ^
         +---------------------------+---------------------------+
         |                           |                           |
+--------+--------+         +--------+--------+         +--------+--------+
|  MockInference  |         | ReplicateInference|       |  CustomServer   |
|     Adapter     |         |     Adapter     |         |    Inference    |
| (Offline / Dev) |         |  (Cloud Hosted) |         | (Dedicated GPU) |
+-----------------+         +-----------------+         +-----------------+
```

#### Common Interface Contract:
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel

class ConceptRequest(BaseModel):
    prompt: str
    creature_type: str = "quadruped" # quadruped, biped, winged, serpent
    style_preset: str = "realistic"
    negative_prompt: Optional[str] = None

class ConceptResult(BaseModel):
    image_path: str
    rgba_image_path: str
    metadata: Dict[str, Any]

class MeshGenerationRequest(BaseModel):
    image_path: str
    format: str = "glb"
    texture_resolution: int = 2048

class MeshResult(BaseModel):
    mesh_path: str
    poly_count: int
    texture_paths: Dict[str, str] # base_color, normal, roughness, metallic
    format: str

class BaseInferenceAdapter(ABC):
    @abstractmethod
    def generate_concept(self, req: ConceptRequest) -> ConceptResult:
        """Generate 2D concept art and clean RGBA alpha silhouette."""
        pass

    @abstractmethod
    def generate_3d_mesh(self, req: MeshGenerationRequest) -> MeshResult:
        """Generate 3D mesh geometry and PBR texture maps from image."""
        pass
```

### 4.2 Mock / Offline Mode Specification
To allow complete offline development, continuous integration (`pytest`), and rapid local iteration without GPU costs or API tokens, the `MockInferenceAdapter` provides:

1. **Deterministic Geometry Synthesis**:
   - Generates mathematically valid `.glb` and `.obj` meshes with correct normals, UV texture coordinates, and manifold topology.
   - Presets available:
     * `quadruped_proxy`: Anatomical proxy containing a torso cylinder, 4 cylindrical leg limbs, neck, box head, and tapered tail.
     * `biped_proxy`: Torso, head, 2 legs, 2 arms.
     * `winged_proxy`: Quadruped body with 2 planar/extruded wing membranes.
     * `primitive_proxy`: UV sphere or smoothed cube for lightweight testing.
2. **Procedural Texture Maps**:
   - Synthetic 1024x1024 / 2048x2048 PNG textures generated via Python `PIL.Image`:
     * `base_color`: Colored diffuse map with grid/checker coordinate guides.
     * `normal`: Flat tangent normal `(128, 128, 255)` with subtle bevel gradients.
     * `roughness`: 8-bit grayscale map (default 0.6 roughness).
     * `metallic`: 8-bit grayscale map (default 0.0 non-metal).
3. **Reproducibility**:
   - Seed-based deterministic output: identical prompts generate identical meshes and vertex counts, ensuring assertions in automated tests never flake.

### 4.3 Production Remote GPU Adapters
1. **`ReplicateInferenceAdapter`**:
   - Utilizes the Replicate REST API (`predictions.create`).
   - Concept generation: FLUX.1-schnell / SDXL with creature prompt templates.
   - 3D Generation: TripoSR / Hunyuan3D-2 / InstantMesh API models.
   - Features: Exponential backoff polling, automated download of asset URLs, local filesystem caching.
2. **`HuggingFaceInferenceAdapter`**:
   - Interacts with Hugging Face Serverless Inference APIs or dedicated Dedicated Endpoints hosting models such as Step1X-3D or Stable Fast 3D.
3. **`CustomServerInferenceAdapter`**:
   - High-throughput gRPC or REST/WebSocket client targeting a dedicated Linux server equipped with NVIDIA RTX 4090 / A100 GPUs running SOTA pipelines:
     * **TRELLIS.2 (4B)** for unprecedented high-fidelity geometry and continuous latent representation.
     * **MeshAnything V2** for true autoregressive artist-grade quad retopology.

### 4.4 Local Fallback Engine (Apple Silicon)
When remote services are offline or for intermediate preprocessing:
- **Image Preprocessing & Background Removal**: Local execution of `rembg` (using ONNX Runtime CPU/Metal execution provider) or Apple CoreML to isolate the creature silhouette against a transparent alpha channel.
- **Local Remeshing**: Headless execution of Blender's native QuadriFlow engine (`bpy.ops.object.quadriflow_remesh`) or Voxel Remesher (`bpy.ops.object.voxel_remesh`), requiring zero third-party C++ compilation on macOS.
- **Local Mesh Sanity Checks**: Verification of vertex counts, non-manifold edge counts, and bounding box dimensions.

---

## 5. Detailed 5-Stage End-to-End Dataflow

```
+----------------------------------------------------------------------------------------------------+
|                               MORPHOMESH 5-STAGE PIPELINE DATAFLOW                                 |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|  [STAGE 1: CONCEPT GENERATION]                                                                     |
|  User Prompt: "Armored frost dragon, quadruped stance, large wings"                                |
|         |                                                                                          |
|         v                                                                                          |
|  +----------------------------------------------------------------------------------------------+  |
|  | Prompt Expansion: Neutral A-pose, orthographic lateral view, closed mouth, neutral gray bg |  |
|  | Negative Prompt: Dynamic action pose, perspective distortion, props, occluded limbs         |  |
|  | Generator (FLUX / SDXL) -> 2D RGB Concept -> Rembg Alpha Masking -> Clean 2D RGBA Image     |  |
|  +----------------------------------------------------------------------------------------------+  |
|         |                                                                                          |
|         v (RGBA PNG Asset)                                                                         |
|                                                                                                    |
|  [STAGE 2: SINGLE-IMAGE TO 3D GENERATION]                                                          |
|  +----------------------------------------------------------------------------------------------+  |
|  | 3D Diffusion / Reconstruction (TRELLIS.2 / Hunyuan3D-2 / TripoSR)                            |  |
|  | Surface Extraction: Marching Cubes / FlexiCubes -> Dense Tri-Mesh (100k - 500k triangles)    |  |
|  | PBR Synthesis: BaseColor, Tangent-Space Normal, Roughness, Metallic                          |  |
|  | Output Artifact: high_poly_raw.glb                                                            |  |
|  +----------------------------------------------------------------------------------------------+  |
|         |                                                                                          |
|         v (Dense GLB Asset)                                                                        |
|                                                                                                    |
|  [STAGE 3: TOPOLOGY OPTIMIZATION]                                                                  |
|  +----------------------------------------------------------------------------------------------+  |
|  | Geometric Healing: Remove isolated floaters, fill holes, weld degenerate vertices           |  |
|  | Quad Remeshing: MeshAnything V2 (Remote) or Blender QuadriFlow (Local Apple Silicon)        |  |
|  | Poly Budget Target: 5,000 - 20,000 quads; X-axis symmetry enforcement                       |  |
|  | UV Parameterization: Non-overlapping conformal UV atlas (Smart UV Project / xatlas)         |  |
|  | Texture Baking: High-to-low normal map & albedo transfer baking                             |  |
|  | Output Artifact: optimized_quad.glb                                                          |  |
|  +----------------------------------------------------------------------------------------------+  |
|         |                                                                                          |
|         v (Clean Quad GLB Asset)                                                                   |
|                                                                                                    |
|  [STAGE 4: SKELETON & RIGGING AUTOMATION]                                                          |
|  +----------------------------------------------------------------------------------------------+  |
|  | Landmark Detection: Volumetric skeletonization (Medial Axis Transform / bounding heuristics)|  |
|  | Template Selection: Quadruped / Biped / Winged / Serpent armature schema                     |  |
|  | Armature Fitting: Bone alignment to morphological landmarks (Spine, Neck, Limbs, Wings)    |  |
|  | Skin Weighting: Blender Biharmonic Heat Diffusion (`ARMATURE_AUTO`) with distance fallback   |  |
|  | Output Hierarchy: Armature Object + Parented Deform Mesh with Vertex Groups                  |  |
|  +----------------------------------------------------------------------------------------------+  |
|         |                                                                                          |
|         v (Rigged Scene Graph)                                                                     |
|                                                                                                    |
|  [STAGE 5: BLENDER SCENE ASSEMBLY]                                                                 |
|  +----------------------------------------------------------------------------------------------+  |
|  | Scene Graph Organization: Collection `MorphoMesh_Creatures`                                  |  |
|  | Material Network: Principled BSDF 2.0 with PBR Image Textures (BaseColor, Normal, Roughness) |  |
|  | Modifier Setup: Armature Modifier + Optional Subdivision Surface (Render Only)               |  |
|  | Studio Lighting: 3-Point Studio Rig (Warm Key Light, Cool Fill Light, Sharp Rim Light)       |  |
|  | Framing & Camera: Auto-focus bounding box, depth of field preview                           |  |
|  | Viewport Render: Metal EEVEE-Next thumbnail render -> Base64 / PNG preview for Agent        |  |
|  +----------------------------------------------------------------------------------------------+  |
|                                                                                                    |
+----------------------------------------------------------------------------------------------------+
```

### 5.1 Stage 1: Prompt Engineering & Concept Generation
Creature generation requires specific anatomical posture to facilitate downstream 3D reconstruction and rigging:
1. **Pose Standardization**: Animals and creatures must be generated in a neutral standing posture (A-pose or quadruped neutral stance) with legs parallel, feet planted, neck extended, and mouth closed. Winged creatures require partially spread wings.
2. **Viewpoint Normalization**: Orthographic or slight 3/4 front-side profile against an untextured solid gray backdrop (`#808080`) avoids perspective foreshortening that distorts 3D generation.
3. **Anatomical Prompt Template**:
   ```
   "{creature_description}, full body shot, neutral standing quadruped pose, legs clearly separated, 
   mouth closed, tail extended straight, symmetric posture, orthographic side profile, 
   neutral studio lighting, solid light gray background, high creature anatomy detail, 
   clean silhouette, 8k concept art"
   ```
4. **Negative Prompting**:
   ```
   "dynamic action pose, running, jumping, perspective distortion, overlapping legs, 
   occluded limbs, weapons, saddle, harness, background scenery, shadows on floor, text, watermark"
   ```
5. **Alpha Masking**: The output 2D image is processed through background segmentation (Rembg/BiRefNet) producing a 32-bit RGBA PNG with a pure transparent background.

### 5.2 Stage 2: Single-Image to 3D Generation
1. The isolated RGBA image is passed to the 3D generator (TRELLIS.2 / Hunyuan3D-2).
2. The network predicts continuous geometric representations (structured 3D latents or multi-resolution triplanes).
3. Iso-surface extraction (Marching Cubes or differentiable FlexiCubes) extracts a high-density polygon mesh (100,000 to 500,000 raw triangles).
4. PBR texture synthesis generates:
   - **Albedo / Base Color Map**: Diffuse surface pigmentation without baked lighting.
   - **Normal Map**: Tangent-space details capturing micro-scales, wrinkles, fur direction.
   - **Roughness Map**: Specular response (wet snout, glossy horns, matte fur).
   - **Metallic Map**: Metallic reflectivity for armored plates or chitinous surfaces.
5. The raw asset is exported to binary glTF format (`.glb`).

### 5.3 Stage 3: Topology Optimization (Retopology)
Raw generative meshes cannot be animated cleanly due to irregular triangle distributions and non-manifold artifacts.
1. **Mesh Cleanup**:
   - Elimination of loose vertices, zero-area faces, and non-manifold edges.
   - Closing internal holes via planar hole filling.
2. **Quad-Dominant Retopology**:
   - **Cloud SOTA**: MeshAnything V2 transforms the irregular geometry into an artist-quality quad mesh with natural edge flow along muscular contours.
   - **Local SOTA (macOS Apple Silicon)**: Blender's built-in `bpy.ops.object.quadriflow_remesh(target_faces=target_poly, use_mesh_symmetry=True, use_preserve_boundary=True)`.
3. **Polycount Budgets**:
   - Mobile / Web 3D: 2,500 – 5,000 quads.
   - Real-Time Indie Game: 8,000 – 15,000 quads.
   - Cinematic / High-Detail Rig: 25,000 – 50,000 quads.
4. **UV Unwrapping & Normal Map Re-Baking**:
   - Blender's Angle-Based Flattening (ABF) or Smart UV Project creates non-overlapping UV islands with minimal seam visibility.
   - Surface details from the 200k triangle raw mesh are baked onto a tangent-space 2048x2048 Normal Map fitted to the new low-poly quad mesh.

### 5.4 Stage 4: Skeleton & Rigging Automation
MorphoMesh categorizes creatures into anatomical rig archetypes:

```
                          +-------------------+
                          | Creature Archetype |
                          +---------+---------+
                                    |
         +-----------------+--------+--------+-----------------+
         |                 |                 |                 |
         v                 v                 v                 v
   [ Quadruped ]      [  Biped  ]       [  Winged ]       [  Serpent ]
   - Root / Pelvis    - Root / Hips     - Quad Body       - Spine Chain
   - Spine (3-4)      - Spine & Chest   - Wing Shoulder   - 10-20 Joints
   - 4x Limbs (3 jts) - 2x Arms, 2x Legs- Wing Elbow      - Head & Jaw
   - Neck & Head      - Neck & Head     - Wing Digits     - Spline IK
   - Segmented Tail   - (Humanoid / Dino)- Hind Legs
```

1. **Morphological Landmark Fitting**:
   - Computes principal axes and bounding volume of the creature mesh.
   - Evaluates cross-sectional slices along the longitudinal axis to detect:
     * Spine path (centroid of vertical slices).
     * Head & jaw protrusion (anterior-most cluster).
     * Tail termination (posterior-most tip).
     * Limb attachment points (lateral low-hanging volume clusters).
2. **Armature Instantiation**:
   - The corresponding anatomical armature template is spawned and its bone joints are fitted to the detected landmark positions.
   - Symmetrical bones (limbs, wings) are constrained with `.L` and `.R` naming conventions for Blender mirror editing.
3. **Skin Weight Binding**:
   - Executes Blender's Automatic Heat Bone Weighting (`bpy.ops.object.parent_set(type='ARMATURE_AUTO')`).
   - **Fallback Algorithm**: If heat diffusion fails (which can occur with complex thin horns or spikes), the bridge falls back to harmonic distance weighting or voxel skinning, ensuring 100% skinning success without human intervention.

### 5.5 Stage 5: Blender Scene Assembly
1. **Hierarchy & Collections**:
   - Assets are grouped in a clean Blender collection named `MorphoMesh_Collection`.
   - Clear naming conventions: `Creature_Mesh`, `Creature_Armature`, `MorphoMesh_Studio_Light`, `MorphoMesh_Preview_Camera`.
2. **Material Node Setup**:
   - Creates a standard Principled BSDF 2.0 material.
   - Plugs BaseColor texture into `Base Color`.
   - Plugs Normal Map texture into a `Normal Map` node (Tangent Space, Non-Color) and wires to `Normal`.
   - Plugs Roughness and Metallic textures into their respective shader inputs.
3. **Studio Lighting**:
   - Spawns a 3-point studio lighting rig:
     * Key Light: Warm Area light (45 degrees front-left, 300W).
     * Fill Light: Cool Area light (45 degrees front-right, 100W).
     * Rim / Back Light: Strong Sun or Spot light from behind to delineate the creature's silhouette.
4. **Camera Framing & Viewport Render**:
   - Aligns the preview camera using bounding sphere math to frame the entire creature with a 15% aesthetic margin.
   - Executes `bpy.ops.render.render(write_still=True)` using the Metal-accelerated EEVEE-Next engine.
   - Returns a 1024x1024 preview PNG to the Antigravity agent.

---

## 6. Blender Addon Structure (`blender_addon/`) & Packaging

### 6.1 Directory Hierarchy
The Blender addon is structured cleanly under `blender_addon/morphomesh/`:

```
blender_addon/
├── package_addon.py                # Standalone packaging script -> creates morphomesh_addon.zip
└── morphomesh/
    ├── __init__.py                 # bl_info metadata, registration, timer lifecycle
    ├── server_listener.py          # Threaded TCP socket server & queue consumer
    ├── operators.py                # Blender operators (Start/Stop Bridge, Manual Actions)
    ├── panels.py                   # 3D Viewport N-Panel UI (Status, Port, Quick Tools)
    ├── mesh_builder.py             # Mesh import, cleanup, QuadriFlow, UVs, Materials
    ├── rig_builder.py              # Bone templates, landmark fitting, auto-weights
    └── preferences.py              # User preferences (Port: 9876, Host: 127.0.0.1, Debug)
```

### 6.2 Addon Lifecycle & Registration
In `__init__.py`:
- Declares standard `bl_info` dictionary:
  ```python
  bl_info = {
      "name": "MorphoMesh Bridge",
      "author": "MorphoMesh Team",
      "version": (1, 0, 0),
      "blender": (4, 2, 0),
      "location": "View3D > Sidebar > MorphoMesh",
      "description": "Bi-directional MCP socket bridge for automated 3D creature generation",
      "category": "3D View",
  }
  ```
- `register()`:
  * Registers custom classes (operators, panels, preferences).
  * Automatically starts the background listener on `localhost:9876`.
  * Registers `process_queue_timer` in `bpy.app.timers`.
- `unregister()`:
  * Gracefully closes all active client sockets and stops the listener thread.
  * Unregisters `bpy.app.timers`.
  * Unregisters all UI panels and operators.

### 6.3 3D Viewport Sidebar Panel (`panels.py`)
Provides real-time visibility and manual controls for 3D artists in Blender:
- **Connection Status Widget**: Green / Red badge showing socket status (`LISTENING: 127.0.0.1:9876`, `CONNECTED`, `IDLE`).
- **Bridge Controls**: "Start Bridge", "Stop Bridge", "Restart".
- **Scene Metrics**: Active object name, quad/tri count, armature status.
- **Quick Action Triggers**: "Remesh Active (QuadriFlow)", "Generate Rig", "Render Preview".

### 6.4 Automated Addon Packaging Script (`package_addon.py`)
A self-contained Python packaging script that packages the `blender_addon/morphomesh` folder into a distributable `morphomesh_addon.zip` for 1-click installation via Blender's `Edit > Preferences > Add-ons > Install...`:

```python
#!/usr/bin/env python3
import os
import zipfile
from pathlib import Path

def package_addon(output_zip="morphomesh_addon.zip"):
    addon_dir = Path(__file__).parent / "morphomesh"
    output_path = Path(__file__).parent / output_zip
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(addon_dir):
            for file in files:
                if file.endswith(".py"):
                    full_path = Path(root) / file
                    rel_path = full_path.relative_to(addon_dir.parent)
                    zipf.write(full_path, rel_path)
    print(f"Packaged addon to: {output_path}")

if __name__ == "__main__":
    package_addon()
```

---

## 7. Implementation Blueprint for R4 (Runnable PoC & Blender Bridge)

### 7.1 Source Tree Layout (`src/morphomesh/` & `tests/`)
```
MorphoMesh/
├── docs/
│   ├── RESEARCH_BENCHMARK.md       # R1 Research Matrix
│   ├── ARCHITECTURE.md             # R2 System Architecture
│   ├── MCP_SPECIFICATION.md        # R3 MCP Tool Schemas
│   └── ROADMAP.md                  # Development Roadmap
├── src/
│   └── morphomesh/
│       ├── __init__.py
│       ├── server.py               # FastMCP Server entry point & tool registration
│       ├── config.py               # Settings, environment variables, defaults
│       ├── blender_bridge.py       # Dual-mode TCP socket & headless CLI client
│       ├── security_validator.py   # AST static code analysis & whitelist enforcement
│       ├── inference_adapter.py    # Plug-and-play adapter (Mock, Replicate, HF, Custom)
│       └── procedural_mesh.py      # Deterministic 3D mesh & texture generator for Mock
├── blender_addon/
│   ├── package_addon.py
│   └── morphomesh/
│       ├── __init__.py
│       ├── server_listener.py
│       ├── operators.py
│       ├── panels.py
│       ├── mesh_builder.py
│       ├── rig_builder.py
│       └── preferences.py
├── tests/
│   ├── conftest.py                 # Pytest fixtures, mock servers, tmp directories
│   ├── test_mcp_tools.py           # Verification of all MCP tool schemas & handlers
│   ├── test_blender_bridge.py      # Socket serialization, headless fallback, IPC logic
│   ├── test_security_validator.py  # AST parser attack vector penetration tests
│   ├── test_inference_adapter.py   # Mock generation, GLB synthesis, texture creation
│   └── test_e2e_pipeline.py        # End-to-end integration test (Mock -> Bridge -> Assertions)
├── README.md                       # Overview & quickstart
└── SETUP_GUIDE.md                  # Detailed environment setup & Blender addon guide
```

### 7.2 Testing Strategy (`pytest` Matrix)
1. **Schema & Tool Registration Tests (`test_mcp_tools.py`)**:
   - Verifies that all 7 MCP tools (`morphomesh_generate_concept`, `morphomesh_create_3d_asset`, `morphomesh_optimize_topology`, `morphomesh_auto_rig`, `morphomesh_blender_execute`, `morphomesh_get_scene_status`, `morphomesh_render_preview`) load into FastMCP without syntax or typing errors.
2. **Inference Adapter Tests (`test_inference_adapter.py`)**:
   - Verifies `MockInferenceAdapter` generates valid GLB meshes with non-zero vertex counts and procedural PNG textures.
   - Tests factory instantiator with mock, invalid, and parameterized configs.
3. **Security Validator Tests (`test_security_validator.py`)**:
   - Tests positive cases (valid `bpy.ops.mesh.primitive_cube_add()`, `mathutils.Vector`).
   - Tests negative attack cases (`import os; os.system()`, `subprocess.Popen()`, `eval()`, `__import__('socket')`, dunder traversal `__subclasses__`). All must raise `SecurityException`.
4. **Blender Bridge Tests (`test_blender_bridge.py`)**:
   - Verifies JSON-RPC 2.0 request formatting and response parsing.
   - Tests socket timeout handling and automatic fallback to headless CLI.
   - Uses real `/Applications/Blender.app` headless invocation to verify script execution on macOS.
5. **E2E Pipeline Integration Test (`test_e2e_pipeline.py`)**:
   - Runs full sequence: Mock Concept -> Mock 3D GLB -> Headless Blender Import -> QuadriFlow Remesh -> Auto Rig -> Scene Assembly.
   - Verifies exit code 0 and non-empty result payload.

---

## 8. Architectural Recommendations & Synthesis

1. **Adopt Dual-Mode Bridge as Core Architecture**:
   Never rely solely on an open Blender UI session. By coupling a localhost TCP socket with an automated headless CLI fallback (`blender -b -P`), MorphoMesh guarantees zero-friction automated testing in CI while preserving the real-time visual workflow for creative artists.
2. **Deterministic Mock Backend as First-Class Citizen**:
   The `MockInferenceAdapter` should be the default mode out-of-the-box (`MORPHOMESH_BACKEND=mock`). This ensures any developer or reviewer can clone the repository, run `pytest`, and see 100% passing tests immediately on macOS without needing cloud credentials or expensive GPU hardware.
3. **Native Blender QuadriFlow for Stage 3 Local Fallback**:
   Because Blender 5.2.1 LTS on macOS natively exposes `bpy.ops.object.quadriflow_remesh`, MorphoMesh can perform genuine, high-quality quad retopology entirely on local Apple Silicon hardware without requiring any external C++ binaries or third-party proprietary software.
4. **Rigid AST Sandbox for Custom Execution**:
   Enforce AST parsing on both the MCP server client side and the Blender addon server side to ensure defense-in-depth against malicious prompt injection or accidental destructive commands.

---
*End of Report — Architecture Survey Complete.*
