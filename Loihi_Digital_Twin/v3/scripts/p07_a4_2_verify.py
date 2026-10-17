#!/usr/bin/env python3
"""Strict A4.2c candidate PHYSICAL P07A4R01 journal and trace verification.

Never substitutes a mock oracle for a board result. Only original XSDB
readback from explicitly supplied --journal/--trace is scored.
Only synthetic and canonical TRAIN-derived validation (NOT t10k TEST).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from loihi_twin_v2.p06_a3_training import load_candidate, integer_weights_sha256
from loihi_twin_v2.p06_a4_snapshot import (
    compile_and_check_traces, require_pinned_training_candidate,
)
from loihi_twin_v2.p07_a1_ingress import mapping_from_compiled
from loihi_twin_v2.p07_a4_stream import (
    parse_stream,parse_journal,sha256,
)
from loihi_twin_v2.p06_packed_replay import replay_p03_image
from loihi_twin_v2.p06_input_contract import image_event_schedule
from loihi_twin_v2.p07_a2_evidence import _state_word


def compare_trace(trace: bytes, image, expected) -> None:
    if len(trace)!=65536 or any(trace[26*42*32:]):
        raise ValueError("A4.2c selected physical full trace length/reserved wrong")
    for tick,step in enumerate(expected.ticks):
        for comp in range(42):
            pos=(tick*42+comp)*32
            actual=trace[pos:pos+32]
            before=int.from_bytes(actual[0:8],"little")
            acc=int.from_bytes(actual[8:16],"little")
            after=int.from_bytes(actual[16:24],"little")
            spike=int.from_bytes(actual[24:32],"little")
            wanted_before=(image.state_words[comp] if tick==0
                           else _state_word(expected.ticks[tick-1].states_after[comp]))
            wanted_after=_state_word(step.states_after[comp])
            expect=(wanted_before,step.accumulators[comp] & ((1<<64)-1),
                    wanted_after,int(comp in step.fired_compartments))
            if (before,acc,after,spike)!=expect:
                raise AssertionError(
                    f"A4.2c physical trace mismatch tick={tick} comp={comp} "
                    f"before=0x{before:X}/0x{expect[0]:X} "
                    f"acc=0x{acc:X}/0x{expect[1]:X} "
                    f"after=0x{after:X}/0x{expect[2]:X} "
                    f"spike=0x{spike:X}/0x{expect[3]:X}")


def validate_staging(stage: Path):
    meta=json.loads((stage/"p07_a4_2a_stage_manifest.json").read_text())
    if (meta.get("schema")!="p07-a4-2a-persistent-ddr-stage-v1" or
            meta.get("official_mnist_test")!="SEALED" or
            meta.get("physical_hardware")!="NOT_RUN" or
            meta.get("scope") not in {
                "SYNTHETIC_BLACK","SYNTHETIC_WHITE","SYNTHETIC_RAMP",
                "TRAIN_DERIVED_VALIDATION_FIRST_16",
                "TRAIN_DERIVED_VALIDATION_FIRST_128"}):
        raise ValueError("A4.2c stage is not sealed synthetic or TRAIN-derived validation")
    spec={
        "descriptor":"p07_a4_descriptor_256.bin",
        "mapping":"p07_a4_mapping_1568.bin",
        "pixels":"p07_a4_pixels_raw.bin",
        "zero_journal_1m":"p07_a4_journal_initial_1m.bin",
    }
    raw={name:(stage/file).read_bytes() for name,file in spec.items()}
    for name,data in raw.items():
        if sha256(data)!=meta.get("sha256",{}).get(name):
            raise ValueError("A4.2c input staged SHA-256 mismatch "+name)
    stream=parse_stream(raw["descriptor"],raw["mapping"],raw["pixels"])
    if (stream.image_count!=meta["frame_count"] or
            stream.trace_index!=meta["trace_index"]):
        raise ValueError("A4.2c wrong trace/frame count")
    return meta,stream


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage-dir",type=Path,required=True)
    p.add_argument("--journal",type=Path,required=True)
    p.add_argument("--trace",type=Path,required=True)
    p.add_argument("--data-dir",type=Path,default=Path("data/mnist_raw"))
    p.add_argument("--candidate-dir",type=Path,default=Path(
        "artifacts/p06_a3_candidate_seed20261013"))
    args=p.parse_args()
    meta,stream=validate_staging(args.stage_dir)
    results=parse_journal(args.journal.read_bytes(),stream)
    model,candidate=load_candidate(args.candidate_dir)
    require_pinned_training_candidate(candidate,integer_weights_sha256(model))
    image,compiled,check=compile_and_check_traces(model,())
    if check or compiled.fingerprint!=meta["compiled_fingerprint"]:
        raise ValueError("A4.2c trained compiler drift")
    mapping=mapping_from_compiled(compiled)
    if mapping!=stream.mapping:
        raise ValueError("A4.2c physical staging map differs from frozen model")

    if meta["scope"].startswith("TRAIN_DERIVED_VALIDATION_"):
        from loihi_twin_v2.p06_a3_data import load_train_validation
        from loihi_twin_v2.p07_a3_3_protocol import select_frames
        split=load_train_validation(args.data_dir)
        if candidate["source_dataset"]!=split.manifest:
            raise ValueError("A4.2c wrong frozen validation dataset")
        selected=select_frames(split)[:stream.image_count]
        if b"".join(f.pixels for f in selected)!=stream.images:
            raise ValueError("A4.2c staged pixels differ from canonical original TRAIN IDX")
        ledger=json.loads((args.stage_dir/"p07_a4_2a_validation_labels_HOST_ONLY.json").read_text())
        if len(ledger.get("rows",[]))!=stream.image_count:
            raise ValueError("A4.2c validation label ledger count")
        for i,f in enumerate(selected):
            row=ledger["rows"][i]
            if (row.get("position")!=i or row.get("source_index")!=f.source_index or
                    row.get("label")!=f.label or row.get("pixels_sha256")!=sha256(f.pixels)):
                raise ValueError(f"A4.2c wrong canonical validation ledger index={i}")
    else:
        kind=meta["scope"].removeprefix("SYNTHETIC_")
        expected={
            "BLACK":bytes(784),
            "WHITE":bytes([255])*784,
            "RAMP":bytes(i%256 for i in range(784)),
        }[kind]
        if stream.images!=expected*stream.image_count:
            raise ValueError("A4.2c synthetic staging altered")

    selected_oracle=None
    for i,result in enumerate(results):
        pixels=stream.image(i)
        oracle=replay_p03_image(image,mapping,pixels)
        for tick,step in enumerate(oracle.ticks):
            want=tuple(int(32+cls in step.fired_compartments) for cls in range(10))
            if result.output_spikes[tick]!=want:
                raise AssertionError(
                    f"A4.2c FIRST FPGA mismatch frame={i} tick={tick} output flags"
                )
        if (result.counts!=oracle.output_counts or
                result.predicted!=oracle.predicted_class or
                result.all_silent!=(sum(oracle.output_counts)==0)):
            raise AssertionError(f"A4.2c FIRST FPGA mismatch frame={i} readout")
        want_routes=sum(len(step.next_packet_axons) for step in oracle.ticks[:-1])
        if (result.routes!=want_routes or
                result.discarded!=len(oracle.dropped_boundary_packets) or
                result.external_events!=sum(len(t) for t in image_event_schedule(pixels))):
            raise AssertionError(f"A4.2c FIRST FPGA mismatch frame={i} routes/ingress")
        if i==stream.trace_index:selected_oracle=oracle
    if selected_oracle is None:raise AssertionError("A4.2c no physical selected-frame trace")
    compare_trace(args.trace.read_bytes(),image,selected_oracle)
    print("P07_A4_2C_PHYSICAL_FRAMES="+str(len(results)))
    print("P07_A4_2C_PHYSICAL_ALL_OUTPUTS_EXACT=1")
    print("P07_A4_2C_PHYSICAL_SELECTED_TRACE_26X42_EXACT=1")
    print("P07_A4_2C_PHYSICAL_SEALED_VALIDATION_GATE_PASS=1")
    print("P07_A4_OFFICIAL_TEST=SEALED")


if __name__=="__main__":
    main()
