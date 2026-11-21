> **AUTHORITATIVE M08 D3.D.2E PHYSICAL ACCEPTANCE — 2026-11-20: PASS; SUPERSEDES historical pending entries below.** The owner reran **only the read-only** independent auditor on immutable FIRST original native `m08_d3d2e_queue_GFz0SbiC` (bit SHA `2c443c3d80e86e5e9488b457110a45b0db96881016e9f87a5c801a72ec7527dc`) and FIRST original physical run `m08_d3d2e_queue_HW_4HQkm7rN`: six new auditor regression tests `OK`, **6/6 original physical receipt SHA rows OK**, exact status `M08_D3D2E_PHYSICAL_M06_17_QUEUED_EVENT_128_BUCKET_384_NEURAL_ACCEPTED`; 17 individual fabric FIFO events accepted/serviced, 128 live input buckets zero before service, four clocked ordered service barriers **5/5/4/3**, 17 high-watermark/depth0; **128 input + 128 voltage + 128 spike decisions + 128 recurrent current = 512/512 exact hardware numerical parity**. No second FPGA programming or owner-original evidence change. Earlier standalone audit false-negative was corrected source-only (literal backslash-n vs actual newline); independent original re-audit now PASS. **D3.D.2E PHYSICAL COMPLETE** only for synchronous PS-PL0 JTAG M06 FIFO/tick service; async/DMA/DDR/HLS/power/throughput not established. **M08 OPEN, M09 PLANNED**. [Owner original physical acceptance](M08_D3D2E_OWNER_PHYSICAL_ACCEPTANCE_2026_11_20.md). Next bounded step D3.D.3 source-only memory ownership/page staging on **new branch**, no DDR/board programming without separate gate. **PR #93 draft/unmerged**.

# M08 D3.D.2E — first-original owner KV260 physical run and read-only audit repair (2026-11-20)

**Evidence-source status:** the owner pasted genuine Vivado 2025.2 first physical JTAG stdout in chat, recorded on 2026-11-20 **16:54:56–16:55:20** local. This is **a real physical execution**, NOT an independent fully accepted receipt **yet**. The stage completed all physical checks and wrote original evidence, but the Python independent auditor returned a **false negative due to searching for literal backslash-n characters** instead of actual newlines. The fix is source-only; preserve first originals unchanged and **NEVER reprogram/re-run the physical shell for the audit fix**.

## Immutable first original references

- First original exact owner native image folder: `/home/dna/Thesis_Evidence/M08/m08_d3d2e_queue_GFz0SbiC`. Image SHA256: `2c443c3d80e86e5e9488b457110a45b0db96881016e9f87a5c801a72ec7527dc`, size 7,797,844 bytes. Exact original native image acceptance printed `image_specific_gate=ACCEPTED`, native ledger `original_12_sha_entries_verified=true`, 7 reviewed DRC vendor/debug warnings, WNS +1.844 ns and WHS +0.010 ns, all inside the physical launcher **before programming**.
- **FIRST original physical HW evidence directory**: `/home/dna/Thesis_Evidence/M08/m08_d3d2e_queue_HW_4HQkm7rN`. The shell created the six original files and printed their **six SHA256 ledger `OK`** markers: `00_executed_source.tcl`, `01_jtag_m06.log`, `02_jtag_m06.jou`, `03_exit.txt`, `10_m06_tickqueue_golden.hex`, `80_m06_tickqueue_hw_parity.txt`. No original evidence may be changed/rehashed/overwritten to repair the auditor.

## Real physical JTAG result

