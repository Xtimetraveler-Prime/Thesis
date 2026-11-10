#!/usr/bin/env python3
"""Read-only G3 measured-pin matrix: generated HLS -> original AMD S00/S03.

The output is an engineering INPUT CONTRACT, not an adapter, a Vivado project
or proof of connected RTL. It independently reads real synthesized HLS RTL
AND immutable original D3 vendor-wrapper/header metadata.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from m06_g3_original_link_inputs import verify as ready
from m06_paged_hls_port_audit import TOP, parse_top
from m06_generate_original_mem_sc_bfm import original_ports, required_ports, READ, WRITE

CHANNELS = {
    "read": ("gmem_read", "S00", READ, ("AR", "R")),
    "write": ("gmem_write", "S03", WRITE, ("AW", "W", "B")),
}
NEEDED = {
    "m_axi_gmem_read_ARADDR":("output",64),
    "m_axi_gmem_read_ARVALID":("output",1),
    "m_axi_gmem_read_ARREADY":("input",1),
    "m_axi_gmem_read_RDATA":("input",32),
    "m_axi_gmem_read_RVALID":("input",1),
    "m_axi_gmem_read_RREADY":("output",1),
    "m_axi_gmem_write_AWADDR":("output",64),
    "m_axi_gmem_write_AWVALID":("output",1),
    "m_axi_gmem_write_AWREADY":("input",1),
    "m_axi_gmem_write_WDATA":("output",32),
    "m_axi_gmem_write_WSTRB":("output",4),
    "m_axi_gmem_write_WVALID":("output",1),
    "m_axi_gmem_write_WREADY":("input",1),
    "m_axi_gmem_write_BRESP":("input",2),
    "m_axi_gmem_write_BVALID":("input",1),
    "m_axi_gmem_write_BREADY":("output",1),
}


def matrix(hls: dict[str,tuple[str,int]],
           original: dict[str,tuple[str,int]]) -> dict:
    if original != required_ports():
        raise ValueError("original 96-pin vendor ABI mismatch")
    for key, expected in NEEDED.items():
        if hls.get(key) != expected:
            raise ValueError("measured HLS AXI role/width incompatible: "+key)
    results=[]
    for role,(hls_name,si,fields,channel_names) in CHANNELS.items():
        hp="m_axi_"+hls_name+"_"
        vp=si+"_AXI_"
        # Inventory the real HLS channel pins, including optional ID, USER,
        # QOS, CACHE, etc. Do not silently terminate a pin by inventing it.
        hls_channels={key[len(hp):]:(direction,width)
                      for key,(direction,width) in hls.items() if key.startswith(hp)}
        vendor_channels={key[len(vp):]:(direction,width)
                         for key,(direction,width) in original.items() if key.startswith(vp)}
        if not hls_channels or not vendor_channels:
            raise ValueError("missing original/HLS sideband interface")
        entries=[]
        for token in sorted(set(hls_channels)|{name.upper() for name in fields}):
            left=hls_channels.get(token)
            right=vendor_channels.get(token.lower())
            if left and right:
                # Master-output -> SmartConnect-input, or reverse handshake.
                if left[0] == right[0]:
                    raise ValueError("same-direction HLS/vendor AXI pins: "+token)
            entries.append({
                "signal": token,
                "hls_direction_width": list(left) if left else None,
                "original_direction_width": list(right) if right else None,
                "requires_adapter_or_explicit_termination":
                    left is None or right is None or left[1]!=right[1],
            })
        results.append({
            "role":role.upper(),
            "hls_bundle":hls_name,
            "original_si":si,
            "hls_data_width":32,
            "original_data_width":256,
            "hls_address_width":64,
            "original_address_width":32,
            "data_width_conversion":"MANDATORY_32_TO_256_VERIFIED_AMD_IP",
            "address_conversion":"MANDATORY_GUARDED_64_TO_32_BOUNDED_64KiB_OFFSET",
            "original_si_id_wires_present":any(
                key in vendor_channels for key in ("arid","awid","rid","bid")),
            "sideband_pin_matrix":entries,
        })
    return {
        "schema":"m06-generated-hls-to-original-amd-pin-matrix-v1",
        "status":"REAL_HEADER_ROLES_AND_WIDTHS_ONLY_NOT_BOUND",
        "original_vendor_ports":len(original),
        "generated_hls_ports":len(hls),
        "paths":results,
        "shared_canonical_memory_bytes":65536,
        "read_after_write_B_acknowledgement":"UNPROVEN",
        "axi_id_sideband_bridge":"MUST_BE_DEFINED_AND_XSIM_TESTED",
        "physical_base":"UNALLOCATED",
        "original_smartconnect_linked":False,
        "genuine_connected_RTL_XSim":False,
        "m06_complete":False,
    }


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hls-cosim",required=True,type=Path)
    ap.add_argument("--vendor-a-e",required=True,type=Path)
    ap.add_argument("--repo",required=True,type=Path)
    ap.add_argument("--d3",required=True,type=Path)
    ap.add_argument("--original-header-json",required=True,type=Path)
    ap.add_argument("--output",required=True,type=Path)
    a=ap.parse_args()
    try:
        if a.output.exists() or not a.output.parent.is_dir():
            raise ValueError("output must be a fresh filename")
        evidence=ready(a.hls_cosim,a.vendor_a_e,a.repo)
        rtl=(a.hls_cosim.resolve(strict=True)/"work/hls/syn/verilog"/(TOP+".v"))
        hls_pins=parse_top(rtl.read_text(errors="replace"))
        original_list=original_ports(a.d3.resolve(strict=True),
                                     json.loads(a.original_header_json.read_text()))
        vendor_pins={p["name"]:(p["direction"],p["packed_width"])
                     for p in original_list}
        report=matrix(hls_pins,vendor_pins)
        report["genuine_hls_top_sha256"]=evidence["hls_generated_top_sha256"]
        report["genuine_hls_cosim_commit"]=evidence["hls_commit"]
        report["genuine_stage_e_log_sha256"]=evidence["original_vendor_stage_e_sha256"]
        with a.output.open("x",encoding="utf8") as dst:
            json.dump(report,dst,indent=2,sort_keys=True)
            dst.write("\n")
    except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as error:
        print("M06 G3 exact HLS/vendor pin matrix REJECTED: "+str(error),
              file=sys.stderr)
        return 2
    print("M06 real generated-HLS/original-AMD port map MEASURED; 32:256 data, 64:32 address, ID+sideband adaptation UNCONNECTED")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
