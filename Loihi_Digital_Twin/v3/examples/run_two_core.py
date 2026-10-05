#!/usr/bin/env python3
"""Run the minimal P02 two-core feed-forward architecture example."""

from __future__ import annotations

import json

from loihi_twin_v2 import (
    CompartmentConfig,
    Deployment,
    InputAxonBinding,
    LogicalCoreConfig,
    OutputRoute,
    OutputRouteEntry,
    SpikePacket,
    SynapseEntry,
    SynapseTemplate,
    deployment_report,
    trace_report,
)


def compartment() -> CompartmentConfig:
    return CompartmentConfig(4096, 4096, threshold=5)


def build_deployment() -> Deployment:
    core0 = LogicalCoreConfig(
        core_id=0,
        compartments=(compartment(),),
        input_axons=(InputAxonBinding(0, 0),),
        synapse_templates=(SynapseTemplate(0, (SynapseEntry(0, 6),)),),
        output_routes=(OutputRouteEntry(0, (OutputRoute(1, 3),)),),
    )
    core1 = LogicalCoreConfig(
        core_id=1,
        compartments=(compartment(),),
        input_axons=(InputAxonBinding(3, 0),),
        synapse_templates=(SynapseTemplate(0, (SynapseEntry(0, 6),)),),
    )
    return Deployment((core0, core1))


def main() -> None:
    deployment = build_deployment()
    chip = deployment.build_chip()
    print("DEPLOYMENT")
    print(json.dumps(deployment_report(deployment), indent=2, sort_keys=True))

    for external in ((SpikePacket(0, 0, 0),), ()):
        trace = chip.step(external)
        print(f"TIMESTEP {trace.algorithmic_timestep}")
        print(json.dumps(trace_report(trace), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
