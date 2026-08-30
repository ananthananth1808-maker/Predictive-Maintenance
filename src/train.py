"""
Model Training and Evaluation Module

Handles XGBoost model training, evaluation, visualization, and SHAP analysis
for the AI Predictive Maintenance System.

Functions:
- train_model: Train XGBoost classifier with class weight balancing
- evaluate_model: Calculate accuracy, precision, recall, F1, ROC-AUC
- plot_results: Generate confusion matrix, feature importance, ROC curve
- explain_with_shap: SHAP analysis for model interpretability
- save_model: Save trained model to disk
- main: Orchestrate the complete ML pipeline
"""

import os
import pickle
from typing import Tuple

import pandas as pd
import numpy as np
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, 
    roc_auc_score, confusion_matrix, roc_curve
)
import matplotlib.pyplot as plt
import seaborn as sns
import xgboost as xgb
import shap

# Import preprocessing functions
from src.preprocess import (
    load_dataset, inspect_data, clean_data, feature_engineering,
    prepare_train_test, save_preprocessing_objects
)


def train_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
    n_estimators: int = 100,
    max_depth: int = 5,
    learning_rate: float = 0.1,
    random_state: int = 42
) -> xgb.XGBClassifier:
    """
    Train an XGBoost binary classification model for machine failure prediction.
    
    XGBoost is chosen because:
    - Handles imbalanced data through scale_pos_weight
    - Provides built-in feature importance
    - Fast and robust to outliers
    - Good generalization performance
    
    Args:
        X_train (np.ndarray): Training features
        y_train (np.ndarray): Training target
        n_estimators (int): Number of boosting rounds (default: 100)
        max_depth (int): Maximum tree depth (default: 5, prevents overfitting)
        learning_rate (float): Learning rate/eta (default: 0.1)
        random_state (int): Random seed for reproducibility
    
    Returns:
        xgb.XGBClassifier: Trained XGBoost model
    """
    print("\n" + "="*80)
    print("MODEL TRAINING")
    print("="*80)
    
    # Calculate scale_pos_weight to handle class imbalance
    # scale_pos_weight = (count of negative class) / (count of positive class)
    # This penalizes misclassification of the minority class
    neg_count = np.sum(y_train == 0)
    pos_count = np.sum(y_train == 1)
    scale_pos_weight = neg_count / pos_count
    
    print(f"\n1. Class Distribution:")
    print(f"   Negative class (0): {neg_count} samples")
    print(f"   Positive class (1): {pos_count} samples")
    print(f"   Scale POS Weight: {scale_pos_weight:.2f}")
    
    # Initialize XGBoost classifier with optimized hyperparameters
    print(f"\n2. Initializing XGBoost Classifier...")
    model = xgb.XGBClassifier(
        objective='binary:logistic',  # Binary classification with logistic sigmoid
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
        scale_pos_weight=scale_pos_weight,  # Weight to handle imbalance
        tree_method='hist',  # Fast histogram-based learning
        subsample=0.8,  # Use 80% of samples for each tree (reduce overfitting)
        colsample_bytree=0.8,  # Use 80% of features for each tree
        random_state=random_state,
        use_label_encoder=False,  # Avoid warning
        eval_metric='logloss'  # Evaluation metric
    )
    
    print(f"   ✓ XGBoost Classifier initialized")
    print(f"   - Objective: binary:logistic")
    print(f"   - Estimators: {n_estimators}")
    print(f"   - Max Depth: {max_depth}")
    print(f"   - Learning Rate: {learning_rate}")
    
    # Train the model
    print(f"\n3. Training model on {len(y_train)} samples...")
    model.fit(
        X_train, y_train,
        verbose=False  # Set to True for detailed training output
    )
    
    print(f"   ✓ Model training complete!")
    print("="*80)
    
    return model


