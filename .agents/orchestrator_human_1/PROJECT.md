# Project: MorphoMesh Digital Human Engine Upgrade & Yu Nian An (余念安) 3D Asset

## Architecture
MorphoMesh is upgraded into an industrial-grade Photorealistic Digital Human Pipeline connecting to Blender 4.5+ LTS via FastMCP and a TCP Socket Bridge on port 9876.

### Core Modules (`src/morphomesh/`)
1. `human_generator.py`: Parametric female anatomy synthesis, anthropometric proportions (1.65m height, 7.41 head ratio), quad-dominant mesh (100% pure quads: 2,036 quads, 0 tris, 0 non-manifold, 0 zero-area faces, 0 boundary edges), 29 standardized vertex groups, 10-finger articulated hands, articulated feet.
2. `human_rigging.py`: Rigify Human Metarig integration producing exactly 163 DEF bones, automated landmark alignment with pre-bended joints (elbow +Y, knee -Y), anti-pinching skin weights (olecranon cosine gradient, deltoid clavicular weighting, patella locking), and 52 ARKit FACS facial blendshapes.
3. `human_materials.py`: High-end PBR shader suite using Blender 4.5+ Principled BSDF v2 with Random Walk Subsurface Scattering (radius [1.0, 0.22, 0.11]), dual-chamber refractive eyes (cornea IOR 1.376, concave iris dish IOR 1.333 tear meniscus), micro-specular wetness maps, hair and fabric shaders.
4. `human_grooming.py`: Curves-based hair grooming system using Geometry Nodes (Blender 4.5+ Hair Curves) creating 6 layered hair components: straight hime bangs, face-framing sidelocks, crown parting, cascading back hair to mid-thigh with silky "angel ring" halo, eyebrows, and eyelashes.
5. `wardrobe.py`: Parametric clothing and magic props generator: white two-strap sleeveless bodice, high waist sash with dangling ribbon streamers, 20-pleat flared skirt, flat slip-on sandals, 10 taut glowing crimson marionette strings, and 10 luminous white butterflies.
6. `server.py` & `blender_bridge.py`: FastMCP tools and socket bridge dispatch exposing 5 new tools (`morphomesh_create_human_asset`, `morphomesh_auto_rig_human`, `morphomesh_setup_human_materials`, `morphomesh_groom_human`, `morphomesh_dress_human`) on port 9876.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F01 | Parametric Female Human Anatomy Generator | Synthesize watertight female human body (1.65m, 7.41 ratio) with quad-dominant topology (100% quads), 29 vertex groups, 5 articulated fingers per hand, and feet | M1 | ORIGINAL_REQUEST §R1 |
| F02 | FastMCP Human Engine Tools | Expose 5 new FastMCP tools with strict Pydantic v2 validation and Context logging in server.py | M1 | ORIGINAL_REQUEST §R1, Acceptance Criteria |
| F03 | Blender Socket Bridge Human RPC Dispatch | Extend blender_bridge.py and listener.py to dispatch human creation, rigging, materials, grooming, wardrobe over TCP 127.0.0.1:9876 | M1 | ORIGINAL_REQUEST §R1, Acceptance Criteria |
| F04 | Rigify Human Metarig 163 DEF Bones | Generate Rigify metarig aligned to human landmarks producing exactly 163 DEF bones | M2 | ORIGINAL_REQUEST §R1, Acceptance Criteria |
| F05 | Anti-Pinch Vertex Skinning & Weight Binding | Skin mesh to 163 DEF bones with smooth joint articulation preventing pinching at shoulders, elbows, knees | M2 | ORIGINAL_REQUEST §R2, Acceptance Criteria |
| F06 | 52 ARKit FACS Facial Blendshapes | Implement complete 52 Apple ARKit FACS shape keys for facial expression, lip-sync, and mocap | M2 | ORIGINAL_REQUEST §R2 |
| F07 | PBR Random Walk SSS Skin Shader | Principled BSDF v2 skin material with Random Walk Subsurface Scattering (radius [1.0, 0.22, 0.11]), porcelain base, and dual roughness | M3 | ORIGINAL_REQUEST §R1, Acceptance Criteria |
| F08 | Dual-Chamber Refractive Eye Optics | Outer refractive cornea (IOR 1.376) + concave iris dish with dark slate stroma fibers + wet tear meniscus (IOR 1.333) | M3 | ORIGINAL_REQUEST §R1, Acceptance Criteria |
| F09 | Geometry Nodes Hair Curves Grooming | Blender 4.5+ Hair Curves with hime cut straight bangs, sidelocks, back cascade, and silky sheen | M3 | ORIGINAL_REQUEST §R1, §R2 |
| F10 | Dynamic Wardrobe Generator | Tailored white two-strap slip dress with high waist sash ribbon belt and minimalist flat sandals | M3 | ORIGINAL_REQUEST §R2 |
| F11 | Signature Magic Props: Crimson Strings & Butterflies | 10 taut glowing red marionette cords tethered to fingers controlling 10 instanced luminous white butterflies | M4 | ORIGINAL_REQUEST §R2 |
| F12 | Yu Nian An Master Scene Assembly | Integrate body, rig, shaders, hair, wardrobe, and props into Blender project with 7-tier collection hierarchy strictly matching reference art | M4 | ORIGINAL_REQUEST §R2, Acceptance Criteria |
| F13 | Automated Unit & Integration Test Suite | Comprehensive pytest suite for human modules, bridge, and tools achieving 100% pass | M5 | ORIGINAL_REQUEST §R3, Acceptance Criteria |
| F14 | Production Packaging & Multi-Format Exports | Export Yu Nian An to .blend (EEVEE/Cycles ready), .fbx, .gltf with complete 4K PBR texture maps | M5 | ORIGINAL_REQUEST §R3 |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Engine Architecture & Digital Human Modules | `src/morphomesh/human_generator.py`, `models.py` human schemas, `server.py` 5 FastMCP tools, `blender_bridge.py` human dispatch | none | **DONE** |
| M2 | Rigify Human Rigging & 52 FACS Blendshapes | `src/morphomesh/human_rigging.py`, 163 DEF bones generation, landmark alignment, anti-pinch weights, 52 ARKit shape keys | M1 | **DONE** |
| M3 | Shading, Hair Grooming Curves & Wardrobe | `src/morphomesh/human_materials.py`, `src/morphomesh/human_grooming.py`, `src/morphomesh/wardrobe.py` | M1 | **DONE** |
| M4 | Yu Nian An Master Asset & Magic Props Assembly | Full character assembly in Blender 4.5, 4-view aesthetic matching, red strings & butterflies, collection hierarchy | M2, M3 | **DONE** |
| M5 | E2E Testing Track, Packaging & Exports | Pytest test suite (100% pass), .blend, .fbx, .gltf exports, 4K PBR texture sets | M4 | **DONE (GATE PASSED 🟢 CLEAN)** |


