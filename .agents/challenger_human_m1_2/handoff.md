# Handoff Report — challenger_human_m1_2: Adversarial Review & Stress Testing (Milestone 1)

## 1. Observation

1. **Target Artifacts & Review Scope**:
   - `src/morphomesh/server.py` (FastMCP server with 5 new human tools: `morphomesh_create_human_asset`, `morphomesh_auto_rig_human`, `morphomesh_setup_human_materials`, `morphomesh_groom_human`, `morphomesh_dress_human`).
   - `src/morphomesh/blender_bridge.py` (Dual-mode IPC, TCP socket communication on port 9876, headless CLI script generation, procedural fallbacks).
   - `src/morphomesh/models.py` (Pydantic v2 input/output schemas, bounds validation).
   - `tests/test_adversarial_fastmcp_bridge_human.py` (Adversarial stress harness with 68 test cases).

2. **Empirical Verification Outputs**:
   - Running full adversarial test harness:
     ```powershell
     $env:PYTHONPATH="src"
     & "C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe" -m pytest tests/test_adversarial_fastmcp_bridge_human.py -v
     ```
     Result: **`68 passed in 9.00s`** (100% pass rate).
   - Running full regression test suite (worker unit tests + adversarial suite):
     ```powershell
     $env:PYTHONPATH="src"
     & "C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe" -m pytest tests/test_fastmcp_human_tools.py tests/test_human_generator.py tests/test_adversarial_fastmcp_bridge_human.py -v
     ```
     Result: **`98 passed in 13.05s`** (100% pass rate).

3. **Confirmed Robustness Aspects**:
   - **Parameter Boundary Enforcement**: Pydantic v2 schemas in `src/morphomesh/models.py` strictly reject out-of-bounds inputs:
     - `height`: Out of range values (`-1.0`, `0.0`, `0.5`, `0.99`, `2.51`, `5.0`, `NaN`, `Inf`) are caught and raise `ToolError`.
     - `head_ratio`: Out of range values (`-5.0`, `0.0`, `3.0`, `4.99`, `10.01`, `15.0`, `NaN`, `Inf`) are caught and raise `ToolError`.
     - `chest_girth`, `waist_girth`, `hip_girth`: Out of range values are caught and raise `ToolError`.
     - `poly_budget`: Values `< 1000` or `> 200000` are caught and raise `ToolError`.
     - `strand_count`: Values `< 1000` or `> 200000` are caught and raise `ToolError`.
     - `butterfly_count`: Values `< 1` or `> 50` are caught and raise `ToolError`.
     - `clearance_offset`: Values `< 0.005` or `> 0.05` are caught and raise `ToolError`.
   - **Exception Containment**: In `src/morphomesh/server.py`, all 5 human tools wrap errors in `try ... except MorphoMeshException as e: raise ToolError(...) except Exception as e: raise ToolError(...)`. No uncaught exceptions escape or crash the FastMCP server when invoking via `mcp.call_tool()`.
   - **Context Logging Resilience**: When `ctx.info` or `ctx.report_progress` throws exceptions, `_safe_ctx_info` and `_safe_ctx_progress` safely swallow them without halting tool execution.
   - **Bridge Fallback Robustness**: When the socket is closed, when the socket server hangs, when socket bytes are corrupted, or when the socket server returns an RPC error, `BlenderBridge` cleanly recovers and executes the local procedural fallback.

