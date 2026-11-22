#!/usr/bin/env python3
"""Build the selected Validation-only pilot dataset from local files.

The script reads source WAV/JSON files without modifying them. It reuses the
normalization, schema parsing, WAV-header validation, and explicit-jangdan
logic in ``prepare_metadata.py``. No network, GPU, CLaMP, or translation API
is used.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import unicodedata
from pathlib import Path

from prepare_metadata import build_audio_index, deduplicate_rows, iter_records, make_row


OUTPUT_COLUMNS = [
    "audio_id", "audio_path", "label_path", "source_split",
    "match_status", "label_status", "duplicate_status", "audio_sha256",
    "duration_seconds", "sample_rate", "bit_depth", "channels",
    "genre", "genre_major", "genre_detail", "title", "instruments", "jangdan",
    "native_kr", "en", "mt_kr", "translation_model", "translation_settings",
    "translation_status", "h1_eligible", "h2_target_term_kr",
    "h2_target_term_romanized", "romanized_en", "descriptive_en",
    "h2_generation_method", "h2_equivalence_status", "h2_eligible",
    "review_status", "review_notes",
]

EXCLUSION_COLUMNS = [
    "audio_id", "declared_audio_file", "label_path", "source_split",
    "exclusion_reason",
]


H2_TERMS = {
    "장구": {
        "romanized": "janggu",
        "description": "Korean hourglass-shaped drum",
        "review_note": "Confirm the romanization and semantic equivalence of the instrument gloss.",
    },
    "소리북": {
        "romanized": "soribuk",
        "description": "Korean barrel drum",
        "review_note": "Confirm the romanization of 소리북 and the breadth of the drum gloss.",
    },
    "대금": {
        "romanized": "daegeum",
        "description": "Korean transverse bamboo flute",
        "review_note": "Confirm the romanization and semantic equivalence of the flute gloss.",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("data/raw"))
    parser.add_argument("--labels", type=Path, default=Path("data/raw/labels_validation"))
    parser.add_argument("--audio", type=Path, default=Path("data/raw/audio_validation"))
    parser.add_argument("--output", type=Path, default=Path("pilot_dataset.csv"))
    parser.add_argument(
        "--exclusions",
        type=Path,
        default=Path("pilot_dataset_exclusions.csv"),
    )
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def has_final_consonant(text: str) -> bool:
    for character in reversed(text.strip()):
        if "가" <= character <= "힣":
            return (ord(character) - ord("가")) % 28 != 0
    return False


def native_description(row: dict[str, str], instruments: list[str]) -> str:
    if row["genre_major"] == row["genre_sub"]:
        genre_sentence = f"이 곡은 {row['genre_sub']}이다."
    else:
        genre_sentence = f"이 곡은 {row['genre_major']}에 속하는 {row['genre_sub']}이다."
    instrument_text = "·".join(instruments)
    particle = "이" if has_final_consonant(instruments[-1]) else "가"
    return f"{genre_sentence} 편성에는 {instrument_text}{particle} 포함된다."


def select_h2_term(instruments: list[str]) -> tuple[str, dict[str, str]]:
    for term in ("장구", "소리북", "대금"):
        if term in instruments:
            return term, H2_TERMS[term]
    raise ValueError(
        "No approved H2 target term is present in instrumentSub: "
        + ";".join(instruments)
    )


def load_rows(
    args: argparse.Namespace,
) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, object]]:
    input_dir = args.input.resolve()
    labels_dir = args.labels.resolve()
    audio_dir = args.audio.resolve()
    audio_index = build_audio_index(audio_dir)
    anomalies: list[str] = []
    rows: list[dict[str, str]] = []
    parse_errors: list[str] = []
    label_file_count = 0

    for json_path in sorted(labels_dir.rglob("*.json")):
        label_file_count += 1
        try:
            with json_path.open("r", encoding="utf-8-sig") as handle:
                document = json.load(handle)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            parse_errors.append(f"{json_path}: {exc}")
            continue
        records = list(iter_records(document))
        if len(records) != 1:
            anomalies.append(f"Expected one record in {json_path}, found {len(records)}")
        for record in records:
            rows.append(make_row(record, json_path, input_dir, audio_index, anomalies))

    raw_count = len(rows)
    rows, identical_duplicates, conflicting_duplicates = deduplicate_rows(rows, anomalies)
    if parse_errors or anomalies or identical_duplicates or conflicting_duplicates:
        raise RuntimeError(json.dumps({
            "parse_errors": parse_errors,
            "anomalies": anomalies,
            "identical_duplicates": identical_duplicates,
            "conflicting_duplicates": conflicting_duplicates,
        }, ensure_ascii=False, indent=2))

    matched = [
        row for row in rows
        if row["split"] == "validation" and row["has_local_audio"] == "true"
    ]
    excluded = [
        row for row in rows
        if row["split"] == "validation" and row["has_local_audio"] != "true"
    ]
    matched_paths = {Path(row["audio_path"]).resolve() for row in matched}
    local_wavs = {
        path.resolve() for path in audio_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in {".wav", ".wave"}
    }
    unmatched_wavs = sorted(str(path) for path in local_wavs - matched_paths)
    if unmatched_wavs:
        raise RuntimeError(
            "Validation WAV files without a matching JSON: "
            + json.dumps(unmatched_wavs, ensure_ascii=False)
        )

    return matched, excluded, {
        "label_file_count": label_file_count,
        "raw_record_count": raw_count,
        "matched_count": len(matched),
        "json_only_count": len(rows) - len(matched),
        "wav_only_count": len(unmatched_wavs),
    }


def build_output_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    required = [
        "audio_id", "audio_path", "audio_file_name", "genre_major", "genre_sub",
        "genre_detail", "title", "instruments", "sample_rate", "bit_depth",
        "channels", "source_json",
    ]
    prepared: list[dict[str, str]] = []
    digest_owner: dict[str, str] = {}

    for row in rows:
        missing = [field for field in required if not row[field]]
        if missing:
            raise ValueError(f"{row['audio_id']}: missing fields {missing}")

        audio_path = Path(row["audio_path"])
        if not audio_path.is_file():
            raise FileNotFoundError(audio_path)
        normalized_id = unicodedata.normalize("NFC", row["audio_id"])
        normalized_stem = unicodedata.normalize("NFC", audio_path.stem)
        normalized_declared = unicodedata.normalize("NFC", Path(row["audio_file_name"]).stem)
        if normalized_id != normalized_stem or normalized_id != normalized_declared:
            raise ValueError(
                f"ID mismatch: {row['audio_id']} / {audio_path.name} / {row['audio_file_name']}"
            )

        instruments = [item for item in row["instruments"].split(";") if item]
        if not instruments:
            raise ValueError(f"{row['audio_id']}: no instrumentSub values")

        digest = sha256_file(audio_path)
        duplicate_status = "unique"
        if digest in digest_owner:
            duplicate_status = f"duplicate_of:{digest_owner[digest]}"
        else:
            digest_owner[digest] = row["audio_id"]

        target_kr, target = select_h2_term(instruments)
        romanized = target["romanized"]
        prepared.append({
            "audio_id": row["audio_id"],
            "audio_path": row["audio_path"],
            "label_path": str(Path("data/raw") / row["source_json"]),
            "source_split": "Validation",
            "match_status": "matched",
            "label_status": "complete",
            "duplicate_status": duplicate_status,
            "audio_sha256": digest,
            "duration_seconds": row["duration"],
            "sample_rate": row["sample_rate"],
            "bit_depth": row["bit_depth"],
            "channels": row["channels"],
            "genre": row["genre_sub"],
            "genre_major": row["genre_major"],
            "genre_detail": row["genre_detail"],
            "title": row["title"],
            "instruments": row["instruments"],
            "jangdan": row["jangdan"],
            "native_kr": native_description(row, instruments),
            "en": "",
            "mt_kr": "",
            "translation_model": "none",
            "translation_settings": "not_applicable",
            "translation_status": "incomplete_no_local_mt_model_or_api",
            "h1_eligible": "false",
            "h2_target_term_kr": target_kr,
            "h2_target_term_romanized": romanized,
            "romanized_en": f"This piece features a {romanized}.",
            "descriptive_en": f"This piece features a {target['description']}.",
            "h2_generation_method": "rule_based_single_term_substitution",
            "h2_equivalence_status": "needs_human_review",
            "h2_eligible": "true",
            "review_status": "needs_human_review",
            "review_notes": (
                "Review the label-grounded Korean caption and H2 term pair. "
                "H1 is incomplete because no local MT model/API was available. "
                + target["review_note"]
            ),
        })

    return prepared


def main() -> int:
    args = parse_args()
    rows, excluded, summary = load_rows(args)
    output_rows = build_output_rows(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(output_rows)

    args.exclusions.parent.mkdir(parents=True, exist_ok=True)
    with args.exclusions.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=EXCLUSION_COLUMNS)
        writer.writeheader()
        writer.writerows(
            {
                "audio_id": row["audio_id"],
                "declared_audio_file": row["audio_file_name"],
                "label_path": str(Path("data/raw") / row["source_json"]),
                "source_split": "Validation",
                "exclusion_reason": "no_local_wav",
            }
            for row in excluded
        )

    summary.update({
        "output": str(args.output),
            "exclusions_output": str(args.exclusions),
        "output_row_count": len(output_rows),
        "h1_eligible_count": sum(row["h1_eligible"] == "true" for row in output_rows),
        "h2_eligible_count": sum(row["h2_eligible"] == "true" for row in output_rows),
        "needs_human_review_count": sum(
            row["review_status"] == "needs_human_review" for row in output_rows
        ),
    })
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
