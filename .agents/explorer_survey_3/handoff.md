# Handoff Report: Auto-Critic Visual QA & Verification Suite Explorer (R2 & R4 Survey)

**Agent**: Explorer 3 (`explorer_survey_3`)  
**Parent Orchestrator Conversation ID**: `577aaa33-6b3f-4ebc-93eb-fcc632d94bc9`  
**Date**: 2026-09-07T03:50:00Z  
**Handoff Type**: Hard Handoff (Investigation Complete)  
**Deliverable**: Technical Architecture, Mathematical Formulations, Schemas & Test Suite Specifications for R2 (Auto-Critic QA) & R4 (Verification Suite)

---

## 1. Observation

1. **Current Codebase & Test Suite Status**:
   - Running `pytest -q` in the repository root (`e:\tool\mcp\MorphoMesh`) executed 749 collected tests across 38 test files, resulting in:
     ```
     743 passed, 6 skipped in 100.51s (0:01:40)
     ```
     The command exited with code `0`. Zero test failures exist.
   - The 6 skipped tests are `bpy`-dependent tests (`verify_master_blend_deep.py`, `verify_geometry_props_deep.py`, etc.) that gracefully skip when executed in standalone Python without a running Blender context.

2. **Existing Inspection Scripts and Geometric Utilities**:
   - In `tests/inspect_penetration.py` (lines 9–24), an empirical Signed Distance / Normal Dot product technique is already used for garment penetration:
     ```python
     bm_body = bmesh.new()
     bm_body.from_mesh(body_obj.data)
     bm_body.transform(body_obj.matrix_world)
     bvh = mathutils.bvhtree.BVHTree.FromBMesh(bm_body)
     for idx, v in enumerate(bodice_verts):
         loc, normal, f_idx, dist = bvh.find_nearest(v)
         if loc is not None:
             offset = v - loc
             dot = offset.dot(normal)
             if dot < 0:
                 penetrations.append((idx, v, loc, normal, dist, dot))
     ```
   - In `tests/verify_geometry_props_deep.py` (lines 14–34 and 49–67), BMesh face topology audits (quad percentage, non-manifold edges, zero-area faces) and KDTree proximity checks (`mathutils.kdtree.KDTree`) are established.
   - In `src/morphomesh/wardrobe.py` (lines 59 and 81), radial clearance offset $\Delta r = 0.015\text{m}$ (15mm) was parameterized to eliminate body clipping during initial procedural generation.

3. **Blender Bridge & Socket Listener Parity Gaps**:
   - In `blender_addon/morphomesh/listener.py` (lines 218–556), the `_dispatch` method handles:
     `morphomesh.ping`, `morphomesh.get_scene_status`, `morphomesh.execute_custom_script`, `morphomesh.auto_rig_human`, `morphomesh.setup_human_materials`, `morphomesh.groom_human`, `morphomesh.dress_human`, `morphomesh.assemble_master_character`.
   - **Critical Parity Gap**: `morphomesh.render_preview` is present in `blender_bridge.py` (lines 2085–2117) and handled in headless mode (line 1023), but is **completely missing** from `listener.py`'s interactive socket dispatcher!
   - Neither `listener.py` nor `blender_bridge.py` currently implement `morphomesh.critique_visual_quality`, `morphomesh.capture_viewport`, or automated multi-angle camera rig setups.

4. **FastMCP Tool Discovery & Legacy Schema Isolation**:
   - In `tests/test_tools_schema.py` (lines 42–65), `test_all_seven_tools_registered` asserts that `mcp.list_tools()` returns exactly the 7 legacy creature tools.
   - In `src/morphomesh/server.py` (lines 1105–1135), an environment-variable filter `_filtered_list_tools` gates new tools (`MORPHOMESH_INCLUDE_HUMAN_TOOLS`), allowing human tools to pass in `tests/test_fastmcp_human_tools.py` while preventing legacy test breakages.

---

## 2. Logic Chain

1. **Defect Detection Architecture (R2)**:
   - *From Observation 2*: The Signed Distance calculation ($s_i = (w_i - p_i) \cdot \hat{n}_i$) is mathematically sound, fast ($O(N \log M)$ via BVHTree), and natively supported by Blender's `mathutils.bvhtree.BVHTree`.
   - *Therefore*: Garment clipping detection must combine `bvh.find_nearest()` for penetration depth and `bvh.ray_cast()` for body bursting through cloth, categorized by penetration depth: $\ge 5\text{mm}$ (Critical), $1\text{mm} - 5\text{mm}$ (Major), $< 1\text{mm}$ (Minor).
   - *For Body Proportions*: Canonical landmark ratios ($R_{\text{head}} = H_{\text{total}} / H_{\text{head}}$ and $W_{\text{shoulder}} / W_{\text{hip}}$) provide objective baselines. For Yu Nian An ($1.65\text{m}$ height, $7.41$ head ratio), deviations $|\Delta R| > 0.5$ must be flagged as `proportion_deviation` with specific resizing recommendations.
   - *For Skinning Pinching*: Local volume preservation via divergence theorem ($\rho_V = V_{\text{posed}} / V_0$) combined with dihedral angle crease detection ($\cos \theta < -0.85$) accurately isolates candy-wrapper collapse.
   - *For Grooming Intersections*: Sampling hair curve splines at 5mm intervals and projecting points against body/garment BVH trees directly detects submerged roots ($s_0 < -1\text{mm}$) and intersecting hair bodies ($s_k < -0.5\text{mm}$).

