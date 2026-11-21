#!/usr/bin/env bash
# M08.5 KV260 first-party READ-ONLY Linux PS/PL/DMA inventory.
# Streamed over SSH via 'bash -s'. Creates NO files on KV260.
# No sudo, /dev/*, MMIO, DMA allocation, FPGA manager writes, xmutil,
# firmware changes, kernel module loading, or board reconfiguration.
set -euo pipefail
export LC_ALL=C
printf 'M08_5_SSH_READONLY_BEGIN\n'
MODEL_FILE=/proc/device-tree/model
[[ -r "$MODEL_FILE" ]] || { echo 'STOP_MODEL_UNREADABLE'; exit 2; }
MODEL="$(tr '\000' ' ' < "$MODEL_FILE")"
[[ "$MODEL" == *KV260* ]] || { echo "STOP_UNEXPECTED_BOARD_MODEL=$MODEL"; exit 2; }
printf 'BOARD_MODEL=%s\n' "$MODEL"
section() { printf 'SECTION_BEGIN|%s\n' "$1"; }
end_section() { printf 'SECTION_END|%s\n' "$1"; }
read_txt() {
    local label="$1" file="$2" limit="${3:-2048}"
    if [[ ! -r "$file" || -L "$file" ]]; then
        printf 'READ_UNAVAILABLE|%s\n' "$label"; return
    fi
    printf 'READ_BEGIN|%s\n' "$label"
    head -c "$limit" "$file" | tr '\000' ' ' || :
    printf '\nREAD_END|%s\n' "$label"
}
read_hex() {
    local label="$1" file="$2"
    if [[ ! -r "$file" || -L "$file" ]]; then
        printf 'HEX_UNAVAILABLE|%s\n' "$label"; return
    fi
    printf 'HEX|%s|' "$label"
    head -c 128 "$file" | od -An -tx1 | tr -d ' \n' || :
    printf '\n'
}
list_dir() {
    local label="$1" dir="$2" cap="${3:-80}"
    if [[ ! -d "$dir" ]]; then
        printf 'DIR_UNAVAILABLE|%s\n' "$label"; return
    fi
    printf 'DIR_BEGIN|%s\n' "$label"
    local count=0 entry
    for entry in "$dir"/*; do
        [[ -e "$entry" || -L "$entry" ]] || continue
        count=$((count+1))
        if ((count > cap)); then printf 'DIR_TRUNCATED|%s|cap=%s\n' "$label" "$cap"; break; fi
        printf 'ENTRY|%s|%s\n' "$label" "${entry##*/}"
    done
    printf 'DIR_END|%s\n' "$label"
}
section system
read_txt os_release /etc/os-release 2048
read_txt proc_version /proc/version 2048
read_txt cmdline /proc/cmdline 2048
read_txt boot_model /proc/device-tree/model 256
read_txt fpga_manager_state /sys/class/fpga_manager/fpga0/state 128
read_txt kernel_modules /proc/modules 10000
end_section system
section device_tree
list_dir overlay_names /sys/kernel/config/device-tree/overlays 24
for symbol in amba fpga_full zynqmp_reset; do
    read_txt "dt_symbol_$symbol" "/proc/device-tree/__symbols__/$symbol" 256
done
# Bounded live applied-DT *metadata only*. No raw MMIO access.
for node in /proc/device-tree/amba /proc/device-tree/axi /proc/device-tree/fpga-full; do
    [[ -d "$node" ]] || continue
    printf 'DT_NODE=%s\n' "$node"
    for key in compatible status '#address-cells' '#size-cells' dma-ranges iommus; do
        read_hex "dt_${node##*/}_$key" "$node/$key"
    done
done
list_dir dt_top /proc/device-tree 100
end_section device_tree
section dma_platform
list_dir dma_heap /sys/class/dma_heap 32
list_dir fpga_managers /sys/class/fpga_manager 32
list_dir iommu_groups /sys/kernel/iommu_groups 64
list_dir platform_devices /sys/bus/platform/devices 128
# Bound the first 40 matching platform-device names. Observations are
# possible clues, never driver binding or valid DMA handle attestations.
seen=0
for dev in /sys/bus/platform/devices/*; do
    [[ -d "$dev" ]] || continue
    name="${dev##*/}"
    case "${name,,}" in
        *axi*|*dma*|*fpga*|*smmu*|*iommu*|*uio*|*zynq*|*m08*|*neurom*|*a000*)
            seen=$((seen+1))
            if ((seen > 40)); then echo 'PLATFORM_CANDIDATES_TRUNCATED'; break; fi
            printf 'PLATFORM_CANDIDATE|%s\n' "$name"
            if [[ -L "$dev/driver" ]]; then
                printf 'DRIVER_LINK|%s|' "$name"
                readlink "$dev/driver" || :
            else
                printf 'DRIVER_UNBOUND_OR_UNKNOWN|%s\n' "$name"
            fi
            if [[ -L "$dev/iommu_group" ]]; then
                printf 'IOMMU_GROUP_LINK|%s|' "$name"
                readlink "$dev/iommu_group" || :
            fi
            for key in dma_mask_bits coherent_dma_mask_bits; do
                read_txt "platform_${name}_$key" "$dev/$key" 128
            done
            if [[ -d "$dev/of_node" ]]; then
                read_txt "platform_${name}_compatible" "$dev/of_node/compatible" 256
                for key in dma-coherent dma-ranges iommus reg; do
                    read_hex "platform_${name}_$key" "$dev/of_node/$key"
                done
            fi
            ;;
    esac
done
end_section dma_platform
section safety_observation
for f in /sys/class/hwmon/hwmon*/name /sys/class/hwmon/hwmon*/fan*_input /sys/class/hwmon/hwmon*/temp*_input /sys/class/thermal/thermal_zone*/temp; do
    [[ -r "$f" && ! -L "$f" ]] || continue
    read_txt "sensor_$f" "$f" 96
done
end_section safety_observation
printf 'M08_5_SSH_READONLY_END_NO_DMA_OR_BOARD_CHANGES\n'
