# M08 D3.D.2C — real M06 32-neuron ×4-tick FPGA neural workload (staged; NO BOARD)

## EXACT OWNER NATIVE PASSED — ONE-SHOT PHYSICAL TEST ARMED (2026-11-20 14:34 MST)

The owner reran the new exact-image read-only `m08_d3d2c_m06_native_review.py` against original `~/Thesis_Evidence/M08/m08_d3d2c_m06_MN2pwduB` and supplied **status `M08_D3D2C_EXACT_OWNER_NATIVE_M06_32_IMAGE_ACCEPTED_NO_BOARD` with exit 0**, candidate SHA256 `244d304a44af6b1eda1943c18e7b5a3bed302cae2308c28a11944ede7eadf932`, 7,797,842 bytes, original 12/12 SHA verified, seven exactly reviewed XSDB/JTAG warnings and clean WNS +2.675ns / WHS +0.010ns timing. This is owner-original evidence, **not** an assistant-local direct filesystem check and **not** a physical test.

The independently protected JTAG shell/Tcl now pin exactly this accepted image/size and require **two explicit owner arming flags** (`M08_D3D2C_ALLOW_PROGRAM=YES` and `M08_D3D2C_PREFLIGHT_CONFIRMED=YES`), independently revalidate the exact original native gate before any JTAG and before creating a hardware folder, and validate K26 device identity prior to the **single** `program_hw_devices $fpga` invocation. They compare every 32-neuron×4-tick voltage (128 values), spike-mask decision (128 bits) and fabric-delivered recurrent current (128 values) to the independent original M06 dense/event/M03 oracle. The 17 external input events are **coalesced on the host**; no M06 DDR, streamed event-ingestion, Linux PS MMIO or sparse hardware skipping is claimed.

### Mandatory physical preflight — do not program if any condition is false

**Owner manual confirmation only:** The KV260 is recoverable to its stock boot, powered normally, independently actively cooled (fan power verified independently of PL), UART is connected and terminal log capture running, USB/JTAG is stable, Vivado 2025.2 is installed, previous hardware programming isn't running, no competing GUI Hardware Manager or other JTAG client owns the cable, exact expected K26 serial target/device is visible or has been verified previously, and the user accepts that programming PL may interrupt current functionality. Keep the original evidence folders untouched. If any item is uncertain, STOP; do not set the preflight flag.

**Local code/real original image checks before programming:**

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-d3d2c-m06-32-neuron
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-d3d2c-m06-32-neuron
cd Neuromorphic_Accelerator/v1
export PYTHONDONTWRITEBYTECODE=1
python3 -m unittest discover -s tests -p 'test_m08_d3d2c_m06_physical_boundary.py' -v
python3 -m unittest discover -s tests -p 'test_m08_d3d2c_m06_physical_audit.py' -v
python3 -m unittest discover -s tests -p 'test_m08_d3d2c_owner_native_review.py' -v
python3 -m unittest discover -s tests -p 'test_m08_d3d2c_owner_native_receipt.py' -v
python3 -m unittest discover -s tests -p 'test_m08_d3d2c_m06_32_source.py' -v
bash -n scripts/run_m08_d3d2c_m06_physical_once.sh
RUN="$HOME/Thesis_Evidence/M08/m08_d3d2c_m06_MN2pwduB"
(cd "$RUN" && sha256sum -c 99_evidence_sha256.txt)
python3 scripts/m08_d3d2c_m06_native_review.py --run-dir "$RUN"
```

**Only after all local tests, native image review, and manual preflight PASS, execute ONCE:**

```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
source /home/dna/Vivado/2025.2/Vivado/settings64.sh
vivado -version
RUN="$HOME/Thesis_Evidence/M08/m08_d3d2c_m06_MN2pwduB"
M08_D3D2C_ALLOW_PROGRAM=YES M08_D3D2C_PREFLIGHT_CONFIRMED=YES \
  bash scripts/run_m08_d3d2c_m06_physical_once.sh "$RUN"
