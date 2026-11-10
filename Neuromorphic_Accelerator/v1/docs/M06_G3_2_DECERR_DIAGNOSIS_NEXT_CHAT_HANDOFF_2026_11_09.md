> **LATEST M06 G3.2 ORIGINAL AMD CONNECTED XSIM PASS; G3.3 REAL GENERATED-HLS INPUT INVENTORY SOURCE READY (2026-11-10 UTC).** User uploaded M06_G3_2_CORRECTED_XSIM_REVIEW_20261110T054830Z.zip, SHA256 b20d27fc6fc5ff9be5ec6ea78a03eb3baa99b563169185c41c7c178cc7c9b42f, owner original source commit 9241042486981b8d83c978e6c3153460b64ebff1, original folder m06_g3_real_dwc_original_sc_xsim_20261110T054742Z_LXrsEf. Genuine original Vivado 2025.2 2x AMD 32→256 DWC + ORIGINAL D3 SmartConnect + 128b 64KiB simulation-only RAM XSim **PASS**: ten 32-bit reads, three writes, independent expected data incl 0xFFFC/4KiB neighbors, partial WSTRB M00 0x5000, 126 AR/R/AW/W/B observations, first_decerr=0, 67 vendor and five test-source hashes before==after, both XCI SHA OK, result exit0. This is **G3.2 BFM-ONLY ACCEPTED**; NO HLS neural RTL instantiated, no real DDR or board. New scripts/m06_g3_2_connected_evidence_audit.py independently accepts exact original ZIP with tamper tests; new scripts/m06_g3_3_hls_inventory.py and scripts/run_m06_g3_3_hls_inventory.sh read existing accepted G1 cosim, original G2 A–E, original DWC and G3.2 ZIP, inventory actual HLS generated Verilog names/SHA and exact HLS+DWC+SC pin widths without changing any sources. New positive/negative synthetic tests. **G3.3 actual HLS→64/32 guards→original AMD converter/SmartConnect connected RTL NOT YET BUILT/RUN; G4 independent state/trace/fault OPEN; M06 OPEN.** Next owner gate is ONE read-only source-inventory run and ONE ZIP, no accepted simulator reruns. Exact VS Code commands and one-ZIP packaging names: docs/M06_G3_3_REAL_HLS_INVENTORY_OWNER_GATE_2026_11_10.md. PR #80 draft/unmerged, no physical board/JTAG/PS DDR/M07.

# ACTUAL G3.2 FIRST-READ DECERR ROOT CAUSE FROM ORIGINAL OWNER HANDSHAKES (2026-11-10 UTC)

The diagnosis is now conclusive for the historical first read: genuine owner ZIP `M06_G3_2_DEBUG_REVIEW_20261110T052354Z.zip`, SHA256 afc76302dce3e84831b1f77d27eadeab659f15c749473a0b13716ed60b983ac2, original commit 3380476b0b5a5745782248e11189ad824a902974, result.txt exit_status1, all source and vendor before/after hashes match. Accepted ARSIZE2/LEN0/ADDR0 at 32b SI (435ns), converter 256b MI/S00 (535ns), original SC M00 into RAM (635ns); RAM `rd_bad_request=1`, first DECERR (640ns), forward responses through original SC and DWC to SI32 (750ns). The SIM-ONLY `m06_axi128_scratch_mem.sv` previously required SIZE4 only. This is the confirmed cause for FIRST failure; does NOT prove all remaining transactions correct. Proposed scratch-only fix now committed: aligned AXI INCR SIZE0..4, 1<<size byte strides, aligned 128b RDATA, byte-lane WSTRB, invalid request DECERR, out-of-lane WSTRB SLVERR; original full-width replay remains tested. Actual genuine owner re-run of fixed RTL NOT YET EXECUTED. **Next one owner run** must include trace 08, summary 09, 07_xsim log, TB, source/vendor/XCI manifest, result/commit in one ZIP on success OR failure. Keep original AMD IP and accepted G1/G2 unchanged, G3.2 open, G3.3/G4 blocked, no PR merge, M07 or board operations.

