#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
CHECKOUT="${1:-$PROJECT_DIR/build/m13_1/catalyst-n1}"
OUT_DIR="${2:-$PROJECT_DIR/build/m13_1/catalyst-rtl-regression}"
PIN="1806bb4b4114d7671e5648fa75b7b83b3a8d5543"
TB_TIMEOUT_SECONDS="${M13_1_TB_TIMEOUT_SECONDS:-300}"

for tool in git python3 iverilog vvp timeout; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "ERROR: required tool is not on PATH: $tool" >&2
        exit 2
    fi
done

if [[ ! "$TB_TIMEOUT_SECONDS" =~ ^[1-9][0-9]*$ ]]; then
    echo "ERROR: M13_1_TB_TIMEOUT_SECONDS must be a positive integer; found: $TB_TIMEOUT_SECONDS" >&2
    exit 2
fi

# Do not pipe `iverilog -V` through `head` while `pipefail` is enabled.
# Some Icarus builds receive SIGPIPE when the consumer exits after one line,
# which made the runner terminate silently before emitting any diagnostics.
version_text="$(iverilog -V 2>&1)"
version_first_line="${version_text%%$'\n'*}"
version_major="$(sed -nE 's/.*version ([0-9]+).*/\1/p' <<< "$version_first_line")"
if [[ -z "$version_major" || "$version_major" -lt 12 ]]; then
    echo "ERROR: Catalyst N1 v2.3-paper documents Icarus Verilog v12+; found: $version_first_line" >&2
    exit 2
fi

echo "M13.1 Catalyst RTL runner: $version_first_line"
echo "M13.1 Catalyst RTL per-testbench timeout: ${TB_TIMEOUT_SECONDS}s (override with M13_1_TB_TIMEOUT_SECONDS)"

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$PROJECT_DIR/examples/validate_m13_1_reference_manifest.py" \
    --catalyst-checkout "$CHECKOUT"

if [[ "$(git -C "$CHECKOUT" rev-parse HEAD)" != "$PIN" ]]; then
    echo "ERROR: Catalyst checkout moved away from M13.1 pin." >&2
    exit 3
fi

REGRESSION="$CHECKOUT/run_regression.sh"
rtl_line="$(grep -m1 '^RTL="' "$REGRESSION")"
tb_line="$(grep -m1 '^for tb in .*; do$' "$REGRESSION")"
if [[ -z "$rtl_line" || -z "$tb_line" ]]; then
    echo "ERROR: could not parse native RTL/testbench lists from pinned run_regression.sh" >&2
    exit 3
fi
rtl_list="${rtl_line#RTL=\"}"
rtl_list="${rtl_list%\"}"
tb_list="${tb_line#for tb in }"
tb_list="${tb_list%; do}"
read -r -a rtl_files <<< "$rtl_list"
read -r -a testbenches <<< "$tb_list"

if [[ "${#testbenches[@]}" -ne 25 ]]; then
    echo "ERROR: expected 25 native Catalyst regression testbenches; found ${#testbenches[@]}" >&2
    exit 3
fi

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR/cases"
summary="$OUT_DIR/summary.tsv"
printf 'index\ttestbench\tcompile\trun\tresult_marker\n' > "$summary"

pushd "$CHECKOUT" >/dev/null
passed=0
for i in "${!testbenches[@]}"; do
    tb="${testbenches[$i]}"
    tb_mod="$(basename "$tb" .v)"
    case_id="$(printf '%02d' "$((i + 1))")"
    vvp_out="$OUT_DIR/cases/${case_id}-${tb_mod}.vvp"
    log="$OUT_DIR/cases/${case_id}-${tb_mod}.log"

    echo "=== M13.1 Catalyst native regression $((i + 1))/25: $tb ==="
    if ! iverilog -g2012 -DSIMULATION -s "$tb_mod" -o "$vvp_out" "${rtl_files[@]}" "$tb" >"$log.compile" 2>&1; then
        cat "$log.compile" >&2
        printf '%s\t%s\tFAIL\tSKIP\t0\n' "$case_id" "$tb" >> "$summary"
        echo "ERROR: Catalyst compile failure: $tb" >&2
        exit 4
    fi

    set +e
    timeout "$TB_TIMEOUT_SECONDS" vvp "$vvp_out" >"$log" 2>&1
    rc=$?
    set -e
    cat "$log"
    if [[ "$rc" -eq 124 ]]; then
        printf '%s\t%s\tPASS\tTIMEOUT(%ss)\t0\n' "$case_id" "$tb" "$TB_TIMEOUT_SECONDS" >> "$summary"
        echo "ERROR: Catalyst testbench exceeded ${TB_TIMEOUT_SECONDS}s timeout: $tb" >&2
        echo "       Retry with a larger value, e.g. M13_1_TB_TIMEOUT_SECONDS=600 bash scripts/run_m13_1_catalyst_rtl_regression.sh" >&2
        exit 4
    fi
    if [[ "$rc" -ne 0 ]]; then
        printf '%s\t%s\tPASS\tFAIL(%s)\t0\n' "$case_id" "$tb" "$rc" >> "$summary"
        echo "ERROR: Catalyst testbench returned nonzero: $tb rc=$rc" >&2
        exit 4
    fi

    # Catalyst testbenches commonly print summaries such as "6 PASSED, 0 FAILED".
    # Preserve those as success while still rejecting any other explicit failure line.
    failure_lines="$(
        grep -Ei 'FAILED|FAILURE|COMPILE ERROR' "$log" \
            | grep -Eiv '(^|[^0-9])0[[:space:]]+FAILED([^A-Z]|$)|ALL TESTS PASSED' \
            || true
    )"
    if [[ -n "$failure_lines" ]]; then
        printf '%s\n' "$failure_lines" >&2
        printf '%s\t%s\tPASS\tFAIL(marker)\t0\n' "$case_id" "$tb" >> "$summary"
        echo "ERROR: Catalyst testbench emitted a failure marker: $tb" >&2
        exit 4
    fi
    if ! grep -Eiq 'PASSED|passed|RESULTS' "$log"; then
        printf '%s\t%s\tPASS\tPASS\t0\n' "$case_id" "$tb" >> "$summary"
        echo "ERROR: Catalyst testbench produced no native result marker: $tb" >&2
        exit 4
    fi
    printf '%s\t%s\tPASS\tPASS\t1\n' "$case_id" "$tb" >> "$summary"
    passed=$((passed + 1))
done
popd >/dev/null

if [[ "$passed" -ne 25 ]]; then
    echo "ERROR: native Catalyst regression incomplete: passed=$passed/25" >&2
    exit 5
fi

echo "M13.1 Catalyst native RTL regression PASS: commit=$PIN iverilog_major=$version_major cases=$passed/25"
echo "M13.1 Catalyst regression summary: $summary"
