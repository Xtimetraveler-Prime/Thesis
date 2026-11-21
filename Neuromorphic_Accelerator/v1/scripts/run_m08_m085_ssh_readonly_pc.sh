#!/usr/bin/env bash
# OWNER PC: one SSH-only M08.5 KV260 READ-ONLY observation.
# No remote files created. Immutable fresh evidence is stored on PC.
# Fail closed on changed SSH host key, unavailable auth, wrong board, timeout,
# incomplete markers or nonzero remote exit. NOT DMA ownership attestation.
set -euo pipefail
TARGET="${1:-}"
if [[ "$#" -ne 1 || "$TARGET" != "ubuntu@10.42.0.135" ]]; then
    echo "Usage: bash scripts/run_m08_m085_ssh_readonly_pc.sh ubuntu@10.42.0.135" >&2
    echo "Historical target only; review repository provenance before changing." >&2
    exit 2
fi
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BOARD="$HERE/m08_m085_ssh_linux_probe.sh"
[[ -f "$BOARD" && ! -L "$BOARD" ]] || {
    echo "STOP: missing or symlinked first-party source" >&2; exit 2;
}
bash -n "$BOARD"
command -v ssh >/dev/null && command -v timeout >/dev/null && command -v sha256sum >/dev/null || {
    echo "STOP: SSH/timeout/sha256sum not installed on PC" >&2; exit 2;
}
BASE="${M08_EVIDENCE_BASE:-$HOME/Thesis_Evidence/M08}"
[[ -d "$BASE" && ! -L "$BASE" ]] || {
    echo "STOP: existing nonsymlink PC evidence parent required: $BASE" >&2; exit 2;
}
OUT="$(mktemp -d "$BASE/m08_m085_ssh_readonly_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXXXX")"
chmod 700 "$OUT"
cp -- "$BOARD" "$OUT/00_remote_source.sh"
printf 'source_commit=%s\ntarget=%s\nscope=SSH_READ_ONLY_NO_DMA_READY\n' \
    "$(git -C "$HERE/.." rev-parse HEAD 2>/dev/null || echo UNKNOWN)" \
    "$TARGET" > "$OUT/01_context.txt"
set +e
timeout --signal=TERM --kill-after=3s 75s ssh -T \
    -o BatchMode=yes \
    -o StrictHostKeyChecking=yes \
    -o ConnectTimeout=12 \
    -o ServerAliveInterval=5 \
    -o ServerAliveCountMax=2 \
    "$TARGET" 'bash -s' \
    < "$OUT/00_remote_source.sh" \
    > "$OUT/02_original_stdout.log" \
    2> "$OUT/03_original_stderr.log"
RC=$?
set -e
printf 'ssh_exit_status=%d\n' "$RC" > "$OUT/04_ssh_exit_status.txt"
(
    cd "$OUT"
    sha256sum -- 00_remote_source.sh 01_context.txt 02_original_stdout.log \
        03_original_stderr.log 04_ssh_exit_status.txt > 99_evidence_sha256.txt
)
printf 'M08_5_SSH_READONLY_EVIDENCE_DIR=%s\n' "$OUT"
if (( RC != 0 )) ||
   [[ "$(head -n1 "$OUT/02_original_stdout.log")" != M08_5_SSH_READONLY_BEGIN ]] ||
   [[ "$(tail -n1 "$OUT/02_original_stdout.log")" != M08_5_SSH_READONLY_END_NO_DMA_OR_BOARD_CHANGES ]] ||
   ! grep -Eq '^BOARD_MODEL=.*KV260' "$OUT/02_original_stdout.log"; then
    echo "M08_5_SSH_READONLY_INCOMPLETE_NOT_DMA_READY; original log preserved" >&2
    exit 3
fi
echo 'M08_5_SSH_READONLY_CAPTURE_PASS_NOT_DMA_READY'
echo "PC audit: ( cd '$OUT' && sha256sum -c 99_evidence_sha256.txt )"
