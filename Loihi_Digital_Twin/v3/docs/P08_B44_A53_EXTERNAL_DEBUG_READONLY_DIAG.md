# P08-B44 post-power-cycle external-debug-disabled A53 #1: read-only diagnostics

## 2026-11-02 RECORDED genuine post-power-cycle PS TAP, PMU, PL-only XSDB target inventory

Operator explicitly confirms **normal PuTTY boot after full KV260 power cycle**.
The existing separate, read-only, SINGLE-CLIENT XSDB inventory
connected successfully. It identified physical xck26 (idcode
04724093) and ARM DAP (idcode 5ba00477), but showed ONLY:

    1 PS TAP
      2 PMU
      3 PL

**Missing** from the same XSDB target listing: PSU, RPU, APU,
and Cortex-A53 #0/#1/#2/#3 software debug targets. AMD UG1725
2024.2 debugging examples display these targets as part of
the same ordinary XSDB target listing. It is therefore NOT
safe to assume that this result was only a collapsed hierarchy.
Earlier original accepted B4.2 had been able to select PSU.
The current debug-target enumeration state differs, and may
relate to JTAG debug permissions, boot/firmware/security,
core power states, or XSDB dynamic discovery. NONE has yet
been independently isolated as the sole root cause. Serial
boot and physical ARM DAP JTAG recognition do NOT alone
prove CPU external-debug authorization.

Operator's original read-only JTAG report:
    /home/dna/Thesis_Evidence/p08_b44_a53_target_readonly_20261102T224514Z.log
SHA256:
    f3d7af4824b43a7b1aa66f4bd8ce92669cedc76a8cee73efb3371d97cc22a769

AMD UG1209 v2025.2 notes that some JTAG security gates
are enabled by default and its boot tutorial describes
**invasive** register writes to change them. We do NOT
perform those writes, disable debug/security protections,
modify Linux cores, or classify external-debug-disabled as
powered down. The exact earlier original P07-B4i safety
gate remains unchanged.

New additional read-only XSDB metadata in our existing
observer, and therefore newly covered by native CI:
- targets -target-properties
- jtag targets -target-properties -filter {name =~ "arm_dap"}

These are READ-ONLY target metadata queries, not JTAG
security permission changes or processor halt/restart. A
device node property such as is_open is a debugger handle
property, NOT proof that all CPU external debug is unlocked.
Both are wrapped in catch so a version-specific error
preserves the basic target inventory.

### Next single-client read-only check (PC terminal)

    cd ~/Git/Thesis
    git fetch origin
    git switch agent/v3-p08-b44-profiling
    git pull --ff-only origin agent/v3-p08-b44-profiling
    source ~/Git/Thesis/.venv-p08/bin/activate
    cd Loihi_Digital_Twin/v3

    PYTHONPATH="$PWD/src" python -m pytest -q -rs       tests/test_p08_b44_readonly_a53_diagnostic.py

    export P08_B44_READONLY2="$HOME/Thesis_Evidence/p08_b44_a53_properties_readonly_$(date -u +%Y%m%dT%H%M%SZ).log"
    test ! -e "$P08_B44_READONLY2"
    set -o pipefail
    xsdb vivado/p08_b44_a53_status_readonly.tcl tcp:127.0.0.1:3121       2>&1 | tee "$P08_B44_READONLY2"
    sha256sum "$P08_B44_READONLY2"

Optional: if Linux shell is available on PuTTY (KV260,
NOT PC), read only:

    cat /sys/devices/system/cpu/online
    cat /sys/devices/system/cpu/offline
    cat /sys/devices/system/cpu/present

STOP after the one metadata observation. DO NOT rerun
the nine-YES B4.4 destructive physical profiling session
or change DDR, PS security, JTAG security gates, original
firmware, or original P07 B4i halt policy. Genuine
B4.4 profile hardware timings are STILL NOT captured.
Original first B4.2 1024 physical scalar/FNV parity,
1023 ordinary service timing and genuine new B44
Vitis profile ELF remain accepted and unchanged.
Official TEST sealed.

---

FIRST failed real B4.4 experimental profile JTAG attempt 2026-11-02:
  /home/dna/Thesis_Evidence/p08_b44_profile1024_physical_20261102T201705Z

User's new Vitis profile ELF/map/offline source admission and B4.4
PC-only FULL1024 oracle/previous B3+B4.2 physical preflight PASSED.
After nine operator YES flags, the original unmodified P07-B4i A53
stop/FPD128 gate observed two transient powerdown retries on
A53 #0, then a positive A53 #0 stop, then FAILED on A53 #1:

  Context Cortex-A53 #1 state: External debug access is disabled
  P07_B4I_STOP_WIDTH_GATE_FAIL_REBOOT_REQUIRED=1

