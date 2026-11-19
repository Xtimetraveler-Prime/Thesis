# M08 D3.2 — Physical stage 0: stock-only, read-only KV260 baseline


## 2026-11-19 second owner read-only evidence accepted in five scopes; exact privilege fault isolated

Owner supplied all actual probe data and 99 SHA verified for `m08_d3_2_stock_READONLY_oyz3sts9`: SSH exit=0, stdout boundary markers present, **5/6** read-only probes rc=0. Only `installed_apps` rc=1, explicitly `xmutil should be called with root privileges. Please try again using 'sudo'.` Baseline correctly refused overall success. Other current observations: KV260 revB, Ubuntu 24.04.2 and kernel 6.8.0-1036-xilinx; FPGA manager `operating`, `dfx-mgr` and `fancontrol` `active`; `default_firmware=k26-starter-kits`; active overlay `k26-starter-kits_image_1`; only four `axi-pmon` UIO names and no M08 UIO entries. Sensor readbacks 31.350/31.909/29.803 Celsius at capture, not proof of physical fan or safe load. Stock file hashes on board: `k26_starter_kits.bit.bin` f9dfe95d14881a2768b2c0e6a36fc363635e8ae7882ecad9725d270490395d3e, `k26_starter_kits.dtbo` 1e998ffd5d33a05da3746df3603e65603e1628006bc878209a836cc9bd3c4ae1, `shell.json` 2967ccbc1f75c8d4accd1b6fecc11b16a32a5d7992e56c6eebceb99a3410f777. These represent **one observed stock deployment**, not an independently tested restore after a new PL fault.

**Narrow correction:** Board script now uses `sudo -n xmutil listapps` ONLY for the unprivileged-account-rejected, read-only installed-apps inventory. This does not grant generic sudo to the other probes. PC gate asserts the exact unique privileged command; tests reject substituted loadapp, sudo shell and duplicated elevated operations. The `-n` option fails immediately without a pre-existing noninteractive sudo policy; **do not add passwordless sudo for unrelated operations**. Captured original evidence directories remain immutable. PC capture still requires original new passive .bit 99/98/96 receipts, manually verified independently powered backup fan, UART/known stock recovery, and unchanged pinned board target/host-key identity. Follow-on is a fresh stage-0 observation, NOT permission to load the FPGA.



## 2026-11-19 SSH authentication update and second incomplete baseline

The owner reports installing a **public SSH key in the KV260 `ubuntu` account** (via prior `ssh-copy-id` guidance; exact public key fingerprint, server-side `authorized_keys` contents and installation method not independently inspected). The owner independently verified PC → board **noninteractive key-based authentication** using `ssh -T -o BatchMode=yes -o StrictHostKeyChecking=yes ubuntu@10.42.0.135 'echo M08_SSH_AUTHENTICATION_OK'`, receiving `M08_SSH_AUTHENTICATION_OK`. **No private key material or passphrase belongs in this repository or evidence reports.**

Earlier PC capture `m08_d3_2_stock_READONLY_rp2nq3it` had SHA receipt intact, SSH exit 255 and `Permission denied (publickey,password)`; expected probe markers absent, **none executed**. After key installation the owner retried the new stage-0 script with readiness flags manually set true; it created a **different PC evidence directory**, `m08_d3_2_stock_READONLY_oyz3sts9`, still returned `STOCK_BOARD_READONLY_CAPTURE_INCOMPLETE_STOP`, `board_programmed=false`, `no_bitstream_copied_to_board=true`. **Reason for the second failure is not yet known**. A simple SSH echo proves authentication, not that all six board probes succeed.

**Next action is diagnostic only, no re-run or PL load:** On the PC, verify the new directory's `99_evidence_sha256.txt`, then inspect `06_readonly_review.json`, `05_ssh_exit_status.txt`, `04_board_stderr.log` and `M08_D3_2_PROBE_(BEGIN|END)` lines plus any failure output in `03_board_stdout.log`. If SSH exit 0 but individual probes fail, review exact `rc` and first error. A known potential incompatibility is that `xmutil listapps` is called as unprivileged `ubuntu`, whereas older owner scripts used `sudo -n xmutil listapps`; treat this only as a hypothesis until evidence arrives. Do not automatically loosen the access boundary or treat nonzero probe statuses as pass. No bitstream load is approved.


