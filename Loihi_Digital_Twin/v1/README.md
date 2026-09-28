# Neuromorphic Twin — Python Golden Model and Brian2Loihi Verification

This project implements a transparent integer neuromorphic-core model intended
to become the software golden model for an FPGA-based, Loihi-inspired digital
twin.

## Verification architecture

```text
ComparisonScenario
       │
       ├── Python backend ──────────────┐
       │   NeuromorphicCore             │
       │                                ├── exact trace comparator
       └── Brian2Loihi backend ─────────┘        │
                                                 ├── console report
                                                 ├── trace JSON
                                                 └── report JSON
```

The trace format is backend-neutral. The same comparator can later accept RTL
simulation or physical FPGA traces.

## Current scope

Implemented:

- Tick-driven current-based LIF neurons
- Integer current and voltage state
- Round-away-from-zero decay arithmetic
- Corrected synaptic-input/current-decay update order
- Configurable saturation or two's-complement wrap policies
- Fixed-weight axon-to-neuron synapses
- Excitatory and inhibitory connections
- Axon fan-in and fan-out
- Deterministic next-tick recurrent spike routing
- Refractory periods
- Exact per-tick current, voltage, and spike traces
- Optional Brian2Loihi reference backend
- Directed deterministic conformance suite
- Portable JSON trace and report artifacts

Deferred:

- Exact Loihi state widths and overflow semantics
- Loihi-native mantissa/exponent weight objects
- Synaptic delays and event queues
- Multiple physical cores and packet routing
- Learning rules and stochastic rounding

## Installation

From this directory, with the intended virtual environment active:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev,compare]"
pytest
```

## Basic reference comparisons

Run the smoke scenario:

```bash
python examples/compare_brian2loihi.py --scenario smoke
```

Run the current-decay regression scenario:

```bash
python examples/compare_brian2loihi.py --scenario decay-order
```

Both scenarios are expected to pass. The second scenario verifies that delivered
synaptic input is present before current decay, voltage integrates the pre-decay
working current, and the stored next current contains the decayed value.

## Directed conformance suite

List cases:

```bash
python examples/run_directed_conformance.py --list
```

Run all cases:

```bash
python examples/run_directed_conformance.py
```

Run selected cases:

```bash
python examples/run_directed_conformance.py \
    --case voltage-decay \
    --case threshold-boundary
```

See [`docs/directed_conformance.md`](docs/directed_conformance.md) for case
purpose and result interpretation.

## Generated outputs

Comparison commands write JSON under `comparison_output/`. These files are
runtime artifacts and are intentionally excluded from version control. Stable
future regression fixtures should be placed under a dedicated `tests/fixtures/`
directory instead of committing transient command output.

## Package layout

```text
src/neuromorphic_twin/
├── arithmetic.py
├── core.py
├── model.py
├── neuron.py
└── comparison/
    ├── brian2loihi_backend.py
    ├── compare.py
    ├── conformance.py
    ├── io.py
    ├── model.py
    └── python_backend.py
```

The core model remains independent of Brian2Loihi. Reference-specific mapping
and compatibility rules stay in the adapter layer.
