# P08-B4.5 unprotected original full1024 A53 physical experiments with second-terminal progress

**Active branch:** agent/v3-p08-b45-unprotected-full1024-progress
**Hardware status:** genuine new full1024 Vitis ELFs and local preflights are
PENDING. Native/GitHub CI is HOST ONLY and must never be treated as a real
Vitis build, JTAG ownership admission or inference result.

**Scientific contract:** new separate once and unchecked full1024 A53
applications, original 27 P02 contexts and exactly 1024 frozen TRAIN-
derived 784-pixel frames, 26 simulation ticks, 702 hardware dispatches
per image and original 1010-neuron trace FNV/reference. One-time SHA
bind vs unchecked content reset as with accepted pilot16; entire source
raw-1024 image pool is always hashed. Full 1024x256B journal, service
timer, and reset-only profile sidecar. All 27 backing context chunks
(27x512KiB) are read back after inference and compared byte-identical
against frozen originals. Backup hardware immutability, early boot
owner exclusion and secure XMPU are NOT proven nor claimed. TEST remains
SEALED_NOT_ACCESSED. The final special image ordinal 1023 is excluded
from ordinary 1023-image descriptive latency, consistent with the
accepted original B4.4 baseline.

**Historical source:** Both actual 16-image pilots independently PASS,
accepted SHA pinned in
docs/P08_B45_OPERATOR_REPORTED_REAL_UNPROTECTED_PILOT16_ACCEPTANCE_2026_11_05.md.
Full1024 physical admission re-opens those local JSON files and rejects
tampering. Before physical execution, the entire original full1024
software oracle is reconstituted from the original 64 immutable
TRAIN-derived scalar shards. The original B4.2 genuine 1024
JTAG physical and B4.4.1/2 1023 ordinary-time baseline JSON SHA pins
must match. Do not recreate or regenerate accepted model assets.

## A. VS Code TERMINAL 1: fetch new branch and PC no-board tests

~~~bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p08-b45-unprotected-full1024-progress
git pull --ff-only origin agent/v3-p08-b45-unprotected-full1024-progress
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
PYTHONPATH="$PWD/scripts:$PWD/src" python3 -m pytest -q -rs \
 tests/test_p08_b45_perf_full1024.py \
 tests/test_p08_b45_perf_pilot16.py \
 tests/test_p08_b45_perf_pilot16_independent.py \
 tests/test_p08_b45_reset_variants.py \
 tests/test_p08_b4_2_full1024_physical.py \
 tests/test_p08_b44_profile_physical.py
~~~

## B. VS Code TERMINAL 1: authentic original evidence paths

Use these exact historical absolute paths, already documented in B3,
B4.2, B4.4, B4.5 runs. If relocated, find exact files and compare
original SHA. A forged/missing file is STOP, not a reason to bypass.

~~~bash
export P08_B45_ORIGINAL_ELF="$HOME/Thesis_Evidence/p08_b2_3_image_only_build_20261102T040903Z/vitis_workspace/p08_b2_3_image_only_1024.elf"
export P08_B2_RESET_PINS="$HOME/Thesis_Evidence/p08_b2_2_original_reset_pins_20261102T005118Z"
export P07_B4L_REPORTS="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports"
export P08_B3_PILOT_STAGE="$HOME/Thesis_Evidence/p08_b3_pilot16_pc_stage_20261102T043729Z"
export P08_B4_FIRST16="$HOME/Thesis_Evidence/p08_b2_4_original_first16_scalar_20261102T042201Z.json"
export P08_B3_INDEPENDENT_REPORT="$HOME/Thesis_Evidence/p08_b3_pilot16_independent_20261102T055256Z.json"
export P08_B4_SHARDS="$HOME/Thesis_Evidence/p08_b4_1_original_scalar_shards_20261102T060939Z"
export P08_B4_INGRESS="$HOME/Thesis_Evidence/p08_b2_1_original1024_20261102T003256Z"
export P08_B4_FULL_ORACLE="$HOME/Thesis_Evidence/p08_b4_1_full1024_scalar_20261102T143900Z.json"
export P08_B4_ORIGINAL_INDEPENDENT="$HOME/Thesis_Evidence/p08_b4_2_independent1024_20261102T184928Z.json"
export P08_B44_ORIGINAL_TIMING="$HOME/Thesis_Evidence/p08_b4_4_first1024_one_session_descriptive_20261102T191317Z.json"
export P08_B45_PILOT_ONCE_INDEPENDENT="$HOME/Thesis_Evidence/p08_b45_perf_once_independent_20261105T154923Z.json"
export P08_B45_PILOT_UNCHECKED_INDEPENDENT="$HOME/Thesis_Evidence/p08_b45_perf_unchecked_independent_20261105T160411Z.json"

