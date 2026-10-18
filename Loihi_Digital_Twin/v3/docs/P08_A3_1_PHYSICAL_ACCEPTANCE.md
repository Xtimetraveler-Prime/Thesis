# P08-A3.1 — User-attested KV260 physical latency pilot acceptance

**Recorded:** 2026-10-18.  
**Gate:** **PHYSICAL NUMERICAL CORRECTNESS + LATENCY TELEMETRY CAPTURE PASS** (16-frame first-TRAIN-validation pilot, user-executed).  
**Limits:** this is a functionality/feasibility acceptance, **not yet** a repeated 1,024-frame statistical latency baseline, a standalone neural PL-only timing measurement, a profiler-overhead measurement, or a power/energy measurement.

## Accepted evidence provenance

The user posted the successful terminal output of `scripts/run_p08_a3_1_pilot.sh` using the experimental A2.2 A53 candidate. This is an **attestation from a real board run supplied in chat**, not an independently downloaded and inspected copy of all raw evidence. Preserve the immutable original evidence files; do not regenerate or overwrite them.

- **Physical evidence directory (user PC):** `/home/dna/Thesis_Evidence/p08_a3_1_pilot_20261018T203342Z`
- **Frozen P03.2c routed XSA SHA256 (prior user-build check):** `52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`
- **User-built and SHA-attested A2.2 experimental ELF:** `/tmp/v3_p08_a2_2_build_20261018T200133Z/vitis_workspace/p08_a2_2_board.elf`
- **A2.2 ELF SHA256:** `87cf5fc4fe37d9d053a3c365db8ae9fdc7e782857612f273835cf5e611aba361`
- **Pilot sample selection:** exactly the original-order first 16 distinct held-out **MNIST TRAIN-derived validation** frames, 26 logical timesteps each (25 event-input ticks + one drain tick).
- **Original MNIST t10k TEST:** excluded from this pilot; the separate historical P07 full TEST acceptance remains unchanged.
- **Power/energy:** deferred by user.

### User-attested terminal PASS markers (verbatim)

```text
P07_A4_2C_JOURNAL_STATUS=0x600D600D
P08_A2_2_IMAGE_TIMING_STATUS=0x600D600D
P08_A2_2_TICK_TIMING_STATUS=0x600D600D
P08_A2_2_KV260_STATUS=TERMINAL_ALL_THREE_SUCCESS_UNVERIFIED_NUMERICS
P07_A4_2C_PHYSICAL_FRAMES=16
P07_A4_2C_PHYSICAL_ALL_OUTPUTS_EXACT=1
P07_A4_2C_PHYSICAL_SELECTED_TRACE_26X42_EXACT=1
P07_A4_2C_PHYSICAL_SEALED_VALIDATION_GATE_PASS=1
P07_A4_OFFICIAL_TEST=SEALED
P08_A3_1_P07_INDEPENDENT_PACKED_ORACLE_PASS=1
P08_A3_1_PER_TICK_LATENCY_CROSSCHECK_PASS=1
P08_A3_1_16FRAME_PHYSICAL_PILOT_PASS=1
P08_A3_1_1024FRAME_BASELINE=NOT_RUN
P08_A3_1_POWER=DEFERRED
P08_A3_1_PHYSICAL_EVIDENCE_DIR=/home/dna/Thesis_Evidence/p08_a3_1_pilot_20261018T203342Z
P08_A3_1_FULL_PHYSICAL_GATE_PASS=1
```

The intermediate XSDB marker `TERMINAL_ALL_THREE_SUCCESS_UNVERIFIED_NUMERICS` means **only** that the three successful terminals were observed. The separate `p07_a4_2_verify.py` packed-oracle and `p08_a3_1_verify.py` per-tick consistency passes are the grounds for accepting numerical and timing telemetry integrity.

## What is established

1. The independent frozen packed oracle matched the user's original 16-frame physical P07 journal; output spikes/counts/classes, event ingress, route and final-drain values passed the accepted original verification procedure.
2. The designated 26 × 42 selected full neural-state/accumulator/spike trace matched the accepted packed oracle.
3. The experimental A2.2 board firmware produced **both** CRC/version/count-checked A53 timing sidecars, with ordered samples within per-image intervals, correct 26 tick IDs per image, input encoder/packet consistency, and per-tick PL dispatch cycle summation matching P03 image counters. This shows timing **capture/readback feasibility on real hardware**, not calibration of the FPGA clock or direct neuron-only compute latency.
4. The original P07 accepted results and P03 HLS code remain unmodified; instrumentation overhead in A2.2 remains an unmeasured difference relative to A2.1 or the frozen P07 build.

## What remains open and what to inspect next

**Do not invent latency numbers.** The terminal log reports pass markers but does **not** include numerical measured latency values. Request or inspect the on-disk physical report:

```text
/home/dna/Thesis_Evidence/p08_a3_1_pilot_20261018T203342Z/p08_a3_1_verified_pilot.json
```

It stores: firmware-reported `CNTFRQ_EL0`, 16 per-image A53 service ticks and seconds, min/max/median seconds, ordinary 15-frame median, selected-trace frame service seconds, 26-tick PL hardware cycle sums, per-tick stage median seconds, original neural and timing evidence SHA256 hashes, and explicit evidence qualification.

Recommended initial checks on host:

```bash
RUN=/home/dna/Thesis_Evidence/p08_a3_1_pilot_20261018T203342Z
cat "$RUN/attempt_exit_status.txt"   # expect script_exit_status=0
sha256sum --check "$RUN/physical_output_sha256.txt"
python -m json.tool "$RUN/p08_a3_1_verified_pilot.json"
```

**Board safety:** user must reboot the KV260 out of the JTAG-only halted state after the run. Preserve immutable raw output and initial staging, including every SHA manifest, before running further physical tests. The `official_mnist_test=SEALED` marker refers to *the workload for this P08 pilot* and does not contradict the historical P07 test acceptance.

## Next research gate (proposal, NOT YET RUN)

**P08-A3.2:** separately validate a 1,024-frame first-TRAIN-validation physical latency baseline (precommitted trace frame 1023), compare matched A2.1 / A2.2 builds in isolated cold-boot JTAG-only runs, quantify profiling perturbation and per-stage latency variability, document the exact **A53 timer domain** separately from PL dispatch-cycle hardware time, and report per-image distribution (median/p95 etc.) plus run-to-run uncertainty. Predeclare the number of repeats before starting (earlier conceptual proposal: **3 × 1,024** for each firmware); do not treat repeated passes over 1,024 images as distinct independent sample populations. No power measurement and no rerun of the P07 official TEST.

The existing 16-frame A3.1 runner is intentionally fixed to first16 and **must not** simply be pointed at a 1,024-frame stage. Design, native-test and independently verify separate A3.2 hardware/replay/evidence gates before running new physical batches.

See [A3.1 methodology](P08_A3_1_PHYSICAL_PILOT_PROTOCOL.md) and [A2.2 timing methods and sources](P08_A2_2_TIMING_METHODS.md).
