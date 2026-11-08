# ARCHIVED M01 handoff — consult M02_NEXT_CHAT_HANDOFF.md for current development

**Superseded after approved M01 merge:** M01 closed and merged into main as PR #75, commit 196ccfdb8fc77b3eaf37f41f9a5f939f47a4e0b2. New M02 PC-only neural reference is in branch agent/neuromorphic-accelerator-v1-m02-lif-reference. Consult [M02_NEXT_CHAT_HANDOFF.md](M02_NEXT_CHAT_HANDOFF.md) before any development. No FPGA activity authorized.

**Original historical M01 status:** 2026-11-07 local / November 8 UTC. **Current task:** M01 CLOSEOUT accepted, begin separate M02 reference milestone. **Authoritative live instructions for NEW accelerator project; old Loihi digital twin handoffs are historical and must not become active tasks.**

## Research direction and immutable history

Repo: Xtimetraveler-Prime/Thesis. Active new project: Neuromorphic_Accelerator/v1/ (NOT Loihi_Digital_Twin/v4). The old Loihi_Digital_Twin/v1, v2 and frozen v3 are intact, including genuine independently accepted TRAIN-derived KV260 neural/evidence runs; v3 original six-new-session study stopped after ONE accepted new A, five canceled; P10 optional v3 bounded optimization deferred. Official MNIST TEST remains sealed. Never re-label an old v3 physical capture as a new accelerator experiment. Repo root README.md has the two central thesis questions and proposed contributions; root LitReview.md has YANA, SENECA, HiAER-Spike, Ansari/Wielgosz, NIR and prior emulation/benchmark studies.

New research question 1: How much performance must we sacrifice to virtualize a larger network, and how much of that cost can sparsity-aware execution recover?

New research question 2: How do DDR-backed virtualization and event-driven sparsity interact to determine the performance, scalability, and hardware efficiency of FPGA-based spiking neural network accelerators?

Conceptual design: retain independently checked LIF semantics and configurable logical-to-physical state virtualization, but NOT Loihi-imposed logical core limits or fixed 27-core scheduling. Separate virtual state groups (memory/caching) from physical HLS/RTL compute pipelines; event-driven sparse scheduling comes only after M02 neural semantics are defined.

## Current Git and milestone status

- Explicit prior user request merged new workspace PR #73 and roadmap PR #74 to main, original integration main commit 8770000419600b377721130e29507b3c5816d3b3.
- **Active new development branch:** agent/neuromorphic-accelerator-v1-m01-trade-study, based directly on the above main. Develop/test in branch; **do NOT merge M01 without user verification and explicit approval**.
- **M01 status: COMPLETE / USER-ACCEPTED strictly PC-only.** User-reported native 20-test PASS and provisional B/group baseline approval; **user-local raw JSON hashes not furnished**. M02–M09 require separate acceptance; M02 is the next approved development scope. M01 options memo and safe experiment tool exist, but no chosen hardware interface or calibrated DDR/BRAM/URAM design; no actual physical acceleration.
- Milestone roadmap: ../roadmap.md. Architecture alternatives / modeled numbers: M01_ARCHITECTURE_OPTIONS.md. Exact PC commands and original-safe JSON output: M01_PC_ONLY_REPRODUCIBILITY_RUNBOOK.md. Earlier open design prompts: ARCHITECTURE_DESIGN_QUESTIONS.md.
- Native no-board GitHub Actions workflow: .github/workflows/neuromorphic_accelerator_m01_pc_only.yml; status historically 20 standard-library unit tests PASS on a successful development-branch workflow (latest workflow result should always be rechecked at branch HEAD before claiming it again).

## Actual new M01 file structure

- src/neuromorphic_accelerator_v1/m01_residency.py: stdlib StudyConfig, deterministic two-location state-request trace, generic LRU read/write/eviction accounting, idealized transfer splitting, optional *user-supplied hypothetical* serial memory time.
- src/neuromorphic_accelerator_v1/__init__.py: new package namespace (do not use old loihi_twin_v2 for v1).
- scripts/m01_explore.py: single matched neuron/block/hybrid state-access comparison for clustered and dispersed IDs; JSON output to stdout or exclusive-create evidence file.
- scripts/m01_sweep.py: 24-cell default 3-budget × 4-block-size × 2-locality no-board grid; deliberately no silent invalid-cell skip.
- tests/test_m01_residency.py, tests/test_m01_sweep.py: 20 standard-library regression/negative tests, capacity, pin prefetch, final dirty writeback, role-matched locality, reversible group size and no-overwrite checks.
- docs/M01_ARCHITECTURE_OPTIONS.md: architecture diagrams/equations, assumptions, comparative source-run modeled counts, prior-art attribution, provisional block baseline and remaining decisions.
- docs/M01_PC_ONLY_REPRODUCIBILITY_RUNBOOK.md: exact local native tests, user evidence capture, SHA256s and output validation.
- docs/M01_NEXT_CHAT_HANDOFF.md: THIS document.

