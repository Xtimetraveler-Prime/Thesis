from __future__ import annotations

import argparse
from pathlib import Path

from mnist_app.fpga_conformance import (
    build_single_image_cases,
    write_conformance_bundle,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate the two frozen MNIST-07 single-image FPGA input cases and "
            "independent Python-golden traces."
        )
    )
    parser.add_argument(
        "--frozen-root",
        type=Path,
        default=Path("applications/mnist_baseline/frozen/mnist-v1"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("applications/mnist_baseline/build/mnist-07/golden"),
    )
    parser.add_argument(
        "--sv-output",
        type=Path,
        default=Path(
            "applications/mnist_baseline/build/mnist-07/generated_m12_3_multitick_cases.svh"
        ),
    )
    args = parser.parse_args()

    cases = build_single_image_cases(args.frozen_root)
    manifest = write_conformance_bundle(cases, args.output_dir, args.sv_output)
    for case in cases:
        max_events = max(len(events) for events in case.external_schedule)
        print(
            f"case={case.case_id} profile={case.profile} "
            f"index={case.mnist_test_index} label={case.label} "
            f"prediction={case.expected_prediction} neurons={case.neuron_count} "
            f"axons={case.axon_count} synapses={case.synapse_count} "
            f"ticks={case.tick_count} max_events/tick={max_events}"
        )
    print(f"manifest: {manifest}")
    print(f"FPGA input include: {args.sv_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
