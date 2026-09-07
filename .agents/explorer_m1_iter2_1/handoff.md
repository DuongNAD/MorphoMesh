# Handoff Report: Explorer M1 Iteration 2 - 1 (Socket Concurrency Remediation Blueprint)

**Agent ID**: Explorer M1 Iteration 2 - 1 (`explorer_m1_iter2_1`)  
**Assigned Directory**: `e:\tool\mcp\MorphoMesh\.agents\explorer_m1_iter2_1`  
**Parent Orchestrator ID**: `577aaa33-6b3f-4ebc-93eb-fcc632d94bc9`  
**Target Milestone**: Milestone 1 (Interactive Socket Bridge Parity & Reliability - R3)  
**Date**: 2026-09-07T04:14:00Z  
**Verdict**: **INVESTIGATION_COMPLETE** (Line-by-Line Blueprint Ready for Worker Implementation)  

---

## 1. Observation

### 1.1 Verbatim Challenger / Reviewer Failures
In Iteration 1, the test suite `tests/test_m1_adversarial_socket.py` produced 2 deterministic failures out of 28 tests:

1. **Failure 1: Queue-Bypass Response Reordering Race Condition**
   - Test: `TestAdversarialMalformedDataResilience.test_malformed_chaos_fuzzing_interleaving` (`tests/test_m1_adversarial_socket.py:614`)
   - Verbatim Error:
     ```
     AssertionError: Frame 0 status mismatch: {'jsonrpc': '2.0', 'id': None, 'status': 'error', 'error': {'code': -32700, 'message': 'Parse error: Expecting value: line 1 column 1 (char 0)'}}
     assert 'error' == 'success'
       - success
       + error
     ```
   - Source Cause: In `blender_addon/morphomesh/listener.py` lines 176–187, upon catching `json.JSONDecodeError`, the background reader thread called `client.sendall(json.dumps(err_resp)...)` directly to the socket, completely bypassing `self.command_queue`. When a valid command preceded a malformed line in the same TCP chunk, the error response for the malformed line was transmitted immediately, arriving before the valid command's response was drained by the main thread.

2. **Failure 2: Premature Socket Teardown on TCP EOF (`SHUT_WR`)**
   - Test: `TestAdversarialDeadlockAndLifecycleResilience.test_client_half_close_shutdown_wr` (`tests/test_m1_adversarial_socket.py:825`)
   - Verbatim Error:
     ```
     Failed to send response to client for req half-close-1: [WinError 10038] An operation was attempted on something that is not a socket
     assert len(responses) == 1
     assert 0 == 1
      +  where 0 = len([])
     ```
   - Source Cause: In `blender_addon/morphomesh/listener.py` lines 160–165 & 218–223, when `client.recv()` returned `b""` (indicating TCP EOF / client half-close `SHUT_WR`), `_client_handler` broke out of the loop and immediately executed `client.close()` in `finally:`. Because the queued command had not yet been processed by Blender's main-thread timer in `_drain_queue()`, the main thread attempted to write to an already-closed socket handle, raising `[WinError 10038]` and dropping the response.

### 1.2 Inspection of Current Code and Interim Worker Fix
Direct inspection of `blender_addon/morphomesh/listener.py` (lines 160–275) revealed that an interim fix was attempted by Worker M1:
- In `_client_handler` (lines 163–171):
  ```python
  if not data:
      # Client disconnected or half-closed (SHUT_WR)
      # Allow pending commands for this client to drain before closing
      start_wait = time.time()
      while time.time() - start_wait < 1.0:
          if not any(c is client for _, c in list(self.command_queue.queue)):
              break
          time.sleep(0.01)
      break
  ```
- In `_client_handler` (lines 183–192):
  ```python
  except Exception as e_parse:
      logger.error(f"NDJSON line parse error: {e_parse} on raw line: {line[:100]}")
      err_resp = {
          "_is_preformatted_response": True,
          "jsonrpc": "2.0",
          "id": None,
          "status": "error",
          "error": {"code": -32700, "message": f"Parse error: {str(e_parse)}"},
      }
      self.command_queue.put((err_resp, client))
  ```
