# Handoff Report: Milestone M1 Research & Benchmark Review

**Agent**: Challenger 1 (`challenger_m1_1`)  
**Role**: Empirical Challenger (Critic & Specialist)  
**Target Document**: `docs/RESEARCH_BENCHMARK.md` (`MM-R1-BENCHMARK-001`)  
**Recipient**: Parent Orchestrator (`orchestrator_1`)  
**Verdict**: **REQUEST_CHANGES**  

---

## 1. Observation

Direct empirical observations and reproduction traces from testing `docs/RESEARCH_BENCHMARK.md` against Blender 5.2.1 LTS and Python 3.11:

### 1.1 Blender Python Runtime Crashes
- **File**: `docs/RESEARCH_BENCHMARK.md`
- **Lines 1014 & 1019**:
  ```python
  bpy.ops.armature.metarig_sample_add(type='wolf')
  bpy.ops.armature.metarig_sample_add(type='bird')
  ```
  - Command: `/Applications/Blender.app/Contents/MacOS/Blender --background --python-expr "..."`
  - Verbatim Error:
    ```
    RuntimeError: Operator bpy.ops.armature.metarig_sample_add.poll() failed, context is incorrect
    ```
- **Lines 1030–1038**:
  ```python
  for side in ['L', 'R']:
      wing_shoulder = eb.get(f"shoulder.{side}")
      if wing_shoulder and spine_chest:
          wing_shoulder.parent = spine_chest
          wing_shoulder.use_connect = False
  ```
  - Directly Observed: Joining the bird metarig into the wolf metarig renames duplicate bones. Wolf's front leg shoulder remains `shoulder.L` / `shoulder.R`, while the bird's wing shoulder is automatically renamed to `shoulder.L.001` / `shoulder.R.001`. `eb.get("shoulder.L")` selects the quadruped's front legs instead of the wings.
- **Lines 1042–1045**:
  ```python
  bpy.ops.pose.rigify_generate()
  production_rig = bpy.data.objects.get("rig")
  production_rig.name = f"{creature_obj_name}_Rig"
  ```
  - Verbatim Output:
    ```
    Info: Successfully generated: "RIG-MetaRig_Chimera"
    production_rig is: None
    AttributeError: 'NoneType' object has no attribute 'name'
    ```
- **Lines 1225–1226**:
  ```python
  mat = low_obj.active_material
  tex_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
  ```
  - Verbatim Error:
    ```
    AttributeError: 'NoneType' object has no attribute 'node_tree'
    ```
  - Observed: Newly imported or retopologized objects have `low_obj.active_material == None`.

### 1.2 License Misclassifications
- **Table 2.1 (Lines 241–242) and Section 5.1 (Line 756)**:
  - Text: `MeshAnything & MeshAnything V2` -> `Apache 2.0 (Permissive Commercial)`.
  - Verbatim official license: Both models are governed by the **S-Lab License 1.0 (Non-commercial research only)**.
- **Table 2.1 (Line 228) and Section 4.2 (Line 546)**:
  - Text: `TRELLIS.2 (4B)` -> `Apache 2.0 (Permissive Commercial)`.
  - Verbatim official license: Microsoft's TRELLIS repository is **MIT License**, but incorporates dependencies (`nvdiffrast`) governed by NVIDIA's Non-Commercial Source Code License.
- **Table 2.1 (Lines 229–230) and Sections 4.3 & 4.4**:
  - Text: `Tencent Hunyuan Community License (<100M MAU)`.
  - Verbatim official license terms: Explicitly excludes commercial use in the **European Union, United Kingdom, and South Korea**.

### 1.3 Hardware Execution Discrepancies
- **Lines 195, 870, 889, 913**:
  - Claims Apple Silicon executes TRELLIS.2 and MeshAnything V2 in 38m 45s and 26m 15s via "CPU fallback with AVX emulation".
  - Command: `python3 -m pip install --dry-run spconv nvdiffrast` on macOS Darwin arm64.
  - Verbatim Result:
    ```
    ERROR: Could not find a version that satisfies the requirement spconv (from versions: none)
    ERROR: No matching distribution found for spconv
    ```
  - Observed: Neither `spconv` nor `nvdiffrast` have wheels or compile on macOS Darwin arm64. Stock TRELLIS.2 and MeshAnything V2 do not execute on Mac CPU; they fail on import.

---

## 2. Logic Chain

1. **Premise 1**: Code snippets in production architecture documents serve as foundational implementation specifications. If an operator fails to poll or targets the wrong bone hierarchy, downstream code generation and bridge runners will inherit fatal bugs.
   - *Supported by Observation 1.1*: `bpy.ops.armature.metarig_sample_add` fails in Object mode; `eb.get("shoulder.L")` erroneously reparents the wolf legs; `bpy.data.objects.get("rig")` returns `None` and crashes.
2. **Premise 2**: Legal and licensing compliance is a mandatory release criterion. Mislabling a non-commercial academic research model (S-Lab License 1.0) as permissive commercial (`Apache-2.0`) exposes commercial studios to intellectual property liability.
   - *Supported by Observation 1.2*: MeshAnything V2 and TRELLIS.2 dependencies are non-commercial; Tencent Hunyuan restricts deployment in the EU, UK, and South Korea.
