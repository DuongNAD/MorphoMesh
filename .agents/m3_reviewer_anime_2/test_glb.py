import struct, json
f = open('output/anime_animated.glb', 'rb')
f.seek(12)
chunk_len, chunk_type = struct.unpack('<II', f.read(8))
data = json.loads(f.read(chunk_len).decode('utf-8'))
print('Asset:', data.get('asset'))
print('Nodes:', len(data.get('nodes', [])))
print('Skins:', len(data.get('skins', [])))
anims = data.get('animations', [])
print('Animations count:', len(anims))
for i, a in enumerate(anims):
    print('  Anim', i, ':', a.get('name'), 'channels:', len(a.get('channels', [])))
