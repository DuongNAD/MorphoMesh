# Project: MorphoMesh Auto-Critic QA & Multi-Angle Inspector Upgrade

## Architecture
MorphoMesh is an autonomous 3D digital content creation pipeline and Blender MCP server. This project establishes a closed-loop quality assurance and inspection subsystem:
1. **Interactive Socket Bridge Subsystem**:
   - `blender_addon/morphomesh/listener.py`: In-Blender TCP socket listener (port 9876) dispatching requests into Blender's main event loop via `bpy.app.timers`.
   - `src/morphomesh/blender_bridge.py`: Python client bridge supporting dual-mode execution (interactive socket RPC when Blender is open, headless background batch CLI fallback when closed).
2. **Inspector Camera & Viewport Capture Subsystem**:
   - `src/morphomesh/camera_rig.py`: Mathematical solver for hierarchical bounding box, 5 anatomical centers (Full Body, Head, Torso, Hands, Feet), and optical framing distance $d = \frac{R}{\sin(\alpha_{\min})} \cdot (1 + \mu)$ across 6 canonical viewpoints and turntable rotations.
   - Dual-mode capture: Interactive OpenGL grab (`bpy.ops.render.opengl`) running in $<200\text{ms}$, and headless Workbench render fallback (`bpy.ops.render.render`).
3. **Auto-Critic Visual QA Subsystem**:
   - `src/morphomesh/visual_critic.py`: Automated structural integrity evaluation engine analyzing BVH signed distance penetration, anthropometric proportions, rig/skinning deformation pinching, and hair curve intersections.
   - `src/morphomesh/models.py`: Pydantic v2 typed diagnostic feedback schema (`VisualCritiqueOutput`, `DefectItem`, `ActionableRecommendation`, `BoundingBox3D`).
4. **FastMCP Server & Tooling Layer**:
   - `src/morphomesh/server.py`: Exposes inspection, capture, and critique tools with feature-flag gating preserving legacy backward compatibility.
5. **Verification & Testing Suite**:
   - Production test suites in `tests/` verifying camera math, viewport rendering, bridge socket parity, defect diagnosis accuracy, and 100% pytest pass rate.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---|---|---|---|
| 1 | Socket NDJSON Streaming & Framing | Newline-delimited JSON framing to eliminate buffer boundary errors and JSONDecodeError | M1 | Survey E2 |
| 2 | Timer Immortality Exception Barrier | Top-level catch block in `_drain_queue` always returning 0.02s to prevent timer drop | M1 | Survey E2 |
| 3 | Socket RPC Dispatch Parity | Full `_dispatch` support in `listener.py` for all 18 core pipeline and inspection methods | M1 | Survey E1, E2, E3 |
| 4 | Complete Scene Status Query Parity | Comprehensive query of meshes, materials, polycounts, lights, cameras, and rig info | M1 | Survey E1 |
| 5 | Hierarchical World Bounding Box Solver | Calculates global AABB across multi-mesh character hierarchies using $M_{\text{world}} \cdot v_{\text{local}}$ | M2 | Survey E1, E2 |
| 6 | Optical Framing Distance Solver | Derives $d = \frac{R}{\sin(\alpha_{\min})} \cdot (1 + \mu)$ accounting for FOV and aspect ratio | M2 | Survey E2 |
| 7 | 5 Anatomical Sub-Region Centers | Computes framing centers for Full Body, Head/Portrait, Torso, Hands, and Feet | M2 | Survey E2 |
| 8 | 6 Canonical Viewpoints & Turntable Orbit | Camera placement $(\theta, \phi, d)$ with `to_track_quat('-Z', 'Y')` for Front, Side, Back, 3/4, Head, Hands | M2 | Survey E1, E2 |
| 9 | Fast Interactive OpenGL Viewport Grab | `bpy.ops.render.opengl` with `temp_override` on `VIEW_3D` in $<200\text{ms}$ with diagnostic shading | M2 | Survey E1, E2 |
| 10 | Headless CLI Workbench Render Fallback | Headless background capture via Workbench engine avoiding missing OpenGL context errors | M2 | Survey E1 |
| 11 | BVH Signed Distance Penetration Detection | $s_i = (w_i - p_i) \cdot \hat{n}_i < -0.5\text{mm}$ and raycasting for garment clipping and skin burst | M3 | Survey E1, E3 |
| 12 | Anthropometric Proportion Analysis | Evaluates height, head ratio ($H_{\text{total}}/H_{\text{head}}$), arm span, and shoulder/hip breadth | M3 | Survey E1, E3 |
| 13 | Rig Skinning Volume & Crease Evaluation | Joint volume preservation $\rho_V = V_{\text{posed}}/V_0$ and acute dihedral creasing $\cos\theta < -0.85$ | M3 | Survey E3 |
| 14 | Grooming Curve Intersection Audit | Hair spline sample queries against body/garment BVH trees detecting submerged roots and collisions | M3 | Survey E1, E3 |
| 15 | Pydantic v2 Diagnostic Feedback Schema | Structured typing for `DefectItem`, `DefectSeverity`, `BoundingBox3D`, `ActionableRecommendation` | M3 | Survey E3 |
| 16 | Baseline Defect Injection Verification Demo | 4 procedural test fixtures with injected flaws proving $>95\%$ critic detection accuracy | M3 | Survey E3 |
| 17 | FastMCP Server Inspection Tools | Expose `morphomesh_capture_viewport`, `morphomesh_critique_visual_quality`, `morphomesh_setup_inspector_camera_rig` | M4 | Survey E1, E3 |
| 18 | Backward-Compatible Tool Gating | `MORPHOMESH_INCLUDE_INSPECTION_TOOLS` preserving legacy 7-tool schema test compatibility | M4 | Survey E3 |
| 19 | Automated Pytest Verification Suite | Comprehensive tests for camera math, viewport rendering, socket parity, and visual critique | M4 | Survey E1, E2, E3 |
| 20 | User & Tool Documentation | Updated README.md and FastMCP docstrings reflecting all new inspection capabilities | M4 | Survey E1, E3 |
| 21 | Full End-to-End Live Scene Inspection | Multi-angle inspection and critique executed against live character session with preview artifacts | M5 | Survey E1, E2, E3 |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| M1 | Interactive Socket Bridge Parity & Reliability (R3) | NDJSON framing, timer immortality guard, full `_dispatch` in `listener.py`, client methods in `blender_bridge.py` | None | DONE |
| M2 | Multi-Angle Inspector Camera & Fast Viewport Capture (R1) | `camera_rig.py`, bounding box & anatomical framing math, 6 viewpoints + turntable, dual-mode OpenGL/Workbench capture | M1 | DONE |
| M3 | Closed-Loop Visual Quality Critique Engine (R2) | `visual_critic.py`, BVH penetration, proportion analysis, skinning pinch, grooming collision, Pydantic schemas, baseline defect demo | M2 | DONE |
| M4 | FastMCP Tool Integration & Verification Suite (R4) | `server.py` tool exposure & gating, README documentation, test suites for camera math, socket parity, and visual critic | M3 | PLANNED |
| M5 | Final E2E Milestone & Adversarial Coverage Hardening | 100% E2E test verification, live scene multi-angle critique run, visual preview artifacts, adversarial tests | M4 | PLANNED |

