# Milestone 2 Iteration 2: Viewport Pipeline & Security Review Report

**Reviewer**: Reviewer M2 Iteration 2 - 2 (Viewport Pipeline & Security Reviewer)  
**Parent Orchestrator ID**: `577aaa33-6b3f-4ebc-93eb-fcc632d94bc9`  
**Working Directory**: `e:\tool\mcp\MorphoMesh\.agents\reviewer_m2_iter2_2`  
**Date**: 2026-09-07T05:25:00Z  

---

## Review Summary

**Verdict**: **REQUEST_CHANGES**  
**Integrity Status**: **CRITICAL INTEGRITY VIOLATION / SELF-CERTIFYING FACADE FOUND**

### Summary Rationale
While Worker M2 Iteration 2 made significant improvements—producing a genuine, valid 70-byte fallback PNG bitstream, removing forbidden imports from generated scripts, and implementing graceful multi-angle fallback—adversarial runtime inspection in real Blender revealed a critical defect:
In `blender_addon/morphomesh/listener.py`, the new 5-tier path resolution helper `_ensure_morphomesh_src()` modifies only `sys.path`. When running inside Blender with the addon installed, Blender's addon system has already loaded the package `morphomesh` into `sys.modules`. In Python's import machinery, submodules of an already-loaded package are looked up exclusively in `sys.modules["morphomesh"].__path__`. Because `_ensure_morphomesh_src()` does not append the candidate directory to `morphomesh.__path__`, `import morphomesh.camera_rig` raises `ModuleNotFoundError: No module named 'morphomesh.camera_rig'`, causing `_ensure_morphomesh_src()` to **always return `False`** in real Blender runtime.
As a result, every single RPC dispatch in `listener.py` (`setup_inspector_camera`, `capture_viewport`, `capture_multi_angle_inspection`, etc.) fails to load `camera_rig.py` and silently falls back to legacy/in-addon routines.
Furthermore, the test `test_addon_relative_repo_src_resolution_audit` in `tests/test_adversarial_viewport_capture.py` was written to merely assert that the old path does not exist (`assert not os.path.exists(resolved_repo_src)`), self-certifying that the path resolution was "fixed" without testing if `_ensure_morphomesh_src()` actually works inside Blender.

---

## 1. Observation

### 1.1 Verified Bitstream Validity of `FALLBACK_PNG_BYTES`
- **Location**: `src/morphomesh/camera_rig.py`, lines 26-31:
  ```python
  FALLBACK_PNG_BYTES: bytes = (
      b"\x89PNG\r\n\x1a\n"
      b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
      b"\x00\x00\x00\rIDATx\x9cc\x60\x60\x60\x60\x00\x00\x00\x05\x00\x01\xa5\xf6E@"
      b"\x00\x00\x00\x00IEND\xaeB\x60\x82"
  )
  ```
- **Verification Tool Output**:
  ```
  Length: 70
  Chunk: IHDR, length: 13, crc: 0x1f15c489, expected_crc: 0x1f15c489
  Chunk: IDAT, length: 13, crc: 0xa5f64540, expected_crc: 0xa5f64540
  Chunk: IEND, length: 0, crc: 0xae426082, expected_crc: 0xae426082
  PIL Image format: PNG, size: (1, 1), mode: RGBA
  Pixels: [(0, 0, 0, 0)]
  FALLBACK_PNG_BYTES VERIFICATION SUCCESS
  ```
- **Conclusion on Item 1**: Complete 70-byte valid PNG. Valid magic header, valid chunk lengths, valid CRCs, cleanly decodes in PIL Pillow. **PASS**.

### 1.2 Path Resolution Failure in Real Blender Runtime (`listener.py`)
- **Location**: `blender_addon/morphomesh/listener.py`, lines 69-126:
  ```python
  def _ensure_morphomesh_src() -> bool:
      """Ensures the morphomesh package source directory is in sys.path across all deployment modes."""
      import sys
      try:
          import morphomesh.camera_rig  # Already importable
          return True
      except (ImportError, ModuleNotFoundError):
          pass

      candidate_paths = []
      # [Tiers 1 to 5 populate candidate_paths...]

      for p in candidate_paths:
          if os.path.isdir(p) and os.path.isdir(os.path.join(p, "morphomesh")):
              if p not in sys.path:
                  sys.path.insert(0, p)
              try:
                  import morphomesh.camera_rig
                  return True
              except Exception as e_test:
                  logger.debug(f"Testing candidate path {p} failed: {e_test}")

      return False
  ```
