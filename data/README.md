# Dataset Directory

This directory should contain the AI4I 2020 Predictive Maintenance Dataset.

## Download Instructions

1. Visit: https://archive.ics.uci.edu/ml/datasets/AI4I+2020+Predictive+Maintenance+Dataset
2. Download the dataset CSV file (ai4i2020.csv)
3. Place it in this directory

## File Expected
- **Filename**: ai4i2020.csv
- **Format**: CSV (comma-separated values)
- **Size**: ~1.5 MB
- **Rows**: ~10,000 samples
- **Columns**: ~14 features + target variable

The training pipeline in `src/train.py` will automatically load this file when executed.
