# M03 — Reproducible workloads, neural state/DDR traffic and quantitative measurement contract

**Status:** M03 ACTIVE / PC-only mathematical and traffic-model development. NOT user-accepted; no FPGA build, measured DDR operation, HLS implementation, real benchmark accuracy, power or energy. Based on the **user-accepted M01 provisional configurable state-block baseline** and **user-accepted M02 initial integer LIF reference revision 1**. No published accelerator's RTL/software has been copied.

## 1. What is fixed and what is varied

### Accepted correctness contract

- Preserve exact M02 per-tick **signed integer LIF** semantics: every neuron must behave as though updated every timestep, including negative currents, rounding toward zero, bias-only autonomous spikes, saturation, reset and positive synaptic delays.
- Independently check **three execution formulations** for every workload: (a) M02 dense scan of previous spikes/all edges, (b) M02 future-event delivery queue with all-neuron updates, and (c) M03 exact sparse zero-state optimization; compare every neuron's voltage and emitted spike every tick. Report **FAIL** rather than performance data on any mismatch.
- **Exact skip lemma for M02 revision 1:** if a neuron has **previous membrane = 0**, **bias = 0**, and **total arriving current = 0** on this tick, then integer decay is zero and threshold is positive; the neuron remains at zero and emits no spike. It can be omitted from evaluation *without changing this reference model*. To be conservative, the M03 evaluator still evaluates every neuron receiving **any** input delivery, even when currents cancel; it also updates every neuron with **prior voltage ≠ 0** or **bias ≠ 0**. This is not a general lazy-leak/fast-forward algorithm for arbitrary new neuron models.
- The M03 sparse evaluator builds a *software worklist* and copies full voltage rows solely for verification. Its work-count estimate does **not** include the real cost of discovering active states, walking a worklist, copying snapshots, or moving data through PL/DDR. M05 hardware must measure those costs before claiming speedup.

### Deterministic active-role workload

