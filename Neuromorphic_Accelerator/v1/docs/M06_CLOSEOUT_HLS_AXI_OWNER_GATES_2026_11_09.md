> **LATEST REAL OWNER EVIDENCE/ENGINEERING BOUNDARY:** M06 G3 genuine owner 2026-11-09 Vivado 2025.2 lock/export-simulation boolean-error (failed exit1) diagnosed from exact zipped log+journal+13-source simulation compile-order TSV. READ DWC real source enumeration succeeded; standalone `export_simulation` errored internally. Removed export_simulation from future owner source gathering; retain original project `-read_only`, query real Vivado compile order for both READ and WRITE, independently SHA/ABI audit using new test+script. Need new owner run of compile-order only to confirm BOTH IPs; no repeat original DWC generation/HLS cosim/vendor A-E. G3 connected full HLS+DWC+original SmartConnect XSim and G4 independent complete trace/state/fault still OPEN; no board/DDR/JTAG, PR #80 draft/unmerged. Docs M06_G3_REAL_EXPORT_BOOLEAN_FAIL_AND_COMPILE_ORDER_FIX_2026_11_09.md.

> **LATEST ENGINEERING STATUS:** M06 G3 update 2026-11-09: AMD original dual width-converter 32:256 genuine Vivado 2025.2 generation now PASS, owner ZIP m06_G3 AMD DWC readback two XCI SHA and sources match. New actual candidate 64:32 bounded AXI read/write guards with DECERR and sticky poison, Icarus RTL regression tests, plus owner read-only official AMD DWC XSim script/compile-order+SIM module pin exporter. Genuine vendor converters generated but NOT yet individually run through AXI, original HLS to original SmartConnect NOT connected, no original vendor XSim on combined chain, G4 neuron M02/M03 fault acceptance still NOT tested. Source/test claims are strictly scoped. Next owner exact source export ZIP: docs/M06_G3_REAL_DWC_PASS_GUARD_AND_XSIM_EXPORT_OWNER_RUNBOOK_2026_11_09.md. M06 OPEN, PR #80 draft/unmerged, no board/JTAG/PS DDR or M07.

> **LATEST CORRECTION:** G3 CURRENT original Vivado DWC trial at 2026-11-09 20:11 local FAILED exit1 from our own Tcl get_files -of_objects $ip lookup assumption; owner original directory m06_g3_real_amd_dwc_20261110T031107Z_linVJf immutable. Fixed with exact checked scratch-project .xci file path, independent audit plus source SHA and real tclsh synthetic negative tests. Owner must rerun new Vivado IP generation; this is NOT vendor converter IP PASS yet, and the genuine HLS->original SmartConnect integrated G3/G4 remain open. G1 real HLS cosim and G2 original vendor A-E functional pass remain accepted at their standalone scopes. See docs/M06_G3_ORIGINAL_AMD_XCI_LOOKUP_FAILURE_AND_FIX_2026_11_09.md.

> **G3 ORIGINAL AMD DWC OFFLINE IP GENERATION EXPERIMENT READY (NOT EXECUTED), 2026-11-09:** User supplied both verified JSON G3 inputs and exact 125-HLS/96-original-vendor pin matrix, plus corrected real Vitis 2025.2 full HLS report (104 BRAM18K/17,390 FF/22,888 LUT/2 DSP; historical pre-alias 42/9,820/12,913/2) and cosim Verilog PASS (20,768 cycle total over test transactions). No files missing. G3 real 32→256 width conversion, guarded 64→32 address, absent original S00/S03 IDs, LOCK 2→1, USER/REGION and B→AR ordering all STILL UNPROVEN. New owner-executable original Vivado 2025.2 AMD 2× axi_dwidth_converter **scratch** IP generator (scripts/m06_g3_generate_amd_dwc.tcl, scripts/run_m06_g3_amd_dwc_ip.sh), independent m06_g3_amd_dwc_evidence_audit.py and 7 synthetic tests; actual AMD width-IP vendor generation must run on owner and its files reviewed before G3 combined XSim. [Current owner commands / exact ZIP handoff](M06_G3_REAL_AMD_WIDTH_IP_OWNER_RUNBOOK_2026_11_09.md). G1/G2 component PASS, G3/G4 OPEN; no real DDR/board/JTAG or merge/M07.

