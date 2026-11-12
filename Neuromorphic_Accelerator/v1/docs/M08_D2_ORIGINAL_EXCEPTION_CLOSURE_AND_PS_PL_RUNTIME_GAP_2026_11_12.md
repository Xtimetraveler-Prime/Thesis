# M08.2b D2 — timing exception closure; pivot to Linux PS/HPM0/PL0 ownership

**2026-11-12 owner native checkpoint inspection, last stage.** This is a continuation of [the first MMIO RCU stall incident](M08_2B_3_FIRST_IDENTITY_RCU_STALL_INCIDENT_AND_FIX_PLAN_2026_11_12.md), [owner seven-route reports](M08_D2_OWNER_NATIVE_FAN_DCP_REPORT_FINDINGS_2026_11_12.md), and [the reset/exception sample review](M08_D2_OWNER_EXCEPTION_AND_METHODOLOGY_FINDINGS_2026_11_12.md). It is **static original DCP evidence only**, not a physical hardware-safe finding.

## Four genuine owner attachments received and independently hashed

| Original owner file | SHA256 | Source observation |
| --- | --- | --- |
| `10_dcp_identity.txt` | `e7364ca805a1967851e45d9c6a15ae11645bc7a37d00a8cda7645d5d3cbc9ed7` | Vivado 2025.2; original fan routed DCP SHA `aea9bb224006907cf7e62c2a135ec36eda4582b15e8cf6575805f7b807b94b0e`; fan A12, WNS +5.355ns, WHS +0.029ns; fully ignored and summary reports `GENERATED_REQUIRES_OWNER_REVIEW`; no runtime claims |
| `20_dcp_fully_ignored_exceptions.rpt` | `3f80666cd3e1e1eb2530cf788c2c28484f85cd982b902fca80a0a630166e3f3c` | **Exactly 3** fully ignored `set_false_path` positions 49–51, each status `Non-existent path` and `-to [get_cells {syncstages_ff_reg[0]}]` |
| `21_dcp_exception_summary.rpt` | `cce18aa8cddfabb400748661af0ab6327c43cd071cea06377bc27886bb86637d` | False Path: **29 constraints, 2 setup endpoints, 2 hold endpoints**. Clock Groups, Multicycle Path, Max Delay, Max Delay DPO, Min Delay all zero |
| `01_native_vivado.log` | `a802a6c524b2ed1378d2c5ecc22ad12545eb03b1982bd3719d05abe9dc5fb475` | Real `open_checkpoint`, `report_drc`, `report_methodology`, completion marker `M08_D2_NATIVE_FAN_DCP_READONLY_INSPECTION_COMPLETED_NO_BOARD` and successful Vivado exit |

**Proven conclusion within the report scope:** the three 0%-coverage cell exceptions in the preceding report are **nonexistent timing paths**, not failure-mode AXI timing paths. Their absence does not make reset sequencing correct. AMD UG906 says `report_exceptions -ignored` distinguishes nonexistent paths from overrides. This result resolves the **three-entry exception ambiguity** but does not prove timing exceptions are universally safe; the first 30 ignored sample paths were XPM async reset clear endpoints. The prior single RTSTAT-10 DRC warning still exists, and no native digital signal observation of AXI handshakes exists.

**Important interpretation:** The summary's 2 setup/2 hold endpoints describe endpoint coverage of false-path constraints, **not 2 failing setup or hold paths**, not zero runtime stalls and not measured physical interface behavior.

Vivado log includes standard warning that CDC reporting excludes clock crossings with missing defined clocks and input ports without input-delay constraints. Source route has 100MHz `PS8/PLCLK[0]` to BUFG_PS (1,678 timed loads); **neither routed clock existence nor zero methodology violations proves that the PS Linux firmware manager actually enabled PL0 or released reset at the failed first identity MMIO attempt**.

The four supplied new files are **not** the entire original SHA evidence folder (e.g., no `99_evidence_sha256.txt` in this upload). The tool/log timestamps and source are consistent with original Vivado 2025.2; do not claim a full receipt was independently verified from the uploaded four files.

## Main unresolved runtime question: who owned the clock and interface?

Original M08 Vivado BD explicitly requests `CONFIG.PSU__FPGA_PL0_ENABLE 1`, ~100MHz `pl_clk0`, `M_AXI_HPM0_FPD` enabled at 128 bits, and connects all SmartConnect/slave clocks to PL0. Reset is `ps/pl_resetn0 -> reset_inv -> pl_reset/ext_reset_in`, `dcm_locked` tied to constant HIGH (not physical lock indication). These *synthesis-time* PS IP parameters do not, by themselves, establish OS-time PL0/HPM0 configuration after a Linux-managed PL image swap.

The M08 `scripts/m08_path_a_stage_uio_overlay.py` explicitly declares `&fpga_full` firmware/reset and two `generic-uio` resources, but no `assigned-clocks`, `assigned-clock-rates`, `xlnx,afi-fpga`, `config-afi`, or per-node `clocks/clock-names`. In contrast, AMD's **ZynqMP Linux FPGA Manager example** includes PS PL clock and AFI fragments, but is not a universal requirement: stock firmware, FSBL, bootloader and Linux clock provider may already configure them. The absence is an **ownership/evidence gap, not proof of a clock bug**. Never guess an AFI value, clock register address, or reset number to install on the board.

