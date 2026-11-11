# M08.2b.4a — genuine KV260 PS→safe-page post-route hardware implementation

**Status 2026-11-11:** Source tools and synthetic rejection tests implemented; new original native Vivado **synthesis/route has NOT been run by the owner yet**. M08.2b.3's native dual-slave *BD-only* acceptance is recorded independently in [M08.2b.3 review](M08_2B_3_NATIVE_BD_ACCEPTANCE_REVIEW_2026_11_11.md).

## Hardware boundary and why routing first

The accepted M08.2b.3 real Vivado 2025.2 design uses K26 KV260 SOM, board-preset PS PL0 output 99,999,001 Hz, HPM0 FPD -> 1×2 SmartConnect -> **two** 4 KiB peripherals:

- read-only M08 identity at owner-verified native BD offset `0xA0000000`;
- M08 signed16 **256-byte** host-staged state page at `0xA0001000`, with `ENABLE_COMPUTE=0` so DISPATCH cannot falsely start an engine-less page.

Those addresses are original *design mappings*, **not** proof that Linux owns a usable `/dev/mem` mapping or that any PL image is installed. Do **not** use them for OS memory access until a new bitstream/XSA, Linux mappings/security policy and physical address proof are reviewed. Existing Loihi P08's successful KV260 route provides a methodology precedent (generate BD targets/wrapper, run `impl_1` through `route_design`, report actual timing/utilization/DRC, then consciously decide bitstream) **not** permission to reuse Loihi bitstreams, context banks, VIO or signed24 compute.

To prevent unsafe automatic programming, M08.2b.4 is split:
- **M08.2b.4a — route-only trial now:** real K26 synth/implementation, nonnegative measured setup/hold path slacks, clock presence, utilization, DRC, methodology and post-route checkpoint, source/evidence audit. This stage **does NOT** write a bitstream or XSA, access a board or issue a DMA request.
- **M08.2b.4b — later, gated:** investigate original routing DRC, unconstrained-path warnings, resource/timing adequacy; only after those pass, implement a separately reviewed bitstream/XSA release procedure with original SHA, board profile and safe deployment plan. Do **not** silently infer that WNS/WHS >= 0 means DRC and unconstrained paths are acceptable.

## New source artifacts

| Source | Purpose |
| --- | --- |
| `scripts/m08_page_post_route_candidate.tcl` | Start NEW Vivado 2025.2 K26 project, `source` the exact already accepted `m08_page_ps_bd_candidate.tcl` to recreate PS clock/reset and two slaves (not import a prior project); generate top wrapper, call `launch_runs impl_1 -to_step route_design` with dependent synthesis, wait for completion; save timing/utilization/DRC/methodology/clock reports and an actual DCP; require real nonnegative setup/hold timing and at least one routed timing clock. Never `write_bitstream`. |
| `scripts/run_m08_page_post_route.sh` | Refuse wrong/missing Vivado, bound jobs 1–8, create **exclusive** original evidence dir in `~/Thesis_Evidence/M08`, record exact **ten** source SHA rows before/after, original vendor exit status and log, run independent source/output audit, and emit a separate original receipt ledger. Never edits M08.2b.3 original folders. |
| `scripts/m08_page_post_route_audit.py` | Require unchanged ten-file exact source manifest, real original PS BD readback, distinct mapped regions, emitted vendor markers, complete synth/route and nonnegative WNS/WHS, clocks, reports and DCP, no falsified bitstream/physical claims; returns an *evidence-consistency-only* receipt with an explicit **DRC/unconstrained-path review still required**. |
| `tests/test_m08_page_post_route_candidate.py` | Check new Tcl ordering and no unsafe `write_bitstream`, bash/Tcl syntax, and synthetic receipt mutation negatives (missing vendor marker, address overlap, negative slack, false physical claim, lost original DCP, changed source manifest). **Synthetic is not vendor proof.** |

**No original M08.2b.3 BD source/Tcl/runner/auditor was changed by this stage.** The seven-checked-source accepted owner evidence remains independently reproducible at its original SHA. New route source includes those seven immutable files and adds only the three route tools.

## Phase A — development-PC source tests (no native Vivado execution)

~~~bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
git status --short
git fetch origin
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-kv260-bringup
git rev-parse HEAD
python3 -m compileall -q src scripts tests
bash -n scripts/run_m08_page_post_route.sh
python3 -m unittest discover -s tests -p 'test_m08_page_post_route_candidate.py' -v
python3 -m unittest discover -s tests -p 'test_m08_page_ps_bd_candidate.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -p 'test_m07*.py' -v
python3 -m unittest discover -s tests -v
~~~

