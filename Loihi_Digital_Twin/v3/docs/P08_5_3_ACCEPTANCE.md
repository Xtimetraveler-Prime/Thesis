# P08.5.3 — Final Closure Acceptance

**Status:** Accepted  
**Accepted:** 2026-09-30

## Independent reproduction

The final P08.5.3 closure candidate was independently reproduced from the dedicated P08 environment with:

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v2
bash scripts/run_p08_5_3_final_closure.sh
```

Observed result:

```text
19 passed in 0.10s
P08.5.3 final-closure gate completed successfully.
```

Accepted deterministic closure fingerprint:

```text
135bdc7f64955972cab11472e5b4ada7d16c62a0bbd5ace8051d424988d81cce
```

The closure is bound to the previously accepted comparison artifacts:

```text
P08.5.1 ledger  = 574023d0e55cf3d5098cccd1f23e597ee63deb872ac119be30bf41a5f495511d
P08.5.2 report  = d3d47e95f928f0de77d2c1b59c2c16f5becdf5dd443f6600c187d3f56e1e68a0
P08.4 merge     = ac40c8239c6b8134f4e6ec74849e7dfafda8335e
P08.5.1 merge   = d45bb5e06aba83a906d170b69a510dfac7bd30d6
P08.5.2 merge   = 688ba77477ca9a7d7bd99d00ef497f1589c07393
```

## Frozen final result

```text
ANN official-test accuracy: 0.987400
SNN official-test accuracy: 0.982400
ANN-SNN accuracy delta:     0.005000
primary SNN horizon:        100 algorithmic timesteps
neurons:                    4,218
trainable parameters:       7,006
expanded connections:       338,880
logical cores:              5
resident K26 contexts:      3
physical HLS engines:       1
```

The accepted P08.5.2 comparison retains the following bounded cross-system quantitative differences:

```text
ANN test-error gap:              0.52 percentage points
SNN test-error gap:              0.97 percentage points
ANN-to-SNN conversion-loss gap: 0.45 percentage points
```

These are reconstruction-bounded comparisons, not claims of exact reproduction of the unpublished NxTF model.

## Physical evidence boundary

P08.4.2 proves complete 100-timestep execution of the accepted five-logical-core deployment under unpaged, forward-paged, and reverse-paged schedules at the normalized architecture boundary.

P08.4.3b physically demonstrates a real deep-network page replacement and logical-core-4 dispatch on the K26 for official-test index 0 at timestep 99. The accepted physical observation used 3,865 PL cycles (38.65 microseconds at the requested 100 MHz clock) and exactly matched all 618 compartment states/traces, packet image, and final ten-value output evidence.

The project does **not** claim that all approximately 500 logical-core dispatch opportunities for the complete 100-timestep inference were replayed end-to-end over JTAG.

## Final claim boundary

The accepted closure retains all of these as false/non-claims:

```text
exact_paper_topology = false
native_storage_equivalence = false
native_loihi_energy_is_direct_fpga_comparison = false
native_loihi_latency_is_direct_fpga_comparison = false
shared_weight_counts_use_same_storage_model = false
mapped_core_counts_use_same_compiler_model = false
representative_dispatch_cycles_are_full_sample_latency = false
full_100_timestep_inference_physically_replayed_over_jtag = false
physical_async_equivalence = false
post_test_model_or_conversion_selection = false
```

The project therefore remains a source-backed **architectural** digital twin. It does not claim transistor-level/asynchronous-circuit equivalence, exact proprietary NxSDK/NxTF encoding, native-Loihi storage packing, or direct FPGA-versus-Loihi energy/latency equivalence.

## Acceptance decision

P08.5.3 is accepted. The independent reproduction requirement has been satisfied, so the candidate field `p08_complete=false` in the pre-acceptance closure artifact is now superseded by this acceptance record.

All P08 completion criteria are satisfied. P08 may be marked **Complete**, which also means all planned FPGA-v2 phases P00-P08 are complete.
