# P06-B1.6 — Scalable packed-network feasibility: FINAL HOST-SOFTWARE ACCEPTANCE

**Decision:** B1.1–B1.5 **USER-ATTESTED PASS; B1 HOST-SOFTWARE PHASE CLOSED (2026-10-19)**. This is a feasibility gate for P06-B2 training, **not** an accepted trained large checkpoint, scaled A53 firmware, 27-core KV260 hardware execution, sealed MNIST TEST or measured scaled bandwidth/power/latency.  
**Source branch:** `agent/v3-p06-b1-scalable-packing`. **Draft PR #46 remains UNMERGED**, pending explicit separate permission; this closeout is not merge authorization.  
**Machine-readable user-reported acceptance:** `docs/P06_B1_6_USER_ACCEPTANCE_LEDGER.json`. Do not replace a user's source file/evidence with a claim that those original local PC artifacts were uploaded or rehashed here.

## Accepted milestone gates and supporting native user reports

| Gate | Acceptance | Accepted user evidence |
|---|---|---|
| B1.1 | **PASS** | Original P03/P02 512 KiB/core and per-core 128 KiB accounting, 32,768 packed synapse words, 4,096 axons/routes/events/packet bounds; original accepted compiler reused read-only. |
| B1.2 | **PASS** | Source-preserving exact-template greedy synapse partitioner. 784→1000→10 **synthetic dense** mapping: **794,000** effective source edges, **27** logical cores (26 hidden partitions of 39×25+25, one 10-neuron readout), **14,155,776** bytes initial DDR backing and max **128,576 logical synapse bytes/core**. User ran full optional structural test and reported `P06_B12_SYNTHETIC_STRUCTURAL_PASS=1`. |
| B1.3 | **PASS** | Distinct versioned `P06B13I1/P06B13R1` many-core source replication/NEXT packet ABI, canonical packet order, 4,096/core admission and fail-closed corruption. Two test failures were corrected with semantic validation before canonical ordering; **user re-ran and verified all tests pass**. |
| B1.4 | **PASS** | Independent original `NetworkSpec` 26-tick signed integer monolithic recurrence compared to partitioned state/current/voltage/refractory/contributions/spikes/NEXT packets and readout. User reported all tests and optional numerical probes passed; 27-core numerical fixture is **SPARSE**, not full dense. |
| B1.5 | **PASS** | Three-resident-context/one-engine P05/P08 modeled LRU and NEXT barriers. User reported all tests and supplied dense27 alternating and sparse27 numerical reports. **627 page-ins, 75 hits, 627 mutable outs, 341,569,536 modeled PL page-engine bytes** alternating; sparse27 report says `algorithmic_neural_parity=true`, 26 ticks and 25,000 routed packets. Both reports explicitly set `physical_scaled_page_traffic_measured=false`. |

The B1 acceptance ledger pins the user's actual printed SHA256s for:
- Dense structural original source `d51d0f2b2e6e20b48fed26275770d089bbc53b704477f644c189e16adf3db411`.
- Dense B1.2 compiled deployment `8374278ca10c7e1a0e1b8a681ae4ecadadc43eab145697316becca75f2cef3cd`.
- Dense B1.1 packed DDR capacity audit `4bc14954d43c67b0ce5bc92961b20c302674630e6c5a8c33e61d16373007406f`.
- Alternating schedule `87299577b72aa9e97ce67de2f2bde847c0cf6b5bd935b43915b5dd55f1f41ffb`.
- Sparse original source/mapping/audit and independent monolithic versus partitioned 26-tick SHA256s (see JSON ledger). The different monolithic and partitioned SHA256s reflect **different trace schema/normalization**, not a numerical mismatch: the comparison tests assert per-neuron equality, and the user-reported `algorithmic_neural_parity=true` reflects that equality.

The user also supplied full 27 per-core dense initial DDR record SHA256s and corresponding initial payload SHA256s in the posted terminal output. Those are **initial immutable records only**; never imply full runtime mutable DDR dumps. The complete PC raw original report and files are not in the GitHub repository, so the ledger references their provenance without claiming it contains all source bytes.

## Unmeasured scaled scenario versus actual P05 physical evidence

The ORIGINAL independent physical P05.2i regression demonstrated **43,581,440 physically observed PL page-engine bytes** for 5 logical cores × 16 barriers / 80 dispatches: 438,272 bytes **per full in**, 106,496 **per mutable out**, 256 byte bursts. B1.5 extrapolates these measured **sizes** to **unexecuted** 27-core service orders. It does NOT measure scaled AXI readback, PCI/PS/PL traffic, sustained bandwidth, elapsed seconds, energy or power.

- **Fixed ascending service:** 26×27 = 702 logical engine dispatches, 702 page-ins, 702 mutable page-outs, **382,427,136 estimated** page-engine bytes.
- **Alternating service:** 702 engine dispatches, 627 ins, 627 mutable outs, 75 hits, **341,569,536 estimated** page-engine bytes.
- **Static backing:** 27 × 524,288 = 14,155,776 bytes complete context image total; **this is NOT the per-dispatch transferred page-engine payload**.
- **Dynamic runtime:** mutable event/state bytes are modeled in Python, **not materialized** as actual P02 runtime DDR images.

