# M06 existing G4 — original-HLS/AMD read error, missing B, quarantine and explicit restore

2026-11-10 UTC. No new milestone subdivisions. Keep M06 OPEN, PR #80 DRAFT/UNMERGED, no M07/board/JTAG/PS DDR.

## Genuine original Vivado 2025.2 first-B SLVERR ACCEPTED

Uploaded ZIP: M06_G4_FIRST_B_SLVERR_HLS_AMD_REVIEW_20261110T171436Z.zip
SHA256: 11c2960d6a130e530ccfde345c42828e42626936e523a77f7b35bacffc87eaca
Tested commit: e3a690f6b92dd1ae878a4e327abf158a45586a56
Owner dir: ~/Thesis_Evidence/m06_g3_3_actual_hls_g4_first_b_slverr_xsim_3yx_bktw

result.txt exit_status=0; genuine original xvhdl/xvlog/xelab/xsim rc0.
XSim 3900 ns original marker:
M06_G4_ACTUAL_HLS_AMD_FIRST_B_SLVERR_QUARANTINE_XSIM_PASS
ORIGINAL_AMD_B_TO_HLS_GUARD_POISON NO_COMMIT NO_ROLLBACK_NO_DDR_NO_BOARD

First original AMD-side scratch B SLVERR, original HLS-side write B SLVERR,
original write guard sticky fault and separate G4 supervisor poison, no commit.
Before/after SHA identical: 16 local sources, 40 generated HLS RTL,
14 original HLS .dat and 67 original AMD RTL; 2 genuine original DWC XCI OK.
The four known vendor/environment elaboration warnings remain recorded.
NOT an actual physical DDR rollback, trace buffer or restored epoch.
Prior G1/G2/G3.2/G3.3 original positive and independent M02/M03 parity
experiments remain accepted. DO NOT rerun an accepted owner experiment.

## Three NEW owner Vivado cases — not accepted until genuine XSim

1. g4_first_r_slverr: inject first ORIGINAL scratch memory R SLVERR.
   Demand original AMD R error reaches original-HLS RRESP, read guard
   sticky fault and G4 supervisor poison. Actual synthesizable
   m06_g4_output_quarantine buffers raw HLS trace+metrics and must
   release ZERO of either on fault.

2. g4_stalled_b: withhold the ORIGINAL scratch BVALID/BREADY at only
   memory endpoint, without faking HLS/AMD or guard. Demand RAM
   pending B, NO HLS-side B handshake and bounded G4 epoch timeout
   poisoning. Actual trace+metrics quarantine must release ZERO.
   MAX_EPOCH_CYCLES=10000 is a simulation watchdog, NOT measured
   physical DDR timing.

3. g4_discard_restore: first cause real original R SLVERR and quarantine,
   then externally RESET original HLS+AMD and explicitly overwrite
   ALL 65536 canonical scratch bytes with known pristine image.
   Rerun original generated-HLS 16x1 positive neural inference.
   Require original HLS AXI-Lite AP_DONE and AP_RETURN=0,
   ZERO first failed-run output, and full release of exactly
   16 clean six-field trace records + 1 metrics word ONLY AFTER
   successful epoch-gate commit; verify canonical bytes.
   This proves only EXPLICIT SIMULATION-OWNER RESTORE, never
   automatic crash-atomic DDR rollback.

Original generated Vitis HLS RTL and AMD SC/DWCs are reused unchanged.
Source CI is only fake port DECLARATIONS with Icarus -tnull plus real
standalone FIFO/gate RTL vvp. No functional HLS/AMD fake simulation.

## VS Code source regression verification FIRST

~~~bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m06-ddr-residency
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m06-ddr-residency
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m06_g4_actual_hls_fault_matrix_tb.py' -v
python3 -m unittest discover -s tests -p 'test_m06_g4_output_quarantine.py' -v
python3 -m unittest discover -s tests -p 'test_m06_g4_actual_hls_recovery_tb.py' -v
python3 -m unittest discover -s tests -p 'test_m06_g3_3_positive16_evidence_package.py' -v
python3 -m unittest discover -s tests -p 'test_m06*.py' -v
~~~

The three Icarus/VVP tests must NOT skip. Do NOT begin the original owner
fault experiments on regression failure. Do not rerun old accepted gates.

## Original-owner first-run one ZIP per mode; STOP at first failure

