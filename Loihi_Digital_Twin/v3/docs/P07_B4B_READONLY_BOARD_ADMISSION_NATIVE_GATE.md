# P07-B.4b — Read-Only KV260 Admission, Bounded DDR Reader and Pristine Mutable Audit

**Status: implemented as additive source, CI PASS, user-local native gate PENDING.** B.4a original P03 CURRENT-input adapter is **user-attested native PASS**, recorded in `docs/P07_B4A_USER_ACCEPTANCE_LEDGER.json`. This milestone develops the next physical bring-up prerequisites only. **No actual Vitis/A53 ELF, board probe, FPGA programming or 27-core inference has been performed.** Draft PR #49 stays unmerged and B2 official MNIST TEST is SEALED. No accepted Track A/B frozen artifacts or original P03/P05 files were modified.

## B.4b1 — Read-only FPD128 + actual P03 shell probe

`software/p07/include/p07_b4b_board_admission.h`, `software/p07/p07_b4b_board_admission.c`, `software/p07/include/p07_b4b_xilinx_platform.h`, and `software/p07/p07_b4b_xilinx_platform.c` add two separately scoped admission operations.

`p07_b4b_probe` reads the **FPD_SLCR.afi_fs PS bus-width register at 0xFD615000** and refuses `dw_ss0_sel[9:8]!=2` (FPD 128-bit). It calls the **unchanged original** `p03_hw_identify` to verify MMIO at **0xA4000000** has exactly accepted shell ID `0x4C543302`, version `0x00010000`, capabilities `0x0001031F`, then original `p03_hw_quiescent` for zero GLOBAL_STATUS and zero PAGE_PENDING_BYTES. The probe itself has no P03 writes, no debug-bank accesses, no DDR writes and no dispatch or page operations. It publishes its receipt only after all checks; **`inference_authorized=0` always**. A matching header/register read does not prove a matched bitstream file SHA, exclusive DDR ownership or a trained model.

`software/p07/p07_b4b_readonly_probe.c` is a **Cortex-A53 standalone probe source**, not a built executable. It binds the original `p03_hw_xilinx_io`, initializes a static P03 adapter, invokes the read-only P07 gate, reports PASS/FAIL on UART via `xil_printf`, then idles. **Do not upload/run it on the board until the actual accepted P05 XSA/BSP, linker map, boot/PL ownership and operator-approved probe plan are independently checked**. No firmware launch/provisioning code for the trained network is present. CI checks this source's host fake-BSP C syntax; it has NOT linked or booted a real Vitis ELF.

## B.4b2 — Bounded, coherent physically referenced DDR reads

`p07_b4b_current_event_read` is the explicitly missing B.4a nonresident DDR-read callback. Its reader is initialized only after a successful read-only probe receipt. A read is legal **only** for aligned 32-bit words within the event0 `+0x54000` or event1 `+0x58000` arrays of logical cores **0–26**, backed by `[0x40000000,0x40D80000)` with 512KiB record stride. It refuses static synapse/neuron memory, descriptors `0x43FE0000`, staging `0x43F00000`, result mailbox `0x43FF0000`, P03 MMIO and unrelated addresses. It leaves the caller's output word untouched on errors.

`p07_b4b_xilinx_read_phys` is a new bare-metal `Xil_In32` transport for the FPD width register and B.4b bounded event areas only; production builds require `__aarch64__` and perform an ARM `dsb sy` barrier. The strict native fake BSP uses the explicit `P07_B4B_TEST_HOST_BSP` build flag and **cannot be mistaken for physically linked firmware**. The `p07_b4b_current_event_read` allowlist complements the original B.4a `hw->io.invalidate_range` + barrier before reading nonresident CURRENT: *the new reader does NOT omit or silently replace the accepted cache-invalidation prerequisite*. Even together these primitives cannot establish live DDR memory-type/shareability attributes; physical MMU/OS ownership remains a board NO-GO.

## B.4b3 — Read-only 27 × 5 mutable P02 snapshot integrity audit

`software/p07/include/p07_b4b_mutable_audit.h` and `software/p07/p07_b4b_mutable_audit.c` validate each logical core's **five original P02 mutable sections** by independent, caller-provided trusted section CRC32 expectations. This is a read-only *equality audit*, NOT a reset routine and NOT cryptographic origin authentication.

