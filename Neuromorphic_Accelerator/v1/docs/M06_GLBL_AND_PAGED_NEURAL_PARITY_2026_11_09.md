# M06 — genuine AMD XSim glbl fix and paged signed16 neural RTL evidence

Date: 2026-11-09. Branch: agent/neuromorphic-accelerator-v1-m06-ddr-residency. PR #80: DRAFT, UNMERGED. NO PHYSICAL BOARD.

## Owner evidence: farther than previous run

The original 2025.2 vendor XSim run in the owner directory named m06_original_vendor_mem_sc_xsim_20261109T204824Z_1o9BR9 returned exit_status=1, but the new original-AMD compile plan succeeded. The owner supplied 02_compile_plan.log, 03_xvlog.log, 04_xelab.log and result.txt. Original xvlog compiled all 56 original vendor RTL compilation sources and both M06 testbench modules. Thus the prior missing axi_infrastructure_v1_1_0.vh problem is RESOLVED.

The first and only fatal cause is now xelab STATIC ELABORATION: VRFC 10-2989, glbl is not declared, in the installed AMD XPM xpm_cdc.sv. The earlier invocation elaborated only work.tb_m06_original_mem_sc_vendor. Nothing reached actual xsim simulation; zero original AMD AXI transaction PASS claims are made. The LIBRARY_PATH warning was not the observed fatal cause and is not being reinvestigated.

Fix: the runner requires and authenticates the actual installed Vivado 2025.2 glbl.v from the XILINX_VIVADO environment, saves its SHA256 and path in each new evidence folder, compiles it through xvlog, and uses TWO elaboration roots for BOTH vendor snapshots: work.<bench> work.glbl. AMD UG900 supports multiple xelab top design units. No source stub or original vendor IP edits were introduced.

## Additional real RTL development: M02 neural arithmetic THROUGH paging

rtl/m06/m06_lif16_neuron_step.sv implements an independent M02 rev1 16-bit LIF arithmetic lane: signed previous voltage, truncation-toward-zero rational decay, signed32 summed current, signed16 saturation BEFORE inclusive threshold test, and reset on spike. It rejects invalid decay/threshold parameters. This is a synthesis-oriented candidate arithmetic unit; dynamic division cost is not yet measured. It is NOT the accepted M05 HLS neural top.

scripts/m06_generate_paged_lif16_vectors.py generates four ticks of 32 logical neuron events, recurrent deliveries and golden results from the independent M02 dense oracle. The event currents are PRECOMPUTED (there is no RTL event router). Fixtures include positive/negative signed16 saturation, cancellation of two independent opposite signed currents, recurrence, delay2 self-edge, bias and negative states.

rtl/m06/tb_m06_paged_lif16.sv combines that actual LIF arithmetic lane with the existing synthesis-oriented RTL 256B AXI block transfer mover and one-slot residency FSM, plus an independent mock canonical-memory RTL BFM. State records hold signed16 voltage at bytes 0:1 and a last-completed tick counter at bytes 2:5 inside the original 16-byte neuron record. Each 256-byte block has 16 neurons. Two blocks must share just ONE resident block, forcing eviction and restoration every logical tick. The bench checks EVERY computed voltage and spike against dense M02 values, and each neuron-state update's byte strobes/metadata; it checks final canonical state after writebacks and both reloads. A downstream injected read error must fail-close into sticky poison.

Real independent Icarus RTL CI PASS (after extending negative and saturation fixtures):
M06_PAGED_LIF16_M02_RTL_PARITY_PASS neurons=32 ticks=4 updates=128 spikes=8 fills=10 wb=8 ar=80 aw=64 resident_slots=1 ORIGINAL_M05_HLS_NOT_CONNECTED
M06_PAGED_LIF16_FAULT_QUARANTINE_PASS no_real_DDR=1

M06 source-only regression methods 124 PASS and inherited M05 430 tests PASS at checkpoint 425b4d3389a75fc017db0ce40d8d768cebdb85fb, and other M06 RTL tests remain PASS. These results are NOT original AMD XSim, real DDR, real M05 event RTL, 8-slot residency or FPGA timing.

