#!/usr/bin/env python3
"""P06 LIF feasibility: original v3 P06 compiler -> P03 HLS hardware image.

No MNIST data or learned checkpoint is needed. Dense synthetic *test-only*
784->32->10 signed-integer synapses deliberately avoid template deduplication,
so the packer must physically reserve all 25,408 entries, not just estimate
logical counts. PASS proves structural/export capacity on native host ONLY.
It does NOT prove snnTorch-to-FPGA numerical parity or KV260 execution.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

from loihi_twin_v2.compiler import (
    InputPopulationSpec, InputProjectionSpec, MappingOptions, NetworkSpec,
    PopulationSpec, ProjectionConnection, ProjectionSpec, compile_network,
)
from loihi_twin_v2.compartment import CompartmentConfig
from loihi_twin_v2.hardware_p03 import export_one_core_image
from loihi_twin_v2.resources import (
    MAX_COMPARTMENTS_PER_CORE,MAX_INPUT_AXONS_PER_CORE,
    MAX_OUTPUT_ROUTES_PER_CORE,MAX_SYNAPSE_MEMORY_BYTES_PER_CORE,
)

IMAGE_PIXELS=784
NUM_OUTPUTS=10
FEASIBILITY_HIDDEN=32
SOURCE_TUTORIAL_HIDDEN=1000
EVENT_BANK_DEPTH=4096
P03_HARD_SYNAPSE_ENTRIES=32768
P05_PROVEN_DDR_CORES=5

def dense_weights(source:int,dest:int,src_size:int,dst_size:int)->int:
    """Unique fanout patterns for each source. Synthetic, never trained."""
    if not (0<=source<src_size and 0<=dest<dst_size):
        raise ValueError("out-of-bounds test-only weight index")
    if dest==0:
        return 1+(source%240)
    if dest==1:
        return 1+(source//240)
    return 1+((source*(dest+3)+11*dest)%251)

def make_synthetic_exploratory_network(hidden:int=FEASIBILITY_HIDDEN)->NetworkSpec:
    if not 1<=hidden<=MAX_COMPARTMENTS_PER_CORE-NUM_OUTPUTS:
        raise ValueError("exploratory 1-core hidden size outside simple bound")
    # This integer LIF config is a compatibility *probe*, NOT snnTorch Leaky.
    # Hardware current decay 4096 => instant current reset; voltage decay
    # 205/4096 => residual ~0.94995, not exactly tutorial's beta=0.95.
    cfg=CompartmentConfig(
        current_decay=4096,voltage_decay=205,threshold=2048,
        reset_voltage=0,refractory_ticks=0,bias=0,
    )
    input_edges=tuple(
        ProjectionConnection(s,d,dense_weights(s,d,IMAGE_PIXELS,hidden))
        for s in range(IMAGE_PIXELS) for d in range(hidden)
    )
    output_edges=tuple(
        ProjectionConnection(s,d,dense_weights(s,d,hidden,NUM_OUTPUTS))
        for s in range(hidden) for d in range(NUM_OUTPUTS)
    )
    return NetworkSpec(
        populations=(PopulationSpec("hidden",hidden,cfg),
                     PopulationSpec("readout",NUM_OUTPUTS,cfg)),
        input_populations=(InputPopulationSpec("pixels",IMAGE_PIXELS),),
        input_projections=(InputProjectionSpec(
            "pixels_to_hidden","pixels","hidden",input_edges),),
        projections=(ProjectionSpec(
            "hidden_to_readout","hidden","readout",output_edges),),
    )

def probe_exploratory(hidden:int=FEASIBILITY_HIDDEN)->dict:
    network=make_synthetic_exploratory_network(hidden)
    deployed=compile_network(network,MappingOptions(max_logical_cores=1))
    if len(deployed.logical_deployment.core_configs)!=1:
        raise RuntimeError("one-context synthetic feasibility compile did not retain one core")
    core=deployed.logical_deployment.core_configs[0]
    image=export_one_core_image(core)
    total_conn=IMAGE_PIXELS*hidden+hidden*NUM_OUTPUTS
    if core.resource_usage.expanded_connections!=total_conn:
        raise RuntimeError("compiler dropped or duplicated some logical test synapses")
    if len(image.synapse_words)!=total_conn:
        raise RuntimeError("synthetic all-unique-pattern HW image unexpectedly deduplicated")
    if image.compartment_count!=hidden+NUM_OUTPUTS:
        raise RuntimeError("FPGA image compartment mismatch")
    if image.synapse_count!=total_conn:
        raise RuntimeError("FPGA image synapse entries mismatch")
    if len(image.axon_words)!=IMAGE_PIXELS+hidden:
        raise RuntimeError("FPGA image destination-side axon count mismatch")
    if image.route_count!=hidden:
        raise RuntimeError("FPGA image hidden-to-readout route count mismatch")
    if len(deployed.ingress_routes)!=IMAGE_PIXELS:
        raise RuntimeError("external pixel-to-axon map is not complete")
    if max(IMAGE_PIXELS,hidden+IMAGE_PIXELS)>EVENT_BANK_DEPTH:
        raise RuntimeError("single-step theoretical event count overflow")
    return {
        "gate":"P06_LIF_NATIVE_STRUCTURAL_ONLY",
        "model_source":"Eshraghian et al. 2023 snnTorch tutorial 5 methodology; resized project exploratory profile",
        "model_is_published_trained_checkpoint":False,
        "weights_are_synthetic_and_have_no_MNIST_accuracy":True,
        "original_tutorial_architecture":[784,1000,10],
        "exploratory_project_architecture":[IMAGE_PIXELS,hidden,NUM_OUTPUTS],
        "compiler":"existing loihi_twin_v2.compiler.compile_network",
        "hardware_packer":"existing loihi_twin_v2.hardware_p03.export_one_core_image",
        "actual_hardware_image":{
            "compartment_count":image.compartment_count,
            "synapse_count":image.synapse_count,
            "destination_axon_count":len(image.axon_words),
            "route_count":image.route_count,
            "core_id":image.core_id,
        },
        "logical_compiler_report":deployed.report(),
        "hard_capacities":{
            "compartments":MAX_COMPARTMENTS_PER_CORE,
            "input_axons":MAX_INPUT_AXONS_PER_CORE,
            "route_entries":MAX_OUTPUT_ROUTES_PER_CORE,
            "synapse_entries":P03_HARD_SYNAPSE_ENTRIES,
            "synapse_memory_bytes":MAX_SYNAPSE_MEMORY_BYTES_PER_CORE,
            "input_events_per_bank":EVENT_BANK_DEPTH,
        },
        "theoretical_worst_case_events_per_step":{
            "all_pixels_external":IMAGE_PIXELS,
            "hidden_routed":hidden,
            "conservative_combined":IMAGE_PIXELS+hidden,
        },
        "timing":None,
        "hardware_execution":False,
        "behavior_parity_snnTorch":False,
        "unproven":[
            "published original 784-1000-10 architecture cannot be asserted mapped",
            "analog tutorial input is not identical to spike-event source input",
            "tutorial 0.95 Leaky/bias/reset/update order vs 24-bit P03 LIF",
            "intra-core hidden-to-output physical route arrives NEXT bank, not same-step",
            "board-local per-sample reset, dynamic multi-axon event loader and readout collection",
            "real trained quantized weights and official MNIST predictions/accuracy",
            "KV260 physical throughput, power and Loihi comparison",
        ],
    }

def original_tutorial_limit()->dict:
    synapses=IMAGE_PIXELS*SOURCE_TUTORIAL_HIDDEN+SOURCE_TUTORIAL_HIDDEN*NUM_OUTPUTS
    return {
        "tutorial_architecture":[IMAGE_PIXELS,SOURCE_TUTORIAL_HIDDEN,NUM_OUTPUTS],
        "dense_potential_synapse_entries":synapses,
        "one_core_synapse_entries_max":P03_HARD_SYNAPSE_ENTRIES,
        "minimum_synapse_banks_without_compression":(
            synapses+P03_HARD_SYNAPSE_ENTRIES-1)//P03_HARD_SYNAPSE_ENTRIES,
        "accepted_p05_ddr_logical_core_records":P05_PROVEN_DDR_CORES,
        "max_dense_synapses_over_five_records":P05_PROVEN_DDR_CORES*P03_HARD_SYNAPSE_ENTRIES,
        "fits_accepted_five_record_hardware":False,
        "qualification":"Exact source tutorial uses analog x repeated for 25 steps; no released corresponding trained weights proven.",
    }

def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",choices=["probe32","original_tutorial"],default="probe32")
    parser.add_argument("--out",type=Path,help="Optional new JSON evidence; must not exist")
    args=parser.parse_args()
    try:
        result=probe_exploratory() if args.mode=="probe32" else original_tutorial_limit()
        if args.out is not None:
            if args.out.exists():
                raise ValueError("refusing to overwrite immutable probe evidence")
            args.out.parent.mkdir(parents=True,exist_ok=True)
            args.out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    except (ValueError,RuntimeError) as e:
        print("FAIL: P06 LIF native compiler/hardware image feasibility: "+str(e),
              file=sys.stderr)
        print("P06_LIF_FEASIBILITY_EXIT=1",file=sys.stderr)
        return 1
    print("PASS: P06 LIF "+("one-core real compiler+HLS packed image" if args.mode=="probe32" else "original published tutorial limitation correctly described"))
    print("P06_LIF_FEASIBILITY="+json.dumps(
        {"mode":args.mode,"synthetic":args.mode=="probe32",
         "image":result.get("actual_hardware_image"),
         "report_headroom":result.get("logical_compiler_report",{}).get("cores",[{}])[0].get("headroom"),
         "original_dense_connections":result.get("dense_potential_synapse_entries"),
         "one_core_hw_synapse_cap":P03_HARD_SYNAPSE_ENTRIES},
        sort_keys=True))
    print("P06_LIF_FEASIBILITY_EXIT=0")
    print("P06_LIF_BENCHMARK_FREEZE=NO_TRAINED_WEIGHTS_NO_ACCURACY_NO_NUMERICAL_PARITY")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
