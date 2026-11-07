# P08-B1 — Matched Track A/Track B scaled physical-latency measurement contract

**2026-11-01 source-development candidate, PC ONLY.** Branch `agent/v3-p08-b-scaled-latency`, based on main `2c9767ba6f6e001b52b14ff4285ae60c2d7ab47b`. P08-B1 is not an operator-accepted physical protocol, instrumented A53 ELF or a measured KV260 latency. P07-B's completed freeze, accepted P03 bitstream/XSA, original V3/B5 ELF/map/evidence, frozen Track A, root `LitReview.md` and historical roadmap must not change. P09 comparison and the original Track B official TEST remain unstarted and sealed.

## B1 source audit and authoritative comparison basis

- **Matched population:** original P08-A3.2 six-session dataset, **first 1,024 distinct canonical TRAIN-derived validation IDs in original seeded order**, raw 784-byte uint8 pixels, **25 injection ticks + one drain tick**. Use precisely the pre-existing P08-A `p08_a3_2_stage1024_20261019T003150Z` (or independently identical SHA-validated original stage), not the three original B4m validation ingress frames. Stage file `p07_a4_pixels_raw.bin` is the comparison population; its P07-A descriptor, 784→axon map, and journal are **NOT valid B ingress artifacts**.
- **Selection:** original `p06_a3_data.load_train_validation(strict=True)` uses canonical TRAIN-only IDX MD5, `random.Random(20261013).shuffle(range(60000))`; first 50,000 training, remaining 10,000 held-out validation. Track A P07-A4 validation and Track B P06-B2.2 `require_pinned_train_validation` both enforce **the same** training-index SHA `1cbcb0b2bf481958d6c917ea6d70fa44a20839406f0c824540f8e691edfdd851` and validation-index SHA `3b9520013f30742c3818f55024ea39e3e0632113c487c589fdfbb73c7d274831`. Independent Python seed reconstruction recovers first indexes **37384, 27347, 20178**, last index **42925**, first1024 LE32 index SHA `8414a9f0f6f2e0f61ccd87ce2f43b972a8d0d8342702d3f2e8ac9351574d2aab`, **zero source-index overlap** with Track B training. A different training source index could still contain **byte-identical raw pixels**; the real stage verifier separately reports all such cross-partition 784-byte pixel aliases instead of silently claiming they do not exist. This is a source-index proof, NOT a substitute for checking original physical stage pixels and 33 frozen B2.4 assets on the operator's workstation.
- **Frozen B authority:** `artifacts/p06_b24_frozen_1000` accepted original 33-file freeze and checkpoint `checkpoint/candidate_manifest.json`, compiled digest `02a6b68a2eda4587bbdf07e3af4aa63bdd7214223e853b08d8f6463896364f5a`. A separate frozen verifier must pass read-only for all 33 assets and model/source manifest must equal the freshly authenticated original TRAIN split. Original B2.4 software validation **97.08% on 10,000 TRAIN-derived validation**; **not** Track B official TEST.
- **New read-only gate:** `scripts/p08_b1_matched_source_audit.py` checks canonical TRAIN archive, pinned selection, original stage descriptor/CRC/manifest and all pixel/label/image IDs/SHA, B candidate source identity and 33-asset freeze, and writes one no-overwrite external JSON with exactly 1,024 per-image hashes, original order, zero source-ID membership overlap, observed byte-exact training pixel aliases, and explicit `B_KV260_physical_run_completed=false`. Negative fixture tests: `tests/test_p08_b1_matched_source.py`. No physical or signed B ingress preparation yet.

## Measurement scope and invariants to implement in B2

