# M08 D3.D.2E — first owner M32Q exact native DRC/timing review and one-shot hardware procedure

**First owner offline image produced 2026-11-20 16:35 local.** Original evidence preserved; image never rebuilt. All seven original vendor DRC warnings have now been reviewed from the user's complete DRC text. A separate *exact-image*, source/hash/timing gate has been implemented and source/mutation-tested. **Hardware NOT yet programmed or physically passed.** The board owner must first run exact native gate on the original evidence and verify exit 0; CI cannot see those original files.

## First original owner image — exact identities

- Original native: /home/dna/Thesis_Evidence/M08/m08_d3d2e_queue_GFz0SbiC.
- UNRELEASED bit: bitstream_candidate/m08_d3d2e_queue_lif_jtag_UNRELEASED.bit, 7,797,844 bytes, SHA256 **2c443c3d80e86e5e9488b457110a45b0db96881016e9f87a5c801a72ec7527dc**.
- Original full DRC SHA256 **3c4c1d8bd304dc71eb4f21bddee7a9c35cbf2053857a805c097bc2e96f0157c6**.
- Original full routed timing SHA256 **cdeaf520fbbb944de4148cecca290651125c3009a2375966ee2b5d17f584c59f**.
- Original clock report SHA256 **836479b2faf87c71df2f50b9b19128d4b6ba7e9ac6dd72a41a6f42383ae43820**.
- The owner previously checked original 12/12 native SHA receipts; local first-image inspector verified source-builder/RTL/POR and correctly returned exit 2. **Leave that initial inspector intact**, as a historical first-image review gate. The new reviewer (scripts/m08_d3d2e_queue_exact_native_accept.py) independently checks the original full DRC, report SHAs, native source identity, whole bit and all original receipts; it is the ONLY exact-image acceptance release gate.

## Exact full original DRC review

Vivado 2025.2 K26 *Fully Routed*, exactly seven **warnings** and no DRC critical/error rule. **These seven instances differ in details from earlier accepted images and were independently reviewed for THIS original.**

| DRC code | Count | Original reviewed instance detail | Bounded disposition |
| --- | ---: | --- | --- |
| PDCN-1569 | 3 | Debug/BSCAN XSDB temp_curid LUT physical **A1/I0**, **A2/I1** with O5=(A5*A3)+(A5*(~A3)*(~A4))+((~A5)); id_state LUT physical **A3/I0** with O6=(A6+~A6)*((A1)). | Vendor-generated debug only, no M32Q/LIF warnings; exact pins/equations strictly pinned. |
| REQP-1857 | 1 | JTAG AXI engine rx_fifo_i, SDP WRITE_FIRST WIDE_PRIM18.ram advisory. | JTAG transport RAM advisory; not evidence of new M32Q FIFO data corruption. **Collision-free operation is not proven by DRC**, so real JTAG readback is required. |
| REQP-1858 | 2 | JTAG AXI engine rd_cmd_fifo_i and wr_cmd_fifo_i, SDP WRITE_FIRST WIDE_PRIM36_NO_ECC.ram advisories. | Vendor JTAG FIFO advisories, not FPGA user queue RAM; functional correctness requires live readback. |
| RTSTAT-10 | 1 | **39** nets no routable loads, first **15 of 37 listed** paths printed and reviewed individually; all 15 are XSDB/debug or JTAG AXI FIFO paths. | Only first printed 15 names can be individually reviewed; other 22 names are not printed and cannot be individually claimed reviewed. Entire original DRC report pinned by SHA. |

**Image-specific engineering review supports exactly one controlled, owner-authorized JTAG experiment**, not a guarantee of sustained or independent asynchronous operation. New/unreviewed warning, changed path/pin/equation, or different original DRC SHA must reject.

## Original routed timing

Owner reported WNS **+1.844ns**, TNS **0.000ns**, WHS **+0.010ns**, THS **0.000ns**, 0 setup / 0 hold failing endpoints, worst pulse-width slack +4.238ns (0 failing); 10.000ns PL0 and PL1 clocks, 50ns internal debug TCK. PS-requested PL0 at 100MHz remains a PS dependency and is NOT runtime-proven until hardware.