for src in "$P08_B45_ORIGINAL_ELF" \
 "$P07_B4L_REPORTS/p03_2_ps_mmio.xsa" \
 "$P08_B2_RESET_PINS/p08_b2_2_original_context_sha256.h" \
 "$P08_B3_PILOT_STAGE/original_27core_backup_source_14155776.bin" \
 "$P08_B4_FIRST16" "$P08_B3_INDEPENDENT_REPORT" \
 "$P08_B4_FULL_ORACLE" "$P08_B4_ORIGINAL_INDEPENDENT" \
 "$P08_B44_ORIGINAL_TIMING" \
 "$P08_B45_PILOT_ONCE_INDEPENDENT" \
 "$P08_B45_PILOT_UNCHECKED_INDEPENDENT"; do
 test -s "$src" || { echo "STOP: missing $src"; break; }
done
test -d "$P08_B4_SHARDS" && test -d "$P08_B4_INGRESS" || echo "STOP: original shard or ingress directory missing"

sha256sum \
 "$P08_B45_PILOT_ONCE_INDEPENDENT" \
 "$P08_B45_PILOT_UNCHECKED_INDEPENDENT" \
 "$P08_B4_FULL_ORACLE" \
 "$P08_B4_ORIGINAL_INDEPENDENT" \
 "$P08_B44_ORIGINAL_TIMING"
~~~

Expected digests in that order:
~~~text
7ab975d3c062df2606357080c1eeda0904ea8aaba0aed4c02fda8ce1140ecdca
5f29cda8661cad64fe39231d42a84c3293bef96af6c7fe74c9c74b466a2195aa
7e564d188651aeabdc284328ea65705bcb0b5571468b9f70d5dcacaa3f5493b8
297114489eb8312733a2e2597f0ee0567f9868552d2bc71d0dd425139368b032
4e0abf43dafab145b2dde6846d5504470c3d122da80923c34441e82877881b81
~~~

## C. VS Code TERMINAL 1: genuine Vitis 2025.2 build BOTH new full ELFs

This is strictly PC-side; nothing touches KV260. Set the actual
installed settings64.sh if the historical path was moved.

~~~bash
source "$HOME/Vivado/2025.2/Vitis/settings64.sh"
command -v vitis
command -v aarch64-none-elf-readelf
command -v aarch64-none-elf-nm

export P08_B45_MODE=once
export P08_B45_BUILD_DIR="$HOME/Thesis_Evidence/p08_b45_perf_once_full1024_build_$(date -u +%Y%m%dT%H%M%SZ)"
bash scripts/build_p08_b45_perf_full1024.sh
export P08_B45_FULL_ONCE_BUILD="$P08_B45_BUILD_DIR"

export P08_B45_MODE=unchecked
export P08_B45_BUILD_DIR="$HOME/Thesis_Evidence/p08_b45_perf_unchecked_full1024_build_$(date -u +%Y%m%dT%H%M%SZ)"
bash scripts/build_p08_b45_perf_full1024.sh
export P08_B45_FULL_UNCHECKED_BUILD="$P08_B45_BUILD_DIR"
~~~

Both fresh genuine mode-specific ELF/maps and separate source
admission JSON must PASS. Do not reuse existing 16-image ELF
and do not alter any original guard or source checksum gate.

## D. VS Code TERMINAL 1: required original + both pilot + 1024 offline preflights

~~~bash
P08_B45_FULL_COMMON=(
 --stage "$P08_B3_PILOT_STAGE"
 --first16 "$P08_B4_FIRST16"
 --b3-report "$P08_B3_INDEPENDENT_REPORT"
 --shards "$P08_B4_SHARDS"
 --ingress "$P08_B4_INGRESS"
 --oracle "$P08_B4_FULL_ORACLE"
 --b4-independent-report "$P08_B4_ORIGINAL_INDEPENDENT"
 --b44-timing-report "$P08_B44_ORIGINAL_TIMING"
 --pilot-once-report "$P08_B45_PILOT_ONCE_INDEPENDENT"
 --pilot-unchecked-report "$P08_B45_PILOT_UNCHECKED_INDEPENDENT"
 --original-elf "$P08_B45_ORIGINAL_ELF"
 --reset-pins "$P08_B2_RESET_PINS"
 --reports "$P07_B4L_REPORTS"
)

PYTHONPATH="$PWD/scripts:$PWD/src" python3 \
 scripts/p08_b45_perf_full1024_physical_run.py \
 --experiment once --build "$P08_B45_FULL_ONCE_BUILD" \
 "${P08_B45_FULL_COMMON[@]}" --mode preflight