- In `_drain_queue` (lines 249–257):
  ```python
  if isinstance(cmd, dict) and cmd.get("_is_preformatted_response"):
      resp_dict = dict(cmd)
      resp_dict.pop("_is_preformatted_response", None)
      try:
          if client:
              client.sendall(json.dumps(resp_dict).encode("utf-8") + b"\n")
      except Exception:
          pass
      continue
  ```

### 1.3 Critical Vulnerabilities in the Interim Fix
While the interim fix allowed fast mock pings to pass, deeper code analysis revealed two severe vulnerabilities:

1. **The In-Flight Execution Race Condition**:
   In `_drain_queue` (line 242):
   ```python
   cmd, client = self.command_queue.get_nowait()
   ```
   As soon as `_drain_queue` retrieves `(cmd, client)`, that command is removed from `self.command_queue.queue`. At this moment, `_drain_queue` begins executing `self._dispatch(method, params)`.
   Concurrently in `_client_handler`:
   ```python
   if not any(c is client for _, c in list(self.command_queue.queue)):
       break
   ```
   Because `cmd` has been popped from the queue, `any(c is client ...)` evaluates to `False`. The polling loop breaks immediately and enters `finally: client.close()`. If `_dispatch` takes more than a few milliseconds (e.g. 50ms for complex mesh operations), `client.close()` executes *while* `_dispatch` is still running, and `client.sendall()` fails with `[WinError 10038]` when `_dispatch` completes.
2. **Private Attribute & Thread-Safety Violation**:
   `self.command_queue.queue` accesses the underlying `collections.deque` without holding `self.command_queue.mutex`. Calling `list(self.command_queue.queue)` concurrently with thread `.put()` operations can raise `RuntimeError: deque mutated during iteration`.
3. **Arbitrary 1.0-Second Timeout**:
   If a heavy command takes longer than 1.0 second (e.g. human generation or topology optimization), the loop times out and unconditionally aborts the connection.
4. **Unhandled Trailing Malformed Buffer on EOF**:
   In lines 214–220:
   ```python
   if buffer.strip():
       try:
           cmd = json.loads(buffer.strip().decode("utf-8"))
           self.command_queue.put((cmd, client))
       except Exception:
           pass
   ```
   If a half-closed client sent a trailing malformed payload without newline, the exception is caught with `pass` and dropped instead of returning code `-32700`.

---

## 2. Logic Chain

1. **Premise 1 (FIFO Stream Contract)**: The interactive socket protocol uses newline-delimited JSON (NDJSON) over TCP. Clients multiplex pipelined requests over persistent connections and match responses either by index or RPC `id`. Every response — whether success, method error, invalid request primitive (-32600), or syntax parse error (-32700) — must be emitted in the strict order the frames were received.
2. **Premise 2 (Concurrency Decoupling)**: `_client_handler` threads run asynchronously in background daemon threads, reading raw TCP frames. `_drain_queue` runs on Blender's main thread via `bpy.app.timers`. The only shared communication channel is `self.command_queue` (`queue.Queue`).
3. **Inference 1 (Remediation for Issue 1)**: If `_client_handler` enqueues preformatted error payloads `({"_is_preformatted_response": True, ...}, client)` into `self.command_queue` on both in-stream parse errors and EOF trailing buffer errors, `_drain_queue` will drain and transmit them in exact chronological sequence. No response can overtake preceding requests.
4. **Premise 3 (TCP Half-Close Semantics)**: In standard TCP communication, a client may close its transmit pipe via `client.shutdown(socket.SHUT_WR)` to indicate it has finished sending data, while keeping its receive pipe open to await server responses. When the server reads `b""` from `recv()`, it indicates client transmit EOF, NOT permission to immediately destroy the socket handle.
5. **Premise 4 (Queue FIFO Ordering for Lifecycle Events)**: Because `queue.Queue` maintains strict FIFO ordering, any sentinel enqueued *after* client commands will be dequeued *after* all those commands have been dispatched and responded to.
6. **Inference 2 (Remediation for Issue 2 via EOF Sentinel)**:
   - When `_client_handler` terminates (upon EOF `not data`, socket error, or shutdown), instead of polling `self.command_queue.queue` and calling `client.close()`, it simply enqueues an EOF sentinel:
     ```python
     self.command_queue.put(({"_is_eof": True}, client))
     ```
   - In `_drain_queue`, when `_is_eof` is dequeued:
     All prior commands for that client have ALREADY been executed and their responses sent via `client.sendall()`.
     `_drain_queue` safely discards `client` from `self._clients` and closes `client.close()`.
