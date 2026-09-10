from __future__ import annotations

import argparse
from pathlib import Path

from neuromorphic_twin.m13_feature_crosswalk import (
    default_crosswalk_path,
    load_feature_crosswalk,
    render_feature_crosswalk_markdown,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate/render the M13.2 four-way feature crosswalk")
    parser.add_argument("--crosswalk", type=Path, default=default_crosswalk_path())
    parser.add_argument("--write-markdown", type=Path)
    args = parser.parse_args()

    data = load_feature_crosswalk(args.crosswalk)
    rendered = render_feature_crosswalk_markdown(data)
    if args.write_markdown is not None:
        args.write_markdown.parent.mkdir(parents=True, exist_ok=True)
        args.write_markdown.write_text(rendered, encoding="utf-8")

    summary = data["summary"]
    print(
        "M13.2 feature crosswalk PASS: "
        f"rows={len(data['rows'])} "
        f"feature_classes={summary['minimum_milestone_feature_classes_covered']} "
        f"common_yes={len(summary['common_subset_yes'])} "
        f"conditional={len(summary['common_subset_conditional'])} "
        f"out_of_common={len(summary['common_subset_no'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
