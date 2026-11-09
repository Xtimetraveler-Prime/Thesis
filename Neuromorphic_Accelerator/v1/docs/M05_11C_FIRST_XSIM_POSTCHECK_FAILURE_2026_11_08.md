# M05.11c first owner integrated XSim: parser-stage failure and corrective action (2026-11-08)

## Immutable original operator evidence — DO NOT REWRITE

- Owner-uploaded console transcript of original evidence folder: `~/Thesis_Evidence/neuromorphic_v1_m05_11c_real_hls_20261108T235448Z_NzKhyY` (absolute operator path: `/home/dna/Thesis_Evidence/neuromorphic_v1_m05_11c_real_hls_20261108T235448Z_NzKhyY`). Checkout: `60c48fe32eed4adb28ba10e7c822fbed63abc3d0`.
- Original result: **`exit_status=1`**, so the overall M05.11c verification gate **FAILED**. Do not retroactively relabel or modify it. The transcript is user-supplied terminal output; the assistant does not have direct access to original operator-local evidence files.
- Genuine generated signed32 K26 HLS implementation: `neuromorphic_v1_m05_rolling_impl_20261108T200432Z_186026`; original kernel source SHA256 reported `24c4de87b5557cd536b33fe518595d56133e2ac737786bdf0d6fdbc53a687073`. 11 genuine RAM images staged, generated register offsets PASS; `xvlog` and `xelab` PASS; Vivado 2025.2 genuine XSim executed both testbench scenarios and logged PASS at simulated **17,530 ns**. This is not physical timing.
- XSim run0: **25** accepted 256b DMA beats = 24 neural rows + terminal TLAST, HLS status0, session `0102030405060708`, committed24. Run1: **9** accepted beats = 8 provisional rows + TLAST, genuine HLS status4, session `1020304050607080`, committed0. Reported **148 DMA-output stalls and 148 HLS-output stalls**. Both were in the SAME RTL instances without reset.
- The next stage, `scripts/m05_11c_replay.py`, emitted **`ERROR: M05.11c real XSim raw DMA frame replay: unknown/malformed M05.11c simulator marker`**. The transcript contains **32** legitimate `M05_11C_ROW` diagnostics (24+8) interleaved immediately after the corresponding 32-bit-field-checked `M05_11C_DMA` handshakes. Old replay parser understood `M05_11C_DMA`, `FINAL`, `COMMIT` and `PASS`, then raised on any other `M05_11C_` prefix. This is a concrete parser/testbench log-contract mismatch, NOT evidence that the signed32 neural engine produced wrong spikes.

## Focused fix, verification level and negative coverage

- Modify **only** `scripts/m05_11c_replay.py` to recognize the existing exact `M05_11C_ROW` format and verify every ROW's tick/neuron/voltage/spike/evaluated/delivered against the **immediately preceding actual DMA TDATA** (decoded using the established trace ABI). Reject malformed, duplicated, out-of-order, shifted-run and incomplete ROW diagnostics. Existing synthetic marker-free transcripts remain supported. Unrecognized `M05_11C_` lines remain errors.
- Add **three native synthetic regression methods** to `tests/test_m05_11c_hls_shell.py`: valid observed marker order, corrupt/missing/duplicate/run-mismatch diagnostics, and misplaced/unknown diagnostics. These are *host-only synthetic tests*, never genuine XSim.
- The uploaded transcript's 34 DMA words were independently decoded offline: the 32 recorded ROW diagnostics match the corresponding neural fields; both footer magic/status/count/session values match the expected contract. This independent inspection is not a replacement for the committed Python replay on the operator's intact `04_xsim.log`.
- Leave original `hls/m05_rolling/m05_rolling.cpp`, Vitis-generated Verilog, transport shell, 1-in-7 `TREADY`, testbench neural oracle, and original evidence folder unchanged.

## Verified post-fix native regression (not Vivado)

At repair source commit `6b5fa76f589d37e103752cf173cc74d0a7355aca`, [M05 no-board workflow run 42537892857](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/42537892857) completed **SUCCESS**. Its original job log reports `Ran 234 tests ... OK`; all three new ROW-diagnostic tests are explicitly `ok`. M04/M03/M02/M01 workflow jobs also report SUCCESS, with 22+28+21+20=91 accepted-method regressions, for **325/325 native method PASS**. These are native/synthetic tests and previous standalone RTL smoke work, not a fresh generated-HLS integrated Vivado XSim rerun.

## Required post-fix operator acceptance (still PENDING)

Use the original authenticated implementation and a newly unique evidence folder:

```bash
cd ~/Git/Thesis
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m05-sparse-onchip
cd Neuromorphic_Accelerator/v1
python3 -m unittest discover -s tests -p 'test_m05_11c_hls_shell.py' -v
python3 -m unittest discover -s tests -p 'test_m05*.py' -v
export ROLL_IMPL="$HOME/Thesis_Evidence/neuromorphic_v1_m05_rolling_impl_20261108T200432Z_186026"
bash scripts/run_m05_11c_hls_shell_xsim.sh "$ROLL_IMPL"
```

If useful, separately **read-only** audit the old original XSim log without writing into its directory: `python3 scripts/m05_11c_replay.py --xsim-log "$HOME/Thesis_Evidence/neuromorphic_v1_m05_11c_real_hls_20261108T235448Z_NzKhyY/04_xsim.log"`. This should be labeled historical replay verification, **not** a retroactive passing `result.txt`. The new full run must produce fresh `exit_status=0`, genuine XSim PASS and independent replay PASS with 24+0 committed, original HLS provenance and source hashes. Do not close M05.11c or begin implementation of actual DMA prior to inspecting the operator's returned original evidence.

**Safety:** no hardware programming, XSDB/JTAG, PS/Linux-owned DDR access, or bitstream creation; PR #79 remains draft/unmerged.
