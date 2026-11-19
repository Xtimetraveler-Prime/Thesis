# M08 D3.2 passive KV260 implementation — route-only owner PC workflow

**Status:** source + synthetic negatives developed; genuine new owner Vivado 2025.2 route pending. **NO bitstream or physical board activity permitted.** This is a D3.2 engineering step, **not a new milestone**.

## Synthesis evidence accepted for routing preparation

Owner's independent source/native audit of `/home/dna/Thesis_Evidence/M08/m08_d3_2_passive_synth_z6PIsrwZ` reports native `synth_design Complete!`, 100%, KV260 SOM board part 1.4, HPM/SmartConnect/identity/page absent, fan output A12/LVCMOS33, `bitstream=NOT_GENERATED`. Uploaded console warnings: many unrelated `[Board 49-26]` entries for other board parts; `[Vivado 12-7122]` standard fallback with no incremental checkpoint; `[Synth 8-7071]` unconnected PS PL0 clock and reset; `[Synth 8-7023]` PS instance 5 ports/2 connections; `[Synth 8-7129]` unused lower TTC slice bits. These are **consistent with the passive no-clocked-AXI fan-only design** and **not independently proved benign electrically**; review them again on route. No errors/critical warnings were in the uploaded grep text. Actual route DRC and timing **not yet reviewed or proven**.

**The old `z6PIsrwZ` evidence MUST NOT be modified.** The route runner invokes the existing synthesis-only runner again to create a **fresh** different `m08_d3_2_passive_synth_XXXXXXXX` folder; only this new run is subsequently reopened for `impl_1 -to_step route_design`.

## New files

- `scripts/m08_d3_2_passive_route_only.tcl`: checks new synthesis report, K26 part/board, all HPM master disables, forbidden cells and fan route; launches Vivado `impl_1 -to_step route_design` only, not `write_bitstream`. Creates routed timing, DRC, utilization, clock, summary files `40...`–`44...` with `NOT_A_PASS_CLAIM` report statuses. Fails before route if prior source is unsafe.
- `scripts/m08_d3_2_passive_route_gate.py`: fail-closed PC source/synthetic evidence checker; optionally reads new route report, requires no bitstream claim, explicitly marks DRC/route and physical safety **not independently accepted**. Doesn't invoke Vivado or touch hardware.
- `scripts/run_m08_d3_2_passive_route_pc.sh`: builds **fresh** D3.1/no-AXI fan-only project, runs fresh synth, validates original 99 receipt, then routes **that new run only**; records separate `98_route_evidence_sha256.txt`. Never changes historical synth evidence and never programs or packages hardware.
- `tests/test_m08_d3_2_passive_route_gate.py`: source negatives for HPM, fan, forbidden implementation steps/bitstream, mock route reports, symlink and Tcl/bash syntax.

## Owner VS Code commands — PC ONLY

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-d3b-boot-ownership-audit
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-d3b-boot-ownership-audit
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m08_d3_2_passive_route_gate.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/m08_d3_2_passive_route_gate.py
bash -n scripts/run_m08_d3_2_passive_route_pc.sh
```

If source tests and same-head CI pass, run Vivado **on PC**, not on KV260:

```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
source /home/dna/Vivado/2025.2/Vivado/settings64.sh
vivado -version
bash scripts/run_m08_d3_2_passive_route_pc.sh
```

After successful completion, terminal prints:

`M08_D3_2_PASSIVE_ROUTE_PC_REPORTS_CAPTURED_REVIEW_REQUIRED_NO_BITSTREAM_NO_BOARD=<NEW_RUN>`

Use the **actual** new path in the receipt checks below:

```bash
RUN="$HOME/Thesis_Evidence/M08/m08_d3_2_passive_synth_<REPLACE_WITH_NEW_SUFFIX>"
(cd "$RUN" && sha256sum -c 99_evidence_sha256.txt)
(cd "$RUN" && sha256sum -c 98_route_evidence_sha256.txt)
python3 scripts/m08_d3_2_passive_route_gate.py --native-run-dir "$RUN"
cat "$RUN/output/40_passive_route_readback.txt"
sed -n '1,140p' "$RUN/output/41_passive_route_timing.rpt"
sed -n '1,140p' "$RUN/output/42_passive_route_drc.rpt"
sed -n '1,100p' "$RUN/output/44_passive_route_clocks.rpt"
grep -nE 'ERROR:|CRITICAL WARNING:|WARNING:' "$RUN/05_passive_route_vivado.log" || true
```

**Do not interpret `route_design Complete!` as route timing/DRC PASS.** If DRC has violations, clocks are unconstrained, fan pin disappears, or physical implementation fails, STOP; preserve the new logs, source SHA and first error. The resulting implemented project is not a safe-to-program or boot image. No `.bit`, `.dtbo`, PS clock/AFI/ATB/AIB or physical MMIO authorization is provided.

## After routing

Review actual routed WNS/TNS and hold slack, DRC, unconstrained paths, fan port A12/IOSTANDARD, original PS fan route and distinct clock ownership. Before considering **a new passive bitstream**, require independently verified cooling, rollback and explicit user hardware approval. A protected HPM0 Linux-accessible design remains blocked by original XSA/boot evidence, ATB4/AIB13 and driver readiness. No old failed M08 image may be used again.
