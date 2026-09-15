"""Deterministic MNIST-to-axon event encoding shared by both application profiles."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from .config import (
    DEFAULT_PROFILE,
    PRESENTATION_TICKS,
    SOURCE_HEIGHT,
    SOURCE_WIDTH,
    MnistProfile,
    get_profile,
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


def preprocess_images(
    images: np.ndarray,
    *,
    profile: str | MnistProfile = DEFAULT_PROFILE,
) -> np.ndarray:
    """Return native 28x28 images or the exact cropped-dense 20x20 view."""

    selected = get_profile(profile)
    array = _validate_images(images)
    if selected.crop_border is None:
        return array

    start = selected.crop_border
    stop_y = start + selected.input_height
    stop_x = start + selected.input_width
    result = array[:, start:stop_y, start:stop_x]
    if result.shape[1:] != (selected.input_height, selected.input_width):
        raise AssertionError("profile crop configuration is inconsistent")
    return result


def center_crop_20x20(images: np.ndarray) -> np.ndarray:
    """Compatibility helper for the cropped-dense profile."""

    return preprocess_images(images, profile="cropped-dense")


def normalize_pixels(
    images: np.ndarray,
    *,
    profile: str | MnistProfile = DEFAULT_PROFILE,
) -> np.ndarray:
    """Return float32 pixels in 0..1, matching the user's notebook convention."""

    selected = preprocess_images(images, profile=profile)
    return selected.astype(np.float32) / np.float32(255.0)


def quantize_spike_levels(
    images: np.ndarray,
    *,
    profile: str | MnistProfile = DEFAULT_PROFILE,
    presentation_ticks: int = PRESENTATION_TICKS,
) -> np.ndarray:
    """Quantize each selected pixel to an exact integer spike count in 0..T."""

    if isinstance(presentation_ticks, bool) or not isinstance(presentation_ticks, int):
        raise TypeError("presentation_ticks must be an int")
    if presentation_ticks <= 0:
        raise ValueError("presentation_ticks must be positive")

    selected = get_profile(profile)
    pixels = preprocess_images(images, profile=selected).astype(np.int64)

    # Integer half-up quantization is the deterministic equivalent of the
    # notebook's pixel/255 normalization followed by scaling to T spikes.
    levels = (pixels * presentation_ticks + 127) // 255
    return levels.reshape(pixels.shape[0], selected.input_axons).astype(np.int16)


def encode_binary_spikes(
    images: np.ndarray,
    *,
    profile: str | MnistProfile = DEFAULT_PROFILE,
    presentation_ticks: int = PRESENTATION_TICKS,
) -> np.ndarray:
    """Encode images as ``(N, T, input_axons)`` boolean spike tensors."""

    levels = quantize_spike_levels(
        images,
        profile=profile,
        presentation_ticks=presentation_ticks,
    )
    ticks = np.arange(presentation_ticks, dtype=np.int64)
    before = (ticks[None, :, None] * levels[:, None, :]) // presentation_ticks
    after = ((ticks[None, :, None] + 1) * levels[:, None, :]) // presentation_ticks
    return after > before


def encode_event_schedule(
    image: np.ndarray,
    *,
    profile: str | MnistProfile = DEFAULT_PROFILE,
    presentation_ticks: int = PRESENTATION_TICKS,
) -> tuple[tuple[int, ...], ...]:
    """Encode one image as the exact per-tick axon-ID sequence for the core."""

    spikes = encode_binary_spikes(
        image,
        profile=profile,
        presentation_ticks=presentation_ticks,
    )
    if spikes.shape[0] != 1:
        raise ValueError("encode_event_schedule accepts exactly one image")
    return tuple(
        tuple(int(axon) for axon in np.flatnonzero(spikes[0, tick]))
        for tick in range(presentation_ticks)
    )


def count_events(schedule: Sequence[Sequence[int]]) -> int:
    """Return the total number of external events in a schedule."""

    return sum(len(tick) for tick in schedule)