7. **Inference 3 (Elimination of Races & Private Attributes)**:
   - The EOF sentinel pattern requires zero sleep loops, zero timeouts, and zero access to private queue attributes.
   - It eliminates the in-flight execution race condition completely: whether `_dispatch` takes 1 millisecond or 60 seconds, `client.close()` is never invoked until `_drain_queue` finishes writing the response and advances to the sentinel.
8. **Inference 4 (Robust Network Exception Containment)**:
   In `_drain_queue`, catching `OSError` explicitly on `client.sendall()` (covering `BrokenPipeError`, `ConnectionResetError`, `[WinError 10038]`, and `[WinError 10054]`) suppresses noisy false-alarm error logs when a remote client abruptly exits, and prevents useless fallback attempts to serialize error responses to a dead socket.

---

## 3. Caveats

1. **Server Shutdown Coordination**:
   If `MorphoMeshSocketServer.stop()` is called, `self.running` becomes `False`. In `stop()`, all sockets in `self._clients` are closed directly and `command_queue` is flushed. The blueprint accounts for this: if `self.running` is False when `_client_handler` exits, the handler does not bother enqueueing `_is_eof` and performs immediate socket cleanup.
2. **Buffer Flooding Guard**:
   To prevent denial-of-service or memory exhaustion from clients streaming gigabytes of data without newlines, the blueprint includes a 16MB maximum buffer size guard (`MAX_BUFFER_SIZE = 16 * 1024 * 1024`).
3. **No Source Code Modified**:
   In strict accordance with the read-only Explorer role, no source files were modified during this investigation. All blueprints are delivered as explicit, line-by-line patch specifications below.

---

## 4. Conclusion & Implementation Blueprint

### 4.1 Executive Assessment
The concurrency and socket lifecycle defects in `blender_addon/morphomesh/listener.py` can be definitively resolved by:
1. **Unifying all parse error responses** (both within the newline split loop and the EOF trailing buffer) through `self.command_queue` with `_is_preformatted_response: True`.
2. **Replacing the flawed polling check** (`list(self.command_queue.queue)`) with an **in-stream EOF Sentinel** (`{"_is_eof": True}`) placed in `self.command_queue` upon `_client_handler` exit.
3. **Draining and closing client sockets exclusively on the main thread** when the EOF sentinel is processed by `_drain_queue`.
4. **Adding explicit `OSError` containment** in `_drain_queue` to handle sudden socket resets gracefully.

---

### 4.2 Exact Line-by-Line Blueprint for `blender_addon/morphomesh/listener.py`

#### Target File
`blender_addon/morphomesh/listener.py`

#### Change 1: Replace Polling & In-Thread Close with EOF Sentinel in `_client_handler`
**Location**: `blender_addon/morphomesh/listener.py`, lines 160–228.

