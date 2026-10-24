# Challenger 2 Handoff Report: Milestone 2 Empirical Adversarial Stress Testing

- **Agent**: Challenger 2 (`m2_veg_challenger_2`)
- **Role**: Empirical Challenger (critic, specialist)
- **Target Implementation**: `teamwork_projects/vegetation_library/vegetation_pipeline/generator.py`
- **Catalog**: `teamwork_projects/vegetation_library/vegetation_pipeline/catalog.py`
- **Adversarial Test Script**: `.agents/m2_veg_challenger_2/empirical_challenge.py`
- **Parent Conversation ID**: `1f2774e9-3e4e-4a4c-8dc6-f85249e37b16`
- **Date**: 2026-09-10T12:57:00+07:00
- **Verdict**: **REQUEST_CHANGES**

---

## Challenge Summary

- **Overall Risk Assessment**: **HIGH**
  While the procedural 3D botanical mesh generation, GLB static structure, ground alignment ($Z_{\min} = 0.000$m), base centering ($\Delta r = 0.000$m), and PBR texture synthesis are remarkably high quality across all 7 biomes (104 of 106 adversarial tests passed), there is an active test failure in the official project repository test suite, along with unhandled crashes on boundary seed values and cross-engine cache pollution that bypasses explicit caller intents.

---

## 1. Observation

