# M08.1 — first PC and KV260 evidence session (read-only)

> **CURRENT 2026-11-11:** **M08.2a OFFLINE IDENTITY PS→PL BLOCK-DESIGN ACCEPTED**, after five immutable failures, sixth genuine Vivado 2025.2 `validate_bd_design` PASS, and seventh original independent auditor receipt PASS `/home/dna/Thesis_Evidence/M08/m08_2_identity_bd_20261111T074810Z_XlzGwf`. The seventh audit JSON's SHA matches the seventh `05_evidence_sha256.txt` entry; the readback/export digests match the previously reviewed sixth originals. [Accepted scoped review](M08_2_IDENTITY_BD_SCOPED_ACCEPTANCE_2026_11_11.md). **Do not rerun or modify the seven original M08.2 evidence folders for this already-accepted gate.** The broader M08.2b routed neural/DDR design remains OPEN; `0xa0000000` is a design-level aperture, NOT an authenticated Linux address. **M08.3.1 safe read-only DMA/Linux readiness source development started; see [board-local DMA observation runbook](M08_3_DMA_READINESS_RUNBOOK.md).** Do not infer any physical implementation, bitstream, MMIO, DDR ownership or neural inference from offline BD validation.

### M08.2b.1 current source-only signed16 one-page hardware checkpoint (NO board commands)

The previously accepted M08.2a genuine Vivado identity BD is frozen. The **new** M08.2b.1 `rtl/m08/m08_host_staged_page_bank.sv` is a first-party **256-byte** host-load/compute state page for 16 M06 signed16 neuron records. It is deliberately not Loihi's full-context signed24 VIO memory system. Its first-party Icarus testbench requires complete host readback coverage before dispatch, complete dirty readback before host save, and checks the actual M06 signed16 neuron-step lane. [Engineering and physical integration roadmap](M08_2B_1_SIGNED16_HOST_STAGING_RTL_2026_11_11.md).

**Run on the Linux development PC from the exact pulled branch HEAD, not on the KV260 board:**

~~~bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
command -v iverilog
command -v vvp
python3 -m unittest discover -s tests -p 'test_m08_host_staged_page_rtl.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -p 'test_m07*.py' -v
python3 -m unittest discover -s tests -v
~~~

If Icarus is unavailable, **do not count the skipped HDL test as a PASS**. The original GitHub Actions M08/M05/M06 first attempts encountered Ubuntu apt/DNS resolution failures while installing Icarus and consequently did not run the HDL tests; [exact vendor-run-independent failure ledger and direct Icarus compile](M08_TESTS_EXPLAINED.md). No owner physical deployment or additional native Vivado project has been requested for this source checkpoint. The next genuine K26 integration step will be a separately reviewed PS AXI4-Lite write/read adapter and new native BD, not a re-run or alteration of old original evidence.

### M08.2b.2 new first-party PS AXI4-Lite page adapter — PC SOURCE ONLY

The owner has now independently confirmed the corrected M08.2b.1 page-bank standalone Icarus simulation passes. M08.2b.2 adds a **new** 32-bit AXI4-Lite S_AXI module, `rtl/m08/m08_axil_page_control.sv`, with 4 KiB internal decode, source-only register map, safe page access and watchdog. It is NOT connected to actual native KV260 PS/SmartConnect, and **no operator programming, Linux MMIO or DDR commands are authorized** by this new source. [Exact register and safety contract](M08_2B_2_AXIL_PAGE_CONTROL_HANDOFF_2026_11_11.md).

From the Linux **development PC** after pulling the exact M08 branch and checking its HEAD:

~~~bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
command -v iverilog
command -v vvp
TMP="$(mktemp -d)"
iverilog -g2012 -s tb_m08_axil_page_control -o "$TMP/m08_axil_page.vvp" \
    rtl/m08/m08_axil_page_control.sv \
    rtl/m08/m08_host_staged_page_bank.sv \
    rtl/m08/tb_m08_axil_page_control.sv
vvp "$TMP/m08_axil_page.vvp"
python3 -m unittest discover -s tests -p 'test_m08_axil_page_control.py' -v
python3 -m unittest discover -s tests -p 'test_m08_host_staged_page_rtl.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -v
~~~

