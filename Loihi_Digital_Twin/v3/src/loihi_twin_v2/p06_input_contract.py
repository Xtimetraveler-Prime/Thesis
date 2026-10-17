"""P06-A2.2 fixed, label-free uint8 MNIST-to-event and spike-readout contract.

This is a project-defined encoder, not the source snnTorch tutorial's analog
input or a stochastic/Poisson rate encoder. Byte ordering is MNIST's 28x28
row-major order. No external RNG, MNIST labels, or P03 runtime are used.

The frozen-input *candidate* needs user native acceptance before P06-A2 closes.
"""

from __future__ import annotations

import hashlib
import struct
from collections.abc import Sequence

IMAGE_SIDE = 28
INPUT_CHANNELS = IMAGE_SIDE * IMAGE_SIDE
INPUT_TICKS = 25
DRAIN_TICKS = 1
TOTAL_TICKS = INPUT_TICKS + DRAIN_TICKS
HIDDEN_NEURONS = 32
OUTPUT_CLASSES = 10
EVENT_BANK_DEPTH = 4096
ENCODER_PROFILE = "p06-uint8-quota-phase17-v1"
READOUT_PROFILE = "p06-26tick-count-argmax-first-v1"


def _validated_pixels(image: Sequence[int] | bytes) -> tuple[int, ...]:
    if len(image) != INPUT_CHANNELS:
        raise ValueError("MNIST image must have exactly 784 row-major uint8 pixels")
    if any(type(value) is not int or not 0 <= value <= 255 for value in image):
        raise ValueError("MNIST image pixels must be integer uint8 values")
    return tuple(image)


def pixel_spikes(image: Sequence[int] | bytes, tick: int) -> tuple[int, ...]:
    """Emit ascending pixel indices (exactly one event per eligible channel).

    Per pixel p and phase s=(tick+17*pixel_index) mod 25, an event fires iff
    floor((s+1)*p/255) > floor(s*p/255). This emits exactly floor(25*p/255)
    events over 25 ticks, including p=0 -> 0 and p=255 -> 25.
    Tick 25 accepts no new external spikes; it drains hidden-route packets.
    """
    pixels = _validated_pixels(image)
    if type(tick) is not int or not 0 <= tick < TOTAL_TICKS:
        raise ValueError("inference tick must be integer in [0, 25]")
    if tick == INPUT_TICKS:
        return ()
    active = []
    for index, level in enumerate(pixels):
        phase = (tick + 17 * index) % INPUT_TICKS
        if ((phase + 1) * level) // 255 > (phase * level) // 255:
            active.append(index)
    if len(active) > EVENT_BANK_DEPTH:
        raise RuntimeError("external event bank capacity exceeded")
    return tuple(active)


def image_event_schedule(image: Sequence[int] | bytes) -> tuple[tuple[int, ...], ...]:
    """Return 26 immutable ordered event lists; last list is always empty."""
    pixels = _validated_pixels(image)
    return tuple(pixel_spikes(pixels, tick) for tick in range(TOTAL_TICKS))


def event_schedule_sha256(image: Sequence[int] | bytes) -> str:
    """Hash canonical event lists: 26 consecutive <H count, <H index*count.

    This serialization is a test/manifest fingerprint, NOT the P03 32-bit
    event-bank ABI or the A53 application's eventual deployment format.
    """
    hasher = hashlib.sha256()
    for active in image_event_schedule(image):
        hasher.update(struct.pack("<H", len(active)))
        for index in active:
            hasher.update(struct.pack("<H", index))
    return hasher.hexdigest()


def classify_spike_counts(counts: Sequence[int]) -> int:
    """Return lowest-index maximizer, including class 0 for ten zero counts."""
    if len(counts) != OUTPUT_CLASSES or any(type(n) is not int or n < 0 for n in counts):
        raise ValueError("readout requires exactly ten nonnegative integer counts")
    winner = 0
    for index in range(1, OUTPUT_CLASSES):
        if counts[index] > counts[winner]:
            winner = index
    return winner
