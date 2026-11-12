# M08.2b Path A: native fan block design accepted; routed K26 candidate

2026-11-11. Consolidated M08.2b milestone. PR #83 stays draft and unmerged.

## Original owner fan block-design evidence (genuine Vivado PASS, OFFLINE)

The owner generated original native Vivado 2025.2 fan+dual-AXI BD under:
/home/dna/Thesis_Evidence/M08/m08_2b_path_a_fan_bd_20261112T033319Z_EqNiGN

The uploaded 01_vivado_fan_bd.log SHA256 is:
4f40262b7e272cfd6aeaf4eb2a7418e249ce744611b720abd98483ab06d01bc4
The uploaded 20_m08_fan_bd_readback.txt SHA256 is:
676adfa961e0dda2371f406b7567d8a5a3ccec2d2c018874efbc020a2203ecb5
The uploaded 23_independent_fan_bd_audit.json SHA256 is:
1e81a4a1d9d48a7986f950ff299ca48ea93a6ee01ce173776250e7534bc3439e

All three were independently rehashed against their rows in uploaded original 30_evidence_sha256.txt (receipt SHA256 bb0bbe416f678ec83d60351406b4670fa7c9d79d73971fe460c37f933c1c849f). Its additional artifact rows were not independently rehashed because original bytes were not provided. Do not modify or replace this accepted source evidence.

Native first-party original BD: KV260 SOM board part 1.4, actual PS PL0/AXI 99,999,001 Hz; identity 0xA0000000/4KiB; signed16 safe page 0xA0001000/4KiB. PS TTC0 EMIO waveform output bit[2] goes through AMD xlslice to one-bit M08_FAN_PWM; the generated XDC targets package A12/LVCMOS33/SLOW/DRIVE 4. Compute remains DISABLED. Actual native second validate_bd_design and genuine native original-source independent audit returned PASS.

Accepted scope: GENUINE LOCAL FAN-PRESERVING BD VALIDATION ONLY. No synthesis, route, timing, DRC review, generated bitstream, cooling continuity, Linux firmware install, PS AXI readback, DDR or neural inference. These remain OPEN.

## Read-only Linux device-tree overlay evidence (actual owner stdout)

Owner newer 01_board_stdout.log SHA256:
f748950b8b62f5af8df2b1457adb93c97b9631cd4cc350c64b94bf9862b59026

Actual Ubuntu 24.04.2 kernel 6.8.0-1036-xilinx, dfx-mgr and fancontrol active, fpga0 operating, active overlay k26-starter-kits_image_1. Installed stock package shell.json is shell_type XRT_FLAT and num_slots 1. Device tree decompile from REAL stock K26 .dtbo shows fragment@0 targeting FPGA full and setting firmware-name k26-starter-kits.bit.bin and four reset IDs 0x74 through 0x77 under zynqmp_reset. The unresolved 0xffffffff tokens are DT fixup placeholders, NOT approved live phandles for a new overlay. Existing uio0..3 are AXI performance monitors; none grant M08 0xA0000000 or 0xA0001000 Linux access.

## Next Path A source: genuine PC-only fan+dual-AXI post-route candidate

New scripts/m08_path_a_fan_post_route.tcl SOURCES the same accepted fan-BD Tcl in a FRESH evidence project, generates genuine AMD BD and RTL wrapper, launches synth+implementation only through route_design, validates native run statuses, opens routed design, checks actual PORT M08_FAN_PWM PACKAGE_PIN A12 / IOSTANDARD LVCMOS33 / direction OUT / SLEW SLOW / DRIVE 4, captures real max/min timing slacks, clock count, routing/utilization/IO/timing/DRC/methodology reports and original routed checkpoint. No bitstream, flash, JTAG, FPGA-manager, fancontrol or Linux MMIO access.

New scripts/run_m08_path_a_fan_post_route.sh runs on PC only with real Vivado 2025.2 and bounded M08_FAN_ROUTE_JOBS (1..8, default 4). It preserves fresh original owner logs and independent SHA ledger on success OR failure, including partial vendor report files. Source digest pre/post is pinned. Original accepted fan BD folder is not re-opened or modified.

New scripts/m08_path_a_fan_post_route_audit.py checks exact original 12-source SHA list, first-party identity/page windows, generated fan constraints, native command markers, actual routed A12 port metrics, nonnegative WNS/WHS and presence of real vendor route reports/DCP. It explicitly reports that DRC and unconstrained-path signoff are PENDING even on PASS. New tests/test_m08_path_a_fan_post_route.py has pure synthetic failure tests for shifted pin, bad addresses, negative slacks, source mismatch, missing markers, false bitstream claims and source-only route safety. These are NOT native passes.

## Exact PC VS Code commands

    cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
    git status --short
    git fetch origin
    git switch agent/neuromorphic-accelerator-v1-m08-kv260-bringup
    git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-kv260-bringup
    git rev-parse HEAD
    python3 -m compileall -q src scripts tests
    bash -n scripts/run_m08_path_a_fan_post_route.sh
    python3 -m unittest discover -s tests -p 'test_m08_path_a_fan_post_route.py' -v
    python3 -m unittest discover -s tests -p 'test_m08*.py' -v
    python3 -m unittest discover -s tests -v
    source /home/dna/Vivado/2025.2/Vivado/settings64.sh
    bash scripts/run_m08_path_a_fan_post_route.sh

Final line executes REAL native Vivado synthesis/routing, strictly OFFLINE; it may consume significant PC resources. It does NOT generate a bitstream. Fresh evidence directory will have prefix m08_2b_path_a_fan_route_ and contains 01_vivado_fan_route.log, 40_fan_route_metrics.txt, 41_fan_timing_post_route.rpt, 43_fan_drc_post_route.rpt, 46_fan_io_post_route.rpt, 47_fan_route_status_post_route.rpt, 48_fan_post_route.dcp, 49_independent_fan_route_audit.json, 52_evidence_sha256.txt (only artifacts actually generated). Preserve native DCP and entire original folder, and share genuine logs/reports for independent signoff; do NOT upload a fabricated output or claim native success if a step fails.

## Safety and acceptance

No unloadapp/loadapp, active starter-kit replacement, JTAG program, firmware/sysfs programming, PS MMIO or DDR; operator must establish fan continuity during reconfiguration, with independent cooling and rollback plan as appropriate. Even a routed fan output does NOT prove continuous fan PWM during configuration. Route/DRC timing and kernel DT binding reviewed BEFORE any new .bit.bin/.dtbo package creation. The existing accepted M08 .bit remains untouched and not suitable for Linux-managed swap. PR #83 stays draft/unmerged.
