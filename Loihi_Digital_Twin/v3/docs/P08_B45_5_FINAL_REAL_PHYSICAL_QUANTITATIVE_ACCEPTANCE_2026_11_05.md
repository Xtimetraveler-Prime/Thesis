# P08-B4.5.5 — ACCEPTED operator-source quantitative closeout

**Status: CLOSED / OPERATOR ATTESTED REAL PHYSICAL SYNTHESIS, 2026-11-05 local (Nov 6 UTC).**

The accepted B4.5.5 four-source PC-only original/optimized 1024
reconstruction script output was provided by the operator, not read
from their PC by GitHub. Its new source-locked output receipts are:

- \`/home/dna/Thesis_Evidence/p08_b45_full1024_synthesis_20261106T011541Z.json\`:
  SHA-256 \`b04aa0ada133a61ce052ce40f7aa7dbf667da6958031cfdc63b99cc57354eff0\`.
- \`/home/dna/Thesis_Evidence/p08_b45_full1024_synthesis_20261106T011541Z.md\`:
  SHA-256 \`8cd181ecedb407e04418ef5ab121e6560a8fef3a5908ac0ec39acfbdae41fef3\`.

The pasted Markdown reports that all FOUR original/optimized
source SHA-256 pins were read and the two new 1024x256B A53
service+reset sidecar captures independently reopened and
verified. It is a local-operator attestation, not independent
cloud access to original raw physical bytes.

## Final accepted B4.5.5 measurements

| Per-image measurement (1023 ordinary frames) | Original B4.4/B4.4.2 | V2 authenticated once | V2 unchecked |
| --- | ---: | ---: | ---: |
| Reset median ms | 5826.767549 | 8.766998 | 8.732007 |
| Complete A53 image-service median ms | 13034.111501 | 7225.137459 | 7222.415632 |
| Descriptive reset ratio of distinct physical-session medians | 1.00x | 664.63x | 667.29x |
| Descriptive complete-service ratio of distinct physical-session medians | 1.00x | 1.804x | 1.805x |

The original reset baseline has a **separate profile-instrumented
ELF/physical session** from original complete service; these are
descriptive cross-session ratios, not matched random trial-level
estimates. Each optimized variant has one independently accepted
real physical 1024-image run, with original 1024 frozen predictions,
all ten output spike counts, full 26tick 1010-neuron FNV traces,
A53 clock/timing, all27 postrun context backup hashes verified.

## Authentic new optimized six-phase A53 attribution

| Service phase | Auth-once median ms | Auth-once sum share | Unchecked median ms | Unchecked sum share |
| --- | ---: | ---: | ---: | ---: |
| Reset 27 original contexts | 8.767 | 0.12% | 8.732 | 0.12% |
| Encode input | 18.681 | 0.26% | 18.682 | 0.26% |
| Initialize virtualized scheduler | 228.103 | 3.16% | 228.103 | 3.16% |
| **All 26 ticks / 702 physical dispatches, DDR paging, routing** | **6944.179** | **96.11%** | **6941.350** | **96.11%** |
| Validate neural receipt | 0.001 | ~0.00% | 0.001 | ~0.00% |
| Commit neural journal | 25.535 | 0.35% | 25.534 | 0.35% |

Percentages are shares of **summed A53 service timer ticks**,
not medians divided by medians. Original B4.4.2 SHA phases
accounted for ~99.84% of original reset ticks. Once those
full-context scans were removed from the per-image path, the
dominating phase became the MIXED software/FPGA virtualized
26tick dispatch/paging/routing interval (~96.11%).
**Do not interpret the 6944ms as isolated PL compute**:
it includes A53 pager, memory copies, MMIO, routing,
wait/poll and trace handling.

## Chosen architecture / next research direction

The user explicitly selects **V2 authenticate-once** as the
primary optimized Track B research architecture for P08-B4.6:
\`B_AUTH_ONCE_UNPROTECTED_V2\`, not the unchecked
performance-bound and NOT a falsely relabeled original
B4.4 per-image full-SHA Track B. Exact accepted V2 ELF
SHA \`a19b50dffb21d897caa1eb19ea62fadd5dec0a1adc27d99354b2d9b6adab0e85\`;
original once independent full1024 verification SHA
\`06a007b73cb3ff31c02910224e28690215bded5bdb401973e6a0347e44d0d65a\`.
Unprotected backup memory, no XMPU write exclusion and
no proof against transient DDR modification remain explicit.

B4.5.5 is CLOSED at the above evidentiary level.
B4.6.1/2 are the next active **PC-only** gates: frozen
original Track A A2.1 (42 neurons, 26 dispatches)
versus B_AUTH_ONCE (1010 neurons, 702 dispatches),
same 1024 original TRAIN-derived raw images but
different frozen learned weights / inference workloads.
Compare system/workload image service, NOT model-independent
FPGA arithmetic efficiency, neural accuracy superiority,
energy or pure PL compute. No official MNIST TEST use.

The accepted full1024 original model, P03 bitstream/XSA,
previous ELF/map, genuine pilot16/1024 receipts and
original operator raw captures remain immutable.
No further destructive JTAG/DDR permission or PR merge
is implied by this research closeout.
