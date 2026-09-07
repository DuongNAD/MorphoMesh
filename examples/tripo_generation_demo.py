"""
Generation script for 'Dư Niệm An' via live Tripo3D API.
"""
import os
import shutil
import sys
import time

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from morphomesh.connectors.tripo_connector import (
    DEFAULT_TRIPO_API_KEY,
    TripoConnector,
    TripoConfig,
    TripoInput,
    parse_glb_metrics,
)

def main():
    api_key = os.environ.get("TRIPO_API_KEY") or DEFAULT_TRIPO_API_KEY
    out_dir = os.path.abspath("output/tripo")
    os.makedirs(out_dir, exist_ok=True)

    config = TripoConfig(
        api_key=api_key,
        mode="api",
        model_name="v3.1-20260211",
        timeout_seconds=360.0,
        polling_interval_seconds=3.0,
        texture=True,
        pbr=True,
        texture_quality="detailed",
        geometry_quality="standard",
    )

    connector = TripoConnector(config=config)
    health = connector.health_check()
    print(f"Health Check: status={health.status}, balance={health.details.get('balance')}")

    prompt = (
        "Yu Nian An (Dư Niệm An), ancient Chinese porcelain doll maiden, "
        "ornate embroidered crimson and gold hanfu dress, glowing butterflies, "
        "floating red marionette silk threads, exquisite porcelain features, "
        "intricate hair accessories, full body 3D model, masterpiece quality /boost"
    )

    inp = TripoInput(
        prompt=prompt,
        task_type="text_to_model",
        output_dir=out_dir,
        texture=True,
        pbr=True,
        texture_quality="detailed",
        geometry_quality="standard",
    )

    print("Submitting text_to_model task for Dư Niệm An...")
    t0 = time.time()
    result = connector.execute(inp)
    elapsed = time.time() - t0

    print("=" * 60)
    print("Generation complete!")
    print(f"Asset ID: {result.asset_id}")
    print(f"Task ID: {result.task_id}")
    print(f"GLB Path: {result.glb_path}")
    print(f"File size: {os.path.getsize(result.glb_path):,} bytes")
    print(f"Vertex Count: {result.vertex_count:,}")
    print(f"Face Count: {result.face_count:,}")
    print(f"Execution Mode: {result.execution_mode}")
    print(f"Duration: {elapsed:.1f}s")
    print(f"Rendered Preview: {result.rendered_image_path}")
    print(f"PBR Textures: {result.texture_paths}")

    # Also save a copy into output/yu_nian_an/Yu_Nian_An_tripo.glb
    yu_dir = os.path.abspath("output/yu_nian_an")
    os.makedirs(yu_dir, exist_ok=True)
    target_glb = os.path.join(yu_dir, "Yu_Nian_An_tripo.glb")
    shutil.copyfile(result.glb_path, target_glb)
    print(f"Saved copy to {target_glb}")

    if result.rendered_image_path and os.path.isfile(result.rendered_image_path):
        target_preview = os.path.join(yu_dir, "Yu_Nian_An_tripo_preview.jpg")
        shutil.copyfile(result.rendered_image_path, target_preview)
        print(f"Saved preview to {target_preview}")

    # Copy all extracted textures
    for map_name, map_path in result.texture_paths.items():
        if map_path and os.path.isfile(map_path):
            dst = os.path.join(yu_dir, f"Yu_Nian_An_tripo_{map_name}.png")
            shutil.copyfile(map_path, dst)
            print(f"Saved {map_name} texture to {dst}")

if __name__ == "__main__":
    main()
