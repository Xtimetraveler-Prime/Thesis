#!/usr/bin/env bash
set -euo pipefail

EXPECTED_BIT_SHA="8b4d1d3996147e73bbe71ec2a5036f0a4d23efc5cc3fe3d25237f855acf72119"
EXPECTED_LTX_SHA="a745b96c24f4e01480d1d89d706e90c52c822b4a7fda7ea43d2ad794a0b86def"
EXPECTED_XSA_SHA="703fa7a44abc56e88e67e1d09424ac59ea96e53aac1708c2c7e6028dcb616f40"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V3_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPORT_DIR="$V3_DIR/vivado/build/p03_2_mmio_impl/reports"

cd "$V3_DIR"

PYTHONPATH="$V3_DIR/src" python -m pytest     tests/test_p03_2_mmio_contract.py     tests/test_p03_2c_smoke_contract.py     -q | tee /tmp/v3_p03_2c_focused_pytest.log

python -m py_compile     scripts/p03_2c_smoke_fixture.py     scripts/p03_2c_verify_mailbox.py     software/p03/build_p03_2c_smoke.py

bash -n scripts/build_p03_2c_smoke.sh
bash -n scripts/run_p03_2c_physical.sh

TMP_FIXTURE="$(mktemp -d)"
TMP_P02_FIXTURE="$(mktemp -d)"
trap 'rm -rf "$TMP_FIXTURE" "$TMP_P02_FIXTURE"' EXIT
PYTHONPATH="$V3_DIR/src" python scripts/p03_2c_smoke_fixture.py     --output-dir "$TMP_FIXTURE"     | tee /tmp/v3_p03_2c_fixture.log
PYTHONPATH="$V3_DIR/src" python scripts/p02_4b_ring_fixture.py generate     --output-dir "$TMP_P02_FIXTURE"     >/tmp/v3_p03_2c_p02_fixture.log

cmp "$TMP_FIXTURE/core0_initial.bin" "$TMP_P02_FIXTURE/core0_initial.bin"
echo "PASS: P03.2c core0 backing record is byte-identical to accepted P02.4b fixture."

python - "$V3_DIR" "$TMP_FIXTURE" <<'PY'
from pathlib import Path
import hashlib
import json
import sys

root = Path(sys.argv[1])
fixture = Path(sys.argv[2])

manifest = json.loads((fixture / "manifest.json").read_text(encoding="utf-8"))
record = (fixture / "core0_initial.bin").read_bytes()
header = (fixture / "p03_2c_fixture.h").read_text(encoding="utf-8")
app = (root / "software/p03/p03_2c_smoke.c").read_text(encoding="utf-8")
build_py = (root / "software/p03/build_p03_2c_smoke.py").read_text(
    encoding="utf-8"
)
build_sh = (root / "scripts/build_p03_2c_smoke.sh").read_text(
    encoding="utf-8"
)
program_tcl = (root / "vivado/p03_2c_program_bitstream.tcl").read_text(
    encoding="utf-8"
)
run_tcl = (root / "vivado/p03_2c_xsdb_run.tcl").read_text(encoding="utf-8")
prepare_tcl = (root / "vivado/p03_2c_xsdb_prepare.tcl").read_text(
    encoding="utf-8"
)

if len(record) != 0x80000:
    raise SystemExit("FAIL: P03.2c fixture record is not 512 KiB")
if hashlib.sha256(record).hexdigest() != manifest["record_sha256"]:
    raise SystemExit("FAIL: P03.2c fixture record SHA mismatch")
if manifest["record_base"] != "0x40000000":
    raise SystemExit("FAIL: P03.2c fixture record base drifted")
if manifest["mailbox_base"] != "0x43FF0000":
    raise SystemExit("FAIL: P03.2c mailbox base drifted")
if manifest["expected_page_bytes"] != 438272:
    raise SystemExit("FAIL: P03.2c page-byte contract drifted")
if manifest["expected_page_read_bursts"] != 1712:
    raise SystemExit("FAIL: P03.2c page-burst contract drifted")

for token in (
    "P03_SMOKE_RECORD_BASE",
    "P03_SMOKE_MAILBOX_BASE",
    "P03_SMOKE_EXPECT_CONFIG0",
    "P03_SMOKE_DISPATCH_METADATA",
):
    if token not in header:
        raise SystemExit(f"FAIL: P03.2c generated header missing {token}")

for token in (
    "P03_REG_ID",
    "P03_REG_PAGE_COMMAND",
    "P03_REG_DEBUG_COMMAND",
    "P03_REG_DISPATCH_COMMAND",
    "MAILBOX_PASS",
):
    if token not in app:
        raise SystemExit(f"FAIL: P03.2c A53 app missing {token}")

for token in (
    'os="standalone"',
    'cpu="psu_cortexa53_0"',
    'domain_name=domain_name',
    'no_boot_bsp=True',
):
    if token not in build_py:
        raise SystemExit(f"FAIL: P03.2c Vitis platform contract missing {token}")

for token in (
    "aarch64-none-elf-gcc",
    "P03_2C_XILINX_VITIS",
    "P03_2C_A53_GCC",
):
    if token not in build_sh:
        raise SystemExit(f"FAIL: P03.2c embedded-toolchain gate missing {token}")

# VIO may be used only for the pre-run reset request.
if "p03_probe $vio vio_output 1" not in program_tcl:
    raise SystemExit("FAIL: P03.2c reset-only VIO output is missing")
for forbidden in (
    "vio_output 0",
    "vio_output 2",
    "vio_output 3",
    "vio_output 4",
    "vio_output 5",
    "vio_output 6",
    "vio_output 7",
    "vio_output 8",
    "vio_output 9",
    "vio_output 10",
    "vio_output 11",
):
    if forbidden in program_tcl:
        raise SystemExit(f"FAIL: P03.2c programming Tcl drives {forbidden}")

if "dow $elf" not in run_tcl or "con" not in run_tcl:
    raise SystemExit("FAIL: P03.2c XSDB run flow does not launch A53 ELF")
if "dow -data $record $record_addr" not in prepare_tcl:
    raise SystemExit("FAIL: P03.2c physical fixture provisioning is missing")

print("PASS: P03.2c fixture/application/ownership static checks")
PY

for pair in     "$REPORT_DIR/p03_2_ps_mmio.bit:$EXPECTED_BIT_SHA"     "$REPORT_DIR/p03_2_ps_mmio.ltx:$EXPECTED_LTX_SHA"     "$REPORT_DIR/p03_2_ps_mmio.xsa:$EXPECTED_XSA_SHA"; do
    path="${pair%%:*}"
    expected="${pair#*:}"
    [[ -f "$path" ]] || {
        echo "ERROR: accepted P03.2b artifact missing: $path" >&2
        exit 3
    }
    actual="$(sha256sum "$path" | awk '{print $1}')"
    [[ "$actual" == "$expected" ]] || {
        echo "ERROR: accepted P03.2b artifact drifted: $path sha=$actual" >&2
        exit 3
    }
done

echo "PASS: P03.2c accepted P03.2b artifact fingerprints verified."
echo "PASS: P03.2c offline smoke preflight completed successfully."
