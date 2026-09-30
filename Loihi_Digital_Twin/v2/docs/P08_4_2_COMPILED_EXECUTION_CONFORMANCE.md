# P08.4.2 Exact Compiled-Execution Conformance Gate

## Purpose

P08.4.2 proves that the exact accepted source-recovered MNIST deployment executes
through the architectural P06 packet/paging path without changing the behavior
measured by the source-recovered vectorized SNN simulator.

This gate is downstream of the accepted P08.4.1 official-test measurement. It is
not an accuracy-selection or tuning stage.

## Frozen identities

P08.4.2 requires the exact accepted P08.3.5c artifacts:

```text
parameters=9169939821201e4764813dbb17e254b796cd952e4707315eb61ecd0e0082926e
network=6e47dc0c37d2f05828f0a0231406c7df8e4bf83652300fde0df1a0b8f9d83f13
compiled=5dc7c9af692ca375283ede186b81d135bd1c76708b114cc64e3f99c085cd856b
```

It also requires the locally accepted P08.4.1 manifest and checks the accepted
official-test measurements and deterministic result fingerprints before running.

## Representative corpus rule

The conformance frame is fixed as:

```text
official MNIST test index = 0
selection rule = fixed_test_index_0_not_conditioned_on_result
```

The frame is not selected by class, correctness, confidence, ANN/SNN agreement,
or any other P08.4.1 outcome. The same frame is intended to remain the primary
physical K26 conformance case so later stages do not shop for a convenient input.

## Input timing boundary

The recovered public NxTF path contains a BIAS-driven input spiking layer. The
accepted P06 graph begins at conv1, so the input layer is represented by the host
ingress encoder.

For each raw MNIST pixel in the accepted 0..255 BIAS domain:

1. add the pixel bias to the input-neuron membrane each source tick;
2. emit a spike only when the candidate membrane is strictly greater than the
   accepted input threshold `2040`;
3. hard-reset the input membrane to zero after a spike; and
4. inject a source spike generated at source tick `t` into the compiled conv1
   graph at algorithmic timestep `t+1`.

This reproduces the one-tick input-layer latency visible in the source-recovered
vectorized simulator. The 100th source-tick spike set is generated for audit
parity but cannot influence conv1 inside the fixed 100-timestep horizon.

## Execution variants

The exact compiled deployment is run for 100 timesteps in three modes:

```text
unpaged_reference
paged_forward: logical order 0,1,2,3,4; forward packet drain
paged_reverse: logical order 4,3,2,1,0; reverse packet drain
```

The paged variants use the accepted P08 boundary:

```text
logical cores      = 5
resident contexts  = 3
physical engines   = 1
paging policy       = deterministic round-robin
```

Both paged runs must exercise page loads and evictions.

## Acceptance conditions

P08.4.2 passes only if:

1. the accepted P08.4.1 result manifest is present and identity-valid;
2. the accepted P08.3.5c parameter/network/deployment fingerprints reproduce;
3. all three execution variants complete exactly 100 timesteps;
4. the normalized architectural trace fingerprint is identical for unpaged,
   paged-forward, and paged-reverse execution;
5. final conv4 membrane evidence from every compiled execution is exactly equal
   to the source-recovered vectorized simulator evidence;
6. all execution variants produce the same class prediction;
7. both paged variants exercise context loads and evictions; and
8. no model/conversion selection or tuning follows from the conformance result.

This gate has no classification-accuracy threshold. P08.4.1 already froze the
full official-test accuracy; P08.4.2 is an implementation-equivalence check.

## Outputs

The local ignored artifact directory is:

```text
applications/mnist_v2_nxtf/artifacts/p08_4_2_compiled_execution_conformance/
```

It contains:

```text
compiled_execution_conformance_manifest.json
compiled_execution_conformance_vectors.npz
```

The vectors artifact contains the fixed input frame, deterministic BIAS input
spike schedule, and source-simulator final evidence so the same corpus can be
carried into the physical K26 conformance stage.
