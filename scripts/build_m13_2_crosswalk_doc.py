from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "Neuromorphic Digital Twin"
JSON_PATH = PROJECT / "references" / "m13_2_feature_crosswalk.json"
DOC_PATH = PROJECT / "docs" / "M13_2_ARCHITECTURAL_CROSSWALK.md"
MILESTONES = ROOT / "MILESTONES.md"

# Repair derived summary count from the actual rows before validating/rendering.
data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
data["summary"]["row_count"] = len(data["rows"])
JSON_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

sys.path.insert(0, str(PROJECT / "src"))
from neuromorphic_twin.m13_feature_crosswalk import load_feature_crosswalk, render_feature_crosswalk_markdown

validated = load_feature_crosswalk(JSON_PATH)
DOC_PATH.write_text(render_feature_crosswalk_markdown(validated), encoding="utf-8")

m = MILESTONES.read_text(encoding="utf-8")n
old = "### M13.2 — Build a four-way architectural feature crosswalk\n\n**Status:** Planned\n"
new = "### M13.2 — Build a four-way architectural feature crosswalk\n\n**Status:** In progress\n**Started:** 2026-09-09\n**Repository evidence:** branch `agent/m13-2-four-way-crosswalk`\n"
if old in m:
    m = m.replace(old, new, 1)
elif new not in m:
    raise SystemExit("Could not locate expected M13.2 status block")
MILESTONES.write_text(m, encoding="utf-8")
