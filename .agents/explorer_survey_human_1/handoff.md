# ARCHITECTURE ANALYSIS & DESIGN REPORT: DIGITAL HUMAN PIPELINE UPGRADE

**Agent**: Explorer 1 (Codebase Architecture Explorer)  
**Date**: 2026-09-06T17:40:00Z  
**Target Milestone**: MorphoMesh Digital Human Engine Upgrade & Dư Niệm An (余念安 - Yu Nian An) 3D Model Synthesis  
**Target Blender Version**: Blender 4.5.4 LTS / Blender 5.2+  
**Target FastMCP Server**: FastMCP (MCP SDK >=1.2.0, <2.0.0)  

---

## 1. OBSERVATION

### 1.1 Existing Architecture & Codebase Layout
Direct inspection of `E:\tool\mcp\MorphoMesh` reveals a dual-mode creature generation architecture:
1. **`src/morphomesh/server.py`**:
   - Initializes FastMCP server: `mcp = FastMCP(name="MorphoMeshServer", ...)` listening on host `127.0.0.1`, port `8765`.
   - Currently exposes 7 MCP tools:
     - `morphomesh_generate_concept`
     - `morphomesh_create_3d_asset`
     - `morphomesh_optimize_topology`
     - `morphomesh_auto_rig`
     - `morphomesh_blender_execute`
     - `morphomesh_get_scene_status`
     - `morphomesh_render_preview`
   - All tools are typed with Pydantic v2 models from `src/morphomesh/models.py`, use async def, accept `ctx: Optional[Context] = None`, and handle `MorphoMeshException` by raising `ToolError`.
2. **`src/morphomesh/blender_bridge.py`**:
   - Implements `BlenderBridge`: dual-mode IPC.
     - **Interactive Mode**: Direct localhost TCP socket to `127.0.0.1:9876` sending JSON-RPC 2.0 requests (`send_socket_request`).
     - **Headless Fallback**: Headless CLI runner `blender --background --factory-startup --python <temp_script>` that captures JSON emitted between `SENTINEL_START` and `SENTINEL_END` tokens.
   - Contains a two-tier AST static security validator (`BpyCodeValidator`) blocking dangerous modules (`os`, `sys`, `subprocess`, `socket`) and reflection attributes (`__subclasses__`, `__globals__`).
   - `_generate_headless_script` embeds parameter JSON and generates complete `bpy` execution logic for each method.
3. **`blender_addon/morphomesh/listener.py`**:
   - Runs `MorphoMeshSocketServer` on `127.0.0.1:9876` inside Blender.
   - Synchronizes command execution onto Blender's main thread via `bpy.app.timers.register(self._drain_queue, persistent=True)` every 20ms.
   - Handles RPC methods: `morphomesh.ping` / `ping`, `morphomesh.get_scene_status` / `get_scene_info`, `morphomesh.execute_custom_script` / `execute_code`.
4. **Active Blender Runtime Environment**:
   - Direct socket ping on `127.0.0.1:9876` confirmed:
     ```json
     {"jsonrpc": "2.0", "id": "test-1", "status": "success", "result": {"status": "pong", "blender_version": "4.5.4", "mode": "interactive"}}
     ```
     **Blender 4.5.4 LTS is currently actively running on Windows with the MorphoMesh Addon listening on port 9876.**
   - Binary location: `C:\Program Files\Blender Foundation\Blender 4.5\blender.exe`.
5. **Existing Creature Engines & Patterns**:
   - `src/morphomesh/creature_generator.py`: Parametric geometry engine with `MeshGeometry` in-memory container, generating quad/tri meshes, 18 standardized vertex groups (`snout`, `limbs`, `torso`, etc.), and claw metrics.
   - `src/morphomesh/grooming.py`: Multi-layer hair grooming engine generating Blender hair particle systems (`Undercoat_Fur`, `Guard_Hairs_Fur`) and polygonal ribbon meshes (`_Fur_Ribbons`) for glTF export.
   - `src/morphomesh/materials.py`: 5-material Principled BSDF v2 suite (`Mat_Bear_Fur`, `Mat_Bear_Skin_Nose`, `Mat_Bear_Claws`, `Mat_Armor_WeatheredSteel`, `Mat_Armor_BrassTrim`).
   - `src/morphomesh/armor.py`: Procedural war armor fitting with BVH radial clearance guarantees ($d_{\min} \ge 0.015\text{m}$).
