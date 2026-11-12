# M08.2b D2 — original owner fan DCP reset/timing-exception closure triage

**2026-11-12.** This follow-up extends [the seven-file native DCP review](M08_D2_OWNER_NATIVE_FAN_DCP_REPORT_FINDINGS_2026_11_12.md). Scope: original fan-preserving owner checkpoint only, K26 `xck26-sfvc784-2LV-c`, physical fan output A12, routed DCP SHA256 `aea9bb224006907cf7e62c2a135ec36eda4582b15e8cf6575805f7b807b94b0e`. The original Linux-deployed bit.bin SHA256 `a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b` remains **QUARANTINED** after the real first-MMIO Linux/RCU stall. No hardware activity was authorized or performed.

## Genuine new owner vendor report evidence

Exactly four new original attached text files have been inspected and independently hashed. The corresponding full current owner evidence folder, Vivado log, original DCP, runner receipt and local SHA ledger were NOT provided in this upload, so don't claim their hashes were independently verified here.

| Original owner attachment | SHA256 | Observation |
|---|---|---|
| `10_dcp_identity.txt` | `6fd1d76c7317217cfeae2ba31a2d7a3bfb1d197cf36decb133bed88be77a5cd1` | Correct pinned DCP SHA, fan A12, 2 declared clocks, 5.355ns WNS, 0.029ns WHS; explicit runtime/unverified flags remain NO |
| `13_dcp_methodology.rpt` | `14938c664bec372b9cf2269b04bb77e905cfe62c381dbd43edc3d3d4de98fe51` | Genuine Vivado 2025.2, fully routed; `Checks found: 0` |
| `18_dcp_exception_coverage.rpt` | `a557a6bcdd072b1c7e16535a1fe8fa51cd1429fa8968fb480c821965b79ba86e` | 29 rows, all `False Path`, with 25 pin-scoped 3-endpoint 100% rows and four cell-scoped rows at positions 48–51 |
| `19_dcp_ignored_paths_inventory.txt` | `1233de024548214cc5eedb2f18fecf75057946bbb4b2328b7651cd248d00cbe3` | 30 sampled ignored paths, all one STARTPOINT and ten XPM reset synchronizer instances with three CLR stage destinations each |

### What is established and what remains unproven

- 25 pin-based exception rows each apply to 3 endpoints with **100% listed pin coverage**.
- Cell-based rows: position 48 has 1 endpoint / 33.33% coverage; position 49 has 0 / 0%; position 50 has 0 / 0%; position 51 has 1 / 0%. **Zero coverage is NOT a failing setup/hold path**. AMD UG906 says it can indicate a non-existent exception path; cell-to-pin expansion can also lower coverage. It is still necessary to inspect which of these exceptions are fully ignored, obsolete or overridden. Native `report_exceptions -ignored` and `-summary` have now been added to the **next** offline report pass to resolve that ambiguity.
- The ignored path STARTPOINT is **exactly one** internal `m08_page_ps_i/ctrl_sc/inst/clk_map/psr_aclk/U0/ACTIVE_LOW_BSR_OUT_DFF[0].FDRE_BSR_N/C`. All 30 sampled ENDPOINTs are `.../(s_sc_)xpm_cdc_async_rst_inst/arststages_ff_reg[0|1|2]/CLR`, across 10 distinct reset synchronizer instances (3 samples per instance).
- AMD XPM_CDC_ASYNC_RST documentation confirms the mechanism used for asynchronous reset assertion and synchronous destination-clock release. That is consistent with the path pattern. This is **not proof** of correct runtime reset release, and a first 30-path `-user_ignored` sample is not a whole-design proof that *all* excluded timing paths are only reset paths.
- `13_dcp_methodology.rpt` contains **zero native methodology checks** reported, which is affirmative static-route evidence.
- The original `RTSTAT-10` DRC (15 counted/14 named internal reset-pipeline nets) still exists. A zero-methodology-violations report does **not** waive or invalidate that DRC warning.
- The original initial physical PS→PL identity transaction **never returned reliable register data**; incident only established lost SSH/RCU stalls. No failure-state PL0/AFI/ATB register capture, AXI waveform, or specific faulting CPU instruction exists. No standalone offline timing report can recreate that event.

