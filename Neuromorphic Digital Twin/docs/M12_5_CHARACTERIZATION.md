# M12.5 FPGA Characterization

## Status

In progress on branch `agent/m12-5-fpga-characterization`.

M12.5 begins only after M12.1-M12.4 establish exact physical behavioral conformance of the frozen FPGA-v1 architecture. The characterization work therefore treats the M10/M11.5 computational core as fixed. Performance instrumentation may observe the validated implementation but must not alter arithmetic, state transitions, event ordering, routing, queue semantics, or the physical trace contract.

## Characterization goals

M12.5 records thesis-ready evidence for:

- routed resource utilization;
- routed setup/hold timing at the frozen 100 MHz target clock;
- physical architectural-tick latency in PL clock cycles;
- derived tick, neuron-update, input-event, and actual synapse-visit throughput;
- scaling across the already validated deterministic workload corpus;
- supported architectural scope and finite implementation limits;
- explicit limitations and excluded claims.

Power/energy is intentionally outside the validated M12.5 claim set unless a trustworthy calibrated board-level measurement method is established. No estimate derived only from synthesis activity or informal board observations should be presented as measured physical energy.

## Frozen implementation boundary

M12.5 reuses the exact 22-case / 166-tick M12.4 workload authority. The generated FPGA-visible corpus continues to use the `M12_4_*` input-array names intentionally. There is no new M12.5 behavioral workload definition and no change to the Python golden expectation.

The characterization image adds one passive 32-bit value:

```text
observed_last_tick_cycles
```

The counter measures PL `ap_clk` periods from the architectural `tick_start` acceptance edge through the edge on which the capture shell observes outer-core `tick_done`. It does not feed any computational-core input, load path, event path, recurrent route path, or trace-read path.

Because instrumentation changes the implemented image, the M12.5 physical run must repeat the full M12.4 exact trace differential before any performance result is accepted. The characterization pass boundary therefore contains two simultaneous requirements:

```text
passive characterization image
        |
        +--> 22 cases / 166 physical ticks
        |       exact vs independent Python golden model
        |       zero mismatches required
        |
        +--> 166 positive per-tick cycle measurements
                |
                +--> resource/timing/throughput/scaling analysis
```

## Timing interpretation

The validation-capable K26 design targets:

```text
target clock: 100 MHz
target period: 10.0 ns
```

Routed worst setup slack (WNS) and worst hold slack (WHS) are reported from Vivado implementation. Positive WNS/WHS demonstrates that the 100 MHz target timing constraint is met. M12.5 does **not** infer or claim a maximum achievable clock frequency merely by algebraically converting WNS into a nominal frequency; such a value would require a separate implementation sweep at tighter constraints.

## Tick-cycle measurement

Wall-clock Hardware Manager/JTAG time is deliberately excluded from architectural latency. JTAG polling and trace reads are host/debug overhead and do not represent core execution.

For every committed tick, the board records one positive integer cycle count while the host continues to capture the complete post-commit architectural trace. The cycle TSV uses the frozen schema:

```text
case_id
case_name
tick
cycles
external_events
recurrent_events
routed_events
```

The event counts in the measurement record are validated against the independent Python golden timeline before performance metrics are calculated.

At 100 MHz:

```text
latency_ns = cycles * 10 ns
ticks_per_second = 100,000,000 / cycles
neuron_updates_per_second = configured_neurons * ticks_per_second
input_events_per_second = (external_events + recurrent_events) * ticks_per_second
```

Actual synapse processing is characterized as **CSR synapse visits**, not merely event count. For each external or recurrent input axon consumed on a tick, the analyzer uses the frozen packed weight-row pointers to count the exact number of synapse entries traversed, preserving repeated-event multiplicity:

```text
synapse_visits = sum(row_end[axon] - row_start[axon] for each consumed event)
synapse_visits_per_second = synapse_visits * ticks_per_second
```

This metric is appropriate to the serialized Phase-B implementation and avoids implying that every input event performs exactly one synaptic operation.

## Scaling evidence

M12.5 characterizes all 166 already validated M12.4 ticks rather than introducing a separate synthetic benchmark. Per-tick evidence records:

