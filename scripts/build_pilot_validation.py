#!/usr/bin/env python3
"""Validate the pilot and analyze saved similarities without model inference."""

from __future__ import annotations

import csv
import hashlib
import json
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "pilot_dataset.csv"
OUT_DIR = ROOT / "artifacts" / "pilot_validation"
SEED = 20261122
N_BOOT = 100_000

REVIEW_FIELDS = [
    "audio_id", "genre", "instruments", "native_kr", "en", "mt_kr",
    "romanized_en", "descriptive_en", "native_label_consistency",
    "translation_semantic_equivalence", "h2_semantic_equivalence",
    "review_notes", "review_status",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def has_final_consonant(text: str) -> bool:
    for char in reversed(text.strip()):
        if "가" <= char <= "힣":
            return (ord(char) - ord("가")) % 28 != 0
    return False


def native_template(row: dict[str, str], instruments: list[str]) -> str:
    if row["genre_major"] == row["genre"]:
        first = f"이 곡은 {row['genre']}이다."
    else:
        first = f"이 곡은 {row['genre_major']}에 속하는 {row['genre']}이다."
    particle = "이" if has_final_consonant(instruments[-1]) else "가"
    return f"{first} 편성에는 {'·'.join(instruments)}{particle} 포함된다."


def metadata_key(row: dict[str, str]) -> tuple[str, str, tuple[str, ...]]:
    instruments = tuple(sorted(x for x in row["instruments"].split(";") if x))
    return row["genre_major"], row["genre"], instruments


def make_groups(rows: list[dict[str, str]]) -> list[list[int]]:
    groups: list[list[int]] = []
    positions: dict[tuple[str, str, tuple[str, ...]], int] = {}
    for index, row in enumerate(rows):
        key = metadata_key(row)
        if key not in positions:
            positions[key] = len(groups)
            groups.append([])
        groups[positions[key]].append(index)
    return groups


def resolve_audio(row: dict[str, str]) -> tuple[Path, str]:
    path = ROOT / row["audio_path"]
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open("rb") as handle:
        header = handle.read(256)
    if not header.startswith(b"version https://git-lfs.github.com/spec/v1"):
        return path, "worktree_audio"
    pointer = path.read_text(encoding="ascii")
    oid_lines = [x for x in pointer.splitlines() if x.startswith("oid sha256:")]
    if len(oid_lines) != 1:
        raise ValueError(f"Malformed Git LFS pointer: {path}")
    oid = oid_lines[0].split(":", 1)[1]
    if oid != row["audio_sha256"]:
        raise ValueError(f"LFS OID mismatch: {row['audio_id']}")
    obj = ROOT / ".git" / "lfs" / "objects" / oid[:2] / oid[2:4] / oid
    return obj, "git_lfs_object"


def translation_review(row: dict[str, str]) -> tuple[str, str]:
    if row["genre_major"] == "창작국악":
        return (
            "auto_flagged_scope_shift_needs_human_review",
            "H1: 창작국악→contemporary gugak→현대 국악으로 범위가 달라질 수 있음.",
        )
    if row["genre_major"] == "민속악":
        return (
            "auto_flagged_genre_term_generalization_needs_human_review",
            "H1: 민속악→folk music→민속 음악으로 용어가 일반화됨.",
        )
    return (
        "auto_preserved_surface_change_needs_human_review",
        "H1: 악기·장르 정보는 유지되고 띄어쓰기와 목록 표기만 변함.",
    )


def h2_review(term: str) -> tuple[str, str]:
    if term == "장구":
        return (
            "auto_plausible_needs_human_review",
            "H2: hourglass-shaped drum은 형태를 비교적 잘 보존하나 사람 검토 전임.",
        )
    if term == "소리북":
        return (
            "auto_flagged_broad_gloss_needs_human_review",
            "H2: Korean barrel drum은 판소리 반주 용도와 구별 특징을 생략한 넓은 표현임.",
        )
    if term == "대금":
        return (
            "auto_flagged_nonunique_gloss_needs_human_review",
            "H2: Korean transverse bamboo flute은 대금을 다른 한국 횡적과 고유하게 구별하지 못함.",
        )
    raise ValueError(f"Unexpected H2 term: {term}")


def validate_dataset(rows: list[dict[str, str]]) -> tuple[list[dict[str, object]], dict[str, object]]:
    if len(rows) != 33 or len({row["audio_id"] for row in rows}) != 33:
        raise ValueError("Expected exactly 33 unique pilot rows")
    groups = make_groups(rows)
    membership = {
        member: (f"g{group_index:02d}", len(members))
        for group_index, members in enumerate(groups, 1)
        for member in members
    }
    review_rows: list[dict[str, object]] = []
    sources: Counter[str] = Counter()
    translation_counts: Counter[str] = Counter()
    h2_counts: Counter[str] = Counter()
    actual_terms: Counter[str] = Counter()
    hashes: set[str] = set()
    checks_passed = 0
    audio_bytes = 0

    for index, row in enumerate(rows):
        label_path = ROOT / row["label_path"]
        with label_path.open(encoding="utf-8-sig") as handle:
            label = json.load(handle)
        master, tags = label["master"], label["master"]["tags"]
        label_instruments: list[str] = []
        for stem in label["stems"]:
            value = stem["tags"]["instrumentSub"]
            if value not in label_instruments:
                label_instruments.append(value)
        csv_instruments = [x for x in row["instruments"].split(";") if x]
        checks = {
            "project_name": nfc(label["project_name"]) == nfc(row["audio_id"]),
            "master_stem": nfc(Path(master["file_name"]).stem) == nfc(row["audio_id"]),
            "audio_stem": nfc(Path(row["audio_path"]).stem) == nfc(row["audio_id"]),
            "label_directory": nfc(label_path.parent.name) == nfc(f"VL_{row['audio_id']}"),
            "genre_major": tags["genreMajor"] == row["genre_major"],
            "genre": tags["genreSub"] == row["genre"],
            "genre_detail": tags["genreDetail"] == row["genre_detail"],
            "title": tags["title"] == row["title"],
            "instruments": label_instruments == csv_instruments,
            "sample_rate": str(tags["sampleRate"]) == row["sample_rate"],
            "bit_depth": str(tags["bitDepth"]) == row["bit_depth"],
            "native": native_template(row, label_instruments) == row["native_kr"],
            "h2_target": row["h2_target_term_kr"] in label_instruments,
        }
        failed = [name for name, ok in checks.items() if not ok]
        if failed:
            raise ValueError(f"{row['audio_id']}: failed {failed}")
        checks_passed += len(checks)

        audio, source = resolve_audio(row)
        with audio.open("rb") as handle:
            header = handle.read(12)
        if header[:4] != b"RIFF" or header[8:12] != b"WAVE":
            raise ValueError(f"Not RIFF/WAVE: {row['audio_id']}")
        digest = sha256_file(audio)
        if digest != row["audio_sha256"] or digest in hashes:
            raise ValueError(f"Bad or duplicate audio hash: {row['audio_id']}")
        hashes.add(digest)
        sources[source] += 1
        audio_bytes += audio.stat().st_size

        translation_status, translation_note = translation_review(row)
        h2_status, h2_note = h2_review(row["h2_target_term_kr"])
        translation_counts[translation_status] += 1
        h2_counts[h2_status] += 1
        for term in ("장구", "소리북", "대금"):
            if term in label_instruments:
                actual_terms[term] += 1
        group_id, group_size = membership[index]
        review_rows.append({
            "audio_id": row["audio_id"], "genre": row["genre"],
            "instruments": row["instruments"], "native_kr": row["native_kr"],
            "en": row["en"], "mt_kr": row["mt_kr"],
            "romanized_en": row["romanized_en"],
            "descriptive_en": row["descriptive_en"],
            "native_label_consistency": "auto_verified_label_match_needs_human_review",
            "translation_semantic_equivalence": translation_status,
            "h2_semantic_equivalence": h2_status,
            "review_notes": (
                "자동검증: WAV–JSON–Audio ID와 Label 기반 장르·전체 악기 설명이 일치함. "
                f"{translation_note} {h2_note} 동일 H1 설명 그룹 {group_id}의 크기는 {group_size}. "
                "Retrieval positive는 Label 기반이며 실제 청감 relevance는 검증되지 않음."
            ),
            "review_status": "needs_human_review",
        })

    summary = {
        "rows": 33, "unique_audio_ids": 33,
        "label_field_checks_passed": checks_passed,
        "label_field_checks_expected": 33 * 13,
        "audio_sources": dict(sources), "audio_total_bytes": audio_bytes,
        "unique_audio_sha256": len(hashes), "metadata_groups": len(groups),
        "group_size_distribution": dict(sorted(Counter(map(len, groups)).items())),
        "unique_text_counts": {
            field: len({row[field] for row in rows})
            for field in ("native_kr", "en", "mt_kr", "romanized_en", "descriptive_en")
        },
        "translation_semantic_equivalence": dict(translation_counts),
        "h2_semantic_equivalence": dict(h2_counts),
        "assigned_h2_targets": dict(Counter(row["h2_target_term_kr"] for row in rows)),
        "label_instrument_occurrences": dict(actual_terms),
        "human_reviewed_rows": 0, "needs_human_review_rows": 33,
    }
    return review_rows, summary


def load_similarity(directory: Path, conditions: tuple[str, ...]) -> tuple[list[str], dict[str, np.ndarray]]:
    order = (directory / "candidate_order.txt").read_text(encoding="utf-8").splitlines()
    matrices = {condition: np.load(directory / f"{condition}.npy") for condition in conditions}
    if len(order) != 33:
        raise ValueError("Expected 33 candidate IDs")
    for condition, matrix in matrices.items():
        if matrix.shape != (33, 33) or not np.isfinite(matrix).all():
            raise ValueError(f"Invalid {condition} matrix: {matrix.shape}")
    return order, matrices


def rank(scores: np.ndarray, positive_index: int) -> int:
    return 1 + int(np.count_nonzero(scores > scores[positive_index]))


def bootstrap(values: np.ndarray) -> dict[str, object]:
    rng = np.random.default_rng(SEED)
    distributions: list[np.ndarray] = []
    remaining = N_BOOT
    while remaining:
        chunk = min(10_000, remaining)
        indices = rng.integers(0, len(values), size=(chunk, len(values)))
        distributions.append(values[indices].mean(axis=1))
        remaining -= chunk
    samples = np.concatenate(distributions)
    low, high = np.percentile(samples, [2.5, 97.5])
    return {
        "estimate": float(values.mean()),
        "ci_95_percentile": [float(low), float(high)],
        "replicates": N_BOOT, "seed": SEED,
        "resampling_unit": "metadata_group",
    }


def analyze_h1(pilot_by_id: dict[str, dict[str, str]]) -> tuple[list[dict[str, object]], dict[str, object]]:
    order, matrices = load_similarity(
        ROOT / "artifacts" / "h1_retrieval" / "similarity",
        ("native_kr", "en", "mt_kr"),
    )
    rows = [pilot_by_id[audio_id] for audio_id in order]
    groups = make_groups(rows)
    output: list[dict[str, object]] = []
    metrics: dict[str, object] = {}
    for aggregation in ("max", "mean"):
        rr_values: dict[str, list[float]] = {condition: [] for condition in matrices}
        for group_index, members in enumerate(groups):
            result: dict[str, object] = {
                "candidate_aggregation": aggregation,
                "group_id": f"g{group_index + 1:02d}",
                "group_size": len(members),
                "member_audio_ids": ";".join(order[i] for i in members),
            }
            for condition, matrix in matrices.items():
                if not np.allclose(matrix[members], matrix[members[0]], atol=1e-7, rtol=0):
                    raise ValueError(f"Different {condition} query rows within group")
                scores = matrix[members[0]]
                if aggregation == "max":
                    group_scores = np.array([scores[candidates].max() for candidates in groups])
                else:
                    group_scores = np.array([scores[candidates].mean() for candidates in groups])
                group_rank = rank(group_scores, group_index)
                rr = 1.0 / group_rank
                result[f"{condition}_rank"] = group_rank
                result[f"{condition}_rr"] = f"{rr:.12f}"
                rr_values[condition].append(rr)
            output.append(result)
        arrays = {key: np.asarray(value) for key, value in rr_values.items()}
        metrics[aggregation] = {
            "query_groups": len(groups), "candidate_groups": len(groups),
            "mrr": {key: float(value.mean()) for key, value in arrays.items()},
            "native_minus_mt": bootstrap(arrays["native_kr"] - arrays["mt_kr"]),
            "native_minus_en": bootstrap(arrays["native_kr"] - arrays["en"]),
        }
    return output, metrics


def average_descending_ranks(scores: np.ndarray) -> np.ndarray:
    order = np.argsort(-scores, kind="mergesort")
    ranks = np.empty(len(scores), dtype=float)
    start = 0
    while start < len(scores):
        end = start + 1
        while end < len(scores) and scores[order[end]] == scores[order[start]]:
            end += 1
        ranks[order[start:end]] = (start + 1 + end) / 2.0
        start = end
    return ranks


def average_precision(scores: np.ndarray, positives: np.ndarray) -> float:
    order = np.argsort(-scores, kind="mergesort")
    relevant = positives[order].astype(int)
    precision = np.cumsum(relevant) / np.arange(1, len(relevant) + 1)
    return float(precision[relevant == 1].mean())


def auroc(scores: np.ndarray, positives: np.ndarray) -> float:
    differences = scores[positives, None] - scores[~positives][None, :]
    wins = np.count_nonzero(differences > 0)
    ties = np.count_nonzero(differences == 0)
    return float((wins + 0.5 * ties) / differences.size)


def analyze_h2(pilot_by_id: dict[str, dict[str, str]]) -> tuple[list[dict[str, object]], dict[str, object]]:
    order, matrices = load_similarity(
        ROOT / "artifacts" / "h2_retrieval" / "similarity",
        ("romanized_en", "descriptive_en"),
    )
    rows = [pilot_by_id[audio_id] for audio_id in order]
    assigned: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        assigned[row["h2_target_term_kr"]].append(index)
    output: list[dict[str, object]] = []
    metrics: dict[str, object] = {}
    for term in ("장구", "소리북", "대금"):
        indices = assigned[term]
        positives = np.array([term in row["instruments"].split(";") for row in rows])
        result: dict[str, object] = {
            "target_term": term, "assigned_rows": len(indices),
            "positive_count": int(positives.sum()),
            "negative_count": int((~positives).sum()),
            "prevalence_ap_baseline": f"{positives.mean():.12f}",
        }
        vectors: dict[str, np.ndarray] = {}
        for condition, matrix in matrices.items():
            # Identical H2 strings were encoded in separate batches; saved cosine
            # rows differ by at most 1.35e-7 from floating-point roundoff.
            if not np.allclose(matrix[indices], matrix[indices[0]], atol=1e-6, rtol=0):
                raise ValueError(f"Different {condition} rows for {term}")
            scores = matrix[indices[0]]
            vectors[condition] = scores
            result[f"{condition}_auroc"] = f"{auroc(scores, positives):.12f}"
            result[f"{condition}_average_precision"] = f"{average_precision(scores, positives):.12f}"
        roman_ranks = average_descending_ranks(vectors["romanized_en"])
        descriptive_ranks = average_descending_ranks(vectors["descriptive_en"])
        result["ranking_spearman_rho"] = f"{np.corrcoef(roman_ranks, descriptive_ranks)[0, 1]:.12f}"
        for k in (5, 10):
            roman_top = set(np.argsort(-vectors["romanized_en"], kind="mergesort")[:k])
            desc_top = set(np.argsort(-vectors["descriptive_en"], kind="mergesort")[:k])
            result[f"top_{k}_overlap"] = len(roman_top & desc_top)
        output.append(result)
        metrics[term] = {
            key: float(value) if isinstance(value, str) else value
            for key, value in result.items() if key != "target_term"
        }
    return output, metrics


def main() -> int:
    rows = read_csv(PILOT)
    by_id = {row["audio_id"]: row for row in rows}
    review_rows, validation = validate_dataset(rows)
    write_csv(ROOT / "pilot_review.csv", review_rows, REVIEW_FIELDS)

    h1_rows, h1_metrics = analyze_h1(by_id)
    write_csv(OUT_DIR / "h1_group_candidate_results.csv", h1_rows, list(h1_rows[0]))
    h2_rows, h2_metrics = analyze_h2(by_id)
    write_csv(OUT_DIR / "h2_term_detection_results.csv", h2_rows, list(h2_rows[0]))

    input_paths = {
        "pilot_dataset": PILOT,
        "h1_retrieval_results": ROOT / "h1_retrieval_results.csv",
        "h2_retrieval_results": ROOT / "h2_retrieval_results.csv",
    }
    metrics = {
        "method": "read_only_validation_and_saved_similarity_analysis_no_model_inference",
        "inputs": {f"{key}_sha256": sha256_file(path) for key, path in input_paths.items()},
        "dataset_validation": validation,
        "h1_group_candidate_sensitivity": h1_metrics,
        "h2_unique_term_instrument_presence": h2_metrics,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "pilot_review_rows": len(review_rows), "human_reviewed_rows": 0,
        "metadata_groups": validation["metadata_groups"],
        "h1": h1_metrics, "h2": h2_metrics,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
