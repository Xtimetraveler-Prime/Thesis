# P08-B4.5 — Context-reset integrity optimization experiments

**Status (2026-11-03): ACTIVE, PC-only implementation and native validation. No Vitis build or physical KV260 run is authorized by this milestone entry.**

## 1. Motivation and accepted baseline

P08-B4.4.2 physically profiled the original 27-context reset on the KV260 and passed independent same-session provenance, 1,024-image scalar/FNV neural parity, and 1,024 reset-profile record checks.

Accepted reset-profile measurements (one instrumented physical session; 1,023 ordinary frames, selected trace ordinal 1023 isolated; A53 `CNTFRQ_EL0=99,999,001 Hz`):

| Reset component | Median |
|---|---:|
| Complete reset service | **5,826.767549 ms** |
| Mutable 27-context memcpy | 7.0247 ms |
| Mutable cache clean/invalidate | 1.6885 ms |
| Immutable source SHA-256 | 2,908.5978 ms |
| Mutable destination SHA-256 | 2,908.5991 ms |

The two SHA scans account for approximately **99.84% of summed reset-service ticks**. The original uninstrumented B4.4 complete image-service median was 13,034.111501 ms in a separate accepted session. These are distinct experiments and their medians must not be subtracted to claim an optimization delta.

Authoritative source: `P08_B4_4_2_RESET_PROFILE_PHYSICAL_RESULTS.md`.

## 2. Research question

How much of Track B's complete image-service latency is caused by repeatedly hashing the immutable and restored 27-core contexts, and what performance can be recovered while preserving neural inference semantics?

Three versions are compared:

1. **Reference:** accepted B4.4.2 full per-image source and destination SHA-256 checks. This implementation and its evidence remain immutable.
2. **P08-B4.5.1 — authenticated-once restoration:** establish persistent protection/ownership of the immutable backup; authenticate all 27 original records once at session bind; on each image, retain quiescence, protection-state checks, 27 source-header checks, the original copy/cache/barrier sequence, and 27 destination-header checks. No per-image SHA-256 is performed.
3. **P08-B4.5.2 — unchecked-content restoration:** use the same session-level backup ownership/protection and operational memory-safety controls, but perform no SHA-256, P02-header, CRC or other data-content validation at bind or per image. The path still checks pointer/range/size validity, quiescence, protection state, cache callback success, barriers, generation and fail-stop poisoning. This is a deliberately experimental lower-bound, not a production recommendation.

The two variants are separate source modes and must be separately built/pinned. Neither may replace the original production reset or the accepted B4.4.2 profiler.

## 3. Critical integrity precondition

The authenticated-once strategy is only defensible if the immutable backup really remains immutable after the initial SHA pass. A one-time digest does not detect a later payload mutation. The new portable C interface therefore requires:
- a platform callback that **establishes persistent exclusive/read-only ownership** of the entire 27×512KiB backup range before authentication/copy;
- a cheap callback that confirms the protection remains active before and after each reset.

Native tests use mock callbacks only. A mock is not physical evidence. A no-op platform implementation is prohibited for KV260 execution. If a genuine protection/ownership mechanism cannot be implemented or independently established, P08-B4.5.1 must not be physically run under a claim of preserved integrity. The same memory ownership and quiescence prerequisites apply to P08-B4.5.2; removing content checks does not authorize unsafe DDR access.

The additional B4.4 profiling range `[0x42400000,0x42440000)` and original immutable backup range `[0x43000000,0x43D80000)` still require a complete runtime ownership audit across FSBL/boot firmware, TF-A, U-Boot, Linux, RPU, PL DMA and all other relevant masters. Static non-overlap is insufficient.

## 4. Controlled comparison protocol

