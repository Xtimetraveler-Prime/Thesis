# P08-A3.1 — Initial physical KV260 latency pilot (16 TRAIN validation images)

**Status (2026-10-18): A3.1 SOURCE + PHYSICAL PROTOCOL IMPLEMENTED; USER REPORTS NATIVE REGRESSIONS PASSED AND A2.2 VITIS BUILD PASS. OFFLINE PREFLIGHT / KV260 PILOT NOT YET RUN.**  
**Scope:** user-approved latency characterization only; **power/energy deferred**. This is the first engineering hardware pilot, **not** the full 1,024-image repeated latency baseline and not a new official MNIST TEST accuracy study.

## 1. Prior accepted evidence and candidate build state

- Exact accepted P03.2c routed XSA SHA256 `52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`; underlying physical engine, P07 neural application ABI, original snapshot/weight checkpoint, and P07 TEST evidence remain **frozen**.
- Accepted immutable P02 512KiB master SHA256 `9617a822f74faa8723869bb576cf57b38af1a1a91ac81c47c246a9425d0dd955`.
- A2.1 user-provided **build-only PASS** on 2026-10-18, ELF SHA256 `fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0`; board not run.
- A2.2 test initially flagged a **comment-only false positive**, later fixed; user reports **all regressions passed** and Vitis **build PASS**. A2.2 user-supplied build: `/tmp/v3_p08_a2_2_build_20261018T200133Z/vitis_workspace/p08_a2_2_board.elf`. User's separately printed `build_identity.txt` and `sha256sum` agree on exact A2.2 ELF SHA256 **`87cf5fc4fe37d9d053a3c365db8ae9fdc7e782857612f273835cf5e611aba361`**. The build reports the original accepted P03.2c routed XSA SHA256 and `P08_A2_2_KV260_LATENCY=NOT_RUN`. This is **user-attested build evidence**, not independent board timing evidence. It is **hard pinned** in the A3.1 physical runner and separately compared with explicit operator-provided SHA256.
- **New A3.1** `scripts/run_p08_a3_1_pilot.sh`: distinct from accepted P07 runner and from the two A2 runners; no source changes to accepted `software/p07/`, `software/p03/` or bitstream.

## 2. Research question, sample population and boundaries

First physically prove that the **instrumented A2.2 bare-metal A53** runs real P03.2c PL inference for an original-order fixed prefix of **16 distinct held-out TRAIN-derived validation images**, produces numerically exact results and exports complete, coherent timing sidecars. Collect:

1. Original P07 `P07A4R01` journal (1MiB) with 26×10 spikes per image, class/count/route/ingress and CRCs.
2. Selected full neural trace (64KiB), 26×42 compartments with original packed-state/accumulator/spike witness.
3. P08-A2.1 `P08ALAT1` (1MiB), frame `service_start` / `after_ingress` / `after_neural` / `after_commit` A53 timestamps; original per-image P03 A53 route/barrier/control/inference ticks and independent PL dispatch/page cycles.
4. P08-A2.2 `P08TCK02` (3MiB), seven ordered A53 raw `CNTVCT_EL0` boundaries per one of 26 logical timesteps and per-tick PL dispatch cycle counts.

For **scope**, study [P08_A2_2_TIMING_METHODS.md](P08_A2_2_TIMING_METHODS.md). The A53 timing arithmetic uses the firmware-reported `CNTFRQ_EL0` frequency: `seconds = (end-start)/CNTFRQ`. This is **not** a calibrated PL/HLS clock, and A2.2 instrumentation adds overhead. Actual raw numbers are not available before KV260 execution. The selected trace frame (default first image in the 16-frame staged batch) is a different, heavier debug-readout path and must be reported separately. Do not treat identical repeated synthetic images as independent validation examples.

**Official TEST state:** The frozen official 10,000-image TEST was already run and closed under P07-A4.4; it is **not sealed as a historical research outcome**. The legacy `official_mnist_test=SEALED` field on the A4.2a TRAIN-validation staging manifest is a conservative **workload exclusion marker**: this new P08 pilot does not load or rerun the TEST partition. Do not change that frozen manifest field or infer it reverses the already accepted P07 full-test result.