6. **Reference Sheet `media_1788716034772.jpg`**:
   - Character: Dư Niệm An (余念安 - Yu Nian An), Semi-Realistic / High-End Stylized Photorealism.
   - Proportions: Slender young female, approx 1.65m height, 7.2 head ratio, delicate features.
   - Face: Calm, sorrowful expression; almond eyes with charcoal/violet irises; delicate nose and soft lips; straight forehead bangs with long side-locks framing the cheeks and jawline.
   - Hair: Jet-black, silky, cascading past waist/hips down to lower back.
   - Outfit: Sleeveless white camisole A-line dress with double shoulder straps, high waist sash with double ribbon belt, flared skirt ending mid-calf, flat white slip-on sandals.
   - Key Props: Delicate crimson/red threads wound around fingers in puppeteer gesture; glowing ethereal white butterflies alighting on and fluttering around the fingertips.

---

## 2. LOGIC CHAIN

### 2.1 Engine Architecture Decomposition
The requirements demand upgrading MorphoMesh into an industrial-grade Photorealistic Digital Human Pipeline while generating character Dư Niệm An. The architecture decomposes cleanly into five modular engine components matching the existing creature paradigm:

```
src/morphomesh/
├── human_generator.py    # Anthropometric geometry, 52 ARKit blendshapes, quad topology
├── human_rigging.py      # Rigify Human Metarig (163 DEF bones, 10 fingers, animatable joints)
├── human_materials.py    # Principled BSDF v2 PBR skin (Random Walk SSS), 2-chamber eyes, hair, fabrics
├── human_grooming.py     # Hair Curves & Particle Systems (hime bangs, long hair, brows, lashes)
├── wardrobe.py           # White slip dress, belt, sandals, red threads, glowing butterflies
├── server.py             # Exposes 5 new FastMCP tools alongside the 7 existing tools (12 total)
├── blender_bridge.py     # Windows path resolution & headless/interactive dispatch for human methods
└── models.py             # Pydantic v2 input/output models and error codes
```

### 2.2 Module 1: `src/morphomesh/human_generator.py`
- **Anthropometric Geometry Generation**:
  - Parametric class `HumanAnatomyConfig`:
    - `height`: float = 1.65m
    - `head_ratio`: float = 7.2
    - `shoulder_width`: float = 0.36m
    - `chest_girth`: float = 0.82m
    - `waist_girth`: float = 0.60m
    - `hip_girth`: float = 0.86m
    - `leg_length`: float = 0.88m
    - `arm_span`: float = 1.62m
    - `gender`: str = "female"
    - `style`: str = "stylized_photorealism"
  - Generates quad-dominant body mesh (>95% quads in deforming regions, watertight 2-manifold, correct face normals).
  - Populates 24 standardized human vertex groups:
    `head`, `face`, `eyes_left`, `eyes_right`, `eyelids`, `eyebrows`, `mouth`, `lips`, `teeth`, `tongue`, `neck`, `torso`, `chest`, `waist`, `hips`, `arm_upper_L`, `arm_lower_L`, `hand_L`, `fingers_L`, `arm_upper_R`, `arm_lower_R`, `hand_R`, `fingers_R`, `leg_upper_L`, `leg_lower_L`, `foot_L`, `leg_upper_R`, `leg_lower_R`, `foot_R`.
