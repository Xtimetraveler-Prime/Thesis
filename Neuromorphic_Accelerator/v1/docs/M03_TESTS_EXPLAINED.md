# M03 — Exact tests performed and what they establish

**Milestone:** **M03 COMPLETE / USER-ACCEPTED in its PC-only synthetic workload/traffic scope**. User-reported native PASS and HEAD source CI PASS; original user-local report SHA256s not provided. This is Python no-board science/traffic modeling, not synthesis, DDR timing, physical accelerator verification, classifier accuracy, or Loihi/YANA equivalence. Accepted M01 has 20 tests and M02 21 tests; this new M03 set adds **28 native test methods** across four source files (some methods contain many independent generated cases).

## 1. Workload and exact locality controls — six methods

Source: ../tests/test_m03_workloads.py.

| Test | How it works | What it proves in scope |
| --- | --- | --- |
| Role-isomorphic voltage/spike invariance | 4 fanouts × 3 event rates × 2 seeds = **24 paired clustered/dispersed networks**; compare role-space network digest, M02 dense/queued output, exact full canonical voltage/spike rows, input event multiplicities and synapse count | Moving only neuron IDs—not weights or spike timing—does not alter mathematical neural workload. |
| Deterministic seeded generator | Re-run identical seed, change seed, compare network+event SHA | Same seed produces same sources independent of global RNG; a changed seed normally creates different source content. |
| Cluster/dispersed ID formulas | K=8, N=128: role IDs 0..7 versus 0,16,..112 | Locality actually changes the memory grouping rather than just labeling two identical traces. |
| Full-activity edge case | K=N=16: clustered and dispersed roles become the same ID mapping | No spurious difference is manufactured when no relocation is possible. |
| Strict invalid-generator rejection | Empty/invalid N/K/T, bool-as-int, fanout too large, negative seed/rate, bad width/locality | Invalid workloads fail before experimental results are reported. |
| Quiet-cell corruption detector | Deliberately corrupt an inactive neuron voltage or truncate the trace | Canonical equality cannot hide an unexpected spike/state in unused neurons. |

## 2. Exact sparse-state eligibility — eight methods

Source: ../tests/test_m03_sparse_reference.py.

The permitted skip rule is not "no arriving spike means skip." It is more restrictive: if **previous voltage = 0**, **bias = 0**, and **arriving current = 0**, then under the M02 accepted rule with positive threshold the neuron cannot fire and remains zero. The event-driven worklist conservatively includes any neuron with a nonzero prior state, nonzero bias or any input delivery, even if signed deliveries cancel. The method returns the full voltage/spike rows only for checking; it does not measure the cost of those snapshots.

| Test | What it checks |
| --- | --- |
| Exact zero-state idle skip | After one subthreshold +4 input, neuron decays across ticks 4,2,1,0; remains in worklist until it reaches zero, then can be skipped. |
| Bias-driven autonomous spike | Zero-input neuron with bias +3, threshold 5 still updates and fires at ticks 1 and 3. |
| Negative bias and reset | Negative membrane, bias and delayed inhibitory synapse do not cause an illegal state skip. |
| Duplicate signed events/cancellation | All deliveries are conservatively tracked even when +10 and -10 sum to zero or current is explicitly zero. |
| Delayed recurrent feedback | Two-neuron delay-2/delay-1 chain produces the independent M02 expected (0,0),(2,1),(3,0) output. |
| No fanout/no input | Zero-state, zero-bias 8-neuron network legitimately performs zero state evaluations while dense reference performs every tick. |
| Synthetic event backlog | The timestamp-bucket Python model counts scheduled future external and synaptic deliveries, not a physical FIFO capacity or PL stall. |
| General randomized differential | **65 seeded arbitrary M02-compatible recurrent networks**: random signs, weights, biases, state initialization, reset values, delay and pulse streams; compare all voltage/spike rows against both independently accepted M02 implementations; assert worklist size ≤ N×T. |

This does **not** prove exact skipping remains correct if M02 semantics change to include hidden synaptic-current state, refractory timing, time-dependent bias, plasticity, zero-delay feedback, or other unmodeled dynamics. Such a change requires a new contract/validation.

