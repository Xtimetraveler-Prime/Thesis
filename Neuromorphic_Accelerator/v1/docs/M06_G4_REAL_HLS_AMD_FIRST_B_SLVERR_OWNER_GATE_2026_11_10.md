# M06 existing G4 — genuine original-HLS/AMD first write-B SLVERR owner gate

2026-11-10 UTC. No new submilestone. PR #80 stays DRAFT, no M07/merge.

## G3.3 independent M02/M03 parity: ACCEPTED

Uploaded owner evidence:
M06_G3_3_M02_M03_PARITY_HLS_AMD_REVIEW_20261110T165556Z.zip
SHA256 c3c9c6c1b21989b11f2d632b306981b10261aa1c6aedd8e54f7cd1c88ed4eb6c
Tested commit bd52a31cbf6ef10a6a02749e772172b81527c54a
Owner directory ~/Thesis_Evidence/m06_g3_3_actual_hls_m02_m03_parity_xsim_9fh6rx40
result.txt exit_status=0. Original Vivado 2025.2 xvhdl/xvlog/xelab/xsim
each rc0. Genuine XSim at 496930ns emitted:
M06_G3_3_ACTUAL_HLS_AMD_M02_M03_TRACE_STATE_PARITY_XSIM_PASS
32_NEURONS 4_TICKS 1_CACHE_SLOT HIGH_ADDR DIRTY_EVICT B_BEFORE_AR NO_DDR_NO_BOARD

Original full-128 six-field trace, 32 final 16B canonical neuron records,
one-slot paging metrics, original AMD AR/AW/B ordering checked against
existing independent M02 dense/event + M03 exact sparse. 14 local, 40
generated HLS, 14 original .dat and 67 original AMD SHA before/after same.
Both AMD DWC original XCI checks OK. Four 06_xelab warnings (environment
LIBRARY_PATH, mb_reset, 2x aclk2x) preserved; 05_xvlog warnings 0.
No PS DDR/FPGA/fault/rollback claim. DO NOT rerun this accepted experiment.

## G4: NEW genuine connected first-B-SLVERR owner trial, NOT YET RUN

Mode: g4_first_b_slverr
Runner: scripts/run_m06_g3_3_actual_hls_idle_xsim.py
Generator: scripts/m06_g4_actual_hls_write_fault_tb.py
Synthesis-oriented independent gate: rtl/m06/m06_g4_epoch_commit_gate.sv

The generator reuses the accepted 16-neuron one-tick control and genuine
original HLS/AMD identity gates, enabling exactly one existing scratch
endpoint inject_next_b_slverr input at the FIRST original AMD-side AW.
It observes RAM-side B SLVERR, original HLS-side B SLVERR, original
write_guard_fault sticky latch and independent epoch-gate poisoned output.
Any commit token is FATAL. Trace release is a TESTBENCH-ONLY monitor;
there is NO production trace FIFO or hardware-atomic DDR rollback.
Epoch begin is driven by the testbench, not production HLS AP_START wiring.
An HLS kernel may stall after an AXI memory fault. G4 mode does not assert
HLS completion or post-fault recovery. Only original owner Vivado can prove
this first error propagation. Fake-port Icarus -tnull is syntax-only.

## VS Code terminal — source regressions BEFORE one new genuine owner trial

~~~bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m06-ddr-residency
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m06-ddr-residency
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m06_g4_actual_hls_write_fault_tb.py' -v
python3 -m unittest discover -s tests -p 'test_m06_g4_epoch_commit_gate.py' -v
python3 -m unittest discover -s tests -p 'test_m06_g3_3_positive16_evidence_package.py' -v
python3 -m unittest discover -s tests -p 'test_m06*.py' -v
source "$HOME/Vivado/2025.2/Vivado/settings64.sh"
xvlog -version
export HLS="$HOME/Thesis_Evidence/m06_paged_rolling_hls_cosim_20261110T022111Z_iMNors"
export D3="$HOME/Thesis_Evidence/neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ"
export PORTS="$HOME/Thesis_Evidence/m06_vendor_xsim_port_contract_20261109T181345Z_f4X4Of"
export DW="$HOME/Thesis_Evidence/m06_g3_real_amd_dwc_20261110T032341Z_YUDRD3"
export EX="$(find "$HOME/Thesis_Evidence" -maxdepth 1 -type d -name 'm06_g3_amd_sim_export_*' | sort | tail -n 1)"
export INV="$HOME/Thesis_Evidence/m06_g3_3_hls_source_inventory_20261110T061525Z_qbrHKZ"
for dir in "$HLS" "$D3" "$PORTS" "$DW" "$EX" "$INV"; do
  test -d "$dir" || { echo "MISSING ORIGINAL OWNER SOURCE: $dir"; exit 2; }
