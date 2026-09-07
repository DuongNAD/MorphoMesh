import os
blend_path = "output/yu_nian_an/Yu_Nian_An_Master.blend"
with open(blend_path, "rb") as f:
    data = f.read(12)
    print("RAW:", data)
    print("MAGIC:", data[:7])
    print("VERSION:", data[9:12])
