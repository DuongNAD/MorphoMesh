import os

fbx_path = 'E:/tool/mcp/MorphoMesh/output/yu_nian_an/Yu_Nian_An.fbx'
assert os.path.exists(fbx_path), 'FBX file does not exist!'
size = os.path.getsize(fbx_path)

with open(fbx_path, 'rb') as f:
    header = f.read(23)
    # FBX binary header is 'Kaydara FBX Binary  \x00'
    assert header.startswith(b'Kaydara FBX Binary'), f'Invalid FBX header: {header}'
    f.seek(23)
    version = int.from_bytes(f.read(4), 'little')

print('=== FBX FORENSIC INSPECTION ===')
print(f'File: {fbx_path}')
print(f'Size: {size:,} bytes')
print(f'FBX Version: {version}')
print('Binary Header: Valid Kaydara FBX Binary')

# Count occurrences of DEF bone and Shape Key names in the binary FBX
with open(fbx_path, 'rb') as f:
    content = f.read()

def_count = content.count(b'DEF-')
jaw_open_count = content.count(b'jawOpen')
eye_blink_count = content.count(b'eyeBlinkLeft')
print(f'Occurrences of DEF- bones: {def_count}')
print(f'Occurrences of jawOpen shape key: {jaw_open_count}')
print(f'Occurrences of eyeBlinkLeft shape key: {eye_blink_count}')
