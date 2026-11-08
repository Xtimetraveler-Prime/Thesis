# M02 — PROVISIONAL Independent LIF / Event-Order Contract

**Status:** Draft v1 functional contract, **not** Loihi 1/2 semantics, v3 bitwise compatibility or a final FPGA hardware interface. No HLS/RTL, bitstream, physical KV260 evidence or neural-network classification result. This contract is proposed to unblock separate independent functional implementations; **user review is required before M02 acceptance/freeze**.

## Why a new reference?

The old Loihi-oriented golden model includes architecture-specific dispatch, context layout and mapping. The new accelerator needs an **architecture-independent mathematical oracle** so that alternative schedulers/caches can be checked against an unchanged neural computation. M02 implements (a) a deliberately simple dense timestep evaluator (reference) and (b) a structurally independent **event-queued synaptic-delivery evaluator**. They compare exact per-tick neuron states and spikes, not just final class. v3 examples can be **later comparison vectors** where numerical contracts overlap, never unexamined sole truth.

## First-scope neuron and network

- `N` fixed neurons with contiguous IDs `0..N-1`. Neuron-specific **initial membrane, bias, threshold, and reset voltage**. Global signed fixed-point storage width `W`, default 16 bits; this version treats weights, bias and input as integer **current units**, not voltage-normalized floating values.
- One membrane state `v_i` per neuron; **no independent synaptic-current state variable** in this first provisional version. No refractory, plasticity, analog input encoder, long axon timing, mesh or core semantics; those would be deliberately versioned extensions.
- One global decay ratio `D_num/D_den` with `0 <= D_num <= D_den`. Computation uses **integer truncation toward zero** on the prior **stored** voltage every timestep, including quiet timesteps. Do not conflate with YANA's lazy leak or assume leap-over-idle equivalence. The choice of decay representation is for a testable first oracle, not a performance claim.
- Each external input event is an independently specified `(tick, destination_neuron, signed_current)`, **not an input neuron spike that traverses edges**. Repeated events sum algebraically.
- Edges `(pre, post, signed_weight, delay)` are **nonplastic**; `delay >= 1` logical tick. A spike emitted by neuron `pre` during tick `t` delivers its synaptic current `weight` to `post` during tick `t+delay`. Distinct parallel edges and negative weights are permitted. Self-connections are allowed only with a positive delay. Scheduled events after the requested run horizon are ignored by that finite run, not wrapped into earlier ticks.
- Recurrent networks are **in scope** with positive delays; instantaneous zero-delay cycles are rejected at input validation. Delayed input that arrives at the exact final tick is processed; a delivery beyond the horizon is not.
- All input events and outgoing edge deliveries at the same destination/tick are summed in unbounded Python integers, **then** added to that tick's decay and bias. Fixed-point saturation occurs **once** after that complete sum; changing event order or grouping must not change the result.
- No stochasticity and no floating-point operations in oracle arithmetic. Both implementations produce **one spike maximum per neuron per tick**.

### Exact per-tick mathematical rule

Let stored `v_i(-1) = initial_i`. For each logical tick `t = 0,...,T-1`, independently for every neuron `i`:

1. `d_i(t) = trunc_zero(D_num * v_i(t-1) / D_den)`.
2. `I_i(t) = sum(external_current events targeting i at t) + sum(edge weights from all presynaptic spikes emitted at t - edge.delay)`.
3. `u_i(t) = clamp_W(d_i(t) + bias_i + I_i(t))`, with `clamp_W` saturating to `[-2^(W-1), 2^(W-1)-1]`.
4. If `u_i(t) >= threshold_i`, emit exactly one event `(t,i)` and store `v_i(t)=reset_i`; otherwise store `v_i(t)=u_i(t)`. Threshold comparison is **inclusive**.
5. All neurons update **once each timestep** (including neurons with no input, because bias can cause an autonomous spike). Visible output is sorted by `(tick, neuron_id)` and per-tick state is captured after reset. The scheduler must never assume all quiet neurons may be safely skipped.

