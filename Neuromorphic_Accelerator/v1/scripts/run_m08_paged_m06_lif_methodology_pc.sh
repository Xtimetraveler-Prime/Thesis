#!/usr/bin/env bash
# FIRST ORIGINAL K26 ROUTED CHECKPOINT METHODOLOGY / CDC INVENTORY (PC ONLY).
# This script never builds/changes a bitstream, opens HW Manager or uses JTAG.
# Original owner K26 project and already-SHA-verified reports are read-only.
set -euo pipefail
if [[ "$#" -ne 1 ]]; then
    echo 'usage: run_m08_paged_m06_lif_methodology_pc.sh <QFKpXlPW original owner native dir>' >&2
    exit 2
fi
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="$HOME/Thesis_Evidence/M08"
NATIVE="$(realpath -- "$1")"
if [[ "$(id -u)" -eq 0 || ! -d "$BASE" || -L "$BASE" ||
      "$NATIVE" != "$BASE/m08_paged_m06_lif_QFKpXlPW" ||
      ! -d "$NATIVE" || -L "$NATIVE" ]]; then
    echo 'M08_4_METHOD_STOP: wrong original owner directory or root user' >&2
    exit 2
fi
if ! command -v vivado >/dev/null 2>&1 ||
   ! vivado -version | grep -Eq '^[Vv]ivado v2025\.2([[:space:]]|$)'; then
    echo 'M08_4_METHOD_STOP: owner genuine Vivado 2025.2 required' >&2
    exit 2
fi
# Independently require unchanged 15 SHA original vendor files, exact bit,
# the source mapping and successful owner offline build before touching DCP.
python3 "$ROOT/scripts/m08_paged_m06_lif_physical_readiness.py" --run-dir "$NATIVE" >/dev/null
mapfile -d '' -t dcp < <(find "$NATIVE/project/m08_paged_m06_lif_jtag.runs/impl_1" \
    -maxdepth 1 -type f -name '*_routed.dcp' -print0)
if [[ "${#dcp[@]}" -ne 1 || -L "${dcp[0]}" || ! -s "${dcp[0]}" ]]; then
    echo 'M08_4_METHOD_STOP: need exactly one original routed implementation DCP; no guessing' >&2
    exit 2
fi
OUT="$(mktemp -d "$BASE/m08_paged_m06_lif_methodology_XXXXXXXX")"
echo "M08_4_NEW_READ_ONLY_METHOD_EVIDENCE_DIR=$OUT"
# Frozen executed Tcl, routed DCP identity and console receipts in NEW
# evidence. Nothing is written to or reopened for modification in NATIVE.
cp -- "$ROOT/scripts/m08_paged_m06_lif_methodology_probe.tcl" "$OUT/00_executed_source.tcl"
sha256sum -- "${dcp[0]}" >"$OUT/03_original_routed_checkpoint_sha256.txt"
set +e
timeout --signal=TERM --kill-after=15s 240s \
    vivado -mode batch -source "$OUT/00_executed_source.tcl" \
    -tclargs "${dcp[0]}" "$OUT" \
    -log "$OUT/01_vivado_methodology.log" -journal "$OUT/02_vivado_methodology.jou"
RC=$?
set -e
printf 'vivado_methodology_exit=%s\n' "$RC" >"$OUT/04_exit.txt"
(
    cd "$OUT"
    : >99_evidence_sha256.txt
    for f in 00_executed_source.tcl 01_vivado_methodology.log \
             02_vivado_methodology.jou 03_original_routed_checkpoint_sha256.txt \
             04_exit.txt 10_new_image_methodology.rpt 11_new_image_cdc.rpt; do
        [[ ! -s "$f" || -L "$f" ]] || sha256sum "$f" >>99_evidence_sha256.txt
    done
)
if [[ "$RC" -ne 0 || ! -s "$OUT/10_new_image_methodology.rpt" ||
      ! -s "$OUT/11_new_image_cdc.rpt" ]]; then
    echo "M08_4_METHOD_STOP_PRESERVE_ORIGINAL=$OUT" >&2
    exit 3
fi
(cd "$OUT" && sha256sum -c 99_evidence_sha256.txt)
echo "M08_4_READ_ONLY_NEW_IMAGE_RESET_METHODOLOGY_AND_CDC_REPORTS_READY=$OUT"
echo 'M08_4_NEW_PAGED_IMAGE_JTAG_HARDWARE_RELEASE=BLOCKED_PENDING_REVIEW'
