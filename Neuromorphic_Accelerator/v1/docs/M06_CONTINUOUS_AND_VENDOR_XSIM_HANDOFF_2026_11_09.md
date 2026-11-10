> **IMPORTANT NEWER ORIGINAL VIVADO CORRECTION, 2026-11-09:** The actual owner D3 port report contradicts this older handoff's generic four 256-bit read/write input assumption. S00-S02 are READ_ONLY, S03 is WRITE_ONLY; SI HAS_BURST=0 MAX_BURST_LENGTH=16; M00 is READ_WRITE 128b MAX32. The original port run resulted exit_status=2 despite Vivado completing 186-source query, due probable Tcl-echo success-marker audit bug; do not claim original port audit PASS without owner offline re-audit. The prior six-case BFM input plan was superseded with nine role-safe cases; one independent actual Icarus RTL 128b scratch target test passed (NO original SmartConnect IP). **LATEST authoritative owner commands, exact original folder, fixed auditor and wrapper extraction:** [M06 original port role correction and no-Vivado recovery](M06_ORIGINAL_MEM_SC_ROLE_CORRECTION_AND_REAUDIT_2026_11_09.md). Do NOT rerun the older original Vivado port probe unnecessarily or feed S00-S02 writes to real vendor IP.

# M06 — continuous software paging and original-memory-IP simulation handoff

**2026-11-09. M06 IN PROGRESS, draft PR #80, no physical hardware.** Owner's last reported verification had all 67 prior M06 tests, 430 M05 tests, M01–M04 regression tests and 12 matched locality source models PASS. Source development continues on the same existing M06 branch and does NOT re-open M05 or add numbered submilestones.

## New completed source development

1. Multi-window paged recurrent neural execution: src/neuromorphic_accelerator_v1/m06_continuous_paging.py carries active-neuron eligibility and future-dated individual recurrent deliveries ACROSS consecutive 1..64-tick windows. Every evaluated signed16 neuron voltage is read/written through the bounded M06 LRU block cache, including last-update timestamp bytes in >=6-byte records. Up to 256 logical ticks are permitted in this SOFTWARE research model only; the original M05 synthesized rolling kernel remains physically unmodified and capped at its original 64-tick invocation. Source tests compare full 80/128/256-tick traces to independent M02 dense/event and M03 sparse references, with recurrent delay 8 crossing the t=63 window boundary.
2. Multi-window shadow epochs: m06_shadow_epoch.py adds a run_windowed method. All windows execute through the software AXI behavioral cache on a separate SHADOW canonical image. The original canonical image is published in software only after complete independent M02 full-trace and voltage/timestamp verification. A fault at any point aborts without publishing the shadow image. This does NOT implement physical multi-page DDR atomicity, crash recovery, or device restart.
3. Exact-original memory SmartConnect SIMULATION-BFM PORT CAPTURE: scripts/m06_original_mem_sc_ports.tcl, scripts/run_m06_original_mem_sc_port_contract.sh and scripts/m06_original_mem_sc_contract_audit.py. This is a single read-only REAL Vivado 2025.2 original-XPR/BD endpoint/simulator-source query designed to extract precise module/port details so we can wire an actual vendor-generated 256-to-128-bit AXI functional test. It explicitly does NOT inventory warnings, change the original saved project, run XSim, synthesize, program hardware, or access DDR. A successful port capture is NOT a functional vendor-IP PASS.
4. Directed future REAL XSim stimulus: scripts/m06_vendor_axi_directed_vectors.py generates six HOST-ONLY independently predetermined byte/strobe read/write cases: S00/S01/S02/S03 individually, 256-byte masked WRITE-then-READ, low/high 128-bit halves, legal split at 4KiB, and the 128-upstream/256-downstream beat limit. Physical addresses are NOT selected; all are abstract BFM memory offsets. These vectors will be checked against ACTUAL vendor IP signals in the next separate functional XSim test.
5. Added 11 continuous neural tests, 8 original-port-auditor synthetic/negative tests, and 6 independent BFM stimulus tests = **25 new tests** on top of the previously accepted 67, for **92 M06 host methods**. This total is subject to final GitHub CI confirmation at exact branch HEAD. Synthetic fixture inputs NEVER substitute for genuine Vivado port data or vendor simulation.

