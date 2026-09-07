# Adversarial Dispatch Challenger Report: Method Parity, Dispatch Robustness & Timer Immortality (M1_2)

**Document ID**: `MM-CHALLENGER-M1-2-REPORT`  
**Challenger**: Challenger M1_2 (Adversarial Dispatch Challenger: Method Parity & Concurrency)  
**Assigned Directory**: `e:\tool\mcp\MorphoMesh\.agents\challenger_m1_2`  
**Parent Orchestrator ID**: `577aaa33-6b3f-4ebc-93eb-fcc632d94bc9`  
**Date**: 2026-09-07T04:09:00Z  
**Verdict**: **REJECT** (4 concrete defects discovered; timer immortality & existing 13 dispatch methods approved, but method parity & fallback architecture incomplete)

---

## 1. Observation

### 1.1 Verified Strengths
1. **Timer Immortality Under Adversarial Exception Assault**:
   - In `blender_addon/morphomesh/listener.py` (`_drain_queue`, lines 225–305):
     ```python
     try:
         # queue draining and request dispatch
     except Exception as e_immortal:
         logger.critical(f"FATAL barrier trapped in _drain_queue: {e_immortal}", exc_info=True)
     finally:
         if self.running:
             return 0.02
         return None
     ```
     Tested with 8 distinct exception types (`ValueError`, `TypeError`, `RuntimeError`, `ZeroDivisionError`, `KeyError`, `IndexError`, `AttributeError`, `Exception`). In 100% of cases, `_drain_queue` caught the error, transmitted a standard JSON-RPC 2.0 error packet (`{"status": "error", "error": {"code": -32000, ...}}`), and returned `0.02`, keeping Blender's timer registered.
   - Tested malformed queue objects (non-tuples, bare strings, `None`, non-dict commands): in all cases, the exception was caught and `0.02` was returned.
   - Tested broken socket descriptors (`BrokenPipeError` / `ConnectionResetError` during `client.sendall`): inner and outer exception handlers prevented timer drop.
   - Tested catastrophic queue corruption (`command_queue.empty` monkeypatched to raise `RuntimeError`): trapped by top-level `e_immortal` barrier, returning `0.02`.
   - On `server.stop()`, `self.running` is set to `False` and `_drain_queue()` returns `None`, permitting clean timer unregistration by Blender.

2. **Implemented Method Robustness (13 methods)**:
   - All 13 methods implemented in `listener.py` (`morphomesh.ping`, `morphomesh.get_scene_status`, `morphomesh.execute_custom_script`, `morphomesh.auto_rig_human`, `morphomesh.setup_human_materials`, `morphomesh.groom_human`, `morphomesh.dress_human`, `morphomesh.assemble_master_character`, `morphomesh.render_preview`, `morphomesh.setup_inspector_camera`, `morphomesh.capture_viewport`, `morphomesh.critique_visual_quality`, `morphomesh.create_human_asset`) were tested with extreme boundary values (empty dicts, non-existent objects, custom vectors, invalid cameras, tight clearance limits) without crashing or raising uncaught exceptions out of `_drain_queue`.

### 1.2 Discovered Deficiencies & Vulnerabilities

#### Defect 1: Incomplete Method Parity (6 Core Creature Methods Missing from `listener.py`)
- **Location**: `blender_addon/morphomesh/listener.py` (`_dispatch`, lines 306–1302).
- **Observation**:
  `PROJECT.md` line 26 dictates:
  > *"| 3 | Socket RPC Dispatch Parity | Full `_dispatch` support in `listener.py` for all 18 core pipeline and inspection methods | M1 | Survey E1, E2, E3 |"*
  
  However, `listener.py` only implements 13 methods. The following 6 core creature generation pipeline methods exposed on `BlenderBridge` are completely omitted from `listener.py`:
  1. `morphomesh.optimize_topology`
  2. `morphomesh.create_armature`
  3. `morphomesh.setup_creature_fur`
  4. `morphomesh.evaluate_fur_ribbons`
  5. `morphomesh.setup_creature_materials`
  6. `morphomesh.generate_war_armor`
- **Impact**: Any direct socket RPC invocation of these 6 methods triggers line 1301 in `listener.py`:
  ```python
  else:
      raise ValueError(f"Unknown RPC method: {method}")
  ```

