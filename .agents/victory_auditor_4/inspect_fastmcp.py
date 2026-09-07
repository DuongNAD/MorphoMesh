import inspect
import asyncio
from morphomesh import server
from morphomesh.server import mcp, HUMAN_TOOL_NAMES
from morphomesh.blender_bridge import BlenderBridge

print('=== FASTMCP TOOLS & BRIDGE INSPECTION ===')
print(f'FastMCP Server Name: {mcp.name}')

tools = asyncio.run(mcp.list_tools())
tool_names = [t.name for t in tools]
print(f'Total Registered Tools: {len(tool_names)}')
for name in sorted(tool_names):
    print(f'  - {name}')

print(f'\nRequired Human Pipeline Tools ({len(HUMAN_TOOL_NAMES)}):')
for req in sorted(HUMAN_TOOL_NAMES):
    found = req in tool_names
    status = 'PASS' if found else 'FAIL'
    print(f'  - {req:42s}: {status}')

bridge = BlenderBridge()
print(f'\nBlenderBridge Host: {bridge.host}')
print(f'BlenderBridge Port: {bridge.port}')
assert bridge.port == 9876, f'Expected port 9876, got {bridge.port}'
print('BlenderBridge Port 9876: PASS')