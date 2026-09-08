from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / "MILESTONES.md"
text = path.read_text(encoding="utf-8")
old = '''### M12.5 — Characterize the validated FPGA and assemble thesis-level evidence

**Status:** Planned

#### Core goal
'''
new = '''### M12.5 — Characterize the validated FPGA and assemble thesis-level evidence

**Status:** In progress
**Started:** 2026-09-07
**Repository evidence:** branch `agent/m12-5-fpga-characterization`

#### Current implementation boundary

M12.5 treats the already validated M10/M11.5 computational core as frozen. The characterization image reuses the exact M12.4 22-case / 166-tick corpus and adds only a passive 32-bit architectural tick-cycle counter exposed through one additional VIO input. The full physical trace is captured again and must reproduce the M12.4 22/22-case, 166/166-tick, zero-mismatch result before any performance measurement is accepted.

The characterization pipeline records routed K26 utilization and timing at the frozen 100 MHz target, per-tick PL cycle latency, ticks/s, neuron updates/s, input events/s, and actual CSR synapse visits/s. It also writes per-workload scaling summaries and a consolidated supported-feature/limitations record. Wall-clock JTAG time is excluded from architectural latency, maximum Fmax is not inferred from slack, and power/energy remains outside the validated claim set unless a trustworthy calibrated board-level measurement method is established.

#### Core goal
'''
if old not in text:
    raise SystemExit("M12.5 planned status anchor not found")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
