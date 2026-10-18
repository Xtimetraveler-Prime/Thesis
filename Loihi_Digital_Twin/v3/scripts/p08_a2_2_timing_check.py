#!/usr/bin/env python3
"""Per-tick P08-A2.2 host-only schema + A2.1 correlation check.

A passing parser is NOT a physical gate. Separate unmodified P07A4R01
journal + selected trace need the independent P03 packed replay verifier.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import statistics

from loihi_twin_v2.p08_a2_timing import parse_timing
from loihi_twin_v2.p08_a2_2_ticks import parse_ticks


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--images",type=Path,required=True,help="A2.1 1MiB image timing")
    p.add_argument("--ticks",type=Path,required=True,help="A2.2 3MiB tick timing")
    p.add_argument("--count",type=int,required=True,help="Original predeclared count <=1024")
    p.add_argument("--descriptor-crc32",type=lambda v:int(v,0),
                   help="Expected original stage descriptor CRC32, if available")
    p.add_argument("--report",type=Path,help="NEW JSON, refuse overwrite")
    args=p.parse_args()
    if args.report and args.report.exists():
        p.error("refusing to overwrite existing timing evidence")
    image=parse_timing(args.images.read_bytes(),expected_count=args.count)
    ticks=parse_ticks(args.ticks.read_bytes(),image,
                      expected_descriptor_crc32=args.descriptor_crc32)
    hz=ticks.hz
    fields={
        "encode": [x.source_ticks / hz for x in ticks.ticks],
        "event_bank_append": [x.bank_ticks / hz for x in ticks.ticks],
        "dispatch_mmio_poll": [x.dispatch_wrapper_ticks / hz for x in ticks.ticks],
        "trace_readback": [x.trace_ticks / hz for x in ticks.ticks],
        "packet_route": [x.route_ticks / hz for x in ticks.ticks],
        "barrier": [x.barrier_ticks / hz for x in ticks.ticks],
    }
    summary={
      "status":"NATIVE_SIDE_CAR_CROSSCHECK_ONLY_NO_PHYSICAL_ACCEPTANCE",
      "frames":ticks.count,
      "timesteps_per_frame":26,
      "records":len(ticks.ticks),
      "trace_index":ticks.trace_index,
      "a53_counter_hz":hz,
      "original_descriptor_crc32":f"0x{ticks.descriptor_crc32:08x}",
      "all_ticks_pl_dispatch_cycles_verified_against_A2_1":True,
      "domains":{"timing":"A53 CNTVCT_EL0","pl_dispatch_cycles":"FPGA separate uncalibrated clock"},
      "median_seconds_per_tick_by_step":{k:statistics.median(v) for k,v in fields.items()},
      "note":"Ordered timestamp differences include seven counter-read boundaries and callback overhead. Sum spans != uninstrumented inference latency.",
      "source_comparison":"A2.1 is separately instrumented; paired physical runs needed for profiler perturbation",
      "physical_numerical_parity":"NOT_RUN_BY_THIS_TOOL",
      "physical_latency_accepted":False,
    }
    rendered=json.dumps(summary,indent=2,sort_keys=True)+"\n"
    if args.report:
        with args.report.open("x") as f:f.write(rendered)
    print(rendered,end="")
    print("P08_A2_2_TICK_SCHEMA_CROSSCHECK_PASS=1")
    print("P08_A2_2_KV260_INFERENCE=NOT_VERIFIED_BY_THIS_TOOL")
    print("P08_A2_2_PHYSICAL_LATENCY_ACCEPTED=0")


if __name__=="__main__":
    main()
