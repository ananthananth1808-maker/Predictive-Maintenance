# MaintenAI ML Module

This module contains the predictive maintenance machine learning pipeline for MaintenAI.

## Features
- Loads the AI4I 2020 dataset
- Removes leakage-prone columns such as failure-mode indicators
- Uses a leak-safe preprocessing pipeline with `ColumnTransformer`
- Trains an XGBoost classifier using class weighting for imbalance
- Saves the trained model and preprocessing object
- Produces evaluation plots and SHAP summary artifacts

## Training

```bash
python ml/src/train.py
```

## Outputs
- `ml/models/predictive_maintenance_model.pkl`
- `ml/models/preprocessor.pkl`
- `ml/models/evaluation_dashboard.png`
- `ml/models/shap_summary.png`
- `ml/models/training_summary.json`
