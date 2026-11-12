# M08.2b — KV260 physical deployment: cooling, ownership, rollback and operator gate

**2026-11-11 America/Denver.** One consolidated M08.2b; PR #83 is DRAFT/UNMERGED. This is a deployment *preflight*, **not** permission to program the PL. The user reports the current source regression suite PASS; do not represent that as new physical evidence.

## Known baseline, immutable originals and why loading must stop here

Owner's active KV260 Ubuntu 24.04.2 / kernel 6.8.0-1036-xilinx has Linux fpga_manager operating, `dfx-mgr` and `fancontrol` active, and **`k26-starter-kits_image_1` is loaded**. The only existing `/sys/class/uio/uio0..3` nodes are `axi-pmon`. M08 has never physically been programmed. The original owner first-stage package `/home/dna/Thesis_Evidence/M08/m08_2b_path_a_linux_package_REVIEW_ONLY_bco0j53i` and warning-bearing original UIO candidate `m08_2b_path_a_uio_overlay_REVIEW_ONLY_tuzu33oo` stay unchanged.

The *corrected* offline DTBO is clean by original native DTC, has exact 2/2 FPGA + AMBA cells, and correct `generic-uio` 4KiB identity/page resources. Original SHA receipt lists corrected DTBO `2b7798053d10415ef528d4abbbdcb5251cd0dee4845c3288de2a3ef7bd2e75ed` and converted fan-preserving `bit.bin` `a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b`; binaries were **not** in the uploaded original archive and need independent **PC owner-side rehash**. Neither the corrected overlay nor the bitstream is deployed.

AMD's K26 Linux documentation explicitly states that the standard `k26-starter-kits` bitstream routes the carrier fan via PS TTC0 EMIO through the PL to HDA20/A12; **unloading it disables active control while the PL is blank**. The M08 offline fan route to A12 is correct *after configuration*, not evidence of cooling in the gap. Reference: https://xilinx-wiki.atlassian.net/wiki/plugins/viewsource/viewpagesrc.action?pageId=2471788698 . The AMD DFX manager supports `PL_FLAT` as a documented shell type, but that does not prove this installed daemon accepts this candidate, nor does it establish the transition/rollback on this exact Ubuntu image. References: https://github.com/Xilinx/dfx-mgr and https://docs.amd.com/r/en-US/ug1630-kria-som-apps-developer-ubuntu/dfx-mgrd .

## P0 — exact-next read-only preflight (SAFE; operator PC via VS Code)

New tools:
- `scripts/m08_path_a_physical_gate_board_readonly.sh`: streamed over SSH with Bash; **read-only** service and firmware-manager version, active overlay and fpga manager, stock firmware files and SHA, current Linux UIO/resource ownership, fancontroller and thermal hwmon/thermal zone telemetry.
- `scripts/run_m08_path_a_physical_preflight_pc.py`: verify **full original corrected candidate ledger and binary SHA** on owner PC *before* SSH; reject old warning-bearing candidate, missing/changed `bit.bin` or `dtbo`, changed shell.json or compiler warnings. Create a **fresh exclusive** `~/Thesis_Evidence/M08/m08_2b_physical_READONLY_*` directory containing the exact sent script, inputs, raw stdout/stderr/exit status, raw limited-scope status JSON, and independent SHA receipt. It creates no files on the KV260 and does not open device nodes. A completed SSH transcript is explicitly **NOT deployment approval**.
- `tests/test_m08_path_a_physical_preflight.py`: Bash grammar, Python syntax, no-mutation constraints, original SHA receipt tampering, wrong board IP, synthetic successful and failed SSH capture, unchanged archived originals. Mocks are NOT a hardware test.

### Commands on user's Linux PC (no PuTTY multiline)

