# MorphoMesh Architectural Survey: FastMCP Tools, Public API Surface, and Blender Socket Bridge Protocol

**Date:** 2026-09-09  
**Investigator:** Explorer 2 (Survey Subagent)  
**Target Repository:** MorphoMesh (E:\tool\mcp\MorphoMesh)  
**Scope:** Phase 0 Architecture Survey for Subsystem Modularization, FastMCP Tool Definitions, Top-Level Public Exports (__init__.py), and Blender Socket IPC Protocol.

---

## 1. Executive Summary & Problem Boundary

MorphoMesh connects AI creature and digital human generative pipelines with Blender (supporting Blender 4.5+ and 5.2.1 LTS) via Model Context Protocol (FastMCP) and a two-way Socket IPC Bridge. Over several development milestones (M1–M5, Armored War Bear, Digital Human Yu Nian An, Auto-Inspector & Closed-Loop Visual Critique, Skeletal Engine), the codebase has accumulated over 2,080 automated tests.

However, two central gateway files have become major architectural bottlenecks:
1. src/morphomesh/server.py: 73,670 bytes (1,690 lines) containing 19 FastMCP tools, Pydantic input model serialization, multi-tier error handling, and environment-variable gating logic.
2. src/morphomesh/blender_bridge.py: 155,140 bytes (3,455 lines) combining TCP socket client transport, NDJSON streaming, AST static analysis validation, subprocess headless CLI execution, ~1,800 lines of inline embedded Python script templates, and 30 public proxy methods.

The objective of this survey is to establish an exhaustive catalog of every public interface, socket message contract, and export symbol, establishing **strict backward-compatibility invariants** so that the refactoring / modularization team can decompose these monoliths without regressing any of the 2,080+ tests or breaking any external client or Blender addon interaction.

---

## 2. FastMCP Server Initialization & Gating Architecture

