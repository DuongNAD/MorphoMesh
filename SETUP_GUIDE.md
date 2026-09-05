# MorphoMesh: Comprehensive Setup & Configuration Guide

**Document ID**: `MM-OPS-GUIDE-001`  
**Target Environments**: macOS Apple Silicon (Darwin ARM64), Blender 5.2.1 LTS, Google Antigravity 2.0, Linux x86_64  
**Date**: September 2026  

---

## 1. System Requirements & Hardware Prerequisites

MorphoMesh is engineered for high-throughput hybrid execution across local Apple Silicon workstations and remote cloud GPU endpoints.

| Component | Minimum Specification | Recommended Specification |
|---|---|---|
| **Operating System** | macOS 13.0+ (Ventura / Sonoma / Sequoia) or Linux Ubuntu 22.04+ | macOS 14.5+ or Linux Ubuntu 24.04 LTS |
| **CPU / Architecture** | Apple Silicon M1 (ARM64) or 8-core x86_64 | Apple Silicon M2/M3/M4 Pro or Max (Unified Memory) |
| **RAM / Unified Memory** | 16 GB Unified Memory | 32 GB – 64 GB Unified Memory |
| **Blender Version** | Blender 5.2.1 LTS | Blender 5.2.1 LTS (macOS Metal Hardware Raytracing) |
| **Python Runtime** | Python 3.11.0 – 3.12.x | Python 3.11.8+ |
| **Disk Storage** | 5 GB free SSD storage | 20 GB NVMe SSD for caching high-poly meshes and PBR maps |

---

## 2. Python Environment & Package Installation

### 2.1 Clone the Repository
```bash
cd /Users/duongnad/Documents/tool/MorphoMesh
```

### 2.2 Create & Activate Python 3.11+ Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip setuptools wheel
```

### 2.3 Install MorphoMesh in Editable Mode
```bash
pip install -e .
```

Verify installed package dependencies:
```bash
python3 -c "import morphomesh, mcp, pydantic, PIL, numpy; print('MorphoMesh v' + morphomesh.__version__ + ' ready!')"
# Expected output: MorphoMesh v0.1.0 ready!
```

---

## 3. Blender 5.2.1 LTS Configuration & Addon Installation

MorphoMesh interacts with Blender 5.2.1 LTS via a dual-mode communication bridge:
- **Interactive Mode**: Real-time bidirectional socket communication on `127.0.0.1:9876` using the MorphoMesh Addon.
- **Headless Mode**: Autonomous background subprocess execution (`blender --background --factory-startup --python <script>`).

### 3.1 Blender Binary Location
MorphoMesh automatically resolves the Blender executable in the following order:
1. `BLENDER_BIN_PATH` or `BLENDER_PATH` environment variables.
2. `/Applications/Blender.app/Contents/MacOS/Blender` (Standard macOS installation).
3. `blender` in system `$PATH` (Standard Linux installation).

To explicitly set a custom Blender path in your shell profile:
```bash
export BLENDER_PATH="/Applications/Blender.app/Contents/MacOS/Blender"
```

Verify that Blender executes from the command line:
```bash
$BLENDER_PATH --version
# Expected output: Blender 5.2.1 LTS
```

### 3.2 Enable Apple Metal GPU Acceleration in Blender
1. Launch **Blender 5.2.1 LTS**.
2. Navigate to **Edit > Preferences > System**.
3. Under **Cycles Render Devices**, select **Metal**.
4. Check the box for your Apple Silicon GPU (e.g., `Apple M3 Max`).
5. In **Viewport Render Engine**, confirm **EEVEE** (EEVEE Next in 5.2.1) is enabled.

### 3.3 Package & Install the MorphoMesh Addon
Build the distribution archive:
```bash
morphomesh package-addon
# Outputs: blender_addon/morphomesh_addon.zip
```

Install the addon inside Blender:
1. Open **Blender 5.2.1 LTS**.
2. Go to **Edit > Preferences > Add-ons**.
3. Click the downward arrow in the top right and choose **Install from Disk...**.
4. Select `/Users/duongnad/Documents/tool/MorphoMesh/blender_addon/morphomesh_addon.zip`.
5. Enable the checkbox for **MorphoMesh Bridge**.

### 3.4 Start the Interactive Socket Server
1. In the 3D Viewport, press **N** to open the Sidebar.
2. Click the **MorphoMesh** tab.
3. Click **Start Server** (default port: `9876`).
4. The status indicator will turn green: `Running (Port 9876)`.

---

## 4. Google Antigravity 2.0 Integration

To connect Google Antigravity 2.0 agents to MorphoMesh, register the MCP server in your workspace configuration file (`mcp_config.json`):

```json
{
  "mcpServers": {
    "morphomesh": {
      "command": "/Users/duongnad/Documents/tool/MorphoMesh/.venv/bin/morphomesh",
      "args": ["server", "--transport", "stdio"],
      "cwd": "/Users/duongnad/Documents/tool/MorphoMesh",
      "env": {
        "MORPHOMESH_BACKEND": "mock",
        "BLENDER_PATH": "/Applications/Blender.app/Contents/MacOS/Blender",
        "MORPHOMESH_STORAGE_DIR": "/Users/duongnad/Documents/tool/MorphoMesh/.cache"
      }
    }
  }
}
```

---

## 5. Remote GPU Inference Configuration (Optional Production Modes)

For production deployment utilizing high-density 3D diffusion models (Microsoft TRELLIS.2 4B or Tencent Hunyuan3D-2.1), configure remote cloud inference credentials:

### 5.1 Replicate API Backend
```bash
export MORPHOMESH_BACKEND="replicate"
export REPLICATE_API_TOKEN="r8_********************************"
```

### 5.2 Hugging Face Serverless / Dedicated Endpoints
```bash
export MORPHOMESH_BACKEND="huggingface"
export HF_TOKEN="hf_********************************"
```

### 5.3 Dedicated Linux GPU Server (TRELLIS.2 4B / MeshAnything V2)
If hosting an on-premise Linux workstation with NVIDIA RTX 4090 / A100:
```bash
export MORPHOMESH_BACKEND="custom_remote"
export MORPHOMESH_REMOTE_ENDPOINT="https://gpu-node.internal:8000"
```

*Note: MorphoMesh includes automated Circuit Breaker protection. If remote API calls fail or exceed timeouts, requests automatically fall back to the local Mock adapter without crashing agent workflows.*

---

## 6. Verification Checklist & Health Checks

Execute the following commands to confirm that all layers of the MorphoMesh architecture are functioning:

### Test 1: Probe Bridge Connectivity
```bash
morphomesh ping
```
*Expected Output:*
```
Interactive TCP Socket (127.0.0.1:9876): CONNECTED
Blender Binary Detected: /Applications/Blender.app/Contents/MacOS/Blender
Ping probe response: {'status': 'pong', 'blender_version': '5.2.1', 'mode': 'headless'}
```

### Test 2: Inspect Blender Scene Graph
```bash
morphomesh status
```
*Expected Output:*
```
Scene: Scene
Blender Version: 5.2.1
Objects (3):
 - Cube (MESH): 8 verts, 6 faces
 - Light (LIGHT): 0 verts, 0 faces
 - Camera (CAMERA): 0 verts, 0 faces
