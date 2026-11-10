# M06 genuine Vitis 2025.2 cosimulation: C testbench vector-generation failure and scoped alias correction

**2026-11-09 19:03 America/Denver. M06 OPEN, PR #80 DRAFT/UNMERGED.** This records the immutable failed owner experiment and the next targeted source trial; no generated RTL cosim PASS is claimed.

## Uploaded real evidence reviewed

1. Owner original AMD A–E archive `m06_stage_e_review_20261110T015513Z.tar.gz`: original directory `~/Thesis_Evidence/m06_original_vendor_mem_sc_xsim_20261110T013912Z_VZwFV2`, `result.txt=exit_status=0`, `commit.txt=ed17c54b8f2b4f24fedf203f04a31dba4a0ae920`. Two original D3 source paths and digests in `sha_before.txt` and `sha_after.txt` **match exactly** (manifest-only evidence). Five real XSim 2025.2 logs (05,07,09,11,13) individually contain their required distinct A–E PASS markers and `exit 0`. Stage E highest page255, neuron4095, byte65535, dirty_wb1, M00 write16/read48, page256 fault quarantine. The owner-only live-source digest comparison requires the installed original D3 directory and new `scripts/m06_original_stage_e_evidence_audit.py`, which has NOT been run by this assistant on the owner PC. Source-version/shas in archive are authentic user-provided records, not an independent live rehash. Stage E is an ORIGINAL AMD IP simulation using a 64KiB synthetic scratch target, no actual HLS neural RTL, no board/DDR.

2. Owner original HLS `--cosim` archive `m06_cosim_review_20261110T015730Z.tar.gz`: `~/Thesis_Evidence/m06_paged_rolling_hls_cosim_20261110T013720Z_ETyAGM`, `result.txt=exit_status=1`, commit `ed17c54b8f2b4f24fedf203f04a31dba4a0ae920`, original source-before and source-after SHA **equal**. Real `03_cosim.log` says `COSIM 212-47 Using XSIM for RTL simulation` then instrumented C TB `COSIM 212-302 Starting C TB testing`, prints `M06_HLS_CSIM_FAIL high-offset 20tick wheel + 4k map`, abort `COSIM 212-359 C TB simulation failed nonzero=1` and `COSIM 212-4 finished FAIL`. **No RTL test vectors generated, no XSim RTL exercised, no actual C/RTL equivalence verdict.** Separate real `--csim` and `--synth` at previous commit succeeded and are preserved; do not conflate the failing C TB instrumentation step with an RTL functional comparison.

3. Owner measured generated port JSON `m06_paged_hls_ports_20261110T010821Z_6262.json` from original successful `--synth`: 37 generated Verilog modules, 125 top pins, top SHA `b42b47a12e016cb315bd9284cefa8b148e3a42a30717f43a7ee73ec950ac3a8f`. Exact generated `gmem_read` READ-ONLY 32-bit/64-bit addr, `gmem_write` WRITE-ONLY 32-bit/64-bit addr; original SmartConnect S00/S03 **256-bit**. Both separate 32→256-bit width adapters must be functionally proven before original vendor integration. 4096 logical 16-byte records in 64KiB and 8×256B slots; neither physical DDR/addresses nor original SmartConnect link proven. ABI stream payload widths neurons128, synapses192, external128, trace192, metrics256.

4. Uploaded `m06_paged_rolling_replay_Pipeline_VITIS_LOOP_356_14_csynth.rpt` is a **real generated internal helper loop report**, NOT the whole HLS neural top. It reports loop II achieved64 vs target1 and a 1365 FF/1470 LUT resource estimate **for that helper only**, never whole-chip numbers. For complete design timing/resources need `$HLS/work/hls/syn/report/m06_paged_rolling_replay_csynth.rpt`; owner should upload that exact report, not another `Pipeline_VITIS_LOOP_...` subordinate report.

## Focused development correction, NOT yet Vitis-verified

The prior testbench passes the SAME `memory.data()` pointer to both `canonical_read_words` and `canonical_write_words`, while HLS targets two distinct `m_axi` bundles. Instrumented C TB may treat pointer ports as independent memory if missing alias metadata; this is a **plausible hypothesis**, not yet proven. AMD UG1399 documents `#pragma HLS ALIAS ports=<list> distance=<int>` for different-m_axi-bundle pointers with equal depth and slave offsets. New M06 source adds exactly `#pragma HLS ALIAS ports=canonical_read_words,canonical_write_words distance=0`, preserving distinct S00/S03 read/write interfaces and M05 arithmetic. The directive documents intent and informs Vitis dependency analysis, **not** cross-master AXI B-response fencing or real shared DDR connection. Source-only `scripts/m06_paged_hls_alias_contract.py` and `tests/test_m06_paged_hls_alias_contract.py` (five positive/negative tests) enforce this exact declaration and that the masters remain separate at depth16384. `m06_paged_rolling_csim_tb.cpp` emits detailed `M06_HLS_CSIM_DIAG` for high-offset/dirty-eviction/invalid-geometry failures without changing any PASS thresholds.

**Consequences:** The modified M06 source is a *new trial*, so prior generated Verilog/SHA/port JSON is HISTORICAL ONLY. Rerun genuine Vitis `--cosim` on a fresh owner output. If it passes, run independent generated-port audit against **that new** cosim folder and inspect new actual widths. If it fails, preserve that folder; use first `M06_HLS_CSIM_DIAG` or tool compilation error to find the root cause. Do not run Stage E again; its original proof stays valid.

## Exact next owner commands

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m06-ddr-residency
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m06-ddr-residency
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m06*.py' -v
python3 scripts/m06_paged_hls_alias_contract.py --root .
source "$HOME/Vivado/2025.2/Vitis/settings64.sh"
vitis-run --version
bash scripts/run_m06_paged_rolling_hls.sh --cosim
echo "M06 corrected alias genuine cosim exit: $?"
export COSIM="$(find "$HOME/Thesis_Evidence" -maxdepth 1 -type d -name 'm06_paged_rolling_hls_cosim_*' | sort | tail -n 1)"
cat "$COSIM/result.txt" "$COSIM/commit.txt"
cmp "$COSIM/source_before_sha256.txt" "$COSIM/source_after_sha256.txt"
grep -E 'M06_HLS_CSIM_(DIAG|FAIL)|COSIM 212-(359|320|5|4|1000)|ERROR:|PASS' "$COSIM/03_cosim.log" | tail -n 55
tail -n 100 "$COSIM/03_cosim.log"
```

When `exit_status=0` and the genuine report has actual C/RTL PASS, audit the **new** generated port contract. On failure supply **new** `result.txt`, `commit.txt`, `03_cosim.log`, `01_csim.log`, `02_csynth.log`, before/after source SHA (original files unchanged). Do NOT report cosim PASS based solely on CSim's older marker.

## Unfinished acceptance after genuine C/RTL pass

G3 genuine generated HLS read/write RTL across measured-width AMD adapters to ORIGINAL SmartConnect S00/S03 and common 64KiB scratch memory: burst/4KiB/WSTRB/backpressure/IDs/BRESP/RRESP and cross-master read-after-write; G4 independent full M02/M03 trace and 16-byte canonical image with forced dirty eviction and quarantined negative/error responses. The HLS C pointer interface has no explicit BRESP/RRESP errors and may require a tested supervisor before safety claims. All originals immutable, no physical DDR/board/JTAG, no PR merge or M07 without owner approval.
