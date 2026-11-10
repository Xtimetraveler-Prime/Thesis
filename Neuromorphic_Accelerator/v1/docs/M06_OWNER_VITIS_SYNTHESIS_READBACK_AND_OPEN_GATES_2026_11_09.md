# M06 genuine paged HLS synthesis readback and remaining offline acceptance gates

**Review date:** 2026-11-09 America/Denver. **Owner-supplied evidence scope:** uploaded `result.txt`, `01_csim.log`, `02_csynth.log`, plus the console text from the independent port audit. **M06 OPEN; PR #80 DRAFT/UNMERGED.**

## Genuine operator Vitis 2025.2 — new paged rolling candidate

The original genuine offline `--synth` evidence directory named in the Vitis log is
`~/Thesis_Evidence/m06_paged_rolling_hls_synth_20261110T010713Z_s1mUED`.
The uploaded `result.txt` says `exit_status=0`. Real Vitis `vitis-run v2025.2` CSim compiled the M06 paged top and untouched M04 LIF C++ and returned `M06_PAGED_ROLLING_HLS_CSIM_PASS`, `CSim done with 0 errors`. Real `v++ v2025.2` C synthesis generated Verilog/VHDL for `m06_paged_rolling_replay` on `xck26-sfvc784-2LV-c`, requested 10ns with 12% uncertainty, estimated **Fmax 113.64 MHz**. Generated top reports **two independent** `gmem_read` and `gmem_write` `m_axi` bundles and five AXIS ports. BRAM inference includes `page_words`, `current`, `touched`, `bias`, `tick_spike`. Owner ran `scripts/m06_paged_hls_port_audit.py` and received its genuine generated-header READ-ONLY VERIFIED message.

**Not yet received/read back:** original `commit.txt`; source-before/source-after SHA `cmp`; the actual generated-port JSON with measured AXI bus widths; complete `*_csynth.rpt` resource/whole-function latency report and `report_paths.txt`. Hence do **not** assert an independently pinned user-local commit, exact bus widths, LUT/FF/BRAM/DSP counts, or the report's latency. The original owner evidence is immutable; never modify those files.

**Real warnings:** one 4-iteration m_axi initialization loop has II=4 (shared bus write), final dirty-page flush pipeline had II=64 and reported loop constraints NOT satisfied. The inner 64-word page fills and writebacks had inferred bursts but Vitis noted both inferred and missed MAXI bursts. The tool's dangling *internal pipelined helper* AXI output tie-offs are not proof of correct top-level transaction ordering. These are investigation items, not grounds for claiming synthesis failed. Estimated HLS frequency is NOT routed end-to-end performance.

## Source-only incremental connection planning (NOT vendor execution)

`scripts/m06_paged_hls_axi_link_plan.py` calls the independent existing HLS generated-Verilog audit **again** on the owner's immutable synthesis directory, verifies the supplied JSON is exactly equal, then writes a **new** plan JSON. It records each measured M_AXI data/address width, read S00 and write S03 roles, whether an explicit adapter is needed for original 256-bit S00/S03, common 64KiB scratch-memory alias requirement, legal page255 / illegal page256, and independent negative verification still needed. It **always** reports not connected and M06 not complete. It does not edit vendor IP or generate a supposed functioning adapter. Synthetic unit test: `tests/test_m06_paged_hls_axi_link_plan.py` (six positive/negative methods, no original tool invoked). The standalone local Python unit tests passed when authored; **GitHub six-workflow status must be checked at latest source HEAD**.

Exact read-only invocation, after pulling latest M06 and setting `HLS` to the **existing** original synth folder:

```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
export HLS="$HOME/Thesis_Evidence/m06_paged_rolling_hls_synth_20261110T010713Z_s1mUED"
cat "$HLS/result.txt" "$HLS/commit.txt" "$HLS/report_paths.txt"
cmp "$HLS/source_before_sha256.txt" "$HLS/source_after_sha256.txt"
find "$HLS/work" -type f -name '*_csynth.rpt' -print
find "$HOME/Thesis_Evidence" -maxdepth 1 -type f -name 'm06_paged_hls_ports_*.json' -print
# Select the ACTUAL JSON emitted by your already-run generated-header audit:
export PORT_JSON="/full/path/to/the/already-generated/m06_paged_hls_ports_....json"
cat "$PORT_JSON"
python3 scripts/m06_paged_hls_axi_link_plan.py --hls-evidence "$HLS" \
  --port-audit "$PORT_JSON" \
  --output "$HOME/Thesis_Evidence/m06_paged_axi_link_plan_$(date -u +%Y%m%dT%H%M%SZ)_$$.json"
```

## Remaining acceptance: order and exact pass criteria

1. **G1 — generated-HLS C/RTL cosim:** unchanged new candidate in `bash scripts/run_m06_paged_rolling_hls.sh --cosim` (unique evidence folder; CSim and synth repeated by runner before cosim); require genuine XSim C/RTL completion, testbench final memory/watermark/trace checks, and the independent M02/M03 parity already established natively. Record full `03_cosim.log`, report, exit, commit and SHA. CSim `hls::stream` parity is not RTL proof. A two-port alias/memory model conflict may require a fresh subsequent source correction; **retain any first failed run**.
2. **G2 — original AMD SmartConnect Stage E:** `bash scripts/run_m06_original_mem_sc_vendor_xsim.sh "$D3" "$PORTS/02_original_mem_sc_ports.txt" "$PORTS/08_mem_sc_wrapper_headers_nonansi_fixed.json"`, after sourcing original Vivado 2025.2. Require genuine `13_4096_xsim.log` marker `M06_ORIGINAL_VENDOR_4096_RANGE_PASS` and `M06_ORIGINAL_VENDOR_4096_OUT_OF_RANGE_QUARANTINE_PASS`, result0, original vendor source hashes unchanged. Replays A–D in a NEW evidence directory; don't repeat their earlier accepted owner archives separately.
3. **G3 — real generated HLS to original SmartConnect integration:** use measured memory widths/IDs, do NOT wire wrong widths directly. Route read HLS to S00 READ_ONLY, write HLS to S03 WRITE_ONLY, using explicit converters if needed. Both must map to the SAME address-owned 64KiB offline scratch array; original mem_sc 256-bit upstream / 128-bit downstream is established only for its separate A–D simulation. Verify AW/W/B and AR/R transactions, 4KiB crossings, WSTRB/byte lanes, stalls, IDs/responses, and dirty-write-B **completion before a separate-master refetch**. Exercise fresh independent M02 oracle with 1 and 8 slots and forced dirty churn. Do not assume HLS C source order enforces a cross-master memory fence in integrated RTL.
4. **G4 — simulated failure/quarantine/commit and research acceptance:** force SLVERR/RRESP, timeouts, interrupted dirty page, illegal canonical page/address, partial write and no published trace on failed epoch. The raw C++ `m_axi` pointer interface does **not** independently expose RRESP/BRESP to the neural logic: require RTL wrapper or an explicit, independently proven system-level response/failure contract, not a false PASS. Preserve source, generated IP and simulator evidence SHA, M02/M03 exact trace and full 16-byte state image. Complete reproducible test explanation and roadmap. Only then request owner decision to accept M06 at explicitly OFFLINE scratch-memory scope.

**Non-claims:** Neither the real HLS CSim/synthesis nor the generated-port audit proves XSim generated-RTL correctness, shared real memory, original SmartConnect binding, Linux DDR allocator isolation, physical FPGA deployment or energy/performance on board. No JTAG/PS-DDR/bitstream actions authorized; no M06 merge/M07 without approval.
