# M08 D3.2 — passive KV260 synthesis-only checkpoint (2026-11-18)

**Goal:** obtain a new ORIGINAL OWNER-PC Vivado 2025.2 synthesis result for the independent D3.1 **fan-only, no-PS-HPM0, no-SmartConnect, no-UIO, no-identity/page** candidate, WITHOUT creating a loadable bitstream, routed image, overlay or boot firmware. No board/JTAG/MMIO access. Preserve all old evidence.

## Can we build a new bitstream soon?

**Passive (no AXI) candidate: potentially yes, after synth, placement/route, full DRC/timing and separate fan/rollback safety review.** The accepted D3.1 native owner Vivado BD result provides a true PS/K26 board-preset setup and fan PWM to A12 but NOT synthesis, timing closure or physical cooling evidence. This checkpoint advances from native BD-only to **native synthesis-only**. The new Tcl must launch only synth_1.

**Protected HPM0/identity/page bitstream: NOT YET.** It needs authentic boot ownership and functional PS-side timeout ATB4, isolation AIB13, outgoing transaction drain/late responses, PL0/reset and HPM0 AFI, Linux clock/region binding and independent cooling. The user's corrected PC inventory: 53 candidate artifacts and verified JSON SHA receipt, but ZERO original XSA, psu_init, or FSBL/PMUFW artifacts among those discovered. Only conversion.bif was classified as a boot-source recipe. A BIF name is NOT evidence of which firmware actually booted. Old M08 bit.bin (SHA a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b) stays QUARANTINED, and no hardware activities are authorized.

## New development on current D3.2 branch

1. scripts/m08_d3_2_passive_synth_only.tcl — opens the new-run D3.1 native BD project, rejects enabled PS masters, SmartConnect/identity/page, missing fan route/A12 constraint and wrong K26 board. Generates BD products and wrapper, launches ONLY Vivado synth_1, reports resource/synthesis timing and native readback. Does not launch implementation, generate bitstream or program board.
2. scripts/m08_d3_2_passive_synth_gate.py — source audit with immutable original D3.1 fan and HPM source hash checks; separate *optional* native output audit. No Vivado invocations or board/device calls in Python.
3. tests/test_m08_d3_2_passive_synth_gate.py — mock negative evidence and implementation/bitstream/HPM-enabled/fan-drift detection, and Tcl brace/quote completion. An accepted synthetic receipt is **never** native proof.
4. scripts/run_m08_d3_2_passive_synth_pc.sh — creates a NEW M08 evidence folder, runs original D3.1 fan-only builder within this new folder, synthesizes only there, audits reports and hashes the new logs/results. Refuses root and requires local Vivado on PATH. Fails at first error and leaves the run intact.

**Legacy xlslice note:** Native D3.1 BD has a nonfatal 2025.2 legacy xlslice advisory recommending ilslice. Do not change source/IP before observing actual native synthesis; a changed fan path needs separate correctness review.

## Owner VS Code terminal — source tests first (NO BOARD)

    cd ~/Git/Thesis
    git status --short
    git fetch origin
    git switch agent/neuromorphic-accelerator-v1-m08-d3b-boot-ownership-audit
    git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-d3b-boot-ownership-audit
    git rev-parse HEAD
    cd Neuromorphic_Accelerator/v1

    python3 -m compileall -q src scripts tests
    python3 -m unittest discover -s tests -p 'test_m08_d3_2_passive_synth_gate.py' -v
    python3 -m unittest discover -s tests -p 'test_m08*.py' -v
    python3 -m unittest discover -s tests -p 'test_*.py' -v
    python3 scripts/m08_d3_2_passive_synth_gate.py
    bash -n scripts/run_m08_d3_2_passive_synth_pc.sh

## NEW PC-only genuine Vivado synthesis — optional owner step after tests

The following runs on the **PC**, NOT KV260, and creates **no bitstream**:

    cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
    source /home/dna/Vivado/2025.2/Vivado/settings64.sh
    vivado -version
    bash scripts/run_m08_d3_2_passive_synth_pc.sh

New output starts at a folder of this form (the script prints exact path):

    $HOME/Thesis_Evidence/M08/m08_d3_2_passive_synth_<GENERATED_SUFFIX>

A genuine success prints both:
- M08_D3_2_PASSIVE_SYNTH_COMPLETE_NO_AXI_NO_IMPL_NO_BITSTREAM_NO_BOARD
- M08_D3_2_PASSIVE_PC_SYNTH_ONLY_RECORDED_NOT_ROUTED_NO_BITSTREAM_NO_BOARD=<NEW_RUN>

Check SHA receipt, synthesis status, fan port and utilization after success:

    RUN="$HOME/Thesis_Evidence/M08/m08_d3_2_passive_synth_<GENERATED_SUFFIX>"
    (cd "$RUN" && sha256sum -c 99_evidence_sha256.txt)
    python3 scripts/m08_d3_2_passive_synth_gate.py --native-output-dir "$RUN/output"
    cat "$RUN/output/20_passive_synth_readback.txt"
    sed -n '1,100p' "$RUN/output/21_passive_synth_utilization.rpt"
    sed -n '1,120p' "$RUN/output/22_passive_synth_timing.rpt"

If any command fails, preserve the new folder and send the first ERROR/CRITICAL WARNING from 01_passive_bd_vivado.log or 03_passive_synth_vivado.log, plus last 50 lines and source digest. No repair by editing evidence or old runs. No generation of bitstream, DTBO, XSA, firmware or live board access until independently cleared in a separate development/review decision.

## Hardware test roadmap, without milestone sprawl

Still **M08 → D3 → D3.2**. The next gate is first original genuine synth acceptance, then separately developed **passive** route/timing/DRC evidence, thermal/fan continuity and stock rollback. Only afterward might a new passive image be built offline and considered for explicitly authorized physical use. A protected AXI image remains blocked by exact original boot firmware/platform proof, ATB4/AIB13 stopped-clock safety, AFI/PL0 clocks and Linux device-tree/driver readiness. Once a genuinely protected physical interface is safe, return to M08 kernel DDR/DMA, physical neural parity, and performance measurement; M09 remains final analysis/closeout. Synthesis-only tests do not change hardware authorization.
