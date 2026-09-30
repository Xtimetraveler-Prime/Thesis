"""Stable P08 MNIST experiment constants.

P08 was realigned on 2026-09-29 to emulate the published NxTF MNIST work as
closely as public evidence and the FPGA-v2 architecture permit.  No neural
network topology is frozen in this module.  The abandoned revision-1/2/3
candidate definitions were intentionally removed so later work cannot silently
reuse them as the accepted P08 model.
"""

from __future__ import annotations

SOURCE_HEIGHT = 28
SOURCE_WIDTH = 28
SOURCE_CHANNELS = 1
NUM_CLASSES = 10

VALIDATION_SIZE = 5_000
VALIDATION_SEED = 0x4D4E4953

# The NxTF paper's frame-based MNIST benchmark reports 100 algorithmic
# timesteps.  Keep that as the primary comparison horizon while the exact
# source-backed topology/conversion contract is reconstructed.
PRIMARY_TIMESTEPS = 100
CHARACTERIZATION_TIMESTEPS = (16, 32, 64, 100)

# Explicit marker used by preflight/documentation.  A new topology must not be
# treated as accepted until P08.1 source reconstruction and P08.2 architecture
# adaptation are complete and the comparison contract is updated.
TOPOLOGY_STATUS = "UNFROZEN_NXTF_EMULATION_REALIGN"