M01–M08 current-SHA GitHub Actions must be independently green. If the new tests fail, do not proceed to Vivado; preserve exact source error. **The preceding owner BD approval is not automatically a route PASS.**

## Phase B — ONE fresh original offline Vivado synth/route trial

This runs only on the development PC. **No FPGA should be programmed.** It may be resource-intensive; default `M08_ROUTE_JOBS=4`, tunable to 1–8 according to actual PC memory/CPU. A new failure is a preserved first routing experiment, not evidence to alter old accepted folders.

~~~bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
source /home/dna/Vivado/2025.2/Vivado/settings64.sh
vivado -version
mkdir -p "$HOME/Thesis_Evidence/M08"

CONSOLE="$(mktemp "$HOME/Thesis_Evidence/M08/m08_2b_4_route_console_XXXXXXXX.log")"
set +e
M08_ROUTE_JOBS=4 bash scripts/run_m08_page_post_route.sh 2>&1 | tee "$CONSOLE"
RUN_EXIT=${PIPESTATUS[0]}
set -e
echo "M08_2B_4_ROUTE_EXIT=$RUN_EXIT"

D="$(sed -n 's/^M08_ROUTE_EVIDENCE_DIR=//p' "$CONSOLE" | head -n 1)"
echo "M08_2B_4_ROUTE_EVIDENCE_DIR=$D"
test -n "$D" && test -d "$D" || { echo "Missing original route evidence dir"; exit 2; }
ls -lah "$D"
cat "$D/result.txt"
cmp "$D/source_sha256_before.txt" "$D/source_sha256_after.txt"
sha256sum -c "$D/source_sha256_after.txt"
grep -nE 'M08_|ERROR:|CRITICAL WARNING:|WARNING:' "$D/01_vivado_impl.log" || true

if [[ "$RUN_EXIT" == 0 ]]; then
    cat "$D/02_vivado_page_bd_readback.txt"
    cat "$D/04_implementation_metrics.txt"
    python3 -m json.tool "$D/11_m08_route_independent_audit.json"
    sha256sum -c "$D/12_evidence_sha256.txt"
    grep -nEi 'unconstrained|critical|error|violation|timing' \
      "$D/05_timing_summary_post_route.rpt" "$D/07_drc_post_route.rpt" \
      "$D/08_methodology_post_route.rpt" | head -n 100 || true
else
    echo "M08_2B_4_NATIVE_ROUTE_FAILED — preserve original error + logs"
fi
~~~

Evidence folder creates `result.txt`, original `01_vivado_impl.log`, `02` PS page BD readback, `03` Vivado BD Tcl export, `04` route metrics, `05` post-route min/max timing, `06` utilization, `07` DRC, `08` methodology, `09` clocks, `10_m08_page_post_route.dcp` (may be large), before/after source SHA, and (only on native PASS) `11` independent audit JSON + `12` SHA receipt.

**Owner evidence to share on success:** original `result.txt`, `01_vivado_impl.log`, `02_vivado_page_bd_readback.txt`, `04_implementation_metrics.txt`, `05_timing_summary_post_route.rpt`, `06_utilization_post_route.rpt`, `07_drc_post_route.rpt`, `08_methodology_post_route.rpt`, `09_clock_utilization_post_route.rpt`, `11_m08_route_independent_audit.json`, `12_evidence_sha256.txt`, `source_sha256_before/after.txt` and entire wrapper-console exit/markers. Upload the `03` exported Tcl if the BD/error diagnosis requires it. **Do not upload the potentially large `10` DCP unless requested**; preserve it immutable on PC and verify its receipt digest. On failure, share `result.txt`, original `01` vendor log, before/after SHA and any generated `04..09` reports. Never clean the old evidence or silently modify a failed folder.

## Scope-bounded acceptance

A **source-level candidate PASS** needs genuine GitHub/owner Python/Tcl checks, not dummy fixture acceptance. **Native M08.2b.4a routing** is accepted only after original vendor completion and digest-checks, original **nonnegative setup and hold slack**, constraint/unconstrained-path review, and inspection of DRC/methodology, timing and utilization reports for actual implementation blockers. The initial audit explicitly returns `ORIGINAL_OWNER_M08_KV260_ROUTE_EVIDENCE_CONSISTENT_DRC_REVIEW_REQUIRED`, not a final routed-hardware release decision.

Even a clean routed PS-only safe page does not execute signed16 spikes or give the PS DDR ownership. A future M08.2b.4b bitstream and M08.4 operator-validated real PS→PL page access will be separately gated; full M06 HLS and device-bound Linux DMA are later independent deliverables.