Require an actual **`M08_AXIL_STANDALONE_NO_K26_NO_DDR_NO_DMA_PASS`** marker and all negative markers, not just successful Python source checks. The next M08.2b.3 owner native Vivado project must be in a **fresh, exclusive evidence directory** with no changes to the seven immutable accepted M08.2a owner folders. The existing M08.2a original PS→identity evidence is not a new read/write page deployment.

### Historical failures — optional read-only inspection, no reruns

~~~bash
D="/home/dna/Thesis_Evidence/M08/m08_2_identity_bd_20261111T055614Z_B7OyfZ"
ls -lah "$D"
cat "$D/result.txt"
grep -nE 'ERROR:|CRITICAL WARNING:|invalid command|wrong # args|couldn.t read|couldn.t find|M08_' "$D/01_vivado_identity_bd.log" | head -80 || true
tail -n 140 "$D/01_vivado_identity_bd.log"
cat "$D/source_sha256_before.txt"
cat "$D/source_sha256_after.txt"
~~~

Preserve the whole folder, including any partial `project/`. Do not delete or overwrite. The original `01_vivado_identity_bd.log`, `result.txt` and before/after source SHA files have now been reviewed. Vivado v2025.2 SW build 6299465 and IP build 6300035 were genuinely invoked; the first missing-project error has been diagnosed and the isolated script ordering corrected. This is **not** yet a new genuine Vivado PASS. The toolchain-not-on-PATH instructions in §B are historical, not the current blocker.


**Research phase:** actual KV260 hardware integration starts after accepted M05/M06 offline simulation and M07 software experiments. Physical activity is owner-authorized for M08, but this first observation uses **NO JTAG programming, memory writes, boot firmware updates or DMA**. The development tool cannot operate the owner's local KV260; these are exact commands to run locally when convenient.

## A. Refresh and run Linux VS Code PC verification

First preserve any local changes; do not discard uncommitted work. In your Linux VS Code terminal:

~~~bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-kv260-bringup
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-kv260-bringup
git rev-parse HEAD

cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -p 'test_m07*.py' -v
python3 -m unittest discover -s tests -v
~~~

No PS/PL hardware accessed. Optional Icarus tests retain existing optional skip behavior unless `iverilog` and `vvp` are installed. Prior M05/M06 genuine vendor test archives should **not** be altered or rerun solely for entry inventory.

## B. Preserve the first host-only inventory and original artifact check

These commands only record tool availability, project source SHA, Git status, USB device enumeration, and SHA256 of the FIVE previously accepted M06 original ZIPs when they are located under `~/Thesis_Evidence`. If your ZIPs live elsewhere, change only the `--accepted-evidence-dir` path to their real parent directory. A missing or duplicate basename results in MISSING/AMBIGUOUS, **not** a forged PASS. This does not modify the originals.

~~~bash
mkdir -p "$HOME/Thesis_Evidence/M08"
OUT="$HOME/Thesis_Evidence/M08/m08_1_host_$(date -u +%Y%m%dT%H%M%SZ)"
python3 scripts/m08_capture_readonly.py \
    --mode host \
    --accepted-evidence-dir "$HOME/Thesis_Evidence" \
    --output-dir "$OUT"
python3 scripts/m08_audit_readonly.py \
    --capture-dir "$OUT" \
    --output "$OUT/m08_readonly_audit.json"
sha256sum "$OUT"/m08_readonly_inventory.json "$OUT"/m08_readonly_audit.json
~~~

A successful capture prints `M08_READONLY_CAPTURE_RECORDED_NOT_BOARD_ACCEPTANCE`; a successful receipt audit prints `M08_READONLY_RECEIPT_INTEGRITY_OK_NOT_HARDWARE_ACCEPTANCE`. **They do NOT print KV260 ready or physical DDR PASS.** The JSON includes local Vitis/Vivado tool command responses: if `vivado -version` says missing, first use your genuine installation's `settings64.sh` with the actual absolute path and repeat capture in a **new** directory. Do not create or modify a file named like one of the original M06 acceptance ZIPs.

## C. Established KV260 Linux and xmutil boot flow (owner-confirmed)

