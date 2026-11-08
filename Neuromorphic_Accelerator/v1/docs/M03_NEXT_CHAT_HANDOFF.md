# ARCHIVED M03 RESEARCH HANDOFF — CURRENT: M04_NEXT_CHAT_HANDOFF_SEED_2026_11_07.md

**Superseded by [authoritative M04 seed](M04_NEXT_CHAT_HANDOFF_SEED_2026_11_07.md):** M03 was user-accepted after all native tests passed, and PR #77 is authorized for merge into main. This document preserves historical details from its active-development phase. **Original date:** 2026-11-07 local / Nov 8 UTC; **historical status at its creation:** M03 ACTIVE. Read this file, ../roadmap.md, M03_WORKLOAD_AND_MEASUREMENT_CONTRACT.md and M03_PC_ONLY_VERIFICATION.md first. Old Loihi v3 next-run JTAG handoffs are HISTORICAL, not instructions for accelerator v1.

## History, program, Git

Repository: Xtimetraveler-Prime/Thesis. First-generation program at Neuromorphic_Accelerator/v1/ (NOT Loihi_Digital_Twin/v4). Root README contains two central questions: what performance it costs to virtualize larger neural networks and how much sparse events recover, and how DDR virtualization interacts with event work, active-context locality, scalability and hardware efficiency. Historical Loihi v1/v2/v3 with all original accepted physical evidence remains immutable; v3 frozen; v3 independent six-session A/B study canceled after ONE new accepted A; P10 optional deferred; official MNIST TEST sealed.

- **M01 COMPLETE and merged PR #75**, main commit 196ccfdb8fc77b3eaf37f41f9a5f939f47a4e0b2. User-reported 20 native M01 tests PASS and accepted reversible configurable *block-based neuron-state cache baseline* with individual/hybrid controls and independent synaptic-memory placement. No physical data collected.
- **M02 COMPLETE and merged PR #76**, main commit 8818838199b30b3ce98683e47228f23ddcda51f0. User-reported 21 native M02 tests PASS and approved original v1 signed-integer LIF revision-1 reference for now; exact fixed-point leak/threshold/reset, positive-delay recurrent synapses. Not a Loihi numerical clone; no raw user-local report SHA supplied.
- **M03 ACTIVE source branch:** agent/neuromorphic-accelerator-v1-m03-workloads-traffic, branched from M02-accepted main. **Do not merge M03** without operator native PC verification and express user approval. No RTL/HLS/FPGA/DDR ownership/real hardware runs authorized.

## M03 code, docs, CI

- src/neuromorphic_accelerator_v1/m03_workloads.py: deterministic *role-space* graph/stimulus. Cluster/dispersed role→neuron ID mapping preserves synapses, signed currents, timestamps and canonical neural outputs exactly. Only state block locality changes. Quiet nonactive cells are zero-state, zero-bias, disconnected in these synthetic fixtures.
- src/neuromorphic_accelerator_v1/m03_sparse_reference.py: exact M02-revision-1 safe zero-state skip: when prior voltage=0, bias=0, no arriving current, threshold>0, update yields zero and no spike. Evaluate other neurons; verify full voltage/spike traces against M02 dense and M02 queued. Count per-tick neuron work, synapse fanout, delivery destinations, conceptual pending future events. This is CPU software evaluation, NOT YANA-style hardware scheduler, no PL.
- src/neuromorphic_accelerator_v1/m03_traffic.py: independent *4-way analytical* event/timestep × onchip/DDR; M01 state LRU bytes/read/write/transactions, separate idealized synaptic edge-array traffic, cache misses/hits and group touches. Disclose control physical-memory resource inequality and onchip unavailable when footprint > capacity. Every comparison fails on M02 vs M03 neural mismatch.
- scripts/m03_explore.py: exact two-locality neural+traffic JSON for N128, K16, fanout4, 6 direct currents/tick, T16, group8, state cache512 B, full onchip capacity2048 B, 16B assumed state, 8B assumed edge, seed20261107. Exclusive-create original file.
- scripts/m03_sweep.py: 36 canonical generated networks (N64/128/256 × fanout0/2/4 × event rate0/3 × seeds17/23), each under two locality mappings. N256 exceeds resident capacity and onchip controls are marked UNAVAILABLE. Seeded PC fixtures are NOT physical repeated boots or trained accuracy.
- tests/test_m03_workloads.py (6 methods), test_m03_sparse_reference.py (8), test_m03_traffic.py (8), test_m03_sweep.py (6): **28 native M03 tests**, with M02 21 and M01 20 unchanged. Workflow .github/workflows/neuromorphic_accelerator_m03_pc_only.yml runs no-board tests, two original reports, fail-closed original output and invalid grouping, artifacts.
- docs/M03_WORKLOAD_AND_MEASUREMENT_CONTRACT.md: full scientific contracts, assumptions, 4-way limitations, future KV260 service clocks, memory counters and physical evidence requirements.
- docs/M03_TESTS_EXPLAINED.md: actual test methods, positive and negative cases and limitations.
- docs/M03_PC_ONLY_VERIFICATION.md: exact PC native tests, new original JSON in $HOME/Thesis_Evidence/, SHA256, independent report checks.

