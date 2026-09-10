#!/usr/bin/env python3
"""Stage the documentation and closure record after independent M13.6 validation.

This helper is intentionally used only by the one-shot M13.6 completion workflow.
It preserves references/m13_6_findings.json byte-for-byte and creates a separate
closure record around the independently reproduced candidate.
"""

from __future__ import annotations

import json
from pathlib import Path

from neuromorphic_twin.m13_closure import build_m13_6_closure

HERE = Path(__file__).resolve()
NDT = HERE.parents[1]
REPO = HERE.parents[2]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one marker, found {count}")
    return text.replace(old, new, 1)


def write_closure() -> None:
    candidate_path = NDT / "references" / "m13_6_findings.json"
    candidate_bytes = candidate_path.read_bytes()
    closure = build_m13_6_closure(
        json.loads(candidate_bytes.decode("utf-8")),
        candidate_bytes,
        load_json(NDT / "references" / "m13_2_feature_crosswalk.json"),
        load_json(NDT / "references" / "m13_4_candidate_findings.json"),
        load_json(NDT / "references" / "m13_5_closure.json"),
    )
    (NDT / "references" / "m13_6_closure.json").write_text(
        json.dumps(closure, indent=2) + "\n", encoding="utf-8"
    )


def update_milestones() -> None:
    path = REPO / "MILESTONES.md"
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "| M13 | Cross-validate and audit against Catalyst N1 | In progress | 2026-09-08 | — |",
        "| M13 | Cross-validate and audit against Catalyst N1 | Complete | 2026-09-08 | 2026-09-10 |",
        "M13 summary row",
    )
    old = """### M13.6 — Adjudicate discrepancies and freeze M13 findings

**Status:** In progress
**Started:** 2026-09-10
**Repository evidence:** branch `agent/m13-6-adjudicate-freeze-findings`; candidate authority `Neuromorphic Digital Twin/references/m13_6_findings.json`

M13.6 is being executed in two ordered sub-boundaries:

- **M13.6.1 — Freeze evidence-driven A–H adjudication and change control.** Regenerate the final candidate findings from the tracked M13.2 crosswalk, M13.4 directed findings, and M13.5 hardware closure; fail closed on source-pin, classification, comparison-limit, or baseline drift.
- **M13.6.2 — Freeze thesis claim boundaries and experiment handoff.** Cross-reference the accepted differences into `EXPERIMENTS.md`, preserve the zero-A/B change-control decision, and complete independent local validation before M13.6/M13 closure.
"""
    new = """### M13.6 — Adjudicate discrepancies and freeze M13 findings

**Status:** Complete  
**Started:** 2026-09-10  
**Completed:** 2026-09-10  
**Repository evidence:** branch `agent/m13-6-adjudicate-freeze-findings`; candidate authority `Neuromorphic Digital Twin/references/m13_6_findings.json`; closure authority `Neuromorphic Digital Twin/references/m13_6_closure.json`

M13.6 was executed in two ordered sub-boundaries:

- **M13.6.1 — Freeze evidence-driven A–H adjudication and change control — Complete.** The final candidate findings regenerate deterministically from the tracked M13.2 crosswalk, M13.4 directed findings, and M13.5 hardware closure and fail closed on source-pin, classification, comparison-limit, or baseline drift.
- **M13.6.2 — Freeze thesis claim boundaries and experiment handoff — Complete.** The accepted differences are cross-referenced into `EXPERIMENTS.md`; the zero-A/B change-control decision is preserved; independent local validation reproduced the candidate byte-for-byte and passed the complete regression.
"""
    text = replace_once(text, old, new, "M13.6 status block")

    if "#### M13.6 completion evidence" not in text:
        text = text.rstrip() + """

#### M13.6 completion evidence

The candidate findings were frozen before independent validation and intentionally remain unchanged at `Neuromorphic Digital Twin/references/m13_6_findings.json`. The independent gate was then executed from branch head `dedd3adcffd4f6080bfbb17153110539d8d45061` in a local Linux VS Code terminal.

Reported independent result:

```text
candidate regeneration: PASS
crosswalk rows:          19
directed probes:         12
agreements:               6
adjudications:            6
Class A/B findings:       0
scope exclusions:         8
M12 revalidation:         false
candidate cmp:            byte-identical / no output
focused tests:            9 passed in 0.12 s
full regression:          367 passed in 5.63 s
```

The local working tree also contained two untracked paths (`Neuromorphic` and `Neuromorphic Digital Twin/rtl/core_v1/xvlog.pb`). They were not part of the source-controlled branch diff and are explicitly excluded from M13 evidence.

The final closure record `Neuromorphic Digital Twin/references/m13_6_closure.json` binds the exact candidate bytes to that independently validated branch head and records the accepted change-control disposition. The accepted audit contains zero Class-A or Class-B findings, so the M10/M12 computational baseline remains frozen, no normative specification change is required, no HLS/RTL regeneration is required, no M12 evidence is superseded, and no M12 physical rerun is required.

#### Final M13 outcome

M13 is complete. The audit established a source-backed four-way architectural crosswalk, froze normalization before differential interpretation, executed twelve directed probes, resolved two audit-harness defects before accepting results, reproduced pinned Catalyst N1 through the strongest source-supported K26-class routed hardware boundary, and adjudicated every supported discrepancy under the A-H taxonomy.

Final accepted result:

```text
three-way/common-boundary agreements: 6
architectural/model differences:      3
partial-scope results:                 1
non-comparable results:                2
resolved Class-H harness defects:      2
Class-A/B findings:                    0
project baseline changed:              no
M12 revalidation required:             no
```

The audit therefore strengthens the thesis by separating **validated FPGA-v1 behavior**, **cross-implementation agreement**, **legitimate architectural/model differences**, and **unsupported or ambiguous claims** instead of treating any one external implementation as Loihi ground truth. `Neuromorphic Digital Twin/docs/M13_FINAL_AUDIT_SUMMARY.md` is the consolidated thesis-facing record of the process, findings, claim limits, and experiment handoff.
""" + "\n"
    path.write_text(text, encoding="utf-8")


