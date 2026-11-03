# P08-B4.4.2 — Original 27-context reset-profile physical results

**Status: OPERATOR-REPORTED INDEPENDENT PHYSICAL ACCEPTANCE — 2026-11-03.**
This record captures the operator-supplied output from the genuine KV260
profiling run and the subsequent PC-only independent verifier. The external
evidence bytes are retained on the operator workstation; this Git document
records their supplied paths, hashes, output markers and interpretation.
It does not claim that the cloud-side GitHub editor independently opened
the workstation files.

## Accepted evidence and provenance

Successful retry evidence directory (preserve; never reuse or overwrite):

```text
/home/dna/Thesis_Evidence/p08_b44_profile1024_retry_20261103T061707Z
```

Same-session A53 execution log:

```text
/home/dna/Thesis_Evidence/p08_b44_profile1024_retry_20261103T061707Z/profile1024_a53_physical_run.log
```

Independent PC-only physical report:

```text
/home/dna/Thesis_Evidence/p08_b44_profile1024_independent_20261103T100712Z.json
SHA256 47f25cada89dd9220636fbb9539aba5bf0d7705ea3788fdc3ebd1d85f1145cfa
```

The operator supplied the report hash above and the following exact verifier
markers:

```text
P08_B44_NEW_RESET_PROFILE1024_INDEPENDENT_SAME_SESSION_JTAG_PROVENANCE_PASS=1
P08_B44_NEW_RESET_PROFILE1024_ORIGINAL_1024_NEURAL_FNV_SPIKE_PARITY_PASS=1
P08_B44_NEW_RESET_PROFILE1024_ALL_1024_REAL_SHA_COPY_CACHE_SUBSPAN_COUNTERS_PASS=1
P08_B44_NEW_RESET_PROFILE1024_NEW_PAIRED_AB_BA_AB_BENCHMARK_ACCEPTED=0
P08_B44_NEW_RESET_PROFILE1024_INDEPENDENT_PHYSICAL_REPORT=/home/dna/Thesis_Evidence/p08_b44_profile1024_independent_20261103T100712Z.json
```

Therefore the new profile run has independent same-session JTAG provenance,
all 1,024 original neural outputs/FNV spike fingerprints match the frozen
scalar oracle, and all 1,024 physical reset-profile records pass the
independent SHA/copy/cache/subspan/counter structural checks. The paired
A/B benchmark is explicitly **not** accepted and is not part of this result.

The earlier failed first attempt remains preserved separately at
`/home/dna/Thesis_Evidence/p08_b44_profile1024_physical_20261102T201705Z`.
It failed closed at the inherited A53 secondary debug halt because XSDB
reported `External debug access is disabled`; that was not an accepted
powered-down observation and did not reach P03 programming, DDR staging,
ELF download or inference. Do not reuse that failed root or weaken the
original P07-B4i stop gate. The successful retry used the separate
`p08_b44_profile1024_retry_20261103T061707Z` evidence root.

## Immutable build and baseline identities

New, separately built profiling A53 ELF:

- `p08_b44_reset_profile_1024.elf`
- SHA256 `bed1301c69594bf7ebeaa37765ad2cb3035aa0f6d5e9cb4d1fb4637042be3ab3`

New profiling linker map:

- `p08_b44_reset_profile_1024.map`
- SHA256 `d94fa2695e82cc3a501442313bb77e89eb046f01450167108832a190fd9fd2c9`

Offline profile ELF admission report SHA256:
`7a5818dc5469ea288fefcefb87ebc4fd3ab1e5c7bdce0bbfda717a6f2787b129`.

The report binds to the already accepted original full1024 B4.2 independent
physical numerical report SHA256
`297114489eb8312733a2e2597f0ee0567f9868552d2bc71d0dd425139368b032`,
the original B4.1 64-shard scalar oracle SHA256
`7e564d188651aeabdc284328ea65705bcb0b5571468b9f70d5dcacaa3f5493b8`,
and the original B4.4 six-phase timing report SHA256
`4e0abf43dafab145b2dde6846d5504470c3d122da80923c34441e82877881b81`.
The original B2.3 production ELF/map and accepted P03 shell remain
immutable; the profile ELF is a distinct instrumented artifact, not a
replacement for the original production image.

## Measured reset-profile results

The physical profile captured 1,024 rows. The specially selected trace
ordinal 1023 is retained and audited separately; the ordinary distribution
below contains **1,023 frames**. The actual A53
`CNTFRQ_EL0` was **99,999,001 Hz**.

### Overall reset service

