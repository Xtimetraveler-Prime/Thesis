#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
EXPECTED_PART="xck26-sfvc784-2LV-c"
EXPECTED_CLOCK="10ns"
EXPECTED_UNCERTAINTY="12%"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"

require_tool() {
    local tool="$1"
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "ERROR: $tool is not on PATH. Source the Vitis/Vivado 2025.2 settings64.sh first." >&2
        exit 2
    fi
}

require_version() {
    local tool="$1"
    shift
    local version_output
    version_output="$("$tool" "$@" 2>&1 || true)"
    if [[ "$version_output" != *"$EXPECTED_VERSION"* ]]; then
        echo "ERROR: $tool is not reporting version $EXPECTED_VERSION." >&2
        echo "$version_output" >&2
        exit 2
    fi
}

for tool in python3 vitis vitis-run v++ vivado; do
    require_tool "$tool"
done

require_version vitis --version
require_version vitis-run --version
require_version v++ --version
require_version vivado -version

if [[ -z "${HLS_PART:-}" ]]; then
    echo "ERROR: HLS_PART is not set. For M11.3 use: export HLS_PART='$EXPECTED_PART'" >&2
    exit 2
fi

if [[ "$HLS_PART" != "$EXPECTED_PART" ]]; then
    echo "ERROR: M11.3 is frozen to target part $EXPECTED_PART, but HLS_PART=$HLS_PART" >&2
    exit 2
fi

STAGE_ROOT="/tmp/neuromorphic_twin_hls_${UID}/m11_3"
WORK_DIR="$STAGE_ROOT/work"
LOCAL_BUILD_DIR="$SCRIPT_DIR/build/m11_3"

rm -rf "$STAGE_ROOT" "$LOCAL_BUILD_DIR"
mkdir -p "$STAGE_ROOT" "$LOCAL_BUILD_DIR"
cp -R "$SCRIPT_DIR/include" "$STAGE_ROOT/"
cp -R "$SCRIPT_DIR/src" "$STAGE_ROOT/"
cp -R "$SCRIPT_DIR/tb" "$STAGE_ROOT/"
cp "$SCRIPT_DIR/hls_config.cfg" "$STAGE_ROOT/"

# Use the same Python-generated M11.2 corpus for C/RTL co-simulation.
PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$PROJECT_DIR/examples/generate_m11_hls_vectors.py" \
    --output "$STAGE_ROOT/tb/generated_m11_2_vectors.inc"

printf 'M11.3 toolchain: Vitis/Vivado %s\n' "$EXPECTED_VERSION"
printf 'M11.3 target part: %s\n' "$HLS_PART"
printf 'M11.3 target clock: %s (100 MHz)\n' "$EXPECTED_CLOCK"
printf 'M11.3 clock uncertainty: %s\n' "$EXPECTED_UNCERTAINTY"
printf 'M11.3 staging directory: %s\n' "$STAGE_ROOT"

cd "$STAGE_ROOT"

echo
echo '=== M11.3 C synthesis ==='
v++ -c --mode hls \
    --config hls_config.cfg \
    --work_dir "$WORK_DIR" \
    --part "$HLS_PART" \
    2>&1 | tee "$LOCAL_BUILD_DIR/vpp_hls_synthesis.log"

SYNTH_REPORT="$(find "$WORK_DIR" -type f -name 'neuron_step_v1_csynth.rpt' -print -quit)"
if [[ -z "$SYNTH_REPORT" ]]; then
    SYNTH_REPORT="$(find "$WORK_DIR" -type f -name '*_csynth.rpt' -print -quit)"
fi
if [[ -z "$SYNTH_REPORT" ]]; then
    echo "ERROR: HLS synthesis completed but no csynth report was found under $WORK_DIR" >&2
    exit 3
fi

cp "$SYNTH_REPORT" "$LOCAL_BUILD_DIR/neuron_step_v1_csynth.rpt"
printf 'HLS synthesis report: %s\n' "$LOCAL_BUILD_DIR/neuron_step_v1_csynth.rpt"

echo
echo '=== HLS synthesis report ==='
# The 2025.2 report tables put many numeric values on lines that do not repeat
# labels such as "Latency" or "LUT". Print the complete report instead of a
# label-only grep so the captured terminal log contains the actual numbers.
cat "$LOCAL_BUILD_DIR/neuron_step_v1_csynth.rpt"

echo
echo '=== M11.3 C/RTL co-simulation ==='
vitis-run --mode hls --cosim \
    --config hls_config.cfg \
    --work_dir "$WORK_DIR" \
    --part "$HLS_PART" \
    2>&1 | tee "$LOCAL_BUILD_DIR/vitis_hls_cosim.log"

COSIM_REPORT="$(find "$WORK_DIR" -type f \( -name '*cosim*.rpt' -o -name '*cosim*.log' \) -print -quit)"
if [[ -n "$COSIM_REPORT" ]]; then
    cp "$COSIM_REPORT" "$LOCAL_BUILD_DIR/$(basename "$COSIM_REPORT")"
fi

echo
echo 'M11.3 synthesis and C/RTL co-simulation completed successfully.'
echo "Saved generated reports/logs under: $LOCAL_BUILD_DIR"
