from __future__ import annotations

import argparse
import json
from pathlib import Path

from mnist_app.matched_bundle import scope_indices, write_matched_request_shards


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate bounded-size matched MNIST request shards for external backends."
    )
    parser.add_argument("--scope", choices=("corpus", "full"), required=True)
    parser.add_argument(
        "--frozen-root",
        type=Path,
        default=Path("applications/mnist/frozen/mnist-v1"),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--shard-size", type=int, default=100)
    args = parser.parse_args()

    indices = scope_indices(args.scope, args.frozen_root)
    manifest_path = write_matched_request_shards(
        args.frozen_root,
        indices,
        args.output_dir,
        shard_size=args.shard_size,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    print(
        f"matched request shards: scope={args.scope} cases={manifest['case_count']} "
        f"shards={manifest['shard_count']} shard_size={manifest['shard_size']} "
        f"manifest={manifest_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
