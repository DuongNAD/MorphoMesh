# Project: MorphoMesh Production Upgrade

## Architecture
MorphoMesh is an autonomous 3D digital content creation pipeline and Blender MCP server. This production upgrade hardens and integrates all 3 tool suites, automates closed-loop visual QA, enables multi-angle inspection and viewport capture, and achieves 100% test pass.

1. **FastMCP Server & Tooling Layer (`src/morphomesh/server.py`)**:
   - Exposes 17 tools across 3 functional suites: Creature Pipeline (7 tools), Human & Wardrobe Generation (7 tools), Inspection & Visual QA (3 tools).
   - Dynamic environment variable gating (`MORPHOMESH_INCLUDE_ALL_TOOLS`, `MORPHOMESH_INCLUDE_HUMAN_TOOLS`, `MORPHOMESH_INCLUDE_INSPECTION_TOOLS`) with absolute backward compatibility (7 tools default).
2. **Interactive Socket Bridge Subsystem (`blender_addon/morphomesh/listener.py` & `src/morphomesh/blender_bridge.py`)**:
   - Line-buffered NDJSON framing (`\n` delimiter).
   - In-Blender event loop timer immortality barrier (`bpy.app.timers`).
   - Hardened teardown exception handling to suppress WinError 10038.
   - 4-tier execution fallback cascade (direct RPC -> execute_code -> headless CLI -> offline pure-Python solvers).
3. **Inspector Camera & Fast Viewport Capture Subsystem (`src/morphomesh/camera_rig.py`)**:
   - Evaluated depsgraph hierarchical bounding box solver ($M_{\text{world}} \cdot v_{\text{local}}$).
   - 5 anatomical focus centers (Full Body, Head, Torso, Hands, Feet) with Armature DEF bone priorities and height fraction fallbacks.
   - Optical framing distance solver $d = \frac{R}{\sin(\alpha_{\min})} \cdot (1 + \mu)$.
   - 6 canonical viewpoints + 360 turntable orbit.
   - Dual-mode viewport capture: Interactive OpenGL frame grab (<200ms) with diagnostic shading (SOLID, RANDOM, WIREFRAME) and headless Workbench render fallback (<700ms).
4. **Auto-Critic Visual QA Subsystem (`src/morphomesh/visual_critic.py` & `src/morphomesh/models.py`)**:
   - PurePythonBVHTree spatial acceleration for 100% offline testability.
   - 4 Defect evaluation categories:
     * Garment/mesh signed distance penetration ($s_i < -0.5\text{mm}$) with 3-tier boundary edge filter.
     * Anthropometric proportion deviations across 6 presets.
     * Rigging/skinning pinch ($\cos\theta < -0.85$) and joint volume conservation via divergence theorem ($\rho_V \notin [0.80, 1.25]$).
     * Hair grooming curve collisions (submerged roots, detached roots, shaft collisions).
   - Pydantic v2 typed output (`VisualCritiqueOutput`) with quality score $100.0 - (25\cdot N_{\text{crit}} + 10\cdot N_{\text{maj}} + 3\cdot N_{\text{min}})$ and actionable remediation recommendations.
   - 100% benchmark detection accuracy.
5. **Character Verification Pipelines & Production Delivery**:
   - "Yu Nian An": 7-tier collection hierarchy, 163 DEF bones, 52 ARKit blendshapes, 9 4K PBR textures, production exports (`.blend`, `.glb`, `.fbx`).
   - "Armored War Bear": Ursine plantigrade anatomy, 20 curved claws ($\text{dot} > 0.60, \Delta z < 0$), 18 vertex groups, 12,000 fur guide strands, fitted armor ($d_{\min} \ge 15\text{mm}$), beauty renders.
6. **Full Test Suite (100% Pass)**:
   - 87 test files in `tests/`, 2,071 tests, 0 failures, 0 regressions.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---|---|---|---|
