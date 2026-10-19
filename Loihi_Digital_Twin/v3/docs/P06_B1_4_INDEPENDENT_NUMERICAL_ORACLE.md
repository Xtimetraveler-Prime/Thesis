# P06-B1.4 — Independent 26-tick integer LIF differential oracle

**Status:** host-only source/tests/diagnostic probes committed as **native user acceptance candidate**. No local pytest, GitHub CI PASS, trained 1000-hidden network or KV260 board result claimed in this authoring session.  
**Branch:** `agent/v3-p06-b1-scalable-packing`, draft PR #46, unmerged.  
**Prior verified gates (user-attested):** B1.1 capacity, B1.2 full synthetic dense 784→1000→10 27-core packed **structural** probe, and B1.3 multi-core streaming ABI regressions including follow-up bug-fix rerun all reported PASS. Do not modify any accepted Track A or originally sealed official MNIST TEST evidence.

## Scientific independence boundary

Three distinct components:

1. `p06_b14_monolithic.py` is a **true flat source-network reference**. It accepts original `NetworkSpec` directly, uses only per-population source graph edges and per-tick source input index tuples, without reading B1.2 core placements, template sharing, packed axons, P03 words, LogicalChip, or production `step_compartment`. Neuron numerical updates delegate to accepted standalone `p06_integer_oracle.LIFParameters/LIFState/lif_step/accumulate_synapses`, the earlier P06-A2 independent scalar integer oracle which itself has **no dependency** on production P03/LogicalChip arithmetic. This retains signed 64-bit synaptic accumulation, 24-bit saturating state/current, round-away-from-zero 4096-scale decay, strict threshold, bias, reset, and refractory semantics.
2. `p06_b14_differential.py` constructs a **separate production B1.2 LogicalChip** and compares all 26 core traces to the independent monolithic run, with first-divergence diagnostics. It derives source neuron and destination-core routing connectivity from the ORIGINAL `NetworkSpec` and placement (not production packet output as its own expected packet source), and rejects incorrect destination fanout or missing neurons.
3. `p06_b14_synthetic_fixtures.py` and `p06_b14_differential_probe.py` are synthetic only, explicitly **not** a trained weight checkpoint, not a physical P07-B or scaled A53 binary.

`pixel_schedule_independent` reproduces the raw uint8 deterministic phase-quota encoder by its mathematical definition, with no call to production `pixel_spikes`; tests compare them over zero, all-255, mid-level, ramp and deliberately varied pixel patterns. The 26-tick inference is **timestep-synchronized**, even though only present spike events contribute to the synaptic accumulator; this is not a physically asynchronous clockless neuromorphic chip.

## Exact independent checks at EVERY tick (0–25)

- All original neurons appear **exactly once**, independent of destination core and physical compartment index.
- For each neuron: **current/voltage/refractory state both before and after**, integer synaptic input (64-bit wrapped source contributions), and emitted spike flag.
- All 784 input source indices (or smaller synthetic explicit input populations) are canonical, sorted, nonduplicated, and checked independently of B1.2 mapping. A disconnected source input can legally emit a source event while producing zero destined packet events.
- Input event ingress groups per destination logical core and prior-epoch neural packet arrivals, checked from original source graph against actual `CoreTrace.packet_in` with source IDs decoded through the real B1.2 mapping.
- For each spiking original neural source, the direct original source network determines its set of destination **logical cores**. A single routed packet per source/destination core may expand to many synaptic connections in the destination core; this is why packet counts are **not synapse counts**. The checker verifies each `source core + original compartment + NEXT logical timestep + destination core` packet group and rejects missing, unexpected, duplicated or mis-timed packet destinations.
- Readout counts after **each** tick, final ten-neuron class by count, deterministic lowest-index winner on ties including all-zero output.
- Literal **25 input ticks plus one drain tick**; a neural spike emitting a packet on final tick 25 is rejected as it would target an unserviced epoch 26 in the currently defined one-image contract. Independent arbitrary recurrent graphs that cannot quiesce by the final drain are **not** silently declared valid.

Output: `B14Comparison.report()` exposes both monolithic source-derived and independently observed partitioned SHA256 trace fingerprints; exact comparison booleans, neuron/tick coverage and counts, route packet/external packet traffic, classification, and explicit `physical_kv260_execution=NOT_TESTED`, `official_mnist_test_access=NONE`. A fingerprint comparison is an integrity/diagnostic check, not a substitute for detailed per-neuron parity.

`B14Divergence` captures **first chronological tick**, named original neuron (when applicable), field name and expected/observed values. Mutable `ChipTrace` copies in tests deliberately alter one synaptic contribution, one state field and one NEXT timestamp to prove that the checker detects the first numerical/transport divergence even if the final output would otherwise agree.

