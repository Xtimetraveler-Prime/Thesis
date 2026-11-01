# P07-B.4i — guarded first physical A53 admission pilot (NOT trained inference)

**Status:** implementation prepared on the existing P07-B draft branch. **OFFLINE verification and genuine Vitis build required before a separately approved physical session.** No KV260 access, programming, A53 download, low-DDR takeover, or MNIST TEST opening is part of repository CI. Do not treat native CI as physical acceptance.

## Why this instead of more live-Linux XSDB probing?

On October 22 the operator read FPD/LPD via Linux BusyBox `devmem` at `0xFD615000=0x00000A00` and `0xFF419000=0x00000200` (both 128-bit). During that same Linux boot, `p07_b4g_ps_width_only.tcl` selected XSDB PSU and printed `0x00002560`/`0x00000512` (decoded 64-bit, also unexpectedly nonzero reserved bits). The existing P07-B4g B4c probe did not launch. The operator clarifies that PuTTY/Linux has historically hung under host JTAG operations **even during successful Track A runs**, so the hang alone is *not a new or conclusive system failure*. The disagreement is real, but its exact cause is unknown. Do not rewrite earlier ledgers to erase this distinction. Do not assert boot firmware changed.

Use the **accepted Track A standalone takeover** rather than relying on Linux remaining responsive under JTAG. Original successful sequences in `scripts/run_p07_a2_physical.sh`, `scripts/run_p07_a4_physical.sh`, P08 launchers:
1. explicit dedicated JTAG CPU/DDR ownership, normal recovery via reboot;
2. **halt A53 / inspect the live PS FPD and LPD register selectors** with original Track A `vivado/p03_2c_xsdb_ps_axi_width_diag.tcl` (this old script HALTS A53!);
3. require BOTH raw width values, not just an ambiguous printed selector;
4. program **exact accepted P03 FPD128** BIT+LTX using `vivado/p03_2c_program_bitstream.tcl` and assert reset-release marker;
5. download/run ONE new standalone A53 application and read a **physical DDR result mailbox**, as accepted P03.2c and Track A did;
6. independently verify mailbox contents on the PC; reboot after attempt and never resume prior Linux context.

This B4i pilot does **not** stage the 27 frozen B2 contexts, overwrite the full reserved P02 64MiB, execute neuron updates, dispatch HLS, or demonstrate trained inference. Its only intentional data-area write is the **64-byte mailbox at `0x43FF0000`**, plus ELF PT_LOAD segments downloaded using XSDB. It calls original P07-B4b read-only admission with inherited P03 adapter: width, identity, version, capabilities, idle status, zero pending. It leaves the accepted original P03/P05/Track A/B2 sources intact.

## Artifacts

- `software/p07/p07_b4i_readonly_mailbox_board.c`: new A53 identity and strict 16×u32/64-byte mailbox, cache flush, success/failure markers, idle WFE. No inference dispatch.
- `software/p07/build_p07_b4i.py` and `scripts/build_p07_b4i.sh`: clone *procedure*, not original accepted files, of the Vitis 2025.2 B4c genuine ELF + linker-generated map build. New workspace outside Thesis and exact accepted XSA/metrics required.
- `scripts/p07_b4i_physical_pilot.py`: default `--mode preflight` is **host-only**. Pins accepted XSA/BIT/LTX SHA, staged original C/header identity, accepted FPD128 route, genuine ELF + map + symbols, PT_LOAD and entry, protected 64MiB P02/MMIO overlap. Records low-DDR risk; *does not* prove ownership.
- `vivado/p07_b4i_xsdb_run.tcl`: **only under gated physical mode**; A53 stop + processor reset + physical 64-byte zero-mailbox overwrite/readback, `dow` ELF, `con`, polling and physical 64-byte result dump. Fails closed on wrong executable, incomplete result, wrong server.
- `scripts/p07_b4i_verify_mailbox.py`: strict 64-byte binary receipt; requires exact FPD raw `0xA00`, original ID `0x4C543302`, version `0x10000`, caps `0x1031F`, idle/zero pending, no inference permission, completion and pass words.
- `tests/test_p07_b4i_physical_pilot.py`, `.github/workflows/p07_b4i_native.yml`: native only, no board, intentional negative cases.