- configured neuron count;
- axon count;
- configured synapse count;
- route count;
- external and recurrent event counts;
- newly routed event count;
- actual CSR synapse visits;
- measured cycles and latency;
- derived throughput metrics.

A workload-level `case_scaling.csv` aggregates each of the 22 deterministic cases with min/mean/max cycles and total event/synapse-visit activity. These are descriptive physical measurements. M12.5 should not claim a universal asymptotic performance law from only this finite corpus.

## Resource evidence

The final routed characterization image records at minimum:

- CLB LUTs / available LUTs;
- CLB registers / available registers;
- conservative BRAM-tile upper bound, plus RAMB36/RAMB18 primitive counts;
- DSPs / available DSPs;
- URAM / available URAM;
- routed WNS and WHS;
- target part and target clock.

The characterization image includes debug/VIO and passive measurement logic, so its reported top-level utilization represents the **validation-capable characterization image**, not an optimized minimal neuromorphic core.

## Supported feature matrix

| Area | Validated FPGA-v1 scope |
| --- | --- |
| Neuron arithmetic | Integer current-based LIF-style state transition under the frozen M10 ordering |
| State precision | Signed 24-bit saturating current and voltage |
| Decay | 13-bit decay controls on the frozen 0..4096 scale and frozen integer rounding behavior |
| Threshold | Strict threshold comparison under the frozen M10 contract |
| Reset/refractory | Frozen reset voltage and 16-bit refractory state/timing behavior |
| Bias | Frozen signed bias contribution |
| Static weights | M08 Loihi-style project representation with mantissa, exponent, precision, and sign mode |
| Synaptic accumulation | Signed 64-bit exact tick-local accumulation before state arithmetic |
| Event multiplicity | Preserved; repeated events are not deduplicated |
| Input ordering | External events before recurrent events under the frozen deterministic contract |
| Recurrent delivery | Spike-generated recurrence is delivered on the next architectural tick only |
| Recurrent storage | Deterministic CSR routes and double-buffered recurrent queues |
| Trace semantics | Atomic post-commit trace window with pre/post state, synaptic input, spikes, external/recurrent/routed events, queue metadata, and faults |
| Physical capacities | 256 neurons, 1,024 axons, 4,096 synapses, 16 weight formats, 4,096 routes, 4,096 external events/tick, 4,096 recurrent events/tick |
| Physical evidence | M12.2 16/16 directed single-tick cases; M12.3 10 scenarios/40 ticks plus reset/replay; M12.4 22 broad cases/166 ticks, all exact |

## Explicit limitations

The validated claim does not include:

- Intel Loihi's undocumented physical microarchitecture, SRAM organization, timing, or NoC implementation;
- a complete Loihi processor feature set;
- online plasticity or learning rules;
- multicore mesh/NoC behavior;
- unsupported programmable synaptic-delay mechanisms outside the frozen recurrent next-tick model;
- production Linux/FPGA-manager integration (the accepted validation path is direct JTAG/VIO with the stock PL application unloaded when necessary);
- an optimized high-throughput implementation—the current architecture deliberately serializes substantial work for transparency and exact verification;
- measured power or energy unless a trustworthy board-level method is separately established;
- maximum Fmax beyond the demonstrated routed 100 MHz target;
- exhaustive validation of every mathematically legal configuration inside the finite capacities.

## Generated evidence

After the physical characterization run, M12.5 produces:

```text
build/m12_5/reports/                         routed Vivado reports
build/m12_5/m12_5_vivado.log                implementation/timing log
build/m12_5/captures/*.physical.json        22 full physical traces
build/m12_5/differential_reports/           exact Python↔FPGA revalidation
build/m12_5/m12_5_tick_cycles.tsv           166 physical cycle measurements
build/m12_5/characterization/characterization.json
build/m12_5/characterization/tick_characterization.csv
build/m12_5/characterization/case_scaling.csv
build/m12_5/characterization/CHARACTERIZATION_SUMMARY.md
```

Final numerical results and thesis-level interpretation will be added only after the characterization image routes successfully, repeats the 22-case/166-tick zero-mismatch physical result, and produces valid cycle measurements.