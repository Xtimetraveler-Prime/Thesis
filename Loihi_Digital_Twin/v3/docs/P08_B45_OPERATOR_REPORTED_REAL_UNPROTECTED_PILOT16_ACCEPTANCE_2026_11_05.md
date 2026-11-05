# P08-B4.5 — 2026-11-05 operator-reported real unprotected pilot16 acceptance

This document records a user-supplied **488-line PC terminal transcript**,
not raw independent-report JSON or independent GitHub access to operator-local
DDR capture files. The accepted original B3, P03, 1024 B4.4 baseline and
full TEST sealing remain unchanged.

| Physical pilot | Operator-reported source admission | Original PLL/gates | Independent post-run numerical and backup verification | Independent JSON path / SHA256 |
| --- | --- | --- | --- | --- |
| `once` 16 images | PASS, new A53 ELF SHA `d528c5a7168a7c119668e2db957bf66d5271ca6edae85115eefa694bc390fbab` | dedicated A53 accounted, FPD/LPD128, original P03 programmed, six original DDR transfers byte exact, strict 16 terminal, 27 post-run backup records captured | `P08_B45_PERF_PILOT16_INDEPENDENT_SCALAR_FNV_AND_POSTBACKUP_PASS=1` | `/home/dna/Thesis_Evidence/p08_b45_perf_once_independent_20261105T154923Z.json`; `7ab975d3c062df2606357080c1eeda0904ea8aaba0aed4c02fda8ce1140ecdca` |
| `unchecked` 16 images | PASS, new A53 ELF SHA `a59f6ce8e158f4b813ffb0a63d42d80675a8acc504a875a060c36d57fbcf269f` | dedicated A53 accounted, FPD/LPD128, original P03 programmed, six original DDR transfers byte exact, strict 16 terminal, 27 post-run backup records captured | `P08_B45_PERF_PILOT16_INDEPENDENT_SCALAR_FNV_AND_POSTBACKUP_PASS=1` | `/home/dna/Thesis_Evidence/p08_b45_perf_unchecked_independent_20261105T160411Z.json`; `5f29cda8661cad64fe39231d42a84c3293bef96af6c7fe74c9c74b466a2195aa` |

Transcript records `P03_2C_PS_FPD_AXIFS_RAW=0x00000A00` and
`P03_2C_PS_LPD_AXIFS_RAW=0x00000200`, both 128-bit decoded.
Both sessions gave expected XSDB `rst -processor` unpredictable-reset
vector warning; neither aborted. Both sessions reported mandatory
reboot after destructive JTAG and denied all security-equivalence
claims. The transcript does **not** contain the original JSON data, so
it does not independently verify per-image latency values; no 1024
speedup or protected immutable DDR is asserted.

The new **full1024** runner requires both external independent JSON
files to be present and to match the exact digests and JSON source
fields above, in addition to reauthentication of original B3/B4/B44
physical and 64-shard TRAIN-derived reference. This prevents a raw
terminal marker, missing pilot report or synthetic dry-run from becoming
authorized full1024 physical admission. Raw output files are not
uploaded or committed; they remain on operator PC.

Next: separate genuine full1024 `once` and `unchecked` Vitis builds,
PC source/ELF/oracle preflights, dedicated separately approved two
physical sessions with atomic progress snapshots and independent
all1024 numerical/27 backup post-run revalidation. Stop if old pilot
JSON digest mismatches (do NOT change pins or source files to bypass).
