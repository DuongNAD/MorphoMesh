import struct, os

path = "output/yu_nian_an/Yu_Nian_An.fbx"
size = os.path.getsize(path)
print(f"Inspecting FBX: {path} ({size} bytes)")
with open(path, "rb") as f:
    header = f.read(27)
    magic = header[:21]
    version = struct.unpack("<I", header[23:27])[0]
    print(f"FBX Header: {magic}, Version: {version}")
    assert b"Kaydara FBX Binary" in magic, "Not a binary Kaydara FBX file"
    assert version >= 7400, f"FBX version {version} < 7400"
    print("FBX Binary Kaydara header verified!")