From same VS Code terminal, AFTER tests pass:
~~~bash
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
    echo "PRIOR OWNER SOURCE NOT ACCEPTED: $dir"; exit 2;
  }
done
set -o pipefail
for MODE in g4_first_r_slverr g4_stalled_b g4_discard_restore; do
  echo "START ONE NEW G4 OWNER CASE: $MODE"
  INVOCATION_LOG="$HOME/Thesis_Evidence/m06_$MODE_first_console_$(date -u +%Y%m%dT%H%M%SZ).log"
  BEFORE_FILE="$(mktemp)"
  find "$HOME/Thesis_Evidence" -maxdepth 1 -type d \
     -name "m06_g3_3_actual_hls_$MODE"_xsim_\* | sort > "$BEFORE_FILE"
  if python3 scripts/run_m06_g3_3_actual_hls_idle_xsim.py \
       --mode "$MODE" \
       --hls-cosim "$HLS" --original-d3 "$D3" \
       --original-report "$PORTS/02_original_mem_sc_ports.txt" \
       --original-headers "$PORTS/08_mem_sc_wrapper_headers_nonansi_fixed.json" \
       --original-dwc "$DW" --amd-export "$EX" \
       --accepted-inventory "$INV" 2>&1 | tee "$INVOCATION_LOG"
  then
    OWNER_STATUS=0
    echo "OWNER RUN reports PASS: $MODE; audit still required"
  else
    OWNER_STATUS=1
    echo "FIRST OWNER RUN FAILED: $MODE; preserve first evidence"
  fi
  LINK="$(comm -13 "$BEFORE_FILE" \
     <(find "$HOME/Thesis_Evidence" -maxdepth 1 -type d \
       -name "m06_g3_3_actual_hls_$MODE"_xsim_\* | sort) | tail -n 1)"
  echo "FIRST EVIDENCE DIR: $LINK"
  if test -n "$LINK" && test -d "$LINK"; then
    cat "$LINK/result.txt" "$LINK/commit.txt"
    test ! -f "$LINK/07_xsim.log" || tail -n 100 "$LINK/07_xsim.log"
    test ! -f "$LINK/owner_error.txt" || cat "$LINK/owner_error.txt"
  fi
  if ! python3 scripts/package_m06_g3_3_positive16_evidence.py \
      --mode "$MODE" --link "$LINK" \
      --invocation-log "$INVOCATION_LOG"
  then
    echo "EVIDENCE ZIP FAILURE: $MODE"; break
  fi
  if test "$OWNER_STATUS" != 0; then
    echo "STOP: upload FIRST failed ZIP; do not rerun or proceed"; break
  fi
done
~~~

Expected real owner mode-specific markers, NOT YET EARNED:
M06_G4_ACTUAL_HLS_AMD_FIRST_R_SLVERR_QUARANTINE_XSIM_PASS
M06_G4_ACTUAL_HLS_AMD_STALLED_B_WATCHDOG_QUARANTINE_XSIM_PASS
M06_G4_ACTUAL_HLS_AMD_FAULT_DISCARD_RESTORE_CLEAN_COMMIT_XSIM_PASS

ZIP output prefixes (UTC timestamp/SHA printed by strict packager):
M06_G4_FIRST_R_SLVERR_HLS_AMD_REVIEW_
M06_G4_STALLED_B_HLS_AMD_REVIEW_
M06_G4_DISCARD_RESTORE_HLS_AMD_REVIEW_

Upload all THREE ZIPs if all succeed, otherwise ONLY the first failed ZIP.
Original HLS/AMD RTL, original .dat and .xci never enter ZIP allowlist.

## Closure contract

For genuine G4 original owner acceptance, require PASS markers,
exit_status=0, authentic tool logs and handshake evidence, full original
HLS+AMD and local SHA before-after equality, staged authentic HLS dat,
both original AMD XCI SHA checks, and no unexplained warnings/errors.
No accepted simulation gate is ever re-run unchanged.

Even if all pass, M06 closure is limited to ORIGINAL 64KiB simulation-owned
canonical DDR image; physical DDR ownership, real FPGA/JTAG, crash-atomic
image rollback, trace FIFO synthesis/timing/BRAM and production control
wiring are NOT proven. G4/M06 remain OPEN until evidence is independently
reviewed and user approves the explicit scope. No M07 or PR #80 merge yet.
