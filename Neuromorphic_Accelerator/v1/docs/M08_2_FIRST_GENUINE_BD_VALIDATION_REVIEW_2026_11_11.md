# M08.2 — first genuine vendor block-design validation PASS; independent-audit fix pending

**Review date:** 2026-11-11 (America/Denver). **Owner-original sixth Vivado evidence:**
`/home/dna/Thesis_Evidence/M08/m08_2_identity_bd_20261111T072331Z_Bo1i5V`.
This document is a review of the **uploaded original** vendor log, readback, BD export, result, and before/after source manifests. It is **not** a synthetic simulation PASS, route, bitstream or KV260 physical execution.

## A. What the sixth original run establishes

1. Real `Vivado v2025.2` (SW build `6299465`, IP build `6300035`) ran on the owner PC at **2026-11-11 00:23:33 MST**, original `result.txt` reports **`exit_status=0`**, and no `ERROR:` or `CRITICAL WARNING:` appears in the raw log.
2. The installed KV260 SOM `BOARD_PART=xilinx.com:kv260_som:part0:1.4` and AMD PS board preset applied. Only `ps/M_AXI_HPM0_FPD` is the selected PS AXI4-Lite master path, through SmartConnect `ctrl_sc` into first-party `identity/S_AXI` (inferred **32-bit AXI4-Lite**). Disabled unused FPD HPM1 / LPD HPM0 remained absent in the runner's fail-closed source checks.
3. The requested PS clock is **100,000,000 Hz**, actual Vivado pin metadata **99,999,001 Hz** (999 Hz deviation within the explicit 1,000 Hz budget), and the log prints `M08_GENUINE_AXI_CLOCK_PROPAGATION_MATCH_HZ=99999001` after `validate_bd_design -force`. The original log shows `validate_bd_design -force` completed and `save_bd_design` / `write_bd_tcl` ran successfully.
4. Readback confirms a **single** Vivado-assigned `/ps/Data/SEG_identity_reg0` aperture `0x00A0000000` / `0x0000001000`, i.e. `0xA0000000` for 4 KiB. This is a *BD-level candidate address*, not proof of a usable Linux MMIO mapping or driver.
5. `03_identity_bd_export.tcl` is **35 KB** and independently shows `get_bd_intf_pins ps/M_AXI_HPM0_FPD` → `ctrl_sc/S00_AXI` → `identity/S_AXI`, a common PS PL0 clock net to `identity/aclk` and interconnect, and the same Vivado address segment. It also includes PS DDR configuration properties because the KV260 **PS board preset** configures PS internals. **No PL DDR module, DDR transaction, DMA or physical memory access is established or claimed.**
6. Two genuine nonfatal warnings require *scope interpretation*, not speculative RTL changes:
   - **`[IP_Flow 19-11770]`**: the identity input clock lacks an explicit `FREQ_HZ` attribute. Vivado propagated the PS source frequency and the post-BD equality checks passed. This is a warning, not a DRC failure.
   - **`[BD 41-2925]`**: the exported Tcl refers to RTL module `m08_axil_readonly_identity` and requires the module source to be added before replay. The original runner does exactly that; the export is not a self-contained project/archive.
   `[BD 5-1043]` inline-HDL migration recommendations are logged as `INFO` in this run and are not blockers at this BD-only gate.