done
for dir in "$HLS" "$EX" "$INV"; do
  test "$(cat "$dir/result.txt")" = "exit_status=0" || {
    echo "PRIOR ORIGINAL OWNER GATE FAILED: $dir"; exit 2;
  }
done
export INVOCATION_LOG="$HOME/Thesis_Evidence/m06_g4_first_b_invocation_$(date -u +%Y%m%dT%H%M%SZ).log"
export BEFORE_FILE="$(mktemp)"
find "$HOME/Thesis_Evidence" -maxdepth 1 -type d -name 'm06_g3_3_actual_hls_g4_first_b_slverr_xsim_*' | sort > "$BEFORE_FILE"
set -o pipefail
if python3 scripts/run_m06_g3_3_actual_hls_idle_xsim.py \
    --mode g4_first_b_slverr \
    --hls-cosim "$HLS" --original-d3 "$D3" \
    --original-report "$PORTS/02_original_mem_sc_ports.txt" \
    --original-headers "$PORTS/08_mem_sc_wrapper_headers_nonansi_fixed.json" \
    --original-dwc "$DW" --amd-export "$EX" \
    --accepted-inventory "$INV" 2>&1 | tee "$INVOCATION_LOG"
then
  echo "G4 FIRST B-SLVERR original XSim reports PASS; audit actual evidence"
else
  echo "G4 FIRST B-SLVERR first original XSim FAILED; preserve first evidence"
fi
export LINK="$(comm -13 "$BEFORE_FILE" <(find "$HOME/Thesis_Evidence" -maxdepth 1 -type d -name 'm06_g3_3_actual_hls_g4_first_b_slverr_xsim_*' | sort) | tail -n 1)"
echo "FIRST NEW EVIDENCE: $LINK"
if test -n "$LINK" && test -d "$LINK"; then
  cat "$LINK/result.txt" "$LINK/commit.txt"
  test ! -f "$LINK/03_g4_first_b_fault_generation.log" || cat "$LINK/03_g4_first_b_fault_generation.log"
  test ! -f "$LINK/07_xsim.log" || tail -n 120 "$LINK/07_xsim.log"
  test ! -f "$LINK/owner_error.txt" || cat "$LINK/owner_error.txt"
fi
python3 scripts/package_m06_g3_3_positive16_evidence.py \
  --mode g4_first_b_slverr \
  --link "$LINK" --invocation-log "$INVOCATION_LOG"
~~~

Mandatory exactly one uploadable first owner ZIP ON PASS OR FAIL:
~/Thesis_Evidence/M06_G4_FIRST_B_SLVERR_HLS_AMD_REVIEW_<UTC_TIMESTAMP>.zip
Packager excludes proprietary original Vitis/AMD RTL, .xci and .dat bytes.
If first owner trial fails even before output, package invocation log.
Do NOT rerun unchanged first-failure experiment.

Expected real owner marker, not yet earned:
M06_G4_ACTUAL_HLS_AMD_FIRST_B_SLVERR_QUARANTINE_XSIM_PASS
ORIGINAL_AMD_B_TO_HLS_GUARD_POISON NO_COMMIT NO_ROLLBACK_NO_DDR_NO_BOARD

Require result.txt exit_status=0, real original owner XSim marker once,
real original Vivado logs/AMD error handshakes, matching original sources
SHA before/after, genuine HLS .dat stage and both AMD XCI checks OK.
Source-only CI or fake declarations alone do not prove G4 acceptance.

## Further G4 requirements AFTER this FIRST trial (even if PASS)

Original-AMD read error, lost-B/stall and late response fault, trace release,
state quarantine and trustworthy discard/restore policy remain open. The
candidate epoch gate is not an atomic DDR controller and no board/JTAG,
PS DDR or physical rollback is yet proven. M06 remains OPEN.
