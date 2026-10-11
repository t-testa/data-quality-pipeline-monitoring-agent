import json
import urllib.error
import urllib.request
from pathlib import Path

token = next(
    line.split("=", 1)[1]
    for line in Path(".env").read_text().splitlines()
    if line.startswith("DQ_API_TOKEN=")
)
base = "http://127.0.0.1:8765"
try:
    urllib.request.urlopen(base + "/api/overview", timeout=5)
    raise AssertionError("Unauthenticated access succeeded")
except urllib.error.HTTPError as error:
    assert error.code == 401
request = urllib.request.Request(base + "/api/overview", headers={"Authorization": "Bearer " + token})
with urllib.request.urlopen(request, timeout=5) as response:
    overview = json.load(response)
assert overview["pipelines"] >= 8
assert overview["run_counts"]["failed"] >= 7
print("Container smoke passed: authenticated overview, eight demos, unauthenticated access denied")
