#!/usr/bin/env python3
"""P06.1 exact isolated source-derived sequential-MNIST SNIP I/O contract.

Transliterates *input event indices* from author source
  intel-nrc-ecosystem/models @ 3dc53bfcfae1efe8772b8cb5e2c512bb28c872f8
  apps/seqmnist/snips/spiking.c, common.h, snip_mgmt.c
and thresholds from apps/seqmnist/seq_img_classifier.py.

Does not emulate Loihi NxSDK timing, physical address assignments,
AHP dynamics, trained weights, power, accuracy or physical KV260.
It is a pure exact reference for the C source's logical spike-port
mapping and final V argmax only.
"""
from __future__ import annotations

from collections.abc import Sequence

PIXELS=784
NUM_INPUTS=80
NUM_THRESHOLDS=40
CUE_STEPS=56
TOTAL_STEPS=PIXELS+CUE_STEPS
# Mathematically equal to the original Python author expression
# np.floor(np.linspace(0,255,NUM_INPUTS//2)); assert this against
# real NumPy in the host regression before choosing as a static contract.
THRESHOLDS=tuple(255*i//(NUM_THRESHOLDS-1) for i in range(NUM_THRESHOLDS))
assert (THRESHOLDS[0],THRESHOLDS[-1])==(0,255)

def spike_ports(image:Sequence[int],timestep:int)->tuple[int,...]:
    """Port indices emitted by the exact author-side SNIP at 1-based timestep."""
    if len(image)!=PIXELS:
        raise ValueError("P06.1 sMNIST requires exact 28x28 uint8 image")
    if not all(type(v)==int and 0<=v<=255 for v in image):
        raise ValueError("P06.1 image must contain exact unscaled python integer uint8 values")
    if not 1<=timestep<=TOTAL_STEPS:
        raise ValueError("P06.1 sample timestep must be 1..840")
    index=timestep-1
    if index>=PIXELS:
        return (79,) # Original 56-step output cue, not a 784-pixel spike.
    here=image[index]
    last=index==PIXELS-1
    next_value=image[index+1] if not last else None
    ports=[]
    # spiking.c uses indices t=1..NUM_THRESHOLDS-1, not t=0.
    for t in range(1,NUM_THRESHOLDS):
        level=THRESHOLDS[t]
        if t==NUM_THRESHOLDS-1:
            # C get_touch_spikes() checks only CURRENT pixel.
            if here==level:
                ports.append(2*t) # port 78
        elif not last:
            # Original algorithm crosses from current pixel to NEXT pixel,
            # not from previous to current.
            if here<level and next_value>=level:
                ports.append(2*t)
            if here>=level and next_value<level:
                ports.append(2*t+1)
    return tuple(ports)

def classify_output_membrane_voltages(voltage:Sequence[int])->int:
    """Loihi management SNIP: 10 signed membrane Vs; first index breaks ties."""
    if len(voltage)!=10 or any(type(v)!=int or not -(1<<23)<=v<(1<<23)
                               for v in voltage):
        raise ValueError("requires 10 valid signed 24-bit physical V readings")
    winning=-8388608
    index=-1
    for i,v in enumerate(voltage):
        if v>winning:
            index=i;winning=v
    if index<0:raise ValueError("no output winner")
    return index

def stream_sparse_ports(image:Sequence[int])->dict[int,tuple[int,...]]:
    """Full sample schedule, 840 *real* logical timesteps, omit empty entries."""
    schedule={}
    for step in range(1,TOTAL_STEPS+1):
        ports=spike_ports(image,step)
        if ports:schedule[step]=ports
    return schedule
