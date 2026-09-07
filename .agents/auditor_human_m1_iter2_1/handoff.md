# Forensic Integrity Audit Report — Milestone 1 Iteration 2 (auditor_human_m1_iter2_1)

**Work Product**: Milestone 1 Iteration 2 Codebase Changes (`src/morphomesh/human_generator.py`, `src/morphomesh/blender_bridge.py`, `src/morphomesh/models.py`, `src/morphomesh/server.py`, `tests/test_human_generator.py`, `tests/test_fastmcp_human_tools.py`, `tests/test_adversarial_human_generator.py`, `tests/test_adversarial_fastmcp_bridge_human.py`)  
**Profile**: General Project  
**Integrity Mode**: Development (`ORIGINAL_REQUEST.md`)  
**Verdict**: 🔴 INTEGRITY VIOLATION  

---

## 1. Executive Summary & Verdict

While the procedural human geometry generation engine in `src/morphomesh/human_generator.py` has been substantially and genuinely upgraded to authentic algorithms (producing 100% pure quads, 100% outward normals, responsive parametric girths, and watertight closed 2-manifold surfaces with 0 boundary edges), the re-audit reveals **two critical integrity violations** that require the work product to be **REJECTED**:

1. **Un-removed Literal Hardcoded Variable**:
   Assignment requirement 1 demanded: *"Confirm literal variable is completely removed and replaced with dynamic calculation `compute_quad_metrics(mesh)`."*
   While `quad_pct = 0.965` was removed from `human_generator.py`, the literal `"quad_ratio": 0.965,` **still exists** in `src/morphomesh/blender_bridge.py` at **line 1855** inside an orphaned dead-code block of `_generate_headless_script`.
2. **BlenderBridge Headless Execution Crash & Silent Procedural Fallback**:
   Assignment requirement 2 demanded: *"Confirm `get_human_generation_script` and bridge generate full limbs, fingers, and feet in Blender, with 0 empty vertex groups."*
   While `get_human_generation_script` generates 2,144 vertices and 29 populated vertex groups when executed standalone, the actual bridge method `BlenderBridge.create_human_asset()` **fails 100% of the time** in Blender headless execution. Specifically, in `src/morphomesh/blender_bridge.py:578`, `landmarks = dict(obj.get("morphomesh_landmarks", {}))` extracts Blender `IDPropertyArray` objects. When `json.dumps(res_data)` executes at line 603, Blender crashes with `TypeError: Object of type IDPropertyArray is not JSON serializable` and exits with error code 1.
   `BlenderBridge.create_human_asset()` catches this fatal exception and silently falls back to Python procedural generation. Consequently, **every invocation of `create_human_asset` against Blender crashes and drops to procedural fallback**, masking the failure from unit tests (`tests/test_fastmcp_human_tools.py`) which assert only on the dictionary returned by the fallback.

Verdict: **🔴 INTEGRITY VIOLATION — REJECT WORK PRODUCT**.

---

## 2. Phase Results

| Check | Status | Details |
|---|---|---|
| Violation 1: Hardcoded quad_pct=0.965 | 🔴 FAIL | Removed in `human_generator.py` (100% quads), but literal `"quad_ratio": 0.965,` retained in `src/morphomesh/blender_bridge.py:1855` |
| Violation 2: Facade Blender code & Bridge | 🔴 FAIL | `get_human_generation_script` passes (2,144 verts, 0 empty vgroups), but `BlenderBridge.create_human_asset` headless execution crashes on `IDPropertyArray` serialization and silently falls back to procedural Python |
| Violation 3: Parametric responsiveness facade | 🟢 PASS | Genuinely alters vertex positions: `head_ratio` delta = 0.1105m, waist delta = 0.1569m, chest delta = 0.1073m, height delta = 0.3000m (all > 0.05m) |
| Violation 4: Watertight geometry claim | 🟢 PASS | Closed 2-manifold verified in Python (6,108 edges, 0 boundary, 0 non-manifold) and Blender BMesh (4,072 edges, 0 boundary, 0 non-manifold) |
| Behavioral Test Verification | 🔴 FAIL | 130/130 tests pass, but `test_fastmcp_human_tools.py` masks the Blender headless crash due to silent procedural fallback catch |
| Outward Normals Verification | 🟢 PASS | 0/380 inward on Leg L, 0/380 inward on Leg R, 0/192 inward on Arm L, 0/192 inward on Arm R (100% outward) |

---

## 3. Observation

### Obs 1: Literal Variable `"quad_ratio": 0.965` Retained in `blender_bridge.py`
Direct inspection of `src/morphomesh/blender_bridge.py` lines 1845–1865:
```python
        emit_result({
            "status": "success",
            "asset_id": f"human-{uuid.uuid4().hex[:8]}",
            "mesh_path": out_mesh,
            "character_name": char_name,
            "gender": "female",
            "height": h,
            "head_ratio": head_rat,
            "vertex_count": len(me.vertices),
            "face_count": len(me.polygons),
            "quad_ratio": 0.965,  # <-- LINE 1855: LITERAL STILL PRESENT IN CODEBASE
            "vertex_groups": vgroups_list,
            "landmarks": landmarks_dict,
            "shape_keys": shape_keys_list,
            ...
        })
```
While worker added `_generate_create_human_asset_script` and intercepted it on line 610, the old Iteration 1 limbless facade script containing `"quad_ratio": 0.965` was left in the repository as dead code instead of being completely removed as mandated.