> **LATEST SOURCE-ONLY G3.2 DECERR DIAGNOSTIC INCREMENT — OWNER XSim PENDING (2026-11-09):** The first actual original AMD connected Vivado 2025.2 run still FAILED (first address 0, RRESP=11, no established origin). The original `ARSIZE=2` first 32-bit read, restrictive simulation-only 128-bit RAM, BOTH original AMD width converters, original D3 SmartConnect and all accepted G1/G2 evidence are UNCHANGED. Newly generated **passive** bounded AR/R/AW/W/B probes observe 32-bit SI, 256-bit converter MI/original S00/S03, and original 128-bit M00/RAM (M00/RAM is ONE shared physical interface); first R/B VALID is observed even if READY=0, before the existing $fatal. Monitors report ARADDR/ARSIZE/ARLEN/ARBURST/cache/ID where present, response/last/data, accepted handshake counters, and RAM `rd_bad_request`, with one first-DECERR-sighting marker. `scripts/m06_g3_axi_trace_audit.py` extracts `08_axi_handshake_trace.log` and `09_axi_probe_summary.json` from genuine `07_xsim.log` on success OR failure; `root_cause_proven=false` until manual original-model evidence review. Positive/negative synthetic source regressions added. This does **not** fix G3.2, and no original vendor/owner XSim has been run against this increment yet. **NEXT:** ONE fresh owner XSim diagnostic, ONE ZIP with raw logs/trace/summary and preserved SHA attestations; **do not alter RAM/functionality until that result is examined.** G3.3/G4 remain OPEN. PR #80 DRAFT/UNMERGED; no physical board/DDR/JTAG or M07.

# M06 G3.2 failure analysis and next-chat takeover — 2026-11-09 21:48 MST

**Canonical next action: DIAGNOSE the first genuine combined AMD XSim read DECERR. Do NOT yet modify implementation, alter accepted vendor IP, merge M06, or begin M07.** This is a documentation/handoff change only.

## 1. Project and branch constraints that remain binding

- Repository Xtimetraveler-Prime/Thesis, working directory Neuromorphic_Accelerator/v1, M06 branch agent/neuromorphic-accelerator-v1-m06-ddr-residency, draft PR #80 UNMERGED. Original failed G3.2 **code commit**: 286e2257044d63a29ce745eab9fea2f1eaa27aca. New documentation-only HEAD may differ; check live PR and CI before modifications.
- Research goal: Loihi-inspired neuromorphic accelerator digital twin on xck26-sfvc784-2LV-c, 4096 canonical neuron records × 16 bytes = 65,536 bytes external-memory image, 8 × 256-byte on-chip page cache, bounded 1024 active neurons per 64 ticks. Immutable M02 independent LIF/event oracle, M03 traffic methodology, accepted M05 event-stream logic, and G1 paged HLS algorithm are separately verified.
- Vivado/Vitis 2025.2, owner Ubuntu VS Code terminal at ~/Git/Thesis. Never claim proprietary vendor IP simulations ran in GitHub CI; CI runs source/native tests and Icarus only. Original vendor AMD D3 code and XCI are **owner-local, hash-attested and not committed**.
- No physical FPGA programming/JTAG/XSDB, PS DDR allocation, board reset/boot, A53/Linux halt, bitstream deployment or measurement. All physical actions require **fresh session-specific operator permission**. No merge/M07 without owner verification and explicit permission. Never overwrite accepted evidence, vendor sources, Vitis generated RTL, or historical Loihi_Digital_Twin/v3.

## 2. Exact owner upload, provenance and verified failure

Upload: M06_G3_REAL_DWC_SC_XSIM_REVIEW_20261110T044546Z.zip. Archive SHA256:
b1b48e38f2948d1bb3d03e262af4e5a3f4e00087a5ca03e3bfd332995503663b

Owner original failed run folder, preserve UNMODIFIED:
~/Thesis_Evidence/m06_g3_real_dwc_original_sc_xsim_20261110T044432Z_1FrIEZ

The archive contains all 16 requested items, including generated TB, 04_xvhdl.log, 05_xvlog.log, 06_xelab.log, 07_xsim.log and before/after original vendor/source manifests. Owner commit = 286e2257044d63a29ce745eab9fea2f1eaa27aca. result.txt = exit_status=1.