#### Defect 2: Fallback Script Rejection by `AddonSecurityValidator` (100% False Headless Fallback)
- **Location**: `blender_addon/morphomesh/listener.py` lines 36, 58–60 vs `src/morphomesh/blender_bridge.py` lines 734–2160.
- **Observation**:
  In `blender_addon/morphomesh/listener.py`:
  ```python
  FORBIDDEN_CALLS = {"eval", "exec", "__import__", "compile", "open", "input", "globals", "locals", "getattr", "setattr"}
  ```
  When direct RPC fails (e.g. for any of the 6 unhandled creature methods), `BlenderBridge.execute()` attempts fallback via `execute_code`:
  ```python
  script = self._generate_headless_script(method, params)
  res = self.send_socket_request("execute_code", {"code": script}, timeout=timeout)
  ```
  However, in `src/morphomesh/blender_bridge.py`, `_generate_headless_script()` emits helper routines such as `ensure_auto_camera()` and object queries that explicitly invoke `getattr()`:
  - Line 837: `"lens_focal_length": getattr(c.data, 'lens', 50.0)`
  - Line 841: `"type": getattr(l.data, 'type', 'POINT'), "energy": getattr(l.data, 'energy', 10.0)`
  - Line 631: calls `open(out_mesh, "wb")`
  - Line 700: `from morphomesh.human_generator import ...`
  
  When `execute_code` is dispatched, line 392 calls `self.validator.validate(code)`.
  The validator immediately raises:
  ```
  ValueError: Forbidden built-in call: getattr()
  ```
- **Empirical Proof**:
  Running `validator.validate()` across all scripts generated by `_generate_headless_script()` resulted in **100% rejection** (18 out of 18 scripts rejected).
  Consequently, `execute()` logs:
  `"Interactive socket execute_code failed ([ERR_BLENDER_EXECUTION_FAILED] Blender Socket Error: Forbidden built-in call: getattr()), falling back to headless runner."`
  and ALWAYS falls back to the heavy headless CLI subprocess, completely negating interactive socket acceleration.

#### Defect 3: Missing `objects` in `BlenderBridge.execute()` Fallback Predicate
- **Location**: `src/morphomesh/blender_bridge.py` lines 537–553 vs Worker M1 Handoff Report line 34, 81.
- **Observation**:
  Worker M1 claimed in `handoff.md`:
  > *"Expanded success predicate to check for ... 'objects' in res"*
  
  The actual code in `src/morphomesh/blender_bridge.py` is:
  ```python
  if isinstance(res, dict) and not (
      res.get("status") == "error"
      or res.get("success") is False
      or "error" in res
  ) and (
      res.get("status") == "success"
      or res.get("success") is True
      or "object_count" in res
      or "blender_version" in res
      or "image_path" in res
      or "camera_name" in res
      or "defects" in res
      or "defect_count" in res
      or "scene_name" in res
      or ("status" in res and res.get("status") != "error")
  ):
  ```
  The key `"objects"` is **NOT** present in the predicate. Any valid dictionary response providing `{"objects": [...]}` without `"scene_name"` or `"object_count"` will fail the check and trigger false fallback to headless CLI (empirically confirmed in `test_execute_code_fallback_predicate_analysis`).

#### Defect 4: Missing Module-Level Import in `src/morphomesh/character_assembler.py`
- **Location**: `src/morphomesh/character_assembler.py` lines 51–56, line 1574.
- **Observation**:
  At the top of `character_assembler.py`:
  ```python
  try:
      import bpy
      HAS_BPY = True
  except (ImportError, ModuleNotFoundError):
      HAS_BPY = False
  ```
  Notice `mathutils` is not imported.
  At line 1574:
  ```python
  if HAS_BPY:
      script = self.get_assembly_script(output_blend_path=target_output)
      local_scope = {"bpy": bpy, "math": math, "mathutils": mathutils}
      exec(script, local_scope, local_scope)
  ```
  When executed in an environment where `bpy` is present, calling `morphomesh.assemble_master_character` raises:
  ```
  NameError: name 'mathutils' is not defined
  ```

---

## 2. Logic Chain

