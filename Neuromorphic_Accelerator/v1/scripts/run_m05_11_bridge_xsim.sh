#!/usr/bin/env bash
# M05.11a independent direct RTL bridge XSim — no HLS/IP regeneration, no board.
# Never overwrite or alter any original HLS, Vivado, Loihi or M05 evidence.
set -euo pipefail
if [[ "$#" -ne 0 ]]; then
    echo "Usage: bash scripts/run_m05_11_bridge_xsim.sh" >&2
    exit 2
fi
for tool in xvlog xelab xsim timeout sha256sum git python3; do
    command -v "$tool" >/dev/null || {
        echo "ERROR: missing $tool (source Vivado 2025.2 settings64.sh)" >&2
        exit 2
    }
done
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RTL="$ROOT/rtl/m05_11"
EVIDENCE_ROOT="${M05_EVIDENCE_ROOT:-$HOME/Thesis_Evidence}"
mkdir -p "$EVIDENCE_ROOT"
OUT="$(mktemp -d "$EVIDENCE_ROOT/neuromorphic_v1_m05_11_bridge_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXX")"
exit_code=1
finish() {
    printf 'exit_status=%s\n' "$exit_code" > "$OUT/result.txt"
    echo "M05.11 BRIDGE EVIDENCE: $OUT"
}
trap finish EXIT
git -C "$ROOT" rev-parse HEAD > "$OUT/commit.txt"
python3 --version > "$OUT/versions.txt" 2>&1
xvlog -version >> "$OUT/versions.txt" 2>&1 || true
sha256sum "$RTL/m05_trace_dma_packetizer.v" \
          "$RTL/m05_ingress_dma_unpad.v" \
          "$RTL/tb_m05_11_packetizer.sv" \
          "$RTL/tb_m05_11_ingress.sv" \
          "$ROOT/scripts/run_m05_11_bridge_xsim.sh" > "$OUT/source_sha256.txt"
cd "$OUT"

# Compile each standalone generated-RTL-independent test against the actual
# Verilog bridge. No HLS kernel, PS, DMA IP or physical K26 involvement.
xvlog -sv "$RTL/m05_trace_dma_packetizer.v" \
    "$RTL/tb_m05_11_packetizer.sv" 2>&1 | tee "02_packetizer_xvlog.log"
xelab --relax -debug typical -L xpm -L unisims_ver -L secureip \
    work.tb_m05_11_packetizer -s m05_11_packetizer_snapshot \
    2>&1 | tee "03_packetizer_xelab.log"
timeout --signal=TERM 120s xsim m05_11_packetizer_snapshot -R \
    2>&1 | tee "04_packetizer_xsim.log"
grep -Fq "PASS: M05.11 RTL packetizer" "04_packetizer_xsim.log" || {
    echo "ERROR: packetizer XSim lacked PASS marker" >&2
    exit 1
}
if grep -Eq 'Fatal: RTL_BRIDGE_FAIL|ERROR: RTL_BRIDGE_FAIL' "04_packetizer_xsim.log"; then
    echo "ERROR: packetizer XSim signaled an RTL test failure" >&2
    exit 1
fi

xvlog -sv "$RTL/m05_ingress_dma_unpad.v" \
    "$RTL/tb_m05_11_ingress.sv" 2>&1 | tee "02_ingress_xvlog.log"
xelab --relax -debug typical -L xpm -L unisims_ver -L secureip \
    work.tb_m05_11_ingress -s m05_11_ingress_snapshot \
    2>&1 | tee "03_ingress_xelab.log"
timeout --signal=TERM 120s xsim m05_11_ingress_snapshot -R \
    2>&1 | tee "04_ingress_xsim.log"
grep -Fq "PASS: M05.11 RTL ingress" "04_ingress_xsim.log" || {
    echo "ERROR: ingress XSim lacked PASS marker" >&2
    exit 1
}
if grep -Eq 'Fatal: RTL_BRIDGE_FAIL|ERROR: RTL_BRIDGE_FAIL' "04_ingress_xsim.log"; then
    echo "ERROR: ingress XSim signaled an RTL test failure" >&2
    exit 1
fi
echo "PASS: M05.11 standalone RTL trace packetization and MM2S ingress; no board or HLS kernel changed."
exit_code=0