def update_final_findings_doc() -> None:
    path = NDT / "docs" / "M13_6_FINAL_FINDINGS.md"
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "**Candidate findings frozen — pending independent local source-level validation before M13.6 and M13 are marked Complete.**",
        "**Complete — candidate findings independently reproduced and accepted on 2026-09-10; M13.6 and M13 are closed.**",
        "M13.6 findings status",
    )
    text = replace_once(
        text,
        "The candidate machine-readable authority is:",
        "The independently reproduced candidate authority is:",
        "candidate authority wording",
    )
    anchor = "The record is generated deterministically from the three tracked evidence authorities rather than transcribed by hand."
    replacement = anchor + """

The candidate remains intentionally unchanged after validation. Final acceptance is recorded separately in:

```text
references/m13_6_closure.json
schema = neuromorphic-twin-m13-closure-v1
status = validated_complete
```

This preserves the exact object that was independently regenerated while making the validation/closure event separately auditable.
"""
    text = replace_once(text, anchor, replacement, "closure authority insertion")
    text = text.replace("The candidate M13.6 decision is:", "The validated M13.6 decision is:", 1)

    heading = "## Reproduction and remaining gate"
    if heading not in text:
        raise SystemExit("M13.6 reproduction section marker not found")
    prefix = text.split(heading, 1)[0]
    completed_tail = """## Reproduction and completed independent gate

The exact pre-closure candidate is reproducible from `Neuromorphic Digital Twin/` with:

```bash
python3 examples/validate_m13_6_findings.py
rm -rf build/m13_6
python3 examples/generate_m13_6_findings.py
cmp references/m13_6_findings.json build/m13_6/m13_6_findings.json
python3 -m pytest --override-ini addopts='' -q tests/test_m13_6_findings.py
```

On 2026-09-10 the independent local run from branch head `dedd3adcffd4f6080bfbb17153110539d8d45061` reported:

```text
M13.6 findings candidate PASS:
  crosswalk=19
  directed=12
  agreements=6
  adjudications=6
  A/B=0
  scope=8
  m12_revalidation=False

cmp tracked candidate vs regenerated candidate: success, no output
focused M13.6 tests: 9 passed in 0.12 s
complete project regression: 367 passed in 5.63 s
```

The local `git status --short` contained two untracked paths, `Neuromorphic` and `Neuromorphic Digital Twin/rtl/core_v1/xvlog.pb`. Neither appeared in the tracked `origin/main...HEAD` branch diff and neither is accepted as thesis evidence.

The final closure record is generated and checked with:

```bash
python3 examples/generate_m13_6_closure.py
python3 examples/validate_m13_6_closure.py
```

The closure record hashes the exact candidate bytes and binds them to the independently tested branch head. It preserves the accepted result of six agreements, six adjudicated non-agreement/scope outcomes, zero Class-A/B findings, and no M12 revalidation requirement.

No new Vivado run, board programming, Catalyst runtime execution, or Brian2Loihi experiment is required for M13.6 closure because M13.6 adjudicates the evidence already frozen by M13.2, M13.4, and M13.5. The final M13 process and thesis claim boundary are consolidated in `docs/M13_FINAL_AUDIT_SUMMARY.md`.

## Pass boundary

**Achieved.** The exact candidate was independently regenerated byte-for-byte, the requested focused and full regressions passed, all findings have a final A-H/scope disposition, the experiment handoff is documented, the validated FPGA-v1 baseline remains unchanged, and `references/m13_6_closure.json` records M13.6 and M13 as complete.
"""
    path.write_text(prefix + completed_tail, encoding="utf-8")


def update_experiments() -> None:
    path = REPO / "EXPERIMENTS.md"
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "The candidate M13.6 adjudication preserves the validated FPGA-v1 baseline because the accepted M13 audit contains **zero Class-A/B findings**.",
        "The completed M13.6 adjudication preserves the validated FPGA-v1 baseline because the accepted M13 audit contains **zero Class-A/B findings**.",
        "EXPERIMENTS M13.6 status wording",
    )
    old = "No experiment status is promoted by M13.6 alone. The machine-readable handoff is part of `Neuromorphic Digital Twin/references/m13_6_findings.json`; experiments move to Designed/Ready only when their own hypotheses, variants, workloads, and validation gates are frozen."
    new = old + " M13.6/M13 closure is recorded in `Neuromorphic Digital Twin/references/m13_6_closure.json`; the completed audit changes experiment interpretation and guardrails, not the validated instrument baseline."
    text = replace_once(text, old, new, "EXPERIMENTS closure handoff")
    path.write_text(text, encoding="utf-8")


def main() -> int:
    write_closure()
    update_milestones()
    update_final_findings_doc()
    update_experiments()
    print("M13.6/M13 completion staging PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
