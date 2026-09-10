#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
PIN="1806bb4b4114d7671e5648fa75b7b83b3a8d5543"
TAG="v2.3-paper"
REPO="https://github.com/catalyst-neuromorphic/catalyst-n1.git"
TARGET="${1:-$PROJECT_DIR/build/m13_1/catalyst-n1}"

if ! command -v git >/dev/null 2>&1; then
    echo "ERROR: git is required." >&2
    exit 2
fi
if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 is required." >&2
    exit 2
fi

mkdir -p "$(dirname "$TARGET")"
if [[ ! -d "$TARGET/.git" ]]; then
    if [[ -e "$TARGET" ]]; then
        echo "ERROR: target exists but is not a Git checkout: $TARGET" >&2
        exit 3
    fi
    git clone --no-checkout "$REPO" "$TARGET"
fi

actual_origin="$(git -C "$TARGET" remote get-url origin)"
if [[ "$actual_origin" != "$REPO" && "$actual_origin" != "https://github.com/catalyst-neuromorphic/catalyst-n1" ]]; then
    echo "ERROR: existing Catalyst checkout has unexpected origin: $actual_origin" >&2
    exit 3
fi

git -C "$TARGET" fetch --tags origin
if ! git -C "$TARGET" cat-file -e "${PIN}^{commit}" 2>/dev/null; then
    echo "ERROR: pinned Catalyst commit is not present after fetch: $PIN" >&2
    exit 4
fi
if [[ "$(git -C "$TARGET" rev-parse "refs/tags/$TAG^{commit}")" != "$PIN" ]]; then
    echo "ERROR: Catalyst tag $TAG no longer resolves to frozen commit $PIN" >&2
    exit 4
fi

git -C "$TARGET" checkout --detach --force "$PIN"
git -C "$TARGET" clean -fdx

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$PROJECT_DIR/examples/validate_m13_1_reference_manifest.py" \
    --catalyst-checkout "$TARGET"

echo "M13.1 Catalyst fetch PASS: tag=$TAG commit=$PIN checkout=$TARGET"
