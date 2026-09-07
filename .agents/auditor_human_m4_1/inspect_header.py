with open(r" \output/yu_nian_an/Yu_Nian_An_Master.blend\\, \\rb\\) as f:
 h = f.read(12)
 print(\\RAW_HEADER:\\, h)
 print(\\MAGIC:\\, h[:7])
 print(\\VERSION:\\, h[9:12])