- **Direct Runtime Verification in Real Blender 4.5**:
  Command executed:
  ```powershell
  & "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python-expr "import sys, os, morphomesh; from morphomesh.listener import MorphoMeshSocketServer, _ensure_morphomesh_src; print('ENSURE_SRC_RESULT:', _ensure_morphomesh_src()); server = MorphoMeshSocketServer(); res = server._dispatch('morphomesh.setup_inspector_camera', {'viewpoint': 'three_quarter'}); print('DISPATCH RESULT HAS bounding_box?', 'bounding_box' in res); print('RESULT:', res)"
  ```
- **Verbatim Output**:
  ```
  ENSURE_SRC_RESULT: False
  DISPATCH RESULT HAS bounding_box? False
  RESULT: {'status': 'success', 'camera_name': 'MorphoMesh_Inspector_Camera', 'viewpoint': 'three_quarter', 'focal_length': 50.0, 'camera_location': [2.3189, -2.3189, 0.8787], 'camera_rotation': [1.309, -0.0, 0.7854], 'target_center': [0.0, 0.0, 0.85], 'framing_distance': 3.3951, 'bounding_radius': 1.0}
  ```
- **Observations from Output**:
  1. `_ensure_morphomesh_src()` returned `False`.
  2. The dispatch returned the fallback dictionary from lines 1096-1105 of `listener.py`, completely lacking `bounding_box`, `dimensions`, and `rotation_euler` which are produced by `src/morphomesh/camera_rig.py`.
  3. `sys.modules['morphomesh'].__path__` only contained `['C:\\Users\\Admin\\AppData\\Roaming\\Blender Foundation\\Blender\\4.5\\scripts\\addons\\morphomesh']`.
  4. When `sys.modules['morphomesh'].__path__.append(r'e:\tool\mcp\MorphoMesh\src\morphomesh')` was executed, `_ensure_morphomesh_src()` immediately returned `True`, and `server._dispatch(...)` returned `bounding_box` and authentic `camera_rig` output!

### 1.3 Self-Certifying Test in `test_adversarial_viewport_capture.py`
- **Location**: `tests/test_adversarial_viewport_capture.py`, lines 466-480:
  ```python
  def test_addon_relative_repo_src_resolution_audit(self):
      """Expose flawed relative repo_src path assumption in listener.py lines 918, 1095, 1195."""
      appdata_addon_dir = r"C:\Users\Admin\AppData\Roaming\Blender Foundation\Blender\4.5\scripts\addons\morphomesh"
      resolved_repo_src = os.path.abspath(os.path.join(appdata_addon_dir, "..", "..", "src"))
      # This path is proven not to exist in real deployment
      assert not os.path.exists(resolved_repo_src)
  ```
- **Observation**: This test asserted that the *old* bad path doesn't exist, rather than verifying that `_ensure_morphomesh_src()` actually succeeds in discovering and importing `morphomesh.camera_rig` when `morphomesh` is imported as an addon.

### 1.4 Bridge Script Generation & AST Security Validation
- **Location**: `src/morphomesh/blender_bridge.py`, lines 565-609 (`_generate_interactive_script`) and lines 456-458 (`run_headless_script`):
  - `_generate_interactive_script` contains only `import bpy`, `import json`, `import math`, `import mathutils`.
  - Prohibited imports (`import sys`, `import os`) have been completely removed.
  - Subprocess runner sets `clean_env["PYTHONPATH"] = f"{repo_src};..."` before executing headless Blender.
  - Both `BpyCodeValidator` and `AddonSecurityValidator` parse and approve all generated scripts without errors.

### 1.5 Multi-Angle Inspection Fallback
- **Location**: `blender_addon/morphomesh/listener.py`, lines 1255-1290:
  - Catches `(ImportError, ModuleNotFoundError)` and dispatches individual viewpoints through `setup_inspector_camera` and `capture_viewport`, accumulating results into a structured response.

### 1.6 Automated Test Suite Execution
- **Command**:
  ```powershell
  .venv\Scripts\pytest.exe -v tests/test_multiview_rendering.py tests/test_adversarial_viewport_capture.py tests/test_bridge_socket_parity.py
  ```
- **Result**: 84 passed, 3 skipped in 18.29s. (Full suite: 183 passed, 3 skipped in 5.31s).

---

## 2. Logic Chain

