# B4.6 reconstructed A2.1: first genuine 1024 KV260 physical revalidation

**STATUS: SOURCE-CODE READY / PC CI PASS; NO NEW PHYSICAL RESULT REPORTED.**
This is ONE original-source rebuilt A2.1 (new SHA) real
1024 TRAIN-derived physical neural/time session, NOT six independent
A-vs-B_AUTH_ONCE AB/BA/AB study sessions. The historical Track A2.1
physical runner and original 2026-10-18 acceptance remain untouched.

New distinct files: scripts/run_p08_b46_rebuilt_a21_1024.sh and
scripts/p08_b46_a21_rebuilt_independent_physical_verify.py.

Pinned rebuilt A2.1 ELF:
fa926823c291b70267c099db00c5052e62405444db58863436c1b2f950a58793
(original historical A2.1 pin:
fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0).
Pinned original P03 XSA:
52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f.
Actual user-accepted new B4.6 original 1024 TRAIN source gate
/home/dna/Thesis_Evidence/p08_b46_Arebuild_vs_Bauthonce_source_20261106T025815Z.json
SHA: ec853c596a9dcfefee57d4da727a31dc55e3852407c589869c7b8838fb0ccd56.
Source gate originally reported new rebuilt A physical ACCEPTANCE=0
and JTAG_AUTHORIZED=0; this source does not implicitly authorize
physical actions. Rebuilt-A2.1 standalone PC admission JSON path
must be discovered from operator's original report (not guessed).

## 1. PC pull and source-only native tests

~~~bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p08-b46-a21-candidate-physical-validation
git pull --ff-only origin agent/v3-p08-b46-a21-candidate-physical-validation
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/scripts:$PWD/src" python3 -m pytest -q -rs \
 tests/test_p08_b46_new_a21_physical_safety.py \
 tests/test_p08_b46_auth_once_source_gate.py \
 tests/test_p08_b45_full1024_latency_synthesis.py \
 tests/test_p08_b45_perf_full1024_independent_cli.py
bash -n scripts/run_p08_b46_rebuilt_a21_1024.sh
~~~

## 2. Original sources, distinct accepted reports, new evidence path

~~~bash
export P08_B46_REBUILT_A21_BUILD="$HOME/Thesis_Evidence/p08_a2_1_rebuild_20261106T023403Z"
export P08_B46_A_STAGE_DIR="$HOME/Thesis_Evidence/p08_a3_2_stage1024_20261019T003150Z"
export P03_DIAG_REPORTS="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports"
export P08_B46_SIGNED_SOURCE_REPORT="$HOME/Thesis_Evidence/p08_b46_Arebuild_vs_Bauthonce_source_20261106T025815Z.json"

# If same PC shell as prior B4.6 source tests, reuse the real admission.
if test -n "$B46_A_REBUILT_ADMISSION"; then
  export P08_B46_SIGNED_A_ADMISSION="$B46_A_REBUILT_ADMISSION"
else
  find "$HOME/Thesis_Evidence" -maxdepth 1 -type f \
    -name 'p08_b46_a21_rebuilt_source_admission_*.json' -print
  # Then export P08_B46_SIGNED_A_ADMISSION to the EXACT genuine file.
fi
test -s "$P08_B46_SIGNED_A_ADMISSION" || {
  echo "STOP: genuine rebuilt A2.1 PC admission report missing"; false;
}
sha256sum "$P08_B46_REBUILT_A21_BUILD/vitis_workspace/p08_a2_board.elf" \
 "$P03_DIAG_REPORTS/p03_2_ps_mmio.xsa" \
 "$P08_B46_SIGNED_SOURCE_REPORT" "$P08_B46_SIGNED_A_ADMISSION"

export P08_B46_REBUILT_A21_RUN_DIR="$HOME/Thesis_Evidence/p08_b46_A21_rebuilt_real1024_$(date -u +%Y%m%dT%H%M%SZ)"
export P08_B46_PREFLIGHT_ONLY=YES
bash scripts/run_p08_b46_rebuilt_a21_1024.sh
~~~

Offline acceptance includes
P08_B46_SIGNED_REBUILT_A21_ELF_AND_ORIGINAL_1024_SOURCE_PREFLIGHT_PASS=1
P08_B46_REBUILT_A21_ORIGINAL_1024_OFFLINE_PREFLIGHT_PASS=1
P08_B46_PREFLIGHT_AUTHORIZES_PHYSICAL_JTAG=0
P08_B46_REBUILT_A21_KV260_PHYSICAL_STATUS=NOT_RUN.
No directory or board changes during offline preflight.

## 3. Board and JTAG safety / operator preparation

DANGER: destructive 64MiB DDR overwrite
[0x40000000,0x44000000), bare-metal A53 halt/takeover
and original P03.2c PS-MMIO bitstream programming. Linux,
DMA or other masters MAY still own DDR. The original
FPD HPM0 128-bit static diagnostic does NOT prove
other owners stopped or DDR exclusion. The chosen
unprotected B_AUTH_ONCE architecture does NOT justify
skipping A-specific risk checks.

Must have a fresh, disposable JTAG-only KV260 session;
close all competing Vivado/XSDB clients; use ONE
hw_server; no active Linux/PL app or streaming DMA.
PuTTY Linux: sudo xmutil listapps; sudo xmutil unloadapp
ONLY if a specific app is shown loaded. Unloading alone
does not prove DDR ownership. Stop if unproven ownership
risk is unacceptable. No proceeding on a production
Linux session. KV260 mandatory PHYSICAL power-cycle
after EVERY JTAG attempt, PASS or FAIL; never resume
halted Linux. Preserve failed-run original evidence and
use a NEW run directory if retry necessary.

