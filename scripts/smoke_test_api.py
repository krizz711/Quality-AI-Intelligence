import urllib.request
import json
from pathlib import Path



def load_api_key() -> str:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("API_AUTH_KEY="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("API_AUTH_KEY not found in .env")

url = "http://localhost:8000/studies/grr"
data = {
    "part_ids": ["P1", "P2", "P3", "P4", "P5"],
    "operator_ids": ["A", "B", "C"],
    "equipment_id": "CMM-001",
    "metadata": {"characteristic_name": "diameter"},
    "measurements": [
        {"part": "P1", "operator": "A", "value": 0.29},
        {"part": "P1", "operator": "A", "value": 0.41},
        {"part": "P2", "operator": "A", "value": -0.56},
        {"part": "P2", "operator": "A", "value": -0.68},
        {"part": "P3", "operator": "A", "value": 1.34},
        {"part": "P3", "operator": "A", "value": 1.17},
        {"part": "P1", "operator": "B", "value": 0.08},
        {"part": "P1", "operator": "B", "value": 0.25},
        {"part": "P2", "operator": "B", "value": -0.47},
        {"part": "P2", "operator": "B", "value": -1.22},
        {"part": "P3", "operator": "B", "value": 1.19},
        {"part": "P3", "operator": "B", "value": 0.94},
        {"part": "P1", "operator": "C", "value": 0.04},
        {"part": "P1", "operator": "C", "value": 0.34},
        {"part": "P2", "operator": "C", "value": -1.38},
        {"part": "P2", "operator": "C", "value": -1.13},
        {"part": "P3", "operator": "C", "value": 0.88},
        {"part": "P3", "operator": "C", "value": 1.09}
    ],
    "method": "xbar_r"
}

req = urllib.request.Request(
    url,
    json.dumps(data).encode('utf-8'),
    {
        'Content-Type': 'application/json',
        'X-API-Key': load_api_key(),
    },
)
try:
    with urllib.request.urlopen(req) as res:
        print("Status Code:", res.getcode())
        print("Response:", res.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code)
    print("Error Body:", e.read().decode('utf-8'))
