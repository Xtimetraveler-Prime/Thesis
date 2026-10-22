# P07-B.4j — isolated accepted-P03 PL programming and reset release

**Development status (2026-10-22):** next physical milestone prepared following the
successful P07-B.4i real XSDB four-core-accounting and FPD/LPD width diagnostic.
**No KV260 programming has been performed for B4j; this is a candidate runner.**
Maintain PR #49 in draft; no merge. Do not alter accepted P03, Track A, P06/B2
or the sealed official B2 TEST.

## Physical evidence that unlocked this checkpoint

After reboot and `sudo xmutil unloadapp`, the operator ran the revised
`xsdb vivado/p07_b4i_stop_and_width_gate.tcl
DEDICATED_DISCARD_LINUX_APPROVED tcp:127.0.0.1:3121` on a real KV260.
The PC output showed A53 #0 stopped, A53 #1 stopped, A53 #2/#3 each
explicitly powered down, XSDB PSU selected, FPD raw `0x00000A00`,
LPD raw `0x00000200`, and completion marker
`P07_B4I_A53_ALL_CORES_ACCOUNTED_AND_PSWIDTH128_GATE_PASS=1`.
**This is one user-reported real physical stop/width PASS, not a
bitstream-programming or A53/ELF inference PASS.** See
`P07_B4I_2026_10_22_PHYSICAL_TAKEOVER_WIDTH_PASS_LEDGER.json`.
The original physical XSDB log remains on the operator PC, with original
contents not independently fetched into the repo.

The old P03/Track A acceptance provides the exact Vivado command and VIO
reset-release marker for programming the accepted P03.2c shell.

## What B4j does and why it is separate

B4j is a **dedicated, intentionally disruptive JTAG-only experiment** with
an expressly narrower privilege than `p07_b4i_physical_pilot.py --mode execute`:
- Pin the accepted P03 XSA/BIT/LTX SHA, routed FPD128 metrics, B4i genuine
  ELF/map and unchanged source staging with the existing B4i offline preflight.
  The ELF is verified as an artifact, **never downloaded** by B4j.
- Re-run the already-proven **real** B4i stop/width gate in this **new boot**.
  Core #0 must stop; #1/#2/#3 must stop or explicitly report powered-down.
  Both raw PS width registers must exactly match accepted 128-bit values.
  Read the full transcript back through `verify_takeover_log` before programming.
- Program the accepted SHA-pinned P03.2c bitstream and probes using only
  original `vivado/p03_2c_program_bitstream.tcl`, which verifies the VIO
  PL reset release. Require Vivado process exit zero and its unique exact
  `PASS: P03.2c accepted PS-MMIO bitstream programmed and PL reset released`
  marker.
- Save all raw logs and a separate success receipt in an absolutely new
  evidence directory outside Thesis. Reboot after the attempt, success or failure.

**Not performed by B4j:** DDR read/write, P02 core staging, `dow`, standalone
A53 execution, mailbox capture, packet route/page/dispatch, official B2 TEST,
trained 27-core inference or numerical comparison.

B4j still stops Linux and programs PL; it is **not** safe to run against a
Linux session you intend to keep or another process using that PL bitstream.
`xmutil unloadapp` alone does not grant A53/DDR ownership. This shell-only
stage avoids touching the unresolved low DDR `[0x0,0x23A40)` and mailbox
`0x43FF0000`, but the later standalone A53 `dow` remains NO-GO until
its own full execution-memory and firmware/PM ownership gate is accepted.

## PC-only new development checkpoint (safe now)

After syncing the branch and activating `.venv-p08`:

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p07-b-scaled-physical-inference
git pull --ff-only origin agent/v3-p07-b-scaled-physical-inference
git rev-parse HEAD
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b4i_physical_pilot.py \
  tests/test_p07_b4j_shell_program_pilot.py

source /home/dna/Vivado/2025.2/Vitis/settings64.sh
export PATH="/home/dna/Vivado/2025.2/gnu/aarch64/lin/aarch64-none/bin:$PATH"
export P07_B4I_BUILD_DIR="/home/dna/p07_b4i_build_20261022T161058Z"
export P07_B4I_REPORTS="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports"

python scripts/p07_b4j_shell_program_pilot.py \
  --mode preflight \
  --build "$P07_B4I_BUILD_DIR" \
  --reports "$P07_B4I_REPORTS"
```

Expected preflight-only markers:
`P07_B4J_OFFLINE_ACCEPTED_P03_B4I_ARTIFACT_PREFLIGHT_PASS=1`,
`P07_B4J_OFFLINE_ONLY_NO_HARDWARE_ACCESS=1` and
`P07_B4J_A53_DDR_ELF_INFERENCE_AUTHORIZED=0`.

## Future physical shell-program pilot (separately operator approved)

The `--mode execute` phase is implemented but must be separately authorized
by the board operator for **a new dedicated JTAG session**. It refuses absent
`--dedicated-jtag-owner YES`, `--cpu-takeover-approved YES`,
`--pl-program-approved YES`, `--reboot-recovery-approved YES`,
or a fresh absolute evidence directory outside the repository.

**No handwritten operator note, recovery-note file, or `--recovery-note`
argument is required.** The four explicit approval flags express the
operator's decision to allow this disruptive session. They do not by
themselves prove low-DDR exclusivity; B4j explicitly does not touch DDR
or launch the A53 executable. Plan to reboot afterwards and never
resume the halted Linux instance.

A future successful run will produce:
- `ps_width.log` with all-core state admission and original raw PS width;
- `program.log` with the original Vivado P03 VIO reset-release PASS;
- `provenance.json` with accepted artifact hashes and session intent (no operator note);
- `result.txt` with
  `P07_B4J_PHYSICAL_SHELL_PROGRAM_VIO_RESET_PASS=1`,
  `P07_B4J_A53_ELF_DOWNLOADED=0` and
  `P07_B4J_DDR_MAILBOX_TOUCHED=0`.

The next *different* milestone after B4j is the read-only standalone A53
`dow`/DDR-mailbox admission, which needs an independently accepted
low-DDR/firmware ownership and recovery plan. B4j success does **not**
authorize that step.

### Operator workflow simplification (2026-10-22)

The B4j and B4i scripts have been updated at operator request to **remove
handwritten operator/recovery-note requirements permanently from this
project's physical test workflow**. They retain concise explicit approval
flags, immutable artifact preflights, fresh evidence directories, actual
hardware checks, and the reboot-after-takeover requirement. A console
PASS or approval flag is not evidence of firmware/low-DDR exclusivity.

After the offline preflight and a fresh KV260 reboot/`xmutil unloadapp`,
the physical B4j runner accepts:

```bash
export P07_B4J_EVIDENCE="$HOME/Thesis_Evidence/p07_b4j_physical_$(date -u +%Y%m%dT%H%M%SZ)"
python scripts/p07_b4j_shell_program_pilot.py \
  --mode execute \
  --build "$P07_B4I_BUILD_DIR" \
  --reports "$P07_B4I_REPORTS" \
  --evidence "$P07_B4J_EVIDENCE" \
  --dedicated-jtag-owner YES \
  --cpu-takeover-approved YES \
  --pl-program-approved YES \
  --reboot-recovery-approved YES
```

Only run if the four approvals are true for that session. This intentionally
halts A53/Linux and programs PL, but never issues `dow` or accesses the
DDR mailbox. Preserve `ps_width.log`, `program.log`, `result.txt` and
`provenance.json`. Reboot on success or failure.