PYTHONPATH="$PWD/scripts:$PWD/src" python3 \
 scripts/p08_b45_perf_full1024_physical_run.py \
 --experiment unchecked --build "$P08_B45_FULL_UNCHECKED_BUILD" \
 "${P08_B45_FULL_COMMON[@]}" --mode preflight
~~~

Require both print:
~~~text
P08_B45_PERF_FULL1024_ORIGINAL_SOURCES_AND_REAL_ELF_OFFLINE_PASS=1
P08_B45_PERF_BACKUP_HARDWARE_PROTECTED=0
P08_B45_PERF_BOARD_VISITED=0
P08_B45_PERF_DESTRUCTIVE_JTAG_NOT_AUTHORIZED_BY_PREFLIGHT=1
~~~

No true 1024 ELF or exact original scalar proof => no physical launch.

## E. BEFORE any destructive JTAG run

Original physically accepted P07-B4i dedicated halt and PS-width
gate must pass first. Use a disposable board/Linux/JTAG session,
working physical reboot recovery, local hw_server (tcp localhost:3121),
no other XSDB/Vivado client, existing original P03 routed BIT/LTX.
This JTAG operation halts Linux A53, programs PL, overwrites original
six DDR staging areas, loads a separate low-DDR A53 ELF, writes
mailbox/three result sidecars. Other boot/early DMA owners and
write-protection remain unproven; risk is explicitly accepted.
A failure to halt all A53/verify 128-bit widths aborts BEFORE any
PL/DDR step; no bypasses. POWER CYCLE/REBOOT after every attempt,
never resume that halted Linux instance.

PuTTY, short single-line inspection only:
~~~bash
sudo xmutil listapps
~~~

If an FPGA app is loaded, and you are ready to free the original PL:
~~~bash
sudo xmutil unloadapp
~~~

All remaining commands execute on the PC in VS Code. Do not
paste anything else through PuTTY.

Define approvals in VS Code only after accepting ten distinct
destructive physical actions:
~~~bash
P08_B45_APPROVALS=(
 --dedicated-jtag-owner YES
 --discard-linux-and-halt-all-a53-approved YES
 --unproven-boot-ddr-dma-exclusivity-risk-accepted YES
 --six-original-ddr-transfers-overwrite-approved YES
 --original-p03-pl-programming-approved YES
 --low-ddr-new-performance-elf-overwrite-approved YES
 --mailbox-and-three-journals-overwrite-approved YES
 --unprotected-backup-integrity-tradeoff-accepted YES
 --post-run-backup-readback-approved YES
 --reboot-and-recovery-approved YES
)
~~~

## F. ONCE full1024: main command, then separate live monitor terminal

VS Code **TERMINAL 1**: set evidence path and publish ONLY a simple
host-side pointer to it, so TERMINAL 2 never needs to type a huge path:

~~~bash
export P08_B45_FULL_ONCE_PHYSICAL="$HOME/Thesis_Evidence/p08_b45_perf_once_full1024_physical_$(date -u +%Y%m%dT%H%M%SZ)"
printf '%s\n' "$P08_B45_FULL_ONCE_PHYSICAL" > "$HOME/Thesis_Evidence/p08_b45_active_full1024_path.txt"
test ! -e "$P08_B45_FULL_ONCE_PHYSICAL" || echo "STOP: evidence path already exists"
~~~

VS Code **TERMINAL 2**, BEFORE or DURING the main run:

~~~bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
python3 -u scripts/p08_b45_perf_full1024_monitor.py \
 --experiment once \
 --evidence "$(cat "$HOME/Thesis_Evidence/p08_b45_active_full1024_path.txt")" \
 --interval 15
~~~

Monitor reads host stage.txt, then atomic host
performance1024_capture/progress_state.txt written by the **original
launch XSDB process**. It does NOT open JTAG itself, nor touch PuTTY,
DDR or progress mailbox independently. Status shows completed/1024,
percent, observed frames/sec, elapsed and snapshot age; STALE snapshot
warning identifies a stalled file. CAPTURE_DONE is **not** independent
numerical/FNV PASS. Ctrl+C on monitor does not stop main test.

VS Code **TERMINAL 1**, with both PC preflights already PASS:

~~~bash
PYTHONPATH="$PWD/scripts:$PWD/src" python3 \
 scripts/p08_b45_perf_full1024_physical_run.py \
 --experiment once --build "$P08_B45_FULL_ONCE_BUILD" \
 "${P08_B45_FULL_COMMON[@]}" \
 --mode execute --evidence "$P08_B45_FULL_ONCE_PHYSICAL" \
 "${P08_B45_APPROVALS[@]}"