| Statistic | Result |
|---|---:|
| Ordinary frame count | 1,023 |
| Median | **5,826.767549 ms** |
| P95 (nearest rank) | **5,826.881051 ms** |
| Minimum | 5,826.591948 ms |
| Maximum | 5,827.041922 ms |
| Median raw ticks | 582,670,934 |
| Sum raw ticks | 596,070,873,266 |

### Five measured reset subphases

| Subphase | Median (ms) | P95 (ms) | Share of summed reset ticks |
|---|---:|---:|---:|
| Mutable 27-core memcpy | 7.0247 | 7.0317 | 0.12% |
| Mutable cache clean/invalidate | 1.6885 | 1.6898 | 0.03% |
| Mutable SHA-256 readback | 2,908.5991 | 2,908.6798 | 49.92% |
| Original immutable cache invalidate | 0.8392 | 0.8394 | 0.01% |
| Original immutable SHA-256 | 2,908.5978 | 2,908.6824 | 49.92% |

Unattributed counter/control residual: median **0.0157 ms**, reported share
**0.00%** after rounding.

The two SHA-256 scans together account for approximately **99.84% of the
measured reset-service tick sum**. This is the main bottleneck finding:
the measured reset interval is dominated by integrity verification, not
by copying the mutable 27-core state. The memcpy median is about 7.0 ms,
whereas each of the two full SHA-256 passes is about 2.909 seconds.

The percentages are calculated from summed ticks across the 1,023 ordinary
rows. **Do not add phase medians and present the result as the overall
median**; medians are not additive. Use the overall reset-service
distribution for its own median/P95 and the sum-based shares for attribution.

## Interpretation and boundaries

1. This is a real, independently verified, instrumented **A53 reset-service**
   profile from one physical KV260 session. It is not an FPGA-only neural
   compute measurement.
2. The profile uses a separate profiling ELF and additional timer/counter
   instrumentation. Its observed timing includes the cost of that
   instrumentation; do not silently equate it with an uninstrumented
   production run.
3. The two SHA operations protect the original immutable backup and restored
   mutable contexts. Removing, weakening or sampling these checks changes
   the integrity contract. Any alternative verification strategy must be
   designed, separately versioned, and proven to preserve the required
   original-model/state guarantees before a performance claim.
4. This result does not independently prove exclusive DDR ownership by
   FSBL/boot firmware, TF-A, U-Boot, Linux, RPU, PL DMA or other masters.
   The additional experimental profile region was
   `[0x42400000,0x42440000)` (262,144 bytes); its independent ownership
   remains unproven. Static non-overlap is not proof of exclusive runtime
   ownership.
5. It does not establish a pure PL neural-engine time, PL frequency in
   seconds, FPGA speedup, system energy, or a repeated Track A-vs-Track B
   comparison. The independent report explicitly records the paired
   benchmark as not accepted.
6. Official Track B MNIST TEST remains **SEALED_NOT_ACCESSED**.

## Next research gate — proposed P08-B4.5

Before another destructive hardware session, first design and review a
separate six-session paired Track A/Track B protocol (AB / BA / AB, three
pairs), using the exact frozen source identities, 1,023 ordinary frames
per run, selected trace ordinal 1023 isolated, independent cold-boot/
recovery accounting, actual per-run A53 counter frequency, and matched
complete image-service start/end boundaries. Track A and Track B are
different workloads (42 vs. 1,010 neurons; 26 vs. 702 dispatches), so even
a successful repeated comparison is a system/workload comparison, not a
matched-complexity or pure FPGA speedup claim.

The B endpoint must include the complete per-image reset/restore, ingress,
scheduler/pager reinitialization, all 26 ticks, 702 dispatches, routing,
required physical trace reads, receipt validation and durable result
journal. The A endpoint must use the already accepted complete image-service
boundary. Keep PL counters in their own clock domain; never convert them
using A53 `CNTFRQ_EL0`.

Before authorizing any further JTAG/DDR experiment, audit the full PS/PL
memory map and runtime ownership (including boot firmware, Linux, RPU and
DMA), identify every destructive region, and obtain fresh explicit operator
approval. If ownership cannot be established or bounded safely, stop and
redesign rather than assuming a region is free. Do not rerun the completed
B4.4.2 physical experiment merely to reproduce this report.

**Primary implementation/runbook:** `docs/P08_B44_PROFILE1024_PHYSICAL_RUNBOOK.md`.
**Source/build development history:** `docs/P08_B4_4_1_RESET_PROFILING_DEV_RUNBOOK.md`.
**Original uninstrumented full1024 timing context:** `docs/P08_B4_4_SINGLE_SESSION_TIMING_ANALYSIS.md`.