## 3. Measurement validation — fail-closed, never infer accuracy from timer output

The new `scripts/p08_a3_1_verify.py` performs these checks *in order*:

1. `p07_a4_2_verify.py` **must actually PASS** its independent project-trained integer/packed P03 oracle for **all 16 physical image records**, original raw pixels, 26×10 output spikes, class counts, exact ingress and committed NEXT routing, final dropped packets, and selected 26×42 full physical neural trace. If this fails, **reject all latency claims**.
2. Parse the original P07 journal again against the staged original dataset; independently parse both 1MiB and 3MiB latency sidecars using strict CRC, schemas and terminal states. The tick parser additionally enforces the actual input descriptor CRC, clock/sample/selected-trace identity, 26 records in frame/tick order, chronological monotonicity, correct reserved zeros, and `sum(26 PL cycles)=original per-image PL counter`.
3. For each of 16 frames, recompute the **exact frozen 26-tick uint8-to-event schedule** for that raw image. Compare every real FPGA-side A53 external event count to this schedule, ensure each emitted packet was acknowledged, match `sum(NEXT acknowledgments at ticks 0..24)` with the original P07 physically committed route count and match tick25 final emitted packets with the original journal's dropped boundary count. The tick25 count of acknowledged packets **does not imply a NEXT-bank write**.
4. Generate a **new no-overwrite** JSON report with original-source and all raw-output SHA256 hashes, actual A53 counter frequency, image-service **raw tick array**, converted per-image service seconds, 16-image median/range, selected trace versus ordinary-frame median, per-stage median A53 service seconds, PL raw cycle sums, successful oracle status and exact limits of the pilot. These are a feasibility pilot, not a generalizable performance estimate. The first 16-image pilot itself is **not enough** for a statistical latency distribution across independently repeated runs.
5. Print `P08_A3_1_16FRAME_PHYSICAL_PILOT_PASS=1` only if **all** gates pass. Return a nonzero code on mismatch; no fallback to simulation metrics or invented hardware results.

A native mock unit test may invoke the consistency helper with `oracle_proof=False`, but its returned `physical_latency_accepted` flag must be **false**. Only the physical CLI workflow with genuine independent P07 oracle may produce an accepted pilot.

## 4. Safety, ownership and evidence retention

The physical pilot **programs** the accepted P03.2c FPGA bitstream, resets/halt the ARM Cortex-A53 and **overwrites the reserved 64MiB physical DDR window `0x40000000..0x43FFFFFF`**. It is **not safe** while Linux is booted and owns DDR. Explicitly reboot the KV260 to a dedicated JTAG-only bare-metal state before and afterward. This first-step 16 validation pilot is **not** a firmware upgrade for daily Linux use.

Required environment variables before launching the guarded physical script:

| Variable | Meaning |
| --- | --- |
| `P03_DIAG_REPORTS` | **Existing real path** to accepted P03.2c routed XSA, bit, LTX, and route metrics; **do not guess** |
| `P08_A2_2_BUILD_DIR` | User-built A2.2 candidate Vitis output directory, with ELF and `build_identity.txt` |
| `P08_A3_1_EXPECTED_ELF_SHA256` | Exact **observed and pinned** A2.2 ELF SHA256 `87cf5fc4fe37d9d053a3c365db8ae9fdc7e782857612f273835cf5e611aba361` (not the A2.1 SHA) |
| `P08_A3_1_STAGE_DIR` | Existing absolute path to original first16 TRAIN-derived validation stage, with original byte-hashed descriptor/map/pixels/initial journal/label ledger |
| `P08_A3_1_RUN_DIR` | A fresh ABSOLUTE output folder **outside Git**; must not already exist (nor be a symlink), saved until copied to durable storage |
| `P08_A3_1_CONFIRM_JTAG_ONLY` | Must be `YES` only after bare-metal reboot and verifying nobody else owns DDR |
| `P08_A3_1_CONFIRM_DDR_OVERWRITE` | Must be `YES` only when user accepts the 64MiB destructive overwrite |
| `P08_A3_1_CONFIRM_TRAIN_VALIDATION_ONLY` | Must be `YES` after confirming staged scope is first16 TRAIN validation only |

