# M02 ACCEPTED HANDOFF — Continue active development in M03

**Updated:** 2026-11-07 local / 2026-11-08 UTC. **Active task:** M02 PC-only reference is **USER-ACCEPTED**, next milestone **M03** must start on a fresh branch after merging M02; this file is a preserved M02-to-M03 handoff. **First read this file plus ../roadmap.md and M02_PROVISIONAL_LIF_CONTRACT.md before making changes.**

## Thesis and integration history

Repo: Xtimetraveler-Prime/Thesis. New first-generation program: Neuromorphic_Accelerator/v1/ (NOT Loihi_Digital_Twin/v4). Research questions: (1) How much performance must we sacrifice to virtualize a larger network, and how much of that cost can sparsity-aware execution recover? (2) How do DDR-backed virtualization and event-driven sparsity interact to determine performance, scalability and hardware efficiency of FPGA-based SNN accelerators?

- The original Loihi-inspired Loihi_Digital_Twin/v1,v2,v3 trees stay intact; v3 frozen, original six-session A/B physical sequence canceled after **1 new accepted A**, old P10 optimization deferred. Original signatures/physical evidence immutable, never a new v1 hardware result. Official MNIST TEST sealed. Older v3 project handoff is historical, not active v1 instruction.
- User requested merging scaffold/roadmap PR #73/#74 and M01 PR #75; all merged to main. M01 merge commit 196ccfdb8fc77b3eaf37f41f9a5f939f47a4e0b2. M01 COMPLETE **PC-only** after user-reported native PASS and approval of configurable **block-based virtual neuron state residency**, retaining individual/hybrid controls and treating synaptic placement separately. Only analytical traffic counts, no actual DDR. Detailed 20-test explanation: M01_TESTS_EXPLAINED.md. M01 user-local original JSON SHA not provided; do not invent one.
- **Active M02 branch:** agent/neuromorphic-accelerator-v1-m02-lif-reference, based on merged M01 main. M02 native tests **user-reported PASS** and first LIF numeric contract **explicitly user-approved for the time being**; M02 may now be merged as requested. M03–M09 pending. User-local SHA receipts not supplied; do not invent them.

## What M02 newly implements (source, NOT hardware)

- src/neuromorphic_accelerator_v1/m02_types.py — immutable-ish dataclass names with strict validation for neuron params, synapses, external signed current events and ReferenceTrace. Contract itself is **still draft**.
- src/neuromorphic_accelerator_v1/m02_dense_reference.py — intentionally slow independent dense timestep oracle, rescans external events and all edges for each neuron/tick.
- src/neuromorphic_accelerator_v1/m02_event_reference.py — independent **scheduled synapse delivery** with outgoing adjacency and future-tick buckets. **All neurons still update every tick**, including silent bias-only neurons; not YANA hot-neuron-only pipeline or proof of idle skipping.
- scripts/m02_reference_check.py — no-overwrite original SHA256 report of 4 hand-curated cases and 50 seeded random cases (default). PC-only/provisional.
- tests/test_m02_reference.py (16 methods including 50 random graphs and one hardcoded absolute trace SHA), tests/test_m02_cli.py (5 methods) — **21 M02 tests**. M01's 20 regression tests run unchanged alongside.
- .github/workflows/neuromorphic_accelerator_m02_pc_only.yml — independent CI runs M02 21 methods, M01 20, 54-case CLI, invalid report overwrite and case-count rejection; archives original synthetic PC JSON.
- docs/M02_PROVISIONAL_LIF_CONTRACT.md — proposed numerical/time rule and unresolved decisions.
- docs/M02_TESTS_EXPLAINED.md — purpose of every group of tests and limits.
- docs/M02_PC_ONLY_VERIFICATION.md — exact Ubuntu PC commands to run and supply SHA-pinned report.
- roadmap.md — M01 COMPLETE, M02 ACTIVE, M03–M09 pending. New hardware engine HLS/RTL/Vivado not started.

**No v1 accelerator scheduler, HLS/RTL, bitstream, Vivado build, DDR-backed neural state, trained dataset evaluation or KV260 inference has been implemented in M02.** Queued synapse propagation is a software scheduling cross-check, not a physical accelerator.

## Candidate M02 numerical contract (requires user approval)

Each tick: start from previously stored integer signed W-bit voltage (default 16 bits). Decay using a global ratio decay_num/decay_den, truncate toward zero. Add per-neuron bias and sum of all signed external current pulses and presynaptic weights delivered on that tick. Saturate ONCE into signed W-bit range, compare against **inclusive threshold**; if reached, emit (tick,neuron) and store per-neuron reset voltage. All neurons evaluated every tick, even if there is no incoming event. Recurrent/self edges allowed only with positive delay >= 1. No refractory, separately decaying synaptic-current state, plasticity, subtractive reset, event-free fast forward or timing-accurate asynchronous hardware in this draft. External currents enter destination neurons directly rather than representing presynaptic input axon spikes.

**Caution:** These are deliberately new first-stage v1 neural semantics for reproducible accelerator comparison, **not** automatically Loihi v3 arithmetic nor YANA lazy-leak update. Hardware optimization or numerical changes require explicitly versioned contract and fixtures. No copied upstream code.

## Native PC commands — no board

~~~bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m02-lif-reference
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m02-lif-reference
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p "test_m02*.py" -v
python3 -m unittest discover -s tests -p "test_m01*.py" -q
~~~

Then follow docs/M02_PC_ONLY_VERIFICATION.md: unique original timestamped report under $HOME/Thesis_Evidence/, python3 scripts/m02_reference_check.py --seed 20261107 --random-cases 50 --out "$M02_REPORT", independently check 54 cases and print report SHA and source commit SHA. Never overwrite. CI cannot authenticate user-private local original bytes.

## Pending decisions / next milestone gate

- **M02 CLOSED:** user reports native PASS and accepts first precise LIF contract with disclosed exclusions. Treat it as revision 1 for comparisons, not a guarantee of Loihi equivalence. **NEXT M03:** derive oracle-backed signed work/event traces, reproducible sparse graph families, and independent virtual-state vs synaptic traffic modeled under matched comparator conditions.
- **M03:** freeze reproducible workloads, event/fanout trace contracts and PC-only traffic instrumentation after M02. HLS reuse and PL scheduling in M04/M05.
- **M01 memory direction remains reversible:** block-based residency initially, neuron-granular/hybrid control mandatory; new M02 reference does not implement caching, DDR, pages, physical scheduling or locality.
- **Prior art:** YANA hot-neuron scheduling/lazy update must be credited; SENECA time multiplex and HiAER hierarchy as well. No originality claim for LIF or cache rules.

## Git, evidence and physical safety

Branch from accepted main per milestone, native tests + no-board CI, user PC source regression and review, merge only after explicit authorization. Provide exact commands after each code change; preserve original source SHA, output SHA and fixture provenance. Later physical KV260 work requires actual Vivado/Vitis/XSA/ELF source hashes, DDR/Linux owner exclusion, separate operator JTAG risk approval and mandatory physical power-cycle after any JTAG attempt. **No M02 hardware deployment or board commands authorized.** Do not infer Loihi silicon exact neural fidelity, YANA performance, original MNIST TEST or energy from PC simulation.
