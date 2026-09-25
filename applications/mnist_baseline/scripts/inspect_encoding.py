#!/usr/bin/env python3
from __future__ import annotations

import argparse

from mnist_app.config import PROFILES, get_profile
from mnist_app.dataset import load_mnist
from mnist_app.encoding import (
    count_events,
    encode_event_schedule,
    preprocess_images,
    quantize_spike_levels,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect one deterministic MNIST spike encoding"
    )
    parser.add_argument("--profile", choices=tuple(PROFILES), default="cropped-dense")
    parser.add_argument("--index", type=int, default=0)
    args = parser.parse_args()

    profile = get_profile(args.profile)
    dataset = load_mnist()
    image = dataset.x_test[args.index]
    label = int(dataset.y_test[args.index])
    selected = preprocess_images(image, profile=profile)[0]
    levels = quantize_spike_levels(image, profile=profile)[0].reshape(
        profile.input_height,
        profile.input_width,
    )
    schedule = encode_event_schedule(image, profile=profile)

    print(f"profile:    {profile.name}")
    print(f"test index: {args.index}")
    print(f"label:      {label}")
    print(f"input shape:{selected.shape}")
    print(f"input axons:{profile.input_axons}")
    print(f"events:     {count_events(schedule)}")
    print(f"max/tick:   {max(len(row) for row in schedule)}")
    print("\nquantized spike levels:")
    print(levels)
    print("\nper-tick axon events:")
    for tick, events in enumerate(schedule):
        print(f"tick {tick:02d} ({len(events):3d} events): {events}")


if __name__ == "__main__":
    main()
