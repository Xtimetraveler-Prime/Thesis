# M06 G3 actual verified owner inputs and 32-to-256-bit original AMD link preparation

**Status 2026-11-09 evening America/Denver: G1 genuine HLS C/RTL cosim PASS; G2 original AMD A-E FUNCTIONAL PASS; G3 actual connected RTL NOT YET RUN; G4 end-to-end trace/fault acceptance OPEN.** Existing draft PR #80, no physical board/JTAG/PS DDR, no merge/M07 without owner approval.

## New genuine owner evidence accepted at its actual scope

Uploaded `m06_corrected_cosim_20261110T022728Z.tar.gz` preserves original owner `~/Thesis_Evidence/m06_paged_rolling_hls_cosim_20261110T022111Z_iMNors`:
- `result.txt=exit_status=0`, `commit.txt=fa9b8c3f1254ce397f8d2757c26ab5f0c1ec57a2`.
- Original source-before/after SHA256 manifests byte-for-byte MATCH.
- Genuine Vitis 2025.2 CSim PASS, Vitis 2025.2 C synthesis generated Verilog, Vitis C/RTL cosim used XSim, generated RTL TB, completed **4/4** transactions, C post-checking PASS, final `COSIM 212-1000 *** C/RTL co-simulation finished: PASS ***` on 2026-11-09 local time. No failing trace/DIAG marker. This ACCEPTS **G1 for tested HLS testbench**, not the generated HLS through original AMD SmartConnect.
- Prior uploaded full `m06_paged_rolling_replay_csynth.rpt` is the **correct whole-neural-top** report from ORIGINAL 2026-11-09 18:07:59 C synthesis baseline, not the newer alias-cosim run. Baseline estimate: 12,913 LUT, 9,820 FF, 42 BRAM18K, 2 DSP, HLS 8.8ns estimated clock; latency **unknown**, no routed timing or real board. Two earlier uploads had identical filename; the mounted full report was read successfully. The new cosim folder also contains its own `work/hls/syn/report/m06_paged_rolling_replay_csynth.rpt` and `work/hls/sim/report/m06_paged_rolling_replay_cosim.rpt`, as evidenced by `report_paths.txt`; use those for CURRENT code resource/timing and cosim summary.

Prior uploaded original vendor Stage E archive shows genuine original AMD A-E XSim PASS and matching before/after D3 source SHA manifests, but independent live original D3/IP source rehash by new audit on owner PC still required. Original vendor input **NEVER instantiates generated HLS IP**, and neither component test proves actual shared-memory, cross-master B→AR coherency or fault containment.

## Actual electrical/transaction architecture prerequisites

New generated HLS top: two distinct 32-bit masters `gmem_read` (read only) and `gmem_write` (write only); 64-bit AXI addresses. The originally authenticated AMD SmartConnect has **S00 read-only and S03 write-only with 256-bit DATA and 32-bit AXI address ports**, downstream original M00 128-bit; its 96-AXI-pin wrapper has no S00/S03 AXI ID wires. A functional link MUST provide:
- Verified **32-to-256-bit width conversion** on each memory master with preserved byte ordering and WSTRB masks. AMD AXI width converter upsizing behavior can depend on AWCACHE/ARCACHE Modifiable signaling; do not presume every upstream 32-bit transfer forms a full 256-bit beat.
- Guarded **64-to-32-bit address translation**, never silently truncate high bits. Both masters must target the **same** independently owned 64KiB offline scratch image, legal pages0..255, illegal 256 rejected before AXI. This is NOT an allocation of any real physical DDR.
- Defined handling/termination of **ID/REGION/QOS/USER etc.** because original S00/S03 does not expose HLS ID signals. The exact matrix must be read from the genuine generated top and original 96-pin ABI, not guessed.
- Correct write-channel AW/W/B completions and no separate-master reread of a dirty evicted page until prior B acknowledgement; enforce and observe protocol via genuine connected XSim, not HLS ALIAS pragma alone.
- Error and timeout poisoning/aborted epoch: pure HLS pointer ports do not expose BRESP/RRESP to the algorithm, requiring tested supervisor/RTL response handling.

## Three new G3 preparation tools and positive/negative tests

