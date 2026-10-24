# Handoff Report: Milestone 2 Iteration 2 Adversarial Stress Testing

- **Agent**: Challenger 1 (`m2_iter2_veg_challenger_1`)
- **Working Directory**: `E:\tool\mcp\MorphoMesh\.agents\m2_iter2_veg_challenger_1`
- **Role**: Critic, Empirical Challenger, Specialist
- **Date**: 2026-09-10T06:21:00Z
- **Target File**: `teamwork_projects/vegetation_library/vegetation_pipeline/generator.py`
- **Parent Conversation ID**: `1f2774e9-3e4e-4a4c-8dc6-f85249e37b16`
- **Empirical Verdict**: **APPROVE** (All 6 Primary Adversarial Invariants Verified; 1 Minor Hardening Advisory)

---

## 1. Observation

### 1.1 Remediation Implementation in `generator.py`
Direct inspection of `teamwork_projects/vegetation_library/vegetation_pipeline/generator.py` reveals the following remediations implemented by Worker 2:

1. **Retry-After Clamping and Anti-DoS (`generator.py:255-268`)**:
   ```python
   255:                 retry_after: Optional[float] = None
   256:                 if hasattr(e, "headers") and e.headers and "Retry-After" in e.headers:
   257:                     try:
   258:                         retry_after = float(e.headers["Retry-After"])
   259:                     except (ValueError, TypeError):
   260:                         pass
   261: 
   262:                 base_delay = self.config.backoff_base_seconds * (2 ** (attempt - 1))
   263:                 jitter = random.uniform(0.0, 0.5)
   264:                 delay = base_delay + jitter
   265:                 if retry_after is not None:
   266:                     delay = max(delay, retry_after)
   267:                 delay = min(self.config.backoff_max_seconds, delay)
   ```
   `delay` is capped against `self.config.backoff_max_seconds` (default `60.0s`) *after* incorporating `retry_after`.

2. **Fast-Fail on Non-429 4xx Client Errors (`generator.py:240-245`)**:
   ```python
   240:                 # Terminal client errors: fail fast without retry (all 4xx except 429 Rate Limit)
   241:                 if 400 <= e.code < 500 and e.code != 429:
   242:                     err_text = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
   243:                     raise RuntimeError(
   244:                         f"Meshy API client error {e.code}: {err_text}"
   245:                     )
   ```
   All client errors in the range `[400, 500)` excluding 429 terminate immediately without sleeping or incrementing attempts.

3. **Mode Dispatch and Provenance Enforcement in `generate_plant` (`generator.py:1454-1486`)**:
   ```python
   1454:     # 0. Validate generation mode
   1455:     if mode not in ("auto", "meshy", "procedural"):
   1456:         raise ValueError(f"Invalid generation mode: '{mode}'")
   ...
   1477:     # 4. Mode: Explicit Meshy
   1478:     if mode == "meshy":
   1479:         api_key = meshy_gen.resolve_api_key()
   1480:         if not api_key:
   1481:             raise RuntimeError("MESHY_API_KEY API key environment variable is not set")
   1482:         if not force_regenerate and not meshy_gen.config.force_regenerate and meshy_gen.config.use_cache:
   1483:             cached_asset = meshy_gen.check_cache(species_obj, target_dir=out_path, expected_source="meshy")
   1484:             if cached_asset is not None:
   1485:                 return cached_asset
   1486:         return meshy_gen.generate(species_obj, output_dir=out_path, force_regenerate=force_regenerate)
   ```
   In `mode="meshy"`, `resolve_api_key()` is evaluated first; if missing, `RuntimeError` is raised immediately before disk cache lookup, preventing cache-masquerade bypass. Furthermore, `expected_source="meshy"` is passed to `check_cache`.

4. **Binary GLB Header and Truncation Validation (`generator.py:469-493`)**:
   ```python
   469:             try:
   470:                 file_size = glb_path.stat().st_size
   471:                 if file_size < 12:
   472:                     continue
   473:                 with open(glb_path, "rb") as f:
   474:                     header = f.read(12)
   475:                 if len(header) < 12:
   476:                     continue
   477:                 magic, version, total_length = struct.unpack_from("<4sII", header, 0)
   478:                 if magic != b"glTF" or version != 2:
   479:                     logger.warning(...)
   480:                     continue
   481:                 if total_length > file_size:
   482:                     logger.warning(...)
   483:                     continue
   ```