```bash
cd /home/dna/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-kv260-bringup
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-kv260-bringup
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
bash -n scripts/m08_path_a_physical_gate_board_readonly.sh
python3 -m unittest discover -s tests -p 'test_m08_path_a_physical_preflight.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Find the **corrected** candidate without guessing a directory name. This searches the known exact corrected review SHA, not just most recent folder:

```bash
EVIDENCE_BASE=/home/dna/Thesis_Evidence/M08
find "$EVIDENCE_BASE" -type f -name 03_review.json -path '*/m08_2b_path_a_uio_overlay_REVIEW_ONLY_*/*' -print
```

Set `CANDIDATE` to the **new warning-free review folder** containing that 03_review.json and corrected DTBO SHA `2b779805...`, **not** the original `tuzu33oo` folder:

```bash
CANDIDATE="/home/dna/Thesis_Evidence/M08/PASTE_NEW_CORRECTED_UIO_REVIEW_FOLDER"
python3 scripts/run_m08_path_a_physical_preflight_pc.py --candidate-dir "$CANDIDATE" --evidence-base "$EVIDENCE_BASE" --ssh-target ubuntu@10.42.0.135
```

The runner first byte-checks original binary files and original ledger on the PC. On successful SSH it prints `M08_PHYSICAL_READONLY_CAPTURE_COMPLETE_NOT_DEPLOYMENT_APPROVAL` and the exact new `M08_PHYSICAL_PREFLIGHT_EVIDENCE_DIR`. Verify the SHA receipt inside that folder:

```bash
CAPTURE="/exact/new/folder/from/runner"
(cd "$CAPTURE" && sha256sum -c 99_evidence_sha256.txt)
```

Send the **actually generated** `01_ssh_stdout.log`, `02_ssh_stderr.log`, `03_ssh_exit.txt`, `04_review.json`, and `99_evidence_sha256.txt` (or tar them without rewriting the originals). If a capture fails, send its original failure evidence and DO NOT proceed to loading.

## P1 — physical deployment plan: safety gates that remain OPEN

The following must be **independently established, reviewed and approved**, not recorded as a self-asserted YES:
1. **Cooling spanning the entire reconfiguration gap:** a genuinely independent external airflow/cooling method with power independent of the PL-routed PWM output, documented monitoring and measured operation. Do not attach arbitrary voltage to the KV260 fan PWM/PL pin. A routed M08 A12 fan connection does NOT satisfy this. Verify a sensor/independent observation path before, during and after the eventual transition; establish a justified operator STOP temperature and maximum time for a failed transition from authoritative thermal limits. No fabricated temperature thresholds or accepted fan-stop duration.
2. **Baseline recovery:** record immutable bytes/SHA for installed stock `k26-starter-kits` .bit.bin/.dtbo/shell.json, shell-type and default firmware ownership, confirm serial and SSH recovery (including after Linux/FPGA-manager failure) and validate an operator-controlled fallback to that exact known-good stock image. Do **not** assume `xmutil loadapp k26-starter-kits` is guaranteed to work after a failed PL load, or that reboot automatically restores fan control, until the installed daemon/default firmware state is verified. Never flash boot firmware.
3. **Linux-manager/package gate:** review actual `dfx-mgr` build/version, stock `XRT_FLAT` layout and the corrected candidate `PL_FLAT` triplet. `PL_FLAT` is documented in upstream, but installed-release acceptance **remains unproven**. Determine expected naming/registration and driver-probe order **without installing or unloading yet**. Check current `/proc/iomem`, `/sys/class/uio`, active DT symbols and address ownership. Even an installed generic-uio device-node match is not a physical AXI response or hardware-identity proof.
4. **Hardware fault containment:** a read-only user-space MMIO read can still trigger SIGBUS or hang on an unmapped or powered-down AXI slave. Need an independently reviewed Linux fault-handling/timeout plan, no blind probing, and a separately permitted identity-only transaction as first physical PS test. Ordinary UIO mmap does **not** expose AXI `RRESP`/`BRESP`; never claim dispatch SLVERR detection from a Python read/write success/failure alone.
5. **Operator permission:** after documenting this exact transition and fallback, obtain explicit confirmation before installing the new package, unloading the starter image, programming via manager/JTAG, changing fancontrol or reading physical M08 registers. The owner's general instruction to proceed with deployment authorizes **planning and read-only preflight only** pending the above verified gates.

### Planned first active experiment (DO NOT EXECUTE YET)

Only after P1 authorization with independent cooling in place: preserve live thermal and serial/SSH logs; execute exactly one manager-controlled replacement (not JTAG hot-program, not multiple retries); verify the expected overlay, bound exact-name UIO map0 resources at 0xA0000000 and 0xA0001000 (both 4096 bytes), and unchanged cooling. First perform **identity-only** readback (magic 0x4D303831/version 0x00010000, page magic 0x4D303850/version 0x00020002/capability 1). Preserve actual original logs/SHAs and halt for review before staged page writes. The later separately approved 64x32-bit write/read/COMMIT experiment verifies 256 genuine bytes, 64 independent comparisons and status; **DISPATCH is compute-disabled**, and safe proof of AXI SLVERR requires separate instrumentation.

### Rollback plan (to verify before any load)

If reconfiguration fails, fan airflow/temperature diverges, manager/DT binding is unexpected or PS-side read is unsafe: STOP all M08 transactions and do not retry. Maintain independent cooling. With a proven responsive manager and correct recovery image, restore the **original** `k26-starter-kits` via its manager-controlled path, verify its loaded overlay, fancontrol operation and thermal stabilization. If the manager/SSH is dead, use the **independently verified serial/boot recovery path** with independent cooling; no ad-hoc JTAG/flash changes. Retain failure logs and original hashes; do not infer that an unloaded PL is safe from the absence of alarms.

## Required evidence boundary

P0 original owner logs + SHA and current thermal/manager state are sufficient for the *next review*. They do **not** authorize active PL programming. Physical M08 identity/page conformance, cooling throughout PL reconfiguration, physical DDR/DMA, signed16 neural inference, and performance benchmarks all remain **OPEN**. PR #83 remains DRAFT and UNMERGED.