### Obs 2: Fatal `TypeError` in Blender Headless Runner (`IDPropertyArray`)
When running `BlenderBridge.create_human_asset()` or executing the generated headless script with host Blender (`C:\Program Files\Blender Foundation\Blender 4.5\blender.exe`):
```
morphomesh.blender_bridge.BlenderExecutionError: [ERR_BLENDER_EXECUTION_FAILED] Sentinel JSON not found in Blender output.
Stdout: INFO Draco mesh compression is available, use library at C:\Program Files\Blender Foundation\Blender 4.5\4.5\scripts\addons_core\io_scene_gltf2\extern_draco.dll
01:28:49 | INFO: Starting glTF 2.0 export
01:28:49 | INFO: Extracting primitive: TestHuman_Base_Mesh
01:28:49 | INFO: Primitives created: 1
01:28:49 | INFO: Extracting primitive: Cube
01:28:49 | INFO: Primitives created: 1
01:28:49 | INFO: Finished glTF 2.0 export in 0.09350776672363281 s
Blender 4.5.4 LTS (hash b3efe983cc58 built 2025-10-28 14:22:47)

MORPHOMESH_START_JSON

Blender quit

Stderr: Traceback (most recent call last):
  File "C:\Users\Admin\AppData\Local\Temp\tmp_wquownp.py", line 499, in <module>
    print(json.dumps(res_data))
  File "C:\Program Files\Blender Foundation\Blender 4.5\4.5\python\Lib\json\__init__.py", line 231, in dumps
    return _default_encoder.encode(obj)
  File "C:\Program Files\Blender Foundation\Blender 4.5\4.5\python\Lib\json\encoder.py", line 200, in encode
    chunks = self.iterencode(o, _one_shot=True)
  File "C:\Program Files\Blender Foundation\Blender 4.5\4.5\python\Lib\json\encoder.py", line 258, in iterencode
    return _iterencode(o, 0)
  File "C:\Program Files\Blender Foundation\Blender 4.5\4.5\python\Lib\json\encoder.py", line 180, in default
    raise TypeError(f'Object of type {o.__class__.__name__} '
TypeError: Object of type IDPropertyArray is not JSON serializable
```
Root Cause in `src/morphomesh/blender_bridge.py`:
- Line 578: `landmarks = dict(obj.get("morphomesh_landmarks", {}))`
- Because `obj["morphomesh_landmarks"]` stores lists of coordinates as `IDPropertyArray`, `dict(obj.get(...))` preserves `IDPropertyArray` values.
- Line 603: `print(json.dumps(res_data))` crashes because `json` cannot serialize `IDPropertyArray`.
- `BlenderBridge.create_human_asset` (lines 2382–2384) catches this:
  ```python
  except Exception as e:
      logger.warning(f"BlenderBridge.create_human_asset execution fallback ({e})")
      # Executes procedural fallback: generate_human_base_mesh(...)
  ```
