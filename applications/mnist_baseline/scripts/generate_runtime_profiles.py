from __future__ import annotations

import argparse
from pathlib import Path

from mnist_app.runtime_static import (
    load_runtime_static_profiles,
    write_runtime_static_include,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate the two frozen static profile images for MNIST-09 runtime."
    )
    parser.add_argument(
        "--frozen-root",
        type=Path,
        default=Path("applications/mnist_baseline/frozen/mnist-v1"),
    )
    parser.add_argument("--sv-output", type=Path, required=True)
    args = parser.parse_args()

    profiles = load_runtime_static_profiles(args.frozen_root)
    output = write_runtime_static_include(profiles, args.sv_output)
    for profile in profiles:
        print(
            f"profile={profile.profile} id={profile.profile_id} "
            f"neurons={profile.neuron_count} axons={profile.axon_count} "
            f"synapses={profile.synapse_count} formats={profile.format_count}"
        )
    print(f"runtime static include: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
