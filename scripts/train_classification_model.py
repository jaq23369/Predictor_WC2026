from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ROOT_DIR = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT_DIR / "data" / "processed" / "final_training_dataset.csv"
ARTIFACTS_DIR = ROOT_DIR / "models" / "artifacts"
REPORTS_DIR = ROOT_DIR / "models" / "reports"

EXCLUDED_FEATURE_COLUMNS = {"match_date", "tournament", "team_a", "team_b", "result", "target"}

TARGET_LABELS = {
    0: "loss",
    1: "draw",
    2: "win",
}


def load_dataset() -> tuple[list[dict[str, str]], np.ndarray, np.ndarray, list[str]]:
    with DATASET_PATH.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    feature_columns = [
        column for column in fieldnames if column not in EXCLUDED_FEATURE_COLUMNS
    ]

    x = np.array(
        [[float(row[column]) for column in feature_columns] for row in rows],
        dtype=float,
    )
    y = np.array([int(row["target"]) for row in rows], dtype=int)
    return rows, x, y, feature_columns


def chronological_split(
    rows: list[dict[str, str]],
    x: np.ndarray,
    y: np.ndarray,
    test_ratio: float = 0.2,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[dict[str, str]], list[dict[str, str]]]:
    split_index = int(len(rows) * (1 - test_ratio))
    return (
        x[:split_index],
        x[split_index:],
        y[:split_index],
        y[split_index:],
        rows[:split_index],
        rows[split_index:],
    )


def build_models() -> dict[str, Any]:
    return {
        "logistic_regression": Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        class_weight="balanced",
                        max_iter=2_000,
                        random_state=42,
                    ),
                ),
            ]
        ),
        "random_forest": RandomForestClassifier(
            class_weight="balanced_subsample",
            max_depth=18,
            min_samples_leaf=8,
            n_estimators=300,
            n_jobs=-1,
            random_state=42,
        ),
        "extra_trees": ExtraTreesClassifier(
            class_weight="balanced",
            max_depth=22,
            min_samples_leaf=6,
            n_estimators=500,
            n_jobs=-1,
            random_state=42,
        ),
        "hist_gradient_boosting": HistGradientBoostingClassifier(
            class_weight="balanced",
            l2_regularization=0.05,
            learning_rate=0.06,
            max_iter=260,
            max_leaf_nodes=24,
            min_samples_leaf=30,
            random_state=42,
        ),
    }


def evaluate_model(model: Any, x_test: np.ndarray, y_test: np.ndarray) -> dict[str, Any]:
    predictions = model.predict(x_test)
    labels = sorted(TARGET_LABELS)
    return {
        "accuracy": accuracy_score(y_test, predictions),
        "precision_macro": precision_score(
            y_test, predictions, average="macro", zero_division=0
        ),
        "recall_macro": recall_score(
            y_test, predictions, average="macro", zero_division=0
        ),
        "f1_macro": f1_score(y_test, predictions, average="macro", zero_division=0),
        "confusion_matrix": confusion_matrix(y_test, predictions, labels=labels).tolist(),
        "classification_report": classification_report(
            y_test,
            predictions,
            labels=labels,
            target_names=[TARGET_LABELS[label] for label in labels],
            zero_division=0,
            output_dict=True,
        ),
    }


def model_summary(
    name: str,
    metrics: dict[str, Any],
    train_rows: list[dict[str, str]],
    test_rows: list[dict[str, str]],
    feature_columns: list[str],
) -> dict[str, Any]:
    return {
        "model_name": name,
        "dataset": str(DATASET_PATH.relative_to(ROOT_DIR)),
        "feature_columns": feature_columns,
        "target_labels": TARGET_LABELS,
        "train_rows": len(train_rows),
        "test_rows": len(test_rows),
        "train_date_min": train_rows[0]["match_date"],
        "train_date_max": train_rows[-1]["match_date"],
        "test_date_min": test_rows[0]["match_date"],
        "test_date_max": test_rows[-1]["match_date"],
        "metrics": metrics,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)
        file.write("\n")


def main() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    rows, x, y, feature_columns = load_dataset()
    x_train, x_test, y_train, y_test, train_rows, test_rows = chronological_split(rows, x, y)

    model_results: dict[str, dict[str, Any]] = {}
    trained_models: dict[str, Any] = {}

    for name, model in build_models().items():
        model.fit(x_train, y_train)
        metrics = evaluate_model(model, x_test, y_test)
        trained_models[name] = model
        model_results[name] = model_summary(
            name, metrics, train_rows, test_rows, feature_columns
        )
        write_json(REPORTS_DIR / f"{name}_metrics.json", model_results[name])
        print(
            f"{name}: accuracy={metrics['accuracy']:.4f} "
            f"f1_macro={metrics['f1_macro']:.4f}"
        )

    best_name = max(
        model_results,
        key=lambda name: model_results[name]["metrics"]["f1_macro"],
    )
    best_model = trained_models[best_name]
    best_summary = model_results[best_name]

    artifact = {
        "model": best_model,
        "model_name": best_name,
        "feature_columns": feature_columns,
        "target_labels": TARGET_LABELS,
    }
    joblib.dump(artifact, ARTIFACTS_DIR / "classification_model.pkl")
    write_json(ARTIFACTS_DIR / "classification_model_metadata.json", best_summary)
    write_json(REPORTS_DIR / "classification_model_comparison.json", model_results)

    print(f"best_model={best_name}")
    print(f"saved={ARTIFACTS_DIR / 'classification_model.pkl'}")


if __name__ == "__main__":
    main()
