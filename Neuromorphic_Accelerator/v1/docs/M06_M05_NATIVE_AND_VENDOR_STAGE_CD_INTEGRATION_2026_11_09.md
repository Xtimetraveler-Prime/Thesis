# M06 integration checkpoint: independently accepted AMD A/B, M05 native integration, 8-slot RTL, vendor C/D staged

**2026-11-09.** M06 draft PR #80 remains OPEN/UNMERGED. ORIGINAL AMD IP immutable. This handoff supersedes older "vendor XSim not run" statements. No physical board/JTAG/PS DDR ownership is authorized.

## A/B: owner archive is authentic PASS evidence for the tested scope

The owner uploaded m06_vendor_xsim_ACCEPTED_20261109.tar.gz, SHA256:
f6f842c3d17b552d5604a5552c292d72a9b889518e8b69f42f10db581644d2ff

It contains ten small evidence files, NOT proprietary IP source. Inspected archive:
- result.txt: exit_status=0. commit.txt: 8c8326ffff1b0a604aab2fc3423394b61ff27b9a.
- sha_before.txt == sha_after.txt EXACT bytes. Original top simulation wrapper source hash 0ec8a01dfc7c23825a8d5c8934c7f26dc5b92b924be88d51addd9e76555b8e12, nested BD source hash c3d7c5021f532aae29c860a63fb92da9529dac489f87a74267b9af82472444f3.
- Genuine XSim 2025.2 Stage A log 05_xsim.log: M06_ORIGINAL_SMARTCONNECT_VENDOR_XSIM_PASS writes=4 reads=14 M00_wbeats=8 M00_rbeats=28 M00_wstalls=6 M00_rstalls=0 NO_BOARD_NO_REAL_DDR. Actual original AMD RTL compiled, elaborated and transacted.
- Genuine XSim 2025.2 Stage B log 07_paged_xsim.log: M06_ORIGINAL_VENDOR_PAGED_RTL_PASS fills=3 wb=1 reload_byte_exact=1 M00_write=16 M00_read=48; M06_ORIGINAL_VENDOR_PAGED_FAULT_QUARANTINE_PASS M00_read=50 stalls=813 NO_BOARD_NO_REAL_DDR.
- New scripts/m06_vendor_evidence_attest.py independently rechecks archive membership, signed exit, original source hashes, original 186-source manifest, installed glbl provenance, xelab/log versions, named transaction markers and exact counts. It NEVER extracts the archive or claims neural/8-slot or physical DDR proofs. Synthetic audit regression tests do not count as real vendor execution.

**Conclusion: The original-SmartConnect byte/response/downsizing (A) and ONE-slot dirty eviction/reload/quarantine (B) acceptance gates are CLOSED for synthetic scratch-memory simulation.** No real memory allocation, board measurement, crash-safe transaction, M05 full HLS neural engine, or 8-slot geometry is implied.

## Native source integration: unchanged M05 STREAM arithmetic with M06 bounded page cache

New hls/m06_paged_adapter/m06_paged_adapter.hpp/.cpp and native host CLI are built with the original unchanged hls/m05_stream_eval/m05_stream.cpp and original unchanged hls/m04_lif_eval/m04_eval.cpp. Each admitted neuron previous voltage and 32-bit last-completed tick watermark is read from a 16B canonical record via an explicit physical 1..8 slot x256B LRU cache. Every evaluated neuron calls the *actual* accepted M05 stream top m05_stream_eval for exact original M04 signed16 voltage/spike arithmetic; results are committed back into the paged cache (not a copied working-voltage source). A separate host scheduler aggregates signed individual recurrent/external events, preserves delayed fanout across up to 64 ticks, and limits 4096 arrivals per tick.

