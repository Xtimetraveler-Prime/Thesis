# M06 G3.3: genuine ACTIVE control ACCEPTED; positive16 NEXT (2026-11-10)

## Owner evidence adjudication — do NOT rerun

Owner ZIP: M06_G3_3_ACTIVE_HLS_AMD_CORRECTED_REVIEW_20261110T154122Z.zip
ZIP SHA256: bb9aeb1481fa4dfaf6927c492f2fdb48e0341c5d5ee46feadc05574f4e1babc0
Original owner evidence directory:
~/Thesis_Evidence/m06_g3_3_actual_hls_invalid_geometry_xsim_hmem2v0k
Tested HEAD: b26de4bc0ee3996fdd584b61f183f003423ac810

**ACCEPTED at narrow scope:** original Vivado 2025.2 xvhdl, xvlog, xelab, xsim
all rc0. Genuine XSim at 3550 ns displayed exactly:
M06_G3_3_ACTUAL_HLS_ORIGINAL_AMD_AXILITE_BAD_GEOMETRY_XSIM_PASS
AP_DONE=1 STATUS=1 NO_CANONICAL_AXI_NO_NEURAL_PARITY_NO_BOARD.
result.txt exit_status=0. Original register map SHA attested AP_CTRL=0x00,
AP_RETURN_0=0x10; 14 real HLS .dat init files staged original/staged SHA-equal;
11 local, 40 original HLS RTL, 14 original HLS dat and 67 original AMD
vendor source hash entries match before/after; both original AMD converter XCI
SHA checks OK. No uninitialized HLS RAM warnings or unresolved Vivado errors.
Untracked owner logs in worktree_status.txt are not tracked code drift.

**NOT accepted:** positive neural inference, genuine canonical AXI workload,
independent M02/M03 trace/state parity, fault/dirty eviction, real DDR, G4 or M06.

Previous G1/G2/G3.2/G3.3-idle evidence remains immutable. Do not rerun it.
PR #80 stays DRAFT/UNMERGED; no physical FPGA, PS DDR, JTAG, bitstream, M07.

## Next prospective source-only candidate: G3.3 positive16

Generator: scripts/m06_g3_3_positive16_axilite_tb.py
Owner runner mode: scripts/run_m06_g3_3_actual_hls_idle_xsim.py --mode positive16
Packaging script: scripts/package_m06_g3_3_positive16_evidence.py

The candidate combines the unchanged 40 genuine generated-HLS files, genuine
two AMD 32->256 converters, original D3 SmartConnect, bounded 64->32 guards
and shared simulation-only 64KiB scratch. It writes **measured original**
AXI-Lite offsets, sends 16 actual neuron AXIS records (one initial voltage1,
other 15 zero, threshold5/bias0/reset0), zero synapses and external events,
1 tick, 1 resident slot, canonical read/write pointers0. It demands:
- actual AP_DONE and status0;
- 16 trace and 1 metrics handshakes;
- at least one real original-HLS canonical AR, AW and B handshake;
- canonical bytes for neuron0 voltage1 and tick watermark1, neighbor untouched;
- no original guard fault or unknown trace/metrics bits.

A positive16 owner PASS is only a SMALL positive connection smoke, not full
6-field independent M02/M03 parity or fault acceptance. Stream bit packing is
a prospective assumption that must be verified by real original HLS RTL.

Source-only CI executes Python negative tests and Icarus -tnull compile against
**fake port declarations only**. It never runs functional fake AMD RTL.

## Copy/paste owner verification commands

~~~bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m06-ddr-residency
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m06-ddr-residency
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m06_g3_3_positive16_axilite_tb.py' -v
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
    test -d "$dir" || { echo "MISSING ORIGINAL OWNER INPUT: $dir"; exit 2; }
done
for dir in "$HLS" "$EX" "$INV"; do
    test "$(cat "$dir/result.txt")" = "exit_status=0" || {
        echo "ORIGINAL OWNER INPUT NOT ACCEPTED: $dir"; exit 2;
    }
done

