# M06 G3: genuine AMD dual-width-IP owner runbook and exact file handoff

Date: 2026-11-09 America/Denver. M06 OPEN; PR #80 DRAFT/UNMERGED. G1 corrected generated-HLS C/RTL cosim PASS, G2 original AMD SmartConnect A-E functional XSim PASS and owner G3 source gates PASS, G3 actual HLS+original SmartConnect combined RTL NOT RUN, G4 numerical/fault acceptance OPEN.

## These four actual owner files are correct and fully reviewed

- m06_g3_input_gate_20261110T024845Z_6262.json: corrected real HLS C/RTL cosim commit fa9b8c3f1254ce397f8d2757c26ab5f0c1ec57a2, generated RTL SHA 80af15cb119d25e76a2ce8a4da9ffde6dbfaf940318bb2f800469dce36e03860, 40 generated RTL sources, original vendor Stage E SHA cdad7f21179da5e3126c63ff4d1f9988337fe8231997a9f9e0bd03045f234582, explicit NOT_CONNECTED and cross-master B->AR NOT_PROVEN.
- m06_g3_pin_matrix_20261110T024854Z_6262.json: 125 real HLS pins versus original AMD 96 wrapper AXI ports, HLS two 32-bit memory AXI masters with 64-bit addresses, original S00/S03 256-bit data and 32-bit addresses. Original S00/S03 have no IDs while HLS exposes 1-bit IDs; HLS ARLOCK/AWLOCK 2 bits vs original 1 bit; user/region and other sideband handling must be decided and tested. No raw truncation.
- m06_paged_rolling_replay_csynth.rpt: corrected REAL Vitis 2025.2 HLS whole-top estimates 104 BRAM18K, 2 DSP, 17,390 FF, 22,888 LUT, 8.8 ns estimated period, unknown overall latency. Historical pre-alias baseline was 42 BRAM18K, 2 DSP, 9,820 FF, 12,913 LUT. Delta +62 BRAM18K, +7,570 FF, +9,975 LUT. Resource regression needs separate explanation/performance review; this is not post-route timing or physical board use.
- m06_paged_rolling_replay_cosim.rpt: genuine xsim Verilog PASS, min/avg/max latency 3/5170/12594 cycles, interval 26/6921/12629 cycles, 20768 total cycles for tested transactions. These are testbench-dependent, not steady-state inference throughput.

## New concrete G3 increment: ORIGINAL AMD Data Width Converter IP generation

scripts/m06_g3_generate_amd_dwc.tcl: genuine Vivado 2025.2 scratch project creating exactly two AMD axi_dwidth_converter cores, read-only and write-only roles, AXI4, SI data32/MI data256, SI_ID_WIDTH1, address32, FIFO_MODE0. IP is created OUTSIDE existing D3, with exact parameter readback and rejection of unsupported property. Does NOT yet link to genuine HLS, original SmartConnect, 64-to-32 guarded address path, or shared scratch memory. No XSim claim.

scripts/run_m06_g3_amd_dwc_ip.sh: unique evidence directory under ~/Thesis_Evidence/m06_g3_real_amd_dwc_*, original Vivado v2025.2 check, owner SHA/commit, new project, original XCI path and digest inventory, no board/JTAG/DDR/bitstream. scripts/m06_g3_amd_dwc_evidence_audit.py validates source manifests, exact two genuine IP identities and readback and GENERATED_ONLY scope; seven synthetic tests in tests/test_m06_g3_amd_dwc_evidence_audit.py cover negative forged roles, width, ID, SHA, missing IP, run failure and false integration claim. CI source-only is not an actual IP/XSim result.

## Exact next owner commands

    cd ~/Git/Thesis
    git status --short
    git fetch origin
    git switch agent/neuromorphic-accelerator-v1-m06-ddr-residency
    git pull --ff-only origin agent/neuromorphic-accelerator-v1-m06-ddr-residency
    git rev-parse HEAD
    cd Neuromorphic_Accelerator/v1
    python3 -m compileall -q src scripts tests
    python3 -m unittest discover -s tests -p 'test_m06_g3_amd_dwc_evidence_audit.py' -v
    python3 -m unittest discover -s tests -p 'test_m06*.py' -v
    source "$HOME/Vivado/2025.2/Vivado/settings64.sh"
    vivado -version
    bash scripts/run_m06_g3_amd_dwc_ip.sh
    echo "Original AMD DWC generation exit: $?"
    export DW="$(find "$HOME/Thesis_Evidence" -maxdepth 1 -type d -name 'm06_g3_real_amd_dwc_*' | sort | tail -n 1)"
    echo "$DW"
    cat "$DW/result.txt" "$DW/commit.txt"
    test -f "$DW/02_amd_dwc_configuration.tsv" && cat "$DW/02_amd_dwc_configuration.tsv"

When result is exit_status=0:

    python3 scripts/m06_g3_amd_dwc_evidence_audit.py --evidence "$DW" --output "$HOME/Thesis_Evidence/m06_g3_amd_dwc_audit_$(date -u +%Y%m%dT%H%M%SZ)_$$.json"

## Only files needed next: ONE ZIP at ~/Thesis_Evidence/M06_G3_AMD_DWC_IP_REVIEW.zip

Pack from the freshly generated $DW folder:
1. result.txt
2. commit.txt
3. vivado_version.txt
4. 01_vivado_amd_dwc.log
5. 02_amd_dwc_configuration.tsv
6. 03_real_amd_dwc_xci_paths.txt
7. 04_real_amd_dwc_xci_sha256.txt

On PASS include newest separate audit JSON m06_g3_amd_dwc_audit_*.json in ~/Thesis_Evidence. If original Vivado generation fails, include all existing files from that same list and the first failing 01_vivado_amd_dwc.log. Do not modify or rerun first failed evidence until diagnosis; preserve original D3. No proprietary XCI/Vendor RTL upload needed at this phase. Exact ZIP packaging command is provided in user-facing answer.

## Next engineering gate after real IP generation

Build a genuine 2025.2 owner XSim bench with REAL corrected generated HLS top, TWO generated AMD width IPs, protected 64:32 address mapping (out-of-window DECERR; no unchecked truncation), explicit ID/LOCK/USER/REGION treatment, original authenticated D3 S00 READ and S03 WRITE and common simulated 64KiB canonical memory. Assert AW/W/B, AR/R, address and WSTRB, 4KiB boundary, stalls, error propagation, write B completion BEFORE cross-master reload. G4 then must use independent M02/M03 exact 16-byte state and neural trace, dirty eviction/reload, timeout/error/quarantine. No M06 closeout, PR merge, M07 or physical use without owner approval.
