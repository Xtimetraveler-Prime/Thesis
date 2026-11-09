#!/usr/bin/env python3
"""Strict, independent readback of a NEW genuine owner DMA HP0 offline trial."""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import sys
DDR_SLAVE = "/ps/SAXIGP2/HP0_DDR_LOW"
OCM_SLAVE = "/ps/SAXIGP2/HP0_LPS_OCM"
DMA = {
    "dma_neurons": "/dma_neurons/Data_MM2S",
    "dma_synapses": "/dma_synapses/Data_MM2S",
    "dma_external": "/dma_external/Data_MM2S",
    "dma_trace": "/dma_trace/Data_S2MM",
}
HEX = re.compile(r"0x[0-9A-Fa-f]+\Z")
MARKER = "M05_D3_DMA_HP0_OFFLINE_MAPPING_PASS|DDR_LOW_MAPPED=4|OCM_EXCLUDED=4|GENERATED_WIDTH_ADAPTER=UNPROVEN"

def check(report: str, validation: str, log: str) -> dict[str, int]:
    lines = report.strip().splitlines()
    if len(lines) != 14 or lines[:3] != [
        "META|scope|OFFLINE_VIVADO_DMA_HP0_DDR_LOW_MAPPING_OCM_EXCLUDED",
        "SLAVE|DDR_LOW|" + DDR_SLAVE, "SLAVE|OCM|" + OCM_SLAVE,
    ] or lines[-3:] != [
        "META|dma_address_width|32", "META|physical_ddr|NOT_AUTHORIZED",
        "META|generated_smartconnect_width_adapter|NOT_YET_PROVEN",
    ]:
        raise ValueError("original DMA HP0 evidence header/rows/footer invalid")
    for i, (name, space) in enumerate(DMA.items()):
        d = lines[3 + 2*i].split("|")
        o = lines[4 + 2*i].split("|")
        if (len(d) != 7 or d[:4] != ["DDR", name, DDR_SLAVE, space]
            or not d[4].startswith(space + "/") or len(d[4].split("/")) != 4
            or not HEX.fullmatch(d[5]) or not HEX.fullmatch(d[6])):
            raise ValueError(f"DDR master/slave/offset/range incorrect: {name}")
        base, size = int(d[5], 16), int(d[6], 16)
        if size <= 0 or base < 0 or base + size > 2**32:
            raise ValueError(f"DDR address cannot fit original 32-bit DMA: {name}")
        if (len(o) != 5 or o[:4] != ["OCM_EXCLUDED", name, OCM_SLAVE, space]
            or not o[4].startswith(space + "/") or len(o[4].split("/")) != 4
            or o[4] == d[4]):
            raise ValueError(f"OCM exclusion absent or wrong: {name}")
    if validation.strip() != "VALIDATION|PASS|FULL_BD_VALIDATE_FORCE":
        raise ValueError("full original Vivado validation is not PASS")
    if MARKER not in log:
        raise ValueError("genuine Vivado full mapping marker not present")
    if any("CRITICAL WARNING: [BD " + code + "]" in log for code in ("41-1356", "41-2909")):
        raise ValueError("original genuine Vivado still shows undefined DMA/SmartConnect memory")
    return {"dma_ddr_low_mapped": 4, "dma_ocm_excluded": 4,
            "physical_ddr": 0, "generated_width_adapter": 0}

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--memory-report", required=True, type=Path)
    p.add_argument("--validation", required=True, type=Path)
    p.add_argument("--vivado-log", required=True, type=Path)
    a = p.parse_args()
    try:
        outcome = check(a.memory_report.read_text(), a.validation.read_text(),
                        a.vivado_log.read_text())
    except (OSError, ValueError) as e:
        print(f"FAIL: independent M05.12d.3 DMA HP0 audit: {e}", file=sys.stderr)
        return 1
    print(f"PASS: M05.12d.3 four authentic DDR_LOW address mappings and four excluded OCM segments independently audited {outcome} (NO PHYSICAL DDR/WIDTH CONVERTER)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
