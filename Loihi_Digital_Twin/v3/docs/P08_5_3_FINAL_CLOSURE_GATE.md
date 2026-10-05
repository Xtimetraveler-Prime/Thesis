# P08.5.3 — Final P08 Closure Gate

## Purpose

P08.5.3 is the final independent-reproduction gate for the NxTF MNIST phase. It does not add another experiment, accuracy measurement, topology choice, conversion choice, performance ratio, or hardware implementation.

Its purpose is to prove that the accepted P08.1-P08.5.2 evidence can be bound into one deterministic closure record without changing any previously accepted measurement or claim boundary.

The generator is:

```text
applications/mnist_v2_nxtf/mnist_v2_nxtf/final_closure.py
```

and the verification gate is:

```text
Loihi_Digital_Twin/v2/scripts/run_p08_5_3_final_closure.sh
```

## Inputs frozen before this gate

P08.5.3 is hard-bound to:

```text
P08.5.1 comparison-ledger fingerprint:
574023d0e55cf3d5098cccd1f23e597ee63deb872ac119be30bf41a5f495511d

P08.5.2 final-comparison fingerprint:
d3d47e95f928f0de77d2c1b59c2c16f5becdf5dd443f6600c187d3f56e1e68a0

P08.4 merge:
ac40c8239c6b8134f4e6ec74849e7dfafda8335e

P08.5.1 merge:
d45bb5e06aba83a906d170b69a510dfac7bd30d6

P08.5.2 merge:
688ba77477ca9a7d7bd99d00ef497f1589c07393
```

The previously frozen ANN, conversion, network, compiled-deployment, trace, bitstream, and probe identities are inherited from the accepted P08.5.1 ledger.

## Final result bound by the closure candidate

```text
ANN official-test accuracy:       0.987400
SNN official-test accuracy:       0.982400
ANN→SNN accuracy drop:            0.005000
primary horizon:                  100 timesteps

neurons:                          4,218
trainable parameters:             7,006
expanded connections:           338,880
logical cores:                    5
resident K26 contexts:            3
physical HLS engines:             1
```

The closure also retains the accepted bounded NxTF comparison:

```text
ANN error gap:                    0.52 percentage points
SNN error gap:                    0.97 percentage points
ANN→SNN conversion-loss gap:      0.45 percentage points
```

Those are reconstruction-bounded comparisons. They are not exact-reproduction claims.

## Evidence chain

The closure candidate requires all of these stages to remain bound:

1. **P08.1** — source-bounded topology/resource reconstruction;
2. **P08.2** — five-over-three deterministic context paging;
3. **P08.3** — frozen ANN training and source-recovered conversion without official-test tuning;
4. **P08.4.1** — frozen full 10,000-image official-test ANN/SNN evaluation;
5. **P08.4.2** — complete 100-timestep compiled paging/order conformance;
6. **P08.4.3** — representative real-MNIST K26 page replacement and physical dispatch conformance;
7. **P08.5.1** — comparison ledger/comparability freeze;
8. **P08.5.2** — deterministic thesis-facing final comparison.

## Physical claim boundary

P08.5.3 preserves the same physical boundary accepted in P08.4 and P08.5.2:

- the complete 100-timestep representative paging sequence is proven in compiled software conformance;
- a real deep-network logical-core-4 timestep-99 snapshot is physically paged and dispatched on the K26;
- all 618 checked physical state/trace entries and final ten-class evidence match the accepted architecture result;
- the representative physical dispatch is 3,865 PL cycles at 100 MHz, or 38.65 us;
- 38.65 us is **one dispatch**, not end-to-end MNIST sample latency;
- the project does not claim that all approximately 500 dispatches were replayed end-to-end over JTAG.

## Explicit non-claims retained

The closure validator rejects any change that promotes the final result into a claim of:

- exact unpublished NxTF topology/checkpoint reproduction;
- native NxTF/Loihi compiler or storage-packing equivalence;
- direct FPGA-versus-Loihi energy comparison;
- direct native-Loihi-versus-K26 sample-latency comparison;
- shared-weight efficiency ratio;
- mapped-core efficiency ratio;
- one physical dispatch as full-sample inference latency;
- complete end-to-end physical JTAG replay of the 100-timestep representative inference;
- transistor-level/physically asynchronous Loihi equivalence; or
- post-test model/conversion/threshold/decoder/timestep tuning.

## Determinism and regression scope

The gate runs the accepted P08.5.1 and P08.5.2 regression suites plus the new P08.5.3 closure regressions. It then generates the closure twice and requires the JSON and Markdown artifacts to be byte-identical.

The generated candidate artifacts are:

```text
applications/mnist_v2_nxtf/artifacts/p08_5_3_final_closure/
├── p08_final_closure.json
└── p08_final_closure.md
```

The JSON contains a deterministic closure fingerprint.

## Completion-state rule

The candidate deliberately records:

```text
p08_complete = false
P08.5.3 = REVIEW_PENDING
```

This is intentional. Generating our own closure candidate is not sufficient to mark the phase complete.

Only after the gate is independently reproduced may the acceptance documentation and roadmap change P08/P08.5.3 to **Complete**. That later documentation update will bind the independently reproduced closure fingerprint rather than regenerate or alter the experiment.

## Run

With the dedicated P08 environment active:

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v2
bash scripts/run_p08_5_3_final_closure.sh
```

## Acceptance gate

P08.5.3 is ready for acceptance when:

- all chained P08.5 regressions pass;
- both closure generations are byte-identical;
- the P08.5.1 and P08.5.2 fingerprints match exactly;
- the accepted merge and deployment identities match exactly;
- the final official-test metrics and architectural totals match exactly;
- all overclaim guardrails remain false;
- the closure fingerprint recomputes exactly; and
- the final output states `candidate_ready=true`, `p08_complete=false`, and `independent_acceptance_required=true`.