- Actual JTAG target `localhost:3121/xilinx_tcf/Xilinx/XFL1RK5M5ILQA`; device `xck26_0` (also `arm_dap_1` enumerated); exactly one `M08_D3D2E_PROGRAM_START` and one `M08_D3D2E_PROGRAM_COMPLETED`. Vivado found `hw_axi_1`.
- JTAG BRAM wrote and read **55AA22DD**, passed; 32-neuron M32Q image ID **4D333251** and version **00060000** passed.
- **17 original distinct signed external events accepted**, all **128 input buckets zero before SERVICE**, four in-order clocked service barriers individually reported `M08_D3D2E_TICK_SERVICE_PARITY|0|5`, `|1|5`, `|2|4`, `|3|3` (17 total). **17 accepted / 17 serviced / depth0 / high watermark17 / completion mask0xF** passed the Tcl checks.
- **All 32 per-neuron event-current checks passed**, reconstructing **128 hardware current buckets**; **all 32 per-neuron membrane, spike-mask and synaptic-current trace checks passed**, corresponding to **128 membrane voltages, 128 spike decisions, 128 recurrent currents**. The original logged final marker was `M08_D3D2E_PHYSICAL_M06_128_EVENT_128_VOLTAGE_128_SPIKE_128_SYN_CURRENT_PASS`. **512 numerical comparisons passed in Tcl.**
- Original owner hardware evidence `99_evidence_sha256.txt` had all **6 out of 6 OK**, but the separate auditor subsequently printed `M08_D3D2E_PHYSICAL_RECEIPT_REJECTED: missing/duplicated physical per-tick SERVICE receipt`. Thus **the independent auditor result is NOT YET PASS**; hold final physical acceptance until read-only re-audit.

## Diagnosis and fix

Old `scripts/m08_d3d2e_queue_physical_audit.py` required `log.count(f"...{per_tick[t]}\\n") == 1`, where the string **contained a literal backslash and n**, not an actual newline. User's real original stdout shows exactly one normal newline-terminated event for each service tick, and all four pass. This was a *test harness text-matching mistake*, not an observed hardware service or numerical discrepancy.

New `verify_tick_service_log(log,per_tick)` extracts **all real line-start tick SERVICE receipts** from `splitlines()` and compares them with the independent M06-derived **four ordered exact markers**. It fails closed on missing, duplicate, out-of-order, altered or unexpected tick count. `tests/test_m08_d3d2e_physical_reaudit.py` adds synthetic six-file audit acceptance and per-tick/order/mutation negative tests, all with **mocked native gate** and **no board access**. Code changes must be confirmed by current CI and owner-local original re-audit before final acceptance.

## Owner READ-ONLY repeat audit — NO JTAG, NO VIVADO, NO REPROGRAMMING

```bash
cd ~/Git/Thesis
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-d3d2e-tick-event-queue
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-d3d2e-tick-event-queue
cd Neuromorphic_Accelerator/v1
export PYTHONDONTWRITEBYTECODE=1

RUN="$HOME/Thesis_Evidence/M08/m08_d3d2e_queue_GFz0SbiC"
HW="$HOME/Thesis_Evidence/M08/m08_d3d2e_queue_HW_4HQkm7rN"

# No hardware, no JTAG, no Vivado, no owner evidence writes.
python3 -m unittest discover -s tests -p 'test_m08_d3d2e_physical_reaudit.py' -v
python3 -m unittest discover -s tests -p 'test_m08_d3d2e_physical_boundary.py' -v
(cd "$HW" && sha256sum -c 99_evidence_sha256.txt)
python3 scripts/m08_d3d2e_queue_physical_audit.py --run-dir "$RUN" --hw-dir "$HW"
```

**Required for first independent acceptance:** all six first-original SHA rows print OK, the auditor exits 0 and prints `status=M08_D3D2E_PHYSICAL_M06_17_QUEUED_EVENT_128_BUCKET_384_NEURAL_ACCEPTED` in its JSON (with proper double quotes), and all 512 original numerical matches + tick-service counters appear in original evidence. **Do not rerun the earlier `run_m08_d3d2e_queue_physical_once.sh` or recreate the evidence**; if read-only audit rejects again, preserve both originals and diagnose from the error.

Scientific boundary: *physical synchronous FPGA FIFO, separate service-clock boundary in PS-requested PL0, four ordered logical tick barriers and complete M06 neural parity*; does **not** establish asynchronous clock-independent event streams, physical M05 HLS, M06 DDR, DMA, performance, power, or Loihi hardware equivalence. Draft PR #93 unmerged; M08 OPEN; M09 PLANNED.
