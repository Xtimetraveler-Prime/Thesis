# P08-A5 — Remaining latency-only closeout criteria after completed A3 physical study

**State:** P08-A3.2.3 physical six-session repeated A53 system-service baseline user-attested complete; **P08-A5 NOT YET EXECUTED and whole P08-A NOT CLOSED**. Physical power/energy P08-A4 expressly deferred by user.

## Evidence already available (no new JTAG requirement)

The accepted [A3.2.3 final physical report](P08_A3_2_3_FINAL_PHYSICAL_REPEAT_RESULTS.md) summarizes six user-operated real KV260 inference runs across three firmware-matched pairs, the same first1024 TRAIN-derived validation image identities (1,023 ordinary + one selected trace frame). Reported ordinary frame A53 service medians:

| Pair | A2.1 ms | A2.2 ms | Frame-paired median A2.2 − A2.1 µs |
|---|---:|---:|---:|
| 1 | 35.7023 | 35.7234 | 16.840 |
| 2 | 35.6946 | 35.7163 | 25.400 |
| 3 | 35.6696 | 35.7220 | 29.710 |

Across the 3 pair-level medians: mean 23.984 µs, sample SD 6.551 µs; fixed-image three-repetition delta-range median 24.730 µs and p95 73.541 µs. There is no FPGA PL-only calibrated compute-time-in-seconds measurement and **no CPU performance result** yet.

## Required before full P08-A acceptance (original P08-A1 contract §§6–7)

1. **Preserve/file-seal A3 evidence.** Confirm the final original `p08_a3_2_three_pair_summary_*.json` exists, archive it with the three source paired reports and six individual physical evidence directories to a durable untracked storage location; execute read-only SHA256 checks of all `physical_output_sha256.txt`, include `sha256sum` of final report; confirm `P08_A3_2_3_THREE_PAIRED_LATENCY_AGGREGATION_PASS=1` from an offline revalidation report if the original terminal output was not preserved. Do not overwrite older files. No KV260 access required.
2. **CPU preloaded compute-loop endpoint.** Use the unchanged P03/P07 exact integer/packed software reference, original frozen weights/encoder and all 26 logical ticks with **preloaded** canonical operands; verify bit-exact physical/oracle output for accepted TRAIN validation images; benchmark per-frame core-only compute duration using a clearly named host monotonic timer after warmup. Record the host's CPU model, architecture/ISA, clock/power governor, threads/affinity, Python vs native code path and version/toolchain. **Do not compare its duration to PL cycles in seconds** until actual achieved PL clock and the hardware cycle-counter scope are separately established.
3. **CPU full image-to-class endpoint.** Benchmark full original 784-byte raw image input through accepted event encoder + same 26-step integer/packed recurrence, routing and final 10-class output policy on the same 1024 validation sample IDs, using explicit preparation/output boundaries. Verify class/spike parity; report per-image latency distributions separately from the CPU compute-only endpoint. Match the board's **full A53 image-service** measurement boundary as far as feasible and explicitly itemize unavoidable PS/PL, MMIO/page, initialization and trace differences; a single unqualified `FPGA speedup` is **not acceptable**.
4. **PL clock and scope qualification.** Preserve per-frame PL dispatch raw counter histograms. Independently inspect the accepted routed Vivado clock/counter implementation and correct hardware clock frequency before converting to seconds; if independent physical achieved-clock verification is absent, report PL cycles only and explicitly withhold pure-PL seconds/speedup assertions. Likewise treat Arm `CNTFRQ_EL0` (reported 99,999,001 Hz in first two runs) as a firmware-programmed rate absent external calibration.
5. **Final uncertainty and written acceptance.** A clear table must separately report 1,023 ordinary validation-image distributions and full-trace frame, between-pair and within-image repeatability (only **3** independent paired hardware runs), CPU run-to-run variation, experimental metric scope, sample reuse/no independent pseudo-replication, image-stage/source hashes, exact firmware/FPGA provenance and uncertainty limitations. Report optional steady-state throughput only with a correctly defined measured interval (not `1/median` advertised as real throughput). Cite original P07 official TEST result only as frozen historical accuracy; **do not rerun official TEST**. Obtain explicit user approval to label the latency-only P08-A milestone accepted and to merge the draft PR.

### Scope decision

**Recommended:** Complete A5 offline CPU references and final comparison with honest PL-clock caveat; do *not* repeat six accepted KV260 physical sessions merely for more data. `P08-A4` remains deferred, not reopened. Alternatively the user can explicitly authorize narrowing P08-A to a standalone physical A53 latency study (with CPU baseline omitted and PL seconds unclaimed), but this **changes the original closeout criteria** and should be documented as a scope change rather than falsely marking A5 complete.

Primary authority: [Original P08-A1 measurement contract](P08_A1_MEASUREMENT_CONTRACT.md) §§3–7; [P08-A3 final repeated measurements](P08_A3_2_3_FINAL_PHYSICAL_REPEAT_RESULTS.md); [P08-A3.2.3 protocol](P08_A3_2_3_REPEATED_LATENCY_PROTOCOL.md).
