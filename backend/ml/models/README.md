# This directory stores trained TFT model artifacts.
# It is populated by running:   python -m ml.train
#
# Expected files after training:
#   tft_carbon_best.ckpt       – model checkpoint
#   preprocessed_data.parquet  – daily-aggregated dataset
#   training_dataset.pkl       – serialised TimeSeriesDataSet
