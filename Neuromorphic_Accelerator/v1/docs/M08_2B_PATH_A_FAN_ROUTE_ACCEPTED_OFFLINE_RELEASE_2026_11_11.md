# M08.2b Path A — accepted original fan route, guarded NEW offline fan bitstream release

**Owner original dated 2026-11-11. Consolidated M08.2b (no sub-milestones). PR #83 DRAFT and UNMERGED. DO NOT PROGRAM the KV260 yet.**

## Genuine native owner K26 route: accepted as OFFLINE route only

Original owner routed evidence folder preserved on the PC:
/home/dna/Thesis_Evidence/M08/m08_2b_path_a_fan_route_20261112T034949Z_utDrAG

The owner provided seven ledger-covered native reports/audit files plus 52_evidence_sha256.txt (eight uploaded files total). All seven independently rehashed native files matched their exact owner-ledger rows; the owner ledger itself is not self-listed and was independently hashed separately. The owner ledger itself had independent SHA256:
0aacf1e841ed05c3bbd099bfd65f39b369cc7e47368689f17a77414579b30938.

Uploaded original exact SHA256 digests:
- 01_vivado_fan_route.log = 48e9f625e69f88b015aca62a1107d6deb911fcaf72315fe4d13b13fded7fdd36
- 40_fan_route_metrics.txt = ef51a46c21894fada6c4b31f7c5212f8749606c23817d01284515be15cbf0d20
- 41_fan_timing_post_route.rpt = 423aa8e4182e34d1477a02b90a0ef551b1ce4ed5619f2c6e8c6ab2692ecb7382
- 43_fan_drc_post_route.rpt = 0b9b970a3ebd4f0c8e9ecedbf785e27947cf77628faa76ab95be8d3db5000970
- 46_fan_io_post_route.rpt = fd084ed36f92663bed2c792d18a7ee6544d70eb1726678f033cab1d66a9e8352
- 47_fan_route_status_post_route.rpt = ba706992db21d69b3db3c1101aaa490b24c89631d4bec5320d0deef1eabc1a39
- 49_independent_fan_route_audit.json = f8ec8736174d6208d704bb9619c83d701d5e9ea64d2e77b2554dd61ca1c71df7

The original ledger also records the large ORIGINAL route checkpoint 48_fan_post_route.dcp with SHA256 aea9bb224006907cf7e62c2a135ec36eda4582b15e8cf6575805f7b807b94b0e. The DCP bytes were NOT uploaded. Its SHA identity and source provenance must be verified on the original PC with the new full-ledger preflight before bitstream release. The original methodology report 44_fan_methodology_post_route.rpt was NOT uploaded; it must be checked locally on owner PC. Do not claim that owner supplied or independent reviewer saw the missing originals.

Genuine native Vivado 2025.2 implementation:
- K26 xck26-sfvc784-2LV-c; both synthesis and route_design completed.
- Real WNS +5.355 ns, WHS +0.029 ns, nonnegative slack with 0 failing setup and hold endpoints. Timing report lists 0 for no_clock, unconstrained_internal_endpoints, no_input_delay and no_output_delay, and no entries in unconstrained path table.
- Design route status: 3,367/3,367 fully routed nets, 0 routing errors.
- Fan M08_FAN_PWM[0] physically assigned to A12 (HD bank 45), LVCMOS33, OUTPUT, drive 4 mA, slew SLOW. Note: this does NOT prove fan PWM continuity during reconfiguration or measured physical fan speed.
- Both original PS AXI 4KiB apertures unchanged: identity 0xA0000000, page 0xA0001000; compute DISABLED.
- One DRC warning RTSTAT-10, SmartConnect internal mi_handler_m_sc_areset_pipe nets, Vivado reports 15 net(s). Human-readable original lists 14 full names. No other DRC severity observed. **This warning is documented, NOT waived.**
- Genuine first-party independent original audit shows routed vendor/source SHA consistency; the prior audit correctly left DRC and unconstrained review explicitly PENDING.

**Accepted scope: ORIGINAL_K26_FAN_DUAL_AXI_ROUTED_IMPLEMENTATION_EVIDENCE_CONSISTENT.** Not physical board programming, Linux MMIO, cooling continuity, neural inference, DDR, or bitstream release.

## Next source-only development: original-route-gated OFFLINE new fan bitstream

New scripts in the SAME M08 branch:
- scripts/m08_path_a_fan_release_preflight.py
- scripts/m08_path_a_fan_bitstream.tcl
- scripts/m08_path_a_fan_bitstream_audit.py
- scripts/run_m08_path_a_fan_bitstream.sh
- tests/test_m08_path_a_fan_bitstream.py

The preflight re-runs the first-party independent route auditor and validates EVERY file in the original 22-row 52_evidence_sha256.txt receipt, including the original DCP and methodology report. It requires original verified fan A12 I/O, a complete 3367/3367 route with zero errors, timing including no unconstrained PL paths, nonnegative matching WNS/WHS, no methodology violations, and ONLY the single unchanged SmartConnect RTSTAT-10 warning. It rejects new warnings, error-severity DRC, corrupted receipts and unexpected/altered original sources.