### 1.1 Empirical Adversarial Test Harness Execution
The dedicated empirical test suite was executed in the workspace:
```powershell
uv run python .agents/m2_veg_challenger_2/empirical_challenge.py
```
**Verbatim Output Summary**:
```
================================================================================
STARTING EMPIRICAL CHALLENGER 2 ADVERSARIAL VERIFICATION HARNESS
Working Directory: E:\tool\mcp\MorphoMesh\.agents\m2_veg_challenger_2
================================================================================
TEST SUITE 1: 7-BIOME MULTI-SPECIES EMPIRICAL INVARIANT VERIFICATION
Testing 14 distinct species across all 7 categories...
  [PASS] veg_tree_oak_01 - Vertex Budget: 4320 verts in budget [3000, 45000]
  [PASS] veg_tree_oak_01 - Ground Alignment: min(z) = 0.000000m (within +/- 0.005m)
  [PASS] veg_tree_oak_01 - Base Contact Centroid Centering: centroid offset = 0.000000m (cx=-0.000000, cy=0.000000) <= 0.05m
  [PASS] veg_tree_oak_01 - Static Mesh Binary GLB Compliance: skins=[], anims=[], zero JOINTS/WEIGHTS accessors
  [PASS] veg_tree_oak_01 - PBR Textures Suite: 512x512, non-flat, non-black Albedo, OpenGL normal, dielectric metallic <= 0.05
  ... (all 14 species tested passed)

================================================================================
TEST SUITE 2: EXHAUSTIVE 35-SPECIES SWEEP (ALL BIOMES)
================================================================================
  [PASS] Exhaustive 35-Species Sweep - Vertex Count Budget: All 35 species strictly within [3000, 45000] vertices
  [PASS] Exhaustive 35-Species Sweep - Ground Pivot Invariant: All 35 species strictly aligned at min(z) == 0.000m (+/- 0.005m)
  [PASS] Exhaustive 35-Species Sweep - Centroid Origin Invariant: All 35 species base contact centroids within 0.05m of origin

================================================================================
TEST SUITE 3: SEED DETERMINISM & DIVERSITY VERIFICATION
================================================================================
  [PASS] veg_tree_oak_01 - Deterministic Repeatability (Seed 12345): Bit-for-bit identical vertices and faces
  [PASS] veg_tree_oak_01 - Morphological Diversity (Seed 12345 vs 98765): Geometry successfully diverges across different seeds
  [PASS] veg_conifer_pine_01 - Deterministic Repeatability (Seed 12345): Bit-for-bit identical vertices and faces
  [PASS] veg_conifer_pine_01 - Morphological Diversity (Seed 12345 vs 98765): Geometry successfully diverges across different seeds
  [PASS] veg_tropical_palm_01 - Deterministic Repeatability (Seed 12345): Bit-for-bit identical vertices and faces
  [PASS] veg_tropical_palm_01 - Morphological Diversity (Seed 12345 vs 98765): Geometry successfully diverges across different seeds
  [PASS] veg_shrub_rose_01 - Deterministic Repeatability (Seed 12345): Bit-for-bit identical vertices and faces
  [PASS] veg_shrub_rose_01 - Morphological Diversity (Seed 12345 vs 98765): Geometry successfully diverges across different seeds
  [PASS] veg_ground_fern_01 - Deterministic Repeatability (Seed 12345): Bit-for-bit identical vertices and faces
  [PASS] veg_ground_fern_01 - Morphological Diversity (Seed 12345 vs 98765): Geometry successfully diverges across different seeds
  [PASS] veg_succulent_saguaro_01 - Deterministic Repeatability (Seed 12345): Bit-for-bit identical vertices and faces
  [PASS] veg_succulent_saguaro_01 - Morphological Diversity (Seed 12345 vs 98765): Geometry successfully diverges across different seeds
  [PASS] veg_vine_ivy_01 - Deterministic Repeatability (Seed 12345): Bit-for-bit identical vertices and faces
  [PASS] veg_vine_ivy_01 - Morphological Diversity (Seed 12345 vs 98765): Geometry successfully diverges across different seeds

================================================================================
TEST SUITE 4: ADVERSARIAL BOUNDARY CONDITIONS STRESS TESTS
================================================================================
  [PASS] Boundary: Zero Seed (seed=0): Generated 4320 verts with Z_min=0.0
  [PASS] Boundary: Large Seed uint31 max (seed=2**31 - 1): Generated 4320 verts
  [PASS] Boundary: Large Seed uint32 max (seed=2**32 - 1): Generated 4320 verts
  [FAIL] Boundary: Negative Seed (seed=-1): Numpy RandomState rejection on negative seed without normalization (ValueError: Seed must be between 0 and 2**32 - 1)
  [FAIL] Boundary: Seed exceeding uint32 (seed=2**32): Numpy RandomState rejection on seed >= 2**32 without modulo masking (ValueError: Seed must be between 0 and 2**32 - 1)
  [PASS] Boundary: Tiny Scale (H=0.05m) - veg_tree_oak_01: verts=4320, z_min=0.000000m, zero NaNs
  [PASS] Boundary: Huge Scale (H=150.0m) - veg_tree_oak_01: verts=4320, z_min=0.000000m, zero NaNs
  ... (all 7 biomes tested for tiny and huge scale passed)

================================================================================
EMPIRICAL CHALLENGER 2 SUMMARY
Total Tests Executed : 106
Passed Tests         : 104
Failed Tests         : 2
================================================================================
ADVERSARIAL CHALLENGES / VULNERABILITIES IDENTIFIED:
[1] Boundary: Negative Seed (seed=-1)
    Reason : Numpy RandomState rejection on negative seed without normalization
    Details: ValueError: Seed must be between 0 and 2**32 - 1
[2] Boundary: Seed exceeding uint32 (seed=2**32)
    Reason : Numpy RandomState rejection on seed >= 2**32 without modulo masking
    Details: ValueError: Seed must be between 0 and 2**32 - 1
```

### 1.2 Official Test Suite Regression Confirmed
Running the project test suite confirms an active failure in `test_generator.py`:
```powershell
uv run pytest teamwork_projects/vegetation_library/tests/test_generator.py -k test_dispatch_mode_meshy_explicit_without_key_raises -v
```
**Verbatim Output**:
```
teamwork_projects/vegetation_library/tests/test_generator.py::TestGeneratePlantDispatch::test_dispatch_mode_meshy_explicit_without_key_raises FAILED [100%]
================================== FAILURES ===================================
_ TestGeneratePlantDispatch.test_dispatch_mode_meshy_explicit_without_key_raises _
    def test_dispatch_mode_meshy_explicit_without_key_raises(self, sample_oak_species, monkeypatch):
        monkeypatch.delenv("MESHY_API_KEY", raising=False)
        monkeypatch.delenv("MESHY_AI_API_KEY", raising=False)
>       with pytest.raises(Exception) as exc_info:
E       Failed: DID NOT RAISE Exception
teamwork_projects\vegetation_library\tests\test_generator.py:634: Failed
```

