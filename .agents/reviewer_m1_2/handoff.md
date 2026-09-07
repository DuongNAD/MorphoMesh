# Handoff Report: Reviewer M1_2 (Robustness & Thread-Safety)

**Reviewer ID**: Reviewer M1_2 (Code Reviewer: Robustness, Thread-Safety & Adversarial Analysis)  
**Assigned Directory**: `e:\tool\mcp\MorphoMesh\.agents\reviewer_m1_2`  
**Parent Orchestrator**: `577aaa33-6b3f-4ebc-93eb-fcc632d94bc9`  
**Milestone**: Milestone 1 (Interactive Socket Bridge Parity & Reliability)  
**Date**: 2026-09-07T04:05:00Z  
**Verdict**: **REQUEST_CHANGES**

---

## 1. Observation

### 1.1 Baseline Target Verification
Executed project test targets as instructed:
```powershell
.venv\Scripts\pytest tests/test_bridge_socket_parity.py tests/test_blender_bridge.py -v
```
**Observed Result**:
- `tests/test_bridge_socket_parity.py`: 21 passed in 14.34s.
- `tests/test_blender_bridge.py`: 79 passed in 0.18s.
- Total baseline: **100 passed in 14.34s (100% pass)**.

### 1.2 Adversarial Verification Failures
Executed the comprehensive adversarial challenger test suite:
```powershell
.venv\Scripts\pytest tests/test_m1_adversarial_socket.py -v
```
**Observed Result**:
- **2 failed, 26 passed in 4.45s**.
- **Failure 1**: `TestAdversarialMalformedDataResilience.test_malformed_chaos_fuzzing_interleaving`
  - Location: `tests/test_m1_adversarial_socket.py:614`
  - Verbatim Output:
    ```
    AssertionError: Frame 0 status mismatch: {'jsonrpc': '2.0', 'id': None, 'status': 'error', 'error': {'code': -32700, 'message': 'Parse error: Expecting value: line 1 column 1 (char 0)'}}
    assert 'error' == 'success'
      - success
      + error
    ```
- **Failure 2**: `TestAdversarialDeadlockAndLifecycleResilience.test_client_half_close_shutdown_wr`
  - Location: `tests/test_m1_adversarial_socket.py:825`
  - Verbatim Output:
    ```
    Failed to send response to client for req half-close-1: [WinError 10038] An operation was attempted on something that is not a socket
    assert len(responses) == 1
    assert 0 == 1
     +  where 0 = len([])
    ```

### 1.3 Code Inspection Findings

#### Finding A: Cross-Thread Unsynchronized `client.sendall` Race Condition
In `blender_addon/morphomesh/listener.py`:
- Lines 176–187 (running in background daemon thread `_client_handler`):
  ```python
  except Exception as e_parse:
      logger.error(f"NDJSON line parse error: {e_parse} on raw line: {line[:100]}")
      err_resp = {
          "jsonrpc": "2.0",
          "id": None,
          "status": "error",
          "error": {"code": -32700, "message": f"Parse error: {str(e_parse)}"},
      }
      try:
          client.sendall(json.dumps(err_resp).encode("utf-8") + b"\n")
      except Exception:
          pass
  ```
- Lines 281–286 (running in Blender main thread `_drain_queue`):
  ```python
  try:
      resp_bytes = json.dumps(response, default=str).encode("utf-8") + b"\n"
      if client:
          client.sendall(resp_bytes)
  except Exception as e_send:
      logger.error(f"Failed to send response to client for req {req_id}: {e_send}")
  ```
When a valid command (e.g. `fuzz-1`) is enqueued into `self.command_queue`, and immediately followed by a malformed line (e.g. `GARBAGE_LINE_12345`), the background thread immediately calls `client.sendall` with the parse error response before the main thread timer drains and dispatches `fuzz-1`. This results in out-of-order response delivery and concurrent unsynchronized writes on the same TCP socket.

#### Finding B: Premature Socket Closure on TCP Half-Close (`SHUT_WR` / EOF)
In `blender_addon/morphomesh/listener.py`:
- Lines 160–165 & 217–223 (in `_client_handler`):
  ```python
  data = client.recv(65536)
  if not data:
      # Client disconnected
      break
  ...
  finally:
      with self._clients_lock:
          self._clients.discard(client)
      try:
          client.close()
      except Exception:
          pass
  ```
When a client sends a valid request and signals EOF on its write channel (`sock.shutdown(socket.SHUT_WR)`), `client.recv()` returns `b""`. `_client_handler` breaks the loop and executes `client.close()` in `finally:`. Because `_drain_queue` has not yet processed the command queued on `self.command_queue`, the subsequent write in `_drain_queue` fails with `[WinError 10038] An operation was attempted on something that is not a socket`, dropping the response completely.

#### Finding C: Verified Positive Robustness Behaviors
1. **Windows Socket Graceful Cleanup**:
   In `src/morphomesh/blender_bridge.py` lines 415–425:
   ```python
   finally:
       if sock is not None:
           try:
               sock.shutdown(socket.SHUT_RDWR)
           except OSError:
               pass
           try:
               sock.close()
           except OSError:
               pass
   ```
   Verified via Python `gc` tracking over 50 rapid sequential requests: 0 socket descriptors leaked (initial open sockets: 1, final open sockets: 1, `server._clients` length: 0).