RC=$?
echo "M08_D3D2C_PHYSICAL_RUN_EXIT=$RC"
```

The one-shot runner prints a **new** `M08_D3D2C_NEW_PC_HW_EVIDENCE=...` folder. Preserve that exact folder and all UART output regardless of results. The runner does NOT retry. On genuine successful board execution it prints `M08_D3D2C_HARDWARE_M06_32X4_RECURRENT_M02_PARITY_SUCCEEDED`, exit 0, and the independent physical auditor status `M08_D3D2C_PHYSICAL_M06_32X4_REAL_RECURRENT_M02_PARITY_ACCEPTED`; six hardware SHA files are checked. **Never fabricate these markers, assume hardware success from CI, or program again automatically after a failure.**

**Independent read-only post-run audit (after owner provides the actual new `HW` folder path):**

```bash
HW="<PASTE_EXACT_M08_D3D2C_NEW_PC_HW_EVIDENCE_PATH>"
(cd "$HW" && sha256sum -c 99_evidence_sha256.txt)
cat "$HW/03_exit.txt"
cat "$HW/80_m06_32x4_hw_parity.txt"
python3 scripts/m08_d3d2c_m06_physical_audit.py --run-dir "$RUN" --hw-dir "$HW"
```

Hardware evidence is **not yet available**. The stock recovery procedure remains the fallback if the one-shot experiment fails or the board becomes unresponsive, and the first failure evidence must be preserved before any investigation or recovery. No repeated JTAG programming without a new review.

---


## D3.D.2C TIMING FIX r2 — staged 32-neuron sequential recurrent evaluation (2026-11-20)

**Actual original owner timing evidence:** `m08_d3d2c_m06_RIezhupj` original routed timing: **WNS −0.188 ns, TNS −18.168 ns, 277 setup-failing endpoints, WHS +0.012 ns, THS 0, 0 hold-failing endpoints**. Worst path begins at `lif/inst/spike_mask_reg[6][3]/Q` and ends at `lif/inst/trace_voltage_reg[80][15]/D`; 10.073 ns datapath (4.268 ns combinational logic, 5.805 ns routed nets), 32 logic levels / 14 CARRY8, 10 ns `clk_pl_0` requirement. Other worst paths end in `trace_voltage` banks and share the recurrent-spike source. These are *measured original routes*, not inferred guesses. The read-only diagnostic's five tests passed; timing report original SHA256 `87109eb9f948368493d4f90561a4dd52b6d0269b1c233c40207bbbeb1e0f42c3` and checkpoint originally 12,605,864 bytes. **Never rewrite/reuse that failed directory.**

**RTL fix (new source commit only, NOT new routed timing closure yet):** The eight parallel signed64 synapse contributions and saturated neuron update are no longer computed as one combinational chain between spike history and voltage registers. The 32-neuron RTL now uses a bounded multi-cycle finite state machine for each neuron/tick:

1. `PHASE_ROUTE`: iterate **only configured** active edges, at most eight. One signed16 weight per clock conditionally accumulates into exact signed20 synaptic sum. Delayed spike bits are from completed logical ticks; no same-tick propagation.
2. `PHASE_BASE`: register signed17 `leaked + bias`, preserving 3/4 signed truncation.
3. `PHASE_EXT`: register exact signed34 `leaked+bias+external_current`.
4. `PHASE_TOTAL`: register exact signed34 total after adding signed20 delayed recurrent current.
5. `PHASE_COMMIT`: saturate once to signed16, threshold/spike/reset, store membrane, voltage and sign-extended signed32 recurrent delivered-current trace. Advance neuron and logical tick **only at commit**.

The engine therefore requires **active_edge_count + 5 fabric cycles per neuron per logical tick**, instead of one cycle. The M06 five-edge network nominally takes **10 clocks × 128 neuron/tick evaluations = 1280 fabric clocks**, not including AXI setup. All four logical timesteps, 32 physical neuron state banks, five weighted positive-delay edges, M02/M03 oracle and `M32N` v4 register ABI are unchanged. This is a deliberate throughput-for-timing tradeoff; actual native WNS/TNS, utilization, fmax, throughput and hardware remain **UNVERIFIED** until a new independent owner Vivado run. The previously verified D3.D.2B physical image is unaffected.

**PC-only validation added:** `scripts/m08_d3d2c_m06_gate.py --source-only` now requires distinct pipeline phases and refuses the old monolithic combinational signature. New regression checks confirm staged arithmetic and use an RTL mutation to reject a flipped recurrent weight sign. Real Icarus bench must again compare all **128 voltages, 128 spike decisions and 128 delivered-synaptic-current values** for two independent replay executions against the original M06 fixture. `NO BOARD` safety guard remains, first original DRC and timing review now exactly SHA/pin-backed but locally unconfirmed, and all previous PRs remain drafts.

### Rebuild policy / new hardware phase

HISTORICAL PRE-REVIEW INSTRUCTION, ALREADY COMPLETED (do not repeat): Only once PC tests and GitHub Actions pass, generate **one new** offline Vivado 2025.2 run via `bash scripts/run_m08_d3d2c_m06_pc.sh`; it creates a fresh unique evidence folder under `~/Thesis_Evidence/M08/`. This is **not** a rebuild of the accepted D3.D.2B image or the original failed D3.D.2C folder. No automatic retries; if timing fails again, preserve the folder and extract WNS/TNS/paths. If native route closes and bitstream generates, the pre-review first-image checker historically **intentionally exited 2** pending exact DRC and SHA review; the updated exact-image reviewer now returns 0 ONLY for this pinned owner original. Do not program the KV260 yet.

---

## FIRST ORIGINAL OWNER NATIVE ROUTE — TIMING FAILURE, NOT BITGEN (2026-11-20 11:36 MST)

**New owner evidence (immutable):** `/home/dna/Thesis_Evidence/M08/m08_d3d2c_m06_RIezhupj`. The owner-provided first original Vivado 2025.2 console excerpt shows:

- `route_design completed successfully`, routed checkpoint `project/m08_d3d2c_m06_lif_jtag.runs/impl_1/m08_d3d2c_m06_lif_jtag_wrapper_routed.dcp` was generated. This is useful original placement/routing evidence.
- During automatic post-route `report_timing_summary`, Vivado reported `CRITICAL WARNING: [Timing 38-282] The design failed to meet the timing requirements`. Additional `Timing 38-436` bus-skew advisory calls for independent `report_bus_skew` review. The `Power 33-332` high-fanout reset/vectorless activity advisory concerns **power-estimate accuracy**, not the demonstrated timing root cause.
- The Tcl status check at line 279 of `scripts/m08_d3d2c_m06_build.tcl` rejected `impl_1` because it was not marked `*Complete!*`. This **correctly stopped bitstream generation**. The source-owned `reports/20_route_drc.rpt`, `reports/21_route_timing.rpt`, `reports/30_native_result.txt`, original 12-file SHA ledger and new `.bit` were **not** reached in this run; no physical programming.
- The submitted console excerpt **does not include numerical WNS, TNS, failing endpoint count, detailed startpoint/endpoint, logic-vs-route delay, or exact critical path hierarchy**. Thus it does not establish whether the longest path is recurrence, neuron state selection, AXI readback, reset, or vendor JTAG. Do not change frequency, apply a false timing exception, use D3.D.2B's warning allowlist, or rebuild simply because route_design itself succeeded.
- **Next: diagnose the FIRST original routed design read-only.** Do not rerun build or Vivado at this stage. The latest branch includes `scripts/m08_d3d2c_m06_failed_route_audit.py` and synthetic negative tests. That auditor reads *existing* original routed reports and hash-checks nothing by mutation; it never starts Vivado, opens the device, or writes evidence.

### Original evidence read-only commands — local VS Code terminal

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-d3d2c-m06-32-neuron
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-d3d2c-m06-32-neuron
cd Neuromorphic_Accelerator/v1
export PYTHONDONTWRITEBYTECODE=1

RUN="$HOME/Thesis_Evidence/M08/m08_d3d2c_m06_RIezhupj"
IMPL="$RUN/project/m08_d3d2c_m06_lif_jtag.runs/impl_1"
test -f "$IMPL/m08_d3d2c_m06_lif_jtag_wrapper_routed.dcp"

python3 -m unittest discover -s tests -p 'test_m08_d3d2c_m06_failed_route_audit.py' -v
python3 scripts/m08_d3d2c_m06_failed_route_audit.py --run-dir "$RUN"

# Direct original report excerpts: read only, no rerun of synthesis/routing.
RPT="$IMPL/m08_d3d2c_m06_lif_jtag_wrapper_timing_summary_routed.rpt"
grep -n -A 5 -m 1 'WNS(ns)' "$RPT"
grep -n -A 90 -m 3 'Slack (VIOLATED)' "$RPT"
grep -n -E -m 40 'Source:|Destination:|Path Group:|Path Type:|Data Path Delay:|Logic Levels:|Requirement:' "$RPT" || true
grep -n -E 'VIOLATED|WNS|bus skew' "$IMPL/m08_d3d2c_m06_lif_jtag_wrapper_bus_skew_routed.rpt" | head -n 40 || true
sha256sum "$RPT" "$IMPL/m08_d3d2c_m06_lif_jtag_wrapper_routed.dcp"
```