1. `scripts/m06_g3_original_link_inputs.py` **READ ONLY**: checks the LIVE owner CSim/synth/C/RTL PASS evidence, that source SHA manifests match AND current unchanged HLS source bytes equal the passed generated source, independently reruns `m06_paged_hls_port_audit.audit` on **new cosim Verilog**, invokes `m06_original_stage_e_evidence_audit.audit` on the LIVE original AMD D3 sources, and checks exact 32/64 HLS vs original 256-bit read/write role. Emits only `REAL_HLS_COSIM_AND_ORIGINAL_AMD_A_E_READY_FOR_UNPROVEN_LINK_TRIAL`, never `connected`. `tests/test_m06_g3_original_link_inputs.py`: six positive/negative SYNTHETIC methods with explicitly mocked vendor/HLS component attestations; tests source mismatch, stale synth/no RTL, missing/duplicate real steps and response-error/fake pass, wrong port role/width and Stage E not accepted.
2. `scripts/m06_axi32_to256_byte_oracle.py`: independent **host-only** 32-bit HLS word to 256-bit byte-lane/partial WSTRB reference. Models all eight lanes, last legal byte65535, 4KiB split behavior, 16-word bursts, pending write B-response fence across master reads, nonzero BRESP/RRESP poisoning; never claims real AMD converter packing/clock/protocol correctness or error atomicity. `tests/test_m06_axi32_to256_byte_oracle.py`: seven positive/negative host-only methods.
3. `scripts/m06_g3_exact_original_pin_matrix.py`: reuses genuine owner preflight and validates original saved 96-port simulation wrapper SHA **by actual D3 file read** with `m06_generate_original_mem_sc_bfm.original_ports`. Parses *all* pins from generated HLS cosim Verilog via `m06_paged_hls_port_audit.parse_top`. Emits per-sideband HLS-vendor width/direction matrix with 32→256 data conversion, 64→32 bounded address guard, present/missing ID/USER/QOS and explicit unconnected status. `tests/test_m06_g3_exact_original_pin_matrix.py`: five positive/negative synthetic methods for byte/data widths, address narrowing, role conflicts and original vendor ABI mismatches.

The preflight/byte-model/pin matrix do not generate a converter, compile Vivado vendor RTL, or close G3. Their purpose is to make the subsequent **actual, owner-only, genuine offline original AMD XSim** binding exact and not guessy. Existing `m06_paged_hls_axi_link_plan.py` now explicitly flags guarded 64→32 address-width mapping, alongside 32→256 data conversion. The older verified generated port audit JSON was from **pre-ALIAS RTL**; new G3 tools automatically inspect the **corrected** cosim RTL.

## Owner exact terminal commands — NO need to re-run successful HLS cosim or A-E vendor stages

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m06-ddr-residency
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m06-ddr-residency
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m06_g3*.py' -v
python3 -m unittest discover -s tests -p 'test_m06_axi32_to256_byte_oracle.py' -v
python3 -m unittest discover -s tests -p 'test_m06*.py' -v

export COSIM="$HOME/Thesis_Evidence/m06_paged_rolling_hls_cosim_20261110T022111Z_iMNors"
export E="$HOME/Thesis_Evidence/m06_original_vendor_mem_sc_xsim_20261110T013912Z_VZwFV2"
export D3="$HOME/Thesis_Evidence/neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ"
export PORTS="$HOME/Thesis_Evidence/m06_vendor_xsim_port_contract_20261109T181345Z_f4X4Of"
cmp "$COSIM/source_before_sha256.txt" "$COSIM/source_after_sha256.txt"
cmp "$E/sha_before.txt" "$E/sha_after.txt"
python3 scripts/m06_original_stage_e_evidence_audit.py --evidence "$E" \
  --output "$HOME/Thesis_Evidence/m06_stage_e_reaudit_$(date -u +%Y%m%dT%H%M%SZ)_$$.json"

python3 scripts/m06_g3_original_link_inputs.py \
  --hls-cosim "$COSIM" --vendor-a-e "$E" --repo "$PWD" \
  --output "$HOME/Thesis_Evidence/m06_g3_input_gate_$(date -u +%Y%m%dT%H%M%SZ)_$$.json"

python3 scripts/m06_g3_exact_original_pin_matrix.py \
  --hls-cosim "$COSIM" --vendor-a-e "$E" --repo "$PWD" \
  --d3 "$D3" --original-header-json "$PORTS/08_mem_sc_wrapper_headers_nonansi_fixed.json" \
  --output "$HOME/Thesis_Evidence/m06_g3_pin_matrix_$(date -u +%Y%m%dT%H%M%SZ)_$$.json"

echo "Corrected full HLS report:"
ls -l "$COSIM/work/hls/syn/report/m06_paged_rolling_replay_csynth.rpt"
echo "Real HLS C/RTL summary:"
ls -l "$COSIM/work/hls/sim/report/m06_paged_rolling_replay_cosim.rpt"
```

**Only request next files:** first G3 error output (if any), the two generated `m06_g3_*json` documents (latest each), the new cosim-folder top-level `m06_paged_rolling_replay_csynth.rpt` and `m06_paged_rolling_replay_cosim.rpt`. No need to upload the whole original generated vendor IP sources as a first step. Once actual ABI/sideband report is available, develop a genuine offline scratch Vivado 2025.2 width/address-converter testbench binding generated HLS IP to authenticated original SmartConnect without editing original D3 files. Do not call G3 PASS until actual original AMD vendor XSim runs the connected neural core; G4 still requires full independent M02/M03 canonical trace/state and negative error/timeout quarantine.

**Hard scope:** no physical board, PS DDR, JTAG, bitstream, M06 PR merge, or M07 work without owner approval.
