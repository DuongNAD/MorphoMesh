# MorphoMesh Milestone 4: Documentation & Regression Matrix Analysis Blueprint

**Author**: Explorer M4_3 (Documentation & Regression Matrix Explorer)  
**Date**: 2026-09-07  
**Working Directory**: `e:\tool\mcp\MorphoMesh\.agents\explorer_m4_insp_3`  
**Milestone**: Milestone 4 (FastMCP Tool Integration & Verification Suite)

---

## 1. Executive Summary

This document establishes the authoritative, turnkey implementation blueprint for:
1. **Repository Documentation in `README.md`**:
   - Integrating two comprehensive, production-grade sections:
     * `## Multi-Angle Inspection Camera & Viewport Capture`
     * `## Closed-Loop Visual Quality Critique (Auto-Critic QA)`
   - Documenting the 3 FastMCP inspection and critique tools (`morphomesh_setup_inspector_camera_rig`, `morphomesh_capture_viewport`, `morphomesh_critique_visual_quality`), their inputs, outputs, schemas, and usage examples.
   - Detailing the 6 canonical viewpoints (`front`, `side`, `back`, `three_quarter`, `top`, `bottom`) and 5 anatomical sub-region centers (`full_body`, `head`, `torso`, `hands`, `feet`).
   - Documenting diagnostic viewport shading modes (`SOLID` with `color_type='RANDOM'`, `WIREFRAME`, `MATERIAL`) and the dual-mode rendering architecture (interactive OpenGL viewport grab `<200ms` vs. headless Workbench fallback `<0.7s`).
   - Documenting the 4 Auto-Critic QA geometric evaluation checks (BVH signed distance garment clipping, body proportion analysis, rig skinning deformation & pinching, and hair curve collision auditing) alongside machine-actionable remediation recommendations.
   - Documenting the feature-flag gating mechanism via environment variable `MORPHOMESH_INCLUDE_INSPECTION_TOOLS=1` ensuring 100% backward compatibility with legacy 7-tool creature tests.
2. **Full Repository Regression Test Matrix**:
   - Compiling the comprehensive test inventory and verification commands across Milestones M1, M2, M3, and M4.
   - Providing verified execution commands for core inspection suites, fast developer suites, and the full repository test suite.

---

## 2. Exact Blueprint for `README.md` Additions

### 2.1 Table of Contents Revision
In `README.md`, update the `Table of Contents` section (currently lines 28–41) to incorporate the two new dedicated sections and maintain consistent numbering:

```markdown
## Table of Contents
1. [Core Features & Systems](#core-features--systems)
2. [Hybrid Computing Topology](#hybrid-computing-topology)
3. [The 5-Stage Synthesis Pipeline](#the-5-stage-synthesis-pipeline)
4. [Open-Source Integration Hub](#open-source-integration-hub)
5. [Anatomy, Grooming, Materials & Armor](#anatomy-grooming-materials--armor)
6. [Installation & Quickstart](#installation--quickstart)
7. [FastMCP Tool Reference (Core & Inspection Tools)](#fastmcp-tool-reference-core--inspection-tools)
8. [Multi-Angle Inspection Camera & Viewport Capture](#multi-angle-inspection-camera--viewport-capture)
9. [Closed-Loop Visual Quality Critique (Auto-Critic QA)](#closed-loop-visual-quality-critique-auto-critic-qa)
10. [Dual-Mode Blender Bridge Architecture](#dual-mode-blender-bridge-architecture)
11. [AST Security Sandbox](#ast-security-sandbox)
12. [Google Antigravity 2.0 Configuration](#google-antigravity-20-configuration)
13. [CLI Usage Guide](#cli-usage-guide)
14. [Verification & Conformance Testing](#verification--conformance-testing)
15. [Documentation Index](#documentation-index)
16. [License & Acknowledgments](#license--acknowledgments)
```

---

### 2.2 FastMCP Tool Reference Section Enhancement
Enhance Section 7 (`## FastMCP Tool Reference`) to present the modular tool suites:
- **7 Canonical Creature Generation Tools** (Active by default)
- **3 Multi-Angle Inspection & Auto-Critic QA Tools** (Active when `MORPHOMESH_INCLUDE_INSPECTION_TOOLS=1`)
- **7 Digital Human Pipeline Tools** (Active when `MORPHOMESH_INCLUDE_HUMAN_TOOLS=1`)

