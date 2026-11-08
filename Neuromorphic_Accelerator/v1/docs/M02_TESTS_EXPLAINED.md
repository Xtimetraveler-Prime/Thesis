# M02 — What the independent neural-reference tests actually validate

**Status:** PC-only candidate **M02** software neural contract. No hardware, physical DDR, end-to-end inference performance, trained-network accuracy, or Loihi silicon fidelity. Numeric choices are **provisional** and require user review before freezing.

## What is being tested

Two implementations consume the identical immutable `Network` and `InputCurrent` definitions in `src/neuromorphic_accelerator_v1/m02_types.py`:

- **`m02_dense_reference.py`:** for each timestep and neuron, scans the external inputs and all network edges, looking backward at previous presynaptic spike rows to calculate incoming current. Performs explicit scalar decay, saturation, threshold and reset.
- **`m02_event_reference.py`:** indexes outgoing edges and schedules each emitted spike into a *future tick* bucket; at each tick collects/delivers scheduled synaptic currents, then independently calculates the same LIF rule.

**Important:** Neither evaluator skips inactive neurons. The event-queued version is event-driven only for **synaptic propagation**, not for neuron updates; bias or other dynamics can cause spikes without input. Neither implementation is a physical scheduler or a Loihi-specific emulator. The two implementations intentionally **do not share arithmetic or routing code**, although they share input dataclasses and validation.

The proposed numerical rule is documented in [M02_PROVISIONAL_LIF_CONTRACT.md](M02_PROVISIONAL_LIF_CONTRACT.md): signed saturating state, integer decay with **truncation toward zero**, bias and synaptic input summed **before saturation**, inclusive threshold, reset, and positive synaptic delays of at least one logical timestep. Parallel/negative edges are legal and delayed recurrent connections are tested. Refractory periods, a separate synaptic-current state, learning and event-free fast-forwarding are not implemented.

## Actual test suite and how it works

**21 Python `unittest` test methods** across `tests/test_m02_reference.py` (16) and `tests/test_m02_cli.py` (5). The reference test methods include additional `subTest` repetitions and **50 independent seeded random networks** in one differential method.

### Neural correctness (16 methods)

| Test area | Mechanism / expected observation |
| --- | --- |
| Threshold equality | Hand-calculated `(3,0,2,1)` voltage sequence, one emitted spike at tick 1; membrane resets when candidate **equals** threshold. |
| Negative leak truncation | A voltage of `-3` decayed by `1/2` produces `-1`, not Python-floor `-2`; tests repeated negative bias and quiet updates. |
| Quiet bias | A neuron with bias `+3`, threshold `5` spikes at ticks `1` and `3` **without any input event**. |
| Signed saturation | Inputs are summed then clipped to 8-bit `[-128,127]` **before** threshold comparison; negative underflow and positive overflow checked. |
| Duplicate/current ordering | Multiple `+100,+100,-100` events produce exactly `+100` rather than per-event saturation artifacts; event order permutations must agree. |
| Negative/parallel synapses | Two parallel weights `+20,-7` combine to `+13` after a source spike; exact destination voltage checked. |
| Recurrent delays | `0→1` delay 2 then `1→0` delay 1 produces spikes `(0,0),(2,1),(3,0)`, no illegal same-tick recursion. |
| Delayed self edge | A neuron can trigger its own future spike with positive delay; no zero-delay self-loop accepted. |
| Last-tick boundary | An input on the final requested tick is processed; its outgoing synapse beyond the horizon does not wrap around. |
| Unsorted inputs | Reversing event order changes neither results nor sorted output; duplicate spike emissions per neuron/tick are not created. |
| Leak endpoints | Decay ratios 0 and 1 have hand-calculated voltage trajectories. |
| Large parallel current | `20×127 + 19×(-127)` sums exactly before saturation; one output spike. |
| Invalid-contract matrix | Empty networks, bad widths, bool-as-int, out-of-range values, reset/threshold incompatibility, delay=0, invalid neuron indices, invalid current/time and non-event input are rejected by **both** implementations. |
| Randomized differential | 50 deterministic generated recurrent/feedforward networks with random signed weights, delays, current events, biases and initial states; **every per-tick voltage and spike row must match**. This verifies internal parity, not external brain-simulation truth. |
| Canonical SHA | A **hand-calculated multi-tick two-neuron fixture** has a pinned exact JSON trace SHA256 (`8bbb6530...08b0db3b`), expected spike rows, and unchanged original input list. This prevents an accidental self-comparison from passing. |
| Input iterator | Both evaluators accept one-pass event iterators and produce identical rows. |

### Report/original-provenance safeguards (5 methods)

- The four curated fixtures plus seeded random cases reproduce **deterministic JSON** with explicit schema, per-case input SHA256 and state/spike trace SHA256.
- The first three curated fixtures have asserted spike/output sequences in the report.
- Bad seed or random-case counts are rejected.
- The report generator **refuses to overwrite** an existing JSON file and preserves its original bytes.
- The report explicitly disclaims device measurement and acknowledges that even the queued event evaluator updates every neuron each tick.

### GitHub Actions workflow checks

`.github/workflows/neuromorphic_accelerator_m02_pc_only.yml` uses Ubuntu Python only:

1. Compile `src`, `scripts` and `tests`.
2. Run all **21** M02 standard-library tests with verbose output.
3. Reproduce a **54-case report** (four hand-curated fixtures + 50 seeded generated networks); assert dense/event parity, fixed expected spikes and source labels.
4. Deliberately attempt a second write to the same JSON and an invalid negative case count. **Both commands must fail**.
5. Run the previous **20 M01 regression tests** to ensure the accepted traffic study has not regressed.
6. Assert a one-neuron golden trace independently of the other assertions and upload the new PC-only report as a GitHub Actions artifact.

**Meaning of PASS:** The two independent software implementations agree under the specified provisional numerical contract and the immutable fixtures match. **Not proven:** equivalence to v3's different numerical contract or YANA's leak approximation, valid hardware idle-skipping, any performance/sparsity advantage, synthesizability, correctness of an unimplemented FPGA engine, trained-model accuracy or power.

## Source transparency and next acceptance gate

All tests use public Python standard library—no copied YANA or third-party RTL. The LIF equations are established prior art, not claimed as a new neural algorithm. The user must independently run [M02 local operator runbook](M02_PC_ONLY_VERIFICATION.md) and review the [provisional mathematical contract](M02_PROVISIONAL_LIF_CONTRACT.md) **before M02 is accepted or any code becomes the frozen v1 neural specification**.
