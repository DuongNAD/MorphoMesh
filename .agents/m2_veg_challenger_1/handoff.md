# Challenger 1 Handoff Report: Milestone 2 Adversarial Stress Testing

- **Agent**: Challenger 1 (`m2_veg_challenger_1`)
- **Role**: Empirical Challenger (critic, specialist)
- **Target Implementation**: `teamwork_projects/vegetation_library/vegetation_pipeline/generator.py`
- **Adversarial Test Suite**: `.agents/m2_veg_challenger_1/test_adversarial_generator.py`
- **Parent Conversation ID**: `1f2774e9-3e4e-4a4c-8dc6-f85249e37b16`
- **Date**: 2026-09-10T05:58:00Z
- **Verdict**: **REQUEST_CHANGES**

---

## 1. Observation

### 1.1 Existing Test Suite Regression
Running the official project test command across the vegetation test suite resulted in a test failure:
```powershell
uv run pytest teamwork_projects/vegetation_library/tests/ -v
```
**Output**:
```
teamwork_projects/vegetation_library/tests/test_generator.py::TestGeneratePlantDispatch::test_dispatch_mode_meshy_explicit_without_key_raises FAILED

================================== FAILURES ===================================
_ TestGeneratePlantDispatch.test_dispatch_mode_meshy_explicit_without_key_raises _
    def test_dispatch_mode_meshy_explicit_without_key_raises(self, sample_oak_species, monkeypatch):
        monkeypatch.delenv("MESHY_API_KEY", raising=False)
        monkeypatch.delenv("MESHY_AI_API_KEY", raising=False)
>       with pytest.raises(Exception) as exc_info:
E       Failed: DID NOT RAISE Exception
teamwork_projects\vegetation_library\tests\test_generator.py:634: Failed
======================== 1 failed, 116 passed in 4.08s ========================
```
Investigation revealed that running any procedural generation defaults its output to `./output/{short_category}/{species_id}`. Once `./output/broadleaf_trees/veg_tree_oak_01` was populated on disk, subsequent calls to `generate_plant(..., mode="meshy")` hit `check_cache()` before checking `mode == "meshy"` or checking for `MESHY_API_KEY`. Because `check_cache()` accepts any asset with `.glb` and textures regardless of whether its source was `"meshy"` or `"procedural"`, it returned the procedural asset as `source='cached'`, causing `test_dispatch_mode_meshy_explicit_without_key_raises` to fail because no exception was raised.

### 1.2 Adversarial Test Suite Execution
An adversarial test suite containing 42 targeted test cases was authored and executed:
```powershell
uv run pytest .agents/m2_veg_challenger_1/test_adversarial_generator.py -v -s
```
**Output**:
```
============================= 42 passed in 2.77s ==============================
```
Every single test executed synchronously offline with zero credit burn, rigorously probing the 5 required stress dimensions.

### 1.3 Key Source Code Observations in `generator.py`
1. **Cross-Engine Cache Pollution & Mode Hijacking** (`generator.py:1398-1408`):
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
   Cache checking at Step 4 occurs before Step 5. `check_cache()` returns cached assets where `source="procedural"`, directly hijacking explicit `mode="meshy"` requests.

2. **Corrupted Non-Zero GLB Binary Accepted** (`generator.py:458-466, 507-523`):
   ```python
   glb_path = cand / f"{species.species_id}.glb"
   if not glb_path.is_file():
       continue
   try:
       if glb_path.stat().st_size == 0:
           continue
   except OSError:
       continue
   ...
   verts, faces = parse_glb_vertex_and_face_counts(glb_path)
   if verts == 0 and "vertex_count" in manifest_data:
       verts = manifest_data["vertex_count"]
   return RawAsset(...)
   ```
   If a GLB file is corrupted (e.g. 100 bytes of non-zero garbage), `stat().st_size > 0`. `parse_glb_vertex_and_face_counts` catches the unpack error and returns `0, 0`. If `manifest_data` provides `vertex_count`, `check_cache()` returns a `RawAsset` pointing to the corrupted GLB.