def evaluate_model(
    model: xgb.XGBClassifier,
    X_test: np.ndarray,
    y_test: np.ndarray
) -> dict:
    """
    Evaluate the trained model on the test set using multiple metrics.
    
    Metrics calculated:
    - Accuracy: Overall correctness
    - Precision: TP / (TP + FP) - % of predicted failures that are actual
    - Recall: TP / (TP + FN) - % of actual failures that are detected
    - F1-Score: Harmonic mean of Precision and Recall
    - ROC-AUC: Area under the ROC curve (0.5 = random, 1.0 = perfect)
    - Confusion Matrix: TP, FP, FN, TN breakdown
    
    Args:
        model (xgb.XGBClassifier): Trained XGBoost model
        X_test (np.ndarray): Test features
        y_test (np.ndarray): Test target
    
    Returns:
        dict: Dictionary containing all evaluation metrics
    """
    print("\n" + "="*80)
    print("MODEL EVALUATION")
    print("="*80)
    
    # Make predictions
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]  # Probability of failure class
    
    # Calculate metrics
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    roc_auc = roc_auc_score(y_test, y_pred_proba)
    cm = confusion_matrix(y_test, y_pred)
    
    print(f"\n1. Classification Metrics (Test Set, n={len(y_test)}):")
    print(f"   Accuracy:  {accuracy:.4f} ({accuracy*100:.2f}%)")
    print(f"   Precision: {precision:.4f} ({precision*100:.2f}%)")
    print(f"   Recall:    {recall:.4f} ({recall*100:.2f}%)")
    print(f"   F1-Score:  {f1:.4f}")
    print(f"   ROC-AUC:   {roc_auc:.4f}")
    
    print(f"\n2. Confusion Matrix:")
    print(f"   True Negatives (TN):  {cm[0, 0]}")
    print(f"   False Positives (FP): {cm[0, 1]}")
    print(f"   False Negatives (FN): {cm[1, 0]}")
    print(f"   True Positives (TP):  {cm[1, 1]}")
    
    # Additional metrics
    specificity = cm[0, 0] / (cm[0, 0] + cm[0, 1])  # True Negative Rate
    sensitivity = recall  # True Positive Rate
    print(f"\n3. Additional Metrics:")
    print(f"   Sensitivity (TPR/Recall): {sensitivity:.4f}")
    print(f"   Specificity (TNR):        {specificity:.4f}")
    print(f"   False Positive Rate:      {1-specificity:.4f}")
    
    print("\n" + "="*80)
    
    # Return all metrics as dictionary
    metrics = {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'roc_auc': roc_auc,
        'confusion_matrix': cm,
        'y_pred': y_pred,
        'y_pred_proba': y_pred_proba,
        'sensitivity': sensitivity,
        'specificity': specificity
    }
    
    return metrics


def plot_results(
    model: xgb.XGBClassifier,
    metrics: dict,
    y_test: np.ndarray,
    output_dir: str = "models"
) -> None:
    """
    Generate visualizations for model evaluation:
    1. Confusion Matrix (heatmap)
    2. Feature Importance (top 10 features)
    3. ROC Curve (TPR vs FPR)
    
    Args:
        model (xgb.XGBClassifier): Trained XGBoost model
        metrics (dict): Dictionary containing evaluation metrics
        y_test (np.ndarray): Test target values
        output_dir (str): Directory to save plots (default: models)
    """
    print("\n" + "="*80)
    print("GENERATING VISUALIZATIONS")
    print("="*80)
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Set style
    sns.set_style("whitegrid")
    plt.rcParams['figure.figsize'] = (15, 5)
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    # 1. Confusion Matrix
    print("\n1. Generating Confusion Matrix...")
    cm = metrics['confusion_matrix']
    sns.heatmap(
        cm, annot=True, fmt='d', cmap='Blues', ax=axes[0],
        cbar=False, annot_kws={'size': 14}
    )
    axes[0].set_title('Confusion Matrix', fontsize=14, fontweight='bold')
    axes[0].set_ylabel('True Label', fontsize=12)
    axes[0].set_xlabel('Predicted Label', fontsize=12)
    axes[0].set_xticklabels(['No Failure', 'Failure'])
    axes[0].set_yticklabels(['No Failure', 'Failure'])
    print("   ✓ Confusion Matrix plotted")
    
    # 2. Feature Importance (Top 10)
    print("\n2. Generating Feature Importance plot...")
    feature_importance = model.feature_importances_
    feature_names = [f"Feature_{i}" for i in range(len(feature_importance))]
    
    # Get top 10 features
    top_indices = np.argsort(feature_importance)[-10:][::-1]
    top_features = [feature_names[i] for i in top_indices]
    top_importance = feature_importance[top_indices]
    
    axes[1].barh(top_features, top_importance, color='steelblue')
    axes[1].set_title('Top 10 Feature Importance', fontsize=14, fontweight='bold')
    axes[1].set_xlabel('Importance Score', fontsize=12)
    axes[1].invert_yaxis()
    print(f"   ✓ Feature Importance plotted (Top 10 shown)")
    
    # 3. ROC Curve
    print("\n3. Generating ROC Curve...")
    fpr, tpr, thresholds = roc_curve(y_test, metrics['y_pred_proba'])
    roc_auc = metrics['roc_auc']
    
    axes[2].plot(fpr, tpr, color='darkblue', lw=2, 
                 label=f'ROC Curve (AUC = {roc_auc:.4f})')
    axes[2].plot([0, 1], [0, 1], color='red', lw=2, linestyle='--', 
                 label='Random Classifier')
    axes[2].set_xlim([0.0, 1.0])
    axes[2].set_ylim([0.0, 1.05])
    axes[2].set_xlabel('False Positive Rate', fontsize=12)
    axes[2].set_ylabel('True Positive Rate', fontsize=12)
    axes[2].set_title('ROC Curve', fontsize=14, fontweight='bold')
    axes[2].legend(loc="lower right", fontsize=10)
    axes[2].grid(True, alpha=0.3)
    print("   ✓ ROC Curve plotted")
    
    plt.tight_layout()
    
    # Save the figure
    plot_path = os.path.join(output_dir, 'evaluation_plots.png')
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    print(f"\n✓ Plots saved to: {plot_path}")
    print("="*80)