**No v1 LIF simulation engine, synapse/weight data, event scheduling hardware, HLS reuse, RTL, Vivado project, physical DDR allocator, synthetic speed benchmark or real KV260 testing has been implemented.** PC-only accesses are modelled, not received SNN spikes.

## Model assumptions and source-run illustrative observations

Default parameter set: 4096 logical neuron IDs; provisional 16-byte state record; 2048-byte on-chip data budget, 16-neuron blocks; hybrid pins IDs 0..31, shared remaining LRU block budget; hypothetical 256-byte max contiguous transfer; synthetic 512 state-modifying accesses over 64 distinct neurons, seed1. Clustered IDs 0..63 vs dispersed IDs covering the logical range; same access multiplicities/order roles. All approaches share exact trace within each locality. Cold-start pinned prefetch and final writeback included, contiguous pin transfers coalesced. No real AXI/DDR burst overhead, cache tags, LIF numerical semantics, fanout, event routing or PS/PL time.

Previously CI source-run comparison: clustered individual 2048 total bytes/128 transfers; block 2048/8; hybrid 2048/8. Dispersed individual 2048/128; block 230912/902 (451 misses, 443 evictions); hybrid 233488/913 (455 misses, 449 evictions). **These are idealized model counts, NOT measured latency, energy, achieved DDR bandwidth, or fairness-equivalent trained SNN outputs.** Grouping appears locality-sensitive; pinning a fixed prefix is a controlled provisional option, NOT an optimized activity-aware policy. Models with different group size must remain comparable in state bytes/total on-chip capacity but controller/tag overhead is not yet budgeted.

## Exact Ubuntu PC verification — user must run independently

~~~bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m01-trade-study
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m01-trade-study
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m01*.py' -v
~~~

Then follow M01_PC_ONLY_REPRODUCIBILITY_RUNBOOK.md to generate TWO *new* original JSON reports in a unique exclusive-create directory outside Git under $HOME/Thesis_Evidence/ and print SHA256s; include final branch HEAD SHA. GitHub CI is not the user's PC, and standalone host CI can never authenticate unrelated board captures.

## Next explicit decision and upcoming development

**M01 RESOLVED:** The user approved adjustable **block/group-based residency as initial provisional baseline**, with individual-neuron and hybrid controls retained. Neuron state and synaptic connectivity stay **separate memory-placement variables**; their exact layouts and on-chip budgets are **not** decided. The detailed test-by-test acceptance explanation is [M01_TESTS_EXPLAINED.md](M01_TESTS_EXPLAINED.md).

**M02 unresolved neural reference:** Select exact v1 LIF arithmetic/precision, decay and idle/bias semantics, spike order/time bucket, delays, saturation/reset/refractory, recurrent scope and reference oracle test vectors. Reuse original v3 golden behavior as comparative fixtures where identical; build a small independent dense timestep v1 LIF oracle with a separate sparse-model checker; don't rely on HLS or YANA as sole source of neural truth.

**Attribution:** existing neuron time-multiplexing has SENECA and general prior art; YANA's hot-neuron FIFO/elapsed-leak event processing MUST be cited and its RTL/software licenses reviewed before any code reuse; HiAER-Spike already combines external sparse connectivity and on-chip neural state. State grouping, caches, LRU and hybrid residency are not new inventions. Document distinct new experiment design and measured results rather than claiming first-ever virtualization.

**Safety:** no JTAG, PL programming, ELF launches, A53 halt, DDR overwrites or Linux boot modifications authorized by M01; future physical work must be separately reviewed with exact original source/binary SHA/evidence ownership and mandatory power-cycle after every JTAG attempt. Do not blindly run historical v3 physical runner commands or infer XMPU protections.
