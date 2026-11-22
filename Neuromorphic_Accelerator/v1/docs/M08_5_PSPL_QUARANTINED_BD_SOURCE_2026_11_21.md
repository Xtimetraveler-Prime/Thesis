# M08.5 — quarantined KV260 HPM0 / HP0 offline Vivado BD candidate (2026-11-21)\n\n> **STATUS UPDATE (2026-11-21 local / 2026-11-22 UTC):** This document originally described the source candidate *before* the owner executed native Vivado. The owner subsequently achieved `vivado_exit_status=0`, **22/22 original SHA checks OK** in `m08_m085_pspl_bd_20261122T041029Z_PDYwZWvm`, and **independently ran the read-only 22-file receipt reviewer PASS** (`OWNER_RECEIPT_CONSISTENT_SOURCE_ONLY_NATIVE_BD_NOT_DMA_RELEASE`; `snapshot_and_builder_match_current_source=true`). The original candidate is now **OWNER-VALIDATED OFFLINE NATIVE PS/PL BD TOPOLOGY ONLY**, still **NO actual kernel-bound DMA, physical drain, synthesis/route/bitstream, or board access**. The older "not yet native" sentences below are preserved to describe what was known at source creation, not the present state. [Current authoritative handoff](M08_5_NEXT_CHAT_HANDOFF_2026_11_21.md) and [owner-verified receipt/kernel report](M08_5_OWNER_BD_RECEIPT_KERNEL_DMA_PREFLIGHT_2026_11_21.md).\n

**State: SOURCE CANDIDATE ONLY.** On existing `agent/neuromorphic-accelerator-v1-m08-matched-experiments` / **draft PR #95**. The owner reported the previous v1.1 MMIO-controlled neural increment **fully verified locally**; its accepted all-75-work-commands/all-512-oracle simulation contract is unchanged. Original M08.4 **accepted physical** bitstream/JTAG evidence is immutable. NO new K26 Vivado 2025.2 **native BD evidence has been collected by the assistant**, no new Vivado synth/route/bitstream, XSA or DT, Linux kernel DMA owner, physical AXI bus drain, fan/boot data, SSH, JTAG or board programming.

## Purpose, evidence basis and explicit quarantine

A source-level `m08_m085_axil_managed_neural_candidate` already has genuine five-channel 32-bit AXI4-Lite registers (ABI v1.1), 75 MMIO LOAD/DISPATCH/SAVE operations, an original seven-slot signed16 LIF shell, one real 64×32-bit bank and a 128-bit AXI4 master. Until now **the Vivado IP Integrator (IPI) port metadata and a KV260 PS block-design topology did not exist** for this composite.

The new builder is derived from **actual accepted M08.4 owner build source** `scripts/m08_paged_m06_lif_build.tcl` (Vivado 2025.2/K26/PL0/fan/POR source method) and from **historical separate Loihi v3** `Loihi_Digital_Twin/v3/vivado/create_p02_ddr_impl_project.tcl` / `create_p03_mmio_impl_project.tcl` (128-bit HP0 and HPM0-to-32-bit control SmartConnect topology), **not from v3 static DDR ownership or its different signed24 neuron design**. The owner-verified first KV260 SSH receipt (5/5 original SHA reported OK) observed Linux 6.8.0-1036-xilinx, a stock-named overlay and PS DMA controllers but NO M08 accelerator kernel driver/device.

**This BD is intentionally unexecutable on DDR:** `accel/csr_trusted`, `accel/driver_bound_verified`, `accel/control_route_verified` and `accel/interconnect_drain_ack` all connect to **the SAME explicit hard-zero constant**. The M08.5 fence cannot grant, any DMA read/write must be denied, and **quarantine is separately audited after Vivado BD validation**. The purpose of the current owner Vivado run is *only to check whether real 2025.2 IP Integrator infers, connects, and address-maps the intended interfaces*. The zero constants are NOT a future driver authentication mechanism, and no report from this candidate can certify RTL placement/timing/energy or Linux DDR access.

## New source artifacts

