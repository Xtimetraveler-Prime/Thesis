# P08-B4.1 — Independent original B2.4 full 1,024-image scalar reference (PC ONLY)

**Status:** source development + synthetic negative CI passed; **genuine
operator-local 64-shard oracle generation NOT YET PERFORMED**.
Depends on separately independently verified P08-B3 original 16-image
KV260 session. No FPGA board contact, XSDB, Vivado, Vitis firmware,
MNIST TEST download or training is permitted in B4.1.

## Verified earlier physical baseline (do not overwrite)

Original third real pilot capture:
\`/home/dna/Thesis_Evidence/p08_b3_pilot16_physical_retry_20261102T053637Z\`
and original 16-image independent physical report:
\`/home/dna/Thesis_Evidence/p08_b3_pilot16_independent_20261102T055256Z.json\`.
Exact reported JSON SHA256
\`b21e388ab2c3896e76373aaf1663b3b3b1a6d6e1e3c192684f7da02d40b0ed11\`.
Six original frozen DDR sources, original first16 10-vector spike
classification and 26-tick 1,010-neuron FNV fingerprint all independently
PASS; 16 complete A53 service timing records structurally valid.
Neither the full 1,024-frame scalar source nor quantitative latency
sessions have been accepted.

## Why shards?

The physically executed B3 scalar oracle covers only ordinals 0..15.
Expanding to all 1,024 original matched validation images requires
running **the independent frozen B2.4 monolithic Python neural model
again** for every new image, not extrapolating or copying physical
outputs and not changing the trained network. To make this auditable
and recoverable, compute **64 separately immutable shards of 16**.
Each must re-verify the pinned A3.2 source, B2.1 original 1,024-image
source and wire-SHA ledger, all 33 signed B2.4 original frozen assets,
and original frozen routes. Shard 0 must compare its independent 16
newly computed rows exactly with the accepted original signed
B2.4 first16 oracle (SHA
\`13e3e679110059c70f8cfd3d51014c37c62a2cb3ea9c85974e27360606d3b271\`).

A later no-overwrite merge rejects incomplete, reordered, duplicated
or different source/frame shards, re-authenticates the original raw pool
and 1,024 encoded ingress IDs, and returns a complete independent
1024-image oracle JSON plus individual 64 shard SHA256 values.
All real model/route/input data must be on the local operator machine.
Synthetic CI is not a substitute.

## Local operator B4.1 steps (NEVER contact KV260)

Update to the new STACKED branch. Do not merge prior B3 PR #52 or
new B4 PR #53:

\`\`\`bash
cd ~/Git/Thesis
git fetch origin
git switch --track origin/agent/v3-p08-b4-fullscale
# If branch already exists: git switch agent/v3-p08-b4-fullscale
git pull --ff-only origin agent/v3-p08-b4-fullscale
git status --short
git rev-parse HEAD
source ~/Git/Thesis/.venv-p08/bin/activate
cd Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p08_b4_1_scalar_1024.py \
  tests/test_p08_b2_4_numerical.py \
  tests/test_p08_b3_pilot16_physical.py
\`\`\`

Set original accepted operators' read-only source directories:

\`\`\`bash
export P08_B4_A_STAGE="$HOME/Thesis_Evidence/p08_a3_2_stage1024_20261019T003150Z"
export P08_B4_DATA_DIR="$PWD/data/mnist_raw"
export P08_B4_FROZEN="$PWD/artifacts/p06_b24_frozen_1000"
export P08_B4_ROUTES="$HOME/p07_b4m_frozen_inputs_20261023T034626Z"
export P08_B4_INGRESS="$HOME/Thesis_Evidence/p08_b2_1_original1024_20261102T003256Z"
export P08_B4_FIRST16="$HOME/Thesis_Evidence/p08_b2_4_original_first16_scalar_20261102T042201Z.json"

test -d "$P08_B4_A_STAGE"
test -d "$P08_B4_DATA_DIR"
test -d "$P08_B4_FROZEN"
test -d "$P08_B4_ROUTES"
test -d "$P08_B4_INGRESS"
test -f "$P08_B4_FIRST16"
sha256sum "$P08_B4_FIRST16"
\`\`\`

The first16 SHA must equal the pinned digest above; no file may
be edited. If your original P07 route directory differs, use
the **previously authenticated original P07-B4m route directory**
rather than creating or exporting new routes.

Create a NEW external root. Shard names are deliberately exact.

\`\`\`bash
export P08_B4_SHARDS="$HOME/Thesis_Evidence/p08_b4_1_original_scalar_shards_$(date -u +%Y%m%dT%H%M%SZ)"
test ! -e "$P08_B4_SHARDS"
mkdir -m 700 "$P08_B4_SHARDS"

PYTHONPATH="$PWD/src" python scripts/p08_b4_1_scalar_shard.py \
  --shard 0 \
  --frozen-dir "$P08_B4_FROZEN" \
  --a-stage "$P08_B4_A_STAGE" \
  --train-data-dir "$P08_B4_DATA_DIR" \
  --routes-dir "$P08_B4_ROUTES" \
  --ingress-dir "$P08_B4_INGRESS" \
  --first16-oracle "$P08_B4_FIRST16" \
  --out "$P08_B4_SHARDS/p08_b4_1_scalar_shard_00.json"
\`\`\`

**Stop here and inspect shard0 before proceeding.** It must print
\`P08_B4_1_ORIGINAL_SCALAR_SHARD_INDEPENDENT_PASS=1\`,
\`P08_B4_1_SHARD=0\` and \`P08_B4_1_VERIFIED_ORDINAL_RANGE=0:16\`.
This proves the new original scalar generator reproduced the
original independent first16 reference from scratch; it does
**NOT** mean 1,024 images have been computed.

After real shard0 PASS, compute the other 63 sequentially in the
foreground. A stopped run retains already finished original shard
files and **never overwrites them**:

\`\`\`bash
for i in $(seq 1 63); do
  output=$(printf '%s/p08_b4_1_scalar_shard_%02d.json' "$P08_B4_SHARDS" "$i")
  test ! -e "$output" || { echo "REFUSE: shard exists: $output"; break; }
  PYTHONPATH="$PWD/src" python scripts/p08_b4_1_scalar_shard.py \
    --shard "$i" \
    --frozen-dir "$P08_B4_FROZEN" \
    --a-stage "$P08_B4_A_STAGE" \
    --train-data-dir "$P08_B4_DATA_DIR" \
    --routes-dir "$P08_B4_ROUTES" \
    --ingress-dir "$P08_B4_INGRESS" \
    --first16-oracle "$P08_B4_FIRST16" \
    --out "$output" || break
done
\`\`\`

Check exactly 64 shards before merge:

\`\`\`bash
find "$P08_B4_SHARDS" -maxdepth 1 -type f -name 'p08_b4_1_scalar_shard_*.json' | wc -l

export P08_B4_FULL_ORACLE="$HOME/Thesis_Evidence/p08_b4_1_original1024_scalar_$(date -u +%Y%m%dT%H%M%SZ).json"
test ! -e "$P08_B4_FULL_ORACLE"

PYTHONPATH="$PWD/src" python scripts/p08_b4_1_merge_scalar_1024.py \
  --shards-dir "$P08_B4_SHARDS" \
  --ingress-dir "$P08_B4_INGRESS" \
  --first16-oracle "$P08_B4_FIRST16" \
  --out "$P08_B4_FULL_ORACLE"

sha256sum "$P08_B4_FULL_ORACLE"
\`\`\`

The full merge PASS requires:
\`P08_B4_1_ALL_1024_ORIGINAL_SCALAR_ROWS_ADMITTED=1\`,
\`P08_B4_1_ALL_64_SHARDS_SHA_VERIFIED=1\`,
\`P08_B4_1_ACCEPTED_FIRST16_SCALAR_REPRODUCED=1\`.
These flags alone do NOT authorize physical JTAG or establish numerical
parity between all physical B images and scalar reference.

## Remaining B4 gated development after genuine 1024 scalar completion

- **B4.2:** fully separated and **authentic Vitis-built**
  1024-image A53 ELF/map and static+dynamic memory admission.
  Provenance pin accepted P03 shell and original 27core frozen
  sources, prevent 1024 ELF substitution into B3 first16 results.
  1024x256B original neural and 1024x256B timer journals,
  exact terminal 1024, progress-aware polling (DONE alone is
  NEVER terminal), complete physical same-session PSU readbacks.
- **B4.3:** full 1024-image genuine physical classification,
  per-image 10-vector spike, 26tick-1010-neuron FNV and timing
  verification against the independent B4.1 oracle **before**
  accepting any aggregate physical latency benchmark.
  First1024 must be the same original TRAIN held-out sequence
  as accepted Track A. Selected full raw trace frame 1023
  requires separate source/physical plan; journal FNV alone is
  not direct raw-trace byte equality.
- **B4.4:** original approved six-session cold-boot and
  counterbalanced AB/BA/AB Track A/Track B latency
  measurement protocol. Report image-service window
  \`CNTVCT_EL0\` ticks divided by observed \`CNTFRQ_EL0\`,
  reset+ingress+scheduler+702 dispatch+26 barriers+result
  journal commit; exclude setup/JTAG/PL shell and after-service
  timing-sidecar collection, and avoid mixing A53 with PL
  cycle domains. Keep selected frame 1023 / intrusive trace
  scope separate from ordinary latency distribution.
  No energy or pure-PL speedup claims without distinct evidence.

**Important limitations:** Physical DDR boot/firmware/Linux/PS/PL-DMA
exclusivity is unproven, even though the operator accepted
the original destructive pilot risk. Any *new* destructive
B4 session must use fresh independent risk verification,
evidence directory and reboot protocol. The official
MNIST TEST remains completely SEALED. B4.1 does not
touch hardware.