**Date:** 2026-11-19. **User request:** try another physical run after owner-PC new passive bitstream generation. This document prepares a safe *first physical observation* of the **existing stock boot**. It is **NOT permission to reconfigure/program the FPGA, load an app, write registers, update boot/firmware, change fans, or access MMIO**.

## Candidate identity and previous incident

Owner supplied actual Vivado 2025.2 output from /home/dna/Thesis_Evidence/M08/m08_d3_2_passive_synth_gKr8mQe6, containing a validated 99 (synthesis), 98 (route), and 96 (new candidate) SHA ledger. Original owner auditor returned M08_D3_2_UNRELEASED_PASSIVE_BITSTREAM_SHA_ACCEPTED_NO_BOARD.

**New candidate:** bitstream_candidate/m08_d3_2_passive_fan_UNRELEASED.bit; 7,797,839 bytes; SHA256 07af9e26905fd72b4d6b5845cbb4e309ecbefa83745a7c371769648cd0bdd547. Vivado K26 part xck26-sfvc784-2LV-c; KV260 SOM board 1.4; fan A12 LVCMOS33; HPM0/HPM1/LPD disabled, no page/identity/neural RTL. DRC=zero default findings, WNS/TNS=NA with zero timed fabric endpoints. The new image is still UNRELEASED, with no .bit.bin/DTBO/boot image or stock manager compatibility proof.

**Original failing M08 image:** original bit.bin SHA256 a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b remains QUARANTINED. Earlier original M08 Linux PS/PL identity read produced genuine RCU/timer stalls, lost SSH, and only recovered after forced power cycle; root cause UNKNOWN. Historical stock k26-starter-kits was observed after power cycle. That is not reliable, pretested rollback for any new image. Never invoke original m08_kv260_program_oneshot.tcl, which is pinned to a different historical candidate/target and is not suitable for this new image.

AMD Kria uses Linux dfx-mgr to manage FPGA and DT overlays; the default stock image routes TTC0 through EMIO to A12 fan control. A raw .bit file is not automatically interchangeable with the running dfx-mgr-installed stock image. Direct JTAG reprogramming while Linux owns the PL is NOT a sanctioned substitute for checking the stock manager, PS, fan and firmware/DT lifecycle.

## Stage 0 operator prerequisites (no board access before these)

Independently power the backup fan, visually/physically confirm airflow; this fan must NOT require TTC0/PL PWM or the board's Linux fancontrol service. Establish the KV260 UART console (with terminal logging already running), confirm access to physical power control, and identify the original stock boot media/recovery process. Check the board is not currently hung. These are manual observations, not claims from our Python source or SSH status.

Owner readiness JSON starts **ALL FALSE** at docs/M08_D3_2_OWNER_STOCK_READONLY_READINESS_TEMPLATE.json. Copy it into a PC-only separate file; edit only true fields personally verified. The tool explicitly labels manual observations as NOT independent boot-platform proof. No source branch command may flip the flags automatically.

## Owner commands — PC, source and native evidence

    cd ~/Git/Thesis
    git status --short
    git fetch origin
    git switch agent/neuromorphic-accelerator-v1-m08-d3b-boot-ownership-audit
    git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-d3b-boot-ownership-audit
    git rev-parse HEAD
    cd Neuromorphic_Accelerator/v1

    python3 -m compileall -q src scripts tests
    python3 -m unittest discover -s tests -p 'test_m08_d3_2_stock_baseline_pc.py' -v
    python3 -m unittest discover -s tests -p 'test_m08*.py' -v
    python3 -m unittest discover -s tests -v
    bash -n scripts/m08_d3_2_stock_board_baseline_readonly.sh

    RUN="$HOME/Thesis_Evidence/M08/m08_d3_2_passive_synth_gKr8mQe6"
    (cd "$RUN" &&
      sha256sum -c 99_evidence_sha256.txt &&
      sha256sum -c 98_route_evidence_sha256.txt &&
      sha256sum -c 96_candidate_evidence_sha256.txt)
    python3 scripts/m08_d3_2_passive_bitstream_gate.py --run-dir "$RUN"

