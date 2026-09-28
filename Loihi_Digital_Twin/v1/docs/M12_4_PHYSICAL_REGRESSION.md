# M12.4 Broad Deterministic Physical Regression

## Status

Complete on the physical KV260 on 2026-09-07.

## Purpose

M12.4 extends the directed physical conformance evidence from M12.2 and M12.3 with a broader deterministic corpus. The goal is not to replace the earlier hand-authored architectural probes, but to increase confidence that combinations of supported FPGA-v1 features continue to agree exactly between the independent Python golden model and the physical FPGA.

The computational core remains the frozen M11.5/M10 FPGA-v1 implementation. M12.4 adds validation workloads, packed input-image generation, a physical capture shell, exact differential reporting, and deterministic failure reproduction.

## Evidence boundary

The authority boundary remains the same as M12.2/M12.3:

```text
Python scenario/configuration
        |
        +--> Python golden trace
        |
        +--> FPGA-visible load image + external-event schedule
                     |
                     v
              physical FPGA
                     |
                     v
          JTAG/VIO trace capture
                     |
                     v
       exact host-side differential
```

The FPGA-visible generated SystemVerilog contains only static configuration/load data and per-tick external-event schedules. It contains no Python-golden expected state, spike, queue, or recurrent-event schedule. Recurrent inputs must be produced by the FPGA's own previous-tick routing state.

## Corpus

The new M12.4 physical corpus contains 22 deterministic cases totaling 166 committed algorithmic ticks:

- 16 seeded generated networks;
- 6 explicit finite-capacity / interaction stress workloads.

The stress layer includes high external-event multiplicity, dense synaptic fan-in, broad recurrent fan-out, a larger neuron population, a longer recurrent ring history, and a denser mixed recurrent workload. All cases remain within the frozen M11.5 physical capacity profile:

- 256 neurons;
- 1,024 axons;
- 4,096 synapses;
- 16 weight formats;
- 4,096 recurrent routes;
- 4,096 external events per tick;
- 4,096 recurrent events per tick.

M12.2's 16 directed single-tick cases and M12.3's 10 directed multi-tick cases remain retained physical regression anchors. They are not redundantly compiled into the M12.4 validation image.

## Deterministic reproduction metadata

Every M12.4 case carries:

- stable case ID;
- source kind (`seeded` or `stress`);
- generator version;
- fixed 64-bit seed;
- SHA-256 of the FPGA-visible configuration/load image;
- Python golden artifact name;
- physical trace artifact name;
- exact differential report name;
- targeted rerun command by case ID.

Variable-length case data is emitted as packed arrays with explicit offsets rather than rectangular maximum-stride padding. This keeps the 22-case validation image practical while preserving deterministic indexing.

If a case fails, it can be repeated without regenerating opaque randomness using:

```bash
bash run_m12_4_case.sh <case-id>
```

The case's seed and configuration hash are printed with the rerun metadata.

## Physical execution

The M12.4 Hardware Manager flow programs one K26 bitstream, selects each case through the host-controlled case index, performs a clean architectural reset/load, and advances one committed tick at a time. Each tick remains paused in the post-commit trace window while the host captures:

- committed tick;
- core fault and fault code;
- external-event count and payloads;
- consumed recurrent-event count and payloads;
- newly routed recurrent-event count and payloads;
- active recurrent queue bank and both bank counts;
- signed 64-bit synaptic input for every configured neuron;
- packed pre-tick and post-tick neuron state;
- spike vector.

The same passive route-target and recurrent-bank write witnesses retained from M12.2 remain available for diagnosis but do not feed architectural computation.

## Final physical result

The complete physical KV260 run completed successfully with the closure markers:

```text
M12.4 physical broad deterministic suite capture completed successfully: cases=22 ticks=166
M12.4 exact broad physical differential passed: cases=22 ticks=166 mismatches=0
M12.4 physical broad deterministic regression completed successfully.
```

Therefore:

```text
new M12.4 physical cases:     22
new M12.4 committed ticks:   166
failed cases:                  0
unexplained mismatches:        0
```

No M12.4 case required an accepted exception or change to the Python expectation.

## Interpretation

M12.4 provides physical evidence that exact Python-to-FPGA agreement survives a substantially broader deterministic workload space than the earlier directed suites. It covers varied generated topology/configuration combinations and selected larger stress conditions while preserving the same frozen FPGA-v1 semantics and physical observation boundary.

Together, the M12 physical evidence now includes:

```text
M12.1  reproducible physical trace boundary
M12.2  16/16 directed single-tick physical cases exact
M12.3  10 directed multi-tick scenarios / 40 ticks exact
        + independent six-tick reset/replay
M12.4  22 broader deterministic/stress cases / 166 ticks exact
```

This does not prove equivalence to undocumented Intel Loihi microarchitecture, nor does it exhaust every legal combination within the finite FPGA capacities. It establishes exact physical implementation of the explicitly frozen, externally informed Loihi-inspired FPGA-v1 computational subset across the agreed directed and broad deterministic validation corpus.

## M12.5 handoff

M12.4 closes behavioral validation coverage. M12.5 can now characterize the already validated implementation without changing its computational behavior. The remaining M12 work is to record final routed timing/resource evidence, derive and/or measure latency and throughput, characterize scaling, consolidate the supported-feature matrix and limitations, and assemble thesis-ready evidence. Power/energy should only enter the validated claim set if a trustworthy board-level measurement method is established.