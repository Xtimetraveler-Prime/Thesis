# P07-B.4g / B.4h — Non-Halting XSDB Shell Snapshot and Offline Correlation

**Current state (2026-10-21):** B.4f user-native accepted via conversation. Real B.4c Vitis AArch64 ELF + genuine map user-rehashed and source/ELF offline audit verified, but **NOT** downloaded to KV260. B.4g/h additive code and synthetic native gate implemented; **user native verification pending; actual XSDB capture NOT RUN**. PR #49 stays draft/unmerged; no accepted Track A/B/P03/P05 changes or B2 official MNIST TEST unseal.

## Purpose

This is the *next physical-observation stage* and is deliberately split into two independent parts:

**B.4g** prepares the optional operator-triggered, non-halting PS/PL shell observation. It does not run `dow`, stop/reset/resume any Cortex-A53, program the FPGA, read/write the reserved 64MiB P02 DDR, dispatch neurons or access MNIST. This is *less intrusive than* accepted older P03.2c diagnostic scripts, which stopped A53 and provisioned DDR fixture data. The user must retain a normal recovery plan and know whether another Linux/XSDB/Vivado process currently controls JTAG. Connecting a debugger, **even just to read**, is still a physical operation that requires active board control and acceptance.

**B.4h** is a separate **host-only transcript review**. It correlates the full B.4f user-local actual-toolchain offline JSON, SHA256 of the real ELF/map/XSA/BIT, and the raw B.4g six-register XSDB text. It never automatically connects to hardware or declares that an unauthenticated text transcript proves a live board state. Even a valid B.4h receipt leaves **physical A53 ELF download and inference unauthorized**.

### Code changes

- `vivado/p07_b4g_readonly_shell.tcl`: standalone XSDB Tcl script requiring explicit literal `READ_ONLY_OPERATOR_APPROVED` argument and localhost XSDB server URL. Selects PSU/APU *physical memory* target and issues exactly six `mrd -force -value -size w ADDRESS 1` **reads**. The AMD XSDB 2025.2 `-value` option returns Tcl values rather than output-formatted console strings; avoids fragile earlier B.4d regexp parse. Exact accepted values: FPD_SLCR.afi_fs (0xFD615000) dw_ss0_sel [9:8]==2; P03 ID (0xA4000000)==0x4C543302; version (0xA4000004)==0x00010000; caps (0xA4000008)==0x0001031F; global status (0xA400000C)==0; pending bytes (0xA4000054)==0. Parses 32-bit values, rejects missing/invalid read, and disconnects even on mid-read failures. Prints unambiguous `P07_B4G_...` markers and `INFERENCE_AUTHORIZED=0`. Does **NOT** prove the loaded BIT matches a specific host file SHA by itself.
- `scripts/p07_b4h_review_shell_capture.py`: offline correlation. Requires `p07-b4f-offline-physical-launch-readiness-v1` manifest, no inferred board/ELF launch permission, unchanged pinned REAL ELF/MAP/XSA/BIT, explicit actual operator-reported KV260 state (`linux_running|standalone|unknown`) and BIT provenance (`observed|independently_accepted`). Rejects duplicate/missing XSDB markers, explicit FAIL, wrong FPD select, busy/pending/nonmatching P03 shell registers. Produces SHA256 of raw log, an optional receipt JSON **outside Thesis repository**, and explicit `XSDB_log_origin_authenticated=false`, `low_DDR_ownership_verified=false`, `physical_inference_authorized=false`. It is not a substitute for live JTAG provenance.
- `tests/test_p07_b4gh_readonly_pilot.py`, `.github/workflows/p07_b4gh_native.yml`: uses **host `tclsh` with fake XSDB commands** for all six reads, cleanup/error branches, remote-host rejection and explicit operator opt-in; Python synthetic ELF/XSA/BIT fixtures exercise text tampering and rehash rejection. CI fake XSDB PASS is never a real physical measurement.

### User-native verification first (NO board access)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p07-b-scaled-physical-inference
git pull --ff-only origin agent/v3-p07-b-scaled-physical-inference
git rev-parse HEAD
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
command -v tclsh
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b4gh_readonly_pilot.py
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b4f_physical_launch_safety.py \
  tests/test_p07_b4d_readonly_evidence.py \
  tests/test_p07_b4c_build_admission.py \
  tests/test_p07_b4b_elf_probe_admission.py
