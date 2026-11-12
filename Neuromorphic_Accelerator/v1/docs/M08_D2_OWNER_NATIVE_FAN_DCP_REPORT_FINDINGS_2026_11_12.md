# M08.2b D2 — reviewed genuine original fan-routed DCP reports (2026-11-12)

**Scope and incident authority:** source/Vivado **offline** forensics of original fan-preserving M08 route; see [authoritative first physical UIO RCU stall incident](M08_2B_3_FIRST_IDENTITY_RCU_STALL_INCIDENT_AND_FIX_PLAN_2026_11_12.md). The owner reports they ran the corrected PC-only SHA-gated Vivado checkpoint inspection and supplied **seven vendor output files**. These observations do NOT establish runtime hardware clock, ATB configuration, AXI response, faulting instruction or safe new deployment. The original M08 Linux `bit.bin` SHA `a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b` stays **QUARANTINED**. No physical MMIO, M08 firmware manager load, PS register writes, FPGA programming, fan manipulation or D3–D5 authorization.

## Uploaded exact file evidence (verified from supplied bytes)

| File | SHA256 |
| --- | --- |
| `10_dcp_identity.txt` | `141643e71aa56b33c3ccf13dae43e70386b2c0bdb6e327d448f48ae50dc4bd27` |
| `11_dcp_timing.rpt` | `23f57daeddc3bc117dbbcbdd7604042828738be84cb84e1681bdc72d437a87b4` |
| `12_dcp_drc.rpt` | `03a324f45a046f25fb80b223f77ab3182233eb80c569cb1330a17d39a08b357c` |
| `14_dcp_clock_utilization.rpt` | `f1fe6aea291bc1157ddca7ade7102516a8988d457bff096cbd17322b1244259b` |
| `15_dcp_clock_interaction.rpt` | `980b2fa53283ad95e6e8eb764dc5ee4abad07c16720b0fedbdbc7038c93a7200` |
| `16_dcp_reset_net_inventory.txt` | `7a5497ac50a07c7661ebd9b4ca8bae936faa87cc0c796ba605515fd68ac71a80` |
| `17_dcp_cdc.rpt` | `2b5feafb67cad6d7ed9a175732a936d920205d37de4b6101e75109caa4ba1878` |

The **seven** files have common genuine Vivado 2025.2 tool/host/route report identity and `10_dcp_identity.txt` pins the original `48_fan_post_route.dcp` SHA `aea9bb224006907cf7e62c2a135ec36eda4582b15e8cf6575805f7b807b94b0e`, K26 part `xck26-sfvc784-2LV-c`, top `m08_page_ps_wrapper`, PWM A12 LVCMOS33 OUT. The owner provided no original `01_native_vivado.log`, `00_original_inputs.json`, `02_vivado_exit.txt`, `03_source_sha256_after.json`, `13_dcp_methodology.rpt`, `98_review.json` or `99_evidence_sha256.txt` **in this upload**. They MAY exist on the PC; do NOT call these original files missing from disk or imply the entire owner ledger was independently rehashed here.

## Findings, concrete source evidence, and limitations

1. **Routed clock wiring EXISTS.** `14_dcp_clock_utilization.rpt` has `PS8/PLCLK[0]` to one `BUFG_PS/O`, 10.000ns period, 1,678 loads on `m08_page_ps_i/ps/inst/pl_clk0`. This is a Vivado clock/timing model and routed resource; **NOT** measured clock running at the moment original Linux accessed UIO.
2. **Routed timings pass.** `11_dcp_timing.rpt` reports WNS **+5.355ns**, WHS **+0.029ns**, no failing endpoints for setup/hold/pulse width, `checking no_clock (0)`, `checking unconstrained_internal_endpoints (0)`. It lists two named `clk_pl_0` and `clk_pl_1` 100MHz clock objects; **only `clk_pl_0` appears in the Intra Clock table** and in the clock-interaction table. Do not infer that `clk_pl_1` is an active second fabric clock domain, or that runtime PL0 and PS HPM0 clocks are running.
3. **Partial false path is an open timing-exception audit.** `15_dcp_clock_interaction.rpt` has one `clk_pl_0 → clk_pl_0` entry: Clock-Pair Classification `Clean`, Inter-Clock Constraints `Partial False Path`, 4,591 total endpoints in that report (a different timing-report summary is 4,515). A same-clock partial exception need not be a CDC defect, and the reported 0 failing timed endpoints cannot certify the excluded paths. AMD UG906: report timing exceptions with `report_exceptions -coverage` and sample `get_timing_paths -user_ignored` for endpoint review. Those diagnostics are added to the **NEXT** PC-only source runner; **they were not produced by the seven uploaded reports.**
4. **DRC warning persists unchanged.** `12_dcp_drc.rpt`: one RTSTAT-10 `No routable loads` warning with **15** nets counted, **14** explicit names shown, no related violations. `16_dcp_reset_net_inventory.txt`: 20 matching reset-pipeline internal SmartConnect net names, including the 14 explicitly named by DRC. Five additional matched nets occur under `switchboards/i_nodes` and one under `m01_nodes/m01_r_node`. Pattern matches are not a count of DRC defects; mismatch **does not prove** missing actual reset. No new DRC warning and no validated explanation of an RCU stall.
5. **CDC output is an empty-body report.** `17_dcp_cdc.rpt` has normal tool header and `CDC Report` label but no findings/table. Compatible with a single analyzed active clock; **NOT** standalone proof of zero CDC/reset-domain hazards or PS/PL clock ownership.
6. **Vivado timing header says no methodology report was run PRIOR to the timing summary**, and the later separate `13_dcp_methodology.rpt` was not supplied in these seven uploads; ask owner to preserve it if already generated, do not claim methodology was never run.
7. **No error address/CPU backtrace** was recovered from the original first physical MMIO attempt. PS clock/reset/AFI live state, ATB instance 4 protection and physical HPM0 AXI transaction completion all remain UNKNOWN. A routed 100MHz clock and correct UIO resource size do not show these runtime properties.

