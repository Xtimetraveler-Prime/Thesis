# P08-B4.6.1/.2 — frozen Track A versus selected B_AUTH_ONCE study

> **A3.1 TAR DOES NOT BY ITSELF RESTORE A2.1.**
> User found `~/Thesis_Evidence/p08_a3_1_pilot_20261018T203342Z.tar.gz`.
> Original accepted A3.1 pilot used **A2.2 detailed per-tick
> instrumentation** with ELF SHA
> `87cf5fc4fe37d9d053a3c365db8ae9fdc7e782857612f273835cf5e611aba361`,
> whereas the required frozen A2.1 image-only ELF had
> `fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0`.
> Archive contents not yet confirmed. Inspect via
> `tar -tzf "$HOME/Thesis_Evidence/p08_a3_1_pilot_20261018T203342Z.tar.gz"`
> without extracting over saved evidence. If no exact
> SHA-matching original A2.1 ELF exists, build with the
> **existing frozen** `scripts/build_p08_a2.sh` into
> a NEW `$HOME/Thesis_Evidence/p08_a2_1_rebuild_<UTC>`
> after sourcing installed Vitis 2025.2 and checking
> SHA-pinned accepted P03.2c XSA. Any new hash different
> from the original must be labeled a reconstructed candidate:
> do not alter accepted historical source/ELF pins, old
> evidence, or B4.6.2 source admission to make it pass.
> New physical acceptance, if needed, is separately gated.
>

> **IMPORTANT A2.1 SOURCE BLOCKER / NO TEMP-BUILD STORAGE — 2026-11-05.**
> Git's original P08-A3.2.2 capture protocol explicitly
> identifies original A2.1 genuine ELF at
> `/tmp/v3_p08_a2_build_20261018T193149Z/vitis_workspace/p08_a2_board.elf`
> (historical accepted SHA
> `fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0`).
> Operator reports that original directory is now MISSING after
> a Linux PC reboot and no matching original ELF under $HOME.
> Discovered `/tmp/pytest-of-dna` ELF files are SYNTHETIC TEST
> fixtures (SHA `13d6152f339a100ace3c45f01e35d78e82009562ff99a299294be6ba6a75deb0`).
> The A/B source gate must remain NO-GO until a genuine matching
> ELF is recovered or a separate transparent reproducible
> reconstruction and original numerical/hardware admission is completed.
> **DO NOT disable/replace the historical SHA gate.**
> Search archive/snapshot/off-machine backup or moved file names
> before proposing a new Vitis ELF. A reboot or tmpfiles
> cleanup CAN erase /tmp; the exact deletion cause is unknown.
> Mandatory future practice: durable unique
> `$HOME/Thesis_Evidence/<build>` paths OUTSIDE Git for
> ALL meaningful ELFs, .map, stage sources, XSA/bitstream,
> build identities and evidence; copy then SHA256-verify to
> independent persistent backup. NO sole builds in
> `/tmp`, `/var/tmp`, pytest temp or volatile caches.
>

**Selected research architecture: authenticated once, experimental
UNPROTECTED backup, V2 A53 ELF.** Explicit user direction overrides
the earlier unlaunched B4.6 protocol that had selected old B4.4
per-image SHA as the B arm. This document does NOT retroactively
relabel old original B4.4 nor change accepted B4.5 results.

**State: PC SOURCE ADMISSION IMPLEMENTED; NO new physical run
or repeated benchmark has been authorized or performed.**

## Two preregistered arms

