# P08-A1 — Compact KV260 Measurement Architecture Audit and Proposed Benchmark Protocol

**Status: LATENCY-ONLY PROTOCOL DIRECTION ACCEPTED BY USER 2026-10-18; POWER/ENERGY DEFERRED; NO P08 PHYSICAL METRICS.**  
**Started:** 2026-10-17. **Branch:** `agent/v3-p08-a-physical-baseline`.  
**Starting point:** merged `main` commit `d31df0ba73568c5e6c3023e0eda7269945f5294d`.

## 2026-10-18 later status addendum — completed latency experiment, A5 still open

The originally authorized **latency-first** work has now yielded a **user-attested complete P08-A3 physical three-pair KV260 A53 service baseline**: six independently launched user-operated hardware sessions of the same original first1024 TRAIN-derived validation image population (trace index 1023), physical independent P07 packed-neural parity gates and versioned timing sidecar integrity accepted by the per-pair verifier. User-supplied matched-image A2.2−A2.1 median differences across A2.1→A2.2 / A2.2→A2.1 / A2.1→A2.2 orders are **+16.840, +25.400, +29.710 µs**; mean across these three pair-level medians **+23.984 µs**, between-pair sample SD **6.551 µs**. Exact values and limitations: [final A3 repeated latency report](P08_A3_2_3_FINAL_PHYSICAL_REPEAT_RESULTS.md).

This **updates** the historical "no P08 physical metrics" status originally written above without replacing that historical A1 starting state. A3 physical **A53 full-image service** is measured around 35.7 ms; no independently calibrated pure FPGA PL inference latency in seconds or full CPU speedup is established. **P08-A5 (section 6)** is still required by the original acceptance contract: same-semantics CPU compute-loop and full image-to-class comparator, scope-matched comparison and final closeout report with explicit user acceptance. Power/energy **P08-A4 remain deferred by user**, not a barrier to latency-only closeout. Hence **P08-A3 may be accepted at user-attested descriptive physical level, but whole P08-A must remain OPEN** unless A5 is completed or explicitly re-scoped by the user. The local aggregate report hash was not uploaded and the final third-pair aggregate PASS marker was not quoted verbatim; independently file-seal existing local evidence before final closeout.

## 2026-10-18 approved scope update

The user approved proceeding to P08-A2 with **latency characterization only for now (dataset-wide throughput derivable as a supplemental, non-gating statistic)**. All power/energy telemetry, rail selection and sensor sampling from sections 5 and 7 are **DEFERRED, NOT PART OF THE CURRENT PHYSICAL ACCEPTANCE GATE**. Those sections are preserved as non-executed future design notes. No sensor search or energy estimate is authorized. P08-A2.1 candidate code and local verification instructions: [P08_A2_1_LATENCY_SIDECAR.md](P08_A2_1_LATENCY_SIDECAR.md). P08-A1's proposed three independent 1,024-image repeat policy remains a **proposal** for P08-A3 and is not considered physically approved or executed.

## 1. Purpose, scope and non-negotiable baseline

P08-A characterizes **actual physical latency, throughput, power and energy** of the **already accepted P07-A compact Track A** on AMD KV260, before Track B implementation. P08-A1 is **protocol, implementation audit and measurement-boundary design**, not a claim of new instrumented firmware, board results or a powered benchmark.

The accepted experiment is the original project-trained **784→32→10** integer SNN: one logical core, 42 neuronal compartments, 25,408 packed synapses, 816 registered axons, **25 input ticks + one NEXT-bank drain (26 logical timesteps)** and a single physical P03.2c HLS engine controlled by a bare-metal A53. The accepted full official MNIST TEST remains **9,456/10,000 = 94.56%**, with 10,000/10,000 independently exact physical/oracle comparisons. P08-A does **not** retrain or reselect after that test.

The following accepted physical artifacts are read-only:

| Artifact | Accepted SHA256 / identity |
| --- | --- |
| P03.2c routed XSA | `52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f` |
| P07-A4.2b persistent standalone ELF | `dcba738e0d9e78a6bf9fb61fba5ff23dcd1da68f8903fb1dbd33952b3dca38fb` |
| P02 immutable 512KiB core0 DDR record | `9617a822f74faa8723869bb576cf57b38af1a1a91ac81c47c246a9425d0dd955` |
| Accepted ELF firmware marker | `P07_A4_2B_PERSISTENT_KV260_A53_FROZEN_TRACK_A_V1` |

