# P08-B4.4 — Original full1024 KV260 single-session A53 service-time audit (PC ONLY)

**Status:** Original 1024 TRAIN-derived validation scalar oracle and genuine
single-session KV260 neural/timing physical evidence independently accepted.
Final repeated Track A/B latency benchmark PENDING.

External signed independent B4.2 report:
 /home/dna/Thesis_Evidence/p08_b4_2_independent1024_20261102T184928Z.json
SHA256: **297114489eb8312733a2e2597f0ee0567f9868552d2bc71d0dd425139368b032**.
Original frozen full1024 independent scalar:
 /home/dna/Thesis_Evidence/p08_b4_1_full1024_scalar_20261102T143900Z.json
SHA256: **7e564d188651aeabdc284328ea65705bcb0b5571468b9f70d5dcacaa3f5493b8**.
The exact physical session evidence directory name was NOT pasted;
use the original operator shell environment variable P08_B4_PHYSICAL.

## Operator B4.2 first 1024 inclusive scalar-matched physical A53 timing summary

| Reported service duration metric | Raw A53 CNTVCT_EL0 ticks |
|---|---:|
| Count | 1024 |
| Minimum | 1,283,832,503 |
| Median | **1,303,433,920** |
| P95 nearest rank | 1,316,697,749 |
| Maximum | 1,327,299,037 |

The full-sample maximum exceeds minimum by ~3.386% of minimum,
and P95 exceeds median by ~1.018%. These describe within-session
frame-to-frame variation only; NOT repeatability across cold boots.
The actual B4 A53 CNTFRQ denominator was NOT in the user excerpt.

Conditional illustration ONLY: if actual B4 CNTFRQ is 100 MHz, median
is ~13.03434 seconds/image; min ~12.83833s, P95 ~13.16698s,
max ~13.27299s. The product 1024 x median is ~3.7075 hours,
but is NOT wall-clock elapsed duration because timing excludes
prelaunch setup and any gaps between measured service windows.
The accepted earlier Track A physical sessions observed
99,999,001 Hz, but this DOES NOT establish the B4 A53 frequency.

Original Track A A2.1/A2.2 3-pair ordinary 1023-image service
medians were approximately 35.67–35.72ms. Both tracks use the
same original TRAIN-derived 1024-source sequence and 26 neural
ticks, but their workload complexities are NOT matched:
A is 42 neurons, one logical core and 26 FPGA dispatches/image;
B is 1010 neurons, 27 logical cores virtualized in three physical
slots, with context reset/paging and 702 FPGA dispatches/image.
No isolated PL-only speedup/slowdown is supported by their ratio.
See docs/P08_B1_MATCHED_TRACK_A_LATENCY_CONTRACT.md and
docs/P08_A3_2_3_FINAL_PHYSICAL_REPEAT_RESULTS.md.

## New read-only script: independently sealed frequency and six-phase breakdown

scripts/p08_b4_4_single_run_timing_audit.py checks the accepted
independent physical-report SHA, its original neural acceptance flags,
the original scalar oracle pin, the captured full1024 physical timing
sidecar's SHA-256, the accepted terminal mailbox SHA, all 1024
CRC-checked 256B timing records, exact actual A53 CNTFRQ_EL0 and
monotonic/additive six-phase timings. It produces new no-overwrite
external JSON without modifying or contacting the KV260.

Run in your PC/VS Code terminal, no hardware:

~~~bash
cd ~/Git/Thesis
git fetch origin
git switch agent/v3-p08-b4-fullscale
git pull --ff-only origin agent/v3-p08-b4-fullscale
source ~/Git/Thesis/.venv-p08/bin/activate
cd Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p08_b4_4_single_run_timing_audit.py \
  tests/test_p08_b4_2_monitor_mailbox_pc_only.py

export P08_B4_INDEPENDENT_REPORT="/home/dna/Thesis_Evidence/p08_b4_2_independent1024_20261102T184928Z.json"
test "$(sha256sum "$P08_B4_INDEPENDENT_REPORT" | cut -d' ' -f1)" = \
  "297114489eb8312733a2e2597f0ee0567f9868552d2bc71d0dd425139368b032"

# IMPORTANT: Set to the EXACT prior accepted physical B4.2 session
# evidence directory. Do not infer it from the independent report filename.
# export P08_B4_PHYSICAL="/home/dna/Thesis_Evidence/<EXACT OLD B4 RUN>"

test -f "$P08_B4_PHYSICAL/full1024_capture/timing1024_physical.bin"
test -f "$P08_B4_PHYSICAL/full1024_capture/mailbox_terminal_physical.bin"

export P08_B4_4_DESCRIPTIVE="$HOME/Thesis_Evidence/p08_b4_4_first1024_one_session_descriptive_$(date -u +%Y%m%dT%H%M%SZ).json"
test ! -e "$P08_B4_4_DESCRIPTIVE"
PYTHONPATH="$PWD/src" python scripts/p08_b4_4_single_run_timing_audit.py \
  --report "$P08_B4_INDEPENDENT_REPORT" \
  --evidence "$P08_B4_PHYSICAL" \
  --out "$P08_B4_4_DESCRIPTIVE"
sha256sum "$P08_B4_4_DESCRIPTIVE"
~~~

The signed audit prints the ACTUAL frequency and normalizes all
counter ticks to milliseconds, computing ordinary-frame statistics
on **1023 images** while separately preserving selected trace
ordinal 1023. The six disjoint A53 phase intervals are:

1. Original 27-logical-core mutable context restore.
2. Frozen B1.3 original input encoding.
3. Virtual pager/scheduler reinitialization.
4. All 26 simulation ticks with 702 P03 FPGA dispatches,
   paging, routing and nested neural trace.
5. Final neural receipt validation.
6. Neural result journal commit.

Do not treat phase medians as additive. Per-frame phase SUMs
and cross-frame MEANS are additive; six phase medians generally
do not sum to the total-service median. All A53 counter times
exclude external host JTAG, initial PL programming and after-service
timing-sidecar commits. The PL FPGA cycle counter belongs
to a separate clock domain and has not been independently
calibrated to seconds.

Expected success markers:

~~~text
P08_B4_4_ONE_ORIGINAL_VERIFIED_1024_SESSION_A53_DESCRIPTIVE_TIMING_PASS=1
P08_B4_4_ACTUAL_A53_CNTFRQ_EL0_HZ=<actual measured B4 value>
P08_B4_4_1023_ORDINARY_MEDIAN_SERVICE_MS=<computed result>
P08_B4_4_1023_ORDINARY_P95_SERVICE_MS=<computed result>
P08_B4_4_SIX_REPEATED_PHYSICAL_SESSIONS_ACCEPTED=0
~~~

**Next:** use the phase shares and audited 1023-image durations to
design independently rebooted, original matched-source physical A/B
measurement sessions, partially counterbalanced AB/BA/AB, with
pair-level uncertainty and trace-scope isolation. The existing
six physical Track A A2.1/A2.2 sessions are timing-instrumentation
comparisons WITHIN Track A, not three matched A-versus-B pairs.
Official MNIST TEST remains SEALED; DDR boot/DMA exclusivity remains
unproven; no energy, isolated PL speedup, or six-session performance
claim is supported by this single verified B4.2 session.