3. **`Retry-After` Header Denial-of-Service / Hanging** (`generator.py:262-267`):
   ```python
   base_delay = self.config.backoff_base_seconds * (2 ** (attempt - 1))
   jitter = random.uniform(0.0, 0.5)
   delay = min(self.config.backoff_max_seconds, base_delay + jitter)
   if retry_after is not None:
       delay = max(delay, retry_after)
   ```
   `min(self.config.backoff_max_seconds, ...)` is evaluated *before* applying `retry_after`. If the server returns `Retry-After: 86400`, `delay` becomes 86,400s (24 hours), completely ignoring `backoff_max_seconds` (default 60s) and hanging the process.

4. **Terminal 4xx Error Classification Gap** (`generator.py:241-246`):
   ```python
   # Terminal client errors: fail fast without retry
   if e.code in (400, 401, 402, 403, 404, 422):
       err_text = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
       raise RuntimeError(f"Meshy API client error {e.code}: {err_text}")
   ```
   Client errors like 405 (Method Not Allowed), 408 (Request Timeout), 409 (Conflict), 413 (Payload Too Large), and 415 (Unsupported Media Type) fall through to the retriable loop and are retried `max_retries` times with exponential delay instead of failing fast.

5. **Truncated Manifest Swallowed Without Invalidation** (`generator.py:501-506`):
   ```python
   manifest_path = cand / "cache_manifest.json"
   manifest_data: Dict[str, Any] = {}
   if manifest_path.is_file():
       try:
           with open(manifest_path, "r", encoding="utf-8") as f:
               manifest_data = json.load(f)
       except Exception:
           pass
   ```
   Truncated or corrupted JSON manifests are caught and swallowed, leaving `manifest_data = {}` and returning the cached asset rather than invalidating the cache.

6. **Deprecated Meshy Model in Configuration** (`generator.py:164`):
   ```python
   ai_model: str = "meshy-4"
   ```
   Sending live API requests with `meshy-4` returns HTTP 400: `{"message":"meshy-4 is deprecated, please use meshy-6 instead"}`.

7. **Silent Swallowing of Invalid Modes and Kwargs** (`generator.py:1365-1424`):
   Passing `mode="invalid_string"` does not raise `ValueError`, but silently executes the `"auto"` mode fallback. Passing `**kwargs` (like `texture_resolution=1024`) is silently discarded.

---

## 2. Logic Chain

1. **Step 1 (Root Cause of Test Suite Failure)**:
   - Observation 1.1 demonstrates that `test_dispatch_mode_meshy_explicit_without_key_raises` fails with `DID NOT RAISE Exception`.
   - Observation 1.3.1 demonstrates that `generate_plant` executes `meshy_gen.check_cache()` before checking `mode == "meshy"` or `resolve_api_key()`.
   - When a procedural asset was previously written to the default directory `./output/broadleaf_trees/veg_tree_oak_01`, `check_cache()` returns it.
   - Therefore, any caller requesting `mode="meshy"` receives a procedural asset without ever validating credentials or calling Meshy AI.

2. **Step 2 (Cache Robustness Assessment)**:
   - Observation 1.3.2 demonstrates that `check_cache()` only verifies `st_size == 0` for GLB files.
   - Our adversarial test `test_corrupted_nonzero_garbage_glb_cache_behavior` confirmed empirically that a 260-byte corrupted text file disguised as a GLB was returned as a valid `RawAsset`. Unpacking its glTF chunk immediately crashes downstream code with `ValueError: Invalid GLB header`.
   - Observation 1.3.5 demonstrates that truncated `cache_manifest.json` files are accepted with empty metadata rather than triggering cache regeneration.

3. **Step 3 (Rate-Limiting & Security Assessment)**:
   - Observation 1.3.3 demonstrates that `retry_after` overrides `backoff_max_seconds`.
   - Adversarial test `test_retry_after_dos_vulnerability_bypasses_max_seconds` empirically verified that `Retry-After: 86400` forces `time.sleep(86400.0)`, proving a denial-of-service vulnerability that halts execution.
   - Observation 1.3.4 demonstrates that non-standard 4xx client errors (405, 409, 413, 415) are retried 5 times with exponential backoff instead of failing fast.

4. **Step 4 (API Compatibility Assessment)**:
   - Observation 1.3.6 demonstrates that the default configuration uses `meshy-4`.
   - Meshy API v2 rejects `meshy-4` with HTTP 400 Bad Request, requiring `meshy-6`.

