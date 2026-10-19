# P08-A3.1 — User-attested numerical physical latency measurements

**Recorded 2026-10-18 from the user's physical KV260 A3.1 console/JSON extraction.** These values are a **16-image feasibility pilot**, not an accepted statistical 1,024-image baseline. The underlying raw files have not been mounted in this tool environment; the displayed numbers are user-provided and preserved verbatim.

## Provenance and exact accepted context

- Real board: KV260, frozen P03.2c XSA SHA256 `52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`, unchanged core0 master and P07 oracle.
- A2.2 experimental A53 ELF SHA256 `87cf5fc4fe37d9d053a3c365db8ae9fdc7e782857612f273835cf5e611aba361`.
- User-local read-only source directory: `/home/dna/Thesis_Evidence/p08_a3_1_pilot_20261018T203342Z`.
- Expected source for numerical values: `p08_a3_1_verified_pilot.json`, emitted **after** `P07_A4_2C_PHYSICAL_ALL_OUTPUTS_EXACT=1`, selected 26×42 trace exact, complete `P08ALAT1` and `P08TCK02` CRC/checksum/counter validations, and `P08_A3_1_FULL_PHYSICAL_GATE_PASS=1` (console success output supplied by user).
- Samples: first **16 distinct TRAIN-derived held-out validation** images; 26 logical timesteps each. Selected full trace is image index 0; other 15 are the standard 10-output readback. The official MNIST TEST data are **not** rerun in P08.
- A53 timer frequency **as reported by firmware** `CNTFRQ_EL0 = 99,999,001 Hz`. Conversion used `time_seconds = CNTVCT_tick_delta / 99999001`; this is a firmware-configured counter rate, **not** an independently calibrated stopwatch.
- FPGA's raw per-image `pl_dispatch_cycles` are an *independent PL clock domain*; no verified exact physical PL frequency supplied. **Do not** convert them using 99,999,001 Hz or describe them as seconds.

## Captured aggregate image service latencies (exact user display)

| Metric | Instrumented duration |
| --- | ---: |
| Median, 16 images | **35.4432 ms** |
| Minimum, 16 images | **31.2682 ms** |
| Maximum, 16 images | **41.2175 ms** |
| Median, 15 ordinary images (excluding full-trace image) | **35.6239 ms** |
| Selected full 26×42 trace image (index 0) | **33.8655 ms** |

The selected trace image is **faster than** the median ordinary image in this particular sample. This does **not** demonstrate that full trace readback reduces latency: input-dependent spike/event differences and small sample size confound that comparison. No per-image software reference, trace-overhead differential, statistical confidence interval or instrumented-vs-uninstrumented physical comparison has yet been made.

## Per-logical-timestep **median** software intervals (exact user display)

| Stage | A53 duration median |
| --- | ---: |
| Event encoding | **499.955 µs** |
| Event-bank append and MMIO | **312.458 µs** |
| Dispatch MMIO setup + PL execution/wait + poll | **70.011 µs** |
| Packet routing | **54.631 µs** |
| Output trace readback | **33.030 µs** |
| Barrier callback | **0.940 µs** |

These are **distinct medians across 416 step records**, not aligned per-tick additive values. Do not sum this table to get image latency. Other operations are outside these six callback spans (initial master reset/page-in, scheduler gaps, final record commit, counters and sidecar writes between images). The **dispatch wrapper includes A53 MMIO/poll and PL elapsed time**, and is **not** pure HLS neuron execution.

The primary *observed engineering bottlenecks in the pilot* are host-side event encoding and event-bank appends, rather than barrier callback time. This is a reason to *measure* carefully before making any hardware optimization. It does not by itself prove that altering the encoder will preserve neural timing/weights, nor does it justify changing accepted frozen P03/P07 behavior during A3.2.

## Raw per-image FPGA dispatch counters (exact user display)

| Original frame | PL dispatch cycles |
| ---: | ---: |
| 0 | 94,751 |
| 1 | 200,328 |
| 2 | 122,761 |
| 3 | 142,606 |
| 4 | 173,048 |
| 5 | 167,972 |
| 6 | 125,166 |
| 7 | 148,446 |
| 8 | 266,333 |
| 9 | 244,107 |
| 10 | 255,144 |
| 11 | 259,724 |
| 12 | 189,097 |
| 13 | 178,689 |
| 14 | 99,627 |
| 15 | 153,184 |

These are **26-timestep sums of a custom FPGA dispatch counter** for each image, not A53 virtual timer ticks. The 1024-run host verifier must continue to correlate each per-tick PL counter with that image-level value and with the independent frozen neural journal.

## Research implications and A3.2 work plan

1. Preserve immutable A3.1 raw binary evidence, manifest hashes, console log and JSON. The values above are **user-reported displays** until independently re-read from the raw files; do not fabricate additional per-image or per-tick measurements.
2. A3.2.1: design and native-test **paired same-image latency analysis** of the pinned A2.1 (coarse image timing) and A2.2 (per-tick timing) using the frozen 1,024 original-order TRAIN-validation prefix with selected trace index 1023. **Independent original P07 packed-oracle verification on BOTH physical runs is required before comparing latency.**
3. A3.2.2: create a separately consent-gated, source-hash-pinned physical 1,024-image runner for each *already built* ELF. The A2.1 SHA256 is `fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0`; the A2.2 SHA256 is `87cf5fc4fe37d9d053a3c365db8ae9fdc7e782857612f273835cf5e611aba361`. The experiment must not rebuild or modify firmware/bitstream and must not rerun official MNIST TEST.
4. A3.2.3: **proposed** three separately rebooted runs per firmware (same 1,024 frames per run, not 3,072 independent images), with explicit run order and no-overwrite evidence captures; report baseline distribution, frame-paired differences, p95 and run-to-run variability. Instrumentation overhead estimate describes the *change in entire A53 service scope* between firmware versions, not just seven timer reads.
5. No PL-clock-in-seconds claim without reading accepted routed clock/RTL timing sources and independently verifying the hardware counter domain. **Power/energy explicitly deferred.**

Timing methods and external documentation: [P08-A2.2 Timing Methods](P08_A2_2_TIMING_METHODS.md); [A3.1 original physical acceptance](P08_A3_1_PHYSICAL_ACCEPTANCE.md); primary Arm CNTVCT/CNTFRQ specifications and AMD UG1399 as cited in the former.
