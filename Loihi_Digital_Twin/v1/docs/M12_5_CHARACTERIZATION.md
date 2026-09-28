# M12.5 FPGA Characterization

## Status

**Complete — physical KV260 characterization accepted on 2026-09-07.**

M12.5 closes the physical-validation phase of M12. It begins from the already validated M10/M11.5 FPGA-v1 computational core and treats that core as frozen. The characterization image adds observability only; it does not change arithmetic, state transitions, event ordering, routing, recurrent queue semantics, or the M12 physical trace contract.

The accepted physical characterization image successfully:

- routed on `xck26-sfvc784-2LV-c` at the frozen 100 MHz target;
- met both routed setup and hold timing;
- executed the complete frozen M12.4 22-case / 166-tick workload corpus;
- reproduced the independent Python FPGA-v1 golden trace exactly for all 166 committed physical ticks with **zero mismatches**;
- emitted one positive PL-cycle measurement for every committed tick;
- produced machine-readable resource, timing, latency, throughput, and workload-scaling artifacts;
- remained reproducible through the source-controlled M12.5 bitstream, board-capture, exact-differential, and host-analysis commands.

The decisive physical completion markers were:

```text
M12.5 physical characterization capture completed successfully: cases=22 ticks=166
M12.4 exact broad physical differential passed: cases=22 ticks=166 mismatches=0 devices=xck26_0
M12.5 characterization assembled: ticks=166 cycles_min=26 cycles_mean=379.10 cycles_max=8218 WNS=0.493ns WHS=0.011ns
M12.5 physical characterization completed successfully.
```

The separate host-only analysis rerun also completed successfully from the preserved raw physical measurements, proving that the numerical characterization can be regenerated without repeating FPGA execution when only tables or interpretation change.

---

## Why the M12.5 result is strong

The most important M12.5 result is not any single throughput number. It is that the **instrumented characterization image remained behaviorally exact**.

Instrumentation necessarily changes the physical implemented image. A performance result would be much weaker if the project simply assumed that the added counter and VIO visibility were harmless. Instead, M12.5 repeats the entire M12.4 broad physical differential on the characterization image itself. Performance data is accepted only after that image proves the same 22/22-case, 166/166-tick, zero-mismatch behavior against the independent Python golden model.

The evidence boundary is therefore:

```text
frozen Python FPGA-v1 workload + expectation
                    |
                    v
M12.5 characterization image
  = validated M12.4 computational behavior
  + passive PL-cycle counter
                    |
         +----------+-----------+
         |                      |
         v                      v
full physical trace       cycle measurement
         |                      |
         v                      |
exact Python differential       |
zero mismatches required        |
         |                      |
         +----------+-----------+
                    v
       accepted characterization
```

This prevents a common validation mistake: measuring the performance of an instrumented design without independently proving that the instrumented design still implements the intended computation.

---

## Frozen implementation boundary

M12.5 reuses the exact 22-case / 166-tick M12.4 workload authority. The generated FPGA-visible corpus continues to use the `M12_4_*` input-array names intentionally. There is no separate M12.5 behavioral workload definition and no change to the Python golden expectation.

The characterization image adds one passive 32-bit value:

```text
observed_last_tick_cycles
```

The counter measures PL `ap_clk` periods from architectural `tick_start` acceptance through the edge on which the capture shell observes outer-core `tick_done`.

The counter is deliberately outside the computational core. It does not feed:

- neuron configuration;
- neuron state;
- packed M08 weight storage;
- external event memory;
- recurrent event memory;
- synaptic accumulation;
- spike generation;
- recurrent route CSR storage;
- recurrent bank selection or queue swapping;
- architectural tick control;
- physical trace-read data.

The final branch diff therefore adds a characterization wrapper/shell and analysis infrastructure without modifying the existing frozen computational-core RTL files.

---

## Final physical implementation results

### Target and clock

```text
device:        xck26-sfvc784-2LV-c
board path:    KV260 / K26
PL clock:      100 MHz
target period: 10.0 ns
transport:     direct JTAG + VIO
```

