# M08.2b — one consolidated KV260 page implementation → bitstream → physical smoke

**2026-11-11 status:** Original owner K26 PS→identity+safe signed16 page RTL, native BD, synthesis and route have PASSED in their correctly bounded scopes. **A new bitstream has NOT yet been generated or programmed**. The next task is the same overall M08.2b hardware-deployment milestone; these checks are **acceptance gates**, not ever-smaller numbered milestones.

## Why this is safe to advance

[Owner original post-route acceptance](M08_2B_POST_ROUTE_ACCEPTANCE_AND_WARNINGS_2026_11_11.md): Vivado 2025.2 K26 part, actual 99,999,001 Hz PS clock, native read-only ID 4 KiB at `0xA0000000` and safe 256B signed16 page 4 KiB at `0xA0001000`, synthesis/route complete. WNS +5.469ns, WHS +0.015ns, zero TNS/THS violations, zero unconstrained internal endpoints, zero methodology findings, 1,957 LUTs and 1,665 FFs. Exactly one **Warning RTSTAT-10** reports 15 SmartConnect internal reset-pipeline nets without routable loads; **14 names** are printed. This is documented and **NOT erased**. The new gate refuses any other DRC rule/severity or changed timing.

The design has **compute DISABLED** until a real signed16 execution engine can be integrated. A bitstream from this checkpoint would demonstrate a *real PS-to-PL AXI page and hardware memory ownership shell*, **not complete neural inference or kernel-owned DDR**.

### Original source and checkpoint provenance

Use ONLY original owner route folder, untouched:

`/home/dna/Thesis_Evidence/M08/m08_2b_4_route_20261111T174620Z_9FLCz7`

The original `10_m08_page_post_route.dcp` SHA in the owner's receipt is `516ded0b2b19352952810b8f2a82f15b9eca02b4757cf53c187d179d051c8673`. This DCP was **not attached** to the research chat; the owner-local preflight rehashes it before use, in addition to verifying all ten original routed-source SHA files, complete original 12-row evidence ledger, the signed original independent audit JSON, original timing/DRC and the corresponding PDF-free plaintext reports. The nine uploaded text artifacts independently matched the provided receipt; missing originals are never claimed verified off-machine.

## Source: four new standalone release tools

- `scripts/m08_page_release_preflight.py` **READ-ONLY** against the original route directory. Re-runs the accepted original `m08_page_post_route_audit.py` against the exact CURRENT checkout, independently verifies all 11 original file digests from `12_evidence_sha256.txt` (including actual DCP), requires 0 failing timing endpoints and **0 unconstrained internal endpoints**, validates WNS/WHS against the timing summary, one exactly documented RTSTAT-10 SmartConnect warning, and 0 methodology findings. Verifies no missing/short originals or unexpected black boxes. Returns a release preflight JSON in the **new** release folder only.
- `scripts/m08_page_bitstream_candidate.tcl` opens the original routed DCP using AMD Vivado `open_checkpoint` (no new synthesis or source alterations), validates K26 part/PS wrapper top and native clock/timing, **reruns `report_drc`** and stops unless exactly the documented RTSTAT-10 Warning reappears, then uses `write_bitstream`. Does not waive warnings or call Hardware Manager. A new native bitstream failure is preserved as such.
- `scripts/run_m08_page_bitstream.sh` demands operator's explicit `M08_ACCEPT_RTSTAT10=YES` after reading the original DRC, requires native Vivado 2025.2 on the PC, and creates a fresh **exclusive** original `m08_2b_bitstream_*` folder. Pins 14 source SHA rows before/after; runs preflight, original vendor tool, independent output auditor and new receipt. Never edits any M08.2a/.3/route history.
- `scripts/m08_page_bitstream_audit.py` independently checks the original preflight and immutable owner route, actual Vivado output markers, native .bit size and SHA256, reopened-checkpoint timing/DRC, all source SHA and no fake claims of board programming, MMIO, DDR or signed16 inference. **It is NOT a physical board signoff**.

`tests/test_m08_page_bitstream_release.py` adds source safety, bash/Tcl syntax and synthetic tamper rejection for changed timing/clock/unconstrained/DRC/original SHA. It deliberately does NOT pretend to run Vivado or generate a real bitstream.

## Phase 1: development-PC source/CI gate (NO native Vivado required)

~~~bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
BRANCH="agent/neuromorphic-accelerator-v1-m08-kv260-bringup"
git status --short
test "$(git branch --show-current)" = "$BRANCH"
git fetch origin
git pull --ff-only origin "$BRANCH"
git rev-parse HEAD
python3 -m compileall -q src scripts tests
bash -n scripts/run_m08_page_bitstream.sh
python3 -m unittest discover -s tests -p 'test_m08_page_bitstream_release.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -p 'test_m07*.py' -v
python3 -m unittest discover -s tests -v
~~~

The exact current commit and all eight M01–M08 GitHub Actions should be verified before new original native output is considered acceptable.

## Phase 2: new owner Vivado offline bitstream and immutable receipt

**Read** `07_drc_post_route.rpt` from the original route folder. Confirm one RTSTAT-10 Warning, internally scoped to `ctrl_sc`, and zero errors/critical warnings. Only then intentionally acknowledge that known warning for this controlled **PS-only** release. Do not set any `DONT_TOUCH`, `-waive` or severity downgrade to hide issues.

~~~bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
source /home/dna/Vivado/2025.2/Vivado/settings64.sh
vivado -version
mkdir -p "$HOME/Thesis_Evidence/M08"

