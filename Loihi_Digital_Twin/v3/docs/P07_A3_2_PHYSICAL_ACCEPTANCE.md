# P07-A3.2 — Physical KV260 inference on frozen MNIST validation diagnostics

**Status:** **CLOSED / USER-ACCEPTED 2026-10-17**.
**Branch:** `agent/v3-p07-a-784-axon-streaming`; **NOT merged**.
**Official canonical MNIST TEST:** **SEALED / NOT READ**.

## Physical run and artifact identities (user-supplied)

The user executed the independently precommitted P07-A3.1
`p07-a3-validation16-probe-v1` training-derived 16-image
validation diagnostic batch in source-index selection order. A53
ran the batch autonomously on the actual KV260 PS/PL and the
A3 oracle scorer reloaded the **canonical training-only** IDX
source, checked source-ID/image/label correspondence, required
full A2 physical trace oracle agreement, then scored the
validation labels.

```text
P07_A2_MAILBOX_STATUS=0x600D600D
P07_A2_KV260_STATUS=TERMINAL_SUCCESS_UNVERIFIED_NUMERICS
P07_A2_PHYSICAL_TRACES_EXACT=1
P07_A2_GATE_FULL_PHYSICAL_PASS=1
P07_A3_PHYSICAL_VALIDATION_EXACT=1
P07_A3_VALIDATION_ACCURACY=15/16
P07_A3_VALIDATION_SILENT=0/16
P07_A3_OFFICIAL_TEST=SEALED
P07_A3_PHYSICAL_GATE_PASS=1
```

**Evidence directory on user's PC**:
`/tmp/v3_p07_a3_val16_20261017T132017`.

| Raw evidence file | User-reported SHA-256 |
|---|---|
| `p07_a2_mailbox.bin` | `f467427dbb6c35a6dae0e1b94f291c278e84f337ce8a9b0d38ddce546404f6d9` |
| `physical_identity.txt` | `9c08df041973206f6bc3b85bd87ba75bbb0988d123a99df185e2ae9d90cac733` |
| `verify.log` | `4c2c03c69dee2573b2fd402bb1500fff46c82786915b20c27926b08dc153f01b` |

The actual binary mailbox is on the user's machine and **not
uploaded** to the GitHub repo. This acceptance reflects the
user-supplied original terminal logs and digests, not an
independent assistant-side reread of the physical binary.

## Per-sample validation truth/prediction

| Frame | Canonical TRAIN source index | Validation label | Physical prediction | Silent |
|---:|---:|---:|---:|---:|
| 0 | 37384 | 1 | 1 | no |
| 1 | 27347 | 2 | 2 | no |
| 2 | 20178 | 1 | 1 | no |
| 3 | 28529 | 7 | 7 | no |
| 4 | 4643 | 7 | 7 | no |
| 5 | 28406 | 3 | 3 | no |
| 6 | 30272 | 4 | 4 | no |
| 7 | 42072 | 6 | 6 | no |
| 8 | 32157 | 3 | **9** | no |
| 9 | 47739 | 0 | 0 | no |
| 10 | 49129 | 8 | 8 | no |
| 11 | 4181 | 0 | 0 | no |
| 12 | 41994 | 3 | 3 | no |
| 13 | 52041 | 3 | 3 | no |
| 14 | 36488 | 3 | 3 | no |
| 15 | 29056 | 0 | 0 | no |

**Result: 15/16 correct = 93.75% on the PRESELECTED DIAGNOSTIC
validation subset; 0/16 all-silent.** The only incorrect
classification (frame 8, label 3 predicted 9) was numerically
**identical** between physical PL and frozen software oracle.
It is thus a **model classification error, not a hardware
arithmetic/scheduler divergence**.

The physical verifier checked all **16 × 26 tick** output
spike flags, class counts and routed event totals; frame 0
also supplied the complete **26 × 42 × 256-bit** per-compartment
hardware trace and exactly matched the independent P06 packed
replay. Exact class-label scoring independently checked image
and label hashes against canonical original TRAIN-only IDX.

## Limits of this acceptance

- The predeclared first 16 images of the seeded 10k validation order
  are a diagnostic, **not** the 10k population's measured accuracy
  or an independent official test accuracy.
- The existing 94.39% 10k **train-derived validation** score was
  reported during model selection/training; this small physical
  diagnostic is not an independent generalization estimate.
- Only one full 26×42 trace is stored per physical batch (frame 0);
  all-frame output spikes/routes are checked.
- No repeat/cold-reboot reproducibility, batch-boundary stress,
  runtime-error recovery, performance, energy or power is shown.
- Neither full official TEST, Intel Loihi physical performance,
  Track B, nor multi-core functional scaling are claimed.

**A3.2 ACCEPTED. Next submilestone: A3.3** prespecifies a
larger, unrevised validation-only diagnostic population and
repeatability/restart checks before any new results. Keep
`main` unchanged until explicit user merge approval.
