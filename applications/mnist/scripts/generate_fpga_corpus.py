from __future__ import annotations

import argparse
from pathlib import Path

from mnist_app.fpga_corpus import (
    EXTERNAL_EVENT_WORD_BITS,
    VIVADO_MAX_VARIABLE_BITS,
    build_corpus_cases,
    write_corpus_bundle,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate the frozen 30-image x 2-profile MNIST-08 FPGA corpus."
    )
    parser.add_argument(
        "--frozen-root",
        type=Path,
        default=Path("applications/mnist/frozen/mnist-v1"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("applications/mnist/build/mnist-08/golden"),
    )
    parser.add_argument(
        "--sv-output",
        type=Path,
        default=Path("applications/mnist/build/mnist-08/generated_m12_3_multitick_cases.svh"),
    )
    args = parser.parse_args()

    cases = build_corpus_cases(args.frozen_root)
    manifest = write_corpus_bundle(cases, args.output_dir, args.sv_output)

    total_events = sum(len(events) for case in cases for events in case.external_schedule)
    print(
        f"MNIST-08 corpus generated: sources={len(cases) // 2} cases={len(cases)} "
        f"ticks={sum(case.tick_count for case in cases)} external_events={total_events}"
    )
    for profile in ("cropped-dense", "native-sparse"):
        group = [case for case in cases if case.profile == profile]
        profile_events = sum(
            len(events) for case in group for events in case.external_schedule
        )
        profile_bits = profile_events * EXTERNAL_EVENT_WORD_BITS
        print(
            f"profile={profile} cases={len(group)} synapses={group[0].synapse_count} "
            f"axons={group[0].axon_count} external_event_words={profile_events} "
            f"external_event_bits={profile_bits} vivado_variable_limit={VIVADO_MAX_VARIABLE_BITS}"
        )
    print(f"manifest: {manifest}")
    print(f"FPGA input include: {args.sv_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
