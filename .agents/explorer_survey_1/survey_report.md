# MorphoMesh Survey Report: R1 FastMCP Tools Integration & Compatibility

**Investigator**: Explorer Survey (`explorer_survey_1`)  
**Target Milestone**: R1: FastMCP Tools Integration & Compatibility  
**Authoritative Reference**: `ORIGINAL_REQUEST.md` (## 2026-09-08T16:06:11Z)  
**Workspace Root**: `E:\tool\mcp\MorphoMesh`  
**Date**: 2026-09-08  

---

## Executive Summary

MorphoMesh's Model Context Protocol (MCP) server layer implements **17 production tools** organized into **3 distinct functional suites**:
1. **Creature Pipeline (7 tools)**: Canonical prompt-to-render procedural/AI creature generation workflow.
2. **Human & Wardrobe Generation (7 tools)**: Anatomically authentic female human modeling, 163-DEF bone metarigging, PBR SSS shaders, hair curves, and dynamic wardrobe generation.
3. **Inspection & Visual QA (3 tools)**: Analytical camera positioning rig, sub-200ms multi-shading viewport capture, and closed-loop automated structural defect critique.

All 17 tools are declared and registered via FastMCP (`@mcp.tool`) in `src/morphomesh/server.py`. An environment variable gating mechanism dynamically filters tool discovery across both high-level Python APIs (`mcp.list_tools()`) and low-level JSON-RPC protocol requests (`ListToolsRequest`), ensuring **100% backward compatibility** (exactly 7 canonical creature tools returned when flags are unset).

Empirical verification confirms **347/347 tests PASSING** across all tool integration, schema validation, socket parity, and adversarial gating test suites with **0 failures and 0 regressions**.

---

## 1. Existing Tool Registration Architecture in `server.py` & `morphomesh/`

### 1.1 Architecture & Server Location
- **Authoritative Server Path**: `src/morphomesh/server.py` (the repository does not maintain a top-level `server.py`; the package layout adheres strictly to standard `src/morphomesh` packaging declared in `pyproject.toml`).
- **Server Instance**: FastMCP instance instantiated as:
  ```python
  mcp = FastMCP(
      name="MorphoMeshServer",
      instructions=(
          "Authoritative 3D creature generation pipeline and Blender bridge. "
          "Coordinates prompt engineering, image-to-3D diffusion, quad retopology, "
          "biomechanical auto-rigging, scene assembly, and EEVEE Next turntable rendering."
      ),
      host=os.environ.get("MORPHOMESH_HOST", "127.0.0.1"),
      port=int(os.environ.get("MORPHOMESH_PORT", "8765")),
  )
  ```
- **CLI Dispatcher**: Invoked via `src/morphomesh/main.py` (`morphomesh server` or `morphomesh-server`).

### 1.2 Tool Registration Catalog (17 Authoritative Tools)

| # | Tool Name | Suite | Decorator Line in `server.py` | Core Underlying Module | Input Schema Model | Output Schema Model |
|---|---|---|---|---|---|---|
| 1 | `morphomesh_generate_concept` | Creature | Line 92 | `inference_adapter.py` | `GenerateConceptInput` | `GenerateConceptOutput` |
| 2 | `morphomesh_create_3d_asset` | Creature | Line 152 | `inference_adapter.py` + `connectors/` | `Create3DAssetInput` | `Create3DAssetOutput` |
| 3 | `morphomesh_optimize_topology` | Creature | Line 220 | `blender_bridge.py` + `meshanything_connector.py` | `OptimizeTopologyInput` | `OptimizeTopologyOutput` |
| 4 | `morphomesh_auto_rig` | Creature | Line 311 | `blender_bridge.py` + `animals3d_connector.py` | `AutoRigInput` | `AutoRigOutput` |
| 5 | `morphomesh_blender_execute` | Creature | Line 441 | `blender_bridge.py` (AST sandbox) | `BlenderExecuteInput` | `BlenderExecuteOutput` |
| 6 | `morphomesh_get_scene_status` | Creature | Line 485 | `blender_bridge.py` | `SceneStatusInput` | `SceneStatusOutput` |
| 7 | `morphomesh_render_preview` | Creature | Line 524 | `blender_bridge.py` | `RenderPreviewInput` | `RenderPreviewOutput` |
| 8 | `morphomesh_create_human_asset` | Human | Line 607 | `blender_bridge.py` + `human_generator.py` | `CreateHumanAssetInput` | `CreateHumanAssetOutput` |
| 9 | `morphomesh_auto_rig_human` | Human | Line 715 | `blender_bridge.py` + `human_rigging.py` | `AutoRigHumanInput` | `AutoRigHumanOutput` |
| 10 | `morphomesh_setup_human_materials` | Human | Line 778 | `blender_bridge.py` + `human_materials.py` | `SetupHumanMaterialsInput` | `SetupHumanMaterialsOutput` |
| 11 | `morphomesh_groom_human` | Human | Line 841 | `blender_bridge.py` + `human_grooming.py` | `GroomHumanInput` | `GroomHumanOutput` |
| 12 | `morphomesh_dress_human` | Human | Line 912 | `blender_bridge.py` + `wardrobe.py` | `DressHumanInput` | `DressHumanOutput` |
| 13 | `morphomesh_assemble_master_character` | Human | Line 983 | `blender_bridge.py` + `character_assembler.py` | Direct kwargs / bridge dict | Direct kwargs / bridge dict |
| 14 | `morphomesh_export_production_character` | Human | Line 1042 | `character_assembler.py` + `export_manager.py` | Direct kwargs / export dict | Direct kwargs / export dict |
| 15 | `morphomesh_setup_inspector_camera_rig` | Inspection | Line 1119 | `blender_bridge.py` + `camera_rig.py` | `SetupInspectorCameraInput`* | `SetupInspectorCameraOutput`* |
| 16 | `morphomesh_capture_viewport` | Inspection | Line 1208 | `blender_bridge.py` + `camera_rig.py` | `CaptureViewportInput`* | `CaptureViewportOutput`* |
| 17 | `morphomesh_critique_visual_quality` | Inspection | Line 1345 | `blender_bridge.py` + `visual_critic.py` | `VisualCritiqueInput`* | `VisualCritiqueOutput`* |

*\*Note: Marked schemas exist in `morphomesh.models` but are currently validated manually in `server.py` rather than directly imported.*

---

## 2. Detailed Technical Specification of the 3 Tool Suites

### 2.1 Suite A: Creature Pipeline (7 Tools)

1. **`morphomesh_generate_concept`**
   - **Signature**:
     ```python
     async def morphomesh_generate_concept(
         prompt: str,
         negative_prompt: str = "",
         creature_type: str = "custom",
         view_mode: str = "front",
         pose: str = "standing_neutral",
         style: str = "realistic",
         background: str = "white_neutral",
         width: int = 1024,
         height: int = 1024,
         seed: int = -1,
         output_format: str = "png",
         backend: str = "default",
         ctx: Optional[Context] = None,
     ) -> Dict[str, Any]
     ```
   - **Implementation**: Wraps `inference_adapter.generate_concept(req)`.
   - **Inputs/Outputs**: Validates via `GenerateConceptInput` (min length 3, width/height in [512, 2048] step 64). Returns `GenerateConceptOutput` (`concept_id`, `image_path`, `alpha_mask_path`, `enhanced_prompt`).

2. **`morphomesh_create_3d_asset`**
   - **Signature**:
     ```python
     async def morphomesh_create_3d_asset(
         image_path: Optional[str] = None,
         concept_id: Optional[str] = None,
         prompt: Optional[str] = None,
         model_backend: str = "mock",
         export_format: str = "glb",
         generate_pbr: bool = True,
         texture_resolution: int = 2048,
         remove_background: bool = True,
         guidance_scale: float = 7.5,
         seed: int = -1,
         quality_tier: Optional[str] = "standard",
         backend: Optional[str] = None,
         ctx: Optional[Context] = None,
     ) -> Dict[str, Any]
     ```
   - **Implementation**: Dispatches to `inference_adapter.generate_3d_asset(req)` supporting backends: `meshy`, `tripo`, `trellis`, `hunyuan`, `anycreature`, `mock`.
   - **Inputs/Outputs**: Validates via `Create3DAssetInput`. Returns `Create3DAssetOutput` (`asset_id`, `mesh_path`, `vertex_count`, `face_count`, PBR texture paths).

3. **`morphomesh_optimize_topology`**
   - **Signature**:
     ```python
     async def morphomesh_optimize_topology(
         asset_id: Optional[str] = None,
         input_mesh_path: Optional[str] = None,
         target_poly_count: int = 10000,
         topology_type: str = "quad_dominant",
         preserve_uvs: bool = True,
         preserve_sharp_edges: bool = True,
         method: str = "quadriflow",
         output_format: str = "glb",
         ctx: Optional[Context] = None,
     ) -> Dict[str, Any]
     ```
   - **Implementation**: Routes neural retopology (`method="meshanything_v2"`) via `inference_adapter.optimize_topology_with_connector`, otherwise delegates to `blender_bridge.optimize_topology` (Blender QuadriFlow).
   - **Inputs/Outputs**: Validates via `OptimizeTopologyInput`. Returns `OptimizeTopologyOutput` (`optimized_face_count`, `quad_percentage`, `reduction_ratio`).

4. **`morphomesh_auto_rig`**
   - **Signature**:
     ```python
     async def morphomesh_auto_rig(
         asset_id: Optional[str] = None,
         input_mesh_path: Optional[str] = None,
         creature_type: str = "quadruped",
         rig_type: str = "rigify_creature",
         skinning_method: str = "automatic_weights",
         symmetry: bool = True,
         generate_test_animation: bool = True,
         load_into_scene: bool = True,
         ctx: Optional[Context] = None,
     ) -> Dict[str, Any]
     ```
   - **Implementation**: Routes SMAL/parametric animal models to `inference_adapter.create_animal_rig_with_connector` or executes `blender_bridge.create_armature`.
   - **Inputs/Outputs**: Validates via `AutoRigInput`. Returns `AutoRigOutput` (`armature_name`, `bone_count`, `bone_hierarchy`, `smal_landmarks`, `rigify_mapping`).

5. **`morphomesh_blender_execute`**
   - **Signature**:
     ```python
     async def morphomesh_blender_execute(
         script: str,
         timeout_seconds: int = 30,
         target_scene: Optional[str] = None,
         save_after: bool = False,
         save_path: Optional[str] = None,
         return_variables: Optional[List[str]] = None,
         ctx: Optional[Context] = None,
     ) -> Dict[str, Any]
     ```
   - **Implementation**: Two-tier AST security sandbox inspection via `BpyCodeValidator` before dispatching to Blender main loop.
   - **Inputs/Outputs**: Validates non-empty code. Returns `BlenderExecuteOutput` (`stdout`, `stderr`, `returned_variables`).

6. **`morphomesh_get_scene_status`**
   - **Signature**:
     ```python
     async def morphomesh_get_scene_status(
         scene_name: Optional[str] = None,
         include_mesh_stats: bool = True,
         include_hierarchy: bool = True,
         include_materials: bool = True,
         include_armatures: bool = True,
         include_cameras_lights: bool = True,
         ctx: Optional[Context] = None,
     ) -> Dict[str, Any]
     ```
   - **Implementation**: Queries Blender scene graph via `blender_bridge.get_scene_status`.
   - **Inputs/Outputs**: Validates via `SceneStatusInput`. Returns `SceneStatusOutput` (`objects`, `vertex_count`, `armatures`, `cameras`, `lights`).

7. **`morphomesh_render_preview`**
   - **Signature**:
     ```python
     async def morphomesh_render_preview(
         camera_name: Optional[str] = None,
         resolution_width: int = 1024,
         resolution_height: int = 1024,
         render_engine: str = "BLENDER_EEVEE",
         samples: int = 64,
         view_angle: str = "three_quarter",
         transparent_background: bool = True,
         lighting_preset: str = "studio_three_point",
         save_to_disk: bool = True,
         output_dir: Optional[str] = None,
         ctx: Optional[Context] = None,
     ) -> Dict[str, Any]
     ```
   - **Implementation**: Directs EEVEE or Cycles turntable render via `blender_bridge.render_preview` and injects base64 preview payload.
   - **Inputs/Outputs**: Validates via `RenderPreviewInput`. Returns `RenderPreviewOutput` (`image_path`, `base64_image`, `render_time_seconds`).

---

### 2.2 Suite B: Human & Wardrobe Generation (7 Tools)

8. **`morphomesh_create_human_asset`**
   - **Signature**:
     ```python
     async def morphomesh_create_human_asset(
         character_name: str = "Yu_Nian_An",
         prompt: str = "Yu Nian An female semi-realistic character",
         gender: str = "female",
         height: float = 1.65,
         head_ratio: float = 7.41,
         style: str = "stylized_photorealism",
         chest_girth: float = 0.82,
         waist_girth: float = 0.58,
         hip_girth: float = 0.86,
         poly_budget: int = 25000,
         include_blendshapes: bool = True,
         export_format: str = "glb",
         load_into_scene: bool = True,
         assemble_master: bool = False,
         config: Optional[HumanAnatomyConfig] = None,
         ctx: Optional[Context] = None,
     ) -> Dict[str, Any]
     ```
   - **Implementation**: Generates anatomically accurate female body mesh with teardrop bust, lumbar curvature, 5-toed feet, and 52 ARKit blendshapes via `human_generator.py` and `blender_bridge.create_human_asset`. Supports `assemble_master=True` full orchestrator passthrough.

9. **`morphomesh_auto_rig_human`**
   - **Signature**:
     ```python
     async def morphomesh_auto_rig_human(
         human_asset_id: Optional[str] = None,
         mesh_object_name: str = "Human_Base_Mesh",
         target_object: Optional[str] = None,
         rig_type: str = "rigify_human",
         skinning_method: str = "automatic_weights",
         include_face_rig: bool = True,
         include_finger_rig: bool = True,
         pose: str = "puppeteer_pose",
         export_format: str = "fbx",
         ctx: Optional[Context] = None,
     ) -> Dict[str, Any]
     ```
   - **Implementation**: Snaps 163 DEF Rigify metarig bones with anatomical pre-bends (elbows +Y, knees -Y) and anti-pinch geodesic skin weights via `human_rigging.py`.

10. **`morphomesh_setup_human_materials`**
    - **Signature**:
      ```python
      async def morphomesh_setup_human_materials(
          mesh_object_name: str = "Human_Base_Mesh",
          target_object: Optional[str] = None,
          material_preset: str = "yu_nian_an",
          skin_tone: str = "porcelain_fair",
          subsurface_scattering: bool = True,
          refractive_eyes: bool = True,
          render_engine: str = "CYCLES",
          save_after: bool = False,
          save_path: Optional[str] = None,
          ctx: Optional[Context] = None,
      ) -> Dict[str, Any]
      ```
    - **Implementation**: Configures Principled BSDF v2 shaders with Random Walk SSS (radii [1.0, 0.22, 0.11]) and dual-chamber refractive optics via `human_materials.py`.

11. **`morphomesh_groom_human`**
    - **Signature**:
      ```python
      async def morphomesh_groom_human(
          mesh_object_name: str = "Human_Base_Mesh",
          target_object: Optional[str] = None,
          hair_style: str = "hime_cut_long",
          hairstyle: Optional[str] = None,
          hair_color: str = "silky_black",
          strand_count: int = 15000,
          include_eyebrows: bool = True,
          include_eyelashes: bool = True,
          generate_ribbons: bool = False,
          save_after: bool = False,
          save_path: Optional[str] = None,
          ctx: Optional[Context] = None,
      ) -> Dict[str, Any]
      ```
    - **Implementation**: Builds 6-strata Geometry Nodes hair curves (eyebrows, eyelashes, blunt bangs, sidelocks, parting, back cascades) with Melanin shading via `human_grooming.py`.

12. **`morphomesh_dress_human`**
    - **Signature**:
      ```python
      async def morphomesh_dress_human(
          human_object_name: str = "Human_Base_Mesh",
          target_object: Optional[str] = None,
          outfit: str = "yu_nian_an_dress",
          outfit_preset: Optional[str] = None,
          include_sandals: bool = True,
          include_red_threads: bool = True,
          include_glowing_butterflies: bool = True,
          butterfly_count: int = 10,
          clearance_offset: float = 0.015,
          save_after: bool = False,
          save_path: Optional[str] = None,
          ctx: Optional[Context] = None,
      ) -> Dict[str, Any]
      ```
    - **Implementation**: Fits slip sundress, conforming sash belt, flat 10-toe sandals, 10 crimson marionette cords, and 10 luminous butterflies via `wardrobe.py`.

13. **`morphomesh_assemble_master_character`**
    - **Signature**:
      ```python
      async def morphomesh_assemble_master_character(
          character_name: str = "Yu_Nian_An",
          height: float = 1.65,
          head_ratio: float = 7.41,
          include_hair: bool = True,
          include_wardrobe: bool = True,
          include_props: bool = True,
          include_armature: bool = True,
          include_lighting: bool = True,
          render_engine: str = "CYCLES",
          samples: int = 128,
          save_blend: bool = True,
          output_path: Optional[str] = None,
          ctx: Optional[Context] = None,
      ) -> Dict[str, Any]
      ```
    - **Implementation**: Orchestrates master character assembly across all 7 collection hierarchies and saves `Yu_Nian_An_Master.blend` via `character_assembler.py`.

14. **`morphomesh_export_production_character`**
    - **Signature**:
      ```python
      async def morphomesh_export_production_character(
          character_name: str = "Yu_Nian_An",
          blend_path: Optional[str] = None,
          output_dir: Optional[str] = None,
          export_fbx: bool = True,
          export_glb: bool = True,
          generate_textures: bool = True,
          generate_docs: bool = True,
          texture_resolution: int = 4096,
          ctx: Optional[Context] = None,
      ) -> Dict[str, Any]
      ```
    - **Implementation**: Packages rigged FBX, glTF 2.0 GLB, and 4K PBR textures (BaseColor, Normal, Roughness, Metallic, SSS, Alpha, Height) via `export_manager.py`.

---

### 2.3 Suite C: Inspection & Visual QA (3 Tools)

15. **`morphomesh_setup_inspector_camera_rig`**
    - **Exposure in `server.py`**: Declared at line 1119.
    - **Signature**:
      ```python
      async def morphomesh_setup_inspector_camera_rig(
          viewpoint: str = "three_quarter",
          target_center: Optional[List[float]] = None,
          sub_region: Optional[str] = None,
          focal_length: float = 50.0,
          camera_name: str = "MorphoMesh_Inspector_Camera",
          mesh_objects: Optional[List[str]] = None,
          ctx: Optional[Context] = None,
      ) -> Dict[str, Any]
      ```
    - **Parameters**:
      * `viewpoint` (str, default `"three_quarter"`): Target canonical viewing perspective (`front`, `side`, `back`, `three_quarter`, `top`, `bottom`, `head`, `hands`, `torso`, `feet`, `turntable_4views`).
      * `target_center` (Optional[List[float]], default `None`): 3-element `[x, y, z]` focus coordinates.
      * `sub_region` (Optional[str], default `None`): Anatomical region (`full_body`, `head`, `torso`, `hands`, `feet`).
      * `focal_length` (float, default `50.0`): Camera focal length in mm ($10.0$ to $300.0\text{ mm}$).
      * `camera_name` (str, default `"MorphoMesh_Inspector_Camera"`): Camera object identifier.
      * `mesh_objects` (Optional[List[str]], default `None`): Target character mesh object names.
    - **Returns**: Dictionary with `status`, `camera_name`, `viewpoint`, `focal_length`, `camera_location`, `camera_rotation`, `target_center`, `framing_distance`, `bounding_radius`, `bounding_box`.
    - **Offline Fallback**: Seamlessly falls back to `camera_rig.py:setup_inspector_camera` pure-Python mathematical solver when Blender socket is offline.

16. **`morphomesh_capture_viewport`**
    - **Exposure in `server.py`**: Declared at line 1208.
    - **Signature**:
      ```python
      async def morphomesh_capture_viewport(
          output_path: Optional[str] = None,
          camera_name: str = "MorphoMesh_Inspector_Camera",
          resolution: List[int] = [1024, 1024],
          shading_mode: str = "SOLID",
          color_type: str = "RANDOM",
          ctx: Optional[Context] = None,
      ) -> Dict[str, Any]
      ```
    - **Parameters**:
      * `output_path` (Optional[str], default `None`): Output destination PNG path.
      * `camera_name` (str, default `"MorphoMesh_Inspector_Camera"`): Name of camera to capture through.
      * `resolution` (List[int], default `[1024, 1024]`): Width and height pixel dimensions.
      * `shading_mode` (str, default `"SOLID"`): Mode from `{"SOLID", "FLAT", "WIREFRAME", "MATERIAL", "RENDERED"}`.
      * `color_type` (str, default `"RANDOM"`): Color scheme from `{"RANDOM", "MATERIAL", "SINGLE", "OBJECT", "TEXTURE"}`.
    - **Returns**: Dictionary with `status`, `image_path`, `resolution`, `shading_mode`, `color_type`, `camera_name`, `base64_preview`, `capture_time_seconds`.
    - **Offline Fallback**: Generates a valid 1x1 transparent PNG (`FALLBACK_PNG_BYTES` in `camera_rig.py`) and encodes to `base64_preview` when Blender is offline.

17. **`morphomesh_critique_visual_quality`**
    - **Exposure in `server.py`**: Declared at line 1345.
    - **Signature**:
      ```python
      async def morphomesh_critique_visual_quality(
          character_name: str = "MorphoMesh_Character",
          target_object: Optional[str] = None,
          camera_angles: Optional[List[str]] = None,
          clearance_tolerance: float = 0.0005,
          target_preset: str = "stylized_heroine",
          ctx: Optional[Context] = None,
      ) -> Dict[str, Any]
      ```
    - **Parameters**:
      * `character_name` (str, default `"MorphoMesh_Character"`): Character hierarchy root name.
      * `target_object` (Optional[str], default `None`): Primary target body mesh name.
      * `camera_angles` (Optional[List[str]], default `None`): Viewpoints evaluated (defaults to `["front", "side", "three_quarter", "back"]`).
      * `clearance_tolerance` (float, default `0.0005`): Penetration clearance threshold ($0.5\text{ mm}$).
      * `target_preset` (str, default `"stylized_heroine"`): Anthropometric preset (`realistic_human`, `stylized_heroine`, `chibi_petite`, `realistic_female`, `heroic_male`, `chibi`).
    - **Returns**: Diagnostic report containing `status`, `passed`, `quality_score` (0-100), `defect_count`, `defects` (list of `DefectItem`), `recommendations` (list of strings), `actionable_recommendations` (list of `ActionableRecommendation`), `inspected_objects`, `scene_stats`, `evaluated_angles`.
    - **Underlying Engine**: Operates via `blender_bridge.py:critique_visual_quality` or `visual_critic.py:run_visual_critique` using pure-Python spatial trees (`PurePythonBVHTree`) when Blender is offline.

---

## 3. Environment Variable Gating Mechanism & Backward Compatibility

### 3.1 Gating Implementation Architecture
In `src/morphomesh/server.py` (lines 1426–1504):
```python
CREATURE_TOOL_NAMES = {
    "morphomesh_generate_concept",
    "morphomesh_create_3d_asset",
    "morphomesh_optimize_topology",
    "morphomesh_auto_rig",
    "morphomesh_blender_execute",
    "morphomesh_get_scene_status",
    "morphomesh_render_preview",
}  # 7 tools

HUMAN_TOOL_NAMES = {
    "morphomesh_create_human_asset",
    "morphomesh_auto_rig_human",
    "morphomesh_setup_human_materials",
    "morphomesh_groom_human",
    "morphomesh_dress_human",
    "morphomesh_assemble_master_character",
    "morphomesh_export_production_character",
}  # 7 tools

INSPECTION_TOOL_NAMES = {
    "morphomesh_setup_inspector_camera_rig",
    "morphomesh_capture_viewport",
    "morphomesh_critique_visual_quality",
}  # 3 tools

ALL_TOOL_NAMES = CREATURE_TOOL_NAMES | HUMAN_TOOL_NAMES | INSPECTION_TOOL_NAMES  # 17 tools
```

### 3.2 Gating Resolution Logic
```python
def _get_active_allowed_tool_names() -> set[str]:
    """Resolve allowed tool names based on environment flags."""
    all_flag = os.environ.get("MORPHOMESH_INCLUDE_ALL_TOOLS", "").strip().lower()
    if all_flag in ("1", "true", "yes", "all"):
        return ALL_TOOL_NAMES

    allowed = set(CREATURE_TOOL_NAMES)
    human_flag = os.environ.get("MORPHOMESH_INCLUDE_HUMAN_TOOLS", "").strip().lower()
    if human_flag in ("1", "true", "yes", "all"):
        allowed |= HUMAN_TOOL_NAMES

    insp_flag = os.environ.get("MORPHOMESH_INCLUDE_INSPECTION_TOOLS", "").strip().lower()
    if insp_flag in ("1", "true", "yes", "all"):
        allowed |= INSPECTION_TOOL_NAMES

    return allowed
```

### 3.3 Two-Tier Protocol Interception
1. **High-Level FastMCP Interception**:
   `mcp.list_tools = _filtered_list_tools` filters the registered tool list returned to high-level callers.
2. **Low-Level JSON-RPC Interception**:
   Wraps `mcp._mcp_server.request_handlers[mcp_types.ListToolsRequest]` to intercept raw protocol discovery packets, guaranteeing that external MCP clients (such as Google Antigravity, Claude Desktop, or custom JSON-RPC clients over stdio/SSE) receive only the active allowed schemas.

### 3.4 Gating Matrix Permutations & Backward Compatibility Guarantees

| `MORPHOMESH_INCLUDE_ALL_TOOLS` | `MORPHOMESH_INCLUDE_HUMAN_TOOLS` | `MORPHOMESH_INCLUDE_INSPECTION_TOOLS` | Discovered Tools Count | Active Discovered Sets | Backward Compatibility Status |
|---|---|---|---|---|---|
| *Unset / 0* | *Unset / 0* | *Unset / 0* | **7** | `CREATURE_TOOL_NAMES` | **Default Mode**: 100% legacy compatible with `test_tools_schema.py`. Zero tool leakage. |
| *Unset / 0* | *Unset / 0* | `1` / `true` | **10** | `CREATURE` + `INSPECTION` | Dedicated visual QA mode. |
| *Unset / 0* | `1` / `true` | *Unset / 0* | **14** | `CREATURE` + `HUMAN` | Dedicated character pipeline mode. |
| *Unset / 0* | `1` / `true` | `1` / `true` | **17** | `ALL_TOOL_NAMES` | Dual enabled mode. |
| `1` / `true` | *Any* | *Any* | **17** | `ALL_TOOL_NAMES` | Full production mode. Overrides individual flags. |

### 3.5 Direct Invocation Resilience (`mcp.call_tool`)
The gating filter specifically controls **tool discovery** (`tools/list` / `ListToolsRequest`). Direct tool invocation via `mcp.call_tool("tool_name", ...)` remains fully active for all 17 tools regardless of environment flags. This ensures agents with static knowledge can invoke tools directly without breaking schema discovery constraints.

---

## 4. Gap Analysis: Imports, Schema Definitions & Tool Wrappers in `server.py`

### 4.1 Missing Top-Level Schema Imports
In `src/morphomesh/server.py` (lines 25–57), the module imports models for creature and human tools, but **omits** the inspection models defined in `src/morphomesh/models.py`:
- **Defined in `models.py` but NOT imported in `server.py`**:
  * `SetupInspectorCameraInput` (line 717)
  * `SetupInspectorCameraOutput` (line 741)
  * `CaptureViewportInput` (line 757)
  * `CaptureViewportOutput` (line 793)
  * `VisualCritiqueInput` (line 1067)
  * `VisualCritiqueOutput` (line 1126)
  * `BoundingBox3D` (line 708)
  * `DefectItem` (line 969)
  * `DefectSeverity` (line 861)
  * `DefectCategory` (line 888)
  * `ActionableRecommendation` (line 923)

### 4.2 Inconsistent Validation Patterns
- In creature tools (e.g. `morphomesh_generate_concept`, `morphomesh_create_3d_asset`) and human tools (e.g. `morphomesh_create_human_asset`, `morphomesh_auto_rig_human`), arguments are immediately packed into a Pydantic model:
  ```python
  req = GenerateConceptInput(prompt=prompt, ...)
  res = inference_adapter.generate_concept(req)
  return res.model_dump()
  ```
- In contrast, inspection tools (`morphomesh_setup_inspector_camera_rig`, `morphomesh_capture_viewport`, `morphomesh_critique_visual_quality`) currently perform **manual defensive `if` validation** against module-level sets (`VALID_INSPECTOR_VIEWPOINTS`, `VALID_SHADING_MODES`, `VALID_COLOR_TYPES`, `VALID_TARGET_PRESETS`).
- **Opportunity for Worker**: Refactoring inspection tools to pass arguments through `SetupInspectorCameraInput`, `CaptureViewportInput`, and `VisualCritiqueInput` would:
  1. Automatically enforce Pydantic v2 field validators and numeric bounds (`focal_length` in [10.0, 300.0], `margin` in [0.0, 1.0], `clearance_tolerance` >= 0.0).
  2. Handle automatic parameter alias resolution (e.g., `char_name` -> `character_name`, `clearance_threshold` -> `clearance_tolerance`).
  3. Eliminate duplicated pre-flight validation code.

### 4.3 Missing Input/Output Models for Tools 13 & 14
`morphomesh_assemble_master_character` and `morphomesh_export_production_character` currently do not have dedicated `AssembleMasterCharacterInput/Output` or `ExportProductionCharacterInput/Output` classes in `models.py`. Instead, they pass raw keyword arguments to `blender_bridge.assemble_master_character` and `export_production_assets`. While operational, creating dedicated Pydantic models in `models.py` would bring them into complete structural alignment with the other 15 tools.

---

## 5. Verification & Test Suite Matrix

To guarantee absolute backward compatibility and empirical soundness, all relevant test suites were executed:

| Test Suite | Test Count | Status | Execution Duration | Scope Verified |
|---|---|---|---|---|
| `tests/test_tools_schema.py` | 31 | **PASS** (31/31) | 0.04s | Default 7-tool schema discovery, parameter constraints, Pydantic bounds |
| `tests/test_fastmcp_inspection_tools.py` | 21 | **PASS** (21/21) | 0.82s | Inspection tools registration, input schemas, direct and `call_tool` execution, offline fallback |
| `tests/test_fastmcp_human_tools.py` | 17 | **PASS** (17/17) | 1.15s | Human tools registration, input schemas, parameter bounds, direct execution |
| `tests/test_adversarial_m4_gating.py` | 121 | **PASS** (121/121) | 19.25s | Full 5-permutation gating matrix, fuzzing of truthy/falsy values, low-level JSON-RPC protocol |
| `tests/test_adversarial_fastmcp_bridge_human.py` | 68 | **PASS** (68/68) | 14.22s | Parameter boundary fuzzing, Unicode resilience, AST containment |
| `tests/test_inspector_camera.py` | 40 | **PASS** (40/40) | 0.35s | Hierarchical AABB math, optical framing distance, sub-region centers, 6 viewpoints |
| `tests/test_visual_critic.py` | 28 | **PASS** (28/28) | 0.32s | `PurePythonBVHTree`, defect injection fixtures, >95% benchmark detection accuracy |
| `tests/test_bridge_socket_parity.py` | 21 | **PASS** (21/21) | 15.40s | NDJSON framing, timer immortality guard, client-server method parity |
| **Total Test Suite** | **347** | **PASS** (347/347) | **51.55s** | **100% Pass Rate, 0 Failures, 0 Regressions** |

---

## 6. Action Plan for Implementation Worker

To finalize R1 and transition smoothly into subsequent Milestones M4 and M5 without regressions:

1. **Step 1: Synchronize Top-Level Imports in `src/morphomesh/server.py`**:
   - Add imports from `morphomesh.models`:
     ```python
     CaptureViewportInput,
     CaptureViewportOutput,
     SetupInspectorCameraInput,
     SetupInspectorCameraOutput,
     VisualCritiqueInput,
     VisualCritiqueOutput,
     ```
2. **Step 2: Streamline Parameter Validation via Pydantic Models**:
   - In `morphomesh_setup_inspector_camera_rig`: wrap incoming arguments in `SetupInspectorCameraInput` before forwarding to bridge.
   - In `morphomesh_capture_viewport`: wrap incoming arguments in `CaptureViewportInput`.
   - In `morphomesh_critique_visual_quality`: wrap incoming arguments in `VisualCritiqueInput`.
   - Maintain `ToolError` mapping on `ValidationError` to preserve existing client error contract:
     ```python
     except ValidationError as e:
         raise ToolError(f"MorphoMesh Parameter Validation Error: {e}")
     ```
3. **Step 3 (Optional / Polishing): Add Pydantic Models for Tools 13 & 14**:
   - Define `AssembleMasterCharacterInput` / `AssembleMasterCharacterOutput` and `ExportProductionCharacterInput` / `ExportProductionCharacterOutput` in `src/morphomesh/models.py`.
4. **Step 4: Regression Testing**:
   - Run `uv run pytest tests/test_tools_schema.py tests/test_fastmcp_inspection_tools.py tests/test_fastmcp_human_tools.py tests/test_adversarial_m4_gating.py` to confirm 100% pass rate.
