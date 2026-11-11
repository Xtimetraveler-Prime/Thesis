# M07 prior-art and configuration-comparability register

**Created:** November 10, 2026. **Status:** living research-attribution ledger; NOT an external hardware benchmark. Update this file for *each new M07/M08 experiment* whose architectural choices overlap or are compared to published accelerators. Link the exact local JSON's experiment ID, commit SHA, numeric geometry, neural/measurement contract and what can (or cannot) be compared. Never describe analogous functionality as identical implementations or imply a published source's code is copied.

## 1. Required comparison fields and gates

For every named prior-art link, record the following in the experiment entry: **(a)** paper/revision/section/URL, **(b)** which architectural concept genuinely overlaps, **(c)** exact local experiment ID, N/K/ticks/event counts, LIF/update precision, page size/budget/slots, state versus synapse placement, mapping and cold/warm policy, **(d)** which quantities differ or remain unknown, **(e)** source-derived versus FPGA RTL versus physical measurement levels, and **(f)** classification:
- **Architectural analogy:** shared idea or scheduling/memory pattern, but workload/model/storage/timing/area not matched. **No numerical performance comparison permitted.**
- **Partial configuration overlap:** a specified dimension, e.g. logical-neuron bound or hardware family, matches, but numerical reference/traffic/memory/resource assumptions do not. No head-to-head speedup or energy claim.
- **Matched computational experiment:** same neural contract, precision, inputs, connectivity, memory placement, resource/clock and timing boundaries established independently on both designs. Not achieved merely by using a similar group size.
- **Physical measured comparison:** additionally same hardware measurement boundary, recorded tool versions/source hashes and independent samples with uncertainty. Not yet achieved.

**Do not upgrade a classification implicitly.** Unknown published cache blocks, leak semantics or memory residency must be marked **NOT ESTABLISHED** rather than guessed. Per-case local JSONs contain source hashes; keep external paper version identifiers separately.

## 2. Verified prior-art architectural references (external research, not project measurements)

| Prior work and externally documented design | Genuine overlap with v1 | What is NOT equivalent |
| --- | --- | --- |
| **YANA, Pachideh et al., arXiv:2604.03432v1 (2026-04-03), §§2.1–2.3, 4;** https://arxiv.org/html/2604.03432 | Five-stage FPGA event pipeline; hot-neuron FIFO and preprocessing summed synaptic input; only event-responsive neurons updated, with last-update timestamps and LUT-based deferred membrane leak; demonstrates sparsity scaling. Core reported for KR260 with up to 2^10 neurons, 2^17 synapses, 740 LUTs, 918 registers, 7 BRAMs and 24 URAMs. Acknowledges on-chip near-memory time-sharing. | Our M02 exact integer dense-per-tick contract and M03 safe-zero skip **are not** YANA's forward-Euler/LUT deferred-leak arithmetic or hot-neuron-only eligibility rule. Our M07.3 state is a bounded **bytearray-backed virtualized cache**, not a demonstrated YANA-equivalent core, its one-event/cycle pipeline, its on-chip memory mapping or its physical KR260 measurements. We must not compare modeled traffic bytes to YANA latency/resource/energy or label our model a reimplementation. |
| **SENECA, Tang et al., Frontiers in Neuroscience 17:1187252 (2023), §§2.1–2.2, 3.6;** https://doi.org/10.3389/fnins.2023.1187252 | Explicit axon/neuron time multiplexing; every physical neuron may read/store logical state; flexible memory hierarchy and optional shared-memory prefetch via the SMPU. Useful precedent for residency/working-set and memory-movement tradeoffs. | SENECA's design, silicon technology, instruction/scheduling hierarchy and prefetch/hybrid memories differ from our source-model M06 page cache. No shared workload, area, clock or energy-measurement boundary. Conventional state-memory time-sharing is not a claimed novel mechanism. |
| **HiAER-Spike, Frank et al., npj Unconventional Computing 3:22 (2026), architectural Fig. 1;** https://doi.org/10.1038/s44335-026-00062-8 | Event-driven sparse processing, hierarchical event routing and a deliberate neuron-state vs synapse-storage placement split. | Its neuron membrane state is in **on-chip URAM** while synaptic lookups are in **off-chip HBM**, the **opposite** of M07.3's modeled off-chip-style *neural state* paging plus on-chip replay adjacency. Our separate M03 synapse DDR-style estimate is not integrated synapse HBM hardware. HiAER is not a cache-size, throughput or speedup baseline for M07.3. |

**Literature source/evidence distinction:** statements in this table about named external accelerators come from the cited publications, not measured by this project. Our source truth is `docs/M03_WORKLOAD_AND_MEASUREMENT_CONTRACT.md`, `src/neuromorphic_accelerator_v1/m06_block_residency.py`, `m07_policy_baseline.py`, `m07_matched_controls.py`, and `m07_ablation_sweep.py`. This comparison is original prose/research analysis; no YANA, SENECA or HiAER code, algorithms or weights were copied.

## 3. Current experiment ledger

### M07.1-BASE — initial direct-fetch vs LRU source model

