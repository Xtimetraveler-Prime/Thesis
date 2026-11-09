# M05.12d.4 — D4.2–D4.4 combined AXI evidence/verification

**2026-11-09 UTC — original user D4.1b Vivado 2025.2 PASSED its limited read-only gate; D4.2–D4.4 source implemented. Original combined owner D4.2–D4.4 run PENDING.** This is still M05.12d.4, NOT a new milestone. PR #79 draft/unmerged, M05 OPEN, M06 NOT STARTED. All accepted original PASS and FAIL folders remain immutable.

## Genuine D4.1b owner evidence accepted

The owner ran the new ORIGINAL Vivado read-only property probe:

    ~/Thesis_Evidence/neuromorphic_v1_m05_12d4_readonly_bd_20261109T154700Z_yG0IsT

Original D4.1b checkout 541cc1742c3d20493af381999366d94cf0cfa4a3; result exit_status=3. The 382 original generated-IP files and earlier 64 warnings were preserved and original provenance checked. The real read-only XPR/BD query completed and the independent actual 23 AXI interface/11 expected original net-pair audit passed. ctrl_sc NUM_SI=1 NUM_MI=6, mem_sc NUM_SI=4 NUM_MI=1, 256-bit four memory-DMA master/S00-S03 interfaces, 128-bit mem_sc M00 and PS HP0. Excerpted original control input ctrl_sc/S00_AXI is AXI4 128-bit/ADDR40/ID16/AWUSER16/ARUSER16, and the first control output is AXI4LITE 32b/no ID/USER/burst. The original independent four-OCM/DDR audit justifies classification only of the one exact OCM exclusion BD41-1629. The remaining 63 warnings include BD41-2384 payload-width internal truncations, BD41-237 USER discrepancies and BD41-3281 automatic configuration. The owner supplied excerpted readback and JSON, NOT full values for every mem_sc/PS property. DO NOT fill those missing values by inference or waive AXI status from an endpoint-property readback.

Prior genuine accepted folders:

    ~/Thesis_Evidence/neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ
    ~/Thesis_Evidence/neuromorphic_v1_m05_12d4_warning_inventory_20261109T152119Z_jBQsxu

## Implementation completed (one combined owner verification, no milestone sprawl)

**D4.2 original configuration risk review:** scripts/m05_12d4_protocol_risk.py authenticates all original D3 file products/hashes, the saved D4.1 64-row original inventory, and exact D4.1b original Vivado 23-endpoint raw report, independent JSON and source pre/post SHA manifest. It compares actual AWUSER/ARUSER/WUSER/BUSER/RUSER/ID, ADDR/DATA, burst, WSTRB, response and protocol properties over all 11 original interface pairs and emits full original warning-by-warning ledger. Exactly one original OCM exclusion is documented intentional, remaining 63 BLOCKED. Decision is NO_MUTATION_JUSTIFIED_FROM_CONFIGURATION_READBACK_ALONE. No AXI configuration, original signed32 HLS RTL or vendor output product changed.

**D4.3 independent source-only AXI byte oracle:** scripts/m05_12d4_axi_byte_oracle.py validates prospective vendor captures for legal 256-bit/32-byte-aligned upstream and 128-bit/16-byte-aligned downstream AXI4 INCR transactions. Asserts split high/low data and 32-bit→16-bit strobe masks, all active bytes, downstream contiguous segment lengths/addresses, 4-KiB burst boundary, last flags, RID/BID association and error response propagation. Checks an optional cycle-level AW/W/B/AR/R VALID/READY stall stability, handshake completeness, reset and watchdog. Supported test domain is deliberately limited; NO claim that unaligned/narrow/WRAP/concurrent ID-remapping is proven. Native tests include high-byte/drop/strobe/ID/response/last/4K/timeout corruption. These are SYNTHETIC HOST ONLY. The CLI refuses synthetic vendor PASS.

**D4.3 original vendor-model feasibility, NOT actual simulation:** scripts/m05_12d4_vendor_sim_feasibility.tcl opens only the exact previously accepted D3 XPR with open_project -read_only and queries sim_1, simulator name/top, simulation compile-order file objects containing mem_sc, and project sources. No launch_simulation, IP generate_target, project save, synthesis, bitstream, board access, or HDL edits. Independent strict parser scripts/m05_12d4_vendor_sim_readback_audit.py captures missing model/errors as BLOCKED, never silently treating model presence as a compiled/simulated SmartConnect. A genuine vendor simulation is still needed to classify AXI behavior.

