# M08.5 — owner-native PS/PL BD receipt review + kernel DMA preflight source (2026-11-21)

**Milestone:** M08.5 (ACTIVE); same `agent/neuromorphic-accelerator-v1-m08-matched-experiments` branch, DRAFT/unmerged PR #95. **No new hardware access, no Linux kernel installation, no FPGA programming, no real DMA transfer and no modification of accepted M08.4 physical evidence.**

## 1. Owner success and what exactly it establishes

The owner reports having run the corrected **first-party quarantined block-diagram-only** Vivado 2025.2 workflow and supplied its original terminal output from:

```text
/home/dna/Thesis_Evidence/M08/m08_m085_pspl_bd_20261122T041029Z_PDYwZWvm
```

The owner ran `sha256sum -c 99_evidence_sha256.txt`, reporting **22/22 OK** (the 7 original stdout/stderr/log/journal/exit/builder/context items, 2 native report/XDC files, and 13 frozen RTL source snapshots). The owner supplied `vivado_exit_status=0`, a native observation record with `status=OFFLINE_BD_TOPOLOGY_ONLY_NEVER_DMA_READY`, K26 `xck26-sfvc784-2LV-c`, **PS HPM0 FPD 128-bit → PL AXI4-Lite 32-bit** via SmartConnect, separate **PL AXI4 128-bit → PS HP0 FPD 128-bit**, PL0 nominal 100MHz, 4KiB `0xA4000000` proposed MMIO decoder, HP0 `0..0x7fffffff` source DDR route, **all four trust/binding/control-route/drain inputs hardwired ZERO**, and native no-synthesis/no-route/no-bitstream/no-driver/no-board fields.

This is **owner-attested native Vivado PS/PL interface topology validation**, NOT independent execution by the assistant, bitstream timing/DRC, physical AFI/DT boot register state, PS DDR access, actual `dma_addr_t`, IOMMU/cache translation, kernel-only MMIO, measured throughput or physical drain evidence. In particular, the original builder `validate_bd_design -force` checks the Vivado IPI model; it does **not** prove the booted KV260 Linux system owns or can reach an actual DDR buffer. The previously failed original `m08_m085_pspl_bd_20261121T205920Z_E7OxxtTo` remains a separate immutable 7/7 SHA first-attempt receipt.

The assistant cannot read the owner's private PC directory. The new independent **read-only receipt reviewer** can be run by the owner against the original bytes to close the extra source/provenance consistency check, without rerunning Vivado or modifying evidence.

## 2. New read-only receipt reviewer

`scripts/m08_m085_pspl_owner_receipt_review.py` performs **22 mandatory SHA-256 rehashes** against the original `99_evidence_sha256.txt` ledger. It rejects unknown/duplicate/absent original entries; malformed ledger, symlinks and file sizes >32MiB; unexpected .bit/.bin files; mismatched first-party original builder and 13 source snapshot files (compared byte-for-byte to the current checkout); nonzero owner Vivado exit; missing unique actual stdout completion line; missing original Vivado 2025.2 log/completion; incorrect fan A12 constraints, owner context/scope, or any missing/extra/changed native report property—especially trust/drain zero, native route not run, bitstream not created and Linux driver not present. It does **not** trust a rehashed modified report as proof of the original source: source snapshot and builder are checked separately.

Receipt test fixtures are **artificial PC-side files**, not another native Vivado execution. `tests/test_m08_m085_pspl_owner_receipt_review.py` mutates recorded hashes, original source snapshots with regenerated hashes, spoofed trust/width/route properties, false native success, wrong exit/version, changed fan/XDC, symlinks and forbidden bit files. A synthetic fixture passing a reviewer only establishes that its *code path* is testable; it is never called original physical or native evidence.