3. **Premise 3**: Hardware trade-off proofs must rely on verified technical characteristics. Claiming that an ARM64 chip runs CUDA-dependent models in 38 minutes via "AVX emulation" undermines technical credibility when the packages cannot be installed on macOS.
   - *Supported by Observation 1.3*: `spconv` and `nvdiffrast` have no Darwin ARM64 support, completely preventing local CPU execution and proving that a remote tier is an absolute hard dependency rather than merely a latency optimization.
4. **Conclusion**: `docs/RESEARCH_BENCHMARK.md` must be updated with corrected code snippets, accurate licensing data, and technically sound hardware execution notes prior to final M1 sign-off.

---

## 3. Caveats

- **Breadth of Survey**: The document surveys 33 model variants across 29 frameworks, comfortably exceeding the >= 20 model requirement in `ORIGINAL_REQUEST.md`.
- **Architectural Soundness**: The core recommendation of a **Hybrid Architecture** (Remote GPU inference + Local Apple Silicon Blender / Rigify) is fundamentally sound and empirically reinforced by the lack of macOS CUDA kernel support.
- **Non-blocking Snippet**: Snippet 2 (`wire_pbr_principled_bsdf`) and Snippet 3 (`align_metarig_to_landmarks`) executed successfully in Blender 5.2.1 LTS without syntax or API breakage.

---

## 4. Conclusion

**Verdict: REQUEST_CHANGES**

The author or orchestrator must apply seven scoped corrections to `docs/RESEARCH_BENCHMARK.md`:
1. **Fix `assemble_fantasy_chimera_rig`**: Use `bpy.ops.object.armature_wolf_metarig_add()` and `bpy.ops.object.armature_bird_metarig_add()`, resolve `.001` wing bone collisions, and retrieve the generated rig via `f"RIG-{metarig.name}"` or `metarig.data.rigify_target_rig`.
2. **Fix `bake_high_to_low_poly`**: Add defensive handling to create and assign a new material when `low_obj.active_material` is `None`.
3. **Correct MeshAnything V2 License**: Update Table 2.1 and Section 5.1 from `Apache-2.0` to **S-Lab License 1.0 (Non-commercial research only)**.
4. **Correct TRELLIS.2 License**: Update Table 2.1 and Section 4.2 to **MIT**, noting the `nvdiffrast` non-commercial dependency.
5. **Add Tencent Territorial Caveat**: Note the EU, UK, and South Korea commercial restrictions in Table 2.1 and Sections 4.3/4.4.
6. **Add SMAL/BARC Commercial Caveat**: In Section 7.3 Use-Case B, clarify that SMAL/BARC require commercial licensing from MPI and offer Blender Rigify as a pure open commercial fallback.
7. **Refine macOS Hardware Claims**: Clarify that `spconv` and `nvdiffrast` lack macOS wheels and compilation support, rendering local execution 100% blocked rather than functional via 38-minute CPU AVX emulation.

Detailed technical analysis and code diffs are preserved in `.agents/challenger_m1_1/analysis.md`.

---

## 5. Verification Method

To independently verify these findings:

1. **Verify Blender Operator Failure**:
   ```bash
   /Applications/Blender.app/Contents/MacOS/Blender --background --python-expr "
   import bpy
   bpy.ops.preferences.addon_enable(module='rigify')
   bpy.ops.armature.metarig_sample_add(type='wolf')
   "
   ```
   *Expected result*: `RuntimeError: Operator bpy.ops.armature.metarig_sample_add.poll() failed, context is incorrect`.

2. **Verify Rigify Generated Rig Name**:
   ```bash
   /Applications/Blender.app/Contents/MacOS/Blender --background --python-expr "
   import bpy
   bpy.ops.preferences.addon_enable(module='rigify')
   bpy.ops.object.armature_wolf_metarig_add()
   metarig = bpy.context.active_object
   metarig.name = 'MetaRig_Chimera'
   bpy.ops.pose.rigify_generate()
   print('get rig:', bpy.data.objects.get('rig'))
   print('get RIG-MetaRig_Chimera:', bpy.data.objects.get('RIG-MetaRig_Chimera'))
   "
   ```
   *Expected result*: `get rig: None`, `get RIG-MetaRig_Chimera: <bpy_struct, Object("RIG-MetaRig_Chimera")>`.

3. **Verify Normal Map Bake Crash on Unmaterialized Mesh**:
   ```bash
   /Applications/Blender.app/Contents/MacOS/Blender --background --python-expr "
   import bpy
   bpy.ops.mesh.primitive_cube_add()
   low_obj = bpy.context.active_object
   print('active_material:', low_obj.active_material)
   mat = low_obj.active_material
   mat.node_tree.nodes.new('ShaderNodeTexImage')
   "
   ```
   *Expected result*: `AttributeError: 'NoneType' object has no attribute 'node_tree'`.

4. **Verify Spconv / Nvdiffrast on macOS**:
   ```bash
   python3 -m pip install --dry-run spconv nvdiffrast
   ```
   *Expected result*: `ERROR: No matching distribution found for spconv`.
