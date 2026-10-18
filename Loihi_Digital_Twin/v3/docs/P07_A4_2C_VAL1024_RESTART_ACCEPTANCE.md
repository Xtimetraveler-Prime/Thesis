# P07-A4.2c — Physical first1024 TRAIN-validation restart acceptance

**USER-ACCEPTED 2026-10-17.** The sustained **1024-image
persistent inference + independent cold-reboot repeat sub-gate
is CLOSED**. **P07-A4.2c overall remains OPEN** pending the
separately precommitted synthetic physical fail-closed input
validation/fault telemetry gate. **Canonical MNIST TEST
remains SEALED / NOT READ.**

User-reported read-only `scripts/p07_a4_2_val1024_verify.py`
evaluated the full *original* physical evidence of one
primary and a separate independently rebooted repeat,
with unchanged accepted persistent A53 ELF, P03 FPGA
bitstream, 1024 distinct frozen TRAIN-derived validation
images, selected full 26×42 trace for final image 1023,
six original byte-exact DDR staging readbacks, per-run
FPGA/software oracle pass logs, and complete physical
journals and traces. The user supplied this exact terminal
evidence:

```text
P07_A4_2C_1024_REPORT=/tmp/v3_p07_a4_val1024_repeat_20261017T201021/p07_a4_2c_1024_physical_restart.json
P07_A4_2C_1024_UNIQUE_TRAIN_VALIDATION=1024
P07_A4_2C_1024_SELECTED_FINAL_TRACE_INDEX=1023
P07_A4_2C_1024_PRIMARY_ORACLE_LOGS_EXACT=1
P07_A4_2C_1024_PRIMARY_DDR_PROVENANCE_EXACT=1
P07_A4_2C_1024_PRIMARY_PHYSICAL_GATE_PASS=1
P07_A4_2C_1024_REPEAT_ORACLE_LOGS_EXACT=1
P07_A4_2C_1024_REPEAT_DDR_PROVENANCE_EXACT=1
P07_A4_2C_1024_PHYSICAL_LAUNCHES=2/2
P07_A4_2C_1024_HARDWARE_IMAGE_EXECUTIONS=2048
P07_A4_2C_1024_JOURNAL_1M_BYTE_EXACT=1
P07_A4_2C_1024_TRACE_64K_BYTE_EXACT=1
P07_A4_2C_1024_RESTART_GATE_PASS=1
P07_A4_OFFICIAL_TEST=SEALED
```

Accepted physical paths on user's PC:

- Primary: `/tmp/v3_p07_a4_val1024_primary_20261017T200134`.
- Repeat: `/tmp/v3_p07_a4_val1024_repeat_20261017T201021`.
- Original strict acceptance report:
  `/tmp/v3_p07_a4_val1024_repeat_20261017T201021/p07_a4_2c_1024_physical_restart.json`.

No raw JTAG binary evidence was uploaded to GitHub;
these are **user-attested original CLI results**. Do
not invent unseen per-artifact SHA256 values or assert
cryptographically verified independent reboots.

**Interpretation:** **2048 hardware image executions,
1024 distinct TRAIN-derived validation images**.
Both journal allocations (complete **1 MiB**) are
byte-identical; both selected last-frame (1023)
full-trace allocations (complete **64 KiB**) are
byte-identical. Each physical run's saved original
independent P03 software oracle and DDR provisioning/
staged artifact checks passed. This does **not** give
full 26×42 neural trace for every one of 1024 images:
only the **selected last frame**, plus complete
26×10 physical output spike flags and route summaries
for **each** image. No official independent TEST
accuracy has been measured; no 10000-image physical
run, power, or latency acceptance has occurred.

**Next required A4.2c step:** separate guarded
**synthetic ramp16 PRE-DISPATCH input corruption**
physical negative test, committed in advance in
`P07_A4_2C_FAIL_CLOSED_PROTOCOL.md`. This must use
the original accepted ELF and bitstream and a
disposable JTAG-owned DDR staging. Corrupt exactly
one reserved descriptor 32-bit word after all six
original staging readbacks; expect `0xDEAD0001`,
zero image completions, no results or trace, valid
failure journal/CRC. The negative physical test has
NOT YET BEEN RUN. A4.2c cannot close until it passes.

Once physical fail-closed acceptance is independently
verified, record closure of A4.2c, reaffirm 10k
original-order fixed test population, accept/lock
reduced full-trace sampling coverage, and ONLY
THEN separately authorize A4.3 canonical MNIST
TEST unsealing. No change to frozen weights, trained
model, encoder or readout is permitted.