| Section | P02 record offset | Bytes/core |
| --- | ---: | ---: |
| Packed signed24 neuron state/current/refractory | `0x05000` | `0x02000` |
| Event bank 0 | `0x54000` | `0x04000` |
| Event bank 1 | `0x58000` | `0x04000` |
| Trace | `0x5C000` | `0x08000` |
| Packet | `0x64000` | `0x08000` |
| **Total** | five regions | **`0x1A000` = 106,496** |

The audit checks 27 registered cores, 3 empty resident slots, zero current/NEXT counts, a zeroed B.3a tick/dispatch ledger, original P03 quiescence and a provided coherent 32-bit callback. Before each section it invokes the accepted P03 invalidate/barrier callbacks, reads **every** aligned word, computes IEEE CRC32 over the original LE bytes, compares against **independently trusted** expected CRCs, and publishes a final read-only receipt only after all checks. Total: **135 physical sections, 2,875,392 bytes**. On failure the receipt stays unchanged and (when supplied) a first bad region/address is returned. A distinct `p07_b4b_xilinx_read_mutable` Xilinx callback only permits these five regions, NEVER unrestricted record writes.

**Critical trusted-input boundary:** The physical B2.4 frozen 27 × 512KiB initial records and externally verified B2.5 source integrity must supply the expected CRCs. This task does **not** open, change or repack those local frozen files. It **does not** make up CRC expectations or replace them with a blanket all-zero assumption. All source DDR initialization writes must be complete, cache-cleaned and independently admitted *before* invalidating/reading physical snapshot sections. Reinitializing a C pager is not a physical neuron reset. Fresh-image state restoration and audit must precede every later physical inference image.

## B.4b ELF/linker-map guard

`scripts/p07_b4b_elf_probe_admission.py` requires the **actual linked AArch64 little-endian EXEC ELF**, actual `-Wl,-Map=` linker map, GNU `readelf -W -h`, `readelf -W -l`, `nm -S --defined-only` and real BSP physical stack/heap extents. It checks:

- AArch64, little-endian, executable ELF instead of an x86 test executable or unlinked source.
- Required read-only probe functions `main`, `p07_b4b_probe`, `p07_b4b_xilinx_read_phys`, `p03_hw_init`, `p03_hw_identify`, `p03_hw_quiescent`, `p03_hw_xilinx_io`.
- A static full-sized (≥65KiB) `hw` P03 adapter BSS symbol **contained in a true ELF LOAD region**, a linker map with text/BSS and probe entry, and mandatory separately declared real physical stack and heap.
- No ELF program LOAD/stack/heap overlaps with original `[0x40000000,0x44000000)` P02 reserved 64MiB (including B1.3 staging/descriptor/result), P03 MMIO `[0xA4000000,0xA4001000)` or one another. It fails closed if the actual ELF/map doesn't exist. It **does not** authorize inference, validate physical Linux exclusion, the real bitstream SHA, MMU attributes or independent source-spike provenance.

**Future user-owned Vitis workflow (not performed or tested here):** start with the accepted P03/P05 K26 BSP/XSA and Cortex-A53 standalone domain. Create an application from `p07_b4b_readonly_probe.c`, `p07_b4b_board_admission.c`, `p07_b4b_xilinx_platform.c`, the **original** `p03_hw_adapter.c` and `p03_hw_xilinx_io.c`, with original P03/P07 headers and Xilinx standalone BSP. Generate a real linker map. Inspect the BSP/ELF actual stack/heap symbols; provide their verified physical boundaries to the following read-only CLI:

```bash
# Use ACTUAL ELF, linker map, and BSP physical extents; these are PLACEHOLDERS.
python scripts/p07_b4b_elf_probe_admission.py \
  --elf /actual/path/p07_b4b_readonly_probe.elf \
  --linker-map /actual/path/p07_b4b_readonly_probe.map \
  --stack 0xACTUAL_STACK_START:0xACTUAL_STACK_END \
  --heap 0xACTUAL_HEAP_START:0xACTUAL_HEAP_END
```

