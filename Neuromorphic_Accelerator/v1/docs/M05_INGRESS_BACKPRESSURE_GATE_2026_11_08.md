# M05.7 — input-side backpressure with a separate 64-neuron RTL scenario

**Status:** New native-verified test harness and documentation; genuine direct
Verilog/XSim result for the 64-neuron ingress scenario is **PENDING**.
M05 remains OPEN; PR #79 remains DRAFT / UNMERGED. No physical board, JTAG,
DMA/DDR, Vivado block design or HLS kernel change.

## The last real operator result, accurately classified

Original evidence `~/Thesis_Evidence/neuromorphic_v1_m05_rolling_axis_rtl_20261108T205357Z_221064`, result `exit_status=1`, following the source-only
hardening change which presented two neuron packets prestart:

- **PASS:** all **11 genuine Vitis-generated RAM .dat files** staged with
  original SHA256 and source manifest. No missing-RAM warning recurred.
- **PASS:** `xvlog` compiled actual generated rolling RTL and testbench.
- **PASS:** `xelab` elaborated the RTL.
- **FAILED COVERAGE REQUIREMENT (not a spike/voltage mismatch):**
  `Fatal: RTL_STRESS_FAIL no meaningful incoming AXIS backpressure`
  at simulation 12170 ns, bench line 345. The original test requires
  `neuron_stall_cycles + synapse_stall_cycles + external_stall_cycles >= 10`,
  but 2 neuron, 1 synapse, 1 external prestart packets did not provide
  sufficient pressure to the input stream. The trace and final status checks
  precede that assertion in source, so the failure does not identify a
  neural-arithmetic fault.
- **XSim reported `exit 0` even after `$fatal`**, while the shell runner
  correctly returned `exit_status=1` for the missing required PASS marker.
  Next runner also explicitly rejects `Fatal: RTL_STRESS_FAIL` in the log.

The prior separately verified **two-neuron output-only test remains PASS**:
`~/Thesis_Evidence/neuromorphic_v1_m05_rolling_axis_rtl_20261108T203635Z_212333`;
24/24 trace rows, 188 measured output stalls, final status 0.
Do not retroactively invalidate this distinct scenario.

## M05.7 development decision: split tests, do not weaken assertions

**Baseline source restored byte-for-byte** from the original XSim PASS at Git
revision `6de148f32c542debf48b8f325e0bce31c7602649`:
`hls/m05_rolling/rtl_stress/tb_m05_rolling_axis_stress.sv`
(Git blob SHA `c2831bc2953b41066ac4ba83afb75fdeda13c15a`).
It checks 2 neurons, 12 ticks, 24 rows and 188 output stall precedent; input
gaps remain checked but it does *not* claim that input TREADY was deasserted.

**New, independent ingress saturation case**
`hls/m05_rolling/rtl_stress/tb_m05_rolling_axis_ingress_stress.sv`:
- 64 neurons, 1 edge (0→1 weight +5 delay 8), 1 external event (t0/n0
  weight +5), 12 logical ticks, **768 expected trace rows**.
- Present ingress neuron packets **300 clock cycles before ap_start**, trying
  to fill the actual generated stream staging capacity. Ingress neuron
  count is 64 (rather than 2) to make TREADY deassertion observable.
- Check true READY/VALID transfer counts (64 neuron, 1 synapse, 1 external),
  input VALID+TDATA hold through stalls, `>=10` **actual input stalled clock
  cycles**, 768 in-order trace rows with correct spike/voltage/evaluated/count,
  output VALID+TDATA hold under one-per-eleven-cycle TREADY throttling,
  final HLS return status 0 and a bounded execution timeout.
- This is a **direct generated-RTL/XSim experiment**; 64 packets may still
  be insufficient if generated buffering accepts all of them before start.
  If the coverage assertion fails again, examine actual generated AXIS
  regslice/FIFO depth and READY timing; do not relax the threshold or report
  an unsupported input-backpressure PASS.

**Runner interface** `scripts/run_m05_rolling_rtl_stress.sh` accepts:
- `<impl evidence folder>`: previously verified two-neuron output scenario.
- `<impl evidence folder> --ingress`: NEW independent 64-neuron ingress.
- Both select their own simulator top/snapshot and exact PASS marker, use the
  SAME earlier `--impl` signed32 kernel source (hash-verified), stage only
  the original 11 RAM initialization assets, preserve fresh evidence folders,
  capture the mode in `stress_mode.txt`, fail if RAM-init warning or RTL
  `$fatal` appears. Native Python CI verifies source/test-runner constraints,
  but **does not run Vivado or claim the new ingress result**.

## Operator commands (Vivado 2025.2 sourced, no board)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m05-sparse-onchip
cd Neuromorphic_Accelerator/v1
python3 -m unittest discover -s tests -p 'test_m05*.py' -v

export ROLL_IMPL="$HOME/Thesis_Evidence/neuromorphic_v1_m05_rolling_impl_20261108T200432Z_186026"
bash scripts/run_m05_rolling_rtl_stress.sh "$ROLL_IMPL" --ingress

export AXIS_EVIDENCE="$(ls -dt "$HOME"/Thesis_Evidence/neuromorphic_v1_m05_rolling_axis_rtl_* | head -n 1)"
echo "$AXIS_EVIDENCE"
cat "$AXIS_EVIDENCE/result.txt"
cat "$AXIS_EVIDENCE/stress_mode.txt"
cat "$AXIS_EVIDENCE/01_ram_init.log" 2>/dev/null || true
tail -n 60 "$AXIS_EVIDENCE/02_xvlog.log" 2>/dev/null || true
tail -n 60 "$AXIS_EVIDENCE/03_xelab.log" 2>/dev/null || true
tail -n 100 "$AXIS_EVIDENCE/04_xsim.log" 2>/dev/null || true
```

Optional baseline replay (fresh separate folder, never overwrites any evidence):
`bash scripts/run_m05_rolling_rtl_stress.sh "$ROLL_IMPL"`.

## Next gates after genuine ingress XSim

1. Repeat directed cases with varying input patterns and source payloads,
   including deliberate multiple external deliveries and graph fanout.
2. Verify nonzero final status / late-failure semantics at actual RTL AXI-Lite
   and AXIS output, with the host transactional commit/abort policy.
3. Pursue a complete PS/DMA/DDR control path, state-preserving execution
   beyond 64 ticks and real board implementation only with explicit approval.

The [canonical engine evolution ledger](M05_EVALUATION_ENGINE_EVOLUTION.md)
remains the authority for exact performance/provenance and must be updated
on every subsequent gate or optimization.