def explain_with_shap(
    model: xgb.XGBClassifier,
    X_test: np.ndarray,
    X_train: np.ndarray = None,
    output_dir: str = "models"
) -> shap.Explainer:
    """
    Generate SHAP explanations for model predictions.
    
    SHAP (SHapley Additive exPlanations) provides:
    - Force plots: Individual prediction explanations
    - Summary plots: Global feature impact
    - Waterfall plots: Step-by-step prediction breakdowns
    
    Args:
        model (xgb.XGBClassifier): Trained XGBoost model
        X_test (np.ndarray): Test features for explanation
        X_train (np.ndarray): Training data for background (optional)
        output_dir (str): Directory to save SHAP plots
    
    Returns:
        shap.Explainer: Fitted SHAP explainer object
    """
    print("\n" + "="*80)
    print("SHAP MODEL EXPLAINABILITY ANALYSIS")
    print("="*80)
    
    os.makedirs(output_dir, exist_ok=True)
    
    print("\n1. Initializing SHAP Explainer...")
    # Use training data as background (can also sample for speed)
    if X_train is not None:
        # Use a sample of training data as background (for speed)
        background = shap.sample(X_train, min(100, len(X_train)))
    else:
        background = X_test
    
    explainer = shap.TreeExplainer(model)
    print("   ✓ SHAP TreeExplainer initialized")
    
    print("\n2. Computing SHAP values for test set...")
    shap_values = explainer.shap_values(X_test)
    print("   ✓ SHAP values computed")
    
    # Handle binary classification (SHAP returns list of arrays)
    if isinstance(shap_values, list):
        shap_values_class1 = shap_values[1]  # Failure class
    else:
        shap_values_class1 = shap_values
    
    # Generate visualizations
    print("\n3. Generating SHAP visualizations...")
    
    # Summary plot (bar)
    print("   - Generating SHAP Summary (mean absolute) plot...")
    plt.figure(figsize=(10, 6))
    shap.summary_plot(shap_values_class1, X_test, show=False, plot_type='bar')
    plt.tight_layout()
    summary_path = os.path.join(output_dir, 'shap_summary_plot.png')
    plt.savefig(summary_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"      ✓ Saved to: {summary_path}")
    
    # Summary plot (scatter)
    print("   - Generating SHAP Summary (scatter) plot...")
    plt.figure(figsize=(10, 8))
    shap.summary_plot(shap_values_class1, X_test, show=False)
    plt.tight_layout()
    scatter_path = os.path.join(output_dir, 'shap_scatter_plot.png')
    plt.savefig(scatter_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"      ✓ Saved to: {scatter_path}")
    
    # Force plot (sample prediction)
    print("   - Generating SHAP Force plot for first prediction...")
    try:
        force_plot = shap.force_plot(
            explainer.expected_value,
            shap_values_class1[0],
            X_test[0],
            show=False
        )
        force_path = os.path.join(output_dir, 'shap_force_plot.html')
        shap.save_html(force_path, force_plot)
        print(f"      ✓ Saved to: {force_path}")
    except Exception as e:
        print(f"      ⚠ Force plot skipped: {str(e)}")
    
    print("\n✓ SHAP analysis complete!")
    print("="*80)
    
    return explainer