~~~

After ANY attempt, **reboot/power-cycle KV260**. On errors preserve
all raw evidence and stop; no retries without diagnosing first.
The host-produced main preliminary PASS marker, if present:
~~~text
P08_B45_PERF_FULL1024_SAME_SESSION_JTAG_SCALAR_FNV_AND_BACKUP_PASS=1
~~~
requires strict all1024 scalar/FNV+time and postbackup; independent
review STILL REQUIRED before accepting a research measurement.

Back in **TERMINAL 1** after reboot:

~~~bash
export P08_B45_FULL_ONCE_INDEPENDENT="$HOME/Thesis_Evidence/p08_b45_perf_once_full1024_independent_$(date -u +%Y%m%dT%H%M%SZ).json"
PYTHONPATH="$PWD/scripts:$PWD/src" python3 \
 scripts/p08_b45_perf_full1024_independent_verify.py \
 --experiment once --build "$P08_B45_FULL_ONCE_BUILD" \
 "${P08_B45_FULL_COMMON[@]}" \
 --evidence "$P08_B45_FULL_ONCE_PHYSICAL" \
 --out "$P08_B45_FULL_ONCE_INDEPENDENT"
sha256sum "$P08_B45_FULL_ONCE_INDEPENDENT"
~~~

Expected:
~~~text
P08_B45_PERF_FULL1024_INDEPENDENT_ALL1024_SCALAR_FNV_AND_POSTBACKUP_PASS=1
~~~

Only on full independent PASS proceed to unchecked.

## G. UNCHECKED full1024 — separately re-booted board, same proven gate

After **once** independent PASS and a new boot/session, repeat short
PuTTY app inspection/unload if needed, and ensure no previous debug
client holds JTAG. Full original DDR staging is re-executed on each
physical session, with new post-run proof.

**TERMINAL 1**:

~~~bash
export P08_B45_FULL_UNCHECKED_PHYSICAL="$HOME/Thesis_Evidence/p08_b45_perf_unchecked_full1024_physical_$(date -u +%Y%m%dT%H%M%SZ)"
printf '%s\n' "$P08_B45_FULL_UNCHECKED_PHYSICAL" > "$HOME/Thesis_Evidence/p08_b45_active_full1024_path.txt"
test ! -e "$P08_B45_FULL_UNCHECKED_PHYSICAL" || echo "STOP: evidence path already exists"
~~~

**TERMINAL 2** (new independent read-only monitor process):

~~~bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
python3 -u scripts/p08_b45_perf_full1024_monitor.py \
 --experiment unchecked \
 --evidence "$(cat "$HOME/Thesis_Evidence/p08_b45_active_full1024_path.txt")" \
 --interval 15
~~~

**TERMINAL 1**, from existing v3 original-source working directory:

~~~bash
PYTHONPATH="$PWD/scripts:$PWD/src" python3 \
 scripts/p08_b45_perf_full1024_physical_run.py \
 --experiment unchecked --build "$P08_B45_FULL_UNCHECKED_BUILD" \
 "${P08_B45_FULL_COMMON[@]}" \
 --mode execute --evidence "$P08_B45_FULL_UNCHECKED_PHYSICAL" \
 "${P08_B45_APPROVALS[@]}"
~~~

Reboot/power-cycle again after ANY JTAG attempt.
Then **TERMINAL 1**:

~~~bash
export P08_B45_FULL_UNCHECKED_INDEPENDENT="$HOME/Thesis_Evidence/p08_b45_perf_unchecked_full1024_independent_$(date -u +%Y%m%dT%H%M%SZ).json"
PYTHONPATH="$PWD/scripts:$PWD/src" python3 \
 scripts/p08_b45_perf_full1024_independent_verify.py \
 --experiment unchecked --build "$P08_B45_FULL_UNCHECKED_BUILD" \
 "${P08_B45_FULL_COMMON[@]}" \
 --evidence "$P08_B45_FULL_UNCHECKED_PHYSICAL" \
 --out "$P08_B45_FULL_UNCHECKED_INDEPENDENT"
sha256sum "$P08_B45_FULL_UNCHECKED_INDEPENDENT"
~~~

Only after independent PASS for both is one descriptive physical
original vs once vs unchecked comparison supported. Two independent
sessions do NOT establish randomized AB/BA repeatability, statistical
confidence or equal security guarantees; the accepted original
one-session reference remains descriptive. The final special
trace frame ordinal 1023 is excluded from normal service-latency
statistics. Retain both original reports and all raw receipts,
not just terminal markers. No official TEST access.