### Next investigation priority (no board)

(a) Capture/read-only verify timing exception coverage and ignored paths on the **same original SHA-pinned fan-routed DCP**. (b) Compare original stock and M08 **PC-side** device-tree overlays and boot/system configuration for PS PL0 clock/AFI programming, but do not guess values or change an installed DTBO. (c) If an appropriate PS/PL reset or firewall change is justified, implement a **NEW** separately named, simulatable candidate with deterministic upstream timeout/isolation and clock-liveness protection; current D3 remains blocked pending safety proof.

### Source additions

- `scripts/m08_d2_triage_native_fan_reports.py`: **read-only** seven-report triage from original owner PC evidence or a copied directory; never claims physical pass and explicitly requires review of exceptions/RTSTAT/CDC/PS runtime. It also exposes per-file SHA256 so uploaded originals can be compared against PC originals.
- `tests/test_m08_d2_native_report_triage.py`: source-only synthetic fixtures and negative report drift detection (these are not native vendor executions).
- `scripts/m08_d2_fan_dcp_readonly_forensics.tcl` now optionally emits `18_dcp_exception_coverage.rpt` with native `report_exceptions -coverage`, always emits `19_dcp_ignored_paths_inventory.txt` from a **maximum 30-path sample** of `get_timing_paths -user_ignored`. Any native inability to generate exception coverage is recorded as UNAVAILABLE, not reported clean. The runner requires the new inventory and records `timing_exception_coverage_signed_off=false` in new receipts. **This change was NOT in the original owner native run and has not yet executed in native Vivado.**

### Exact optional next owner PC commands

```bash
cd /home/dna/Git/Thesis
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-kv260-bringup
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-kv260-bringup
cd Neuromorphic_Accelerator/v1

python3 -m unittest discover -s tests -p 'test_m08_d2_native_report_triage.py' -v
python3 -m unittest discover -s tests -p 'test_m08_d2_fan_dcp_readonly_forensics.py' -v
# Existing original native forensic report folder, not the ORIGINAL route evidence folder:
REPORTS="$HOME/Thesis_Evidence/M08/m08_d2_fan_dcp_READONLY_n9z3lyes"
python3 scripts/m08_d2_triage_native_fan_reports.py --reports-dir "$REPORTS"
```

Optionally rerun the **already verified original-route only** PC forensic Vivado runner, which creates NEW evidence and additionally generates report 18/19:

```bash
source /home/dna/Vivado/2025.2/Vivado/settings64.sh
export M08_FAN_ORIGINAL_ROUTE="$HOME/Thesis_Evidence/M08/m08_2b_path_a_fan_route_20261112T034949Z_utDrAG"
python3 scripts/m08_d2_run_fan_dcp_readonly_forensics.py \
    --route-dir "$M08_FAN_ORIGINAL_ROUTE" \
    --evidence-base "$HOME/Thesis_Evidence/M08"
```

Return optional **PC-only** `13_dcp_methodology.rpt`, new `18_dcp_exception_coverage.rpt`, `19_dcp_ignored_paths_inventory.txt`, `10_dcp_identity.txt` and original/new run `98_review.json`. This does not permit original image MMIO/reload or ANY change to recovered stock firmware.