**Report the exact WNS/TNS and the first one to three worst setup path excerpts** (source/destination, requirement, data path delay, major cells/nets and bus-skew result). This determines whether to pipeline synaptic routing, restructure neuron state selection or fix a distinct AXI/IP path. The source/RTL Icarus PASS remains valid for its bounded model but does not override native timing.

The original `m08_d3d2c_m06_RIezhupj` directory and its failed run status are **immutable**. Any subsequent RTL timing fix must produce a **NEW** distinct native evidence folder with new full DRC/timing review; no original `.dcp`, log, or report gets replaced.

---


**November 20, 2026; new stacked branch based on documented D3.D.2B physical PASS.**

## Why this is a distinct hardware milestone

D3.D.2B original physical owner receipt `~/Thesis_Evidence/M08/m08_d3d2b_synaptic_HW_Pw3KKKXl` independently accepted two four-neuron/eight-edge recurrent networks: **32/32 membrane voltages, 32/32 spike decisions and 32/32 hardware-derived synaptic currents** matched M02; one-shot JTAG, six physical hashes, exit 0. Original bit SHA256 `dae1c4953826317854acd3c61d013b6fddec410a0450002fa13b3ab1f1650d14`. **Do not rebuild or reprogram that image.**

D3.D.2C is NEW RTL and a NEW image: 32 stateful signed16 LIF neurons, four ticks, the **actual accepted M06 G3.3 32×4 fixture**, not an invented larger 4-neuron fixture. In `scripts/m06_generate_paged_lif16_vectors.py` and `scripts/m06_g3_3_m02_m03_owner_vectors.py`, the workload has **five signed recurrent synapses (including cross-half and self delays), 17 signed input events, 3/4 truncation-toward-zero decay**, 32 logical neurons and 4 ticks. M06 G3.3 already accepted this workload in *offline* original-HLS+AMD XSim and one-slot **simulated** canonical memory; no M06 32-neuron physical RTL or DDR was previously proven.

