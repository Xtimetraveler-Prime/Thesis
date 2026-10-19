# P08-A3.2.3 — User-reported Pair 2 KV260 latency measurements

**State:** PAIR 2 REVERSED-ORDER A2.2 → A2.1 PHYSICAL PAIR USER-ATTESTED PASS; PAIR 3 NOT RUN.
These are user-provided terminal results; raw binary evidence and exact paired-report JSON path have not been independently inspected here.

## Physical population and acceptance

Same frozen 1,024 original-order TRAIN-derived validation images, last selected full-trace frame index 1023. Reported distributions use the **1,023 ordinary frames** only. Official MNIST TEST not rerun. Power/energy deferred.
Each independently executed variant passed the original P07 numerical neural oracle and timing checks; paired output reported `Neural verification: PASS` and `Timing integrity: PASS_SINGLE_PAIR`.
Pair 2 A2.2 independently passed all physical success markers, `script_exit_status=0`, and five raw evidence SHA256 checks.
Pair 2 A2.2 physical evidence directory: `/home/dna/Thesis_Evidence/p08_a3_2_pair2_A2_2_20261019T010354Z`.
Pair 2 A2.1 evidence directory and original Pair 2 JSON report location: **not supplied**, must be identified from actual local output.
Both firmware A53 timer frequencies reported 99,999,001 Hz, not the separate PL dispatch clock.

## Exact paired report, times in ms

| Metric | A2.1 service | A2.2 service | Matched-frame A2.2 − A2.1 |
|---|---:|---:|---:|
| Median | 35.6946 | 35.7163 | **+0.0254** |
| P95 nearest rank | 41.9578 | 41.9317 | +0.0827 |
| Min | 27.8364 | 27.7999 | −0.0428 |
| Max | 48.7927 | 48.8713 | +0.0909 |
| Sample stdev | 3.3940 | 3.3940 | 0.0255 |

Paired median **+25.4 µs** is approximately **0.071%** of the A2.1 median, a descriptive ratio and not a confidence interval. The difference of the two separate medians is +21.7 µs and **must not** be substituted for the actual matched-frame median of +25.4 µs. The delta distribution includes negative individual values. No causal timer-instruction overhead is identifiable from these two physically separate runs.

## First versus second pair

| Pair | Actual firmware execution order | Median A2.1 ms | Median A2.2 ms | Median matched difference µs | P95 matched difference µs |
|---|---|---:|---:|---:|---:|
| 1 | A2.1 → A2.2 | 35.7023 | 35.7234 | +16.8 | +74.4 |
| 2 | A2.2 → A2.1 | 35.6946 | 35.7163 | +25.4 | +82.7 |

Both pairs show a positive median even after reversed run order; the **8.6 µs** between-pair change is not by itself an identified order/thermal effect. The A53 frame-service interval includes CPU-side encoder, MMIO, scheduler and readback costs; do not interpret it as isolated PL compute. FPGA PL cycle counters have a separate, not-yet-calibrated clock.

## Remaining actions

Preserve the two earlier pairs' raw evidence and JSON unchanged. Complete **Pair 3 A2.1 → A2.2**, each in its own dedicated rebooted bare-metal JTAG-only KV260 session, using new no-overwrite evidence directories and the original frozen first1024 TRAIN-validation stage. Recheck full 1,024 original P07 packed neural results plus selected 26×42 trace and firmware-specific timing CRCs; compare only after both acceptances. Then aggregate the three real paired reports offline with `scripts/p08_a3_2_repeat_check.py` (does not access hardware). Three repeats of the same 1,023 ordinary images **do not** create 3,069 independent images. Power remains deferred.

See [first-pair physical report](P08_A3_2_2_PHYSICAL_RESULTS.md) and [three-pair protocol](P08_A3_2_3_REPEATED_LATENCY_PROTOCOL.md).