The accepted board procedure keeps the PS available as the known-good `pl_clk0` source and unloads the stock Kria PL application before direct JTAG replacement when necessary.

### Routed timing

| Metric | Result | Interpretation |
| --- | ---: | --- |
| Target period | 10.000 ns | Frozen 100 MHz implementation target |
| Worst setup slack (WNS) | **+0.493 ns** | Setup timing passes |
| Worst hold slack (WHS) | **+0.011 ns** | Hold timing passes |

Both routed slacks are positive, so the characterization image meets the frozen 100 MHz target.

The setup result corresponds to 4.93% of the target 10 ns period remaining as positive setup margin. This is a timing-margin description only. M12.5 does **not** convert WNS into a claimed maximum Fmax. A maximum-frequency claim would require a separate implementation sweep with progressively tighter clock constraints and repeated routed closure.

The small positive hold margin is also recorded explicitly rather than hidden. The accepted routed image has positive hold slack, which is the relevant closure criterion.

### Final top-level resource utilization

The characterization image includes the computational core, broad-corpus load image, VIO/debug shell, physical trace path, and passive timing counter. These values therefore characterize the **validation-capable physical image**, not a stripped-down or throughput-optimized neuromorphic core.

| Resource | Used | Available | Device fraction |
| --- | ---: | ---: | ---: |
| CLB LUTs | **4,424** | 117,120 | **3.78%** |
| CLB registers | **4,280** | 234,240 | **1.83%** |
| BRAM tiles | **<=18** | 144 | **<=12.50%** |
| RAMB36 primitives | 15 | — | included in BRAM bound |
| RAMB18 primitives | 5 | — | included in BRAM bound |
| DSPs | **2** | 1,248 | **0.16%** |
| URAM | **0** | 64 | **0.00%** |

The BRAM figure is intentionally conservative. The report parser uses:

```text
BRAM_TILE_upper_bound = RAMB36 + ceil(RAMB18 / 2)
                      = 15 + ceil(5 / 2)
                      = 18
```

This cannot understate tile consumption. It may overstate it if some 18 Kb primitives are packed into common physical 36 Kb tiles, so documentation retains the `<=18` notation rather than pretending the conservative count is an exact placement-level tile occupancy.

The result leaves substantial capacity on the K26. That should not be interpreted as proof that all logical capacities can be scaled proportionally: the current implementation is deliberately serialized and its memory organization, route/event limits, timing behavior, and generated validation image impose separate constraints.

---

## Physical behavioral revalidation on the characterization image

The complete M12.4 corpus was rerun physically after the cycle counter and M12.5 VIO signal were added.

All 22 cases passed:

```text
00 seeded-00                         PASS
01 seeded-01                         PASS
02 seeded-02                         PASS
03 seeded-03                         PASS
04 seeded-04                         PASS
05 seeded-05                         PASS
06 seeded-06                         PASS
07 seeded-07                         PASS
08 seeded-08                         PASS
09 seeded-09                         PASS
10 seeded-10                         PASS
11 seeded-11                         PASS
12 seeded-12                         PASS
13 seeded-13                         PASS
14 seeded-14                         PASS
15 seeded-15                         PASS
16 stress-external-multiplicity-1024 PASS
17 stress-dense-fanin-256-synapses   PASS
18 stress-recurrent-fanout-256       PASS
19 stress-neuron-population-128      PASS
20 stress-recurrent-ring-32-ticks    PASS
21 stress-mixed-dense-history        PASS
```

Final exact differential:

```text
cases:      22 / 22 pass
ticks:      166 / 166 exact
mismatches: 0
device:     xck26_0
```

This is the accepted M12.5 behavioral gate. No expected value was changed to accommodate hardware output, no mismatch was waived, and no characterization result is accepted from a behaviorally divergent image.

---

## Tick-cycle measurement definition

Wall-clock Hardware Manager/JTAG time is deliberately excluded from architectural latency. Host polling, VIO refresh, trace reads, JSON writing, and Python differential analysis are validation/debug overhead; they are not core execution.

For every committed tick, the board records one positive cycle count. The cycle TSV schema is frozen as:

```text
case_id
case_name
tick
cycles
external_events
recurrent_events
routed_events
```

Before performance metrics are calculated, the analyzer verifies that the recorded event counts agree with the independently generated Python-golden timeline for that exact case and tick.

At the frozen 100 MHz clock:

```text
latency_ns = cycles * 10 ns
ticks_per_second = 100,000,000 / cycles
neuron_updates_per_second = configured_neurons * ticks_per_second
input_events_per_second = (external_events + recurrent_events) * ticks_per_second
```

Synaptic processing is characterized as **actual CSR synapse visits**, not merely input-event count. For each consumed external or recurrent axon event, the analyzer follows the frozen packed row pointers and counts the number of stored synapse entries traversed:

```text
synapse_visits =
    sum(row_end[axon] - row_start[axon] for every consumed event)

synapse_visits_per_second = synapse_visits * ticks_per_second
```

Repeated events remain repeated in this count. This is important because event multiplicity is architecturally meaningful in the FPGA-v1 contract and because one event can visit zero, one, or many synapses depending on its CSR row.

---

## Aggregate measured latency

Across all 166 physical committed ticks:

| Metric | Cycles | Time at 100 MHz |
| --- | ---: | ---: |
| Minimum | **26** | **260 ns / 0.260 us** |
| Mean | **379.10** | **3,791 ns / 3.791 us** |
| Maximum | **8,218** | **82,180 ns / 82.180 us** |

The wide range is expected and desirable for this first implementation: execution is deliberately serialized, so cost depends on neuron population, event count, synapse-row length, recurrent-copy activity, and routed-event fanout.

A single average therefore does not adequately describe the implementation. The workload-level stress cases below are more useful for understanding what drives latency.

### Corpus-weighted derived throughput

The 22 workload summaries imply 62,931 total PL cycles across the 166 measured ticks, or **629.31 us** of back-to-back architectural execution at 100 MHz. Summing the workload metadata gives:

```text
committed ticks:        166
neuron updates:       2,035
input events:         2,231
CSR synapse visits:   4,084
routed output events:   725
```

If those same 166 ticks are considered back-to-back with no JTAG/host gaps, the corpus-weighted derived rates are approximately:

| Derived corpus-weighted rate | Value |
| --- | ---: |
| Architectural ticks | **263,781 ticks/s** |
| Neuron updates | **3.234 million updates/s** |
| Input events consumed | **3.545 million events/s** |
| CSR synapse visits | **6.490 million visits/s** |
| Routed output events | **1.152 million events/s** |

These are descriptive rates for this finite mixed corpus, not a universal benchmark or guaranteed sustainable rate for arbitrary networks. In particular, averaging per-tick reciprocal latency is different from dividing aggregate work by aggregate execution time; thesis discussion should use the latter when describing a complete workload and retain the per-tick fields when discussing individual execution states.

---

## Stress-case scaling results

The six selected stress cases intentionally isolate different cost drivers.

| Case | Main stressor | Ticks | Neurons | Synapses | Routes | Total input events | Total CSR visits | Total routed | Cycles min / mean / max |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 16 | external multiplicity | 2 | 1 | 1 | 0 | 1,024 | 1,024 | 0 | **26 / 4,122 / 8,218** |
| 17 | dense fan-in | 2 | 32 | 256 | 0 | 32 | 256 | 0 | **522 / 1,098 / 1,674** |
| 18 | recurrent fanout | 3 | 2 | 257 | 256 | 257 | 257 | 256 | **42 / 1,154 / 2,858** |
| 19 | neuron population | 2 | 128 | 128 | 0 | 128 | 128 | 0 | **2,058 / 2,570 / 3,082** |
| 20 | long recurrent ring | 32 | 16 | 16 | 16 | 32 | 32 | 32 | **276 / 278.906 / 279** |
| 21 | mixed dense history | 12 | 32 | 256 | 128 | 440 | 1,760 | 340 | **834 / 1,388 / 1,798** |

### Case 16 — 1,024 repeated external events

The workload is deliberately simple:

```text
1 neuron
1 axon
1 synapse in the axon's row
no recurrent routes
external schedule:
  tick 1 -> 1024 copies of axon 0
  tick 2 -> empty
```

