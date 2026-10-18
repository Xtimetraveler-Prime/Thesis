# P07-A4.2c — Precommitted PHYSICAL fail-closed negative gate

**Precommitted 2026-10-17 BEFORE any deliberate physical fault injection.
PHYSICAL KV260 NEGATIVE RUN COMPLETE / USER-INDEPENDENT ACCEPTED
2026-10-17, `0xDEAD0001`, ZERO completed frames/output/trace.**
Exact original terminal results and limits are preserved in
`P07_A_FINAL_PHYSICAL_ACCEPTANCE.md`.
This experiment is separate from the **accepted** persistent 16,
128 and 1024 TRAIN-validation inference experiments. Complete the
user-prespecified 1024 **cold-reboot repeat** and strict
`P07_A4_2C_1024_RESTART_GATE_PASS=1` **first**.
Only after the second accepted 1024 physical run may this
separately approved synthetic-only negative test close the
remaining A4.2c physical failure-admission requirement.
Canonical MNIST official t10k **TEST REMAINS SEALED**.

## Objective and frozen fault stimulus

**Intentionally invalidate ONE reserved descriptor word in physically
staged PS DDR after original successful byte-exact provision/readbacks
and before the unchanged persistent A53 firmware is started.**
This must cause a fail-closed *input validation* terminal, never
a successful inference or result. Exact conditions:

- Original source: unmodified accepted first **16 repeated synthetic
  RAMP uint8 images** and original `P07A4P01` descriptor,
  trace=0, same frozen mapping/model/ELF/FPGA identities.
  The on-disk prepared stage must remain **unchanged**.
- JTAG stage exact original 256B descriptor at `0x43FE0000`,
  raw images, immutable P02 master, mapping, initialized 1MiB
  result journal and initialized zero 64KiB trace. Read back
  all six regions byte-identically before injecting any fault.
- **One and only one physical mutation**:
  reserved descriptor bytes `[144:148]`, address
  `0x43FE0090`, change `00 00 00 00` to
  `01 00 00 00`, using XSDB `mwr`. Read back the
  entire descriptor before and after and require that
  exact difference. No trained weights, pixel input,
  immutable master, A53 ELF, accepted bitstream or any
  accepted physical evidence file is changed.
- Independent KV260 bare-metal JTAG-only reboot before
  this negative launch, and after the launch. Explicit
  **TWO** opt-ins for DDR overwrite and intentional
  fault injection. If either absent, refuse before XSDB.
- Launch the exact user-Vitis-accepted standalone persistent
  A53 ELF SHA256
  `dcba738e0d9e78a6bf9fb61fba5ff23dcd1da68f8903fb1dbd33952b3dca38fb`.
  In `p07_a4_board.c`, `load_dataset` validates
  the descriptor before verifying immutable model or
  dispatching core0, rejects the nonzero reserved word;
  `record_failed(1u)` writes expected status
  **`0xDEAD0001`** to the 256B journal header.
- Expect `P07A4R01` header CRC and exact fields:
  schema v1, header bytes 256, status `0xDEAD0001`,
  **requested count=1** (safe error fallback because
  dataset was intentionally *NOT validated*),
  **completed=0**, first fault `0xFFFFFFFF` because
  this was a pre-frame admission failure, bound CRC=0,
  selected trace=0, flags=0, all reserved header
  bytes zero; **all remaining journal 1MiB bytes ZERO**
  and selected trace 64KiB ZERO.
- Failure is the **expected NEGATIVE test outcome**, not
  valid inference. The wrapper MUST NOT print or accept
  a `P07_A4_2C_FULL_PHYSICAL_GATE_PASS=1` normal
  numerical inference marker for this negative attempt.
  Any `0x600D600D`, any output record, nonzero
  trace, another error code, stale artifact, malformed
  CRC or failure to terminate is a **negative gate FAIL**.

No deliberate high-current hardware stress, no PL memory-map
corruption, no Linux concurrent DDR ownership and no attempt to
turn a failed ordinary positive run into a valid negative run.

## Native offline checks (safe)

After pulling the branch, from
`~/Git/Thesis/Loihi_Digital_Twin/v3` with
`.venv-p08` active:

```bash
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_a4_fault.py \
  tests/test_p07_a4_val1024_gate.py \
  tests/test_p07_a4_restart.py

bash -n scripts/run_p07_a4_fault_physical.sh

export P07_A4_BUILD_DIR=/tmp/v3_p07_a4_persistent_20261017T190943
export P07_A4_FAULT_STAGE_DIR="$PWD/artifacts/p07_a4_2a_ramp16_v1"
export P07_A4_VAL1024_STAGE_DIR="$PWD/artifacts/p07_a4_2c_val1024_first_v1"
export P07_A4_VAL1024_PRIMARY_EVIDENCE=/tmp/v3_p07_a4_val1024_primary_20261017T200134
# Must be set to the ACTUAL independently verified 1024 cold-repeat directory:
export P07_A4_VAL1024_REPEAT_EVIDENCE=/tmp/REPLACE_WITH_ACCEPTED_val1024_repeat_DIR
export P03_2C_EXPECTED_XSA_SHA=52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f

PYTHONPATH="$PWD/src" python scripts/p07_a4_2_check.py \
  --stage-dir "$P07_A4_FAULT_STAGE_DIR"
```