Add the following inspection tools table directly beneath the core tools table:

```markdown
### Inspection & Visual Critique Tools (Milestones M2–M4)
*Enabled by setting `MORPHOMESH_INCLUDE_INSPECTION_TOOLS=1` or `MORPHOMESH_INCLUDE_ALL_TOOLS=1`.*

| # | Tool Name | Role | Primary Inputs | Output Artifacts |
|---|---|---|---|---|
| 8 | `morphomesh_setup_inspector_camera_rig` | Camera Placement | `viewpoint`, `target_object`, `sub_region`, `focal_length`, `margin` | Camera metadata, location, Euler rotation, framing distance, AABB |
| 9 | `morphomesh_capture_viewport` | Viewport Grab | `output_path`, `camera_name`, `resolution`, `shading_mode`, `color_type` | Saved PNG path, image dimensions, base64 preview string, capture time |
| 10 | `morphomesh_critique_visual_quality` | Auto-Critic QA | `character_name`, `camera_angles`, `clearance_tolerance`, `target_preset` | Structured defect report, quality score, actionable modifier recommendations |
```

---

### 2.3 Dedicated Section: `## Multi-Angle Inspection Camera & Viewport Capture`

```markdown
---

## Multi-Angle Inspection Camera & Viewport Capture

Autonomous generative 3D modeling cannot operate blindly. To evaluate aesthetic silhouette, anatomical proportions, garment fit, and surface curvature, MorphoMesh implements a non-destructive **Multi-Angle Inspection Camera Rig and Viewport Capture Subsystem** ([`src/morphomesh/camera_rig.py`](src/morphomesh/camera_rig.py)).

```
+----------------------------------------------------------------------------------------------------+
|                             MULTI-ANGLE INSPECTION CAMERA RIG ARCHITECTURE                         |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|   [ 1. Scene Geometry ]         [ 2. Mathematical Solver ]          [ 3. Optical Positioning ]      |
|   Multi-mesh Hierarchy   --->   Hierarchical World AABB     --->   Exact Framing Distance          |
|   (Body, Dress, Hair)           Circumscribing Sphere (C, R)        d = (R / sin(alpha_min))*(1+mu)|
|                                                                                    |               |
|                                                                                    v               |
|   [ 5. Fast Dual Capture ]       [ 4. Shading & Perspective ]       [ Spherical Orbit Placement ]  |
|   - OpenGL Grab (<200ms) <---   - SOLID (color_type=RANDOM)  <---   - Azimuth theta (0 deg - 360)  |
|   - Workbench (<0.7s)           - WIREFRAME / MATERIAL              - Elevation phi (-88 to +88)   |
|                                                                                                    |
+----------------------------------------------------------------------------------------------------+
```

### 1. Mathematical Framing Solver

Traditional Blender camera framing scripts rely on crude screen-space fits or hardcoded distances that clip elongated limbs or produce excessive margins on tall humanoid meshes. MorphoMesh solves optical framing analytically:

1. **Hierarchical World Bounding Box**:
   Recursively traverses parent Empties, Armatures, and nested mesh objects, evaluating transformed world-space vertices:
   $$\vec{v}_{\text{world}} = \mathbf{M}_{\text{world}} \cdot \vec{v}_{\text{local}}$$
   Derives the global Axis-Aligned Bounding Box (AABB) $[\vec{v}_{\min}, \vec{v}_{\max}]$, geometric center $\vec{C} = \frac{\vec{v}_{\min} + \vec{v}_{\max}}{2}$, and circumscribing sphere radius $R = \frac{\|\vec{v}_{\max} - \vec{v}_{\min}\|}{2}$.

2. **Optical Framing Distance Derivation**:
   For camera lens focal length $f$ and effective sensor dimensions $(w_{\text{eff}}, h_{\text{eff}})$:
   $$\alpha_h = \arctan\left(\frac{w_{\text{eff}}}{2f}\right), \quad \alpha_v = \arctan\left(\frac{h_{\text{eff}}}{2f}\right)$$
   $$\alpha_{\min} = \min(\alpha_h, \alpha_v)$$
   The exact tangency distance ensuring the bounding sphere remains strictly inscribed within both horizontal and vertical frustum boundaries is:
   $$d = \frac{R}{\sin(\alpha_{\min})} \cdot (1 + \mu)$$
   where $\mu$ is the configurable framing safety margin factor (default $0.15$ or $15\%$).

### 2. Canonical Viewpoints & Turntable Sequencing

MorphoMesh provides standardized spherical orbit coordinate presets $(\theta, \phi)$ with automated look-at tracking targeting center $\vec{C}$:

| Viewpoint | Azimuth ($\theta$) | Elevation ($\phi$) | Lens ($f$) | Primary Verification Scope |
|---|---|---|---|---|
| `front` | $0.0^\circ$ | $0.0^\circ$ | $50\text{ mm}$ | Frontal silhouette, facial symmetry, eye alignment, sternum line |
| `side` (`side_right`) | $90.0^\circ$ | $0.0^\circ$ | $50\text{ mm}$ | Spinal S-curve, thoracic posture, nasal bridge, jaw projection |
| `side_left` | $270.0^\circ$ | $0.0^\circ$ | $50\text{ mm}$ | Left lateral profile and contrapposto limb clearance |
| `back` | $180.0^\circ$ | $0.0^\circ$ | $50\text{ mm}$ | Dorsal fur flow, scapula curvature, dress lacing, heel alignment |
| `three_quarter` | $45.0^\circ$ | $15.0^\circ$ | $50\text{ mm}$ | Primary aesthetic 3/4 perspective, cheekbone contour, volumetric depth |
| `top` | $0.0^\circ$ | $88.0^\circ$ | $50\text{ mm}$ | Shoulder breadth, cranial crown parting, clavicle curvature |
| `bottom` | $0.0^\circ$ | $-88.0^\circ$ | $50\text{ mm}$ | Footwear soles, claw beds, underbelly clearance, ground plane contact |
| `turntable_4views` | Batch Orbit | $0.0^\circ$ | $50\text{ mm}$ | Automated 4-angle turntable (`front` -> `side` -> `back` -> `side_left`) |

### 3. Anatomical Sub-Region Framing

When inspecting localized details, the rig shifts its focus center $\vec{C}$, framing radius $R$, and lens focal length $f$ dynamically. If an active Armature is present, bone head positions (`DEF-head`, `DEF-spine.002`, `DEF-hand.R`, `DEF-foot.R`) are resolved; otherwise, deterministic anthropometric height ratios are applied:

- **`head` / `portrait`**: Targets cranial apex ($Z \approx 88\%$ height), $R \approx 0.15 H$, $f = 85\text{ mm}$ portrait telephoto.
- **`torso` / `bodice`**: Targets mid-chest ($Z \approx 60\%$ height), $R \approx 0.25 H$, $f = 70\text{ mm}$ portrait mid-shot.
- **`hands` / `marionette`**: Targets wrist and fingers ($Z \approx 50\%$ height, $X = +0.35\text{ m}$ lateral offset), $R \approx 0.18 H$, $f = 85\text{ mm}$ macro.
- **`feet` / `sandals`**: Targets ground-contact plane ($Z \approx 8\%$ height), $R \approx 0.18 H$, $f = 70\text{ mm}$.
- **`full_body`**: Standard full-figure framing ($Z \approx 50\%$ height), $R = R_{\text{global}}$, $f = 50\text{ mm}$.

### 4. Diagnostic Shading Modes & Dual-Mode Capture Engine

To diagnose defects without noisy rendering cycles, the viewport capture pipeline supports dedicated diagnostic shading:

- **`SOLID` with `color_type='RANDOM'`**:
  Assigns a distinct pseudo-random pastel hue to every discrete mesh object in the scene. Immediately isolates garment layers, separate straps, eye corneas, teeth, and hair locks, exposing interpenetration that is invisible under standard uniform white clay shading.
- **`WIREFRAME`**:
  Renders black wireframe overlays, highlighting quad flow, non-manifold edges, tri poles, and polygon density distributions.
- **`MATERIAL`**:
  Evaluates real-time PBR material shaders, BaseColor textures, and normal perturbation via Blender's EEVEE viewport rasterizer.

#### Dual-Mode Capture Architecture:
1. **Interactive Viewport OpenGL Grab (`bpy.ops.render.opengl`)**:
   - Executes in **$<200\text{ ms}$** via `temp_override(area=VIEW_3D, region=WINDOW)`.
   - Temporarily strips viewport gizmos, floor grids, 3D cursor, and object selection outlines for pristine image output.
2. **Headless CLI Workbench Render Fallback (`bpy.ops.render.render`)**:
   - Executes in **$<0.7\text{ s}$** using Blender's native Workbench engine.
   - Automatically activates screen-space cavity shading (`shading.show_cavity = True`) to delineate creases and geometric seams.
   - Guaranteed to succeed in headless cloud servers, Docker containers, and CI environments without X11 or hardware OpenGL displays.

---

### 5. FastMCP Inspection Tools Reference

#### Tool: `morphomesh_setup_inspector_camera_rig`
Sets up or repositions the dedicated, non-destructive `MorphoMesh_Inspector_Camera` in Blender without altering existing artist cameras.

**Parameters**:
- `viewpoint` (*string*, default `"three_quarter"`): Canonical angle (`"front"`, `"side"`, `"back"`, `"three_quarter"`, `"top"`, `"bottom"`, `"head"`, `"hands"`, `"torso"`, `"feet"`).
- `target_center` (*list of 3 floats*, optional): Explicit `[x, y, z]` focus target. Auto-derived from character bounds if omitted.
- `sub_region` (*string*, optional): Anatomical sub-region (`"full_body"`, `"head"`, `"torso"`, `"hands"`, `"feet"`).
- `focal_length` (*float*, default `50.0`): Camera lens focal length in millimeters ($10.0$ to $300.0\text{ mm}$).
- `camera_name` (*string*, default `"MorphoMesh_Inspector_Camera"`): Object name of the inspector camera in Blender.
- `mesh_objects` (*list of strings*, optional): Names of mesh objects to bound. Auto-detects character meshes if omitted.
- `target_object` (*string*, optional): Name of specific character root object.
- `margin` (*float*, default `0.15`): Framing safety margin factor ($0.0$ to $1.0$).
- `resolution` (*list of 2 ints*, default `[1024, 1024]`): Target image resolution `[width, height]`.

**Output Schema**:
```json
{
  "status": "success",
  "camera_name": "MorphoMesh_Inspector_Camera",
  "viewpoint": "three_quarter",
  "focal_length": 50.0,
  "camera_location": [1.442, -1.442, 1.488],
  "camera_rotation": [1.143, 0.0, 0.785],
  "target_center": [0.0, 0.0, 0.825],
  "framing_distance": 2.039,
  "bounding_radius": 0.884,
  "bounding_box": {
    "min_point": [-0.35, -0.22, 0.0],
    "max_point": [0.35, 0.22, 1.65],
    "dimensions": [0.70, 0.44, 1.65]
  }
}
```

#### Tool: `morphomesh_capture_viewport`
Triggers immediate viewport capture through the active inspector camera, saving a PNG and returning metadata with inline base64 image data.

**Parameters**:
- `output_path` (*string*, optional): Destination path for the PNG file. If omitted, generates a temporary timestamped file.
- `camera_name` (*string*, default `"MorphoMesh_Inspector_Camera"`): Camera object to render through.
- `resolution` (*list of 2 ints*, default `[1024, 1024]`): Image resolution `[width, height]`.
- `shading_mode` (*string*, default `"SOLID"`): Shading mode (`"SOLID"`, `"FLAT"`, `"WIREFRAME"`, `"MATERIAL"`).
- `color_type` (*string*, default `"RANDOM"`): Color mode (`"RANDOM"`, `"MATERIAL"`, `"SINGLE"`, `"OBJECT"`).

**Output Schema**:
```json
{
  "status": "success",
  "image_path": "/tmp/morphomesh/viewport_7f8a12c4.png",
  "image_format": "png",
  "resolution": [1024, 1024],
  "shading_mode": "SOLID",
  "color_type": "RANDOM",
  "camera_name": "MorphoMesh_Inspector_Camera",
  "base64_preview": "iVBORw0KGgoAAAANSUhEUgAABAAAAAQACAIAAAD...",
  "capture_time_seconds": 0.142
}
```
```

