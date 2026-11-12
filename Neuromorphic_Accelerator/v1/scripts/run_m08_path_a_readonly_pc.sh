#!/usr/bin/env bash
# M08.2b Path A: PC read-only SSH capture. No on-board files are created.
# Read-only board script runs over stdin; sudo -n will never prompt via SSH.
# This DOES NOT authorize a new FPGA image, overlay, fan change or MMIO.
set -euo pipefail
HERE="$(cd -- "$(dirname -- "$0")" && pwd)"
if [[ "$#" -ne 1 ||
      ! "$1" =~ ^[a-zA-Z_][a-zA-Z0-9._-]*@[a-zA-Z0-9._-]+$ ]]; then
  echo "usage: bash scripts/run_m08_path_a_readonly_pc.sh ubuntu@BOARD_IP_OR_HOSTNAME" >&2
  exit 2
fi
TARGET="$1"
BOARD="$HERE/m08_kv260_path_a_readonly.sh"
if [[ ! -f "$BOARD" || -L "$BOARD" ]]; then
  echo "ERROR: missing or symlinked first-party board script" >&2
  exit 2
fi
BASE="$HOME/Thesis_Evidence/M08"
if [[ -v M08_EVIDENCE_BASE ]]; then BASE="$M08_EVIDENCE_BASE"; fi
if [[ ! -d "$BASE" || -L "$BASE" ]]; then
  echo "ERROR: existing trusted owner evidence parent required: $BASE" >&2
  exit 2
fi
DIR="$(mktemp -d "$BASE/m08_2b_path_a_readonly_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXX")"
printf 'M08_PATH_A_EVIDENCE_DIR=%s\n' "$DIR"
cp -- "$BOARD" "$DIR/00_board_probe_source.sh"
printf 'ssh_target=%s\n' "$TARGET" > "$DIR/00_input.txt"
printf 'source_head=%s\n' "$(git -C "$HERE/.." rev-parse HEAD 2>/dev/null || echo unavailable)" >> "$DIR/00_input.txt"
set +e
ssh -T -o ConnectTimeout=12 -o StrictHostKeyChecking=ask \
  "$TARGET" "bash -s" \
  < "$DIR/00_board_probe_source.sh" \
  > "$DIR/01_board_stdout.log" \
  2> "$DIR/02_ssh_stderr.log"
RC=$?
set -e
printf 'ssh_exit_status=%d\n' "$RC" > "$DIR/03_exit_status.txt"
(
  cd "$DIR"
  sha256sum -- 00_board_probe_source.sh 00_input.txt \
    01_board_stdout.log 02_ssh_stderr.log 03_exit_status.txt \
    > 04_evidence_sha256.txt
)
if (( RC != 0 )) ||
   ! grep -Fxq M08_PATH_A_LINUX_READ_ONLY_BEGIN "$DIR/01_board_stdout.log" ||
   ! grep -Fxq M08_PATH_A_LINUX_READ_ONLY_END_NO_FPGA_CHANGES "$DIR/01_board_stdout.log"; then
  echo "M08_PATH_A_READONLY_CAPTURE_INCOMPLETE preserve=$DIR" >&2
  exit 3
fi
echo "M08_PATH_A_READONLY_CAPTURED_NOT_DEPLOYMENT_APPROVAL"
echo "M08_PATH_A_EVIDENCE_DIR=$DIR"
