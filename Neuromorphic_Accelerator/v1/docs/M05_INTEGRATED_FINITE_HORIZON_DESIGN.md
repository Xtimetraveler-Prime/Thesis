# M05 integrated finite-horizon temporal scheduler — first physical-IP increment

**Updated verification status 2026-11-08:** the operator's genuine Vitis 2025.2 K26 HLS CSim, standalone HLS csynth and XSim C/RTL cosimulation for `m05_integrated_replay` **all PASS**; no physical device operation, live AXIS ready/valid performance or routed timing. The former source-only text below is historical. Do not borrow real standalone IP HLS evidence as proof of this new top. M05 remains OPEN and PR #79 draft/unmerged.

**Top-level HLS synthesis estimates:** target 10.00 ns; estimated period **8.002 ns**; **5,914 LUT, 3,122 FF, 6 DSP, 74 BRAM18K, zero URAM**; top-level latency `?` (unresolved). The original C/RTL console postcheck PASS and return 0 are confirmed; pending detailed [cosimulation timing report](M05_ROLLING_WHEEL_DESIGN_2026_11_08.md). Operator original evidence folders recorded in [rolling design and evidence metadata](M05_ROLLING_WHEEL_DESIGN_2026_11_08.md). The more scalable rolling follow-on is still native-only.

## Motivation and scope

The three earlier genuine-Vitis-verified IPs are independent: a deeply pipelined stateless LIF evaluator, a stateful BRAM service (with its own sequential divider), and an exact signed accumulator. **Connecting their AXIS ports would not create an autonomous future-event scheduler**, because no block owns recurrent synaptic fanout, future delivery timestamps, sparse wakeups, and the complete tick barrier. It would also duplicate LIF arithmetic.

This incremental fourth top, [`m05_integrated_replay`](../hls/m05_integrated/m05_integrated.cpp), **fuses those control responsibilities** into a single offline HLS-oriented C++ datapath and reuses the *same accepted* M04/M02 `m04_eval_one` numeric contract. It does **not** instantiate all three prior cores; those remain reference/candidate alternatives. The PL-oriented top owns state/config, adjacency, future current buckets, touched flags, admission counts, tick sequencing and a buffered output trace. **No Python function or A53 transaction is invoked per tick.**

## First integration admission profile (explicit limits)

| Property | Current prototype limit | Boundary |
| --- | --- | --- |
| Resident neurons | `1..1024` | State W16, independent threshold/reset/bias/voltage per neuron |
| Directed synapse records | `0..4096` | Each W16 signed weight; self and parallel edges legal |
| Run horizon | `1..8` ticks | One `ap_ctrl_hs` run starts at logical tick 0; no continuing stream across invocations |
| Individual arrivals | `<=4096` per tick | Sum external + recurrent; **zero** and canceling deliveries COUNT |
| External events over run | `<=32768` | Each has a tick, target neuron and W16 individual contribution |
| Delay | `uint64 >=1` | Delayed events beyond the configured run horizon have no in-run effect |
| Leak | `u32 numerator/denominator` | `0 <= numerator <= denominator`, denominator nonzero; mathematical signed truncation to zero |
| Aggregate | `int64` | Exact sum before ONE W16 clamp |
| Output | `ticks * neurons` records | Sorted tick-major/neuron-major; post-tick voltage, spike bit, evaluated flag, individual-delivery count |

**This finite horizon is an explicit prototype concession, not the complete M05/Loihi-like temporal memory model.** It is suitable for offline end-to-end HLS verification and recurrent neural parity. The long-running event engine needs a rolling bounded temporal queue, overflow recovery across runs, richer graph loading and real AXIS flow-control handling. No equivalence to Loihi silicon is claimed.

## Dataflow and non-negotiable safety/correctness