**Reasoned D2 priority change:** Timing closure/exception structure is no longer the leading actionable explanation; investigate **Linux-managed PS PL0 clock/reset + PS→PL HPM0 AFI interface ownership and PS-side ATB4 timeout protection** first. The original DT overlay source does not independently declare `assigned-clocks`, `assigned-clock-rates`, or `xlnx,afi-fpga` / `config-afi`, but stock firmware may have configured them. This is a **configuration ownership proof gap, not a demonstrated bug**. Don't attempt PS MMIO or add guessed device-tree values.

References: AMD UG906, report_exceptions -coverage: https://docs.amd.com/r/2025.2-English/ug906-vivado-design-analysis/Reporting-the-Timing-Exceptions-Coverage ; AMD UG835 report_exceptions -ignored: https://docs.amd.com/r/2025.1-English/ug835-vivado-tcl-commands/report_exceptions ; AMD XPM CDC reset macro: https://docs.amd.com/r/en-US/pg382-xpm-cdc-generator/XPM_CDC_ASYNC_RST .

## New source-only development

1. `scripts/m08_d2_review_reset_timing_exceptions.py` is **pure Python read-only** and explicitly checks all four owner report shapes, original DCP SHA, methodology zero, exact 29-row exception coverage (including 3 zero-coverage cell entries), exact 30 ignored paths, their one STARTPOINT, and 10 distinct XPM async-reset synchronization groups of stages 0–2. Prints a JSON review with complete four input SHA256s and all physical safety flags false; rejects evidence drift, symlinks, non-reset exclusion or changed DCP. Source tests use **synthetic fixtures** and are NOT more vendor runs.
2. `tests/test_m08_d2_reset_exception_review.py` exercises positive source fixture and negative variants, including methodology violation, changed 0% exception, unexpected ignored AXI data-path endpoint, duplicate reset stages, wrong DCP SHA, missing/symlinked input and no hardware commands.
3. `scripts/m08_d2_fan_dcp_readonly_forensics.tcl` now additionally requests `20_dcp_fully_ignored_exceptions.rpt` (`report_exceptions -ignored`) and `21_dcp_exception_summary.rpt` (`report_exceptions -summary`) **without waiver or checkpoint/bitstream write**. Native unavailable commands are explicitly logged as UNAVAILABLE, not falsely interpreted as clean signoff. These two added reports have **not** yet been generated by the owner.

## Owner PC-only commands — no board / no MMIO

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
python3 -m unittest discover -s tests -p 'test_m08_d2_fan_dcp_readonly_forensics.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

To independently inspect the same four existing owner-PC reports (adjust to the actual folder printed by the last run; this path was visible in the new native exception report):

```bash
cd /home/dna/Git/Thesis/Neuromorphic_Accelerator/v1
REPORTS="$HOME/Thesis_Evidence/M08/m08_d2_fan_dcp_READONLY_pcuy8ne0"
python3 scripts/m08_d2_review_reset_timing_exceptions.py --reports-dir "$REPORTS"
```

Optional, if pursuing native positions 49–51 further: PC ONLY, genuine Vivado 2025.2, original immutable DCP and original immutable source receipt, create a completely **NEW sibling evidence directory**. This will reread/rehash original `48_fan_post_route.dcp`, run read-only report commands and emit 20/21 as available:

```bash
source /home/dna/Vivado/2025.2/Vivado/settings64.sh
export M08_FAN_ORIGINAL_ROUTE="$HOME/Thesis_Evidence/M08/m08_2b_path_a_fan_route_20261112T034949Z_utDrAG"
python3 scripts/m08_d2_run_fan_dcp_readonly_forensics.py \
  --route-dir "$M08_FAN_ORIGINAL_ROUTE" \
  --evidence-base "$HOME/Thesis_Evidence/M08"
```

Return `10_dcp_identity.txt`, `20_dcp_fully_ignored_exceptions.rpt`, `21_dcp_exception_summary.rpt` and `01_native_vivado.log` from the newly printed folder if available; preserve full `99_evidence_sha256.txt` on PC. Even if all exception review checks succeed, **D3 new-image release / D4 first physical identity read / D5 page remain STOP** pending independent PS-side timeout/clock/isolation safety design and owner authorization.
