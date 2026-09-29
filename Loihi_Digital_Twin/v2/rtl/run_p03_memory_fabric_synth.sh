#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
EXPECTED_PART="xck26-sfvc784-2LV-c"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
HOST_BRIDGE_RTL="$SCRIPT_DIR/p03_memory_host_bridge.v"
MEMORY_FABRIC_RTL="$SCRIPT_DIR/p03_memory_fabric.v"
TCL_SCRIPT="$SCRIPT_DIR/synth_p03_memory_fabric.tcl"
BUILD_DIR="$SCRIPT_DIR/build/p03_memory_fabric_synth"
REPORT_DIR="$BUILD_DIR/reports"

command -v vivado >/dev/null 2>&1 || {
    echo "ERROR: vivado is not on PATH. Source Vivado 2025.2 settings64.sh first." >&2
    exit 2
}
if [[ "$(vivado -version 2>&1 || true)" != *"$EXPECTED_VERSION"* ]]; then
    echo "ERROR: Vivado is not reporting $EXPECTED_VERSION" >&2
    exit 2
fi

rm -rf "$BUILD_DIR"
mkdir -p "$REPORT_DIR"

vivado -mode batch \
  -source "$TCL_SCRIPT" \
  -tclargs "$HOST_BRIDGE_RTL" "$MEMORY_FABRIC_RTL" "$EXPECTED_PART" "$REPORT_DIR" \
  2>&1 | tee "$BUILD_DIR/vivado_memory_fabric_synth.log"

for required in \
  "$REPORT_DIR/utilization_memory_fabric_synth.rpt" \
  "$REPORT_DIR/utilization_memory_fabric_hierarchical_synth.rpt" \
  "$REPORT_DIR/memory_primitives_synth.rpt" \
  "$REPORT_DIR/memory_fabric_synth_metrics.txt"; do
  [[ -f "$required" ]] || {
    echo "ERROR: missing P03 XPM synthesis artifact: $required" >&2
    exit 3
  }
done

echo
echo '=== P03 XPM memory-fabric synthesis metrics ==='
cat "$REPORT_DIR/memory_fabric_synth_metrics.txt"
echo
echo '=== P03 XPM bank hierarchy ==='
grep -E 'u_config_words|u_state_words|u_axon_words|u_synapse_words|u_route_desc_words|u_route_words|u_input_events|u_trace_words|u_packet_words' \
  "$REPORT_DIR/utilization_memory_fabric_hierarchical_synth.rpt" || true

echo
echo 'P03 XPM memory-fabric synthesis gate completed.'