The script supports `P08_A3_1_PREFLIGHT_ONLY=YES` for **offline preflight**: all SHA256/ELF/source/validation/canonical TRAIN checks run while *no XSDB or Vivado command is executed*, no physical DDR is touched and no JTAG consent is requested; it exits with `P08_A3_1_OFFLINE_PREFLIGHT_PASS=1` and `P08_A3_1_KV260_LATENCY=NOT_RUN`. Clear this environment override before the real physical run. The script first authenticates pinned XSA and frozen master SHA256, exact A2.2 ELF marker/observed hash/build identity, staged sources and original P03/P07 source byte equality, design bus configuration, stage manifest, 16 original image ledger, zeroed journal, and ELF LOAD section isolation. **Before JTAG**, it additionally reloads the actual accepted MNIST TRAIN 50k/10k split and frozen P06 checkpoint to prove the staged first16 bytes and labels really belong to the selected TRAIN-derived validation prefix; a self-consistent but forged ledger is insufficient. Raw output inside the Git worktree is rejected. Any mismatch exits **before hardware is accessed**. The source is separately pinned by the user's build identity; updating the feature branch after a build may require a new build. The physical runner calls the **same accepted** P07 XSDB width check, six-region staging and **readback**, and P03.2c Vivado programming scripts before the single autonomous A53 launch.

It uses `vivado/p08_a2_2_xsdb_run.tcl` to wait for **three** independent terminal statuses: original neural journal, image timings and tick timings, before reading 1MiB + 64KiB + 1MiB + 3MiB raw memory. If timeout, fault or neural mismatch: **do not accept latency**. All partial evidence, logs, sha256 identity, output attempts and terminal-state data should be preserved. Never overwrite a previous run directory. After successful completion, the script records `physical_output_sha256.txt`, comprehensive JSON report, and prints `P08_A3_1_FULL_PHYSICAL_GATE_PASS=1`. The script attempts to write exit status and available-output SHA256 even on nonzero exit.

## 5. Reproduction and checkpoint — first preflight, then physical pilot

The next user interaction should **first** verify the native guard and selected original regression suites, with no board access:

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p08-a-physical-baseline
git pull --ff-only origin agent/v3-p08-a-physical-baseline

source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
PYTHONPATH="$PWD/src" python -m pytest -q \
  tests/test_p08_a3_1_pilot.py tests/test_p08_a2_2_ticks.py \
  tests/test_p08_a2_timing.py \
  tests/test_p07_a4_official.py tests/test_p07_a4_fault.py

bash -n scripts/run_p08_a3_1_pilot.sh
python -m py_compile scripts/p08_a3_1_verify.py
```

**Do not proceed to board until all tests PASS and actual A2.2 ELF SHA is recorded.** If native checks fail, preserve terminal output and fix in a new commit without touching earlier raw evidence.

If the frozen first16 TRAIN-validation stage is not already stored, generate it **offline**, from canonical TRAIN only, to a fresh untracked directory:

```bash
# Choose a durable, untracked location of your own.
export P08_A3_1_STAGE_DIR="$HOME/Thesis_Evidence/p08_a3_1_stage16_$(date -u +%Y%m%dT%H%M%SZ)"
PYTHONPATH="$PWD/src" python scripts/p07_a4_2_prepare.py \
  --validation-first 16 --trace-index 0 --out "$P08_A3_1_STAGE_DIR"