UG1087 defines `PL0_REF_CTRL` `CLKACT` bit 24 as **enable or stop** for PL0. This is a direct reason a routed PL0 clock may be absent at runtime. But the `CLKACT` value **during the failed boot** is unknown, and no register read/write from the active recovered K26 is authorized to infer it.

AMD UG1085 documents ATB **instance 4** in FPD ahead of `M_AXI_HPM0_FPD`. ATB timeouts are programmable, not automatic proof of safety, can track **fewer than 16 transactions**, and AMD recommends **restart after the first timeout**. We do NOT know its failed-boot enable/response state. A timeout clocked solely by stopped PL0 is insufficient protection; any corrected candidate must prove PS-domain or otherwise independent bounded failure isolation before a physical read.

**Leading hypothesis remains unproven:** first M08 physical identity access may have hit a nonresponding PS-to-PL AXI interface because of runtime PL0 clock/reset/AFI/ATB state; the original incident's failed SSH and RCU/timer stalls did not capture a faulting address or transaction. Alternatives (AXI bridge/address, kernel hangs, driver/system interactions) remain open.

References:
- AMD UG906 timing exception ignores: https://docs.amd.com/r/en-US/ug906-vivado-design-analysis/Reporting-the-Timing-Exceptions-Being-Ignored
- AMD ZynqMP FPGA Manager Linux PS/PL clock and AFI example: https://xilinx-wiki.atlassian.net/wiki/spaces/A/pages/18841847
- AMD UG1087 `PL0_REF_CTRL` `CLKACT`: https://docs.amd.com/r/en-US/ug1087-zynq-ultrascale-registers/PL0_REF_CTRL-CRL_APB-Register
- AMD UG1085 ATB instances/programming: https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Instances and https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Programming

## New D2 first-party source work

- Extended `scripts/m08_d2_review_reset_timing_exceptions.py` to **optionally** accept genuine `20` and `21` native reports alongside the previous four. If both present, must confirm original Vivado route/tool/command, **exact** positions 49–51 `Non-existent path`, and **exactly** 29 false-path constraints with 2 setup/2 hold endpoints. Rejects missing partner, changed status, extra ignored entry, changed endpoint counts, or swapped input. Computes new SHA256s and clears `fully_ignored_or_nonexistent_positions_not_yet_classified` only on genuine closure. Historical four-file evidence remains supported and explicitly pending.
- `tests/test_m08_d2_reset_exception_review.py` includes additional **synthetic** positive and negative closure cases. These are NOT genuine vendor runs.
- New `scripts/m08_d2_offline_ps_pl_contract_audit.py` uses Python AST to read **without executing** the original M08 overlay `DTS` constant, examines the source BD/fan continuity, and emits a fail-closed JSON analysis of PS HPM0, 128-bit interface, PL0 requested clock, reset, clock/AFI declarations and unresolved runtime proof. Optionally consumes **already saved PC-side stock and deployed M08 DTS text** (`--stock-dts` and `--deployed-m08-dts`) and only reports presence of DT configuration properties; broad presence does **not** imply HPM0 configured or clock active. Never calls the board, shell, native Vivado, DT compiler, PS registers or physical MMIO.
- `tests/test_m08_d2_ps_pl_contract_audit.py` verifies original source facts, no false runtime claim, symlink refusal, source clock regression, and negative changes to the original DTS.

## Exact owner-PC-only verification commands

```bash
cd /home/dna/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-kv260-bringup
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-kv260-bringup
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1

python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m08_d2_reset_exception_review.py' -v
python3 -m unittest discover -s tests -p 'test_m08_d2_ps_pl_contract_audit.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -p 'test_*.py' -v

# Use the LAST original owner read-only DCP evidence directory from native report headers:
REPORTS="$HOME/Thesis_Evidence/M08/m08_d2_fan_dcp_READONLY_rhnlc6fr"
python3 scripts/m08_d2_review_reset_timing_exceptions.py --reports-dir "$REPORTS"
python3 scripts/m08_d2_offline_ps_pl_contract_audit.py
```

**Optional existing owner-PC original device tree sources only:** if stock and original M08 DTBO files are already available as IMMUTABLE PC-side originals, first decompile the **copies** with `dtc -I dtb -O dts` into NEW PC-side files; pass both absolute DTS paths to `--stock-dts` and `--deployed-m08-dts`. Do **not** move binaries to/from the board in this step. Do not interpret a static DTS as the original failed Linux live register state. Preserve all original SHA receipts and files.

**Hardware STOP unchanged:** Do not reload the original quarantined bit.bin, attempt old `/dev/uio*`, `/dev/mem`, `devmem`, `xmutil`, or JTAG, or alter fan/boot/clock/AFI registers. The board remains on recovered stock `k26-starter-kits` while D0/D1/D2 continue. D3 new safeguarded image, D4 first physical read and D5 page are NOT authorized.