## D3.D.2C phase 1 implementation (PC SOURCE/RTL STAGED, NO OWNER NATIVE BUILD)

- `rtl/m08/m08_d3d2c_m06_32_lif_axil.v` — distinct `M32N` v4 AXI4-Lite peripheral; 32 neuron banks, four logical ticks, eight configured signed16 directed edges (five used by original M06), delay 1..3, signed64 summed inputs, saturate once to signed16, threshold-spike/reset and full hardware-generated synaptic currents. One neuron update per fabric clock. Reentrant START clears all 32 state/history/traces and increments completed run_count.
- `scripts/m08_d3d2c_m06_vectors.py` — imports the **existing** original M06 G3.3 `fixture_oracles()` and thereby requires independent M02 dense/event and M03 exact sparse agreement, then derives the exact expected per-tick voltage, spike masks, and independently counted delayed synaptic current words.
- `rtl/m08/tb_m08_d3d2c_m06_32_lif_axil.sv` — real Icarus clocked RTL/AXI simulation reading a unique 579-word M06 hex golden: 32×4 voltages (128), 32×4 spike decisions (128), 32×4 delivered synaptic current values (128), plus nonce/status/run_count and negative invalid-IDs/zero-delay/unextended-weight/partial-write/early-readback cases. Runs twice with distinct nonces and checks a cleared state/replay.
- `scripts/m08_d3d2c_m06_gate.py`, `tests/test_m08_d3d2c_m06_32_source.py` — source-only checks including genuine Icarus when installed. A synthetic pass is not a physical/native result.
- `scripts/m08_d3d2c_m06_build.tcl` and `scripts/run_m08_d3d2c_m06_pc.sh` — separate owner-PC Vivado 2025.2 **offline** candidate builder with exact K26 part, dual 4KiB JTAG address windows, PS HPM masters disabled, fabric 256-cycle POR, TTC0 EMIO fan A12, original 12-file SHA evidence and Vivado timing/DRC reports. It does **not** connect to or program the board.
- `scripts/m08_d3d2c_m06_native_review.py` — first new image SHA and metadata/timing/DRC reporter. now accepts exactly the reviewed first owner native image (owner-local 12 hashes, bit, pins, timing, source); any other candidate fails. No inherited seven-warning waiver from D3.D.2B.