Never overwrite source artifacts, raw evidence, frozen journal ABI, P07 numerical fields, hardware bitstream, existing physical results, or `main`. An **instrumented experimental A53 application** (if needed in P08-A2) must be separately built, named, hashed, tested, and numerically reverified on KV260 before its metrics are accepted. A modified bitstream is a **separate change requiring a new physical equivalence gate**, not an implicit requirement of P08-A.

Relevant original evidence is user-local, notably `/tmp/v3_p07_a4_official_full10000_20261017T204944`, and must be backed up to a **user-approved durable, untracked location** before any cleanup. Do not invent the `P03_DIAG_REPORTS` absolute directory, test-archive SHA256, bitstream SHA256, or power sensor.

## 2. Read-only source audit: measured counters versus missing observability

| Component | Existing capability, verified in source | P08-A limitation |
| --- | --- | --- |
| `software/p03/p03_runtime.c` | `ps_inference_ticks`, `ps_control_ticks`, `ps_route_ticks`, `ps_barrier_ticks`, `pl_dispatch_cycles`, `pl_page_cycles`, dispatch and page/hit counts | `ps_inference_ticks` starts **after initial page-in** and ends **before `write_result`**. It is not image entry→committed-result latency. Timing samples are aggregate per call, not a 26-point per-tick series. |
| `software/p03/p03_hw_adapter.c` | Split 64-bit PL `P03_REG_DISPATCH_CYCLES_LO/HI` and `P03_REG_PAGE_CYCLES_LO/HI` read after completed hardware commands; MMIO command, DONE polling, packet status | PL hardware cycles and A53 timer ticks are **different clock domains**. A PL dispatch counter should not be labeled an HLS neuron-only/event-source counter until the RTL/HLS definition and clock are confirmed. |
| `software/p07/p07_a2_runtime.c` | Per-tick deterministic ingress event encoding + event-bank append, FPGA dispatch, ten readout trace reads, packet routing, barrier | These extra calls occur around PL dispatch; the existing PL cycle field does **not** capture full per-tick software and MMIO service. Need distinct event encoding / bank-writing / trace readback timestamps. |
| `software/p07/p07_a4_board.c` | A53 `cntvct_el0` timer callback; one autonomous persistent launch over raw image staging; complete journal/result emission | Current `P07A4R01` 96B/image journal has **no calibrated image timing fields**. Result ABI is frozen. Setup, per-frame reset/prepare, post-frame journal commit, and any selected trace cannot be inferred from XSDB wall time. |
| `vivado/p07_a4_xsdb_run.tcl` | Launch once; poll terminal journal at 1s intervals; read back 1MiB journal plus 64KiB selected trace | Host polling/ELF download/JTAG readback are **not** precise inference timestamps. Existing terminal `0x600D600D` proves completion only, not numerical parity or speed. |
| P05.2i physical observability | Read-only PL HP0 page AXI successful burst/byte counters were independently physically accepted | They capture **page-engine traffic**, not all PS/DDR writes, neuron/event MMIO, packet traffic, whole-system bandwidth or energy. Existing P05 timings are **not MNIST timings**. |

Prior P03 documentation records `CNTFRQ_EL0` for calibrating the A53 generic timer and separately warns that PL counters require their own clock interpretation. **A53 timer frequency and FPGA clock rate must be recorded in the P08 evidence for the exact setup**; never silently treat raw cycles as seconds. In particular, there is currently **no independently verified physical event-source-only interval** and **no accepted P08 power probe**.

P08-A2 should first evaluate **adding an optional, separately stored versioned performance sidecar** (not modifying the CRC-protected P07 result journal) around the current frozen firmware control points. Design it fail-closed with bounds, overflow detection, sequence IDs, terminal state and no silent rollover. If sampling changes the event path, quantify instrumentation overhead with paired runs. Do not claim a noninvasive instrument changes neither semantics nor timing without testing.

## 3. Proposed timing definitions to freeze before measurement

All timestamps in the same duration arithmetic are taken on one clock with recorded frequency; store **raw ticks/cycles and endpoint names** before computing seconds. Distinguish:

1. **PL dispatch interval (per logical tick):** completed hardware-reported `P03_REG_DISPATCH_CYCLES` scope, confirmed against RTL/HLS definition and PL clock. Report 26 samples/image, distribution and aggregate. This is *not automatically* pure LIF compute time.
2. **Event-source software interval (per tick):** A53 begins `p07_a1_tick_events` → encoder returns; separate **event-bank append/AXI/MMIO interval** from first append to last accepted write. Explicitly label software duration and source of timer.
3. **Tick-service interval:** from start of event encoding on the A53 to completion of tick barrier/bank-swap bookkeeping, including trace sampling and routing. Measure separately from PL dispatch and do not sum overlapping spans.
4. **Neural execution window (26 ticks):** P03 `ps_inference_ticks` after first resident page-in and before the final write-result callback; includes software `load_input`, tick loop, routing and barriers. Do **not** equate it with per-image service.
5. **Complete image-service latency:** A53 `execute_image` entry before image load/ingress → successful journal and selected trace commit (when applicable). Includes full core reset/reprepare, initial page-in and all 26 ticks; reports trace-selected versus ordinary frames separately. Excludes prelaunch DDR provisioning, ELF download, board programming and XSDB collection.
6. **Autonomous steady-state throughput:** total **successfully verified** committed frames ÷ board-local active processing interval (start of first frame service → last frame commit), with first-frame startup and potential selected-trace cost explicitly identified. Separately report **operator-visible cold-launch throughput** if desired, with host/JTAG provisioning and setup separately itemized.
7. **PS and memory overhead:** A53 callback and bookkeeping periods (reset/copy/cache work, encoder, MMIO dispatch-and-poll wrapper, readback, route, barrier, journal); initial page-in versus additional paging, hits/misses/evictions, actual PL HP0 page bursts and bytes. These terms **must not be subtracted as if disjoint** without endpoint verification.

Do not derive latency by `PL cycles × 26` or compute per-image FPS from the interval between XSDB polls. Record expected single-core resident behavior separately from **physically observed** page counters.

## 4. Proposed population, repeat policy, and correctness gate

Use **TRAIN-derived held-out validation only** for P08 instrumentation development, not fresh official TEST replays. Preferred predeclared population: the **same original first 1,024 distinct validation images** already proven in P07-A (same order, raw pixels, source identities, 25+1 ticks). First run a 16-image synthetic/validation pilot to check the timing sidecar and numeric invariants. For final characterization, propose **three independent JTAG-only cold-reboot 1,024-image runs** as a starting repeat policy (3,072 physical image executions, 1,024 distinct images), subject to user acceptance *before* the first timed run.

For each launch require original-order image ledger, raw sidecar samples, unmodified P07 journal and selected neural trace, check of `0x600D600D`, **independent exact P03 packed-oracle checks for every image's 26×10 spike histories/routes/counts** and the selected 26×42 full trace. Fail closed on any numerical mismatch, missing sample, wrong timestamp ordering, missing timer rate, unverified deployment hash, or counter overflow. Repeated images are **not 3,072 statistically independent data examples**. Summarize within-run per-image distributions and **between-run** dispersion separately.

Preserve all attempts (including timeouts and failures) in unique timestamped **no-overwrite** evidence directories **outside Git-tracked source**, with input/image map hashes, SHA256 manifest, ELF/XSA/bitstream fingerprint, runner logs, raw counters, profiler schema, exact clock sources/frequencies, thermal/sampling conditions and verifier output. `/tmp` evidence is temporary until deliberately archived. A4 official full-test data must not be rewritten, fault injected or used to tune P08.

## 5. DEFERRED — future power/energy measurement contract, NOT an active task

**No KV260/K26 usable rail sensor, exact rail boundary, sample cadence or metrological accuracy has yet been verified for this P08 setup.** The roadmap permits SOM telemetry as an *option*, not proof of a live accessible channel in bare-metal JTAG mode. P08-A1 leaves its selection **open** pending documented actual sensor/equipment discovery and the user's physical access confirmation. External DC input power measurement is an alternative if it can be safely and independently performed.

Before collecting publishable power data:

- Record **exact boundary**: K26/SOM rail(s), whole board DC input, or another identified domain; supply voltage/current units, equipment calibration/accuracy, raw sampling timestamps and cadence.
- Measure **unconfigured idle**, **configured idle without active inference**, and **sustained active inference** under a documented bare-metal DDR ownership policy. If an idle state is inaccessible or incompatible, label it *not measured* rather than infer it from another configuration.
- Record board/ambient thermal conditions and boot-state controls; choose a stable, repeatable observation window. Align actual active timestamps to power samples, quantify sensor resolution and synchronization uncertainty.
- **Total active energy** is the integral of same-domain power over the declared active interval. **Incremental energy** is the integral of `P_active(t) − P_configured_idle` over the same interval, with uncertainty. Divide by verified completed frame count only when integration windows match.
- If polling is slower than single-image inference, power is a **sustained-run aggregate estimate**, not an observed single-image power trace. No claims of core-only FPGA energy or Intel Loihi energy equivalence without a justified subsystem attribution.
- Quantify spread across independent runs, meter accuracy, and sensitivity to idle baseline. Do not label RTL static power estimates or `V × I` guesses as observed energy.

No board reboot/JTAG-ownership conflicting with Linux, destructive descriptor fault or new official t10k TEST run is authorized by this protocol.

## 6. CPU/software comparison contract

Compare the **same** frozen checkpoint, raw input encoder, 26 logical steps, integer/packed semantics and deterministic output policy against an explicitly specified CPU software implementation, preferably the project's accepted independent exact integer/packed oracle. Record host CPU model, ISA/core count, clock/governor, threading, Python/native implementation, compiler versions and timer.

Publish **at least two named endpoints** rather than a single unexplained `FPGA speedup`: (a) CPU compute/inference core loop (preloaded operands, analogous scope), and (b) CPU full 784-byte image-to-class inference with stated data preparation and result handling. Compare with the correspondingly named FPGA endpoints and state unavoidable hardware/software architectural asymmetries. Do not compare a host batch including model initialization against a warmed FPGA PL-only dispatch or conflate A53 scheduling with purely PL execution.

## 7. Proposed P08-A sequence and stop gates

| Stage | Deliverable | Required gate |
| --- | --- | --- |
| **P08-A1 (this document)** | Source audit, metric definitions, repeat/correctness plan, raw evidence/telemetry scope, frozen-file separation | Review and explicit user acceptance; text-only branch changes, native regression/CI source checks; **no P08 physical acceptance** |
| P08-A2 | **IN PROGRESS:** A2.1 per-image sidecar, host parser and native tests implemented as a candidate; A2.2 per-tick source/dispatch instrumentation pending | User host/native/Vitis verification pending; no real KV260 timing claim |
| P08-A3 | Actual KV260 16-image pilot, then validation 1,024 × cold repeats with independent numerical proof and timestamp integrity | User-run physical PASS, raw immutable artifacts, measured timer/PL clocks, uncertainties |
| P08-A4 | **DEFERRED BY USER:** equipment/rail discovery and physical power/energy | Not part of current latency-only acceptance; restart only with explicit user direction |
| P08-A5 | Scope-matched CPU baseline, reproducible statistical reports and Track A P08-A acceptance closeout | User-accepted comparison and uncertainty; only then consider Track B |

**A1 completion criteria:** documentation reviewed, boundaries distinguish PL from PS and host, power hardware explicitly unverified, original journal/ELF/XSA/weights unchanged, candidate branch diff documentation-only, local native test commands given, and GitHub CI status recorded if available. **A1 cannot be labeled ACCEPTED until the user checks it.** A2 is intentionally not started in this changeset.

## 8. Reproduction, safety and evidence pointers

Authoritative references: `LOIHI_TWIN_ROADMAP.md` P08-A, `docs/P07_A_FINAL_PHYSICAL_ACCEPTANCE.md`, `docs/P07_A4_3_4_FINAL_CANONICAL_TEST_PLAN.md`, `docs/P03_PS_AUTONOMOUS_APPLICATION.md`, `docs/P05_2I_ACCEPTANCE.md`, and the source files in section 2. The accepted P07-A merge is `d31df0b`; P08-A1 documentation is deliberately separate.

Local review from `~/Git/Thesis` (protect uncommitted changes first):

```bash
git status --short
git fetch origin
git switch agent/v3-p08-a-physical-baseline
git pull --ff-only origin agent/v3-p08-a-physical-baseline
git diff --name-status origin/main...HEAD
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
PYTHONPATH="$PWD/src" python -m pytest -q tests/test_p07_a4_official.py tests/test_p07_a4_fault.py
```

All physical acceptance and P08 measurements remain **NOT RUN** until the user explicitly runs and verifies them under JTAG-only bare-metal ownership.
