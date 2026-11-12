#!/usr/bin/env bash
# M08.2b: streamed over existing SSH, read-only PRE-DEPLOYMENT observation.
# No file creation, driver changes, UIO device access, or FPGA operations.
set -u
printf 'M08_PHYSICAL_PREFLIGHT_BEGIN_READ_ONLY\n'
probe() {
    local label="$1"
    shift
    printf 'M08_GATE_PROBE_BEGIN|%s\n' "$label"
    "$@" 2>&1
    local rc=$?
    printf 'M08_GATE_PROBE_END|%s|rc=%s\n' "$label" "$rc"
}
probe board_identity sh -c 'uname -a; printf "MODEL="; tr "\000" " " < /proc/device-tree/model; echo; grep "^PRETTY_NAME=" /etc/os-release; cat /proc/cmdline'
probe firmware_manager sh -c 'systemctl is-active dfx-mgr; systemctl show dfx-mgr -p LoadState -p ActiveState -p FragmentPath -p ExecStart; if [ -r /etc/dfx-mgrd/daemon.conf ]; then cat /etc/dfx-mgrd/daemon.conf; fi; if [ -r /etc/dfx-mgrd/default_firmware ]; then cat /etc/dfx-mgrd/default_firmware; fi'
probe services_and_fpga sh -c 'systemctl is-active fancontrol; for f in /sys/class/fpga_manager/fpga*/state; do if [ -r "$f" ]; then printf "%s=" "$f"; cat "$f"; fi; done; for d in /sys/kernel/config/device-tree/overlays/*; do [ -d "$d" ] && echo "ACTIVE_OVERLAY=$d"; done; true'
probe manager_packages sh -c 'for p in dfx-mgr dfx-mgrd libdfx-mgr-dev xlnx-firmware-k26-starter-kits; do dpkg-query -W -f="\${Package} \${Version} \${Status}\n" "$p" 2>&1 || :; done; command -v xmutil; command -v dfx-mgr-client || :; command -v dfx-mgrd || :'
probe installed_baseline_files sh -c 'd=/lib/firmware/xilinx/k26-starter-kits; if [ ! -d "$d" ]; then echo "BASELINE_FIRMWARE_DIR_MISSING"; exit 2; fi; find "$d" -maxdepth 1 -type f -print | sort; for f in "$d"/*.dtbo "$d"/*.bit.bin "$d"/shell.json; do if [ -f "$f" ] && [ -r "$f" ]; then sha256sum "$f"; fi; done; if [ -r "$d/shell.json" ]; then cat "$d/shell.json"; fi'
probe xmutil_listapps sh -c 'if ! command -v xmutil >/dev/null 2>&1; then echo "XMUTIL_MISSING"; exit 2; fi; if [ "$(id -u)" -eq 0 ]; then xmutil listapps; else sudo -n xmutil listapps; fi'
probe thermal_hwmon sh -c 'for h in /sys/class/hwmon/hwmon*; do [ -d "$h" ] || continue; if [ -r "$h/name" ]; then printf "HWMON_NAME=%s:" "$h"; cat "$h/name"; fi; for f in "$h"/temp*_input "$h"/fan*_input "$h"/pwm*; do if [ -f "$f" ] && [ -r "$f" ]; then printf "SENSOR=%s:" "$f"; cat "$f"; fi; done; done; for t in /sys/class/thermal/thermal_zone*; do [ -d "$t" ] || continue; if [ -r "$t/type" ] && [ -r "$t/temp" ]; then printf "THERMAL=%s:" "$t"; cat "$t/type" "$t/temp"; fi; done; true'
probe fan_control_config sh -c 'if [ -r /etc/fancontrol ]; then cat /etc/fancontrol; else echo "FANCONTROL_CONFIG_NOT_READABLE"; fi; for p in /sys/class/pwm/pwmchip*; do if [ -d "$p" ]; then echo "PWM_CHIP=$p"; for x in "$p"/npwm "$p"/device/of_node/compatible; do if [ -r "$x" ]; then printf "%s=" "$x"; tr "\000" " " < "$x"; echo; fi; done; fi; done; true'
probe linux_resources sh -c 'cat /proc/iomem; if [ -d /sys/bus/platform/drivers/uio_pdrv_genirq ]; then echo "GENERIC_UIO_DRIVER_PRESENT"; fi; for d in /sys/class/uio/uio*; do [ -d "$d" ] || continue; printf "UIO=%s:" "$d"; if [ -r "$d/name" ]; then cat "$d/name"; fi; for m in "$d"/maps/map*; do [ -d "$m" ] || continue; for f in "$m"/addr "$m"/size; do [ -r "$f" ] && { printf "%s=" "$f"; cat "$f"; }; done; done; done; true'
printf 'M08_PHYSICAL_PREFLIGHT_END_NO_FPGA_CHANGES\n'
