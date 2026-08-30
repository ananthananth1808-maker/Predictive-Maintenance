"""
Data Preprocessing Module

Handles data loading, cleaning, feature engineering, and train/test split
for the AI Predictive Maintenance System.

Functions:
- load_dataset: Load CSV from disk
- inspect_data: Display data statistics and distributions
- clean_data: Remove NaN, duplicates, and irrelevant columns
- feature_engineering: Encode and scale features
- prepare_train_test: Stratified split with SMOTE imbalance handling
"""

import os
import pickle
from typing import Tuple, Dict, Any

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from imblearn.over_sampling import SMOTE


def load_dataset(data_path: str = "data/ai4i2020.csv") -> pd.DataFrame:
    """
    Load the AI4I 2020 Predictive Maintenance dataset from CSV.
    
    Args:
        data_path (str): Path to the CSV file (default: data/ai4i2020.csv)
    
    Returns:
        pd.DataFrame: Loaded dataset
    
    Raises:
        FileNotFoundError: If the CSV file does not exist
    """
    if not os.path.exists(data_path):
        raise FileNotFoundError(
            f"Dataset not found at '{data_path}'. "
            f"Please download it from: https://archive.ics.uci.edu/ml/datasets/AI4I+2020+Predictive+Maintenance+Dataset"
        )
    
    print(f"Loading dataset from: {data_path}")
    df = pd.read_csv(data_path)
    print(f"✓ Dataset loaded successfully!")
    
    return df


def inspect_data(df: pd.DataFrame) -> None:
    """
    Inspect and display data statistics, distributions, and quality metrics.
    
    This function checks:
    - Dataset shape (rows, columns)
    - Column names and data types
    - Missing values
    - Duplicate rows
    - Target variable distribution
    - Basic statistics (mean, std, min, max)
    
    Args:
        df (pd.DataFrame): Dataset to inspect
    """
    print("\n" + "="*80)
    print("DATA INSPECTION REPORT")
    print("="*80)
    
    # Dataset Shape
    print(f"\n1. Dataset Shape:")
    print(f"   Rows: {df.shape[0]}, Columns: {df.shape[1]}")
    
    # First 5 Rows
    print(f"\n2. First 5 Rows:")
    print(df.head())
    
    # Column Names and Data Types
    print(f"\n3. Column Names and Data Types:")
    print(df.dtypes)
    
    # Missing Values
    print(f"\n4. Missing Values:")
    missing = df.isnull().sum()
    if missing.sum() == 0:
        print("   ✓ No missing values detected!")
    else:
        print(missing[missing > 0])
    
    # Duplicate Rows
    duplicates = df.duplicated().sum()
    print(f"\n5. Duplicate Rows: {duplicates}")
    if duplicates > 0:
        print(f"   ⚠ {duplicates} duplicate rows detected")
    else:
        print("   ✓ No duplicates detected!")
    
    # Target Distribution
    print(f"\n6. Target Variable Distribution:")
    if 'Target' in df.columns:
        target_counts = df['Target'].value_counts()
        target_pct = df['Target'].value_counts(normalize=True) * 100
        for idx, count in target_counts.items():
            pct = target_pct[idx]
            print(f"   Class {idx}: {count:,} samples ({pct:.2f}%)")
        
        # Calculate imbalance ratio
        class_ratio = target_counts.min() / target_counts.max()
        print(f"   Imbalance Ratio: 1:{target_counts.max()/target_counts.min():.2f}")
    
    # Basic Statistics
    print(f"\n7. Numerical Features Statistics:")
    print(df.describe())
    
    print("\n" + "="*80)


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean the dataset by:
    1. Removing NaN values (if any)
    2. Removing duplicate rows (if any)
    3. Removing irrelevant columns (e.g., ID columns, UDI, Product_ID)
    
    Args:
        df (pd.DataFrame): Raw dataset
    
    Returns:
        pd.DataFrame: Cleaned dataset
    """
    print("\n" + "="*80)
    print("DATA CLEANING")
    print("="*80)
    
    initial_rows = len(df)
    
    # Remove NaN values
    print("\n1. Removing NaN values...")
    df = df.dropna()
    rows_after_nan = len(df)
    removed_nan = initial_rows - rows_after_nan
    print(f"   Rows removed: {removed_nan}")
    
    # Remove duplicate rows
    print("\n2. Removing duplicate rows...")
    df = df.drop_duplicates()
    rows_after_dup = len(df)
    removed_dup = rows_after_nan - rows_after_dup
    print(f"   Rows removed: {removed_dup}")
    
    # Remove irrelevant columns (IDs, indices)
    print("\n3. Removing irrelevant columns...")
    # Common ID column names in datasets
    id_cols = ['UDI', 'Product_ID', 'Index', 'ID', 'id']
    cols_to_drop = [col for col in id_cols if col in df.columns]
    
    if cols_to_drop:
        print(f"   Dropping: {cols_to_drop}")
        df = df.drop(columns=cols_to_drop)
    else:
        print("   No ID columns found")
    
    final_rows = len(df)
    print(f"\n   Final dataset size: {final_rows} rows, {df.shape[1]} columns")
    print(f"   ✓ Cleaning complete!")
    
    print("="*80)
    
    return df


def feature_engineering(
    df: pd.DataFrame,
    exclude_target: bool = True
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Perform feature engineering:
    1. Encode categorical features (one-hot or label encoding)
    2. Scale numerical features using StandardScaler
    3. Return transformed data and preprocessing objects
    
    Args:
        df (pd.DataFrame): Cleaned dataset
        exclude_target (bool): If True, exclude 'Target' column from transformation
    
    Returns:
        Tuple containing:
        - df_encoded (pd.DataFrame): Transformed dataset
        - preprocessing_objects (Dict): Dictionary with scalers and encoders for inference
    """
    print("\n" + "="*80)
    print("FEATURE ENGINEERING")
    print("="*80)
    
    df_fe = df.copy()
    preprocessing_objects = {}
    
    # Separate features and target
    if exclude_target and 'Target' in df_fe.columns:
        target = df_fe.pop('Target')
        has_target = True
    else:
        has_target = False
    
    # Identify categorical and numerical columns
    categorical_cols = df_fe.select_dtypes(include=['object']).columns.tolist()
    numerical_cols = df_fe.select_dtypes(include=['int64', 'float64']).columns.tolist()
    
    print(f"\n1. Categorical Features: {categorical_cols}")
    print(f"2. Numerical Features: {numerical_cols}")
    
    # Encode categorical features using LabelEncoder
    # For production: Use OneHotEncoder for multi-class; LabelEncoder for binary/ordinal
    if categorical_cols:
        print(f"\n3. Encoding categorical features...")
        label_encoders = {}
        
        for col in categorical_cols:
            le = LabelEncoder()
            df_fe[col] = le.fit_transform(df_fe[col])
            label_encoders[col] = le
            print(f"   ✓ {col}: {len(le.classes_)} classes")
        
        preprocessing_objects['label_encoders'] = label_encoders
    
    # Scale numerical features using StandardScaler
    if numerical_cols:
        print(f"\n4. Scaling numerical features...")
        scaler = StandardScaler()
        df_fe[numerical_cols] = scaler.fit_transform(df_fe[numerical_cols])
        preprocessing_objects['scaler'] = scaler
        print(f"   ✓ StandardScaler fitted on {len(numerical_cols)} features")
    
    # Add target back if it was removed
    if has_target:
        df_fe['Target'] = target
    
    print(f"\n✓ Feature Engineering complete!")
    print("="*80)
    
    return df_fe, preprocessing_objects


