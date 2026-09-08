from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / "MILESTONES.md"
text = path.read_text(encoding="utf-8")

text = text.replace(
    "| M12 | Validate FPGA against Python golden model | In progress | 2026-08-27 | — |",
    "| M12 | Validate FPGA against Python golden model | In progress | 2026-08-27 | — |",
    1,
)
text = text.replace(
    "- [ ] A broader deterministic physical corpus completes with zero unexplained mismatches and reproducible failure artifacts.",
    "- [x] A broader deterministic physical corpus completes with zero unexplained mismatches and reproducible failure artifacts.",
    1,
)
old = '''### M12.4 — Broad deterministic physical regression and boundary stress

**Status:** In progress
**Started:** 2026-09-07
**Repository evidence:** branch `agent/m12-4-broad-physical-regression`

#### Current implementation boundary

M12.4 retains the already-closed M12.2 and M12.3 directed physical suites as architectural anchor evidence rather than duplicating all 26 earlier directed cases inside the new broad-regression bitstream. The new physical corpus adds 22 deterministic cases totaling 166 committed ticks: 16 seeded generated networks plus 6 selected finite-capacity stress workloads. Together with the retained directed evidence, this broadens coverage without weakening or replacing the earlier physical gates.

Every new case has a stable case ID, generator version, 64-bit seed, SHA-256 hash of the FPGA-visible configuration/load image, host-side Python golden artifact, physical trace path, exact differential report, and a one-command targeted board rerun by case ID. FPGA-visible generated source contains only static load images and per-tick external-event schedules; expected outputs and recurrent-event schedules remain host-side.

To keep the synthesized validation image practical, variable-length per-case data is stored in packed generated arrays with explicit offsets rather than rectangular maximum-stride padding. All 22 cases are separately gated against the frozen M11.5 physical capacity profile; M12.4 does not change computational-core capacities or semantics.

#### Core goal

Increase confidence beyond hand-authored demonstrations by running a reproducible deterministic corpus across a broad portion of the supported FPGA-v1 configuration and workload space.

#### Planned corpus strategy

Combine three layers rather than relying on undirected random testing alone:

1. **Directed architectural boundaries** retained from M12.2/M12.3.
2. **Seeded deterministic generated networks** varying neuron/axon/synapse/route counts, topology, weights, decays, thresholds, refractory settings, external events, recurrent multiplicity, and run length.
3. **Finite-capacity stress cases** approaching selected M11.5 physical limits where those cases are practical and informative on the board.

Every generated case should carry a stable case ID, generator version, seed, configuration hash, Python expectation artifact, FPGA trace artifact, and exact comparison report so any mismatch can be reproduced independently.

#### Failure policy

A corpus mismatch does not become an accepted exception merely because most other cases pass. Each mismatch must be classified as a golden-model problem, hardware implementation problem, capture/transport problem, unsupported configuration, or test-infrastructure defect. Valid implementation defects require a minimized directed regression before closure.

#### Pass boundary

The agreed deterministic physical corpus completes with zero unexplained mismatches, and the repository contains enough metadata to reproduce individual passing or failing cases without regenerating an opaque random workload.
'''
new = '''### M12.4 — Broad deterministic physical regression and boundary stress

**Status:** Complete  
**Started:** 2026-09-07  
**Completed:** 2026-09-07  
**Repository evidence:** branch `agent/m12-4-broad-physical-regression`; physical KV260 closure with 22 cases / 166 committed ticks / zero mismatches

#### Core goal

Increase confidence beyond hand-authored demonstrations by running a reproducible deterministic corpus across a broad portion of the supported FPGA-v1 configuration and workload space.

#### Delivered

- Retained the already-closed M12.2 and M12.3 physical directed suites as architectural anchor evidence rather than redundantly recompiling all 26 earlier directed cases into the broad-regression image.
- Added 22 new deterministic physical cases totaling 166 committed ticks: 16 seeded generated networks plus 6 selected finite-capacity / interaction stress workloads.
- Froze stable case IDs, generator version, 64-bit seed, SHA-256 of each FPGA-visible configuration/load image, Python-golden artifact names, physical trace names, exact differential reports, and one-command targeted reruns by case ID.
- Kept the FPGA evidence boundary independent: generated RTL contains only static load images and per-tick external-event schedules, with no Python-golden expected outputs and no injected recurrent-event schedule.
- Replaced rectangular maximum-stride corpus padding with packed variable-length generated arrays and explicit offsets so larger stress cases remain practical in the validation image.
- Added capacity gates proving all 22 cases stay within the frozen M11.5 physical profile without changing core capacities or semantics.
- Added exact host-side suite validation and a targeted `run_m12_4_case.sh <case-id>` path so any mismatch can be reproduced from the same compiled corpus using its stable seed and configuration hash.

#### Physical completion evidence

The complete M12.4 KV260 suite executed all 22 workloads and 166 committed algorithmic ticks. The host-side exact differential reported zero failed cases and zero mismatches:

```text
M12.4 physical broad deterministic suite capture completed successfully: cases=22 ticks=166
M12.4 exact broad physical differential passed: cases=22 ticks=166 mismatches=0
M12.4 physical broad deterministic regression completed successfully.
```

No M12.4 workload required an accepted exception or a change to the independent Python expectation.

#### Failure policy

A corpus mismatch does not become an accepted exception merely because most other cases pass. Each mismatch must be classified as a golden-model problem, hardware implementation problem, capture/transport problem, unsupported configuration, or test-infrastructure defect. Valid implementation defects require a minimized directed regression before closure. No unexplained mismatch remained in the accepted M12.4 physical run.

#### Pass boundary

**Achieved.** The agreed broad deterministic physical corpus completed with 22/22 cases, 166/166 committed ticks, and zero unexplained mismatches. Every case is tied to stable reproduction metadata and a targeted board-rerun command, so the result is reproducible rather than an opaque random sweep.

#### Detailed design record

See `Neuromorphic Digital Twin/docs/M12_4_PHYSICAL_REGRESSION.md` for the corpus design, independence boundary, deterministic reproduction metadata, physical trace fields, completion markers, scope, and M12.5 handoff.
'''
if old not in text:
    raise SystemExit("M12.4 active section anchor not found")
text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
