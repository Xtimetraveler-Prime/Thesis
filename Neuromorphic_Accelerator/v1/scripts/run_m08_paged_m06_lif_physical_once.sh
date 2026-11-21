#!/usr/bin/env bash
# M08.4 STAGED physical one-shot ONLY, currently BLOCKED pending exact NEW
# owner-original DRC/timing/clock/source/image SHA release gate.
# A source CI PASS and 15/15 SHA alone NEVER authorize a JTAG program.
# No flash, Linux MMIO, PS DDR/DMA, auto retries or original-owner overwrite.
set -euo pipefail
if [[ "$#" -ne 1 ]]; then
    echo 'usage: run_m08_paged_m06_lif_physical_once.sh <exact-new-original-native-folder>' >&2
    exit 2
fi
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="$HOME/Thesis_Evidence/M08"
NATIVE="$(realpath -- "$1")"
BIT="$NATIVE/bitstream_candidate/m08_paged_m06_lif_jtag_UNRELEASED.bit"
EXPECTED_SHA="6a4a71f255adcc79a4131401a3f75eb64f253d3431f5ad1babc0da48479f6494"
if [[ "$(id -u)" -eq 0 || ! -d "$BASE" || -L "$BASE" ||
      "$NATIVE" != "$BASE/m08_paged_m06_lif_QFKpXlPW" ||
      ! -d "$NATIVE" || -L "$NATIVE" ]]; then
    echo 'M08_4_PHYSICAL_STOP: original owner native directory/root invalid' >&2
    exit 2
fi
if ! command -v vivado >/dev/null 2>&1 ||
   ! vivado -version | grep -Eq '^[Vv]ivado v2025\.2([[:space:]]|$)'; then
    echo 'M08_4_PHYSICAL_STOP: genuine Vivado 2025.2 needed' >&2
    exit 2
fi
# This read-only triage rechecks all 15 SHA receipts/source files and the
# individually reported ORIGINAL bit SHA, but deliberately NEVER releases.
python3 "$ROOT/scripts/m08_paged_m06_lif_physical_readiness.py" --run-dir "$NATIVE"
# ABSOLUTE HARD BLOCK UNTIL separate first ORIGINAL image-specific reviewer
# validates every new DRC warning/pin, actual setup/hold/clocks and exact bit.
# No gate has been accepted yet; do not create a bypass for this condition.
EXACT_GATE="$ROOT/scripts/m08_paged_m06_lif_exact_native_accept.py"
if [[ ! -f "$EXACT_GATE" || -L "$EXACT_GATE" ]]; then
    echo 'M08_4_PHYSICAL_BLOCKED: new image-specific native release gate NOT YET APPROVED' >&2
    exit 2
fi
python3 "$EXACT_GATE" --run-dir "$NATIVE"
if [[ ! -f "$BIT" || -L "$BIT" ||
      "$(sha256sum -- "$BIT" | awk '{print $1}')" != "$EXPECTED_SHA" ]]; then
    echo 'M08_4_PHYSICAL_STOP: exact owner original image mismatch' >&2
    exit 2
fi
if [[ "${M08_4_PROGRAM_ONCE:-}" != YES ||
      "${M08_4_PREFLIGHT_CONFIRMED:-}" != YES ]]; then
    echo 'M08_4_PHYSICAL_STOP: confirm active independent cooling, UART capture, stock recovery, exclusive JTAG, one-shot consent' >&2
    exit 2
fi
# All gate/safety checks precede creation of a new physical evidence folder
# and ANY attempt to open Hardware Manager. One fresh run; no auto retry.
HW="$(mktemp -d "$BASE/m08_paged_m06_lif_HW_XXXXXXXX")"
echo "M08_4_NEW_ORIGINAL_PHYSICAL_EVIDENCE=$HW"
python3 "$ROOT/scripts/m08_paged_m06_lif_physical_vectors.py" --out-dir "$HW"
cp -- "$ROOT/scripts/m08_paged_m06_lif_physical_once.tcl" "$HW/00_executed_source.tcl"
export M08_4_BIT="$BIT"
export M08_4_NATIVE="$NATIVE"
export M08_4_HW="$HW"
export M08_4_EXPECTED_SHA="$EXPECTED_SHA"
export M08_4_IMAGE_RELEASE=YES
set +e
timeout --signal=TERM --kill-after=15s 3600s \
    vivado -mode batch -source "$HW/00_executed_source.tcl" \
    -log "$HW/01_jtag_paged_m06.log" -journal "$HW/02_jtag_paged_m06.jou"
RC=$?
set -e
printf 'vivado_physical_exit=%s\n' "$RC" >"$HW/03_exit.txt"
(
    cd "$HW"
    FILES=(00_executed_source.tcl 01_jtag_paged_m06.log 02_jtag_paged_m06.jou
           03_exit.txt 10_edge_config_input.hex
           11_neural_page_0_input.hex 11_neural_page_1_input.hex
           11_neural_page_2_input.hex 11_neural_page_3_input.hex
           11_neural_page_4_input.hex 11_neural_page_5_input.hex
           20_independent_512_oracle_ONLY.hex 80_physical_paged_neural_parity.txt)
    # Preserve SHA of every actually created ORIGINAL file, including failed
    # attempts; do not forge a passing 13-row receipt after a hardware fault.
    : >99_evidence_sha256.txt
    for f in "${FILES[@]}"; do
        if [[ -s "$f" && ! -L "$f" ]]; then
            sha256sum "$f" >>99_evidence_sha256.txt
        fi
    done
    if [[ "$RC" -ne 0 || ! -s 80_physical_paged_neural_parity.txt ||
          "$(wc -l <99_evidence_sha256.txt)" -ne 13 ]]; then
        echo "M08_4_PHYSICAL_STOP_NO_AUTO_RETRY_PRESERVE_ORIGINAL=$HW" >&2
        exit 3
    fi
    sha256sum -c 99_evidence_sha256.txt
)
# Independent auditor is read-only and cannot change original JTAG receipts.
python3 "$ROOT/scripts/m08_paged_m06_lif_physical_audit.py" --native-dir "$NATIVE" --hw-dir "$HW"
echo "M08_4_ORIGINAL_HW_DIR=$HW"