> **UPDATED M06 CLOSEOUT 2026-11-09: G1 GENUINE VITIS C/RTL COSIM NOW PASS, G2 STAGE E FUNCTIONAL PASS, G3/G4 OPEN.** Corrected owner Vitis `--cosim` evidence `m06_paged_rolling_hls_cosim_20261110T022111Z_iMNors` original source SHA match, genuine real RTL XSim 4/4 transactions, `COSIM 212-1000 PASS`, exit0; earlier failed cosim is historical. Original AMD 5-stage A-E XSim functional PASS under 64KiB simulated scratch; live D3 original source rehash pending. New full-neural-top HLS report uploaded (ORIGINAL pre-alias synth baseline): **42 BRAM18K, 2 DSP, 9,820 FF, 12,913 LUT, 8.8ns estimate**, unknown whole latency; corrected cosim run produces own top report for updated measurement. G3 HLS-generated two 32-bit DATA/64-bit ADDRESS m_axi masters cannot directly connect original 256-bit DATA/32-bit ADDRESS original S00/S03; proper AMD data width conversion plus guarded 64→32 address translation and ID/sideband handling needed. Added genuine source/HLS/Stage A-E input readiness `m06_g3_original_link_inputs.py`, full actual HLS/header original 96-pin gap inventory `m06_g3_exact_original_pin_matrix.py`, host-only byte-lane/B→AR oracle `m06_axi32_to256_byte_oracle.py`, and 18 synthetic/negative test methods. **These are source-only scaffolding NOT actual linked original vendor XSim**, G3 and G4 remain open. See [real new owner original files / next exact commands](M06_G3_REAL_OWNER_INPUTS_AND_EXACT_PORT_MATRIX_2026_11_09.md). No board/DDR/M06 merge/M07.

> **ACTUAL G1 COSIM FAILURE + NEW SOURCE CORRECTION, 2026-11-09 19:03 local:** Original uploaded Vitis 2025.2 `--cosim` folder exit1: C testbench instrumentation fails FIRST high-offset scenario (`COSIM 212-359`), no RTL XSim vectors/simulation, so no RTL equivalence PASS/FAIL. Original independent HLS CSim+synth still passed; uploaded independent RTL-port JSON gives real HLS m_axi widths 32b READ + 32b WRITE, 64b addresses against original 256b S00/S03. Stage E original-vendor A–E PASS evidenced by full owner archive matching SHA manifests, five genuine XSim logs; live original D3 rehash still pending. New M06 HLS source adds AMD-documented zero-distance ALIAS for the two pointers + testbench failure diagnostics and five source-only positive/negative tests; **NOT YET TRIED IN GENUINE VITIS**. Rerun only fresh `--cosim` and source hashes; then if PASS independently audit new generated top pins; Stage E needs no rerun. Top HLS resources report required `m06_paged_rolling_replay_csynth.rpt`; uploaded `Pipeline_VITIS_LOOP_356_14_csynth.rpt` is just its helper pipeline (II64). See [full real owner cosim error and targeted source trial](M06_OWNER_COSIM_FAIL_AND_ALIAS_NEXT_GATE_2026_11_09.md). G3 actual HLS IP SmartConnect, G4 numeric/failure acceptance still OPEN, no board/M06 closeout/merge/M07.

> **NEW OWNER ORIGINAL AMD STAGE E FUNCTIONAL PASS (2026-11-09 18:41 local time):** Owner excerpt from `m06_original_vendor_mem_sc_xsim_20261110T013912Z_VZwFV2`: `M06_ORIGINAL_VENDOR_4096_RANGE_PASS highest_page=255 last_neuron=4095 last_byte=65535 dirty_wb=1 M00_write=16 M00_read=48`, `M06_ORIGINAL_VENDOR_4096_OUT_OF_RANGE_QUARANTINE_PASS block256_rejected=1 no_physical_DDR=1`, actual XSim exit0 and A–E runner exit0. Original source pre/post manifest, original owner commit, raw run-wide logs not supplied yet: functional Stage E PASS based on reported excerpt, COMPLETE PROVENANCE AUDIT PENDING. New independently coded read-only `m06_original_stage_e_evidence_audit.py` plus six positive/negative synthetic tests validates owner files without rerun. [Actual evidence and next gate commands](M06_STAGE_E_OWNER_RESULT_AND_BINDING_HANDOFF_2026_11_09.md). **Remaining G1 real HLS cosim result UNKNOWN (user says they ran it, logs not supplied), G3 actual generated-HLS to original AMD S00/S03 integrated function and G4 M02 exact connected RTL/fault acceptance OPEN; no M06 merge or M07.** Historical Stage E NOT RUN language below is superseded.

