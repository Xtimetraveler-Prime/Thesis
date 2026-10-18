#!/usr/bin/env bash
# P08-A3.1: physical latency PILOT only (16 TRAIN-derived validation frames).
# Never execute under Linux DDR ownership: JTAG owns 0x40000000..0x43FFFFFF.
# This script will PROGRAM the accepted PL and launch a NEW experimental ELF.
# User must reboot into JTAG-only bare-metal before, and reboot afterward.
set -euo pipefail

V3="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
RUN="${P08_A3_1_RUN_DIR:?Set a NEW absolute physical evidence directory outside Git}"
BUILD="${P08_A2_2_BUILD_DIR:?Point to the user-verified P08-A2.2 Vitis build}"
REPORTS="${P03_DIAG_REPORTS:?Use the accepted routed P03.2c reports directory}"
STAGE="${P08_A3_1_STAGE_DIR:?Use the frozen first-16 TRAIN validation stage}"
EXPECTED_ELF="${P08_A3_1_EXPECTED_ELF_SHA256:?Supply the actual newly built A2.2 ELF SHA256}"
MASTER="${P08_A3_1_MASTER_DDR:-$V3/artifacts/p06_a4_static_ddr_seed20261013/core0_initial_p02_ddr_512k.bin}"
XSA="$REPORTS/p03_2_ps_mmio.xsa"
BIT="$REPORTS/p03_2_ps_mmio.bit"
LTX="$REPORTS/p03_2_ps_mmio.ltx"
METRICS="$REPORTS/p03_2_post_route_metrics.txt"
ELF="$BUILD/vitis_workspace/p08_a2_2_board.elf"
XSDB_URL="${P08_A3_1_XSDB_URL:-tcp:127.0.0.1:3121}"
HW_URL="${P08_A3_1_HW_URL:-localhost:3121}"
TIMEOUT="${P08_A3_1_TIMEOUT:-3600}"
XSA_SHA=52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f
MASTER_SHA=9617a822f74faa8723869bb576cf57b38af1a1a91ac81c47c246a9425d0dd955
MARKER=P08_A2_2_PER_TICK_KV260_A53_CANDIDATE_V1
cd "$V3"