## NEXT OWNER ACTION: one original Vivado 2025.2 read-only simulation PORT capture

This run is needed to construct the genuine original mem_sc functional XSim BFM with ACTUAL signal/sideband widths and module names; it is not another SmartConnect warning investigation. It uses the accepted D3 evidence folder and creates a NEW isolated M06 evidence folder. The original XPR/BD/manifest SHA256 are compared before and after. No board connection or JTAG is required.

Run in VS Code Ubuntu terminal after sourcing the usual Vivado 2025.2 settings:

    cd ~/Git/Thesis
    git status --short
    git fetch origin
    git switch agent/neuromorphic-accelerator-v1-m06-ddr-residency
    git pull --ff-only origin agent/neuromorphic-accelerator-v1-m06-ddr-residency
    git rev-parse HEAD

    cd Neuromorphic_Accelerator/v1
    python3 -m compileall -q src scripts tests
    python3 -m unittest discover -s tests -p 'test_m06*.py' -v
    bash -n scripts/run_m06_original_mem_sc_port_contract.sh
    vivado -version

    export D3="$HOME/Thesis_Evidence/neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ"
    cat "$D3/result.txt"
    bash scripts/run_m06_original_mem_sc_port_contract.sh "$D3"
    echo "M06 port-capture exit code: $?"

    export PORTS="$(ls -dt "$HOME"/Thesis_Evidence/m06_vendor_xsim_port_contract_* | head -n 1)"
    echo "$PORTS"
    cat "$PORTS/commit.txt" "$PORTS/result.txt"
    cmp "$PORTS/01_original_source_sha256.txt" "$PORTS/04_original_source_after_sha256.txt"
    grep -E '^(MEM_IP_|ENDPOINT|ENDPOINT_PROPERTY|SIM_QUERY|SIM_SOURCE|RESULT)' "$PORTS/02_original_mem_sc_ports.txt" | head -n 100
    python3 -m json.tool "$PORTS/05_sim_bfm_contract_summary.json"
    tail -n 80 "$PORTS/03_vivado_readonly.log"

Share the THREE original M06 outputs: (1) 02_original_mem_sc_ports.txt, (2) 05_sim_bfm_contract_summary.json, (3) 03_vivado_readonly.log, plus result.txt/commit.txt. If the original read-only probe fails, share the same files that exist and the FIRST error in the log; do not retry automatically. If success, port-capture exit_status=0 means only ports/models DISCOVERED; the actual vendor AXI simulator has NOT executed.

Generate non-Vivado expected transaction vectors in a fresh, exclusive JSON file:

    python3 scripts/m06_vendor_axi_directed_vectors.py \
      --output "$HOME/Thesis_Evidence/m06_vendor_expected_vectors_$(date -u +%Y%m%dT%H%M%SZ)_$$.json"

No existing owner reports or vendor files are overwritten.

## After original module/port readback — one real functional XSim acceptance gate

Build a separate testbench for the actual ORIGINAL saved Vivado 2025.2 generated memory SmartConnect model (not a guessed 1-SI replacement), a 128-bit behavioral memory endpoint, and four 256-bit AXI masters. Test real byte/WSTRB integrity, legal burst size/4KiB splitting, deterministic AR/R and AW/W/B stalls, independent response and ID/USER handling and timeout/failure quarantine. Compare real accepted handshakes and byte arrays to the committed source-only golden vectors and preserve all raw simulator logs in new evidence. This true vendor functional test is NOT yet implemented or run; exact generated module/port data is the necessary boundary.

**M06 remains OPEN; PR #80 stays DRAFT/UNMERGED.** Original 63 SmartConnect warnings remain UNWAIVED but there will be NO repeated warning inventory in this handoff. No PS DDR ownership, Linux MMIO, FPGA bitstream, JTAG or actual physical memory access is authorized. After genuine vendor simulation passes, develop real transfer/paging control and independently verify state correctness across evictions. Remaining hardware gaps include synapse residency, persisted event queues across independent resets, physical crash-safe commit, and full integrated routed timing.