1. **Premise**: PROJECT.md Milestone 1 and Feature 3 mandate full socket RPC parity across all 18 core pipeline and inspection methods, eliminating false headless CLI fallbacks.
2. **Observation**: Direct inspection of `blender_addon/morphomesh/listener.py` reveals only 13 methods implemented; 6 creature methods (`optimize_topology`, `create_armature`, `setup_creature_fur`, `evaluate_fur_ribbons`, `setup_creature_materials`, `generate_war_armor`) are unhandled and raise `ValueError: Unknown RPC method`.
3. **Observation**: When direct RPC fails, `BlenderBridge.execute()` attempts fallback via `execute_code`.
4. **Observation**: `_generate_headless_script()` emits Python code containing `getattr()`, `open()`, and `from morphomesh... import...`.
5. **Observation**: `AddonSecurityValidator` in `listener.py` explicitly forbids `getattr` and `open`.
6. **Inference**: Every single `execute_code` fallback attempt is rejected by the server AST validator.
7. **Conclusion**: When Blender is open and interactive, calling any of the 6 creature methods will ALWAYS fail both direct RPC and `execute_code`, triggering an expensive, unrequested headless Blender subprocess.
8. **Inference**: Milestone 1 does not satisfy the parity and non-fallback criteria. Therefore, the work product must be **REJECTED**.

---

## 3. Caveats

1. **Live Blender GUI Rendering vs Mock Environment**:
   Automated testing was conducted using the project's standard `mock_bpy_environment` with real TCP sockets and threading. Live GPU viewport grabs were not executed against an active X11/Win32 display server, but the socket protocol framing, queue dispatch, AST validation, and return structures were evaluated under real network and thread conditions.
2. **Worker M1's Scoping Focus**:
   Worker M1 successfully remediated the 5 critical baseline bugs documented in their handoff report (NDJSON line buffering, timer immortality barrier, `mathutils.bvhtree` scoping, and basic inspection methods). However, their focus was limited to the 6 newly introduced digital human / inspection methods, neglecting the 6 creature methods required by PROJECT.md Feature 3.

---

## 4. Conclusion

**Verdict**: **REJECT**

While Worker M1 achieved substantial progress on timer immortality, NDJSON framing, and the digital human methods, the interactive socket subsystem fails on four critical fronts:
1. **Omission of 6 core creature pipeline methods** from `listener.py` (`optimize_topology`, `create_armature`, `setup_creature_fur`, `evaluate_fur_ribbons`, `setup_creature_materials`, `generate_war_armor`).
2. **Incompatibility between `_generate_headless_script()` and `AddonSecurityValidator`**: Fallback scripts violate server security rules (`getattr` forbidden), causing 100% of fallback socket requests to fail and trigger headless CLI.
3. **Omission of `"objects" in res`** in `BlenderBridge.execute()`'s success predicate.
4. **`NameError: name 'mathutils' is not defined`** in `character_assembler.py` line 1574 during live `bpy` execution.

### Actionable Remediations for Worker M1 Remediation Turn:
1. In `blender_addon/morphomesh/listener.py`:
   - Add dispatch handlers for the 6 missing creature methods in `_dispatch()`.
   - Update `AddonSecurityValidator`: allow `getattr` and `open` (or allow internal MorphoMesh scripts by signing/tagging or permitting safe `getattr` calls on Blender datablocks).
2. In `src/morphomesh/blender_bridge.py`:
   - Add `"objects" in res` to the success predicate in `execute()`.
3. In `src/morphomesh/character_assembler.py`:
   - Add `import mathutils` under `try: import bpy ...` at the top of the file.

---

## 5. Verification Method

### 5.1 Run Adversarial Test Suite
```powershell
.venv\Scripts\pytest tests/test_adversarial_dispatch_m1_2.py -v
```
**Expected Result**: 24 passed in ~17s (100% pass).

### 5.2 Run Combined Bridge & Parity Test Suites
```powershell
.venv\Scripts\pytest tests/test_bridge_socket_parity.py tests/test_blender_bridge.py tests/test_adversarial_dispatch_m1_2.py -q
```
**Expected Result**: 124 passed in ~35s (100% pass).

### 5.3 Invalidation Conditions
- Any failure in `tests/test_adversarial_dispatch_m1_2.py`.
- Any socket request failing to return `0.02` upon unhandled method exceptions.
- Any direct RPC call for creature methods succeeding in `listener.py` without implementation.
