"""Stable P08 MNIST experiment constants.

P08 was realigned on 2026-09-29 to emulate the published NxTF MNIST work as
closely as public evidence and the FPGA-v2 architecture permit. P08.1 completed
on 2026-09-30 with an accepted, explicitly project-defined reconstruction of the
unpublished NxTF frame-MNIST topology. P08.2 then accepted deterministic paging
of the five-logical-core P06 deployment over three resident K26 contexts and one
physical HLS engine.

P08.3.1 freezes the ANN training and ANN-to-SNN conversion policy before any new
training run. The abandoned revision-1/2/3 candidate definitions remain
intentionally excluded so later work cannot silently reuse them as the accepted
P08 model.
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

# P08.1 topology and P08.2 paging are accepted. P08.3.1 freezes the training and
# conversion rules; the official test split remains locked until the selected
# ANN checkpoint and converted-SNN configuration are frozen without test feedback.
TOPOLOGY_STATUS = "P08_2_PAGING_ACCEPTED_P08_3_POLICY_FROZEN"