The owner confirms that the KV260 **boots Linux normally** and that the established Loihi-v2 routine is to unload the default accelerated application after boot. Do not redo a boot-failure recovery process without evidence of an actual problem. The accepted Loihi v2 `docs/P08_4_ACCEPTANCE.md` and `P08_4_3B_ACCEPTANCE.md` also establish a prior routed K26 host-paged core and **real** JTAG/VIO physical dispatch, but they do **NOT** validate the new M08 signed16 pager/DDR integration.

From the **KV260 Linux shell**, preserve the active-app state before and after the user's usual operation:

~~~bash
sudo xmutil listapps

# Established owner boot routine — unload only after examining listapps.
sudo xmutil unloadapp

sudo xmutil listapps
uname -a
cat /etc/os-release
tr '\\000' '\\n' < /proc/device-tree/model
~~~

`xmutil unloadapp` is a platform application-unload operation that can remove the currently loaded PL accelerator. Do not confuse it with Linux shutdown, a bitstream programming success, physical DMA buffer allocation, or authorization to choose an arbitrary PS physical address. If the board-local inventory script is present, `python3 scripts/m08_capture_readonly.py --mode board-local --output-dir NEW_DIR` can collect `xmutil listapps`, `boardid`, `bootfw_status`, and `platformstats` without executing unload, load or firmware update. Run before/after unloading to preserve both observations if convenient; preserve new evidence folders and redact unique board identifiers when sharing raw logs.

**Known report review:** the owner host capture SHA256 `2c4276c13e3adb21721b8b49e027aa94cbe1e51cf592d402272684bc518606e0` matched its independent receipt; all five original M06 archives matched. The host terminal saw USB FT4232H ID `0403:6011`, but `vivado` and `vitis_hls` were not on PATH. `git status` also showed untracked Loihi physical-evidence directories and Vivado logs; **do not clean or overwrite them**. See [owner evidence and Loihi reuse review](M08_1_OWNER_EVIDENCE_AND_LOIHI_REUSE_2026_11_10.md).

### Genuine local Vivado source environment and M08.2 PS→PL identity trial

**One new SEVENTH offline vendor/independent-auditor receipt attempt, conditional on eight new-HEAD M01–M08 CI workflows GREEN:** the sixth genuine Vivado design already validated and exported successfully; no further Vivado design correction is indicated by its original log. The sole corrected behavior is the audit counting the **actual** marker output rather than Vivado's commented Tcl `puts` echo. Run the same approved wrapper in a **new** directory to obtain `04_m08_identity_independent_audit.json`, `05_evidence_sha256.txt` and the final wrapper marker tied to the exact updated four-file source SHA. No historical folder changes, no physical programming, no DDR. Review the immutable original log above if needed. Run the following on the **development PC** only after you have fetched the correction and confirmed green same-SHA CI. The runner creates a *different* evidence directory and does not build a bitstream or operate the KV260:

~~~bash
# Run on the PC, not the KV260. Preserve untracked original local evidence.
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
git status --short
git fetch origin
git branch --show-current   # must be agent/neuromorphic-accelerator-v1-m08-kv260-bringup
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-kv260-bringup
git rev-parse HEAD        # confirm SHA matches all eight successful PR workflow runs
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -p 'test_m07*.py' -v
python3 -m unittest discover -s tests -v
bash -n scripts/run_m08_identity_bd.sh
source /home/dna/Vivado/2025.2/Vivado/settings64.sh
vivado -version           # requires genuine 2025.2; Vitis HLS is not used
mkdir -p "$HOME/Thesis_Evidence/M08"
bash scripts/run_m08_identity_bd.sh
~~~

The script checks genuine Vivado 2025.2, uses a fresh `$HOME/Thesis_Evidence/M08/m08_2_identity_bd_*_XXXXXX` folder and **never deletes** historical logs. It must preserve `result.txt`, `source_sha256_before.txt`, `source_sha256_after.txt`, `01_vivado_identity_bd.log`, `02_vivado_identity_bd_readback.txt`, `03_identity_bd_export.tcl` and `04_m08_identity_independent_audit.json` on success. A failure preserves the raw Vivado log and nonzero result; it must NOT be reported as a successful physical design. The required success text is `M08_IDENTITY_BD_GENUINE_LOCAL_VIVADO_VALIDATED_NOT_A_BITSTREAM_OR_FPGA_TEST`.

