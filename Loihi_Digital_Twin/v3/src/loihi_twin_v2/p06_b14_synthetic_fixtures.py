"""P06-B1.4 synthetic-only 27-core numerical exercise; never trained data.

1,000 hidden neurons and 784 input channels, but SPARSE input connectivity.
Place 26 hidden cores via explicit 39-compartment test policy. Every pixel
fans out to all 26 cores via one anchor destination neuron per core, and the
readout core collects 1,000 source packets per active hidden-spike tick.
This is NOT the 794k-edge DENSE B1.2 production planning topology.
"""
from __future__ import annotations

from .compiler import (
    InputPopulationSpec, InputProjectionSpec, NetworkSpec, PopulationSpec,
    ProjectionConnection, ProjectionSpec,
)
from .compartment import CompartmentConfig


def sparse_27_core_network() -> NetworkSpec:
    hidden = CompartmentConfig(current_decay=4096, voltage_decay=4096, threshold=2)
    readout = CompartmentConfig(current_decay=4096, voltage_decay=4096, threshold=1000)
    ingress: list[ProjectionConnection] = []
    for destination in range(1000):
        if destination % 39 == 0:
            ingress.extend(ProjectionConnection(source, destination, 4)
                           for source in range(784))
        else:
            ingress.append(ProjectionConnection(destination % 784, destination, 4))
    return NetworkSpec(
        populations=(PopulationSpec("h", 1000, hidden),
                     PopulationSpec("z", 10, readout)),
        input_populations=(InputPopulationSpec("pixels", 784),),
        input_projections=(InputProjectionSpec("sparse_ingress", "pixels", "h",
                                              tuple(ingress)),),
        projections=(ProjectionSpec(
            "readout", "h", "z",
            tuple(ProjectionConnection(source, target, 2)
                  for source in range(1000) for target in range(10)),
        ),),
    )
