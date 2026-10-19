"""P08-A5 host CPU replay of P03 packed integer neuron semantics.

Two declared endpoints, same prepared immutable packed network:
- preloaded_compute: accepts a pre-encoded 26-tick event schedule;
- image_to_class: accepts raw 784B uint8 and includes the ORIGINAL
  accepted P06 event encoder and spike count class selection.
Model decoding/packing are explicitly outside both timed scopes.
This is a Python scalar CPU reference; NOT CPU native throughput or PL-only time.
Numerical output must be validated against the accepted original independent
P06 packed replay AND the real P07 physical journal before benchmarking.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence
from typing import Any

from .p06_input_contract import (
    INPUT_CHANNELS, INPUT_TICKS, TOTAL_TICKS, HIDDEN_NEURONS, OUTPUT_CLASSES,
    EVENT_BANK_DEPTH, image_event_schedule, classify_spike_counts,
)
from .p06_integer_oracle import LIFParameters, LIFState, lif_step, wrap64
from .p06_packed_replay import _decode_config, _decode_state, _signed24


@dataclass(frozen=True, slots=True)
class PreparedCPU:
    """Immutable decoded model, NOT an independent source of neuron semantics."""
    core_id: int
    initial: tuple[LIFState, ...]
    parameters: tuple[LIFParameters, ...]
    pixel_to_axon: tuple[int, ...]
    axon_table: dict[int, tuple[tuple[int, int], ...]]
    route_table: dict[int, tuple[int, ...]]


@dataclass(frozen=True, slots=True)
class CPUOutcome:
    """The same class/output, routes and event counts in the P07 physical journal."""
    predicted: int
    counts: tuple[int, ...]
    output_spikes: tuple[tuple[int, ...], ...]
    routes: int
    discarded: int
    external_events: int
    all_silent: bool


def prepare_cpu(image: Any, pixel_to_axon: Sequence[int]) -> PreparedCPU:
    """Decode frozen P03 packed arrays ONCE, strictly before per-image timings.

    The accepted P06 packed independent replay remains the numerical oracle.
    This derivation is a separately differential-tested timed CPU implementation.
    """
    n=HIDDEN_NEURONS+OUTPUT_CLASSES
    if (image.compartment_count!=n or not 0<=image.core_id<128 or
            len(image.config_words)!=n or len(image.state_words)!=n or
            image.synapse_count!=len(image.synapse_words) or
            image.synapse_count>32768 or
            image.route_count!=len(image.route_words) or
            image.route_count>4096):
        raise ValueError("A5 packed image compartment/synapse/route contract invalid")
    mapping=tuple(pixel_to_axon)
    if (len(mapping)!=INPUT_CHANNELS or
            any(type(x) is not int or not 0<=x<4096 for x in mapping) or
            len(set(mapping))!=INPUT_CHANNELS):
        raise ValueError("A5 input-to-axon mapping not the accepted 784 distinct channels")
    params=tuple(_decode_config(word) for word in image.config_words)
    initial=tuple(_decode_state(word) for word in image.state_words)
    synapses=[]
    for word in image.synapse_words:
        if word>>48 or (word>>34)&0x3F:
            raise ValueError("A5 unsupported packed synapse reserved/delay bits")
        synapses.append((word&0x3FF,_signed24(word>>10)))
    axon={}
    for item in image.axon_words:
        if not 0<=item.index<4096 or item.index in axon:
            raise ValueError("A5 invalid/duplicate packed axon")
        word=item.word
        if word>>42 or (word>>41)&1!=1:
            raise ValueError("A5 invalid axon valid/reserved bits")
        first,length,offset=word&0x7FFF,(word>>15)&0xFFFF,(word>>31)&0x3FF
        if first+length>len(synapses):
            raise ValueError("A5 axon points beyond packed synapses")
        destinations=[]
        for rel,weight in synapses[first:first+length]:
            dest=offset+rel
            if dest>=n:
                raise ValueError("A5 synapse destination outside compact core")
            destinations.append((dest,weight))
        axon[item.index]=tuple(destinations)
    if any(channel not in axon for channel in mapping):
        raise ValueError("A5 missing external ingress axon")
    routes={}
    for item in image.route_descriptor_words:
        if not 0<=item.index<n or item.index in routes:
            raise ValueError("A5 invalid/duplicate route descriptor")
        word=item.word
        if word>>26 or (word>>25)&1!=1:
            raise ValueError("A5 invalid route descriptor valid/reserved bits")
        first,length=word&0xFFF,(word>>12)&0x1FFF
        if first+length>len(image.route_words):
            raise ValueError("A5 route descriptor overflow")
        dests=[]
        for raw in image.route_words[first:first+length]:
            if raw>>19 or (raw&0x7F)!=image.core_id:
                raise ValueError("A5 invalid route word or destination core")
            dest=(raw>>7)&0xFFF
            if dest not in axon:
                raise ValueError("A5 route destination axon missing")
            dests.append(dest)
        routes[item.index]=tuple(dests)
    # Original P06 packed replay validates even unused route words.
    for raw in image.route_words:
        if raw>>19 or (raw&0x7F)!=image.core_id or ((raw>>7)&0xFFF) not in axon:
            raise ValueError("A5 invalid unused packed route word")
    return PreparedCPU(image.core_id,initial,params,mapping,axon,routes)


def preloaded_compute(prepared: PreparedCPU,
                      schedule: Sequence[Sequence[int]]) -> CPUOutcome:
    """Core/recurrent computation with 26 external pixel-event lists already ready.

    Includes axon map, synaptic accumulation, integer LIF steps, spike
    accumulation and same-core NEXT-bank routing; does not include pixel
    event encoding, pack/model initialization, IO or host journal writes.
    """
    if len(schedule)!=TOTAL_TICKS or tuple(schedule[INPUT_TICKS])!=():
        raise ValueError("A5 requires canonical 25 input ticks plus empty drain tick")
    states=list(prepared.initial)
    counts=[0]*OUTPUT_CLASSES
    next_axons=()
    output_spikes=[]
    route_count=0
    external_count=0
    n=HIDDEN_NEURONS+OUTPUT_CLASSES
    for tick,active in enumerate(schedule):
        if (len(active)>EVENT_BANK_DEPTH or
                any(type(pixel) is not int or not 0<=pixel<INPUT_CHANNELS for pixel in active) or
                len(set(active))!=len(active)):
            raise ValueError(f"A5 invalid or duplicate pixel events at tick {tick}")
        external_count+=len(active)
        current=tuple(prepared.pixel_to_axon[p] for p in active)+next_axons
        if len(current)>EVENT_BANK_DEPTH:
            raise ValueError("A5 combined current event bank overflow")
        accum=[0]*n
        for axon in current:
            if axon not in prepared.axon_table:
                raise ValueError("A5 unknown event axon")
            for dest,weight in prepared.axon_table[axon]:
                accum[dest]=wrap64(accum[dest]+weight)
        outgoing=[]
        fired_output=[0]*OUTPUT_CLASSES
        for comp in range(n):
            step=lif_step(states[comp],prepared.parameters[comp],accum[comp])
            states[comp]=step.state
            if step.spiked:
                if comp>=HIDDEN_NEURONS:
                    cls=comp-HIDDEN_NEURONS
                    counts[cls]+=1
                    fired_output[cls]=1
                outgoing.extend(prepared.route_table.get(comp,()))
        if len(outgoing)>4096:
            raise ValueError("A5 emitted packet capacity exceeded")
        output_spikes.append(tuple(fired_output))
        if tick<INPUT_TICKS:
            route_count+=len(outgoing)
        next_axons=tuple(outgoing)
    return CPUOutcome(
        predicted=classify_spike_counts(counts),
        counts=tuple(counts),output_spikes=tuple(output_spikes),
        routes=route_count,discarded=len(next_axons),
        external_events=external_count,all_silent=(sum(counts)==0),
    )


def image_to_class(prepared: PreparedCPU, raw_pixels: bytes) -> CPUOutcome:
    """Full CPU software path: raw uint8 pixels -> original encoder -> 26 ticks -> class.

    Does NOT include per-image loading from file, neural model decode,
    journal formatting or FPGA PS/PL MMIO; those asymmetries must be reported.
    """
    return preloaded_compute(prepared,image_event_schedule(raw_pixels))


def assert_matches_physical(result: CPUOutcome, journal_row: Any, index: int) -> None:
    if (result.predicted!=journal_row.predicted or
            result.counts!=journal_row.counts or
            result.output_spikes!=journal_row.output_spikes or
            result.routes!=journal_row.routes or
            result.discarded!=journal_row.discarded or
            result.external_events!=journal_row.external_events or
            result.all_silent!=journal_row.all_silent):
        raise AssertionError(f"A5 CPU vs original KV260 physical neural parity FAILED at frame={index}")


def assert_matches_original_packed(result: CPUOutcome, oracle: Any, schedule: Sequence[Sequence[int]],index:int) -> None:
    ref=CPUOutcome(
        predicted=oracle.predicted_class,
        counts=oracle.output_counts,
        output_spikes=tuple(tuple(int(32+cls in step.fired_compartments)
                                  for cls in range(OUTPUT_CLASSES))
                            for step in oracle.ticks),
        routes=sum(len(step.next_packet_axons) for step in oracle.ticks[:-1]),
        discarded=len(oracle.dropped_boundary_packets),
        external_events=sum(len(t) for t in schedule),
        all_silent=sum(oracle.output_counts)==0,
    )
    if result!=ref:
        raise AssertionError(f"A5 CPU prepared replay vs original immutable P06 packed oracle mismatch at frame={index}")