1. **Observation 1.1** proves that `FALLBACK_PNG_BYTES` is a valid, well-formed 70-byte PNG file with valid IHDR, IDAT, and IEND chunks and valid CRCs. It opens cleanly in PIL Pillow without error.
2. **Observation 1.4** proves that `blender_bridge.py` no longer generates scripts with `sys` or `os` imports, resolving the AST security violation in `execute_code`.
3. **Observation 1.5** proves that `capture_multi_angle_inspection` in `listener.py` catches `ImportError` and falls back gracefully.
4. **Observation 1.2** proves that in real Blender runtime, the package `morphomesh` is loaded into `sys.modules` from the addon directory `%APPDATA%\Blender Foundation\Blender\4.5\scripts\addons\morphomesh`.
5. Under Python's module import resolution rules (PEP 302/420), when a package is already present in `sys.modules`, submodules are resolved against `sys.modules[package].__path__`, NOT against `sys.path`.
6. Therefore, `sys.path.insert(0, p)` does NOT make `morphomesh.camera_rig` visible or importable to Python when `morphomesh` is already loaded from the addon folder.
7. Consequently, `_ensure_morphomesh_src()` in `blender_addon/morphomesh/listener.py` fails on line 121 (`import morphomesh.camera_rig`), catches `ModuleNotFoundError`, and returns `False`.
8. When `_ensure_morphomesh_src()` returns `False`, every method in `listener.py` that delegates to `morphomesh.camera_rig` catches the import failure and falls back to the in-addon naive solver.
9. This means that in the actual running Blender environment, the entire new `camera_rig.py` engine (hierarchy bounding box traversal, authentic quaternion tracking, optical framing derivation) is **completely bypassed**, and legacy fallback logic is executed instead.
10. **Observation 1.3** proves that `test_addon_relative_repo_src_resolution_audit` only tested that the legacy path didn't exist, which self-certified the fix and allowed this runtime bypass to slip past CI.

---

## 3. Caveats

- In headless CLI mode where Blender is executed via `blender -b -P <script>` with `PYTHONPATH` pointing directly to `src`, `morphomesh` is loaded directly from `src\morphomesh`, so `camera_rig.py` is found. The failure occurs specifically when running inside Blender as the installed addon (e.g. via the interactive socket listener on port 9876), which is the primary operational mode of Milestone 2 (R1 & R3).
- Extending `sys.modules["morphomesh"].__path__` completely resolves the issue in real Blender without requiring package restructuring.

---

## 4. Findings & Defects

### [Critical / Integrity Violation] Finding 1: Ineffective Addon Path Resolution & Runtime Bypass of `camera_rig`
- **Location**: `blender_addon/morphomesh/listener.py`, lines 116-126 (`_ensure_morphomesh_src`).
- **Severity**: **Critical / Integrity Violation** (Bypasses core engine logic; self-certifying test).
- **Why**:
  In Python, modifying `sys.path` does not update the submodule search paths of packages already imported into `sys.modules`. Because Blender's addon system imports the addon as `morphomesh`, `sys.modules['morphomesh'].__path__` only contains the addon directory in `%APPDATA%`. When `_ensure_morphomesh_src()` runs, it inserts `e:\tool\mcp\MorphoMesh\src` into `sys.path`, but fails to append `os.path.join(p, "morphomesh")` to `sys.modules['morphomesh'].__path__`.
  As an empirical consequence, `import morphomesh.camera_rig` raises `ModuleNotFoundError: No module named 'morphomesh.camera_rig'`. `_ensure_morphomesh_src()` returns `False`, and `listener.py` falls back to the naive in-addon stub, silently bypassing `src/morphomesh/camera_rig.py`.
- **Required Remediation**:
  In `blender_addon/morphomesh/listener.py` (and the deployed copy in `%APPDATA%\Blender Foundation\Blender\4.5\scripts\addons\morphomesh\listener.py`), update `_ensure_morphomesh_src()` to extend `sys.modules["morphomesh"].__path__`:
  ```python
  for p in candidate_paths:
      pkg_dir = os.path.join(p, "morphomesh")
      if os.path.isdir(p) and os.path.isdir(pkg_dir):
          if p not in sys.path:
              sys.path.insert(0, p)
          if "morphomesh" in sys.modules and hasattr(sys.modules["morphomesh"], "__path__"):
              if pkg_dir not in sys.modules["morphomesh"].__path__:
                  sys.modules["morphomesh"].__path__.append(pkg_dir)
          try:
              import morphomesh.camera_rig
              return True
          except Exception as e_test:
              logger.debug(f"Testing candidate path {p} failed: {e_test}")
  ```

