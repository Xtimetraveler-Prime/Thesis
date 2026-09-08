from __future__ import annotations

import argparse
from pathlib import Path

from neuromorphic_twin.m13_reference_manifest import (
    load_reference_manifest,
    verify_catalyst_checkout,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate the frozen M13.1 external-reference manifest and, optionally, a local Catalyst checkout."
    )
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--catalyst-checkout", type=Path, default=None)
    parser.add_argument(
        "--allow-dirty-catalyst",
        action="store_true",
        help="Allow local Catalyst modifications. Not suitable for accepted native evidence.",
    )
    args = parser.parse_args()

    manifest = load_reference_manifest(args.manifest)
    catalyst = manifest["catalyst_n1"]
    brian = manifest["brian2loihi"]
    project = manifest["project_baseline"]

    print(
        "M13.1 reference manifest PASS: "
        f"project={project['commit'][:12]} "
        f"catalyst={catalyst['primary_tag']}@{catalyst['commit'][:12]} "
        f"brian2loihi={brian['tag']}@{brian['commit'][:12]} "
        f"loihi_publications={len(manifest['published_loihi'])}"
    )

    if args.catalyst_checkout is not None:
        result = verify_catalyst_checkout(
            args.catalyst_checkout,
            manifest,
            require_clean=not args.allow_dirty_catalyst,
        )
        print(
            "M13.1 Catalyst checkout PASS: "
            f"commit={result.commit} tags={','.join(result.tags_at_commit)} "
            f"files={len(result.required_files)} testbenches={len(result.regression_testbenches)} "
            f"clean={int(result.clean)}"
        )


if __name__ == "__main__":
    main()