```

**Stop at this checkpoint to report native results before planning any physical memory ownership changes.**

### Stage 1 — User-local real offline audit saved for B.4h (NO XSDB)

The user says B.4f is verified; if the previous B.4f audit was printed without `--json-out`, the following re-runs it on the same immutable already built ELF/map and writes a new *out-of-repository* receipt. No board accessed:

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
source /home/dna/Vivado/2025.2/Vitis/settings64.sh
export PATH="/home/dna/Vivado/2025.2/gnu/aarch64/lin/aarch64-none/bin:$PATH"
export P07_B4G_EVIDENCE_DIR="$HOME/p07_b4g_readonly_$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -m 700 "$P07_B4G_EVIDENCE_DIR"
export P07_B4C_BUILD_DIR="/home/dna/p07_b4c_real_linkmap_20261021T181921Z"
export P07_B4G_REPORTS="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports"
export P07_B4G_ELF="$P07_B4C_BUILD_DIR/vitis_workspace/p07_b4c_readonly_probe.elf"
export P07_B4G_MAP="$P07_B4C_BUILD_DIR/vitis_workspace/p07_b4c_readonly_probe.map"
python scripts/p07_b4f_physical_launch_safety.py \
  --build-dir "$P07_B4C_BUILD_DIR" \
  --xsa "$P07_B4G_REPORTS/p03_2_ps_mmio.xsa" \
  --bit "$P07_B4G_REPORTS/p03_2_ps_mmio.bit" \
  --ltx "$P07_B4G_REPORTS/p03_2_ps_mmio.ltx" \
  --route-metrics "$P07_B4G_REPORTS/p03_2_post_route_metrics.txt" \
  --xsa-sha256 52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f \
  --bit-sha256 beb7324decacf1c39d1cda97b6f13f347ecb1901a9670e75479f27a669d988a4 \
  --elf-sha256 ba96b4c6afac4dd4d7ceb63f417664da8fda1f482757a0b2b6ce80a8faecf86a \
  --map-sha256 a7b0ac270c92631d1f1a3a39a7af549523770cde031a998935b6bc000fdd7b02 \
  --bit-provenance observed \
  --json-out "$P07_B4G_EVIDENCE_DIR/b4f_actual_elf_audit.json"
```

Successful audit marker: `P07_B4F_OFFLINE_LAUNCH_SAFETY_AUDIT_PASS_NO_BOARD_GO=1`. **A matching hash does not independently prove the BIT's prior physical acceptance**; keep provenance `observed` until separately reconciled.

### Stage 2 — OPTIONAL operator-run XSDB read-only six-register snapshot

Only when the operator has established that the KV260 is accessible on JTAG, understands its **current Linux/boot/PL state**, knows the relevant shell is expected to be programmed already, owns the JTAG session, and agrees that reading static PS/PL registers is appropriate. **No instructions here authorize `dow`, `stop`, `rst`, `con`, `mwr`, or bitstream programming.** If unknown, stop and inspect the state before running XSDB.

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
command -v xsdb
set -o pipefail
# Deliberate operator acknowledgment; NO ELF downloaded.
xsdb vivado/p07_b4g_readonly_shell.tcl READ_ONLY_OPERATOR_APPROVED \
  tcp:127.0.0.1:3121 \
  2>&1 | tee "$P07_B4G_EVIDENCE_DIR/readonly_xsdb_raw.log"
```

If this returns an XSDB error (including no PSU/APU target, PL shell unavailable, missing/changed ID, nonzero busy or FPD64), **stop**. Do **not** attempt to fix it by programming a new BIT, halting Linux or trying an ELF download. Keep the raw log and board state notes. A successful textual snapshot still does not verify the physical bitstream SHA.

### Stage 3 — Review the collected log OFFLINE (NO hardware)

After collecting a successful B.4g log, choose the *observed* actual current boot state (unknown is allowed). Example assumes the boot state remains unknown:

```bash
python scripts/p07_b4h_review_shell_capture.py \
  --audit "$P07_B4G_EVIDENCE_DIR/b4f_actual_elf_audit.json" \
  --transcript "$P07_B4G_EVIDENCE_DIR/readonly_xsdb_raw.log" \
  --elf "$P07_B4G_ELF" \
  --linker-map "$P07_B4G_MAP" \
  --xsa "$P07_B4G_REPORTS/p03_2_ps_mmio.xsa" \
  --bit "$P07_B4G_REPORTS/p03_2_ps_mmio.bit" \
  --board-state unknown \
  --bit-provenance observed \
  --json-out "$P07_B4G_EVIDENCE_DIR/b4h_offline_shell_receipt.json"
```

Expected `P07_B4H_OFFLINE_SHELL_LOG_FORMAT_PASS_NOT_PHYSICAL_GO=1` **only if inputs and read-only capture are internally consistent**. Log origin is **not authenticated**. Do **not** run the original B.4d UART+XSDB log checker at this stage, because the new A53 probe **has not been executed and no UART log exists**; B.4h intentionally correlates an XSDB-only snapshot.

### Next stop: low-DDR A53 execution ownership

Default standalone ELF previously reported `entry=0`, physical LOAD `[0,0x23a40)` in low DDR. The script B.4f flags this risk. Reading PS/PL shell is **separate** from writing low DDR and launching A53. Before attempting a standalone ELF download, there must be a separately verified low-DDR exclusive owner, known Linux/FSBL/TF-A/U-Boot/CPU reset plan, a safe actual boot/loader address layout, full MMU/cache policy, current BIT provenance and operator approval. We may relink the ELF **only after selecting a verified safe owned window**, not by assuming a random address is available. Original P03 smoke did halt CPUs and provision DDR, but it is not a safe substitute for this new non-halting stage.

Never modify frozen Track A/B, original P03/P05, unseal B2 official MNIST TEST, or merge PR #49 without separate user authorization.
