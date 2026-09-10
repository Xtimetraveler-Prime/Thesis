from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "Neuromorphic Digital Twin"
JSON_PATH = PROJECT / "references" / "m13_2_feature_crosswalk.json"
DOC_PATH = PROJECT / "docs" / "M13_2_ARCHITECTURAL_CROSSWALK.md"
MILESTONES = ROOT / "MILESTONES.md"

# Keep derived summary counts authoritative and link prior direct comparison evidence.
data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
data["summary"]["row_count"] = len(data["rows"])
source_id = "project_m03_m08_brian_evidence"
data["source_registry"][source_id] = {
    "column": "brian2loihi_comparison_evidence",
    "evidence_type": "direct_observation",
    "repository": "Xtimetraveler-Prime/Thesis",
    "commit": "80a502ec6dfc4c8d61372089b08c9a584ad65f85",
    "path": "MILESTONES.md",
    "locator": "M03-M08 completion evidence, especially M05, M07, and M08.3",
    "role": "Project-owned direct observations against Brian2Loihi: M05 current-decay ordering probe; M07 12/12 directed current/voltage/spike conformance across 34 ticks; M08.3 15/15 encoded-weight conformance including direct w_act comparison."
}
rows = {row["id"]: row for row in data["rows"]}
for row_id in (
    "neuron-state-model",
    "current-voltage-decay",
    "tick-update-order",
    "threshold-reset",
    "refractory-semantics",
    "weight-encoding",
    "synaptic-accumulation",
):
    evidence = rows[row_id]["brian2loihi"]["evidence"]
    if source_id not in evidence:
        evidence.append(source_id)
JSON_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

sys.path.insert(0, str(PROJECT / "src"))
from neuromorphic_twin.m13_feature_crosswalk import load_feature_crosswalk, render_feature_crosswalk_markdown

validated = load_feature_crosswalk(JSON_PATH)
DOC_PATH.write_text(render_feature_crosswalk_markdown(validated), encoding="utf-8")

m = MILESTONES.read_text(encoding="utf-8")
old = "### M13.2 — Build a four-way architectural feature crosswalk\n\n**Status:** Planned\n"
new = "### M13.2 — Build a four-way architectural feature crosswalk\n\n**Status:** In progress\n**Started:** 2026-09-09\n**Repository evidence:** branch `agent/m13-2-four-way-crosswalk`\n"
if old in m:
    m = m.replace(old, new, 1)
elif new not in m:
    raise SystemExit("Could not locate expected M13.2 status block")
MILESTONES.write_text(m, encoding="utf-8")