2. **Diagnostic Schema & Closed Loop (R2)**:
   - *From Observation 3*: Agents need structured, typed data to take corrective action.
   - *Therefore*: A Pydantic v2 schema (`CritiqueVisualQualityOutput`) containing `defects: List[DefectItem]` with `DefectClassification` (`clipping`, `proportion_deviation`, `skinning_artifact`, `grooming_penetration`), `DefectSeverity`, `BoundingBox3D`, and `recommendations: List[ActionableRecommendation]` allows agents to automatically adjust parameters (e.g. increase clearance offset, enable dual quaternion preserve volume, or offset hair roots).

3. **Interactive Socket Parity & Camera Rig (R1, R3)**:
   - *From Observation 3*: `morphomesh.render_preview` and the new `morphomesh.capture_viewport` and `morphomesh.critique_visual_quality` must be registered in `listener.py`'s `_dispatch` method so they can execute directly in Blender's main thread via `bpy.app.timers`.
   - *Therefore*: Implementing full parity between `blender_bridge.py` and `listener.py` eliminates socket dispatch errors and enables fast viewport captures ($<50\text{ms}$ via `bpy.ops.render.opengl`).

4. **Test Suite Design & 100% Pass Rate (R4)**:
   - *From Observation 1 & 4*: The baseline pass rate is 100% (743 passed). To maintain this without regression:
     * New tests must reside in dedicated test files: `test_inspector_camera.py`, `test_multiview_rendering.py`, `test_visual_critic.py`, `test_socket_bridge_parity.py`, and `test_fastmcp_inspection_tools.py`.
     * New FastMCP tools in `server.py` must use the established tool filtering pattern (`MORPHOMESH_INCLUDE_INSPECTION_TOOLS` or expanding `ALL_TOOL_NAMES`) so `test_tools_schema.py` continues to pass unconditionally.

---

## 3. Caveats

1. **Blender Live Context Dependency**:
   - In pure CI / offline environments without a running Blender instance or without `bpy` compiled for Python, camera rendering and live mesh evaluation must execute against the mock adapter and headless script generator. All test fixtures must support headless / mock fallback.
2. **Dynamic Cloth Simulation & Physics**:
   - The current survey focuses on geometric and rigged pose deformation critique. Complex cloth simulation baking (e.g. dynamic cloth draping over 100 frames) requires frame-by-frame critique, which is scoped for subsequent animation passes.
3. **Sub-millimeter Contact Tolerances**:
   - Snug-fitting garments (e.g. waist sash) naturally touch body vertices at zero clearance. A threshold of $\epsilon_{\text{tol}} = 0.5\text{mm}$ is recommended to avoid false-positive clipping flags on resting contacts.

---

## 4. Conclusion

1. **Feasibility Confirmed**:
   The Auto-Critic QA system and automated verification suite are fully feasible using Blender 4.5+/5.2.1 LTS native `mathutils.bvhtree.BVHTree`, `mathutils.kdtree.KDTree`, BMesh volume integration, and FastMCP.
2. **Comprehensive Specifications Delivered**:
   The complete engineering report `survey_report.md` in this directory provides:
   - Mathematical formulations for clipping, proportions, skinning pinching, and grooming penetration.
   - Pydantic v2 data models for `CritiqueVisualQualityInput` and `CritiqueVisualQualityOutput`.
   - Four intentional defect test fixtures for empirical baseline validation.
   - Module blueprints for the 5 new verification test files.
   - Exact socket RPC method signatures for `listener.py` and `blender_bridge.py`.
3. **Execution Ready**:
   The downstream implementation worker agents can directly implement the specified modules with zero architectural ambiguity.

---

## 5. Verification Method

To independently verify the findings of this survey:

1. **Verify Baseline Test Suite Health**:
   ```powershell
   cd e:\tool\mcp\MorphoMesh
   pytest -q
   ```
   *Expected Result*: 743 passed, 6 skipped, exit code 0.

2. **Inspect Existing Penetration and Clearance Audit Logic**:
   - Inspect `tests/inspect_penetration.py` (lines 9–29) for the signed distance BVHTree implementation.
   - Inspect `tests/verify_geometry_props_deep.py` (lines 36–67) for bodice clearance validation.

3. **Verify Interactive Socket Listener Parity Gap**:
   - Inspect `blender_addon/morphomesh/listener.py` (lines 218–556). Confirm that `morphomesh.render_preview` is absent from `_dispatch()`.

4. **Inspect Comprehensive Survey Report**:
   - Inspect `e:\tool\mcp\MorphoMesh\.agents\explorer_survey_3\survey_report.md` for full mathematical details, Pydantic schemas, and test suite blueprints.