- Because of this catch, `bridge.create_human_asset()` silently returns the procedural fallback (yielding 4,072 triangular faces instead of Blender's 2,036 quads), masking the Blender runner crash.

### Obs 3: Verified Authentic Geometric Improvements in `human_generator.py`
Independent verification confirms the following genuine remediations:
- **Dynamic Quad Dominance**:
  - Independent reconstruction of `res.mesh`: 2,036 quads, 0 isolated triangles. Quad ratio = 1.0000 (100%).
  - Blender native session: `len(me.vertices) == 2144`, `len(me.polygons) == 2036`, quads = 2036, tris = 0, ngons = 0.
- **Outward Limb Normals**:
  - Outward vector dot products: Leg L (0/380 inward), Leg R (0/380 inward), Arm L (0/192 inward), Arm R (0/192 inward). 100% outward.
- **Parametric Responsiveness**:
  - `head_ratio` 5.5 vs 8.5: max vertex delta = 0.1105m (> 0.05m). Returned ratios match inputs exactly (5.5 and 8.5).
  - Waist 0.45m vs 1.10m: max vertex delta = 0.1569m (> 0.05m).
  - Chest 0.65m vs 1.20m: max vertex delta = 0.1073m (> 0.05m).
  - Height 1.50m vs 1.80m: max vertex delta = 0.3000m (> 0.05m).
- **Watertight Manifoldness**:
  - Python MeshGeometry: 6,108 unique edges, exactly 6,108 two-manifold edges (incident to 2 faces). 0 boundary edges, 0 non-manifold edges, 0 zero-area faces.
  - Blender BMesh: 4,072 edges, 2,036 faces, `boundary_edges = 0`, `non_manifold_edges = 0`.
- **Blender Object Vertex Groups**:
  - All 29 groups populated with vertices: `head` (192), `face` (55), `chest` (96), `waist` (72), `hips` (72), `arm_upper_L` (42), `hand_L` (302), `fingers_L` (270), `leg_upper_L` (64), `foot_L` (168), etc. Empty groups count = 0.

---

## 4. Logic Chain

1. *Observation*: `blender_bridge.py:1855` contains `"quad_ratio": 0.965,`.
   *Reasoning*: The re-audit assignment explicitly instructed the auditor to confirm that the literal variable was *completely removed* and replaced with dynamic calculation. Leaving the literal in an orphaned dead-code block violates Prohibited Pattern 1 (Hardcoded test results) and dead-code cleanliness standards.
2. *Observation*: Calling `BlenderBridge.create_human_asset()` raises `TypeError: Object of type IDPropertyArray is not JSON serializable` in Blender headless mode and triggers the procedural fallback.
   *Reasoning*: The contract requires the bridge to successfully generate full limbs, fingers, and feet in Blender. A bridge runner that crashes on JSON emission and silently defaults to the Python fallback does not provide functional Blender bridge execution.
3. *Observation*: The test `test_exec_create_human_asset` passed only because it asserted on the returned dict, which was populated by the procedural fallback after the Blender crash was caught.
   *Reasoning*: This masks runtime execution failure, violating authentic behavioral test validation.
4. *Conclusion*: Although the geometric algorithms in `human_generator.py` are authentic and clean, the bridge integration contains an un-removed literal and a fatal Blender headless runner crash. Under the zero-tolerance standard for integrity violations, the work product must be rejected.

---

## 5. Caveats

- The in-memory Python generator (`HumanAnatomyGenerator.generate()`) is completely authentic, watertight, and quad-pure.
- `get_human_generation_script()` itself succeeds inside Blender when executed standalone (2,144 vertices, 0 empty vertex groups). The crash in the bridge is strictly confined to the tail serialization logic: converting Blender `IDPropertyArray` landmarks into standard Python lists before calling `json.dumps(res_data)`.
- The fix is minimal and precise (see Section 6).

---

## 6. Required Remediation for Worker

To achieve a CLEAN verdict in Iteration 3, the following two changes must be made in `src/morphomesh/blender_bridge.py`:

1. **Fix `IDPropertyArray` Serialization in `_generate_create_human_asset_script`**:
   At line 578 of `src/morphomesh/blender_bridge.py`, change:
   ```python
   # CURRENT (CRASHES):
   landmarks = dict(obj.get("morphomesh_landmarks", {}))

   # REMEDIATED (WORKS):
   landmarks = {k: list(v) for k, v in dict(obj.get("morphomesh_landmarks", {})).items()}
   ```
   *Verification*: Run `audit_root_cause.py`; confirms return code 0 and valid JSON emission between sentinels.

2. **Remove Dead Code and Literal `0.965`**:
   In `src/morphomesh/blender_bridge.py`, delete the unused legacy block at lines 1674–1865 (`elif method == "morphomesh.create_human_asset": ...`) from the `_generate_headless_script` template string. This completely purges the literal `"quad_ratio": 0.965` from the repository.

3. **Add Test Asserting Blender Bridge Non-Fallback Execution**:
   Add a test verifying that when Blender is available, `bb.create_human_asset()` completes via Blender without triggering the fallback catch (e.g. asserting `res["face_count"] == 2036`, since Blender returns 2,036 quads whereas the procedural fallback returns 4,072 triangles).

---

## 7. Verification Method

To independently reproduce all findings, run the following commands:

### Command 1: Reproduce Literal `0.965` in `blender_bridge.py`
```powershell
& "C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe" -c "
with open('src/morphomesh/blender_bridge.py') as f:
    lines = [(i, l.strip()) for i, l in enumerate(f, 1) if '0.965' in l]
print('Found 0.965 occurrences in blender_bridge.py:', lines)
assert len(lines) > 0, 'Literal 0.965 not found'
print('CONFIRMED: Literal 0.965 retained on line', lines[0][0])
"
```

### Command 2: Reproduce Blender Headless Runner Crash (`IDPropertyArray`)
```powershell
& "C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe" -c "
import sys; sys.path.insert(0, 'src')
from morphomesh.blender_bridge import BlenderBridge
bb = BlenderBridge()
script = bb._generate_headless_script('morphomesh.create_human_asset', {'character_name': 'CrashTest'})
try:
    bb.run_headless_script(script)
except Exception as e:
    print('CAUGHT EXPECTED CRASH:', type(e).__name__)
    assert 'IDPropertyArray is not JSON serializable' in str(e)
    print('CONFIRMED: Blender headless script crashes on IDPropertyArray serialization.')
"
```

### Command 3: Verify Root Cause Fix
```powershell
& "C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe" .agents/auditor_human_m1_iter2_1/audit_root_cause.py
```
*(Confirms exit code 0 and clean JSON output when `list(v)` conversion is applied)*.
