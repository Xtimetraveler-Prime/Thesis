#!/usr/bin/env bash
# P07-B.4e manual real-toolchain build LAUNCHER, not automatically executed.
# User invokes only after independently reviewing accepted P03.2c XSA+BIT
# digests and proving the build location outside Thesis. No board access.
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V3="$(cd -- "$HERE/.." && pwd)"
REPORTS="${P07_B4E_ACCEPTED_REPORTS:?Set absolute accepted P03.2c routed report dir}"
XSA_PIN="${P07_B4E_ACCEPTED_XSA_SHA256:?Set independently accepted XSA sha256}"
BIT_PIN="${P07_B4E_ACCEPTED_BIT_SHA256:?Set independently accepted BIT sha256}"
OUT="${P07_B4E_PREFLIGHT_DIR:?Set a NEW absolute out-of-repository preflight folder}"
BUILD="${P07_B4C_BUILD_DIR:?Set a NEW absolute out-of-repository Vitis build directory}"

fail(){ printf 'P07_B4E_BUILD_BLOCKED: %s\n' "$*" >&2; exit 3; }
[[ "$REPORTS" = /* && "$OUT" = /* && "$BUILD" = /* ]] ||
  fail "absolute report/preflight/build paths required"
[[ "$OUT" != "$BUILD" ]] || fail "preflight evidence and Vitis build must differ"
[[ ! -e "$OUT" && ! -L "$OUT" ]] || fail "preflight directory must be new"
[[ ! -e "$BUILD" && ! -L "$BUILD" ]] || fail "Vitis build directory must be new"
command -v python3 >/dev/null || fail "Python 3 missing"
# All integrity/structure/toolchain checks take place before writing any files.
python3 "$V3/scripts/p07_b4e_vitis_inputs.py" \
  --reports "$REPORTS" \
  --xsa-sha256 "$XSA_PIN" \
  --bit-sha256 "$BIT_PIN" \
  --build-dir "$BUILD" \
  --require-tools >/dev/null || fail "real hardware/Vitis input preflight failed"
mkdir -m 700 -- "$OUT"
python3 "$V3/scripts/p07_b4e_vitis_inputs.py" \
  --reports "$REPORTS" \
  --xsa-sha256 "$XSA_PIN" \
  --bit-sha256 "$BIT_PIN" \
  --build-dir "$BUILD" \
  --require-tools \
  --json-out "$OUT/p07_b4e_inputs.json" \
  | tee "$OUT/preflight.log"
test -s "$OUT/p07_b4e_inputs.json" || fail "preflight identity file missing"
export P07_B4C_XSA="$REPORTS/p03_2_ps_mmio.xsa"
export P07_B4C_XSA_SHA256="$XSA_PIN"
export P07_B4C_ROUTE_METRICS="$REPORTS/p03_2_post_route_metrics.txt"
# Actual Vitis build is performed only when a user manually calls this script.
# Existing B4c script refuses overwriting the requested output and never
# invokes xsdb, vivado, JTAG, PL programming, Linux stop or board operations.
bash "$V3/scripts/build_p07_b4c.sh" 2>&1 | tee "$OUT/real_vitis_build.log"
printf 'P07_B4E_REAL_VITIS_BUILD_COMMAND_COMPLETED=1\n'
printf 'P07_B4E_BOARD_PROBE=NOT_RUN\n'
printf 'P07_B4E_INFERENCE_AUTHORIZED=0\n'
