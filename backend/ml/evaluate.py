#!/usr/bin/env python3
"""
Evaluate the trained TFT model on the held-out validation split.

Outputs aggregate forecasting metrics suitable for the paper's
forecast-evaluation table:
  - MAE
  - RMSE
  - MAPE
  - 80% prediction interval coverage (P10-P90)
  - model parameter count

Usage (run from backend/):

    python -m ml.evaluate
    python -m ml.evaluate --output-json ml/models/evaluation_metrics.json
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict

import numpy as np
import pandas as pd
from pytorch_forecasting import TemporalFusionTransformer

from .tft_model import BEST_MODEL_PATH, DATA_PATH, create_training_dataset


def compute_metrics() -> Dict[str, Any]:
    """Compute aggregate validation metrics from saved TFT artifacts."""
    if not os.path.exists(BEST_MODEL_PATH):
        raise FileNotFoundError(
            f"Model checkpoint not found: {BEST_MODEL_PATH}. Run `python -m ml.train` first."
        )
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(
            f"Preprocessed dataset not found: {DATA_PATH}. Run `python -m ml.train` first."
        )

    df = pd.read_parquet(DATA_PATH)
    _train_ds, _val_ds, _train_dl, val_dl = create_training_dataset(df)

    model = TemporalFusionTransformer.load_from_checkpoint(BEST_MODEL_PATH)
    model.eval()

    prediction = model.predict(val_dl, mode="quantiles", return_y=True)
    quantiles = prediction.output.detach().cpu().numpy()  # [N, H, Q]
    y_true = prediction.y[0].detach().cpu().numpy()       # [N, H]

    y_pred = quantiles[:, :, 3]  # median / p50
    p10 = quantiles[:, :, 1]
    p90 = quantiles[:, :, 5]

    errors = y_pred - y_true
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors ** 2)))

    nonzero_mask = np.abs(y_true) > 1e-8
    mape = float(np.mean(np.abs(errors[nonzero_mask] / y_true[nonzero_mask])) * 100.0)
    coverage_80 = float(np.mean((y_true >= p10) & (y_true <= p90)) * 100.0)

    return {
        "validation_points": int(y_true.size),
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "mape_percent": round(mape, 2),
        "coverage_80_percent": round(coverage_80, 2),
        "model_parameters_k": round(model.size() / 1e3, 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate the trained TFT carbon-forecasting model"
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default=None,
        help="Optional path to save the metrics JSON output.",
    )
    args = parser.parse_args()

    metrics = compute_metrics()
    print(json.dumps(metrics, indent=2))

    if args.output_json:
        output_path = os.path.abspath(args.output_json)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(metrics, fh, indent=2)
        print(f"\nSaved metrics to {output_path}")


if __name__ == "__main__":
    main()