4. **Specific Implementation Discrepancies & Confirmed Bugs (Direct Code Observations)**:

   - **Finding 1: `head_ratio` Parameter Dropped in `BlenderBridge.create_human_asset`**:
     - *Observation (`src/morphomesh/blender_bridge.py:2234-2260`)*:
       ```python
       def create_human_asset(self, ..., head_ratio: float = 7.41, ...):
           params = {
               "character_name": character_name,
               "gender": gender,
               "height": height,
               "style": style,
               "poly_budget": poly_budget,
               "include_blendshapes": include_blendshapes,
               "export_format": export_format,
               "load_into_scene": load_into_scene,
               "chest_girth": chest_girth,
               "waist_girth": waist_girth,
               "hip_girth": hip_girth,
               # NOTE: "head_ratio" IS MISSING FROM params DICTIONARY!
           }
       ```
       In the fallback block (lines 2252-2260):
       ```python
       cfg = HumanAnatomyConfig(
           height=height,
           gender=gender,
           style=style,
           poly_budget=poly_budget,
           chest_girth=chest_girth,
           waist_girth=waist_girth,
           hip_girth=hip_girth,
           # NOTE: head_ratio IS NOT PASSED TO HumanAnatomyConfig!
       )
       ```
     - *Empirical Test*: Calling `morphomesh_create_human_asset(head_ratio=8.5)` returns `"head_ratio": 7.41` (default) instead of `8.5`.

   - **Finding 2: `config: HumanAnatomyConfig` Object Ignored in `morphomesh_create_human_asset`**:
     - *Observation (`src/morphomesh/server.py:623-655`)*:
       When a user passes `config=HumanAnatomyConfig(height=1.85, head_ratio=8.2)`, the function signature's root defaults (`height=1.65`, `head_ratio=7.41`) populate `CreateHumanAssetInput`, and `blender_bridge.create_human_asset` is called with both root arguments and `config=req.config`. In `blender_bridge.py:2252`, `config` is ignored and replaced by `cfg = HumanAnatomyConfig(...)` built only from root parameters.
     - *Empirical Test*: Calling `morphomesh_create_human_asset(config=HumanAnatomyConfig(height=1.85))` returns `"height": 1.65`.

   - **Finding 3: `clearance_offset` Hardcoded to 0.015 in Headless Blender Script**:
     - *Observation (`src/morphomesh/blender_bridge.py:1951`)*:
       In `_generate_headless_script`:
       ```python
       emit_result({
           "status": "success",
           "outfit_preset": outfit_p,
           "garments": garments,
           "accessories": accessories,
           "prop_count": 10 + b_fly_count,
           "clearance_offset": 0.015, # NOTE: HARDCODED TO 0.015!
           "blend_file_path": None,
       })
       ```
     - *Empirical Test*: Calling `morphomesh_dress_human(clearance_offset=0.035)` returns `"clearance_offset": 0.015`.

   - **Finding 4: Phantom Non-Existent File on `export_format='fbx'` in `create_human_asset`**:
     - *Observation (`src/morphomesh/blender_bridge.py:1727-1734`)*:
       In headless script generator:
       ```python
       if export_fmt == "glb":
           bpy.ops.export_scene.gltf(filepath=out_mesh, export_format='GLB')
       elif export_fmt == "obj":
           if hasattr(bpy.ops.wm, "obj_export"):
               bpy.ops.wm.obj_export(filepath=out_mesh)
           else:
               bpy.ops.export_scene.obj(filepath=out_mesh)
       ```
       If `export_format='fbx'` is requested, neither branch executes. `out_mesh` is never written, yet the tool reports `status: success` with `mesh_path: .../Yu_Nian_An_xxxx.fbx`.
     - *Empirical Test*: `os.path.exists(res.get("mesh_path"))` is `False` when `export_format="fbx"`.

   - **Finding 5: Phantom Non-Existent File for `exported_mesh_path` in `auto_rig_human`**:
     - *Observation (`src/morphomesh/blender_bridge.py:1831-1844`)*:
       In `_generate_headless_script`:
       ```python
       tmp_dir = tempfile.gettempdir().replace('\\', '/')
       out_rig = f"{tmp_dir}/Yu_Nian_An_Rigged.{export_fmt}"
       emit_result({
           "status": "success",
           ...
           "exported_mesh_path": out_rig,
       })
       ```
       No `bpy.ops.export_scene.fbx` or export operator is ever called.
     - *Empirical Test*: `os.path.exists(res.get("exported_mesh_path"))` is `False`.

   - **Finding 6: `outfit_preset` Parameter Ignored in Local Fallback of `dress_human`**:
     - *Observation (`src/morphomesh/blender_bridge.py:2498`)*:
       ```python
       effective_outfit = outfit_preset or outfit # computed at line 2478
       ...
       except Exception as e:
           return {
               "status": "success",
               "outfit_preset": outfit, # NOTE: returns outfit instead of effective_outfit!
           }
       ```
     - *Empirical Test*: In procedural fallback, calling `bridge.dress_human(outfit_preset="court_dress")` returns `"outfit_preset": "yu_nian_an_dress"`.

   - **Finding 7: Broken Interactive Socket `execute_code` Fallback Due to Security Validator**:
     - *Observation (`src/morphomesh/blender_bridge.py:475-486`)*:
       When direct socket RPC fails, `execute` attempts:
       `script = self._generate_headless_script(method, params)`
       `res = self.send_socket_request("execute_code", {"code": script})`
       However, the generated headless script is ~67,400 characters (violating the 10,000 character maximum AST limit enforced by `BpyCodeValidator` and `AddonSecurityValidator`) and imports `os`, `sys`, `uuid`, `tempfile` (which are in `FORBIDDEN_MODULES`).
     - *Empirical Test*: `BpyCodeValidator().validate(script)` raises `SecurityException [ERR_SCRIPT_SECURITY_VIOLATION] Script exceeds maximum length of 10000 characters`. Consequently, interactive socket fallback to `execute_code` will always fail and incur an unnecessary socket round-trip before falling back to headless runner.

