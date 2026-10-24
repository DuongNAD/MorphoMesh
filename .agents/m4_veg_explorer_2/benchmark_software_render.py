import time
import math
import numpy as np
from PIL import Image, ImageDraw

def test_painters_rasterizer():
    # Create 10,000 synthetic triangles
    num_faces = 10000
    triangles_2d = np.random.uniform(50, 450, (num_faces, 3, 2))
    depths = np.random.uniform(1.0, 10.0, num_faces)
    colors = np.random.randint(40, 200, (num_faces, 3), dtype=np.uint8)

    # Sort back to front
    t0 = time.time()
    order = np.argsort(-depths)
    sorted_triangles = triangles_2d[order]
    sorted_colors = colors[order]

    canvas = Image.new("RGBA", (512, 512), (245, 247, 250, 255))
    draw = ImageDraw.Draw(canvas)

    for i in range(num_faces):
        pts = [
            (float(sorted_triangles[i, 0, 0]), float(sorted_triangles[i, 0, 1])),
            (float(sorted_triangles[i, 1, 0]), float(sorted_triangles[i, 1, 1])),
            (float(sorted_triangles[i, 2, 0]), float(sorted_triangles[i, 2, 1])),
        ]
        c = tuple(sorted_colors[i]) + (255,)
        draw.polygon(pts, fill=c)

    elapsed = time.time() - t0
    print(f"Painter's algorithm rendered {num_faces} triangles in {elapsed:.3f}s")
    return canvas

if __name__ == "__main__":
    test_painters_rasterizer()
