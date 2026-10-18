#!/usr/bin/env bash
# P08-A3.2.2 — ONE variant-selected 1024-image TRAIN-only physical capture.
# DANGEROUS: with consent this programs KV260 FPGA, runs A53 and OVERWRITES
# reserved 0x40000000..0x43FFFFFF DDR. NEVER RUN WHILE KV260 LINUX OWNS DDR.
# OFFLINE preflight ONLY when P08_A3_2_PREFLIGHT_ONLY=YES.
set -euo pipefail
V3="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$V3"
MODE="${P08_A3_2_VARIANT:?Explicitly choose A2_1 or A2_2}"
case "$MODE" in
  A2_1)
    BUILD="${P08_A2_BUILD_DIR:?Supply original user-built A2.1 build directory}"
    ELF_NAME=p08_a2_board.elf
    ID_PREFIX=P08_A2_1
    MARKER=P08_A2_1_LATENCY_ONLY_KV260_A53_CANDIDATE_V1
    PINNED_ELF_SHA=fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0
    XSDB_SCRIPT=vivado/p08_a2_xsdb_run.tcl
    SUCCESS_STATUS=P08_A2_1_KV260_STATUS=TERMINAL_BOTH_SUCCESS_UNVERIFIED_NUMERICS
    ;;
  A2_2)
    BUILD="${P08_A2_2_BUILD_DIR:?Supply original user-built A2.2 build directory}"
    ELF_NAME=p08_a2_2_board.elf
    ID_PREFIX=P08_A2_2
    MARKER=P08_A2_2_PER_TICK_KV260_A53_CANDIDATE_V1
    PINNED_ELF_SHA=87cf5fc4fe37d9d053a3c365db8ae9fdc7e782857612f273835cf5e611aba361
    XSDB_SCRIPT=vivado/p08_a2_2_xsdb_run.tcl
    SUCCESS_STATUS=P08_A2_2_KV260_STATUS=TERMINAL_ALL_THREE_SUCCESS_UNVERIFIED_NUMERICS
    ;;
  *)
    echo "ERROR: P08_A3_2_VARIANT must be A2_1 or A2_2" >&2;exit 2 ;;
esac

RUN="${P08_A3_2_RUN_DIR:?Set a FRESH absolute evidence directory outside Git}"
STAGE="${P08_A3_2_STAGE_DIR:?Set original accepted first1024 TRAIN-validation stage}"
REPORTS="${P03_DIAG_REPORTS:?Use genuine accepted P03.2c routed reports directory}"
MASTER="${P08_A3_2_MASTER_DDR:-$V3/artifacts/p06_a4_static_ddr_seed20261013/core0_initial_p02_ddr_512k.bin}"
ELF="$BUILD/vitis_workspace/$ELF_NAME"
XSA="$REPORTS/p03_2_ps_mmio.xsa"
BIT="$REPORTS/p03_2_ps_mmio.bit"
LTX="$REPORTS/p03_2_ps_mmio.ltx"
METRICS="$REPORTS/p03_2_post_route_metrics.txt"
XSDB_URL="${P08_A3_2_XSDB_URL:-tcp:127.0.0.1:3121}"
HW_URL="${P08_A3_2_HW_URL:-localhost:3121}"
TIMEOUT="${P08_A3_2_TIMEOUT:-3600}"
XSA_SHA=52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f
MASTER_SHA=9617a822f74faa8723869bb576cf57b38af1a1a91ac81c47c246a9425d0dd955