Copy the **FALSE by default** manual checklist:

    cp docs/M08_D3_2_OWNER_STOCK_READONLY_READINESS_TEMPLATE.json \
       "$HOME/Thesis_Evidence/M08/m08_d3_2_owner_readiness.json"
    nano "$HOME/Thesis_Evidence/M08/m08_d3_2_owner_readiness.json"

Change only confirmations you have personally verified to true. If any cannot be confirmed, STOP before SSH; no blanket override or forced permission. The manual record references only the new bit SHA256.

## Stage 0: one PC initiated read-only SSH capture — AFTER manual prerequisites

    cd ~/Git/Thesis/Neuromorphic_Accelerator/v1

    python3 scripts/m08_d3_2_stock_baseline_pc.py \
       --candidate-run "$RUN" \
       --readiness "$HOME/Thesis_Evidence/M08/m08_d3_2_owner_readiness.json" \
       --evidence-base "$HOME/Thesis_Evidence/M08" \
       --target ubuntu@10.42.0.135

The code verifies the new candidate full 99/98/96 receipts **BEFORE SSH**, refuses wrong SHA or old original image, refuses missing manual observations, requires known host key and non-root account, and streams scripts/m08_d3_2_stock_board_baseline_readonly.sh into a remote Bash process. It does NOT write any files to the board; it only reads model, uname, current FPGA-manager state, dfx-mgr/fancontrol statuses, stock firmware-file paths + hashes, xmutil listapps (read only, no sudo), temperature/fan sensors, active overlay and UIO *names*, not device registers. It never calls xmutil unloadapp/loadapp, JTAG, bitstream conversion, FPGA manager writes, sudo, root or MMIO.

A completed capture yields (new path each time):

    {
      "status": "STOCK_BOARD_READONLY_CAPTURE_COMPLETE_HUMAN_REVIEW_REQUIRED",
      "board_programmed": false,
      "no_bitstream_copied_to_board": true,
      "new_pc_evidence_dir": "...m08_d3_2_stock_READONLY_..."
    }

An incomplete probe or SSH mismatch yields STOCK_BOARD_READONLY_CAPTURE_INCOMPLETE_STOP, preserves evidence and exits nonzero. A completed SSH script is NOT proof that the reported stock image is actually compatible with this Vivado PS design, and neither a reported stock firmware path nor a manual checklist proves rollback.

Examine the new path:

    BASELINE="<NEW_PC_EVIDENCE_DIR_FROM_OUTPUT>"
    (cd "$BASELINE" && sha256sum -c 99_evidence_sha256.txt)
    cat "$BASELINE/06_readonly_review.json"
    cat "$BASELINE/03_board_stdout.log"
    cat "$BASELINE/04_board_stderr.log"

Share the original 06 JSON and the selected stock manager/stock firmware/fan/overlay lines from 03 stdout, but do not share secrets or private hostnames. No additional programming commands follow from this capture automatically.

## Gate before any first physical PL image replacement (NOT satisfied here)

1. Independently powered fan actually working; UART log and power cycle recovery available.
2. Stock manager/FPGA-region ownership and original stock firmware bytes identified and backed up or reinstallable from a trustworthy source; **stock recovery tested/defined without depending on SSH after a possible stall**.
3. Choice between Linux dfx-mgr managed transition (requires matching .bit.bin, DTBO and shell identity) and isolated JTAG test (requires actually isolated PS/PL, not a running Linux-managed image) reviewed against the **current** KV260 version. Neither approach is yet authorized.
4. Explicit exact new SHA, physical-target identity, one-shot stop criteria, and rollback steps in separate physical test plan. Never invoke historical one-shot scripts pinned to old image/target.
5. No first identity register read, /dev/uio, FPGA region writes, PL0/reset/AFI/ATB4/AIB13 settings or original M08 .bit.bin.

**Next decision:** inspect stock-only snapshot, then separately prepare/approve one-shot passive-only PL load in a compatible, recoverable state. If any condition is unknown, do not load the bitstream.