- **`rtl/m08/m08_m085_axil_managed_neural_candidate.v`**: inserted exact `X_INTERFACE_INFO` and `X_INTERFACE_PARAMETER` metadata for 19 AXI4-Lite slave signals, 37 AXI4 master signals, PL clock association and active-low reset. The original arithmetic and command FSM are unchanged. The 32-bit little-endian control has 12-bit **byte** addresses, the 128-bit master has 49-bit addresses / 1-bit IDs / maximum 16-beat page bursts.
- **`scripts/m08_m085_pspl_quarantine_bd.tcl`**: new unique K26 `xck26-sfvc784-2LV-c` Vivado 2025.2 project and exclusive copied first-party snapshot of 12 real neural/AXI RTL files + source fabric POR. Requests 128-bit PS `M_AXI_HPM0_FPD` → **dedicated SmartConnect** → 32-bit module-ref `accel/S_AXI`. Separately connects `accel/M_AXI` 128-bit → dedicated SmartConnect → 128-bit PS `S_AXI_HP0_FPD`. Requests PS PL0 nominal 100MHz, clocks both PS HPM0/HP0 and the two SmartConnects + accelerator, resets using original synchronous 256-cycle fabric POR, routes TTC0 EMIO waveout2 through slice to `M08_FAN_PWM` A12 LVCMOS33. Strictly requires inferred `S_AXI` and `M_AXI` types, PS port widths, correct connections, clock/reset nets, hard-zero trust net and no surprise HPM masters. Maps a **source-only proposed** 4KiB HPM0 aperture to `0xA4000000` (from historical v3 diagnostics), and the PS HP0 low route to `0x00000000..0x7fffffff`. These are **interconnect routing addresses**, never kernel-owned DDR addresses or proof of actual live boot mapping. Stops at `validate_bd_design -force`, saves BD + source snapshots and a `status=OFFLINE_BD_TOPOLOGY_ONLY_NEVER_DMA_READY` receipt. Deliberately has **no** `launch_runs`, `open_run`, `write_bitstream`, `write_hw_platform`, JTAG/hardware-manager or firmware commands.
- **`scripts/run_m08_m085_pspl_quarantine_bd_pc.sh`**: PC-only, fail-closed wrapper for **new** `~/Thesis_Evidence/M08/m08_m085_pspl_bd_<unique>` directory. Rejects non-Vivado-2025.2. Runs owner Vivado in batch, captures ORIGINAL exit/stdout/stderr/log/journal and exact copied builder source, creates source snapshot, SHA-256 ledger excluding volatile Vivado project cache. Even a fake/unfinished Vivado exit 0 is marked **INCOMPLETE**, never physical PASS. No automatic rerun or cleanup of old evidence.
- **`scripts/m08_m085_pspl_quarantine_source_check.py`**: pure PC Python source-only contract auditor (exact 56 annotated pins, 12 source entries, PS port properties, SmartConnect/clock/reset/fan/address nets, hard-zero owner/drain pins, no programming/synthesis commands). Prints source hashes plus **all physical release fields FALSE**.
- **`tests/test_m08_m085_pspl_quarantine.py`**: Python mutation-negative checks of missing/changed physical ports, address windows, kernel trust, clock, reset, source manifest and forbidden commands; Tcl text syntax `info complete` via real `tclsh` if present; **MOCK** Vivado success and wrong-version tests that must FAIL-CLOSED and retain new original PC logs. These are NOT real native Vivado tests.

## 2026-11-21 owner first native attempt — preflight coordination bug and source fix

The owner's first **offline** Vivado 2025.2 attempt captured its original evidence under `/home/dna/Thesis_Evidence/M08/m08_m085_pspl_bd_20261121T205920Z_E7OxxtTo`. Its original `02_vivado_exit_status.txt` states `vivado_exit_status=1` and the original `00_vivado.log` shows **no PS/PL BD validation was reached**. The first failure was exactly:

```text
Evidence directory not fresh or unexpected content: 04_stdout.txt
(file ".../m08_m085_pspl_quarantine_bd.tcl" line 23)
```

The shell runner created `04_stdout.txt` and `05_stderr.txt` **before** Vivado entered Tcl (normal `> ... 2> ...` redirection), but the source Tcl allowlist recognized only `00_vivado.log` and `01_vivado.jou`. This was an erroneous startup contract between our two first-party scripts, **not** evidence of incorrect K26 interfaces or failed Vivado BD validation. The owner ran `sha256sum -c 99_evidence_sha256.txt` and reported original **7/7 SHA entries OK**: Vivado log, journal, exit status, builder source, stdout, stderr and context. Those seven original bytes and the original directory remain **untouched**; seven hash passes prove receipt integrity, **not** native BD success.

**Fix:** `scripts/m08_m085_pspl_quarantine_bd.tcl` now has one exact startup allowlist: `{00_vivado.log 01_vivado.jou 04_stdout.txt 05_stderr.txt}`, still requiring each existing entry be a regular non-symlink file and refusing ANY other entry (such as stale `02_vivado_exit_status.txt`, `99_evidence_sha256.txt`, `project/`, hidden stale files or symlinked stdout). The owner PC runner's output/redirection and new-folder creation are unchanged. `scripts/m08_m085_pspl_quarantine_source_check.py` pins the exact Tcl **and** shell four-file startup contract, preventing future mismatches; new `test_m08_m085_pspl_quarantine.py` cases invoke the **real local Tcl interpreter** with `create_project` stubbed to stop before any Vivado project, showing valid precreated files pass and stale/symlink/extra files reject. These tests do not claim native Vivado was run in CI.

**Next owner action after tests:** pull the corrected branch and run `bash scripts/run_m08_m085_pspl_quarantine_bd_pc.sh` again. It MUST create a **second, new** `m08_m085_pspl_bd_*` directory, never restart or rewrite the failed first folder. Continue to check its own full original SHA ledger and logged Vivado result; any subsequent Vivado IP/interface error is a NEW finding, not evidence that this fixed preflight already established PS/PL topology.

