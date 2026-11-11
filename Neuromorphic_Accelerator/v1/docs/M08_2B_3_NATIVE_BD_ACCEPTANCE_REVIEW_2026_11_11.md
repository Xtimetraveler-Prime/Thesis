# M08.2b.3 — Owner-verified native KV260 PS→identity+safe-page BD acceptance

**Decision (2026-11-11): ACCEPTED, strictly within OFFLINE Vivado 2025.2 native BD creation/validation and evidence-integrity scope.** This does **not** accept physical programming, routed implementation, a bitstream, PS Linux MMIO, actual PS DDR, a connected compute engine, signed16 inference or performance.

## Genuine owner result and retained history

The owner ran `bash scripts/run_m08_page_bd.sh` locally after the corrected Verilog `.v` module-reference wrapper, in the original evidence folder:

`/home/dna/Thesis_Evidence/M08/m08_2b_3_page_bd_20261111T172547Z_ZHe4WE`.

The owner-provided native console and complete 20-row report establish:

| Claim/field | Actual owner observation |
| --- | --- |
| Vivado | v2025.2 (64-bit), genuine local installed tool |
| Original `result.txt` | `exit_status=0` |
| Board preset | `xilinx.com:kv260_som:part0:1.4`, `M08_KV260_PS_BOARD_PRESET_APPLIED=1` |
| Device | `xck26-sfvc784-2LV-c` |
| Actual PL0 clock | **99,999,001 Hz**, 999 Hz below requested 100 MHz; post-validated AXI propagation matched |
| PS AXI master | `M_AXI_HPM0_FPD`, address space `/ps/Data` |
| First PS-to-PL slave | `/identity/S_AXI`, segment `/ps/Data/SEG_identity_reg0`, **0xA0000000–0xA0000FFF** |
| Second PS-to-PL slave | `/page/S_AXI`, segment `/ps/Data/SEG_page_reg0`, **0xA0001000–0xA0001FFF** |
| Segment separation | Two distinct, nonoverlapping, 4 KiB apertures |
| Page wrapper | `rtl/m08/m08_ps_page_safe_shell.v`, compute **DISABLED** |
| Native BD | `META|validated_bd|YES`; output `M08_PAGE_GENUINE_VIVADO_BD_VALIDATED_NO_BITSTREAM_NO_BOARD` |
| Native route/bitstream/DDR/board | **NOT RUN / NOT GENERATED / NOT ACCESSED / NOT PROGRAMMED** |

Native log warnings inventoried from owner output, not falsely discarded: two `WARNING: [IP_Flow 19-11770]` messages indicate `aclk` inputs have no **fixed** FREQ_HZ (accepted because original post-validation PS/AXI clock propagation **exactly matched 99,999,001 Hz**). `WARNING: [BD 41-2925]` says exported Tcl contains original RTL module references and needs the source files to replay (the original owner run added those real files before validating). There were no reported `ERROR:` or `CRITICAL WARNING:` lines in the owner-provided filtered vendor log; the native auditor required their absence as well.

The separately preserved **first M08.2b.3 failed original** remains at `m08_2b_3_page_bd_20261111T171034Z_8UoMK5` (`exit_status=1`; `[filemgmt 56-195]` unsupported SystemVerilog top module reference); it was corrected by the `.v` wrapper without changing the signed16 page/AXI semantics. Both original trial folders are immutable.

## Independent original receipt scope

The owner reported a successful audit and actual `sha256sum -c` checks:

`M08_PAGE_BD_SOURCE_AND_ORIGINAL_VIVADO_RECEIPT_AUDITED_NOT_PHYSICAL`

`M08_PAGE_BD_GENUINE_LOCAL_VIVADO_VALIDATED_NOT_A_BITSTREAM_OR_FPGA_TEST`

`ORIGINAL_OWNER_KV260_PS_TO_SAFE_PAGE_BD_EVIDENCE_CONSISTENT`.

Original JSON from owner terminal reports these SHA256 digests:

| Original artifact | SHA256 in owner's audit |
| --- | --- |
| `source_sha256_before.txt` manifest | `776004de7880afc52f0ddeb9c5b5ceb606c3384be39c7295575d491d91273148` |
| `01_vivado_page_bd.log` | `0b16273d92647b0fd0bb3d4bd9f2e860dcd1821898cd0d6561e232c7b1d7dae2` |
| `02_vivado_page_bd_readback.txt` | `4a81a287626776f679c20837639a3afdc07ba7c999cfa86219b54879ae7e525a` |
| `03_page_bd_export.tcl` | `4f98953dcff19ae2f1219190a840c5970fb78e70690cd1318bf915182aadc5e4` |

`05_evidence_sha256.txt` was checked by the owner and all **four** original artifact lines returned `OK`. All **seven** original source rows in the source manifest passed `sha256sum -c`; before and after manifests matched. The original auditor requires whole-line native markers, true two-slave PS/SmartConnect connections, non-overlapping 4 KiB native PS address segments, safe compute disabled, expected clock propagation, source SHA and nonphysical scope.

**Evidence review caveat:** the original binary/file bytes from this second run were **not separately attached in chat**; the recorded acceptance rests on the owner-supplied full terminal readback, original independent auditor JSON, successful file-hash verification outputs and known first-party scripts. Do not describe this as a separate byte-for-byte off-machine re-audit. Original files should remain owner-held, unchanged.

## Gate to M08.2b.4

The valid native two-slave BD may now seed **a new, isolated** synthesis/routed implementation workflow. It is NOT a route checkpoint and must not be used as a pre-existing implemented design.

M08.2b.4a uses `scripts/m08_page_post_route_candidate.tcl`, `scripts/run_m08_page_post_route.sh` and `scripts/m08_page_post_route_audit.py`. It first re-runs the exact accepted BD code in a **new original owner evidence folder** (never opens this accepted directory), then generates the BD HDL wrapper, runs real synthesis and implementation through `route_design`, and captures actual timing/setup+hold/DRC/utilization/checkpoint reports. It deliberately **stops without a bitstream** until the owner reports real route success and DRC/unconstrained-path review. [Next gate](M08_2B_4A_POST_ROUTE_SOURCE_AND_OWNER_RUNBOOK_2026_11_11.md).
