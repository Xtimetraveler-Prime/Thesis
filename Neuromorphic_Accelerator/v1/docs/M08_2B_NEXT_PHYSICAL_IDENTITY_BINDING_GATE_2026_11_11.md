# M08.2b.3 — first post-deployment physical kernel binding gate (metadata-only)

**After first M08 Linux-managed physical image deployment acceptance on 2026-11-11 America/Denver.** Preserve accepted M08 image **already loaded**. The new safe probe does not call `xmutil`, install overlays, remap a device, change fancontrol or touch MMIO. **Do not unload/reload the successfully working FPGA merely to retest.**

## Evidence prerequisite

Review the accepted [first successful Linux-managed KV260 deployment and reproducible method](M08_2B_KV260_FIRST_PHYSICAL_DEPLOYMENT_ACCEPTANCE_AND_REPRODUCIBLE_METHOD_2026_11_11.md). Owner original archive contains 5/5 SHA-covered originals, active M08 slot 0, M08 configfs overlay, and UIO metadata: identity `uio4 / 0xA0000000/0x1000`, page `uio5 / 0xA0001000/0x1000`. These `uio4/uio5` are **observed at one time, not stable API IDs**; the next probe locates them dynamically by `name`.

Still OPEN: actual `uio_pdrv_genirq` driver symlink ownership for both platforms, first `/dev/uioN` *read* access, physical AXI read data, rollback actually performed. Owner reports fan continuity by direct observation; no continuous fan telemetry attached. Maintain independently powered external cooling and serial recovery for upcoming physical transactions.

## Immediately safe next owner probe — read-only SSH, exact original SHA

On Linux PC VS Code terminal, after pulling latest branch and running tests:

```bash
cd /home/dna/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-kv260-bringup
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-kv260-bringup
git rev-parse HEAD

cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
bash -n scripts/m08_kv260_identity_binding_readonly.sh
bash -n scripts/run_m08_identity_binding_readonly_pc.sh
python3 -m unittest discover -s tests -p 'test_m08_first_identity_binding_readonly.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -p 'test_*.py' -v

bash scripts/run_m08_identity_binding_readonly_pc.sh ubuntu@10.42.0.135
```

The last command streams the first-party Bash probe over SSH, **no sudo/no remote created files**. It asserts real `/proc/device-tree/model` contains KV260, FPGA manager `operating`, `dfx-mgr` and `fancontrol` active, exact M08 configfs overlay, discovers each UIO by its name, requires map0 address and 4096B size and no second map, and requires `/sys/class/uio/uioN/device/driver` symlink to resolve to **`uio_pdrv_genirq`**. It also snapshots current read-only thermal sensors. It never opens `/dev/uioN` or touches physical registers.

On success expect `M08_IDENTITY_BINDING_METADATA_CAPTURE_PASS_NOT_MMIO_APPROVAL`. Its stdout prints the exact new `M08_IDENTITY_BINDING_EVIDENCE_DIR=...` path containing script SHA source, raw original remote stdout/stderr/SSH exit and original independent `99_evidence_sha256.txt`. Verify without modifying original files:

```bash
RECEIPT="/exact/new/m08_2b_identity_binding_READONLY_..._folder"
(cd "$RECEIPT" && sha256sum -c 99_evidence_sha256.txt)
tar -C "$RECEIPT" -czf "$RECEIPT.tar.gz" .
```

Upload the tarball to review. If any asserted condition fails, the runner **returns nonzero but still preserves original raw logs and SHA**: STOP, do not advance to MMIO. There is no reason to reload M08 on a metadata failure.

## Following gate: genuine read-only identity PS-to-PL transaction

After accepting original kernel ownership, carefully review the existing `scripts/m08_path_a_uio_identity_guard.py` and `tests/test_m08_uio_identity_guard.py`. `--mode preflight --expected present` only inspects sysfs metadata. Its separate physical `--mode identity` can **SIGBUS/hang** even with PROT_READ if the real AXI slave does not respond; do not run unreviewed. It requires original exact-authorized operator JSON/SHA, an explicit CLI flag, real KV260 aarch64/model, exact /sys root, driver symlinks, and env consent. **Do not write `rollback_to_starter_kit_verified=YES` unless supported by actual original rollback evidence.** The present original archive documents a rollback method and verified recovery bytes, NOT a physical rollback exercise. Never manufacture a signed YES receipt to get past software guards.

When separately authorized, the first read should observe only these fixed words twice, identity **before** page:
- Identity map0 `0xA0000000`: `0x00 = 0x4D303831`, `0x04 = 0x00010000`, `0x08 = 0` (no DMA), `0x0C = 0`; `0x10..0x1C` build tag default zero **unprovisioned**, not bitstream authentication.
- Page map0 `0xA0001000`: `0x00 = 0x4D303850`, `0x04 = 0x00020002`, `0x08 = 1`, `0x0C = EMPTY 0`, `0x1C = loaded bytes 0`. No host state changes and no `DISPATCH`. Both must be stable across duplicate reads.

UIO `mmap` sees data, **not AXI BRESP/RRESP protocol**. Preserve original live outputs and SHA receipts and review before physical page writes. The later separate 64-word full readback/COMMIT uses `m08_uio_page_protocol.py` after a physically safe write transport is developed and approved, not a guessed `/dev/mem` mapping. Do not claim signed16 inference, DDR, DMA or Loihi Twin acceptance from M08 compute-disabled image.

## Milestone and branch policy

This is still ONE M08.2b physical path. Mark **first PL load accepted** and **exact UIO sysfs metadata accepted**; keep physical identity, 256B readback, stock rollback exercise, and physical compute **open**. All eight M01–M08 workflows must be green on latest branch HEAD; preserve owner local test/evidence as usual. PR #83 DRAFT/UNMERGED.