**Before**:
```python
            while self.running:
                try:
                    data = client.recv(65536)
                    if not data:
                        # Client disconnected or half-closed (SHUT_WR)
                        # Allow pending commands for this client to drain before closing
                        start_wait = time.time()
                        while time.time() - start_wait < 1.0:
                            if not any(c is client for _, c in list(self.command_queue.queue)):
                                break
                            time.sleep(0.01)
                        break
                    buffer += data

                    # 1. Process all newline-delimited lines (NDJSON streaming)
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            cmd = json.loads(line.decode("utf-8"))
                            self.command_queue.put((cmd, client))
                        except Exception as e_parse:
                            logger.error(f"NDJSON line parse error: {e_parse} on raw line: {line[:100]}")
                            err_resp = {
                                "_is_preformatted_response": True,
                                "jsonrpc": "2.0",
                                "id": None,
                                "status": "error",
                                "error": {"code": -32700, "message": f"Parse error: {str(e_parse)}"},
                            }
                            self.command_queue.put((err_resp, client))

                    # 2. Fallback: Parse complete JSON object if no trailing newline was sent
                    if buffer.strip():
                        try:
                            text = buffer.decode("utf-8")
                            stripped_text = text.lstrip()
                            lead_spaces = len(text) - len(stripped_text)
                            obj, end_idx = decoder.raw_decode(stripped_text)
                            self.command_queue.put((obj, client))
                            consumed_chars = lead_spaces + end_idx
                            buffer = text[consumed_chars:].encode("utf-8")
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            # Partial data chunk, wait for next recv
                            pass

                except socket.timeout:
                    continue
                except Exception as e_sock:
                    logger.debug(f"Client socket exception: {e_sock}")
                    break

            # Process any remaining complete command on EOF
            if buffer.strip():
                try:
                    cmd = json.loads(buffer.strip().decode("utf-8"))
                    self.command_queue.put((cmd, client))
                except Exception:
                    pass

        finally:
            with self._clients_lock:
                self._clients.discard(client)
            try:
                client.close()
            except Exception:
                pass
```

**After**:
```python
            while self.running:
                try:
                    data = client.recv(65536)
                    if not data:
                        # Client disconnected or half-closed (SHUT_WR)
                        break
                    buffer += data

                    # Safety guard: prevent unbounded buffer growth on malicious streams
                    if len(buffer) > 16 * 1024 * 1024:
                        logger.error("Client buffer exceeded 16MB limit without newline delimiter; closing stream")
                        break

                    # 1. Process all newline-delimited lines (NDJSON streaming)
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            cmd = json.loads(line.decode("utf-8"))
                            self.command_queue.put((cmd, client))
                        except Exception as e_parse:
                            logger.error(f"NDJSON line parse error: {e_parse} on raw line: {line[:100]}")
                            err_resp = {
                                "_is_preformatted_response": True,
                                "jsonrpc": "2.0",
                                "id": None,
                                "status": "error",
                                "error": {"code": -32700, "message": f"Parse error: {str(e_parse)}"},
                            }
                            self.command_queue.put((err_resp, client))

                    # 2. Fallback: Parse complete JSON object if no trailing newline was sent
                    if buffer.strip():
                        try:
                            text = buffer.decode("utf-8")
                            stripped_text = text.lstrip()
                            lead_spaces = len(text) - len(stripped_text)
                            obj, end_idx = decoder.raw_decode(stripped_text)
                            self.command_queue.put((obj, client))
                            consumed_chars = lead_spaces + end_idx
                            buffer = text[consumed_chars:].encode("utf-8")
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            # Partial data chunk, wait for next recv
                            pass

                except socket.timeout:
                    continue
                except Exception as e_sock:
                    logger.debug(f"Client socket exception: {e_sock}")
                    break

            # Process any remaining complete command on EOF (or queue parse error if corrupted)
            if buffer.strip():
                try:
                    cmd = json.loads(buffer.strip().decode("utf-8"))
                    self.command_queue.put((cmd, client))
                except Exception as e_parse:
                    logger.error(f"NDJSON EOF line parse error: {e_parse} on raw line: {buffer[:100]}")
                    err_resp = {
                        "_is_preformatted_response": True,
                        "jsonrpc": "2.0",
                        "id": None,
                        "status": "error",
                        "error": {"code": -32700, "message": f"Parse error: {str(e_parse)}"},
                    }
                    self.command_queue.put((err_resp, client))

        finally:
            # Defer socket closure until all queued commands for this client have been drained by main thread
            if self.running:
                self.command_queue.put(({"_is_eof": True}, client))
            else:
                with self._clients_lock:
                    self._clients.discard(client)
                try:
                    client.close()
                except Exception:
                    pass
```