## NEXT OWNER: one original vendor XSim invocation, no project changes and NO BOARD

Run in VS Code terminal:

    cd ~/Git/Thesis
    git status --short
    git fetch origin
    git switch agent/neuromorphic-accelerator-v1-m06-ddr-residency
    git pull --ff-only origin agent/neuromorphic-accelerator-v1-m06-ddr-residency
    git rev-parse HEAD
    cd Neuromorphic_Accelerator/v1
    python3 -m unittest discover -s tests -p 'test_m06*.py' -q
    bash -n scripts/run_m06_original_mem_sc_vendor_xsim.sh

    # If not already sourced, use local installed 2025.2 settings:
    source "$HOME/Vivado/2025.2/Vivado/settings64.sh"
    xvlog -version
    echo "$XILINX_VIVADO"
    test -f "$XILINX_VIVADO/data/verilog/src/glbl.v"

    export D3="$HOME/Thesis_Evidence/neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ"
    export PORTS="$HOME/Thesis_Evidence/m06_vendor_xsim_port_contract_20261109T181345Z_f4X4Of"

    bash scripts/run_m06_original_mem_sc_vendor_xsim.sh "$D3" \
      "$PORTS/02_original_mem_sc_ports.txt" \
      "$PORTS/08_mem_sc_wrapper_headers_nonansi_fixed.json"
    echo "Original XSim exit: $?"

To extract:

    export RUN="$(find "$HOME/Thesis_Evidence" -maxdepth 1 -type d -name 'm06_original_vendor_mem_sc_xsim_*' | sort | tail -n 1)"
    echo "$RUN"
    cat "$RUN/result.txt" "$RUN/commit.txt"
    cmp "$RUN/sha_before.txt" "$RUN/sha_after.txt"
    cat "$RUN/installed_vivado_glbl_path.txt" "$RUN/installed_vivado_glbl_sha256.txt"
    grep -E 'M06_ORIGINAL_SMARTCONNECT_VENDOR_XSIM_PASS|M06_ORIGINAL_VENDOR_PAGED_|M06_VENDOR_FAIL|M06_ORIGINAL_PAGED_FAIL|ERROR:|FATAL' \
      "$RUN/04_xelab.log" "$RUN/05_xsim.log" "$RUN/06_paged_xelab.log" "$RUN/07_paged_xsim.log" 2>/dev/null | tail -n 70 || true
    tail -n 40 "$RUN/03_xvlog.log" 2>/dev/null || true

Upload result.txt and the LAST nonempty failed stage log. If BOTH real vendor stages succeed, upload 05_xsim.log and 07_paged_xsim.log. The runner always writes a new evidence folder and hashes original vendor sources before and after; never overwrite the prior failed run.

Optional local neural RTL-only verification when iverilog/vvp are installed:

    TMP="$(mktemp -d)"
    python3 scripts/m06_generate_paged_lif16_vectors.py --output "$TMP/m06_lif16_vectors.vh"
    iverilog -g2012 -I "$TMP" -s tb_m06_paged_lif16 -o "$TMP/neural.vvp" \
      rtl/m06/m06_lif16_neuron_step.sv rtl/m06/m06_residency_control_fsm.sv \
      rtl/m06/m06_axi256_block_transfer.sv rtl/m06/tb_m06_paged_lif16.sv
    vvp "$TMP/neural.vvp"

## Milestone acceptance remains OPEN

Real original vendor 2025.2 XSim stage A (byte/response/downsizing) and B (256-byte neural state block eviction/reload through vendor AXI) are still NOT RUN following the glbl fix. After those gates, M06 closure still requires integration of the accepted M05 HLS/event-execution kernel to the paged state path and numerical trace parity under forced evictions (the standalone independent arithmetic lane is NOT that kernel), and complete intended 8-slot/2048B bounded on-chip residency geometry and canonical 4096-neuron mapping as appropriate. Actual PS/DDR ownership/board operations remain separately unauthorized. No warnings investigation and no M07 start.
