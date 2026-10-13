#!/usr/bin/env bash
# P05.2i FINAL physical phase-5 counter-provenance regression.
# Keep P05.2h original A53/PL/banking workload EXACTLY; add two read-only
# MMIO samples of FPGA's successful AXI transfers AFTER A53 terminal.
# IMPORTANT: This HALTS Linux, OVERWRITES reserved project DDR. Reboot
# KV260 before & after on ANY result. Never overwrite prior physical evidence.
set -euo pipefail
[[ $# -eq 2 ]] || {
  echo "Usage: $0 {prepare|physical} /absolute/NEW-evidence-directory" >&2
  exit 2
}
MODE="$1";OUT="$2"
[[ "$MODE" == prepare || "$MODE" == physical ]] || {
  echo "ERROR: use prepare or physical" >&2;exit 2;
}
[[ "$OUT" == /* ]] || {
  echo "ERROR: P05.2i requires an absolute fresh evidence directory" >&2;exit 2;
}
V3="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$V3"
python -m py_compile \
  scripts/p05_2i_axi_closeout.py \
  scripts/p05_2h_barrier_fixture.py \
  scripts/p05_2h_barrier_verify.py \
  tests/test_p05_2i_axi_closeout.py
if [[ "$MODE" == prepare ]]; then
  [[ ! -e "$OUT" ]] || {
    echo "ERROR: fresh evidence required, no overwrite" >&2;exit 2;
  }
  bash scripts/run_p05_2h_barrier.sh prepare "$OUT"
  PYTHONPATH="$V3/src" python scripts/p05_2i_axi_closeout.py \
    prepare --directory "$OUT"
  {
    echo "status=MODEL_ONLY; no KV260 traffic has occurred"
    echo "P05.2i uses the unchanged P05.2h single 16-barrier workload"
    sha256sum "$OUT/p05_2i_counter_expectations.json"
    sha256sum "$OUT/p05_2h_barrier_gate.json"
    sha256sum "$OUT/p05_artifacts/p05_header.bin"
    sha256sum "$OUT/p05_artifacts/p05_payload.bin"
    for core in 0 1 2 3 4; do
      sha256sum "$OUT/barrier_physical_golden/core${core}_expected.bin"
    done
  } | tee "$OUT/p05_2i_preflight_identity.txt"
  echo "P05_2I_EVIDENCE_DIR=$OUT"
  echo "PASS: P05.2i final page AXI counter provenance staged OFFLINE; KV260 NOT TOUCHED"
  exit 0
fi

[[ "${P05_2I_CONFIRM_KV260_DDR_OVERWRITE:-}" == YES ]] || {
  echo "ERROR: reboot KV260, explicitly set P05_2I_CONFIRM_KV260_DDR_OVERWRITE=YES" >&2;exit 2;
}
[[ -s "$OUT/p05_2i_preflight_identity.txt" && -s "$OUT/preflight_identity.txt" ]] || {
  echo "ERROR: P05.2i original+counter evidence must first be PREPARED" >&2;exit 2;
}
[[ ! -e "$OUT/p05_a53_result.bin" && ! -e "$OUT/p05_2i_axi_witness.bin" &&
    ! -e "$OUT/p05_2i_verify.log" ]] || {
  echo "ERROR: physical evidence already exists; NEVER reuse path" >&2;exit 2;
}
# Before touching hardware, validate the independent frozen AXI byte ledger.
PYTHONPATH="$V3/src" python - "$OUT" <<'PY'
import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1])
for line in (root/"p05_2i_preflight_identity.txt").read_text().splitlines():
    values=line.split()
    if len(values)==2 and len(values[0])==64:
        source=Path(values[1])
        if hashlib.sha256(source.read_bytes()).hexdigest()!=values[0]:
            raise SystemExit("FAIL: P05.2i SHA provenance changed BEFORE physical JTAG: "+str(source))
from p05_2i_axi_closeout import calculation
frozen=json.loads((root/"p05_2i_counter_expectations.json").read_text())
if calculation(root)!=frozen:
    raise SystemExit("FAIL: P05.2i page-AXI counter reference drift")
print("PASS: P05.2i source/burst geometry/golden SHA physical-admission preflight")
PY
XSDB_URL="${P05_2I_XSDB_SERVER_URL:-tcp:127.0.0.1:3121}"
echo "P05.2i PHYSICAL: reboot KV260 FIRST, accepted 128-bit PL shell and P05 ELF."
echo "This HALTS Linux, OVERWRITES project DDR 0x40000000..0x43FFFFFF."
echo "DO NOT resume Linux after this; reboot KV260 when completed OR on failure."
# Reuse full accepted original P05.2h physical runner: XSA SHA,
# accepted ELF C-source identities, FPD width, immutable input
# provisioning, bitstream programming, 80 A53 HLS dispatches,
# 318 checkpoints and all FIVE byte-exact DDR dumps are reverified.
P05_2H_CONFIRM_KV260_DDR_OVERWRITE=YES \
P05_2H_RUN_MAX_SECONDS="${P05_2I_RUN_MAX_SECONDS:-1800}" \
P05_2H_XSDB_SERVER_URL="$XSDB_URL" \
bash scripts/run_p05_2h_barrier.sh physical "$OUT" \
  2>&1 | tee "$OUT/p05_2h_physical_under_2i.log"
grep -Fxq 'P05_2H_VERIFY_EXIT=0' "$OUT/verify.log"
# The A53 remains halted at successful P05R; PL counter state is
# still present. The new Tcl uses no MMIO writes, no resets and
# independently reads the four PL counter words TWICE.
xsdb vivado/p05_2i_read_axi_counters.tcl "$OUT" "$XSDB_URL" \
  2>&1 | tee "$OUT/p05_2i_axi_capture.log"
grep -Fq 'PASS: P05.2i four live PL AXI page-counter words read-only captured twice and identical' \
  "$OUT/p05_2i_axi_capture.log"
set +e
PYTHONPATH="$V3/src" python scripts/p05_2i_axi_closeout.py \
  verify --directory "$OUT" 2>&1 | tee "$OUT/p05_2i_verify.log"
EXIT=${PIPESTATUS[0]}
set -e
echo "P05_2I_VERIFY_EXIT=$EXIT"
echo "P05_2I_EVIDENCE_DIR=$OUT"
echo "IMPORTANT: reboot KV260 immediately, even if verification failed; do NOT resume Linux"
if [[ "$EXIT" != 0 ]]; then
  echo "FAIL: P05.2i final page AXI burst/byte proof; preserve physical evidence"
  exit 5
fi
echo "PASS: P05.2i candidate FINAL physical phase-5 counter provenance (await independent user acceptance)"