```

### Test 3: Execute End-to-End Offline 5-Stage Pipeline
```bash
python3 -c "
import asyncio
from morphomesh.server import (
    morphomesh_generate_concept,
    morphomesh_create_3d_asset,
    morphomesh_optimize_topology,
    morphomesh_auto_rig,
    morphomesh_blender_execute,
    morphomesh_get_scene_status,
    morphomesh_render_preview
)

async def test_pipeline():
    print('[1/7] Concept generation...')
    c = await morphomesh_generate_concept('Saber-toothed snow feline', creature_type='quadruped')
    print('      Concept generated:', c['concept_id'])

    print('[2/7] 3D mesh synthesis & PBR baking...')
    a = await morphomesh_create_3d_asset(concept_id=c['concept_id'])
    print('      Mesh generated:', a['asset_id'], 'Vertices:', a['vertex_count'])

    print('[3/7] QuadriFlow topology retopology...')
    o = await morphomesh_optimize_topology(input_mesh_path=a['mesh_path'], target_poly_count=4000)
    print('      Retopologized faces:', o['optimized_face_count'], 'Quads:', o['quad_percentage'], '%')

    print('[4/7] Procedural auto-rigging...')
    r = await morphomesh_auto_rig(input_mesh_path=o['output_mesh_path'], creature_type='quadruped')
    print('      Rigged armature:', r['armature_name'], 'Bones:', r['bone_count'])

    print('[5/7] Safe sandboxed script execution...')
    e = await morphomesh_blender_execute('import math\nres = math.factorial(5)', return_variables=['res'])
    print('      Script result:', e['returned_data'])

    print('[6/7] Scene graph state inspection...')
    s = await morphomesh_get_scene_status()
    print('      Objects in scene:', s['object_count'])

    print('[7/7] Multi-angle EEVEE render preview...')
    p = await morphomesh_render_preview(resolution_width=512, resolution_height=512)
    print('      Preview rendered at:', p['image_path'])

    print('\nCONFORMANCE PASS: All 7 MorphoMesh tools operating normally.')

asyncio.run(test_pipeline())
"
```

---

## 7. Troubleshooting & FAQ

### Q1: `ERR_BLENDER_UNAVAILABLE` - Blender binary not found
**Solution**: Define the `BLENDER_PATH` environment variable pointing to your Blender executable:
```bash
export BLENDER_PATH="/Applications/Blender.app/Contents/MacOS/Blender"
```

### Q2: Port 9876 is already bound by another process
**Solution**: MorphoMesh connects to any active server on port 9876 (including the standard Blender MCP addon). If you need to rebind to another port:
```bash
export BLENDER_PORT=9877
morphomesh server --port 8765
```

### Q3: `[ERR_SCRIPT_SECURITY_VIOLATION] Forbidden module import: 'os'`
**Explanation**: MorphoMesh enforces strict AST static analysis on all scripts passed to `morphomesh_blender_execute`. Imports of `os`, `sys`, `subprocess`, `shutil`, `socket`, and calls to `eval()`, `exec()`, or `open()` are strictly rejected by design. Use Blender's native API (`bpy`, `mathutils`, `bmesh`) to perform digital content creation tasks.

---

*MorphoMesh Configuration Standard `MM-OPS-GUIDE-001` — Core Architecture Team.*