The PC wrapper REQUIRES an explicit operator signoff variable M08_ACCEPT_FAN_RTSTAT10=YES, genuine Vivado 2025.2 and exact original route evidence directory. It creates a NEW independent owner evidence folder and a SHA-verified COPY of the original routed DCP, never changing the original route folder. The copied DCP must match the original preflight-recorded SHA **before** Vivado starts. Tcl independently rehashes the copied DCP, opens its genuine routed checkpoint, verifies K26 part, m08_page_ps_wrapper TOP, physical A12/LVCMOS33 fan pin, timing, exactly the original documented DRC warning, then issues one OFFLINE write_bitstream with no -force, no waiver and NO hardware calls.

Afterwards a separate auditor revalidates the original routed source/receipts, new actual vendor log and DRC/timing, new .bit size/SHA and absence of a false claim that the old unfanned 05_m08_safe_page.bit equals the new fan-preserving image. All output originals and failures are SHA-receipted, with generated .bit named 05_m08_path_a_fan_page.bit in its NEW folder only.

**This new source has NOT been run through owner's native Vivado yet. DO NOT treat source CI as bitstream-generated PASS.** The new .bit is an offline artifact, NOT a Linux-ready bit.bin or DT overlay and NOT safe to program via JTAG or xmutil yet.

## Exact PC VS Code terminal commands

First verify current clean local Git checkout and run all regression tests:

    cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
    git status --short
    git fetch origin
    git switch agent/neuromorphic-accelerator-v1-m08-kv260-bringup
    git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-kv260-bringup
    git rev-parse HEAD
    python3 -m compileall -q src scripts tests
    bash -n scripts/run_m08_path_a_fan_bitstream.sh
    python3 -m unittest discover -s tests -p 'test_m08_path_a_fan_bitstream.py' -v
    python3 -m unittest discover -s tests -p 'test_m08*.py' -v
    python3 -m unittest discover -s tests -v

Then, after reading the original 43_fan_drc_post_route.rpt and 44_fan_methodology_post_route.rpt locally, native PC-only release:

    source /home/dna/Vivado/2025.2/Vivado/settings64.sh
    export M08_FAN_ROUTE_EVIDENCE_DIR="$HOME/Thesis_Evidence/M08/m08_2b_path_a_fan_route_20261112T034949Z_utDrAG"
    less "$M08_FAN_ROUTE_EVIDENCE_DIR/43_fan_drc_post_route.rpt"
    less "$M08_FAN_ROUTE_EVIDENCE_DIR/44_fan_methodology_post_route.rpt"
    M08_ACCEPT_FAN_RTSTAT10=YES bash scripts/run_m08_path_a_fan_bitstream.sh

The final line is CONDITIONAL ON YOUR REVIEW of the original single RTSTAT-10 warning. It never touches the KV260. Use no QSPI, SD, fancontrol, boot firmware, device tree, xmutil, /dev/mem or JTAG while performing these steps.

Expected success terminal marker ONLY if entire original preflight, genuine bitstream and independent audit pass:
M08_PATH_A_NEW_OFFLINE_FAN_BITSTREAM_SHA_AUDITED_NOT_PROGRAMMED

The output path is printed with M08_PATH_A_FAN_BITSTREAM_EVIDENCE_DIR. Preserve ORIGINAL source/route/bitstream evidence folders unchanged. On any failure, return only files that actually exist, particularly 01_preflight_console.log, 02_vivado_fan_bitstream.log, 03_fan_release_drc.rpt, 04_fan_release_timing.rpt, 07_audit_console.log and 08_evidence_sha256.txt. On success also supply 06_fan_bitstream_metrics.txt and 07_fan_bitstream_independent_audit.json; the large generated .bit may stay on the PC.

**LATER VERIFIED OWNER RESULT (2026-11-11):** The offline fan-preserving M08 bitstream WAS generated and is accepted as genuine native Vivado-only source evidence, not physical programming: actual uploaded 05_m08_path_a_fan_page.bit SHA 2d749451f46fe0660a9e78081cb6c92920a608ba16c084f37d2e1ab32f3e8af8, exact 7,797,831 bytes, all eight uploaded ledger-listed artifacts independently verified, vendor and auditor PASS. This earlier section's 'not yet implemented' language is historical. See [current owner-accepted bitstream and Linux REVIEW-ONLY staging](M08_2B_PATH_A_BITSTREAM_ACCEPTED_LINUX_STAGING_2026_11_11.md). No physical fan, Ubuntu PL image, or M08 AXI has been touched.

## After new offline bitstream (NOT yet implemented/authorized)

- Review genuine owner 2025.2 bitstream evidence and hardware fan pin against the running Ubuntu 24.04.2 K26 starter-kit overlay.
- Package distinct NEW Linux-managed firmware using real XRT_FLAT single-slot shell.json and ZynqMP fpga_full four-reset overlay, but do NOT clone unresolved 0xffffffff DTBO fixup placeholders. Need owned kernel/UIO bindings for separate 0xA0000000 and 0xA0001000 resources, not old AXI performance-monitor UIO nodes.
- Build an explicit thermal/power-safe live transition plan including a mechanism for fan cooling during the configuration gap, independent board evidence, and a rollback path before a first xmutil unload/load. A correct fan output pin does not guarantee continuous fan PWM during PL reconfiguration.
- After owner-approved live deployment, validate physical PS HPM0 AXI identity and all 64 independently compared page words (256 bytes), then COMMIT and rejected DISPATCH. Physical inference, DDR/DMA and benchmarks remain outside the accepted scope.

PR #83 stays draft and unmerged absent explicit approval.