**No cross-timestep concurrent racing:** All arrivals for tick `t` are computed from spikes emitted at strictly *earlier* ticks, since all delays are positive. If any `spike` at tick `t` schedules a delivery to tick `t+delay`, it cannot affect its own tick.

## Independent evaluator strategies

**Dense oracle:** stores the complete prior tick's spike rows. At each tick, each neuron sums all external currents and scans all network edges, asking whether a presynaptic neuron emitted at `t - delay`, then performs a scalar LIF update. Intentionally simple and nonoptimized.

**Event-queue cross-check:** indexes outgoing edges by presynaptic ID. Each emitted spike schedules future `(destination, current)` deliveries in a `tick -> deliveries` bucket; each tick independently coalesces arriving currents by destination and updates all neurons with its **separately coded** integer math. This is event-driven for **synaptic scheduling**, **not** a fully sparse neuron-evaluation engine, and does not claim a hardware hot-neuron scheduler. In particular, zero-event neurons still decay and integrate bias at every tick.

**Independence boundary:** modules share typed **network data validation**, but do **not** call the same LIF update function or implementation of synaptic traversals. Differential tests are necessary but **insufficient by themselves**; hand-calculated hard-coded expected traces independently pin the chosen semantics.

## Correctness fixtures / hazards targeted

- Zero-input, negative initial states, negative weights and current cancellation; Python `//` rounds negatives down and must **not** replace truncation-toward-zero.
- Threshold equality and reset state in recorded traces.
- Signed W-bit saturation **before** threshold; accumulate duplicate/simultaneous currents *before* saturation (to avoid order-dependent results).
- Bias-only neuron emits with zero external or incoming events; proves skipping all idle neurons would be wrong.
- Positive-delay recurrent and self connections; no same-tick propagation.
- Last-tick events and delayed deliveries beyond run horizon.
- Invalid event types/IDs, non-integer boolean values, invalid width/decay/threshold and zero delay fail closed; no input mutation.
- Reproducibility: two implementations agree exactly across fixed random feedforward/recurrent graphs and unsorted/multiple external events, and frozen JSON/trace SHA match at fixed input.

## Future choices intentionally not frozen by this draft

1. Which **precision, leak equation and per-neuron parameter layout** best match an efficient new HLS evaluation engine? 16-bit state and rational decay are *first implementation choices*, not measured hardware costs.
2. Should **refractory**, **synaptic current state**, distinct leak terms, subtractive reset, more detailed delays or timestep-free asynchronous semantics be required by the chosen benchmark? Changing any of these requires a new reference-contract revision and golden fixtures, not silently changing a bitstream.
3. Which **neural workloads** should define application-level accuracy? M02 uses deterministic synthetic fixtures only. Official MNIST TEST remains sealed.
4. How might exact idle-step skipping be legal? Only with a separately proven fast-forward/closed form for the specified fixed-point rounding and all bias/refractory behavior, or by demonstrating exact parity; defer this optimization to M05/M07 and credit YANA lazy-update prior art.
5. What should be used as on-chip state format / DDR ABI? M01 approved configurable group residency as a **provisional memory baseline**, not an HLS/DDR memory layout. State and synaptic placement remain separate variables.

## Provenance, citation and limitations

The LIF model is standard neuroscience/computing prior art; this project's code will independently implement a **specified mathematical rule** and neither claim original neuron equations nor reproduce YANA's specific five-stage pipeline or hot-neuron FIFO. YANA/Pachideh et al. (https://arxiv.org/abs/2604.03432) is an event-driven influence; SENECA (https://doi.org/10.3389/fnins.2023.1187252) and HiAER-Spike (https://doi.org/10.1038/s44335-026-00062-8) are relevant broader precedent. No third-party source code is copied.

**Acceptance gate:** Native independent PC verification of hard-coded fixtures and differential sparse/dense parity; exact source commit SHA; user review of this provisional mathematical contract before calling M02 complete. No physical FPGA/JTAG work is authorized by any test here.
