#!/usr/bin/env bash
# M08 D3.2 -- owner PC Vivado 2025.2 PASSIVE FAN synthesis ONLY.
# No existing owner project is modified. No route, .bit, .dtbo, JTAG or board.
set -euo pipefail

if [[ "$EUID" -eq 0 ]]; then
    echo "M08_D3_2_PASSIVE_PC_REFUSED: do not run Vivado as root" >&2
    exit 2
fi
if ! command -v python3 >/dev/null 2>&1 || ! command -v vivado >/dev/null 2>&1; then
    echo "M08_D3_2_PASSIVE_PC_REFUSED: python3 and local Vivado must be on PATH" >&2
    exit 2
fi

ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd -P)"
EVIDENCE_BASE="$HOME/Thesis_Evidence/M08"
mkdir -p -- "$EVIDENCE_BASE"

# Verify the genuine original fan sources and that only synth_1 is permissible.
python3 "$ROOT/scripts/m08_d3_2_passive_synth_gate.py" >/dev/null

RUN="$(mktemp -d "$EVIDENCE_BASE/m08_d3_2_passive_synth_XXXXXXXX")"
mkdir -- "$RUN/output"
printf 'M08_D3_2_PASSIVE_PC_NEW_EVIDENCE_DIR=%s\n' "$RUN"

# Generate a distinct D3A no-HPM/fan-only BD in this new run; no original
# immutable D3A receipt, native Vivado project, or quarantined image is edited.
vivado -mode batch \
    -source "$ROOT/scripts/m08_d3a_passive_fan_bd_candidate.tcl" \
    -log "$RUN/01_passive_bd_vivado.log" \
    -journal "$RUN/02_passive_bd_vivado.jou" \
    -tclargs "$ROOT" "$RUN/output"

# Reopen ONLY the newly generated BD project and run synthesis, NEVER route,
# write_bitstream, boot firmware packaging, DTBO or physical board operations.
vivado -mode batch \
    -source "$ROOT/scripts/m08_d3_2_passive_synth_only.tcl" \
    -log "$RUN/03_passive_synth_vivado.log" \
    -journal "$RUN/04_passive_synth_vivado.jou" \
    -tclargs "$RUN/output"

python3 "$ROOT/scripts/m08_d3_2_passive_synth_gate.py" \
    --native-output-dir "$RUN/output" \
    > "$RUN/30_pc_source_and_native_review.json"

(
    cd "$RUN"
    sha256sum \
        01_passive_bd_vivado.log \
        02_passive_bd_vivado.jou \
        03_passive_synth_vivado.log \
        04_passive_synth_vivado.jou \
        output/10_d3a_passive_bd_readback.txt \
        output/11_d3a_passive_bd_export.tcl \
        output/12_d3a_fan_a12.xdc \
        output/20_passive_synth_readback.txt \
        output/21_passive_synth_utilization.rpt \
        output/22_passive_synth_timing.rpt \
        30_pc_source_and_native_review.json \
        > 99_evidence_sha256.txt
    sha256sum -c 99_evidence_sha256.txt
)

printf 'M08_D3_2_PASSIVE_PC_SYNTH_ONLY_RECORDED_NOT_ROUTED_NO_BITSTREAM_NO_BOARD=%s\n' "$RUN"