- **52 ARKit FACS Blendshapes (Shape Keys)**:
  - Generates full Apple ARKit standard shape key offsets:
    `eyeBlinkLeft`, `eyeBlinkRight`, `eyeLookDownLeft`, `eyeLookDownRight`, `eyeLookInLeft`, `eyeLookInRight`, `eyeLookOutLeft`, `eyeLookOutRight`, `eyeLookUpLeft`, `eyeLookUpRight`, `eyeSquintLeft`, `eyeSquintRight`, `eyeWideLeft`, `eyeWideRight`, `browDownLeft`, `browDownRight`, `browInnerUp`, `browOuterUpLeft`, `browOuterUpRight`, `jawForward`, `jawLeft`, `jawRight`, `jawOpen`, `mouthClose`, `mouthFunnel`, `mouthPucker`, `mouthLeft`, `mouthRight`, `mouthSmileLeft`, `mouthSmileRight`, `mouthFrownLeft`, `mouthFrownRight`, `mouthDimpleLeft`, `mouthDimpleRight`, `mouthStretchLeft`, `mouthStretchRight`, `mouthRollLower`, `mouthRollUpper`, `mouthShrugLower`, `mouthShrugUpper`, `mouthPressLeft`, `mouthPressRight`, `mouthLowerDownLeft`, `mouthLowerDownRight`, `mouthUpperUpLeft`, `mouthUpperUpRight`, `cheekPuff`, `cheekSquintLeft`, `cheekSquintRight`, `noseSneerLeft`, `noseSneerRight`, `tongueOut`.
  - In offline mode: Stores delta offsets in `HumanMeshResult.shape_keys`.
  - In Blender mode: Creates shape keys on `mesh.shape_keys` (`Basis` + 52 keys).

### 2.3 Module 2: `src/morphomesh/human_rigging.py`
- **Rigify Human Metarig Integration (163 DEF Bones)**:
  - Uses Blender's native Rigify metarig (`type='human'`) or programmatic hierarchy aligned to Yu Nian An's anthropometric landmarks.
  - Complete bone chains:
    - Root: `root`
    - Spine: `spine`, `spine.001`, `spine.002`, `spine.003`, `neck`, `head`
    - Face: 28 facial bones for lips, jaw, eyes, brows, cheeks
    - Limbs (L/R): `clavicle`, `shoulder`, `upper_arm` (with twist), `forearm` (with twist), `hand`
    - Hands & Fingers: 10 articulated digits, each with 3 phalanges + metacarpal (thumb: 3 bones; index, middle, ring, pinky: 3 bones each) = 15 bones per hand.
    - Pelvis & Legs (L/R): `pelvis`, `thigh` (with twist), `shin` (with twist), `foot`, `toe`
  - Automatic skinning calculation via harmonic automatic weights (`bpy.ops.object.parent_set(type='ARMATURE_AUTO')`).
  - Prepares test actions: `A_Pose`, `T_Pose`, `Puppeteer_Pose` (hands raised, fingers elegantly curled, wrists flexed).

### 2.4 Module 3: `src/morphomesh/human_materials.py`
- **Photorealistic Principled BSDF v2 Suite**:
  - Implements 8 specialized shaders conforming to Blender 4.5+ socket architecture:
    1. `Mat_Human_Skin`:
       - Subsurface Scattering: `subsurface_weight = 0.32`, `subsurface_scale = 0.05`, `subsurface_radius = (1.0, 0.35, 0.15)`.
       - Socket `Subsurface Method`: Set to `'RANDOM_WALK'` (standard in Blender 4.5+).
       - Roughness: `0.45`, Specular IOR: `0.50`, IOR: `1.45`.
       - Micro-pore texture bump via procedural Voronoi/Noise (`scale=450.0, strength=0.06`).
       - Clearcoat moisture on T-zone / lips: `coat_weight = 0.25, coat_roughness = 0.04`.
    2. `Mat_Human_Eye_Cornea`: Outer transparent refractive shell: transmission `1.0`, roughness `0.0`, IOR `1.376`, specular `1.0`.
    3. `Mat_Human_Eye_Iris`: Inner chamber concave disc: dark charcoal/violet-grey `(0.12, 0.11, 0.15, 1.0)`, limbal ring gradient, radial striations.
    4. `Mat_Human_Eye_Sclera`: Sclera white `(0.92, 0.90, 0.88, 1.0)`, subtle red vascular noise bump, SSS weight `0.15`.
    5. `Mat_Human_Lips`: Soft rosy coral `(0.82, 0.42, 0.42, 1.0)`, SSS weight `0.45`, coat weight `0.40`.
    6. `Mat_Dress_White_Silk`: Pure soft white `(0.95, 0.95, 0.96, 1.0)`, sheen weight `0.75`, roughness `0.38`.
    7. `Mat_Red_Thread`: Vivid crimson red `(0.85, 0.02, 0.02, 1.0)`, sheen `0.80`, roughness `0.30`.
    8. `Mat_Butterfly_Glow`: Emissive translucent shader: base color `(0.95, 0.98, 1.0, 1.0)`, emission color `(0.85, 0.95, 1.0, 1.0)`, emission strength `3.5`.