# PRE-HARDWARE GATES (do not launch even an XSDB width probe without these).
[[ "$RUN" == /* && ! -e "$RUN" && ! -L "$RUN" ]] || {
    echo "ERROR: new absolute no-overwrite physical evidence directory required" >&2; exit 2;
}
# Raw physical evidence must never be placed in tracked Git worktrees.
REPO_ROOT="$(git -C "$V3" rev-parse --show-toplevel)"
RUN_CANONICAL="$(realpath -m -- "$RUN")"
REPO_CANONICAL="$(realpath -m -- "$REPO_ROOT")"
[[ "$RUN_CANONICAL" != "$REPO_CANONICAL" &&
   "$RUN_CANONICAL" != "$REPO_CANONICAL/"* ]] || {
    echo "ERROR: physical raw evidence must be outside the Git checkout" >&2;exit 2;
}
[[ "$STAGE" == /* && -d "$STAGE" ]] || {
    echo "ERROR: first16 validation stage must exist at absolute path" >&2; exit 2;
}
[[ "${P08_A3_1_CONFIRM_JTAG_ONLY:-}" == YES &&
   "${P08_A3_1_CONFIRM_DDR_OVERWRITE:-}" == YES &&
   "${P08_A3_1_CONFIRM_TRAIN_VALIDATION_ONLY:-}" == YES ]] || {
    echo "ERROR: physically reboot KV260 into bare-metal JTAG-only state" >&2
    echo "Then explicitly set all THREE P08_A3_1_CONFIRM_* variables to YES." >&2
    exit 2
}
[[ "$EXPECTED_ELF" =~ ^[a-fA-F0-9]{64}$ ]] || {
    echo "ERROR: explicit expected ELF SHA256 must be exactly 64 hex digits" >&2;exit 2;
}
[[ "$TIMEOUT" =~ ^[0-9]+$ ]] && (( TIMEOUT >= 10 && TIMEOUT <= 28800 )) || {
    echo "ERROR: timeout outside 10..28800 seconds" >&2;exit 2;
}
for tool in python xsdb vivado sha256sum grep cmp readelf git realpath;do
    command -v "$tool" >/dev/null || {
        echo "ERROR: missing $tool (source Vivado/Vitis tool environment)" >&2;exit 2;
    }
done
for f in "$MASTER" "$XSA" "$BIT" "$LTX" "$METRICS" "$ELF" "$BUILD/build_identity.txt";do
    [[ -s "$f" ]] || { echo "ERROR: missing artifact $f" >&2;exit 2; }
done
[[ "$(sha256sum "$XSA" | awk '{print $1}')" == "$XSA_SHA" ]] || {
    echo "ERROR: accepted XSA pin mismatch" >&2;exit 2;
}
[[ "$(sha256sum "$MASTER" | awk '{print $1}')" == "$MASTER_SHA" ]] || {
    echo "ERROR: frozen original core0 master differs" >&2;exit 2;
}
ACTUAL_ELF="$(sha256sum "$ELF" | awk '{print $1}')"
[[ "$ACTUAL_ELF" == "${EXPECTED_ELF,,}" ]] || {
    echo "ERROR: ELF digest changed since the user-verified build" >&2;exit 2;
}
grep -Fxq "P08_A2_2_ELF_SHA256=$ACTUAL_ELF" "$BUILD/build_identity.txt" || {
    echo "ERROR: recorded build identity does not match candidate ELF" >&2;exit 2;
}
grep -aFq "$MARKER" "$ELF" || {
    echo "ERROR: ELF missing exact P08-A2.2 candidate identity" >&2;exit 2;
}
if grep -aFq P07_A4_2B_PERSISTENT_KV260_A53_FROZEN_TRACK_A_V1 "$ELF";then
    echo "ERROR: wrong/legacy A53 candidate ELF" >&2;exit 2;
fi
for expected in \
  p03_hpm0_data_width_bits=128 \
  p03_hpm0_transport=smartconnect_width_protocol \
  p03_mmio_slave_data_width_bits=32 \
  p03_ps_mmio_master=FPD \
  p03_mmio_base=0xA4000000;do
    grep -Fxq "$expected" "$METRICS" || {
        echo "ERROR: routed artifact metrics do not match $expected" >&2;exit 2;
    }
done

# Require byte identity to the checked-out firmware and accepted original C.
for f in p08_a2_2_board.c p08_a2_timing.c p08_a2_2_ticks.c p08_a2_2_runtime.c;do
    cmp -s "$BUILD/source/$f" "software/p08/$f" || {
        echo "ERROR: staged P08 C source drift: $f" >&2;exit 2;
    }
done
for f in p08_a2_timing.h p08_a2_2_ticks.h p08_a2_2_runtime.h;do
    cmp -s "$BUILD/source/$f" "software/p08/$f" || {
        echo "ERROR: staged P08 header drift: $f" >&2;exit 2;
    }
done
for f in p07_a4_stream.c p07_a4_supervisor.c p07_a1_ingress.c p07_a2_sha256.c;do
    cmp -s "$BUILD/source/$f" "software/p07/$f" || {
        echo "ERROR: staged frozen P07 source drift: $f" >&2;exit 2;
    }
done
for f in p07_a1_ingress.h p07_a2_runtime.h p07_a2_batch.h p07_a2_sha256.h p07_a4_stream.h p07_a4_supervisor.h;do
    cmp -s "$BUILD/source/include/$f" "software/p07/include/$f" || {
        echo "ERROR: staged frozen P07 header drift: $f" >&2;exit 2;
    }
done
for f in p03_runtime.c p03_hw_adapter.c p03_hw_runtime_bridge.c p03_hw_xilinx_io.c;do
    cmp -s "$BUILD/source/$f" "software/p03/$f" || {
        echo "ERROR: staged frozen P03 C drift: $f" >&2;exit 2;
    }
done
for f in p03_mmio.h p03_runtime.h p03_hw_adapter.h p03_hw_runtime_bridge.h p03_hw_xilinx_io.h;do
    cmp -s "$BUILD/source/$f" "software/p03/include/$f" || {
        echo "ERROR: staged frozen P03 header drift: $f" >&2;exit 2;
    }
done

# TRAIN validation only. This checker authenticates descriptor CRCs, pixels,
# validation host ledger, frozen map and initial journal BEFORE hardware.
PYTHONPATH="$V3/src" python scripts/p07_a4_2_check.py --stage-dir "$STAGE"
PYTHONPATH="$V3/src" python - "$STAGE" <<'PY'
import json
from pathlib import Path
import sys
p=Path(sys.argv[1])/"p07_a4_2a_stage_manifest.json"
m=json.loads(p.read_text())
if (m.get("scope")!="TRAIN_DERIVED_VALIDATION_FIRST_16" or
    m.get("frame_count")!=16 or
    m.get("official_mnist_test")!="SEALED"):
    raise SystemExit("P08-A3.1 refuses anything but first-16 TRAIN-validation")
print("P08_A3_1_STAGE_FIRST16_ACCEPTED_SCOPE_PASS=1")
PY
# Stronger pre-hardware check: authenticate the ORIGINAL first16 TRAIN split
# against user-local frozen canonical TRAIN, not just manifest/ledger hashes.
# This prevents a forged TRAIN label on a different image population.
PYTHONPATH="$V3/src" python - "$STAGE" <<'PY'
from pathlib import Path
import json
import sys
from scripts.p07_a4_2_verify import validate_staging
from loihi_twin_v2.p06_a3_data import load_train_validation
from loihi_twin_v2.p06_a3_training import load_candidate
from loihi_twin_v2.p07_a4_validation import (
    select_validation_prefix, validate_ledger,
)
stage=Path(sys.argv[1])
meta,stream=validate_staging(stage)
split=load_train_validation(Path("data/mnist_raw"))
_,candidate=load_candidate(Path("artifacts/p06_a3_candidate_seed20261013"))
if split.manifest != candidate.get("source_dataset"):
    raise SystemExit("P08-A3.1 original canonical TRAIN split/model mismatch")
frames=select_validation_prefix(split,16)
ledger=json.loads((stage/"p07_a4_2a_validation_labels_HOST_ONLY.json").read_text())
validate_ledger(ledger,frames,stream.images)
if meta["scope"]!="TRAIN_DERIVED_VALIDATION_FIRST_16":
    raise SystemExit("P08-A3.1 wrong sealed pilot scope")
print("P08_A3_1_ORIGINAL_TRAIN_FIRST16_PHYSICAL_PREFLIGHT_PASS=1")
PY
readelf -lW "$ELF" | python -c '
import sys
loads=[f for line in sys.stdin if (f:=line.split()) and f[0]=="LOAD"]
if not loads: raise SystemExit("No program LOAD segments")
for f in loads:
    start=int(f[2],16); stop=start+int(f[5],16)
    if start < 0x44000000 and stop > 0x40000000:
        raise SystemExit("P08-A3.1 candidate ELF overlaps reserved 64MiB DDR")
print("P08_A3_1_ELF_DDR_ISOLATION_PASS=1")
'

mkdir -p "$RUN/readback"
# Preserve artifact hashes and the exit status even when provisioning,
# hardware, timeout or independent oracle validation fails.
capture_attempt_exit() {
    local rc=$?
    printf 'script_exit_status=%s\n' "$rc" > "$RUN/attempt_exit_status.txt"
    {
        for f in "$RUN"/p07_a4_journal_1m.bin \
                 "$RUN"/p07_a4_trace_64k.bin \
                 "$RUN"/p08_a2_1_images_1m.bin \
                 "$RUN"/p08_a2_2_ticks_3m.bin \
                 "$RUN"/p08_a3_1_verified_pilot.json;do
            [[ ! -f "$f" ]] || sha256sum "$f"
        done
    } > "$RUN/available_output_sha256.txt"
}
trap capture_attempt_exit EXIT
python - "$RUN/trace_zero_64k.bin" <<'PY'
from pathlib import Path
import sys
with Path(sys.argv[1]).open("xb") as f:
    f.write(bytes(65536))
PY
{
  echo "phase=P08-A3.1 initial 16-frame TRAIN-only KV260 latency pilot"
  echo "status=PHYSICAL_NOT_YET_RUN"
  echo "git_commit=$(git rev-parse HEAD)"
  echo "candidate_elf_sha256=$ACTUAL_ELF"
  echo "scope=TRAIN_DERIVED_VALIDATION_FIRST_16"
  echo "official_TEST_population=NOT_USED"
  echo "power_energy=DEFERRED"
  sha256sum "$XSA" "$BIT" "$LTX" "$ELF" "$MASTER" \
      "$STAGE/p07_a4_descriptor_256.bin" \
      "$STAGE/p07_a4_mapping_1568.bin" \
      "$STAGE/p07_a4_pixels_raw.bin" \
      "$STAGE/p07_a4_journal_initial_1m.bin" \
      "$STAGE/p07_a4_2a_stage_manifest.json" \
      "$STAGE/p07_a4_2a_validation_labels_HOST_ONLY.json"
} | tee "$RUN/physical_identity.txt"

cat <<'EOF'
P08-A3.1 IS A DESTRUCTIVE BARE-METAL JTAG RUN.
This programs the P03.2c FPGA and overwrites 0x40000000..0x43FFFFFF.
Never run with Linux or any other owner of DDR. Do not continue a halted OS.
Only the original first-16 TRAIN-derived validation images are admitted.
Reboot the KV260 again after capture; preserve ALL evidence even on failure.
EOF

# Follow the accepted P07 ordering: PS-width check, byte-exact DDR staging,
# route-bitstream program, one autonomous A53 run, independent oracle check.
xsdb vivado/p03_2c_xsdb_ps_axi_width_diag.tcl "$XSDB_URL" \
    2>&1 | tee "$RUN/ps_width.log"
grep -Fxq 'P03_2C_PS_FPD_HPM0_WIDTH_BITS=128' "$RUN/ps_width.log"

xsdb vivado/p07_a4_xsdb_prepare.tcl \
    "$MASTER" "$STAGE" "$RUN/trace_zero_64k.bin" \
    "$RUN/readback" "$XSDB_URL" 2>&1 | tee "$RUN/provision.log"
grep -Fq 'P07_A4_2C_XSDB_PROVISION_PASS=1' "$RUN/provision.log"

vivado -mode batch -source vivado/p03_2c_program_bitstream.tcl \
    -tclargs "$BIT" "$LTX" "$HW_URL" 2>&1 | tee "$RUN/program.log"
grep -Fq 'PASS: P03.2c accepted PS-MMIO bitstream programmed and PL reset released' \
    "$RUN/program.log"

# A2.2 XSDB module enforces BOTH isolated consent flags, checks exact ELF
# marker, waits for the P07 journal and BOTH P08 timing sidecar terminals.
export P08_A2_CONFIRM_KV260_JTAG_ONLY=YES
export P08_A2_CONFIRM_VALIDATION_ONLY=YES
xsdb vivado/p08_a2_2_xsdb_run.tcl \
    "$ELF" "$RUN/p07_a4_journal_1m.bin" "$RUN/p07_a4_trace_64k.bin" \
    "$RUN/p08_a2_1_images_1m.bin" "$RUN/p08_a2_2_ticks_3m.bin" \
    "$XSDB_URL" "$TIMEOUT" 2>&1 | tee "$RUN/a53_run.log"
grep -Fxq 'P08_A2_2_KV260_STATUS=TERMINAL_ALL_THREE_SUCCESS_UNVERIFIED_NUMERICS' \
    "$RUN/a53_run.log" || {
        echo "ERROR: terminal statuses not all successful; keep raw evidence" >&2;exit 4;
    }

# Existing original P07 independent packed oracle is run FIRST inside here.
# Timing and per-tick packet/encoder verification only AFTER it succeeds.
PYTHONPATH="$V3/src" python scripts/p08_a3_1_verify.py \
    --stage-dir "$STAGE" --journal "$RUN/p07_a4_journal_1m.bin" \
    --trace "$RUN/p07_a4_trace_64k.bin" \
    --image-timing "$RUN/p08_a2_1_images_1m.bin" \
    --tick-timing "$RUN/p08_a2_2_ticks_3m.bin" \
    --report "$RUN/p08_a3_1_verified_pilot.json" \
    2>&1 | tee "$RUN/verify.log"
grep -Fxq 'P08_A3_1_16FRAME_PHYSICAL_PILOT_PASS=1' "$RUN/verify.log"

# Evidence hashes written only after both proofs, to an untracked directory.
sha256sum "$RUN"/p07_a4_journal_1m.bin "$RUN"/p07_a4_trace_64k.bin \
    "$RUN"/p08_a2_1_images_1m.bin "$RUN"/p08_a2_2_ticks_3m.bin \
    "$RUN"/p08_a3_1_verified_pilot.json > "$RUN/physical_output_sha256.txt"

echo "P08_A3_1_PHYSICAL_EVIDENCE_DIR=$RUN"
echo "P08_A3_1_FULL_PHYSICAL_GATE_PASS=1"
echo "REBOOT THE KV260; never resume the halted operating system."
