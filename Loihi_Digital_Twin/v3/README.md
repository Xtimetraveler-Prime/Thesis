# FPGA-v3 / Board-Local Loihi-1 Architectural Twin

This directory is the active FPGA-v3 development tree.

v3 was forked from the final accepted FPGA-v2 state at:

```text
a9329caa064fee3876d69fbbe6c626ac035e67b5
Close P08 and complete FPGA-v2 roadmap
```

The accepted v2 tree remains preserved under `../v2/`. v3 inherits the v2 implementation as its starting baseline so that development can focus on board-local execution, stronger physical testing, a better-specified published MNIST benchmark, and defensible latency/power/energy characterization.

Development authority is:

- `LOIHI_TWIN_ROADMAP.md` — v3 phases, deliverables, and acceptance tracker;
- `docs/LOIHI1_TARGET_SPEC.md` — inherited Loihi-1 architecture contract until P01 determines whether a v3 addendum is required.

## Current status

**P00 — Establish v3 baseline, directory, and roadmap: Complete.**

**P01 — Board-local architecture, ownership, and v3 contract: Complete.**

**Next phase: P02 — DDR-backed logical-core virtualization.**

The implementation code is intentionally copied from v2 before architectural changes begin. Therefore some inherited package names, scripts, comments, and documentation still contain `v2` identifiers. Those names are compatibility artifacts of the baseline copy and should only be renamed deliberately with regression coverage.

The v2 accepted architecture remains:

```text
5 logical cores
3 resident K26 context slots
1 physical HLS engine
host-owned cross-page routing/barrier
host/PC-RAM backing for non-resident contexts
```

The accepted P01 board-local partition is:

```text
logical cores backed by K26 DDR
PS/PL-owned runtime control
PC removed from the algorithmic timestep loop
full board-local inference where practical
substantially more physical regression/application testing
```

## Baseline software verification

From this directory, the inherited Python regression suite can be forced to use the v3 source tree without changing the existing v2 package name:

```bash
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
PYTHONPATH="$PWD/src" python -m pytest -q
```

P00 was independently verified and accepted on 2026-10-05. See `docs/P00_ACCEPTANCE.md`.