2. **Timer Immortality Exception Barrier**:
   In `blender_addon/morphomesh/listener.py` lines 299–305:
   Traps fatal exceptions and returns `0.02` as long as `self.running` is true. Verified under deliberate non-dict queue injection and unhandled dispatch errors.
3. **Clean Exception Propagation**:
   Verified that `TimeoutError` and `ConnectionRefusedError` propagate cleanly to callers without hanging or socket descriptor leaks.
4. **Integrity Mandate Compliance**:
   No hardcoded test mocks, facade implementations, or fabricated verification outputs were detected. The implementations perform authentic AST analysis, math calculations, and network socket I/O.

---

## 2. Logic Chain

1. **Premise 1 (Observation 1.3 Finding A)**: `_client_handler` runs on a background daemon thread per client, whereas `_drain_queue` runs on Blender's main event loop via `bpy.app.timers`.
2. **Premise 2 (Observation 1.3 Finding A)**: Line 185 allows `_client_handler` to write directly to `client.sendall`, while line 284 allows `_drain_queue` to write directly to `client.sendall` for the same client.
3. **Inference 1**: Because `_client_handler` does not enqueue parse error responses into `command_queue`, any parse error is transmitted over the wire immediately. If a valid request preceded it in `command_queue`, the error response arrives at the client before the valid request's response. This violates FIFO ordering in multiplexed/pipelined connections and directly caused `test_malformed_chaos_fuzzing_interleaving` to fail.
4. **Premise 3 (Observation 1.3 Finding B)**: Under TCP half-close (`SHUT_WR`), `recv()` returns `b""` to indicate the client is done sending, but the client remains listening for incoming responses.
5. **Premise 4 (Observation 1.3 Finding B)**: `_client_handler` treats `b""` as full disconnection and closes `client` in its `finally:` block without checking whether commands for that client remain pending in `self.command_queue`.
6. **Inference 2**: When `client.close()` runs before `_drain_queue` processes the command, `_drain_queue` attempts to write to an invalid file descriptor (`[WinError 10038]`), causing the client to receive 0 bytes and fail `test_client_half_close_shutdown_wr`.
7. **Conclusion**: While baseline functionality and socket descriptor cleanup are solid, the bridge addon exhibits two critical concurrency and socket lifecycle defects under adversarial conditions. A verdict of `REQUEST_CHANGES` is necessary to guarantee robustness.

---

## 3. Caveats

- **Scope Boundary**: Reviewer did not alter any implementation code, strictly honoring the review-only constraint.
- **Mock Environment**: Verification of Blender operations used simulated `mock_bpy_environment`, which accurately mirrors `bpy.app.timers`, `bpy.data`, and `mathutils` semantics on Windows without requiring a dedicated GUI Blender process.

---

## 4. Conclusion

### Final Verdict: REQUEST_CHANGES

The Milestone 1 work product successfully delivers NDJSON framing, Windows socket cleanup (zero leaks), timer immortality barriers, and full dispatch parity across 100 baseline tests. However, two major robustness issues must be resolved before Milestone 1 can be approved:

### Actionable Remediation Requirements:
1. **Remediation 1: Unified Queue for Parse Errors (Eliminate Out-of-Order Race)**:
   In `blender_addon/morphomesh/listener.py` (`_client_handler`), do not call `client.sendall` directly upon catching `json.JSONDecodeError`. Instead, enqueue the error payload to `self.command_queue` as a synthetic error command, e.g.:
   ```python
   self.command_queue.put(({"_is_raw_error": True, "payload": err_resp}, client))
   ```
   In `_drain_queue`, if `cmd.get("_is_raw_error")` is True, serialize and send `cmd["payload"]` to `client`. This guarantees 100% strict FIFO ordering between valid and invalid requests and eliminates multi-threaded socket write races.
2. **Remediation 2: Defer Socket Closure until Pending Commands are Drained**:
   In `blender_addon/morphomesh/listener.py`, when `client.recv()` returns `b""`, do not close the socket immediately if pending requests for that client exist in `self.command_queue`. Instead, enqueue an EOF marker `( {"_is_eof": True}, client )` so `_drain_queue` closes the client socket only after all preceding responses have been transmitted, or check pending client commands before closing.
3. **Remediation 3: Guard Buffer Upper Bound**:
   Add a safety limit in `_client_handler` (e.g. `MAX_BUFFER_SIZE = 16 * 1024 * 1024`) to reset or reject streams that exceed memory limits without newline delimiters.

---

## 5. Verification Method

To verify the fixes independently:
1. Run the baseline tests:
   ```bash
   .venv\Scripts\pytest tests/test_bridge_socket_parity.py tests/test_blender_bridge.py -v
   ```
   (Must pass 100/100).
2. Run the adversarial stress test suite:
   ```bash
   .venv\Scripts\pytest tests/test_m1_adversarial_socket.py -v
   ```
   (Must pass 28/28 with 0 failures, specifically passing `test_malformed_chaos_fuzzing_interleaving` and `test_client_half_close_shutdown_wr`).
3. Invalidation Conditions:
   - Any response delivered out of order during interleaved valid/garbage streams.
   - Any dropped response when client issues `shutdown(socket.SHUT_WR)`.
   - Any failure in `pytest tests/test_bridge_socket_parity.py` or `pytest tests/test_m1_adversarial_socket.py`.
