from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / "MILESTONES.md"
text = path.read_text(encoding="utf-8")

old = '''### M12.4 — Broad deterministic physical regression and boundary stress

**Status:** Planned

#### Core goal
'''
new = '''### M12.4 — Broad deterministic physical regression and boundary stress

**Status:** In progress
**Started:** 2026-09-07
**Repository evidence:** branch `agent/m12-4-broad-physical-regression`

#### Current implementation boundary

M12.4 retains the already-closed M12.2 and M12.3 directed physical suites as architectural anchor evidence rather than duplicating all 26 earlier directed cases inside the new broad-regression bitstream. The new physical corpus adds 22 deterministic cases totaling 166 committed ticks: 16 seeded generated networks plus 6 selected finite-capacity stress workloads. Together with the retained directed evidence, this broadens coverage without weakening or replacing the earlier physical gates.

Every new case has a stable case ID, generator version, 64-bit seed, SHA-256 hash of the FPGA-visible configuration/load image, host-side Python golden artifact, physical trace path, exact differential report, and a one-command targeted board rerun by case ID. FPGA-visible generated source contains only static load images and per-tick external-event schedules; expected outputs and recurrent-event schedules remain host-side.

To keep the synthesized validation image practical, variable-length per-case data is stored in packed generated arrays with explicit offsets rather than rectangular maximum-stride padding. All 22 cases are separately gated against the frozen M11.5 physical capacity profile; M12.4 does not change computational-core capacities or semantics.

#### Core goal
'''
if old not in text:
    raise SystemExit("M12.4 planned status anchor not found")
text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
