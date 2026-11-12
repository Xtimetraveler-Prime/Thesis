# M08.1 — owner host receipt review and Loihi v2 KV260 precedent

**Received from owner:** original M08.1 read-only host inventory JSON, matching one-line SHA256 receipt and independent host-only audit JSON; the owner also confirms the KV260 boots Linux reliably and normally runs `sudo xmutil unloadapp` after boot. This written review is a **digest-bound interpretation** of owner-supplied evidence, not a claim of independent live board access. All source code/hardware in Loihi Digital Twin remains unmodified.

## User-provided M08.1 first receipt

- `m08_readonly_inventory.json` SHA256 **`2c4276c13e3adb21721b8b49e027aa94cbe1e51cf592d402272684bc518606e0`** (matches uploaded `m08_readonly_inventory.sha256`; audit `receipt_sha256` same).
- `m08_readonly_audit.json` SHA256 **`d804ac023db8fe42b8538bd9762d96e6a5b438421cbd420375894e3e7ff42425`**; audit reported `RECEIPT_HASH_AND_SCHEMA_OK`, `archive_scan_status=CHECKED`, `physical_run_verified=false`, and `ready_for_physical_ddr=false`.
- Capture reports M08 branch head `bfb49474e820a574beeaf1e95d45d4fb2540823f`, a historical checkpoint before these follow-up changes. **Source SHA hashes belong to that historical revision**, not later code. It is normal that new report re-capture will have different HEAD/source hashes and timestamps.
- **Five genuine M06 owner original archive filenames and published SHA-256 fingerprints matched**, without rerunning any of the original five Vivado 2025.2/XSim gates. Their exact identities remain specified in `src/neuromorphic_accelerator_v1/m08_entry.py` and `docs/M06_ACCEPTANCE_REVIEW_2026_11_10.md`.
- Linux developer host is x86_64 Ubuntu 24.04 class, Python 3.12.3; `lsusb` saw FTDI **VID:PID 0403:6011** quad UART/JTAG-capable bridge. A USB VID/PID is **not** a unique board identity or evidence a specific hardware target is opened.
- `vivado -version` and `vitis_hls -version` returned `COMMAND_NOT_FOUND` **in that host shell**; the files do not establish that Vivado/Vitis 2025.2 are uninstalled. First source the previously used installation's real `settings64.sh` path and repeat in a fresh receipt directory. Do not assert unavailable vendor tooling until this is checked.
- Host `git status --porcelain=v1` is nonempty: untracked Loihi v2 physical-evidence subdirectories and **multiple v1/root Vivado journal/log/backup artifacts**. None are assumed safe to delete. Keep them outside any automated build cleanup; new work uses an exclusive timestamped `~/Thesis_Evidence/M08` directory. The host inventory's `git_clean=false` is an **environment warning, not failed neural regression**.
- Host report explicitly contains no board-local DT, OS, FPGA status or DDR allocation proof. The owner's **separate** report that the KV260 boots normally is accepted as an operator observation, but no board-side `xmutil listapps` or `/proc/device-tree/model` receipt has yet been uploaded.

## Physical precedents found in the separate Loihi Digital Twin v2 directory

These sources are **useful hardware integration references** and do not transfer signed16 or signed32 neuron contracts into Loihi's 24-bit design:

| Prior original Loihi v2 result | Documentary evidence | Applicability to M08 |
| --- | --- | --- |
| K26 routed physical host-paged shell, 100 MHz, WNS +0.734 ns, WHS +0.010 ns, 47 URAMs, 1 HLS core/3 resident slots | `Loihi_Digital_Twin/v2/docs/P08_4_ACCEPTANCE.md`; `docs/P08_4_3A_HOST_PAGED_K26_SHELL.md` | Shows this **board family and local 2025.2 flow** previously routed a memory-rich design. NOT an M08 accelerator implementation or achievable M08 routed timing. |
| Representative real K26 deep-core page replacement, logical core 4, timestep 99, 618 states verified, 3,865 HLS dispatch cycles, exact output trace | `Loihi_Digital_Twin/v2/docs/P08_4_3B_ACCEPTANCE.md`; `docs/P08_4_3B_PHYSICAL_MNIST_CONFORMANCE.md` | Demonstrates the archived **Vivado hardware manager/JTAG/VIO handshake, SRAM load/readback and independently frozen oracle** worked once. Not the M06 PS DDR/AXI architecture; no head-to-head time ratio. |
| Routed Loihi v2 bitstream `p08_host_paged.bit` SHA256 `3538b8f7a23dbd923c77471cb533cd844af548c0d50d7679cd40844f465e8f83` and probes SHA256 `e32376f31486b96b070b0b12c6131d7bed067e0dd05e0461b029baf3eeea6936` | `Loihi_Digital_Twin/v2/docs/P08_4_3B_ACCEPTANCE.md`, `v2/hardware/run_p08_4_3b_physical.sh` | A prior physical artifact identity for documentary comparison **only**. Do not load into M08 and report inference or resources as M08. |
| Existing `vivado/run_p08_impl.sh`, `hardware/run_p08_4_3b_physical.sh` | `Loihi_Digital_Twin/v2/` | Useful *reference pattern*: pin tool/version/part, verify bitstream/LTX hashes, save immutable output and independently check raw results. Do not copy their output files into M08 or run Loihi reprogramming to begin M08. |
| Linux boot then `sudo xmutil unloadapp` | **Owner statement**, supported as standard Kria accelerated-app lifecycle by AMD documentation | Use `xmutil listapps` read-only before/after **operator's customary unload**, avoid running PL programmers while a conflicting app owns the PL; command does not prove a particular future bitstream/DT/driver exists. |

**Important distinction:** accepted Loihi v2 paging was largely host/JTAG/VIO-controlled resident URAM and no native Linux DDR ownership was proven for the **new M08 paged AXI neural engine**. The prior work establishes an efficient **known-good physical test methodology**, not an opportunity to shortcut M08.3 kernel-owned DDR isolation or M05/M06 numerical equivalence.

## Revised next steps

1. With Linux booted, run `sudo xmutil listapps` to capture loaded accelerator state, then (as in the user's existing established workflow) `sudo xmutil unloadapp` and capture `sudo xmutil listapps` again. Do not call `xmutil bootfw_update` or flash QSPI. This is an *operator run*, not a GitHub CI operation.
2. On development PC, source real Vivado/Vitis 2025.2 `settings64.sh`, run `vivado -version`, `vitis_hls -version` and record genuine full-system `.xpr/.xsa/.bit` existence under accepted evidence/Loihi v2 only as a reference. Preserve sha in a **new** M08 folder.
3. Continue M08.2 with **its own read-only AXI4-Lite PL identity candidate**, using actual PS clock/reset and native address assignment from a new genuine Vivado BD trial. Do not guess Linux physical BAR/MMIO. Inspect real output before any JTAG programming.
4. Only then integrate actual M06 signed16 pager/AMD width conversion and a driver-backed Linux DMA buffer, exercise independent exact neural state/spikes and active W-before-R ordering, and report routed resources/timing.

**Stop reason:** Current GitHub-side source development can prepare Verilog, Tcl, report checks, tests and owner execution commands, but cannot verify a live Vivado BD, native routed image, current Linux driver, or physical DDR. Those need new local evidence, not a new hardware-authorization prompt.

See `M08_FIRST_PC_KV260_RUNBOOK.md` and `M08_PHASED_HARDWARE_PLAN.md`.
