#!/usr/bin/env bash
# M08.5: OWNER-PC offline Vivado 2025.2 QUARANTINED PS/PL BD.
# Creates one NEW evidence dir, never touches KV260/SSH/HW Manager/JTAG.
# Even a successful BD is NOT synthesis/route/bitstream/physical DMA ready.
set -euo pipefail
if [[ "$#" -ne 0 ]]; then
    echo "Usage: bash scripts/run_m08_m085_pspl_quarantine_bd_pc.sh" >&2
    exit 2
fi
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BD="$HERE/m08_m085_pspl_quarantine_bd.tcl"
if [[ ! -f "$BD" || -L "$BD" ]]; then
    echo 'STOP: missing or symlinked first-party BD Tcl' >&2; exit 2
fi
if ! command -v vivado >/dev/null || ! command -v sha256sum >/dev/null; then
    echo 'STOP: Vivado and sha256sum must be installed on the owner PC' >&2; exit 2
fi
VER="$(vivado -version 2>&1 | head -n 1)"
if [[ "$VER" != *2025.2* ]]; then
    echo "STOP: refusing non-Vivado-2025.2 tool: $VER" >&2; exit 2
fi
BASE="$HOME/Thesis_Evidence/M08"
if [[ ! -d "$BASE" || -L "$BASE" ]]; then
    echo "STOP: create an existing regular M08 evidence parent: $BASE" >&2; exit 2
fi
D="$(mktemp -d "$BASE/m08_m085_pspl_bd_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXXXX")"
chmod 700 "$D"
echo "M08_5_OFFLINE_BD_EVIDENCE_DIR=$D"
set +e
vivado -mode batch -source "$BD" -log "$D/00_vivado.log" \
    -journal "$D/01_vivado.jou" -tclargs "$D" > "$D/04_stdout.txt" 2> "$D/05_stderr.txt"
rc=$?
set -e
printf 'vivado_exit_status=%s\n' "$rc" > "$D/02_vivado_exit_status.txt"
cp -- "$BD" "$D/03_builder_source.tcl"
printf 'source_revision=%s\nrepository_dir=%s\nvivado=%s\nscope=QUARANTINED_PSPL_BD_ONLY_NO_DMA\n' \
    "$(git -C "$HERE/../../.." rev-parse HEAD 2>/dev/null || echo UNKNOWN)" \
    "$(cd "$HERE/.." && pwd)" "$VER" > "$D/06_context.txt"
# Source snapshot plus all native stdout/stderr/Tcl and original reports;
# never produce a "good" receipt by rewriting any prior evidence.
(
    cd "$D"
    find . -path './project' -prune -o -type f ! -name '99_evidence_sha256.txt' \
        -print0 | LC_ALL=C sort -z | xargs -0 -r sha256sum -- > 99_evidence_sha256.txt
)
if (( rc != 0 )) ||
   ! grep -Fxq 'M08_M085_QUARANTINED_PSPL_BD_COMPLETE_NO_DMA_NO_BITSTREAM' "$D/04_stdout.txt" ||
   ! grep -Fxq 'status=OFFLINE_BD_TOPOLOGY_ONLY_NEVER_DMA_READY' "$D/reports/20_quarantined_bd_observation.txt" 2>/dev/null ||
   [[ -d "$D/bitstream_candidate" ]] ||
   find "$D" -type f \( -name '*.bit' -o -name '*.bin' \) -print -quit | grep -q .; then
    echo 'M08_5_OFFLINE_BD_INCOMPLETE_OR_REJECTED_NO_PHYSICAL_RELEASE' >&2
    echo "Original evidence preserved in: $D" >&2
    exit 3
fi
echo 'M08_5_OFFLINE_BD_SOURCE_TOPOLOGY_ONLY_PASS_NOT_DMA_READY'
echo "Verify: ( cd '$D' && sha256sum -c 99_evidence_sha256.txt )"