## First checkpoint — PC-only tests (safe NOW)

From VS Code Ubuntu/Linux on your PC (NOT KV260 PuTTY):

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p07-b-scaled-physical-inference
git pull --ff-only origin agent/v3-p07-b-scaled-physical-inference
git rev-parse HEAD
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python -m pytest -q -rs tests/test_p07_b4i_physical_pilot.py
PYTHONPATH="$PWD/src" python -m pytest -q -rs tests/test_p07_b4g_width_timeout_regression.py tests/test_p07_b4gh_readonly_pilot.py
```

Second command should report historical `22 passed`; the new B4i count depends on the latest tests. **Stop and send output for independent verification.**

## Second checkpoint — real Vitis build (PC ONLY, after native acceptance)

```bash
source /home/dna/Vivado/2025.2/Vitis/settings64.sh
export PATH="/home/dna/Vivado/2025.2/gnu/aarch64/lin/aarch64-none/bin:$PATH"
export P07_B4I_REPORTS="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports"
export P07_B4I_BUILD_DIR="$HOME/p07_b4i_build_$(date -u +%Y%m%dT%H%M%SZ)"
bash scripts/build_p07_b4i.sh
python scripts/p07_b4i_physical_pilot.py --mode preflight --build "$P07_B4I_BUILD_DIR" --reports "$P07_B4I_REPORTS"
```

Expected marker after a genuinely successful local build: `P07_B4I_REAL_VITIS_ELF_AND_MAP_BUILT=1`. After real artifact pin/layout gates: `P07_B4I_REAL_ARTIFACT_OFFLINE_PREFLIGHT_PASS=1` and `P07_B4I_OFFLINE_ONLY_NO_BOARD_ACCESS=1`. Report actual ELF entry, PT_LOAD span(s), real map and hashes. **If entry remains `0x0` and loads cross early DDR, NO automatic physical GO.** A dedicated bare-metal takeover does not itself prove all low DDR is exclusively safe.

## Physical pilot — designed, NOT authorized by these offline steps

The driver contains separately gated `--mode execute` and six independent explicit approvals for dedicated JTAG ownership, A53 takeover, *entire PT_LOAD low DDR exclusive ownership*, mailbox overwrite, accepted PL programming, and reboot/recovery. It requires a new evidence directory outside the repository, but **no handwritten operator/recovery note file**. Explicit flags do not themselves establish memory exclusivity. Missing information or nonmatching PS width **fails before programming**.

**Do not execute it yet.** A new, operator-approved physical session must first establish:
- The OS/Linux instance will be discarded; no CPU/Linux owner resumes afterward.
- The **specific ELF entry and every physical PT_LOAD span**, heap/stack and any early boot/low-DDR memory owner have been independently reconciled. Consent alone is not proof of memory exclusivity.
- The legacy mailbox `0x43FF0000` is safe to overwrite in that dedicated run and cache/MMU mapping is understood.
- Exact accepted P03 XSA/BIT/LTX provenance and matched FPD128 PS↔PL setup.
- JTAG server ownership, recovery power/reboot plan, saved evidence, and no sealed B2 TEST exposure.

Even after a physical pilot **PASS**, this is **read-only shell admission**, NOT P07-B 27-core numerical inference. Full B2 27-context physical parity remains separately blocked pending reset/provenance/scaling work. Preserve draft PR #49; no merge without user approval.


## 2026-10-22 historical Track A real ELF physical layout reconciliation

The operator recovered the precise P07-A4 physically accepted file at
`/tmp/v3_p07_a4_persistent_20261017T190943/vitis_workspace/p07_a4_board.elf`.
A fresh independent `sha256sum` matched the recorded P07-A4 acceptance SHA
`dcba738e0d9e78a6bf9fb61fba5ff23dcd1da68f8903fb1dbd33952b3dca38fb`.

Independent *actual user-local* `aarch64-none-elf-readelf -W -h -l` comparison:

| ELF | ELF entry | Physical PT_LOAD span, exclusive end | MemSiz | FileSiz |
|---|---|---|---:|---:|
| Accepted P07-A4 | 0x0 | [0x0,0x29D80) | 171392 | 0x13054 |
| Current P07-B.4i | 0x0 | [0x0,0x23A40) | 145984 | 0xE054 |

Both AArch64 ELF64 little-endian EXEC with one RWE LOAD starting at 0, and
their identical mapped section types include `.mmu_tbl*`, `.bss`,
`.heap`, and `.stack`. The B4i LOAD is a **strict subset** of the former
P07-A4 physical LOAD span, 25,408 bytes smaller. This **resolves the
layout-convention discrepancy**, not exclusivity of today's Linux/firmware
low-DDR owners. The source of the 64-bit *live Linux XSDB* readback remains
unresolved. B4i physical inference is still not accepted.

## Tightened physical gate following the real ELF comparison

B4i now uses new `vivado/p07_b4i_stop_and_width_gate.tcl` for the **first
destructive takeover step**, instead of calling the older P03 width
diagnostic directly. The old script catches and ignores `stop` errors; the
new B4i-only script demands four A53 target selections, a **successful
`stop` on A53 #0**, and a strict one-of-two result for secondary A53
#1/#2/#3: either `stop` succeeds, or XSDB gives the **exact** error string
`The core is powered down`. It neither powers on a sleeping core nor masks
other debugger errors. It disconnects on failure and refuses proceeding to
P03 programming unless both historical raw widths are read: FPD
`0x00000A00`, LPD `0x00000200`. No stop or powered-down report alone proves
boot-firmware/DDR ownership; this remains a separately operator-assessed
dedicated-session contract. It prints
`P07_B4I_A53_ALL_CORES_ACCOUNTED_AND_PSWIDTH128_GATE_PASS=1` only after
all four cores are accounted and both widths match. The Python driver
independently validates every exact transcript marker before programming.

A physical run deliberately discards the Linux instance, unlike a safe
in-place Linux accelerator operation. No original Track A/P03 sources or
user-built B4i ELF were changed by this enhancement; the user can reuse
the preflight-passing B4i ELF and exact SHA. The revised native synthetic
tests verify that the stop gate fails closed on a failed stop command.

**Do not equate an existing `xmutil unloadapp` with dedicated A53 ownership,
or set `--low-ddr-exclusive YES` merely because ELF LOAD spans match.**
Establish independent consent, backup, boot-firmware and exclusive CPU/DDR
ownership, and recovery policy before operator-triggered physical mode.

## First physical attempt: secondary A53 #1 powered down (2026-10-22)

After the operator rebooted KV260 and ran `sudo xmutil unloadapp`, the
first genuine B4i hardware stop/width diagnostic produced:

```text
P07_B4I_A53_0_STOP_COMMAND_PASS=1
P07_B4I_STOP_WIDTH_GATE_FAIL_REBOOT_REQUIRED=1
P07-B.4i stop failed for Cortex-A53 #1: The core is powered down
```

**Observed scope:** core #0 stop acknowledged; #1 reported powered down;
#2/#3 not checked; FPD/LPD XSDB registers not read; no PL bitstream
programming, ELF download, DDR mailbox overwrite or inference occurred.
This is a conservative gate rejection, not a B4i application failure.
Linux's previously reported `psci_idle` driver makes powered-down secondary
cores plausible, but the exact cause wasn't measured. The historical P03
width script used `catch {stop}` and skipped failures, explaining why
Track A could proceed; the amended B4i gate is narrower and fail-closed.

**Recovery and retest:** do not resume a halted Linux instance; reboot the
KV260 and repeat normal user preparation before any new JTAG attempt.
First run the new native Tcl/Python gate tests and the unchanged offline
ELF preflight. Only then re-run this **stop+PS-width diagnostic** under
separate operator authorization, saving a new log. Do not immediately run
the full physical `--mode execute` pipeline: low-DDR, mailbox and PM/firmware
ownership remain separate gates, not resolved by a successful CPU stop.
The 2026-10-22 attempt has a versioned evidence ledger file next to this
document; preserve the original physical log outside the repo.

## 2026-10-22 B4i second real board attempt: STOP + FPD128/LPD128 PASS

The operator **rebooted the KV260, ran `sudo xmutil unloadapp`, and
independently executed the revised B4i stop/width gate** using physical
XSDB/JTAG. The real PC terminal reported:

```text
P07_B4I_A53_0_STOP_COMMAND_PASS=1
P07_B4I_A53_1_STOP_COMMAND_PASS=1
P07_B4I_A53_2_POWERED_DOWN_OBSERVED=1
P07_B4I_A53_3_POWERED_DOWN_OBSERVED=1
P07_B4I_PS_WIDTH_TARGET=PSU
P03_2C_PS_FPD_AXIFS_RAW=0x00000A00
P03_2C_PS_FPD_HPM0_WIDTH_BITS=128
P03_2C_PS_LPD_AXIFS_RAW=0x00000200
P03_2C_PS_LPD_HPM0_WIDTH_BITS=128
P07_B4I_A53_ALL_CORES_ACCOUNTED_AND_PSWIDTH128_GATE_PASS=1
P07_B4I_DISCARD_PREVIOUS_LINUX_AND_REBOOT_AFTER_TEST=1
```

**Accepted scope:** the new gate handled naturally powered-down secondary
cores without masking unrelated halt errors; all four A53 states accounted,
PSU selected, and both historical FPD/LPD raw width readings 128-bit.
This is a **real KV260 CPU/PS width checkpoint PASS**, not a synthetic
receipt. Full raw log is local to user; the repository stores an explicitly
user-reported transcript evidence ledger at
`P07_B4I_2026_10_22_PHYSICAL_TAKEOVER_WIDTH_PASS_LEDGER.json`.

**Not established:** no A53 ELF download/execute, PL bitstream programming,
DDR mailbox read/write, neural inference, or proof of exclusive early
boot-firmware/low DDR ownership. The earlier contradictory XSDB
`0x00002560`/`0x00000512` observations remain distinct historical
evidence; this successful dedicated-run read shows the accepted raw values
**for this session**, not the cause of the earlier discrepancy.

**Next sub-milestone P07-B.4j:** a separately operator-approved,
rebooted, disposable Linux/JTAG session that re-runs these checks and
programs the SHA-pinned accepted P03.2c BIT/LTX with the original VIO
reset-release verification. This shell-only next step explicitly does
**not** launch ELF or touch DDR. See `P07_B4J_SHELL_PROGRAM_MILESTONE.md`.
Reboot after all A53 takeover attempts; never resume halted Linux.

## Note-free hardware approval workflow (2026-10-22)

At the operator's request, the B4i driver no longer accepts or requires
`--recovery-note`, and no operator-authored note file is necessary for
future B4i/B4j sessions. The operator still explicitly approves the
relevant destructive operations using flags, and the tools enforce artifact
preflight, A53 state/PS width gate, unique out-of-repo evidence directory,
bitstream/VIO result, and standalone mailbox acceptance. A declared
`--low-ddr-exclusive YES` is an assertion by the operator, **not** a
measurement of firmware/Linux DDR ownership. The B4i ELF download is
still blocked operationally until that ownership has genuinely been
established. The B4j shell-only run is the next physical checkpoint.
