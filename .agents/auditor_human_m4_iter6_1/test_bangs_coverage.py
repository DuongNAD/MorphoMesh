import bpy

bangs = bpy.data.objects.get('Hair_Hime_Bangs')
mesh = bangs.data

for test_z in [1.55, 1.57, 1.59, 1.61]:
    intervals = []
    for p in mesh.polygons:
        pts = [mesh.vertices[v].co for v in p.vertices]
        zs = [pt.z for pt in pts]
        if min(zs) <= test_z <= max(zs):
            xs = [pt.x for pt in pts]
            intervals.append((min(xs), max(xs)))
    
    intervals.sort()
    merged = []
    for iv in intervals:
        if not merged:
            merged.append(iv)
        else:
            prev_x0, prev_x1 = merged[-1]
            if iv[0] <= prev_x1 + 0.0005:  # within 0.5mm
                merged[-1] = (prev_x0, max(prev_x1, iv[1]))
            else:
                merged.append(iv)
    
    print(f'Z = {test_z:.2f}m: {len(intervals)} quads intersected. Merged segments: {len(merged)}')
    for idx, (x0, x1) in enumerate(merged):
        print(f'  Segment {idx}: [{x0*1000:.1f}mm, {x1*1000:.1f}mm], span = {(x1-x0)*1000:.1f}mm')
    if len(merged) > 1:
        gaps = [(merged[i][0] - merged[i-1][1])*1000 for i in range(1, len(merged))]
        print(f'  Gaps between segments: {gaps}')
    else:
        print('  CONTINUOUS COVERAGE: Zero gaps across entire span!')