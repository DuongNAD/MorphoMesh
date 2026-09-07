import traceback
from morphomesh.blender_bridge import BlenderBridge

bridge = BlenderBridge()
print('Connected to socket?', bridge.is_interactive_connected())
print('Blender bin path:', bridge.blender_bin_path)

params = {'character_name': 'Yu_Nian_An', 'height': 1.65}
try:
    print('Trying execute directly...')
    res = bridge.execute('morphomesh.create_human_asset', params, timeout=30)
    print('Execute succeeded:', res.get('status'))
except Exception as e:
    print('Execute failed with:', e)
    traceback.print_exc()

print('Trying bridge.create_human_asset()...')
res2 = bridge.create_human_asset(character_name='Yu_Nian_An', height=1.65)
print('create_human_asset returned:', res2.get('status'), 'mesh_path:', res2.get('mesh_path'))
