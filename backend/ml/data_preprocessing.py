"""
Data preprocessing pipeline for TFT carbon intensity forecasting.

Loads hourly CSV data from carbon-emission-region/{provider}/ folders,
aggregates to daily means, engineers calendar-based time features,
and prepares DataFrames suitable for pytorch-forecasting TimeSeriesDataSet.
"""

import os
import glob
import pandas as pd
import numpy as np
from typing import Optional

# Default path to the carbon-emission-region data directory
DEFAULT_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "carbon-emission-region",
)


def load_all_csvs(data_dir: str = DEFAULT_DATA_DIR) -> pd.DataFrame:
    """
    Load all CSV files from aws/, azure/, and gcp/ subdirectories.

    Returns a single DataFrame with columns:
        timestamp, provider, region, carbon_intensity, unit
    """
    frames = []
    for provider in ["aws", "azure", "gcp"]:
        provider_dir = os.path.join(data_dir, provider)
        if not os.path.isdir(provider_dir):
            print(f"  Warning: directory not found – {provider_dir}")
            continue
        for csv_path in sorted(glob.glob(os.path.join(provider_dir, "*.csv"))):
            try:
                df = pd.read_csv(csv_path, parse_dates=["timestamp"])
                frames.append(df)
            except Exception as e:
                print(f"  Warning: failed to read {csv_path}: {e}")

    if not frames:
        raise FileNotFoundError(f"No CSV files found under {data_dir}")

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values(
        ["provider", "region", "timestamp"]
    ).reset_index(drop=True)
    return combined


def aggregate_to_daily(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate hourly carbon_intensity to *daily mean* per provider+region.

    Returns DataFrame with columns:
        date, provider, region, carbon_intensity, group_id
    """
    df = df.copy()
    df["date"] = df["timestamp"].dt.date

    daily = (
        df.groupby(["provider", "region", "date"])["carbon_intensity"]
        .mean()
        .reset_index()
    )
    daily["date"] = pd.to_datetime(daily["date"])
    daily = daily.sort_values(
        ["provider", "region", "date"]
    ).reset_index(drop=True)

    # Combined group identifier  e.g. "aws_us-east-1"
    daily["group_id"] = daily["provider"] + "_" + daily["region"]
    return daily


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add calendar-based time features used as known covariates."""
    df = df.copy()
    df["day_of_week"] = df["date"].dt.dayofweek            # 0=Mon … 6=Sun
    df["day_of_month"] = df["date"].dt.day                  # 1–31
    df["month"] = df["date"].dt.month                       # 1–12
    df["week_of_year"] = (
        df["date"].dt.isocalendar().week.astype(int)
    )
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)  # 0/1
    df["quarter"] = df["date"].dt.quarter                    # 1–4
    return df


def add_time_index(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add a monotonically increasing *time_idx* (int) based on date.
    Required by pytorch-forecasting TimeSeriesDataSet.
    """
    df = df.copy()
    min_date = df["date"].min()
    df["time_idx"] = (df["date"] - min_date).dt.days
    return df


def remove_incomplete_groups(
    df: pd.DataFrame, min_days: int = 365
) -> pd.DataFrame:
    """Remove groups (provider+region) with fewer than *min_days* of data."""
    counts = df.groupby("group_id")["time_idx"].count()
    valid = counts[counts >= min_days].index
    return df[df["group_id"].isin(valid)].reset_index(drop=True)


def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Forward/backward fill missing carbon_intensity within each group."""
    df = df.copy()
    df["carbon_intensity"] = df.groupby("group_id")[
        "carbon_intensity"
    ].transform(lambda s: s.ffill().bfill())
    df = df.dropna(subset=["carbon_intensity"]).reset_index(drop=True)
    return df


def prepare_dataset(
    data_dir: str = DEFAULT_DATA_DIR,
    min_days: int = 365,
) -> pd.DataFrame:
    """
    Full preprocessing pipeline:
        load CSVs → aggregate daily → add features → clean.

    Returns a DataFrame ready for TFT training.
    """
    print("[Preprocessing] Loading CSV files …")
    raw = load_all_csvs(data_dir)
    print(
        f"  Loaded {len(raw):,} hourly records across "
        f"{raw['region'].nunique()} regions"
    )

    print("[Preprocessing] Aggregating to daily …")
    daily = aggregate_to_daily(raw)
    print(f"  {len(daily):,} daily records")

    print("[Preprocessing] Adding time features …")
    daily = add_time_features(daily)
    daily = add_time_index(daily)

    print("[Preprocessing] Handling missing values …")
    daily = handle_missing_values(daily)

    print("[Preprocessing] Removing incomplete groups …")
    daily = remove_incomplete_groups(daily, min_days=min_days)
    print(
        f"  {daily['group_id'].nunique()} groups retained, "
        f"{len(daily):,} total rows"
    )

    return daily
