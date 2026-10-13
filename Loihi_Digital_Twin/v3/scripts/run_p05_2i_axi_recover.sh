#!/usr/bin/env bash
# P05.2i passive RECOVERY after the first XSDB MMIO memory-map rejection.
# DOES NOT reboot, stop, reset, start, download, program or write PL/DDR.
# Reuses the already-complete P05.2h physical A53 P05R + all 5 DDR files.
# Rebooting since the aborted counter capture destroys PL counter evidence;
# in that case this MUST fail and the original workload must be rerun on
# a FRESH directory, never copy/forge the counters.
set -euo pipefail
[[ $# -eq 1 ]] || {
  echo "Usage: $0 /absolute/existing-P05.2i-evidence-directory" >&2;exit 2;
}
OUT="$1"
[[ "$OUT" == /* ]] || {
  echo "ERROR: absolute existing evidence directory required" >&2;exit 2;
}
V3="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$V3"
[[ "${P05_2I_CONFIRM_READONLY_RECOVERY:-}" == YES ]] || {
  echo "ERROR: P05_2I_CONFIRM_READONLY_RECOVERY=YES required" >&2;exit 2;
}
for cmd in xsdb python grep sha256sum;do
    command -v "$cmd" >/dev/null || { echo "ERROR: missing $cmd" >&2;exit 2; }
done
python -m py_compile scripts/p05_2i_axi_closeout.py scripts/p05_2h_barrier_verify.py
for item in \
  p05_a53_result.bin \
  p05_2i_counter_expectations.json \
  p05_2i_preflight_identity.txt \
  p05_2h_barrier_gate.json \
  p05_artifacts/p05_header.bin \
  p05_artifacts/p05_payload.bin \
  verify.log; do
    [[ -s "$OUT/$item" ]] || {
      echo "ERROR: original P05.2i/P05.2h physical evidence absent: $item" >&2;exit 2;
    }
done
grep -Fxq 'P05_2H_VERIFY_EXIT=0' "$OUT/verify.log" || {
  echo "ERROR: original P05.2h physical execution NOT independently accepted" >&2;exit 2;
}
[[ ! -e "$OUT/p05_2i_verify.log" ]] || {
  echo "ERROR: P05.2i verification result already exists; no overwrite" >&2;exit 2;
}
[[ ! -e "$OUT/p05_2i_axi_capture_retry.log" ]] || {
  echo "ERROR: previous recovery capture log exists, no silent retry" >&2;exit 2;
}
for core in 0 1 2 3 4; do
  [[ -s "$OUT/final_ddr/core${core}_after.bin" ]] || {
    echo "ERROR: missing physical DDR core$core" >&2;exit 2;
  }
done
PYTHONPATH="$V3/src:$V3/scripts" python - "$OUT" <<'PY'
import hashlib,json,struct,sys
from pathlib import Path
from p05_2i_axi_closeout import calculation
root=Path(sys.argv[1])
for line in (root/"p05_2i_preflight_identity.txt").read_text().splitlines():
    values=line.split()
    if len(values)==2 and len(values[0])==64:
        p=Path(values[1])
        if hashlib.sha256(p.read_bytes()).hexdigest()!=values[0]:
            raise SystemExit("FAIL: original physical evidence preflight SHA drift: "+str(p))
if json.loads((root/"p05_2i_counter_expectations.json").read_text())!=calculation(root):
    raise SystemExit("FAIL: model-derived PL AXI counter reference changed")
mailbox=dict(zip(
    __import__("p05_1_verify").FIELDS,
    struct.unpack("<64I",(root/"p05_a53_result.bin").read_bytes())
))
if (mailbox["result"],mailbox["hw_dispatches"],mailbox["hw_pages"],
    mailbox["hw_pending_bytes"])!=(0x600D600D,80,160,0):
    raise SystemExit("FAIL: original A53 terminal not the completed 16-barrier run")
if (mailbox["hw_read_bursts"],mailbox["hw_write_bursts"])!=(136960,33280):
    raise SystemExit("FAIL: original A53 P05R counters not physically complete")
print("PASS: original P05.2i A53 P05R, immutable workload, and 5 DDR records preserved; no KV260 touched")
PY
echo "P05.2i read-only XSDB PL MMIO counter recovery (NO reboot or bitstream reload)"
echo "NOTE: If KV260 has been rebooted since the original failure, these"
echo "physical counters are gone; read-only snapshot MUST fail, use a fresh full run."
SERVER="${P05_2I_XSDB_SERVER_URL:-tcp:127.0.0.1:3121}"
xsdb vivado/p05_2i_read_axi_counters.tcl "$OUT" "$SERVER" \
  2>&1 | tee "$OUT/p05_2i_axi_capture_retry.log"
grep -Fq 'PASS: P05.2i four live PL AXI page-counter words read-only captured twice and identical' \
 "$OUT/p05_2i_axi_capture_retry.log"
set +e
PYTHONPATH="$V3/src" python scripts/p05_2i_axi_closeout.py \
  verify --directory "$OUT" 2>&1 | tee "$OUT/p05_2i_verify.log"
RESULT=${PIPESTATUS[0]}
set -e
echo "P05_2I_RECOVERY_VERIFY_EXIT=$RESULT"
echo "P05_2I_EVIDENCE_DIR=$OUT"
echo "IMPORTANT: REBOOT KV260 after recovery; DO NOT resume halted Linux."
if [[ "$RESULT" != 0 ]]; then
  echo "FAIL: P05.2i physical AXI counter gate; keep original 5-DDR/P05R evidence" >&2
  exit 5
fi
echo "PASS: P05.2i same-run READ-ONLY AXI counter recovery after debugger memory-map workaround; independent review pending"
