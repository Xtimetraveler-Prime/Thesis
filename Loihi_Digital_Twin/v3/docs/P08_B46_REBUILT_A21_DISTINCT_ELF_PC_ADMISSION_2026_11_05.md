# P08-B4.6.2R — new rebuilt A2.1 A53 ELF, distinct source admission (PC ONLY)

**User rebuild: successful (build-only), original historical A2.1 ELF NOT reproduced.**

The user ran the unchanged \`scripts/build_p08_a2.sh\` under Vitis 2025.2,
with original accepted P03.2c XSA. Its actual output:

- Original historical P08-A2.1 first accepted ELF SHA:
  \`fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0\`,
  originally built under \`/tmp/v3_p08_a2_build_20261018T193149Z\`.
  The historical genuine ELF is missing after an operator Linux PC reboot.
- New rebuilt A2.1 real firmware SHA:
  \`fa926823c291b70267c099db00c5052e62405444db58863436c1b2f950a58793\`,
  durable \`/home/dna/Thesis_Evidence/p08_a2_1_rebuild_20261106T023403Z/vitis_workspace/p08_a2_board.elf\`.
- Accepted original P03.2c XSA SHA
  \`52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f\`.
- Builder PASS:
  \`P08_A2_A53_VITIS_BUILD_PASS=1\`,
  \`P08_A2_1_ELF_DDR_ISOLATION_PASS=1\`,
  \`P08_A2_1_VITIS_BUILD_PASS=1\`,
  \`P08_A2_1_KV260_LATENCY=NOT_RUN\`.
- Old A2.1 hash comparison reported
  \`ORIGINAL_A21_BINARY_REPRODUCED=0\`.
  This is *not* by itself a proof of incorrect neural behavior;
  it is a new binary and requires separately authenticated tests.

**The old original SHA is preserved and must NOT be overwritten,
mutated or re-labeled. All historical A3.2 original accepted physical
results remain associated with the original historical SHA.**

## New source-gated implementation

New descendant branch:
\`agent/v3-p08-b46-a21-rebuild-admission\`.

\`scripts/p08_b46_a21_rebuild_admission.py\` rechecks the actual user's
NEW reconstructed A2.1 ELF and complete original Vitis build stage
on the PC:

1. Hard-pins both old SHA and NEW rebuilt candidate SHA, original P03.2c
   XSA bytes, Vitis build identity/NOT_RUN and actual build-success log.
2. Independently reads ELF64 little-endian AArch64 header; checks ELF
   PT_LOAD entries against reserved original [0x40000000,0x44000000)
   DDR using both physical and virtual load addresses, ELF firmware
   identity string, and builder's original readelf program header proof.
3. Byte-for-byte SHA matches **all staged original P08-A2.1,
   original P07 sources+headers, and original P03 sources+headers**
   against present frozen Git source, including nested and flat
   original P07 headers. Rejects a drifted staged compiled source.
4. Requires genuine build rooted in durable storage outside Git,
   denies /tmp, /var/tmp, /dev/shm, and never overwrites accepted
   artifacts. Emits NEW no-overwrite external JSON containing
   original+rebuilt SHA, full staged source hashes, ELF LOAD geometry
   and explicit **physical neural / A53 timing reacceptance FALSE**.
5. Does NOT interact with KV260, run XSDB/Vivado, access t10k TEST
   or modify existing physical evidence.

The prior exact-original \`scripts/p08_b46_auth_once_source_gate.py\`
default remains STRICT, requiring the genuinely historical SHA.
A new explicitly selected pair of options
\`--a-rebuilt-admission\` + \`--a-rebuilt-xsa\` makes it independently
**re-run** the reconstructed candidate's original source/ELF/
P03 XSA inspection and check it equals the saved source manifest,
before the original B1 canonical 1024-image TRAIN source audit.
The new schema labels the A side:
\`A_REBUILT_A21_CANDIDATE_42_NEURONS_26_DISPATCHES\`
and clearly records **NO accepted physical revalidation**;
selected B is still original, genuine SHA-locked
\`B_AUTH_ONCE_UNPROTECTED_V2\` with the accepted scalar/FNV evidence.

**Passing BOTH PC checks is NOT permission to run the revised
A/B six-session physical benchmark.** A new A53 candidate requires
independent original P07 packed neural oracle and real A53
image-sidecar revalidation on an explicitly approved hardware run.
The old A2.1 physical scripts hard-pin the historical SHA and
SHALL NOT be patched to silently run the new candidate.
A separate fail-closed candidate/PS-DDR recovery runner and new
physical admission must be reviewed before any board launch.

## Operator VS Code terminal: pull and verify source code

~~~bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p08-b46-a21-rebuild-admission
git pull --ff-only origin agent/v3-p08-b46-a21-rebuild-admission

source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
PYTHONPATH="$PWD/scripts:$PWD/src" python3 -m pytest -q -rs \
  tests/test_p08_b46_auth_once_source_gate.py \
  tests/test_p08_b45_full1024_latency_synthesis.py \
  tests/test_p08_b45_perf_full1024_independent_cli.py \
  tests/test_p08_b45_full1024_reset_bind_repair.py
~~~

## Operator's saved real rebuilt A2.1 and exact original XSA

~~~bash
export P08_A2_BUILD_DIR="$HOME/Thesis_Evidence/p08_a2_1_rebuild_20261106T023403Z"
export B46_A_ELF="$P08_A2_BUILD_DIR/vitis_workspace/p08_a2_board.elf"
export P03_DIAG_REPORTS="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports"
export B46_A_XSA="$P03_DIAG_REPORTS/p03_2_ps_mmio.xsa"

sha256sum "$B46_A_ELF" "$B46_A_XSA"
cat "$P08_A2_BUILD_DIR/build_identity.txt"
~~~

Expected rebuilt ELF \`fa926823c291b70267c099db00c5052e62405444db58863436c1b2f950a58793\`;
accepted P03 XSA \`52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f\`.
Stop on wrong actual SHA. No Vitis rebuild is needed again.

## PC gate 1 — independently source/ELF-admit NEW A2.1

~~~bash
export B46_A_REBUILT_ADMISSION="$HOME/Thesis_Evidence/p08_b46_a21_rebuilt_source_admission_$(date -u +%Y%m%dT%H%M%SZ).json"

PYTHONPATH="$PWD/scripts:$PWD/src" python3 \
 scripts/p08_b46_a21_rebuild_admission.py \
 --build "$P08_A2_BUILD_DIR" \
 --xsa "$B46_A_XSA" \
 --out "$B46_A_REBUILT_ADMISSION"

sha256sum "$B46_A_REBUILT_ADMISSION"
~~~

Expected:
\`P08_B46_NEW_A21_SOURCE_AND_REAL_ELF_PC_ONLY_PASS=1\`,
\`P08_B46_OLD_A21_HISTORICAL_ACCEPTANCE_REPRODUCED=0\`,
\`P08_B46_NEW_A21_PHYSICAL_NEURAL_PARITY_AND_TIMING_PENDING=1\`,
\`P08_B46_KV260_JTAG_AUTHORIZED=0\`.

## PC gate 2 — source-match with B_AUTH_ONCE for 1024 original TRAIN images

~~~bash
export B46_B_ONCE_ELF="$HOME/Thesis_Evidence/p08_b45_perf_once_full1024_V2_20261105T192804Z/vitis_workspace/p08_b45_perf_once_full1024.elf"
export B46_A_STAGE="$HOME/Thesis_Evidence/p08_a3_2_stage1024_20261019T003150Z"
export B46_B_ORACLE="$HOME/Thesis_Evidence/p08_b4_1_full1024_scalar_20261102T143900Z.json"
export B46_B_ONCE_REPORT="$HOME/Thesis_Evidence/p08_b45_perf_once_full1024_V2_verified_20261106T005213Z.json"
export B46_B45_SYNTHESIS="$HOME/Thesis_Evidence/p08_b45_full1024_synthesis_20261106T011541Z.json"

export B46_SOURCE_REPORT="$HOME/Thesis_Evidence/p08_b46_Arebuild_vs_Bauthonce_source_$(date -u +%Y%m%dT%H%M%SZ).json"

PYTHONPATH="$PWD/scripts:$PWD/src" python3 \
 scripts/p08_b46_auth_once_source_gate.py \
 --a-elf "$B46_A_ELF" \
 --a-rebuilt-admission "$B46_A_REBUILT_ADMISSION" \
 --a-rebuilt-xsa "$B46_A_XSA" \
 --b-once-elf "$B46_B_ONCE_ELF" \
 --a-stage "$B46_A_STAGE" \
 --train-data-dir "$PWD/data/mnist_raw" \
 --frozen-b "$PWD/artifacts/p06_b24_frozen_1000" \
 --b-oracle "$B46_B_ORACLE" \
 --b-once-report "$B46_B_ONCE_REPORT" \
 --b45-synthesis "$B46_B45_SYNTHESIS" \
 --out "$B46_SOURCE_REPORT"

sha256sum "$B46_SOURCE_REPORT"
~~~

Expected:
\`P08_B46_REBUILT_A21_VS_AUTH_ONCE_FROZEN_1024_TRAIN_POPULATION_PASS=1\`,
\`P08_B46_TRACK_A_REBUILT_CANDIDATE_PHYSICAL_REACCEPTED=0\`,
\`P08_B46_NEW_SIX_SESSION_STUDY_JTAG_AUTHORIZED=0\`,
\`P08_B46_SOURCE_GATE_PC_ONLY_PASS=1\`.

## Preserve reconstructed original build (not /tmp)

The operator's entire build, stage sources, ELF, logs and identity are
already under \`$HOME/Thesis_Evidence\`. Preserve them, hash and archive
to a NEW destination (no overwrite). Copy onto independent non-volatile
drive/cloud backup and re-verify SHA. The archive is NOT the original
historical ELF and must never replace previously signed physical
artifacts. Do not publish proprietary/private board headers if any.

~~~bash
cd "$HOME/Thesis_Evidence"
tar -czf "$(basename "$P08_A2_BUILD_DIR").tar.gz" \
 "$(basename "$P08_A2_BUILD_DIR")"
sha256sum "$(basename "$P08_A2_BUILD_DIR").tar.gz"
~~~

## Next gates AFTER operator two report SHAs

- Verify reconstructed A candidate vs original A2.1 firmware build
  source and exact A53 timer boundaries (original 4 timestamp intervals)
  and analyze build difference; no assumption equal runtimes.
- Implement distinct source-pinned rebuilt-A2.1 1024 physical runner;
  retain original A2.1 historical runner unmodified, fail on original
  DDR / FPD+LPD width / independent P07 oracle / JTAG ownership.
- User explicitly authorizes a separate disposable physical A2.1
  revalidation session and recovers/reboots KV260 afterward.
- Independent original 1024 packed oracle and A53 service sidecar
  verify genuinely reconstructed candidate before final B4.6
  AB / BA / AB six-session physical repeated experiment.
- Selected B stays original genuine once V2 and remains explicitly
  unprotected hardware backup. Historical accepted SHA, TEST seal and
  original six physical A2.1/A2.2 observations are untouched.

**No new hardware has been visited in this recovery step.**
