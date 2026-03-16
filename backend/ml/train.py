#!/usr/bin/env python3
"""
Training script for the TFT carbon-intensity forecasting model.

Usage (run from the ``backend/`` directory):

    python -m ml.train                          # defaults
    python -m ml.train --epochs 30 --gpu        # 30 epochs on GPU
    python -m ml.train --data-dir /path/to/carbon-emission-region

Artifacts are saved under ``backend/ml/models/``.
"""

import argparse
import os
import sys

# Ensure the backend package root is on sys.path so relative imports work
# when the script is executed as ``python -m ml.train`` from backend/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train TFT carbon-intensity forecasting model"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Path to the carbon-emission-region directory "
        "(default: auto-detected relative to repo root)",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=50,
        help="Maximum number of training epochs (default: 50)",
    )
    parser.add_argument(
        "--gpu",
        action="store_true",
        help="Use GPU for training if available",
    )
    args = parser.parse_args()

    from ml.data_preprocessing import prepare_dataset
    from ml.tft_model import train_model

    kwargs = {}
    if args.data_dir:
        kwargs["data_dir"] = args.data_dir

    df = prepare_dataset(**kwargs)
    ckpt = train_model(df, max_epochs=args.epochs, gpus=1 if args.gpu else 0)
    print(f"\n✓ Training complete. Model checkpoint → {ckpt}")


if __name__ == "__main__":
    main()
