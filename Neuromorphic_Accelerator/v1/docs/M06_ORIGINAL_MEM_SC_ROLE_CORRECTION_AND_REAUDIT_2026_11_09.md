> **NEW REAL RTL BFM-TARGET COMPONENT PASS — 2026-11-09:** Separate from the original AMD IP, new rtl/m06/m06_axi128_scratch_mem.sv implements a restricted simulation-only 128-bit AXI4 byte-addressed memory endpoint (AW/W/B and AR/R, WSTRB, single read/write outstanding, 1..32 INCR beats, 4KiB boundary and scratch-address decode, synthetic READY stalls, forced B/R SLVERR). rtl/m06/tb_m06_axi128_scratch_mem.sv exercises the endpoint using actual Icarus RTL simulator, including masked high/low byte lanes, downstream W/LAST and R/LAST sequencing, B/R held stable under backpressure, bad 4KiB crossing DECERR and a potentially committed write returned with SLVERR. GitHub Actions m06 job 42675553325 **PASSED**, genuine standalone Icarus transcript `M06_AXI128_SCRATCH_STANDALONE_PASS writes=3 reads=6 stalls=7 | NO_VENDOR_XSIM_NO_DDR`. Its CI run also reported 102 M06 host tests pass and inherited M05 430 tests + M01..M04 regressions. **Do not confuse this scratch RTL module with real original memory SmartConnect or DDR.** It is designed to become the simulation-only 128-bit endpoint behind the vendor DUT once the original generated mem_sc AXI module/port header is authenticated. No physical memory address, bitstream or hardware operation was authorized. Full set 102 M06 host tests and standalone Icarus, pending last docs-head CI.

# M06 continuation — original mem_sc role-correct AXI design and no-Vivado evidence recovery

**2026-11-09; user-original Vivado results, not vendor functional XSim.** The user's exact original Vivado owner port run had folder:
`/home/dna/Thesis_Evidence/m06_vendor_xsim_port_contract_20261109T181345Z_f4X4Of`
and commit `918c4210ed31fdcf399ba2b9f12bcca824deeb21`; the reported result.txt was **exit_status=2**, not PASS. It DID produce an original XPR/BD endpoint report, and Vivado reached its execution completion marker after the 186-source compile-order query. It did NOT produce `05_sim_bfm_contract_summary.json`, and did NOT run functional XSim. Existing original D3 XPR/BD hash manifests compared equal before/after in the owner's terminal (`cmp` produced no differences). Full original report, log and `05_audit.log` have NOT yet been supplied as files, so the exact reason for the audit `exit_status=2` is a diagnosis, not independently reproduced against full original evidence.

## What the genuine user Vivado readback *actually* says

| Original endpoint | Data width | Direction | Address width | ID width | AW/AR USER | Burst properties |
| --- | ---: | --- | ---: | ---: | --- | --- |
| mem_sc/S00_AXI | 256 | READ_ONLY | 32 | 0 | 0/0 | MAX=16, HAS_BURST=0 |
| mem_sc/S01_AXI | 256 | READ_ONLY | 32 | 0 | 0/0 | MAX=16, HAS_BURST=0 |
| mem_sc/S02_AXI | 256 | READ_ONLY | 32 | 0 | 0/0 | MAX=16, HAS_BURST=0 |
| mem_sc/S03_AXI | 256 | WRITE_ONLY | 32 | 0 | 0/0 | MAX=16, HAS_BURST=0 |
| mem_sc/M00_AXI | 128 | READ_WRITE | 49 | 0 | 0/0 | MAX=32, HAS_BURST=1 |
| ps/S_AXI_HP0_FPD | 128 | READ_WRITE | 49 | 6 | 1/1 | MAX=32, HAS_BURST=1 |

These are genuine BD **interface properties**, NOT authenticated generated HDL signal declarations, simulation waveforms or a proven AXI transfer. Original S00-S02 are *not* write-capable; S03 is not read-capable. Thus the old six-case generic 4-SI WRITE_THEN_READ stimulus was invalid for this original design and has been **replaced, not waivered**, by role-correct nine-case input vectors. A generic 128×256b upstream beat -> 256×128b downstream stress request is not justified by SI MAX_BURST_LENGTH=16 and SI HAS_BURST=0; it is now a clearly blocked capability probe, and no such command will be driven until actual generated AXI pin semantics are observed. The original PS HP0 ID/USER width difference must be verified later on actual 128b vendor M00/PS adapter signals rather than guessed from interface properties.

### Specific original auditor bug found, now fixed

The original independent source auditor used:

    log.count("M06_EXACT_ORIGINAL_MEM_SC_PORTS_CAPTURED|READ_ONLY_NO_XSIM_NO_BOARD") != 1

In the user's Vivado log, Vivado echoes the Tcl source instruction as `# puts "M06_EXACT..."` AND separately executes the instruction, so the token appears twice. This causes the auditor to reject an otherwise completed read-only capture. The corrected code counts only **standalone executed completion lines**, and now also verifies the actual original S00..S03 read/write roles, SI AXI ID/burst properties, and M00/PS exposed values. Added negative/synthetic tests explicitly check the Tcl-echo behavior and prevent promotion of an incomplete report to a functional AXI PASS. Because we do not have `05_audit.log` yet, this is a source-identified cause, not proof that it was the **only** exit2 cause. The corrected auditor also scans only the paths originally enumerated by Vivado instead of recursively walking every generated product.

## Work completed before a real vendor simulation

