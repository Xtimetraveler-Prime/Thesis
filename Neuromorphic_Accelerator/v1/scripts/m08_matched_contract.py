#!/usr/bin/env python3
"""Emit the M08.5 *source-only* six-cell comparison/provenance contract.

No JTAG, MMIO, Vivado, physical evidence read, DDR allocation or write.
Re-derives the frozen M06 G3.3 neural workload via the M02/M03 references.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import m08_paged_m06_lif_fixture as original
from neuromorphic_accelerator_v1.m08_matched_experiments import (
    build_contract, check_contract, witness_from_original,
)

REFERENCES = (
    "src/neuromorphic_accelerator_v1/m02_dense_reference.py",
    "src/neuromorphic_accelerator_v1/m02_event_reference.py",
    "src/neuromorphic_accelerator_v1/m03_sparse_reference.py",
    "scripts/m06_g3_3_m02_m03_owner_vectors.py",
    "scripts/m08_d3d2c_m06_vectors.py",
    "scripts/m08_paged_m06_lif_fixture.py",
)


def make_report() -> dict:
    _, net, events, _, _, _, _ = original.source()
    if (len(net.neurons) != 32 or len(net.synapses) != 5
            or len(events) != 17 or net.state_bits != 16
            or (net.decay_num, net.decay_den) != (3, 4)):
        raise ValueError("original M02/M03 signed16 fixture changed")
    pages = tuple(original.neural_words(i) for i in range(original.PAGES))
    for i, words in enumerate(pages):
        original.audit_page(words, i, 0, post_compute=False)
    source_ids = {name: sha256((ROOT / name).read_bytes()).hexdigest()
                  for name in REFERENCES}
    witness = witness_from_original(
        neuron_pages=pages,
        edge_page=original.edge_words(),
        event_records=tuple((ev.tick, ev.neuron, ev.current) for ev in events),
        golden_words=original.golden_words(),
        reference_source_sha256=source_ids,
    )
    report = build_contract(witness)
    check_contract(report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-only", action="store_true", required=True)
    parser.add_argument("--output", type=Path,
                        help="optional NEW JSON file in an existing directory (never overwrite)")
    args = parser.parse_args(argv)
    report = make_report()
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        if (not args.output.parent.is_dir() or args.output.is_symlink()
                or args.output.exists()):
            parser.error("output must be a fresh non-symlink file in an existing directory")
        with args.output.open("x", encoding="utf-8") as handle:
            handle.write(payload)
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
