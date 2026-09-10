from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "Neuromorphic Digital Twin"
JSON_PATH = PROJECT / "references" / "m13_2_feature_crosswalk.json"
DOC_PATH = PROJECT / "docs" / "M13_2_ARCHITECTURAL_CROSSWALK.md"
MODULE_PATH = PROJECT / "src" / "neuromorphic_twin" / "m13_feature_crosswalk.py"
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

finding = (
    "The Michaelis/Brian2Loihi paper writes the discrete synaptic-current recurrence with the new spike term "
    "added after the decay of the previous current, while this project's M05 direct Brian2Loihi observation "
    "established its compared software boundary as same-tick input visible before stored-current decay. M13.3 "
    "must reconcile timestep indexing/scheduler semantics explicitly before M13.4 treats this textual difference "
    "as behavioral evidence."
)
if finding not in data["summary"]["major_crosswalk_findings"]:
    data["summary"]["major_crosswalk_findings"].append(finding)
rows["current-voltage-decay"]["m13_3_action"] = (
    "Freeze which Catalyst execution boundary represents CUBA comparison; reconcile the published "
    "I[t] recurrence with the M05 directly observed Brian2Loihi scheduling/index convention; then specify "
    "the one-tick/current-source mapping before probes."
)
JSON_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

# The renderer is itself durable source, so close its generated-document wording before rendering.
module = MODULE_PATH.read_text(encoding="utf-8")
module = module.replace(
    "**Status:** Complete crosswalk candidate; M13.2 only. No A–H discrepancy adjudication is performed here.",
    "**Status:** Complete — M13.2 pass boundary achieved on 2026-09-09. No A–H discrepancy adjudication is performed here."
)
module = module.replace(
    "M13.2 is ready to close when this generated document and its machine-readable source agree, all 15 milestone feature classes are present, every one of the four columns is source-backed in every row, and the full project regression suite remains green. No behavioral differential result is required by M13.2 itself.",
    "**Achieved.** The generated document and machine-readable source agree byte-for-byte under regeneration, all 15 milestone feature classes are covered by 19 rows, every one of the four columns is source-backed in every row, prior M03-M08 Brian2Loihi observations are linked where applicable, exact external source identities are verified, and the full project regression suite remains green. No behavioral differential result is required by M13.2 itself."
)
MODULE_PATH.write_text(module, encoding="utf-8")

sys.path.insert(0, str(PROJECT / "src"))
from neuromorphic_twin.m13_feature_crosswalk import load_feature_crosswalk, render_feature_crosswalk_markdown

validated = load_feature_crosswalk(JSON_PATH)
DOC_PATH.write_text(render_feature_crosswalk_markdown(validated), encoding="utf-8")

m = MILESTONES.read_text(encoding="utf-8")
m = m.replace(
    "**Repository evidence:** current work on branch `agent/m13-1-pin-catalyst-methodology`",
    "**Repository evidence:** M13.1 merged via PR #14; M13.2 on branch `agent/m13-2-four-way-crosswalk`",
    1,
)
m = m.replace(
    "- [ ] Produce a source-cited architectural crosswalk containing published Loihi, Brian2Loihi, this project, and Catalyst N1 for every feature relevant to the supported computational subset and important scope gaps.",
    "- [x] Produce a source-cited architectural crosswalk containing published Loihi, Brian2Loihi, this project, and Catalyst N1 for every feature relevant to the supported computational subset and important scope gaps.",
    1,
)
start = m.index("### M13.2 — Build a four-way architectural feature crosswalk")
end = m.index("### M13.3 —", start)
section = m[start:end]
section = section.replace(
    "**Status:** In progress\n**Started:** 2026-09-09\n**Repository evidence:** branch `agent/m13-2-four-way-crosswalk`",
    "**Status:** Complete\n**Started:** 2026-09-09\n**Completed:** 2026-09-09\n**Repository evidence:** branch `agent/m13-2-four-way-crosswalk`; validated before merge",
    1,
)
completion = """#### Completion evidence

**Achieved.** M13.2 freezes a reviewable four-way architectural crosswalk before normalization or differential probing. The machine-readable authority is `Neuromorphic Digital Twin/references/m13_2_feature_crosswalk.json`; `Neuromorphic Digital Twin/docs/M13_2_ARCHITECTURAL_CROSSWALK.md` is generated deterministically from that source.

The accepted matrix contains **19 rows covering all 15 milestone-required feature classes**. Every row keeps four independent columns—published Loihi, Brian2Loihi 0.5.2, the M12-validated project, and pinned Catalyst N1—and every cell cites one or more entries from the frozen source registry. The registry links the project's earlier direct Brian2Loihi evidence rather than re-deriving it informally: M05 current-update ordering, M07 **12/12** directed conformance over 34 ticks, and M08.3 **15/15** encoded-weight conformance with directly observed `w_act`.

The source-integrity preflight checks the pinned Catalyst and Brian2Loihi commits and verifies **seven exact external Git blob identities** used by the matrix. It also proves generated Markdown is byte-identical to a fresh render, runs the focused M13.2 source-contract tests, runs the complete historical thesis regression suite, and verifies the validation process leaves the repository clean.

The crosswalk deliberately does **not** assign A-H discrepancy classes. It records comparability relationships and hands unresolved questions forward. Major handoffs include Catalyst's distinct CPU/simple-LIF and RTL/CUBA boundaries, project/Brian strict `>` versus Catalyst `>=` threshold comparison, refractory register/countdown normalization, native weight-encoding transforms, observable event-order limits, and current-update/timestep-indexing questions that must be normalized before any output difference is interpreted as architectural evidence.

No project computational behavior, HLS, RTL, or M12 physical evidence changed in M13.2.

"""
if "#### Completion evidence" not in section:
    marker = "#### Pass boundary\n"
    if marker not in section:
        raise SystemExit("Could not locate M13.2 pass-boundary heading")
    section = section.replace(marker, completion + marker, 1)
section = section.replace(
    "#### Pass boundary\n\nThe repository contains a reviewable, source-cited matrix that makes the supported common subset and major architectural differences explicit before M13 differential probes are interpreted.",
    "#### Pass boundary\n\n**Achieved.** The repository contains a reviewable, source-cited matrix that makes the supported common subset and major architectural differences explicit before M13 differential probes are interpreted. M13.3 may now define the common behavioral subset and normalization rules from this frozen crosswalk.",
    1,
)
m = m[:start] + section + m[end:]
MILESTONES.write_text(m, encoding="utf-8")
