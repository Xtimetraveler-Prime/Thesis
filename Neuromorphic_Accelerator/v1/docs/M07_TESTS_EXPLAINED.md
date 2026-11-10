# M07 tests explained — source-only cache-policy work

**Status:** M07.1 initial implementation on a NEW development branch; **M07 NOT ACCEPTED**. This is a living test ledger. Last content update: 2026-11-10. Live CI results must be read from the exact branch HEAD, not inferred from checked-in files.

## 1. Scope, reference hierarchy and counters

- **M02** `evaluate_dense` and separately structured `evaluate_events` remain unchanged independent neural references.
- **M03** `build_workload`, `canonicalize_trace` and `evaluate_exact_sparse` supply fixed-seed role-isomorphic networks, independently computed eligible neurons and recurrent deliveries. Compare canonical role traces across relabelings, not raw physical IDs.
- **M06** `BlockCache`, `CanonicalImage` and `replay_with_paging` are unchanged. `BlockCache` is the preexisting exact dirty LRU. M07's `DirectFetchCache` subclasses it and supports a **strict paired read/write per logical neuron evaluation**. It uses the existing M06 version/lease/fault checks and full-block acknowledged writeback, then invalidates the just-written block. Zero reuse is permitted **between evaluations**, even on the same page; the read and write halves of ONE evaluation share the same fetched page. A second read without writing, a write to a different neuron and an incomplete flush are illegal and quarantine.
- **Block identity:** `neuron_id // neurons_per_block`; a page contains exactly `neurons_per_block * bytes_per_neuron` canonical bytes. `resident_budget_bytes` bounds resident block data, and `slots = floor(budget/page_bytes)`; metadata, queues and controller area are **not** costed.
- **Counter units:** M06 `accesses`, `hits`, `misses` refer to individual `read()` and `write()` method calls (exactly **2 per evaluated neuron**). Each M07 direct evaluation yields one miss, one hit, one page load and one full dirty page write; `direct_invalidations_not_evictions` counts explicit post-write invalidations, while M06 `evictions` counts capacity replacements only. `read_bytes`/`write_bytes` count full-page emulated canonical transfers; transactions are ceiling(page_bytes / max_model_transfer_bytes) per page transfer. An M06 LRU cache may defer dirty writeback until replacement/end flush. Because M03's original M01 analytical traffic uses **one access per neuron update** and often assumes writes on first touch, do NOT equate raw M01/M03 hit/miss counts with M06 method-level counters.
- **Fault contract:** never publish traffic as successful if independent neural traces, final canonical bytes, transfer version/ownership, or write acknowledgment disagree. Neither a partially written canonical page nor a clean flush after a fault is allowed.
- **Not modeled:** synapse DDR traffic (M06 replay keeps adjacency locally), AXI outstanding/burst/channel handshakes, B-before-AR **cycle count** and fence latency, actual FIFO backpressure, queue stalls, full service time, controller resource cost, physical DDR read/write bytes, DMA or power. Report these as `null`, not fabricated zero. M06 already has distinct original-HLS/AMD verified simulations; M07.1 does NOT rerun them or claim a new original-RTL verification.

## 2. Unit and integration tests

All M07 test methods are in `tests/test_m07_policy_baseline.py`. Levels: **Python host/source only**.

| Test | Fixture / sequence | Expected result and negative boundary |
| --- | --- | --- |
| `test_direct_no_reuse_and_lru_reuse_exact_bytes_transactions` | 8 neurons, 16 B/row, 2 neurons/block, 2 slots, 16 B/max emulated transfer. Write neurons 0,1,0, each as read→write. | Direct 3 misses/3 hits, 96 read +96 write bytes, 6 read+6 write transactions and 3 invalidations; no capacity evictions. LRU 1 miss/5 hits, 32+32 B, 2+2 transfers. Both persist identical final state and clear dirty pages. |
| `test_matched_m03_recurrent_workload_independent_M02_oracles_and_locality` | M03 synthetic N32/K8/fanout3/input rate4/T12/seed20261110; clustered and dispersed ID placements, each direct and LRU. | M02 dense=queued=M03 sparse=M06 paged trace, scheduled state IDs, event deliveries, and fanout. Same canonical role hash/spikes/work across four cases. Full canonical image and per-neuron last-update tick exact. Hit/miss and 2×state-evaluation accesses conserved. No greater LRU state transfer bytes than direct in this fixture. No physical timings presented. |
| `test_explicit_signed_delayed_recurrent_zero_and_quiet_neurons` | 8 neurons with negative initial voltage/bias, opposite signed duplicate arrivals, zero current, recurring self and delayed edges 1/3/8, 32 ticks, single-slot churn. | Both policies reproduce M02 dense/queued and M03 sparse independently; input zero still wakes target; disconnected quiet neurons stay at zero; final canonical signed voltages identical. |
| `test_zero_event_quiet_workload_never_fetches_a_page` | 32-neuron M03 zero-pulse/zero-fanout network, 8 ticks. | Both policies do zero evaluated updates, cache accesses, transfer bytes or transactions; M02 silent trace parity preserved. |
| `test_incomplete_or_wrong_pair_quarantines_without_committing` | Orphan write; read→second read; read→write of another ID; read→flush without write. | `ResidencyError`, sticky poison, unchanged canonical bytes, no subsequent read admitted. No silent invalidation or commit. |
| `test_faults_version_change_and_revoke_fail_closed` | Inject chunk-1 read fault, chunk-1 write fault, external canonical version change after read, revoke owner before write. | Fail closed with zero *acknowledged* write traffic and zero successful direct invalidations; interrupted write leaves dirty uncommitted page and original canonical bytes. Owner revocation is never treated as physical access. |
| `test_reject_unsupported_policy_bad_geometry_and_incomplete_image` | Unknown FIFO mode (not yet implemented), too few neurons, nondivisible block, too-small record for tick watermark. | Reject rather than silently falling back to LRU or making invalid memory/trace claims. |
| `test_cli_exclusive_create_and_source_only_evidence_label` | Run four-case command in a temporary folder twice with the same output filename. | First produces schema-stamped model JSON, four comparisons and role equivalence; second fails, preserving byte-for-byte first artifact. Real hardware and vendor execution flags remain false. |