The **genuine AMD Vivado 2025.2** executed:
- xvhdl: PASS, including ORIGINAL D3 SmartConnect VHDL and official AMD width-IP FIFO VHDL.
- xvlog: PASS, no reported syntax errors.
- xelab: PASS; snapshot m06_g3_real_dwc_original_sc_snapshot built with original AMD read/write width converters, original 96-port SmartConnect, our 64KiB 128b simulated scratch and independent 32b AXI testbench. Warnings: unconnected original mb_reset and converter aclk2x in underlying vendor hierarchy; warnings cannot be presumed root cause.
- xsim: **FAILED FUNCTIONALLY on FIRST 32-bit read address 0x00000000** at simulated 755ns. Actual independent expected word 0x382b1e11, actual RDATA 0x00000000, RRESP 2'b11 = AXI DECERR. Exact log:
    Fatal: M06_G3_REAL_DWC_SC_FAIL READ32 at=00000000 got=00000000 wanted=382b1e11 resp=11
    Time: 755 ns  Iteration: 0  Process: /tb_m06_g3_real_dwc_original_sc/read32  File: .../tb_m06_g3_real_dwc_original_sc.sv Line: 453
- xsim subsequently prints "$finish" and "exit 0" despite the fatal diagnostic. Owner shell runner correctly caught M06_G3_REAL_DWC_SC_FAIL and wrote exit_status=1. DO NOT treat simulator exit 0 or elaboration PASS as acceptance.
- Original repo 4 test source files have identical before/after SHA256: scripts/m06_g3_generate_real_dwc_original_sc_bfm.py, scripts/m06_g3_merge_vendor_sources.py, scripts/run_m06_g3_real_dwc_original_sc_xsim.sh, rtl/m06/m06_axi128_scratch_mem.sv. All **67 merged vendor RTL** SHA lines match before/after. Compile plan selected 63 Verilog files, 4 VHDL files and 58 include directories; 14 duplicate-library path rows were deduplicated only on equal SHA256. Genuine owner dual AMD XCI and source attestations accepted separately. No vendor IP edits made.
- The run is BFM-only: DOES NOT contain generated HLS neural RTL, 64→32 guards, or physical DDR. One failed read cannot prove width conversion, shared-memory coherence, or neural numerical correctness.

## 3. The leading hypothesis is NOT YET A PROVEN ROOT CAUSE

Look at the generated local TB:

- scripts/m06_g3_generate_real_dwc_original_sc_bfm.py, function render, issues SINGLE 4-byte read at 0x0: read DWC S_AXI_ARLEN = 0, S_AXI_ARSIZE = 3'd2, S_AXI_ARBURST = INCR (01), S_AXI_ARCACHE = 4'b0011 (modifiable bit set). Read DWC SI width = 32b; MI width = 256b, M_AXI read signals feed ORIGINAL SmartConnect S00; SmartConnect M00 width = 128b.
- The current simulation-only rtl/m06/m06_axi128_scratch_mem.sv legal_request REQUIRES s_axi_arsize == 3'd4 (full 16-byte beat), 16-byte aligned address, and increments by 16 bytes. A genuinely legal AXI narrow read (size=2, 4 bytes) might remain narrow after the converter(s) and reach M00, where this deliberately restrictive test memory issues DECERR. Alternatively the SmartConnect might reject the 32-bit-sized S00 transfer before M00, or a real converter sideband/upsizing behavior could be responsible. **NO upstream/downstream ARSIZE, ARLEN, ARCACHE, ARADDR, ARVALID/ARREADY or return-channel handshake trace exists in the uploaded ZIP.**
- We therefore DO NOT know whether the DECERR originated from the original SmartConnect decode, original RAM's strict SIZE4 validator, or an earlier converter error. Do not unconditionally widen the RAM's accepted sizes or modify AMD converters to force a PASS.
- Original M05/M06 accepted vendor A–E tests used 256-bit S00 full-width size5 and original M00 128-bit size4. This first combined 32-bit-DWC experiment is a new narrower traffic pattern, NOT a contradiction of their original PASS.

**Secondary items to verify only if first instrumentation indicates them:** ARLOCK/ARCACHE/QOS/REGION sideband semantics, full-wrapper generated SI/MI direction/ID mapping, ARLEN and LEN conversion for a single beat, read response stability/backpressure, SmartConnect address decode, and whether the RAM saw an address at all. Avoid speculative changes to more than one component in a trial.

## 4. Required next-chat FIX PLAN (do not skip steps)