# OFFLINE provenance / output refusal. No JTAG call occurs above this point.
[[ "$RUN" == /* && ! -e "$RUN" && ! -L "$RUN" ]] || {
  echo "ERROR: evidence directory must be absolute, NEW and never overwritten" >&2;exit 2;
}
REPO_ROOT="$(git rev-parse --show-toplevel)"
RUN_REAL="$(realpath -m -- "$RUN")"
ROOT_REAL="$(realpath -m -- "$REPO_ROOT")"
[[ "$RUN_REAL" != "$ROOT_REAL" && "$RUN_REAL" != "$ROOT_REAL/"* ]] || {
  echo "ERROR: raw physical evidence must remain outside Git checkout" >&2;exit 2;
}
[[ "$STAGE" == /* && -d "$STAGE" ]] || {
  echo "ERROR: source stage must be an existing absolute path" >&2;exit 2;
}
[[ "$RUN_REAL" != "$(realpath -m -- "$STAGE")" &&
   "$RUN_REAL" != "$(realpath -m -- "$BUILD")" ]] || {
  echo "ERROR: evidence path aliases stage/build directory" >&2;exit 2;
}
if [[ "${P08_A3_2_PREFLIGHT_ONLY:-}" != YES ]];then
  [[ "${P08_A3_2_CONFIRM_JTAG_ONLY:-}" == YES &&
     "${P08_A3_2_CONFIRM_DDR_OVERWRITE:-}" == YES &&
     "${P08_A3_2_CONFIRM_TRAIN_VALIDATION_ONLY:-}" == YES ]] || {
    echo "ERROR: physical run requires a NEW dedicated JTAG-only bare-metal boot," >&2
    echo "64MiB DDR overwrite consent and original TRAIN-validation-only consent" >&2
    exit 2
  }
fi
[[ "$TIMEOUT" =~ ^[0-9]+$ ]] && (( TIMEOUT>=10 && TIMEOUT<=28800 )) || {
  echo "ERROR: invalid XSDB timeout" >&2;exit 2;
}
for cmd in python sha256sum cmp grep readelf git realpath;do
  command -v "$cmd" >/dev/null || { echo "ERROR: missing $cmd" >&2;exit 2; }
done
# Vivado/XSDB are NOT needed or invoked in offline preflight.
if [[ "${P08_A3_2_PREFLIGHT_ONLY:-}" != YES ]];then
  for cmd in xsdb vivado;do
    command -v "$cmd" >/dev/null || { echo "ERROR: missing $cmd" >&2;exit 2; }
  done
fi
for f in "$XSA" "$BIT" "$LTX" "$METRICS" "$MASTER" "$ELF" "$BUILD/build_identity.txt";do
  [[ -s "$f" ]] || { echo "ERROR: physical dependency missing: $f" >&2;exit 2; }
done
[[ "$(sha256sum "$XSA" | awk '{print $1}')" == "$XSA_SHA" ]] || {
  echo "ERROR: accepted XSA mismatch" >&2;exit 2;
}
[[ "$(sha256sum "$MASTER" | awk '{print $1}')" == "$MASTER_SHA" ]] || {
  echo "ERROR: original frozen core0 model master SHA mismatch" >&2;exit 2;
}
ACTUAL_ELF_SHA="$(sha256sum "$ELF" | awk '{print $1}')"
[[ "$ACTUAL_ELF_SHA" == "$PINNED_ELF_SHA" ]] || {
  echo "ERROR: $MODE ELF differs from pinned user-attested build" >&2;exit 2;
}
for marker in "${ID_PREFIX}_ELF_SHA256=$PINNED_ELF_SHA" \
              "${ID_PREFIX}_XSA_SHA256=$XSA_SHA" \
              "${ID_PREFIX}_VITIS_BUILD_PASS=1";do
  grep -Fxq "$marker" "$BUILD/build_identity.txt" || {
    echo "ERROR: $MODE build identity missing $marker" >&2;exit 2;
  }
done
grep -aFq "$MARKER" "$ELF" || {
  echo "ERROR: A53 ELF identity marker does not match $MODE" >&2;exit 2;
}
if grep -aFq P07_A4_2B_PERSISTENT_KV260_A53_FROZEN_TRACK_A_V1 "$ELF";then
  echo "ERROR: cannot substitute historical P07 ELF" >&2;exit 2
fi
for required in p03_hpm0_data_width_bits=128 \
                p03_hpm0_transport=smartconnect_width_protocol \
                p03_mmio_slave_data_width_bits=32 \
                p03_ps_mmio_master=FPD p03_mmio_base=0xA4000000;do
  grep -Fxq "$required" "$METRICS" || {
    echo "ERROR: P03 accepted route/AXI metrics drift at $required" >&2;exit 2;
  }
done

# Byte-exact source identity of BOTH original firmware candidates.
if [[ "$MODE" == A2_1 ]];then
  P08_C=(p08_a2_board.c p08_a2_timing.c)
  P08_HEADERS=(p08_a2_timing.h)
  P07_C=(p07_a4_stream.c p07_a4_supervisor.c p07_a2_runtime.c p07_a1_ingress.c p07_a2_sha256.c)
else
  P08_C=(p08_a2_2_board.c p08_a2_timing.c p08_a2_2_ticks.c p08_a2_2_runtime.c)
  P08_HEADERS=(p08_a2_timing.h p08_a2_2_ticks.h p08_a2_2_runtime.h)
  P07_C=(p07_a4_stream.c p07_a4_supervisor.c p07_a1_ingress.c p07_a2_sha256.c)
fi
for f in "${P08_C[@]}" "${P08_HEADERS[@]}";do
  cmp -s "$BUILD/source/$f" "software/p08/$f" || {
    echo "ERROR: built $MODE P08 source/header drift: $f" >&2;exit 2;
  }
done
for f in "${P07_C[@]}";do
  cmp -s "$BUILD/source/$f" "software/p07/$f" || {
    echo "ERROR: built $MODE frozen P07 code drift: $f" >&2;exit 2;
  }
done
for f in p07_a1_ingress.h p07_a2_runtime.h p07_a2_batch.h \
         p07_a2_sha256.h p07_a4_stream.h p07_a4_supervisor.h;do
  cmp -s "$BUILD/source/include/$f" "software/p07/include/$f" || {
    echo "ERROR: built $MODE frozen P07 header drift: $f" >&2;exit 2;
  }
done
for f in p03_runtime.c p03_hw_adapter.c p03_hw_runtime_bridge.c p03_hw_xilinx_io.c;do
  cmp -s "$BUILD/source/$f" "software/p03/$f" || {
    echo "ERROR: built $MODE frozen P03 code drift: $f" >&2;exit 2;
  }
done
for f in p03_mmio.h p03_runtime.h p03_hw_adapter.h \
         p03_hw_runtime_bridge.h p03_hw_xilinx_io.h;do
  cmp -s "$BUILD/source/$f" "software/p03/include/$f" || {
    echo "ERROR: built $MODE frozen P03 header drift: $f" >&2;exit 2;
  }
done

# Authenticate bytes, original 1024 TRAIN identities, ledger and selected frame.
PYTHONPATH="$V3/src" python scripts/p07_a4_2_check.py --stage-dir "$STAGE"
PYTHONPATH="$V3/src" python - "$STAGE" <<'PY'
from pathlib import Path
import json
import sys
from scripts.p07_a4_2_verify import validate_staging
from loihi_twin_v2.p06_a3_data import load_train_validation
from loihi_twin_v2.p06_a3_training import load_candidate
from loihi_twin_v2.p07_a4_validation import select_validation_prefix, validate_ledger
stage=Path(sys.argv[1])
meta,stream=validate_staging(stage)
if (meta["scope"]!="TRAIN_DERIVED_VALIDATION_FIRST_1024" or
    meta["frame_count"]!=1024 or stream.image_count!=1024 or
    stream.trace_index!=1023 or meta["trace_index"]!=1023 or
    meta["official_mnist_test"]!="SEALED"):
    raise SystemExit("A3.2.2 refuses noncanonical 1024 TRAIN stage/trace")
split=load_train_validation(Path("data/mnist_raw"))
_,candidate=load_candidate(Path("artifacts/p06_a3_candidate_seed20261013"))
if split.manifest!=candidate.get("source_dataset"):
    raise SystemExit("A3.2.2 original TRAIN source split/model mismatch")
frames=select_validation_prefix(split,1024)
ledger=json.loads((stage/"p07_a4_2a_validation_labels_HOST_ONLY.json").read_text())
validate_ledger(ledger,frames,stream.images)
print("P08_A3_2_2_ORIGINAL_TRAIN_FIRST1024_PREFLIGHT_PASS=1")
PY
# Must use memory segment size, not file size, to protect reserved DDR.
readelf -lW "$ELF" | python -c '
import sys
loads=[f for line in sys.stdin if (f:=line.split()) and f[0]=="LOAD"]
if not loads: raise SystemExit("A3.2.2 expected ELF LOAD segments")
for f in loads:
    start=int(f[2],16); stop=start+int(f[5],16)
    if start < 0x44000000 and stop > 0x40000000:
        raise SystemExit("A3.2.2 physical ELF overlaps reserved 64MiB DDR")
print("P08_A3_2_2_ELF_DDR_ISOLATION_PASS=1")
'
if [[ "${P08_A3_2_PREFLIGHT_ONLY:-}" == YES ]];then
  echo "P08_A3_2_2_OFFLINE_PREFLIGHT_PASS=1"
  echo "P08_A3_2_2_PHYSICAL_VARIANT=$MODE"
  echo "P08_A3_2_2_KV260_LATENCY=NOT_RUN"
  exit 0
fi

# FIRST destructive hardware call BELOW. Both consent and all SHA/data gates passed.
mkdir -p "$RUN/readback"
record_exit() {
  local code=$?
  printf 'script_exit_status=%s\n' "$code" > "$RUN/attempt_exit_status.txt"
  {
    for f in "$RUN"/p07_a4_journal_1m.bin \
             "$RUN"/p07_a4_trace_64k.bin \
             "$RUN"/p08_a2_1_images_1m.bin \
             "$RUN"/p08_a2_2_ticks_3m.bin \
             "$RUN"/p08_a3_2_single_verified.json;do
      [[ ! -f "$f" ]] || sha256sum "$f"
    done
  } > "$RUN/available_output_sha256.txt"
}
trap record_exit EXIT
python - "$RUN/trace_zero_64k.bin" <<'PY'
from pathlib import Path
import sys
with Path(sys.argv[1]).open("xb") as out:out.write(bytes(65536))
PY
{
  echo "phase=P08-A3.2.2 one 1024-frame TRAIN-validation KV260 capture"
  echo "status=PHYSICAL_NOT_YET_RUN"
  echo "git_commit=$(git rev-parse HEAD)"
  echo "firmware_variant=$MODE"
  echo "candidate_elf_sha256=$ACTUAL_ELF_SHA"
  echo "scope=TRAIN_DERIVED_VALIDATION_FIRST_1024"
  echo "trace_frame=1023"
  echo "official_TEST_population=NOT_USED"
  echo "power_energy=DEFERRED"
  sha256sum "$XSA" "$BIT" "$LTX" "$ELF" "$MASTER" \
      "$STAGE/p07_a4_descriptor_256.bin" \
      "$STAGE/p07_a4_mapping_1568.bin" \
      "$STAGE/p07_a4_pixels_raw.bin" \
      "$STAGE/p07_a4_journal_initial_1m.bin" \
      "$STAGE/p07_a4_2a_stage_manifest.json" \
      "$STAGE/p07_a4_2a_validation_labels_HOST_ONLY.json"
} > "$RUN/physical_identity.txt"

echo "DANGEROUS $MODE: PROGRAMMING P03.2c + WRITING 0x40000000..0x43FFFFFF DDR."
echo "Never run while KV260 Linux owns the memory. Reboot after EVERY attempt."
xsdb vivado/p03_2c_xsdb_ps_axi_width_diag.tcl "$XSDB_URL" \
    2>&1 | tee "$RUN/ps_width.log"
grep -Fxq 'P03_2C_PS_FPD_HPM0_WIDTH_BITS=128' "$RUN/ps_width.log"
xsdb vivado/p07_a4_xsdb_prepare.tcl \
    "$MASTER" "$STAGE" "$RUN/trace_zero_64k.bin" \
    "$RUN/readback" "$XSDB_URL" 2>&1 | tee "$RUN/provision.log"
grep -Fxq 'P07_A4_2C_XSDB_PROVISION_PASS=1' "$RUN/provision.log"
vivado -mode batch -source vivado/p03_2c_program_bitstream.tcl \
    -tclargs "$BIT" "$LTX" "$HW_URL" 2>&1 | tee "$RUN/program.log"
grep -Fq 'PASS: P03.2c accepted PS-MMIO bitstream programmed and PL reset released' \
    "$RUN/program.log"

export P08_A2_CONFIRM_KV260_JTAG_ONLY=YES
export P08_A2_CONFIRM_VALIDATION_ONLY=YES
if [[ "$MODE" == A2_1 ]];then
  xsdb "$XSDB_SCRIPT" \
    "$ELF" "$RUN/p07_a4_journal_1m.bin" "$RUN/p07_a4_trace_64k.bin" \
    "$RUN/p08_a2_1_images_1m.bin" "$XSDB_URL" "$TIMEOUT" \
    2>&1 | tee "$RUN/a53_run.log"
else
  xsdb "$XSDB_SCRIPT" \
    "$ELF" "$RUN/p07_a4_journal_1m.bin" "$RUN/p07_a4_trace_64k.bin" \
    "$RUN/p08_a2_1_images_1m.bin" "$RUN/p08_a2_2_ticks_3m.bin" \
    "$XSDB_URL" "$TIMEOUT" 2>&1 | tee "$RUN/a53_run.log"
fi
grep -Fxq "$SUCCESS_STATUS" "$RUN/a53_run.log" || {
  echo "ERROR: $MODE terminal status failed; preserve raw files" >&2;exit 4;
}

# REAL independent original P07 packed-neural oracle + timing sidecar gate.
PYTHONPATH="$V3/src" python scripts/p08_a3_2_single_check.py \
  --stage-dir "$STAGE" --run-dir "$RUN" --variant "$MODE" \
  --elf "$ELF" --report "$RUN/p08_a3_2_single_verified.json" \
  2>&1 | tee "$RUN/verify.log"
grep -Fxq 'P08_A3_2_2_SINGLE_1024_PHYSICAL_CAPTURE_PASS=1' "$RUN/verify.log" || {
  echo "ERROR: real P07 original oracle/per-tick timing verification failed" >&2;exit 5;
}
files=("$RUN/p07_a4_journal_1m.bin" "$RUN/p07_a4_trace_64k.bin"
       "$RUN/p08_a2_1_images_1m.bin" "$RUN/p08_a3_2_single_verified.json")
if [[ "$MODE" == A2_2 ]];then
  files+=("$RUN/p08_a2_2_ticks_3m.bin")
fi
sha256sum "${files[@]}" > "$RUN/physical_output_sha256.txt"
echo "P08_A3_2_2_PHYSICAL_VARIANT=$MODE"
echo "P08_A3_2_2_PHYSICAL_EVIDENCE_DIR=$RUN"
echo "P08_A3_2_2_SINGLE_1024_FULL_PHYSICAL_GATE_PASS=1"
echo "P08_A3_2_2_PAIRED_BASELINE=NOT_YET_RUN"
echo "REBOOT KV260; NEVER RESUME HALTED LINUX."
