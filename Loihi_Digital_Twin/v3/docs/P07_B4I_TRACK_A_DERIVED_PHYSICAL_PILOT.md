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

The driver contains separately gated `--mode execute` and six independent explicit approvals for dedicated JTAG ownership, A53 takeover, *entire PT_LOAD low DDR exclusive ownership*, mailbox overwrite, accepted PL programming, and reboot/recovery. It also requires a meaningful user-owned absolute-path recovery/board-state note and a new evidence directory outside the repository. Missing information or nonmatching PS width **fails before programming**.

**Do not execute it yet.** A new, operator-approved physical session must first establish:
- The OS/Linux instance will be discarded; no CPU/Linux owner resumes afterward.
- The **specific ELF entry and every physical PT_LOAD span**, heap/stack and any early boot/low-DDR memory owner have been independently reconciled. Consent alone is not proof of memory exclusivity.
- The legacy mailbox `0x43FF0000` is safe to overwrite in that dedicated run and cache/MMU mapping is understood.
- Exact accepted P03 XSA/BIT/LTX provenance and matched FPD128 PS↔PL setup.
- JTAG server ownership, recovery power/reboot plan, saved evidence, and no sealed B2 TEST exposure.

Even after a physical pilot **PASS**, this is **read-only shell admission**, NOT P07-B 27-core numerical inference. Full B2 27-context physical parity remains separately blocked pending reset/provenance/scaling work. Preserve draft PR #49; no merge without user approval.