1. **Confirm archive and repo identity.** Read this document, current roadmap.md, docs/M06_NEXT_CHAT_HANDOFF_2026_11_09.md, docs/M06_G3_2_REAL_DWC_ORIGINAL_SC_CONNECTED_OWNER_RUNBOOK_2026_11_09.md and scripts/rtl listed above, live PR #80 and workflow status. The original ZIP is already analyzed here; do not ask user to reupload it without a specific need for byte-level reinspection. Any older chat uploads may have expired, but original accepted owner evidence remains under ~/Thesis_Evidence.
2. **Instrument WITHOUT changing functionality.** Add passive handshake counters and a bounded AXI trace (log accepted valid&ready beats and returned R/B responses) at: 32b read DWC S_AXI AR/R, 256b DWC M_AXI→SmartConnect S00 AR/R, original SmartConnect 128b M00 AR/R and RAM S_AXI AR/R. Record ARADDR, ARLEN, ARSIZE, ARBURST, ARCACHE, ID (where present), ARVALID/ARREADY, RDATA, RRESP, RLAST, RVALID/RREADY, timestamp and which component generated/forwarded DECERR. Include a unique first-DECERR marker. Keep the first 0x0000 read unchanged as a reproducer, preserve all original vendor modules and RAM behavior for baseline. Make no assumptions about the source of DECERR. Add a short bounded per-test watchdog, preserve existing global watchdog, and assert end-to-end response origin and count. Ensure printed errors cannot be masked by xsim process exit 0.
3. **Unit/static tests and CI first.** Add focused positive and negative tests of trace formatting/handshake detection, BFM valid/ready R/B stability, source-only assertions, and a clearly labeled FAKE stub Icarus syntax-only compilation; never claim fake stub simulation proves behavior. Extend docs/M06_TESTS_EXPLAINED.md and source SHA evidence list for any changed testbench/runner/RTL scripts.
4. **One new genuine owner-only Vivado 2025.2 XSim baseline diagnostic run** in a NEW ~/Thesis_Evidence/m06_g3_real_dwc_original_sc_xsim_* folder, original audited AMD IP, hash before==after. A failure is expected until diagnosed. Request ONE ZIP with exact paths, numbered file list and a copy-paste packager, accepting partial output on failure. Include 07_xsim.log plus any new 08_...handshake_trace.log or 09_...probe_summary.json, generated TB, original compile manifest, source/vendor SHA before/after, real xelab/xvlog logs. Do NOT ask for proprietary AMD sources.
5. **Decide from the observed handshake path:**
   - If M00 receives ARSIZE2 and our RAM responds DECERR, determine whether this is a valid narrow AXI4 transaction; then write a **simulation-memory-only** narrow-transfer BFM fix (byte lane selection, transfer-size-aligned beat addressing, read-data lane placement, WSTRB, 4KiB and 64KiB bounds, bad-size negatives). Preserve prior full-width Stage A–E test behavior. Alternatively use explicitly justified AXI source legal full-packed bursts if correct for HLS's 32-bit traffic. Never simply turn DECERR into OKAY.
   - If the SmartConnect returns DECERR without any M00 AR handshake, isolate S00 ARSIZE/ARLEN/ARCACHE/address/region and compare against accepted original 256-bit transfer; use independent ONE-variable-at-a-time genuine runs. Do not change original SmartConnect D3 or AMD DWC RTL.
   - If width converter fabricates/returns DECERR, inspect actual interface and permitted AXI4 cache/packing and ID semantics, with real source-side and MI-side trace. Correct only generated BFM/legally allowed adapter configuration (new scratch-only IP only with explicit source/evidence versioning), not the original accepted IP.
6. **After root-cause fix**, rerun all native M06 unit tests plus genuine owner XSim end-to-end 10 independent expected reads and 3 writes through BOTH real converters, original SC, shared RAM. Assert last legal 0xfffc, 0x0ffc/0x1000, untouched adjacent bytes, partial WSTRB, deliberate B/R backpressure, correct ID/response and real M00 AR/R/AW/W/B handshakes. Current test BFM uses sequential B→AR readback only; this is not yet full simultaneous-master coherence.
7. **Then G3.3**, replace independent 32b driver with corrected real paged-HLS generated RTL and stream/AXI-Lite controls, integrate tested 64→32 bounds/DECERR guard and ID/LOCK/USER/REGION sideband handling; test B-response fencing before page reload, 64KiB canonical 4096 neurons and no invalid page256 memory traffic.
8. **Then G4**, independent M02/M03 full 16-byte canonical neuron-state and trace comparison, dirty evict/reload, delayed wheel/event ordering, stalls/timeouts, RRESP/BRESP errors and fail-closed epoch quarantine, bounded resources; genuine owner XSim output and SHA manifests. M06 closeout only after user native pass + explicit acceptance. M07, merge, physical FPGA still FORBIDDEN without explicit authorization.