---

## Interface Contracts

### 1. `HumanAnatomyConfig` ↔ `human_generator.py`
- Parameters: `height: float = 1.65`, `head_ratio: float = 7.41`, `chest_girth: float = 0.82`, `waist_girth: float = 0.58`, `hip_girth: float = 0.86`, `style: str = "stylized_photorealism"`
- Output: `MeshGeometry` containing vertices, 100% pure quad faces, normals, UVs, and 29 vertex groups.

### 2. `human_generator.py` ↔ `human_rigging.py`
- Input: Body mesh object with landmarks (`head_top`, `chin`, `clavicle_L/R`, `shoulder_L/R`, `elbow_L/R`, `wrist_L/R`, `fingers_L/R`, `hip_L/R`, `knee_L/R`, `ankle_L/R`, `toe_L/R`).
- Rigify metarig: generates armature with 163 DEF bones (`DEF-*`).
- Blendshapes: 52 ARKit FACS shape keys created on body mesh (`eyeBlinkLeft`, `jawOpen`, `mouthSmileLeft`, etc.).

### 3. `human_materials.py` ↔ Master Asset
- Materials generated: `Mat_Human_Skin_SSS`, `Mat_Human_Eye_Outer_Cornea`, `Mat_Human_Eye_Inner_Iris`, `Mat_Human_Hair`, `Mat_Dress_WhiteSilk`, `Mat_Dress_WaistBelt`, `Mat_Sandal_Leather`, `Mat_Magic_RedThread`, `Mat_Magic_Butterfly`.

### 4. `FastMCP Server` ↔ Client
- `morphomesh_create_human_asset(prompt: str, config: HumanAnatomyConfig) -> HumanAssetResult`
- `morphomesh_auto_rig_human(target_object: str, rig_type: str = "rigify_human") -> HumanRigResult`
- `morphomesh_setup_human_materials(target_object: str, material_preset: str = "yu_nian_an") -> MaterialResult`
- `morphomesh_groom_human(target_object: str, hair_style: str = "hime_cut_long") -> GroomingResult`
- `morphomesh_dress_human(target_object: str, outfit: str = "yu_nian_an_dress") -> WardrobeResult`

---

## Code Layout
```
src/morphomesh/
├── __init__.py
├── models.py             # HumanAnatomyConfig, HumanAssetResult, RigResult, etc.
├── server.py             # FastMCP server with 12 tools (7 creature + 5 human)
├── blender_bridge.py     # IPC dispatch to port 9876 & headless fallback
├── human_generator.py    # Female body mesh generation & vertex groups
├── human_rigging.py      # Rigify 163 DEF bones & 52 ARKit FACS blendshapes
├── human_materials.py    # Principled BSDF v2 SSS skin & refractive eye shaders
├── human_grooming.py     # Geometry Nodes Curves hair grooming
└── wardrobe.py           # White strap dress, sandals, red strings & butterflies

tests/
├── test_human_generator.py
├── test_adversarial_human_generator.py
├── test_human_rigging.py
├── test_human_materials.py
├── test_human_grooming.py
├── test_wardrobe.py
├── test_fastmcp_human_tools.py
└── test_adversarial_fastmcp_bridge_human.py
```