---

## Interface Contracts

### `src/morphomesh/camera_rig.py` ↔ `src/morphomesh/blender_bridge.py`
```python
def calculate_character_bounds(
    mesh_objects: Optional[List[str]] = None
) -> Tuple[mathutils.Vector, float, mathutils.Vector, mathutils.Vector]:
    """Returns (center, radius, min_corner, max_corner) in world space."""

def setup_inspector_camera(
    viewpoint: str = "three_quarter",
    target_center: Optional[Tuple[float, float, float]] = None,
    framing_radius: Optional[float] = None,
    focal_length: float = 50.0,
    camera_name: str = "MorphoMesh_Inspector_Camera",
) -> Dict[str, Any]:
    """Creates/repositions camera in Blender, tracks target center, returns camera metadata."""

def capture_viewport_image(
    output_path: str,
    camera_name: str = "MorphoMesh_Inspector_Camera",
    resolution: Tuple[int, int] = (1024, 1024),
    shading_mode: str = "SOLID",
    color_type: str = "RANDOM",
) -> str:
    """Executes OpenGL grab or Workbench render, saves PNG to output_path, returns path."""
```

### `src/morphomesh/visual_critic.py` ↔ `src/morphomesh/models.py`
```python
def evaluate_mesh_penetration(
    body_obj_name: str,
    garment_obj_names: List[str],
    clearance_tolerance: float = 0.0005,
) -> List[DefectItem]:
    """Evaluates signed distance and face overlaps via BVHTree."""

def evaluate_body_proportions(
    body_obj_name: str,
    target_preset: str = "stylized_heroine",
) -> List[DefectItem]:
    """Evaluates anatomical ratios (head-to-body, arm span, shoulder/hip) against preset."""

def evaluate_rig_skinning_pinch(
    armature_obj_name: str,
    mesh_obj_name: str,
) -> List[DefectItem]:
    """Evaluates joint volume retention and acute dihedral creases."""

def evaluate_grooming_intersections(
    hair_obj_names: List[str],
    body_obj_name: str,
) -> List[DefectItem]:
    """Evaluates hair curve collisions with scalp/garments."""

def run_visual_critique(
    input_data: VisualCritiqueInput
) -> VisualCritiqueOutput:
    """Executes multi-angle capture and full defect evaluation, returning structured diagnostic report."""
```

---

## Code Layout
- `src/morphomesh/camera_rig.py` (New): Camera positioning math, framing algorithms, viewpoint coordinate solvers.
- `src/morphomesh/visual_critic.py` (New): Auto-critic defect detection algorithms, diagnostic report generator.
- `src/morphomesh/models.py`: Pydantic v2 schemas for viewport capture and visual critique.
- `src/morphomesh/blender_bridge.py`: Client-side RPC methods for inspection camera, viewport capture, and critique.
- `blender_addon/morphomesh/listener.py`: Server-side socket listener, NDJSON framing, main-thread timer dispatch.
- `src/morphomesh/server.py`: FastMCP tools for capture and visual critique.
- `tests/test_inspector_camera.py` (New): Unit tests for camera math and framing.
- `tests/test_visual_critic.py` (New): Unit tests for defect detection algorithms, schemas, and intentional defect injection baseline.
- `tests/test_bridge_socket_parity.py` (New): Tests for socket RPC communication parity.
- `tests/test_fastmcp_inspection_tools.py` (New): Tests for FastMCP tool schemas and execution.
- `README.md`: Documentation updates.
