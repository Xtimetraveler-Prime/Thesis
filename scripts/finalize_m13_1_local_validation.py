from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
doc_path = ROOT / "Neuromorphic Digital Twin" / "docs" / "M13_1_REFERENCE_BASELINE.md"
milestones_path = ROOT / "MILESTONES.md"

doc = doc_path.read_text(encoding="utf-8")
doc = doc.replace(
    "**Complete — M13.1 pass boundary achieved on 2026-09-08.** Development and closure evidence are on branch `agent/m13-1-pin-catalyst-methodology` pending user validation/merge.",
    "**Complete — M13.1 pass boundary achieved on 2026-09-08 and independently validated locally on 2026-09-09.** Development and closure evidence are on branch `agent/m13-1-pin-catalyst-methodology` pending merge."
)
anchor = "## M13.1 pass boundary\n"
block = '''## Independent local validation closure\n\nThe user independently reproduced the M13.1 external-reference boundary on the development branch on 2026-09-09. The pinned Catalyst CPU simulator suite completed **56/56** tests successfully, and the pinned Catalyst native RTL regression completed **25/25** testbenches successfully with exit code 0. No Catalyst source, RTL expectation, testbench list, compile flag, or project computational baseline was changed for this reproduction.\n\nTwo host-harness portability issues were exposed during local reproduction and were corrected as Class-H tooling issues before final acceptance:\n\n1. With `set -euo pipefail`, piping `iverilog -V` into `head -n 1` could cause some local Icarus builds to receive SIGPIPE and terminate the wrapper before emitting diagnostics. The runner now captures the full version output first and extracts the first line in Bash without a pipe.\n2. The original wrapper imposed a fixed 120-second `vvp` timeout. On the user's PC, `tb/tb_p13a.v` was still producing the expected cross-core spike sequence when GNU `timeout` terminated it with exit code 124. The wrapper now defaults to 300 seconds per native testbench and exposes `M13_1_TB_TIMEOUT_SECONDS` as an explicit host-performance override. The successful local acceptance used 600 seconds per testbench. A timeout is reported separately from a genuine simulator failure.\n\nThe longer local timeout does not weaken the behavioral gate: compile failures, nonzero simulator exits, explicit native failure markers, missing native result markers, changed testbench count, dirty/moved Catalyst source, and incorrect commit/tag/blob provenance remain fatal. The local 25/25 pass therefore confirms that the earlier 120-second stop was host-runtime variability rather than a Catalyst architectural discrepancy.\n\nThe independent local closure result is:\n\n```text\nCatalyst native RTL: 25/25 PASS\nCatalyst CPU tests:   56/56 PASS\nCatalyst source pin:  1806bb4b4114d7671e5648fa75b7b83b3a8d5543\nProject M12 baseline: unchanged\nDiscrepancy outcome:  no architectural discrepancy identified in M13.1\n```\n\n'''
if "## Independent local validation closure" not in doc:
    doc = doc.replace(anchor, block + anchor, 1)
doc_path.write_text(doc, encoding="utf-8")

m = milestones_path.read_text(encoding="utf-8")
needle = "M13.1 reference"
# Add closure evidence near the M13.1 section if not already present.
section_start = m.find("### M13.1")
if section_start == -1:
    section_start = m.find("#### M13.1")
if section_start == -1:
    raise SystemExit("Could not locate M13.1 section in MILESTONES.md")
next_section = m.find("### M13.2", section_start + 1)
if next_section == -1:
    next_section = m.find("#### M13.2", section_start + 1)
if next_section == -1:
    raise SystemExit("Could not locate M13.2 section in MILESTONES.md")
section = m[section_start:next_section]
local_block = '''\n##### Independent local closure evidence\n\nOn 2026-09-09 the pinned Catalyst reference was independently reproduced on the user's local PC. The CPU simulator suite passed **56/56** tests and the native RTL suite passed **25/25** testbenches. The local RTL run used `M13_1_TB_TIMEOUT_SECONDS=600` after a 120-second wrapper timeout terminated a still-progressing `tb_p13a.v`; the longer timeout was classified as a Class-H host-harness portability correction, not a behavioral change. The accepted runner keeps compile errors, native failure markers, nonzero simulator exits, source-pin changes, and provenance failures fatal.\n\nThis local reproduction closes the M13.1 validation boundary with no architectural discrepancy and no change to the M12-validated project baseline.\n\n'''
if "##### Independent local closure evidence" not in section:
    section += local_block
    m = m[:section_start] + section + m[next_section:]
milestones_path.write_text(m, encoding="utf-8")
