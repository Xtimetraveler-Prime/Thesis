#!/usr/bin/env python3
"""M08.4 ORIGINAL hardware input-only page fixtures and independent oracle.

Writes exactly seven host-input page files (edges + six distinct neural
contexts) plus one comparison-only 512-word oracle to NEW owner evidence.
The oracle is NEVER loaded into the fabric as compute-facing neural state.
17 raw input events are HOST-COALESCED, not fabric FIFO in this image.
No JTAG, native Vivado, PS writes, DDR, or hardware actions.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import m08_paged_m06_lif_fixture as fixture

class Reject(ValueError):
    pass

def generate(outdir: Path) -> dict:
    root = Path.home() / "Thesis_Evidence/M08"
    if (outdir.parent != root or not outdir.name.startswith("m08_paged_m06_lif_HW_")
        or not outdir.is_dir() or outdir.is_symlink()):
        raise Reject("must use NEW original owner M08.4 hardware evidence directory")
    # Source input parameters and independent M02/M03 output fixture remain separate.
    _,net,events,external,volts,masks,syn=fixture.source()
    if len(events)!=17 or len(net.neurons)!=32 or len(net.synapses)!=5:
        raise Reject("original independent M06 geometry drift")
    work = [("10_edge_config_input.hex", fixture.edge_words())]
    work += [(f"11_neural_page_{i}_input.hex",fixture.neural_words(i))
             for i in range(6)]
    work += [("20_independent_512_oracle_ONLY.hex",fixture.golden_words())]
    if len(work[-1][1]) != 512:
        raise Reject("wrong independent comparison geometry")
    for name,words in work:
        fixture.write_hex(outdir / name,words)
    return {
        "status":"M08_4_OWNER_HOST_PAGES_ONLY_GOLDEN_NEVER_COMPUTE_INPUT",
        "input_host_coalesced_raw_events":17,
        "logical_neuron_pages":6,
        "physical_resident_page_banks":1,
        "neurons_per_page":[6,6,6,6,6,2],
        "oracle_comparisons":512,
        "host_input_current_comparisons":128,
        "pl_computed_voltage_spike_recurrent_comparisons":384,
        "page_input_sha256":{
            name:sha256((outdir/name).read_bytes()).hexdigest()
            for name,_ in work[:-1]
        },
        "comparison_only_oracle_sha256":
            sha256((outdir/work[-1][0]).read_bytes()).hexdigest(),
        "hardware_test_executed":False,
    }

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out-dir", type=Path, required=True)
    args=p.parse_args()
    try:
        print(json.dumps(generate(args.out_dir),indent=2,sort_keys=True))
        return 0
    except (Reject,fixture.Reject,ValueError,OSError) as exc:
        print("M08_4_OWNER_VECTOR_PREP_REJECTED: "+str(exc),file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
