# P06-B1.5 — Three-resident-slot scheduling, NEXT routing and DDR traffic model

**Status:** B1.5 host-only source/tests/diagnostics **USER-ATTESTED NATIVE PASS (2026-10-19)**; final B1 software acceptance is recorded in `docs/P06_B1_6_FINAL_HOST_SOFTWARE_ACCEPTANCE.md`. No GitHub CI PASS or new KV260 measurements claimed.  
**Branch:** `agent/v3-p06-b1-scalable-packing`, draft PR #46 **unmerged**.  
**Prerequisites (user-attested):** B1.1, B1.2, B1.3 (including corrected decoder-order regressions), and B1.4 independent 26-tick monolithic-versus-partitioned oracles all reported native PASS. B1.2 previously demonstrated a structurally packed, **synthetic dense** 784→1000→10, 27-core, 794,000-connection topology with 27 full 512 KiB DDR records (13.5 MiB). No separately trained scaled checkpoint, sealed official MNIST TEST, or physical scaled acceptance exists.

## Original accepted P05.2i *physical* byte geometry vs new B1.5 *estimates*

Physical reference: `docs/P05_2I_ACCEPTANCE.md` from accepted real KV260 P05.2i user-verified MMIO/burst counters. This was a **five-logical-core / three-resident-context / one-engine / 16-barrier / 80-dispatch** physical regression on the original P03.2c PL shell, **NOT the 27-core scaled workload**.

| Item | Accepted P05.2i observation/contract | B1.5 usage |
|---|---:|---|
| Logical DDR image | **524,288 bytes** (fixed P02 v1 record) | One 512 KiB backing record per logical core, SHA256 anchored to B1.1 |
| Completed full page-in | **0x6B000 = 438,272 PL AXI bytes** | Count *per simulated page miss* |
| Completed mutable-only page-out | **0x1A000 = 106,496 PL AXI bytes** | Count *per dirty replacement / final dirty flush* |
| Completed AXI burst granularity | **256 bytes/burst** | Derive not claim observed read/write bursts |
| Actual P05 read bursts | **136,960** | Recompute 80 × (438,272/256) in independent sanity test |
| Actual P05 write bursts | **33,280** | Recompute 80 × (106,496/256) in independent sanity test |
| Actual physical total PL paging traffic | **43,581,440 bytes** | Recompute 80 × (438,272+106,496); historical evidence only |
| Actual measured 27-core paging or bandwidth | **NONE** | All 27-core figures are estimated / host-simulated |
| Actual scaled inference latency or energy | **NONE** | No default seconds, speedup, watts, or throughput inferred |

**The full P02 record is NOT transferred for each P05 page-in or mutable-out.** The accepted DMA payload limits are 0x6B000 in and 0x1A000 out; do not report 512 KiB × page-ins as observed page-engine traffic. The immutable base DDR image header/tail exists but is not moved in every transfer. P05 PL AXI page-engine registers did **not** measure all PS, cache, CPU, ingress or routing memory traffic; the B1.5 estimator does not invent these bytes.

## B1.5 algorithm and source reuse

`src/loihi_twin_v2/p06_b15_paging.py`:

1. Accept a **real B1.2** `B12Result`, original `NetworkSpec`, valid 26-tick schedule. Recompute `audit_compiled_candidate` to independently verify accepted **B1.1 P03/P02 initial 512KiB memory records and SHA256**. Export the genuine P08 paged image, check exactly 3 slots maximum and exactly one accepted HLS engine.
2. Create deterministic **LRU page slots** (up to 3 physical retention locations, distinct from logical core IDs). On empty slot or cache miss, charge 438,272-byte read; on dirty victim, charge 106,496-byte mutable write; cache hit charges **zero page transfer**. Every serviced logical core becomes dirty (even when silent); perform a mandatory final dirty flush. The program validates actual accepted `PagedHardwareImage.resident_page` core→slot identity **after each dispatch** rather than inventing a different fixed mapping.
3. Exactly one core is serviced per serial dispatch; **all cores must be visited once per epoch**. Each 26-tick schedule supplies an explicit complete permutation or defaults to ascending core IDs. An optional alternating ascending/descending order changes page hits and misses but **cannot** change neural results.
4. Compute canonical CURRENT event bank pressure as `external_packet(t) + routed_packet(t−1)` for **every** logical core, even when nonresident. Check <=4,096 current events/core before dispatch. Dispatch using the existing validated logical `LogicalCore.evaluate(t)` and source-derived ingress map, keeping 24-bit neuron-state evolution unchanged.
5. Gather and classify each source's emitted packet **at emission time** according to whether its destination logical core occupies a resident slot. Maintain remote/nonresident NEXT packets on a **conceptual software host-backing buffer** regardless of their physical residency; every emitted `SpikePacket` targets `t+1`. Enforce per-destination NEXT event <=4,096 and per-source output packet bank <=4,096; forbid any unserviced packet emitted at final tick 25. Only after all cores have executed and every NEXT packet is accounted for can the host model advance the global barrier.
6. Run the previously **user-accepted independent B1.4 monolithic** oracle against all 26 production core traces. Per original neuron compare integer synaptic inputs, before/after current/voltage/refractory, spikes and NEXT packet source/destination IDs; independently verify readout counts and first-index tie classification. Preserve the B1.4 reference trace SHA and normalized partitioned trace SHA across scheduling orders.
7. `B15Run.report()` and `project_schedule_only()` expose deterministic page-operation SHA256, logical-context DDR base offsets and original 512 KiB SHA256s, transfer counts, derived bursts, source-packet residency accounting, real numerical parity (if executed), and explicit **non-measurement** flags.

**Critical limitations:** the P08 initial context export is real; the **dynamic dirty state is still a Python logical-core object**, not a byte-exact runtime P02 mutable DDR dump or measured FPGA memory content. B1.5 simulates that logical state persists through page evictions and reports the physical cost of doing so. It does not implement A53 page ownership, cache coherency, physical HP0 streaming, serial PL dispatch timing, the B1.3 wire protocol in firmware, or FPGA readback parity. Model failures abort before claiming successful inference, but there is no claim of recoverable hardware backpressure or transactional rollback of an in-progress physical dispatch. These are subsequent P07-B physical acceptance questions.

## Distinct dense-27 *schedule-only* versus sparse-27 *numerical* probes

Because running all 794,000 synthetic connections for all 26 ticks is a separate heavier numerical workload, B1.5 supports two explicitly distinguished host paths:

**A. Dense 784→1000→10, 27 cores, 794,000 synthetic synapses — SCHEDULE-ONLY.**
Use `project_schedule_only(B12Result)`, which validates all real B1.1 packed DDR core records/source-SHA and per-core conservative event/packet occupancy; it creates the **26×27=702 visit** schedule but does **not** run neural timesteps. Readout's conservative incoming packet bound is 1,000/core, and maximum one 39-hidden-neuron core's emitted packet bound is 39/core. Fixed ascending core order, LRU/3 slots, cold empty slots and mandatory dirty final flush imply:

| Traffic estimate for 26 epochs | All ascending every tick | Alternating ascending/descending |
|---|---:|---:|
| One-engine sequential dispatches | **702** | **702** |
| Full page-ins | **702** | **627** |
| Page hits | **0** | **75** |
| Dirty runtime evictions | **699** | **624** |
| Final mutable page-outs | **3** | **3** |
| Total mutable page-outs | **702** | **627** |
| Estimated PL page-engine read bytes | **307,666,944** | **627 × 438,272** |
| Estimated PL page-engine write bytes | **74,760,192** | **627 × 106,496** |
| **Estimated PL page-engine total bytes** | **382,427,136** | **341,569,536** |

These values follow from the declared deterministic caching/order policy and accepted P05 **per-transfer byte sizes**. **None of these 27-core totals were measured.** They do not include host routing, CPU cache, image ingestion, board DDR transactions outside the PL paging engine or any time/energy.