- Keep the exact accepted P02 contexts, B2.4 frozen model, route tables, P03 bitstream/XSA/LTX, ingress ABI, 26-tick semantics, 27 logical cores, three resident PL slots and 702 dispatches per image.
- Use the same frozen 1,024-image TRAIN-derived validation source population and order as B4.2/B4.4. Do not access official MNIST TEST.
- Each experimental build has a unique source identity, Vitis workspace, ELF SHA-256, linker-map SHA-256, admission report and evidence root. Never overwrite original B2.3 or B4.4.2 artifacts.
- First pass native C11 differential/fault tests, source admission, Vitis offline build and ELF PT_LOAD/BSS/heap/stack/memory-map audit.
- Then, only after independent memory-owner/protection proof, fresh read-only preflight, recovery readiness and new explicit operator approval, run a bounded 16-image physical pilot for each variant. Require exact independent scalar-oracle output/spike/FNV parity before accepting timing.
- Only after each pilot is accepted, run a separately approved full 1,024-image physical session per variant. Preserve all 1,024 neural rows; selected trace ordinal 1023 is analyzed separately and excluded from the 1,023 ordinary latency distribution.
- Measure both reset subspan and complete A53 image service with the same service start/end boundaries. Record actual per-session `CNTFRQ_EL0`; keep PL counters in their own clock domain. Include reset, ingress, scheduler/pager reinitialization, all ticks/dispatches, routing, required trace reads, receipt validation and journal commit in complete service.
- Report medians/P95/min/max per run and paired per-image comparisons against the accepted baseline only when measurement boundaries and instrumentation are demonstrably equivalent. Account for instrumentation perturbation and do not subtract medians from distinct sessions as if they were paired observations.

## 5. Acceptance gates

### P08-B4.5.1 — authenticate once, lightweight per-image checks

- All 27 source SHA-256 checks occur once during session bind; exactly zero source/destination SHA-256 checks occur in each image reset.
- Each image checks all 27 source P02 headers before the first destination write, copies exactly 14,155,776 bytes, performs the original cache/barrier sequence, and checks all 27 destination headers.
- Backup protection is established before authentication and remains positively confirmed throughout the session.
- Native corruption tests prove pre-bind source corruption is rejected; header corruption is rejected per image; a deliberate post-bind payload mutation with the protection callback bypassed is explicitly shown to be undetected, documenting why physical protection is mandatory.
- Operational failures poison the session; no retry after partial restore.

### P08-B4.5.2 — unchecked-content performance bound

- No SHA-256, header, CRC or payload checks are performed by the reset variant.
- It retains the same backup ownership/protection, quiescence, cache maintenance, barriers, copy geometry, generation accounting and fail-stop behavior.
- Native tests explicitly demonstrate that content corruption is not detected; this is expected and must not be misreported as an integrity pass.
- Inference is accepted only if the actual staged frozen source is independently verified before launch and all 1,024 physical neural outputs match the frozen scalar oracle.

### Shared physical acceptance

- Independent same-session JTAG provenance and full 1,024-image neural/FNV/spike parity.
- Exact 27-context restore geometry, 26 ticks, 702 dispatches, 26 barriers, 3 physical slots and unchanged source/model/route identities.
- Complete per-image reset and image-service timing rows, CRC/terminal checks, actual A53 counter frequency, selected trace ordinal isolation.
- Independent DDR ownership/protection and ELF memory-envelope admission.
- Separate immutable reports and fresh evidence roots. Official TEST remains sealed.

## 6. Sequencing and next milestone

P08-B4.5.1 and P08-B4.5.2 are separate experiments. The authenticated-once version is the candidate optimization; the unchecked-content version is a diagnostic lower bound. Do not merge their results or firmware identities.

After B4.5 closes, P08-B4.6 will conduct the previously proposed six-session paired Track A/Track B system/workload comparison in AB/BA/AB order. Track A and Track B have different sizes (42 versus 1,010 neurons; 26 versus 702 dispatches), so even a successful comparison is not matched-complexity or pure FPGA speedup.

No P08-B4.5 physical action is authorized by source/CI success or by the previous B4.4.2 approval.
