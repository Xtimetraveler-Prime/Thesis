# M08.2b.3/.4 — Post-power-cycle physical UIO test and recovery runbook
**Prepared 2026-11-12; PR #83 DRAFT/UNMERGED.** Physical MMIO has NOT been executed or accepted. Keep independent external cooling powered and PuTTY UART recovery available.

## Accepted original owner kernel-binding evidence

Received m08_2b_identity_binding_READONLY_SUEpxqpK.tar.gz SHA256 **0962658528d715d761a81309af890ec949588ebb0f61504e369f14e3390bb24c**. Six entries including SHA ledger, all **five covered files** independently match. Original ledger SHA256 **26a0cb6759b5e2286048d8b49f6134a74fb5a26e6bdcd28826db8d583e7dbbb6**. SSH exit0, empty stderr. Real KV260 revB and running M08 overlay/FPGA manager/fancontrol; both M08 identities have kernel symlinks resolving to uio_pdrv_genirq: m08-identity uio4 0xA0000000/4096, m08-page uio5 0xA0001000/4096. Temperatures 35.158/35.515/33.277°C. These names and address bindings are accepted for the original session; UIO numbers may change after power cycle. **NO /dev/uio or physical register access occurred.**

## Power-cycle consequence

Existing /etc/dfx-mgrd/default_firmware was observed to contain k26-starter-kits. On daemon startup Linux typically loads this original stock app by default; see https://github.com/Xilinx/dfx-mgr (default_accel) and https://xilinx.github.io/kria-apps-docs/dfx/build/html/docs/run_application_on_target.html . The EXACT post-boot board state must be inspected before any access. The original successful M08 PL_FLAT triplet was installed in /lib/firmware/xilinx/m08-v1-fan-page-uio-review and is expected to persist across reboot, but its bytes and registration must be reverified.

## PC source update and regression tests

~~~bash
cd /home/dna/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-kv260-bringup
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-kv260-bringup
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m08_physical_uio_operator.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -p 'test_*.py' -v
~~~

Require 8/8 M01–M08 CI workflows green on exact HEAD before real board use.

## Inspect power-cycled board FIRST (no PL operation)

~~~bash
EVIDENCE_BASE=/home/dna/Thesis_Evidence/M08
POSTBOOT="$(mktemp -d "$EVIDENCE_BASE/m08_2b_post_reboot_XXXXXXXX")"
ssh -tt ubuntu@10.42.0.135 'sudo xmutil listapps; cat /sys/class/fpga_manager/fpga0/state; systemctl is-active dfx-mgr fancontrol; cat /etc/dfx-mgrd/default_firmware; for f in /sys/class/hwmon/hwmon*/temp*_input; do if test -r "$f"; then printf "%s=" "$f"; cat "$f"; fi; done' 2>&1 | tee "$POSTBOOT/01_postboot.log"
POST_RC=${PIPESTATUS[0]}
printf 'exit_status=%s\n' "$POST_RC" > "$POSTBOOT/02_exit.txt"
(cd "$POSTBOOT" && sha256sum 01_postboot.log 02_exit.txt > 99_evidence_sha256.txt)
~~~

Inspect **each** result; the semicolon-separated SSH command exiting 0 does not mean every sub-probe passed. If manager not operating, SSH/UART unstable, unexpected app, unverified fan: STOP. If stock k26-starter-kits XRT_FLAT 0->0 is loaded, externally verify second fan and serial recovery and SHA recheck both original stock and M08 package before the one permitted managed transition. If M08 PL_FLAT 0->0 is already loaded, **do not reconfigure**. If no app is loaded, avoid unnecessary unload and only load once after operator risk review. Never change default firmware or use JTAG/devmem.

## Re-establish actual M08 only when needed

Use interactive VS Code ssh -tt ubuntu@10.42.0.135 so sudo can prompt. Run the checks individually and STOP on any mismatch:

~~~bash
sudo -v
sudo xmutil listapps
cat /sys/class/fpga_manager/fpga0/state
systemctl is-active dfx-mgr fancontrol
cat /etc/dfx-mgrd/default_firmware
APP=m08-v1-fan-page-uio-review
printf '%s  %s\n' a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b /lib/firmware/xilinx/$APP/$APP.bit.bin | sha256sum -c -
printf '%s  %s\n' 2b7798053d10415ef528d4abbbdcb5251cd0dee4845c3288de2a3ef7bd2e75ed /lib/firmware/xilinx/$APP/$APP.dtbo | sha256sum -c -
printf '%s  %s\n' 0377daaf2050b88df14de9a79d120144cf49381d00fa552402395a322cb7b1a3 /lib/firmware/xilinx/$APP/shell.json | sha256sum -c -
printf '%s  %s\n' f9dfe95d14881a2768b2c0e6a36fc363635e8ae7882ecad9725d270490395d3e /lib/firmware/xilinx/k26-starter-kits/k26_starter_kits.bit.bin | sha256sum -c -
printf '%s  %s\n' 1e998ffd5d33a05da3746df3603e65603e1628006bc878209a836cc9bd3c4ae1 /lib/firmware/xilinx/k26-starter-kits/k26_starter_kits.dtbo | sha256sum -c -
printf '%s  %s\n' 2967ccbc1f75c8d4accd1b6fecc11b16a32a5d7992e56c6eebceb99a3410f777 /lib/firmware/xilinx/k26-starter-kits/shell.json | sha256sum -c -
~~~

