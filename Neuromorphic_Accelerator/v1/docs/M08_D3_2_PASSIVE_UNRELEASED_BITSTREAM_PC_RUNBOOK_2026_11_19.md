# M08 D3.2 — offline PASSIVE bitstream candidate runbook (2026-11-19)

**Decision:** The owner explicitly requested generating a new passive KV260 bitstream after independent successful Vivado 2025.2 route and report review. Owner has a backup fan. This is permission for an **offline, unreleased candidate file** ONLY. No hardware programming, DTBO/.bit.bin, JTAG, firmware, stock changes, Linux FPGA manager, PS registers, MMIO, physical inference or boot changes are authorized by this code. The old suspect M08 bit.bin SHA256 a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b remains QUARANTINED. Keep the work within existing **M08 -> D3 -> D3.2**, no tiny new milestone.

## Input evidence and important limitations

Owner original PC run /home/dna/Thesis_Evidence/M08/m08_d3_2_passive_synth_77Ols9zt: both native 99/98 SHA receipts passed, new independent read-only reviewer returned PASSIVE_ROUTE_DRC_ZERO_NO_TIMED_FABRIC_PATHS_HARDWARE_BLOCKED. Native route 100% complete; default DRC 0 reported findings; WNS/TNS NA because **no timed fabric endpoints**; 1 PS8, 1 OBUF, 1 IOB, no CLB LUTs/registers/BRAM/DSP; A12/LVCMOS33 fan port; HPM masters disabled. That does NOT prove neural timing, live fan PWM, Linux PS clock/reset, thermal safety or recovery.

A backup fan reduces the cooling concern only when independently powered and confirmed working BEFORE any eventual load. Fan behavior observed after loading can be supplementary evidence but must not be the only protective mechanism. Even with backup cooling, original Linux stall root cause and stock boot/FPGA-region compatibility are UNKNOWN. An offline .bit file can be generated without communicating with the board; programming it remains a separate decision.

## Added implementation

- scripts/m08_d3_2_passive_bitstream_candidate.tcl: reopens ONLY a fresh, HPM0-disabled fan-only PS8 native implemented project, checks part/board/AXI/fan A12, and uses exactly one write_bitstream -file on opened routed design to create an explicitly UNRELEASED .bit. It checks file size and writes no deployment image. The native Vivado implementation project is newly created, not an original accepted historical run.
- scripts/run_m08_d3_2_passive_bitstream_pc.sh: runs the existing route-only PC runner AGAIN to create a NEW evidence directory. Checks original 99 synth and 98 route receipts, reruns semantic DRC/NA-timing checker, calls bitgen on a NEW empty bitstream_candidate subdirectory and creates separate 96 candidate SHA receipt. Previously accepted owner runs z6PIsrwZ and 77Ols9zt remain untouched.
- scripts/m08_d3_2_passive_bitstream_gate.py: refuses unusual native byte sizes, changed byte length, bogus board/run, unexpected extra .bin/.bit.bin/.xsa/.pdi/.dtbo outputs, changed SHA receipt and any claim of hardware deployment. Source checks reject hardware calls. Provides --pre-ledger option only for a preliminary native check before writing the 96 receipt.
- tests/test_m08_d3_2_passive_bitstream_gate.py: synthetic-only tests for parent source, non-overwriting single bitgen, real PC shell syntax, hardware prohibition, fake binary evidence, symlinks, duplicate SHA, forged bitstream/deployment claims and unexpected additional outputs. No Vivado or board is used in CI.

The resulting bitstream is **not approved for physical deployment** by these scripts. No XSA, DTBO, BOOT.BIN, .bit.bin or stock firmware changes are part of this development.

## Owner Linux VS Code commands: source validation first

    cd ~/Git/Thesis
    git status --short
    git fetch origin
    git switch agent/neuromorphic-accelerator-v1-m08-d3b-boot-ownership-audit
    git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-d3b-boot-ownership-audit
    git rev-parse HEAD
    cd Neuromorphic_Accelerator/v1

    python3 -m compileall -q src scripts tests
    python3 -m unittest discover -s tests -p 'test_m08_d3_2_passive_bitstream_gate.py' -v
    python3 -m unittest discover -s tests -p 'test_m08*.py' -v
    python3 -m unittest discover -s tests -v
    python3 scripts/m08_d3_2_passive_bitstream_gate.py
    bash -n scripts/run_m08_d3_2_passive_bitstream_pc.sh

## Genuine NEW owner-PC Vivado bitstream candidate, not deployment

ONLY on the development PC, with genuine installed local Vivado 2025.2:

    cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
    source /home/dna/Vivado/2025.2/Vivado/settings64.sh
    vivado -version
    bash scripts/run_m08_d3_2_passive_bitstream_pc.sh

Expected last line on success:

    M08_D3_2_UNRELEASED_BITSTREAM_CANDIDATE_CAPTURED_NO_BOARD=<NEW_RUN_DIR>

Find the new binary at NEW_RUN_DIR/bitstream_candidate/m08_d3_2_passive_fan_UNRELEASED.bit. The runner starts a brand-new project; do not supply 77Ols9zt as an input or edit any original SHA receipts.

Verify the new record, substituting the actual path printed above:

    RUN="$HOME/Thesis_Evidence/M08/m08_d3_2_passive_synth_<NEW_SUFFIX>"
    (cd "$RUN" &&
        sha256sum -c 99_evidence_sha256.txt &&
        sha256sum -c 98_route_evidence_sha256.txt &&
        sha256sum -c 96_candidate_evidence_sha256.txt)
    python3 scripts/m08_d3_2_passive_bitstream_gate.py --run-dir "$RUN"
    cat "$RUN/bitstream_candidate/61_unreleased_bitstream_readback.txt"
    sha256sum "$RUN/bitstream_candidate/m08_d3_2_passive_fan_UNRELEASED.bit"
    grep -nE 'ERROR:|CRITICAL WARNING:|WARNING:' "$RUN/07_passive_bitgen_vivado.log" || true

Success marks the candidate as generated and byte-hashed, but PHYSICAL PROGRAMMING AUTHORIZED remains FALSE. Preserve any first error and all new run material if Vivado or a gate fails; do not override rejects or alter evidence.

## Gate before any future load of candidate

Separate, explicit owner signoff will be needed with working independently powered cooling, stock recovery/power control if PS/Linux hangs, verified firmware/PS/FPGA-region ownership and known-good stock boot, and safe timing/lifecycle for fan control. No HPM0/SmartConnect/identity/page/PS MMIO is added to this passive checkpoint. Genuine PS ATB4/AIB13 and Linux driver validation remain open for the later protected AXI design. Bitstream generation is not proof those conditions are satisfied.