PYTHONPATH="$PWD/src" python scripts/p07_a4_2_check.py --stage-dir "$P08_A3_1_STAGE_DIR"
```

Pinned user-verified candidate and reproducible host preflight (in VS Code terminal; `P03_DIAG_REPORTS` still points to the **real accepted** artifact directory, never a guessed location):

```bash
export P08_A2_2_BUILD_DIR=/tmp/v3_p08_a2_2_build_20261018T200133Z
export P08_A3_1_EXPECTED_ELF_SHA256=87cf5fc4fe37d9d053a3c365db8ae9fdc7e782857612f273835cf5e611aba361
export P08_A3_1_RUN_DIR="$HOME/Thesis_Evidence/p08_a3_1_pilot_$(date -u +%Y%m%dT%H%M%SZ)"
cat "$P08_A2_2_BUILD_DIR/build_identity.txt"
sha256sum "$P08_A2_2_BUILD_DIR/vitis_workspace/p08_a2_2_board.elf"
P08_A3_1_PREFLIGHT_ONLY=YES bash scripts/run_p08_a3_1_pilot.sh
```

Expected **offline** markers: `P07_A4_2A_STAGING_CHECK_PASS=1`, `P08_A3_1_ORIGINAL_TRAIN_FIRST16_PHYSICAL_PREFLIGHT_PASS=1`, `P08_A3_1_ELF_DDR_ISOLATION_PASS=1`, `P08_A3_1_OFFLINE_PREFLIGHT_PASS=1` and `P08_A3_1_KV260_LATENCY=NOT_RUN`. No physical output directory will be created yet. **Do not proceed if this fails.**

After **explicit user authorization and reboot to dedicated JTAG-only bare-metal**, supply the environmental gates and a **new** run directory, then:

```bash
# Use exactly the same new P08_A3_1_RUN_DIR that passed offline preflight.
# Must be a JTAG-only bare-metal reboot; NO booted KV260 Linux DDR owner.
unset P08_A3_1_PREFLIGHT_ONLY
export P08_A3_1_CONFIRM_JTAG_ONLY=YES
export P08_A3_1_CONFIRM_DDR_OVERWRITE=YES
export P08_A3_1_CONFIRM_TRAIN_VALIDATION_ONLY=YES
bash scripts/run_p08_a3_1_pilot.sh
```

The script takes no hardware action before the explicit consents and all provenance preflight. **No P08-A3.1 physical execution is reported yet.** Retain the complete evidence directory; reboot after any attempt. The user should paste full terminal pass/fail markers and the A2.2 build identity, not discard failures.

## 6. Sources and scope of methodological derivation

Our **primary implementation-level sources** are the already accepted project files, which define exact tested semantics and endpoints:
- `docs/P03_PS_AUTONOMOUS_APPLICATION.md`: A53 scheduler ownership, timer scope, clock domains, result ABI and full-DDR memory/packet ownership.
- `software/p03/p03_runtime.c`, `software/p03/p03_hw_adapter.c`, `software/p07/p07_a2_runtime.c`: actual completed PS/PL dispatch, per-tick encoder, packet routes and barrier endpoints.
- `software/p07/p07_a4_board.c`, `software/p07/p07_a4_stream.c` and `scripts/p07_a4_2_verify.py`: original journal, staged validation and independent packed oracle, selected trace.
- `vivado/p07_a4_xsdb_prepare.tcl`, `scripts/run_p07_a4_physical.sh`: historical accepted byte-exact real KV260 staging/provisioning, physical board safety and evidence handling.
- `software/p08/p08_a2_2_runtime.c`, `src/loihi_twin_v2/p08_a2_2_ticks.py`: actual new instrumented boundaries and consistency checks.
- [P08-A2.2 Timing Methods](P08_A2_2_TIMING_METHODS.md): Arm Generic Timer/CNTFRQ documentation references, AMD Vitis HLS UG1399 clock-target-vs-counter caveats. **No additional external metrology method was invented for A3.1.**

A3.1 closes only the **correctness and readback feasibility of a 16-image instrumented real-board pilot** once physically run. Next A3.2, subject to user acceptance, would compare the same first 1,024 images in separate A2.1/A2.2 cold-boot runs and quantify profiler perturbation and run-to-run uncertainty. **No power characterization will be resumed without explicit permission.**