**Owner PC verification (the exact original folder; read-only):**

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-matched-experiments
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-matched-experiments
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
export PYTHONDONTWRITEBYTECODE=1
D="$HOME/Thesis_Evidence/M08/m08_m085_pspl_bd_20261122T041029Z_PDYwZWvm"
( cd "$D" && sha256sum -c 99_evidence_sha256.txt )
python3 scripts/m08_m085_pspl_owner_receipt_review.py --original-evidence "$D"
python3 -m unittest discover -s tests -p 'test_m08_m085_pspl_owner_receipt_review.py' -v
```

Expected successful independent *receipt* review status:
`OWNER_RECEIPT_CONSISTENT_SOURCE_ONLY_NATIVE_BD_NOT_DMA_RELEASE`.
Do not copy/overwrite/rebuild the original folder if this review rejects; return its exact error and keep first original bytes intact.

## 3. New source-only Linux coherent DMA preflight candidate

Added:

- `kernel/m08_m085_dma_contract.h`: **actual portable C** validated DMA descriptor math matching original first-party `rtl/m08/m08_m085_kernel_dma_lease_fence.v`. Requires 256B alignment, exactly 7×256=1792 usable bytes, 32-bit allocation byte field and nonzero 32-bit generation, strict `dma_base + allocation_bytes < 2^49` without overflow, slots `0..6` and ticks `0..3` (slot6 requires tick0). This header rejects invalid or out-of-aperture addresses but is **not authentication** or DMA-API allocation.
- `kernel/m08_m085_dma_preflight.c`: **kernel 6.8 API-shaped**, first-party **source-only, UNBUILT** platform-driver preflight. Uses a unique, not deployed `thesis,m08-m085-preflight-quarantined` OF compatible; checks exact resource size and MMIO **read-only** CAP `M085` / ABI `0x00010001`; requests candidate `dma_set_mask_and_coherent(..., DMA_BIT_MASK(49))`; obtains a page-sized coherent allocation from the SAME bound `struct device`, checks the actual `dma_addr_t` and full page against the pure C guard. Uses `devm_add_action_or_reset` and `dma_free_coherent` only because this is a **never-shared-with-PL** preflight. There are **NO CSR writes, no grant, no work/doorbell, no IRQ, no userspace mapping, no buffer sharing, no firmware manipulation**. It is not registered in a Kbuild/Makefile, has no enabled DT node and has not been compiled against the real KV260 kernel headers. Do **not** build, load, bind or install it on KV260 as part of this source increment.
- `tests/cases/m08_m085_dma_contract_host.c` + `tests/test_m08_m085_kernel_dma_preflight_source.py`: compile the same portable C header with a genuine host `cc`/GCC under `-std=c11 -Wall -Wextra -Werror -pedantic`; exercise 49 descriptor/slot boundary assertions, including `base+allocation_bytes == 2^49` rejection. A mutated strict `>=` boundary compiled as `>` must fail the real C runner. Source tests check exact kernel API names and forbid write/GRANT/user-MMIO APIs. **NOT** a kernel build or proof that live `dma_alloc_coherent` succeeds.

Linux kernel APIs are based on the official Linux 6.8/core DMA API, platform device/driver model and devres documentation:
- https://docs.kernel.org/6.8/core-api/dma-api.html
- https://docs.kernel.org/driver-api/driver-model/platform.html
- https://docs.kernel.org/driver-api/driver-model/devres.html

**Critical lifetime rule:** `dma_free_coherent` is safe in this never-submitted preflight because no PL master can have seen the address. This cleanup MUST NOT be reused once any live GRANT/AXI transfer occurs. Then even `STOP`, CSR SEALED, computation idle, PL reset or a stale low-high ACK do not prove no late AXI R/B: retain/quarantine the buffer until independently verified PS/interconnect outstanding drain and isolation, otherwise do not free and require reviewed recovery.

**Critical device rule:** Setting a 49-bit DMA mask and seeing a coherent allocation on a platform driver does not independently authenticate which live DMA/IOMMU device or HP0 route is active. Actual future deployment must match a reviewed kernel-bound device, XSA, applied DTB, live AFI width/reset, `dma-ranges`, IOMMU, clock/boot/firmware, security and independent control path. A Linux platform node/compatible string alone cannot hardwire `csr_trusted`; the validated quarantined BD deliberately ties it zero.

## 4. Owner PC verification: strictly no board, no kernel install

```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
export PYTHONDONTWRITEBYTECODE=1
command -v cc && command -v iverilog && command -v vvp
python3 scripts/m08_m085_pspl_quarantine_source_check.py --source-only
python3 -m unittest discover -s tests -p 'test_m08_m085_kernel_dma_preflight_source.py' -v
python3 -m unittest discover -s tests -p 'test_m08_m085_pspl_owner_receipt_review.py' -v
python3 -m unittest discover -s tests -p 'test_m08_m085_pspl_quarantine.py' -v
python3 -m unittest discover -s tests -p 'test_m08_m085_axil_managed_neural.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -v
```

**Next separate source gate:** develop a kernel-owned seven-page staging/lifetime API only after the owner confirms original receipt review and platform/DT/XSA/AFI provenance. Design and independently test a genuine PS/PL AXI outstanding monitor/isolation/reset handshake before allowing any driver to GRANT or re-use coherent DMA memory. A new **non-quarantined** RTL/bitstream must never inherit this source hard-zero fixture as production trust, and must require its own separate native K26 synth/route/DRC and owner-authorized physical trial. Accepted M08.4 original evidence and draft PR #95 remain untouched/unmerged.
