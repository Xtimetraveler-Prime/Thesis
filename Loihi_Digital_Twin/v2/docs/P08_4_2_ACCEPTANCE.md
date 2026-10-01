# P08.4.2 Acceptance Record — Exact Compiled Execution Conformance

**Status:** Accepted  
**Accepted:** 2026-09-30  
**Branch:** `agent/p08.4-official-test-evaluation`

## Accepted result

P08.4.2 executed the exact accepted P08.3.5c P06 deployment for one representative official-test frame through the packet-level architectural path. The representative corpus was fixed as official MNIST test index `0` before physical conformance selection and was not chosen by label, correctness, confidence, or any P08.4.1 result.

```text
representative test index: 0
label:                     7
algorithmic timesteps:     100
source-input spikes:       807
prediction:                7
final conv4 evidence:      [-284, -1203, 104, 109, -2253, -599, -2659, 1446, -436, -63]
```

The source-recovered vectorized simulator and exact P06 packet-level deployment produced the same final ten-value membrane-evidence vector and the same class prediction.

## Paging and ordering conformance

The same exact deployment was executed in three legal modes:

```text
unpaged logical reference
paged forward service/drain
paged reverse service/drain
```

All three normalized architectural traces had the identical fingerprint:

```text
a81844443b6e5f6c278167a4aafc46dcfd74f7df5498179312b1fc39edba09d6
```

The paging runs exercised real five-over-three residency pressure:

```text
forward page loads:       497
forward evictions:        497
reverse page loads:       499
reverse evictions:        499
logical cores:              5
resident contexts:          3
physical compute engines:   1
```

The unpaged execution observed:

```text
ingress packets:   2,382
internal traffic: 17,910
```

Paging/service order therefore changed physical scheduling behavior but not the normalized neural result.

## Frozen artifact identity

```text
parameter_fingerprint=9169939821201e4764813dbb17e254b796cd952e4707315eb61ecd0e0082926e
network_fingerprint=6e47dc0c37d2f05828f0a0231406c7df8e4bf83652300fde0df1a0b8f9d83f13
compiled_fingerprint=5dc7c9af692ca375283ede186b81d135bd1c76708b114cc64e3f99c085cd856b
```

P08.4.2 remained downstream of the accepted P08.4.1 official-test measurement. The official test set was already open for evaluation, but no model, conversion, threshold, decoder, or timestep selection was made after observing it.

## Acceptance boundary

P08.4.2 establishes that the exact trained/converted workload survives the complete source-recovered SNN -> P06 compiled-deployment -> five-logical-core paged software execution boundary without a semantic change.

It does not yet establish physical K26 execution of the trained deployment. That belongs to P08.4.3.

## Next stage

P08.4.3 is split into two physical sub-gates:

1. **P08.4.3a — physical host-paged shell implementation.** Integrate the already verified `p08_paged_dispatch_controller` with the accepted P05 full-context memory fabric and P03-compatible HLS engine, then require routed timing closure on K26.
2. **P08.4.3b — representative physical conformance.** Use the fixed P08.4.2 test frame and exact deployment snapshots to exercise real host page replacement/dispatch on the K26 and compare physical state/packet/readout behavior with software expectations.

The physical proof must not silently fall back to the older P05 controller, because that controller assumes at most three simultaneously configured logical destinations and therefore is not the accepted P08 host-paged execution model.