- **Local configuration:** N32/K8, T12, 16-byte neuron rows, 4 neurons/block (64 B/page), two slots (128 B), clustered/dispersed role maps and M02 exact signed16 LIF. All event counts/weights identical within the pair. One-page read + full-page dirty commit per evaluated neuron for direct, LRU cold fills/dirty eviction/final flush for the inherited policy.
- **Closest prior-art idea:** YANA's sparse event-triggered updates and SENECA's amortized state movement; classification **architectural analogy only**, not equivalent scheduling or memory. YANA's hot-only neuron updates may omit states that M02's independent safe-sparse contract evaluates due to nonzero voltage/bias.
- **Measured here:** independent M02/M03/M06 source parity and model-only state bytes. **Not measured:** hardware pipeline cycles, physical DDR, synapse DDR, FPGA area/energy.

### M07.2-FOURWAY — four M03 logical models × direct/LRU

- **Local configuration:** default N128/K16, T16, 8 neurons/block, four 128-byte blocks (512 B cache), 2048 B full-onchip capacity, 16-byte rows. Clustered/dispersed ID mapping; event/DDR executes M06 Python neural replay, timestep/DDR replays M02 expected state through M06 Python cache, on-chip comparisons logical; M03 synapse DDR estimate is separate.
- **Closest prior-art idea:** YANA event-only sparsity and SENECA time-multiplexed state read/write. **Architectural analogy only.** Same logical neuron count below YANA's published 1024-neuron core maximum is not identical neuron numerics, chip resources or execution throughput.
- **Measured here:** software emulated page bytes/transactions and analytically estimated synapse records. This is not a KR260/KV260 cross-device comparison.

### M07.3-GRID-A — fixed-byte-budget locality and page-size ablations (current work)

- **Declared default plan** (see `scripts/m07_ablation.py`): N128, K16, T8, signed16 M02 LIF, 16-byte state record, fanout3 per active role, 4 external pulses/tick, 2 PC-only seeds (17,23); clustered vs dispersed M03 role relabeling. `resident_budgets_bytes ∈ {128,256,512}`, `block_neurons ∈ {2,4,8}`, with resident slots **derived** from `budget/(16×block)` rather than held constant. Cold cache and final dirty-state flush. Full on-chip comparator capacity 2048 B, max model transfer 256 B; each canonical full-block transfer is capped to page width. Exactly **18 parameter combinations, 2 locality mappings, 2 policies, 4 logical execution modes = 288 logical model rows** (not hardware runs).
- **Fixed per matched pair:** seed-specific canonical role network/edge weights/delays, input events and their timestamps, all emitted spikes and role-canonical state traces, total synaptic work, numerical precision, full comparator capacity and byte budget. Separate seeds are distinct **synthetic workloads**, not physical repetitions.
- **Changed between pairs:** role-to-neuron ID placement only. **Changed between geometry experiments:** declared byte budget or block width; changing block width also changes the number of resident slots while keeping total resident data bytes constant. Each result identifies the altered axis, page/block identities and M06 read/write method-level counters.
- **Closest prior-art ideas:** YANA hot-neuron event-driven locality and last-update timestamps, SENECA state working-set tradeoffs; **architectural analogy only**. This study DOES NOT instantiate YANA's on-chip hot-neuron FIFO, forward-Euler LUT leak, one-event/cycle RX, or published KR260 1024-neuron core. **HiAER-Spike memory placement differs** and is only context for future state/synapse placement studies.
- **Honest claims:** synthetic M02/M03 neural exact parity, method-level cache hits/misses, model page transfers and M03 separately modeled synapse bytes. **No matched physical DDR service time, LUT/FF/BRAM/URAM, energy or actual YANA benchmark claim.** A zero/negative LRU improvement is retained, not discarded. The official MNIST TEST remains sealed.
- **Future comparability promotion gate:** select a cited external configuration's exact SNN input/network/precision/leak/update rule; independently validate both neural oracles, memory and synapse placement, actual clock/throughput and end-to-end boundaries; then perform separately authorized, SHA-pinned FPGA benchmarking. Until then mark **NOT MATCHED**.

## 4. Data provenance and future entries

Source-level M07.3 JSON reports carry `schema=m07-residency-locality-ablation-v1`, source SHA256 ledger, full plan, per-seed neural/canonical hashes, 18 seed/budget/group configurations with 288 policy/locality/mode rows, exact counter units and physical/nonphysical flags. They must be written with exclusive-create mode into a **unique** `~/Thesis_Evidence/M07` receipt; a later report must not overwrite any prior failure or positive run.

For future M07.4 caching/scheduling concepts, add a **new ledger entry before any YANA comparison**, explicitly distinguishing YANA's activity-driven FIFO, weight accumulation, and deferred leak from our untouched M02 integer LIF correctness. Simply resembling a worklist, caching the active blocks or choosing a different group width does not make an implementation a YANA configuration.

**License caution:** the publications and hardware/software repositories have their own potentially different licenses; prior-art citation does not grant permission to copy RTL. If external implementation is later reused, audit the exact upstream commit and applicable files/licenses first.