---

## 2. Logic Chain

1. **Safety & Containment Logic**:
   - *Premise*: An industrial-grade MCP server must reject invalid parameters and never crash or leak raw unhandled tracebacks to MCP clients.
   - *Observation*: Tests in `TestBoundaryAndInvalidInputs` and `TestFastMCPExceptionContainment` systematically tested negative, zero, out-of-range, NaN, and Inf values across all parameters, as well as throwing `Context` objects.
   - *Inference*: Pydantic v2 schemas and FastMCP `ToolError` exception wrappers successfully contain all errors. The server does not crash under malformed or adversarial inputs.

2. **Parameter Integrity Logic**:
   - *Premise*: If an MCP tool defines a parameter in its schema and accepts it from a client, the pipeline must propagate that parameter to underlying generators rather than silently dropping it and substituting defaults.
   - *Observation*: `head_ratio` was omitted from `params` in `create_human_asset` (Finding 1), `config` was overridden by root defaults (Finding 2), `clearance_offset` was hardcoded to 0.015 in headless output (Finding 3), and `outfit_preset` was bypassed in local fallback (Finding 6).
   - *Inference*: Clients attempting to customize proportions (e.g. 8.5 head ratio) or garment clearance (e.g. 0.035m) will receive successful return payloads that silently ignored their customization requests.

3. **File System Contract Logic**:
   - *Premise*: If a tool returns a dictionary containing file paths (`mesh_path`, `exported_mesh_path`), the file must actually be written to disk when reporting `"status": "success"`.
   - *Observation*: When requesting `export_format='fbx'` in `create_human_asset` (Finding 4), or when calling `auto_rig_human` (Finding 5), the returned paths do not exist on disk.
   - *Inference*: Downstream pipeline steps (e.g. import operators or packaging scripts) expecting these files will fail with `FileNotFoundError`.

---

## 3. Caveats

1. **Non-destructive Challenge Role**:
   - In accordance with the Review-Only constraint (`🔒 Key Constraints`), challenger agent has not modified any files in `src/morphomesh/`. The bugs are documented with exact file and line references for remediation by the worker agent.
2. **Interactive GUI Blender Session**:
   - Tests were conducted against both the live interactive socket listener (running on Blender 4.5.4 LTS) and headless CLI execution. Live GUI viewport rendering of hair curves was not interactively observed.

---

## 4. Conclusion & Verdict

### Verdict: **CHALLENGE**

While the FastMCP server layer and Pydantic validation boundaries are remarkably robust (preventing server crashes and enforcing data types), adversarial testing has uncovered **7 concrete implementation bugs** in `src/morphomesh/blender_bridge.py` and `src/morphomesh/server.py`:

1. **`head_ratio` parameter dropped** in `blender_bridge.create_human_asset` (`params` dict and fallback `cfg`).
2. **`config: HumanAnatomyConfig` object ignored** in `morphomesh_create_human_asset`.
3. **`clearance_offset` hardcoded to 0.015** in `_generate_headless_script` for `dress_human`.
4. **Phantom file path returned on `export_format='fbx'`** in `create_human_asset` (file not exported).
5. **Phantom file path returned for `exported_mesh_path`** in `auto_rig_human` (FBX not exported).
6. **`outfit_preset` ignored in local fallback** of `dress_human` (returns `outfit`).
7. **`_generate_headless_script` cannot pass `execute_code` AST security checks** (~67KB script > 10KB limit and forbidden imports).

**Recommendation**: Worker agent should apply targeted remediations in Milestone 1 remediation phase before proceeding to Milestone 2.

---

## 5. Verification Method

To reproduce and independently verify all 68 adversarial assertions:

```powershell
# Set PYTHONPATH to include src
$env:PYTHONPATH="src"

# Run the adversarial stress test suite
& "C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe" -m pytest tests/test_adversarial_fastmcp_bridge_human.py -v

# Run the full regression test suite
& "C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe" -m pytest tests/test_fastmcp_human_tools.py tests/test_human_generator.py tests/test_adversarial_fastmcp_bridge_human.py -v
```

Expected output:
- `tests/test_adversarial_fastmcp_bridge_human.py`: `68 passed in ~9s`.
- All suites: `98 passed in ~13s` (100% pass rate).