The physical costs are:

```text
quiescent tick: 26 cycles
1024-event tick: 8218 cycles
increment:       8192 cycles
```

Because every event visits exactly one synapse:

```text
8192 / 1024 = 8 additional cycles per event/synapse pair
```

This is a very clean demonstration of the serialized event-processing cost and also proves that event multiplicity is not collapsed in hardware.

### Case 17 — 32 events traversing 256 synapses

This case has 32 neurons and 32 axons, with eight synapses in every axon row. The first tick delivers all 32 axons; the second is empty.

Measured:

```text
empty 32-neuron tick: 522 cycles
active tick:          1674 cycles
increment:            1152 cycles
```

The active tick contains:

```text
32 input events
256 CSR synapse visits
```

The increment decomposes exactly as:

```text
4 * 32 events + 4 * 256 synapse visits
= 128 + 1024
= 1152 cycles
```

This separates event-loop overhead from actual row traversal more clearly than an event/s metric alone.

### Case 19 — neuron-population scaling

This case has 128 neurons, 128 one-synapse axons, no recurrent routes, one fully active external tick, and one empty tick.

Measured:

```text
empty 128-neuron tick: 2058 cycles
active 128-event tick: 3082 cycles
increment:             1024 cycles
```

The one-neuron empty tick from case 16 is 26 cycles. The two isolated quiescent points are exactly consistent with:

```text
quiescent_cycles = 16 * neuron_count + 10

N=1:   16*1   + 10 = 26
N=128: 16*128 + 10 = 2058
```

The active increment is again:

```text
128 events * 8 cycles/event = 1024 cycles
```

This does **not** establish a universal asymptotic timing law for all possible workloads. It establishes a strong empirical timing decomposition for the deliberately isolated no-route cases in this implementation.

### Case 18 — recurrent fanout

The first neuron is driven by one external event and emits one spike. That spike fans out to 256 recurrent target axons. On the next tick those 256 recurrent events are copied into the core and consumed.

Measured range:

```text
42 .. 2858 cycles
```

The three-tick total is:

```text
3 * 1154 = 3462 cycles
```

The measurements are exactly consistent with the isolated costs above plus:

```text
3 additional cycles per consumed recurrent event
2 additional cycles per newly routed output event
```

For the route-producing tick:

```text
2-neuron quiescent base = 16*2 + 10 = 42
1 external event + 1 visit = 8
256 routed outputs * 2 = 512
--------------------------------
42 + 8 + 512 = 562 cycles
```

For the following 256-recurrent-event tick:

```text
base = 42
256 input events * 4 = 1024
256 synapse visits * 4 = 1024
256 recurrent copies * 3 = 768
--------------------------------
42 + 1024 + 1024 + 768 = 2858 cycles
```

The remaining empty tick is 42 cycles, producing the measured total of 3462 cycles.

### Case 20 — 32-tick recurrent ring

This is one of the strongest stateful performance observations in M12.5. Sixteen neurons form a ring; a single initial external event starts activity and all remaining ticks rely on physical next-tick recurrence and repeated queue swaps.

Across all 32 committed ticks:

```text
minimum: 276 cycles
mean:    278.90625 cycles
maximum: 279 cycles
```

The first external-input tick is consistent with:

```text
base for 16 neurons: 16*16 + 10 = 266
1 external event + 1 synapse visit: 8
1 routed event: 2
--------------------------------------
276 cycles
```

Every steady recurrent tick is consistent with:

```text
266 base
+ 4 input-event cycles
+ 4 synapse-visit cycles
+ 3 recurrent-copy cycles
+ 2 routed-output cycles
= 279 cycles
```

The observed 276-to-279-cycle spread therefore has a concrete architectural explanation rather than measurement noise. It also shows that the recurrent double-buffered path behaves deterministically over a long physical state history.

### Case 21 — mixed dense history

This case deliberately combines features rather than isolating one cost:

```text
32 neurons
64 axons
256 configured synapses
128 recurrent routes
12 ticks
440 total consumed input events
1760 total CSR synapse visits
340 routed output events
mixed weight formats
state/history variation
```