---

#### Change 2: Handle `_is_eof` Sentinel and Robust Response Writing in `_drain_queue`
**Location**: `blender_addon/morphomesh/listener.py`, lines 240–305.

**Before**:
```python
        try:
            while not self.command_queue.empty():
                try:
                    cmd, client = self.command_queue.get_nowait()
                except queue.Empty:
                    break
                except Exception as e_queue:
                    logger.error(f"Error retrieving command from queue: {e_queue}")
                    break

                if isinstance(cmd, dict) and cmd.get("_is_preformatted_response"):
                    resp_dict = dict(cmd)
                    resp_dict.pop("_is_preformatted_response", None)
                    try:
                        if client:
                            client.sendall(json.dumps(resp_dict).encode("utf-8") + b"\n")
                    except Exception:
                        pass
                    continue

                if not isinstance(cmd, dict):
                    err_resp = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "status": "error",
                        "error": {"code": -32600, "message": "Invalid Request: Expected JSON object dict"},
                    }
                    try:
                        if client:
                            client.sendall(json.dumps(err_resp).encode("utf-8") + b"\n")
                    except Exception:
                        pass
                    continue

                req_id = cmd.get("id", "res-1")
                method = cmd.get("method") or cmd.get("type", "")
                params = cmd.get("params", {})
                if not isinstance(params, dict):
                    params = {}

                try:
                    result = self._dispatch(method, params)
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "status": "success",
                        "result": result,
                    }
                except Exception as e_dispatch:
                    logger.error(f"Error executing RPC method '{method}': {e_dispatch}", exc_info=True)
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "status": "error",
                        "error": {"code": -32000, "message": str(e_dispatch)},
                    }

                try:
                    resp_bytes = json.dumps(response, default=str).encode("utf-8") + b"\n"
                    if client:
                        client.sendall(resp_bytes)
                except Exception as e_send:
                    logger.error(f"Failed to send response to client for req {req_id}: {e_send}")
                    try:
                        fallback_err = {
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "status": "error",
                            "error": {"code": -32603, "message": f"Serialization error: {e_send}"},
                        }
                        if client:
                            client.sendall(json.dumps(fallback_err).encode("utf-8") + b"\n")
                    except Exception:
                        pass
```

