#!/usr/bin/env bash
# M05.11b: pure AXI4-Lite command slave verification, no original HLS or board.
# One fresh evidence directory per run; never delete old Thesis_Evidence.
set -euo pipefail
if [[ "$#" -ne 0 ]]; then
    echo "Usage: bash scripts/run_m05_11_axil_xsim.sh" >&2
    exit 2
fi
for program in xvlog xelab xsim timeout git sha256sum; do
    command -v "$program" >/dev/null || {
        echo "ERROR: $program missing; source Vivado 2025.2 settings64.sh" >&2
        exit 2
    }
done
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RTL="$ROOT/rtl/m05_11"
BASE="${M05_EVIDENCE_ROOT:-$HOME/Thesis_Evidence}"
mkdir -p "$BASE"
OUT="$(mktemp -d "$BASE/neuromorphic_v1_m05_11_axil_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXX")"
result=1
report_exit() {
    printf 'exit_status=%s\n' "$result" > "$OUT/result.txt"
    echo "M05.11b AXI-Lite evidence: $OUT"
}
trap report_exit EXIT
git -C "$ROOT" rev-parse HEAD > "$OUT/commit.txt"
sha256sum "$RTL/m05_11_axil_session_controller.v" \
          "$RTL/m05_11_stream_shell.v" \
          "$RTL/m05_trace_dma_packetizer.v" \
          "$RTL/m05_ingress_dma_unpad.v" \
          "$RTL/tb_m05_11_axil_controller.sv" \
          "$ROOT/scripts/run_m05_11_axil_xsim.sh" > "$OUT/source_sha256.txt"
cd "$OUT"
xvlog -sv "$RTL/m05_11_axil_session_controller.v" \
    "$RTL/tb_m05_11_axil_controller.sv" 2>&1 | tee 02_xvlog.log
xelab --relax -debug typical -L xpm -L unisims_ver -L secureip \
    work.tb_m05_11_axil_controller -s m05_11_axil_snapshot \
    2>&1 | tee 03_xelab.log
timeout --signal=TERM 120s xsim m05_11_axil_snapshot -R \
    2>&1 | tee 04_xsim.log
if grep -Eq 'Fatal: AXIL_BRIDGE_FAIL|ERROR: AXIL_BRIDGE_FAIL' 04_xsim.log; then
    echo "ERROR: AXI-Lite RTL testbench signaled fatal" >&2
    exit 1
fi
grep -Fq "PASS: M05.11b AXI-Lite" 04_xsim.log || {
    echo "ERROR: no M05.11b genuine XSim PASS marker" >&2
    exit 1
}
echo "PASS: M05.11b standalone AXI4-Lite session controller tested in Vivado; no original HLS or physical board."
result=0
