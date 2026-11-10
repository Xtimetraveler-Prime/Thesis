> **SUPERSEDED OWNER RUN STATUS — ACCEPTED 2026-11-10.** The original M02/M03 32x4 G3.3 owner experiment documented below PASSED in genuine Vivado 2025.2. The first accepted ZIP SHA256 is c3c9c6c1b21989b11f2d632b306981b10261aa1c6aedd8e54f7cd1c88ed4eb6c; tested commit bd52a31cbf6ef10a6a02749e772172b81527c54a; result exit_status=0 and real owner XSim original-HLS/AMD M02/M03 trace/state parity marker at 496930ns. DO NOT rerun accepted trial. Current work is **existing G4**, instructions in docs/M06_G4_REAL_HLS_AMD_FIRST_B_SLVERR_OWNER_GATE_2026_11_10.md. The historical one-run script below is retained for reproducibility and is NOT the next trial.

# M06 G3.3 — genuine original-HLS/AMD independent M02/M03 parity owner gate

2026-11-10 UTC. This is within EXISTING G3.3, not a new sub-milestone.

## Accepted owner result — do not rerun

The owner's original archive
M06_G3_3_POSITIVE16_HLS_AMD_REVIEW_20261110T161803Z.zip has SHA256
fd23ee9a57ec5d6aad1bce9f71eca175639d4dd57c9ad76bc2bdc72e6341f868.
Tested source commit: 080f85dd47fc4617d429d72b4c7e734c7e4c9cea.
Original immutable owner directory:
~/Thesis_Evidence/m06_g3_3_actual_hls_positive16_xsim_w1jle6j8.
Result: exit_status=0, genuine Vivado 2025.2 original xvhdl, xvlog,
xelab, xsim rc0. 07_xsim.log at 42790ns:
M06_G3_3_ACTUAL_HLS_ORIGINAL_AMD_POSITIVE16_XSIM_PASS STATUS=0 TRACE=16
METRICS=1 CANONICAL_READ_WRITE NO_M02_M03_PARITY_NO_BOARD.
Before/after SHA agree for 12 local, 40 generated original HLS RTL, 14 HLS
initialization .dat, and 67 genuine AMD vendor RTL; both original XCI checks OK.
Original generated HLS init staging same SHA. Four xelab warning notices
(environment/optional ports) remain recorded, not waived.

This accepts only positive 16-neuron single-tick control, AXIS and canonical
AXI read/write smoke. No exact independent neural trace or G4/DDR/FPGA claim.
Historical accepted G1, G2, G3.2, G3.3 idle and invalid-geometry remain intact.

## Next existing G3.3 test — source-ready, genuine owner XSim NOT RUN YET

The new owner mode m02_m03_parity uses the SAME original 40-file HLS and genuine
AMD original DWC/SmartConnect/guards/simulated canonical 64KiB memory. New
script m06_g3_3_m02_m03_owner_vectors.py reuses the accepted independent M02
dense fixture (32 neurons, 4 ticks, 5 recurrent edges, 17 external signed
current events) and cross-checks M02 event and M03 exact sparse outputs.
It tests exactly 128 six-field trace rows, full 32x16B canonical state including
tick watermarks, all 8 metrics, and AR/AW/B and B-before-AR ordering.
It targets canonical_first_neuron=4064 (last two 256B pages) with ONE slot,
requiring dirty eviction and recovery. Imported C struct bit packing is
candidate until genuine original HLS XSim; if a mismatch appears, preserve
FIRST failed owner log and diagnose the exact field. Source CI uses fake module
DECLARATIONS for Icarus -tnull only. Never run fake functional RTL.

Existing G4 fault injection, quarantine and full M06 acceptance remain OPEN.
No physical DDR, JTAG, board programming, bitstream, M07 or merge.

## ONE owner run in VS Code terminal

~~~bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m06-ddr-residency
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m06-ddr-residency
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1

python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m06_g3_3_m02_m03_owner_vectors.py' -v
python3 -m unittest discover -s tests -p 'test_m06_g3_3_m02_m03_parity_tb.py' -v
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
  test -d "$dir" || { echo "MISSING ORIGINAL OWNER EVIDENCE: $dir"; exit 2; }
