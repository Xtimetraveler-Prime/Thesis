# M06 G3: owner AMD width-IP PASS, RTL address guards, and real XSim source export

Date: 2026-11-09 America/Denver. M06 OPEN, PR #80 DRAFT/UNMERGED. No board/JTAG/bitstream/PS DDR/physical programming; original AMD D3 IP and prior evidence stay immutable.

## Genuine 2025.2 owner evidence: dual AMD 32-to-256 IP generation PASS

The user's M06_G3_AMD_DWC_IP_REVIEW_20261110T032444Z.zip contains result.txt=exit_status=0, original owner commit 381c3740fa253d4ec4314e826160f0a0446a61ff, genuine Vivado 2025.2 log, exact successful readback for two vendor axi_dwidth_converter cores m06_g3_read_dwc READ_ONLY and m06_g3_write_dwc WRITE_ONLY, SI_DATA_WIDTH=32, MI_DATA_WIDTH=256, ADDR_WIDTH=32, SI_ID_WIDTH=1, AXI4, FIFO_MODE=0, .xci digests, source SHA before==after, GENERATED_ONLY scope, independent owner-side audit JSON success. Output products (including Simulation) were generated; log contains only two nonfatal overwriting-existing-OOC-XDC warnings and no tool ERROR. Owner original real evidence directory:

/home/dna/Thesis_Evidence/m06_g3_real_amd_dwc_20261110T032341Z_YUDRD3

SHA readback actual individual XCI:
- m06_g3_read_dwc.xci: 35503d7e4e8a29f0d09594884a3c68134df437c67171d6307b13fae706bed80b
- m06_g3_write_dwc.xci: b4ecae6f5f8dd1029e104965441d3d65731fd05e00fec722cc15a574e2532d41

PASS at genuine vendor GENERATION ONLY. The XCI source files were NOT uploaded here and their live contents can only be rehashed on the owner's PC. G1 genuine corrected HLS C/RTL cosim passed earlier, G2 original AMD A-E genuine scratch XSim passed earlier, G3 HLS->width IP->original SmartConnect connected RTL and G4 full numerical/fault acceptance still NOT performed. Do not conflate IP generation with integrated XSim proof.

## New actual RTL source increment: guarded 64-to-32 addressing

rtl/m06/m06_axi64_to32_guards.sv now contains TWO synthesizable, single-outstanding, 32-bit-word AXI channel guards (READ and WRITE) designed to sit upstream of original AMD 32:256 converter SI. Strict legal envelope: 0..65535 64KiB canonical scratch only, 4-byte alignment, INCR burst SIZE2, LEN0..15, 4KiB boundary may not be crossed, no 64-bit-high-address truncation. Rejected read AR synthesizes the complete R beat sequence with DECERR, zero data and correct RLAST while honoring RREADY; rejected AW drains matching W beats and issues DECERR B, no downstream original AMD request; both guards latch fault_seen until reset. Legal traffic is single outstanding, backpressure is propagated. This design is a CANDIDATE with sideband/ID/LOCK adaptation and real vendor timing still unverified; sticky fault signal alone does not cancel previously streamed HLS trace or provide AXI transactional atomicity. Current RTL does not implement timeout safety or complete AXI arbitrary-width/burst protocol. Do not reuse for general DDR addresses.

tests/test_m06_axi64_to32_guards.py invokes genuine Icarus on the candidate RTL and self-checking testbench where installed (GitHub Actions environment does have Icarus). Covers legal page255 word, R/B backpressure, byte-lane WSTRB, illegal page256 returning DECERR with no downstream transaction, sticky poison, and invalid 4KiB-crossing 2-word burst with RLAST; also source-only invariants. THIS IS NOT original vendor XSim, generated HLS C/RTL cosim or actual DWC connection.

## Second development increment: exact REAL AMD 2025.2 XSim compile order + pin ABI

scripts/m06_g3_export_real_dwc_xsim.tcl uses Vivado 2025.2 'open_project -read_only' on the already-successful original owner dual converter scratch .xpr, independent role/width readback, 'get_files -compile_order sources -used_in simulation -of_objects [get_ips]' and AMD documented 'export_simulation -simulator xsim -of_objects $ip -absolute_path'. Both original simulated IP compilation scripts are written ONLY to a new generated owner output directory, NOT executed, and source compile order is preserved. This DOES NOT modify or overwrite the original accepted XCI, does not compile generated HLS, original AMD SmartConnect or run XSim. The first failed owner converter generation is untouched.

