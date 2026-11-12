# M08.2b D2 — original fan-routed checkpoint read-only forensic audit

**November 12, 2026.** Complement to the [authoritative M08 first-identity RCU incident and D0–D5 quarantine](M08_2B_3_FIRST_IDENTITY_RCU_STALL_INCIDENT_AND_FIX_PLAN_2026_11_12.md), not a replacement. Original M08 bit.bin SHA `a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b` remains **QUARANTINED**. No physical M08 MMIO, PL reload, JTAG hot programming or boot/fan configuration changes are authorized.

## New D2 result and important distinction

The first-party baseline BD and Icarus models show intended PS `M_AXI_HPM0_FPD` → SmartConnect → identity/page connectivity, clock and reset wiring, but the first owner physical identity attempt triggered an RCU stall. The prior simulation did not inspect the **original fan-preserving routed DCP**. This D2 extension introduces a **source-only tested** PC script that can ask genuine **Vivado 2025.2** to read and report on the actual routed design. No such new vendor run is claimed until the owner performs the steps below and provides genuine original output.

The owner-original fan route checkpoint (not the earlier unfanned candidate) is:
- Evidence directory: `/home/dna/Thesis_Evidence/M08/m08_2b_path_a_fan_route_20261112T034949Z_utDrAG`
- File: `48_fan_post_route.dcp`
- SHA256 (from the accepted original route ledger): `aea9bb224006907cf7e62c2a135ec36eda4582b15e8cf6575805f7b807b94b0e`
- Fan-preserving routed timing in owner evidence: WNS +5.355ns, WHS +0.029ns, 3,367/3,367 nets fully routed, A12/LVCMOS33 PWM, one documented **unresolved** SmartConnect RTSTAT-10 warning.
- Contrast: the original *unfanned* DCP and its +5.469/+0.015ns route are **NOT** the deployed fan-preserving route. Do not accidentally compare the wrong checkpoint.

The new scripts are:
- `scripts/m08_d2_run_fan_dcp_readonly_forensics.py`: strict PC Linux-only, prevents execution on an identified KV260; requires original evidence dir and unchanged SHA ledger, verifies all original rows, verifies the exact original DCP SHA before and after Vivado, records source SHA before and after and preserves new evidence in a fresh directory. No hardware shell, AXI, bitstream, or board command.
- `scripts/m08_d2_fan_dcp_readonly_forensics.tcl`: requires genuine native Vivado 2025.2, again rehashes DCP before opening, opens the routed checkpoint, checks K26 part/top and fan pin, checks timing, writes **read-only derived reports** in the fresh directory: timing summary, DRC including RTSTAT-10, methodology, clock utilization, clock interaction, reset-pipeline net inventory and CDC (when supported). Never writes checkpoint/bitstream.
- `tests/test_m08_d2_fan_dcp_readonly_forensics.py`: negative original evidence/provenance checks; Tcl script parser/SHA guard in local `tclsh` with mock Vivado boundary; mocked vendor output and missing marker fail-closed. Mocks **do not** represent Vivado results.

The DCP can't prove actual failed-board Linux `pl_clk0` was enabled, `pl_resetn0` was released, Linux firmware manager reset ordering, AXI HPM0 responses, physical ATB settings or owner UART evidence. Expect the new review status `NATIVE_OFFLINE_DCP_REPORTS_GENERATED_REVIEW_PENDING`, **not** root cause resolved.

## D2 hardware protection hypothesis refinement (external documentation, not observed on owner board)

AMD Zynq UltraScale+ TRM UG1085, rev 2.6 (2026-10-28), lists **ATB instance 4** in FPD specifically from `FPD main interconnect` to `M_AXI_HPM0_FPD`. It can generate an error for a nonresponding slave when explicitly configured (response enable, SLVERR type, prescale, enable). **We have not inspected old-boot registers or verified that the original firmware configured instance 4.** AMD warns it has fewer than 16 transaction slots and recommends system restart after the FIRST timeout. Registers should be programmed at boot; runtime changes require quiescence. No ATB register write is authorized on currently recovered stock firmware.
  - https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Instances
  - https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Programming
  - https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/ATB-Timeout-Description

AMD PG293's **MI-side AXI Protocol Firewall** can detect missing ARREADY and delayed RVALID, block further downstream requests, and synthesize upstream completion, but may cancel downstream VALID as part of failure isolation and therefore requires downstream reset/recovery before being unblocked. A firewall clocked by **missing PL0** cannot protect a processor independently. Full AXI path, chosen clock source, outstanding-transaction drain, PS isolation, and recovery still need native test/simulation. It is **not** present or demonstrated in the original M08 routed bitstream.
  - https://docs.amd.com/r/en-US/pg293-axi-firewall/Timeout-Faults
  - https://docs.amd.com/r/en-US/pg293-axi-firewall/MI-Side-Mode-Block-Condition

## Additional D1 risk discovered: dynamic DTBO does not explicitly configure PS PL0 clock or AFI

