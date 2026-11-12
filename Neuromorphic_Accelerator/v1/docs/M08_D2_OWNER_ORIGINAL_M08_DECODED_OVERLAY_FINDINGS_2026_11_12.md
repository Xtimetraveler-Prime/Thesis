# M08 D2 — owner-original decoded M08 UIO DTBO evidence and runtime configuration boundary

**2026-11-12.** Owner uploaded three genuine PC-side M08-only evidence files from the local new folder `m08_d2_OWNER_DTBO_OFFLINE_o22ssz1_`. Files were independently opened and byte SHA256-hashed, and JSON/DTS source cross-checked. The original failed image remains **QUARANTINED**, stock K26 remains unmodified. This record is not hardware retry approval.

## Original owner file receipts, verified from bytes

| File | SHA256 | Native/proven contents |
| --- | --- | --- |
| `00_review.json` | `469c7bf15a1ab6988e09235e9764f9824c2a4f9523cbd383b0d61bbafdc30b45` | status `ORIGINAL_M08_DTS_COPY_CREATED_STOCK_ABSENT_NO_BOARD`, `m08_only=true`, `stock_dtbo_compared=false`, `originals_unchanged=true`, `dtc_exit_status=0`, `hardware_retry_authorized=false`; original binary SHA `2b7798053d10415ef528d4abbbdcb5251cd0dee4845c3288de2a3ef7bd2e75ed` rechecked after native `dtc` |
| `12_m08.dts` | `772c6b0bb299d0bf0665cc79063a198d331dc9543249e5c62f7f0cff18d9aabe` | 961-byte real decompiled original overlay; SHA exactly equals the review JSON `decompiled_sha256` |
| `22_m08_dtc_stderr.txt` | `ec72006cc28cdf378b01e230b680386c65a00534107b15cdc47b789b99de48a8` | exactly one warning: `Warning (resets_property): /fragment@0/__overlay__:resets: Could not get phandle node for (cell 1)`, attributable to unapplied symbolic reset phandle |

The available **text receipt** says the original binary was independently rehashed before and after native `dtc`, but binary DTBO bytes were not uploaded into this chat; do not falsely describe that binary as rehashed here. Missing stock DTBO remains missing; no stock PS clock or AFI ownership value has been proved.

## Decoded original overlay — binary-specific conclusion

`fragment@0` targets `fpga_full` through `__fixups__`. It configures `firmware-name = "m08-v1-fan-page-uio-review.bit.bin"` and exactly four reset specifiers, `0x74`, `0x75`, `0x76`, `0x77`, with `zynqmp_reset` symbolic fixups at offsets 0/8/16/24. `fragment@1` targets `amba` through another symbolic fixup. It declares `#address-cells=<2>`, `#size-cells=<2>` and two `generic-uio` nodes: `m08-identity@a0000000` (4KiB) and `m08-page@a0001000` (4KiB). No other UIO resource is in the decoded file.

**The actual original decoded deployed DTBO does not contain any** `assigned-clocks`, `assigned-clock-rates`, `clocks`, `clock-names`, `xlnx,fclk`, `xlnx,afi-fpga`, or `config-afi` properties anywhere. This **independently confirms a missing declaration in this particular M08 overlay**, not just the original Python template.

AMD's FPGA Manager full-reconfiguration documentation includes a separate PS–PL configuration fragment with an AFI `config-afi` node, fabric clock `assigned-clocks`/`assigned-clock-rates`, then PL peripheral driver nodes with clock handles. AMD's 2025.2 device-tree generator similarly can derive these nodes from the hardware description. That does **not** establish these nodes were required for the user's stock boot environment; the still-missing base DTB and boot firmware may provide them. We have not read failure-time PS PL0 `CLKACT`, reset, HPM0 AFI or ATB4 state. No first-failing AXI transfer trace survived. Avoid declaring a verified root cause.

