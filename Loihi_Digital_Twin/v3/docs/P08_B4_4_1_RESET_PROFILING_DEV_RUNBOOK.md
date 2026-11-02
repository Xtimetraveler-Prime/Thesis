# P08-B4.4.1/B4.4.2 — Independent original 27-context reset profiler (SOURCE ONLY)

**No new Vitis ELF, physical KV260 session or profiling benchmark has been
performed or approved.** Accepted full1024 original B2.4 A53 physical
numerical/26tick FNV report
/home/dna/Thesis_Evidence/p08_b4_2_independent1024_20261102T184928Z.json,
SHA256 297114489eb8312733a2e2597f0ee0567f9868552d2bc71d0dd425139368b032.
Original 1023 ordinary-frame six-phase physically grounded A53 timing report
/home/dna/Thesis_Evidence/p08_b4_4_first1024_one_session_descriptive_20261102T191317Z.json,
SHA256 **4e0abf43dafab145b2dde6846d5504470c3d122da80923c34441e82877881b81**.
Physical A53 CNTFRQ 99,999,001Hz, median 13,034.1115ms/image;
27-context reset 5826.6933ms (44.6953% sum-of-service);
26tick mixed CPU/PL phase 6935.0696ms (53.2157%).

## Newly implemented source

New stacked development branch agent/v3-p08-b44-profiling is based on
draft PR #53 (itself stacked on draft B3 PR #52). Original accepted
B2.3 full1024 firmware, original P08-B2.2 reset, frozen 33 B2.4 files,
P03 BIT/XSA/LTX, P07, physical B3/B4 and Track A evidence,
root LitReview.md and official MNIST TEST are NEVER modified.

**B4.4.1: Original 27x512KiB reset profiled PORTABLE C11 clone:**
software/p08/p08_b4_4_profile_reset.h and .c contain new independent
function p08_b44_profile_reset_image, separate from the accepted
production p08_b2_reset_image. It verifies all 27 immutable source
SHA256 before the first live DDR copy, performs the original 27
memcpy operations with destination cache clean/invalidate/barriers,
and validates all 27 destination SHA256 before accepting the original
reset receipt/generation. Clock invalidity fails closed. It records
disjoint A53 time for (1) immutable source cache invalidate,
(2) immutable source SHA256, (3) mutable memcpy, (4) mutable cache
clean/invalidate, (5) mutable destination SHA256. The remainder is
**unattributed timing/control/idle/clock overhead**. Integrity
overhead is scientifically intentional; it is NOT isolated DDR/PL
compute time. Source has NOT been built/run on KV260.

Native GCC differential source tests:
tests/native/p08_b44_reset_profile_diff.c and
tests/test_p08_b4_4_1_profile_reset_native.py
allocate real 27x512KiB record-sized synthetic contexts, generate
real pinned original P07 SHA256, run production original AND profiled
new C reset independently for two generations, compare all 13.5MiB
restored bytes and every receipt field, and verify source tampering
causes original and cloned paths to poison with identical fault stage
BEFORE mutable copy. None of this runs physical FPGA.

**B4.4.2: EXPERIMENTAL separate 1024-image A53 profiling source:**
software/p08/p08_b44_profile_full1024_a53.c clones original 1024
firmware with DISTINCT new embedded identity
P08_B44_ORIGINAL_27CORE_RESET_PROFILE_1024_A53_V1.
Production original signed ELF and source remain untouched. Same
neural/routing algorithms, exact original 1024 TRAIN-source images,
original 1024 result journal and six-phase A53 sidecars; replaces
only per-image state reset with the profiled clone.
It also emits a new additional 1024x256B reset-only profile record
at the CANDIDATE DDR span [0x42400000,0x42440000), outside original
P08 B2.3 0x422... journal and 0x423... A53 timing region, and
before 0x430... immutable backup. Static disjointness DOES NOT
establish independent PS firmware/DMA DDR ownership or authorization.
The new sidecar is emitted after original A53 service timer closes,
but additional timer probes and cache effects change runtime.
DO NOT pretend experimental timing equals uninstrumented B2.3 timing.

