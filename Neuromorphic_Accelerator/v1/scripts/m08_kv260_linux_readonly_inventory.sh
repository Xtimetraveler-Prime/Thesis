#!/usr/bin/env bash
# M08.2b on-BOARD KV260 Linux inventory. Run on actual KV260 serial/SSH
# shell, NOT PC. Never loads/unloads a PL app, writes hardware registers,
# programs FPGA, updates firmware, or accesses raw MMIO/DDR.
set -euo pipefail
BASE="${1:-$HOME/M08_Physical_Evidence}"
if [[ ! -d "$BASE" || -L "$BASE" ]]; then
  echo "ERROR: create a trusted board-local evidence parent first: $BASE" >&2
  exit 2
fi
DIR="$(mktemp -d "$BASE/m08_kv260_linux_readonly_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXX")"
echo "M08_BOARD_READONLY_EVIDENCE_DIR=$DIR"

capture() {
  local label="$1"; shift
  local out="$DIR/$label.txt"
  set +e
  "$@" >"$out" 2>&1
  local rc=$?
  set -e
  printf '%s exit=%d\n' "$label" "$rc" >>"$DIR/00_command_status.txt"
}
capture uname uname -a
capture os_release cat /etc/os-release
capture kernel_cmdline cat /proc/cmdline
if [[ -r /proc/device-tree/model ]]; then
  capture board_model sh -c 'tr "\000" "\n" </proc/device-tree/model'
else
  printf 'board_model unavailable\n' >"$DIR/board_model.txt"
  printf 'board_model exit=1\n' >>"$DIR/00_command_status.txt"
fi
capture fpga_manager_state sh -c '
  for d in /sys/class/fpga_manager/*; do
      [ -d "$d" ] || continue
      echo "FPGA_MANAGER=$d"
      if [ -r "$d/state" ]; then cat "$d/state"; fi
  done
'
capture fpga_overlays sh -c '
  base=/sys/kernel/config/device-tree/overlays
  if [ -d "$base" ]; then
    find "$base" -mindepth 1 -maxdepth 2 -type d -print
  else
    echo "No device tree overlay configfs at $base"
  fi
'
if command -v xmutil >/dev/null 2>&1; then
  capture installed_apps xmutil listapps
else
  printf 'xmutil unavailable; DO NOT infer no active PL app\n' >"$DIR/installed_apps.txt"
  printf 'installed_apps exit=127\n' >>"$DIR/00_command_status.txt"
fi
capture dfx_fan_services sh -c '
  if command -v systemctl >/dev/null 2>&1; then
    systemctl --no-pager --full is-active dfx-mgrd fancontrol 2>&1 || :
  fi
  for f in /sys/class/hwmon/hwmon*/fan*_input; do
    [ -r "$f" ] || continue
    printf "%s " "$f"
    cat "$f"
  done
'
capture iomem cat /proc/iomem
capture loaded_modules sh -c '
  if [ -r /proc/modules ]; then
    grep -Ei "fpga|xilinx|zocl|uio" /proc/modules || :
  fi
'
(
  cd "$DIR"
  sha256sum -- *.txt >sha256_evidence.txt
)
echo "M08_BOARD_LINUX_READ_ONLY_INVENTORY_CAPTURED_NO_MMIO_NO_FPGA_CHANGES"
echo "M08_BOARD_READONLY_EVIDENCE_DIR=$DIR"