**Source-observed, not physically proven:** the `DTS` string in `scripts/m08_path_a_stage_uio_overlay.py` declares `&fpga_full` firmware/reset and two `&amba` `generic-uio` regions, but contains **no** `assigned-clocks`, `assigned-clock-rates`, `xlnx,afi-fpga` or `config-afi` properties. The accepted source overlay thus does not, **by itself**, demonstrate control of the HPM0 AXI PS-to-PL interface formatting or enablement/rate of PL0 after manager-controlled image replacement. The earlier original fan-preserving BD configuration configures the PS IP **at synthesis time**; it does not establish that the Linux manager configured a live software-owned PS clock or AFI register after load.

AMD's ZynqMP Linux FPGA Manager programming example explicitly includes a PS-PL configuration overlay fragment containing an `xlnx,afi-fpga` node plus a fabric-clock node with `assigned-clocks`/`assigned-clock-rates`. That example is not a universal deployment requirement; stock firmware/boot firmware or Linux clock/AFI drivers could establish the state in other ways. **Absence of these nodes is a serious audit gap, NOT evidence that the original M08 clock was stopped or AFI wrong.** Do **not** add assumed AFI values or blindly edit/install the original DTBO. First compare original, SHA-verified stock and M08 DTBO decompilations on the PC; consult the exact board BSP and Linux firmware-manager ownership model; independently review AFI width/format compatibility with the PS `128-bit` HPM0 and converted 32-bit AXI-Lite slaves. No current-stock clock reading can recover failed-image clock state.

AMD deployment example: https://xilinx-wiki.atlassian.net/wiki/spaces/A/pages/18841847/Solution%2BZynqMP%2BPL%2BProgramming .

## Exact owner PC commands — no board connection or MMIO

First run source-only targeted verification and broader regressions on the exact new commit:

```bash
cd /home/dna/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-kv260-bringup
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-kv260-bringup
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m08_d2_fan_dcp_readonly_forensics.py' -v
python3 -m unittest discover -s tests -p 'test_m08_ps_pl_stall_forensics.py' -v
python3 -m unittest discover -s tests -p 'test_m08_post_incident_mmio_quarantine.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

**OPTIONAL next owner original Vivado 2025.2 read-only inspection, AFTER source verification**; safe for the PC, NO board cable, SSH, PuTTY or manager operations required:

```bash
cd /home/dna/Git/Thesis/Neuromorphic_Accelerator/v1
source /home/dna/Vivado/2025.2/Vivado/settings64.sh
command -v vivado
export M08_FAN_ORIGINAL_ROUTE="$HOME/Thesis_Evidence/M08/m08_2b_path_a_fan_route_20261112T034949Z_utDrAG"
sha256sum "$M08_FAN_ORIGINAL_ROUTE/48_fan_post_route.dcp"
# Expected: aea9bb224006907cf7e62c2a135ec36eda4582b15e8cf6575805f7b807b94b0e
python3 scripts/m08_d2_run_fan_dcp_readonly_forensics.py \
  --route-dir "$M08_FAN_ORIGINAL_ROUTE" \
  --evidence-base "$HOME/Thesis_Evidence/M08"
```

Output identifies a new `M08_D2_FORENSIC_EVIDENCE_DIR=...` with `01_native_vivado.log`, SHA-provenance JSON, native report files `10`–`17`, result `98_review.json` and `99_evidence_sha256.txt`. In that printed evidence directory, run `sha256sum -c 99_evidence_sha256.txt` in the local PC terminal. Save all native diagnostics, including failure/partial logs. **Do not alter, move or delete the original fan-route directory.** A successful run means read-only derived native reports were generated, not that the design is safe to program.

### What to review from genuine native reports

1. `12_dcp_drc.rpt`: inspect **all** RTSTAT-10 listed nets vs original warning (15 counted, 14 shown). Any additional rules or changed methodology block a D3 release.
2. `16_dcp_reset_net_inventory.txt`: inspect actual routed SmartConnect reset-pipeline net names. Missing matches can mean naming/optimization, **not** proof of a clean reset.
3. `14_dcp_clock_utilization.rpt` and `15_dcp_clock_interaction.rpt`: inspect PL0 path clocks, interconnect, clock domains, timing path coverage.
4. `17_dcp_cdc.rpt` if generated: review reset/CDC findings. If absent or reported unavailable, mark CDC **OPEN**, never clean.
5. `11_dcp_timing.rpt`: compare with original WNS/WHS and unconstrained endpoint counts.
6. `01_native_vivado.log` and `10_dcp_identity.txt`: confirm original SHA, K26 fan pin, part/top, and native command execution.

**Next source work after real vendor report review:** decide whether reset/clock or interconnect implementation justifies a new diagnostic candidate with IP-level AXI protocol instrumentation; separately prove clock liveness and PS-side ATB safety/isolation (including no-clock scenarios) before ANY owner-approved new image. D4 first 32-bit identity-only MMIO and D5 64-word page remain blocked.