**Important:** The corrected ordering has a mocked Tcl regression and source-only checks, but the corrected source has **not** yet been run against a genuine local Vivado IP catalog. It is a **trial**, not an already validated block diagram; if Vivado rejects module-reference AXI inference, PS clock/reset wiring, exact address segment or a version-specific IP property, the appropriate next action is to inspect the original log and revise the candidate. Do not silently waive a vendor `ERROR` or `CRITICAL WARNING`, assume a 32-bit MMIO base address from source text, or program the existing Loihi v2 bitstream as an M08 design.

**After the new run**, inspect the **newly printed** `M08_IDENTITY_BD_EVIDENCE_DIR`; check `result.txt`, raw `01_vivado_identity_bd.log`, and original `source_sha256_before.txt`/`source_sha256_after.txt` with `cmp` and `sha256sum -c`. On success require `02_vivado_identity_bd_readback.txt`, `03_identity_bd_export.tcl`, `04_m08_identity_independent_audit.json`, and the exact `M08_IDENTITY_BD_GENUINE_LOCAL_VIVADO_VALIDATED_NOT_A_BITSTREAM_OR_FPGA_TEST` marker. The old two folders must not change. If the run returns nonzero, preserve the new folder and share the **first** new genuine Vivado diagnostic before another correction. No bitstream, JTAG or DDR work at this gate.

### UART fallback: only if the normally booting KV260 stops reaching Linux

1. Use the actual KV260 power supply. Connect PC to carrier J4 USB UART/JTAG and check USB enumeration on Linux with `lsusb`, `ls -l /dev/serial/by-id/` and `dmesg | tail -60`. Multiple FTDI serial devices may be exposed: verify the serial port that actually emits Linux/FSBL logs, **don't assume every kit enumerates as ttyUSB1**.
2. Use PuTTY, minicom or another serial tool on the identified port with **115200 baud, 8 data bits, no parity, one stop bit, hardware/software flow control disabled**. Record a *raw* UART boot log to a new file under `~/Thesis_Evidence/M08/`. A heartbeat LED or JTAG being visible does not prove Linux boot, PL programming or inference.
3. If the boot stops at an FSBL/BL31/PMU log or never reaches Linux, preserve the **exact last lines** and power/reset observation; this is a legitimate M08.1 blocker. Do not blindly issue JTAG resets, `bootfw_update`, QSPI erase, or write a random SD image. A power cycle may be used for an operator-controlled clean restart; do not resume an OS halted during JTAG experiments.
4. If you do reach a Linux shell, run the following **on the KV260 itself** (separate from the PC) and save the terminal output under a new immutable evidence file:

~~~bash
uname -a
cat /etc/os-release
cat /proc/cmdline
tr '\000' '\n' < /proc/device-tree/model
cat /proc/meminfo | head -40
ls -ld /sys/class/fpga_manager 2>/dev/null || true
~~~

These commands are read-only. They do **not** identify a safe PS DDR allocation, prove DMA connectivity, or authorize any physical base address. If you have the full v1 repository and Python available **on the KV260**, you can additionally run `python3 scripts/m08_capture_readonly.py --mode board-local --output-dir /path/to/new/empty-parent/m08_1_board_UTC` from that on-device checkout, then independently audit the copied evidence on your PC. If no repo is installed on the board, the raw serial and shell transcripts are sufficient to decide the next step; **do not install extra software just to satisfy a report format**.

## D. Read-only build/toolchain readiness: exact files needed before routing or programming

From the original machine that ran M05/M06 and your accepted evidence directory, determine whether the actual design artifacts exist. Preserve hashes and source roots; do not rerun accepted HLS simply to create a synthetic placeholder.

~~~bash
# PC / development host, optional read-only inventory
vivado -version
vitis_hls -version
find "$HOME/Thesis_Evidence" -type f \( -name '*.xsa' -o -name '*.bit' -o -name '*.hwh' -o -name '*.xpr' \) -print
~~~

