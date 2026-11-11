#!/usr/bin/env bash
# M08.2b Path A: READ ONLY inspection of an already booted K26 Linux system.
# Execute over PC ssh ('bash -s' receives this file) or in a board shell.
# Never unload/reload/flash/configure PL, change fan/PWM, or access raw MMIO.
set -euo pipefail
echo "M08_PATH_A_LINUX_READ_ONLY_BEGIN"
probe() {
  local name="$1"
  shift
  printf 'M08_PROBE_BEGIN|%s\n' "$name"
  local status=0
  "$@" 2>&1 || status=$?
  printf 'M08_PROBE_END|%s|rc=%s\n' "$name" "$status"
}
probe uname uname -a
probe os_release cat /etc/os-release
probe model sh -c '
  if [ -r /proc/device-tree/model ]; then
    tr "\000" "\n" < /proc/device-tree/model
  else
    echo "MODEL_NOT_ACCESSIBLE"
  fi
'
probe cmdline cat /proc/cmdline
probe manager_service sh -c '
  if command -v systemctl >/dev/null 2>&1; then
    systemctl --no-pager is-active dfx-mgr || :
    systemctl --no-pager is-active dfx-mgrd || :
    systemctl --no-pager is-active fancontrol || :
    systemctl --no-pager list-unit-files "dfx-mgr*" "fancontrol*" || :
  else
    echo "systemctl unavailable"
  fi
'
probe fpga_manager sh -c '
  for p in /sys/class/fpga_manager/*; do
    [ -d "$p" ] || continue
    printf "manager=%s\n" "$p"
    if [ -r "$p/state" ]; then cat "$p/state"; fi
  done
'
probe active_overlays sh -c '
  base=/sys/kernel/config/device-tree/overlays
  if [ -d "$base" ]; then
    find "$base" -mindepth 1 -maxdepth 2 -type d -print
  else
    echo "OVERLAY_CONFIGFS_NOT_MOUNTED"
  fi
'
probe firmware_catalog sh -c '
  base=/lib/firmware/xilinx
  if [ -d "$base" ]; then
    find "$base" -mindepth 1 -maxdepth 2 \( -type f -o -type d \) -print
  else
    echo "FIRMWARE_XILINX_NOT_FOUND"
  fi
'
probe firmware_manager_config sh -c '
  for p in /etc/dfx-mgrd/daemon.conf /etc/dfx-mgr/daemon.conf; do
    if [ -r "$p" ]; then
      printf "config=%s\n" "$p"
      cat "$p"
    fi
  done
'
probe device_resources sh -c '
  cat /proc/iomem
  for p in /sys/class/uio/*; do
    [ -d "$p" ] || continue
    printf "uio=%s\n" "$p"
    if [ -r "$p/name" ]; then cat "$p/name"; fi
    for m in "$p"/maps/map*; do
      [ -d "$m" ] || continue
      for field in name addr size; do
        if [ -r "$m/$field" ]; then
          printf "%s=" "$field"
          cat "$m/$field"
        fi
      done
    done
  done
'
probe fan_sensors sh -c '
  for p in /sys/class/hwmon/hwmon*/fan*_input /sys/class/hwmon/hwmon*/temp*_input; do
    [ -r "$p" ] || continue
    printf "%s=" "$p"
    cat "$p"
  done
'
probe xmutil_listapps_noninteractive sh -c '
  if ! command -v xmutil >/dev/null 2>&1; then
    echo "XMUTIL_NOT_INSTALLED"
  elif [ "$(id -u)" = 0 ]; then
    xmutil listapps
  elif command -v sudo >/dev/null 2>&1; then
    # -n means fail rather than request password on redirected SSH stdin.
    sudo -n xmutil listapps || echo "XMUTIL_SUDO_NONINTERACTIVE_UNAVAILABLE"
  else
    echo "XMUTIL_REQUIRES_PRIVILEGE"
  fi
'
probe active_firmware_metadata sh -c '
  for app in k26-starter-kits k24-starter-kits; do
    base="/lib/firmware/xilinx/$app"
    [ -d "$base" ] || continue
    echo "FIRMWARE_APP=$app"
    if [ -r "$base/shell.json" ]; then
      echo "SHELL_JSON_BEGIN=$app"
      cat "$base/shell.json"
      echo "SHELL_JSON_END=$app"
    fi
    for p in "$base"/*.dtbo "$base"/*.bit.bin; do
      [ -r "$p" ] || continue
      sha256sum "$p"
      if command -v file >/dev/null 2>&1; then file "$p"; fi
    done
  done
  link=/etc/dfx-mgrd/default_firmware
  if [ -e "$link" ] || [ -L "$link" ]; then
    printf "DEFAULT_FIRMWARE="
    readlink -f "$link" || :
  fi
'
probe fan_pwm_sysfs sh -c '
  for p in /sys/class/pwm/pwmchip*; do
    [ -d "$p" ] || continue
    echo "PWM_DEVICE=$p"
    for f in "$p"/npwm "$p"/device/of_node/compatible; do
      [ -r "$f" ] || continue
      printf "%s=" "$f"
      tr "\000" "\n" < "$f"
    done
  done
  if [ -r /etc/fancontrol ]; then
    echo "FANCONTROL_CONFIG_PRESENT"
    cat /etc/fancontrol
  fi
'
probe packaging_tools sh -c '
  for cmd in dtc python3 xmutil fpgautil; do
    command -v "$cmd" || :
  done
  if command -v dtc >/dev/null 2>&1; then dtc --version; fi
'
echo "M08_PATH_A_LINUX_READ_ONLY_END_NO_FPGA_CHANGES"
