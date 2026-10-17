#!/usr/bin/env python3
"""P06 candidate project-defined deterministic event-input boundary, NOT snnTorch.

Existing published snnTorch tutorial 5 uses static analog pixel currents,
not this packet-based rate code. The rate-spike generator here is an
exploratory architectural decision, requiring its own MNIST train/validation
and source-reference parity before a future checkpoint can be frozen.
"""
from __future__ import annotations
from collections.abc import Sequence

PIXELS=784
INPUT_TIMESTEPS=25
OUTPUT_FLUSH_TIMESTEPS=1
COMPLETE_TIMESTEPS=INPUT_TIMESTEPS+OUTPUT_FLUSH_TIMESTEPS
EVENT_DEPTH=4096

def rate_coded_pixel_indices(image:Sequence[int],step:int)->tuple[int,...]:
    """Deterministic 8-bit distributed quota code, with per-pixel phase offset.

    Over 25 steps, the exact spike count for pixel p is floor(25*p/255).
    This is a PROJECT-specific deterministic rate code, **not** snnTorch's
    Bernoulli spikegen.rate and not the author's static analog current.
    """
    if len(image)!=PIXELS or any(type(v)!=int or not 0<=v<=255 for v in image):
        raise ValueError("requires exactly 784 Python integer uint8 MNIST pixel values")
    if not 0<=step<COMPLETE_TIMESTEPS:
        raise ValueError("sample timestep outside 0..25")
    if step==INPUT_TIMESTEPS:
        return ()   # Drain hidden->readout NEXT bank without new image pixels.
    out=[]
    for pixel_index,level in enumerate(image):
        shifted_step=(step+(pixel_index*17)%INPUT_TIMESTEPS)%INPUT_TIMESTEPS
        if ((shifted_step+1)*level)//255 > (shifted_step*level)//255:
            out.append(pixel_index)
    if len(out)>EVENT_DEPTH:
        raise RuntimeError("external event bank overflow")
    return tuple(out)

def verified_external_packets(compiled,image:Sequence[int],step:int):
    """Use EXISTING v3 compiler ingress routes, never fabricate an axon ID."""
    pixels=rate_coded_pixel_indices(image,step)
    packets=compiled.external_packets("pixels",pixels,target_timestep=step)
    if len(packets)!=len(pixels):
        raise RuntimeError("compiler ingress route not one-to-one for 784 pixels")
    if len({(p.destination_core,p.destination_axon) for p in packets})!=len(pixels):
        raise RuntimeError("duplicate destination-side axon during input encoding")
    return packets

def class_from_output_spike_counts(counts:Sequence[int])->int:
    """Provisional 10-neuron spike-count readout; ties choose lowest class.

    This PROJECT readout must be frozen before training. snnTorch tutorial 5
    also measures output spike counts, but no accuracy equivalence is implied.
    """
    if len(counts)!=10 or any(type(v)!=int or v<0 for v in counts):
        raise ValueError("readout must contain exactly 10 nonnegative integer spike counts")
    return max(range(10),key=lambda i:counts[i])
