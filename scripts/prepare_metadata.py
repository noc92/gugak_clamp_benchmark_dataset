#!/usr/bin/env python3
"""Build metadata.csv and a machine-readable summary from AI-Hub 71955 JSON.

The script only reads source JSON/audio and never modifies it.  In particular,
``timeSignature`` is not treated as ``jangdan``.  The jangdan column is filled
only when an explicit jangdan/장단 key exists in the annotation.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import unicodedata
import wave
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


CSV_COLUMNS = [
    "audio_id",
    "split",
    "has_local_audio",
    "audio_path",
    "audio_file_name",
    "genre",
    "genre_major",
    "genre_sub",
    "genre_detail",
    "title",
    "instruments",
    "instrument_major_groups",
    "jangdan",
    "duration",
    "tempo_bpm",
    "time_signature",
    "western_key",
    "moods",
    "mood_counts",
    "performers",
    "record_date",
    "sample_rate",
    "bit_depth",
    "channels",
    "stem_count",
    "source_json",
]

EXPLICIT_JANGDAN_KEYS = {
    "jangdan",
    "jangdanname",
    "jangdan_name",
    "장단",
    "장단명",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/raw"),
        help="Directory containing approved AI-Hub JSON and optional WAV files",
    )
    parser.add_argument("--output", type=Path, default=Path("metadata.csv"))
    parser.add_argument(
        "--summary", type=Path, default=Path("metadata_summary.json")
    )
    return parser.parse_args()


def clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (str, int)):
        return str(value).strip()
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        return str(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def normalized_key(key: Any) -> str:
    return unicodedata.normalize("NFKC", str(key)).replace("-", "_").strip().lower()


def explicit_jangdan_values(value: Any) -> list[str]:
    """Return only values attached to an explicit jangdan/장단 field."""
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if normalized_key(key) in EXPLICIT_JANGDAN_KEYS:
                if isinstance(child, list):
                    found.extend(clean(item) for item in child if clean(item))
                elif clean(child):
                    found.append(clean(child))
            else:
                found.extend(explicit_jangdan_values(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(explicit_jangdan_values(child))
    return list(dict.fromkeys(found))


def looks_like_record(value: Any) -> bool:
    return isinstance(value, dict) and (
        ("project_name" in value and "master" in value)
        or ("master" in value and "stems" in value)
    )


def iter_records(value: Any) -> Iterable[dict[str, Any]]:
    if looks_like_record(value):
        yield value
        return
    if isinstance(value, list):
        for child in value:
            yield from iter_records(child)
    elif isinstance(value, dict):
        for child in value.values():
            yield from iter_records(child)


def build_audio_index(input_dir: Path) -> dict[str, list[Path]]:
    index: dict[str, list[Path]] = {}
    if not input_dir.exists():
        return index
    for path in input_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".wav", ".wave"}:
            key = unicodedata.normalize("NFC", path.name).casefold()
            index.setdefault(key, []).append(path)
    return index


def resolve_audio(
    declared_name: str,
    audio_index: dict[str, list[Path]],
    anomalies: list[str],
) -> Path | None:
    if not declared_name:
        return None
    key = unicodedata.normalize("NFC", declared_name).casefold()
    matches = audio_index.get(key, [])
    if len(matches) > 1:
        anomalies.append(
            f"Multiple audio files match declared name {declared_name!r}: "
            + ", ".join(str(path) for path in matches)
        )
        return None
    return matches[0] if matches else None


def wav_properties(path: Path, anomalies: list[str]) -> dict[str, str]:
    try:
        with wave.open(str(path), "rb") as handle:
            rate = handle.getframerate()
            duration = handle.getnframes() / rate if rate else None
            return {
                "duration": (
                    f"{duration:.6f}".rstrip("0").rstrip(".")
                    if duration is not None
                    else ""
                ),
                "sample_rate": clean(rate),
                "bit_depth": clean(handle.getsampwidth() * 8),
                "channels": clean(handle.getnchannels()),
            }
    except (wave.Error, OSError, EOFError) as exc:
        anomalies.append(f"Could not read WAV duration for {path}: {exc}")
        return {"duration": "", "sample_rate": "", "bit_depth": "", "channels": ""}


def explicit_duration(tags: dict[str, Any]) -> str:
    for key in ("duration", "durationSeconds", "duration_seconds"):
        if key in tags and clean(tags[key]):
            return clean(tags[key])
    return ""


def format_moods(value: Any) -> str:
    if not isinstance(value, list):
        return clean(value)
    labels: list[str] = []
    for item in value:
        if isinstance(item, dict):
            label = clean(item.get("mood"))
            if label:
                labels.append(label)
        elif clean(item):
            labels.append(clean(item))
    return ";".join(dict.fromkeys(labels))


def format_mood_counts(value: Any) -> str:
    if not isinstance(value, list):
        return ""
    pairs: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        label = clean(item.get("mood"))
        count = clean(item.get("count"))
        if label and count:
            pairs.append(f"{label}:{count}")
    return ";".join(pairs)


def infer_split(source_json: Path) -> str:
    normalized_parts = [
        unicodedata.normalize("NFKC", part).casefold() for part in source_json.parts
    ]
    if any(part.startswith("tl_") or part == "labels_training" for part in normalized_parts):
        return "training"
    if any(part.startswith("vl_") or part == "labels_validation" for part in normalized_parts):
        return "validation"
    if "sample" in normalized_parts:
        return "sample"
    return ""


def deduplicate_rows(
    rows: list[dict[str, str]], anomalies: list[str]
) -> tuple[list[dict[str, str]], int, int]:
    by_id: dict[str, list[dict[str, str]]] = {}
    no_id: list[dict[str, str]] = []
    for row in rows:
        if row["audio_id"]:
            by_id.setdefault(row["audio_id"], []).append(row)
        else:
            no_id.append(row)

    deduplicated: list[dict[str, str]] = []
    identical_duplicates = 0
    conflicting_duplicates = 0
    ignored_for_comparison = {
        "source_json",
        "split",
        "has_local_audio",
        "audio_path",
        "duration",
        "channels",
    }
    comparison_fields = [
        field for field in CSV_COLUMNS if field not in ignored_for_comparison
    ]

    for audio_id, group in by_id.items():
        if len(group) == 1:
            deduplicated.append(group[0])
            continue
        reference = group[0]
        identical = all(
            all(candidate[field] == reference[field] for field in comparison_fields)
            for candidate in group[1:]
        )
        if not identical:
            conflicting_duplicates += len(group) - 1
            anomalies.append(
                f"Conflicting duplicate audio_id {audio_id!r}: {len(group)} records"
            )
            deduplicated.extend(group)
            continue

        identical_duplicates += len(group) - 1
        preferred = next((row for row in group if row["audio_path"]), group[0]).copy()
        preferred["source_json"] = ";".join(
            dict.fromkeys(row["source_json"] for row in group if row["source_json"])
        )
        splits = {row["split"] for row in group if row["split"]}
        for split in ("training", "validation", "sample"):
            if split in splits:
                preferred["split"] = split
                break
        preferred["has_local_audio"] = (
            "true" if any(row["audio_path"] for row in group) else "false"
        )
        deduplicated.append(preferred)

    deduplicated.extend(no_id)
    deduplicated.sort(key=lambda row: (row["audio_id"], row["source_json"]))
    return deduplicated, identical_duplicates, conflicting_duplicates


def make_row(
    record: dict[str, Any],
    source_json: Path,
    input_dir: Path,
    audio_index: dict[str, list[Path]],
    anomalies: list[str],
) -> dict[str, str]:
    master = record.get("master") if isinstance(record.get("master"), dict) else {}
    tags = master.get("tags") if isinstance(master.get("tags"), dict) else {}
    stems = record.get("stems") if isinstance(record.get("stems"), list) else []
    audio_file_name = clean(master.get("file_name"))
    audio_path = resolve_audio(audio_file_name, audio_index, anomalies)

    instrument_sub: list[str] = []
    instrument_major: list[str] = []
    for stem in stems:
        if not isinstance(stem, dict):
            continue
        stem_tags = stem.get("tags") if isinstance(stem.get("tags"), dict) else {}
        if clean(stem_tags.get("instrumentSub")):
            instrument_sub.append(clean(stem_tags.get("instrumentSub")))
        if clean(stem_tags.get("instrumentMajor")):
            instrument_major.append(clean(stem_tags.get("instrumentMajor")))

    jangdan = explicit_jangdan_values(record)
    wav_info = (
        wav_properties(audio_path, anomalies)
        if audio_path is not None
        else {"duration": "", "sample_rate": "", "bit_depth": "", "channels": ""}
    )
    duration = wav_info["duration"] or explicit_duration(tags)
    genre_major = clean(tags.get("genreMajor"))
    genre_sub = clean(tags.get("genreSub"))

    declared_sample_rate = clean(tags.get("sampleRate"))
    declared_bit_depth = clean(tags.get("bitDepth"))
    if declared_sample_rate and wav_info["sample_rate"]:
        if declared_sample_rate != wav_info["sample_rate"]:
            anomalies.append(
                f"sampleRate mismatch for {audio_file_name}: JSON={declared_sample_rate}, "
                f"WAV={wav_info['sample_rate']}"
            )
    if declared_bit_depth and wav_info["bit_depth"]:
        if declared_bit_depth != wav_info["bit_depth"]:
            anomalies.append(
                f"bitDepth mismatch for {audio_file_name}: JSON={declared_bit_depth}, "
                f"WAV={wav_info['bit_depth']}"
            )

    if audio_path is not None:
        try:
            audio_path_label = str(audio_path.resolve().relative_to(Path.cwd().resolve()))
        except ValueError:
            audio_path_label = str(audio_path)
    else:
        audio_path_label = ""

    try:
        source_label = str(source_json.relative_to(input_dir))
    except ValueError:
        source_label = str(source_json)

    return {
        "audio_id": clean(record.get("project_name")) or Path(audio_file_name).stem,
        "split": infer_split(source_json),
        "has_local_audio": "true" if audio_path is not None else "false",
        "audio_path": audio_path_label,
        "audio_file_name": audio_file_name,
        "genre": genre_sub or genre_major,
        "genre_major": genre_major,
        "genre_sub": genre_sub,
        "genre_detail": clean(tags.get("genreDetail")),
        "title": clean(tags.get("title")),
        "instruments": ";".join(dict.fromkeys(instrument_sub)),
        "instrument_major_groups": ";".join(dict.fromkeys(instrument_major)),
        "jangdan": ";".join(jangdan),
        "duration": duration,
        "tempo_bpm": clean(tags.get("tempoBpm")),
        "time_signature": clean(tags.get("timeSignature")),
        "western_key": clean(tags.get("western_key")),
        "moods": format_moods(tags.get("moods")),
        "mood_counts": format_mood_counts(tags.get("moods")),
        "performers": clean(tags.get("performers")),
        "record_date": clean(tags.get("recordDate")),
        "sample_rate": declared_sample_rate or wav_info["sample_rate"],
        "bit_depth": declared_bit_depth or wav_info["bit_depth"],
        "channels": wav_info["channels"],
        "stem_count": str(sum(isinstance(stem, dict) for stem in stems)),
        "source_json": source_label,
    }


def main() -> int:
    args = parse_args()
    input_dir = args.input.resolve()
    json_files = sorted(input_dir.rglob("*.json")) if input_dir.exists() else []
    audio_index = build_audio_index(input_dir)
    anomalies: list[str] = []
    rows: list[dict[str, str]] = []
    parse_errors: list[str] = []
    declared_stem_names: list[str] = []

    for json_path in json_files:
        try:
            with json_path.open("r", encoding="utf-8-sig") as handle:
                document = json.load(handle)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            parse_errors.append(f"{json_path}: {exc}")
            continue
        records = list(iter_records(document))
        if not records:
            anomalies.append(f"No project/master/stems record found in {json_path}")
        for record in records:
            stems = record.get("stems") if isinstance(record.get("stems"), list) else []
            for stem in stems:
                if isinstance(stem, dict) and clean(stem.get("file_name")):
                    declared_stem_names.append(clean(stem.get("file_name")))
            row = make_row(record, json_path, input_dir, audio_index, anomalies)
            rows.append(row)

    raw_parsed_record_count = len(rows)
    rows, identical_duplicate_count, conflicting_duplicate_count = deduplicate_rows(
        rows, anomalies
    )

    required_csv_fields = [
        "audio_id",
        "audio_file_name",
        "genre_major",
        "genre_sub",
        "genre_detail",
        "title",
        "instruments",
        "tempo_bpm",
        "time_signature",
        "western_key",
        "sample_rate",
        "bit_depth",
    ]
    missing = {
        field: sum(not row[field] for row in rows) for field in required_csv_fields
    }
    all_csv_missing = {
        field: sum(not row[field] for row in rows) for field in CSV_COLUMNS
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    genre_distribution = Counter(row["genre"] for row in rows if row["genre"])
    genre_major_distribution = Counter(
        row["genre_major"] for row in rows if row["genre_major"]
    )
    genre_sub_distribution = Counter(
        row["genre_sub"] for row in rows if row["genre_sub"]
    )
    genre_detail_distribution = Counter(
        row["genre_detail"] for row in rows if row["genre_detail"]
    )
    instrument_distribution: Counter[str] = Counter()
    instrument_major_distribution: Counter[str] = Counter()
    mood_distribution: Counter[str] = Counter()
    for row in rows:
        instrument_distribution.update(
            item for item in row["instruments"].split(";") if item
        )
        instrument_major_distribution.update(
            item for item in row["instrument_major_groups"].split(";") if item
        )
        mood_distribution.update(item for item in row["moods"].split(";") if item)
    split_distribution = Counter(row["split"] for row in rows if row["split"])
    time_signature_distribution = Counter(
        row["time_signature"] for row in rows if row["time_signature"]
    )
    tempo_bpm_distribution = Counter(
        row["tempo_bpm"] for row in rows if row["tempo_bpm"]
    )
    western_key_distribution = Counter(
        row["western_key"] for row in rows if row["western_key"]
    )
    stem_count_distribution = Counter(row["stem_count"] for row in rows)

    matched_stem_count = 0
    missing_declared_stems: list[str] = []
    unique_declared_stem_names = list(dict.fromkeys(declared_stem_names))
    for name in unique_declared_stem_names:
        key = unicodedata.normalize("NFC", name).casefold()
        matches = audio_index.get(key, [])
        if len(matches) == 1:
            matched_stem_count += 1
        elif not matches:
            missing_declared_stems.append(name)

    malformed_time_signatures: list[dict[str, str]] = []
    unusual_time_signatures: list[dict[str, str]] = []
    for row in rows:
        value = row["time_signature"]
        if not re.fullmatch(r"\d+/\d+", value):
            malformed_time_signatures.append(
                {"audio_id": row["audio_id"], "value": value}
            )
            continue
        numerator = int(value.split("/", 1)[0])
        if numerator > 32:
            unusual_time_signatures.append(
                {
                    "audio_id": row["audio_id"],
                    "value": value,
                    "reason": "numerator greater than 32; verify against source/guide",
                }
            )

    invalid_tempo_values: list[dict[str, str]] = []
    tempo_numbers: list[float] = []
    for row in rows:
        try:
            tempo = float(row["tempo_bpm"])
            if not math.isfinite(tempo) or tempo <= 0:
                raise ValueError
            tempo_numbers.append(tempo)
        except (TypeError, ValueError):
            invalid_tempo_values.append(
                {"audio_id": row["audio_id"], "value": row["tempo_bpm"]}
            )

    audio_id_file_name_mismatches = [
        {
            "audio_id": row["audio_id"],
            "audio_file_name": row["audio_file_name"],
        }
        for row in rows
        if row["audio_file_name"]
        and Path(row["audio_file_name"]).stem != row["audio_id"]
    ]

    summary = {
        "status": "ok" if rows else "no_json_files",
        "input_directory": str(input_dir),
        "json_file_count": len(json_files),
        "raw_parsed_record_count": raw_parsed_record_count,
        "parsed_record_count": len(rows),
        "identical_duplicate_record_count": identical_duplicate_count,
        "conflicting_duplicate_record_count": conflicting_duplicate_count,
        "master_audio_count": sum(bool(row["audio_file_name"]) for row in rows),
        "declared_stem_audio_count": sum(int(row["stem_count"]) for row in rows),
        "local_wav_file_count": sum(len(paths) for paths in audio_index.values()),
        "matched_master_wav_count": sum(bool(row["audio_path"]) for row in rows),
        "matched_stem_wav_count": matched_stem_count,
        "missing_declared_stem_file_count": len(missing_declared_stems),
        "missing_declared_stem_files_sample": missing_declared_stems[:20],
        "explicit_jangdan_record_count": sum(bool(row["jangdan"]) for row in rows),
        "duration_available_record_count": sum(bool(row["duration"]) for row in rows),
        "local_audio_available_record_count": sum(
            row["has_local_audio"] == "true" for row in rows
        ),
        "malformed_time_signature_count": len(malformed_time_signatures),
        "malformed_time_signatures_sample": malformed_time_signatures[:20],
        "unusual_time_signature_count": len(unusual_time_signatures),
        "unusual_time_signature_distribution": dict(
            Counter(item["value"] for item in unusual_time_signatures).most_common()
        ),
        "unusual_time_signatures_sample": unusual_time_signatures[:20],
        "invalid_tempo_value_count": len(invalid_tempo_values),
        "invalid_tempo_values_sample": invalid_tempo_values[:20],
        "tempo_bpm_range": {
            "min": min(tempo_numbers) if tempo_numbers else None,
            "max": max(tempo_numbers) if tempo_numbers else None,
        },
        "audio_id_file_name_mismatch_count": len(audio_id_file_name_mismatches),
        "audio_id_file_name_mismatches_sample": audio_id_file_name_mismatches[:20],
        "genre_distribution": dict(genre_distribution.most_common()),
        "genre_major_distribution": dict(genre_major_distribution.most_common()),
        "genre_sub_distribution": dict(genre_sub_distribution.most_common()),
        "genre_detail_distribution": dict(genre_detail_distribution.most_common()),
        "instrument_distribution": dict(instrument_distribution.most_common()),
        "instrument_major_distribution": dict(
            instrument_major_distribution.most_common()
        ),
        "mood_distribution": dict(mood_distribution.most_common()),
        "time_signature_distribution": dict(
            time_signature_distribution.most_common()
        ),
        "tempo_bpm_distribution": dict(tempo_bpm_distribution.most_common()),
        "western_key_distribution": dict(western_key_distribution.most_common()),
        "stem_count_distribution": dict(stem_count_distribution.most_common()),
        "split_distribution": dict(split_distribution.most_common()),
        "missing_value_counts": missing,
        "all_csv_missing_value_counts": all_csv_missing,
        "parse_errors": parse_errors,
        "anomalies": anomalies,
        "notes": [
            "timeSignature is exported only as time_signature and is never mapped to jangdan.",
            "duration is populated only from an explicit duration field or a readable local WAV.",
        ],
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    with args.summary.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(
        f"Wrote {len(rows)} row(s) to {args.output}; "
        f"summary status={summary['status']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
