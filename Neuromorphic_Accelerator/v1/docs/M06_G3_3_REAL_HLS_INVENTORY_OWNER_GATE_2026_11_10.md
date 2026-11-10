# M06 G3.2 ACCEPTED / G3.3 genuine-HLS source inventory next owner gate — 2026-11-10 UTC

**Current state: G3.2 genuine original AMD XSim BFM-only PASS, G3.3 actual HLS-connected RTL NOT YET VERIFIED, G4 independent full neural/fault validation OPEN. M06 OPEN. PR #80 DRAFT/UNMERGED. No board, PS DDR, JTAG, M07 or merge authorization.**

## Accepted original G3.2 evidence — DO NOT RERUN

Owner supplied M06_G3_2_CORRECTED_XSIM_REVIEW_20261110T054830Z.zip, SHA256 b20d27fc6fc5ff9be5ec6ea78a03eb3baa99b563169185c41c7c178cc7c9b42f; owner original folder ~/Thesis_Evidence/m06_g3_real_dwc_original_sc_xsim_20261110T054742Z_LXrsEf, tested commit 9241042486981b8d83c978e6c3153460b64ebff1.

Actual genuine original AMD Vivado 2025.2 xvhdl/xvlog/xelab/xsim exited 0, original 2 x AMD 32→256 converters plus ORIGINAL 96-port D3 SmartConnect plus one corrected simulation-only RAM; PASS marker M06_G3_REAL_DWC_ORIGINAL_SC_32TO256_XSIM_PASS (write3 read10 M00 write3/read10, high byte65535, shared64K, NO_HLS_NO_BOARD_NO_DDR). Raw 126 AXI events verify ten SI32→MI256→SC M00 AR/R and three write AW/W/B at SI32, MI256, and M00. WSTRB at M00 for high-end sparse write=5000, remaining=000f/000f. First read0 value 382B1E11, final legal FFFC and 4KiB neighbors tested. All responses OKAY; zero observed DECERR. 67 vendor HDL SHA and five test-source SHA lines identical before/after, both genuine original AMD DWC XCI SHA checks OK. All original accepted G1/G2 experiments remain untouched.

New scripts/m06_g3_2_connected_evidence_audit.py independently audits that exact owner ZIP and emits a BFM-only JSON report. tests/test_m06_g3_2_connected_evidence_audit.py uses six synthetic positive/negative fixtures; those are NOT genuine original AMD simulation.

## Remaining G3.3 HLS integration requirements

Existing genuine owner G1 cosim folder: ~/Thesis_Evidence/m06_paged_rolling_hls_cosim_20261110T022111Z_iMNors, Vitis 2025.2. Genuine original AMD A–E G2 folder: ~/Thesis_Evidence/m06_original_vendor_mem_sc_xsim_20261110T013912Z_VZwFV2. Original D3, DWC and G3.2 passed files are reused READ-ONLY. The actual HLS top has 32-bit read and write AXI masters with 64-bit addresses, while original SC S00/S03 is 256b data and 32b addresses. Need real 64→32 guard placement, original DWC, exact ID/LOCK/USER/REGION sideband mapping, stream inputs and AXI-Lite control, cross-master write B→read AR fence. G3.2 BFM does not establish these, nor independent M02/M03 whole-state parity or fault quarantine.

New scripts/m06_g3_3_hls_inventory.py validates the real accepted G1/G2 evidence, source files and generated HLS top pins, accepted G3.2 ZIP, original D3 96 ports and measured original DWC 36/42 pins. Enumerates actual work/hls/syn/verilog Verilog files and hashes in a new metadata-only JSON. This is a READ-ONLY SOURCE INVENTORY; it does NOT compile/connect HLS into original AMD RTL or claim a neural XSim pass. Existing genuine Vitis HLS synthesis or cosim need not rerun. Fail closed on missing/changed originals.

## Exact VS Code terminal / source tests / ONE read-only owner gate

After pulling the current branch and checking git rev-parse HEAD against the latest response, work from ~/Git/Thesis/Neuromorphic_Accelerator/v1:

    python3 -m compileall -q src scripts tests
    bash -n scripts/run_m06_g3_3_hls_inventory.sh
    python3 -m unittest discover -s tests -p 'test_m06_g3_2_connected_evidence_audit.py' -v
    python3 -m unittest discover -s tests -p 'test_m06_g3_3_hls_inventory.py' -v
    python3 -m unittest discover -s tests -p 'test_m06*.py' -v

    export HLS="$HOME/Thesis_Evidence/m06_paged_rolling_hls_cosim_20261110T022111Z_iMNors"
    export AE="$HOME/Thesis_Evidence/m06_original_vendor_mem_sc_xsim_20261110T013912Z_VZwFV2"
    export D3="$HOME/Thesis_Evidence/neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ"
    export PORTS="$HOME/Thesis_Evidence/m06_vendor_xsim_port_contract_20261109T181345Z_f4X4Of"
    export DW="$HOME/Thesis_Evidence/m06_g3_real_amd_dwc_20261110T032341Z_YUDRD3"
    export G32="$HOME/Thesis_Evidence/M06_G3_2_CORRECTED_XSIM_REVIEW_20261110T054830Z.zip"
    export INVOCATION_LOG="$HOME/Thesis_Evidence/m06_g3_3_inventory_invocation_$(date -u +%Y%m%dT%H%M%SZ).log"
    if bash scripts/run_m06_g3_3_hls_inventory.sh "$HLS" "$AE" "$D3" "$PORTS/08_mem_sc_wrapper_headers_nonansi_fixed.json" "$DW" "$G32" "$PWD" 2>&1 | tee "$INVOCATION_LOG"; then
      echo "G3.3 read-only inventory exit0"
    else
      echo "G3.3 read-only inventory failed; preserve evidence"
    fi
    export LINK="$(find "$HOME/Thesis_Evidence" -maxdepth 1 -type d -name 'm06_g3_3_hls_source_inventory_*' | sort | tail -n 1)"
    echo "$LINK"
    test -d "$LINK" && cat "$LINK/result.txt" "$LINK/commit.txt"

Expected marker: M06_G3_3_REAL_HLS_RTL_INVENTORY_READY NOT_CONNECTED_NO_NEURAL_XSIM_OR_BOARD and result.txt exit_status=0. Do NOT call this a G3.3 XSim PASS. If fail, retain first failure; do not rerun original G1/G2/G3.2.

Package ONE ZIP under ~/Thesis_Evidence with Python zipfile, including whichever of these exist in the new LINK directory on PASS or FAIL: result.txt, commit.txt, worktree_status.txt, 00_g3_2_reaccepted.json, 01_g3_3_hls_interface_inventory.json, 02_inventory_console.log, source_before_sha256.txt, source_after_sha256.txt, original_hls_folder.txt, original_vendor_ae_folder.txt, original_d3_folder.txt, original_dwc_folder.txt, original_g3_2_zip_path.txt, original_g3_2_zip_sha256.txt; plus INVOCATION_LOG as 03_operator_invocation_console.log. Name: M06_G3_3_REAL_HLS_INVENTORY_REVIEW_<UTC_TIMESTAMP>.zip. The exact one-paste packager is provided in the accompanying chat handoff. No original proprietary AMD HDL/XCI required.

After this one source gate, develop a genuine original-AMD XSim harness with the ACTUAL generated HLS top and all supporting RTL, real 64→32 guarded address path and both original DWC, original D3 SC and shared memory; drive streams/AXI-Lite, compare full independently calculated trace and canonical neuron words, test B→AR coherence and G4 fault poisoning. No M06 closeout without owner acceptance.