## 3. Four-way model/traffic tests — eight methods

Source: ../tests/test_m03_traffic.py.

| Test | Method |
| --- | --- |
| Matched four controls | Run timestep/event × onchip/DDR with one network/source and both locality relabelings; assert neural equivalence, equal canonical hashes, state/synapse byte conservation and four named rows. |
| Locality changes traffic, not work | Cluster/dispersed case must preserve same role-spikes/fanout count but change modeled external-state transactions under the selected finite cache. |
| Zero-event network | No input, no bias, no fanout yields **zero legal sparse state work and no event-DDR state/synapse traffic**; dense timestep baseline still touches all N neurons. |
| On-chip capacity gate | Increase N beyond available on-chip state footprint; both on-chip alternatives are marked **UNAVAILABLE** rather than supplying fabricated estimates. |
| Keep M01 controls | Explicitly run the same source/network with group, neuron-granular and hybrid caching; verify the chosen policy is reflected in the DDR-state accounting. |
| Invalid group/metadata/budgets | Reject cache ≥ on-chip capacity, N indivisible by block size, invalid policy, impossible hybrid grouping and noninteger/zero state sizes. |
| Exclusive-create CLI | Run m03_explore.py twice against the same original path; second attempt must fail and original bytes remain unchanged. |
| Memory-policy invariance of neural truth | Changing cache policy changes modeled memory records but must leave original network and canonical neural trace hashes unchanged. |

**Important:** modeled DDR synaptic bytes are computed from assumed fixed-size contiguous adjacency records; M03 does not implement an AXI DMA or actual CSR lookup. The four configurations are **software analytical controls, not four executed FPGA implementations**, and available onchip control uses a larger state capacity than the intentionally constrained DDR cache.

## 4. Multi-axis synthetic sweep tests — six methods

Source: ../tests/test_m03_sweep.py.

- Reproduce a 16-paired-case small grid twice byte-for-byte; verify signed source hashes, N×T baseline, safe-sparse work upper bound, four rows and nonnegative transactions.
- N=256 vs default 2 KiB full-state capacity: explicitly mark on-chip alternatives unavailable while DDR models remain available.
- Zero-event/zero-fanout grid: no spiking, no sparse updates, no modeled event-DDR traffic.
- Reject empty, duplicate, negative and invalid grid inputs rather than silently skipping inconvenient cells.
- Reject malformed CSV grid axes, including duplicate, trailing comma and noninteger values.
- Run CLI with unique original path, verify first success and second overwrite refusal, preserve original report bytes.

**Default production sweep** in scripts/m03_sweep.py is **36 paired canonical synthetic networks** (72 clustered/dispersed locality scenarios): 3 network sizes × 3 fanouts × 2 input rates × 2 PC seeds. These are **NOT 36 independent board boots or application accuracy tests**.

## 5. GitHub Actions check and current limit

.github/workflows/neuromorphic_accelerator_m03_pc_only.yml: Python syntax checking; all **28 M03 methods**; preserved **21 M02 + 20 M01** regressions; produce a source- and canonical-trace-hashed clustered/dispersed original JSON with M02+M03 neural parity for each of four analytical controls; independently verify work/bytes/counters; produce the **36-pair sweep** and ensure capacity-gate reports; deliberately reject overwriting originals and an illegal block size; upload both original PC-only JSON artifacts.

**What test success means:** reproducible source, an exact functional M02 oracle match, reversible access and memory traffic accounting at declared capacities, no-overwrite report preservation, honest nonavailability at large N.

**What it cannot establish:** real KV260 latency/throughput, actual DDR DMA bursting, physical PS/PL behavior, event-FIFO backpressure, resource area/cost, reproducibility across actual hardware boots, trained-model inference accuracy, power/energy savings, or a speedup relative to YANA/HiAER/Loihi v3.

Reference docs: [M03 source/measurement contract](M03_WORKLOAD_AND_MEASUREMENT_CONTRACT.md), [native runbook](M03_PC_ONLY_VERIFICATION.md), [v1 roadmap](../roadmap.md).