---

### 2.4 Dedicated Section: `## Closed-Loop Visual Quality Critique (Auto-Critic QA)`

```markdown
---

## Closed-Loop Visual Quality Critique (Auto-Critic QA)

The **Auto-Critic QA Engine** ([`src/morphomesh/visual_critic.py`](src/morphomesh/visual_critic.py)) provides automated, closed-loop structural integrity inspection. Operating either interactively via Blender's `mathutils.bvhtree` or 100% offline via MorphoMesh's pure-Python spatial index (`PurePythonBVHTree`), the critic identifies subtle 3D modeling defects and returns machine-executable remediation plans.

```
+----------------------------------------------------------------------------------------------------+
|                                 AUTO-CRITIC QA EVALUATION WORKFLOW                                 |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|    1. BVH Penetration Check          2. Anthropometric Proportions                                 |
|    - Signed distance s_i < -0.5mm    - Head-to-body ratio (Nominal: 7.41 heroine)                  |
|    - Garment-body interpenetration   - Arm span & shoulder/hip breadth                             |
|    - Raycast skin burst detection    - Preset tolerance: +/- 10%                                   |
|                  |                                 |                                               |
|                  +----------------+----------------+                                               |
|                                   |                                                                |
|                                   v                                                                |
|    3. Rig Skinning Deformation       4. Hair Grooming Auditing                                     |
|    - Joint volume loss (rho_V < 0.7) - Submerged roots (>0.5mm inside skull)                       |
|    - Acute dihedral crease (< -0.85) - Detached floating roots (>2.0mm off)                        |
|    - Candy-wrapper pinching check    - Hair strand collision with garments                         |
|                                   |                                                                |
|                                   v                                                                |
|    [ Pydantic v2 Report ]  ---> [ Actionable Recommendations ] ---> [ Automated Remediation ]      |
|    Quality Score (0-100)        Shrinkwrap, Smooth, Anti-Pinch      Modifier Stacks & Weight Paint |
|                                                                                                    |
+----------------------------------------------------------------------------------------------------+
```

### 1. Four Core Structural QA Checks

#### A. BVH Signed Distance & Garment Penetration Detection
- **Geometric Principle**: Evaluates whether garment or armor meshes penetrate beneath the underlying body skin.
- **Signed Distance Formulation**: For each vertex $\vec{w}_i$ on garment geometry, queries the character body surface for the nearest triangle point $\vec{p}_i$ and outward unit normal $\hat{n}_i$:
  $$s_i = (\vec{w}_i - \vec{p}_i) \cdot \hat{n}_i$$
  A clearance violation is recorded whenever $s_i < -\text{clearance_tolerance}$ (default $0.0005\text{ m}$ or $0.5\text{ mm}$).
- **Skin Burst Detection**: Evaluates raycasting along surface normal directions to detect when body vertices bulge through outer layered geometry.

#### B. Anthropometric Body Proportion Analysis
- **Measurements**: Quantifies total model height, cranial height ($H_{\text{head}}$), arm span ($W_{\text{arm\_span}}$), shoulder breadth, and pelvic width.
- **Preset Calibration**: Compares measurements against anatomical standards:
  * `stylized_heroine`: Height $1.65\text{ m}$, Head Ratio $7.41 : 1$, Arm Span Ratio $1.00 : 1$, Shoulder-to-Hip $1.15 : 1$.
  * `realistic_female`: Height $1.68\text{ m}$, Head Ratio $7.50 : 1$, Arm Span Ratio $1.02 : 1$.
  * `heroic_male`: Height $1.85\text{ m}$, Head Ratio $8.00 : 1$, Arm Span Ratio $1.05 : 1$.
  * `chibi`: Height $1.00\text{ m}$, Head Ratio $3.50 : 1$, Arm Span Ratio $0.90 : 1$.
- Flags deviations exceeding $\pm 10\%$ as `PROPORTION` defects.

#### C. Rig Skinning Deformation & Joint Creasing
- **Volume Preservation Ratio**:
  $$\rho_V = \frac{V_{\text{posed}}}{V_0}$$
  Evaluates signed polyhedral volume of limbs during acute flexion poses (elbows bent $90^\circ$, knees bent $120^\circ$). Flags `SKINNING_PINCH` if volume collapses below $\rho_V < 0.70$ (candy-wrapper artifact).
- **Acute Dihedral Creasing**:
  Computes the cosine of the dihedral angle between adjacent polygon face normals:
  $$\cos\theta = \hat{n}_1 \cdot \hat{n}_2$$
  Flags acute pinching if $\cos\theta < -0.85$ (dihedral fold angle $> 148^\circ$).

#### D. Hair Grooming Curve Collision Audit
- Evaluates Geometry Nodes Hair Curve splines against scalp and garment surfaces:
  * **Submerged Roots**: Root point buried $> 0.5\text{ mm}$ beneath scalp surface.
  * **Detached Roots**: Root origin floating $> 2.0\text{ mm}$ off the emitter mesh.
  * **Garment Collisions**: Hair guide curves intersecting high-collar garments or shoulder armor.

---

### 2. Defect Hierarchy & Quality Scoring

Defects are categorized by severity:
- `CRITICAL`: Severe penetration ($> 5.0\text{ mm}$), catastrophic volume collapse ($> 50\%$), or inverted normals.
- `MAJOR`: Noticeable penetration ($1.0 - 5.0\text{ mm}$), proportion skew ($> 15\%$), or joint pinching.
- `MINOR`: Micro-clearance breach ($< 1.0\text{ mm}$), slight proportion variation ($10 - 15\%$), or stray curve roots.
- `INFO`: Non-breaking diagnostic observations and stylistic notices.

**Quality Score Formulation**:
$$\text{Quality Score} = \max\left(0.0, 100.0 - 25.0 \cdot N_{\text{critical}} - 10.0 \cdot N_{\text{major}} - 2.0 \cdot N_{\text{minor}}\right)$$
A model passes inspection (`passed = True`) when $N_{\text{critical}} = 0$ and the overall quality score exceeds $80.0$.

---

### 3. Actionable Recommendations Engine

Unlike generic linters that output passive warnings, MorphoMesh produces machine-actionable remediation instructions (`ActionableRecommendation`):

- **Shrinkwrap Offset Fix**:
  Prescribes an automated `Shrinkwrap` modifier targeting `Human_Base_Mesh` with mode `OUTSIDE_SURFACE` and offset $+0.005\text{ m}$ ($5\text{ mm}$) to immediately resolve garment clipping.
- **Laplacian Smooth Fix**:
  Prescribes a `LaplacianSmooth` modifier (factor $0.5$, iterations $4$) over creased joint vertex groups.
- **Armature Anti-Pinch Weight Recalculation**:
  Recommends re-weighting deform bones with dual-quaternion blending or volume-preserving helper bones.
- **Hair Comb & Puff Displacements**:
  Prescribes vector displacement of curve guide points along scalp normal vectors to clear intersecting armor.

---

### 4. FastMCP Tool: `morphomesh_critique_visual_quality`

Executes comprehensive structural QA and emits a fully typed diagnostic report.

**Parameters**:
- `character_name` (*string*, default `"MorphoMesh_Character"`): Name of the character root.
- `target_object` (*string*, optional): Primary body mesh name (default `"Human_Base_Mesh"`).
- `camera_angles` (*list of strings*, default `["front", "side", "three_quarter", "back"]`): Viewpoints evaluated.
- `clearance_tolerance` (*float*, default `0.0005`): Penetration clearance threshold in meters ($0.5\text{ mm}$).
- `target_preset` (*string*, default `"stylized_heroine"`): Anthropometric proportion preset.
- `evaluate_penetration` (*bool*, default `True`): Run BVH signed distance checks.
- `evaluate_proportions` (*bool*, default `True`): Run body proportion ratio checks.
- `evaluate_skinning` (*bool*, default `True`): Run skinning deformation and crease checks.
- `evaluate_grooming` (*bool*, default `True`): Run hair curve intersection checks.
- `capture_images` (*bool*, default `False`): Embed multi-angle viewport renders in report.

**Output Schema**:
```json
{
  "status": "success",
  "passed": false,
  "quality_score": 75.0,
  "defect_count": 2,
  "defects": [
    {
      "defect_id": "DEF-c48f21",
      "category": "PENETRATION",
      "severity": "MAJOR",
      "affected_objects": ["Dress_Bodice", "Human_Base_Mesh"],
      "description": "Garment penetration: 14 vertices beneath body surface (max depth 1.85mm).",
      "confidence": 0.98,
      "location": [0.0, 0.12, 1.15],
      "penetration_depth_mm": 1.85,
      "penetration_count": 14,
      "recommendation": {
        "action_id": "REC-7b19a2",
        "action": "APPLY_SHRINKWRAP_OFFSET",
        "target_objects": ["Dress_Bodice"],
        "suggested_modifier": "Shrinkwrap",
        "parameters": {
          "target": "Human_Base_Mesh",
          "wrap_method": "OUTSIDE_SURFACE",
          "offset": 0.005
        },
        "description": "Apply Shrinkwrap modifier with 5mm outward offset."
      }
    }
  ],
  "recommendations": [
    "Apply Shrinkwrap modifier to Dress_Bodice with target Human_Base_Mesh."
  ],
  "actionable_recommendations": [
    {
      "action_id": "REC-7b19a2",
      "action": "APPLY_SHRINKWRAP_OFFSET",
      "target_objects": ["Dress_Bodice"],
      "suggested_modifier": "Shrinkwrap",
      "parameters": {"target": "Human_Base_Mesh", "offset": 0.005}
    }
  ],
  "inspected_objects": ["Human_Base_Mesh", "Dress_Bodice", "Hair_Curves"],
  "scene_stats": {
    "total_vertices": 14820,
    "total_faces": 14612,
    "quad_percentage": 99.2,
    "character_height_m": 1.652,
    "head_ratio": 7.41
  },
  "evaluated_angles": ["front", "side", "three_quarter", "back"],
  "execution_time_seconds": 0.38
}
```

---

### 5. Environment Variable Gating & Backward Compatibility

To maintain 100% backward compatibility with legacy test suites that assert exactly 7 registered FastMCP tools (e.g., `tests/test_tools_schema.py`), inspection tools are feature-flagged:

```bash
# Enable Inspection & Viewport Capture Tools in FastMCP server
export MORPHOMESH_INCLUDE_INSPECTION_TOOLS=1