- `scripts/m06_vendor_axi_directed_vectors.py` now describes nine SOURCE-ONLY cases: FOUR single-256b-beat **S03 WRITE** cases with full/sparse WSTRB (including high-half lane 31); THREE **S00/S01/S02 READ** cases each reading the same post-write canonical scratch addresses; ONE sequence of independent S00 reads across a 4KiB boundary (no illegal crossing burst); and ONE **blocked** multibeat capability probe. No case is mislabelled as vendor PASS, and no illegal SI direction is driven. The proposed 256→2×128 model split is an expected value for future vendor verification, NOT a proven internal IP transformation.
- `scripts/m06_original_mem_sc_contract_audit.py` re-audits the original report OFFLINE, without needing another Vivado launch. It refuses overwriting existing output. It does not mutate original D3 evidence.
- `scripts/m06_vendor_wrapper_ports.py` consumes the original Vivado `02_original_mem_sc_ports.txt` and reads only ORIGINAL listed generated Verilog under D3 to discover genuine candidate `mem_sc` module names and ANSI AXI port directions/packed widths. It does NOT compile, synthesize, simulate, or assume a missing header. Exit code 3 means bounded **MODEL_HEADER_UNAVAILABLE** (share JSON and report); exit0 means public candidate header(s) found, NOT an XSim PASS.
- The source regression suite and M06 GitHub Actions exercise malformed report, duplicated echo, wrong read/write roles, illegal original bursts, no arbitrary external source reads, and byte/strobe golden correctness. The workflow uploads the nine-case input JSON (MODEL ONLY).

## ONE cheap owner action — REUSE ALREADY CAPTURED ORIGINAL RESULT, NO VIVADO RE-RUN

Run in VS Code terminal, on the updated M06 branch (and **do not manually edit any old evidence report**):

    cd ~/Git/Thesis
    git status --short
    git fetch origin
    git switch agent/neuromorphic-accelerator-v1-m06-ddr-residency
    git pull --ff-only origin agent/neuromorphic-accelerator-v1-m06-ddr-residency
    git rev-parse HEAD

    cd Neuromorphic_Accelerator/v1
    python3 -m unittest discover -s tests -p 'test_m06*.py' -v

    export D3="$HOME/Thesis_Evidence/neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ"
    export PORTS="$HOME/Thesis_Evidence/m06_vendor_xsim_port_contract_20261109T181345Z_f4X4Of"

    cat "$PORTS/result.txt"
    cat "$PORTS/05_audit.log" || true
    cmp "$PORTS/01_original_source_sha256.txt" "$PORTS/04_original_source_after_sha256.txt"

    # Corrected audit of EXACT SAME ORIGINAL report, no Vivado call.
    python3 scripts/m06_original_mem_sc_contract_audit.py \
      --original "$D3" \
      --report "$PORTS/02_original_mem_sc_ports.txt" \
      --vivado-log "$PORTS/03_vivado_readonly.log" \
      --output "$PORTS/05_sim_bfm_contract_summary_reaudited.json"
    echo "Original report OFFLINE re-audit exit: $?"

    # Find actual ORIGINAL vendor module/header names, NO Vivado or bitstream.
    python3 scripts/m06_vendor_wrapper_ports.py \
      --original "$D3" \
      --report "$PORTS/02_original_mem_sc_ports.txt" \
      --output "$PORTS/06_original_mem_sc_wrapper_headers.json"
    echo "Original HDL header discovery exit (0=headers, 3=unavailable): $?"

    # Replace old impossible four-SI write/read vectors with legal RO/WO roles.
    python3 scripts/m06_vendor_axi_directed_vectors.py \
      --port-report "$PORTS/02_original_mem_sc_ports.txt" \
      --output "$PORTS/07_original_role_safe_bfm_inputs.json"

    # Only small output/evidence to upload.
    cat "$PORTS/result.txt" "$PORTS/commit.txt"
    python3 -m json.tool "$PORTS/05_sim_bfm_contract_summary_reaudited.json" | head -n 140
    python3 -m json.tool "$PORTS/06_original_mem_sc_wrapper_headers.json" | head -n 160
    python3 -m json.tool "$PORTS/07_original_role_safe_bfm_inputs.json" | head -n 90

**Files requested:** Please attach all of the following from:
`/home/dna/Thesis_Evidence/m06_vendor_xsim_port_contract_20261109T181345Z_f4X4Of/`

- `02_original_mem_sc_ports.txt` — **most important**, full original 186-entry SIM_SOURCE list plus MEM_PROJECT_SOURCE lines.
- `05_audit.log` — first original failed audit reason; if absent, say so.
- `05_sim_bfm_contract_summary_reaudited.json` — only if the new offline auditor succeeds; otherwise share its first printed error.
- `06_original_mem_sc_wrapper_headers.json` — genuine-original HDL candidate header/port names; safe even with a 3=unavailable result.
- `03_vivado_readonly.log` — authentic complete tool log and error context.
- Optionally `07_original_role_safe_bfm_inputs.json`; the source generates it deterministically and it can be reconstructed from Git, so sharing is not essential.

**Why this is the next real development input:** the visible 186 source paths and original header list are required to instantiate the correct four-input/one-output IP DUT and the actual port directions. Without those, a guessed generic AXI testbench could appear to pass while never exercising ORIGINAL generated vendor RTL. After those files are returned, the next development is ONE real offline XSim with original mem_sc, physical-memory-free 128b scratch endpoint, S03 write, S00–S02 read, byte/response/stall scoreboard. Avoid repetitive warning inventories.

## Honest safety / status boundary

M05 remains closed/merged at bounded on-chip HLS/RTL prototype scope. M06 draft PR #80 remains OPEN and unmerged. No original vendor memory functional XSim has been run or claimed PASS; no physical DDR allocator/ownership or board programming has been authorized. The original incomplete capture stays `result.txt exit_status=2` forever; the new independent re-audit artifact will not overwrite it. The 63 original SmartConnect warning occurrences remain unwaived, but are not the subject of this next functional test. The owner's physical board and original 382 generated D3 files are untouched.
