# P08-B4.4.1/B4.4.2 — Independent original 27-context reset profiler (SOURCE ONLY)

## 2026-11-02 real Vitis first attempt staging failure — shell COPY BUG FIXED, local retry PENDING

The operator ran the genuine separate Vitis 2025.2 B4.4
build with the unchanged original B2.3 ELF, P03 report/XSA,
and original B2.2 SHA pins. Strict Python source admission
stopped BEFORE platform build/link:

    ValueError: new Vitis source stage incomplete/extra:
    missing={'p08_b44_profile_full1024_a53.c',
             'p08_b4_4_profile_reset.c',
             'p08_b4_4_profile_reset.h'},
    extra={'p08_b2_3_image_only_a53.c'}

**Cause:** the first shell COPY loop still staged the old
B2.3 A53 main and omitted the three new B4.4 profile C/H
files. The Python builder correctly FAIL-CLOSED. This is
not evidence of a Vitis compiler, XSA, P03 or FPGA problem;
the newer A53 profiling ELF was NOT built or deployed.

Fix: in scripts/build_p08_b44_profile_full1024.sh,
the real shell copy lists now stage the NEW separate
A53 main and original-reset profiling C/H and forbid the
old B2.3 main. The Python builder offers read-only
--check-stage-only to verify the ACTUAL copied 21 C and
21 header inputs before the script even launches Vitis,
and emits
P08_B44_ACTUAL_SHELL_STAGED_PROFILE_SOURCE_EXACT_PASS=1.
An independent native regression parses the real shell
copy loops and compares their union to builder.SOURCES
and builder.HEADERS. It also recreates the EXACT prior
extra-old-main/missing-three-files error as a negative test.

The existing unsuccessful operator external build dir has
a partial staged copy. Preserve it; do NOT overwrite or
remove it, and do NOT run its nonexistent profile ELF.
After pulling and passing native tests, retry to a new
unique external directory:

~~~bash
cd ~/Git/Thesis
git fetch origin
git switch agent/v3-p08-b44-profiling
git pull --ff-only origin agent/v3-p08-b44-profiling
source ~/Git/Thesis/.venv-p08/bin/activate
cd Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python -m pytest -q -rs   tests/test_p08_b44_build_offline.py   tests/test_p08_b44_profile_elf_admission.py   tests/test_p08_b4_4_1_profile_reset_native.py   tests/test_p08_b44_reset_profile_sidecar.py

# Re-source original genuine Vitis 2025.2 toolchain as needed;
# keep P07_B4L_REPORTS / P08_B44_ORIGINAL_ELF /
# P08_B2_RESET_PINS pointing to the accepted originals.
export P08_B44_BUILD_DIR="$HOME/Thesis_Evidence/p08_b44_reset_profile_retry_$(date -u +%Y%m%dT%H%M%SZ)"
if test ! -e "$P08_B44_BUILD_DIR"; then
  bash scripts/build_p08_b44_profile_full1024.sh
else
  echo "NO-GO: choose a NEW retry directory" >&2
fi
~~~

The first new expected marker is
P08_B44_ACTUAL_SHELL_STAGED_PROFILE_SOURCE_EXACT_PASS=1.
A genuine Vitis 2025.2 compilation/linker/map and distinct
profile ELF64 offline admission must then succeed; no
destructive profiling run is authorized by these source checks.
Independent hardware 1024 profile sidecar capture + genuine
original scalar/FNV parity verification is not yet implemented.

---

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


## New B4.4.2 local GENUINE experimental A53 ELF/map static admission (source implemented, ELF still absent)

The new PC-only script
scripts/p08_b44_profile_elf_admission.py compares a separately
genuinely built experimental Vitis 2025.2 A53 ELF/map to the
ORIGINAL signed full1024 B2.3 ELF. It requires:
- Existing original B2.3 ELF SHA
  0c2de1656eff897e71d6d4fffe5575db9969baf7d3da7b82a2ec765447d36ee1,
  original identity and no experimental identity.
