"""Deterministic MNIST-to-axon event encoding.

The FPGA baseline consumes integer axon IDs, not floating-point pixels. The
encoder uses the original uint8 MNIST image, center-crops 28x28 to 20x20,
quantizes each pixel to an integer spike count in 0..T, and distributes those
spikes deterministically across T algorithmic ticks.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from .config import (
    CROP_BORDER,
    INPUT_AXONS,
    INPUT_HEIGHT,
    INPUT_WIDTH,
    PRESENTATION_TICKS,
    SOURCE_HEIGHT,
    SOURCE_WIDTH,
)


def _validate_images(images: np.ndarray) -> np.ndarray:
    array = np.asarray(images)
    if array.ndim == 2:
        array = array[np.newaxis, ...]
    if array.ndim != 3 or array.shape[1:] != (SOURCE_HEIGHT, SOURCE_WIDTH):
        raise ValueError(
            f"MNIST images must have shape (28, 28) or (N, 28, 28); got {array.shape}"
        )
    if not np.issubdtype(array.dtype, np.number):
        raise TypeError("MNIST images must contain numeric pixel values")
    if np.any(array < 0) or np.any(array > 255):
        raise ValueError("MNIST pixel values must be in 0..255")
    return array.astype(np.uint8, copy=False)


def center_crop_20x20(images: np.ndarray) -> np.ndarray:
    """Return the frozen 20x20 center crop while preserving uint8 pixels."""

    array = _validate_images(images)
    stop = SOURCE_HEIGHT - CROP_BORDER
    cropped = array[:, CROP_BORDER:stop, CROP_BORDER:stop]
    if cropped.shape[1:] != (INPUT_HEIGHT, INPUT_WIDTH):
        raise AssertionError("internal crop configuration is inconsistent")
    return cropped


def quantize_spike_levels(
    images: np.ndarray,
    *,
    presentation_ticks: int = PRESENTATION_TICKS,
) -> np.ndarray:
    """Quantize each cropped pixel to an exact integer spike count in 0..T."""

    if isinstance(presentation_ticks, bool) or not isinstance(presentation_ticks, int):
        raise TypeError("presentation_ticks must be an int")
    if presentation_ticks <= 0:
        raise ValueError("presentation_ticks must be positive")

    cropped = center_crop_20x20(images).astype(np.int64)
    levels = (cropped * presentation_ticks + 127) // 255
    return levels.reshape(cropped.shape[0], INPUT_AXONS).astype(np.int16)


def encode_binary_spikes(
    images: np.ndarray,
    *,
    presentation_ticks: int = PRESENTATION_TICKS,
) -> np.ndarray:
    """Encode images as a dense boolean tensor ``(N, T, 400)``.

    A pixel with level ``k`` emits exactly ``k`` spikes, spread as evenly as
    possible over the presentation window. Every axon can appear at most once
    per tick, so one image can generate no more than 400 external events on any
    tick.
    """

    levels = quantize_spike_levels(images, presentation_ticks=presentation_ticks)
    ticks = np.arange(presentation_ticks, dtype=np.int64)
    before = (ticks[None, :, None] * levels[:, None, :]) // presentation_ticks
    after = ((ticks[None, :, None] + 1) * levels[:, None, :]) // presentation_ticks
    return after > before


def encode_event_schedule(
    image: np.ndarray,
    *,
    presentation_ticks: int = PRESENTATION_TICKS,
) -> tuple[tuple[int, ...], ...]:
    """Encode one image as the exact per-tick axon-ID sequence for the core."""

    spikes = encode_binary_spikes(image, presentation_ticks=presentation_ticks)
    if spikes.shape[0] != 1:
        raise ValueError("encode_event_schedule accepts exactly one image")
    return tuple(
        tuple(int(axon) for axon in np.flatnonzero(spikes[0, tick]))
        for tick in range(presentation_ticks)
    )


def count_events(schedule: Sequence[Sequence[int]]) -> int:
    """Return the total number of external events in a schedule."""

    return sum(len(tick) for tick in schedule)