export INVOCATION_LOG="$HOME/Thesis_Evidence/m06_g3_3_positive16_invocation_$(date -u +%Y%m%dT%H%M%SZ).log"
export BEFORE_FILE="$(mktemp)"
find "$HOME/Thesis_Evidence" -maxdepth 1 -type d \
    -name 'm06_g3_3_actual_hls_positive16_xsim_*' | sort > "$BEFORE_FILE"
set -o pipefail
if python3 scripts/run_m06_g3_3_actual_hls_idle_xsim.py \
    --mode positive16 \
    --hls-cosim "$HLS" --original-d3 "$D3" \
    --original-report "$PORTS/02_original_mem_sc_ports.txt" \
    --original-headers "$PORTS/08_mem_sc_wrapper_headers_nonansi_fixed.json" \
    --original-dwc "$DW" --amd-export "$EX" \
    --accepted-inventory "$INV" 2>&1 | tee "$INVOCATION_LOG"
then
    echo "G3.3 POSITIVE16 COMMAND SUCCEEDED; VERIFY ALL GATE EVIDENCE"
else
    echo "G3.3 POSITIVE16 FIRST OWNER TRIAL FAILED; PRESERVE AND REVIEW"
fi
export LINK="$(comm -13 "$BEFORE_FILE" \
    <(find "$HOME/Thesis_Evidence" -maxdepth 1 -type d \
    -name 'm06_g3_3_actual_hls_positive16_xsim_*' | sort) | tail -n 1)"
echo "NEW EVIDENCE DIRECTORY: $LINK"
if test -n "$LINK" && test -d "$LINK"; then
    cat "$LINK/result.txt" "$LINK/commit.txt"
    test ! -f "$LINK/03_control_map.log" || cat "$LINK/03_control_map.log"
    test ! -f "$LINK/03_positive16_generation.log" || cat "$LINK/03_positive16_generation.log"
    test ! -f "$LINK/07_xsim.log" || tail -n 100 "$LINK/07_xsim.log"
    test ! -f "$LINK/owner_error.txt" || cat "$LINK/owner_error.txt"
fi
~~~

Expected real XSim line **only when genuinely achieved**:
M06_G3_3_ACTUAL_HLS_ORIGINAL_AMD_POSITIVE16_XSIM_PASS
STATUS=0 TRACE=16 METRICS=1 CANONICAL_READ_WRITE NO_M02_M03_PARITY_NO_BOARD

Also require result.txt exit_status=0, no fatal/.dat init warnings, both original
XCI digests OK, all before/after source manifests identical. If failure,
**DO NOT rerun**: submit first evidence ZIP, analyze first genuine failure.

## Mandatory ONE-ZIP command (PASS OR FAIL, SAME TERMINAL)

~~~bash
python3 scripts/package_m06_g3_3_positive16_evidence.py \
    --link "$LINK" \
    --invocation-log "$INVOCATION_LOG"
~~~

Expected ZIP path is printed by the script:
~/Thesis_Evidence/M06_G3_3_POSITIVE16_HLS_AMD_REVIEW_<UTC_TIMESTAMP>.zip

Exact allowlist is defined by NAMES inside the packager: result, commit,
worktree/error, all 01/02/03 original vendor plan + HLS init/control
generation logs/JSON, genuine 04/05/06/07 Vivado stage logs, two generated
**local testbench-only** SVs, original candidate/HLS/dat/vendor SHA before/after,
original XCI checks, source path lists, provenance folder refs, plus
08_operator_invocation_console.log and operator_evidence_path.txt.
**No proprietary original generated HLS Verilog, AMD RTL, .xci or .dat bytes.**
If first run fails before creating an evidence folder, the ZIP still records
operator invocation console (when present) and NOT_CREATED path.

M06 remains OPEN. Once this real owner gate is assessed, the subsequent
remaining work is independent actual M02/M03 6-field trace/16B canonical
state, high-offset page/dirty eviction and B-before-AR ordering and G4
fault/quarantine acceptance. No new milestone labels and no M07.