scripts/run_m06_g3_amd_xsim_export.sh:
- requires exact original successful owner DWC directory argument.
- independently reruns earlier live owner .xci attestation and SHA before/after; fail-closed if DWC project or source changed.
- records source SHA, commit, original vendor Vivado version, new unique ~/Thesis_Evidence/m06_g3_amd_sim_export_* result and genuine simulation scripts.
- after Vivado export, executes scripts/m06_g3_capture_dwc_ports.py, which searches for ONE original generated SIM wrapper per role, extracts only actual vendor AXI signal names/directions/widths, checks 32:256 READ/WRITE port roles and real wrapper SHA. This is a header-only readback, not proprietary IP source upload or vendor proof.
- tests/test_m06_g3_amd_xsim_export.py: 5 synthetic positive/negative ABI/changed width/duplicate/missing pin tests, bash syntax and Tcl brace completeness, static no-program/no-XSim source checks. There is NO real Vivado run by GitHub CI.

AMD documentation explicitly supports open_project -read_only, export_simulation -simulator xsim -of_objects and get_files -compile_order -used_in simulation. The owner run can fail on differences between vendor generated simulation wrapper formatting or IP compile object behavior; preserve raw first failure and correct from genuine evidence, never force guessed ports or silently claim integration.

## Next owner commands (one fresh output, no repeated DWC/HLS/Stage E)

    cd ~/Git/Thesis
    git status --short
    git fetch origin
    git switch agent/neuromorphic-accelerator-v1-m06-ddr-residency
    git pull --ff-only origin agent/neuromorphic-accelerator-v1-m06-ddr-residency
    git rev-parse HEAD
    cd Neuromorphic_Accelerator/v1
    python3 -m compileall -q src scripts tests
    python3 -m unittest discover -s tests -p 'test_m06_axi64_to32_guards.py' -v
    python3 -m unittest discover -s tests -p 'test_m06_g3_amd_xsim_export.py' -v
    python3 -m unittest discover -s tests -p 'test_m06*.py' -v
    source "$HOME/Vivado/2025.2/Vivado/settings64.sh"
    vivado -version
    export DW="$HOME/Thesis_Evidence/m06_g3_real_amd_dwc_20261110T032341Z_YUDRD3"
    bash scripts/run_m06_g3_amd_xsim_export.sh "$DW"
    echo "M06 G3 original AMD XSim source export exit: $?"
    export EX="$(find "$HOME/Thesis_Evidence" -maxdepth 1 -type d -name 'm06_g3_amd_sim_export_*' | sort | tail -n 1)"
    echo "$EX"
    cat "$EX/result.txt" "$EX/commit.txt"
    test -s "$EX/02_genuine_dwc_sim_compile_order.tsv" && sed -n '1,25p' "$EX/02_genuine_dwc_sim_compile_order.tsv"

## Exactly which files to upload next

ONE ZIP at ~/Thesis_Evidence/M06_G3_REAL_AMD_XSIM_PORTS_REVIEW.zip. Include files from the NEW $EX directory:

1. result.txt
2. commit.txt
3. vivado_version.txt
4. 01_vivado_export.log
5. 02_genuine_dwc_sim_compile_order.tsv
6. 03_official_amd_xsim_script_paths.txt
7. 04_real_amd_dwc_port_headers.json
8. 00_owner_xci_before_check.txt
9. 05_owner_xci_after_check.txt
10. source_before_sha256.txt
11. source_after_sha256.txt
12. original_width_ip_folder.txt

The official .sh simulation scripts, proprietary vendor Verilog, and original .xci are NOT requested in this first port-review package. If new original vendor export FAILS, same single ZIP of EXISTING files is sufficient, especially 01_vivado_export.log, result.txt and 02_genuine_dwc_sim_compile_order.tsv. Original successful DWC evidence directory and all original D3 files must not be changed.

## Next genuine integrated G3 acceptance (NOT YET)

Once actual AMD SIM wrapper pins and official compile-order are independently reviewed, create a single offline 2025.2 XSim testbench containing:
- NEW genuine generated HLS m06_paged_rolling_replay Verilog and AXI-Lite/AXIS start/stimuli for one neural run,
- tested bounded 64->32 HLS AXI channel guards and complete actual sideband bridge,
- BOTH genuine 32->256 AMD width-converter simulation models,
- ORIGINAL immutable D3 SmartConnect S00 READ / S03 WRITE (S00/S03 no ID) and shared 64KiB memory through M00 128-bit,
- exact page eviction + dirty writeback/reload, source SHA, 4KiB, WSTRB/BRESP/RRESP/ID handshake and poison, independent M02/M03 neural trace/16B canonical state.
No claim of this XSim run or M06 closeout yet. PR #80 remains DRAFT and unmerged. No physical board/DDR/JTAG/M07.
