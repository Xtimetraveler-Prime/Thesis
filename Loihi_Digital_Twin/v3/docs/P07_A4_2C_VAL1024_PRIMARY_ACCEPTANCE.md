# P07-A4.2c — Long-running one-launch validation1024 primary: accepted

**User independently verified primary physical KV260 run — 2026-10-17.**
**Status:** first1024 persistent physical PRIMARY complete; independent
cold reboot REPEAT not yet executed/accepted. Overall A4.2c still
requires repeat, plus separate physical fail-closed negative test.
Canonical MNIST t10k **TEST SEALED**.

This run used one user-Vitis-accepted persistent Cortex-A53 standalone ELF,
one unchanged P03.2c bitstream and the frozen first **1,024 distinct
TRAIN-derived validation samples** in existing seeded original order.
Full compartment trace selected *last* image index 1023, with
26×10 physical output spike flags and routing for **every** image.
The original first128 subset is preserved unchanged.

**Exact user-pasted physical markers:**

```text
PASS: P03.2c accepted PS-MMIO bitstream programmed and PL reset released
P07-A4.2c standalone persistent A53 ELF downloaded; starting ONE dataset run
P07_A4_2C_JOURNAL_STATUS=0x600D600D
P07_A4_2C_JOURNAL=/tmp/v3_p07_a4_val1024_primary_20261017T200134/p07_a4_journal_1m.bin
P07_A4_2C_TRACE=/tmp/v3_p07_a4_val1024_primary_20261017T200134/p07_a4_trace_64k.bin
P07_A4_2C_KV260_STATUS=TERMINAL_SUCCESS_UNVERIFIED_NUMERICS
P07_A4_2C_PHYSICAL_FRAMES=1024
P07_A4_2C_PHYSICAL_ALL_OUTPUTS_EXACT=1
P07_A4_2C_PHYSICAL_SELECTED_TRACE_26X42_EXACT=1
P07_A4_2C_PHYSICAL_SEALED_VALIDATION_GATE_PASS=1
P07_A4_OFFICIAL_TEST=SEALED
P07_A4_2C_PHYSICAL_EVIDENCE_DIR=/tmp/v3_p07_a4_val1024_primary_20261017T200134
P07_A4_2C_FULL_PHYSICAL_GATE_PASS=1
REBOOT THE KV260; do not resume the halted operating system.
```

**Separate independent strict physical evidence preflight (user-pasted):**

```text
P07_A4_2C_1024_UNIQUE_TRAIN_VALIDATION=1024
P07_A4_2C_1024_SELECTED_FINAL_TRACE_INDEX=1023
P07_A4_2C_1024_PRIMARY_ORACLE_LOGS_EXACT=1
P07_A4_2C_1024_PRIMARY_DDR_PROVENANCE_EXACT=1
P07_A4_2C_1024_PRIMARY_PHYSICAL_GATE_PASS=1
P07_A4_2C_1024_COLD_REPEAT=NOT_RUN
P07_A4_OFFICIAL_TEST=SEALED
```

**Physical evidence:** `/tmp/v3_p07_a4_val1024_primary_20261017T200134`
on user's PC; raw logs, full 1MiB journal, full selected 64KiB trace,
six XSDB binary staging readbacks, per-run physical identity hashes
remain there, not copied into GitHub.

**Interpretation:** The single A53 execution completed all 1024
ordered frames, and every recorded 26×10 output sequence, class/readout,
external event/routing counters and selected image 1023 full
26×42 compartment trace match the frozen independent software oracle.
The separate evidence gate verified saved physical log flags,
input/firmware identity and staging binary readbacks. This is an
actual long-run hardware result, not 1024 independent compartment
traces, and is *not* official 10000 MNIST TEST accuracy.

**Next:** A separate KV260 reboot into JTAG-only bare-metal,
run same unmodified 1024-stage, accepted ELF/XSA/FPGA in fresh
repeat evidence directory. Reject incomplete or failed run.
Require full 1MiB journal and selected full 64KiB trace
byte-for-byte identical plus all original separate physical
gate logs/binaries. Protocol: `P07_A4_2C_VAL1024_PROTOCOL.md`.
This closes the sustained-repeat sub-gate **only after observed PASS**.
The separate prespecified physical fail-closed pre-dispatch corruption
gate is still needed to close *overall* A4.2c. Do not unseal TEST.