Only after a real ELF and operator-approved read-only live shell probe should the later stage design/prove a full inference firmware image. This read-only probe and ELF guard do **not** check the full future B.4 image runner's large B.4a 442,368-byte CURRENT scratch, B.3c1 dual 98,432-byte frame buffers, B.3c2 raw capture arena, 4,096-word temporary capture, source-spike evidence buffers, heap/stack and 27 × 512KiB exclusive DDR backing. The **later inference ELF needs its own separate complete memory audit**.

## Native verification, CI, physical hard stops

**New tests:**

- `tests/native/p07_b4b_admission_harness.c` and `tests/test_p07_b4b_board_admission.py`: link original P03 C adapter with a fake Xilinx read-only BSP and the new gate, verify exactly matching FPD128/shell/version/capabilities/idle and **zero P03/DDR writes**, no unpublished output on faults. Test bad FPD width, wrong shell, busy PL, nonzero page pending, failed original P03 bus reads and forged inference-authorization receipts. Test exact 27-core event-bank bounds, all forbidden address categories, output immutability, failed word reads, and original physical stride. Extend to the full 135-section *synthetic patterned* mutable CRC audit, corruption injection, nonempty event counts, resident-slot dirty state, failed word reads and unchanged prior receipts. These synthetic CRCs are NOT from trained B2 frozen files.
- `tests/test_p07_b4b_elf_probe_admission.py`: independently generated synthetic ELF program-header/symbol/map fixtures, rejecting wrong architecture, endian, ELF type, missing required symbols, truncated P03 BSS, mismapped BSS, conflicting stack/heap and protected P02/P03 memory extents. This is only an **offline parser regression**, NOT an actual A53 ELF.

**Independent CI evidence:** [P07-B.4b native gate, run #39455844312](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/39455844312) strict C11 `-Wall -Wextra -Werror -pedantic` real original P03 adapter C + host Xilinx shim, **ASan+UBSan** and parser smoke: SUCCESS, native marker `P07_B4B_READONLY_A53_ADMISSION_NATIVE_PASS=1`; ELF fixture marker `P07_B4B_FAKE_ELF_PARSER_PASS=1`. The read-only standalone A53 probe source is **syntax-checked only with a fake BSP**, not built into a real executable. Accepted B.4a and B.3c2/3 CI also remain green. A real ELF and physical verification are NOT complete.

### Commands to reproduce on VS Code PC

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p07-b-scaled-physical-inference
git pull --ff-only origin agent/v3-p07-b-scaled-physical-inference
git rev-parse HEAD

source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b4b_board_admission.py \
  tests/test_p07_b4b_elf_probe_admission.py

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b4a_current_ingress.py \
  tests/test_p07_b3c23_hw_integration.py \
  tests/test_p07_b3c3_elf_admission.py \
  tests/test_p07_b3c_packet_bridge.py \
  tests/test_p07_b3b_event_owner.py \
  tests/test_p07_b3a_pager.py \
  tests/test_p07_b2a_ingress.py \
  tests/test_p07_b2b_transaction.py \
  tests/test_p07_b2b_packets.py
```

### Physical B.4 NO-GOs that this development intentionally does not clear

1. **No actual A53 build or live KV260 admission result.** XSA/bitstream digest, BSP linker geometry, OS/DDR exclusivity, MMU/cache memory attributes, PS/PL shell revision and FPD128 physical probe pending; zero DDR writes must be confirmed on the board.
2. **No real trained 27-core frozen-P02 boot provisioning** or verified per-image reset. 135-section audit requires independently frozen trusted CRCs, correct cache clean/ownership and actual DDR scan before every image. A read-only scan does not restore state.
3. **No independent HLS source-neuron emission evidence.** Original P03 64-bit packet word does not expose a complete source-neuron spike list; B2b full-fanout validation must never reconstruct missing source origins from routed packets alone. No real 27-core source-graph parity proof until this hardware observability gap is resolved.
4. **No original trained signed24 27-core full-network inference or trained B2.4 physical oracle parity**, no 26-tick readout/classifier, no P07-B.5 TRAIN-derived numerical corpus, no measurement or energy claim.
5. **B2 official MNIST TEST SEALED, no PR merge, no FPGA programming or board ownership claim** without separate user-approved next gates.

**User-native B.4b pass is pending.** Stop after the supplied tests; use their results to decide on an actual ELF/project bring-up plan. No automatic advancement to physical KV260 execution.
