#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CATALYST="${1:-$ROOT/build/m13_1/catalyst-n1}"
OUT="${2:-$ROOT/build/m13_5/catalyst-k26-vivado}"
NATIVE_BUILD="$CATALYST/fpga/kria/build"

command -v python3 >/dev/null
command -v vivado >/dev/null

# Remove only the known generated upstream build directory before provenance
# validation so an interrupted prior vendor run cannot poison a clean rerun.
rm -rf "$NATIVE_BUILD"

cd "$ROOT"
PYTHONPATH=src python3 examples/validate_m13_5_hardware_manifest.py --catalyst-checkout "$CATALYST"

vivado_text="$(vivado -version 2>&1)"
VIVADO_VERSION="$(PYTHONPATH=src python3 -c 'import sys; from neuromorphic_twin.m13_hardware_audit import require_vivado_2025_2; print(require_vivado_2025_2(sys.stdin.read()))' <<<"$vivado_text")"

rm -rf "$OUT"
mkdir -p "$OUT/native_reports"
printf '%s\n' "$vivado_text" > "$OUT/vivado-version.txt"
git -C "$CATALYST" rev-parse HEAD > "$OUT/catalyst-head.txt"

cat > "$OUT/commands.txt" <<EOF
vivado -mode batch -source fpga/kria/build_kria.tcl -tclargs synth_only
vivado -mode batch -source fpga/kria/run_impl.tcl
EOF

(
  cd "$CATALYST"
  vivado -mode batch -source fpga/kria/build_kria.tcl -tclargs synth_only
) 2>&1 | tee "$OUT/synthesis.log"

synth_dcp="$NATIVE_BUILD/catalyst_kria_n1.runs/synth_1/kria_neuromorphic.dcp"
if [[ ! -f "$synth_dcp" ]]; then
  echo "ERROR: Catalyst synth_only flow did not produce expected checkpoint: $synth_dcp" >&2
  exit 3
fi

(
  cd "$CATALYST"
  vivado -mode batch -source fpga/kria/run_impl.tcl
) 2>&1 | tee "$OUT/implementation.log"

required=(
  "$NATIVE_BUILD/synth_utilization.rpt"
  "$NATIVE_BUILD/synth_utilization_hier.rpt"
  "$NATIVE_BUILD/synth_timing.rpt"
  "$NATIVE_BUILD/impl_results/kria_n1_impl.dcp"
  "$NATIVE_BUILD/impl_results/timing_summary.rpt"
  "$NATIVE_BUILD/impl_results/timing_paths.rpt"
  "$NATIVE_BUILD/impl_results/utilization.rpt"
  "$NATIVE_BUILD/impl_results/utilization_hier.rpt"
  "$NATIVE_BUILD/impl_results/power.rpt"
  "$NATIVE_BUILD/impl_results/clock_utilization.rpt"
  "$NATIVE_BUILD/impl_results/design_analysis.rpt"
)
for path in "${required[@]}"; do
  if [[ ! -f "$path" ]]; then
    echo "ERROR: Catalyst Vivado flow missing expected artifact: $path" >&2
    exit 4
  fi
done

cp "$NATIVE_BUILD/synth_utilization.rpt" "$OUT/native_reports/synth_utilization.rpt"
cp "$NATIVE_BUILD/synth_utilization_hier.rpt" "$OUT/native_reports/synth_utilization_hier.rpt"
cp "$NATIVE_BUILD/synth_timing.rpt" "$OUT/native_reports/synth_timing.rpt"
cp "$NATIVE_BUILD/impl_results/timing_summary.rpt" "$OUT/native_reports/timing_summary.rpt"
cp "$NATIVE_BUILD/impl_results/timing_paths.rpt" "$OUT/native_reports/timing_paths.rpt"
cp "$NATIVE_BUILD/impl_results/utilization.rpt" "$OUT/native_reports/utilization.rpt"
cp "$NATIVE_BUILD/impl_results/utilization_hier.rpt" "$OUT/native_reports/utilization_hier.rpt"
cp "$NATIVE_BUILD/impl_results/power.rpt" "$OUT/native_reports/power.rpt"
cp "$NATIVE_BUILD/impl_results/clock_utilization.rpt" "$OUT/native_reports/clock_utilization.rpt"
cp "$NATIVE_BUILD/impl_results/design_analysis.rpt" "$OUT/native_reports/design_analysis.rpt"
cp "$NATIVE_BUILD/impl_results/kria_n1_impl.dcp" "$OUT/native_reports/kria_n1_impl.dcp"

PYTHONPATH=src python3 examples/parse_m13_5_catalyst_reports.py \
  --utilization "$OUT/native_reports/utilization.rpt" \
  --timing "$OUT/native_reports/timing_summary.rpt" \
  --vivado-version "$VIVADO_VERSION" \
  --output "$OUT/catalyst-hardware-result.json"

PYTHONPATH=src python3 examples/render_m13_5_hardware_comparison.py \
  --catalyst-result "$OUT/catalyst-hardware-result.json" \
  --output-json "$OUT/hardware-comparison.json" \
  --output-md "$OUT/hardware-comparison.md"

PYTHONPATH=src python3 - "$OUT" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

out = Path(sys.argv[1])
files = {}
for path in sorted(p for p in out.rglob('*') if p.is_file()):
    if path.name == 'evidence-manifest.json':
        continue
    files[str(path.relative_to(out))] = hashlib.sha256(path.read_bytes()).hexdigest()
result = json.loads((out / 'catalyst-hardware-result.json').read_text())
comparison = json.loads((out / 'hardware-comparison.json').read_text())
manifest = {
    'schema': 'neuromorphic-twin-m13-hardware-evidence-manifest-v1',
    'catalyst_commit': result['catalyst_commit'],
    'vivado': result['vivado'],
    'target_part': result['target_part'],
    'timing_closed': result['timing_closed'],
    'strongest_catalyst_boundary': comparison['strongest_catalyst_boundary'],
    'latency_throughput_comparison': comparison['latency_throughput']['comparison_status'],
    'power_energy_comparison': comparison['power_energy']['comparison_status'],
    'physical_catalyst_execution': comparison['physical_execution']['catalyst'],
    'files_sha256': files,
}
(out / 'evidence-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
if not result['timing_closed']:
    raise SystemExit(
        f"Catalyst routed implementation completed but 100 MHz timing did not close: {result['timing']}"
    )
if comparison['latency_throughput']['comparison_status'] != 'withheld':
    raise SystemExit('M13.5 fairness violation: latency/throughput comparison was not withheld')
if comparison['power_energy']['comparison_status'] != 'withheld':
    raise SystemExit('M13.5 fairness violation: power/energy comparison was not withheld')
if comparison['physical_execution']['catalyst'] is not False:
    raise SystemExit('M13.5 fairness violation: routed Catalyst evidence was labeled physical')
PY

# The Vivado flow may create ignored/untracked products, but tracked Catalyst source must remain byte-identical.
git -C "$CATALYST" diff --quiet --
git -C "$CATALYST" diff --cached --quiet --

# Preserve evidence in the thesis build tree, then restore the pinned Catalyst checkout to pre-run generated state.
rm -rf "$NATIVE_BUILD"

printf 'M13.5 Catalyst K26 Vivado PASS: commit=%s vivado=%s part=%s clock=100MHz output=%s\n' \
  "$(cut -c1-12 "$OUT/catalyst-head.txt")" "$VIVADO_VERSION" "xczu5ev-sfvc784-2-i" "$OUT"