def prepare_train_test(
    df: pd.DataFrame,
    test_size: float = 0.2,
    random_state: int = 42,
    apply_smote: bool = True
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Perform stratified train/test split and handle class imbalance with SMOTE.
    
    Steps:
    1. Separate features (X) and target (y)
    2. Stratified train/test split (preserves target distribution)
    3. Apply SMOTE to training set only (avoid data leakage)
    
    Args:
        df (pd.DataFrame): Dataset with features and target
        test_size (float): Test set proportion (default: 0.2 = 80/20 split)
        random_state (int): Random seed for reproducibility
        apply_smote (bool): Whether to apply SMOTE (default: True)
    
    Returns:
        Tuple containing:
        - X_train (np.ndarray): Training features
        - X_test (np.ndarray): Test features
        - y_train (np.ndarray): Training target
        - y_test (np.ndarray): Test target
    """
    print("\n" + "="*80)
    print("TRAIN/TEST SPLIT & IMBALANCE HANDLING")
    print("="*80)
    
    # Separate features and target
    X = df.drop(columns=['Target'])
    y = df['Target']
    
    print(f"\n1. Original Dataset:")
    print(f"   Total samples: {len(y)}")
    print(f"   Features: {X.shape[1]}")
    print(f"   Target distribution: {dict(y.value_counts())}")
    
    # Stratified train/test split
    print(f"\n2. Stratified Train/Test Split (80/20)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=test_size,
        random_state=random_state,
        stratify=y  # Maintain target distribution
    )
    
    print(f"   Training set: {len(y_train)} samples")
    print(f"   Test set: {len(y_test)} samples")
    print(f"   Train target distribution: {dict(y_train.value_counts())}")
    print(f"   Test target distribution: {dict(y_test.value_counts())}")
    
    # Handle class imbalance with SMOTE
    if apply_smote:
        print(f"\n3. Applying SMOTE (Synthetic Minority Oversampling) to training set...")
        smote = SMOTE(random_state=random_state)
        X_train_smote, y_train_smote = smote.fit_resample(X_train, y_train)
        
        print(f"   ✓ SMOTE Applied!")
        print(f"   Training set (after SMOTE): {len(y_train_smote)} samples")
        print(f"   New target distribution: {dict(pd.Series(y_train_smote).value_counts())}")
        
        X_train, y_train = X_train_smote, y_train_smote
    
    print(f"\n✓ Data preparation complete!")
    print("="*80)
    
    return X_train.values, X_test.values, y_train, y_test


def save_preprocessing_objects(
    preprocessing_objects: Dict[str, Any],
    output_path: str = "models/preprocessing_objects.pkl"
) -> None:
    """
    Save preprocessing objects (scalers, encoders) for future inference.
    
    Args:
        preprocessing_objects (Dict): Dictionary containing scalers and encoders
        output_path (str): Path to save the pickle file
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    print(f"\nSaving preprocessing objects to: {output_path}")
    with open(output_path, 'wb') as f:
        pickle.dump(preprocessing_objects, f)
    print(f"✓ Preprocessing objects saved!")