### 1.3 Exact Code Locations of Deficiencies
1. **Seed Normalization Gap (`generator.py:632-638`)**:
   ```python
   active_seed = (
       seed if seed is not None
       else (self.config.seed if self.config.seed is not None
             else abs(hash(species.species_id)) % (2**31 - 1))
   )
   rng = np.random.RandomState(active_seed)
   ```
   When `seed` is passed explicitly (or in `ProceduralGeneratorConfig`), it is passed raw to `np.random.RandomState`. Passing `seed=-1`, `seed=-42`, `seed=2**32`, or standard 64-bit Python integer hashes directly raises `ValueError: Seed must be between 0 and 2**32 - 1`.

2. **Cross-Engine Cache Pollution & Mode Hijacking (`generator.py:1398-1408`)**:
   ```python
   # 4. Check disk cache if not force_regenerate
   if not force_regenerate and not meshy_gen.config.force_regenerate and meshy_gen.config.use_cache:
       cached_asset = meshy_gen.check_cache(species_obj, target_dir=out_path)
       if cached_asset is not None:
           return cached_asset

   # 5. Mode: Explicit Meshy
   if mode == "meshy":
       api_key = meshy_gen.resolve_api_key()
       if not api_key:
           raise RuntimeError("MESHY_API_KEY API key environment variable is not set")
   ```
   In `generator.py`, Step 4 checks `check_cache()` before Step 5 checks `mode == "meshy"` or validates `MESHY_API_KEY`. Because `output/broadleaf_trees/veg_tree_oak_01` was populated by procedural generation, `check_cache()` returns the procedural asset, bypassing the `MESHY_API_KEY` check and causing the repo test failure.

3. **Non-Scaling Subcrown Radius in Broadleaf Trees (`generator.py:789`)**:
   ```python
   cr = rng.uniform(0.8, 1.4)
   add_quad_ellipsoid(mesh, (cx, cy, cz), (cr, cr, cr * 0.8), rings=5, sectors=8)
   ```
   In `_build_broadleaf_tree`, `cr` is hardcoded to $0.8 - 1.4$ meters. If a user sets height or canopy spread to $0.05$m (e.g. bonsai or miniature), the crown ellipsoids remain $1.6 - 2.8$m wide.

---

## 2. Logic Chain