> **NEW OWNER GENUINE VITIS RESULT / SUPERSEDES OLD SYNTH PENDING STATUS (2026-11-09 18:07 America/Denver):** First real owner `--synth` output is now available and PASS: `result.txt exit_status=0`, genuine Vitis 2025.2 CSim zero errors and `M06_PAGED_ROLLING_HLS_CSIM_PASS`, genuine Vitis 2025.2 synthesis emitted Verilog, inferred `page_words` BRAM, distinct `gmem_read`/`gmem_write` M_AXI, estimated Fmax **113.64 MHz**. Independent generated RTL header audit returned PASS. **NOT received:** actual port JSON/data widths, synthesis `*_csynth.rpt` resource/whole top latency, owner `commit.txt`, source SHA `cmp`. Warnings init II4, final flush II64 and unsatisfied loops merit latency review, not synthesis rejection. New `m06_paged_hls_axi_link_plan.py` produces only a read-only measured-width NOT_CONNECTED plan (6 synthetic positive/negative regression tests). **Original AMD Stage E and genuine HLS C/RTL cosim NOT RUN, original SmartConnect integration NOT VERIFIED, M06 OPEN.** [Full actual source/evidence review and next G1–G4 gates](M06_OWNER_VITIS_SYNTHESIS_READBACK_AND_OPEN_GATES_2026_11_09.md). All older "Vitis NOT RUN" sections below are historical snapshots, not the live status. PR #80 stays draft, no physical/PS-DDR/JTAG or M07.

> **LATEST CANONICAL NEXT-CHAT HANDOFF AND OWNER COMMANDS (2026-11-09, docs-only continuation):** [docs/M06_NEXT_CHAT_HANDOFF_2026_11_09.md](M06_NEXT_CHAT_HANDOFF_2026_11_09.md) supersedes older statements that C/D still need owner verification. It precisely distinguishes original AMD vendor **A/B PASS**, owner **C/D exit0 with missing local run-wide commit/hash evidence**, and future **Stage E NOT RUN**. It also distinguishes native g++ `m06_paged_rolling_replay` parity from original **Vitis 2025.2 --synth/--cosim NOT RUN**; first new operator step is `bash scripts/run_m06_paged_rolling_hls.sh --synth` then header/port audit on genuine success, and independent original-vendor Stage E. Source current at 1e1a76ae (all six CI PASS, M06 158 native methods), next commit docs only. M05 PR #79 MERGED to main, M06 draft PR #80 open; no board/DDR/JTAG, no M07 and no M06 closeout until genuine remaining gates pass. Preserve original owner evidence and all existing detailed commands below.

# M06 closeout candidate: genuine original vendor C/D PASS; paged autonomous M05 HLS top + 4096-address gate staged

Date: 2026-11-09. Track: Neuromorphic_Accelerator/v1 M06. Current PR #80 DRAFT/UNMERGED. **M06 not yet CLOSED.** No M07 start, physical board/JTAG/PS DDR operations or destructive image changes are authorized.

## Owner original AMD SmartConnect acceptance — 4 real XSim stages passed