1. **Admission** checks shape before consuming streams, validates *all* neuron parameters, synapse endpoints/weights/delays, and external events; invalid requests return a nonzero `M05_INT_*` status and yield **zero** trace records.
2. **On-chip setup** zeroes all eight future-bucket counts/touched/aggregate cells, initializes the 1,024-element graph adjacency heads, then loads 1,024-row neuron arrays and up to 4,096 synapse records in BRAM-candidate static arrays. A linked-list adjacency representation makes output-event fanout proportional to actual outgoing degree, not a scan of every edge for each spike.
3. **External event preloading** writes signed i64 per-(tick,neuron) aggregates and increments a separate *individual delivery* counter. The touched bit is set even if the contribution equals zero or algebraically cancels others; the 4,097th arrival of any future tick aborts the *whole run*.
4. **Global tick barrier:** each tick visits neuron IDs in ascending order; only `voltage != 0 || bias != 0 || touched[t][i]` is eligible. For eligible neurons call `m04_eval_one`: truncate signed leak toward zero, exact decay+bias+aggregate, one W16 clamp, inclusive threshold, reset on spike. All other neurons are valid exact-zero skips. Spike fanout targets **only** `t+delay` (positive delay), so no same-tick feedback; duplicates, signed weights and self-loops are preserved.
5. **Staged publication:** voltage/spike/evaluated records for each tick go into resident trace arrays. **No AXIS trace output occurs until the entire finite run is valid**, including all future-bucket capacity checks. Hence a fault on a later tick never exposes a partial earlier trace. Each new invocation starts with a fresh logical epoch.
6. **Error contract:** `M05_INT_BAD_SHAPE`, `M05_INT_BAD_NEURON`, `M05_INT_BAD_SYNAPSE`, `M05_INT_BAD_EXTERNAL`, `M05_INT_DELIVERY_OVERFLOW`, `M05_INT_LIF_ERROR` each return nonzero without any trace. This implementation does not continue from a failed run.

The future storage is **aggregate+touch+count buckets**, *not* an individual-event FIFO. This is behaviorally correct for the accepted additive M02 neuron model and delivery-count rules; it is not a claim of an event-preserving on-wire temporal packet protocol.

## Source and test inventory

- [`m05_integrated.hpp`](../hls/m05_integrated/m05_integrated.hpp) — bounded profile, AXIS structs, statuses, top signature.
- [`m05_integrated.cpp`](../hls/m05_integrated/m05_integrated.cpp) — HLS-oriented resident memory, graph fanout, temporal bucket scheduler, exact M04 neuron step, trace commit.
- [`m05_integrated_host_cli.cpp`](../hls/m05_integrated/m05_integrated_host_cli.cpp) — native **test-only** strict framed payloads; not a physical host/AXI driver.
- [`m05_integrated_csim_tb.cpp`](../hls/m05_integrated/m05_integrated_csim_tb.cpp) — HLS testbench: recurrent self-edge trace, 4097 zero-event overflow, recovery to clean run.
- [`test_m05_integrated.py`](../tests/test_m05_integrated.py) — **12 named methods**: native-compilation, bias wakeup, canceling/zero touches, self/parallel/delay semantics, negative leak + threshold equality, 4096 exact W16 terms, 4097 external overflow, 4097 recurrent overflow, invalid horizons/ranges, malformed config/events, 16 seeded recurrent networks over 8 ticks with complete M02 dense/event and M03 sparse parity.
- [`m05_integrated_hls_config.cfg`](../hls/m05_integrated/m05_integrated_hls_config.cfg) — fourth standalone K26 target with 10ns requested clock, 12% uncertainty and RTL.
- [`run_m05_offline_hls.sh`](../hls/m05_stream_eval/run_m05_offline_hls.sh) — new `--integrated` selection; same new-only evidence directory and absolute-source-config hash protections as the other three tops.
- CI runs **60 named M05 methods** total, 91 accepted M01–M04 regressions, and native compiles all four CSim vector benches. **Native PASS is not Vitis CSim/C-RTL PASS.**

## Next real HLS gate (operator's Vitis 2025.2 machine)

```bash
cd ~/Git/Thesis
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m05-sparse-onchip
cd Neuromorphic_Accelerator/v1

python3 -m unittest discover -s tests -p 'test_m05*.py' -v
# With your Vitis 2025.2 environment already sourced:
export HLS_PART=xck26-sfvc784-2LV-c
bash hls/m05_stream_eval/run_m05_offline_hls.sh --integrated --csim
```

**Stop and provide the original integrated CSim log on any failure.** If genuine CSim PASSES, proceed to independent `--integrated --synth`; inspect **BRAM, LUT/FF/DSP, graph traversal latency, estimated clock** (none yet demonstrated) before `--integrated --cosim`. If synth or cosim fail, retain originals and revise source; do not silently substitute the prior three IP results. Optional `--impl` is only isolated out-of-context P&R; no JTAG/DDR/board operations are authorized.

## Remaining milestone closure gates

The integrated *finite-run* prototype must prove genuine Vitis CSim, HLS synthesis and full XSim C/RTL parity first. Then complete **continuous arbitrary-length** temporal scheduling (rolling future-event queues/buckets with bounded backpressure), live streaming handshakes, reliable all-tick run abortion/recovery, state commit/overflow policy, full independent network-level RTL test coverage, resource feasibility including routing/controls, and eventually user-authorized physical workflow. Do not label M05 complete based on this increment.