1. **Test Failure Origin**:
   - Procedural generation writes output to `./output/{category}/{species_id}` by default.
   - When any test or verification command runs (e.g. M2 Worker's handoff line 165-177 or standard pipeline invocations), `./output/broadleaf_trees/veg_tree_oak_01` is written.
   - `generate_plant()` executes `check_cache()` at line 1398, prior to checking `mode == "meshy"` at line 1404.
   - `check_cache()` does not verify `expected_source="meshy"`; it accepts procedural assets.
   - Calling `generate_plant(species, mode="meshy")` without `MESHY_API_KEY` returns the cached procedural asset without raising `RuntimeError`.
   - This invalidates the contract for explicit mode enforcement and breaks `test_dispatch_mode_meshy_explicit_without_key_raises`.

2. **Boundary Seed Fragility**:
   - While the fallback hash `abs(hash(species.species_id)) % (2**31 - 1)` is well-bounded, caller-provided seeds are not sanitized.
   - Standard Python functions accept arbitrary integers (including negative hashes or 64-bit integers).
   - In numpy, `np.random.RandomState` strictly requires $0 \le \text{seed} \le 2^{32} - 1$.
   - Any external system passing a signed hash or 64-bit timestamp triggers an unhandled `ValueError`.

3. **Procedural Invariant Robustness**:
   - Invariant enforcement in `_enforce_mesh_invariants`:
     - $\min(v_z) \equiv 0.000000$m is maintained analytically across all 35 catalog species and extreme dimension bounds ($H \in [0.05\text{m}, 150.0\text{m}]$).
     - Base contact centroid centering shifts bottom 5% height vertices to $(0.0, 0.0)$ with precision $\Delta r = 0.000000$m.
     - Vertex count for all 35 catalog species falls between 3,336 and 5,024 vertices, strictly within $[3000, 45000]$.
     - GLB containers serialize only `POSITION`, `NORMAL`, and `TEXCOORD_0` accessors, completely omitting `skins`, `animations`, and `JOINTS_0`/`WEIGHTS_0`.
     - 4-channel PBR textures meet all dimensional and statistical bounds (non-black, non-flat, OpenGL normal, dielectric metallic).

---

## 3. Challenges

### [High] Challenge 1: Cross-Engine Cache Pollution Breaks Explicit Mode Contracts
- **Assumption Challenged**: `check_cache()` can be safely invoked before checking generation mode or credentials.
- **Attack Scenario**: A user runs `generate_plant(oak, mode="procedural")` to test offline. Later, production batch generation calls `generate_plant(oak, mode="meshy")` expecting a high-fidelity Meshy AI quad mesh. The system silently serves the low-poly procedural fallback instead, without notifying the user or checking API keys.
- **Blast Radius**: Silent quality degradation, contract violation, and broken test suite (`test_dispatch_mode_meshy_explicit_without_key_raises`).
- **Mitigation**: In `generate_plant`, validate `mode` and credentials first. Pass `expected_source="meshy"` to `check_cache()` when `mode == "meshy"`.

### [Medium] Challenge 2: Negative and 64-Bit Seed Rejection
- **Assumption Challenged**: Caller-provided seeds are always non-negative 32-bit unsigned integers.
- **Attack Scenario**: An orchestration system or user hashes a prompt or asset GUID (`hash("garden_tree_01")` which returns a signed 64-bit int on 64-bit Python) and passes it as `seed=hash(...)`.
- **Blast Radius**: Crash with `ValueError: Seed must be between 0 and 2**32 - 1`.
- **Mitigation**: Sanitize seed with `active_seed = abs(int(seed)) % (2**32 - 1)`.

### [Medium] Challenge 3: Hardcoded Absolute Dimensions in Procedural Crowns
- **Assumption Challenged**: All broadleaf trees have canopy spreads $> 3.0$m.
- **Attack Scenario**: A bonsai or seedling species is modeled with $H = 0.2$m and canopy spread $0.15$m.
- **Blast Radius**: Subcrown ellipsoids ($r = 0.8 - 1.4$m) dwarf the trunk, resulting in severe geometrical distortion.
- **Mitigation**: Scale `cr` proportionally with `species.dimensions.canopy_spread_m` (e.g. `cr = rng.uniform(0.12, 0.22) * species.dimensions.canopy_spread_m`).

---

## 4. Stress Test Results Summary

| Scenario | Expected Behavior | Actual Behavior | Result |
|---|---|---|---|
| Vertex count budget across 14 species | $3000 \le N_{\text{verts}} \le 45000$ | $3,336 - 5,024$ vertices | **PASS** |
| Ground alignment across 14 species | $\min(v_z) = 0.000\text{m} \pm 0.005\text{m}$ | $0.000000$m exact | **PASS** |
| Base contact centroid across 14 species | Centered within $\pm 0.05$m of origin | $0.000000$m offset | **PASS** |
| GLB static mesh container across 14 species | Zero skins, anims, joints, or weights | Confirmed via glTF JSON chunk inspection | **PASS** |
| 4-channel PBR textures across 14 species | 512x512, non-flat, non-black, metallic $\le 0.05$ | All variance & mean constraints satisfied | **PASS** |
| Exhaustive 35-species catalog sweep | Zero invariant outliers | 35/35 species compliant | **PASS** |
| Seed determinism across 7 biomes | Identical on same seed, divergent on different | Verified bit-for-bit | **PASS** |
| Boundary: Zero seed (`seed=0`) | Generates valid mesh | 4,320 verts, $Z_{\min} = 0.0$m | **PASS** |
| Boundary: Large uint32 seed (`2**32 - 1`) | Generates valid mesh | 4,320 verts, $Z_{\min} = 0.0$m | **PASS** |
| Boundary: Negative seed (`seed=-1`) | Gracefully normalizes seed | Raises unhandled `ValueError` | **FAIL** |
| Boundary: Overflow seed (`seed=2**32`) | Gracefully normalizes seed | Raises unhandled `ValueError` | **FAIL** |
| Boundary: Extreme scale ($H=0.05$m & $150$m) | Zero NaNs, valid mesh bounds | All 7 biomes generated with zero NaNs | **PASS** |
| Repo test: `test_dispatch_mode_meshy_explicit_without_key_raises` | Raises Exception without key | Fails: cache returns procedural asset | **FAIL** |

---

## 5. Caveats

1. **Live Meshy AI Credit Consumption**:
   - In accordance with team testing protocol, no live API credits were spent during verification. All tests exercised the offline procedural generator, GLB unpacker, and local cache fixtures.
2. **Procedural Botanical Generation Quality**:
   - The underlying geometric algorithms (spires, helical vines, fan palms, flower petals, ribbed cacti) are botanically authentic, highly performant (~0.05s per tree), and conform to all physical constraints.

---

## 6. Conclusion & Actionable Recommendations

### Verdict: **REQUEST_CHANGES**

The M2 implementation is structurally impressive and the procedural engine is mathematically sound, but cannot be approved until the active repository test failure and seed boundary crashes are resolved.

### Actionable Remediation Items:
1. **Fix `generate_plant` Cache Dispatch and Credential Ordering**:
   - In `generate_plant` (`generator.py:1390-1415`):
     - Check `mode == "meshy"` before checking cache, or pass `expected_source="meshy"` to `check_cache()`.
     - When `mode == "meshy"`, validate `MESHY_API_KEY` first. If absent, raise immediately.
     - In `test_generator.py:630`, isolate `output_dir` using `tmp_path` to avoid relying on `./output`.
2. **Normalize Seed in `ProceduralBotanicalGenerator`**:
   - In `generator.py:632`:
     ```python
     if seed is not None:
         active_seed = abs(int(seed)) % (2**32 - 1)
     elif self.config.seed is not None:
         active_seed = abs(int(self.config.seed)) % (2**32 - 1)
     else:
         active_seed = abs(hash(species.species_id)) % (2**31 - 1)
     ```
3. **Scale Broadleaf Subcrowns Proportionally**:
   - In `generator.py:789`:
     ```python
     cr = rng.uniform(0.15, 0.25) * species.dimensions.canopy_spread_m
     ```

---

## 7. Verification Method

To independently reproduce and verify this assessment:

1. **Execute Empirical Challenger 2 Test Harness**:
   ```powershell
   uv run python .agents/m2_veg_challenger_2/empirical_challenge.py
   ```
   *Expected*: 104 passed, 2 failed (`seed=-1` and `seed=2**32`).

2. **Verify Official Test Suite Failure**:
   ```powershell
   uv run pytest teamwork_projects/vegetation_library/tests/test_generator.py -k test_dispatch_mode_meshy_explicit_without_key_raises -v
   ```
   *Expected*: `FAILED` with `DID NOT RAISE Exception`.

3. **Invalidation Conditions**:
   - `uv run python .agents/m2_veg_challenger_2/empirical_challenge.py` exits with code 0 (106/106 passed).
   - `uv run pytest teamwork_projects/vegetation_library/tests/ -v` passes 117/117 without regressions.