### [Major] Finding 2: Self-Certifying Test in `test_adversarial_viewport_capture.py`
- **Location**: `tests/test_adversarial_viewport_capture.py`, lines 466-480 (`test_addon_relative_repo_src_resolution_audit`).
- **Severity**: **Major**
- **Why**:
  The test merely asserts `assert not os.path.exists(resolved_repo_src)`, asserting that the old bug exists instead of verifying that `_ensure_morphomesh_src()` actually allows `morphomesh.camera_rig` to be imported when `morphomesh` is pre-loaded as an addon package.
- **Required Remediation**:
  Update `test_addon_relative_repo_src_resolution_audit` to simulate a pre-imported `morphomesh` addon module and assert that calling `_ensure_morphomesh_src()` returns `True` and that `morphomesh.camera_rig` can be imported.

---

## 5. Verified Claims vs Failed Claims

| Claim | Method | Result |
|---|---|---|
| Valid 70-byte fallback PNG bitstream | Structural chunk parse, CRC verification, PIL `Image.open()` | **PASS** (100% compliant) |
| Bridge script security (no `sys`, `os` imports) | AST inspection of `_generate_interactive_script` with `BpyCodeValidator` & `AddonSecurityValidator` | **PASS** (100% compliant) |
| Clean `PYTHONPATH` injection for headless runs | Code inspection in `blender_bridge.py` line 457 | **PASS** (100% compliant) |
| Multi-angle inspection graceful fallback on `ImportError` | Code inspection in `listener.py` lines 1255-1290 | **PASS** (100% compliant) |
| De-certified tests in `test_multiview_rendering.py` | Code inspection of dual-mode execution tests | **PASS** (100% compliant) |
| Addon path resolution `_ensure_morphomesh_src()` in Blender | Direct execution in Blender 4.5 background process | **FAIL** (returns `False`, fails to extend `morphomesh.__path__`) |

---

## 6. Conclusion

**Verdict**: **REQUEST_CHANGES**

The fallback PNG bitstream, bridge script security, and multi-angle fallback mechanisms have been successfully remediated. However, the path resolution in `listener.py` fails to account for Python's package caching in `sys.modules`, causing all interactive RPC calls in real Blender to bypass `camera_rig.py` and execute the naive in-addon fallback.
Once `_ensure_morphomesh_src()` extends `sys.modules["morphomesh"].__path__` and the test suite verifies genuine path resolution, Milestone 2 will achieve complete integrity.

---

## 7. Verification Method

To independently reproduce and verify this finding:

1. **Reproduce Path Resolution Failure in Real Blender**:
   ```powershell
   & "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python-expr "import sys, os, morphomesh; from morphomesh.listener import MorphoMeshSocketServer, _ensure_morphomesh_src; print('ENSURE_SRC_RESULT:', _ensure_morphomesh_src()); server = MorphoMeshSocketServer(); res = server._dispatch('morphomesh.setup_inspector_camera', {'viewpoint': 'three_quarter'}); print('DISPATCH RESULT HAS bounding_box?', 'bounding_box' in res)"
   ```
   *Expected Current Output*: `ENSURE_SRC_RESULT: False`, `DISPATCH RESULT HAS bounding_box? False`.
   *Expected Post-Fix Output*: `ENSURE_SRC_RESULT: True`, `DISPATCH RESULT HAS bounding_box? True`.

2. **Verify Remediation with Extension of `__path__`**:
   ```powershell
   & "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python-expr "import sys, os, morphomesh; p = r'e:\tool\mcp\MorphoMesh\src\morphomesh'; morphomesh.__path__.append(p); from morphomesh.listener import _ensure_morphomesh_src, MorphoMeshSocketServer; print('ENSURE_SRC_RESULT:', _ensure_morphomesh_src()); server = MorphoMeshSocketServer(); res = server._dispatch('morphomesh.setup_inspector_camera', {'viewpoint': 'three_quarter'}); print('DISPATCH RESULT HAS bounding_box?', 'bounding_box' in res)"
   ```
   *Output*: `ENSURE_SRC_RESULT: True`, `DISPATCH RESULT HAS bounding_box? True`.

3. **Verify Milestone 2 Test Suite**:
   ```powershell
   .venv\Scripts\pytest.exe -v tests/test_multiview_rendering.py tests/test_adversarial_viewport_capture.py tests/test_bridge_socket_parity.py
   ```
   *Result*: 84 passed, 3 skipped in 18.29s.
