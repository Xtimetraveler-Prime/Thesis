# FPGA-v2 / Loihi-1 Architectural Twin

This directory is the development home for the new source-backed Loihi-1 architectural digital twin.

Development authority is split between:

- `LOIHI_TWIN_ROADMAP.md` — the active phase/deliverable tracker;
- `docs/LOIHI1_TARGET_SPEC.md` — the normative source-backed architecture contract.

FPGA-v1 remains frozen under `../v1/`. No v2 implementation should silently import behavioral assumptions from v1 unless the target specification explicitly adopts them.

## P02 Python golden model

The independent v2 package lives under `src/loihi_twin_v2/`. It models logical resources, destination-side axons and synapse templates, explicit inter-core spike packets, logical cores, packet routing, timestep drain/advance barriers, deterministic deployment serialization, and multi-timestep replay separately from any future FPGA implementation.

Install and run its directed tests from this directory:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

Run the minimal two-core causality example:

```bash
python examples/run_two_core.py
```

Run the three-core serialization/replay example:

```bash
python examples/run_three_core_replay.py
```

Run the integrated P02 behavioral validator:

```bash
python scripts/validate_p02.py
```

The validator serializes/reloads a three-core recurrent deployment, executes it under different legal core-service and packet-drain orders, checks the expected four-timestep spike wave, and requires identical normalized trace fingerprints.

## P02 documents

- `docs/P02_IMPLEMENTATION_NOTES.md` records implementation choices and claim boundaries.
- `docs/P02_DEPLOYMENT_SCHEMA.md` defines the project deployment interchange document and fingerprint rules.

The current synapse-memory model (`v2-simple-32bit-entry`) is a documented project accounting choice, not a claim of exact Loihi SRAM bit packing. It is isolated behind `SynapseCostModel` so later native-style encoding work can replace it without changing logical routing behavior.
