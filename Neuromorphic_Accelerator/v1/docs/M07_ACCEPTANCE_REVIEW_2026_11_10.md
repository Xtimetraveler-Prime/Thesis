# M07 — policies and ablations — scope-bounded acceptance review (November 10, 2026)

**Disposition:** M07 source-only cache/scheduling-control research deliverables **COMPLETE within a PC/M06-software model scope**, subject to final exact-head CI and PR #82 merge checks. This is NOT a real accelerator throughput, energy, AXI-cycle, RTL integration, or physical-DDR acceptance. The owner explicitly asked on November 10 to complete the remaining M07 work and merge after checking requirements; the owner independently reported M07.1–M07.4 local regressions PASS. M07.5 was added in response, with dedicated CI and local owner reproduction commands. It did **not** require or receive new FPGA/JTAG authorization.

## Requirements-to-evidence disposition

| M07 roadmap requirement | Evidence and result | Scope boundary |
| --- | --- | --- |
| Direct/no-inter-evaluation reuse and simple LRU-class cache | M07.1 `m07_policy_baseline.py`, `DirectFetchCache` vs accepted M06 `BlockCache`; exact owner/version/fault/dirty flush protocol; M02/M03 references | Source-level synchronous modeled transfers, not PS DDR |
| Fair four-way controls | M07.2 M03 timestep/on-chip, event/on-chip, timestep/DDR-style and event/DDR-style × two policies with matched neural work, explicit unavailable over-capacity controls | Timestep/DDR is M02-oracle-guided state movement, **not separate dense RTL**; M03 synapses DDR analytical only |
| Capacity/block/locality with fixed neural work | M07.3 two synthetic seeds × three resident byte budgets × three block widths × two locality maps × two policies × four modes = 288 model rows; all canonical role-trace hashes and work matched | Data bytes fixed across block-width axis; unequal cache-tag/controller FPGA area not equated |
| At most one activity-aware alternative | M07.4 bounded causal completed-page-history eviction, depths 4/16/32, 48 same-work comparisons; independent source positives/negative counterexample | Decision: exploratory only, **do not promote to HLS/RTL** without full metadata/scan cost |
| Event batching / fanout representation | M07.5 independent queue ingress batch widths 1/4 and 4B/8B **hypothetical off-chip synapse record** size sensitivity with unchanged M06 event LIF and adjacency | No fabricated actual edge compression or RTL event batching; representation is analytical sensitivity |
| Page bytes, hits, misses, modeled bursts, B-before-AR and queue stalls | M07.1–M07.5 exact M06 hit/miss/read/write counters; M07.5 passive **successfully completed** block-service operation trace reconciles chunks/bytes and records software write-return-before-read count. Declared FIFO with bounded capacity and slower-consumer saturation test records **simulated** occupancy, dispatch, producer stalls and total serialized **assumed** cycle count | Actual AXI B/R/AR channel handshakes, outstanding requests, queue stalls, physical DDR bytes, clock, runtime, full-device resource/energy **NOT MEASURED**. Source order != live B-before-AR waveform. Original M06 XSim accepted separately |
| Neural safety and exact matching | Unmodified independent M02 dense/queued, M03 safe-sparse and M06 Python paged execution exact spike/voltage/tick watermark/eligibility checks, old M01–M06 CI and full repository discovery | All accepted HLS/Vivado work and M02/M05/M06 original owner evidence remain frozen |
| Reproducibility and attribution | Source SHA256s + distinct exclusive-create M07.1–M07.5 JSON, full Linux owner runbook, test ledger, prior-art comparison register with YANA/SENECA/HiAER and explicit non-equivalence | No trained SNN/SHD/MNIST/benchmark score, no YANA code copy or cross-accelerator speedup |

## Representative modeled outcomes (NOT speedup)

**M07.1:** direct emits a full block read and acknowledged whole-block write for *every evaluated neuron*; inherited LRU can reuse clustered pages but may lose its advantage on dispersed layouts.

**M07.2:** default N128/K16/T16, 8-neuron blocks and 512B modeled resident state: event/DDR-style LRU clustered 512 bytes vs direct 55,552 bytes; dispersed LRU and direct both 55,552 model state bytes. The separate 2,240B event synapse estimate was NOT issued by the M06 pager.