The exact native gate also uses the existing Vivado constraint-aware report timing parser and confirms zero violations and original timing/clock report SHA. Source Icarus simulation and CI cannot replace owner-local validation.

## Owner step 1 — read-only before hardware

~~~bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-d3d2e-tick-event-queue
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-d3d2e-tick-event-queue
cd Neuromorphic_Accelerator/v1
export PYTHONDONTWRITEBYTECODE=1
RUN="$HOME/Thesis_Evidence/M08/m08_d3d2e_queue_GFz0SbiC"

python3 scripts/m08_d3d2e_queue_gate.py --source-only
python3 -m unittest discover -s tests -p 'test_m08_d3d2e_exact_native_accept.py' -v
python3 -m unittest discover -s tests -p 'test_m08_d3d2e_physical_boundary.py' -v
python3 -m unittest discover -s tests -p 'test_m08_d3d2e_tick_queue.py' -v
bash -n scripts/run_m08_d3d2e_queue_physical_once.sh

# THIS NEW IMAGE-SPECIFIC NATIVE REVIEW MUST RETURN 0; NO BOARD here.
python3 scripts/m08_d3d2e_queue_exact_native_accept.py --run-dir "$RUN"
~~~

If any test or the new exact reviewer returns nonzero, **STOP**, preserve and share its output. Do not rebuild, rename, edit or rehash any original source, report, bit or owner SHA receipt, do not bypass the reviewer. The original first-image inspector intentionally STILL exits 2; never run it instead of the new exact reviewer to release an image.

## Owner step 2 — confirm separate physical preflight

Before any programming, personally confirm all of:

- **Independent active fan actually powered and rotating**; TTC0-to-A12 route is not a cooling guarantee.
- **UART serial logging active** and stock recovery path/known-good stock boot ready; do not rely on HDMI.
- Board powered; genuine Vivado **2025.2** sourced; unique stable K26 device xck26_0, single expected JTAG target localhost:3121/xilinx_tcf/Xilinx/XFL1RK5M5ILQA; close GUI Hardware Manager / competing JTAG clients.
- Consent for exactly **one** program_hw_devices invocation on this exact image. Never auto-retry on a failed/partial run. No SD/QSPI/flash programming, no PS Linux MMIO, no M05 HLS or M06 DDR physical claims.
- Original physically accepted D3.D.2D evidence and bitstream untouched.

## Owner step 3 — only if exact gate EXIT 0 AND step 2 physically confirmed

~~~bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
source /home/dna/Vivado/2025.2/Vivado/settings64.sh
vivado -version
RUN="$HOME/Thesis_Evidence/M08/m08_d3d2e_queue_GFz0SbiC"

# NEXT COMMAND REALLY PROGRAMS THE KV260 ONCE; do not run if preflight incomplete.
M08_D3D2E_ALLOW_PROGRAM=YES \
M08_D3D2E_PREFLIGHT_CONFIRMED=YES \
bash scripts/run_m08_d3d2e_queue_physical_once.sh "$RUN"
~~~

The launcher rechecks the new exact native gate and first original bit SHA **before** creating any physical evidence directory or opening JTAG; Tcl checks target/device and bit SHA again and contains exactly one programming operation. Then BRAM 55AA22DD; M32Q v6 magic/version; 17 distinct original signed32 events pushed into FIFO; verify live current buckets are ZERO until SERVICE; four ordered 0→3 explicit tick-service barriers, accepted 17 / serviced 17 / depth0 / high-watermark17 / tick mask 0xF / per-tick counts; **128 FPGA current sums plus 128 membrane voltages +128 spike decisions +128 delayed recurrent currents =512** independent M02/M03 comparisons.

The new one-shot physical folder and **six new SHA receipts** are preserved and independently audited. On any error, **STOP/NO RETRY**, report the folder/log and investigate before considering further programming. Only a new original hardware six-receipt auditor PASS substantiates physical verification.

**Still not claimed:** asynchronous independent clock, DMA/AXI stream, HLS M05 physical router, M06 DDR/paging, sparse skipping, measured energy/throughput, or Loihi chip equivalence. **M08 OPEN; M09 PLANNED; draft PR #93 remains unmerged.**