export M08_ROUTE_EVIDENCE_DIR="$HOME/Thesis_Evidence/M08/m08_2b_4_route_20261111T174620Z_9FLCz7"
grep -A30 'RTSTAT-10#1' "$M08_ROUTE_EVIDENCE_DIR/07_drc_post_route.rpt"
# The preflight will read/rehash this immutable original DCP and ALL old
# reports from your PC; it will never modify the route evidence folder.
sha256sum "$M08_ROUTE_EVIDENCE_DIR/10_m08_page_post_route.dcp"
sha256sum -c "$M08_ROUTE_EVIDENCE_DIR/12_evidence_sha256.txt"

CONSOLE="$(mktemp "$HOME/Thesis_Evidence/M08/m08_bitstream_console_XXXXXXXX.log")"
set +e
M08_ACCEPT_RTSTAT10=YES \
    bash scripts/run_m08_page_bitstream.sh 2>&1 | tee "$CONSOLE"
RUN_EXIT=${PIPESTATUS[0]}
set -e
echo "M08_BITSTREAM_RUN_EXIT=$RUN_EXIT"

D="$(sed -n 's/^M08_BITSTREAM_EVIDENCE_DIR=//p' "$CONSOLE" | head -n 1)"
echo "M08_BITSTREAM_EVIDENCE_DIR=$D"
test -n "$D" && test -d "$D" || { echo "No release evidence folder"; exit 2; }
cat "$D/result.txt"
ls -lh "$D"
cmp "$D/source_sha256_before.txt" "$D/source_sha256_after.txt"
sha256sum -c "$D/source_sha256_after.txt"
grep -nE 'M08_|ERROR:|CRITICAL WARNING:|WARNING:' "$D/02_vivado_bitstream.log" || true

if [[ "$RUN_EXIT" == 0 ]]; then
    python3 -m json.tool "$D/01_release_preflight.json"
    python3 -m json.tool "$D/07_m08_bitstream_independent_audit.json"
    cat "$D/06_bitstream_native_metrics.txt"
    sha256sum -c "$D/08_evidence_sha256.txt"
    sha256sum "$D/05_m08_safe_page.bit"
else
    echo "M08 original offline bitstream failed; preserve and upload vendor log"
fi
~~~

Expected success markers **only if genuine vendor run succeeds**, never guessed:
`M08_ROUTE_REPORTS_REVIEWED_RTSTAT10_DOCUMENTED_NO_BITSTREAM_YET`,
`M08_PAGE_RELEASE_CHECKPOINT_TIMING_AND_DRC_RECHECKED=1`,
`M08_PAGE_GENUINE_OFFLINE_BITSTREAM_EMITTED_NOT_PROGRAMMED`,
`M08_OFFLINE_BITSTREAM_SHA_AND_NATIVE_VENDOR_RECEIPT_AUDITED_NO_BOARD`,
`M08_OFFLINE_KV260_SAFE_PAGE_BITSTREAM_AND_SOURCE_RECEIPT_AUDITED`.

The new original folder will contain:
`01_release_preflight.json`, `02_vivado_bitstream.log`, `03_rechecked_drc.rpt`, `04_rechecked_timing.rpt`, **`05_m08_safe_page.bit`**, `06_bitstream_native_metrics.txt`, `07_m08_bitstream_independent_audit.json`, `08_evidence_sha256.txt`, `result.txt`, and two source SHA manifests.

If the native tool fails, do **not** modify this folder or rerun into it. Share the original new `02` Vivado log, `result.txt` and before/after hashes and any generated DRC/timing evidence. If successful, share `01,02,03,04,06,07,08`, `result`, source SHA and `sha256sum 05_m08_safe_page.bit`. The binary bitstream may be large; preserve it locally, **don't upload it unless requested**. No user or assistant should infer a successful bitstream without these originals.

## Phase 3: controlled, separate physical KV260 gate (NOT automatic)

No software in this phase programs a board. The next operator-specific test—**after** a verified genuine new M08 bitstream—should obtain a fresh **READ-ONLY** hardware inventory from the *actual* KV260 Linux/serial image and Vivado JTAG device identity and determine how PS configures PL0 clock, resets, firmware and region management. Prefer the user's proven working KV260 board workflow, **not** Loihi's previous bitstream or an assumed device tree. Capture `/proc/device-tree/model`, `/proc/cmdline`, `/etc/os-release`, `uname -a`, read-only `xmutil listapps` if present, and known `/proc/iomem` ranges with care about host permissions.

Once the actual board image, PS register ownership, board-app PL overlay, and access method have been explicitly reviewed, stage the M08 .bit through a **manual, operator-controlled** programming method and inspect PS-to-PL identity first, then 64-word real signed16 page staging/load/readback, dirty save/replacement and host/compute exclusion behavior. It is unsafe to assume an address printed in Vivado (e.g. `0xA0001000`) is automatically accessible in Linux without a matching device-tree/driver binding and a live programmed PS→PL fabric. `xmutil unloadapp` changes the active board image and is **not** part of these source scripts. No automatic flash/boot firmware changes, raw memory writes or DDR operations are authorized by an offline .bit alone.

**Single M08.2b completion criterion:** actual placed/routed + provenance-checked .bit, controlled live KV260 PS→PL ID and 256B page roundtrip, verified no alias/unsafe commands, captured byte-accurate logs and original physical evidence. M06 full neural engine and DDR are later, explicitly separate integration goals.
