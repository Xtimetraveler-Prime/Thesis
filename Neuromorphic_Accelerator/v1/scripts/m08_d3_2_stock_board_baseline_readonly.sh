#!/usr/bin/env bash
# M08 D3.2 STOCK BASELINE on KV260, invoked by guarded OWNER-PC SSH capture.
# READ ONLY. No root, no writes to board, no FPGA manager state changes,
# no probing /dev/mem or /dev/uio, and NO bitstream loading/flash/JTAG.
set -u
printf 'M08_D3_2_STOCK_READONLY_BEGIN\n'
probe() {
    local label="$1"
    shift
    printf 'M08_D3_2_PROBE_BEGIN|%s\n' "$label"
    "$@" 2>&1
    local result=$?
    printf 'M08_D3_2_PROBE_END|%s|rc=%s\n' "$label" "$result"
    return 0
}
probe board_identity sh -c '
  printf "MODEL="; tr "\000" " " </proc/device-tree/model; printf "\n"
  uname -a
  cat /proc/cmdline
  grep "^PRETTY_NAME=" /etc/os-release
'
probe stock_pl_manager sh -c '
  printf "FPGA_STATE="; cat /sys/class/fpga_manager/fpga0/state
  printf "DFX_SERVICE="; systemctl is-active dfx-mgr
  printf "FAN_SERVICE="; systemctl is-active fancontrol
  for path in /etc/dfx-mgrd/default_firmware /etc/dfx-mgrd/daemon.conf; do
    if [ -r "$path" ]; then printf "CONFIG=%s\n" "$path"; cat "$path"; fi
  done
'
probe installed_apps sh -c '
  command -v xmutil >/dev/null 2>&1 || exit 4
  xmutil listapps
'
probe stock_firmware_files sh -c '
  dir=/lib/firmware/xilinx/k26-starter-kits
  test -d "$dir" || { echo "STOCK_FIRMWARE_DIR_MISSING"; exit 5; }
  find "$dir" -maxdepth 1 -type f -print | sort
  for f in "$dir"/*.bit.bin "$dir"/*.dtbo "$dir"/shell.json; do
    if [ -f "$f" ] && [ -r "$f" ]; then sha256sum "$f"; fi
  done
'
probe sensors sh -c '
  for f in /sys/class/hwmon/hwmon*/name /sys/class/hwmon/hwmon*/temp*_input /sys/class/hwmon/hwmon*/fan*_input /sys/class/thermal/thermal_zone*/type /sys/class/thermal/thermal_zone*/temp; do
    if [ -r "$f" ]; then printf "SENSOR=%s=" "$f"; cat "$f"; fi
  done
'
probe overlay_and_uio_names sh -c '
  for d in /sys/kernel/config/device-tree/overlays/*; do
    if [ -d "$d" ]; then printf "ACTIVE_OVERLAY=%s\n" "$d"; fi
  done
  for d in /sys/class/uio/uio*; do
    if [ -r "$d/name" ]; then printf "UIO_NAME=%s=" "$d"; cat "$d/name"; fi
  done
'
printf 'M08_D3_2_STOCK_READONLY_END_NO_PL_OR_KERNEL_CHANGES\n'