| 1 | Socket NDJSON Streaming & Framing | Newline-delimited JSON framing to eliminate buffer boundary errors | M1 | Survey E2 |
| 2 | Timer Immortality Exception Barrier | Top-level catch block in `_drain_queue` always returning 0.02s | M1 | Survey E2 |
| 3 | Socket RPC Dispatch Parity | Full `_dispatch` support in `listener.py` for all 18 core methods | M1 | Survey E1, E2, E3 |
| 4 | Complete Scene Status Query Parity | Comprehensive query of meshes, materials, polycounts, armatures | M1 | Survey E1 |
| 5 | Hierarchical World Bounding Box Solver | Global AABB across multi-mesh hierarchies using evaluated depsgraph | M2 | Survey E1, E2 |
| 6 | Optical Framing Distance Solver | Derives $d = \frac{R}{\sin(\alpha_{\min})} \cdot (1 + \mu)$ accounting for FOV and sensor fit | M2 | Survey E2 |
| 7 | 5 Anatomical Sub-Region Centers | Computes framing centers for Full Body, Head, Torso, Hands, Feet | M2 | Survey E2 |
| 8 | 6 Canonical Viewpoints & Turntable Orbit | Placement $(\theta, \phi, d)$ with `to_track_quat('-Z', 'Y')` | M2 | Survey E1, E2 |
| 9 | Fast Interactive OpenGL Viewport Grab | `bpy.ops.render.opengl` with `temp_override` on `VIEW_3D` in <200ms | M2 | Survey E1, E2 |
| 10 | Headless CLI Workbench Render Fallback | Headless background capture via Workbench engine | M2 | Survey E1 |
| 11 | BVH Signed Distance Penetration Detection | $s_i = (w_i - p_i) \cdot \hat{n}_i < -0.5\text{mm}$ with 3-tier boundary edge filter | M3 | Survey E1, E3 |
| 12 | Anthropometric Proportion Analysis | Evaluates height, head ratio, arm span, and shoulder/hip breadth | M3 | Survey E1, E3 |
| 13 | Rig Skinning Volume & Crease Evaluation | Joint volume preservation $\rho_V$ and acute dihedral creasing | M3 | Survey E3 |
| 14 | Grooming Curve Intersection Audit | Hair spline sample queries against body/garment BVH trees | M3 | Survey E1, E3 |
| 15 | Pydantic v2 Diagnostic Feedback Schema | Structured typing for `VisualCritiqueOutput`, `DefectItem`, `ActionableRecommendation` | M3 | Survey E3 |
| 16 | Baseline Defect Injection Verification Demo | 4 procedural test fixtures proving >95% (achieved 100%) critic detection accuracy | M3 | Survey E3 |
| 17 | FastMCP Server 17 Tools Exposure | Expose all 3 suites (Creature: 7, Human: 7, Inspection: 3) in `server.py` | M4 | Survey E1 |
| 18 | Backward-Compatible Tool Gating | `MORPHOMESH_INCLUDE_ALL_TOOLS`, `MORPHOMESH_INCLUDE_HUMAN_TOOLS`, `MORPHOMESH_INCLUDE_INSPECTION_TOOLS` | M4 | Survey E1 |
| 19 | Inspection Schemas Integration in `server.py` | Top-level imports and Pydantic model validation with `ToolError` | M4 | Survey E1 |
| 20 | Socket IPC Teardown Hardening | Guard in `listener.py::_accept_loop` suppressing WinError 10038 | M4 | Survey E3 |
| 21 | Base Mold Anatomical Topology Corrections | Fix chin tip anterior projection (>=45mm), 8 quad winding orders, WHR [0.67, 0.72] | M5 | Survey E3 |
| 22 | Wardrobe Bodice Bust Clearance Expansion | Expand `generate_dress_bodice()` anterior contour for teardrop bust | M5 | Survey E3 |
| 23 | Upper Limb Twist Skinning Weight Normalization | Normalize linear blend twist weights in `human_rigging.py` | M5 | Survey E3 |
| 24 | Character Master Asset Regeneration | Re-run `scripts/build_ultimate_yu_nian_an.py` to update master .blend and exports | M5 | Survey E3 |
| 25 | Multi-Angle Inspector Preview Artifacts | Capture 6 canonical viewpoint preview images in `artifacts/` | M5 | Survey E2 |
| 26 | 100% Repository Test Pass Verification | Ensure all 2,071 tests in `tests/` pass with 0 failures and 0 regressions | M5 | Survey E3 |
| 27 | Production Documentation Update | Update `PROJECT.md` and `README.md` reflecting M4 & M5 completion | M5 | Survey E1, E3 |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| M1 | Interactive Socket Bridge Parity & Reliability | NDJSON framing, timer immortality guard, full `_dispatch` in `listener.py`, client methods in `blender_bridge.py` | None | DONE |
| M2 | Multi-Angle Inspector Camera & Fast Viewport Capture | `camera_rig.py`, bounding box & anatomical framing math, 6 viewpoints + turntable, dual-mode OpenGL/Workbench capture | M1 | DONE |
| M3 | Closed-Loop Visual Quality Critique Engine | `visual_critic.py`, BVH penetration, proportion analysis, skinning pinch, grooming collision, Pydantic schemas, baseline defect demo | M2 | DONE |
| M4 | FastMCP Tool Integration & Socket Hardening | `server.py` inspection schemas & Pydantic validation, gating verification, `listener.py` teardown guard | M3 | IN_PROGRESS |
| M5 | 100% Test Pass, Scene Verification & Production Delivery | Base mold & wardrobe geometry fixes, master scene & preview generation, 2,071 tests 100% pass, documentation | M4 | PLANNED |

---

## Code Layout
- `src/morphomesh/server.py`: FastMCP server registering 17 tools across 3 suites, environment gating.
- `src/morphomesh/camera_rig.py`: Camera positioning math, framing algorithms, viewpoint coordinate solvers, OpenGL grab.
- `src/morphomesh/visual_critic.py`: PurePythonBVHTree, defect evaluation engines, diagnostic reporting.
- `src/morphomesh/models.py`: Pydantic v2 schemas for all tools, viewport capture, and visual critique.
- `src/morphomesh/blender_bridge.py`: Client-side RPC methods for all 17 tools and fallback execution.
- `blender_addon/morphomesh/listener.py`: Server-side socket listener, NDJSON framing, main-thread timer dispatch.
- `src/morphomesh/human_generator.py`: Anatomical base mold, chin projection, facial features, WHR.
- `src/morphomesh/wardrobe.py`: Sundress, bodice, pleated skirt, sandals, cords, butterflies.
- `src/morphomesh/human_rigging.py`: 163 DEF bones, ARKit shape keys, twist bone skinning weights.
- `tests/`: 87 test files, 2,071 tests covering creature, human, inspection, gating, and socket parity.
