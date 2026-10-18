# P07-A4.2c — Persistent 128-image independent reboot repeat accepted

**2026-10-17 — USER-PROVIDED PHYSICAL ACCEPTANCE.**
The persistent A53 128-image TRAIN-derived validation primary and independent
reboot repeat are **CLOSED**. **Overall A4.2c remains OPEN**, pending
precommitted larger-scale distinct validation and physical fault-handling
acceptance. Canonical official MNIST t10k **TEST remains SEALED**.

The user independently executed the existing strict physical
`scripts/p07_a4_2_restart_verify.py`, which required original logs,
actual DDR readbacks, accepted frozen A53 ELF/XSA/source identities,
the old eight P07-A3.3 physical mailboxes, complete per-image
`P07A4R01` journal, and full trace byte equality.

**Original user terminal evidence (verbatim):**

```text
P07_A4_2C_128_REPORT=/tmp/v3_p07_a4_val128_repeat_20261017T194315/p07_a4_2c_128_cold_repeat_acceptance.json
P07_A4_2C_128_PRIMARY_ORACLE_LOGS_EXACT=1
P07_A4_2C_128_PRIMARY_PREVIOUS_PHYSICAL_EXACT=128/128
P07_A4_2C_128_PRIMARY_ELF_XSA_STAGE_PINNED=1
P07_A4_2C_128_REPEAT_ORACLE_LOGS_EXACT=1
P07_A4_2C_128_REPEAT_PREVIOUS_PHYSICAL_EXACT=128/128
P07_A4_2C_128_PHYSICAL_LAUNCHES=2/2
P07_A4_2C_128_TOTAL_HARDWARE_IMAGE_EXECUTIONS=256
P07_A4_2C_128_UNIQUE_VALIDATION_IMAGES=128
P07_A4_2C_128_JOURNAL_1M_BYTE_EXACT=1
P07_A4_2C_128_TRACE_64K_BYTE_EXACT=1
P07_A4_2C_128_COLD_REPEAT_ALL_BYTES_EXACT=1
P07_A4_2C_128_PHYSICAL_RESTART_GATE_PASS=1
P07_A4_OFFICIAL_TEST=SEALED
```

Evidence directory on user's PC:
`/tmp/v3_p07_a4_val128_repeat_20261017T194315`, with original
read-only acceptance JSON. The primary evidence directory is
referred to by the original accepted report but was not included
in the user-pasted output. Do not invent a directory or hashes
for raw binary evidence that hasn't been provided in this chat.

**Interpretation:** Exactly **128 unique** original-order TRAIN-derived
validation images were executed twice after independent user-declared
bare-metal KV260 reboots, **256 physical image executions** but **not
256 unique images**. The user-reported checker saw both
runs' hardware software-oracle PASS logs, exact equivalence against
the eight original physical A3.3 primary mailboxes, full 1MiB
result-journal equality and complete 64KiB selected compartment
trace equality, on the identical accepted A53 ELF and FPGA.

This does **not** prove correctness over arbitrary 10k images,
unexpected interruption/failure physical telemetry, P08 energy/
latency, or the sealed official t10k TEST accuracy. It does
not attest a reboot cryptographically; independent reboot is
an operator-executed procedure supported by separate run evidence.

**Next accepted engineering goal:** precommit original-order
**first 1024 distinct TRAIN-derived validation source indices**
and trace index **1023** for a longer *single autonomous
persistent A53 launch*. Freeze separate primary and cold-reboot
repeat; check complete journals, all output bits/routes/ties,
selected last-image 26×42 trace, and input/source-ID provenance.
No training, hardware arithmetic, weight, encoder, ELF or
official test population changes. Additionally prepare
physical pre-dispatch fault-injection acceptance before TEST
unseal. See `P07_A4_2C_VAL1024_PROTOCOL.md`.