Load your genuinely installed Vitis/Vivado 2025.2 env:

~~~bash
source "$HOME/Vivado/2025.2/Vitis/settings64.sh"
command -v xsdb
command -v vivado
command -v hw_server
pgrep -af 'hw_server|xsdb|vivado' || true
~~~

If and only if there is NOT already a JTAG hw_server,
run in another PC terminal:

~~~bash
source "$HOME/Vivado/2025.2/Vitis/settings64.sh"
hw_server -s tcp::3121
~~~

Keep that terminal dedicated; do not create a second server.

## 4. ONE actual A2.1 new SHA destructive validation

Only after reviewing and personally accepting the risks:

~~~bash
unset P08_B46_PREFLIGHT_ONLY
export P08_B46_CONFIRM_DISPOSABLE_LINUX_JTAG_ONLY=YES
export P08_B46_CONFIRM_OVERWRITE_ORIGINAL_64M_DDR=YES
export P08_B46_CONFIRM_ORIGINAL_TRAIN_ONLY=YES
export P08_B46_CONFIRM_UNPROVEN_BOOT_DDR_DMA_RISK=YES
export P08_B46_CONFIRM_PWR_CYCLE_AFTER_ANY_ATTEMPT=YES
export P08_B46_CONFIRM_NEW_CANDIDATE_ELF=YES

set -o pipefail
bash scripts/run_p08_b46_rebuilt_a21_1024.sh
~~~

Actual runner fail-closes on source/pin mismatches BEFORE
first board access. Once hardware access begins, it performs
128bit FPD width diagnostic, original P07 DDR physical
staging+readbacks at original 6 source addresses, accepted
P03 bitstream, exact NEW A2.1 A53 ELF download,
1024 journal/trace/timing capture, independent ORIGINAL
P07 packed software oracle on all 1024 images + original
selected 26x42 trace, CRC and actual A53 time checks,
new report and new physical raw hashes.

Successful final physical marker:
P08_B46_NEW_REBUILT_A21_ORIGINAL_1024_PHYSICAL_AND_INDEPENDENT_PASS=1
alongside separate independent marker:
P08_B46_REBUILT_A21_INDEPENDENT_ORIGINAL_ALL1024_PACKED_NEURAL_AND_TIMING_PASS=1
and explicit B4.6 six-run study=NOT_RUN.

**POWER-CYCLE THE KV260 AFTER ANY ATTEMPT**, even success.
Stop at any missing PASS; do not launch B_AUTH_ONCE
or any six-session follow-up automatically.

## 5. PC-only independent rereview after reboot

~~~bash
cat "$P08_B46_REBUILT_A21_RUN_DIR/attempt_exit_status.txt"
cat "$P08_B46_REBUILT_A21_RUN_DIR/verify.log"
sha256sum \
 "$P08_B46_REBUILT_A21_RUN_DIR/p08_b46_rebuilt_A21_1024_independent.json" \
 "$P08_B46_REBUILT_A21_RUN_DIR/physical_output_sha256.txt"

export P08_B46_A_RECHECK_JSON="$HOME/Thesis_Evidence/p08_b46_rebuilt_A21_rereview_$(date -u +%Y%m%dT%H%M%SZ).json"
PYTHONPATH="$PWD/scripts:$PWD/src" python3 \
 scripts/p08_b46_a21_rebuilt_independent_physical_verify.py \
 --build "$P08_B46_REBUILT_A21_BUILD" \
 --xsa "$P03_DIAG_REPORTS/p03_2_ps_mmio.xsa" \
 --source-report "$P08_B46_SIGNED_SOURCE_REPORT" \
 --candidate-report "$P08_B46_SIGNED_A_ADMISSION" \
 --stage "$P08_B46_A_STAGE_DIR" \
 --evidence "$P08_B46_REBUILT_A21_RUN_DIR" \
 --out "$P08_B46_A_RECHECK_JSON"
sha256sum "$P08_B46_A_RECHECK_JSON"
~~~

Expected independent marker:
P08_B46_REBUILT_A21_INDEPENDENT_ORIGINAL_ALL1024_PACKED_NEURAL_AND_TIMING_PASS=1.

## 6. Subsequent B4.6 A vs B_AUTH_ONCE six independent sessions

STOP HERE after the single candidate run. The original
B4.6 source-gate manuscript still marks A/B timer
boundary equivalence, both physical runner six-session
reuse, other DDR masters, and the three paired
A B / B A / A B coldboot study **UNPROVEN**.
The previous original B4.5 B_AUTH_ONCE full1024 PASS
is not a new independent B4.6 session. Historical
Track A original fc44... physical observations remain
historical—not new repeated A/B data.

Once the new A21 1024 real independent report+SHA
passes, examine both actual source A53 service start/stop
boundaries and all physical recovery/provenance requirements,
then add a *separate* six-run study runner with individual
hardware approvals, signed receipt/reboot after each,
and an independent analysis across 3 session-level pairs.
Never count the 1023 images of one session as 1023
independent hardware trials. Preserve official MNIST
TEST seal, original accepted pins, and all source hashes.
