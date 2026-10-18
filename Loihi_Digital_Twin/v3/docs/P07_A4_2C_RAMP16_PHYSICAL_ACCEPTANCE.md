# P07-A4.2c — First persistent A53 physical run, ramp16

**CLOSED / USER-ACCEPTED 2026-10-17 — first 16-image synthetic
pilot only.** A4.2c **overall is NOT closed**: original-order
128 TRAIN-derived validation, cold restart repeats and larger
persistent workload remain pending. The official canonical
MNIST t10k TEST remains **SEALED / NOT READ**.

The user executed the *new* physically independent standalone
Cortex-A53 persistent application in one KV260 JTAG-controlled
bare-metal batch: **16 synthetic ramp input images**,
**one A53 ELF launch**, and FPGA P03.2c core invoked for
26 timesteps per image. This differs from A2's one-launch-per-
16-image protocol by reading the new `P07A4P01`
DDR-resident raw-image stream, reconstructing P07A1
ingress and committing `P07A4R01` CRC-protected
96-byte results to a 1MiB journal without per-image host
commands.

**User-supplied terminal evidence, verbatim:**

```text
P07-A4.2c standalone persistent A53 ELF downloaded; starting ONE dataset run
P07_A4_2C_JOURNAL_STATUS=0x600D600D
P07_A4_2C_JOURNAL=/tmp/v3_p07_a4_ramp16_20261017T191755/p07_a4_journal_1m.bin
P07_A4_2C_TRACE=/tmp/v3_p07_a4_ramp16_20261017T191755/p07_a4_trace_64k.bin
P07_A4_2C_KV260_STATUS=TERMINAL_SUCCESS_UNVERIFIED_NUMERICS
P07_A4_2C_PHYSICAL_FRAMES=16
P07_A4_2C_PHYSICAL_ALL_OUTPUTS_EXACT=1
P07_A4_2C_PHYSICAL_SELECTED_TRACE_26X42_EXACT=1
P07_A4_2C_PHYSICAL_SEALED_VALIDATION_GATE_PASS=1
P07_A4_OFFICIAL_TEST=SEALED
P07_A4_2C_PHYSICAL_EVIDENCE_DIR=/tmp/v3_p07_a4_ramp16_20261017T191755
P07_A4_2C_FULL_PHYSICAL_GATE_PASS=1
REBOOT THE KV260; do not resume the halted operating system.
```

**Preserved original evidence directory on user's PC**:
`/tmp/v3_p07_a4_ramp16_20261017T191755`.
The terminal proves first-pilot accepted application completion,
16 parsed terminal frame records, all **26×10** physical
output spike flags exact against independent frozen P03 packed
replay on every image, exact readout and route/drop/event
totals, and **26×42** full compartment trace exact for
selected index 0. The actual binary journal, trace, staging
readback and original logs remain on the user's machine and
have **not** been uploaded / independently re-read through
GitHub. Do not invent their hashes. Firmware pinned to
the independently user-Vitis-accepted A4.2b ELF
SHA256 `dcba738e0d9e78a6bf9fb61fba5ff23dcd1da68f8903fb1dbd33952b3dca38fb`
and P03.2c accepted XSA SHA256
`52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`.

## Strict limits

- The ramp16 images are **synthetic and repeated**, so
  this is an execution/provenance/numerical gate, **not**
  MNIST test or validation classification accuracy.
- One 16-image dataset in one A53 launch does **not**
  yet prove restart repeatability, 128 distinct image
  correctness, 10,000-image sustained throughput, error
  recovery in physical execution or actual latency/power.
- Only **one selected** 26×42 compartment trace was captured
  and all 16 per-tick output-spike streams. Do not describe
  per-compartment physical readout for every image.
- The official t10k TEST remains sealed and model weights,
  readout rule, P03 bitstream and numerical oracle remain frozen.

**Next acceptance stage:** persistent one-launch **128**
distinct canonical TRAIN-derived validation examples,
with independent current software oracle and direct
comparison to A3.3's **eight** accepted physical 16-frame
primary mailboxes; compare the selected image full trace
where the two protocols select the same source. Then
prespecify cold-start repeat and larger validation-only
stress before authorizing any official TEST unseal.
