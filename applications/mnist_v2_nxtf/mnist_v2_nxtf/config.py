"""Stable P08 MNIST experiment constants.

P08 was realigned on 2026-09-29 to emulate the published NxTF MNIST work as
closely as public evidence and the FPGA-v2 architecture permit. P08.1 completed
on 2026-09-30 with an accepted, explicitly project-defined reconstruction of the
unpublished NxTF frame-MNIST topology. P08.2 then accepted deterministic paging
of the five-logical-core P06 deployment over three resident K26 contexts and one
physical HLS engine.

P08.3 froze the ANN checkpoint and the source-recovered ANN-to-SNN conversion,
then accepted a full 5,000-example validation measurement before any official
MNIST test result was observed. P08.4 is now allowed to evaluate the untouched
official test split, but the accepted checkpoint, conversion, thresholds,
readout, and primary 100-timestep horizon must not change in response to test
performance.
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

# P08.1 topology, P08.2 paging, and P08.3 ANN/conversion freeze are accepted.
# P08.4 official-test evaluation is now active and is evaluation-only.
TOPOLOGY_STATUS = "P08_3_ACCEPTED_P08_4_OFFICIAL_TEST_EVALUATION_ACTIVE"
