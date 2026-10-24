import os
import json
import urllib.request
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("MESHY_API_KEY")
url = "https://api.meshy.ai/openapi/v2/text-to-3d?pageNum=1&pageSize=100"
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read().decode("utf-8"))

latin_names = [
    "matteuccia", "agave", "aloe", "echinocactus", "echeveria",
    "hedera", "wisteria", "bougainvillea", "tillandsia", "epipremnum"
]

for latin in latin_names:
    matches = [t for t in res if latin in t.get("prompt", "").lower()]
    print(f"{latin}: {len(matches)} match(es)")
    for m in matches:
        print(f"   id={m.get('id')} mode={m.get('mode')} status={m.get('status')} progress={m.get('progress')}")