## Native boundary and all remaining information gaps

| Gate | Status at this increment | Required independent evidence |
| --- | --- | --- |
| 56 explicitly annotated PL AXI pins | Source candidate + source checker | Actual native Vivado 2025.2 IPI must infer `accel/S_AXI` and `accel/M_AXI` exactly, reject unexpected protocol/width and confirm actual routing |
| 128→32 HPM0, 128→128 HP0 and PL0/reset/fan | Source proposed; simulator does NOT implement PS IP | Native validated BD on owner PC, original SHA receipt, exact IP port and address segment readbacks; may require corrected **new** candidate if Vivado rejects |
| Real PS Linux boot/AFI and address map | UNKNOWN | Owner read-only applied DT/boot firmware/XSA/PS AFI source reconciliation and future separately reviewed live readbacks |
| Kernel-only register access and authentic `csr_trusted`/driver-bound/route | HARDWIRED **ZERO** in quarantine | Reviewed actual kernel-bound platform driver/DT and privileged PS HPM0 route; NOT UIO or unchecked PROT bits |
| Coherent DMA allocation and device-visible address | NOT implemented | Actual selected `struct device` with reviewed mask/ranges/IOMMU, `dma_alloc_coherent` + checked `dma_addr_t`, 7×256B layout, barriers and driver lifecycle |
| Real interconnect outstanding drain/isolation, safe reset/reuse | HARDWIRED **ZERO** ack; NO physical drain | Independent hardware/PS owner with no-late R/B evidence on timeout/revoke/STOP, protected buffer quarantine until true isolation; fabric reset is insufficient |
| K26 synth/place/route/timing/DRC/bit | **NOT RUN; intentionally excluded** | After verified non-quarantined architecture, **separate** exact-source native candidate with all timing, DRC and release gates, and owner approval before any board program |
| Hardware DDR, matched six-cell performance, power, sparse skipping | NOT observed | New separate owner-armed physical evidence AFTER above gates; never infer from this quarantined BD |

In particular, Vivado `validate_bd_design` **cannot** prove the original boot used this PS XSA, identify Linux `dma_addr_t`, prove an IOMMU is disabled, or authorize actual DDR. The static fan output pin **cannot** prove active cooling. A constant-0 trust design may optimize away meaningful LIF compute if someone later synthesizes it—**do not use its resource numbers for scientific comparisons**.

## Owner VS Code / Ubuntu 24.04.5: source-only verification first

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-matched-experiments
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-matched-experiments
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
export PYTHONDONTWRITEBYTECODE=1
python3 scripts/m08_m085_pspl_quarantine_source_check.py --source-only
python3 -m unittest discover -s tests -p 'test_m08_m085_pspl_quarantine.py' -v
python3 -m unittest discover -s tests -p 'test_m08_m085_axil_managed_neural.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -v
```

## OPTIONAL next owner-PC Vivado 2025.2 **OFFLINE BD validation only** (NO BOARD, NO BITSTREAM)

Run separately after reviewing the Tcl and confirming it only creates a quarantined new project. This is a new source-specific native workflow and must not be confused with historical accepted M08.4:

```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
source /home/dna/Vivado/2025.2/Vivado/settings64.sh
vivado -version
mkdir -p "$HOME/Thesis_Evidence/M08"
bash scripts/run_m08_m085_pspl_quarantine_bd_pc.sh
```

The runner prints `M08_5_OFFLINE_BD_EVIDENCE_DIR=<new original directory>`. Record the EXACT path, do not guess or reuse an older folder. If status says `INCOMPLETE` or Vivado reports an error, preserve the new original folder and report the build error; do NOT change firmware/PS settings on the board. The source is a candidate and native Vivado may reject interface inference/PS IP, which is a genuine blocker to resolve.

```bash
D="/paste/the/new/offline/m08_m085_pspl_bd_DIRECTORY"
( cd "$D" && sha256sum -c 99_evidence_sha256.txt )
cat "$D/02_vivado_exit_status.txt"
cat "$D/reports/20_quarantined_bd_observation.txt"
grep -nE 'ERROR|CRITICAL WARNING|WARNING|M08_M085_QUARANTINED' "$D/00_vivado.log" | tail -n 100 || true
find "$D" -type f \( -name '*.bit' -o -name '*.bin' \) -print
```

A successful `sha256sum -c` establishes integrity of the **captured PC receipt only**, not native route acceptance. Any nonempty `*.bit` list or quarantined trust mismatch is a failure to investigate. Keep both the original output and original Vivado log; do not rerun in-place to overwrite them.

**Stop after this incremental handoff for owner local replay.** Next source increment: native BD observation review/fixes, PS Linux device-tree binding and safe `dma_alloc_coherent` platform-driver skeleton, physical real drain/isolation design, and only then non-quarantined K26 offline synthesis and owner-approved programming.