## Regression scope

`tests/test_p06_b14_differential.py`:

- Hand-computed signed source graph: two hidden neurons both spike at t=0 from integer (+5,−2) and (−4,+9) sums, with readout0 first firing at **t=1**, readout1 receiving **−3+6=3** and remaining subthreshold; 10-class final first-class result. Check across several destination-core partition policies and both forward/reversed legal service orders.
- Zero input/tie/silence; image encoder parity; randomized fixed-seed negative weights, nonzero bias/reset, fractional 4096-scale decay and refractory; signed-24 extremes including saturation; malformed source schedules; dropped final-drain packets; deliberately corrupted source/time/state/contribution/packet vectors.
- Default all-255 dense **784→6→10** full 26-tick source-neuron parity through two hidden cores; 784×2=1,568 mapped ingress events each input epoch, six hidden packets/epoch reaching the common readout core, and 10 readout spikes across t=1..25.
- Optional more expensive **784→40→10 dense** all-255 26-tick numerical check against actual **39+1 hidden cores**, 31,760 synthetic network connections. This is a complete small dense analog of the proposed topology, not the entire 1000-hidden network.
- Optional **27 logical cores / 1000 hidden neurons / 784 pixels**, independently checked **sparse** synthetic input graph. Explicitly uses a 39-neuron/core configuration to force 26 hidden partitions. One special anchor neuron/core receives each of the 784 pixels to stress replicated ingress; all 1000 hidden neurons route to 10 readout neurons via 1,000 distinct readout axons. Every neuron/tick, 509,600 replicated input packet deliveries over 25 input ticks, 25,000 hidden→readout packets, readout counts and service-order invariance are checked. **It is not the earlier B1.2 794,000-connection dense graph**, and has not yet been accepted or exercised on KV260.
- The already user-verified B1.2 **dense 784→1000→10 structural placement** remains a distinct gate; do not claim a complete 26-tick full-DENSE numerical test or hardware throughput result unless it is separately run and verified.

## Native PC verification (no JTAG / KV260 access)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p06-b1-scalable-packing
git pull --ff-only origin agent/v3-p06-b1-scalable-packing
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

# First run B1.4 host-only numerical and mutation tests:
PYTHONPATH="$PWD/src" python -m pytest -q -rs tests/test_p06_b14_differential.py

# Re-run previously accepted Track B and Track A regression gates:
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p06_b13_streaming.py tests/test_p06_b12_partition.py \
  tests/test_p06_b1_contract.py tests/test_p06_lif_compiler_probe.py \
  tests/test_p06_lif_input_probe.py

# Syntax verification:
PYTHONPATH="$PWD/src" python -m compileall -q \
  src/loihi_twin_v2/p06_b14_monolithic.py \
  src/loihi_twin_v2/p06_b14_differential.py \
  src/loihi_twin_v2/p06_b14_synthetic_fixtures.py \
  scripts/p06_b14_differential_probe.py \
  tests/test_p06_b14_differential.py

# Default reproducible small dense 26-tick numerical parity report:
PYTHONPATH="$PWD/src" python scripts/p06_b14_differential_probe.py --shape dense6

# Optional larger host-only runs; run ONE at a time with sufficient PC RAM:
P06_B14_DENSE40=1 PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p06_b14_differential.py -k dense_784_to_40_to_10_full_numerical_26_ticks

PYTHONPATH="$PWD/src" python scripts/p06_b14_differential_probe.py --shape dense40

P06_B14_SPARSE27=1 PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p06_b14_differential.py -k 27_core_sparse_1000_hidden_26_tick_numerical_reference

PYTHONPATH="$PWD/src" python scripts/p06_b14_differential_probe.py --shape sparse27
```

Expected success marker on each script: `P06_B14_INDEPENDENT_DIFFERENTIAL_PASS=1`. The optional test may be slower and memory-intensive because it retains detailed per-core trace contributions across 26 ticks. **All native outcomes remain PENDING until the user runs and shares them.**

## Next: B1.5 (NOT STARTED)

Build a separately audited 3-resident-slot / 1-HLS-engine paging model:
deterministic per-epoch service, barrier and NEXT event buffers,
full page-in vs mutable page-out bytes, host scheduling order parity and
**estimated** unexecuted scaled DDR traffic/time. The P05 measured
physical page sizes and immutable Track A baseline remain the distinct
source of accepted hardware evidence. B1.6 then consolidates a SHA-bound
feasibility gate; scaled physical P07-B still needs separately authorized
safe DDR-owner/JTAG isolation and a distinct real A53 ingress ABI.

**Do not merge draft PR #46 without explicit user approval.**