**B. SPARSE 784→1000→10, 27 cores — NUMERICAL.**
Reuse the deliberately sparse B1.4 27-core source graph (one 784-input fanout destination neuron per hidden core, others with one input edge; all 1,000 hidden neurons route to one readout core with internal 10-output synapse expansion). User can opt into 26 independent monolithic-vs-paged neural ticks, both ascending and alternating service policies, 509,600 replicated external event packets, 25,000 emitted hidden→readout packets and 25 readout spikes per class. Full per-neuron parity tests are genuine for this separate sparse graph only, **not the dense 794,000-edge model**.

**C. Dense 784→6→10 and 784→40→10 — SMALLER NUMERICAL.**
Convenient local positive-control shapes to check actual density, multi-core partitioning and page eviction/parity before the expensive 27-core case.

## Optional explicitly hypothetical time calculation

`hypothetical_transport_seconds(bytes, assumed_sustained_aggregate_gib_per_second)` simply divides estimated page-engine bytes by a **caller-supplied positive, finite hypothetical aggregate sustained bandwidth**. It does NOT infer real KV260 bandwidth, PL frequency, algorithm latency or processor overlap; it excludes PL compute, PS cache/page management, control, barriers, other DDR users, and image/packet movement. No bandwidth assumption is supplied by default, and normal B1.5 reports return `latency_seconds=null`.

## Independent tests and run commands — PC only; no Vivado, JTAG or FPGA

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p06-b1-scalable-packing
git pull --ff-only origin agent/v3-p06-b1-scalable-packing
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

# New scheduling/cache/P05 physical-reference arithmetic/numerical tests
PYTHONPATH="$PWD/src" python -m pytest -q -rs tests/test_p06_b15_paging.py

# Previous B1.1–B1.4 and accepted P06-A regression gates
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p06_b14_differential.py tests/test_p06_b13_streaming.py \
  tests/test_p06_b12_partition.py tests/test_p06_b1_contract.py \
  tests/test_p06_lif_compiler_probe.py tests/test_p06_lif_input_probe.py

# Compile syntax and optional smaller numerical probe
PYTHONPATH="$PWD/src" python -m compileall -q \
  src/loihi_twin_v2/p06_b15_paging.py \
  tests/test_p06_b15_paging.py scripts/p06_b15_paging_probe.py
PYTHONPATH="$PWD/src" python scripts/p06_b15_paging_probe.py --shape dense40 --numerical

# FULL 27-core DENSE *STRUCTURAL* traffic estimates; separate CPU/RAM-intensive test
P06_B15_DENSE27=1 PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p06_b15_paging.py -k full_27_core_dense_structural_schedule_only_vs_alternating_lru

PYTHONPATH="$PWD/src" python scripts/p06_b15_paging_probe.py --shape dense1000
PYTHONPATH="$PWD/src" python scripts/p06_b15_paging_probe.py --shape dense1000 --order alternate

# FULL 27-core SPARSE *NUMERICAL* test; CPU/RAM-intensive; run one at a time
P06_B15_SPARSE27=1 PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p06_b15_paging.py -k full_27_core_26_tick_sparse_numerical_traffic_estimate

PYTHONPATH="$PWD/src" python scripts/p06_b15_paging_probe.py --shape sparse27 --numerical

# Optional what-if (not a physical measurement):
PYTHONPATH="$PWD/src" python scripts/p06_b15_paging_probe.py \
  --shape dense1000 --assume-gib-s 1
```

The user subsequently reported **all B1.5 tests and optional host probes passed** and supplied full dense27 alternating structural and sparse27 numerical terminal reports (see B1.6 acceptance ledger). The reported probe marker was `P06_B15_HOST_ONLY_PAGING_ESTIMATE_PASS=1`. Distinguish structural-only from independently numerically executed; a skipped optional test is NOT an accepted PASS. **Native PASS is user-attested; the authoring agent did not independently execute CI/native or any physical KV260 runs.**

## Next milestones (not yet started)

**B1.6:** accepted B1 user results and source/occupancy/initial DDR hashes, impossibility counterexamples, B1.1–B1.5 evidence ledger, honest dense structural vs sparse numerical interpretation, and recommendation for P06-B2 separate training checkpoint. Later **P07-B** requires separately authorized bare-metal operator isolation and a real new A53 multi-core streaming/paging firmware; no board tests or physical page-traffic claims are authorized here. Do not merge draft PR #46 without explicit user approval.
