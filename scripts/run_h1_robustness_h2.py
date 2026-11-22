#!/usr/bin/env python3
"""H1 group robustness analysis and H2 terminology retrieval evaluation."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from statistics import fmean
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ROWS = 33
EXPECTED_DIM = 768
H2_CONDITIONS = ("romanized_en", "descriptive_en")
BOOTSTRAP_REPLICATES = 100_000
BOOTSTRAP_SEED = 20_261_122

H2_TERMS = {
    "장구": {
        "romanized": "janggu",
        "descriptive": "Korean hourglass-shaped drum",
        "equivalence_note": "Strong shape-level equivalence; human review still pending.",
    },
    "소리북": {
        "romanized": "soribuk",
        "descriptive": "Korean barrel drum",
        "equivalence_note": (
            "Broad/non-unique: the phrase omits the instrument's pansori-accompaniment "
            "function and tacked-head distinction."
        ),
    },
    "대금": {
        "romanized": "daegeum",
        "descriptive": "Korean transverse bamboo flute",
        "equivalence_note": (
            "Broad/non-unique: the phrase omits the daegeum's large size and membrane."
        ),
    },
}


def project_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Missing header: {path}")
        return list(reader.fieldnames), list(reader)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_dataset(path: Path) -> list[dict[str, str]]:
    fieldnames, rows = read_csv(path)
    required = {
        "audio_id",
        "genre_major",
        "genre",
        "instruments",
        "h2_target_term_kr",
        "h2_target_term_romanized",
        "romanized_en",
        "descriptive_en",
        "h2_equivalence_status",
        "review_status",
    }
    missing = required - set(fieldnames)
    if missing:
        raise ValueError(f"Missing Pilot fields: {sorted(missing)}")
    if len(rows) != EXPECTED_ROWS or len({row["audio_id"] for row in rows}) != EXPECTED_ROWS:
        raise ValueError("Pilot Dataset must contain exactly 33 unique audio IDs")
    return rows


def instruments(row: dict[str, str]) -> frozenset[str]:
    return frozenset(item.strip() for item in row["instruments"].split(";") if item.strip())


def signature(row: dict[str, str]) -> tuple[str, str, tuple[str, ...]]:
    return row["genre_major"], row["genre"], tuple(sorted(instruments(row)))


def ordered_groups(rows: list[dict[str, str]]) -> tuple[dict[tuple[Any, ...], str], dict[str, list[int]]]:
    signature_to_id: dict[tuple[Any, ...], str] = {}
    group_indices: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        key = signature(row)
        if key not in signature_to_id:
            signature_to_id[key] = f"g{len(signature_to_id) + 1:02d}"
        group_indices[signature_to_id[key]].append(index)
    if len(group_indices) != 17:
        raise ValueError(f"Expected 17 metadata groups, found {len(group_indices)}")
    return signature_to_id, dict(group_indices)


def quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return ordered[low]
    fraction = position - low
    return ordered[low] * (1 - fraction) + ordered[high] * fraction


def paired_bootstrap(
    differences: list[float],
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    rng = random.Random(seed)
    count = len(differences)
    samples = [
        sum(differences[rng.randrange(count)] for _ in range(count)) / count
        for _ in range(replicates)
    ]
    return {
        "estimate": fmean(differences),
        "ci_95_percentile": [quantile(samples, 0.025), quantile(samples, 0.975)],
        "replicates": replicates,
        "seed": seed,
        "resampling_unit": "metadata_group",
    }


def h1_condition_summary(rows: list[dict[str, str]], indices: list[int]) -> dict[str, float]:
    return {
        condition: fmean(1.0 / int(rows[index][f"{condition}_rank"]) for index in indices)
        for condition in ("native_kr", "en", "mt_kr")
    }


def analyze_h1(args: argparse.Namespace) -> int:
    dataset_rows = read_dataset(project_path(args.dataset))
    _, result_rows = read_csv(project_path(args.h1_results))
    if len(result_rows) != EXPECTED_ROWS:
        raise ValueError("H1 result row count is not 33")
    if [row["audio_id"] for row in dataset_rows] != [row["audio_id"] for row in result_rows]:
        raise ValueError("H1 result order/IDs do not match Pilot Dataset")

    signature_to_id, group_indices = ordered_groups(dataset_rows)
    group_rows: list[dict[str, Any]] = []
    for key, group_id in signature_to_id.items():
        indices = group_indices[group_id]
        ranks: dict[str, int] = {}
        for condition in ("native_kr", "en", "mt_kr"):
            observed = {int(result_rows[index][f"{condition}_rank"]) for index in indices}
            if len(observed) != 1:
                raise ValueError(f"Non-identical ranks inside {group_id}: {condition}")
            ranks[condition] = observed.pop()
        group_rows.append(
            {
                "group_id": group_id,
                "audio_ids": ";".join(dataset_rows[index]["audio_id"] for index in indices),
                "group_size": len(indices),
                "genre_major": key[0],
                "genre": key[1],
                "instruments": ";".join(key[2]),
                "native_kr_rank": ranks["native_kr"],
                "en_rank": ranks["en"],
                "mt_kr_rank": ranks["mt_kr"],
                "native_kr_rr": 1.0 / ranks["native_kr"],
                "en_rr": 1.0 / ranks["en"],
                "mt_kr_rr": 1.0 / ranks["mt_kr"],
            }
        )

    all_indices = list(range(EXPECTED_ROWS))
    query_mrr = h1_condition_summary(result_rows, all_indices)
    group_macro = {
        condition: fmean(float(row[f"{condition}_rr"]) for row in group_rows)
        for condition in ("native_kr", "en", "mt_kr")
    }
    native_mt_differences = [
        float(row["native_kr_rr"]) - float(row["mt_kr_rr"]) for row in group_rows
    ]
    native_en_differences = [
        float(row["native_kr_rr"]) - float(row["en_rr"]) for row in group_rows
    ]

    excluded_id = "0066_정악_풍류음악"
    excluded_index = next(
        index for index, row in enumerate(dataset_rows) if row["audio_id"] == excluded_id
    )
    excluded_group = signature_to_id[signature(dataset_rows[excluded_index])]
    kept_query_indices = [index for index in all_indices if index != excluded_index]
    kept_group_rows = [row for row in group_rows if row["group_id"] != excluded_group]
    excluded_query_mrr = h1_condition_summary(result_rows, kept_query_indices)
    excluded_group_macro = {
        condition: fmean(float(row[f"{condition}_rr"]) for row in kept_group_rows)
        for condition in ("native_kr", "en", "mt_kr")
    }

    metrics = {
        "group_definition": "genre_major + genre + unordered validated instrument set",
        "groups": len(group_rows),
        "group_size_distribution": dict(sorted(Counter(int(row["group_size"]) for row in group_rows).items())),
        "query_level_mrr": query_mrr,
        "group_macro_mrr": group_macro,
        "differences": {
            "native_minus_mt": {
                "query_level": query_mrr["native_kr"] - query_mrr["mt_kr"],
                "group_macro": group_macro["native_kr"] - group_macro["mt_kr"],
                "bootstrap": paired_bootstrap(native_mt_differences),
            },
            "native_minus_en": {
                "query_level": query_mrr["native_kr"] - query_mrr["en"],
                "group_macro": group_macro["native_kr"] - group_macro["en"],
                "bootstrap": paired_bootstrap(native_en_differences),
            },
        },
        "exclude_0066_query_keep_33_candidates": {
            "excluded_audio_id": excluded_id,
            "excluded_group": excluded_group,
            "query_count": len(kept_query_indices),
            "group_count": len(kept_group_rows),
            "query_level_mrr": excluded_query_mrr,
            "query_level_differences": {
                "native_minus_mt": excluded_query_mrr["native_kr"] - excluded_query_mrr["mt_kr"],
                "native_minus_en": excluded_query_mrr["native_kr"] - excluded_query_mrr["en"],
            },
            "group_macro_mrr": excluded_group_macro,
            "group_macro_differences": {
                "native_minus_mt": excluded_group_macro["native_kr"] - excluded_group_macro["mt_kr"],
                "native_minus_en": excluded_group_macro["native_kr"] - excluded_group_macro["en"],
            },
        },
    }

    artifact_root = project_path(args.h1_artifact_root)
    write_csv(
        artifact_root / "group_results.csv",
        [
            "group_id", "audio_ids", "group_size", "genre_major", "genre", "instruments",
            "native_kr_rank", "en_rank", "mt_kr_rank",
            "native_kr_rr", "en_rr", "mt_kr_rr",
        ],
        group_rows,
    )
    (artifact_root / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return 0


def expected_h2_text(term: str, condition: str) -> str:
    phrase_key = "romanized" if condition == "romanized_en" else "descriptive"
    return f"This piece features a {H2_TERMS[term][phrase_key]}."


def write_text_if_equal_or_new(path: Path, text: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise ValueError(f"Refusing to overwrite differing H2 input: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def validate_h2_descriptions(rows: list[dict[str, str]]) -> dict[str, Any]:
    assigned_counts: Counter[str] = Counter()
    label_counts: Counter[str] = Counter()
    for row in rows:
        row_instruments = instruments(row)
        for term in H2_TERMS:
            if term in row_instruments:
                label_counts[term] += 1
        term = row["h2_target_term_kr"]
        if term not in H2_TERMS:
            raise ValueError(f"Unexpected H2 term: {row['audio_id']} {term}")
        assigned_counts[term] += 1
        if term not in row_instruments:
            raise ValueError(f"H2 target absent from label: {row['audio_id']} {term}")
        if row["h2_target_term_romanized"] != H2_TERMS[term]["romanized"]:
            raise ValueError(f"Romanized target mismatch: {row['audio_id']}")
        for condition in H2_CONDITIONS:
            if row[condition] != expected_h2_text(term, condition):
                raise ValueError(f"Unexpected {condition}: {row['audio_id']}")
        if row["h2_equivalence_status"] != "needs_human_review":
            raise ValueError(f"H2 equivalence unexpectedly reviewed: {row['audio_id']}")
        if row["review_status"] != "needs_human_review":
            raise ValueError(f"Row unexpectedly reviewed: {row['audio_id']}")

    return {
        "rows": len(rows),
        "assigned_target_counts": dict(assigned_counts),
        "label_instrument_occurrence_counts": dict(label_counts),
        "unique_texts": {
            condition: len({row[condition] for row in rows}) for condition in H2_CONDITIONS
        },
        "structure": "This piece features a <target noun phrase>.",
        "equivalence_status": "needs_human_review",
        "term_notes": {term: values["equivalence_note"] for term, values in H2_TERMS.items()},
    }


def prepare_h2(args: argparse.Namespace) -> int:
    rows = read_dataset(project_path(args.dataset))
    audit = validate_h2_descriptions(rows)
    artifact_root = project_path(args.h2_artifact_root)
    for row in rows:
        for condition in H2_CONDITIONS:
            path = artifact_root / "inputs" / "text" / condition / f"{row['audio_id']}.txt"
            write_text_if_equal_or_new(path, row[condition])
    artifact_root.mkdir(parents=True, exist_ok=True)
    (artifact_root / "description_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    return 0


def load_embedding(path: Path, np: Any) -> tuple[Any, dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    array = np.load(path, allow_pickle=False)
    if array.shape != (1, EXPECTED_DIM) or array.dtype != np.float32:
        raise ValueError(f"Unexpected embedding {array.shape}/{array.dtype}: {path}")
    nan_count = int(np.isnan(array).sum())
    inf_count = int(np.isinf(array).sum())
    norm = float(np.linalg.norm(array))
    if nan_count or inf_count or not norm:
        raise ValueError(f"Invalid embedding: {path}")
    return array[0], {
        "shape": "(1, 768)", "dtype": "float32",
        "nan_count": nan_count, "inf_count": inf_count, "l2_norm": f"{norm:.9f}",
    }


def first_positive_rank(scores: Any, positives: list[int], np: Any) -> int:
    best_positive = float(np.max(scores[positives]))
    return 1 + int(np.count_nonzero(scores > best_positive))


def group_macro_from_results(
    result_rows: list[dict[str, Any]], group_indices: dict[str, list[int]], rr_field: str
) -> float:
    return fmean(
        fmean(float(result_rows[index][rr_field]) for index in indices)
        for indices in group_indices.values()
    )


def evaluate_h2(args: argparse.Namespace) -> int:
    import numpy as np

    dataset_rows = read_dataset(project_path(args.dataset))
    description_audit = validate_h2_descriptions(dataset_rows)
    signature_to_id, group_indices = ordered_groups(dataset_rows)
    for group_id, indices in group_indices.items():
        if len({dataset_rows[index]["h2_target_term_kr"] for index in indices}) != 1:
            raise ValueError(f"Inconsistent H2 target inside {group_id}")
    audio_ids = [row["audio_id"] for row in dataset_rows]
    h2_root = project_path(args.h2_artifact_root)
    h1_audio_root = project_path(args.audio_embeddings)

    validation_rows: list[dict[str, Any]] = []
    audio_vectors = []
    for audio_id in audio_ids:
        vector, validation = load_embedding(h1_audio_root / f"{audio_id}.npy", np)
        audio_vectors.append(vector)
        validation_rows.append(
            {"modality": "audio_reused", "condition": "audio", "audio_id": audio_id, **validation}
        )
    audio_matrix = np.stack(audio_vectors)
    audio_matrix /= np.linalg.norm(audio_matrix, axis=1, keepdims=True)

    scores: dict[str, Any] = {}
    for condition in H2_CONDITIONS:
        vectors = []
        for audio_id in audio_ids:
            vector, validation = load_embedding(
                h2_root / "embeddings" / "text" / condition / f"{audio_id}.npy", np
            )
            vectors.append(vector)
            validation_rows.append(
                {"modality": "text", "condition": condition, "audio_id": audio_id, **validation}
            )
        matrix = np.stack(vectors)
        matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
        scores[condition] = matrix @ audio_matrix.T

    signature_positives: dict[tuple[Any, ...], list[int]] = defaultdict(list)
    for index, row in enumerate(dataset_rows):
        signature_positives[signature(row)].append(index)
    term_positives = {
        term: [index for index, row in enumerate(dataset_rows) if term in instruments(row)]
        for term in H2_TERMS
    }

    result_rows: list[dict[str, Any]] = []
    for query_index, row in enumerate(dataset_rows):
        term = row["h2_target_term_kr"]
        group_id = signature_to_id[signature(row)]
        proxy_positives = signature_positives[signature(row)]
        semantic_positives = term_positives[term]
        ranks = {
            condition: first_positive_rank(scores[condition][query_index], proxy_positives, np)
            for condition in H2_CONDITIONS
        }
        term_ranks = {
            condition: first_positive_rank(scores[condition][query_index], semantic_positives, np)
            for condition in H2_CONDITIONS
        }
        result_rows.append(
            {
                "audio_id": row["audio_id"], "target_term": term, "group_id": group_id,
                "positive_count": len(proxy_positives),
                "term_positive_count": len(semantic_positives),
                "romanized_en": row["romanized_en"],
                "descriptive_en": row["descriptive_en"],
                "romanized_rank": ranks["romanized_en"],
                "descriptive_rank": ranks["descriptive_en"],
                "romanized_rr": 1.0 / ranks["romanized_en"],
                "descriptive_rr": 1.0 / ranks["descriptive_en"],
                "romanized_to_descriptive_rank_change": (
                    ranks["descriptive_en"] - ranks["romanized_en"]
                ),
                "term_positive_romanized_rank": term_ranks["romanized_en"],
                "term_positive_descriptive_rank": term_ranks["descriptive_en"],
                "term_positive_romanized_rr": 1.0 / term_ranks["romanized_en"],
                "term_positive_descriptive_rr": 1.0 / term_ranks["descriptive_en"],
                "review_status": row["review_status"],
                "equivalence_status": row["h2_equivalence_status"],
                "equivalence_note": H2_TERMS[term]["equivalence_note"],
            }
        )

    result_fields = [
        "audio_id", "target_term", "group_id", "positive_count", "term_positive_count",
        "romanized_en", "descriptive_en", "romanized_rank", "descriptive_rank",
        "romanized_rr", "descriptive_rr", "romanized_to_descriptive_rank_change",
        "term_positive_romanized_rank", "term_positive_descriptive_rank",
        "term_positive_romanized_rr", "term_positive_descriptive_rr",
        "review_status", "equivalence_status", "equivalence_note",
    ]
    write_csv(project_path(args.output), result_fields, result_rows)

    query_mrr = {
        "romanized_en": fmean(float(row["romanized_rr"]) for row in result_rows),
        "descriptive_en": fmean(float(row["descriptive_rr"]) for row in result_rows),
    }
    group_macro = {
        "romanized_en": group_macro_from_results(result_rows, group_indices, "romanized_rr"),
        "descriptive_en": group_macro_from_results(result_rows, group_indices, "descriptive_rr"),
    }
    group_differences = [
        fmean(float(result_rows[index]["romanized_rr"]) for index in indices)
        - fmean(float(result_rows[index]["descriptive_rr"]) for index in indices)
        for indices in group_indices.values()
    ]

    term_metrics: dict[str, Any] = {}
    for term in H2_TERMS:
        indices = [index for index, row in enumerate(result_rows) if row["target_term"] == term]
        term_group_ids = sorted({str(result_rows[index]["group_id"]) for index in indices})
        term_metrics[term] = {
            "assigned_query_count": len(indices),
            "metadata_group_count": len(term_group_ids),
            "label_positive_count": len(term_positives[term]),
            "query_mrr": {
                "romanized_en": fmean(float(result_rows[index]["romanized_rr"]) for index in indices),
                "descriptive_en": fmean(float(result_rows[index]["descriptive_rr"]) for index in indices),
            },
            "query_delta_romanized_minus_descriptive": fmean(
                float(result_rows[index]["romanized_rr"])
                - float(result_rows[index]["descriptive_rr"]) for index in indices
            ),
            "group_macro_mrr": {
                condition: fmean(
                    fmean(
                        float(result_rows[index][f"{condition.removesuffix('_en')}_rr"])
                        for index in group_indices[group_id]
                    )
                    for group_id in term_group_ids
                )
                for condition in H2_CONDITIONS
            },
            "term_presence_positive_mrr": {
                "romanized_en": fmean(
                    float(result_rows[index]["term_positive_romanized_rr"]) for index in indices
                ),
                "descriptive_en": fmean(
                    float(result_rows[index]["term_positive_descriptive_rr"]) for index in indices
                ),
            },
        }

    term_presence_mrr = {
        "romanized_en": fmean(float(row["term_positive_romanized_rr"]) for row in result_rows),
        "descriptive_en": fmean(float(row["term_positive_descriptive_rr"]) for row in result_rows),
    }
    primary_term_macro_mrr = {
        condition: fmean(term_metrics[term]["query_mrr"][condition] for term in H2_TERMS)
        for condition in H2_CONDITIONS
    }
    term_presence_term_macro_mrr = {
        condition: fmean(
            term_metrics[term]["term_presence_positive_mrr"][condition]
            for term in H2_TERMS
        )
        for condition in H2_CONDITIONS
    }
    rank_changes = [int(row["romanized_to_descriptive_rank_change"]) for row in result_rows]
    metrics = {
        "queries": len(result_rows), "candidates": len(audio_ids),
        "exact_unique_texts_per_condition": 3,
        "primary_proxy_answer_definition": (
            "H1-compatible metadata group: genre_major + genre + unordered instrument set"
        ),
        "primary_proxy_warning": (
            "H2 text mentions only one target instrument, so this 17-group answer definition "
            "is under-specified and provisional."
        ),
        "query_mrr": query_mrr,
        "query_delta_romanized_minus_descriptive": (
            query_mrr["romanized_en"] - query_mrr["descriptive_en"]
        ),
        "group_macro_mrr": group_macro,
        "group_macro_delta_romanized_minus_descriptive": (
            group_macro["romanized_en"] - group_macro["descriptive_en"]
        ),
        "group_bootstrap_romanized_minus_descriptive": paired_bootstrap(group_differences),
        "term_metrics": term_metrics,
        "primary_term_macro_mrr": primary_term_macro_mrr,
        "primary_term_macro_delta": (
            primary_term_macro_mrr["romanized_en"]
            - primary_term_macro_mrr["descriptive_en"]
        ),
        "supplementary_term_presence_answer_definition": (
            "All candidates whose validated label instrument set contains the target term"
        ),
        "supplementary_term_presence_mrr": term_presence_mrr,
        "supplementary_term_presence_delta": (
            term_presence_mrr["romanized_en"] - term_presence_mrr["descriptive_en"]
        ),
        "supplementary_term_presence_term_macro_mrr": term_presence_term_macro_mrr,
        "supplementary_term_presence_term_macro_delta": (
            term_presence_term_macro_mrr["romanized_en"]
            - term_presence_term_macro_mrr["descriptive_en"]
        ),
        "rank_change_counts": {
            "descriptive_better": sum(change < 0 for change in rank_changes),
            "same": sum(change == 0 for change in rank_changes),
            "descriptive_worse": sum(change > 0 for change in rank_changes),
            "max_absolute": max(map(abs, rank_changes)),
        },
        "description_audit": description_audit,
        "embedding_counts": {"audio_reused": 33, "romanized_en": 33, "descriptive_en": 33},
        "embedding_shape": [1, EXPECTED_DIM], "embedding_dtype": "float32",
        "nonfinite_values": 0,
    }
    (h2_root / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    write_csv(
        h2_root / "embedding_validation.csv",
        ["modality", "condition", "audio_id", "shape", "dtype", "nan_count", "inf_count", "l2_norm"],
        validation_rows,
    )
    similarity_root = h2_root / "similarity"
    similarity_root.mkdir(parents=True, exist_ok=True)
    for condition, matrix in scores.items():
        np.save(similarity_root / f"{condition}.npy", matrix.astype(np.float32))
    (similarity_root / "candidate_order.txt").write_text(
        "\n".join(audio_ids) + "\n", encoding="utf-8"
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="pilot_dataset.csv")
    subparsers = parser.add_subparsers(dest="command", required=True)
    h1 = subparsers.add_parser("analyze-h1")
    h1.add_argument("--h1-results", default="h1_retrieval_results.csv")
    h1.add_argument("--h1-artifact-root", default="artifacts/h1_additional_analysis")
    h2_prepare = subparsers.add_parser("prepare-h2")
    h2_prepare.add_argument("--h2-artifact-root", default="artifacts/h2_retrieval")
    h2_evaluate = subparsers.add_parser("evaluate-h2")
    h2_evaluate.add_argument("--h2-artifact-root", default="artifacts/h2_retrieval")
    h2_evaluate.add_argument(
        "--audio-embeddings", default="artifacts/h1_retrieval/embeddings/audio"
    )
    h2_evaluate.add_argument("--output", default="h2_retrieval_results.csv")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "analyze-h1":
        return analyze_h1(args)
    if args.command == "prepare-h2":
        return prepare_h2(args)
    if args.command == "evaluate-h2":
        return evaluate_h2(args)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