**After**:
```python
        try:
            while not self.command_queue.empty():
                try:
                    cmd, client = self.command_queue.get_nowait()
                except queue.Empty:
                    break
                except Exception as e_queue:
                    logger.error(f"Error retrieving command from queue: {e_queue}")
                    break

                # 1. Handle EOF sentinel (deferred socket cleanup after queue drain)
                if isinstance(cmd, dict) and cmd.get("_is_eof"):
                    with self._clients_lock:
                        self._clients.discard(client)
                    if client is not None:
                        try:
                            client.close()
                        except Exception:
                            pass
                    continue

                # 2. Handle preformatted raw responses (parse error FIFO preservation)
                if isinstance(cmd, dict) and (cmd.get("_is_preformatted_response") or "_raw_response" in cmd or cmd.get("_is_raw_error")):
                    if "_raw_response" in cmd:
                        resp_dict = cmd["_raw_response"]
                    elif cmd.get("_is_raw_error"):
                        resp_dict = cmd.get("payload", {})
                    else:
                        resp_dict = dict(cmd)
                        resp_dict.pop("_is_preformatted_response", None)
                    try:
                        if client is not None:
                            resp_bytes = json.dumps(resp_dict, default=str).encode("utf-8") + b"\n"
                            client.sendall(resp_bytes)
                    except OSError as e_os:
                        logger.debug(f"Client disconnected during preformatted response write: {e_os}")
                    except Exception as e_send:
                        logger.error(f"Failed to send preformatted response to client: {e_send}")
                    continue

                # 3. Handle non-dict invalid request primitives (e.g. 42, "string", [1,2,3])
                if not isinstance(cmd, dict):
                    err_resp = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "status": "error",
                        "error": {"code": -32600, "message": "Invalid Request: Expected JSON object dict"},
                    }
                    try:
                        if client is not None:
                            client.sendall(json.dumps(err_resp).encode("utf-8") + b"\n")
                    except OSError as e_os:
                        logger.debug(f"Client disconnected during invalid request write: {e_os}")
                    except Exception:
                        pass
                    continue

                # 4. Standard RPC dispatch
                req_id = cmd.get("id", "res-1")
                method = cmd.get("method") or cmd.get("type", "")
                params = cmd.get("params", {})
                if not isinstance(params, dict):
                    params = {}

                try:
                    result = self._dispatch(method, params)
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "status": "success",
                        "result": result,
                    }
                except Exception as e_dispatch:
                    logger.error(f"Error executing RPC method '{method}': {e_dispatch}", exc_info=True)
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "status": "error",
                        "error": {"code": -32000, "message": str(e_dispatch)},
                    }

                try:
                    resp_bytes = json.dumps(response, default=str).encode("utf-8") + b"\n"
                    if client is not None:
                        client.sendall(resp_bytes)
                except OSError as e_os:
                    logger.debug(f"Client disconnected during response write for req {req_id}: {e_os}")
                except Exception as e_send:
                    logger.error(f"Failed to send response to client for req {req_id}: {e_send}")
                    try:
                        fallback_err = {
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "status": "error",
                            "error": {"code": -32603, "message": f"Serialization error: {e_send}"},
                        }
                        if client is not None:
                            client.sendall(json.dumps(fallback_err).encode("utf-8") + b"\n")
                    except Exception:
                        pass
```

---

## 5. Verification Method

### 5.1 Test Execution Commands
The implementer can independently verify this remediation using the project virtual environment:

1. **Adversarial Socket Fuzzing Suite**:
   ```powershell
   .venv\Scripts\pytest tests/test_m1_adversarial_socket.py -v
   ```
   **Expected Result**: All 28 tests pass (100% pass rate in <6.0s), specifically:
   - `test_malformed_chaos_fuzzing_interleaving` PASSED (verifies 7/7 responses delivered in exact FIFO order).
   - `test_client_half_close_shutdown_wr` PASSED (verifies 1/1 response delivered under TCP `SHUT_WR`).
   - `test_rapid_client_churn_descriptor_leak_prevention` PASSED (verifies zero socket leaks after 50 rapid connections).
   - `test_immediate_client_disconnect_mid_packet` PASSED (verifies clean descriptor recovery).

2. **Adversarial Dispatch & Parity Suite**:
   ```powershell
   .venv\Scripts\pytest tests/test_adversarial_dispatch_m1_2.py -v
   ```
   **Expected Result**: All 24 tests pass (100% pass rate).

3. **Baseline Parity & Bridge Test Suites**:
   ```powershell
   .venv\Scripts\pytest tests/test_bridge_socket_parity.py tests/test_blender_bridge.py -v
   ```
   **Expected Result**: All 100 tests pass (100% pass rate).

4. **Consolidated M1 Regression Suite**:
   ```powershell
   .venv\Scripts\pytest tests/test_bridge_socket_parity.py tests/test_blender_bridge.py tests/test_m1_adversarial_socket.py tests/test_adversarial_dispatch_m1_2.py -q
   ```
   **Expected Result**: Exactly `152 passed` with exit code 0.

### 5.2 Invalidation Conditions
The remediation is invalidated if:
- Any frame in `test_malformed_chaos_fuzzing_interleaving` arrives out of order.
- `test_client_half_close_shutdown_wr` raises `[WinError 10038]` or times out with 0 responses.
- Any client socket remains in `server._clients` after client disconnection (`test_rapid_client_churn_descriptor_leak_prevention` fails).
- Any private attribute of `self.command_queue` is accessed without locking.