**Owner-original six uploaded files' SHA-256** (independently calculated from uploaded bytes in this review):
```text
ed163d69a09ddc0ffcbdf126a42d5745a93449fa7a39354788e948b7ac795c04  result.txt
2b2c1e61cb690e91715e50431350802ffb821d9f6ffe68cca0d9e7393a992bf1  01_vivado_identity_bd.log
0dc0068bd28ec284fd2cafed81507c6af73951345083b9941e125e4b1657e812  02_vivado_identity_bd_readback.txt
d4c4f2d7e10573a484429610784fcd3ab466dcacf325dd1a975198895e77f303  03_identity_bd_export.tcl
50a2c056a6b31b2f317bb0d145d833340cded1a21c725ab39e2cb04771ef7872  source_sha256_before.txt
50a2c056a6b31b2f317bb0d145d833340cded1a21c725ab39e2cb04771ef7872  source_sha256_after.txt
```
Original source manifest: `rtl/m08/m08_axil_readonly_identity.v=78bf51cfafa4abec7d007d710beeba8f9b7295c61e50affade1b4483494b3c46`, `scripts/m08_identity_ps_bd_candidate.tcl=367afeb5488de7b528254da35682222a8995d94e009498be573aed8e44d6483f`, `scripts/m08_identity_bd_audit.py=02a4b171602564719b24d465471532b29f41091b4b807a65499d61769a8ca955`, `scripts/run_m08_identity_bd.sh=dd299b3c2916d5ef5a7353fa5c4d59e2b9e283e056694e83b2a66ea52ec0a5c7`. The four before/after SHA rows are byte-identical. Do not edit the original files, change their receipts, or copy a new audit into the historical directory.

## B. Remaining audit-only defect found during independent review

**Important distinction:** `result.txt=exit_status=0` is the real **Vivado process status**, not necessarily the final shell-runner status.

The original auditor used `log.count(MARKER)!=1`, but in genuine Vivado `-mode batch` the original log contains both:
```text
# puts "M08_IDENTITY_GENUINE_VIVADO_BD_VALIDATED_NO_BITSTREAM_NO_BOARD"
M08_IDENTITY_GENUINE_VIVADO_BD_VALIDATED_NO_BITSTREAM_NO_BOARD
```
A substring count is therefore **2** despite only **one** genuine output marker. This means the original independent auditor **would reject this real vendor PASS**. The owner did not upload `04_m08_identity_independent_audit.json`, `05_evidence_sha256.txt` or final console transcript, so their absence **within the owner folder has not been directly checked**. Do not invent the auditor result or claim accepted M08.2 closure.

**Narrow source correction:** count exactly one whole `line.strip()==MARKER`, rejecting zero or multiple genuine printed success lines while ignoring comments/Tcl command echoes. Test the actual echoed-command pattern, duplicate true output, and comment-only false PASS with mock log evidence. Leave the proven clock setup, AXI logic, IP design, report, runner and independent hash requirements intact.

The original source hash includes the previous buggy auditor. The corrected auditor is a *new revision*; the original runner requires original source SHA from its own invocation. Therefore **do not** run the new auditor directly against the old immutable evidence or overwrite original receipt files. A subsequent **seventh** fresh, isolated offline Vivado run after the corrected same-SHA eight-workflow CI is green is the clean way to obtain the full original audit/receipt. If the owner's original `04` already exists, inspect it first; otherwise do not regenerate it in place.

## C. Gate disposition and next steps

| Boundary | Status |
| --- | --- |
| Real Vivado 2025.2 clock/IP/AXI BD construction and `validate_bd_design` | **PASS on sixth owner run** |
| Validated BD export/readback, exact source-before/after manifests | **PASS on inspected uploaded originals** |
| Auditor success and complete runner final marker / SHA receipt | **NOT YET DEMONSTRATED — audit bug corrected in source** |
| Full M08.2 offline acceptance | **OPEN until original independent audit and final wrapper proof** |
| Routed timing / FPGA bitstream / connected Linux driver / DDR-safe memory access / board execution | **NOT RUN; no claim** |

Do not run `git clean`, overwrite historical evidence, merge PR #83, produce an FPGA bitstream, alter Linux PS DDR, or treat this PS-only candidate as the accepted signed16 M06/M05/Loihi application. After exact-new-SHA M01–M08 source CI, owner conducts only one new **offline** identity BD validation, supplies original `result.txt`, log, readback, export, both SHA manifests, `04_m08_identity_independent_audit.json`, `05_evidence_sha256.txt`, and final wrapper console marker for external gate review. The original sixth pass remains preserved as a real historical success with a separate auditor bug.