- **A_ORIGINAL_A2_1:** original physically accepted Track A A2.1
  42-neuron, 26-dispatch/image, image-level A53 service timer.
  Exact original immutable genuine ELF basename
  \`p08_a2_board.elf\`, SHA256
  \`fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0\`.
  Its original six prior A2.1/A2.2 sessions studied only the
  A image-vs-per-tick instrumentation overhead; those sessions
  are not used as newly repeated A-versus-B_AUTH_ONCE pairs.
- **B_AUTH_ONCE_UNPROTECTED_V2:** genuine accepted 27-virtual-core,
  1010-neuron, 702-dispatch/image Track B V2 one-time
  source SHA bind and per-frame header validations,
  ORIGINAL frozen software oracle and 27 physical postrun backup
  endpoint readbacks. Genuine distinct ELF basename
  \`p08_b45_perf_once_full1024.elf\`, SHA256
  \`a19b50dffb21d897caa1eb19ea62fadd5dec0a1adc27d99354b2d9b6adab0e85\`.
  Original independent once physical SHA
  \`06a007b73cb3ff31c02910224e28690215bded5bdb401973e6a0347e44d0d65a\`;
  B4.5.5 real four-report synthesis SHA
  \`b04aa0ada133a61ce052ce40f7aa7dbf667da6958031cfdc63b99cc57354eff0\`.
  This is explicitly NOT the old per-image full-SHA original
  B4.4 arm and NOT unchecked-content, and has no hardware
  backup write protection proof.

The frozen original A and B source image sequence is the same
1024 first canonical TRAIN-derived seeded validation indices,
in the original order, with **identical raw 784B pixel
SHA-256 for each frame**. A and B have DIFFERENT weights
and neural architectures; never demand identical predictions
ACROSS arms. Each must independently match its OWN
original scalar/packed oracle; preserve original TRAIN/Test seal.
Existing B1 source checks regenerate actual canonical TRAIN split,
verify A stage and original 33-file B freeze and compare original
A/B source IDs/raw pixel SHA. Preserve those checks in B4.6.

## Six independent matched temporal sessions

Pre-register the exact scheduled sequence **A B / B A / A B**
(3 pairs, six physical coldboots, 3 accepted independent runs per
arm). No original A2.1/A2.2 timing instrumentation pairs,
old original B4.4 numerical run or B4.5 once accepted
single-run may substitute for a NEW session in this design.

Each session requires its own fresh exact source/ELF pin and
time-boundary audit, independent original model FNV/outputs,
1024 captured frame ordinal receipts, 1023 ordinary timings
excluding isolated trace ordinal 1023, original real per-session
CNTFRQ and signed new no-overwrite raw evidence. For Track
B_AUTH_ONCE, preserve all27 post-run backup records and
recovery/reboot. These A53 service timers include software+PL
and are NOT isolated FPGA neural arithmetic. All failures,
retries and boot/environment changes require a new append-only
session log, never silent replacement.

**Significant existing engineering boundary:** the historical
Track A \`scripts/run_p08_a3_2_1024.sh\` and new Track B
\`scripts/p08_b45_perf_full1024_physical_run.py\` are separate
historical launchers with different DDR overwrite regions,
gate requirements, sidecar schemas and JTAG launch paths.
This B4.6.2 PC source gate does NOT prove that their complete
A53 service boundaries and startup/recovery protocols are
interchangeable or that a physical six-session orchestrator is
implemented. No new destructive hardware command is
provided before a separate audited adapter, review and
per-session risk approval. The user's acceptance of
unprotected backed memory is a research integrity tradeoff,
not proof of DDR/boot/DMA ownership for EITHER arm.

## B4.6.2 PC-only source gate

New \`scripts/p08_b46_auth_once_source_gate.py\` creates one
new outside-checkout JSON with:

- strict original Track A2.1 ELF SHA and TRUE V2
  B_AUTH_ONCE ELF SHA (refuses other B/unchecked);
- SHA-locked B4.5 once independent real 1024 parity receipt,
  original 64-shard B software scalar oracle and final
  B4.5.5 actual four-report synthesis JSON;
- actual original A P08-A3.2 stage, original canonical
  IDX TRAIN gzip source, 33-file frozen B2.4 checkpoint,
  original 1024 A stage frames and 1024 B frozen scalar frames,
  **each** original source index + pixel SHA + selected trace;
- **six** pre-registered pair/order entries with no physics
  permission or accepted same-boundary/repeated-run claim.

### Run on your PC / VS Code only

~~~bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p08-b46-auth-once-comparator-gate
git pull --ff-only origin agent/v3-p08-b46-auth-once-comparator-gate
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/scripts:$PWD/src" python3 -m pytest -q -rs \
 tests/test_p08_b46_auth_once_source_gate.py \
 tests/test_p08_b45_full1024_latency_synthesis.py \
 tests/test_p08_b45_perf_full1024_independent_cli.py
~~~

Locate ORIGINAL accepted Track A2.1 ELF; there may be more
than one historical build directory. **Do not substitute A2.2.**

~~~bash
find "$HOME/Thesis_Evidence" -type f \
 -name 'p08_a2_board.elf' -print
~~~

Choose one exact prior accepted ORIGINAL Track A2.1 ELF
and export it. Its hash must match
\`fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0\`.

~~~bash
# EDIT only this local path to the exact existing A2.1 ELF found:
export B46_A_ELF="/home/dna/Thesis_Evidence/<EXACT_A21_BUILD>/vitis_workspace/p08_a2_board.elf"
export B46_B_ONCE_ELF="$HOME/Thesis_Evidence/p08_b45_perf_once_full1024_V2_20261105T192804Z/vitis_workspace/p08_b45_perf_once_full1024.elf"
export B46_A_STAGE="$HOME/Thesis_Evidence/p08_a3_2_stage1024_20261019T003150Z"
export B46_B_ORACLE="$HOME/Thesis_Evidence/p08_b4_1_full1024_scalar_20261102T143900Z.json"
export B46_B_ONCE_REPORT="$HOME/Thesis_Evidence/p08_b45_perf_once_full1024_V2_verified_20261106T005213Z.json"
export B46_B45_SYNTHESIS="$HOME/Thesis_Evidence/p08_b45_full1024_synthesis_20261106T011541Z.json"

sha256sum "$B46_A_ELF" "$B46_B_ONCE_ELF" \
 "$B46_B_ORACLE" "$B46_B_ONCE_REPORT" "$B46_B45_SYNTHESIS"
~~~

Do not proceed if the original A2.1 ELF cannot be found.
The gate verifies all hashes and REAL canonical source
assets; it does not need raw new JTAG capture folders.

~~~bash
export B46_SOURCE_REPORT="$HOME/Thesis_Evidence/p08_b46_A_vs_B_AUTH_ONCE_source_gate_$(date -u +%Y%m%dT%H%M%SZ).json"

PYTHONPATH="$PWD/scripts:$PWD/src" python3 \
 scripts/p08_b46_auth_once_source_gate.py \
 --a-elf "$B46_A_ELF" \
 --b-once-elf "$B46_B_ONCE_ELF" \
 --a-stage "$B46_A_STAGE" \
 --train-data-dir "$PWD/data/mnist_raw" \
 --frozen-b "$PWD/artifacts/p06_b24_frozen_1000" \
 --b-oracle "$B46_B_ORACLE" \
 --b-once-report "$B46_B_ONCE_REPORT" \
 --b45-synthesis "$B46_B45_SYNTHESIS" \
 --out "$B46_SOURCE_REPORT"

sha256sum "$B46_SOURCE_REPORT"
python3 -m json.tool "$B46_SOURCE_REPORT"
~~~

Expected exact offline markers:

~~~text
P08_B46_ORIGINAL_A_VS_AUTH_ONCE_FROZEN_1024_TRAIN_POPULATION_PASS=1
P08_B46_NEW_SIX_SESSION_STUDY_JTAG_AUTHORIZED=0
P08_B46_SOURCE_GATE_PC_ONLY_PASS=1
~~~

The resulting report explicitly identifies each of six coldboots,
and says original Track A/B timer boundary equivalence and
physical runner repeated readiness are **NOT yet proven**.

## Next code submilestone

P08-B4.6.3: build/test the separate six-session original
Track A vs optimized Track B_AUTH_ONCE numerical/recovery
and matched-timing admissions. Review A's historical
64MiB DDR overwrite JTAG runner vs B's 27x512KiB
backup/current P03 setup, ensure same A53 entry-to-journal
commit definition and source/ELF pins; produce native
negative/regression tests and independent signed per-session
timing receipts. Obtain explicit hardware permission for
each session individually. **Do not launch any** based only
on this PC-only source-gate PASS.

P08-B4.6.4: after all independently authorized physical
runs, compare 3 per-pair session medians and report
geometric mean ratio, spread/order dependency and
confidence limitations. N=3 physical pairs, NOT N=1023
independent hardware replicates. Do not assert formal
statistical significance with only 3 pairs.

The original official MNIST TEST remains SEALED.
No main/feature branch merge without explicit user approval.