Primary comparable number = complete **A53 image service** `after_commit - service_start` in raw `CNTVCT_EL0` ticks divided by that physical session's recorded `CNTFRQ_EL0`. Track A `service_start` is before image ingress; `after_commit` after original neural result/selected trace journal commit, excluding profile-sidecar flush. Match those boundaries for B **including per-image restoration of all original 27 logical DDR contexts, ingress generation, three-slot pager and scheduler re-init, 26 ticks, routing, all physical state/trace reads necessary for oracle, and durable result commit**. Exclude prelaunch XSDB/bitstream/ELF downloads and JTAG collection. Do not falsely omit B reset/context staging, or time host-preparation externally while calling the remainder equivalent to A complete service.

A2.1-like B **image-only** and A2.2-like B **detailed-tick** firmware should be separate, versioned, externally built/ELF+map SHA-pinned candidates to quantify instrumentation perturbation. B tick boundaries should aim for `t0` before external source/encode, `t1` after source, `t2` after CURRENT commit, `t3` after all 27 dispatch+poll operations, `t4` after per-core physical spike/state readback, `t5` after NEXT routing, `t6` after the global barrier. **Not yet scope-matched:** the accepted B V3 source performs trace reads via a hook *during each individual core's dispatch before eviction*; hence the A2.2 `t3` (dispatch before trace) cannot be copied mechanically, and naive `t3`/`t4` subtraction would lie. B2 must either introduce semantically safe, separately stamped per-core nested subspans with an explicit inclusive definition, or document a bounded unmatchable interval before physical approval. B has 27 dispatches per tick, A one; per-tick durations and A53 runtime includes architecture-dependent work.

Required B descriptors/receipts: image ID/order, SHA of raw pixels and frozen B ingress encoding, 26 tick identities, raw A53 clock frequency and monotone service/tick timestamps, 702 physical dispatches, 26 barriers, three physical context slots, per-core page in/out counts and bytes, trace/raw-clock integrity, physical P03 PL dispatch/page cycles **in its own clock domain**, source spikes, packets and routed NEXT counts, predicted class and output spike vector, raw journal and timing sidecar version/CRC/terminal receipts. The original TRAIN0 structural traffic numbers (307,666,944 page-read and 74,760,192 page-write bytes, etc.) are **historical observations**, not blindly a per-image assertion for all future inputs. Never identify a PL cycle with A53 `CNTFRQ_EL0` or sum overlapping A53 windows as disjoint.

## Numerical gate and dataset policy

For **every physical B image**, compare independent original frozen B2.4 scalar 26-tick oracle against actual B physical output spikes, route/source fingerprints, 26 barriers, 702 dispatches and any separately selected full trace. The current B5 raw numerical reference is restricted to original TRAIN ordinals 0/1/2; B2 must extend the independent reference to **arbitrary pinned raw TRAIN validation pixels**, without modifying accepted model, accepted routes, B ingress ABI, official TEST or original V3/B5 physical evidence. Selected full 26 × 1,010-neuron trace for frame **1023** (if approved and feasible) is analyzed separately; **1,023 ordinary frames/run** enter the central latency distribution. Physical timing without independent B numerical equality = **NO-GO** even if timer sidecars/CI pass.

Two model sizes are materially different: A 784→32→10, one logical core, 42 neurons, 26 FPGA dispatches/image; B 784→1000→10, 27 logical cores virtualized through three physical slots, 1,010 neurons and **702 FPGA dispatches/image**. Matched image IDs and tick semantics enable a controlled dataset comparison, **not matched computational complexity, true Loihi hardware emulation, pure PL speedup or energy advantage**. P09 will perform final comparisons; no premature speedup conclusion in P08-B.

## Existing B scheduler and memory audit — outstanding implementation blockers

The accepted `p07_b4m_full_board_diag_v3.c` loads **one** ingress at `0x41100000` and creates a fresh `p07_b3_init` and `p07_b3c2_init` once; `p07_b4m_full_run` consumes all 26 ticks and final-flushes all three slots, making the backing records **mutable**. Calling `p07_b3_init` alone resets scheduler bookkeeping but **does not recreate the immutable original 27 context bytes**, which is essential before each distinct image. B2 requires safe frame-by-frame restoration, complete initialization and native numerical multi-frame evidence before any 1,024-frame claim.

