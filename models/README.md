# Models Directory

This directory will contain the trained machine learning models and preprocessing objects.

## Expected Files (Generated After Training)

### After running `python src/train.py`:

1. **predictive_maintenance_model.pkl**
   - Trained XGBoost classifier
   - Used for making predictions on new data
   - Size: ~200-500 KB

2. **preprocessing_objects.pkl**
   - Scaling and encoding transformers
   - Required to preprocess new data before inference
   - Includes: StandardScaler, LabelEncoders

3. **evaluation_plots.png**
   - Confusion matrix, feature importance, ROC curve
   - Model performance visualization

4. **shap_summary_plot.png**
   - Mean absolute feature impact plot
   - Shows average feature importance via SHAP

5. **shap_scatter_plot.png**
   - Feature value vs SHAP value scatter plot
   - Shows feature impact patterns

6. **shap_force_plot.html**
   - Interactive force plot for a single prediction
   - Shows how each feature contributes to a prediction

## Usage

To load the saved model for inference:

```python
import pickle
import pandas as pd

# Load model and preprocessing objects
model = pickle.load(open('models/predictive_maintenance_model.pkl', 'rb'))
preprocessing = pickle.load(open('models/preprocessing_objects.pkl', 'rb'))

# Preprocess new data
X_new = df_new.copy()
if 'scaler' in preprocessing:
    numerical_cols = ['col1', 'col2', ...]
    X_new[numerical_cols] = preprocessing['scaler'].transform(X_new[numerical_cols])

# Make predictions
predictions = model.predict(X_new)
probabilities = model.predict_proba(X_new)
```
