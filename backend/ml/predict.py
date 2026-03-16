"""
Prediction service for TFT carbon intensity forecasting.

Exposes a *singleton* ``CarbonForecaster`` that:
  1. Loads the trained model + artefacts once (lazy, on first call).
  2. Pre-computes 7-day forecasts for every region at init time.
  3. Serves cached forecasts via simple lookup functions.

Gracefully degrades when the model has not been trained yet.
"""

import os
import pickle
import warnings
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import torch
import yaml

from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet

from .tft_model import (
    BEST_MODEL_PATH,
    DATA_PATH,
    DATASET_PATH,
    ENCODER_LENGTH,
    PREDICTION_LENGTH,
)

warnings.filterwarnings("ignore", category=UserWarning)

# ── Region-name look-up tables ──────────────────────────────────────────────
_region_display_to_code: Dict[str, str] = {}


def _load_region_mappings() -> None:
    """
    Build a mapping  ``{provider}_{display_name}`` → ``{provider}_{code}``
    from *providers_regions.yaml*.
    """
    global _region_display_to_code

    yaml_path = os.path.join(
        os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ),
        "carbon-emission-region",
        "providers_regions.yaml",
    )
    if not os.path.exists(yaml_path):
        return

    with open(yaml_path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if "cloud_regions" in data:
        data = data["cloud_regions"]

    for provider, regions in data.items():
        if not isinstance(regions, dict):
            continue
        for code, display_name in regions.items():
            if isinstance(display_name, str):
                key_display = f"{provider.lower()}_{display_name}"
                key_code = f"{provider.lower()}_{code}"
                _region_display_to_code[key_display] = key_code
                _region_display_to_code[key_code] = key_code


# ── Singleton forecaster ────────────────────────────────────────────────────
class CarbonForecaster:
    """Lazy-loaded singleton that serves cached 7-day carbon forecasts."""

    _instance: Optional["CarbonForecaster"] = None

    def __new__(cls) -> "CarbonForecaster":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False  # type: ignore[attr-defined]
        return cls._instance

    # ── initialisation ───────────────────────────────────────────────────
    def initialize(self) -> None:
        """Load model, data, and pre-compute forecasts (called once)."""
        if self._initialized:
            return

        if not os.path.exists(BEST_MODEL_PATH):
            raise FileNotFoundError(
                f"No trained model found at {BEST_MODEL_PATH}. "
                "Run `python -m ml.train` first."
            )

        print("[Forecaster] Loading TFT model …")
        self.model = TemporalFusionTransformer.load_from_checkpoint(
            BEST_MODEL_PATH
        )
        self.model.eval()

        print("[Forecaster] Loading preprocessed data …")
        self.df = pd.read_parquet(DATA_PATH)
        self.df["date"] = pd.to_datetime(self.df["date"])

        print("[Forecaster] Loading training dataset …")
        with open(DATASET_PATH, "rb") as fh:
            self.training_dataset: TimeSeriesDataSet = pickle.load(fh)

        _load_region_mappings()

        self.available_groups: set = set(self.df["group_id"].unique())

        # Pre-compute forecasts for every region
        print("[Forecaster] Generating forecasts for all regions …")
        self._cache: Dict[str, Dict] = {}
        for gid in sorted(self.available_groups):
            try:
                self._cache[gid] = self._generate_forecast(gid)
            except Exception as exc:
                print(f"  ⚠  forecast failed for {gid}: {exc}")

        print(f"[Forecaster] Ready – {len(self._cache)} region forecasts cached")
        self._initialized = True

    # ── group-id resolution ──────────────────────────────────────────────
    def _resolve_group_id(
        self, provider: str, region: str
    ) -> Optional[str]:
        """Map (provider, region) → group_id present in the data."""
        prov = provider.lower()

        direct = f"{prov}_{region}"
        if direct in self.available_groups:
            return direct

        mapped = _region_display_to_code.get(direct)
        if mapped and mapped in self.available_groups:
            return mapped

        # Case-insensitive fallback
        for gid in self.available_groups:
            if gid.lower() == direct.lower():
                return gid

        return None

    # ── single-group forecast ────────────────────────────────────────────
    def _generate_forecast(self, group_id: str) -> Dict:
        """Run TFT inference for *group_id* and return structured result."""
        group_data = self.df[self.df["group_id"] == group_id].copy()
        if len(group_data) < ENCODER_LENGTH:
            return {"error": "Insufficient historical data"}

        max_time_idx = int(group_data["time_idx"].max())
        last_date = group_data["date"].max()
        provider = group_data["provider"].iloc[0]
        region = group_data["region"].iloc[0]

        # ── future rows (targets set to 0 – the model predicts them) ────
        future_rows = []
        for i in range(1, PREDICTION_LENGTH + 1):
            fd = last_date + pd.Timedelta(days=i)
            future_rows.append(
                {
                    "date": fd,
                    "provider": provider,
                    "region": region,
                    "group_id": group_id,
                    "carbon_intensity": 0.0,
                    "time_idx": max_time_idx + i,
                    "day_of_week": fd.dayofweek,
                    "day_of_month": fd.day,
                    "month": fd.month,
                    "week_of_year": int(fd.isocalendar()[1]),
                    "is_weekend": int(fd.dayofweek >= 5),
                    "quarter": fd.quarter,
                }
            )

        future_df = pd.DataFrame(future_rows)

        # Combine last chunk of real data + future placeholder
        encoder_data = group_data.tail(ENCODER_LENGTH + PREDICTION_LENGTH)
        combined = pd.concat([encoder_data, future_df], ignore_index=True)

        # Ensure dtypes match training
        int_cols = [
            "day_of_week", "day_of_month", "month",
            "week_of_year", "is_weekend", "quarter", "time_idx",
        ]
        for col in int_cols:
            combined[col] = combined[col].astype(int)
        combined["carbon_intensity"] = combined["carbon_intensity"].astype(
            float
        )

        # Build prediction dataset from saved training dataset
        pred_ds = TimeSeriesDataSet.from_dataset(
            self.training_dataset,
            combined,
            predict=True,
            stop_randomization=True,
        )
        pred_dl = pred_ds.to_dataloader(
            train=False, batch_size=1, num_workers=0
        )

        # Inference
        with torch.no_grad():
            raw = self.model.predict(
                pred_dl, mode="quantiles", return_x=False
            )

        # raw shape: (n_samples, PREDICTION_LENGTH, n_quantiles)
        # quantiles: [0.02, 0.1, 0.25, 0.5, 0.75, 0.9, 0.98]
        preds = raw[0].cpu().numpy()  # (PREDICTION_LENGTH, 7)

        # Historical context (last 30 days)
        history = group_data.tail(30)[["date", "carbon_intensity"]].copy()
        history["date"] = history["date"].dt.strftime("%Y-%m-%d")

        forecast_points = []
        for i in range(PREDICTION_LENGTH):
            fd = (last_date + pd.Timedelta(days=i + 1)).strftime("%Y-%m-%d")
            forecast_points.append(
                {
                    "date": fd,
                    "predicted": round(float(preds[i, 3]), 2),   # median
                    "lower_80": round(float(preds[i, 1]), 2),    # p10
                    "upper_80": round(float(preds[i, 5]), 2),    # p90
                    "lower_50": round(float(preds[i, 2]), 2),    # p25
                    "upper_50": round(float(preds[i, 4]), 2),    # p75
                }
            )

        # Trend assessment
        predicted_vals = [p["predicted"] for p in forecast_points]
        recent_avg = float(group_data.tail(7)["carbon_intensity"].mean())
        forecast_avg = float(np.mean(predicted_vals))

        if forecast_avg < recent_avg * 0.98:
            trend = "decreasing"
        elif forecast_avg > recent_avg * 1.02:
            trend = "increasing"
        else:
            trend = "stable"

        return {
            "provider": provider,
            "region": region,
            "group_id": group_id,
            "history": history.to_dict(orient="records"),
            "forecast": forecast_points,
            "summary": {
                "forecast_avg_gCO2": round(forecast_avg, 2),
                "recent_avg_gCO2": round(recent_avg, 2),
                "trend": trend,
                "prediction_days": PREDICTION_LENGTH,
                "unit": "gCO2eq/kWh",
            },
        }

    # ── public API ───────────────────────────────────────────────────────
    def get_forecast(
        self, provider: str, region: str
    ) -> Optional[Dict]:
        """Full forecast (history + predicted points + summary)."""
        if not self._initialized:
            try:
                self.initialize()
            except FileNotFoundError:
                return None

        gid = self._resolve_group_id(provider, region)
        if gid is None:
            return None
        return self._cache.get(gid)

    def get_forecast_summary(
        self, provider: str, region: str
    ) -> Optional[Dict]:
        """Lightweight dict suitable for embedding in pricing responses."""
        fc = self.get_forecast(provider, region)
        if fc is None or "error" in fc:
            return None
        return fc.get("summary")

    def get_all_forecasts(self) -> Dict[str, Dict]:
        if not self._initialized:
            try:
                self.initialize()
            except FileNotFoundError:
                return {}
        return self._cache


# ── module-level convenience functions ───────────────────────────────────────
_forecaster: Optional[CarbonForecaster] = None


def get_forecaster() -> CarbonForecaster:
    global _forecaster
    if _forecaster is None:
        _forecaster = CarbonForecaster()
    return _forecaster


def get_carbon_forecast(
    provider: str, region: str
) -> Optional[Dict]:
    """Return full forecast for a provider + region (or *None*)."""
    return get_forecaster().get_forecast(provider, region)


def get_carbon_forecast_summary(
    provider: str, region: str
) -> Optional[Dict]:
    """Return lightweight summary for a provider + region (or *None*)."""
    return get_forecaster().get_forecast_summary(provider, region)
