#!/usr/bin/env bash
# M08.2b.3: ON-BOARD read-only kernel driver/PL ownership inspection.
# Streamed over SSH stdin; no remote files, no /dev/uio opens, no MMIO.
set -euo pipefail

echo M08_IDENTITY_BINDING_PREFLIGHT_BEGIN_READ_ONLY
MODEL="$(tr '\000' ' ' </proc/device-tree/model)"
[[ "$MODEL" == *KV260* ]] || { echo 'STOP_WRONG_BOARD'; exit 2; }
printf 'BOARD_MODEL=%s\n' "$MODEL"
STATE="$(cat /sys/class/fpga_manager/fpga0/state)"
[[ "$STATE" == operating ]] || { echo 'STOP_FPGA_MANAGER_NOT_OPERATING'; exit 2; }
echo "FPGA_MANAGER_STATE=$STATE"
[[ "$(systemctl is-active dfx-mgr)" == active ]] || exit 2
[[ "$(systemctl is-active fancontrol)" == active ]] || exit 2
echo DFX_MANAGER_AND_FANCONTROL_ACTIVE
OVERLAY=/sys/kernel/config/device-tree/overlays/m08-v1-fan-page-uio-review_image_1
[[ -d "$OVERLAY" ]] || { echo 'STOP_M08_OVERLAY_NOT_ACTIVE'; exit 2; }
echo M08_EXPECTED_OVERLAY_ACTIVE

for spec in m08-identity:0xa0000000 m08-page:0xa0001000; do
    NAME="${spec%%:*}"
    EXPECTED_ADDR="${spec#*:}"
    FOUND=0
    for DEVICE in /sys/class/uio/uio*; do
        [[ -r "$DEVICE/name" ]] || continue
        [[ "$(cat "$DEVICE/name")" == "$NAME" ]] || continue
        FOUND=$((FOUND + 1))
        [[ -r "$DEVICE/maps/map0/addr" && -r "$DEVICE/maps/map0/size" ]] || exit 2
        MAP_ADDR="$(cat "$DEVICE/maps/map0/addr")"
        MAP_SIZE="$(cat "$DEVICE/maps/map0/size")"
        [[ $((MAP_ADDR)) -eq $((EXPECTED_ADDR)) && $((MAP_SIZE)) -eq 4096 ]] || {
            echo "STOP_BAD_M08_UIO_MAP=$NAME:$MAP_ADDR:$MAP_SIZE"
            exit 2
        }
        # UIO has a kernel driver; do not infer its owner from the name alone.
        DRIVER_LINK="$DEVICE/device/driver"
        [[ -L "$DRIVER_LINK" ]] || { echo "STOP_NO_M08_KERNEL_DRIVER=$NAME"; exit 2; }
        DRIVER="$(readlink -f "$DRIVER_LINK")"
        [[ "$(basename "$DRIVER")" == uio_pdrv_genirq ]] || {
            echo "STOP_BAD_M08_KERNEL_DRIVER=$NAME:$DRIVER"
            exit 2
        }
        OTHER_MAP_COUNT=0
        for OTHER in "$DEVICE"/maps/map[1-9]*; do
            [[ ! -d "$OTHER" ]] || OTHER_MAP_COUNT=$((OTHER_MAP_COUNT + 1))
        done
        [[ "$OTHER_MAP_COUNT" -eq 0 ]] || {
            echo "STOP_EXTRA_M08_UIO_MAP=$NAME"
            exit 2
        }
        echo "M08_VERIFIED_BINDING|$NAME|$(basename "$DEVICE")|$MAP_ADDR|$MAP_SIZE|$DRIVER"
    done
    [[ "$FOUND" -eq 1 ]] || { echo "STOP_M08_UIO_BINDING_COUNT=$NAME:$FOUND"; exit 2; }
done

for SENSOR in /sys/class/hwmon/hwmon*/temp*_input; do
    [[ -r "$SENSOR" ]] || continue
    printf 'THERMAL_READING|%s|' "$SENSOR"
    cat "$SENSOR"
done

echo M08_IDENTITY_BINDING_PREFLIGHT_PASS_NO_MMIO