# Or enable all extended tools (Inspection + Digital Human)
export MORPHOMESH_INCLUDE_ALL_TOOLS=1
```

In `mcp_config.json` for Google Antigravity 2.0:
```json
{
  "mcpServers": {
    "morphomesh": {
      "command": "morphomesh",
      "args": ["server", "--transport", "stdio"],
      "env": {
        "MORPHOMESH_INCLUDE_INSPECTION_TOOLS": "1"
      }
    }
  }
}
```
When this variable is omitted or set to `0`, `mcp.list_tools()` strictly returns the 7 canonical creature tools, ensuring continuous zero-regression across legacy workflows.
```

---

## 3. Full Repository Regression Test Matrix

### 3.1 Milestone Test Inventory & Coverage Map

| Milestone | Test Module | Test Count | Scope & Verification Invariants |
|---|---|:---:|---|
| **M1** | `tests/test_bridge_socket_parity.py` | 21 | Socket connection lifecycle, NDJSON chunking, timer immortality barrier, bridge dispatch parity |
| **M1** | `tests/test_m1_adversarial_socket.py` | 34 | Rapid reconnection storms, saturated buffers, socket error handling |
| **M1** | `tests/test_adversarial_dispatch_m1_2.py` | 58 | High-throughput concurrent dispatch, execution latency, non-blocking timers |
| **M1** | `tests/test_blender_bridge.py` | 23 | Bridge IPC serialization, security sandbox, headless fallback |
| **M1** | `tests/test_tools_schema.py` | 31 | Strict 7-tool legacy schema conformance and input parameter validation |
| **M2** | `tests/test_inspector_camera.py` | 40 | Hierarchical AABB bounds, analytical framing math d = R/sin(alpha) * (1+margin), 6 viewpoints, 5 sub-regions |
| **M2** | `tests/test_multiview_rendering.py` | 24 | Single & batch capture, diagnostic shading (`SOLID` random, `WIREFRAME`), dual-mode OpenGL/Workbench fallback |
| **M2** | `tests/test_adversarial_camera_math.py` | 35 | Extreme aspect ratios (100:1, 0.001), inverted scales, zero-volume degenerate geometry |
| **M2** | `tests/test_adversarial_viewport_capture.py` | 36 | Corrupted render paths, headless display simulation, context override recovery |
| **M3** | `tests/test_visual_critic.py` | 28 | PurePythonBVHTree, Eberly closest point, 4 defect injection fixtures, >95% benchmark accuracy, Pydantic schemas |
| **M3** | `tests/test_adversarial_bvh_penetration.py` | 33 | Coplanar triangle intersections, degenerate faces, sub-millimeter tolerances |
| **M3** | `tests/test_adversarial_critic_benchmark.py` | 48 | Adversarial defect injections, false-positive resistance, metric validation |
| **M4** | `tests/test_fastmcp_inspection_tools.py` | ~20 | FastMCP registration under MORPHOMESH_INCLUDE_INSPECTION_TOOLS=1, input validation, direct & protocol calls, 7-tool gating |
| **Human** | `tests/test_fastmcp_human_tools.py` | 12 | Digital human FastMCP tool schemas, bounds, and execution |
| **Human** | `tests/test_human_generator.py` | 15 | Quad body geometry, 29 vertex groups, anthropometric landmarks |
| **Human** | `tests/test_human_rigging.py` | 20 | Rigify Metarig 163 DEF bones, anti-pinch bone weighting |
| **Human** | `tests/test_human_materials.py` | 18 | Dual-layer SSS, 2-chamber eye refraction, PBR Principled BSDF v2 |
| **Human** | `tests/test_human_grooming.py` | 16 | 6 hair curve layers (hime bangs, sidelocks, back cascade), ribbon export |
| **Human** | `tests/test_wardrobe.py` | 15 | White strap dress, 20-pleat skirt, marionette strings, glowing butterflies |
| **Human** | `tests/test_character_assembler.py` | 25 | Master assembly orchestrator, 7-tier collection hierarchy, AgX color |
| **Human** | `tests/test_production_exports.py` | 22 | Production FBX (163 DEF bones, 52 ARKit keys), glTF GLB, 4K PBR texture maps |
| **Core** | `tests/test_connectors.py` | 28 | TRELLIS, SMAL, anyCreature, MeshAnything, Hunyuan3D connectors |
| **Core** | `tests/test_inference_adapter.py` | 16 | Offline procedural generator, circuit breaker fallback |
| **Bear** | `tests/test_anatomy_generator.py` | 14 | Ursine/quadruped anatomy, plantigrade foot pads, curved claws |
| **Bear** | `tests/test_bear_anatomy.py` | 12 | Production bear claw orientation vectors, articulated facial geometry |
| **Bear** | `tests/test_grooming.py` | 15 | Volumetric hair curves, dual-coat undercoat/guard hairs |
| **Bear** | `tests/test_materials_and_armor.py` | 16 | Keratin shaders, segmented war armor plates, pauldron clearance |
| **Cross** | Additional Adversarial Suites | ~100 | Challenger empirical audits, geometry stress tests, socket stress |

