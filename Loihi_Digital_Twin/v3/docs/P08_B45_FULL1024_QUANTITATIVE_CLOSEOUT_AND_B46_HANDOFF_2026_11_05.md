# P08-B4.5.5: physical full1024 quantitative closeout and B4.6 handoff

**Operator-supplied independently verified physical runs, 2026-11-05 local (2026-11-06 UTC).**
Both V2 once and unchecked runs independently passed all 1024 original
software-reference predictions, ten output spike vectors, full 26tick
1010-neuron FNV, per-frame A53 timing/reset receipts, and 27 post-run
physical backup context endpoint readbacks.

## Original signed reports (SHA-256)

Original B4.4 whole-image service timing:
p08_b4_4_first1024_one_session_descriptive_20261102T191317Z.json
SHA 4e0abf43dafab145b2dde6846d5504470c3d122da80923c34441e82877881b81

Original B4.4.2 separately instrumented reset:
p08_b44_profile1024_independent_20261103T100712Z.json
SHA 47f25cada89dd9220636fbb9539aba5bf0d7705ea3788fdc3ebd1d85f1145cfa

New real V2 once independent:
p08_b45_perf_once_full1024_V2_verified_20261106T005213Z.json
SHA 06a007b73cb3ff31c02910224e28690215bded5bdb401973e6a0347e44d0d65a

New real V2 unchecked independent:
p08_b45_perf_unchecked_full1024_V2_verified_20261106T005240Z.json
SHA 68655383c582577986d7bdd253b21ecf1c933d234136d51b7b5076591c63cf79

All share the original frozen 64-shard full1024 scalar oracle SHA
7e564d188651aeabdc284328ea65705bcb0b5571468b9f70d5dcacaa3f5493b8
and accepted B4.2 independent numerical physical report SHA
297114489eb8312733a2e2597f0ee0567f9868552d2bc71d0dd425139368b032.

| Metric | Original | Once | Unchecked |
| --- | ---: | ---: | ---: |
| Reset median ms | 5826.767549 | 8.7669975823 | 8.7320072328 |
| Reset P95 ms | 5826.881051 | ~8.7774 | ~8.7425 |
| Whole-image service median ms | 13034.111501 | 7225.137459 | 7222.415632 |
| Whole-image service P95 ms | 13167.109029 | ~7360.6956 | ~7357.6732 |
| Descriptive reset median ratio | 1x | ~664.63x | ~667.29x |
| Descriptive service median ratio | 1x | ~1.804x | ~1.805x |

Original B4.4.2 measured approximately 99.84% of its reset ticks
in the two complete source+destination SHA scans. Context memcpy was
~7.025ms. This strongly explains why the reset now takes ~8.7ms.

**Scope:** exactly 1023 ordinary frames per run with final selected
trace ordinal 1023 audited separately. Original reset was a DIFFERENT
instrumented physical session and executable from original whole
service. Each optimized variant is a SINGLE independently accepted
physical session, not a repeated paired trial. Therefore the ratio
of session medians is DESCRIPTIVE, not a significance test, pure
FPGA neural arithmetic speedup or energy efficiency. All original
backup records were equal after each optimized run, but transient
writes / hardware DDR write protection were not disproven/proven.
The unchecked approach is a reduced-integrity research bound.
Official MNIST TEST remains SEALED_NOT_ACCESSED.

## PC-only next deliverable: exact residual six-phase A53 reconstruction

New branch agent/v3-p08-b45-comparison-and-b46-handoff contains
scripts/p08_b45_full1024_latency_synthesis.py. It refuses unsigned/
changed independent reports. Rechecks original accepted full1024 model
provenance, both new raw physical 1024x256B service timing sidecars,
both raw reset-profile sidecars, original CRC and all six additive,
monotonic A53 CNTVCT phase boundaries using actual session CNTFRQ.
Emits NEW external never-overwritten JSON and Markdown with phase
medians, shares of same-session total ticks and dominant remaining
A53 mixed software+PL service interval. NO physical operations.

### PC VS Code: fetch and run native tests

~~~bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p08-b45-comparison-and-b46-handoff
git pull --ff-only origin agent/v3-p08-b45-comparison-and-b46-handoff
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
PYTHONPATH="$PWD/scripts:$PWD/src" python3 -m pytest -q -rs \
 tests/test_p08_b45_full1024_latency_synthesis.py \
 tests/test_p08_b45_perf_full1024_independent_cli.py \
 tests/test_p08_b45_full1024_reset_bind_repair.py
~~~

### Original four signed local reports