### 2.5 Module 4: `src/morphomesh/human_grooming.py`
- **Hair Curves & Particle Systems for Yu Nian An**:
  - Hime Cut + Straight Forehead Bangs + Cascading Long Back Hair:
    - `Hair_Bangs`: Flat horizontal fringe across forehead (length ~0.09m, guide strands >= 2,500).
    - `Hair_Sidelocks`: Face-framing side strands falling down the cheeks and shoulders (length ~0.40m, guide strands >= 1,500).
    - `Hair_Back_Long`: Long silky hair cascading down the back past the waist (length ~0.85m, guide strands >= 12,000, total >= 16,000 parent strands, > 100,000 render strands).
    - `Eyebrows`: Feminine arched eyebrow curves (length ~0.012m, guide strands ~800).
    - `Eyelashes`: Fine curved upper and lower eyelashes (length ~0.008m, guide strands ~400).
  - Vertex Group Masking:
    - Full density on `Hair_Scalp`, `Hair_Bangs`, `Hair_Sides`, `Eyebrows`, `Eyelashes`.
    - Strict 0.0 density on face, nose, mouth, eyes, body skin.
  - Generates polygonal ribbon quad mesh (`_Hair_Ribbons`) with UVs for real-time glTF / game engine compatibility.

### 2.6 Module 5: `src/morphomesh/wardrobe.py`
- **Dynamic Wardrobe & Character Accessories**:
  - Garments:
    - `Dress_White_Slip`: Double shoulder straps, fitted bodice with sweetheart neckline, flared A-line pleated skirt ending mid-calf ($d_{\min} \ge 0.015\text{m}$ clearance from body mesh to eliminate clipping).
    - `Dress_Belt`: Cinched double-ribbon waist sash with trailing tails.
    - `Shoes_Flat_Slippers`: Minimalist flat sole with forefoot strap.
  - Character Props:
    - `Accessory_Red_Threads`: 4-5 fine crimson threads originating from finger joints (index, middle, ring, pinky of both hands) spiraling outward into the scene.
    - `Accessory_Glowing_Butterflies`: 8-12 ethereal white butterflies in various flight poses (wings spread, semi-folded, hovering) perched on strings and hovering around the hands.

### 2.7 FastMCP Server Specification (`src/morphomesh/server.py`)
5 new FastMCP tools registered using `@mcp.tool()`:

```python
# 1. morphomesh_create_human_asset
@mcp.tool(name="morphomesh_create_human_asset")
async def morphomesh_create_human_asset(
    character_name: str = "Yu_Nian_An",
    gender: str = "female",
    height: float = 1.65,
    style: str = "stylized_photorealism",
    poly_budget: int = 25000,
    include_blendshapes: bool = True,
    export_format: str = "glb",
    load_into_scene: bool = True,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]

# 2. morphomesh_auto_rig_human
@mcp.tool(name="morphomesh_auto_rig_human")
async def morphomesh_auto_rig_human(
    human_asset_id: Optional[str] = None,
    mesh_object_name: str = "Human_Base_Mesh",
    rig_type: str = "rigify_human",
    skinning_method: str = "automatic_weights",
    include_face_rig: bool = True,
    include_finger_rig: bool = True,
    pose: str = "puppeteer_pose",
    export_format: str = "fbx",
    ctx: Optional[Context] = None,
) -> Dict[str, Any]

# 3. morphomesh_setup_human_materials
@mcp.tool(name="morphomesh_setup_human_materials")
async def morphomesh_setup_human_materials(
    mesh_object_name: str = "Human_Base_Mesh",
    skin_tone: str = "porcelain_fair",
    subsurface_scattering: bool = True,
    refractive_eyes: bool = True,
    render_engine: str = "CYCLES",
    save_after: bool = False,
    save_path: Optional[str] = None,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]

# 4. morphomesh_groom_human
@mcp.tool(name="morphomesh_groom_human")
async def morphomesh_groom_human(
    mesh_object_name: str = "Human_Base_Mesh",
    hairstyle: str = "hime_cut_long_bangs",
    hair_color: str = "silky_black",
    strand_count: int = 15000,
    include_eyebrows: bool = True,
    include_eyelashes: bool = True,
    generate_ribbons: bool = False,
    save_after: bool = False,
    save_path: Optional[str] = None,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]

# 5. morphomesh_dress_human
@mcp.tool(name="morphomesh_dress_human")
async def morphomesh_dress_human(
    human_object_name: str = "Human_Base_Mesh",
    outfit_preset: str = "yu_nian_an_dress",
    include_sandals: bool = True,
    include_red_threads: bool = True,
    include_glowing_butterflies: bool = True,
    butterfly_count: int = 8,
    clearance_offset: float = 0.015,
    save_after: bool = False,
    save_path: Optional[str] = None,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]
```