---

### 3.2 Authoritative Verification Commands

#### Suite 1: Milestone 1-4 Core Inspection & Tool Verification (Fast, ~45s)
Verifies camera math, multiview rendering, visual critic, bridge socket parity, and tool schemas:
```bash
pytest \
  tests/test_inspector_camera.py \
  tests/test_multiview_rendering.py \
  tests/test_visual_critic.py \
  tests/test_bridge_socket_parity.py \
  tests/test_tools_schema.py \
  tests/test_adversarial_camera_math.py \
  tests/test_adversarial_viewport_capture.py \
  tests/test_adversarial_bvh_penetration.py \
  tests/test_adversarial_critic_benchmark.py \
  tests/test_m1_adversarial_socket.py \
  tests/test_adversarial_dispatch_m1_2.py \
  -v
```
*Expected Result: 388 passed, 3 skipped, 0 failures (100% pass rate).*

#### Suite 2: Backward-Compatibility Gating Verification
Verifies that when extended tool flags are absent, exactly 7 canonical tools are exposed:
```bash
# Unset all tool gating environment flags
export MORPHOMESH_INCLUDE_INSPECTION_TOOLS=0
export MORPHOMESH_INCLUDE_HUMAN_TOOLS=0
pytest tests/test_tools_schema.py -v
```
*Expected Result: 31 passed, 0 failures.*

#### Suite 3: Extended Tool Discovery Verification
Verifies that inspection tools are registered when the feature flag is activated:
```bash
export MORPHOMESH_INCLUDE_INSPECTION_TOOLS=1
pytest tests/test_fastmcp_inspection_tools.py -v
```
*Expected Result: All inspection tool discovery, schema, and execution tests pass.*

#### Suite 4: Full Repository Master Regression Suite
Executes all unit, integration, procedural, and adversarial test suites across the entire repository:
```bash
pytest tests/ -v --durations=10
```
*Expected Result: >1,000 passed tests, 0 failures across the entire repository.*