**Second deployment-architecture question discovered:** M08's two `generic-uio`
nodes are placed in a **separate `&amba` overlay fragment**, NOT as children
under `&fpga_full`. The Linux FPGA-region binding describes safe sequencing
(bridge disable → program → bridge enable → overlay accepted → *region child*
devices populated). Its child-device ordering assurance cannot simply be
extended to independent sibling `&amba` fragment nodes without checking
the actual Linux/XRT/dfx-mgr overlay notifier ordering and dependencies.
The downloaded original does NOT declare FPGA bridges for fail-closed MMIO
isolation, and the `generic-uio` nodes lack `clocks` dependencies. These are
**static topology/integration risk factors only**; do not assert that UIO
was bound before program, that a race occurred, or that Linux ordering
violated its contract. The original board did reach a first identity read.
Ref: Linux FPGA region bindings:
https://kernel.googlesource.com/pub/scm/linux/kernel/git/stable/linux-stable/+/61b57d35396a4b4bcca9944644b24fc6015976b5/Documentation/devicetree/bindings/fpga/fpga-region.yaml

**Additional important constraint:** Even if properly configured, the M08 original PL-clock-dependent SmartConnect and identity slaves can fail to respond if `pl_clk0` disappears. AMD's 2025 proposal for ZynqMP AXI Timeout Block driver describes timeout events as capable of hanging Linux, with finite protection: it is not proof that enabling a driver in a future overlay alone guarantees bounded recovery. The relevant PS-side ATB instance is 4 for `M_AXI_HPM0_FPD`, but that **does not imply** it was enabled at the failed M08 event. A corrected safe architecture must explicitly handle absent PL clock with upstream independent timeout/isolation and verified failure handling before physical read attempts.

## First-party added review/test work

- New `scripts/m08_d2_verify_original_m08_decoded_overlay.py`: PC read-only, requires all three genuine original text files in one directory; checks exact SHA-pinned M08 DTS, status, original DTBO SHA recorded in review JSON, original `dtc` success, exact symbolic fixups, two original UIO address windows, absence of clock/AFI directives, and the one expected unattached `resets_property` warning. Prints JSON only, no file or hardware writes. Rejects missing/stale/changed/partial input or any unexpected clock/AFI declaration. Result explicitly refuses hardware/runtime signoff.
- New `tests/test_m08_d2_verify_original_m08_decoded_overlay.py`: **synthetic** original-shaped static fixture, SHA drift, unexpected `dtc` warning, counterfeit hardware approval and symlink refusals.
- Original strict four/optional six timing report source audit and clock/AFI source contract work remain in place. This is a **source-to-native-binary closeout**, not a runtime test.

Owner PC verification:

```bash
cd /home/dna/Git/Thesis
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-kv260-bringup
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-kv260-bringup
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m08_d2_verify_original_m08_decoded_overlay.py' -v

EVIDENCE="$HOME/Thesis_Evidence/M08/m08_d2_OWNER_DTBO_OFFLINE_o22ssz1_"
python3 scripts/m08_d2_verify_original_m08_decoded_overlay.py --evidence-dir "$EVIDENCE"
python3 scripts/m08_d2_offline_ps_pl_contract_audit.py --deployed-m08-dts "$EVIDENCE/12_m08.dts"
```

## D2 priority after this finding

Do not keep looking for the original stock DTBO in the same unsuccessful PC directories. Next offline primary proof gaps: stock/base DT and firmware/clock-manager *configuration ownership* from prior immutable build evidence if available, whether HPM0 width/AFI will match the M08 128-bit design, and independent PS-side bounded transaction handling including ATB instance 4 behavior. Do not fabricate a base DT or claim `&fpga_full` children magically imply `&amba` clock activation. If stock evidence stays unavailable, preserve UNKNOWN rather than inventing values.

**STOP unchanged:** No old M08 bit.bin reload, MMIO, SSH to the board, device registers, JTAG, fan change, `xmutil`, Linux overlay installation or hardware retry. D3–D5 remain STOP pending bounded upstream safety plus owner clearance.

References: AMD FPGA manager PS/PL example https://xilinx-wiki.atlassian.net/wiki/spaces/A/pages/18841847 ;
AMD 2025.2 device-tree generator https://github.com/Xilinx/system-device-tree-xlnx/blob/xlnx_rel_v2025.2/device_tree/data/device_tree.tcl ;
ZynqMP ATB driver 2025 patch discussion https://lists.infradead.org/pipermail/linux-arm-kernel/2025-May/1030828.html .