5. **Manifest Parsing and Source Provenance Filter (`generator.py:524-550`)**:
   ```python
   524:             # Read manifest & verify JSON integrity
   525:             manifest_path = cand / "cache_manifest.json"
   526:             manifest_data: Dict[str, Any] = {}
   527:             if manifest_path.is_file():
   528:                 try:
   529:                     with open(manifest_path, "r", encoding="utf-8") as f:
   530:                         manifest_data = json.load(f)
   531:                 except Exception as e:
   532:                     logger.warning(...)
   533:                     continue
   534:             elif expected_source is not None:
   535:                 continue
   536: 
   537:             # Provenance source check
   538:             if expected_source is not None:
   539:                 manifest_source = manifest_data.get("source")
   540:                 if manifest_source != expected_source:
   541:                     continue
   ```

### 1.2 Adversarial Test Suite Results
The adversarial test suite `test_adversarial_m2_iter2.py` was executed via `uv run pytest .agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py -v`:
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
rootdir: E:\tool\mcp\MorphoMesh
collected 54 items

.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestRetryAfterCapping::test_retry_after_86400_clamped_to_default_60s PASSED [  1%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestRetryAfterCapping::test_retry_after_clamped_to_custom_backoff_max PASSED [  3%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestRetryAfterCapping::test_multi_attempt_429_flood_strictly_capped_and_exceeds_max_retries PASSED [  5%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestRetryAfterCapping::test_retry_after_malformed_string_graceful_fallback PASSED [  7%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestFastFailOnNon429ClientErrors::test_fast_fail_required_4xx_codes[400] PASSED [  9%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestFastFailOnNon429ClientErrors::test_fast_fail_required_4xx_codes[401] PASSED [ 11%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestFastFailOnNon429ClientErrors::test_fast_fail_required_4xx_codes[403] PASSED [ 12%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestFastFailOnNon429ClientErrors::test_fast_fail_required_4xx_codes[404] PASSED [ 14%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestFastFailOnNon429ClientErrors::test_fast_fail_required_4xx_codes[405] PASSED [ 16%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestFastFailOnNon429ClientErrors::test_fast_fail_required_4xx_codes[408] PASSED [ 18%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestFastFailOnNon429ClientErrors::test_fast_fail_required_4xx_codes[409] PASSED [ 20%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestFastFailOnNon429ClientErrors::test_fast_fail_required_4xx_codes[413] PASSED [ 22%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestFastFailOnNon429ClientErrors::test_fast_fail_required_4xx_codes[415] PASSED [ 24%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestFastFailOnNon429ClientErrors::test_fast_fail_required_4xx_codes[422] PASSED [ 25%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestFastFailOnNon429ClientErrors::test_fast_fail_extended_edge_4xx_codes[402] PASSED [ 27%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestFastFailOnNon429ClientErrors::test_fast_fail_extended_edge_4xx_codes[406] PASSED [ 29%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestFastFailOnNon429ClientErrors::test_fast_fail_extended_edge_4xx_codes[410] PASSED [ 31%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestFastFailOnNon429ClientErrors::test_fast_fail_extended_edge_4xx_codes[411] PASSED [ 33%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestFastFailOnNon429ClientErrors::test_fast_fail_extended_edge_4xx_codes[412] PASSED [ 35%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestFastFailOnNon429ClientErrors::test_fast_fail_extended_edge_4xx_codes[414] PASSED [ 37%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestFastFailOnNon429ClientErrors::test_fast_fail_extended_edge_4xx_codes[418] PASSED [ 38%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestFastFailOnNon429ClientErrors::test_fast_fail_extended_edge_4xx_codes[428] PASSED [ 40%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestFastFailOnNon429ClientErrors::test_fast_fail_extended_edge_4xx_codes[431] PASSED [ 42%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestFastFailOnNon429ClientErrors::test_fast_fail_extended_edge_4xx_codes[451] PASSED [ 44%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestFastFailOnNon429ClientErrors::test_server_5xx_errors_do_retry_with_backoff[500] PASSED [ 46%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestFastFailOnNon429ClientErrors::test_server_5xx_errors_do_retry_with_backoff[502] PASSED [ 48%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestFastFailOnNon429ClientErrors::test_server_5xx_errors_do_retry_with_backoff[503] PASSED [ 50%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestFastFailOnNon429ClientErrors::test_server_5xx_errors_do_retry_with_backoff[504] PASSED [ 51%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestCacheProvenanceAndCredentialEnforcement::test_mode_meshy_with_keys_stripped_rejects_procedural_cache PASSED [ 53%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestCacheProvenanceAndCredentialEnforcement::test_mode_meshy_with_key_rejects_procedural_cache_provenance PASSED [ 55%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestCacheProvenanceAndCredentialEnforcement::test_check_cache_rejects_manifest_without_source_tag PASSED [ 57%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestCacheProvenanceAndCredentialEnforcement::test_check_cache_rejects_missing_manifest_when_expected_source_specified PASSED [ 59%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestCacheProvenanceAndCredentialEnforcement::test_valid_meshy_cache_returned_when_credentials_present PASSED [ 61%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestCorruptGlbDetection::test_corrupt_glb_100_bytes_ascii_garbage_rejected PASSED [ 62%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestCorruptGlbDetection::test_corrupt_glb_less_than_12_bytes PASSED [ 64%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestCorruptGlbDetection::test_corrupt_glb_zero_bytes PASSED [ 66%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestCorruptGlbDetection::test_corrupt_glb_invalid_magic_bytes PASSED [ 68%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestCorruptGlbDetection::test_corrupt_glb_invalid_version PASSED [ 70%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestCorruptGlbDetection::test_corrupt_glb_truncated_total_length PASSED [ 72%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestTruncatedManifestHandling::test_truncated_json_in_cache_manifest PASSED [ 74%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestTruncatedManifestHandling::test_zero_byte_cache_manifest PASSED [ 75%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestTruncatedManifestHandling::test_syntax_corrupt_cache_manifest PASSED [ 77%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestModeValidation::test_invalid_generation_modes_raise_value_error[invalid_xyz] PASSED [ 79%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestModeValidation::test_invalid_generation_modes_raise_value_error[] PASSED [ 81%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestModeValidation::test_invalid_generation_modes_raise_value_error[MESHY] PASSED [ 83%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestModeValidation::test_invalid_generation_modes_raise_value_error[PROCEDURAL] PASSED [ 85%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestModeValidation::test_invalid_generation_modes_raise_value_error[AUTO] PASSED [ 87%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestModeValidation::test_invalid_generation_modes_raise_value_error[mesh] PASSED [ 88%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestModeValidation::test_invalid_generation_modes_raise_value_error[procedural_fallback] PASSED [ 90%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestModeValidation::test_invalid_generation_modes_raise_value_error[random_mode] PASSED [ 92%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestModeValidation::test_invalid_generation_modes_raise_value_error[None] PASSED [ 94%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestModeValidation::test_valid_generation_modes_accepted_at_entry_boundary[auto] PASSED [ 96%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestModeValidation::test_valid_generation_modes_accepted_at_entry_boundary[meshy] PASSED [ 98%]
.agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py::TestModeValidation::test_valid_generation_modes_accepted_at_entry_boundary[procedural] PASSED [100%]

============================= 54 passed in 0.88s ==============================
```

### 1.3 Full Test Suite Regression Check
The entire vegetation library test suite was executed via `uv run pytest teamwork_projects/vegetation_library/tests/ -v`:
```
============================= 148 passed in 4.91s =============================
```

### 1.4 Non-Dict Manifest Type Hardening Observation
Execution of `empirical_manifest_type_finding.py` revealed that if `cache_manifest.json` contains valid JSON that is not a JSON object/mapping (e.g. `[1, 2, 3]`, `12345`, `"string"`, `null`, `true`), `check_cache` crashes with `AttributeError` or `TypeError` instead of gracefully treating it as a cache miss:
```
[Array / List] with expected_source='meshy': CRASHED with AttributeError: 'list' object has no attribute 'get'
[Scalar Integer] with expected_source=None: CRASHED with TypeError: argument of type 'int' is not iterable
[JSON null] with expected_source='meshy': CRASHED with AttributeError: 'NoneType' object has no attribute 'get'
```

---

## 2. Logic Chain

1. **Retry-After Capping (DoS Immunity)**:
   - *Observation 1.1.1 & 1.2*: Line 267 `delay = min(self.config.backoff_max_seconds, delay)` is positioned after `delay = max(delay, retry_after)`.
   - *Logic*: When a malicious or upstream load-shedding response sends `Retry-After: 86400`, `delay` is set to 86400.0, and then clamped to `backoff_max_seconds` (60.0s).
   - *Empirical Verification*: Test 1.1 proved `sleep_recorded[0] == 60.0` exactly, and Test 1.2 proved custom limits (e.g. 10.0s) clamp to 10.0s. Test 1.3 proved multi-attempt rate-limit storms clamp every sleep to `backoff_max_seconds` and terminate at `max_retries`.

2. **Fast-Fail on 4xx Client Errors**:
   - *Observation 1.1.2 & 1.2*: Line 241 `if 400 <= e.code < 500 and e.code != 429:` checks all HTTP 4xx errors except 429.
   - *Logic*: Because non-429 client errors (e.g. 400 bad request, 401 unauthorized, 403 forbidden, 404 not found, 408 timeout, 409 conflict, 413 payload too large, 415 unsupported media, 422 unprocessable entity) represent terminal caller faults, retrying them is futile and wastes time.
   - *Empirical Verification*: Tests 2.1 and 2.2 proved that for all 10 required codes + 10 extended codes, `urlopen` was invoked exactly once (0 retries), `time.sleep` was called 0 times, and `RuntimeError` was raised immediately. Test 2.3 verified that transient 5xx errors (500, 502, 503, 504) preserve retry semantics.

3. **Cache Provenance & Credential Isolation**:
   - *Observation 1.1.3 & 1.2*: Line 1479 validates `api_key` before calling `check_cache(expected_source="meshy")`. Line 538-549 in `check_cache` filters `manifest_source == expected_source`.
   - *Logic*: In Milestone 2 Iteration 1, pre-existing procedural assets in `./output` were returned to callers invoking `mode="meshy"`, even when callers lacked credentials. With the remediation, stripped credentials trigger immediate `RuntimeError("MESHY_API_KEY API key environment variable is not set")`, and `check_cache` strictly rejects assets with `source="procedural"` when `expected_source="meshy"`.
   - *Empirical Verification*: Test 3.1 confirmed `RuntimeError` is raised when keys are stripped and procedural cache exists. Test 3.2 confirmed that even with a dummy key, `check_cache` returns `None` for procedural cache. Tests 3.3 and 3.4 confirmed rejection of missing or non-tagged manifests.

4. **Corrupt GLB Detection**:
   - *Observation 1.1.4 & 1.2*: Lines 469-489 unpack the 12-byte header `<4sII`, asserting `magic == b"glTF"`, `version == 2`, and `total_length <= file_size`.
   - *Logic*: Non-GLB files (e.g. 100-byte ASCII text files, corrupt download fragments) cannot produce magic `b"glTF"` or version 2. Truncated downloads will fail the `total_length <= file_size` check.
   - *Empirical Verification*: Tests 4.1 through 4.6 verified that 100-byte ASCII text, 0-byte, sub-12-byte, invalid magic (`b"RIFF"`, `b"\x89PNG"`, `b"PK\x03\x04"`), invalid versions (0, 1, 3), and truncated lengths all return `None` (cache miss).

5. **Truncated Manifest Handling**:
   - *Observation 1.1.5 & 1.2*: Lines 528-536 wrap `json.load` in a `try...except Exception` block, logging a warning and executing `continue` on parse failure.
   - *Logic*: Interrupted writes produce malformed JSON syntax or truncated strings, which raise `json.JSONDecodeError`. Catching this and treating the cache candidate as a miss prevents crashes.
   - *Empirical Verification*: Tests 5.1 through 5.3 verified that truncated JSON, 0-byte manifest, and corrupt syntax manifests safely return `None`.

6. **Generation Mode Validation**:
   - *Observation 1.1.3 & 1.2*: Line 1455 `if mode not in ("auto", "meshy", "procedural"): raise ValueError(...)` executes at entry.
   - *Logic*: Callers passing unknown, misspelled, or uppercase modes receive immediate actionable errors before any compute or I/O.
   - *Empirical Verification*: Tests 6.1 and 6.2 confirmed all invalid modes raise `ValueError` and all valid modes pass.

---

## 3. Caveats

1. **Non-Dict Manifest Edge Case (Advisory)**:
   If `cache_manifest.json` is modified or written by an external tool with non-object JSON (e.g. `[1, 2, 3]`, `12345`, `null`), `json.load` does not raise an exception, leading to an `AttributeError` or `TypeError` downstream in `check_cache`. This is easily remediated with a two-line type guard:
   ```python
   if not isinstance(manifest_data, dict):
       logger.warning("Manifest at %s is not a JSON object. Treating as cache miss.", manifest_path)
       continue
   ```
   This is non-blocking for Milestone 2 since engine-generated manifests are always JSON dicts and truncated manifests are properly handled, but is documented for future defense-in-depth hardening.
2. **Live Meshy API Mocks**: Tests use high-fidelity HTTP mocks for `urllib.request.urlopen` to verify HTTP status codes, backoff clamping, and payload formatting without consuming external Meshy API cloud credits.
3. No other caveats.

---

## 4. Conclusion

**Verdict: APPROVE**

The remediations delivered in `generator.py` for Milestone 2 Iteration 2 are robust, comprehensive, and empirically verified:
1. `Retry-After: 86400` is strictly clamped to `backoff_max_seconds` (default 60.0s), preventing denial-of-service thread freezing.
2. Non-429 4xx client errors (400, 401, 403, 404, 405, 408, 409, 413, 415, 422 + extended codes) fail fast immediately on attempt 1 with 0 retries and 0 sleep.
3. Cache provenance is strictly enforced: procedural cache assets are never returned for explicit `mode="meshy"` requests, and missing credentials raise `RuntimeError` before cache lookup.
4. Corrupt GLB files (100-byte ASCII garbage, sub-12-byte, invalid magic, invalid version, truncated length) are rejected as cache misses.
5. Truncated and corrupt JSON manifests are rejected as cache misses.
6. Generation modes are validated at the entry gate, rejecting invalid modes with `ValueError`.
7. All 54 tests in the adversarial stress test suite pass with 100% success.
8. All 148 tests in the vegetation library test suite pass with 100% success.

---

## 5. Verification Method

To independently reproduce and verify this empirical challenge:

1. **Run Adversarial Stress Test Suite via pytest**:
   ```powershell
   uv run pytest .agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py -v
   ```
   *Expected Output*: `54 passed in ~0.9s` (exit code 0).

2. **Run Standalone Adversarial Script**:
   ```powershell
   uv run python .agents/m2_iter2_veg_challenger_1/test_adversarial_m2_iter2.py
   ```
   *Expected Output*: All tests pass, with detailed logs showing clamped sleep times, 0 retries on 4xx, and rejected corrupt headers.

3. **Run Full Vegetation Library Test Suite**:
   ```powershell
   uv run pytest teamwork_projects/vegetation_library/tests/ -v
   ```
   *Expected Output*: `148 passed` (exit code 0).

4. **Verify Non-Dict Manifest Edge Case Script**:
   ```powershell
   uv run python .agents/m2_iter2_veg_challenger_1/empirical_manifest_type_finding.py
   ```
   *Expected Output*: Demonstrates the non-dict manifest behavior documented in Caveats.