tests/test_m06_original_m05_paged_adapter.py compiles and executes this C++ path AND a separate binary using the original unchanged M05 rolling event scheduler m05_rolling_replay. The whole per-tick six-column trace must match original M05 rolling output, independent M02 dense reference and independent M03 sparse evaluated IDs/arrivals, including positive/negative saturation, cancellation, delay-8 recurrence and 64 ticks. At the end it decodes every 16B canonical record, checking final voltage, last-tick watermark, and reserved bytes zero. It tests 1-slot and 8-slot capacity pressure on up to 256 logical neurons (16 canonical pages). The 8-slot page budget is 2048B; the test explicitly recognizes that a 16-page fully sequential scan thrashes BOTH 1-slot and 8-slot LRU, even though locality workloads do benefit from 8 slots. A failed request publishes no partial trace, but software canonical image operations are NOT AXI/crash atomic.

**Boundary:** This is genuine C++ compilation/execution of the unchanged accepted M05 HLS computation source, but its vector-backed LRU pager and event scheduler are HOST NATIVE ONLY and NOT a synthesized FPGA kernel or DMA integration. Do not promote it to PL timing, memory bus or synthesized HLS proof.

## Eight-slot 2048B physical RTL data cache

New rtl/m06/m06_residency_lru8.sv holds eight tag/valid/dirty/recency records. New rtl/m06/m06_axi256_multislot_transfer.sv holds eight 256-byte data slots (64 x 256-bit words). It issues eight single-beat original S00-read or S03-write transactions per 256B page with explicit target slot index, dirty-victim ACK-before-fill, stalled-cycle counter, and sticky poisoned state for unknown AXI commit/failed reads. The previously verified one-slot RTL modules remain unchanged.

Real Icarus CI integration RTL test tb_m06_residency_lru8_bridge.sv plus independent 256-bit canonical memory BFM: **PASS**, exact marker:
M06_LRU8_AXIBRIDGE_RTL_PASS physical_slots=8 resident_bytes=2048 fills=19 WB=2 evictions=11 AR=152 AW=16
M06_LRU8_FAULT_QUARANTINE_RTL_PASS M00_MODEL_ONLY NO_DDR_BOARD

This tests actual block data and masked-byte edits, eight initial slots, LRU victim on ninth page, dirty eviction and page0 byte-exact reload under further misses, and SLVERR poison. It is not a real original AMD IP or real DDR experiment yet.

## Two NEW original vendor XSim integration gates — C and D

The unchanged A and B benches still execute first in scripts/run_m06_original_mem_sc_vendor_xsim.sh against the same immutable original 2025.2 D3 source. We now generate two more authenticated 96-pin testbenches, and the runner requires their real PASS markers after A/B have passed.

**Stage C**: scripts/m06_generate_original_vendor_neural_paged_bfm.py generates tb_m06_original_vendor_neural_paged.sv. The ORIGINAL AMD SmartConnect is connected to the M06 RTL one-slot pager/mover, genuine 128-bit scratch RAM and independent RTL m06_lif16_neuron_step.sv. The 32-neuron x4-tick M02 dense-oracle vector is testbench-initialized before reset (subsequent state accesses MUST traverse vendor AXI). Eight spikes, 128 neural updates, 10 page fills and 8 writebacks must match exact voltage/spike/time-stamp/byte strobes and downstream M00 counts. An injected read error must quarantine. Required real markers in 09_neural_paged_xsim.log:
- M06_ORIGINAL_VENDOR_NEURAL_PAGED_M02_PARITY_PASS
- M06_ORIGINAL_VENDOR_NEURAL_PAGED_FAULT_PASS

This stage proves neural arithmetic through REAL original AMD AXI paging, **NOT** instantiation of M05 HLS event scheduler. Recurrent current deliveries are testbench oracle-precomputed.

**Stage D**: scripts/m06_generate_original_vendor_lru8_bfm.py generates tb_m06_original_vendor_lru8.sv. ORIGINAL AMD SmartConnect drives the **new** 8-slot LRU metadata/data RTL plus 128-bit scratch. After eight page fills, a ninth demand selects a dirty LRU victim, and repeated page faults force byte-exact dirty writeback/reload. Required real markers in 11_lru8_xsim.log:
- M06_ORIGINAL_VENDOR_LRU8_RTL_PASS
- M06_ORIGINAL_VENDOR_LRU8_FAULT_PASS

