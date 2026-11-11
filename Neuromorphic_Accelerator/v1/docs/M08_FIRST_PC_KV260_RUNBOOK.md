# M08.1 — first PC and KV260 evidence session (read-only)

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

## C. Check live KV260 status via UART (no programming)

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

### What to provide back to continue

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