Each experimental 256B record uses exactly 64 little-endian uint32:
word0 magic 0x50523434; 1 version1; 2 ordinal; 3 PASS;
4 generation ordinal+1; 5 27 verified contexts;
6 original 14155776 copied bytes; 7 27 source SHA checks;
8 27 destination SHA checks; 9..10 actual A53 CNTFRQ;
11..12 full reset ticks; 13..22 five 64-bit disjoint phases;
23..24 unattributed ticks; 25..60 zeros;
61 CRC32 first61 words; 62 zero; 63 original DONE sentinel.
Python PC-only strict structural parser
scripts/p08_b44_reset_profile_sidecar.py and native synthetic
tests/test_p08_b44_reset_profile_sidecar.py verify all1024 ordinal,
CRC, SHA counts, exact observed frequency, additive phase/residual,
and selected trace image ordinal 1023 exclusion. Even structural
PASS does NOT prove actual physical data provenance, neural 1024
parity, or repeated A/B speed.

## NEXT GATES — DO NOT RUN NEW DESTRUCTIVE JTAG YET

1. Genuine separate **Vitis 2025.2** AArch64 ELF/map must be built from
   the new A53 source and the new profiled reset C, plus ORIGINAL
   production reset C (for binding) and accepted P07 neural files.
   Independent ELF PT_LOAD/entry/heap/stack/BSS/region admission,
   immutable original P03 shell/XSA and genuine NEW SHA pins are
   required. This candidate has NOT been built.
2. Separate physical JTAG runner/capture and independent verifier must
   be developed for the 1024x256B new profile region **in addition to**
   old six original DDR source-readback, old 1024 result journals,
   old 1024 timing rows and 1024 terminal mailbox. Require same-session
   original all-1024 scalar neural/FNV/output spike parity before
   accepting any profiling timing results. Do not reuse old B3/B4
   accepted ELF hash or operator physical approval for this new ELF.
3. Separately instrument inside the original 26tick mixed phase:
   per-core page-in/out and cache, AXI/MMIO dispatch+poll,
   trace readback, software routing and barriers. Profile them with
   independent signed variant and numerical equality, and do not
   conflate PL cycles with A53 CNTVCT wall time.
4. Predeclare genuine **A-vs-B** six rebooted paired sessions
   AB/BA/AB with original 1024 frozen TRAIN-only IDs, 1023
   ordinary images, ordinal1023 trace isolated, equal full A53
   service boundaries and per-run observed CNTFRQ.
   The original earlier six Track A sessions are pairs of A2.1-vs-A2.2
   instrumentation, NOT true A-versus-B measurements. These
   different-sized networks cannot support equal-workload speedup.
5. P08-B final scientific limitations/provenance report plus explicit
   operator milestone acceptance and independently authorized merge.
   No official TEST, power, pure PL acceleration or PS/DDR ownership
   exclusivity is inferred.

## Operator reproducible PC-only tests

~~~bash
cd ~/Git/Thesis
git fetch origin
git switch --track origin/agent/v3-p08-b44-profiling
# On a subsequent pull: git switch agent/v3-p08-b44-profiling
git pull --ff-only origin agent/v3-p08-b44-profiling
git status --short
git rev-parse HEAD
source ~/Git/Thesis/.venv-p08/bin/activate
cd Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p08_b4_4_1_profile_reset_native.py \
  tests/test_p08_b44_reset_profile_sidecar.py \
  tests/test_p08_b4_4_single_run_timing_audit.py \
  tests/test_p08_b4_2_monitor_mailbox_pc_only.py

python -m compileall -q scripts/p08_b44_reset_profile_sidecar.py
~~~

No new JTAG commands are supplied because the genuine profiling
ELF/sidecar physical admission is NOT yet implemented/accepted.