- Original accepted routed P03 XSA SHA
  52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f.
- Original generated 27-core source SHA header SHA
  5be79b38ec7f42622573a7fa59adb689a65bfcf5d8e5a6e8cdaec0e75c9f7171.
- New unique experimental embedded A53 identity and unique terminal
  marker, not the accepted original B2.3 firmware marker.
- New genuine Vitis linker map with actual executable main,
  p08_b44_profile_reset_image, ELF64 AArch64 e_machine=183,
  valid entrypoint/PT_LOAD all in <0x40000000 (candidate),
  nonoverlapping memory PT_LOAD ranges.
- Static proposed 256KiB added DDR sidecar region, exact
  original sealed boot/test scope, **NO destructive JTAG permission**.

Local OFFLINE negative tests:

~~~bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p08_b44_profile_elf_admission.py
~~~

After the operator produces a **genuine separately compiled**
profiled image and Vitis linker map, and ONLY THEN, one new offline
preflight can be run with actual paths. These are symbolic variables,
NOT existing accepted physical artifacts:

~~~bash
export P08_B44_PROFILE_ELF="/absolute/path/to/NEW_b44_profiler.elf"
export P08_B44_PROFILE_MAP="/absolute/path/to/NEW_b44_profiler.map"
export P08_B44_ORIGINAL_ELF="$HOME/Thesis_Evidence/p08_b2_3_image_only_build_20261102T040903Z/vitis_workspace/p08_b2_3_image_only_1024.elf"
export P08_B44_ORIGINAL_XSA="$P07_B4L_REPORTS/p03_2_ps_mmio.xsa"
export P08_B44_ORIGINAL_PINS="$HOME/Thesis_Evidence/p08_b2_2_original_reset_pins_20261102T005118Z/p08_b2_2_original_context_sha256.h"
export P08_B44_ELF_AUDIT="$HOME/Thesis_Evidence/p08_b44_elf_readonly_$(date -u +%Y%m%dT%H%M%SZ).json"
test ! -e "$P08_B44_ELF_AUDIT"

PYTHONPATH="$PWD/src" python scripts/p08_b44_profile_elf_admission.py \
  --profile-elf "$P08_B44_PROFILE_ELF" \
  --profile-map "$P08_B44_PROFILE_MAP" \
  --original-elf "$P08_B44_ORIGINAL_ELF" \
  --xsa "$P08_B44_ORIGINAL_XSA" \
  --pins-header "$P08_B44_ORIGINAL_PINS" \
  --out "$P08_B44_ELF_AUDIT"
sha256sum "$P08_B44_ELF_AUDIT"
~~~

The tool must state
P08_B44_SEPARATE_GENUINE_PROFILE_ELF_STATIC_SOURCE_ADMISSION_PASS=1,
P08_B44_NEW_PROFILE_REAL_KV260_RUN_EXECUTED=0, and
P08_B44_NEW_PROFILE_ELF_DESTRUCTIVE_JTAG_AUTHORIZED=0.

If no new genuine Vitis ELF/map exist, **STOP at native source CI**
and DO NOT run the above command with the accepted B2.3 ELF
substituted. Do not reuse historical B3/B4.2 destructive runner
or original B2.3 ELF admission script for this new identity.

A full independent physical source/profiling capture gate remains
to be implemented after genuine Vitis linker/ELF admission, with
separate user confirmation and dedicated recovery-ready board.
The unsigned experimental profiling CLR/CRC sidecar, by itself,
is never physical proof or genuine neural parity.


## NEW genuine Vitis 2025.2 offline profile build now implemented (do not run board)

Two new offline build files:

- software/p08/build_p08_b44_profile_full1024.py — exact
  new imported C/H source list, original full1024 source
  except DIFFERENT experimental A53 entrypoint and extra reset
  profiler, fresh distinct Vitis app/platform and map output;
  no original B2.3 source or original accepted ELF modification.
