# P03.2c handoff — close the full A53 page/resident/dispatch smoke

> **Completed/accepted 2026-10-11:** The user independently ran the full
> FPD128 A53 smoke and the strict mailbox verifier passed (438272 bytes,
> resident `config[0]=0x14001000`, one completed HLS dispatch, all
> error/status checks clean). This handoff remains as reproducible
> test instructions and archival pre-acceptance planning. See
> [P03_2C_ACCEPTANCE.md](P03_2C_ACCEPTANCE.md). P03.3 is now active.


**Prepared:** 2026-10-11  
**Hardware gate:** not yet independently run  
**Prerequisite physically passed:** standalone four-register read-only A53
diagnostic on the corrected 128-bit FPD + SmartConnect-to-32-bit design.  
**Branch:** `agent/v3-p03-autonomous-runtime`; no merge permitted until
explicit approval.

This document is an exact next-step companion to
[`P03_2C_MMIO_ROOT_CAUSE_AND_FIX.md`](P03_2C_MMIO_ROOT_CAUSE_AND_FIX.md).

## Acceptance vs. preparation

The read-only test checked only ID, VERSION, CAPABILITIES and a temporary
unmapped diagnostic signature. P03.2c additionally requires proof that
the Cortex-A53 can **write** MMIO control registers to drive the
page/dispatch/resident-memory logic, that the PL paging path can read
actual DDR backing data, that the resident-memory debug path returns a
known configuration word, and that the HLS engine completes one
no-event dispatch without error.

The full smoke uses the same MMIO base `0xA4000000` and fixed
`p03_mmio.h` header. It **must** be built against the fixed XSA of the
corrected **128-bit FPD/SmartConnect** candidate, **not** against the
previous accepted 32-bit FPD XSA nor the LPD diagnostic XSA.

## Recorded golden values from the deterministic fixture generator

- DDR backing record: `0x40000000`, size `0x80000` (512 KiB).
- DDR result mailbox: `0x43FF0000`, size 64 bytes.
- Page transfer: 438,272 bytes, 1,712 read bursts, zero write bursts.
- Resident configuration: `config[0]` must match `fixture/manifest.json`
  (value generated from the frozen P03 sample, not hardcoded here).
- Dispatch: one completed HLS dispatch of context 0, with no current
  events/packets; both dispatch and global error statuses must be clean.