If **stock ACTIVE**, after confirming external cooling/serial logging and all 6 hashes, explicitly type RELOAD_M08 and run exactly once: sudo xmutil unloadapp; sudo xmutil loadapp m08-v1-fan-page-uio-review. If **no image ACTIVE**, issue only sudo xmutil loadapp m08-v1-fan-page-uio-review; if **M08 already ACTIVE**, do nothing. If load fails, no blind retry; keep external fan on and recover original stock according to *observed actual manager state*. Check active M08 slot, overlay, fpga_manager operating, temps and services.

After any reboot/load, from PC again run bash scripts/run_m08_identity_binding_readonly_pc.sh ubuntu@10.42.0.135; it must PASS and create original SHA evidence.

## Stage first-party on-board Python source, not FPGA firmware

The physical operator imports the existing first-party read-only identity and 64-word page protocol. PC (from v1 root), after re-establishing a successfully loaded M08 and read-only kernel ownership:

~~~bash
REMOTE_DIR="$(ssh -T ubuntu@10.42.0.135 'mktemp -d "$HOME/m08_2b_tests_XXXXXXXX"')"
[[ "$REMOTE_DIR" =~ ^/home/ubuntu/m08_2b_tests_[A-Za-z0-9]+$ ]] || { echo "STOP unexpected remote path"; exit 2; }
echo "REMOTE_DIR=$REMOTE_DIR"
ssh -T ubuntu@10.42.0.135 "mkdir -m 755 '$REMOTE_DIR/neuromorphic_accelerator_v1'"
scp -p scripts/m08_kv260_physical_uio_operator.py "ubuntu@10.42.0.135:$REMOTE_DIR/"
scp -p src/neuromorphic_accelerator_v1/__init__.py src/neuromorphic_accelerator_v1/m08_identity_client.py src/neuromorphic_accelerator_v1/m08_uio_page_protocol.py "ubuntu@10.42.0.135:$REMOTE_DIR/neuromorphic_accelerator_v1/"
sha256sum scripts/m08_kv260_physical_uio_operator.py src/neuromorphic_accelerator_v1/__init__.py src/neuromorphic_accelerator_v1/m08_identity_client.py src/neuromorphic_accelerator_v1/m08_uio_page_protocol.py
ssh -T ubuntu@10.42.0.135 "sha256sum '$REMOTE_DIR/m08_kv260_physical_uio_operator.py' '$REMOTE_DIR/neuromorphic_accelerator_v1/__init__.py' '$REMOTE_DIR/neuromorphic_accelerator_v1/m08_identity_client.py' '$REMOTE_DIR/neuromorphic_accelerator_v1/m08_uio_page_protocol.py'"
~~~

Manually **require all four local/remote SHA values equal**, no auto rerun. Execute no-MMIO readiness first:

~~~bash
ssh -tt ubuntu@10.42.0.135 "sudo python3 '$REMOTE_DIR/m08_kv260_physical_uio_operator.py' --mode preflight"
~~~

Require LIVE_KERNEL_AND_INSTALLED_FIRMWARE_READY_NO_MMIO. This probes real UIO /dev character device identity, six stock/M08 firmware digests, actual live M08 slot and driver without opening /dev/uio.

## M08.2b.3 — Physical identity READ (one attempt; not yet run)

**HAZARD:** Even an O_RDONLY Linux mmap of inaccessible AXI hardware can SIGBUS or hang the kernel. GNU timeout is **not a guarantee** of recovery if a kernel task is uninterruptible. Require independently powered cooling, PuTTY UART access, operator oversight and consent; stock restore is documented but an actual manager-controlled rollback has NOT been exercised. Do NOT fake a YES approval claiming otherwise. This new operator explicitly flags the unexercised rollback instead.

~~~bash
MMIO_EVIDENCE="$(mktemp -d "$EVIDENCE_BASE/m08_2b_first_mmio_XXXXXXXX")"
printf 'head=%s\nremote=%s\n' "$(git rev-parse HEAD)" "$REMOTE_DIR" > "$MMIO_EVIDENCE/00_context.txt"
ssh -tt ubuntu@10.42.0.135 "sudo env M08_EXPLICIT_PHYSICAL_TEST_APPROVED=YES timeout --kill-after=3s 20s python3 '$REMOTE_DIR/m08_kv260_physical_uio_operator.py' --mode identity --acknowledge-axi-read-risk --acknowledge-rollback-not-yet-exercised --output-file '$REMOTE_DIR/identity.json'" 2>&1 | tee "$MMIO_EVIDENCE/01_identity_original.log"
ID_RC=${PIPESTATUS[0]}
printf 'exit_status=%s\n' "$ID_RC" > "$MMIO_EVIDENCE/02_identity_exit.txt"
echo "ID_RC=$ID_RC"
~~~