CI ONLY syntax-checks both generated vendor benches with a clearly FAKE, NON-SIMULATED module; Icarus independently runs real RTL against behavioral canonical memory. Neither C nor D has yet run in authenticated original AMD XSim as of this handoff. A COMPLETE new four-stage owner run with exit_status=0, original SHAs unchanged, and four logs is required to close C/D.

## One-shot LOCAL owner verification, **offline Vivado XSim only**

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

    # No re-run is required to prove the existing A/B archive:
    export ARCHIVE="$HOME/Thesis_Evidence/m06_vendor_xsim_ACCEPTED_20261109.tar.gz"
    python3 scripts/m06_vendor_evidence_attest.py \
      --archive "$ARCHIVE" \
      --output "$HOME/Thesis_Evidence/m06_vendor_A_B_attestation_20261109.json"

    # Use your already working Vivado 2025.2 environment settings:
    source /home/dna/Vivado/2025.2/Vivado/settings64.sh
    xvlog -version
    export D3="$HOME/Thesis_Evidence/neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ"
    export PORTS="$HOME/Thesis_Evidence/m06_vendor_xsim_port_contract_20261109T181345Z_f4X4Of"

    bash scripts/run_m06_original_mem_sc_vendor_xsim.sh \
      "$D3" \
      "$PORTS/02_original_mem_sc_ports.txt" \
      "$PORTS/08_mem_sc_wrapper_headers_nonansi_fixed.json"
    echo "four-stage XSim exit: $?"

    export RUN="$(find "$HOME/Thesis_Evidence" -maxdepth 1 -type d \
      -name 'm06_original_vendor_mem_sc_xsim_*' | sort | tail -n 1)"
    echo "$RUN"
    cat "$RUN/result.txt" "$RUN/commit.txt"
    cmp "$RUN/sha_before.txt" "$RUN/sha_after.txt"
    grep -E \
      'M06_ORIGINAL_SMARTCONNECT_VENDOR_XSIM_PASS|M06_ORIGINAL_VENDOR_PAGED_|M06_ORIGINAL_VENDOR_NEURAL_PAGED_|M06_ORIGINAL_VENDOR_LRU8_|M06_VENDOR_NEURAL_FAIL|M06_VENDOR_LRU8_FAIL|FATAL|ERROR:' \
      "$RUN/05_xsim.log" "$RUN/07_paged_xsim.log" \
      "$RUN/09_neural_paged_xsim.log" "$RUN/11_lru8_xsim.log" \
      2>/dev/null | tail -n 80 || true

**Files to upload**: always latest run result.txt and commit.txt; successful 09_neural_paged_xsim.log and 11_lru8_xsim.log, plus optionally 05_xsim.log and 07_paged_xsim.log if new-run A/B behave differently. If failure occurs, submit the first failing nonempty stage log (03_xvlog.log, 08_neural_paged_xelab.log, 09_neural_paged_xsim.log, 10_lru8_xelab.log or 11_lru8_xsim.log) and result.txt. Do not automatically rerun when one stage fails, modify original D3, or revisit unrelated warnings.

## Remaining M06 acceptance boundary

After C/D PASS, we still need a genuine synthesized/Vitis or generated HLS RTL integration connecting the **actual accepted M05 neural/event-execution engine** to the page-request/response/data slots, not merely native C++ or an independent M06 LIF arithmetic lane. The 4096-logical-neuron canonical-addressing envelope is supported by source-model Geometry but the original scratch endpoint and generated RTL tests only cover 32 pages (512 16B neurons). Validate or explicitly bound this gap before M06 acceptance. No physical DDR or JTAG actions are authorized; that campaign remains later.

**Do not merge PR #80 or mark M06 COMPLETE on CI alone.** M06 closure requires the owner's new C/D original-vendor evidence and a separately accepted full M05 HLS/RTL paging interconnect proof.
