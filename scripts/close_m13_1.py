from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

milestones = ROOT / "MILESTONES.md"
text = milestones.read_text(encoding="utf-8")
text = text.replace(
    "- [ ] Pin and archive the exact Catalyst N1 source/version, toolchain, documentation, and comparison assumptions used for M13.",
    "- [x] Pin and archive the exact Catalyst N1 source/version, toolchain, documentation, and comparison assumptions used for M13.",
    1,
)
old = """### M13.1 — Pin Catalyst N1 and freeze the comparison methodology

**Status:** In progress
**Started:** 2026-09-08
**Repository evidence:** branch `agent/m13-1-pin-catalyst-methodology`
"""
new = """### M13.1 — Pin Catalyst N1 and freeze the comparison methodology

**Status:** Complete
**Started:** 2026-09-08
**Completed:** 2026-09-08
**Repository evidence:** branch `agent/m13-1-pin-catalyst-methodology`; validated before merge
"""
if old not in text:
    raise SystemExit("M13.1 status anchor not found")
text = text.replace(old, new, 1)
pass_old = """#### Pass boundary

The exact source versions, evidence hierarchy, comparison terminology, and discrepancy-handling rules are recorded well enough that another researcher could reconstruct which implementations and documents were compared.
"""
pass_new = """#### Pass boundary

**Achieved.** The exact source versions, evidence hierarchy, comparison terminology, and discrepancy-handling rules are recorded well enough that another researcher can reconstruct which implementations and documents were compared.

Closure evidence on 2026-09-08 includes a clean Catalyst `v2.3-paper` / `n1-final` checkout at `1806bb4b4114d7671e5648fa75b7b83b3a8d5543`, exact key-source Git-blob verification, both lightweight tag-object checks, a passing complete thesis regression, **25/25** native Catalyst RTL regression testbenches under Icarus Verilog 12.0, and **56/56** pinned Catalyst CPU-simulator tests under Python 3.11.16. The exact validation environment and the distinction between source-declared minimums and closure-time versions are frozen in `Neuromorphic Digital Twin/references/m13_1_reference_manifest.json` and `Neuromorphic Digital Twin/docs/M13_1_REFERENCE_BASELINE.md`.

No project computational behavior, HLS, RTL, or M12 physical baseline was changed by M13.1. The only M12-era edit made while establishing this gate restored the already-intended documentation phrase required by its existing source-contract regression. K26 Catalyst reproduction remains deferred to M13.5.
"""
if pass_old not in text:
    raise SystemExit("M13.1 pass-boundary anchor not found")
text = text.replace(pass_old, pass_new, 1)
milestones.write_text(text, encoding="utf-8")

doc = ROOT / "Neuromorphic Digital Twin" / "docs" / "M13_1_REFERENCE_BASELINE.md"
doc_text = doc.read_text(encoding="utf-8")
doc_text = doc_text.replace(
    "In progress on branch `agent/m13-1-pin-catalyst-methodology`.",
    "**Complete — M13.1 pass boundary achieved on 2026-09-08.** Development and closure evidence are on branch `agent/m13-1-pin-catalyst-methodology` pending user validation/merge.",
    1,
)
needle = "## M13.1 pass boundary\n\nM13.1 can close when all of the following are true:\n"
replacement = "## M13.1 pass boundary\n\n**Achieved on 2026-09-08.** M13.1 closed only after the provenance-corrected final gate reproduced the clean external checkout and both independent Catalyst execution boundaries.\n\nThe closure criteria are:\n"
if needle not in doc_text:
    raise SystemExit("M13.1 document pass-boundary anchor not found")
doc_text = doc_text.replace(needle, replacement, 1)
doc.write_text(doc_text, encoding="utf-8")