done
for dir in "$HLS" "$EX" "$INV"; do
  test "$(cat "$dir/result.txt")" = "exit_status=0" || {
    echo "PRIOR OWNER EVIDENCE NOT ACCEPTED: $dir"; exit 2;
  }
done
export INVOCATION_LOG="$HOME/Thesis_Evidence/m06_g3_3_parity_invocation_$(date -u +%Y%m%dT%H%M%SZ).log"
export BEFORE_FILE="$(mktemp)"
find "$HOME/Thesis_Evidence" -maxdepth 1 -type d \
  -name 'm06_g3_3_actual_hls_m02_m03_parity_xsim_*' | sort > "$BEFORE_FILE"
set -o pipefail
if python3 scripts/run_m06_g3_3_actual_hls_idle_xsim.py \
    --mode m02_m03_parity \
    --hls-cosim "$HLS" \
    --original-d3 "$D3" \
    --original-report "$PORTS/02_original_mem_sc_ports.txt" \
    --original-headers "$PORTS/08_mem_sc_wrapper_headers_nonansi_fixed.json" \
    --original-dwc "$DW" --amd-export "$EX" \
    --accepted-inventory "$INV" 2>&1 | tee "$INVOCATION_LOG"
then
  echo "G3.3 M02/M03 OWNER COMMAND SUCCEEDED; CHECK ALL ACTUAL EVIDENCE"
else
  echo "G3.3 M02/M03 FIRST OWNER TRIAL FAILED; PRESERVE FIRST EVIDENCE"
fi
export LINK="$(comm -13 "$BEFORE_FILE" \
  <(find "$HOME/Thesis_Evidence" -maxdepth 1 -type d \
    -name 'm06_g3_3_actual_hls_m02_m03_parity_xsim_*' | sort) | tail -n 1)"
echo "FIRST NEW EVIDENCE DIRECTORY: $LINK"
if test -n "$LINK" && test -d "$LINK"; then
  cat "$LINK/result.txt" "$LINK/commit.txt"
  test ! -f "$LINK/03_independent_m02_m03_vectors.log" || cat "$LINK/03_independent_m02_m03_vectors.log"
  test ! -f "$LINK/03_m02_m03_parity_generation.log" || cat "$LINK/03_m02_m03_parity_generation.log"
  test ! -f "$LINK/07_xsim.log" || tail -n 100 "$LINK/07_xsim.log"
  test ! -f "$LINK/owner_error.txt" || cat "$LINK/owner_error.txt"
fi
~~~

One *genuine* PASS requires:
M06_G3_3_ACTUAL_HLS_AMD_M02_M03_TRACE_STATE_PARITY_XSIM_PASS
32_NEURONS 4_TICKS 1_CACHE_SLOT HIGH_ADDR DIRTY_EVICT B_BEFORE_AR NO_DDR_NO_BOARD

Also require result.txt exit_status=0, no real XSim FAIL/fatal/uninitialized
data, identical local/HLS/AMD/HLS-dat before-after SHA and both genuine AMD
XCI checks OK. A source-only CI PASS does NOT satisfy this gate.

## Mandatory one-ZIP on PASS OR FAIL (SAME TERMINAL)

~~~bash
python3 scripts/package_m06_g3_3_positive16_evidence.py \
    --mode m02_m03_parity \
    --link "$LINK" \
    --invocation-log "$INVOCATION_LOG"
~~~

Output path (script prints exact timestamp and SHA):
~/Thesis_Evidence/M06_G3_3_M02_M03_PARITY_HLS_AMD_REVIEW_<UTC_TIMESTAMP>.zip

Contents: allowlisted first-owner result/commit/worktree/error, original
AMD compile plans and reports, original HLS data stage and control-map logs,
new independent M02/M03 vector generation, generated SV bench and SVH oracle
(both local test artifacts only), original 04–07 Vivado/XSim logs, 12+ local
source hashes, 40 HLS RTL, 14 HLS .dat and 67 AMD RTL before/after manifests,
original AMD converter XCI check, compiled source-path lists, owner console
and evidence-folder reference. Proprietary original AMD/HLS Verilog, XCI and
dat payloads are excluded. Even a pre-output FAIL gets a ZIP with original
invocation console and NOT_CREATED path. Do not rerun unchanged.