Measured:

```text
minimum:  834 cycles
mean:    1388 cycles
maximum: 1798 cycles
```

The workload-level totals correspond to approximately:

```text
72,046 aggregate ticks/s
2.642 million aggregate input events/s
10.567 million aggregate CSR synapse visits/s
```

for this specific 12-tick workload at 100 MHz when considered back-to-back without host/debug gaps.

This case is especially useful in the thesis because it shows that the implementation remains exact under combined weight-format, dense-synapse, routing, event, and state-history pressure—not only in isolated microbenchmarks.

---

## Empirical cycle-accounting model exposed by the stress suite

Taken together, the deliberately isolated stress cases expose a useful implementation-level cycle model.

The measurements are exactly consistent with the following components for the exercised serialized paths:

```text
quiescent neuron/tick cost:     16 cycles per configured neuron + 10 fixed cycles
input-event handling:            4 cycles per consumed input event
CSR synapse traversal:           4 cycles per visited synapse entry
recurrent-bank copy:             3 additional cycles per consumed recurrent event
recurrent output routing:        2 cycles per newly routed output event
```

A compact form is:

```text
C ≈ 16*N + 10 + 4*I + 4*S + 3*R + 2*O
```

where:

```text
N = configured neurons
I = total consumed input events (external + recurrent)
S = actual CSR synapse visits
R = consumed recurrent events
O = newly routed output events
```

For the deliberately isolated stress cases above, the equation reproduces the measured cycle totals exactly.

This is an **implementation timing decomposition**, not part of the frozen M10 behavioral semantics and not a claim about Intel Loihi timing. It should be presented as an observed consequence of this project's transparent serialized FSM/HLS architecture. It is useful precisely because the FPGA digital twin exposes these architectural costs explicitly.

The project should also avoid turning this into an unsupported universal law. Other future extensions—additional pipeline stages, different memory implementations, multicore routing, plasticity, or a redesigned parallel datapath—would change these coefficients while leaving the high-level FPGA-v1 computational semantics potentially unchanged.

---

## Throughput interpretation

The implementation is intentionally not optimized as a high-throughput accelerator. M12 prioritized:

1. explicit state and ordering;
2. independent software/hardware equivalence;
3. reproducible physical observability;
4. deterministic recurrent semantics;
5. transparent cost attribution.

As a result, latency scales with actual serialized work. This is scientifically useful for the thesis because it connects the architectural choices to measurable FPGA cost.

The generated `tick_characterization.csv` retains per-tick instantaneous derived rates. The workload `case_scaling.csv` retains arithmetic means of those per-tick rates alongside min/mean/max cycle counts. When discussing sustained work over a complete workload, the more defensible quantity is:

```text
aggregate_rate = total_work / total_measured_PL_cycles * 100 MHz
```

rather than simply averaging reciprocal per-tick latencies. Both representations remain useful as long as their definitions are stated.

---

## Supported feature matrix at M12 closure

| Area | Validated FPGA-v1 scope |
| --- | --- |
| Neuron arithmetic | Integer current-based LIF-style state transition under the frozen M10 ordering |
| State precision | Signed 24-bit saturating current and voltage |
| Decay | 13-bit decay controls on the frozen 0..4096 scale and frozen integer rounding behavior |
| Threshold | Strict threshold comparison under the frozen M10 contract |
| Reset/refractory | Frozen reset voltage and 16-bit refractory state/timing behavior |
| Bias | Frozen signed bias contribution |
| Static weights | M08 Loihi-style **project representation** with mantissa, exponent, precision, and sign mode |
| Synaptic accumulation | Signed 64-bit exact tick-local accumulation before state arithmetic |
| Event multiplicity | Preserved; repeated events are not deduplicated |
| Input ordering | External events before recurrent events under the frozen deterministic contract |
| Recurrent delivery | Spike-generated recurrence is delivered on the next architectural tick only |
| Recurrent storage | Deterministic CSR routes and double-buffered recurrent queues |
| Trace semantics | Atomic post-commit trace window with pre/post state, synaptic input, spikes, external/recurrent/routed events, queue metadata, and faults |
| Physical capacities | 256 neurons, 1,024 axons, 4,096 synapses, 16 weight formats, 4,096 routes, 4,096 external events/tick, 4,096 recurrent events/tick |
| Directed physical evidence | M12.2: 16/16 exact single-tick cases |
| Stateful physical evidence | M12.3: 10 scenarios / 40 committed ticks exact, plus independent reset/replay evidence |
| Broad physical evidence | M12.4: 22 cases / 166 committed ticks exact |
| Characterization-image evidence | M12.5 repeats all 22 M12.4 cases / 166 ticks with zero mismatches while collecting cycle data |
| Routed timing | Characterization image closes at 100 MHz with WNS +0.493 ns and WHS +0.011 ns |

