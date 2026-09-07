
import json

with open('E:/tool/mcp/MorphoMesh/.agents/victory_auditor_4/blend_inspection_report.json') as f:
    d = json.load(f)

sk = d['shape_keys']['keys']
print('--- 52 ARKit Shape Keys Delta Inspection ---')
for name, data in sorted(sk.items()):
    ds = data['delta_sum']
    md = data['max_delta']
    print(f'{name:25s}: delta_sum={ds:8.4f}, max_delta={md:8.4f}')

print('\n--- Materials Inspection ---')
mats = d.get('materials', {})
for mname, mdata in sorted(mats.items()):
    print(f'Material: {mname}')
    for node in mdata.get('nodes', []):
        if node['type'] in ('BSDF_PRINCIPLED', 'EMISSION'):
            ntype = node['type']
            nname = node['name']
            print(f'  - Node: {ntype} ({nname})')
            if 'subsurface_method' in node:
                print('    subsurface_method:', node.get('subsurface_method'))
                print('    subsurface_weight:', node.get('subsurface_weight'))
                print('    roughness:', node.get('roughness'))
                print('    ior:', node.get('ior'))
                print('    transmission:', node.get('transmission'))
            if 'strength' in node:
                print('    emission strength:', node.get('strength'))
