# P08-B44 post-power-cycle external-debug-disabled A53 #1: read-only diagnostics

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