If you have an actual candidate `.xpr`, `.xsa`, full-system `.bit` or user-controlled DDR driver/device-tree source, record its exact path and hash. Do not equate a standalone Vitis HLS-generated RTL module or M05 PS/DMA *candidate Tcl* with a fully connected and routed KV260 hardware platform. **Missing artifacts are not failures of M07**; they are the honest M08.2 engineering starting point.

### What to provide back to continue M08.2

The most useful first items are: the **host** `m08_readonly_inventory.json` and its audit result; whether the five M06 original archive SHAs match; the KV260 raw UART boot result (booting Linux or exact last line); the on-board `uname`/device-tree/OS readbacks if available; and whether Vivado 2025.2 can open any existing *full-system* K26 project/XSA. Paths and redacted logs are enough to begin; no need to upload large archive ZIPs unless the hash gate flags a mismatch. Please redact credentials, IPs or serial identifiers if sharing logs publicly.

**Required next result for M08.2:** a genuine local original vendor full-integration `validate_bd_design`/interface/address-map report or a verified list of missing PS/PL interface and HLS synthesis artifacts. Until then, no honest physical page-traffic experiment can be promised. Once the board and Vivado project are characterized, we can develop the board-resident kernel DMA driver and exact PS/PL status/trace path against the *observed* actual hardware interfaces.

## E. Standalone PL identity RTL and host protocol (still NO KV260 access)

M08.2 includes one new side-effect-free AXI4-Lite slave `rtl/m08/m08_axil_readonly_identity.v`, its own `tb_m08_axil_readonly_identity.sv`, and a read-only host protocol checker `m08_identity_client.py`. The candidate is tested with *real* Icarus iverilog/vvp (or explicitly skipped on an owner PC where Icarus is not installed). The M08 GitHub-hosted job installs Icarus and requires the test to pass.

From `Neuromorphic_Accelerator/v1`:

~~~bash
python3 -m unittest discover -s tests -p 'test_m08_identity_client.py' -v
python3 -m unittest discover -s tests -p 'test_m08_identity_rtl.py' -v

mkdir -p "$HOME/Thesis_Evidence/M08"
D="$HOME/Thesis_Evidence/M08/m08_2_identity_sim_$(date -u +%Y%m%dT%H%M%SZ)"
mkdir "$D"
iverilog -g2012 -s tb_m08_axil_readonly_identity \
  -o "$D/m08_identity.vvp" \
  rtl/m08/m08_axil_readonly_identity.v \
  rtl/m08/tb_m08_axil_readonly_identity.sv
vvp "$D/m08_identity.vvp" | tee "$D/m08_identity_sim.log"
sha256sum "$D/m08_identity.vvp" "$D/m08_identity_sim.log"
~~~

Expected a single `M08_AXIL_IDENTITY_STANDALONE_ICARUS_PASS READS=13 REJECTED_WRITES=3 NO_DMA` marker. This is **standalone local first-party RTL**, not the original AMD PS/PL SmartConnect/HLS or a physical board. If Icarus is unavailable, the dedicated local Python RTL test is SKIPPED; the CI Icarus PASS, not a local skip, is the current source-backed verification.

The probe register map exposes magic `0x4D303831` ("M081"), version 1.0, **no DMA master**, and four parameterized build-tag words which are zero by default. The host client requires a nonzero, double-read-stable tag but still does **not** authenticate the deployed bitstream or DDR ownership. **Do not guess a physical MMIO address**, instantiate `/dev/mem`, or run a read on the KV260 until an independently verified Vivado design has connected this slave and a trusted kernel interface exposes its exact address.

## F. Why no guessed DDR command is included

The M06 original connected vendor simulation used a **64 KiB simulated memory image**, not a Linux-owned physical allocation. The earlier M05 Vivado candidate mapped DMA to PS HP0 DDR_LOW but did not prove kernel ownership, full HLS/DMA path integration or a real tested bitstream. Real Linux must expose a driver-allocated or driver-attached DMA-safe buffer, valid device DMA mask, exact physical/bus alias and cache-coherency behavior; direct `/dev/mem` page writes or user-provided DDR base addresses would be scientifically and technically invalid.

See [M08 phased plan](M08_PHASED_HARDWARE_PLAN.md), [M08 tests explained](M08_TESTS_EXPLAINED.md), and [M06 original acceptance](M06_ACCEPTANCE_REVIEW_2026_11_10.md).
