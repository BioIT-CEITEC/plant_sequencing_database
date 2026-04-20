import os
import sys
import json
from pathlib import Path

# Ensure venv site-packages are on the path
VENV_SITE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "lib", "python3.12", "site-packages"
)
if VENV_SITE not in sys.path:
    sys.path.insert(0, VENV_SITE)

# Also adding for linux path
LINUX_VENV_SITE = "/mnt/f/Collab/plant_breeding/lib/python3.12/site-packages"
if LINUX_VENV_SITE not in sys.path:
    sys.path.insert(0, LINUX_VENV_SITE)

from graphify.build import build_from_json
from graphify.export import to_html
from graphify.cluster import cluster

out_dir = Path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "graphify-out"))
data = json.loads((out_dir / "graph.json").read_text())

G = build_from_json(data)
communities = cluster(G)
to_html(G, communities, str(out_dir / "graph.html"))
print("Generated graphify-out/graph.html successfully.")
