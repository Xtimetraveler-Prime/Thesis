#!/usr/bin/env python3
from __future__ import annotations

import argparse

from mnist_app.dataset import load_mnist
from mnist_app.encoding import center_crop_20x20, count_events, encode_event_schedule, quantize_spike_levels


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect one deterministic MNIST spike encoding")
    parser.add_argument("--index", type=int, default=0)
    args = parser.parse_args()

    dataset = load_mnist()
    image = dataset.x_test[args.index]
    label = int(dataset.y_test[args.index])
    crop = center_crop_20x20(image)[0]
    levels = quantize_spike_levels(image)[0].reshape(20, 20)
    schedule = encode_event_schedule(image)

    print(f"test index: {args.index}")
    print(f"label:      {label}")
    print(f"crop shape: {crop.shape}")
    print(f"events:     {count_events(schedule)}")
    print(f"max/tick:   {max(len(row) for row in schedule)}")
    print("\nquantized spike levels (20x20):")
    print(levels)
    print("\nper-tick axon events:")
    for tick, events in enumerate(schedule):
        print(f"tick {tick:02d} ({len(events):3d} events): {events}")


if __name__ == "__main__":
    main()