One *canonical* generated model has a fixed \`N\` neurons and an active subset of \`K\` **logical roles**. Random outgoing synapses are generated from role \`pre\` to role \`post\` with bounded fanout, signed weights and positive delays. External current pulses are generated **in role space** at the declared rate per tick. The remaining \`N-K\` neurons start at zero, have no bias, receive no edges and never fire, making their quietness independently verifiable.

Two copies of the very same network/stimulus are constructed:

| Locality | Role → physical/logical neuron ID (for 0≤r<K) |
| --- | --- |
| **Clustered** | \`id(r) = r\` |
| **Dispersed** | \`id(r) = floor(r*N/K)\` |

Weights, timestamps, edge direction, delays, signed pulses and per-role event multiplicities **DO NOT CHANGE**. Only the numeric neuron IDs—and therefore their grouping into state blocks—change. Every comparison verifies the canonical role-level workload SHA256 and the **entire role-normalized voltage/spike trace SHA256** match across the two permutations. Raw ID-ordered voltage rows are **not** required to match: that would be an invalid test for renamed networks.

**Independent knobs:** N (logical network size), K (active logical roles), per-active-role fanout (connectivity sparsity), external current pulses/tick (temporal stimulus rate), time horizon T, random seed, group size G, resident capacity C, and cache policy. A controlled locality pair holds N/K/fanout/rate/seed/T and all neural work fixed. Multiple seeds sample **synthetic PC workload variability**, not repeated physical boots or actual inference samples.

This generator provides small synthetic LIF stress tests, **not** an event-camera dataset, a trained classifier, an accuracy benchmark, a statistically representative workload distribution, or a proof that real network connectivity maps naturally into contiguous IDs. The actual trained/model workload, split, accuracy target and event encoding must be selected and documented later.

## 2. Four logical analytical controls — not four RTL builds

All four use *the same full M02 neural semantics, generated graph, weights, current pulses and seed*.

| Logical model | Source of neuron evaluation requests | Synaptic reads | DDR neuron-state data traffic |
| --- | --- | --- | --- |
| **timestep/onchip** | Every N neuron states every one of T ticks | Full adjacency scanned every tick, on-chip | Zero (full state assumed locally resident); **UNAVAILABLE** when N×S exceeds declared on-chip capacity |
| **event/onchip** | Exact M02 safe-skip worklist of previous-nonzero, bias, or event destinations | Outgoing fanout of spiking neurons only, on-chip | Zero; same on-chip capacity validity gate |
| **timestep/DDR** | Every N neuron state per tick | Full adjacency sequential read **each tick** in hypothetical DDR | M01 chosen finite state-cache model plus cold loads, dirty evictions and final flush |
| **event/DDR** | Safe-skip worklist | Sequential fanout list per emitting presynaptic neuron, hypothetical DDR | Same M01 cache size/policy but with sparse state-access trace |

**State accesses vs synapse accesses remain independently reported.** This M03 first-pass four-way control models *both* state and adjacency resident for on-chip controls and *both* accessible in DDR for external controls. It does **not** thereby force the future hardware to keep synapses and states together. M06/M07 will vary their placement separately. More importantly, these rows are separate **models**, not resource-, clock- or interface-matched FPGA binaries.

Default illustrative parameters: N=128, K=16, fanout=4 per active role, 6 direct current pulses/tick, T=16, seed 20261107; accepted M02 16-bit state numerics. **Assumed** state record S=16 bytes (not yet an actual M02-to-RTL packed layout), edge record 8 bytes (not an actual CSR binary format), on-chip full-state capacity 2048 bytes, DDR-state cache 512 bytes (4×128-byte groups), G=8, maximum ideal contiguous transfer 256 bytes.

For DDR neuron state, use **exactly the accepted M01** cache accounting: LRU, fixed grouped residency (or independent/hybrid control), startup state loads, dirty evictions and final flush. It reports state reads/writes, idealized transactions, cache hits/misses, working-set capacity and dirty writes. Other hardware memory cost (tag RAM, actual AXI bursts, controller control area) remains unmodeled.

For DDR synaptic adjacency, first-pass accounting assumes a precontiguous edge record array. Timestep mode scans E edges per tick, giving **T×E edge visits** and \`T * E * edge_bytes\` modeled synapse read bytes, split into transactions by a declared max transfer size. Event mode traverses the outgoing fanout of each *emitted spike*: sum outdegrees over spikes; for each firing presynaptic ID, its outgoing records are assumed sequential and may be split at max-transfer boundaries. **No CSR index/pointer lookup, byte alignment/banking, burst setup, memory collision, synaptic weights cache, or overlap is modeled.** Outgoing fanout is conservatively counted even when its time-delayed delivery would fall after the observation horizon.

**Conceptual pending event counts:** M03 logs input/synaptic deliveries per tick and the number pending for future ticks in a Python timestamp-bucket structure. All future external events are already in that software map at the beginning. This is **not** actual FIFO depth, physical queue SRAM requirements, scheduler backpressure, arbiter stalls, DMA descriptors or physical timestamp-buffer sizing.

### Practical capacity gate

The resident alternative only exists when \`N × assumed_state_bytes <= declared_onchip_state_capacity_bytes\`. Otherwise it is explicitly **UNAVAILABLE**, not given a fabricated performance figure. DDR alternatives can still be studied at larger N. DDR state cache capacity is intentionally **smaller** than the declared full-resident capacity to force virtualization; therefore **this PC model does not by itself normalize LUT/FF/BRAM/URAM/DSP area across the alternatives**. Matching physical resources and clocks is an M05–M08 hardware requirement.

## 3. What the initial no-board report demonstrates (source checks, NOT KV260)

At the default fixed synthetic model, all three independently structured references agree on every voltage/spike state, and the pairwise relocated workloads have the same canonical functional trace. Source-verified baseline example:

| Model / locality | Neuron updates | Edge visits | State read+write bytes | Synapse read bytes | Combined idealized transactions |
| --- | ---: | ---: | ---: | ---: | ---: |
| Timestep / onchip, either locality | 2048 | 1024 | 0 | 0 | 0 |
| Event / onchip, either locality | 213 | 260 | 0 | 0 | 0 |
| Timestep / DDR, clustered | 2048 | 1024 | 65536 | 8192 | 544 |
| Event / DDR, clustered | 213 | 260 | 512 | 2080 | 69 |
| Timestep / DDR, dispersed | 2048 | 1024 | 65536 | 8192 | 544 |
| Event / DDR, dispersed | 213 | 260 | 54528 | 2080 | 491 |

**Interpretation:** the **same neural computation** can demand very different idealized memory traffic under different neuron-ID layouts. Under the declared toy cache model, sparse event processing reduces modeled neuron evaluations by 1835 and edge traversals by 764; however, dispersed active groups almost erase its state-traffic advantage. This is **not a measured acceleration** and no real KV260 latency, throughput, DDR transfer count, CPU interaction, memory bandwidth or energy follows from these numbers.

In particular, avoid interpreting 69 vs 491 model transactions as a 7× FPGA speedup: actual burst lengths, bank conflicts, setup cycles, queue costs and code throughput are unmeasured.

## 4. M03 multi-seed sweep and archival

- \`scripts/m03_explore.py\`: single role-isomorphic cluster/dispersed pair, same graph and accepted LIF function, four analytical controls; exact input/canonical-trace SHA values and full per-tick traces. Exclusive-create JSON only.
- \`scripts/m03_sweep.py\`: default **3 N sizes (64,128,256) × 3 fanouts (0,2,4) × 2 event rates (0,3) × 2 independent PC seeds (17,23) = 36 canonical workloads, each with a clustered/dispersed pair** (72 analytical locality cases). Every pair checks the accepted M02 and M03 references. N256 exceeds default full-on-chip capacity, so resident controls are marked **UNAVAILABLE**. A 0-event/0-fanout case properly yields zero safe-sparse state update and zero event-DDR traffic under our zero-bias workload construction.
- Reports are **source- and trace-hash-carrying JSON**, created with exclusive-create \`x\` mode and never silently overwritten. GitHub CI artifacts are no-board synthetic outputs. User PC original evidence belongs in unique \`$HOME/Thesis_Evidence/\` folders. Neither the 36 seeded generated models nor 72 locality cases are physical measurement repetitions.

## 5. Physical KV260 measurement contract to decide BEFORE M08

These are **future requirements**, not a claim the counters or timer boundaries presently exist.

1. **Fair workloads:** hash exact neural network, weights, precision, event encoding, sample ID/order; require same input-output and full voltage/spike reference parity where feasible. Separate synthetic graph experiments from real trained benchmark accuracy.
2. **Matched controls:** where all four fit, control neuron count, synapse count, precision, trained weights, activity, hardware clock and timing boundaries. Report real LUT/FF/BRAM/URAM/DSP resources, including cache/tag/queue/DMA structures, even if the area is unequal. Above full-on-chip capacity, report DDR scaling separately and never invent an on-chip comparison.
3. **Clocks/timers:** preserve a clearly defined end-to-end service boundary (from A53 input submission until final result received), actual clock frequency and repeat measurement methodology; separately instrument PL processing, PS orchestration, DMA/DDR activity, queue backpressure and initialization/cold-versus-warm-cache policy. Calibrate clock-domain conversion rather than conflating A53 vs PL cycles.
4. **Actual memory counters:** where instrumentable, report physical bytes, bursts, transaction sizes, read/write stalls, cache misses/evictions, dirty writebacks, synapse-index lookups and external address region. Distinguish hardware-observed counters from PC-estimated traffic and selected event-work counts.
5. **Statistical unit:** independent samples produce within-run latency distribution (median/p95), while independent coldboots/reprogramming captures form a **different replication level**. Predefine source/ELF/bitstream SHA, warmup, controlled temperature/power supply if relevant, separate accepted physical sessions and raw artifacts. Reanalysis of the same capture is NOT a new session.
6. **Claims:** derive virtualization penalty \`T_DDR/T_onchip\`, event benefit \`T_timestep/T_event\` separately for each memory mode, locality penalty at *fixed actual neural work*, and interaction as controlled differences/ratios with variability. No automatic power/energy claim without a separately defined calibrated power sensor and system boundary; no comparison with YANA/other published hardware without model/network/precision/timer-boundary matching.
7. **Hardware safety:** no PS halt, Linux-owned DDR overwrite, PL/JTAG download or destructive action until separately authorized per KV260 session. Never reuse retired v3 JTAG scripts; power-cycle after **every JTAG attempt** with known board ownership.

**Experiment acceptance principle:** A negative virtualization/sparsity result is a meaningful research outcome if the workload and measurement contracts are explicit. Never tune a cache policy on evaluation traces without disclosing training/calibration; keep synthetic seed settings and application TEST split boundaries fixed before comparing configurations.

## 6. Open M03 gates (not accepted yet)

- [x] Deterministic N/fanout/stimulus/seed workloads with exact role-isomorphic neural SHA controls.
- [x] Independently accepted M02 dense + queued numerical parity vs M03 provably safe zero-state skip.
- [x] State and synapse bytes, transaction accounting, active-group counters and modeled pending-delivery work separated, with cold writes/dirty end flush.
- [x] Four analytical control definitions, capacity gating, source/trace provenance and 36-paired-case no-board sweep tools.
- [ ] Operator runs native PC M03 + M02/M01 regression tests and reproduces original no-overwrite JSON; report original SHA(s).
- [ ] User reviews the **four-way model scope**, synthetic workload limitations, capacity/memory-placement assumptions and *future* physical measurement contract.
- [ ] M03 acceptance/merge authorized; M04 hardware engine reuse assessment stays a separately scoped milestone.

Further implementation and original instructions: [M03 native verification runbook](M03_PC_ONLY_VERIFICATION.md) and [M03 test-by-test explanation](M03_TESTS_EXPLAINED.md). Historical reference: [M02 initial accepted contract](M02_PROVISIONAL_LIF_CONTRACT.md) and [root literature review](../../../LitReview.md).