- Full A53 mailbox magic: `0x50333243` (different from the
  read-only diagnostic's `0x50335244`).
- Full smoke pass result: `0x600D600D`.

The 64-byte result is verified by
`scripts/p03_2c_verify_mailbox.py` using the generated manifest. An
ELF launch alone or a populated mailbox alone is **not** a pass.

## One-time development-PC setup

On the same development PC that routed/programmed the successful
FPD128 candidate, preserve its exact reports directory.

```bash
cd ~/Git/Thesis
git switch agent/v3-p03-autonomous-runtime
git pull --ff-only origin agent/v3-p03-autonomous-runtime
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

python -m pytest -q \
  tests/test_p03_2c_full_smoke_candidate.py \
  tests/test_p03_2c_smoke_contract.py \
  tests/test_p03_2c_a53_readonly.py

# Set this to the exact successful *FPD128* routed output, not a new build:
export P03_DIAG_REPORTS="$(ls -dt "$PWD"/vivado/build/p03_2c_fpd128_route_*/reports | head -1)"
export P03_XSA="$P03_DIAG_REPORTS/p03_2_ps_mmio.xsa"
export P03_2C_EXPECTED_XSA_SHA="$(sha256sum "$P03_XSA" | awk '{print $1}')"
export P03_2C_SMOKE_CANDIDATE=1
export P03_2C_APP_NAME=p03_2c_smoke
export P03_2C_SOURCE_FILE=p03_2c_smoke.c
export P03_2C_READONLY_MMIO_BASE=0xA4000000
export P03_2C_BUILD_DIR="$PWD/vivado/build/p03_2c_fullsmoke_fpd128_$(date -u +%Y%m%dT%H%M%SZ)"

grep -E '^p03_hpm0_data_width_bits=|^p03_hpm0_transport=|^p03_ps_mmio_master=|^p03_mmio_base=' \
  "$P03_DIAG_REPORTS/p03_2_post_route_metrics.txt"
bash scripts/build_p03_2c_smoke.sh 2>&1 | tee /tmp/v3_p03_2c_fullsmoke_build.log
```

Expected build PASS marker:

```text
PASS: P03.2c candidate full A53 smoke build gate completed (physical acceptance pending).
```

The builder explicitly requires a fresh isolated directory and the
matching XSA fingerprint, and does not alter the previously frozen
P03.2b smoke build path.

## Physical board verification

With `hw_server` active, **reboot the KV260** to allow normal firmware
initialization of PS clocks and DDR, then issue from the PC (PuTTY is not
needed):

```bash
set -o pipefail
export P03_2C_FULL_EVIDENCE_DIR="/tmp/v3_p03_2c_fullsmoke_$(date -u +%Y%m%dT%H%M%SZ)"
bash scripts/run_p03_2c_full_smoke.sh "$P03_2C_FULL_EVIDENCE_DIR" \
  2>&1 | tee /tmp/v3_p03_2c_fullsmoke_console.log
cat "$P03_2C_FULL_EVIDENCE_DIR/verify.log"
```

The runner verifies the **live** PS FPD HPM0 width is 128 bits,
validates the routed PS/PL width and topology metrics, provisions
the accepted DDR fixture, programs the matching .bit/.ltx, launches
the A53 ELF over XSDB, retrieves the DDR mailbox, and validates it
against the fixture's manifest.

**Caution:** this test stops the A53/Linux execution context,
overwrites the project-designated 512 KiB DDR fixture and 64-byte mailbox
region, and writes page/debug/dispatch MMIO commands. It is not a
non-invasive Linux test. **Reboot the KV260 after it finishes**, including
on failure. Do not resume the halted Linux instance.

Expected full physical PASS markers:

```text
PASS: P03.2c backing record provisioned and mailbox cleared by physical readback
PASS: P03.2c mailbox verified id=0x4C543302 capabilities=0x0001031F page_bytes=438272 ...
P03_2C_FULL_SMOKE_VERIFY_EXIT=0
PASS: P03.2c full A53 physical page/resident/dispatch smoke (independent review pending)
```

Preserve/upload `ps_width.log`, `program.log`, `a53_run.log`,
`verify.log`, `artifact_identity.txt` and
`p03_2c_full_smoke_mailbox.bin`. The previous four-register read-only
pass log should remain in its **separate** evidence directory.

## Failure classification

| Observation | Meaning / next action |
|---|---|
| PS FPD width is not 128 | Stop; candidate PS/PL boot contract not met |
| DDR provision/readback fails | Debug DDR/JTAG/fixture ownership, not MMIO alone |
| ID or VERSION fails | Reconfirm programmed bitstream and PS width; preserve ILA evidence |
| Page timeout or error | Inspect page command, page walker, HP0/DDRx, PL reset, and counters |
| Page bytes/bursts mismatch | Inspect exact transfer boundaries and ABI assumptions |
| Resident config mismatch | Inspect debug Port-B arbiter, resident-memory read and layout |
| Dispatch timeout or nonzero errors | Inspect HLS control handshakes, reset and status paths |
| PASS mailbox but other physical evidence absent | Incomplete acceptance; collect identity and run logs |

After independent full-smoke PASS, decide whether to retain the temporary
diagnostic signature/ILAs or route a clean P03.2 final shell; record a
separate clean-shell evidence fingerprint if needed. Only then request
P03.2c/P03.2 acceptance and proceed to P03.3 implementation.

## Remaining P03 phases after this handoff

P03.3 implements a standalone Cortex-A53 scheduler/router/barrier
runtime, including page replacement, cross-core packet transfer and
cache ownership. P03.4 tests the frozen 7-timestep/35-dispatch
five-logical-core, three-resident-slot workload *without a PC in the
algorithmic loop*. P03.5 tests 100 board-local timesteps and requires
normalized agreement with the frozen Python/v2 architectural boundary.

Nothing in the four-register read-only pass, nor the full P03.2c smoke
alone, proves those later milestones.
