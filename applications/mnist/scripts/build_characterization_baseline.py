from __future__ import annotations

import argparse
from pathlib import Path

from mnist_app.characterization import write_characterization_baseline


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build MNIST-10 internal characterization baseline from frozen accepted evidence."
    )
    parser.add_argument(
        "--accepted-validation",
        type=Path,
        default=Path("applications/mnist/frozen/mnist-v1/accepted_software_validation.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("applications/mnist/build/mnist-10/characterization_baseline.json"),
    )
    parser.add_argument("--clock-hz", type=int, default=100_000_000)
    args = parser.parse_args()

    output = write_characterization_baseline(
        args.accepted_validation,
        args.output,
        clock_hz=args.clock_hz,
    )
    import json

    payload = json.loads(output.read_text(encoding="utf-8"))
    print(f"characterization baseline: {output}")
    for profile, record in payload["profiles"].items():
        workload = record["workload"]
        timing = record["architectural_timing_model"]
        memory = record["logical_static_deployment_memory"]
        print(
            f"{profile}: accuracy={record['accuracy']['golden']:.4f} "
            f"events/image={workload['mean_input_events_per_image']:.2f} "
            f"visits/image={workload['mean_synaptic_visits_per_image']:.2f} "
            f"spikes/image={workload['mean_output_spikes_per_image']:.2f} "
            f"modeled_cycles/image={timing['mean_cycles_per_image']:.2f} "
            f"modeled_latency_ms={timing['mean_latency_ms']:.6f} "
            f"logical_static_KiB={memory['kibibytes']:.3f}"
        )
    comparison = payload["comparison"]
    print(
        "native-vs-cropped: "
        f"accuracy_delta_pp={comparison['native_minus_cropped_accuracy_pp']:+.3f} "
        f"visit_ratio={comparison['native_to_cropped_synaptic_visit_ratio']:.4f} "
        f"modeled_cycle_ratio={comparison['native_to_cropped_modeled_cycle_ratio']:.4f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
