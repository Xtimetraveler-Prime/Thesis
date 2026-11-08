# P08-B4.5 original unprotected full1024 authenticate-once: 2026-11-05 physical FAILURE triage

**Status: PHYSICAL NO-GO; no diagnosis of actual fault ordinal/code
until saved mailbox content is decoded.** Operator reported the new
original `once` 1024 JTAG run failed with a genuine A53
`0xDEAD0823` TERMINAL FAILURE. This is NOT a host timeout,
not a missing JTAG connection and not a 1024/1024 accepted performance
result. The user transcript includes an exact prior six DDR original
source byte readback PASS, strict B4i A53 halt and FPD/LPD128
PASS (from full user context), original accepted P03 programming,
four distinct zero-region physical readbacks, genuine newly SHA-pinned
A53 ELF download, physical mailbox and three full 256KiB sidecar
captures. The actual saved failure mailbox *content*, failing frame,
and A53 fault code were **not provided**. No 27-backup postrun readback
was captured because this genuine A53 terminal failure correctly
aborted the XSDB runner **before** that optional later step.

Operator's exact original evidence location:

```text
/home/dna/Thesis_Evidence/p08_b45_perf_once_full1024_physical_20261105T172141Z/
```

Observed final markers:

```text
P08_B45_PERF1024_PHYSICAL_TERMINAL_MAILBOX_CAPTURED_256B=1
P08_B45_PERF1024_REAL_1024_JOURNAL_AND_TIMING_SIDECARS_PHYSICAL_CAPTURED=1
P08_B45_PERF1024_JTAG_ATTEMPT_FAILED_REBOOT_REQUIRED=1
P08-B4.5 PERF1024: real A53 reported a TERMINAL FAILURE.
P08_B45_PERF_FULL1024_NO_GO=hardware command failed (exit 1)
```

**DO NOT:** try a new physical full1024 run, relax the error code,
interpret the four zero readback PASS as a neural inference PASS,
assume which frame failed, automatically launch the unchecked variant,
launch another XSDB inspector against a live halted Linux A53, or
continue using the previously halted Linux session. **Power-cycle
the KV260 after the failed attempt.** The accepted independent
physical first16 `once` and `unchecked` pilots remain valid.

## New PC-only original saved-binary postmortem

No board, XSDB, serial, Vivado or network accessed. The user can
run this in the Ubuntu **PC VS Code terminal**, not PuTTY:

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p08-b45-full1024-failure-triage
git pull --ff-only origin agent/v3-p08-b45-full1024-failure-triage
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/scripts:$PWD/src" python3 -m pytest -q -rs \
 tests/test_p08_b45_full1024_failed_run_postmortem.py

export P08_B45_FAILED_FULL_RUN="$HOME/Thesis_Evidence/p08_b45_perf_once_full1024_physical_20261105T172141Z"
export P08_B45_ORIGINAL_FULL_ORACLE="$HOME/Thesis_Evidence/p08_b4_1_full1024_scalar_20261102T143900Z.json"
export P08_B45_FAILURE_REPORT="$HOME/Thesis_Evidence/p08_b45_failed_full1024_triage_$(date -u +%Y%m%dT%H%M%SZ).json"

test -s "$P08_B45_FAILED_FULL_RUN/performance1024_capture/mailbox_terminal_physical.bin" &&
test -s "$P08_B45_FAILED_FULL_RUN/performance1024_capture/journal1024_physical.bin" &&
test -s "$P08_B45_FAILED_FULL_RUN/performance1024_capture/timing1024_physical.bin" &&
test -s "$P08_B45_FAILED_FULL_RUN/performance1024_capture/reset_profile1024_physical.bin" &&
test -s "$P08_B45_ORIGINAL_FULL_ORACLE" &&
test ! -e "$P08_B45_FAILURE_REPORT" &&
echo P08_B45_FAILURE_RAW_FILES_PRESENT=1

PYTHONPATH="$PWD/scripts:$PWD/src" python3 \
 scripts/p08_b45_full1024_failed_run_postmortem.py \
 --evidence "$P08_B45_FAILED_FULL_RUN" \
 --oracle "$P08_B45_ORIGINAL_FULL_ORACLE" \
 --out "$P08_B45_FAILURE_REPORT"

sha256sum "$P08_B45_FAILURE_REPORT"
python3 -m json.tool "$P08_B45_FAILURE_REPORT"
```

The first step in decoding is terminal `mailbox_terminal_physical.bin`
(64 little-endian uint32 words). Original unprotected A53
`B23_FAIL=0xDEAD0823` at word2, image ordinal at word3, exact
`fault` at word4, count of fully completed images at word5.
A sentinel ordinal `0xFFFFFFFF` means failure before the first
image (codes 100..105). On per-image error, ordinal is 0..1023,
code 200..214. Do not assume it is fault 201/208/210 merely
because the 16-image pilot previously passed.

The new analyzer ONLY reads captured local binary files and original
frozen `7e564d188651aeabdc284328ea65705bcb0b5571468b9f70d5dcacaa3f5493b8`
full1024 scalar oracle. It separately counts contiguous CRC+DONE
256B valid journal, timing and reset profile records, requires each
to cover the A53-reported completed-frame count, allows one
partially committed frame in the failed ordinal, checks original
full-26tick scalar/FNV/predictions and all six timing phases for
completed frames, and checks mode-specific context reset counters
and elapsed reset-within-phase0. It produces a fresh never-overwritten
JSON report. If any prefix row differs, it FAILS CLOSED and names
the frame; this is useful evidence, not permission to rewrite
expected SHA or original model. No postrun 27-backup proof exists
for this failed attempt; it never fabricates it.

**Required operator follow-up:** provide terminal stdout from
postmortem plus fault/index/completed prefix and report SHA. Only
then determine whether any source change is justified. If the
actual code is due to a repeatable known logic error, prepare a
separate reviewed fix, new native tests and fresh genuine ELF/map
before any **separately approved** retry. Keep the failed
physical evidence immutable. No PR merge until explicit approval.