Both service orders are valid under the host P05 LRU scenario and use a single HLS engine and at most three resident slots. B1.4/B1.5 numerical equality was established for **small dense** and **large sparse** synthetic source graphs only. There is no accepted complete 26-tick numerical execution of the **794,000-edge dense** graph in B1, and no FPGA scaled inference. The maximum conservative per-core CURRENT events for dense B1 was 1,000, less than 4,096; maximum hidden emitted packets per core 39.

## Resource feasibility and intentional fail-closed bounds

B1.2's dense synthetic 784→1000→10 partition is **greedy**, not a proof of global minimum possible cores. The 39-neuron group is constrained by **logical synapse accounting**:
`4 × (784×39 + 784 template headers + 784 axon bindings) = 128,576` bytes < 131,072.
Forty neurons under the corresponding unique-template shape cost
`4 × (784×40 + 784 + 784) = 131,712` bytes > 131,072.
The normal B1.1/B1.2 tests reject intentionally impossible single-neuron axon/event/synapse budgets, insufficient core IDs, route fanout and 4,097-event oversubscription instead of truncating edges.
For the readout core, 1,000 routed packets expand locally into ten output compartments; packet count is not synapse count.

## GO / NO-GO decision

**GO for P06-B2 TRAIN+VALIDATION-ONLY candidate development:** a distinct project-trained 784→1000→10 dense model using the accepted exact 25-input+one-drain / signed24 LIF/P03 / t+1 neural recurrence and B1.2 capacity-verified opt-in packer. A new B2 checkpoint **must** earn separate integer numerical parity, per-core packing, validation/silent-class review, atomic SHA freeze and separately prespecified official TEST protocol before any P07-B physical deployment. B2 does NOT overwrite the accepted Track A 784→32→10 checkpoint or expose the sealed test partition.

**NO-GO for physical scaled deployment now:** P05's accepted diagnostic ABI supports only one external input axon per core and is not this scaled B1.3 transport. There is no accepted A53+PL implementation of `P06B13I1/P06B13R1`, physical 27-context reset/backing/owner/barrier contract, live KV260 27-core state traces, runtime DDR byte-exact checks or physical paging telemetry. These need separately authorized P07-B with explicit operator/DDR-owner isolation.

## Reproducibility (off-board)

On branch `agent/v3-p06-b1-scalable-packing`, user-verified test groups:
```bash
cd ~/Git/Thesis
git fetch origin
git switch agent/v3-p06-b1-scalable-packing
git pull --ff-only origin agent/v3-p06-b1-scalable-packing
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p06_b1_contract.py tests/test_p06_b12_partition.py \
  tests/test_p06_b13_streaming.py tests/test_p06_b14_differential.py \
  tests/test_p06_b15_paging.py

# Optional user-accepted full structural and numerical cases, separately:
P06_B12_FULL_SYNTHETIC=1 PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p06_b12_partition.py -k full_784_1000_10_synthetic_structural_feasibility_only

P06_B15_DENSE27=1 PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p06_b15_paging.py -k full_27_core_dense_structural_schedule_only_vs_alternating_lru

P06_B15_SPARSE27=1 PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p06_b15_paging.py -k full_27_core_26_tick_sparse_numerical_traffic_estimate
```

B1 user reported PASS; this acceptance document itself was authored on the remote branch and **was not independently executed through CI**. Any new B2 tests or reports require their own subsequent user PC native gate.

## Follow-up

Begin B2 on a **separate branch based on the B1 closeout commit**, preserving PR #46 draft/unmerged until the user expressly permits merge. B2's next PR must remain **stacked on the B1 branch** unless and until the B1 PR is explicitly merged into main. Never merge one PR to make progress on the other without permission.

## Post-merge integration addendum (2026-10-19)

The branch/PR status in earlier sections of this phase document is
**historical provenance from when this submilestone was under review**,
not the current integration status. After the user accepted B2.5 and
explicitly authorized sequential integration, GitHub confirmed:
**P06-B1 PR #46 merged to `main`** as
`35ea181360ebf15627c2943090fbdc3c6bf3949e`;
**P06-B2 PR #47 retargeted and merged to `main`** as
`42f84de3bbbe62302599818c39e7e54747ce8aa2`.
The B2.1–B2.5 host gates are user-accepted, and B2.4's original
33-asset/27-P02-context freeze is locally SHA-verifiable. Next work
starts from merged `main` at **P07-B**; see
`docs/P07_B_NEXT_CHAT_HANDOFF_SEED.md`.

All original experimental distinctions persist: B2's **97.08%**
comes from canonical **TRAIN-derived validation**, not the sealed
official B2 MNIST TEST; three complete B2.3 dense trained
26-tick validation frames do NOT imply a physical 27-core run.
P07-B KV260 multi-core hardware integration, physical paging/
latency/energy and B2 official TEST are **NOT YET ACCEPTED**.
