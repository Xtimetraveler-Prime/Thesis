# M08.5 — 32-bit AXI4-Lite CSR plus recurrent LIF source integration (2026-11-21)

**Classification: synthesizable source candidate + genuine offline RTL verification ONLY.** Same M08.5 branch / draft PR #95. Original M08.4 accepted owner physical receipts are immutable. No Linux module, device-tree deployment, PS HPM0/HP0 connection, actual PS DDR, AFI/readout, physical drain, Vivado timing, new bitstream, FPGA programming, kernel memory allocation, measured power, sparse skipping, or DMA buffer-release authorization exists in this increment.

## 1. Owner SSH evidence is now independently owner-verified on the PC

The first owner-submitted original KV260 Linux SSH stdout and SSH-exit files matched their owner five-file SHA ledger during independent assistant byte review of those **two uploaded files**. Following the earlier review, the owner separately ran `sha256sum -c 99_evidence_sha256.txt` against the **original PC directory** `/home/dna/Thesis_Evidence/M08/m08_m085_ssh_readonly_20261121T181457Z_Cu9fFaJN` and reported **all five entries OK**, including original `00_remote_source.sh`, `01_context.txt`, `03_original_stderr.log`. This establishes an **owner-local original 5/5 SHA receipt PASS**; assistant did NOT obtain the three missing original files or independently verify their bytes. The read-only Linux observations remain exactly as characterized in [first capture review](M08_5_KV260_FIRST_SSH_OBSERVATION_REVIEW_2026_11_21.md): stock-named overlay, Linux 6.8.0-1036-xilinx, existing PS DMA controllers, **no identified bound M08 device/driver**, unverified DMA mask/physical mapping/AFI/DDR/drain. Owner SSH integrity success is not DMA owner attestation.

## 2. New actual AXI4-Lite protocol frontend

New `rtl/m08/m08_m085_axil_control_candidate.v` wraps the existing **unchanged** `m08_m085_trusted_control_abi.v` (which itself instantiates the existing DMA lease fence). It is a fully clocked **32-bit AXI4-Lite five-channel protocol endpoint** with a **12-bit 4 KiB byte-offset aperture** (not an assigned SoC base address).

- AW and W may arrive in any order or together. Each is held in its own skid/ownership register; neither channel depends on the other's VALID. One BRESP after both channels arrive, held while BREADY=0; no duplicate acceptance/response. A fresh CSR VALID pulse commits one complete write; the original CSR `write_armed` deassertion/rearm stays intact.
- AR read accepted only when neither half of a write nor BRESP is pending; RDATA/RRESP registered and held while RREADY=0. Return `SLVERR=2` for invalid/unprivileged read of protected status/fields, with zeros instead of disclosing DMA handle. CAP `M085` and ABI v1 remain readable. Read side errors do not poison the compute path.
- Full aligned strobes are required by original CSR decoder. Misaligned, unknown, read-only-register or aliasing-outside-low-256B writes reach invalid CSR decode and **poison the lease** with `SLVERR=2`; no wrap/alias to valid descriptor bytes. Successful CSR write admission is not a guarantee that a later fence grant passes descriptor masks; software must read STATUS before treating grant as admitted.
- **Conservative work embargo:** an AW or W acceptance in the current cycle, or either held half of a write, masks `admit_work` and zeroes `admitted_begin/end` immediately, prior to delayed command decode. This includes orphaned AW/W waits, precludes a work request racing a STOP before both channels arrive, and preserves the underlying one-way stop/drain/fault state. A half-written AXI transaction cannot complete until both channel beats arrive; future external watchdog/isolator still required for bounded recovery.
- `AWPROT/ARPROT` are ignored for *identity*: AXI protection bits cannot prove a Linux driver. `csr_trusted`, `driver_bound_verified`, `control_route_verified`, `interconnect_drain_ack` remain **synthetic testbench pins**, not an authorization mechanism. Actual kernel-only decoder, PS HPM0 128→32 width conversion, firewall/privileged ownership, bus reset and physical quiescence remain to be developed/reviewed.

`rtl/m08/tb_m08_m085_axil_control_candidate.sv` tests complete 32-bit AXI-Lite CAP/version/descriptor/grant/STOP/fresh external low→high drain handshake and **19 independently invoked adverse cases**, including AW-first, W-first, both-at-once, B/R backpressure, malformed WSTRB, 4KiB high-address alias, misalignment, protected reads, untrusted controls, owner/route loss, orphan AW/W STOP admission embargo, bad grant/command, stale drain acknowledgment, mid-drain owner loss, invalid status writes, same-cycle STOP, dirty bank timeout and read/write serialization. `tests/test_m08_m085_axil_control_candidate.py` requires genuine `iverilog` + `vvp`. No synthetic “pass” substitution is permitted.