~~~bash
export B45_ORIGINAL_SERVICE="$HOME/Thesis_Evidence/p08_b4_4_first1024_one_session_descriptive_20261102T191317Z.json"
export B45_ORIGINAL_RESET="$HOME/Thesis_Evidence/p08_b44_profile1024_independent_20261103T100712Z.json"
export B45_ONCE_REPORT="$HOME/Thesis_Evidence/p08_b45_perf_once_full1024_V2_verified_20261106T005213Z.json"
export B45_UNCHECKED_REPORT="$HOME/Thesis_Evidence/p08_b45_perf_unchecked_full1024_V2_verified_20261106T005240Z.json"
sha256sum "$B45_ORIGINAL_SERVICE" "$B45_ORIGINAL_RESET" \
 "$B45_ONCE_REPORT" "$B45_UNCHECKED_REPORT"
~~~

Expect the exact four SHA above IN THAT ORDER; do not modify an
accepted report to bypass a mismatch.

### Locate accepted original V2 physical capture folders

If the terminal still has them:

~~~bash
declare -p P08_B45_FULL_ONCE_PHYSICAL P08_B45_FULL_UNCHECKED_PHYSICAL
~~~

If not, read-only discovery:

~~~bash
find "$HOME/Thesis_Evidence" -maxdepth 1 -type d \
 -name 'p08_b45_perf_*_full1024_V2_physical_*' -print
~~~

Export the two variables to the actual successful original
once and unchecked V2 evidence directories. Do not choose the
earlier failed V1 capture; the tool separately rehashes the
two original 256KiB sidecars against each signed independent JSON.

~~~bash
test -s "$P08_B45_FULL_ONCE_PHYSICAL/performance1024_capture/timing1024_physical.bin" &&
test -s "$P08_B45_FULL_ONCE_PHYSICAL/performance1024_capture/reset_profile1024_physical.bin" &&
test -s "$P08_B45_FULL_UNCHECKED_PHYSICAL/performance1024_capture/timing1024_physical.bin" &&
test -s "$P08_B45_FULL_UNCHECKED_PHYSICAL/performance1024_capture/reset_profile1024_physical.bin" &&
echo B45_GENUINE_RAW_TIMING_AND_RESET_CAPTURES_PRESENT=1
~~~

### Fresh independently audited quantitative output

~~~bash
export B45_SYNTHESIS_JSON="$HOME/Thesis_Evidence/p08_b45_full1024_synthesis_$(date -u +%Y%m%dT%H%M%SZ).json"
export B45_SYNTHESIS_MD="$(dirname "$B45_SYNTHESIS_JSON")/$(basename "$B45_SYNTHESIS_JSON" .json).md"
PYTHONPATH="$PWD/scripts:$PWD/src" python3 \
 scripts/p08_b45_full1024_latency_synthesis.py \
 --original-service "$B45_ORIGINAL_SERVICE" \
 --original-profile "$B45_ORIGINAL_RESET" \
 --once-report "$B45_ONCE_REPORT" \
 --unchecked-report "$B45_UNCHECKED_REPORT" \
 --once-evidence "$P08_B45_FULL_ONCE_PHYSICAL" \
 --unchecked-evidence "$P08_B45_FULL_UNCHECKED_PHYSICAL" \
 --out "$B45_SYNTHESIS_JSON" \
 --markdown-out "$B45_SYNTHESIS_MD"
sha256sum "$B45_SYNTHESIS_JSON" "$B45_SYNTHESIS_MD"
cat "$B45_SYNTHESIS_MD"
~~~

Expected markers:
P08_B45_SIGNED_FOUR_REPORT_AND_RAW_A53_SIDECAR_COMPARE_PASS=1
P08_B45_STATISTICAL_PAIRED_REPEATED_SPEEDUP_PROVEN=0
P08_B45_PC_ONLY_NO_BOARD_CONTACT=1

Please share the NEW per-mode DOMINANT_A53_PHASE markers and the
Markdown's six-phase attribution, plus both new output SHA. No new
Vitis ELF, Vivado build, model, hardware JTAG, PuTTY or test-set access.

## Next: P08-B4.6 counterbalanced Track A/B research protocol

The original roadmap defines B4.6 as a future six-session repeated
AB / BA / AB Track A vs Track B system/workload study. Before physical
launch, prepare a PC-only protocol with six independent reboot/recovery
records, original identical TRAIN-derived 1024 input population,
1023 ordinary frame full-service boundaries, actual per-run A53
CNTFRQ, selected trace isolation, independent model/scalar/FNV
proof per session and run-level uncertainty analysis. Track A is
42 neurons/26 FPGA dispatches; Track B is 1010 neurons/702
dispatches; a difference is NOT matched-workload pure FPGA
compute speedup. Do not silently substitute unprotected B4.5
optimized Track B for the accepted original Track B without
explicitly changing and labeling the workload/security contract.
No current authority for new JTAG runs is inferred from this plan.