The M08 format remains explicitly a transparent project-specific Loihi-style storage representation. It must not be described as a claim about undocumented Intel SRAM bit layout.

---

## Explicit limitations and excluded claims

The validated M12 claim does **not** include:

- Intel Loihi's undocumented physical microarchitecture, SRAM organization, physical timing, or NoC implementation;
- a complete Loihi processor feature set;
- online plasticity or learning rules;
- multicore mesh/NoC behavior;
- unsupported programmable synaptic-delay mechanisms outside the frozen recurrent next-tick model;
- production Linux/FPGA-manager integration;
- uninterrupted coexistence with the stock Kria PL application after direct JTAG replacement;
- an optimized parallel/high-throughput implementation;
- maximum Fmax beyond the demonstrated routed 100 MHz target;
- measured power or energy;
- exhaustive validation of every mathematically legal configuration inside the finite capacities;
- proof that agreement with Brian2Loihi or another implementation establishes undocumented Loihi behavior.

### Power and energy

Power/energy is intentionally outside the validated M12 claim set. No calibrated board-level measurement method was established during M12. Synthesis estimates, informal board readings, or host-side observations are insufficient to call a number measured neuromorphic energy.

This omission strengthens rather than weakens the final claim because it cleanly separates physically established evidence from quantities that would require additional methodology.

### Linux/platform integration

The accepted physical validation path remains direct JTAG/VIO. The stock Kria application is unloaded when necessary so it does not own the PL while the M12 image is programmed.

This is an accepted research/debug transport, not a production deployment architecture. A future production-quality platform would package the design for Linux FPGA-manager/device-tree ownership and provide a software-facing command/data interface rather than relying on Hardware Manager VIO.

---

## Reproducible M12.5 command chain

### 1. Software regression

```bash
cd "/home/dna/Git/Thesis/Neuromorphic Digital Twin"
python3 -m pytest -q \
    tests/test_m12_5_characterization.py \
    tests/test_m12_5_capture_sources.py
python3 -m pytest -q
```

The M12.5 preflight also regenerated the frozen broad corpus, linted the passive characterization RTL hierarchy, reran the M12.2 recurrent-bank selector regression, and syntax-checked the source-controlled runners.

### 2. Build the characterization image

```bash
cd "/home/dna/Git/Thesis/Neuromorphic Digital Twin/rtl/core_v1"
bash run_m12_5_bitstream.sh
```

Required routed evidence includes:

```text
utilization_impl.rpt
utilization_hierarchical_impl.rpt
ram_utilization_impl.rpt
ram_utilization_impl.csv
timing_summary_impl.rpt
setup_paths_impl.rpt
hold_paths_impl.rpt
route_status_impl.rpt
methodology_impl.rpt
drc_impl.rpt
clocks_impl.rpt
neuromorphic_twin_m12_5.bit
neuromorphic_twin_m12_5.ltx
neuromorphic_twin_m12_5_routed.dcp
neuromorphic_twin_m12_5.xsa
```

### 3. Prepare the KV260

If the stock Kria PL application is active:

```bash
sudo xmutil unloadapp
```

### 4. Run physical characterization

```bash
bash run_m12_5_hardware_characterization.sh
```

This single command:

1. programs the M12.5 bitstream;
2. confirms PL heartbeat/reset behavior;
3. executes all 22 physical cases;
4. records all 166 cycle measurements;
5. captures all 22 complete physical trace artifacts;
6. runs the exact M12.4 Python-vs-physical differential;
7. refuses characterization if any mismatch exists;
8. parses routed implementation reports;
9. derives per-tick latency/throughput;
10. writes workload scaling evidence.

### 5. Re-run host analysis without the board

```bash
bash run_m12_5_analysis.sh
```

This consumes the already captured cycle TSV and Vivado reports. It allows tables or numerical summaries to be regenerated later without repeating physical execution.

---

## Generated evidence

The accepted M12.5 run produces:

```text
build/m12_5/reports/
    routed Vivado implementation/timing reports

build/m12_5/m12_5_vivado.log
    source implementation log containing routed timing marker

build/m12_5/captures/*.physical.json
    22 complete physical architectural traces

build/m12_5/differential_reports/
    exact Python↔FPGA per-case reports + suite_report.json

build/m12_5/m12_5_tick_cycles.tsv
    166 raw physical PL-cycle measurements

build/m12_5/characterization/characterization.json
    machine-readable implementation + per-tick characterization

build/m12_5/characterization/tick_characterization.csv
    per-tick cycles, latency, workload counts, and derived rates

build/m12_5/characterization/case_scaling.csv
    22 workload-level scaling summaries

build/m12_5/characterization/CHARACTERIZATION_SUMMARY.md
    compact human-readable routed/resource/latency summary
```

The raw physical trace and cycle artifacts remain the evidence authority. Derived tables can be regenerated from them.

---

## M12.5 completion decision

M12.5 passes because every planned evidence boundary is now closed:

1. **Behavioral preservation:** the characterization image repeats the complete 22-case / 166-tick M12.4 suite with zero mismatches.
2. **Timing closure:** routed WNS and WHS are both positive at the frozen 100 MHz target.
3. **Resource characterization:** LUT, register, BRAM, DSP, and URAM use is recorded against K26 capacity.
4. **Physical latency measurement:** every one of the 166 committed ticks has a positive on-FPGA PL-cycle count.
5. **Throughput characterization:** tick, neuron-update, event, and exact CSR-synapse-visit rates are derivable from physical cycle counts.
6. **Scaling evidence:** all 22 workloads have min/mean/max cycle summaries and workload metadata, including dedicated event, fan-in, fanout, population, recurrent-history, and mixed-feature stress cases.
7. **Transparent timing interpretation:** isolated cases expose understandable serialized cycle costs rather than only a black-box benchmark result.
8. **Supported scope recorded:** the exact validated FPGA-v1 feature set and finite capacities are explicit.
9. **Limitations recorded:** unsupported Loihi features, Linux deployment limitations, power exclusion, and Fmax exclusion are explicit.
10. **Reproducibility:** source-controlled build, capture, exact-differential, and host-analysis commands reproduce the evidence chain.

No critical unexplained discrepancy remains.

---

## Thesis-level conclusion from M12.5

M12.5 supports a stronger conclusion than simply saying that the FPGA "runs an SNN."

The project now has a transparent, finite, Loihi-inspired FPGA-v1 processor model whose state-transition semantics were defined independently in software, externally checked where applicable against Brian2Loihi, translated into an HLS/RTL implementation, and then validated against the independent Python model on the physical K26 across directed, stateful/recurrent, and broad deterministic workloads.

The final characterization image preserves exact behavior while exposing physical implementation cost.

The defensible thesis claim is therefore:

> The project implements a transparent FPGA digital twin of an explicitly defined Loihi-inspired computational subset and demonstrates exact software-to-physical state-transition equivalence for that subset, together with reproducible physical timing, resource, latency, throughput, and scaling evidence.

The claim is deliberately narrower than "reimplements Intel Loihi." It does not depend on undocumented Intel microarchitecture. Its strength comes from an explicit architecture, independent golden model, exact trace evidence, physical reproduction, and transparent implementation-level cost characterization.

That evidence is the foundation for M13's external architectural audit against Catalyst N1 and for the later controlled experiments in `EXPERIMENTS.md`.