### 2.1 Server Instance & Core Singletons
The server instance is initialized in src/morphomesh/server.py lines 83-105:
- mcp: FastMCP(\"MorphoMeshServer\", instructions=..., host=os.environ.get(\"MORPHOMESH_HOST\", \"127.0.0.1\"), port=int(os.environ.get(\"MORPHOMESH_PORT\", \"8765\")))
- inference_adapter: BaseInferenceAdapter (obtained via get_inference_adapter(mode=_backend_mode, cache_dir=_storage_dir))
- lender_bridge: BlenderBridge(host=BLENDER_HOST, port=BLENDER_PORT, blender_bin_path=...)
- meshy_connector: MeshyConnector()
- create_mcp_server() -> FastMCP: Factory returning mcp.

### 2.2 Environment Gating Matrix & Tool Sets
server.py defines four tool categories (lines 1602-1634):
- CREATURE_TOOL_NAMES (7 tools): morphomesh_generate_concept, morphomesh_create_3d_asset, morphomesh_optimize_topology, morphomesh_auto_rig, morphomesh_blender_execute, morphomesh_get_scene_status, morphomesh_render_preview.
- HUMAN_TOOL_NAMES (7 tools): morphomesh_create_human_asset, morphomesh_auto_rig_human, morphomesh_setup_human_materials, morphomesh_groom_human, morphomesh_dress_human, morphomesh_assemble_master_character, morphomesh_export_production_character.
- INSPECTION_TOOL_NAMES (3 tools): morphomesh_setup_inspector_camera_rig, morphomesh_capture_viewport, morphomesh_critique_visual_quality.
- ANIMATION_TOOL_NAMES (2 tools): morphomesh_animate_asset, morphomesh_list_animations.
- ALL_TOOL_NAMES: Union of CREATURE_TOOL_NAMES | HUMAN_TOOL_NAMES | INSPECTION_TOOL_NAMES (17 tools).

### 2.3 Gating Mechanics & Permutation Truth Table
_get_active_allowed_tool_names() parses tokens:
- **Truthy tokens**: '1', 'true', 'yes', 'all' (case-insensitive, whitespace-trimmed).
- **Falsy/Inactive tokens**: '0', 'false', 'none', '', etc.

| MORPHOMESH_INCLUDE_ALL_TOOLS | MORPHOMESH_INCLUDE_HUMAN_TOOLS | MORPHOMESH_INCLUDE_INSPECTION_TOOLS | MORPHOMESH_INCLUDE_ANIMATION_TOOLS | Active Tools Count | Exposed Tool Sets |
| :---: | :---: | :---: | :---: | :---: | :--- |
| Unset / 0 | Unset / 0 | Unset / 0 | Unset / 0 | **7** | CREATURE_TOOL_NAMES (Default legacy state) |
| Unset / 0 | Unset / 0 | 1 | Unset / 0 | **10** | CREATURE + INSPECTION |
| Unset / 0 | 1 | Unset / 0 | Unset / 0 | **14** | CREATURE + HUMAN |
| Unset / 0 | 1 | 1 | Unset / 0 | **17** | CREATURE + HUMAN + INSPECTION (ALL_TOOL_NAMES) |
| 1 | * | * | Unset / 0 | **17** | ALL_TOOL_NAMES (Independent of other flags) |
| * | * | * | 1 | Baseline + 2 | Adds ANIMATION_TOOL_NAMES (+2 tools) |

### 2.4 Dual-Layer Interception & Execution Bypass Invariant
1. **High-Level Filter:** mcp.list_tools = _filtered_list_tools filters the tools returned to MCP SDK callers.
2. **Low-Level JSON-RPC Filter:** mcp._mcp_server.request_handlers[mcp_types.ListToolsRequest] = _wrapped_lowlevel_list_tools ensures strict protocol parity for low-level clients.
3. **Execution Bypass Invariant:** Tools NOT included in list_tools() **REMAIN DIRECTLY CALLABLE** via mcp.call_tool(\"tool_name\", {...}). Gating controls tool discovery only.

---

## 3. Catalog of All 19 FastMCP Tools

### 3.1 Group A: Canonical Creature Pipeline (7 Tools)

#### 1. morphomesh_generate_concept
- **Function Signature:**
  `python
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
  `
- **Docstring:** Stage 1: Generate a 2D creature concept image conditioned on anatomical priors. Expands natural language prompts with standardized anatomical rest poses, eliminating dynamic limb overlap and producing a clean silhouette suitable for single-view 3D reconstruction. Supports Google Gemini & Imagen 3 (backend="gemini") or deterministic procedural synthesis (backend="mock" or "default").
- **Underlying Call:** inference_adapter.generate_concept(GenerateConceptInput(...))
- **Returns:** GenerateConceptOutput.model_dump() (concept_id, image_path, creature_type, iew_mode, prompt_expanded, metadata).

#### 2. morphomesh_create_3d_asset
- **Function Signature:**
  `python
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
  `
- **Docstring:** Stage 2: Reconstruct a textured 3D mesh with PBR maps from a 2D concept image or prompt. Consumes the concept image or text prompt, extracts foreground geometry via single-image 3D diffusion or text-to-3D backends (including Meshy AI, Tripo3D, Microsoft TRELLIS, Tencent Hunyuan3D-2.1, or local procedural generator), and generates a dense mesh accompanied by albedo, normal, roughness, and metallic texture maps. Supported model_backend / backend values: 'meshy', 'tripo', 'trellis', 'hunyuan', 'anycreature', 'mock'. Supports '/boost' parameter in prompt for high-fidelity refined mesh synthesis.
- **Underlying Call:** If backend/model_backend == 'meshy': meshy_connector.text_to_3d(...) or image_to_3d(...); else: inference_adapter.create_3d_asset(Create3DAssetInput(...)).
- **Returns:** Create3DAssetOutput.model_dump() (sset_id, mesh_path, pbr_textures, poly_count, ertex_count, ormat).

#### 3. morphomesh_optimize_topology
- **Function Signature:**
  `python
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
  `
- **Docstring:** Stage 3: Retopologize dense triangular mesh into clean quad-dominant topology. Employs QuadriFlow remeshing or decimation solvers inside Blender to produce animatable, deforming mesh structures adhering to the specified polygon budget.
- **Underlying Call:** Dispatches to lender_bridge.optimize_topology(...) if connected/available; falls back to inference_adapter.optimize_topology(OptimizeTopologyInput(...)).
- **Returns:** OptimizeTopologyOutput.model_dump() (optimized_asset_id, output_mesh_path, original_vertex_count, original_face_count, optimized_vertex_count, optimized_face_count, quad_percentage, eduction_ratio).

#### 4. morphomesh_auto_rig
- **Function Signature:**
  `python
  async def morphomesh_auto_rig(
      asset_id: Optional[str] = None,
      input_mesh_path: Optional[str] = None,
      creature_type: str = "quadruped",
      rig_type: str = "rigify_creature",
      skinning_method: str = "automatic_weights",
      symmetry: bool = True,
      generate_test_animation: bool = True,
      load_into_scene: bool = True,
      backend: str = "blender",
      model_task_id: Optional[str] = None,
      height_meters: float = 1.7,
      ctx: Optional[Context] = None,
  ) -> Dict[str, Any]
  `
- **Docstring:** Stage 4: Construct modular creature armature and compute automatic skin deformation weights. Fits a procedural creature armature to anatomical landmarks detected from the input mesh, binds bones via harmonic/biharmonic heat diffusion, and generates validation walk/idle cycles.
- **Underlying Call:** If backend == 'meshy': meshy_connector.auto_rig(...); else: lender_bridge.create_armature(...) or inference_adapter.auto_rig(...).
- **Returns:** AutoRigOutput.model_dump() (ig_id, rmature_name, one_count, ones, skinning_method, nimation_clips).

#### 5. morphomesh_blender_execute
- **Function Signature:**
  `python
  async def morphomesh_blender_execute(
      script: str,
      timeout_seconds: int = 30,
      target_scene: Optional[str] = None,
      save_after: bool = False,
      save_path: Optional[str] = None,
      return_variables: Optional[List[str]] = None,
      ctx: Optional[Context] = None,
  ) -> Dict[str, Any]
  `
- **Docstring:** Stage 5 Utility: Execute arbitrary bpy script in Blender protected by two-tier AST analysis. Validates script against forbidden modules (os, sys, subprocess, socket), dangerous built-ins (exec, eval, compile, open), and dunder reflection attributes before dispatching to Blender's Python runtime via interactive socket or headless subprocess.
- **Underlying Call:** BpyCodeValidator().validate(script) followed by lender_bridge.execute_custom_script(...).
- **Returns:** BlenderExecuteOutput.model_dump() (success, stdout, stderr, eturned_data, execution_time_ms).

#### 6. morphomesh_get_scene_status
- **Function Signature:**
  `python
  async def morphomesh_get_scene_status(
      scene_name: Optional[str] = None,
      include_mesh_stats: bool = True,
      include_hierarchy: bool = True,
      include_materials: bool = True,
      include_armatures: bool = True,
      include_cameras_lights: bool = True,
      ctx: Optional[Context] = None,
  ) -> Dict[str, Any]
  `
- **Docstring:** Stage 5 Utility: Inspect active Blender scene graph and geometric statistics. Queries active objects, poly/vertex counts, armature hierarchies, bounding boxes, cameras, lights, and materials in the current Blender session.
- **Underlying Call:** lender_bridge.get_scene_status(...).
- **Returns:** SceneStatusOutput.model_dump() (scene_name, lender_version, ctive_object, object_count, 	otal_vertices, 	otal_faces, objects, rmatures, cameras, lights).

#### 7. morphomesh_render_preview
- **Function Signature:**
  `python
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
  `
- **Docstring:** Stage 5: Render high-fidelity viewport preview using studio lighting and procedural auto-camera. Frames the camera to the creature bounding box, sets up 3-point key/fill/rim lighting, renders via Apple Metal-accelerated EEVEE, and returns image metadata and base64 preview.
- **Underlying Call:** lender_bridge.render_preview(...).
- **Returns:** RenderPreviewOutput.model_dump() (image_path, ase64_preview, esolution, ender_time_seconds, ender_engine).

### 3.2 Group B: Digital Human Engine Pipeline (7 Tools)

#### 8. morphomesh_create_human_asset
- **Function Signature:**
  `python
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
  `
- **Docstring:** Stage 1 Human Engine: Generate an anthropometrically accurate 3D female human mesh. Constructs water-tight base body mesh adhering to medical human anatomy (MakeHuman/CC0 canonical mold), authentic female body curves (teardrop volumetric bust, inframammary fold, 0.70 waist-to-hip ratio, gluteal curve), clavicle S-curve, distinct 5-toed feet, and 52 ARKit FACS facial blendshapes.
- **Underlying Call:** lender_bridge.create_human_asset(...) (or fallback local assembly).
- **Returns:** Dict / CreateHumanAssetOutput (sset_id, mesh_path, ertex_count, ace_count, quad_ratio, shape_keys, landmarks, ounding_box).

#### 9. morphomesh_auto_rig_human
- **Function Signature:**
  `python
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
  `
- **Docstring:** Stage 2 Human Engine: Rig digital human body mesh using Blender Rigify Human Armature. Binds all 163 DEF bones (torso spine, limbs, 10 articulated fingers, neck/head) and evaluates smooth deformation weights to eliminate joint volume loss at elbows, knees, and ankles.
- **Underlying Call:** lender_bridge.auto_rig_human(...).
- **Returns:** Dict / AutoRigHumanOutput (rmature_name, def_bone_count [163], ones, has_skin_weights, pose, exported_mesh_path).

#### 10. morphomesh_setup_human_materials
- **Function Signature:**
  `python
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
  `
- **Docstring:** Stage 3 Human Engine: Setup photorealistic PBR materials for digital human character. Constructs Blender Principled BSDF v2 shaders with Random Walk Subsurface Scattering (radius [1.0, 0.22, 0.11]), dual-chamber refractive eye optics (cornea IOR 1.376, concave iris dish with tear meniscus IOR 1.333), silky dark hair shader, and translucent white silk fabric.
- **Underlying Call:** lender_bridge.setup_human_materials(...).
- **Returns:** Dict / SetupHumanMaterialsOutput (status, materials_assigned, shader_nodes_created).

#### 11. morphomesh_groom_human
- **Function Signature:**
  `python
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
  `
- **Docstring:** Stage 4 Human Engine: Generate procedural Geometry Nodes Hair Curves grooming. Creates 6 structural hair layers: eyebrow curves, eyelash arcs, straight blunt bangs brow-grazing hime cut, face-framing cheek sidelocks, crown scalp parting, and cascading back hair down to mid-thigh with anisotropic silky sheen. Optionally evaluates polygonal quad ribbons for real-time FBX/glTF export.
- **Underlying Call:** lender_bridge.groom_human(...).
- **Returns:** Dict / GroomHumanOutput (status, hair_system_name, curve_count, strata_count, ibbon_mesh_path).

#### 12. morphomesh_dress_human
- **Function Signature:**
  `python
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
  `
- **Docstring:** Stage 5 Human Engine: Synthesize tailored wardrobe and character magic props. Fits conforming one-piece sundress bodice with teardrop bust drape and realistic gravity folds, ice-blue satin waist sash with 3D knot loops, flat strappy sandals leaving 10 toes exposed, 10 crimson marionette control threads attached to distal finger bones, and 10 luminous swallowtail butterflies flocking around the character.
- **Underlying Call:** lender_bridge.dress_human(...).
- **Returns:** Dict / DressHumanOutput (status, wardrobe_objects, dress_face_count, sash_offset, utterfly_count).

#### 13. morphomesh_assemble_master_character
- **Function Signature:**
  `python
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
  `
- **Docstring:** Stage 6 Master Assembly: Orchestrate complete digital human scene in Blender 4.5+ LTS. Assembles all 7 canonical collections: 01_Body, 02_Hair, 03_Wardrobe, 04_Props, 05_Armature, 06_Lights, 07_Cameras into Yu_Nian_An_Master.blend with full Cycles AgX render setup and multi-angle camera turntable.
- **Underlying Call:** lender_bridge.assemble_master_character(...).
- **Returns:** Dict (status, lend_file_path, master_character_name, collections_created, object_count).

#### 14. morphomesh_export_production_character
- **Function Signature:**
  `python
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
  `
- **Docstring:** Stage 7 Production Export: Multi-format packaging and 4K PBR texture generation. Packages the assembled character into output/yu_nian_an/ with Yu_Nian_An.fbx (163 DEF bones, animatable bind pose), Yu_Nian_An.glb (52 ARKit blendshapes, TEXCOORD_0 UVs, quad ribbon hair), 4K PBR texture maps, and comprehensive production documentation.
- **Underlying Call:** character_assembler.export_production_assets(...).
- **Returns:** Dict (status, exported_files [bx_path, glb_path, lend_path, 	extures_dir], 	exture_resolution).

### 3.3 Group C: Camera Rig & Visual Quality QA Pipeline (3 Tools)

#### 15. morphomesh_setup_inspector_camera_rig
- **Function Signature:**
  `python
  async def morphomesh_setup_inspector_camera_rig(
      viewpoint: str = "three_quarter",
      target_center: Optional[List[float]] = None,
      sub_region: Optional[str] = None,
      focal_length: float = 50.0,
      camera_name: str = "MorphoMesh_Inspector_Camera",
      mesh_objects: Optional[List[str]] = None,
      ctx: Optional[Context] = None,
  ) -> Dict[str, Any]
  `
- **Docstring:** Stage 8 Inspection: Position and configure dedicated multi-angle inspector camera. Solves bounding box across character meshes, determines anatomical sub-region centers (Full Body, Head/Portrait, Torso, Hands, Feet), and applies optical framing distance derivation: d = (R / sin(alpha_min)) * (1 + margin) for canonical viewpoints ('front', 'side', 'back', 'three_quarter', 'head', 'hands', 'turntable'). Non-destructively creates or updates the camera object in Blender and aims look-at tracking.
- **Underlying Call:** lender_bridge.setup_inspector_camera(...).
- **Returns:** SetupInspectorCameraOutput.model_dump() (status, camera_name, iewpoint, camera_location, 	arget_center, ocal_length, raming_distance).

#### 16. morphomesh_capture_viewport
- **Function Signature:**
  `python
  async def morphomesh_capture_viewport(
      output_path: Optional[str] = None,
      camera_name: str = "MorphoMesh_Inspector_Camera",
      resolution: List[int] = [1024, 1024],
      shading_mode: str = "SOLID",
      color_type: str = "RANDOM",
      ctx: Optional[Context] = None,
  ) -> Dict[str, Any]
  `
- **Docstring:** Stage 8 Inspection: Ultra-fast multi-shading viewport capture. Captures high-resolution diagnostic viewport frames using OpenGL offscreen buffers (<200ms) or Workbench fallback. Supports 4 shading modes: 'WIREFRAME', 'SOLID' (with 'RANDOM' per-object color coding to immediately reveal mesh penetrations), 'MATERIAL', and 'RENDERED'.
- **Underlying Call:** lender_bridge.capture_viewport(...).
- **Returns:** CaptureViewportOutput.model_dump() (status, image_path, ase64_preview, esolution, shading_mode, color_type).

#### 17. morphomesh_critique_visual_quality
- **Function Signature:**
  `python
  async def morphomesh_critique_visual_quality(
      character_name: str = "MorphoMesh_Character",
      target_object: Optional[str] = None,
      camera_angles: Optional[List[str]] = None,
      clearance_tolerance: float = 0.0005,
      target_preset: str = "stylized_heroine",
      ctx: Optional[Context] = None,
  ) -> Dict[str, Any]
  `
- **Docstring:** Stage 8 Closed-Loop Quality Assurance: Automated visual defect critique. Multi-domain diagnostic engine inspecting 3D meshes for 4 defect classes:
  1. CLIPPING: Garment-on-skin penetration evaluated via Möller-Trumbore ray/triangle intersection and PurePythonBVHTree.
  2. PROPORTION_DEVIATION: Anthropometric body ratios vs medical standards (head ratio, waist-hip ratio, limb span).
  3. SKINNING_ARTIFACT: Abnormal joint pinch, concave folding, or volume collapse under deformation.
  4. GROOMING_COLLISION: Hair curve roots penetrating scalp geometry or garment colliders.
  Outputs structured QA critique with defect locations, bounding boxes, severity ratings ('CRITICAL', 'MAJOR', 'MINOR'), actionable remediation commands, and an overall quality score (0.0 to 1.0).
- **Underlying Call:** lender_bridge.critique_visual_quality(...).
- **Returns:** VisualCritiqueOutput.model_dump() (status, character_name, defects, defect_count, quality_score, passed, ctionable_recommendations).

---

### 3.4 Group D: Meshy Animation Library Pipeline (2 Tools)

#### 18. morphomesh_animate_asset
- **Function Signature:**
  `python
  async def morphomesh_animate_asset(
      asset_id: Optional[str] = None,
      rig_task_id: Optional[str] = None,
      input_mesh_path: Optional[str] = None,
      action_id: Optional[int] = None,
      action_name: Optional[str] = None,
      fps: int = 30,
      output_format: str = "glb",
      backend: str = "meshy",
      ctx: Optional[Context] = None,
  ) -> Dict[str, Any]
  `
- **Docstring:** Retarget an animation action onto a rigged 3D character. Retargets motion clips from the Meshy Animation Library onto a rigged character and exports animatable GLB/FBX.
- **Underlying Call:** meshy_connector.animate(MeshyAnimationInput(...)).
- **Returns:** AnimateAssetOutput.model_dump() (nimation_id, output_mesh_path, ction_name, duration_seconds, ps).

#### 19. morphomesh_list_animations
- **Function Signature:**
  `python
  async def morphomesh_list_animations(
      category: Optional[str] = None,
      sub_category: Optional[str] = None,
      search: Optional[str] = None,
      limit: int = 50,
      ctx: Optional[Context] = None,
  ) -> Dict[str, Any]
  `
- **Docstring:** Browse and search the 340+ preset animation actions in the Meshy Animation Library. Free endpoint (0 credits). Returns action IDs, descriptive names, and preview GIF URLs. Categories: 'WalkAndRun', 'BodyMovements', 'DailyActions', 'Fighting', 'Dancing'.
- **Underlying Call:** meshy_connector.list_animations(...).
- **Returns:** ListAnimationsOutput.model_dump() (	otal_count, nimations [list of AnimationItem]).

---

## 4. Top-Level Public Exports (src/morphomesh/__init__.py)

src/morphomesh/__init__.py serves as the primary public entry point for the MorphoMesh Python library. It re-exports 40 explicit symbols via __all__ plus 26 error code constants into the package namespace.

### 4.1 Exhaustive Catalog of Symbols in __all__

`python
__all__ = [
    # 1. Version & Server Instances
    "__version__",
    "mcp",
    "create_mcp_server",

    # 2. Blender Bridge & AST Security Validation
    "BlenderBridge",
    "BpyCodeValidator",
    "SecurityException",
    "BlenderExecutionError",

    # 3. Inference Adapters & Factory
    "BaseInferenceAdapter",
    "MockInferenceAdapter",
    "ReplicateInferenceAdapter",
    "HuggingFaceInferenceAdapter",
    "get_inference_adapter",

    # 4. Domain Enumerations & Structures
    "CreatureType",
    "ViewMode",
    "Pose",
    "Style",
    "QualityTier",
    "TopologyType",
    "RetopoMethod",
    "RigType",
    "SkinningMethod",
    "RenderEngine",
    "LightingPreset",
    "BoundingBox",
    "SceneObjectInfo",

    # 5. Pydantic Request/Response Contract Schemas
    "GenerateConceptInput",
    "GenerateConceptOutput",
    "Create3DAssetInput",
    "Create3DAssetOutput",
    "OptimizeTopologyInput",
    "OptimizeTopologyOutput",
    "AutoRigInput",
    "AutoRigOutput",
    "BlenderExecuteInput",
    "BlenderExecuteOutput",
    "SceneStatusInput",
    "SceneStatusOutput",
    "RenderPreviewInput",
    "RenderPreviewOutput",
    "MorphoMeshException",
]
`

### 4.2 Error Codes Available in morphomesh Namespace
The following 26 integer and string error codes are imported into morphomesh and must remain accessible:
- ERR_PARSE_ERROR (-32700)
- ERR_INVALID_REQUEST (-32600)
- ERR_METHOD_NOT_FOUND (-32601)
- ERR_INVALID_ARGUMENT (-32602)
- ERR_IMAGE_NOT_FOUND (-32001)
- ERR_BACKEND_UNAVAILABLE (-32002)
- ERR_VRAM_EXHAUSTED (-32003)
- ERR_REMESH_FAILED (-32004)
- ERR_SKINNING_HEAT_FAILURE (-32005)
- ERR_SCRIPT_SECURITY_VIOLATION (-32006)
- ERR_TIMEOUT (-32007)
- ERR_BLENDER_UNAVAILABLE (-32008)
- ERR_NO_CAMERA (-32009)
- ERR_ANATOMY_DETECTION_FAILED (-32010)
- ERR_INPUT_MESH_NOT_FOUND (-32011)
- ERR_INVALID_POLY_COUNT (-32012)
- ERR_NON_MANIFOLD_MESH (-32013)
- ERR_SCENE_NOT_FOUND (-32014)
- ERR_RENDER_FAILED (-32015)
- ERR_OUTPUT_WRITE_FAILED (-32016)
- ERR_SCRIPT_SYNTAX_ERROR (-32017)
- ERR_SCRIPT_RUNTIME_EXCEPTION (-32018)
- ERR_INFERENCE_FAILED (-32019)
- ERR_DISK_WRITE_FAILED (-32020)
- ERR_SCRIPT_EXECUTION_TIMEOUT (-32007)
- ERR_BLENDER_EXECUTION_FAILED (-32000)

### 4.3 Consumer Import Patterns Across the Project
An exhaustive AST analysis across 	ests/, examples/, src/, and lender_addon/ revealed that external callers rely heavily on direct module imports:
1. rom morphomesh import ...: __version__, mcp, create_mcp_server, BlenderBridge, BpyCodeValidator, SecurityException, ERR_BLENDER_UNAVAILABLE.
2. rom morphomesh.server import ...:
   - Tool sets: ALL_TOOL_NAMES, CREATURE_TOOL_NAMES, HUMAN_TOOL_NAMES, INSPECTION_TOOL_NAMES.
   - Singletons: mcp, create_mcp_server, lender_bridge.
   - All individual tool functions: morphomesh_create_3d_asset, morphomesh_generate_concept, morphomesh_auto_rig_human, etc.
3. rom morphomesh.blender_bridge import ...:
   - Classes: BlenderBridge, BpyCodeValidator, SecurityException, BlenderExecutionError.
   - Sentinels: SENTINEL_START, SENTINEL_END.
   - Constants: ALL_163_DEF_BONES, ARKIT_52_BLENDSHAPES.

**Refactoring Invariant:** All re-exports from src/morphomesh/__init__.py, src/morphomesh/server.py, and src/morphomesh/blender_bridge.py must remain fully intact to prevent breaking downstream consumers or test suites.

---

## 5. Blender Socket Bridge Protocol Deep-Dive

The bridge subsystem coordinates communication between the client environment (running MCP / FastMCP) and the Blender Python runtime (py).

`
[ Antigravity / Client ]
           │
           ▼
[ FastMCP Server (server.py) ]
           │
           ▼
[ BlenderBridge (blender_bridge.py) ]
           │
     Is Socket Connected?
     ├── YES ──► TCP Socket (127.0.0.1:9876, NDJSON) ──► [ listener.py in Blender ]
     │                │                                         │ (bpy.app.timers 50Hz)
     │                │                                         ▼
     │                └── Tier 2: execute_code fallback ──► Blender Main Thread
     │
     └── NO  ──► Subprocess Runner (blender -b -P <tmp.py>)
                      │
                      ▼
                 Stdout Sentinel Parsing (MORPHOMESH_START_JSON ... MORPHOMESH_END_JSON)
`

---

### 5.1 Network Transport & Framing Specifications
- **Transport:** Stream TCP socket (socket.AF_INET, socket.SOCK_STREAM).
- **Default Host:** 127.0.0.1 (configurable via BLENDER_HOST).
- **Default Port:** 9876 (configurable via BLENDER_PORT).
- **Framing Protocol:** Newline-Delimited JSON (NDJSON).
  - Every outgoing JSON request line is encoded as UTF-8 and terminated with "\n".
  - Every incoming JSON response line is encoded as UTF-8 and terminated with "\n".
- **Chunk Size:** 64 KB (client.recv(65536)).
- **Buffer Safety Guard:** 16 MB maximum buffer length. If an incoming byte stream exceeds 16MB without a newline delimiter, the connection is forcibly terminated to protect against memory exhaustion.
- **Fragmentation & Streaming Resilience:** The listener's buffer loop (while b"\n" in buffer:) handles fragmented packets and pipelined sequential commands across a single socket connection.
- **EOF Fallback:** If the connection is closed or half-closed (SHUT_WR) without a trailing newline, json.JSONDecoder().raw_decode parses the remaining complete JSON object.

---

### 5.2 Concurrency, Thread Synchronization & Blender Main Thread Safety
Blender's C-Python API (py) is **not thread-safe**. Invoking operators (py.ops), scene graph modifications, or rendering from a Python background worker thread leads to memory corruption, segmentation faults, or silent state drops.

MorphoMesh solves this via a robust decoupled queue architecture:
1. **Background Socket Threads:**
   - _accept_loop: Runs in a daemon thread, accepting new client sockets (settimeout(1.0)).
   - _client_handler: Runs in a dedicated daemon thread per client, reading incoming TCP stream data, parsing NDJSON lines, and enqueueing pairs into self.command_queue:
     `python
     self.command_queue.put((cmd, client))
     `
2. **Main Thread Execution via py.app.timers:**
   - The queue is drained by self._drain_queue, registered on Blender's persistent application timers:
     `python
     bpy.app.timers.register(self._drain_queue, persistent=True)
     `
   - **Polling Interval:** Returns  .02 seconds (executing at 50Hz).
   - **Immortal Barrier:** The entire _drain_queue method is guarded with fatal exception traps. If a dispatched RPC method raises an unhandled exception, it is formatted into a JSON-RPC error response and sent to the client. The timer callback itself **NEVER raises an unhandled exception**, preventing Blender from unregistering the timer.
   - **Orderly Teardown:** When stopping, _drain_queue is unregistered, active sockets are closed, and queued commands are purged.

---

### 5.3 JSON-RPC Request and Response Schema

#### Outgoing Request Format:
`json
{
  "jsonrpc": "2.0",
  "id": "req-a1b2c3d4",
  "method": "<method_name>",
  "type": "<method_name>",
  "params": {
    "<param_key>": "<param_value>"
  }
}
`
*Note:* Both "method" and "type" keys are populated with the same command string to maintain dual-compatibility with legacy listener revisions.

#### Incoming Success Response Format:
`json
{
  "jsonrpc": "2.0",
  "id": "req-a1b2c3d4",
  "status": "success",
  "result": {
    "<key>": "<value>"
  }
}
`

#### Incoming Error Response Format:
`json
{
  "jsonrpc": "2.0",
  "id": "req-a1b2c3d4",
  "status": "error",
  "error": {
    "code": -32000,
    "message": "<human_readable_error>"
  }
}
`

#### Standard Error Codes:
- -32700: Parse error (invalid JSON received by listener)
- -32600: Invalid request (received JSON primitive instead of object dict)
- -32603: Internal serialization error (response object failed JSON encoding)
- -32000: General method execution exception
- -32006: AST security violation (attempted forbidden call or module import)
- -32007: Execution timeout
- -32008: Blender binary / host unavailable

---

## 6. Catalog of 20 Supported Socket RPC Commands & Multi-Tier Dispatch

Both lender_addon/morphomesh/listener.py and src/morphomesh/blender_bridge.py implement identical dispatch capabilities across 20 distinct command types. Each command accepts both its canonical prefixed form (morphomesh.<command>) and its short alias (<command>):

| # | Prefixed Command | Short Alias | Primary Input Parameters | Key Return Fields |
| :-: | :--- | :--- | :--- | :--- |
| 1 | morphomesh.ping | ping | {} | status: "pong", lender_version, mode: "interactive" |
| 2 | morphomesh.get_scene_status | get_scene_info | scene_name: Optional[str] | scene_name, object_count, 	otal_vertices, 	otal_faces, objects: List[dict], rmatures: List[dict], cameras: List[dict], lights: List[dict] |
| 3 | morphomesh.execute_custom_script | execute_code | script: str (or code), eturn_variables: List[str], save_after: bool, save_path: Optional[str] | success: bool, stdout: str, stderr: str, eturned_data: Dict[str, Any] |
| 4 | morphomesh.create_human_asset | create_human_asset | character_name, gender, height, head_ratio, style, poly_budget, chest_girth, waist_girth, hip_girth, export_format | status: "success", sset_id, mesh_path, ertex_count, ace_count, quad_ratio, shape_keys, landmarks, ounding_box |
| 5 | morphomesh.auto_rig_human | uto_rig_human | mesh_object_name, 	arget_object, ig_type, pose, export_format | status: "success", rmature_name, def_bone_count: 163, ones: List[str], has_skin_weights: True |
| 6 | morphomesh.setup_human_materials | setup_human_materials | mesh_object_name, material_preset, skin_tone, subsurface_scattering, efractive_eyes, ender_engine | status: "success", materials_assigned: List[str] |
| 7 | morphomesh.groom_human | groom_human | mesh_object_name, hair_style, hair_color, strand_count, include_eyebrows, include_eyelashes, generate_ribbons | status: "success", hair_system_name, curve_count, ibbon_mesh_name |
| 8 | morphomesh.dress_human | dress_human | human_object_name, outfit, include_sandals, include_red_threads, include_glowing_butterflies, utterfly_count, clearance_offset | status: "success", wardrobe_objects: List[str], dress_face_count, utterfly_count |
| 9 | morphomesh.assemble_master_character | ssemble_master_character | character_name, height, head_ratio, include_hair, include_wardrobe, include_props, include_armature, include_lighting, ender_engine, samples, save_blend, output_path | status: "success", lend_file_path, master_character_name, collections_created: List[str] |
| 10 | morphomesh.render_preview | ender_preview | camera_name, esolution_width, esolution_height, ender_engine, samples, iew_angle, 	ransparent_background, lighting_preset, save_to_disk, output_dir | status: "success", image_path, ase64_preview, esolution: List[int], ender_engine |
| 11 | morphomesh.setup_inspector_camera | setup_inspector_camera | iewpoint, 	arget_center: Optional[List[float]], sub_region: Optional[str], ocal_length, camera_name, mesh_objects, margin | status: "success", camera_name, iewpoint, camera_location, 	arget_center, ocal_length, raming_distance |
| 12 | morphomesh.capture_viewport | capture_viewport | output_path, camera_name, esolution: List[int], shading_mode, color_type | status: "success", image_path, ase64_preview, esolution, shading_mode, color_type |
| 13 | morphomesh.capture_multi_angle_inspection | capture_multi_angle_inspection | iewpoints: List[str], 	arget_object, output_dir, esolution: Tuple[int, int], shading_mode, color_type, ocal_length, camera_name, include_base64 | status: "success", captures: Dict[str, dict], output_dir |
| 14 | morphomesh.critique_visual_quality | critique_visual_quality | character_name, 	arget_object, camera_angles, clearance_tolerance, 	arget_preset, evaluate_penetration, evaluate_proportions, evaluate_skinning, evaluate_grooming, capture_images | status: "success", character_name, defects: List[dict], defect_count, quality_score, passed: bool, ctionable_recommendations: List[str] |
| 15 | morphomesh.optimize_topology | optimize_topology | input_mesh_path, 	arget_poly_count, 	opology_type, preserve_uvs, preserve_sharp_edges, method, output_format | optimized_asset_id, output_mesh_path, original_vertex_count, original_face_count, optimized_vertex_count, optimized_face_count, quad_percentage |
| 16 | morphomesh.create_armature | create_armature | input_mesh_path, creature_type, ig_type, skinning_method, symmetry, generate_test_animation, load_into_scene | ig_id, creature_type, one_count, ones: List[str], rmature_name, has_skin_weights: True |
| 17 | morphomesh.setup_creature_fur | setup_creature_fur | mesh_object_name, undercoat_strands, guard_hair_strands, low_vertex_group, clump_factor, 	aper_shape, generate_gltf_ribbons, max_ribbon_strands | status: "success", mesh_object_name, ur_system_names: List[str], 	otal_strand_count |
| 18 | morphomesh.evaluate_fur_ribbons | evaluate_fur_ribbons | mesh_object_name, ur_system_names: Optional[List[str]], max_export_strands | status: "success", ibbon_mesh_name, ertex_count, ace_count |
| 19 | morphomesh.setup_creature_materials | setup_creature_materials | mesh_object_name, rmor_object_names: Optional[List[str]], claws_object_names: Optional[List[str]] | status: "success", materials_assigned: List[str] |
| 20 | morphomesh.generate_war_armor | generate_war_armor | ase_mesh_name, clearance_offset, scale | status: "success", rmor_objects: List[str] |

---

### 6.1 Multi-Tier Execution Architecture
When lender_bridge.execute(method, params) is called, it follows a deterministic three-tier execution hierarchy:

1. **Tier 1: Interactive Socket Direct RPC**
   Checks self.is_interactive_connected(). If connection is active, sends send_socket_request(method, params) over TCP.
2. **Tier 2: Interactive Socket execute_code Bridging**
   If direct RPC returns an error or method is unrecognized by a generic Blender MCP addon, calls _generate_interactive_script(method, params) and transmits it via send_socket_request("execute_code", {"code": script, "return_variables": ["_morphomesh_result"]}).
3. **Tier 3: Subprocess Headless CLI Runner**
   If interactive socket is not connected or fails, falls back to _dispatch_headless(method, params, timeout):
   - Generates a complete standalone Python script incorporating params.
   - Writes script to a temporary file (	empfile.NamedTemporaryFile).
   - Invokes Blender in background mode: lender -b -P <script_path>.
   - Captures stdout and isolates the structured JSON payload enclosed between sentinel strings:
     `
     MORPHOMESH_START_JSON
     { ... json payload ... }
     MORPHOMESH_END_JSON
     `
   - Parses the JSON and returns the dictionary.

---

## 7. AST Static Analysis & Modularization Blueprint for lender_bridge.py

### 7.1 AST Static Analysis & Redundant Security Architecture
To eliminate Remote Code Execution (RCE), arbitrary system command execution, and filesystem destruction, MorphoMesh enforces redundant two-tier AST static analysis:

1. **Client-Side Validator (BpyCodeValidator in src/morphomesh/blender_bridge.py):**
   - Max length: 10,000 characters.
   - Allowed modules: py, math, mathutils, mesh, 
umpy, andom, json, collections, itertools, 	ime, morphomesh.
   - Forbidden modules: os, sys, subprocess, shutil, socket, http, urllib, equests, ctypes, multiprocessing, 	hreading, signal, pty, importlib, uiltins, posix.
   - Forbidden calls: eval, exec, __import__, compile, open, input, reakpoint, globals, locals, getattr, setattr, delattr.
   - Forbidden attributes: __subclasses__, __globals__, __code__, __dict__, __bases__, __mro__, __class__.
   - Forbidden names: __builtins__, eval, exec, open, compile, __import__, globals, locals, getattr, setattr, delattr, os, sys, subprocess, shutil, socket.
   - Rejection mechanism: Raises SecurityException.

2. **Server-Side Validator (AddonSecurityValidator in lender_addon/morphomesh/listener.py):**
   - Redundantly analyzes any script received via execute_custom_script or execute_code before calling Python exec().
   - Enforces identical module and built-in restrictions inside Blender's process boundary.

---

### 7.2 Modularization Blueprint for lender_bridge.py
src/morphomesh/blender_bridge.py currently spans 3,455 lines (155 KB). A safe, 100% backward-compatible decomposition involves creating a dedicated subpackage src/morphomesh/bridge/:

`
src/morphomesh/
├── blender_bridge.py            # Backward-compatible facade (re-exports BlenderBridge, BpyCodeValidator, etc.)
└── bridge/
    ├── __init__.py              # Subpackage exports
    ├── client.py                # TCP socket transport, NDJSON streaming, connection probe, timeout handling
    ├── headless.py              # Headless CLI runner, binary resolution, sentinel extraction (SENTINEL_START/END)
    ├── validator.py             # BpyCodeValidator, SecurityException, BlenderExecutionError
    ├── constants.py             # SENTINEL_START, SENTINEL_END, ALL_163_DEF_BONES, ARKIT_52_BLENDSHAPES, error codes
    ├── scripts/                 # Domain-specific headless & interactive script templates
    │   ├── __init__.py
    │   ├── scene_scripts.py     # ping, get_scene_status, render_preview
    │   ├── human_scripts.py     # create_human_asset, auto_rig_human, setup_human_materials, groom, dress, assemble
    │   ├── creature_scripts.py  # create_armature, setup_fur, evaluate_ribbons, setup_materials, war_armor
    │   └── camera_scripts.py    # setup_inspector_camera, capture_viewport, multi_angle, visual_critique
    └── bridge.py                # BlenderBridge class coordinating client, headless, and domain methods
`

**Key Backward-Compatibility Guarantee:**
src/morphomesh/blender_bridge.py will remain at its current path and import/re-export all symbols from morphomesh.bridge:
`python
from morphomesh.bridge import (
    BlenderBridge,
    BpyCodeValidator,
    SecurityException,
    BlenderExecutionError,
    SENTINEL_START,
    SENTINEL_END,
    ALL_163_DEF_BONES,
    ALL_SEVEN_COLLECTIONS,
    ARKIT_52_BLENDSHAPES,
)
`
Existing unit tests, MCP tools, and external scripts will observe zero breaking changes.

---

## 8. Strict Backward-Compatibility Invariants

Any refactoring, decomposition, or modularization of MorphoMesh MUST adhere to the following six strict invariant sets:

### Invariant Set 1: FastMCP Tool Signatures & Behavior
1. **Tool Names Verbatim:** All 19 tool names must match verbatim (morphomesh_generate_concept through morphomesh_critique_visual_quality).
2. **Parameter Contracts:** All parameter names, types, ordering, and default values must remain identical. No parameters may be removed or made mandatory.
3. **Pydantic Model Coercion:** All input validations and bounds checks in morphomesh.models must continue to validate parameter bounds (e.g. focal length 10.0 to 300.0, margin 0.0 to 1.0, clearance tolerance >= 0.0).
4. **Return Types:** Every tool must return a Python dictionary (Dict[str, Any]) matching its authoritative JSON schema.
5. **Exception Handling:** Unhandled tool exceptions must raise ToolError(f"MorphoMesh Tool Error: [{e.code}] {e.message}") or ToolError(f"Unexpected Tool Failure in <tool_name>: {str(e)}").
6. **Direct Function Callable:** Tool functions in morphomesh.server must remain importable and directly awaitable (wait morphomesh_create_3d_asset(...)).

### Invariant Set 2: Environment Variable Gating
1. **Default State:** When MORPHOMESH_INCLUDE_* env vars are unset, wait mcp.list_tools() must return EXACTLY the 7 canonical creature tools (CREATURE_TOOL_NAMES).
2. **Matrix Permutations:** Setting MORPHOMESH_INCLUDE_HUMAN_TOOLS=1 yields 14 tools; MORPHOMESH_INCLUDE_INSPECTION_TOOLS=1 yields 10 tools; MORPHOMESH_INCLUDE_ALL_TOOLS=1 yields 17 tools; MORPHOMESH_INCLUDE_ANIMATION_TOOLS=1 adds 2 tools.
3. **Fuzzing Robustness:** Gating must accept all truthy tokens (1, 	rue, yes, ll in any case or whitespace) and ignore falsy tokens ( , alse, 
one, empty string).
4. **Low-Level RPC Parity:** mcp._mcp_server.request_handlers[mcp_types.ListToolsRequest] must return the identical filtered tool set as mcp.list_tools().
5. **Call-Tool Invocation:** Gated-out tools must remain directly invocable via mcp.call_tool().

### Invariant Set 3: Public Export & __all__ Surface
1. **morphomesh.__all__:** Must continue to contain all 40 symbols listed in Section 4.1.
2. **Error Code Constants:** All 26 error code constants (ERR_BLENDER_UNAVAILABLE, ERR_PARSE_ERROR, etc.) must remain accessible via rom morphomesh import ....
3. **FastMCP Server Import:** External code doing rom morphomesh.server import mcp, create_mcp_server, blender_bridge, ALL_TOOL_NAMES, ... must resolve cleanly without circular imports.
4. **No Circular Imports:** Modular subpackages must avoid circular dependencies between 	ools, ridge, models, and connectors.

### Invariant Set 4: Socket IPC Protocol & Command Schema
1. **Host and Port:** Default must remain 127.0.0.1:9876.
2. **Framing:** Must strictly use NDJSON (newline-terminated UTF-8 byte lines).
3. **Dual Identification:** Outgoing request payloads must include both "method" and "type".
4. **Dual Method Aliasing:** The bridge and listener must recognize both prefixed (morphomesh.<cmd>) and short (<cmd>) command names across all 20 commands.
5. **JSON-RPC 2.0 Responses:** Successful responses must contain "jsonrpc": "2.0", "status": "success", and "result": {...}. Errors must contain "status": "error", and "error": {"code": ..., "message": ...}.
6. **Main Thread Execution:** All commands received by the listener must execute on Blender's main thread via py.app.timers. The timer interval must return  .02.
7. **Immortal Timer:** Unhandled exceptions during command dispatch must never crash or unregister Blender's main timer loop.

### Invariant Set 5: Headless CLI Runner & Sentinel Extraction
1. **Headless Fallback:** If the interactive socket is not connected, commands must automatically fall back to headless CLI script execution (_dispatch_headless).
2. **Sentinel Delimiters:** Headless scripts must emit JSON results between SENTINEL_START = 'MORPHOMESH_START_JSON' and SENTINEL_END = 'MORPHOMESH_END_JSON'.
3. **Binary Discovery:** _resolve_blender_binary() must search standard installation directories on macOS, Linux, and Windows, honoring BLENDER_PATH and BLENDER_BIN_PATH environment variables.

### Invariant Set 6: AST Static Analysis & Security
1. **BpyCodeValidator:** Must enforce script length <= 10,000 characters and reject any script attempting to import forbidden modules or invoke forbidden functions (eval, exec, open, subprocess).
2. **SecurityException:** Must be raised on security violations and mapped to ERR_SCRIPT_SECURITY_VIOLATION (-32006).
3. **Server-Side Redundancy:** The Blender listener's AddonSecurityValidator must continue to validate all received scripts before evaluation.