Physical DDR accepted original regions: 27×512KiB `[0x40000000,0x40D80000)`, input routing `[0x41000000,0x410E0000)`, one B ingress `[0x41100000,0x411E0000)`, bindings `[0x43FC0000,0x43FC4000)`, output routes `[0x43FC4000,0x43FD8000)`, V3 mailbox `[0x43FF0000,0x43FF0100)`, B5 mailbox `[0x43FF0100,0x43FF0200)`, accepted B5 selected trace `[0x42000000,0x420CD280)`; original V3 low-DDR ELF load envelope `[0x0,0x106B00)`. **No new P08-B allocation/owner exemption is approved yet.** Raw pixels alone are 1,024×784 = **802,816 bytes**; 1,024 maximum-size B encoded ingress frames cannot be presumed to fit 64MiB, so B2 should explore a read-only audited raw-image staging region plus single-buffer frame encoding and provenance-safe context restoration. Prove physical DDR range non-overlap and actual Vitis ELF `PT_LOAD`/stack/heap limits before proposing any run. Neither static non-overlap nor cold boot proves exclusive FSBL/TF-A/U-Boot/Linux/DMA DDR ownership. New sidecar buffers must avoid accepted B5 trace areas and firmware.

## Acceptance steps and physical checkpoint

**B1:** source contract, reproducible explicit manifest/ledger audit and native negative tests; PC-only. Run the operator's genuine local B1 source gate below; retain any failures as evidence. **B2:** new distinct timing firmware, full 1,024 image ingestion/reset/buffering, arbitrary-image scalar reference, strict offline source/memory/ELF admission, native and Vitis build. **B3:** explicit operator-approved destructive first16 JTAG-only physical pilot after passing all PC/ELF/DDR gates and a fresh cold boot; collect genuine timing and independent neuronal parity. **B4:** only after accepted B3, six independent cold-boot physical sessions paired AB/BA/AB as in Track A and no batch/trace scope drift. **B5:** preserve original signed evidence, summarize standalone B results, P09 handoff and separate operator acceptance; no merge without explicit user approval.

The **next operator validation** does not touch KV260:

```bash
cd ~/Git/Thesis
git fetch origin
git switch --track origin/agent/v3-p08-b-scaled-latency
# If branch already exists locally: git switch agent/v3-p08-b-scaled-latency
git pull --ff-only origin agent/v3-p08-b-scaled-latency
source ~/Git/Thesis/.venv-p08/bin/activate
cd Loihi_Digital_Twin/v3
PYTHONPATH="$PWD/src" python -m pytest -q -rs tests/test_p08_b1_matched_source.py
PYTHONPATH="$PWD/src" python -m py_compile scripts/p08_b1_matched_source_audit.py
```

Then independent genuine local gate (no writing to original source/stage/freeze; NEW file name only):

```bash
export P08_B1_STAGE="$HOME/Thesis_Evidence/p08_a3_2_stage1024_20261019T003150Z"
export P08_B1_REPORT="$HOME/Thesis_Evidence/p08_b1_matched_source_$(date -u +%Y%m%dT%H%M%SZ).json"
test ! -e "$P08_B1_REPORT"
PYTHONPATH="$PWD/src" python scripts/p08_b1_matched_source_audit.py \
  --stage-dir "$P08_B1_STAGE" \
  --train-data-dir "$PWD/data/mnist_raw" \
  --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" \
  --out "$P08_B1_REPORT"
```

Require `P08_B1_MATCHED_DATASET_OFFLINE_PASS=1`, zero B training overlap, exactly 1,024 pixel rows and `B_KV260_physical_run_completed=false`. This is only source admission. No JTAG call, no B firmware build, no P09 comparison and no new official TEST evaluation.
