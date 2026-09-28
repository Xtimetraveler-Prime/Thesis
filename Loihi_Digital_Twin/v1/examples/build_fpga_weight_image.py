#!/usr/bin/env python3
"""Build a frozen FPGA weight-memory image from validated weight cases."""

from __future__ import annotations

import argparse
from pathlib import Path

from neuromorphic_twin import (
    Synapse,
    freeze_encoded_synapses,
    write_weight_storage_image,
)
from neuromorphic_twin.comparison import build_weight_conformance_cases


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Freeze repeated copies of the fifteen validated encoded-weight "
            "cases into profile-v1 FPGA memory files."
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("comparison_output/fpga_weights"),
        help="output directory for JSON and .mem files",
    )
    parser.add_argument(
        "--axon-rows",
        type=int,
        default=8,
        help="number of axon rows used to replicate the validated cases",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 1 <= args.axon_rows <= 65536:
        raise SystemExit("--axon-rows must be in 1..65536")

    cases = build_weight_conformance_cases()
    synapses: list[Synapse] = []
    for axon_id in range(args.axon_rows):
        for target_neuron, case in enumerate(cases):
            encoding = case.encoding
            synapses.append(
                Synapse.encoded(
                    axon_id=axon_id,
                    target_neuron=target_neuron,
                    mantissa=encoding.requested_mantissa,
                    weight_format=encoding.weight_format,
                )
            )

    storage = freeze_encoded_synapses(synapses)
    artifacts = write_weight_storage_image(storage, args.output)
    estimate = storage.estimate()

    print("Frozen FPGA weight storage v1")
    print(f"formats={storage.format_count}")
    print(f"synapses={storage.synapse_count}")
    print(f"axons={storage.axon_count}")
    print(f"shared_total_bits={estimate.shared_total_bits}")
    print(f"inline_total_bits={estimate.inline_total_bits}")
    print(f"saved_bits={estimate.saved_bits}")
    print(f"manifest={artifacts.manifest}")
    print(f"formats_mem={artifacts.formats}")
    print(f"synapses_mem={artifacts.synapses}")
    print(f"axon_rows_mem={artifacts.axon_rows}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