Preserve `P03_DIAG_REPORTS` from accepted routed
P03.2c physical artifacts. Existing synthetic ramp16
stage may be reused (do not recreate or overwrite).
**Do not run the negative hardware test unless BOTH
the accepted 1024 physical cold repeat and its strict
aggregate verifier have already passed**.

## Physical negative launch — separate independent reboot

After accepting the 1024 repeat, boot the KV260 into
the same dedicated JTAG-only bare-metal state. Linux
must not co-own `0x40000000..0x43FFFFFF`:

```bash
export P07_A4_FAULT_RUN_DIR="/tmp/v3_p07_a4_fail_closed_$(date +%Y%m%dT%H%M%S)"
export P07_A4_CONFIRM_KV260_DDR_OVERWRITE=YES
export P07_A4_CONFIRM_DESTRUCTIVE_FAULT_INJECTION=YES

bash scripts/run_p07_a4_fault_physical.sh
```

The physical script first reruns the entire accepted
**1024-image PRIMARY + independently rebooted REPEAT**
original XSDB-evidence verifier and requires
`P07_A4_2C_1024_RESTART_GATE_PASS=1` BEFORE any board
access. Set the actual `P07_A4_VAL1024_REPEAT_EVIDENCE`
directory from the accepted user repeat; the illustrative
`/tmp/REPLACE_WITH_ACCEPTED_...` above is a placeholder
and must not be used literally. This cannot be bypassed
simply by writing a success marker to a log.
It then performs all accepted ELF/XSA/source
checks and original XSDB staging/provision readbacks,
programs the original FPGA, **then** makes exactly the
single descriptor-word modification and captures
original before/after readbacks. The original A53
ELF is downloaded/launched ONCE and should refuse
before one frame, yielding `0xDEAD0001`. It retains
the full 1MiB physical failure journal, zero 64KiB
trace, all six original provision readbacks and
all initial original logs in a **NEW** evidence dir.

User must reboot the KV260 after this run even on
error. The verifier is read-only and may be rerun:

```bash
PYTHONPATH="$PWD/src" python scripts/p07_a4_2_fault_verify.py \
  --stage-dir "$P07_A4_FAULT_STAGE_DIR" \
  --evidence-dir "$P07_A4_FAULT_RUN_DIR" \
  --report "$P07_A4_FAULT_RUN_DIR/p07_a4_2c_fault_acceptance.json"
```

The report destination is exclusively created, not
overwritten. Expected **NEGATIVE** physical markers:

```text
P07_A4_2C_JOURNAL_STATUS=0xDEAD0001
P07_A4_2C_KV260_STATUS=TERMINAL_FAILURE_INSPECT_JOURNAL
P07_A4_2C_DESCRIPTOR_ONE_WORD_PHYSICAL_FAULT_CONFIRMED=1
P07_A4_2C_PHYSICAL_DESCRIPTOR_MUTATION_ONE_WORD_EXACT=1
P07_A4_2C_PHYSICAL_ORIGINAL_PROVISION_EXACT=1
P07_A4_2C_PHYSICAL_INFERENCE_FRAMES_COMPLETED=0
P07_A4_2C_PHYSICAL_RESULT_BODY_ALL_ZERO=1
P07_A4_2C_PHYSICAL_TRACE_ALL_ZERO=1
P07_A4_2C_PHYSICAL_FAIL_CLOSED_GATE_PASS=1
P07_A4_2C_NEGATIVE_TEST_PASS=1
P07_A4_OFFICIAL_TEST=SEALED
```

**The preceding physical NEGATIVE targets were all
observed by the user on 2026-10-17.** A53
`0xDEAD0001`, one physically mutated reserved
descriptor 32-bit word verified exactly, the
original source provisioning unchanged, all zero
output/journal body/trace and **zero completed
images** were verified in the independent
read-only physical negative gate.

Original full failure evidence on user's PC:
`/tmp/v3_p07_a4_fail_closed_20261017T204554`.
User-attested `P07_A4_2C_PHYSICAL_FAIL_CLOSED_GATE_PASS=1`
and `P07_A4_2C_NEGATIVE_TEST_PASS=1`.
This event **CLOSED A4.2c**; the official TEST
was still SEALED at the time this synthetic-only
fault experiment completed. After the subsequently
explicitly authorized A4.3 unseal, A4.4's full
physical 10000-image original-order benchmark
also passed. See `P07_A_FINAL_PHYSICAL_ACCEPTANCE.md`.
The 64KiB trace was all zero here because there
was no admitted valid image for inference.