### Important scope limitation: external-event coalescing

The **17 M06 external current events are aggregated by the Python golden/host into 32×4 signed32 input-current registers**. The FPGA independently computes every delayed recurrent current from its own previously emitted spikes. This confirms original M06 **neural arithmetic and recurrent routing** for a bounded 32×4 workload, but NOT physical ingestion/ordering of the 17 individual external events, original M06 HLS engine equivalence, M03 sparse evaluation-skip behavior, DDR/page-state residency, stream protocol, memory/page eviction, PS clock independence, or Linux-owned integration. Preserve this distinction in any physical-paper claim. Sparse M03 traces agree for the reference, but RTL evaluates all 32 neurons per tick.

## New 4 KiB peripheral ABI (relative to 0xA0001000)

| Region | Offsets | Register contract |
|---|---|---|
| Header | `0x000-0x020` | `M32N` magic `0x4D33324E`, v4 `0x00040000`, status, nonce, 0/half/one/three-quarter decay mode, START, DONE nonce, monotonic run count, edge count 0..8 |
| Neurons | `0x100+32*n+4*j` | `n=0..31`, `j=0..7`: initial, bias, threshold, reset, preaggregated external current t0..t3 |
| Edges | `0x500+16*e+4*j` | `e=0..7`, `j=0..3`: pre, post, signed16 weight, positive delay 1..3 |
| Voltage and spike mask results | `0x900+32*n+4*j` | `j=0..3` four signed16 voltage words, `j=4` four-bit tick spike mask; only accessible after DONE |
| Fabric-computed synaptic currents | `0xD00+4*(4*n+t)` | `n=0..31,t=0..3`, signed32 delivered recurrent-current words; only accessible after DONE |

The JTAG-only BRAM echo remains `0xA0000000`. New physical identity is **different** from D3.D.2B `M4SN`. All active synapses require valid neuron IDs and delay ≥1; AXI writes require full strobe and are blocked BUSY. No DRAM/LINUX MMIO access.

## Staged next physical test harness — deliberately UNRELEASED

The following files are now staged for a **future** one-shot physical experiment, but cannot program any device in the present phase:

- `scripts/m08_d3d2c_m06_readback_once.tcl`: exact KV260 `xck26_0`/JTAG target, future one-program-only operation, BRAM echo and `M32N` v4 identity, five active M06 synapse configurations, 32 neuron configurations, complete 128 voltage + 128 spike-decision + 128 hardware-computed synaptic-current comparison, 32 per-neuron receipt rows. Contains `RELEASED_SHA=UNREVIEWED_M08_D3D2C_OWNER_IMAGE` hard stop **before** hardware manager is opened.
- `scripts/run_m08_d3d2c_m06_physical_once.sh`: a second independent hard stop runs the exact original-image review before creating any hardware evidence or starting Vivado; its image SHA is likewise `UNREVIEWED_M08_D3D2C_OWNER_IMAGE`. If later separately authorized, it would use one new unique hardware evidence folder, bounded Vivado, six SHA rows, no automatic programming retry and no reuse of old evidence.
- `scripts/m08_d3d2c_m06_physical_audit.py`: read-only independent complete-neural-trace auditor; requires an exact native release status which the updated first-image reviewer returns ONLY for the reviewed owner-original image, as well as six original SHA rows and exact source/target/trace/nonce evidence.
- `tests/test_m08_d3d2c_m06_physical_boundary.py`: PC-only guard and negative tests that check these blockers. This source coverage is not a native Vivado or hardware execution result.

**DO NOT run the staged physical shell or Tcl against a board now.** A source/CI PASS does not allow removal of these barriers. A first genuine owner Vivado 2025.2 offline build and full new DRC/timing/source SHA/image review must happen first, with any change to release gate separately reviewed and tested. The already accepted D3.D.2B image must never be swapped in.

## PC-only owner replication (no Vivado needed for first part)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-d3d2c-m06-32-neuron
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-d3d2c-m06-32-neuron
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
export PYTHONDONTWRITEBYTECODE=1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m08_d3d2c_m06_32_source.py' -v
python3 -m unittest discover -s tests -p 'test_m08_d3d2c_m06_native_boundary.py' -v
python3 -m unittest discover -s tests -p 'test_m08_d3d2c_m06_physical_boundary.py' -v
python3 scripts/m08_d3d2c_m06_gate.py --source-only
bash -n scripts/run_m08_d3d2c_m06_pc.sh
bash -n scripts/run_m08_d3d2c_m06_physical_once.sh
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
```

**STOP** if any test fails. Icarus without `iverilog`/`vvp` is SKIP, not accepted RTL parity.

## Proposed next owner-PC native gate — only after source/CI verification

**This command is optional offline synthesis/routing on the owner PC and must be run separately. It does not program the KV260.** Do **not** run the D3.D.2B builder again.

```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
source /home/dna/Vivado/2025.2/Vivado/settings64.sh
vivado -version
bash scripts/run_m08_d3d2c_m06_pc.sh
```

Expected after a successful bitgen: NEW, distinct `~/Thesis_Evidence/M08/m08_d3d2c_m06_XXXXXXXX` folder, **12 original SHA entries**, new routed DRC/timing reports, original new `m08_d3d2c_m06_lif_jtag_UNRELEASED.bit` and a historical **pre-review-required exit 2** (the current exact original image now requires owner-local exit 0). This is a safety feature, NOT proof of a failed bitgen. Preserve the first stdout, timing, DRC report, bit SHA, utilization, original logs and receipts; do not rerun automatically. An actual negative-route/DRC or critical warning demands diagnosis, not waiver.

No JTAG programming command is authorized/staged at this source phase. The next development gate is new native routed-image review, SHA/RTL/builder source pinning, new timing/DRC classification (no inheritance), and only then a distinct one-shot owner-controlled physical readback/auditor with **128 voltages, 128 spike decisions, 128 delivered-synaptic-current words**. Independent external cooling, UART capture, exact K26 identity, stock recovery and no automatic retry remain mandatory. Keep M08 OPEN, M09 PLANNED and all stacked PRs drafts/unmerged.
