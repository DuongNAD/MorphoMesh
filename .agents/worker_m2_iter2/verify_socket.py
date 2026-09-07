import socket
import json

s = socket.socket()
s.connect(('127.0.0.1', 9876))

# 1. Ping
s.sendall(json.dumps({'jsonrpc': '2.0', 'id': 'p1', 'method': 'ping', 'params': {}}).encode('utf-8') + b'\n')
print('Ping:', s.recv(4096).decode('utf-8').strip())

# 2. Open master blend file
open_code = "import bpy\nbpy.ops.wm.open_mainfile(filepath='e:/tool/mcp/MorphoMesh/output/yu_nian_an/Yu_Nian_An_Master.blend')"
s.sendall(json.dumps({'jsonrpc': '2.0', 'id': 'p2', 'method': 'execute_code', 'params': {'code': open_code, 'return_variables': []}}).encode('utf-8') + b'\n')
print('Open blend:', s.recv(4096).decode('utf-8').strip())

# 3. setup_inspector_camera
s.sendall(json.dumps({'jsonrpc': '2.0', 'id': 'p3', 'method': 'morphomesh.setup_inspector_camera', 'params': {'viewpoint': 'three_quarter'}}).encode('utf-8') + b'\n')
print('Setup camera:', s.recv(4096).decode('utf-8').strip())

# 4. get_scene_status
s.sendall(json.dumps({'jsonrpc': '2.0', 'id': 'p4', 'method': 'morphomesh.get_scene_status', 'params': {}}).encode('utf-8') + b'\n')
status_raw = s.recv(65536).decode('utf-8').strip()
status_data = json.loads(status_raw)
print('Status objects count:', len(status_data['result']['objects']))
print('Scene name:', status_data['result']['scene_name'])

s.close()
