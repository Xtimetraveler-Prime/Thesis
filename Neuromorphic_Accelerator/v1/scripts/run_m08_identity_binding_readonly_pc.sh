#!/usr/bin/env bash
# M08.2b.3 PC-side read-only physical PL + exact UIO kernel-driver binding.
# Captures *original* remote stdout/stderr/exit in a fresh SHA-logged folder.
set -euo pipefail

TARGET="${1:-}"
[[ "$#" -eq 1 && "$TARGET" == ubuntu@10.42.0.135 ]] || {
    echo 'usage: bash scripts/run_m08_identity_binding_readonly_pc.sh ubuntu@10.42.0.135' >&2
    exit 2
}

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BOARD="$HERE/m08_kv260_identity_binding_readonly.sh"
[[ -f "$BOARD" && ! -L "$BOARD" ]] || { echo "STOP missing first-party board script" >&2; exit 2; }

BASE="${M08_EVIDENCE_BASE:-$HOME/Thesis_Evidence/M08}"
[[ -d "$BASE" && ! -L "$BASE" ]] || { echo "STOP owner evidence base missing" >&2; exit 2; }
OUT="$(mktemp -d "$BASE/m08_2b_identity_binding_READONLY_XXXXXXXX")"
cp -- "$BOARD" "$OUT/00_board_probe_source.sh"
printf 'ssh_target=%s\nsource_head=%s\n' "$TARGET" \
    "$(git -C "$HERE/.." rev-parse HEAD)" > "$OUT/00_context.txt"

set +e
ssh -T -o ConnectTimeout=12 -o StrictHostKeyChecking=ask "$TARGET" 'bash -s' \
    < "$OUT/00_board_probe_source.sh" \
    > "$OUT/01_original_stdout.log" 2> "$OUT/02_original_stderr.log"
RC=$?
set -e

printf 'exit_status=%s\n' "$RC" > "$OUT/03_ssh_exit.txt"
(
  cd "$OUT"
  sha256sum -- 00_board_probe_source.sh 00_context.txt \
    01_original_stdout.log 02_original_stderr.log 03_ssh_exit.txt \
    > 99_evidence_sha256.txt
)
echo "M08_IDENTITY_BINDING_EVIDENCE_DIR=$OUT"

if [[ "$RC" -ne 0 ]] ||
   ! grep -Fxq 'M08_IDENTITY_BINDING_PREFLIGHT_BEGIN_READ_ONLY' "$OUT/01_original_stdout.log" ||
   ! grep -Fxq 'M08_IDENTITY_BINDING_PREFLIGHT_PASS_NO_MMIO' "$OUT/01_original_stdout.log" ||
   [[ "$(grep -c '^M08_VERIFIED_BINDING|' "$OUT/01_original_stdout.log")" -ne 2 ]]; then
    echo "M08_IDENTITY_BINDING_PREFLIGHT_FAILED_PRESERVE_ORIGINAL_EVIDENCE" >&2
    exit 3
fi
echo M08_IDENTITY_BINDING_METADATA_CAPTURE_PASS_NOT_MMIO_APPROVAL