## Source-backed default example — NOT HW

Default N128/K16/T16/F4, group8, 512 B state cache; 2048 B resident full-state capacity:
- Dense always evaluates **2048 neurons**, event exact-safe-skip **213**, dense scans **1024 edges**, sparse fanout **260**. Each resulting voltage/spike state and canonical role trace MATCH across M02 dense, queued, M03 sparse and both location relabelings.
- Timestep/DDR both localities: state read+write **65536 B**, synapse read **8192 B**, total **544 modeled transactions**.
- Event/DDR clustered: state read+write **512 B**, synapse read **2080 B**, **69 modeled transactions**.
- Event/DDR dispersed: state read+write **54528 B**, synapse read **2080 B**, **491 modeled transactions**.
- Onchip model reports zero DDR by definition; no actual resource-matched hardware builds. These values are CPU logical work and hypothetical memory traffic ONLY, never achieved KV260 latency, energy/power, real DDR bursts, bandwidth or throughput.

## Native PC source tests (NO BOARD)

~~~bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m03-workloads-traffic
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m03-workloads-traffic
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m03*.py' -v
python3 -m unittest discover -s tests -p 'test_m02*.py' -q
python3 -m unittest discover -s tests -p 'test_m01*.py' -q
~~~

Follow docs/M03_PC_ONLY_VERIFICATION.md for TWO unique original no-overwrite JSONs, verify neural role-source and trace SHAs, sweep 36 paired cases, record source HEAD and both original SHA256s. Never use old board captures as accelerator-v1 results.

## Pending gates and future M04

**M03 user gates SATISFIED:** User reports 28+21+20 native PASS and explicitly authorizes M03 closure/merge. Future physical measurement details still require fresh operator design and safety approval. Full-onchip capacity comparison exists only when N×S fits. State and synapse placement still independent future architecture axes. Default record bytes, AXI burst sizes, cache tag/control and computing costs hypothetical. No real-trained benchmark results, measured clock domains, physical DDR latency, resource area, energy or hardware FIFO stalls.

After user acceptance/merge, M04 can audit v3 self-authored HLS arithmetic vs old Loihi-style logical-core dispatch, specify a minimal streaming input/output LIF packet, and compare reuse/refactor/new designs with real resource/timing gates. Preserve M02 numerical trace compatibility. Cite YANA, SENECA, HiAER and prior time multiplex/hot-neuron work; do not copy source RTL/software without licensing/provenance review.

**Physical safety:** no KV260 JTAG, PL or PS firmware, DDR/AXI writes, Linux halt or old v3 runner scripts. Future real board work needs session-specific preflight, owner allocation, exact bitstream/ELF/build SHA and mandatory physical power-cycle after every JTAG attempt; MNIST TEST stays sealed.
