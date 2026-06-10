from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.linear_model import PoissonRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ROOT_DIR = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT_DIR / "data" / "processed" / "training_matches_model_ready.csv"
ARTIFACTS_DIR = ROOT_DIR / "models" / "artifacts"
REPORTS_DIR = ROOT_DIR / "models" / "reports"

EXCLUDED_FEATURE_COLUMNS = {
    "match_date",
    "tournament",
    "team_a",
    "team_b",
    "goals_for",
    "goals_against",
    "result",
    "target",
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
    y = np.array([float(row["goals_for"]) for row in rows], dtype=float)
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


def build_model() -> Pipeline:
    return Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("model", PoissonRegressor(alpha=0.2, max_iter=1_000)),
        ]
    )


def evaluate_model(model: Any, x_test: np.ndarray, y_test: np.ndarray) -> dict[str, Any]:
    predictions = model.predict(x_test)
    predictions = np.clip(predictions, 0, None)
    return {
        "mae": mean_absolute_error(y_test, predictions),
        "rmse": mean_squared_error(y_test, predictions) ** 0.5,
        "actual_goals_mean": float(np.mean(y_test)),
        "predicted_goals_mean": float(np.mean(predictions)),
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

    model = build_model()
    model.fit(x_train, y_train)
    metrics = evaluate_model(model, x_test, y_test)

    summary = {
        "model_name": "poisson_regressor",
        "dataset": str(DATASET_PATH.relative_to(ROOT_DIR)),
        "feature_columns": feature_columns,
        "target": "goals_for",
        "train_rows": len(train_rows),
        "test_rows": len(test_rows),
        "train_date_min": train_rows[0]["match_date"],
        "train_date_max": train_rows[-1]["match_date"],
        "test_date_min": test_rows[0]["match_date"],
        "test_date_max": test_rows[-1]["match_date"],
        "metrics": metrics,
    }

    artifact = {
        "model": model,
        "model_name": "poisson_regressor",
        "feature_columns": feature_columns,
        "target": "goals_for",
    }
    joblib.dump(artifact, ARTIFACTS_DIR / "poisson_score_model.pkl")
    write_json(ARTIFACTS_DIR / "poisson_score_model_metadata.json", summary)
    write_json(REPORTS_DIR / "poisson_score_model_metrics.json", summary)

    print(
        "poisson_regressor: "
        f"mae={metrics['mae']:.4f} rmse={metrics['rmse']:.4f} "
        f"predicted_goals_mean={metrics['predicted_goals_mean']:.4f}"
    )
    print(f"saved={ARTIFACTS_DIR / 'poisson_score_model.pkl'}")


if __name__ == "__main__":
    main()
