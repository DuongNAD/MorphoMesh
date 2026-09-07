import importlib.util
import json
import socket
import threading
import time
from unittest.mock import MagicMock, patch

listener_path = 'blender_addon/morphomesh/listener.py'
spec = importlib.util.spec_from_file_location('listener_mod', listener_path)
mod = importlib.util.module_from_spec(spec)

mock_bpy = MagicMock()
mock_scene = MagicMock()
mock_scene.name = 'EmpiricalTestScene'
mock_scene.objects = []
mock_bpy.context.scene = mock_scene
mock_bpy.data.objects = {}

with patch.dict('sys.modules', {'bpy': mock_bpy, 'mathutils': MagicMock()}):
    spec.loader.exec_module(mod)
    server = mod.MorphoMeshSocketServer(host='127.0.0.1', port=0)
    server.start()
    port = server.socket.getsockname()[1]
    
    stop_drain = threading.Event()
    def drain_worker():
        while not stop_drain.is_set() and server.running:
            server._drain_queue()
            time.sleep(0.005)
    t = threading.Thread(target=drain_worker, daemon=True)
    t.start()
    
    # TEST 1: Strict FIFO error queueing with mixed malformed and valid requests
    print('--- TEST 1: FIFO Error Queueing ---')
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('127.0.0.1', port))
    
    raw_payload = (
        b'{bad json\n'
        b'{"jsonrpc": "2.0", "id": "req-1", "method": "morphomesh.ping", "params": {}}\n'
        b'not a json either\n'
        b'{"jsonrpc": "2.0", "id": "req-2", "method": "morphomesh.get_scene_status", "params": {}}\n'
    )
    s.sendall(raw_payload)
    
    responses = []
    buf = b''
    for _ in range(4):
        while b'\n' not in buf:
            chunk = s.recv(4096)
            if not chunk:
                break
            buf += chunk
        line, buf = buf.split(b'\n', 1)
        responses.append(json.loads(line.decode('utf-8')))
    s.close()
    
    print(f'Received {len(responses)} responses:')
    for idx, r in enumerate(responses):
        print(f'  [{idx}] status={r.get("status")} error={r.get("error", {}).get("code")} id={r.get("id")}')
    
    assert responses[0]['status'] == 'error' and responses[0]['error']['code'] == -32700, 'Resp 0 must be parse error'
    assert responses[1]['status'] == 'success' and responses[1]['id'] == 'req-1', 'Resp 1 must be ping'
    assert responses[2]['status'] == 'error' and responses[2]['error']['code'] == -32700, 'Resp 2 must be parse error'
    assert responses[3]['status'] == 'success' and responses[3]['id'] == 'req-2', 'Resp 3 must be get_scene_status'
    print('TEST 1 PASSED: Strict FIFO response order preserved under interleaving parse errors!')
    
    # TEST 2: EOF Sentinel (shutdown SHUT_WR)
    print('--- TEST 2: EOF Sentinel Deferred Teardown ---')
    s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s2.connect(('127.0.0.1', port))
    reqs = (
        b'{"jsonrpc": "2.0", "id": "eof-1", "method": "ping", "params": {}}\n'
        b'{"jsonrpc": "2.0", "id": "eof-2", "method": "ping", "params": {}}\n'
    )
    s2.sendall(reqs)
    # Half-close write side
    s2.shutdown(socket.SHUT_WR)
    
    buf2 = b''
    while True:
        chunk = s2.recv(4096)
        if not chunk:
            break
        buf2 += chunk
    s2.close()
    
    lines = [json.loads(l.decode('utf-8')) for l in buf2.strip().split(b'\n') if l.strip()]
    print(f'Received {len(lines)} responses after half-close:')
    for idx, r in enumerate(lines):
        print(f'  [{idx}] status={r.get("status")} id={r.get("id")}')
    assert len(lines) == 2, f'Expected 2 responses before clean EOF, got {len(lines)}'
    assert lines[0]['id'] == 'eof-1' and lines[1]['id'] == 'eof-2'
    print('TEST 2 PASSED: Clean EOF sentinel processing verified without connection drop!')
    
    stop_drain.set()
    server.stop()
    print('ALL EMPIRICAL SOCKET TESTS COMPLETED SUCCESSFULLY')
