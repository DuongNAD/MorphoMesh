"""
Auditor M1_1: Adversarial Integrity Stress Tests
Validates:
1. Concurrency stress: 10 concurrent client threads x 10 requests = 100 requests.
2. Large payload handling: 200KB payload transmitted without framing corruption.
3. String literal newline handling (JSON escaped \\n vs newline delimiter \\n).
4. Timer immortality barrier under catastrophic client network failure.
5. Server stop clean deregistration.
"""

import importlib.util
import json
import socket
import sys
import threading
import time
from unittest.mock import MagicMock, patch

def run_adversarial_suite():
    # 1. Load MorphoMeshSocketServer
    spec = importlib.util.spec_from_file_location("morphomesh_listener_mod", "blender_addon/morphomesh/listener.py")
    mod = importlib.util.module_from_spec(spec)
    mock_bpy = MagicMock()
    mock_bpy.app.version = (4, 5, 0)
    mock_bpy.app.timers.is_registered.return_value = False
    mock_bpy.app.background = False
    mock_mathutils = MagicMock()

    with patch.dict("sys.modules", {"bpy": mock_bpy, "mathutils": mock_mathutils}):
        spec.loader.exec_module(mod)
        server = mod.MorphoMeshSocketServer(host="127.0.0.1", port=0)
        server.start()
        port = server.socket.getsockname()[1]

    print(f"Ephemeral server running on port: {port}")

    stop_drain = threading.Event()
    def drain_worker():
        while not stop_drain.is_set() and server.running:
            server._drain_queue()
            time.sleep(0.005)

    drain_thread = threading.Thread(target=drain_worker, daemon=True)
    drain_thread.start()

    try:
        # Test 1: Concurrency stress (10 threads x 10 requests = 100 requests)
        results = []
        def worker(worker_id):
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=5.0) as s:
                    for req_idx in range(10):
                        req = {
                            "jsonrpc": "2.0",
                            "id": f"w{worker_id}-r{req_idx}",
                            "method": "ping",
                            "params": {"t": time.time()}
                        }
                        s.sendall(json.dumps(req).encode("utf-8") + b"\n")
                        buf = b""
                        while b"\n" not in buf:
                            data = s.recv(4096)
                            if not data:
                                break
                            buf += data
                        line, _ = buf.split(b"\n", 1)
                        resp = json.loads(line.decode("utf-8"))
                        assert resp.get("id") == f"w{worker_id}-r{req_idx}"
                        assert resp.get("status") == "success"
                results.append(True)
            except Exception as e:
                results.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert len(results) == 10
        assert all(r is True for r in results), f"Concurrency errors: {[r for r in results if r is not True]}"
        print("ADVERSARIAL CHECK 1 (Concurrency 10 threads x 10 requests): PASS")

        # Test 2: Large Payload (200 KB comment payload in execute_custom_script)
        with socket.create_connection(("127.0.0.1", port), timeout=5.0) as s:
            large_comment = "# " + ("A" * 200000) + "\n"
            code = large_comment + "res = 999"
            req = {
                "jsonrpc": "2.0",
                "id": "large-req-1",
                "method": "morphomesh.execute_custom_script",
                "params": {"code": code, "return_variables": ["res"]}
            }
            s.sendall(json.dumps(req).encode("utf-8") + b"\n")
            buf = b""
            while b"\n" not in buf:
                chunk = s.recv(65536)
                if not chunk:
                    break
                buf += chunk
            line, _ = buf.split(b"\n", 1)
            resp = json.loads(line.decode("utf-8"))
            assert resp.get("id") == "large-req-1"
            assert resp["result"]["returned_data"]["res"] == 999
        print("ADVERSARIAL CHECK 2 (Large payload 200KB): PASS")

        # Test 3: Newlines inside strings vs NDJSON delimiter
        with socket.create_connection(("127.0.0.1", port), timeout=5.0) as s:
            code_multiline = 'msg = "hello\\nworld\\nwith\\nnewlines"\ncount = 4'
            req = {
                "jsonrpc": "2.0",
                "id": "esc-newline-1",
                "method": "morphomesh.execute_custom_script",
                "params": {"code": code_multiline, "return_variables": ["msg", "count"]}
            }
            s.sendall(json.dumps(req).encode("utf-8") + b"\n")
            buf = b""
            while b"\n" not in buf:
                chunk = s.recv(4096)
                if not chunk:
                    break
                buf += chunk
            line, _ = buf.split(b"\n", 1)
            resp = json.loads(line.decode("utf-8"))
            assert resp.get("id") == "esc-newline-1"
            assert resp["result"]["returned_data"]["msg"] == "hello\nworld\nwith\nnewlines"
            assert resp["result"]["returned_data"]["count"] == 4
        print("ADVERSARIAL CHECK 3 (Escaped newlines inside JSON values): PASS")

        # Test 4: Timer immortality under client network explosion
        stop_drain.set()
        drain_thread.join()

        exploding_client = MagicMock()
        exploding_client.sendall.side_effect = RuntimeError("Simulated network explosion")
        server.command_queue.put(({"jsonrpc": "2.0", "id": "x-1", "method": "ping", "params": {}}, exploding_client))

        ret = server._drain_queue()
        assert ret == 0.02, f"Timer dropped when client exploded! Returned: {ret}"
        print("ADVERSARIAL CHECK 4 (Timer immortality on network exception during drain): PASS")

    finally:
        server.stop()
        ret_stopped = server._drain_queue()
        assert ret_stopped is None, f"Expected None on stopped server, got {ret_stopped}"
        print("ADVERSARIAL CHECK 5 (Clean deregistration on server.stop()): PASS")

if __name__ == "__main__":
    run_adversarial_suite()
