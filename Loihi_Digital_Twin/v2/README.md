# FPGA-v2 / Loihi-1 Architectural Twin

This directory is the development home for the new source-backed Loihi-1 architectural digital twin.

Development authority is split between:

- `LOIHI_TWIN_ROADMAP.md` — the active phase/deliverable tracker;
- `docs/LOIHI1_TARGET_SPEC.md` — the normative source-backed architecture contract.

FPGA-v1 remains frozen under `../v1/`. No v2 implementation should silently import behavioral assumptions from v1 unless the target specification explicitly adopts them.

## P02 Python golden model — complete

The independent v2 package lives under `src/loihi_twin_v2/`. It models logical resources, destination-side axons and synapse templates, explicit inter-core spike packets, logical cores, packet routing, timestep drain/advance barriers, deterministic deployment serialization, and multi-timestep replay separately from the FPGA implementation.

Install and run its directed tests from this directory:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

P02 closed with 26 tests passing plus verified two-core causality and three-core recurrent schedule invariance.

Supporting material:

- `docs/P02_IMPLEMENTATION_NOTES.md`
- `docs/P02_DEPLOYMENT_SCHEMA.md`
- `scripts/validate_p02.py`
- `examples/run_two_core.py`
- `examples/run_three_core_replay.py`

## P03 one-core FPGA-v2 implementation — active

P03 translates one verified P02 logical core into a synthesizable, transparent hardware boundary.

The packed memory/export layer is:

```text
src/loihi_twin_v2/hardware_p03.py
```

The source-level hardware contract is:

```text
docs/P03_ONE_CORE_HARDWARE_BOUNDARY.md
```

The first HLS core is:

```text
hls/core_v2/
├── include/loihi_core_v2.hpp
├── src/loihi_core_v2.cpp
├── tb/test_loihi_core_v2.cpp
├── hls_config.cfg
├── run_csim.sh
└── run_synth_cosim.sh
```

The HLS testbench does not use hand-entered expected behavior. Before compilation, `examples/generate_p03_hls_vectors.py` runs the P02 Python `LogicalCore` and emits a deterministic five-timestep differential corpus covering shared synapse templates, positive/negative weights, refractory behavior, state persistence, spike generation, and explicit output routing.

With Vitis/Vivado 2025.2 on `PATH`:

```bash
export HLS_PART='xck26-sfvc784-2LV-c'
bash hls/core_v2/run_csim.sh
```

After C simulation passes:

```bash
bash hls/core_v2/run_synth_cosim.sh
```

The synthesis/co-simulation result is the next P03 gate. Its timing, inferred interfaces/memories, resource use, and RTL behavior will determine the Vivado/K26 wrapper without changing the normalized one-core architecture contract.

## Resource-accounting boundary

The current logical synapse-memory model (`v2-simple-32bit-entry`) is a documented project accounting choice, not a claim of exact Loihi SRAM bit packing. P03 intentionally distinguishes this logical mapping budget from physical FPGA storage width and will report synthesized BRAM/URAM use separately.
