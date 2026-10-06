#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V3_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"

cd "$V3_DIR"

PYTHONPATH="$V3_DIR/src" python -m pytest     tests/test_p03_1_runtime_contract.py     tests/test_p03_2_mmio_contract.py     -q | tee /tmp/v3_p03_2_focused_pytest.log

if grep -Eq 'failed|error|ERROR|FAIL' /tmp/v3_p03_2_focused_pytest.log; then
    echo "ERROR: P03.2 focused Python gate failed." >&2
    exit 3
fi

bash "$V3_DIR/rtl/run_p03_ps_control_regs_sim.sh"
bash "$V3_DIR/rtl/run_p02_page_host_arbiter_held_request_sim.sh"
bash "$V3_DIR/rtl/run_p02_context_page_bank_walker_sim.sh"
bash "$V3_DIR/rtl/run_p02_axi128_burst_adapter_sim.sh"
bash "$V3_DIR/rtl/run_p02_ddr_backing_range_guard_sim.sh"

python - "$V3_DIR" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])
rtl = (root / "rtl/p03_ps_control_regs.v").read_text(encoding="utf-8")
doc = (root / "docs/P03_2_PS_MMIO_CONTROL.md").read_text(encoding="utf-8")
py = (root / "src/loihi_twin_v2/p03_mmio.py").read_text(encoding="utf-8")

rtl_tokens = (
    'XIL_INTERFACENAME S_AXI',
    'P03_MMIO_ID = 32\'h4C54_3302',
    'debug_req && debug_ack',
    'page_done_latched',
    'dispatch_done_latched',
)
for token in rtl_tokens:
    if token not in rtl:
        raise SystemExit(f"FAIL: P03.2 RTL contract missing {token!r}")

for token in (
    "0xA0000000",
    "M_AXI_HPM0_FPD",
    "S_AXI_HP0_FPD",
    "VIO must not remain connected as a competing",
):
    if token not in doc:
        raise SystemExit(f"FAIL: P03.2 document missing {token!r}")

for token in (
    "P03_MMIO_BASE = 0xA0000000",
    "REG_PAGE_CONFIG = 0x020",
    "REG_DISPATCH_CONFIG = 0x080",
    "REG_DEBUG_CONFIG = 0x100",
):
    if token not in py:
        raise SystemExit(f"FAIL: P03.2 software MMIO contract missing {token!r}")

vivado = (root / "vivado/create_p03_mmio_impl_project.tcl").read_text(
    encoding="utf-8"
)
required_vivado = (
    "CONFIG.PSU__USE__M_AXI_GP0 {1}",
    "CONFIG.PSU__MAXIGP0__DATA_WIDTH {32}",
    "M_AXI_HPM0_FPD",
    "p03_ps_control_regs_0/S_AXI",
    "0xA0000000",
    "0x00001000",
    "p03_ps_control_regs_0/page_start",
    "p03_ps_control_regs_0/dispatch_start",
    "p03_ps_control_regs_0/debug_req",
)
for token in required_vivado:
    if token not in vivado:
        raise SystemExit(f"FAIL: P03.2 Vivado integration missing {token!r}")

for forbidden in (
    "connect_pair vio_p08/probe_out0 p08_paged_dispatch_controller_0/dispatch_start",
    "connect_pair vio_p08/probe_out6 p02_page_host_arbiter_0/debug_req",
    "connect_pair vio_p02_page/probe_out0 p02_context_page_bank_walker_0/cmd_start",
):
    if forbidden in vivado:
        raise SystemExit(
            f"FAIL: P03.2 still has competing VIO command source {forbidden!r}"
        )

print("PASS: P03.2 MMIO contract static checks")
print("PASS: P03.2 HPM0/Vivado ownership static checks")
PY

bash -n "$V3_DIR/vivado/run_p03_mmio_impl.sh"

echo "PASS: P03.2 PS-visible MMIO preflight completed successfully."
