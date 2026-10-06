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

**P02 — DDR-backed logical-core virtualization: Complete.**

**P03 — Autonomous PS-resident runtime: In progress.**

**P03.1 — Autonomous runtime contract: Complete.**

Current sub-milestone: **P03.2c — Physical Cortex-A53 MMIO smoke**.

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


## P02 accepted physical baseline

P02 closed on 2026-10-06 with:

```text
5 logical cores
3 resident K26 context slots
1 physical HLS engine
K26 DDR authoritative for non-resident logical contexts
35 physical dispatches
7 algorithmic barriers
30 routed packets
60 page-ins
60 mutable page-outs
57 evictions
all five final DDR records byte-exact to golden
```

Accepted P02 physical artifact identities:

```text
bitstream_sha256=0d96ae6af0cc313ccbd8f9c802aeb0c8c7946bfeabaca3152ef5c7b9d2b23f26
probes_sha256=f4a9cb8c0ba676b86de784444968ec928cc4fc2be979f006bc39380ab86a8dbe
```

The PC still owns scheduling, packet-routing bookkeeping, and global barriers in
this P02 baseline. P03 moves those responsibilities onto the Cortex-A53.


## P03 active direction

P03 moves the algorithmic control loop from the external host to the
Cortex-A53.

The first verification candidate freezes:

- exact runtime/barrier/error transitions;
- deterministic service and page-replacement policy;
- resident/non-resident packet-delivery behavior;
- cache ownership and the reserved 64 MiB DDR backing window;
- board-local timing/counter boundaries;
- sticky fail-closed recovery;
- the FPGA-v3 addendum to the inherited Loihi-1 target specification.

Primary record: `docs/P03_1_AUTONOMOUS_RUNTIME_CONTRACT.md`.


## P03.2 verification candidate

P03.2 now provides a 32-bit AXI4-Lite PS control endpoint at
`0xA4000000..0xA0000FFF` through `M_AXI_HPM0_FPD`.

It replaces VIO command ownership for:

- DDR page commands;
- HLS dispatch commands;
- low-rate resident-memory reads/writes.

The accepted P02 HP0 DDR page data path is retained. VIO remains only for
observation and pre-run reset during bring-up.

Primary record: `docs/P03_2_PS_MMIO_CONTROL.md`.


## P03.2b accepted routed shell

The PS-visible HPM0/MMIO shell is now routed and accepted:

```text
MMIO base/range: 0xA4000000 / 0x00001000
WNS:             +0.539 ns
WHS:             +0.010 ns
resident slots:  3
physical engines:1
URAM:            47
```

Accepted artifacts:

```text
bitstream_sha256=8b4d1d3996147e73bbe71ec2a5036f0a4d23efc5cc3fe3d25237f855acf72119
probes_sha256=a745b96c24f4e01480d1d89d706e90c52c822b4a7fda7ea43d2ad794a0b86def
xsa_sha256=703fa7a44abc56e88e67e1d09424ac59ea96e53aac1708c2c7e6028dcb616f40
```

P03.2c now verifies those registers physically from Cortex-A53 standalone
software. Primary record: `docs/P03_2C_PHYSICAL_MMIO_SMOKE.md`.