## 3. NEW composite top connects AXI-Lite lease directly to unchanged 7-page recurrent engine

`rtl/m08/m08_m085_axil_neural_candidate.v` composes `m08_m085_axil_control_candidate` with **the existing unmodified `m08_m085_axi_neural_shell.v`**:

```text
       TEST ONLY fake driver/route/drain verifier signals
                           |
  upstream 32-bit AXI4-Lite AW/W/B, AR/R (UNCONNECTED PS)
                           |
             m08_m085_axil_control_candidate
                           |
            ORIGINAL trusted CSR + DMA fence
           admit_work / frozen base + 1792B window
                           |
        two independent work request pins (NOT MMIO yet)
                   |                 |
           page request        neural dispatch
                   |                 |
                   +--- unchanged recurrent shell ----+
                                      |
                           one real 64-word bank
                                      |
                           16-beat 128-bit AXI4 master
                                      |
                        SYNTHETIC seven-page DDR model
```

The composite top denies work and routes `session_poison` immediately when an unauthorized page/compute request is made, while deriving transfer address only from `admitted_begin + (transport_slot << 8)`. It retains exactly six neural M6NF slots, separate M6EG edge slot 6, and one resident bank. Original external page/dispatch producer pins are **still testbench driven**; a real kernel-only MMIO command/IRQ/poll/control ABI for these commands is not implemented yet. Original M02/M03 signed16 numerical source and neural engine are unchanged.

`rtl/m08/tb_m08_m085_axil_neural_candidate.sv` + `tests/test_m08_m085_axil_neural_candidate.py` run a *new real RTL* positive 32-bit AXI-Lite grant followed by actual unmodified neural LIF over the same seven **simulated** 256B DDR records: M6EG original five edges, 6 M6NF neural pages ×4 ticks = 24 dispatches, each actual 256B AXI load + dirty save + independent AXI full readback. Original independently generated signed16 M02/M03 **512 comparison-only** values are checked (128 host-coalesced input-current + 384 actual RTL neural output calculations), never injected as output page states. The 19,200 bus bytes and 24 page markers are **source-simulated**, not hardware measurements. The existing old kernel-lease negative cases and old 512-oracle TB remain unchanged and independently run in regression.

## 4. What STILL blocks a real memory experiment

1. Source-level master/control composition has **no PS connected SmartConnect/HPM0/HP0**; verify boot AFI width, clock/reset, 49-bit physical reachability and exact owner-specific XSA/DT. The 32-bit AXI-Lite endpoint is not a 128-bit HPM0 width converter.
2. No privileged *actual* platform driver, exact compatible binding, DMA mask/IOMMU/translation and `dma_alloc_coherent` generation/readback to prevent arbitrary Linux DDR accesses. `csr_trusted=1` in a TB is not attestation.
3. The composite has external page/dispatch requests, not protected register-controlled sequencing/IRQ/poll/status. The source-only `stop_new_requests` signal does not prove PS interconnect AW/W/B/AR/R drain after timeout, stalled one-sided transaction, external late response or reset isolation. Never free or reuse a DMA allocation on synthetic ACK.
4. No **new** Vivado 2025.2 exact-K26 synthesis/route and full timing, DRC, resource or native review. No owner-approved one-shot new bitstream/physical readback. M08.4 JTAG result stays accepted and untouched.
5. Full six-cell physically matched timestep/event × on-chip/JTAG-host-page/DDR strategy study and real sparse-neuron skipping remain separate.

**Next source milestone inside active M08.5 (not a new milestone number):** a bounded kernel-only page/dispatch/status command ABI with real AXI-Lite backpressure and event service completion, error/poison and clean stop; independently review a real PS HPM0 128→32 and PS HP0 data path in a **new offline Vivado candidate**; concurrently design Linux platform-device `dma_alloc_coherent` ownership and separately verified drain/isolation. No hardware programming without fresh explicit approval.

## 5. Owner PC / VS Code real-RTL verification (no board, no Vivado)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-matched-experiments
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-matched-experiments
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
export PYTHONDONTWRITEBYTECODE=1
command -v iverilog && command -v vvp
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m08_m085_axil_control_candidate.py' -v
python3 -m unittest discover -s tests -p 'test_m08_m085_axil_neural_candidate.py' -v
python3 -m unittest discover -s tests -p 'test_m08_m085_trusted_control_abi.py' -v
python3 -m unittest discover -s tests -p 'test_m08_m085_kernel_dma_lease.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -v
```

All tests must actually execute Icarus, not silently skip. If local tests fail, preserve original output and correct source in a fresh Git commit; no physical test is authorized.