## 5. Mandatory workflow and exact VS Code terminal baseline

For each next chat change: develop on current branch (do not create random duplicates or merge), show commit SHA, actual changed files, tests' scope, all six M01–M06 GitHub workflows at FINAL HEAD and owner-only limits; update roadmap, handoff, M06_TESTS_EXPLAINED.md as needed. ALWAYS provide exact local git pull, compile/syntax tests, genuine tool invocation, and a SINGLE evidence ZIP script with EXACT filenames and original directory. Never ask to rerun accepted G1, G2 or dual-DWC generation without a documented new dependency. On first genuine failure, preserve original evidence and analyze the first true error.

Owner terminal baseline after next code update (avoid rerun until instrumentation is committed):

    cd ~/Git/Thesis
    git status --short
    git fetch origin
    git switch agent/neuromorphic-accelerator-v1-m06-ddr-residency
    git pull --ff-only origin agent/neuromorphic-accelerator-v1-m06-ddr-residency
    git rev-parse HEAD
    cd Neuromorphic_Accelerator/v1
    python3 -m compileall -q src scripts tests
    bash -n scripts/run_m06_g3_real_dwc_original_sc_xsim.sh
    python3 -m unittest discover -s tests -p 'test_m06_g3_generate_real_dwc_original_sc_bfm.py' -v
    python3 -m unittest discover -s tests -p 'test_m06_g3_merge_vendor_sources.py' -v
    python3 -m unittest discover -s tests -p 'test_m06*.py' -v
    source "$HOME/Vivado/2025.2/Vivado/settings64.sh"
    xvlog -version

    export D3="$HOME/Thesis_Evidence/neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ"
    export PORTS="$HOME/Thesis_Evidence/m06_vendor_xsim_port_contract_20261109T181345Z_f4X4Of"
    export DW="$HOME/Thesis_Evidence/m06_g3_real_amd_dwc_20261110T032341Z_YUDRD3"
    export EX="$(find "$HOME/Thesis_Evidence" -maxdepth 1 -type d -name 'm06_g3_amd_sim_export_*' | sort | tail -n 1)"
    test "$(cat "$EX/result.txt")" = "exit_status=0" || { echo "not accepted AMD source evidence"; exit 2; }
    bash scripts/run_m06_g3_real_dwc_original_sc_xsim.sh "$D3" \
      "$PORTS/02_original_mem_sc_ports.txt" \
      "$PORTS/08_mem_sc_wrapper_headers_nonansi_fixed.json" \
      "$DW" "$EX"
    echo "M06 genuine G3.2 XSim exit: $?"
    export LINK="$(find "$HOME/Thesis_Evidence" -maxdepth 1 -type d -name 'm06_g3_real_dwc_original_sc_xsim_*' | sort | tail -n 1)"
    echo "$LINK"
    cat "$LINK/result.txt" "$LINK/commit.txt"
    test -f "$LINK/07_xsim.log" && tail -n 45 "$LINK/07_xsim.log"

Do not run this baseline unchanged until next chat commits instrumentation and validates native CI. An instrumentation-only run is diagnostic, not an acceptance PASS.

### Exact evidence packaging contract — ONE ZIP, existing files on PASS or FAIL