New owner run original directory:
`~/Thesis_Evidence/m06_original_vendor_mem_sc_xsim_20261109T225500Z_Q55EJq` (the operator's existing run, NEVER overwrite). User sent `result.txt`, `09_neural_paged_xsim.log` and `11_lru8_xsim.log`. Result is `exit_status=0`, both logs from xsim v2025.2 and `exit 0`:
- Stage C: `M06_ORIGINAL_VENDOR_NEURAL_PAGED_M02_PARITY_PASS neurons=32 ticks=4 updates=128 spikes=8 fills=10 wb=8 M00_write=128 M00_read=160 ORIGINAL_M05_HLS_NOT_INSTANTIATED`; `M06_ORIGINAL_VENDOR_NEURAL_PAGED_FAULT_PASS`. Actual AMD SmartConnect + one-slot M06 resident page/mover + independent signed16 neural-step RTL, benchmark currents computed outside RTL from M02 reference.
- Stage D: `M06_ORIGINAL_VENDOR_LRU8_RTL_PASS slots=8 resident_bytes=2048 fills=19 evictions=11 dirty_wb=2 M00_write=32 M00_read=304`; `M06_ORIGINAL_VENDOR_LRU8_FAULT_PASS`. Actual AMD SmartConnect + eight-slot RTL tag/LRU/mover + 128-bit scratch.
- SHA256 uploaded Stage C log: `81a0f77256fa025977f8ad061a9d0baf6da7ec35517efd145125464bc364ed25`. Stage D: `65478c577a0e150cab97782309e2298c8ede2c3f79a1315a9f793a89819599b4`. `result.txt`: `ed163d69a09ddc0ffcbdf126a42d5745a93449fa7a39354788e948b7ac795c04`.
- Previously independently accepted actual original-vendor Stage A 4x write/14 read/byte-lane and Stage B one-slot 3 fills/1 dirty writeback/byte reload/poison remained valid under their earlier authenticated A/B archive. The uploaded current C/D logs and runner success independently establish their own actual simulator outcomes. The current C/D **commit.txt and original SHA before/after were not uploaded**, so their run-wide source identity check still needs operator `cmp` readback. Do not silently claim those unprovided files were checked.
- **Accepted simulator boundaries**: original AMD vendor memory transactions **A-D PASS** for modeled scratch, NOT real DDR, not M05-generated HLS neural RTL instantiation, and not actual 4096-neuron address space (original scratch = 8KiB).

## New M06 architecture: true autonomous event-engine HLS with page-backed state

M05 accepted untouched originals continue as regression references:
`hls/m05_rolling/m05_rolling.cpp`, `hls/m05_stream_eval/m05_stream.cpp`, `hls/m04_lif_eval/m04_eval.cpp`. Added a **NEW**, independently named top:
`hls/m06_paged_rolling/m06_paged_rolling_replay` implemented in `m06_paged_rolling.cpp` with `m06_paged_rolling.hpp`. It derives the **accepted M05 rolling temporal wheel, event ingestion, independent per-edge positive-delay fanout, signed32 aggregate current cap, speculative full trace and M04 exact signed16 arithmetic**, but replaces all on-chip working-voltage arrays with an eight-slot x256B page data SRAM (64 x 32-bit words per page, 2048 bytes of resident state). Trace voltage is reread from the page cache even for silent neurons, rather than consulting a parallel full-neuron voltage observer. A bitmap tracks eligibility; existing M05 wheel/current and per-neuron config arrays remain on-chip. HLS design is not RAM-free outside the 2KiB neuron-state budget.

The 16B canonical neuron row is four 32-bit words, word0 signed16 voltage (upper16 reserved), word1 last-completed tick+1 watermark, words2/3 reserved. One 256B page holds 16 neurons. The top supports the accepted M05 bounded run envelope (1..1024 neurons, <=64 ticks, <=8 delay, <=4096 individual arrivals per tick); requires admitted neuron count and canonical tile base be 16-neuron aligned. AXI-Lite selects `canonical_first_neuron` inside the **4096-neuron logical canonical region**, with 64KiB total state backing and safe page IDs 0..255. Both the top and host tests check high tile `canonical_first_neuron=3072` +1024 neurons and a small tile starting at 4048, and verify surrounding rows untouched. It does not claim a single M05 invocation supports 4096 active neurons.

**Critical original-SmartConnect role fix**: the new top exposes **TWO physically separate m_axi master interfaces**, `canonical_read_words` only READ (target original S00), and `canonical_write_words` only WRITE (target original S03), with maximum requested AXI burst 16 beats. These ports MUST be assigned to the SAME exclusively owned 64KiB canonical memory region by a later system operator; the C++ reference test aliases both pointers to one byte array. **Data width unknown until genuine Vitis synthesis.** Do NOT directly wire hypothetical 32-bit HLS AXI data to original 256-bit SmartConnect without verified AMD width conversion. Cross-port write completion / read-after-write order, AXI address translation, physical DDR ownership and source binding remain open.

**Real native regression result**: tests/test_m06_paged_rolling_hls.py builds that same HLS C++ top with unchanged accepted M04 arithmetic and a separate untouched M05 rolling binary. It verifies full six-field trace parity against M05 rolling and independent M02 dense/M03 sparse, including network sizes 32/256/1024, 64-tick delayed recursion, 1 vs 8 slots, signed extreme event cancellation, high 4096-space tiles, 16B canonical final record bytes/watermarks, and invalid slot/address guards. A separate Vitis CSim testbench is compiled and run by host CI; this is **not a genuine Vitis-generated RTL pass** until the operator runs the Vitis tool.

The prior native adapter `hls/m06_paged_adapter` also remains tested and unchanged. It calls the actual accepted M05 streaming calculation top on native 1..8 page-cache state, but does not synthesize paging. The NEW M06 top is a separate integrated candidate, not the accepted M05 generated RTL **module** modified or instantiated.

## One extra original AMD memory contract gate, Stage E (NOT RUN)

The original vendor `scripts/run_m06_original_mem_sc_vendor_xsim.sh` now keeps A/B/C/D in their established order and adds **Stage E** using the SAME authentic saved original AMD 96-pin SmartConnect. It temporarily PARAMETERIZES ONLY the scratch 128-bit simulation RAM to **65,536 bytes** and raises only the 256-bit page mover's synthetic `MAX_BLOCKS` to 256. The existing A-D scratch defaults remain exactly 8192 bytes, so previous results are not retconned. Stage E must perform full dirty writeback/reload of highest legal block255 (neurons4080..4095, last byte65535), then prove illegal block256 **quarantines without memory AXI access**. Its PASS markers in new run `13_4096_xsim.log`:
- `M06_ORIGINAL_VENDOR_4096_RANGE_PASS`
- `M06_ORIGINAL_VENDOR_4096_OUT_OF_RANGE_QUARANTINE_PASS`

CI only SYNTAX-COMPILES this new vendor testbench with a clearly synthetic NONEXECUTED stub. No new owner Stage E result exists until the operator runs it in their own Vivado 2025.2.

## New real offline Vitis 2025.2 gate (NOT RUN)

`hls/m06_paged_rolling/m06_paged_rolling_hls_config.cfg` targets the existing `xck26-sfvc784-2LV-c` K26 at requested 10ns. `scripts/run_m06_paged_rolling_hls.sh` creates a fresh evidence directory, compiles CSim with **real Vitis**, requires the CSim PASS marker, and (with `--synth` or `--cosim`) runs genuine HLS C synthesis and optional C/RTL simulation, SHA-checking original M05 plus new M06 source before/after. No selected old Vitis/Vivado project is overwritten and no board access is requested. C synthesis may reject this architecture, fail resource budget or reveal unintended port widths; **DO NOT infer success from host g++ CI**.

`scripts/m06_paged_hls_port_audit.py` will independently inspect the **ACTUAL generated top** in a genuine successful `--synth` folder. It requires two distinct M_AXI channel groups and exact read/write port direction, original M05 stream ABI and new metrics, resolves generated Verilog width parameters without inventing values, and records whether 32/64/128-to-256 data-width conversion is required. This is **generated header readback**, not proof that the HLS IP is bound to original SmartConnect.

## Precise operator commands — from existing VS Code terminal

    cd ~/Git/Thesis
    git status --short
    git fetch origin
    git switch agent/neuromorphic-accelerator-v1-m06-ddr-residency
    git pull --ff-only origin agent/neuromorphic-accelerator-v1-m06-ddr-residency
    git rev-parse HEAD
    cd Neuromorphic_Accelerator/v1
    python3 -m compileall -q src scripts tests
    python3 -m unittest discover -s tests -p 'test_m06*.py' -q
    bash -n scripts/run_m06_original_mem_sc_vendor_xsim.sh
    bash -n scripts/run_m06_paged_rolling_hls.sh

    # Review SAME already-successful C/D run WITHOUT rerunning it.
    export CD="$HOME/Thesis_Evidence/m06_original_vendor_mem_sc_xsim_20261109T225500Z_Q55EJq"
    cat "$CD/result.txt" "$CD/commit.txt"
    cmp "$CD/sha_before.txt" "$CD/sha_after.txt"
    grep -E 'M06_ORIGINAL_VENDOR_NEURAL_PAGED_|M06_ORIGINAL_VENDOR_LRU8_' \
      "$CD/09_neural_paged_xsim.log" "$CD/11_lru8_xsim.log"

    # First real Vitis 2025.2 CSim AND C synthesis of NEW page-backed rolling top.
    source /home/dna/Vivado/2025.2/Vitis/settings64.sh
    vitis-run --version
    bash scripts/run_m06_paged_rolling_hls.sh --synth
    echo "Vitis new paged HLS synthesis exit: $?"

    export HLS="$(find "$HOME/Thesis_Evidence" -maxdepth 1 -type d \
      -name 'm06_paged_rolling_hls_synth_*' | sort | tail -n 1)"
    echo "$HLS"
    cat "$HLS/result.txt" "$HLS/commit.txt" "$HLS/report_paths.txt"
    cmp "$HLS/source_before_sha256.txt" "$HLS/source_after_sha256.txt"
    tail -n 50 "$HLS/01_csim.log"
    tail -n 70 "$HLS/02_csynth.log"

    # Run ONLY after genuine synthesis exits zero; this is header, not DDR proof.
    python3 scripts/m06_paged_hls_port_audit.py \
      --hls-evidence "$HLS" \
      --output "$HOME/Thesis_Evidence/m06_paged_hls_ports_$(date -u +%Y%m%dT%H%M%SZ)_$$.json"

    # Original AMD SmartConnect Stage E (runs A-D first in a new scratch folder).
    source /home/dna/Vivado/2025.2/Vivado/settings64.sh
    export D3="$HOME/Thesis_Evidence/neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ"
    export PORTS="$HOME/Thesis_Evidence/m06_vendor_xsim_port_contract_20261109T181345Z_f4X4Of"
    bash scripts/run_m06_original_mem_sc_vendor_xsim.sh \
      "$D3" \
      "$PORTS/02_original_mem_sc_ports.txt" \
      "$PORTS/08_mem_sc_wrapper_headers_nonansi_fixed.json"
    echo "All FIVE original AMD vendor XSim stage exit: $?"
    export E="$(find "$HOME/Thesis_Evidence" -maxdepth 1 -type d \
      -name 'm06_original_vendor_mem_sc_xsim_*' | sort | tail -n 1)"
    echo "$E"
    cat "$E/result.txt" "$E/commit.txt"
    cmp "$E/sha_before.txt" "$E/sha_after.txt"
    grep -E 'M06_ORIGINAL_VENDOR_4096_|M06_VENDOR_4096_FAIL|ERROR:|FATAL' \
      "$E/12_4096_xelab.log" "$E/13_4096_xsim.log" 2>/dev/null | tail -n 70

Files needed for next review: for Vitis, `result.txt`, `commit.txt`, `01_csim.log`, `02_csynth.log`, `report_paths.txt`, full generated-header contract JSON and the actual `*_csynth.rpt` if synth succeeds (do NOT upload proprietary generated IP sources unless necessary). For Stage E, `result.txt`, `commit.txt`, `13_4096_xsim.log` and `12_4096_xelab.log` if it fails; include original before/after SHA comparison output. Preserve failed evidence; don't blindly rerun.

**After real Vitis synthesis and co-sim**, decide whether the new HLS m_axi top can be integrated through width adaptation/controlled bases into the original AMD S00 read/S03 write path in a new scratch Vivado project. **Do not close M06 merely because Stage E passes**; the actual generated HLS + original vendor AXI binding, and cross-master coherency, remain unknown. If binding is proven, the M06 offline acceptance evidence could support closeout without unauthorized physical DDR/board use. NO M07 development until accepted by owner.