---

## 3. Caveats

1. **Procedural Geometry and PBR Synthesis Are Excellent**:
   - The procedural botanical generator (`ProceduralBotanicalGenerator`) across all 7 biomes is robust, strictly deterministic, and fully compliant with invariant bounds ($Z_{\min} = 0.000$m, vertex budget $[3000, 45000]$, dielectric metallic $\le 0.05$, zero armatures).
2. **Concurrent Request Safety Is Verified**:
   - Adversarial test `test_concurrent_duplicate_requests_stress_test` verified that 8 concurrent threads writing to the same species directory do not cause unhandled race conditions or file corruption.
3. **No Live API Credits Burned**:
   - In accordance with QA requirements, all tests were verified offline using mocked boundaries and local filesystem harnesses.

---

## 4. Conclusion & Actionable Recommendations

### Verdict: **REQUEST_CHANGES**

The M2 implementation cannot be approved in its current state due to a failing test in the repo test suite, cross-engine cache pollution, cache acceptance of corrupted GLBs, and an unbounded sleep vulnerability.

### Actionable Remediation Items:
1. **Fix Cross-Engine Cache Pollution in `generate_plant` & `check_cache`**:
   - In `generate_plant()`:
     - For `mode == "meshy"`: Check API key FIRST, and only accept cached assets where `manifest.get("source") == "meshy"` (pass `expected_source="meshy"` to `check_cache`).
     - For `mode == "procedural"`: Skip cache or ensure `manifest.get("source") == "procedural"`.
   - In `test_generator.py`: Update `test_dispatch_mode_meshy_explicit_without_key_raises` to pass `output_dir=tmp_path` to guarantee an isolated test environment.
2. **Validate Binary GLB Header in `check_cache`**:
   - In `check_cache()`: Before accepting `glb_path`, read the first 12 bytes and verify `magic == b"glTF"` and `version == 2`. If invalid, treat as cache miss (`continue`).
3. **Clamp `Retry-After` to `backoff_max_seconds`**:
   - In `_request_with_retry()`:
     ```python
     if retry_after is not None:
         delay = max(delay, retry_after)
     delay = min(self.config.backoff_max_seconds, delay)
     ```
4. **Fast-Fail on All Non-429 4xx Client Errors**:
   - In `_request_with_retry()`:
     ```python
     if 400 <= e.code < 500 and e.code != 429:
         err_text = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
         raise RuntimeError(f"Meshy API client error {e.code}: {err_text}")
     ```
5. **Invalidate Cache on Corrupt Manifest**:
   - In `check_cache()`: If `manifest_path.is_file()` fails `json.load(f)`, log a warning and treat as cache miss (`continue`).
6. **Update Default Meshy Model to `meshy-6`**:
   - In `MeshyGeneratorConfig`: change `ai_model: str = "meshy-6"`.
7. **Validate `mode` in `generate_plant`**:
   - `if mode not in ("auto", "meshy", "procedural"): raise ValueError(f"Invalid mode: {mode}")`.

---

## 5. Verification Method

To independently reproduce and verify all findings:

1. **Verify Official Test Suite Failure**:
   ```powershell
   uv run pytest teamwork_projects/vegetation_library/tests/test_generator.py -k test_dispatch_mode_meshy_explicit_without_key_raises -v
   ```
   *Result*: Fails with `DID NOT RAISE Exception` due to cache pollution from `./output`.

2. **Verify 42 Adversarial Challenge Tests**:
   ```powershell
   uv run pytest .agents/m2_veg_challenger_1/test_adversarial_generator.py -v -s
   ```
   *Result*: All 42 tests pass, printing empirical evidence of GLB corruption acceptance, Retry-After DoS bypass, and cache hijacking.

3. **Invalidation Conditions**:
   - `uv run pytest teamwork_projects/vegetation_library/tests/ -v` passes 117/117 without regressions.
   - `check_cache()` rejects non-zero corrupted GLB containers.
   - `generate_plant(..., mode="meshy")` never returns procedural cache.
   - `Retry-After` values $> 60$s are strictly capped at `backoff_max_seconds`.