The new chat MUST include this equivalent automated packaging block whenever requesting user local vendor verification; NEVER merely say "send logs". A ZIP with missing files is normal on failure; still include the original failure logs. An extra 08/09 trace is **optional unless the new code actually creates it**.

    export LINK="$(find "$HOME/Thesis_Evidence" -maxdepth 1 -type d -name 'm06_g3_real_dwc_original_sc_xsim_*' | sort | tail -n 1)"
    export ZIP="$HOME/Thesis_Evidence/M06_G3_2_DEBUG_REVIEW_$(date -u +%Y%m%dT%H%M%SZ).zip"
    python3 - <<'PY'
    from pathlib import Path
    from zipfile import ZipFile, ZIP_DEFLATED
    import os
    folder = Path(os.environ["LINK"])
    outfile = Path(os.environ["ZIP"])
    names = [
      "result.txt", "commit.txt",
      "03_connected_vendor_compile_plan.json",
      "02_original_sc_compile_plan.json",
      "generated_bfm_sha256.txt",
      "tb_m06_g3_real_dwc_original_sc.sv",
      "04_xvhdl.log", "05_xvlog.log",
      "06_xelab.log", "07_xsim.log",
      "08_axi_handshake_trace.log", "09_axi_probe_summary.json",
      "00_reaudit_real_amd_dwc.json",
      "01_reaudit_dwc_sim_sources.json",
      "vendor_sha_before.txt", "vendor_sha_after.txt",
      "source_before_sha256.txt", "source_after_sha256.txt",
      "original_d3_folder.txt", "original_dwc_folder.txt",
      "original_dwc_compile_order_folder.txt",
    ]
    assert folder.is_dir(), f"Missing original evidence directory: {folder}"
    with ZipFile(outfile, "w", ZIP_DEFLATED) as zipf:
      for name in names:
        f = folder / name
        if f.is_file():
          zipf.write(f, arcname=name)
          print("ADDED:", f)
        else:
          print("NOT GENERATED:", f)
    print("UPLOAD ONE FILE:", outfile, "SIZE:", outfile.stat().st_size)
    PY

The new chat must name the actual exported ZIP path and exact source folder ($LINK), and ask only for the ZIP. Do not ask to upload original proprietary .xci/IP HDL. On failure, do not rerun unchanged before inspecting it.

## 6. Accepted component evidence and limitations to preserve

- G1 genuine corrected Vitis 2025.2 paged rolling HLS CSim/C-synth and C/RTL XSim cosim PASS at commit fa9b8c3f1254ce397f8d2757c26ab5f0c1ec57a2. Owner directory ~/Thesis_Evidence/m06_paged_rolling_hls_cosim_20261110T022111Z_iMNors. 4/4 transactions, real generated HLS RTL, NOT through original SmartConnect. Corrected HLS estimated 104 BRAM18K, 2 DSP, 17,390 FF, 22,888 LUT, 8.8ns HLS clock estimate, NOT routed timing; prior pre-alias estimate 42 BRAM18K/9,820 FF/12,913 LUT. Resource regression remains a future scoped review.
- G2 genuine original AMD SmartConnect A–E XSim PASS in original owner directory ~/Thesis_Evidence/m06_original_vendor_mem_sc_xsim_20261110T013912Z_VZwFV2; original D3 project basename neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ, original port contract report folder m06_vendor_xsim_port_contract_20261109T181345Z_f4X4Of; original source/hash attested. These tests did NOT instantiate neural HLS.
- Original two genuine AMD 2025.2 32→256 IP generation PASS owner dir ~/Thesis_Evidence/m06_g3_real_amd_dwc_20261110T032341Z_YUDRD3, read-only 13 SIM sources/role, read wrapper 36 pins, write wrapper 42 pins; exact source compile-order PASS at an owner folder matching m06_g3_amd_sim_export_*. They were correctly compiled in the failed combined G3.2 test, but no connected passing memory transaction yet.
- G3.2 genuine combined original vendor chain compiled+elaborated and FAILED first read DECERR, as above.
- G3.3 generated HLS-to-original SC complete integration and G4 independent neural/memory/failure acceptance remain OPEN. No accepted physical DDR/FPGA inference, hardware speedup, or energy result. PR #80 draft/unmerged.

## 7. Preserve existing documentation

This file supplements rather than replaces roadmap.md, docs/M06_NEXT_CHAT_HANDOFF_2026_11_09.md, docs/M06_G3_2_REAL_DWC_ORIGINAL_SC_CONNECTED_OWNER_RUNBOOK_2026_11_09.md, docs/M06_CLOSEOUT_HLS_AXI_OWNER_GATES_2026_11_09.md, docs/M06_TESTS_EXPLAINED.md and all M01–M05 source/methodology docs. Old "next owner run" commands are historical for their original states; use **this file's latest failure/fix-plan and evidence packager** until new source changes are committed. Do not delete other milestones' information or historical test results.
