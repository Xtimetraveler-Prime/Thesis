"""Stable P08 MNIST experiment constants.

P08 was realigned on 2026-09-29 to emulate the published NxTF MNIST work as
closely as public evidence and the FPGA-v2 architecture permit. P08.1 completed
on 2026-09-30 with an accepted, explicitly project-defined reconstruction of the
unpublished NxTF frame-MNIST topology. The abandoned revision-1/2/3 candidate
definitions remain intentionally excluded so later work cannot silently reuse
them as the accepted P08 model.
"""

from __future__ import annotations

SOURCE_HEIGHT = 28
SOURCE_WIDTH = 28
SOURCE_CHANNELS = 1
NUM_CLASSES = 10

VALIDATION_SIZE = 5_000
VALIDATION_SEED = 0x4D4E4953

# The NxTF paper's frame-based MNIST benchmark reports 100 algorithmic
# timesteps. Keep that as the primary comparison horizon.
PRIMARY_TIMESTEPS = 100
CHARACTERIZATION_TIMESTEPS = (16, 32, 64, 100)

# P08.1 acceptance freezes the reconstruction choice, not the training or
# conversion contract. P08.2 must first prove that the five-logical-core graph
# can be serviced correctly through the three-resident-context K26 shell.
TOPOLOGY_STATUS = "P08_1_RECONSTRUCTION_ACCEPTED_P08_2_PENDING"