No physical P03 programming, original 6 DDR transfers, new ELF
download, 1024 neural journal or reset profile capture happened.
The user FULLY POWER CYCLED the board. PC file listing contains only
preflight.json, stage.txt and a53_takeover_and_ps128.log (486 B).
PC process list shows one hw_server process tree (launcher + loader
+ actual server), no separate xsdb or Vivado process. Remote
hw_server clients cannot be ruled out from local pgrep alone.
Normal boot via PuTTY has NOT yet been reported.

**Never change the original P07-B4i fail-closed guard to accept
external-debug-disabled as proof that a CPU is halted/off.**
Arm Cortex-A53 TRM distinguishes core-off EDPRSR.PU=0 from
AllowExternalDebugAccess()==FALSE (EDAD), plus other lock states.
The XSDB message alone does not isolate the cause, which might
involve boot/firmware, power states, or debug access control.

## Step 1: Verify recovery in normal serial console

Since the board has already been power cycled, use the usual
PuTTY serial connection to confirm its original expected
boot state. If Linux login exists, optional READ-ONLY commands
INSIDE PuTTY on KV260 (not in PC terminal):

    uname -a
    cat /sys/devices/system/cpu/online
    cat /sys/devices/system/cpu/offline
    cat /sys/devices/system/cpu/present

Linux CPU hotplug status does NOT by itself prove that XSDB
can safely stop/read every CPU. Do not modify CPU online
state, security/debug gates, boot files or PSU registers.

## Step 2: ONE read-only JTAG target-status observation

Only after confirming normal board recovery, with no concurrent
Vivado/XSDB user/session, use the new dedicated Tcl script.
It executes ONLY connect, targets, jtag targets, disconnect;
NO stop/rst/dow/mwr/mrd/con/PL programming or selecting CPUs.
Unlike the historical PC-only mailbox file monitor, this
DOES contact hardware via READ-ONLY JTAG inspection.

    cd ~/Git/Thesis
    git fetch origin
    git switch agent/v3-p08-b44-profiling
    git pull --ff-only origin agent/v3-p08-b44-profiling
    source ~/Git/Thesis/.venv-p08/bin/activate
    cd Loihi_Digital_Twin/v3
    PYTHONPATH="$PWD/src" python -m pytest -q -rs \
      tests/test_p08_b44_readonly_a53_diagnostic.py

    export P08_B44_READONLY_LOG="$HOME/Thesis_Evidence/p08_b44_a53_target_readonly_$(date -u +%Y%m%dT%H%M%SZ).log"
    test ! -e "$P08_B44_READONLY_LOG"
    set -o pipefail
    xsdb vivado/p08_b44_a53_status_readonly.tcl tcp:127.0.0.1:3121 \
      2>&1 | tee "$P08_B44_READONLY_LOG"
    sha256sum "$P08_B44_READONLY_LOG"

Expected success markers (all *diagnostic* only):

    P08_B44_READONLY_JTAG_TARGET_OBSERVATION_CONNECTED=1
    P08_B44_READONLY_JTAG_TARGETS_BEGIN
    ... current XSDB processor and statuses ...
    P08_B44_READONLY_JTAG_TARGETS_END
    P08_B44_READONLY_JTAG_CHAIN_BEGIN
    ... JTAG device list ...
    P08_B44_READONLY_JTAG_CHAIN_END
    P08_B44_READONLY_TARGET_OBSERVATION_ONLY=1
    P08_B44_HALTED_OR_POWERED_DOWN_ALL_A53_PROVEN=0
    P08_B44_NEW_PROFILE_PHYSICAL_JTAG_AUTHORIZED=0
    P08_B44_ORIGINAL_P07_CORE_STOP_GATE_UNCHANGED=1

AMD UG1725/UG1400 document connect, targets and jtag targets
for listing processor and JTAG states. Do not confuse a
read-only target listing (which may display Running,
No Power, or External debug access is disabled) with a
successful safe takeover / 128bit FPD width check.

STOP after this inspection and share original target statuses,
serial boot result and log SHA. Do not rerun the nine-YES
destructive profiling command. The original P07-B4i strict
A53 takeover must still succeed in any future separately
approved physical attempt. All accepted B4.2 evidence and
new genuine Vitis profile ELF SHA remain untouched; actual
B4.4 physical reset microtiming is STILL NOT COLLECTED.
Official TEST sealed. No PL speedup/energy/exclusive boot/DDR
owner claims.
