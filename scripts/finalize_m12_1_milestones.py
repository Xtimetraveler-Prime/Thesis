from pathlib import Path

path = Path("MILESTONES.md")
text = path.read_text(encoding="utf-8")

old = "- [ ] A stable machine-readable physical-FPGA trace path exists for the required M10/M11 architectural observables."
new = "- [x] A stable machine-readable physical-FPGA trace path exists for the required M10/M11 architectural observables."
if old not in text:
    raise SystemExit("missing M12 overall physical-trace completion criterion")
text = text.replace(old, new, 1)

old = """### M12.1 — Build the physical FPGA trace-capture boundary\n\n**Status:** In progress  \n**Started:** 2026-08-27  \n**Repository evidence:** PR #8 / merge `044093b825bd8bfbb9b3f7971157b0d22c365b7d` for M12.1.1–M12.1.3; branch `agent/m12-1-closure` for M12.1.4\n"""
new = """### M12.1 — Build the physical FPGA trace-capture boundary\n\n**Status:** Complete  \n**Started:** 2026-08-27  \n**Completed:** 2026-09-02  \n**Repository evidence:** PR #8 / merge `044093b825bd8bfbb9b3f7971157b0d22c365b7d` for M12.1.1–M12.1.3; branch `agent/m12-1-closure` for M12.1.4 and final closure\n"""
if old not in text:
    raise SystemExit("missing M12.1 in-progress header")
text = text.replace(old, new, 1)

old = """#### M12.1.4 — Prove repeated physical capture reproducibility and close M12.1\n\n**Status:** In progress  \n**Started:** 2026-09-02\n\nThe final M12.1 closure gate requires two independent executions of the accepted M12.1.3 program/reset/capture path for the same deterministic four-tick recurrent-chain workload. The repository now contains a repeated-capture board wrapper plus a comparator that requires:\n\n- both physical JSON files independently pass the frozen schema/parser validation;\n- complete typed physical artifacts are identical;\n- replayed backend-neutral `TickTrace` sequences are identical;\n- raw JSON files are byte-for-byte identical;\n- the stable artifact byte count and SHA-256 digest are reported;\n- both run logs and both physical trace artifacts are preserved under the M12.1.4 build directory.\n\nNo Python-golden output differential is performed in M12.1.4; that remains the explicit M12.2 boundary. The computational M11.5 core remains frozen throughout M12.1 closure.\n\n#### M12.1 pass boundary\n\nM12.1 closes when the repeated physical-board gate passes and demonstrates that the same deterministic workload can be independently programmed/reset/executed/captured twice with byte-stable machine-readable traces, while the parser/replay regressions and complete software suite remain passing.\n"""
new = """#### M12.1.4 — Prove repeated physical capture reproducibility and close M12.1\n\n**Status:** Complete  \n**Started:** 2026-09-02  \n**Completed:** 2026-09-02\n\nThe final closure gate executes the accepted M12.1.3 program/reset/capture path twice for the same deterministic four-tick recurrent-chain workload. `run_m12_1_4_reproducibility.sh` preserves both hardware logs and both physical JSON traces, validates each artifact independently, then compares the complete typed physical artifacts, reconstructed backend-neutral `TickTrace` sequences, and raw JSON bytes. The comparator also reports the stable artifact byte count and SHA-256 digest.\n\nThe independently run physical closure completed successfully on the KV260 on 2026-09-02. Both independent program/reset/execution/capture runs completed, and the final reproducibility gate reported:\n\n```text\nM12.1.4 physical trace reproducibility passed:\nM12.1.4 repeated physical capture closure completed successfully.\n```\n\nThe two captured artifacts were byte-for-byte identical and both replayed successfully through the frozen parser/trace model. This proves the M12 physical-observation path is deterministic and reproducible rather than a one-off manually inspected VIO session. No Python-golden output differential is performed here; that remains the explicit M12.2 boundary. The computational M11.5 core remained frozen throughout M12.1 closure.\n\n#### M12.1 pass boundary\n\n**Achieved.** A deterministic physical workload can now be independently programmed, reset, stepped, captured, serialized, parsed, replayed, and repeated with byte-stable machine-readable architectural traces and no manual transcription. M12.1 therefore hands M12.2 a trustworthy physical observation boundary for exact Python-versus-FPGA differential testing.\n"""
if old not in text:
    raise SystemExit("missing M12.1.4 in-progress block")
text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
