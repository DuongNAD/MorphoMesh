# MorphoMesh: Developer & Extension Guide

**Document ID**: `MM-DEV-GUIDE-001`  
**Target Environment**: Python 3.10+ (Recommended 3.11+), FastMCP (`mcp` >= 1.28.1), Blender 4.x / 5.x LTS, `uv`  
**Repository Path**: `docs/DEVELOPER_GUIDE.md`  

---

## Table of Contents
1. [Environment Setup & Toolchain](#1-environment-setup--toolchain)
   - [1.1 Prerequisites](#11-prerequisites)
   - [1.2 Virtual Environment with `uv`](#12-virtual-environment-with-uv)
   - [1.3 Blender 4.x / 5.x Configuration](#13-blender-4x--5x-configuration)
   - [1.4 Verification Smoke Test](#14-verification-smoke-test)
2. [Architecture Map & Subsystem Decomposition](#2-architecture-map--subsystem-decomposition)
   - [2.1 Subsystem Boundaries & Responsibilities](#21-subsystem-boundaries--responsibilities)
   - [2.2 Facade Backward Compatibility Strategy](#22-facade-backward-compatibility-strategy)
   - [2.3 Data Flow & Component Interaction](#23-data-flow--component-interaction)
3. [5 Concrete Extension Recipes](#3-5-concrete-extension-recipes)
   - [Recipe 1: Adding a New FastMCP Tool](#recipe-1-adding-a-new-fastmcp-tool)
   - [Recipe 2: Adding a Pluggable Inference Backend](#recipe-2-adding-a-pluggable-inference-backend)
   - [Recipe 3: Adding a New Creature Limb Topology](#recipe-3-adding-a-new-creature-limb-topology)
   - [Recipe 4: Adding a New Wardrobe Garment](#recipe-4-adding-a-new-wardrobe-garment)
   - [Recipe 5: Adding a Custom Visual Critique Rule](#recipe-5-adding-a-custom-visual-critique-rule)
4. [Testing & Quality Assurance Guide](#4-testing--quality-assurance-guide)
   - [4.1 Test Hierarchy & Pytest Markers](#41-test-hierarchy--pytest-markers)
   - [4.2 Running Unit & Integration Tests](#42-running-unit--integration-tests)
   - [4.3 Mock Mode vs. Live Blender Verification](#43-mock-mode-vs-live-blender-verification)
   - [4.4 Running Adversarial & Fuzzing Suites](#44-running-adversarial--fuzzing-suites)
   - [4.5 AST Security Validator Testing](#45-ast-security-validator-testing)
5. [Security Architecture & Safe Script Execution](#5-security-architecture--safe-script-execution)
   - [5.1 Two-Tier AST Validation (`BpyCodeValidator`)](#51-two-tier-ast-validation-bpycodevalidator)
   - [5.2 Forbidden AST Nodes, Imports, and Builtins](#52-forbidden-ast-nodes-imports-and-builtins)
   - [5.3 Socket Bridge Isolation & Localhost Binding](#53-socket-bridge-isolation--localhost-binding)
   - [5.4 Execution Boundaries & Timeouts](#54-execution-boundaries--timeouts)

---

## 1. Environment Setup & Toolchain

### 1.1 Prerequisites
- **Python**: Version 3.10 or later (Python 3.11+ strongly recommended).
- **Package & Project Manager**: [`uv`](https://github.com/astral-sh/uv) is the standard package manager for MorphoMesh, offering 10-100x faster environment resolution and reproducible locking.
- **Blender**: Blender 4.2 LTS, 4.3+, or 5.2.1 LTS.
- **Operating Systems**: macOS (Apple Silicon M1/M2/M3/M4 with Metal acceleration), Linux (Ubuntu 22.04+ with CUDA 12.x), or Windows 10/11 x86_64.

### 1.2 Virtual Environment with `uv`

Clone the repository and initialize the isolated virtual environment:

```bash
# Clone the repository
git clone https://github.com/DuongNAD/MorphoMesh.git
cd MorphoMesh

# Create virtual environment with Python 3.11
uv venv .venv --python 3.11

# Activate virtual environment
# On macOS / Linux:
source .venv/bin/activate
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1

# Install MorphoMesh in editable development mode with all dependencies
uv pip install -e ".[dev]"
```

Alternatively, you can run any command directly through `uv run` without manually activating the virtual environment:

```bash
uv run python -c "import morphomesh; print(morphomesh.__version__)"
```

### 1.3 Blender 4.x / 5.x Configuration

MorphoMesh bridges with Blender in two distinct modes:
1. **Interactive Socket Bridge**: Blender runs with the `blender_addon/morphomesh` addon enabled, listening on localhost TCP `127.0.0.1:9876`.
2. **Headless CLI Runner**: MorphoMesh spawns `blender -b -P <script>` subprocesses for headless batch rendering, baking, and procedural generation.

To configure Blender for headless execution:

```bash
# Verify Blender is accessible from your shell
blender --version

# If Blender is not on your PATH, set the BLENDER_EXECUTABLE environment variable:
# On macOS:
export BLENDER_EXECUTABLE="/Applications/Blender.app/Contents/MacOS/Blender"

# On Linux:
export BLENDER_EXECUTABLE="/usr/local/bin/blender"

# On Windows (PowerShell):
$env:BLENDER_EXECUTABLE = "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"
```

To configure the interactive Blender addon:
1. Open Blender.
2. Go to **Edit > Preferences > Add-ons**.
3. Click **Install from Disk...** and select the folder `blender_addon/morphomesh` or symlink it into your Blender addons directory:
   ```bash
   # macOS example
   ln -s "$(pwd)/blender_addon/morphomesh" ~/Library/Application\ Support/Blender/4.2/scripts/addons/morphomesh
   ```
4. Enable the **MorphoMesh Bridge** addon.
5. Verify in the Blender System Console that the TCP listener is active on `127.0.0.1:9876`.

### 1.4 Verification Smoke Test

Run this one-line smoke test to verify package integrity and FastMCP server instantiation:

```bash
uv run python -c "import morphomesh; from morphomesh.server import mcp; print(f'MorphoMesh v{morphomesh.__version__} initialized with {mcp.name}')"
```

Expected output:
```text
MorphoMesh v0.1.0 initialized with MorphoMeshServer
```

---

## 2. Architecture Map & Subsystem Decomposition

### 2.1 Subsystem Boundaries & Responsibilities

MorphoMesh is engineered into 11 decoupled, cohesive sub-packages located under `src/morphomesh/`:

```
src/morphomesh/
├── models/             # Domain Pydantic v2 schemas, enumerations, error codes
│   ├── base.py         # BaseRequest, BaseResponse, MeshMetadata
│   ├── creature.py     # Creature generation, rigging, topology schemas
│   ├── human.py        # Digital human base molds, dress, hair schemas
│   ├── inspection.py   # Inspector camera rig and viewport schemas
│   ├── critique.py     # Visual quality defect classification models
│   ├── animation.py    # Creature and character animation schemas
│   ├── enums.py        # Pipeline enumerations (CreatureType, Pose, ViewMode)
│   └── errors.py       # Standardized error codes and exception classes
├── geometry/           # High-performance in-memory mesh & format exporters
│   ├── mesh.py         # MeshGeometry core class (vertices, faces, UVs, normals)
│   ├── exporters.py    # Pure-Python glTF 2.0 Binary (.glb) and Wavefront (.obj)
│   ├── primitives.py   # Procedural cylinders, cubes, spheres, tubes
│   └── quad_utils.py   # Quad topology validation and face splitting
├── inference/          # Generative backends & external connectors
│   ├── base.py         # BaseInferenceAdapter, CircuitBreaker, telemetry models
│   ├── mock.py         # Zero-VRAM deterministic procedural generator
│   ├── replicate.py    # Remote Replicate API client
│   ├── huggingface.py  # Hugging Face Inference Endpoints client
│   └── factory.py      # Pluggable adapter instantiation factory
├── bridge/             # Blender communication & security sandboxing
│   ├── client.py       # Non-blocking TCP client with NDJSON streaming
│   ├── headless.py     # Headless CLI subprocess runner with sentinel parser
│   ├── validator.py    # AST BpyCodeValidator static security analyzer
│   ├── constants.py    # Protocol ports, timeouts, JSON-RPC command constants
│   └── scripts/        # Modular domain bpy script templates
├── tools/              # FastMCP tool declarations & environment gating
│   ├── creature.py     # 7 creature generation & scene tools
│   ├── human.py        # 7 digital human generation & assembly tools
│   ├── inspection.py   # 3 inspection camera & visual critic tools
│   ├── animation.py    # 2 animation dispatch & query tools
│   ├── gating.py       # Dual-layer environment gating matrix
│   ├── registry.py     # Central tool registration orchestrator
│   └── server_instance.py # FastMCP server factory & singleton
├── human/              # Anatomical human body generation & molds
│   ├── mold_loader.py  # MakeHuman CC0 base mold loader and cache
│   ├── morphology.py   # Anatomical morphology deformations (bust, hips)
│   ├── anatomy.py      # Anthropometric landmark detection & feature lines
│   └── scripts.py      # Blender script generators for base mold import
├── rigging/            # Armatures, skin weights & blendshapes
│   ├── metarig.py      # 163 DEF bone Rigify Human Metarig generation
│   ├── anti_pinch.py   # Volume preservation weights for joints
│   ├── blendshapes.py  # 52 ARKit FACS morph targets delta calculation
│   └── scripts.py      # Armature binding and weight transfer scripts
├── wardrobe/           # Dynamic clothing, footwear & props
│   ├── garments.py     # Parametric sundress, bodice, sash, strappy sandals
│   ├── props.py        # Marionette red threads and glowing butterflies
│   ├── skinning.py     # Geodesic pin weights and cloth collision setup
│   └── scripts.py      # Cloth simulation modifier setup scripts
├── grooming/           # Volumetric hair curves & fur systems
│   ├── hime_cut.py     # Spline math for straight bangs and hime sidelocks
│   ├── ribbons.py      # Hair ribbon geometries and accessory mounts
│   ├── curves_pipeline.py # Geometry Nodes Curves hair groom trees
│   └── creature.py     # Multi-layer quadruped fur grooming (undercoat/guard)
├── assembler/          # Master character assembly & packaging
│   ├── assembler.py    # Yu Nian An master character scene assembler
│   ├── pbr_baker.py    # 4K PBR procedural texture synthesis (Albedo/Normal/Rough/SSS)
│   ├── scene_builder.py# 3-point studio lighting, camera presets, AgX color
│   └── packager.py     # FBX, GLB, and master .blend binary export pipeline
├── critic/             # Closed-loop automated visual quality critique
│   ├── bvh.py          # PurePythonBVHTree for raycasting & proximity checks
│   ├── geometry_math.py# Möller–Trumbore ray-triangle, Möller triangle-triangle
│   ├── penetration.py  # Cloth-mesh penetration & hair-scalp collision analysis
│   ├── proportions.py  # Anthropometric proportions (head-to-body ratios)
│   ├── deformation.py  # Joint pinch volume loss & acute crease detection
│   └── reporter.py     # Diagnostic defect classification & benchmark runner
└── anatomy/            # Biomechanical locomotion & skeleton estimation
    ├── locomotor.py    # Stance classification (Humanoid, Plantigrade, Digitigrade)
    ├── landmarks.py    # Bony landmark identification & joint centers
    ├── bone_roll.py    # Hinge normal vector & biomechanical roll solver
    └── biharmonic.py   # Geodesic voxel skin weight diffusion solver
```

### 2.2 Facade Backward Compatibility Strategy

To maintain 100% backward compatibility with external scripts, existing tests, and client integrations, every root module that was decomposed into a sub-package is preserved as a **facade module** at `src/morphomesh/<name>.py`:

| Facade Path | Underlying Sub-Package | Re-Export Guarantee |
|---|---|---|
| `src/morphomesh/models.py` | `morphomesh.models.*` | All 62 Pydantic models, 32 error constants, and enums |
| `src/morphomesh/inference_adapter.py` | `morphomesh.inference.*` & `geometry.*` | `InferenceAdapter`, `MeshGeometry`, `CircuitBreaker` |
| `src/morphomesh/blender_bridge.py` | `morphomesh.bridge.*` | `BlenderBridge`, `BpyCodeValidator`, protocol constants |
| `src/morphomesh/server.py` | `morphomesh.tools.*` | `mcp`, `create_mcp_server`, all 19 tool callables |
| `src/morphomesh/human_generator.py` | `morphomesh.human.*` | `generate_female_base_mold`, morphology functions |
| `src/morphomesh/human_rigging.py` | `morphomesh.rigging.*` | `setup_rigify_human_metarig`, blendshape generators |
| `src/morphomesh/wardrobe.py` | `morphomesh.wardrobe.*` | `generate_yu_nian_an_wardrobe`, garment generators |
| `src/morphomesh/human_grooming.py` | `morphomesh.grooming.*` | `generate_hime_cut_hair`, hair curve pipelines |
| `src/morphomesh/character_assembler.py` | `morphomesh.assembler.*` | `CharacterAssembler`, `PBRBaker`, packaging tools |
| `src/morphomesh/visual_critic.py` | `morphomesh.critic.*` | `run_visual_critique`, defect evaluation functions |

Every facade defines an exhaustive `__all__` list and re-exports symbols identically. Developers can import from either `morphomesh.models` (package) or `morphomesh.models.creature` (sub-module).

### 2.3 Data Flow & Component Interaction

```
┌────────────────────────────────────────────────────────┐
│                   Google Antigravity 2.0               │
└──────────────────────────┬─────────────────────────────┘
                           │ JSON-RPC (stdio / SSE)
                           ▼
┌────────────────────────────────────────────────────────┐
│              MorphoMesh FastMCP Server                 │
│  (src/morphomesh/server.py / src/morphomesh/tools/)    │
└──────────────┬──────────────────────────┬──────────────┘
               │                          │
               ▼                          ▼
┌──────────────────────────────┐  ┌──────────────────────────────┐
│       Inference Subsystem    │  │       Bridge Subsystem       │
│ (src/morphomesh/inference/)  │  │   (src/morphomesh/bridge/)   │
│  ├── MockInferenceAdapter    │  │  ├── AST BpyCodeValidator    │
│  ├── ReplicateAdapter        │  │  ├── TCP Client (port 9876)  │
│  └── Connectors (TRELLIS)    │  │  └── Headless CLI Runner     │
└──────────────┬───────────────┘  └──────────────┬───────────────┘
               │                                 │
               ▼                                 ▼
┌──────────────────────────────┐  ┌──────────────────────────────┐
│      Geometry Subsystem      │  │      Blender 4.x / 5.x       │
│  (src/morphomesh/geometry/)  │  │  ├── Bmesh & Rigify Engine   │
│  ├── MeshGeometry            │  │  ├── Hair Curves Pipelines   │
│  └── GLB / OBJ Exporters     │  │  └── EEVEE / Cycles Renders  │
└──────────────────────────────┘  └──────────────────────────────┘
```

---

## 3. 5 Concrete Extension Recipes

### Recipe 1: Adding a New FastMCP Tool

To add a new tool to MorphoMesh, follow this 4-step workflow:
1. Define the input/output schemas in `src/morphomesh/models/`.
2. Implement the tool handler in `src/morphomesh/tools/`.
3. Register the tool in `src/morphomesh/tools/registry.py`.
4. Configure environment gating in `src/morphomesh/tools/gating.py`.

#### Step 1: Define Schemas (`src/morphomesh/models/inspection.py`)
```python
from pydantic import BaseModel, Field
from typing import List, Optional

class MeasureTurntableDistanceInput(BaseModel):
    object_name: str = Field(..., description="Target object identifier in Blender scene.")
    camera_fov: float = Field(default=45.0, description="Vertical field of view in degrees.")
    margin_ratio: float = Field(default=1.2, description="Framing margin multiplier.")

class MeasureTurntableDistanceOutput(BaseModel):
    recommended_distance: float = Field(..., description="Calculated optimal camera distance in meters.")
    bounding_radius: float = Field(..., description="Bounding sphere radius of the target mesh.")
    target_center: List[float] = Field(..., description="Object center of mass [x, y, z].")
```

#### Step 2: Implement Tool Function (`src/morphomesh/tools/inspection.py`)
```python
import math
from mcp.server.fastmcp import Context
from morphomesh.models.inspection import (
    MeasureTurntableDistanceInput,
    MeasureTurntableDistanceOutput,
)
from morphomesh.tools.dependencies import blender_bridge, logger

async def morphomesh_measure_turntable_distance(
    object_name: str,
    camera_fov: float = 45.0,
    margin_ratio: float = 1.2,
    ctx: Optional[Context] = None,
) -> MeasureTurntableDistanceOutput:
    """Calculate the mathematically optimal camera distance to frame a mesh."""
    if ctx:
        await ctx.info(f"Measuring turntable distance for {object_name}...")

    # Query object bounding box via bridge
    scene_status = blender_bridge.get_scene_status()
    # Compute optimal distance based on bounding sphere and FOV
    radius = 1.0  # Derived from scene bounds
    half_fov_rad = math.radians(camera_fov / 2.0)
    optimal_dist = (radius / math.sin(half_fov_rad)) * margin_ratio

    return MeasureTurntableDistanceOutput(
        recommended_distance=round(optimal_dist, 3),
        bounding_radius=round(radius, 3),
        target_center=[0.0, 0.0, 1.0],
    )
```

#### Step 3: Register in Registry (`src/morphomesh/tools/registry.py`)
```python
from morphomesh.tools.inspection import morphomesh_measure_turntable_distance

def register_all_tools(mcp: FastMCP) -> None:
    # Existing registrations...
    mcp.tool(name="morphomesh_measure_turntable_distance")(
        morphomesh_measure_turntable_distance
    )
```

---

### Recipe 2: Adding a Pluggable Inference Backend

To connect a new 3D generative model (e.g., RunPod Serverless or a custom REST microservice), subclass `BaseInferenceAdapter` and register it in the factory.

#### Implementation (`src/morphomesh/inference/runpod.py`)
```python
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from morphomesh.models import (
    Create3DAssetInput,
    Create3DAssetOutput,
    GenerateConceptInput,
    GenerateConceptOutput,
)
from morphomesh.inference.base import BaseInferenceAdapter, CircuitBreaker, EnhancedCreate3DAssetOutput

class RunPodInferenceAdapter(BaseInferenceAdapter):
    """Generative inference adapter connecting to RunPod Serverless GPU endpoints."""

    def __init__(
        self,
        endpoint_id: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 180.0,
    ):
        self.endpoint_id = endpoint_id or os.environ.get("RUNPOD_ENDPOINT_ID", "")
        self.api_key = api_key or os.environ.get("RUNPOD_API_KEY", "")
        self.timeout = timeout
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
        self.base_url = f"https://api.runpod.ai/v2/{self.endpoint_id}"

    def generate_concept(self, request: GenerateConceptInput) -> GenerateConceptOutput:
        """Forward prompt to RunPod FLUX.1 endpoint."""
        if not self.circuit_breaker.can_attempt():
            raise RuntimeError("Circuit breaker is OPEN: RunPod endpoint is temporarily unreachable.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = json.dumps({"input": {"prompt": request.prompt, "aspect_ratio": "1:1"}}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/runsync",
            data=payload,
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            self.circuit_breaker.record_success()
            return GenerateConceptOutput(
                concept_id=data["id"],
                image_path=data["output"]["image_url"],
                prompt_used=request.prompt,
                quality_tier="production",
            )
        except Exception as err:
            self.circuit_breaker.record_failure()
            raise RuntimeError(f"RunPod concept generation failed: {err}") from err

    def generate_3d_asset(self, request: Create3DAssetInput) -> Create3DAssetOutput:
        """Forward 2D image to RunPod TRELLIS / Hunyuan3D endpoint."""
        # Similar implementation with 3D endpoint payload...
        pass
```

#### Register in Factory (`src/morphomesh/inference/factory.py`)
```python
from .runpod import RunPodInferenceAdapter

def get_inference_adapter(mode: str = "mock", **kwargs: Any) -> BaseInferenceAdapter:
    m = mode.lower()
    if m == "runpod":
        return RunPodInferenceAdapter(**kwargs)
    # ... existing fallbacks
```

---

### Recipe 3: Adding a New Creature Limb Topology

To generate novel creature limbs (e.g., an arachnid/arthropod segmented walking leg), define the parametric config and synthesize the vertices and faces in `src/morphomesh/creature_generator.py`:

```python
import math
from typing import List, Tuple
from morphomesh.geometry.mesh import MeshGeometry

def generate_arachnid_leg(
    coxa_length: float = 0.15,
    femur_length: float = 0.40,
    tibia_length: float = 0.50,
    tarsus_length: float = 0.20,
    radius: float = 0.03,
    num_segments: int = 8,
) -> MeshGeometry:
    """
    Procedurally synthesize a 4-segment articulated arachnid leg with chitinous plates.
    Joint segments: Coxa -> Femur -> Tibia -> Tarsus (Claw tip).
    """
    mesh = MeshGeometry()

    joints = [
        (0.0, 0.0, 0.0),                          # Base joint (Body mount)
        (coxa_length, 0.0, 0.05),                 # Coxa-Femur joint
        (coxa_length + 0.2, 0.0, femur_length),   # Knee joint (raised apex)
        (coxa_length + 0.45, 0.0, 0.1),           # Tibia-Tarsus joint
        (coxa_length + 0.60, 0.0, -0.05),         # Ground contact tip
    ]

    # Generate cylindrical sleeves around joint bones with tapering radii
    for idx in range(len(joints) - 1):
        p_start = joints[idx]
        p_end = joints[idx + 1]
        r_start = radius * (1.0 - idx * 0.18)
        r_end = radius * (1.0 - (idx + 1) * 0.18)

        # Build ring vertices around bone vector...
        ring_start_idx = len(mesh.vertices)
        for seg in range(num_segments):
            angle = (2.0 * math.pi * seg) / num_segments
            dx = math.cos(angle) * r_start
            dy = math.sin(angle) * r_start
            mesh.add_vertex((p_start[0] + dx, p_start[1] + dy, p_start[2]))

        for seg in range(num_segments):
            angle = (2.0 * math.pi * seg) / num_segments
            dx = math.cos(angle) * r_end
            dy = math.sin(angle) * r_end
            mesh.add_vertex((p_end[0] + dx, p_end[1] + dy, p_end[2]))

        # Stitch quad faces between start and end rings
        for seg in range(num_segments):
            next_seg = (seg + 1) % num_segments
            v0 = ring_start_idx + seg
            v1 = ring_start_idx + next_seg
            v2 = ring_start_idx + num_segments + next_seg
            v3 = ring_start_idx + num_segments + seg
            mesh.add_quad(v0, v1, v2, v3)

    mesh.add_to_vertex_group("leg_arthropod", list(range(len(mesh.vertices))))
    return mesh
```

---

### Recipe 4: Adding a New Wardrobe Garment

To add a new wearable garment (e.g., a flowing cape/cloak or shoulder shawl), implement the parametric generator in `src/morphomesh/wardrobe/garments.py` and register it in `WardrobeConfig`:

```python
import math
from typing import List, Tuple
from morphomesh.geometry.mesh import MeshGeometry

def generate_flowing_cape(
    neck_radius: float = 0.09,
    cape_length: float = 1.10,
    flare_width: float = 0.75,
    num_folds: int = 12,
    num_rows: int = 24,
) -> MeshGeometry:
    """
    Synthesize an organic draped back cape with gravity folds radiating from the shoulders.
    Clearance: Positioned +12mm dorsal to the spine to prevent mesh penetration.
    """
    mesh = MeshGeometry()

    for r in range(num_rows + 1):
        v_ratio = r / float(num_rows)
        z = 1.45 - (v_ratio * cape_length)  # Starts at neck/clavicle (Z=1.45m)
        width = neck_radius + (v_ratio * flare_width)
        y_depth = -0.12 - (v_ratio * 0.08)  # Drapes behind character (negative Y)

        cols = num_folds * 2
        for c in range(cols + 1):
            u_ratio = c / float(cols)
            x = (u_ratio - 0.5) * 2.0 * width
            # Add sinusoidal gravity cloth folds
            fold_depth = math.sin(u_ratio * num_folds * math.pi) * (0.015 * v_ratio)
            mesh.add_vertex((x, y_depth + fold_depth, z))

    # Connect quad faces
    cols_count = num_folds * 2 + 1
    for r in range(num_rows):
        for c in range(cols_count - 1):
            v0 = r * cols_count + c
            v1 = r * cols_count + c + 1
            v2 = (r + 1) * cols_count + c + 1
            v3 = (r + 1) * cols_count + c
            mesh.add_quad(v0, v1, v2, v3)

    mesh.add_to_vertex_group("cape", list(range(len(mesh.vertices))))
    return mesh
```

---

### Recipe 5: Adding a Custom Visual Critique Rule

To inspect models for a custom geometric or aesthetic defect (e.g., detecting non-manifold manifold holes or boundary edges), add an evaluation function in `src/morphomesh/critic/`:

```python
from typing import Dict, List, Set, Tuple
from morphomesh.models.critique import DefectCategory, DefectItem, DefectSeverity

def evaluate_mesh_manifold_boundaries(
    object_name: str,
    faces: List[List[int]],
    allowed_open_boundaries: bool = False,
) -> List[DefectItem]:
    """
    Detect non-manifold boundary edges (edges shared by exactly 1 face)
    or non-manifold junctions (edges shared by >2 faces).
    """
    edge_counts: Dict[Tuple[int, int], int] = {}

    for face in faces:
        n = len(face)
        for i in range(n):
            v0, v1 = face[i], face[(i + 1) % n]
            edge = (min(v0, v1), max(v0, v1))
            edge_counts[edge] = edge_counts.get(edge, 0) + 1

    defects: List[DefectItem] = []
    open_edges = [edge for edge, count in edge_counts.items() if count == 1]
    junction_edges = [edge for edge, count in edge_counts.items() if count > 2]

    if junction_edges:
        defects.append(
            DefectItem(
                category=DefectCategory.SKINNING_PINCH,
                severity=DefectSeverity.CRITICAL,
                description=f"Mesh {object_name} contains {len(junction_edges)} non-manifold edge junctions shared by >2 faces.",
                affected_objects=[object_name],
                metric_value=float(len(junction_edges)),
                threshold=0.0,
            )
        )

    if open_edges and not allowed_open_boundaries:
        defects.append(
            DefectItem(
                category=DefectCategory.PENETRATION,
                severity=DefectSeverity.MAJOR,
                description=f"Mesh {object_name} contains {len(open_edges)} open boundary holes.",
                affected_objects=[object_name],
                metric_value=float(len(open_edges)),
                threshold=0.0,
            )
        )

    return defects
```

---

## 4. Testing & Quality Assurance Guide

### 4.1 Test Hierarchy & Pytest Markers

MorphoMesh enforces rigorous test discipline across multiple test categories registered in `pyproject.toml`:

```ini
[tool.pytest.ini_options]
markers = [
    "unit: Isolated fast unit tests (<100ms)",
    "integration: End-to-end multi-component tests",
    "live_blender: Tests requiring a running Blender instance on localhost:9876",
    "adversarial: Stress testing, fuzzing, and AST attack injection suites",
]
```

### 4.2 Running Unit & Integration Tests

```bash
# Run all standard offline unit and integration tests:
uv run pytest tests/ -m "not live_blender"

# Run tests with verbose output and failure summary:
uv run pytest tests/ -v --tb=short

# Run tests for a specific subsystem:
uv run pytest tests/test_fastmcp_inspection_tools.py
uv run pytest tests/test_connectors.py
uv run pytest tests/test_anatomy.py
```

### 4.3 Mock Mode vs. Live Blender Verification

MorphoMesh operates completely headless and zero-VRAM in **Mock Mode** for automated CI pipelines:
- In mock mode, procedural meshes are written directly into `.glb` or `.blend` structures without spawning Blender.
- In **Live Mode**, test cases connect to `127.0.0.1:9876` and verify live viewport capture, modifier evaluation, and cycles baking:

```bash
# Terminal 1: Launch Blender with socket listener
blender --python blender_addon/morphomesh/listener.py

# Terminal 2: Execute live Blender tests
uv run pytest tests/ -m "live_blender"
```

### 4.4 Running Adversarial & Fuzzing Suites

Adversarial test suites verify that malicious prompts, malformed JSON-RPC payloads, and boundary-condition deformations fail safely:

```bash
# Run the adversarial character assembler test:
uv run pytest tests/test_adversarial_character_assembler.py

# Run the environment gating fuzzing suite:
uv run pytest tests/test_adversarial_m4_gating.py

# Run the FastMCP stress and schema fuzzing suite:
uv run pytest tests/test_challenger_m2_1_fastmcp_stress.py
```

### 4.5 AST Security Validator Testing

To test the security sandbox against Python exploit payloads (eval injection, socket exfiltration, os.system calls):

```bash
uv run pytest tests/test_blender_bridge.py -k "validator or security"
```

---

## 5. Security Architecture & Safe Script Execution

### 5.1 Two-Tier AST Validation (`BpyCodeValidator`)

Because autonomous LLM agents have access to `morphomesh_blender_execute`, MorphoMesh implements a strict **Two-Tier Abstract Syntax Tree (AST) Security Sandbox** located at `src/morphomesh/bridge/validator.py`.

Before any Python script is submitted to Blender's Python interpreter, it is parsed and analyzed via Python's native `ast.NodeVisitor`:

```
Agent Script (Text) ───► ast.parse() ───► BpyCodeValidator ───► Passes?
                                                 │                 │
                                                 │ (Violations)    ├──► YES ──► Bridge Execution
                                                 ▼                 │
                                          SecurityError ◄──────────┴──► NO  ──► Abort & Report
```

### 5.2 Forbidden AST Nodes, Imports, and Builtins

The validator enforces three layers of static safety checks:

1. **Forbidden AST Node Types**:
   - `ast.Import` / `ast.ImportFrom`: Direct imports are strictly prohibited unless the module is explicitly allowlisted (`math`, `mathutils`, `bpy`, `bmesh`).
   - `ast.Exec` / `ast.Global` / `ast.Nonlocal`: Arbitrary runtime code execution.

2. **Forbidden Modules & Imports**:
   - Prohibited: `os`, `sys`, `subprocess`, `socket`, `http`, `urllib`, `shutil`, `threading`, `multiprocessing`, `ctypes`, `builtins`, `importlib`.

3. **Forbidden Builtin Functions & Attributes**:
   - Prohibited calls: `eval()`, `exec()`, `compile()`, `open()`, `input()`, `getattr()`, `setattr()`, `delattr()`, `globals()`, `locals()`.
   - Prohibited attribute accesses: `__subclasses__`, `__bases__`, `__class__`, `__mro__`, `__globals__`, `__code__`.

Any violation raises `SecurityError` with exact line number, AST node type, and the violating identifier.

### 5.3 Socket Bridge Isolation & Localhost Binding

- **Localhost Only**: The TCP socket bridge binds strictly to `127.0.0.1:9876`. It never binds to `0.0.0.0` or external network interfaces.
- **NDJSON Framing**: Messages are framed as newline-delimited JSON (`\n`), preventing buffer overflow and stream truncation attacks.
- **Main Thread Event Loop**: Inside Blender, incoming commands are placed on a thread-safe queue and executed strictly on Blender's main thread via `bpy.app.timers`, preventing thread-safety crashes and memory corruption in the C/C++ Blender core.

### 5.4 Execution Boundaries & Timeouts

Every bridge command and subprocess execution enforces strict timeout boundaries:
- Socket RPC commands: 30.0-second default timeout (configurable per command).
- Headless Blender subprocesses: 120.0-second process termination timer.
- Unhandled timeouts raise `BridgeTimeoutError` and cleanly release all network and file locks.
