#!/usr/bin/env python3
"""Prepare and evaluate the 33-item CLaMP 3 H1 retrieval pilot.

The preparation step validates the immutable Pilot CSV, resolves Git LFS
objects without materializing a second copy of the WAV files, and writes the
three text conditions. The evaluation step consumes official CLaMP 3 global
embeddings and computes multi-positive text-to-audio retrieval metrics.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONDITIONS = ("native_kr", "en", "mt_kr")
EXPECTED_ROWS = 33
EXPECTED_DIM = 768


def project_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def read_dataset(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Missing CSV header: {path}")
        rows = list(reader)
        fieldnames = list(reader.fieldnames)

    required = {
        "audio_id",
        "audio_path",
        "audio_sha256",
        "genre",
        "genre_major",
        "instruments",
        *CONDITIONS,
    }
    missing = required - set(fieldnames)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    if len(rows) != EXPECTED_ROWS:
        raise ValueError(f"Expected {EXPECTED_ROWS} rows, found {len(rows)}")

    audio_ids = [row["audio_id"] for row in rows]
    if len(set(audio_ids)) != EXPECTED_ROWS:
        raise ValueError("audio_id values are not unique")
    if len({row["audio_path"] for row in rows}) != EXPECTED_ROWS:
        raise ValueError("audio_path values are not unique")
    for row in rows:
        for condition in CONDITIONS:
            if not row[condition].strip():
                raise ValueError(f"Empty {condition}: {row['audio_id']}")
    return fieldnames, rows


def signature(row: dict[str, str]) -> tuple[str, str, tuple[str, ...]]:
    instruments = tuple(
        sorted(item.strip() for item in row["instruments"].split(";") if item.strip())
    )
    return row["genre_major"].strip(), row["genre"].strip(), instruments


def signature_groups(rows: list[dict[str, str]]) -> dict[tuple[Any, ...], list[str]]:
    groups: dict[tuple[Any, ...], list[str]] = defaultdict(list)
    for row in rows:
        groups[signature(row)].append(row["audio_id"])
    return dict(groups)


def validate_caption_groups(rows: list[dict[str, str]]) -> None:
    expected = {
        frozenset(audio_ids) for audio_ids in signature_groups(rows).values()
    }
    for condition in CONDITIONS:
        caption_groups: dict[str, list[str]] = defaultdict(list)
        for row in rows:
            caption_groups[row[condition]].append(row["audio_id"])
        observed = {frozenset(audio_ids) for audio_ids in caption_groups.values()}
        if observed != expected:
            raise ValueError(
                f"Exact-caption groups do not match metadata groups for {condition}"
            )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_lfs_pointer(path: Path) -> tuple[str, int] | None:
    if path.stat().st_size > 1024:
        return None
    text = path.read_text(encoding="utf-8")
    if not text.startswith("version https://git-lfs.github.com/spec/v1\n"):
        return None
    values = dict(line.split(" ", 1) for line in text.splitlines()[1:] if " " in line)
    oid = values.get("oid", "")
    if not oid.startswith("sha256:") or "size" not in values:
        raise ValueError(f"Malformed Git LFS pointer: {path}")
    return oid.removeprefix("sha256:"), int(values["size"])


def resolve_wav(row: dict[str, str]) -> tuple[Path, str]:
    worktree_path = project_path(row["audio_path"])
    if not worktree_path.is_file():
        raise FileNotFoundError(worktree_path)
    pointer = parse_lfs_pointer(worktree_path)
    if pointer is None:
        target = worktree_path
        source = "worktree_wav"
    else:
        oid, expected_size = pointer
        if oid != row["audio_sha256"]:
            raise ValueError(f"LFS pointer hash mismatch: {row['audio_id']}")
        target = PROJECT_ROOT / ".git" / "lfs" / "objects" / oid[:2] / oid[2:4] / oid
        if not target.is_file() or target.stat().st_size != expected_size:
            raise FileNotFoundError(f"Missing/incomplete LFS object: {target}")
        source = "git_lfs_object"

    with target.open("rb") as handle:
        header = handle.read(12)
    if header[:4] != b"RIFF" or header[8:12] != b"WAVE":
        raise ValueError(f"Not a RIFF/WAVE file: {target}")
    if sha256_file(target) != row["audio_sha256"]:
        raise ValueError(f"WAV SHA-256 mismatch: {row['audio_id']}")
    return target.resolve(), source


def write_if_equal_or_new(path: Path, text: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise ValueError(f"Refusing to overwrite differing generated input: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def prepare(args: argparse.Namespace) -> int:
    dataset = project_path(args.dataset)
    artifact_root = project_path(args.artifact_root)
    _, rows = read_dataset(dataset)
    validate_caption_groups(rows)

    staging = artifact_root / "staging" / "audio"
    staging.mkdir(parents=True, exist_ok=True)
    source_counts: Counter[str] = Counter()
    resolved_rows = []

    for row in rows:
        target, source = resolve_wav(row)
        source_counts[source] += 1
        link = staging / f"{row['audio_id']}.wav"
        if os.path.lexists(link):
            if not link.is_symlink() or link.resolve() != target:
                raise ValueError(f"Unexpected existing staging path: {link}")
        else:
            link.symlink_to(target)
        resolved_rows.append(
            {
                "audio_id": row["audio_id"],
                "staging_path": str(link.relative_to(PROJECT_ROOT)),
                "source": source,
                "bytes": target.stat().st_size,
                "sha256": row["audio_sha256"],
            }
        )

        for condition in CONDITIONS:
            text_path = artifact_root / "inputs" / "text" / condition / f"{row['audio_id']}.txt"
            write_if_equal_or_new(text_path, row[condition])

    groups = signature_groups(rows)
    duplicate_groups = [ids for ids in groups.values() if len(ids) > 1]
    audit = {
        "dataset": str(dataset.relative_to(PROJECT_ROOT)),
        "dataset_sha256": sha256_file(dataset),
        "rows": len(rows),
        "unique_audio_ids": len({row["audio_id"] for row in rows}),
        "complete_texts": {condition: len(rows) for condition in CONDITIONS},
        "unique_texts": {
            condition: len({row[condition] for row in rows}) for condition in CONDITIONS
        },
        "answer_definition": "genre_major + genre + unordered validated instrument set",
        "answer_groups": len(groups),
        "group_size_distribution": dict(sorted(Counter(map(len, groups.values())).items())),
        "duplicate_groups": duplicate_groups,
        "audio_sources": dict(source_counts),
        "audio_total_bytes": sum(item["bytes"] for item in resolved_rows),
        "audio_files": resolved_rows,
    }
    artifact_root.mkdir(parents=True, exist_ok=True)
    (artifact_root / "data_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"Prepared {len(rows)} audios and {len(rows) * len(CONDITIONS)} texts; "
        f"{len(groups)} multi-positive groups; sources={dict(source_counts)}"
    )
    return 0


def load_embedding(path: Path, np: Any) -> tuple[Any, dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    array = np.load(path, allow_pickle=False)
    if array.shape != (1, EXPECTED_DIM):
        raise ValueError(f"Unexpected embedding shape {array.shape}: {path}")
    if array.dtype != np.float32:
        raise ValueError(f"Unexpected embedding dtype {array.dtype}: {path}")
    nan_count = int(np.isnan(array).sum())
    inf_count = int(np.isinf(array).sum())
    if nan_count or inf_count:
        raise ValueError(f"Non-finite embedding: {path}")
    vector = array[0]
    norm = float(np.linalg.norm(vector))
    if not norm:
        raise ValueError(f"Zero-norm embedding: {path}")
    validation = {
        "shape": "(1, 768)",
        "dtype": str(array.dtype),
        "nan_count": nan_count,
        "inf_count": inf_count,
        "l2_norm": f"{norm:.9f}",
    }
    return vector, validation


def rank_first_positive(scores: Any, positive_indices: list[int], np: Any) -> int:
    best_positive = float(np.max(scores[positive_indices]))
    # Competition ranking makes exact similarity ties independent of CSV order.
    return 1 + int(np.count_nonzero(scores > best_positive))


def evaluate(args: argparse.Namespace) -> int:
    import numpy as np

    dataset = project_path(args.dataset)
    artifact_root = project_path(args.artifact_root)
    output_csv = project_path(args.output)
    _, rows = read_dataset(dataset)
    validate_caption_groups(rows)
    audio_ids = [row["audio_id"] for row in rows]

    validation_rows: list[dict[str, Any]] = []
    audio_vectors = []
    for audio_id in audio_ids:
        path = artifact_root / "embeddings" / "audio" / f"{audio_id}.npy"
        vector, validation = load_embedding(path, np)
        audio_vectors.append(vector)
        validation_rows.append(
            {"modality": "audio", "condition": "audio", "audio_id": audio_id, **validation}
        )
    audio_matrix = np.stack(audio_vectors)
    audio_matrix = audio_matrix / np.linalg.norm(audio_matrix, axis=1, keepdims=True)

    condition_scores: dict[str, Any] = {}
    for condition in CONDITIONS:
        vectors = []
        for audio_id in audio_ids:
            path = artifact_root / "embeddings" / "text" / condition / f"{audio_id}.npy"
            vector, validation = load_embedding(path, np)
            vectors.append(vector)
            validation_rows.append(
                {"modality": "text", "condition": condition, "audio_id": audio_id, **validation}
            )
        text_matrix = np.stack(vectors)
        text_matrix = text_matrix / np.linalg.norm(text_matrix, axis=1, keepdims=True)
        condition_scores[condition] = text_matrix @ audio_matrix.T

    signature_to_indices: dict[tuple[Any, ...], list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        signature_to_indices[signature(row)].append(index)

    result_rows = []
    per_condition_rr: dict[str, list[float]] = {condition: [] for condition in CONDITIONS}
    per_condition_rank: dict[str, list[int]] = {condition: [] for condition in CONDITIONS}
    for query_index, row in enumerate(rows):
        positives = signature_to_indices[signature(row)]
        ranks: dict[str, int] = {}
        rrs: dict[str, float] = {}
        for condition in CONDITIONS:
            rank = rank_first_positive(condition_scores[condition][query_index], positives, np)
            rr = 1.0 / rank
            ranks[condition] = rank
            rrs[condition] = rr
            per_condition_rank[condition].append(rank)
            per_condition_rr[condition].append(rr)
        result_rows.append(
            {
                "audio_id": row["audio_id"],
                "positive_count": len(positives),
                "native_kr_rank": ranks["native_kr"],
                "en_rank": ranks["en"],
                "mt_kr_rank": ranks["mt_kr"],
                "native_kr_rr": f"{rrs['native_kr']:.9f}",
                "en_rr": f"{rrs['en']:.9f}",
                "mt_kr_rr": f"{rrs['mt_kr']:.9f}",
                "native_to_mt_rank_change": ranks["mt_kr"] - ranks["native_kr"],
            }
        )

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    result_fields = [
        "audio_id",
        "positive_count",
        "native_kr_rank",
        "en_rank",
        "mt_kr_rank",
        "native_kr_rr",
        "en_rr",
        "mt_kr_rr",
        "native_to_mt_rank_change",
    ]
    with output_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=result_fields)
        writer.writeheader()
        writer.writerows(result_rows)

    validation_path = artifact_root / "embedding_validation.csv"
    validation_fields = [
        "modality",
        "condition",
        "audio_id",
        "shape",
        "dtype",
        "nan_count",
        "inf_count",
        "l2_norm",
    ]
    with validation_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=validation_fields)
        writer.writeheader()
        writer.writerows(validation_rows)

    similarity_dir = artifact_root / "similarity"
    similarity_dir.mkdir(parents=True, exist_ok=True)
    for condition, scores in condition_scores.items():
        np.save(similarity_dir / f"{condition}.npy", scores.astype(np.float32))
    (similarity_dir / "candidate_order.txt").write_text(
        "\n".join(audio_ids) + "\n", encoding="utf-8"
    )

    mrr = {
        condition: float(np.mean(per_condition_rr[condition]))
        for condition in CONDITIONS
    }
    rank_changes = [
        mt_rank - native_rank
        for native_rank, mt_rank in zip(
            per_condition_rank["native_kr"], per_condition_rank["mt_kr"]
        )
    ]
    metrics = {
        "queries": len(rows),
        "candidates": len(rows),
        "answer_groups": len(signature_to_indices),
        "answer_definition": "multi-positive: genre_major + genre + unordered validated instrument set",
        "ranking": "1 + count(scores strictly greater than best positive score)",
        "mrr": mrr,
        "delta_mrr_native_minus_mt": mrr["native_kr"] - mrr["mt_kr"],
        "native_to_mt_rank_change": {
            "improved": sum(change < 0 for change in rank_changes),
            "unchanged": sum(change == 0 for change in rank_changes),
            "worsened": sum(change > 0 for change in rank_changes),
            "mean": float(np.mean(rank_changes)),
        },
        "embedding_counts": {"audio": len(rows), **{condition: len(rows) for condition in CONDITIONS}},
        "embedding_shape": [1, EXPECTED_DIM],
        "embedding_dtype": "float32",
        "nonfinite_values": 0,
    }
    (artifact_root / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="pilot_dataset.csv")
    parser.add_argument("--artifact-root", default="artifacts/h1_retrieval")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("prepare")
    evaluate_parser = subparsers.add_parser("evaluate")
    evaluate_parser.add_argument("--output", default="h1_retrieval_results.csv")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "prepare":
        return prepare(args)
    if args.command == "evaluate":
        return evaluate(args)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