def save_model(
    model: xgb.XGBClassifier,
    output_path: str = "models/predictive_maintenance_model.pkl"
) -> None:
    """
    Save the trained XGBoost model to disk using joblib/pickle.
    
    Args:
        model (xgb.XGBClassifier): Trained model to save
        output_path (str): Path to save the model (default: models/predictive_maintenance_model.pkl)
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    print(f"\nSaving model to: {output_path}")
    with open(output_path, 'wb') as f:
        pickle.dump(model, f)
    print(f"✓ Model saved successfully!")


def main():
    """
    Main pipeline orchestration function.
    
    Steps:
    1. Load dataset from CSV
    2. Inspect data (statistics, distributions)
    3. Clean data (remove NaN, duplicates, irrelevant columns)
    4. Feature engineering (encoding, scaling)
    5. Train/test split with SMOTE imbalance handling
    6. Train XGBoost model
    7. Evaluate model (metrics and visualizations)
    8. SHAP analysis
    9. Save model and preprocessing objects
    """
    print("\n" + "="*80)
    print("AI PREDICTIVE MAINTENANCE SYSTEM - PHASE 1")
    print("Machine Failure Prediction ML Pipeline")
    print("="*80)
    
    # Step 1: Load Dataset
    print("\n[STEP 1/9] Loading dataset...")
    df = load_dataset("data/ai4i2020.csv")
    
    # Step 2: Inspect Data
    print("\n[STEP 2/9] Inspecting data...")
    inspect_data(df)
    
    # Step 3: Clean Data
    print("\n[STEP 3/9] Cleaning data...")
    df_clean = clean_data(df)
    
    # Step 4: Feature Engineering
    print("\n[STEP 4/9] Performing feature engineering...")
    df_engineered, preprocessing_objects = feature_engineering(df_clean)
    
    # Step 5: Train/Test Split & Imbalance Handling
    print("\n[STEP 5/9] Preparing train/test split...")
    X_train, X_test, y_train, y_test = prepare_train_test(df_engineered)
    
    # Step 6: Train Model
    print("\n[STEP 6/9] Training XGBoost model...")
    model = train_model(X_train, y_train)
    
    # Step 7: Evaluate Model
    print("\n[STEP 7/9] Evaluating model...")
    metrics = evaluate_model(model, X_test, y_test)
    
    # Step 8: Visualizations
    print("\n[STEP 8/9] Generating plots and visualizations...")
    plot_results(model, metrics, y_test)
    
    # Step 9: SHAP Analysis
    print("\n[STEP 9/9] SHAP explainability analysis...")
    explain_with_shap(model, X_test, X_train)
    
    # Save Model & Preprocessing Objects
    print("\n[SAVING] Saving trained model and preprocessing objects...")
    save_model(model)
    save_preprocessing_objects(preprocessing_objects)
    
    # Final Summary
    print("\n" + "="*80)
    print("✓ PIPELINE COMPLETE!")
    print("="*80)
    print("\nDeliverables:")
    print(f"  - Trained Model: models/predictive_maintenance_model.pkl")
    print(f"  - Preprocessing Objects: models/preprocessing_objects.pkl")
    print(f"  - Evaluation Plots: models/evaluation_plots.png")
    print(f"  - SHAP Plots: models/shap_*.png/.html")
    print("\nKey Metrics:")
    print(f"  - Accuracy:  {metrics['accuracy']:.4f}")
    print(f"  - Precision: {metrics['precision']:.4f}")
    print(f"  - Recall:    {metrics['recall']:.4f}")
    print(f"  - F1-Score:  {metrics['f1']:.4f}")
    print(f"  - ROC-AUC:   {metrics['roc_auc']:.4f}")
    print("\nNext Steps:")
    print("  1. Review the generated plots and SHAP analysis")
    print("  2. Fine-tune hyperparameters if needed")
    print("  3. Use saved model for inference on new data")
    print("="*80)


if __name__ == "__main__":
    main()