**D4.4 source/evidence truth table:** scripts/m05_12d4_exit_audit.py checks the exact original D4.2 risk report, pre/post source SHA equality, and original D4.3 feasibility report. It records original gates and M05 acceptance explicitly: independently checked on-chip event-driven neural inference and counters WITHOUT dependence on DDR virtual paging. Does not use this source-only D4 probe to claim that M05 requirement is satisfied or start M06.

**Single owner runner:** scripts/run_m05_12d4_protocol_gate.sh takes the THREE genuine original evidence directories, builds a fresh evidence folder, runs risk audit before Vivado, runs real Vivado 2025.2 READ-ONLY simulation source discovery, rehashes original XPR/BD/source/report inputs, re-verifies all 382 original generated IP hashes afterward, reruns and compares the original risk report, then performs D4.4 exit truth-table audit. Successful collection returns **exit code 3** intentionally (protocol still BLOCKED); input/corrupted provenance/vendor error returns **exit code 2**. All original PASS/FAIL evidence preserved.

## Ubuntu VS Code terminal commands — ONE combined original read-only verification

    cd ~/Git/Thesis
    git status --short
    git fetch origin
    git switch agent/neuromorphic-accelerator-v1-m05-sparse-onchip
    git pull --ff-only origin agent/neuromorphic-accelerator-v1-m05-sparse-onchip
    git rev-parse HEAD
    cd Neuromorphic_Accelerator/v1
    python3 -m compileall -q src scripts tests
    python3 -m unittest discover -s tests -p 'test_m05_12d4*.py' -v
    python3 -m unittest discover -s tests -p 'test_m05_12d*.py' -v
    python3 -m unittest discover -s tests -p 'test_m05*.py' -q
    python3 -m unittest discover -s tests -p 'test_m04*.py' -q
    python3 -m unittest discover -s tests -p 'test_m03*.py' -q
    python3 -m unittest discover -s tests -p 'test_m02*.py' -q
    python3 -m unittest discover -s tests -p 'test_m01*.py' -q
    bash -n scripts/run_m05_12d4_protocol_gate.sh
    vivado -version

    export IP_D3="$HOME/Thesis_Evidence/neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ"
    export D4_OLD="$HOME/Thesis_Evidence/neuromorphic_v1_m05_12d4_warning_inventory_20261109T152119Z_jBQsxu"
    export D4_BD="$HOME/Thesis_Evidence/neuromorphic_v1_m05_12d4_readonly_bd_20261109T154700Z_yG0IsT"
    cat "$IP_D3/result.txt" "$D4_OLD/result.txt" "$D4_BD/result.txt"

    bash scripts/run_m05_12d4_protocol_gate.sh "$IP_D3" "$D4_OLD" "$D4_BD"
    echo "D4 exit=$?; 3 is expected bounded collection, 2 is a real verification failure"

    export D4_GATE="$(ls -dt "$HOME"/Thesis_Evidence/neuromorphic_v1_m05_12d4_protocol_gate_* | head -n 1)"
    echo "$D4_GATE"
    cat "$D4_GATE/commit.txt" "$D4_GATE/result.txt"
    cat "$D4_GATE/01_original_risk_audit.log"
    cat "$D4_GATE/05_model_discovery_audit.log"
    cat "$D4_GATE/09_m05_exit_audit.log"
    cmp "$D4_GATE/source_sha256.txt" "$D4_GATE/08_source_sha256_after.txt"
    head -n 100 "$D4_GATE/04_vendor_sim_sources.txt"
    tail -n 60 "$D4_GATE/03_vivado_sim_discovery.log"
    python3 -m json.tool "$D4_GATE/06_model_discovery_audit.json"
    python3 -m json.tool "$D4_GATE/09_m05_exit_audit.json"
    python3 -m json.tool "$D4_GATE/02_original_axi_risk.json" | head -n 80

Send this one run's ORIGINAL result, 01 risk and 05 model audit logs, 04 original Vivado simulator model report, 06 model audit JSON, 09 M05 exit audit JSON, and first actual error if any. No rerunning D3 output generation, no bitstream, PS Linux, JTAG, hardware manager, DDR writes or merge.

## Exact remaining boundary

Even if the consolidated original read-only discovery passes, full byte-level AXI conversion still requires a REAL supported AMD SmartConnect XSim simulation with authenticated vendor sources, checkable transactions and negative fault cases, or a documented unsupported-model blocker. The D4.3 source oracle is an independent reference, NOT a software substitute for real RTL. No known original generated payload field bit offsets have been proven safe to discard. M05 acceptance (independent on-chip neural run and counters against M02 oracle, no DDR virtualization) and owner authorization for closure remain separate. M06 NOT STARTED.

References for tool operation, not experimental evidence: AMD UG835 get_files -compile_order and open_project -read_only; UG900/UG939 2025.2 simulation source/model support.