**M07.3:** default 18 case synthetic grid yields 288 logical comparisons. On seed 17, fixed 128B resident data budget, the **dispersed minus clustered LRU** event/DDRx model-byte difference is 1,280B (2 neurons/block), 5,248B (4), and 13,824B (8), which is a cache locality effect, not estimated clock latency. Separately N1024 matches only YANA's cited neuron capacity number, NOT hardware or neural equivalence.

**M07.4:** 48 paired synthetic history-vs-LRU model trials gave 8 lower, 40 equal, 0 higher byte totals; +2,048 modeled bytes saved in aggregate across nonindependent configurations. Independent NON-NEURAL directed hot-page and obsolete-hot-page controls demonstrate policy wins and losses; replacement complexity has extra uncharged history/scan metadata. Retain LRU as hardware baseline; do not call experimental history a proven speedup.

**M07.5:** 48 source-only matched serial-service scenarios vary event batch width and hypothetical adjacency bytes at fixed neural contract. Completed canonical read/write operations match accepted M06 byte/chunk counters. `ServiceAssumptions` are explicitly synthetic: FIFO 4 events; batch dispatch setup 2 model cycles; consumer interval 2; LIF service 3; read chunk 5; write chunk 7; write completion 2. The default may legitimately show **no batching-cycle improvement** because the consumer is rate-limiting; a deliberate saturation case verifies producer stalls with a slower consumer. **No ns, actual AXI throughput or placed/routed clock is inferred.** Different synapse record size changes only M03 analytical external-adjacency byte estimates, not M06 state service.

## Verification and failure history

- The user reported M07.1–M07.4 full local regressions PASS, most recently November 10, 2026. The owner-local M07.5 commands are in `docs/M07_PC_ONLY_VERIFICATION.md` and should be rerun on main after merge; no owner-archive replacement is requested.
- GitHub Actions host-only M07.4 workflow at code commit `c84ae3c9e152f5ef2d0d12f155adbdc9be558bdd` passed 880 full tests (13 skips). First failed M07.4 negative fixture classified a **valid one-slot cache** as invalid; corrected without changing M06 geometry.
- M07.5 source addition initially passed 886 full tests (13 optional skips), then added an independently tested slower-consumer FIFO path to exercise nonzero synthetic producer stalls. Exact final-source-head CI run and PR-check IDs must be checked on GitHub before merge, including inherited M06 actual Icarus tests.
- Original local M07.1 nested JSON assertion and initial owner-discovered M05/M06 `prepare_hls_config` shared-module import collision were fixed in test-only changes; both failed observations remain in CI/owner logs. Accepted M05 and M06 vendor/HLS config scripts were not altered.
- M07 source-test CI is **not** a new original vendor gate. Previous M06 original 2025.2 AMD SmartConnect and fault/recovery proof is separately accepted in `M06_ACCEPTANCE_REVIEW_2026_11_10.md`. Physical PS DDR remains untested.

## Decision and next milestone boundary

**M07 source-only policy ablations can close without claiming measured performance.** It has achieved reproducible policies, equivalent neural outputs, matched locality and sizing controls, per-policy state-memory bytes and chunk counts, explicit modeled event-batching and queue/backpressure assumptions, an exploratory scheduling/replacement candidate, and source-labeled timing accounting. The M07.5 timing model intentionally does not calibrate to real silicon and is not an equivalent four-way FPGA build. Do **not** reinterpret measured M08 target questions as already answered: real complete-run latency/throughput, actual DDR traffic, AXI outstanding/handshake timing, FIFO resource costs, FPGA area/clock, and power/energy are **M08**, requiring separate authorization.

**Merge gate:** latest M07 branch HEAD must show M01–M07 GitHub no-board workflows all successful on **the same commit**, draft PR #82 only merged upon owner instruction (given here), and `main` compared against branch with no unrelated merges or original toolchain code changes. No new original Vivado/Vitis/XSim, JTAG or physical DDR actions are authorized by accepting M07. If final CI does not pass, keep M07 open.

**Prior art:** `docs/M07_PRIOR_ART_CONFIGURATION_COMPARISON.md` records why the named YANA hot-neuron system and SENECA/HiAER memory hierarchies are **architectural analogies**, never numerical source-model-to-real-hardware performance benchmarks.