**If ID_RC nonzero, no original identity file, or thermal/UART problem: STOP with original logs.** Do not run page test. On success, inspect and save genuine raw original receipt:

~~~bash
scp "ubuntu@10.42.0.135:$REMOTE_DIR/identity.json" "$MMIO_EVIDENCE/03_identity.json"
ID_SHA="$(sha256sum "$MMIO_EVIDENCE/03_identity.json" | cut -d' ' -f1)"
echo "ID_SHA=$ID_SHA"
python3 - "$MMIO_EVIDENCE/03_identity.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
assert d['status']=='PHYSICAL_UIO_READ32_IDENTITY_AND_EMPTY_PAGE_MATCHED'
assert d['identity_words'][:4]==['0x4d303831','0x00010000','0x00000000','0x00000000']
assert d['page_words'][:4]==['0x4d303850','0x00020002','0x00000001','0x00000000']
assert d['page_words'][-1]=='0x00000000'
assert d['physical_256byte_page_written'] is False
print('M08_IDENTITY_VALUES_MATCH_OWNER_REVIEW_CANDIDATE')
PY
(cd "$MMIO_EVIDENCE" && sha256sum 00_context.txt 01_identity_original.log 02_identity_exit.txt 03_identity.json > 99_identity_sha256.txt)
~~~

The first physical identity success is **pending independent acceptance of this owner evidence**. Build tag is default ZERO, not bitstream authentication. UIO cannot expose AXI RRESP.

## M08.2b.4 — Page write/read/COMMIT (separate mode, after identity accepted)

Source is prepared and uses the tested m08_uio_page_protocol.stage_and_compare with **exactly 64 nontrivial little-endian 32-bit words** and logical id 0x4D080201. It demands the **SHA-pinned original identity.json**, rereads fresh identity and EMPTY status, uses aligned native uint32 stores for FULL WSTRB, checks loaded count=256, independently rereads all 64 words and only then COMMIT. Requires READY/valid and correct resident id. No DISPATCH, DDR or DMA.

**DO NOT BLINDLY RUN UNTIL THE GENUINE M08.2b.3 IDENTITY RESULT HAS BEEN INDEPENDENTLY REVIEWED AND ACCEPTED**, and the board is still safe. New explicit physical page write authorization required. A failed write may leave LOADING/poison: STOP, no retry without a separately verified reset/reload.

~~~bash
ssh -tt ubuntu@10.42.0.135 "sudo env M08_EXPLICIT_PHYSICAL_TEST_APPROVED=YES M08_EXPLICIT_PAGE_WRITE_APPROVED=YES timeout --kill-after=3s 30s python3 '$REMOTE_DIR/m08_kv260_physical_uio_operator.py' --mode page --acknowledge-axi-read-risk --acknowledge-axi-write-risk --acknowledge-rollback-not-yet-exercised --identity-evidence '$REMOTE_DIR/identity.json' --identity-evidence-sha256 '$ID_SHA' --output-file '$REMOTE_DIR/page.json'" 2>&1 | tee "$MMIO_EVIDENCE/04_page_original.log"
PAGE_RC=${PIPESTATUS[0]}
printf 'exit_status=%s\n' "$PAGE_RC" > "$MMIO_EVIDENCE/05_page_exit.txt"
echo "PAGE_RC=$PAGE_RC"
~~~

If successful ONLY:

~~~bash
scp "ubuntu@10.42.0.135:$REMOTE_DIR/page.json" "$MMIO_EVIDENCE/06_page.json"
python3 - "$MMIO_EVIDENCE/06_page.json" <<'PY'
import json,sys
x=json.load(open(sys.argv[1]))
assert x['status']=='PHYSICAL_UIO_64_WORD_READBACK_MATCHED_AND_COMMIT_READY'
assert x['transaction']['words_compared']==64
assert x['transaction']['bytes_compared']==256
assert x['transaction']['readback_sha256_little_endian']==x['expected_pattern_little_endian_sha256']
assert x['dispatch_attempted'] is False
assert x['axi_rresp_bresp_directly_observed'] is False
print('M08_PHYSICAL_PAGE_256B_COMMIT_REVIEW_CANDIDATE')
PY
(cd "$MMIO_EVIDENCE" && sha256sum 00_context.txt 01_identity_original.log 02_identity_exit.txt 03_identity.json 04_page_original.log 05_page_exit.txt 06_page.json > 99_complete_sha256.txt)
tar -C "$MMIO_EVIDENCE" -czf "$MMIO_EVIDENCE.tar.gz" .
echo "MMIO_EVIDENCE_ARCHIVE=$MMIO_EVIDENCE.tar.gz"
~~~

**After COMMIT the page is READY and subsequent tests MUST NOT rerun writing in-place**. Physical success is the staged page only. A kernel hang, SIGBUS, hidden UIO BRESP or injected driver fault cannot be automatically recovered. No neural inference from this compute-disabled PL image. Owner original evidence + independent review required before closing both submilestones or progressing to hardware compute.
