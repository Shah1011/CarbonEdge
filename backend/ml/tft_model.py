"""
Temporal Fusion Transformer – build, train, and save.

Uses pytorch-forecasting's TFT implementation with:
  • 30-day encoder window
  • 7-day prediction horizon
  • Quantile loss  (0.02, 0.1, 0.25, 0.5, 0.75, 0.9, 0.98)
  • Group-level normalisation (softplus)
"""

import os
import pickle
import shutil
import warnings
from typing import Tuple

import pandas as pd
import numpy as np
import torch
import lightning.pytorch as pl
from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet
from pytorch_forecasting.data import GroupNormalizer
from pytorch_forecasting.metrics import QuantileLoss
from lightning.pytorch.callbacks import EarlyStopping, LearningRateMonitor

warnings.filterwarnings("ignore", category=UserWarning)

# ── hyper-parameters ─────────────────────────────────────────────────────────
ENCODER_LENGTH = 30          # days of look-back
PREDICTION_LENGTH = 7        # days to forecast
BATCH_SIZE = 64
MAX_EPOCHS = 50
LEARNING_RATE = 1e-3
HIDDEN_SIZE = 32
ATTENTION_HEAD_SIZE = 2
DROPOUT = 0.1
HIDDEN_CONTINUOUS_SIZE = 16
GRADIENT_CLIP_VAL = 0.1

# ── paths ────────────────────────────────────────────────────────────────────
MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
BEST_MODEL_PATH = os.path.join(MODEL_DIR, "tft_carbon_best.ckpt")
DATA_PATH = os.path.join(MODEL_DIR, "preprocessed_data.parquet")
DATASET_PATH = os.path.join(MODEL_DIR, "training_dataset.pkl")


# ── dataset creation ─────────────────────────────────────────────────────────
def create_training_dataset(
    df: pd.DataFrame,
    encoder_length: int = ENCODER_LENGTH,
    prediction_length: int = PREDICTION_LENGTH,
    training_cutoff_frac: float = 0.85,
) -> Tuple[
    TimeSeriesDataSet,
    TimeSeriesDataSet,
    torch.utils.data.DataLoader,
    torch.utils.data.DataLoader,
]:
    """Return (train_ds, val_ds, train_dl, val_dl)."""

    max_idx = df["time_idx"].max()
    cutoff = int(max_idx * training_cutoff_frac)

    training = TimeSeriesDataSet(
        df[df["time_idx"] <= cutoff],
        time_idx="time_idx",
        target="carbon_intensity",
        group_ids=["group_id"],
        min_encoder_length=encoder_length // 2,
        max_encoder_length=encoder_length,
        min_prediction_length=1,
        max_prediction_length=prediction_length,
        static_categoricals=["group_id"],
        time_varying_known_reals=[
            "time_idx",
            "day_of_week",
            "day_of_month",
            "month",
            "week_of_year",
            "is_weekend",
            "quarter",
        ],
        time_varying_unknown_reals=["carbon_intensity"],
        target_normalizer=GroupNormalizer(
            groups=["group_id"],
            transformation="softplus",
        ),
        add_relative_time_idx=True,
        add_target_scales=True,
        add_encoder_length=True,
        allow_missing_timesteps=True,
    )

    validation = TimeSeriesDataSet.from_dataset(
        training, df, predict=True, stop_randomization=True
    )

    train_dl = training.to_dataloader(
        train=True, batch_size=BATCH_SIZE, num_workers=0
    )
    val_dl = validation.to_dataloader(
        train=False, batch_size=BATCH_SIZE * 2, num_workers=0
    )

    return training, validation, train_dl, val_dl


# ── model factory ────────────────────────────────────────────────────────────
def build_tft(
    training_dataset: TimeSeriesDataSet,
) -> TemporalFusionTransformer:
    """Construct a TFT from the training dataset metadata."""
    return TemporalFusionTransformer.from_dataset(
        training_dataset,
        learning_rate=LEARNING_RATE,
        hidden_size=HIDDEN_SIZE,
        attention_head_size=ATTENTION_HEAD_SIZE,
        dropout=DROPOUT,
        hidden_continuous_size=HIDDEN_CONTINUOUS_SIZE,
        output_size=7,  # one per quantile
        loss=QuantileLoss(
            quantiles=[0.02, 0.1, 0.25, 0.5, 0.75, 0.9, 0.98]
        ),
        log_interval=10,
        reduce_on_plateau_patience=4,
    )


# ── training loop ────────────────────────────────────────────────────────────
def train_model(
    df: pd.DataFrame,
    max_epochs: int = MAX_EPOCHS,
    gpus: int = 0,
) -> str:
    """
    Train the TFT model and persist all artifacts:
      • model checkpoint  →  models/tft_carbon_best.ckpt
      • preprocessed data →  models/preprocessed_data.parquet
      • training dataset  →  models/training_dataset.pkl

    Returns the path to the saved checkpoint.
    """
    os.makedirs(MODEL_DIR, exist_ok=True)

    training, _val, train_dl, val_dl = create_training_dataset(df)
    model = build_tft(training)
    print(f"[Training] Model size: {model.size()/1e3:.1f}K parameters")

    early_stop = EarlyStopping(
        monitor="val_loss",
        min_delta=1e-4,
        patience=5,
        verbose=True,
        mode="min",
    )
    lr_monitor = LearningRateMonitor()

    use_gpu = gpus > 0 and torch.cuda.is_available()
    trainer = pl.Trainer(
        max_epochs=max_epochs,
        accelerator="gpu" if use_gpu else "cpu",
        devices=gpus if use_gpu else "auto",
        gradient_clip_val=GRADIENT_CLIP_VAL,
        callbacks=[early_stop, lr_monitor],
        enable_progress_bar=True,
    )

    trainer.fit(model, train_dataloaders=train_dl, val_dataloaders=val_dl)

    # ── persist model ────────────────────────────────────────────────────
    best = trainer.checkpoint_callback.best_model_path
    if best:
        shutil.copy2(best, BEST_MODEL_PATH)
    else:
        trainer.save_checkpoint(BEST_MODEL_PATH)
    print(f"[Training] Model checkpoint → {BEST_MODEL_PATH}")

    # ── persist data ─────────────────────────────────────────────────────
    df.to_parquet(DATA_PATH, index=False)
    print(f"[Training] Preprocessed data → {DATA_PATH}")

    with open(DATASET_PATH, "wb") as fh:
        pickle.dump(training, fh)
    print(f"[Training] Training dataset  → {DATASET_PATH}")

    return BEST_MODEL_PATH