### 2.8 Blender 4.5+ & Socket Bridge (Port 9876) Integration
- **Interactive Socket Dispatch**:
  - The live socket listener in `blender_addon/morphomesh/listener.py` handles requests on port 9876 and executes commands on Blender's main thread via `bpy.app.timers`.
  - When `blender_bridge.execute(method, params)` is called:
    1. If interactive socket is active, it dispatches via `execute_code` with an AST-validated script.
    2. If interactive socket is offline, it dispatches via headless runner `blender --background --factory-startup --python <script>`.
- **Windows Path & String Escaping Consideration (CRITICAL)**:
  - On Windows, `tempfile.gettempdir()` produces paths like `C:\Users\Admin\...`.
  - In Python script templates, direct f-string injection like `f'"{path}"'` leads to `SyntaxError: (unicode error) 'unicodeescape' codec can't decode bytes in position 2-3: truncated \UXXXXXXXX escape`.
  - **Rule**: All script templates MUST sanitize Windows paths using `.replace('\\', '/')` or `json.dumps(path)` or `repr(path)` before embedding!
- **Binary Resolution on Windows**:
  - `_resolve_blender_binary()` in `blender_bridge.py` must include:
    `C:\Program Files\Blender Foundation\Blender 4.5\blender.exe`,
    `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`,
    and check `os.environ.get("PROGRAMFILES")`.

### 2.9 Dependency & `pyproject.toml` Considerations
- **No new third-party dependencies are needed**:
  - `mcp>=1.2.0,<2.0.0`
  - `pydantic>=2.0.0`
  - `pillow>=10.0.0`
  - `numpy>=1.24.0`
  - `pytest>=7.0.0`
  - `pytest-asyncio>=0.21.0`
- Keeping the dependency footprint strictly minimal ensures:
  - 100% offline unit testing and sub-second test execution.
  - Zero external cloud API lock-in during testing.
  - Flawless execution across both Windows and macOS Apple Silicon environments.

---

## 3. CAVEATS

1. **Headless vs Interactive Blender**:
   - Blender 4.5.4 is currently running interactively and listening on port 9876. When tests or commands run headless (`--background`), they create a separate transient Blender process. Both modes must be supported seamlessly.
2. **Windows Backslash Pathing**:
   - Any script template generating Python code to run inside Blender must use forward slashes `/` for filepaths to prevent `\U` unicode escape syntax errors.
3. **Existing Tool Schema Test Assertion**:
   - `tests/test_tools_schema.py` currently asserts `assert len(tools) == 7` and `registered_names == EXPECTED_TOOL_NAMES`.
   - When 5 new tools are added, `EXPECTED_TOOL_NAMES` must be updated to include all 12 tools (7 creature + 5 digital human), and `assert len(tools) == 12`.
4. **ARKit Shape Keys Memory Usage**:
   - In pure Python mock environments, storing 52 sparse vertex deltas takes negligible RAM (<2 MB). In Blender, shape keys are natively managed by Bmesh / KeyBlocks.