- scripts/build_p08_b44_profile_full1024.sh — requires new
  outside-repo evidence root, exact original P03 XSA/width
  metrics, immutable accepted B2.2 27 SHA header + manifest,
  SHA-pinned original accepted B2.3 full1024 ELF, Vitis tools.
  Stages ORIGINAL P07 modules into distinct local copied
  source, applies only the historically accepted B4m 10,000
  route ceiling within the new source copy. Runs Vitis 2025.2
  and independently executes the newly separate profile
  AArch64 ELF+map offline admission. Original signed
  firmware and original model assets are unchanged.

**User-local PC-only offline build** (one build, no JTAG):

~~~bash
cd ~/Git/Thesis
git fetch origin
git switch agent/v3-p08-b44-profiling
git pull --ff-only origin agent/v3-p08-b44-profiling
source ~/Git/Thesis/.venv-p08/bin/activate
cd Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p08_b4_4_1_profile_reset_native.py \
  tests/test_p08_b44_reset_profile_sidecar.py \
  tests/test_p08_b44_profile_elf_admission.py \
  tests/test_p08_b44_build_offline.py

# Only after native tests PASS, source your genuine Vitis 2025.2
# environment as in accepted B2.3 build. DO NOT start XSDB.
export P08_B44_ORIGINAL_ELF="$HOME/Thesis_Evidence/p08_b2_3_image_only_build_20261102T040903Z/vitis_workspace/p08_b2_3_image_only_1024.elf"
export P08_B2_RESET_PINS="$HOME/Thesis_Evidence/p08_b2_2_original_reset_pins_20261102T005118Z"
# P07_B4L_REPORTS must remain previously accepted original P03 routed reports.
test -f "$P07_B4L_REPORTS/p03_2_ps_mmio.xsa"
test "$(sha256sum "$P08_B44_ORIGINAL_ELF" | cut -d' ' -f1)" = \
  "0c2de1656eff897e71d6d4fffe5575db9969baf7d3da7b82a2ec765447d36ee1"

export P08_B44_BUILD_DIR="$HOME/Thesis_Evidence/p08_b44_reset_profile_build_$(date -u +%Y%m%dT%H%M%SZ)"
test ! -e "$P08_B44_BUILD_DIR"

bash scripts/build_p08_b44_profile_full1024.sh
~~~

A successful REAL Vitis profile build must report:

~~~text
P08_B44_SEPARATE_GENUINE_PROFILE_ELF_STATIC_SOURCE_ADMISSION_PASS=1
P08_B44_SEPARATE_RESET_PROFILE_1024_A53_ELF_AND_MAP_BUILT=1
P08_B44_NEW_PROFILE_KV260_PHYSICAL_RUN=NOT_RUN
P08_B44_EXPERIMENTAL_DESTRUCTIVE_JTAG_PERMISSION=NOT_GRANTED
~~~

Record output and SHA-256s:

~~~bash
sha256sum \
  "$P08_B44_BUILD_DIR/vitis_workspace/p08_b44_reset_profile_1024.elf" \
  "$P08_B44_BUILD_DIR/vitis_workspace/p08_b44_reset_profile_1024.map" \
  "$P08_B44_BUILD_DIR/p08_b44_profile_elf_ptload_preflight.json"

test -f "$P08_B44_BUILD_DIR/vitis_build.log"
test -f "$P08_B44_BUILD_DIR/readelf_layout.txt"
~~~

The build output is a **new experimental ELF candidate**, not a
successful FPGA experiment. Because profiling changes the
image-service path and newly owns the proposed extra DDR range,
the **new physical JTAG runner with same-session readback and
independent full1024 original scalar/FNV verification is still
not implemented**. Do NOT substitute this profile ELF into
the historical B3 pilot or the accepted B4.2 physical runner.
Stop after the offline build and report exact markers and SHA.
