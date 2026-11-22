#!/usr/bin/env python3
"""Merge separately generated Codex H1 forward/back translations into the pilot CSV."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, default=Path("pilot_dataset.pre_h1.csv"))
    parser.add_argument("--forward", type=Path)
    parser.add_argument("--back", type=Path)
    parser.add_argument(
        "--translations",
        type=Path,
        help="Persistent CSV with audio_id,native_kr,en,mt_kr",
    )
    parser.add_argument("--output", type=Path, default=Path("pilot_dataset.csv"))
    parser.add_argument(
        "--pairs", type=Path, default=Path("h1_translation_pairs.csv")
    )
    return parser.parse_args()


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Missing header: {path}")
        return reader.fieldnames, list(reader)


def main() -> int:
    args = parse_args()
    fieldnames, base_rows = read_rows(args.base)
    translation_native: dict[str, str] = {}
    if args.translations is not None:
        if args.forward is not None or args.back is not None:
            raise ValueError("Use --translations or --forward/--back, not both")
        translation_fields, translation_rows = read_rows(args.translations)
        expected = ["audio_id", "native_kr", "en", "mt_kr"]
        if translation_fields != expected:
            raise ValueError(f"Unexpected translation columns: {translation_fields}")
        forward_rows = [
            {"audio_id": row["audio_id"], "en": row["en"]}
            for row in translation_rows
        ]
        back_rows = [
            {"audio_id": row["audio_id"], "mt_kr": row["mt_kr"]}
            for row in translation_rows
        ]
        translation_native = {
            row["audio_id"]: row["native_kr"] for row in translation_rows
        }
    else:
        if args.forward is None or args.back is None:
            raise ValueError("Provide --translations or both --forward and --back")
        forward_fields, forward_rows = read_rows(args.forward)
        back_fields, back_rows = read_rows(args.back)
        if forward_fields != ["audio_id", "en"]:
            raise ValueError(f"Unexpected forward columns: {forward_fields}")
        if back_fields != ["audio_id", "mt_kr"]:
            raise ValueError(f"Unexpected back-translation columns: {back_fields}")

    base_ids = [row["audio_id"] for row in base_rows]
    forward_ids = [row["audio_id"] for row in forward_rows]
    back_ids = [row["audio_id"] for row in back_rows]
    if not (len(base_rows) == 33 and base_ids == forward_ids == back_ids):
        raise ValueError("The 33 audio IDs/order do not match across inputs")
    if any(not row["en"].strip() for row in forward_rows):
        raise ValueError("At least one forward translation is empty")
    if any(not row["mt_kr"].strip() for row in back_rows):
        raise ValueError("At least one back-translation is empty")

    forward = {row["audio_id"]: row["en"] for row in forward_rows}
    back = {row["audio_id"]: row["mt_kr"] for row in back_rows}
    old_review_text = "H1 is incomplete because no local MT model/API was available."
    new_review_text = "H1 Codex forward/back translations need human review."

    pair_rows: list[dict[str, str]] = []
    for row in base_rows:
        if row["en"] or row["mt_kr"]:
            raise ValueError(f"Base row already has H1 translations: {row['audio_id']}")
        if old_review_text not in row["review_notes"]:
            raise ValueError(f"Unexpected review note: {row['audio_id']}")

        audio_id = row["audio_id"]
        if translation_native and translation_native[audio_id] != row["native_kr"]:
            raise ValueError(f"native_kr mismatch in translation file: {audio_id}")
        row["en"] = forward[audio_id]
        row["mt_kr"] = back[audio_id]
        row["translation_model"] = "Codex-based LLM (current session)"
        row["translation_settings"] = (
            "two_pass_separate_contexts;fixed_glossary;"
            "back_translation_en_only;decoding_parameters_not_exposed"
        )
        row["translation_status"] = "completed_codex_llm_needs_human_review"
        row["h1_eligible"] = "true"
        row["review_notes"] = row["review_notes"].replace(
            old_review_text, new_review_text
        )
        pair_rows.append(
            {
                "audio_id": audio_id,
                "native_kr": row["native_kr"],
                "en": row["en"],
                "mt_kr": row["mt_kr"],
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(base_rows)

    args.pairs.parent.mkdir(parents=True, exist_ok=True)
    with args.pairs.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["audio_id", "native_kr", "en", "mt_kr"]
        )
        writer.writeheader()
        writer.writerows(pair_rows)

    print(
        f"Updated {len(base_rows)} rows in {args.output}; "
        f"wrote review pairs to {args.pairs}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