### Regression gates and classification

- `python3 -m compileall -q src scripts tests`: Python syntax only, not functional verification.
- `python3 -m unittest discover -s tests -p 'test_m07*.py' -v`: **new M07 host-only functional, parity and negative tests**.
- `python3 -m unittest discover -s tests -p 'test_m02*.py' -v` and `test_m03*.py`: unchanged independent numerics and role/traffic contracts.
- `python3 -m unittest discover -s tests -p 'test_m06*.py' -v`: accepted residency, replay, faults and local test-source regressions; a test relying on `iverilog` may skip if Icarus is absent. A local Icarus functional simulation is **not** original Vitis HLS+AMD XSim.
- `python3 -m unittest discover -s tests -v`: broader host suite. Optional Icarus tests should be recorded as skips if tools are missing, never converted into claimed passes.
- Root GitHub workflow `neuromorphic_accelerator_m07_host_only.yml`: same host gates plus immutable CI-generated model JSON artifact. Inherited M06 GitHub workflow continues independently testing its local Icarus RTL and syntax-only vendor stubs. Neither workflow runs Vivado/Vitis 2025.2 or a board.

**Observed M07.1 GitHub Actions evidence (source-only):**

- First M07 workflow at `dc5d00b597b0ada15db1c619f48a279ffffe12f3`, run **42916491858**, FAILED: 7/8 M07 unit tests passed; the report-schema test incorrectly asserted `len(results)==4` although four actual cases are nested under **two** locality keys. This was a test-assertion bug, not a neural mismatch. The failed attempt remains in Actions history; do not erase it.
- Commit `f18433dd80482ac03514b91d775b0cf393781b5b` corrected only the assertion to require the two locality keys and **four policy leaf cases**. Source-only M07 push run **42916600964** and draft-PR run **42916608860** both PASSED. M07 push log: **8/8 M07**, **21/21 M02**, **28/28 M03**, and **324 M06 methods (312 passed, 12 skipped)**. The optional Icarus skips are NOT counted as local RTL passes; the separate inherited M06 GitHub workflow installs Icarus and performed its admitted standalone RTL checks successfully.
- The exact `f18433dd...` source workflow produced a model-only artifact and reported fixed N32 synthetic state transfers: **clustered direct=10,496 bytes vs LRU=256 bytes; dispersed direct=10,496 bytes vs LRU=10,496 bytes**. These values are **full-block software state model traffic**, not DDR bus timing, hardware throughput, speedup, or synapse traffic. The four neural traces and independent role inputs matched as required.
- The M01–M07 no-board workflows **all succeeded** for the tested `f18433dd...` HEAD on both push and draft PR. Later documentation-only commits, if any, need a fresh latest-head status check; this historic SHA-bound observation remains intact.

M07 is still NOT accepted. Owner Linux VS Code replication, remaining fairness/ablation work packages, final evidence review and explicit merge approval are outstanding.

## 3. What remains for M07

M07.1 only supplies a safe, reproducible **event-driven DDR-style state** direct-vs-LRU baseline with unchanged on-chip synapse adjacency. M03's four analytical controls remain accepted and must be integrated into a declared fair policy comparison for M07.2 (timestep/onchip, event/onchip, timestep/DDR-style, event/DDR-style). Before M07 acceptance, extend separate synapse traffic estimates; capacity-gate impossible on-chip baselines; sweep block size, resident slots and locality at fixed event count; instrument or explicitly label missing modeled queue/service fences; decide whether a single activity-aware scheduler is justified. Physical sample timing/resource and DDR evidence are M08 gates.

No modification of accepted M02 golden behavior, M05 HLS, M06 RTL, M06 original AMD/Vitis evidence, Loihi v3 or sealed MNIST TEST is made by this first work package.
