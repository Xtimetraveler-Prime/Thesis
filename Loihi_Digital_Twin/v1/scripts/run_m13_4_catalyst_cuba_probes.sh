#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
CHECKOUT="${1:-$PROJECT_DIR/build/m13_1/catalyst-n1}"
OUT_DIR="${2:-$PROJECT_DIR/build/m13_4/catalyst-rtl}"
PIN="1806bb4b4114d7671e5648fa75b7b83b3a8d5543"
TB="$PROJECT_DIR/rtl/m13_4/tb_m13_4_catalyst_cuba.sv"

for tool in git python3 iverilog vvp; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "ERROR: required tool is not on PATH: $tool" >&2
        exit 2
    fi
done

version_text="$(iverilog -V 2>&1)"
version_first_line="${version_text%%$'\n'*}"
version_major="$(sed -nE 's/.*version ([0-9]+).*/\1/p' <<< "$version_first_line")"
if [[ -z "$version_major" || "$version_major" -lt 12 ]]; then
    echo "ERROR: Catalyst N1 v2.3-paper documents Icarus Verilog v12+; found: $version_first_line" >&2
    exit 2
fi

if [[ ! -d "$CHECKOUT/.git" ]]; then
    echo "ERROR: pinned Catalyst checkout not found: $CHECKOUT" >&2
    echo "       Run scripts/fetch_m13_1_catalyst.sh first." >&2
    exit 3
fi

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$PROJECT_DIR/examples/validate_m13_1_reference_manifest.py" \
    --catalyst-checkout "$CHECKOUT"

if [[ "$(git -C "$CHECKOUT" rev-parse HEAD)" != "$PIN" ]]; then
    echo "ERROR: Catalyst checkout moved away from M13.1 pin." >&2
    exit 3
fi
if [[ -n "$(git -C "$CHECKOUT" status --porcelain)" ]]; then
    echo "ERROR: Catalyst checkout is dirty; M13.4 will not run against modified reference RTL." >&2
    exit 3
fi

REGRESSION="$CHECKOUT/run_regression.sh"
rtl_line="$(grep -m1 '^RTL="' "$REGRESSION")"
if [[ -z "$rtl_line" ]]; then
    echo "ERROR: could not parse native RTL list from pinned Catalyst run_regression.sh" >&2
    exit 3
fi
rtl_list="${rtl_line#RTL=\"}"
rtl_list="${rtl_list%\"}"
read -r -a rtl_files <<< "$rtl_list"

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"
vvp_out="$OUT_DIR/m13_4_catalyst_cuba.vvp"
compile_log="$OUT_DIR/compile.log"
run_log="$OUT_DIR/native.log"

pushd "$CHECKOUT" >/dev/null
if ! iverilog -g2012 -DSIMULATION -s tb_m13_4_catalyst_cuba \
    -o "$vvp_out" "${rtl_files[@]}" "$TB" >"$compile_log" 2>&1; then
    cat "$compile_log" >&2
    echo "ERROR: M13.4 Catalyst CUBA probe compile failed." >&2
    exit 4
fi
set +e
vvp "$vvp_out" >"$run_log" 2>&1
rc=$?
set -e
popd >/dev/null
cat "$run_log"
if [[ "$rc" -ne 0 ]]; then
    echo "ERROR: M13.4 Catalyst CUBA probe returned rc=$rc" >&2
    exit 4
fi
if grep -q 'M13_4_CUBA_TIMEOUT' "$run_log"; then
    echo "ERROR: M13.4 Catalyst CUBA probe timed out." >&2
    exit 4
fi
if ! grep -q '^M13_4_CUBA_DONE$' "$run_log"; then
    echo "ERROR: M13.4 Catalyst CUBA completion marker missing." >&2
    exit 4
fi
positive_count="$(grep -c '^M13_4_CUBA|case=positive|' "$run_log")"
negative_count="$(grep -c '^M13_4_CUBA|case=negative|' "$run_log")"
if [[ "$positive_count" -ne 5 || "$negative_count" -ne 4 ]]; then
    echo "ERROR: unexpected M13.4 Catalyst CUBA trace lengths: positive=$positive_count negative=$negative_count" >&2
    exit 4
fi

echo "M13.4 Catalyst CUBA native probe PASS: commit=$PIN iverilog_major=$version_major positive_ticks=$positive_count negative_ticks=$negative_count"
echo "M13.4 Catalyst CUBA native log: $run_log"