5. **Hair Simulation vs Realtime Ribbons**:
   - Blender hair particle systems and Geometry Nodes hair curves look photorealistic in Cycles/EEVEE, but standard glTF/FBX exporters do not natively export particle curves. Therefore, generating evaluated polygonal quad ribbon meshes (`_Hair_Ribbons`) is essential for exported assets.

---

## 4. CONCLUSION

The proposed architecture cleanly extends MorphoMesh into an industrial-grade Photorealistic Digital Human Pipeline while preserving 100% backward compatibility with the existing creature generation pipeline.

### Summary of New Modules & Responsibilities:
| Module | Primary Responsibility | Key Classes & Functions |
|---|---|---|
| `src/morphomesh/human_generator.py` | Anthropometric body mesh, 52 ARKit FACS blendshapes, 24 vertex groups | `HumanAnatomyConfig`, `HumanMeshResult`, `generate_human_base_mesh()`, `get_human_generation_script()` |
| `src/morphomesh/human_rigging.py` | Rigify Human Metarig (163 DEF bones, 10 fingers, facial bones, skinning) | `HumanRigConfig`, `HumanArmatureBuilder`, `get_rigify_human_blender_script()` |
| `src/morphomesh/human_materials.py` | Principled BSDF v2 PBR skin (Random Walk SSS), refractive eyes, hair, fabrics | `HumanPBRSuite`, `PBRMaterialConfig`, `get_human_materials_blender_script()` |
| `src/morphomesh/human_grooming.py` | Multi-layer hair grooming (hime cut, bangs, long back hair, brows, lashes) | `HumanGroomingEngine`, `HairLayerConfig`, `get_human_grooming_blender_script()` |
| `src/morphomesh/wardrobe.py` | White slip dress, waist belt, flat sandals, red threads, glowing butterflies | `WardrobeEngine`, `GarmentConfig`, `get_wardrobe_blender_script()` |
| `src/morphomesh/models.py` | Pydantic v2 schemas for all 5 new FastMCP tools | `CreateHumanAssetInput/Output`, `AutoRigHumanInput/Output`, `SetupHumanMaterialsInput/Output`, `GroomHumanInput/Output`, `DressHumanInput/Output` |
| `src/morphomesh/server.py` | FastMCP registration for 5 new tools (total 12 tools) | `morphomesh_create_human_asset`, `morphomesh_auto_rig_human`, `morphomesh_setup_human_materials`, `morphomesh_groom_human`, `morphomesh_dress_human` |
| `src/morphomesh/blender_bridge.py` | Windows path resolution and RPC script dispatch for human methods | `_resolve_blender_binary()`, `_generate_headless_script()`, `create_human_asset()`, `rig_human()`, etc. |

---

## 5. VERIFICATION METHOD

### 5.1 Independent Test Commands
1. **Verify Python Environment and Blender Path**:
   ```powershell
   $env:BLENDER_PATH="C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
   & "C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe" -c "import socket, json; s = socket.socket(); s.connect(('127.0.0.1', 9876)); s.sendall(json.dumps({'jsonrpc':'2.0','id':'ping','method':'morphomesh.ping','params':{}}).encode('utf-8')); print(s.recv(4096).decode('utf-8')); s.close()"
   ```
2. **Run FastMCP Tools Schema Verification**:
   ```powershell
   pytest tests/test_tools_schema.py -v
   ```
   *Expected*: All 12 tools registered and pass schema, property, and constraint validation.
3. **Run Full Test Suite**:
   ```powershell
   $env:BLENDER_PATH="C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
   pytest tests/ -v
   ```
   *Expected*: 100% test pass rate with exit code 0.
4. **Inspect Files Produced**:
   - `src/morphomesh/human_generator.py`
   - `src/morphomesh/human_rigging.py`
   - `src/morphomesh/human_materials.py`
   - `src/morphomesh/human_grooming.py`
   - `src/morphomesh/wardrobe.py`
   - `src/morphomesh/models.py`
   - `src/morphomesh/server.py`
   - `src/morphomesh/blender_bridge.py`
   - `src/morphomesh/__init__.py`
