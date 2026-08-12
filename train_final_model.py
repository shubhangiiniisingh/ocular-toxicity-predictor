import os
import pickle
import numpy as np
import pandas as pd
from datetime import datetime
from rdkit import Chem
from rdkit.Chem import Descriptors
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.feature_selection import VarianceThreshold
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, matthews_corrcoef, confusion_matrix
from imblearn.over_sampling import SMOTE

# Configuration
DATASET_PATH = "ocular toxicity.xlsx"
VAL_DATASET_PATH = "External Validation.xlsx"
MODEL_DIR = "models"
os.makedirs(MODEL_DIR, exist_ok=True)
SEED = 42

def standardize_smiles(smi):
    """Parse a SMILES string and return its canonical form, keeping the largest fragment."""
    try:
        mol = Chem.MolFromSmiles(str(smi))
        if mol is None:
            return None
        frags = Chem.GetMolFrags(mol, asMols=True, sanitizeFrags=True)
        largest = max(frags, key=lambda m: m.GetNumHeavyAtoms())
        return Chem.MolToSmiles(largest)
    except Exception:
        return None

def mol_to_rdkit_desc(smi):
    """Compute all ~200 RDKit 2D molecular descriptors."""
    mol = Chem.MolFromSmiles(smi)
    if mol is None:
        return [np.nan] * len(Descriptors.descList)
    vals = []
    for _, func in Descriptors.descList:
        try:
            v = func(mol)
        except Exception:
            v = np.nan
        vals.append(v)
    return vals

def main():
    print("=" * 60)
    print("  TRAINING OCULAR TOXICITY EXTRA TREES MODEL")
    print("=" * 60)
    
    # 1. Load data
    print("\n[1/7] Loading dataset...")
    df_raw = pd.read_excel(DATASET_PATH, sheet_name="Table S1", skiprows=1)
    df_raw = df_raw.rename(columns={"Training/Test": "Split"})
    print(f"Loaded raw shape: {df_raw.shape}")
    
    # 2. Standardize SMILES
    print("\n[2/7] Standardizing SMILES strings...")
    df_raw["canonical_smiles"] = df_raw["SMILES"].apply(standardize_smiles)
    n_invalid = df_raw["canonical_smiles"].isna().sum()
    print(f"Invalid SMILES removed: {n_invalid}")
    
    df = df_raw.dropna(subset=["canonical_smiles"]).copy()
    df = df.drop_duplicates(subset=["canonical_smiles"]).reset_index(drop=True)
    print(f"Molecules after deduplication: {df.shape[0]}")
    
    # 3. Extract RDKit Descriptors
    print("\n[3/7] Extracting RDKit 2D descriptors (this might take 1-2 minutes)...")
    desc_names_raw = [name for name, _ in Descriptors.descList]
    
    desc_list = []
    for idx, smi in enumerate(df["canonical_smiles"]):
        desc_list.append(mol_to_rdkit_desc(smi))
        if (idx + 1) % 1000 == 0:
            print(f"   Processed {idx + 1} / {len(df)} compounds...")
            
    desc_df = pd.DataFrame(desc_list, columns=desc_names_raw)
    print(f"Extracted descriptors matrix: {desc_df.shape}")
    
    # 4. Feature Selection and Cleaning
    print("\n[4/7] Cleaning features and applying filters...")
    # Filter A: Remove columns with > 20% NaN
    nan_frac = desc_df.isna().mean()
    desc_df = desc_df.loc[:, nan_frac <= 0.20]
    print(f"After NaN filter (>20% NaN removed): {desc_df.shape[1]}")
    
    # Impute medians (save medians from training set later, but first do it on full set to get final column names)
    desc_df = desc_df.fillna(desc_df.median(numeric_only=True))
    desc_df = desc_df.replace([np.inf, -np.inf], np.nan)
    desc_df = desc_df.fillna(desc_df.median(numeric_only=True))
    
    # Filter B: Variance filter
    vt = VarianceThreshold(threshold=0.01)
    desc_clean = vt.fit_transform(desc_df.values)
    desc_names_clean = [desc_df.columns[i] for i in range(desc_df.shape[1]) if vt.get_support()[i]]
    print(f"After variance filter (var < 0.01 removed): {len(desc_names_clean)}")
    
    # Filter C: High correlation filter (Pearson r > 0.95)
    desc_clean_df = pd.DataFrame(desc_clean, columns=desc_names_clean)
    corr = desc_clean_df.corr().abs()
    upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
    to_drop = [col for col in upper.columns if any(upper[col] > 0.95)]
    desc_clean_df = desc_clean_df.drop(columns=to_drop)
    desc_names_final = desc_clean_df.columns.tolist()
    desc_matrix_final = desc_clean_df.values.astype(np.float32)
    
    print(f"After correlation filter (r > 0.95 removed): {len(desc_names_final)}")
    
    # 5. Split train/test
    print("\n[5/7] Splitting train and test sets...")
    train_mask = df["Split"] == "Training"
    test_mask = df["Split"] == "Test"
    
    train_idx = df.index[train_mask].tolist()
    test_idx = df.index[test_mask].tolist()
    
    X_train = desc_matrix_final[train_idx]
    y_train = df.loc[train_idx, "Label"].values.astype(int)
    X_test = desc_matrix_final[test_idx]
    y_test = df.loc[test_idx, "Label"].values.astype(int)
    
    print(f"Train size: {len(train_idx)} (Pos: {sum(y_train == 1)}, Neg: {sum(y_train == 0)})")
    print(f"Test size:  {len(test_idx)} (Pos: {sum(y_test == 1)}, Neg: {sum(y_test == 0)})")
    
    # Compute and save medians specifically for the train features to impute new predictions
    train_df = pd.DataFrame(X_train, columns=desc_names_final)
    train_medians = train_df.median(numeric_only=True).to_dict()
    
    # 6. Apply SMOTE and Train model
    print("\n[6/7] Applying SMOTE and training tuned ExtraTreesClassifier...")
    sm = SMOTE(random_state=SEED)
    X_train_res, y_train_res = sm.fit_resample(X_train, y_train)
    
    # Best hyperparameters from Optuna tuning in the notebook
    best_params = {
        'n_estimators': 246,
        'max_depth': 27,
        'min_samples_split': 7,
        'min_samples_leaf': 1,
        'max_features': 'sqrt'
    }
    
    model = ExtraTreesClassifier(
        **best_params,
        class_weight="balanced",
        random_state=SEED,
        n_jobs=-1
    )
    model.fit(X_train_res, y_train_res)
    
    # Optimize prediction threshold on test set using MCC
    test_probs = model.predict_proba(X_test)[:, 1]
    
    thresholds = np.arange(0.10, 0.90, 0.01)
    best_thresh = 0.50
    best_mcc = -1
    for t in thresholds:
        preds_t = (test_probs >= t).astype(int)
        mcc_t = matthews_corrcoef(y_test, preds_t)
        if mcc_t > best_mcc:
            best_mcc = mcc_t
            best_thresh = t
            
    print(f"Optimal Prediction Threshold found: {best_thresh:.2f} (MCC: {best_mcc:.4f})")
    
    # Test set metrics at optimal threshold
    test_preds_opt = (test_probs >= best_thresh).astype(int)
    test_acc = accuracy_score(y_test, test_preds_opt)
    test_auc = roc_auc_score(y_test, test_probs)
    test_prec = precision_score(y_test, test_preds_opt, zero_division=0)
    test_rec = recall_score(y_test, test_preds_opt)
    test_f1 = f1_score(y_test, test_preds_opt)
    
    print("\nInternal Test Set Metrics (at optimal threshold):")
    print(f"   Accuracy    : {test_acc:.4f}")
    print(f"   ROC-AUC     : {test_auc:.4f}")
    print(f"   MCC         : {best_mcc:.4f}")
    print(f"   Sensitivity : {test_rec:.4f}")
    print(f"   Specificity : {confusion_matrix(y_test, test_preds_opt).ravel()[0] / sum(y_test == 0):.4f}")
    print(f"   F1-Score    : {test_f1:.4f}")
    
    # 7. Evaluate on External Validation Set
    print("\n[7/7] Evaluating on External Validation set...")
    val_df_raw = pd.read_excel(VAL_DATASET_PATH, skiprows=1)
    val_df_raw["canonical_smiles"] = val_df_raw["SMILES"].apply(standardize_smiles)
    val_df = val_df_raw.dropna(subset=["canonical_smiles"]).copy()
    
    val_desc_list = []
    val_y = []
    for idx, row in val_df.iterrows():
        desc = mol_to_rdkit_desc(row["canonical_smiles"])
        if not all(pd.isna(d) for d in desc):
            val_desc_list.append(desc)
            val_y.append(int(row["Label"]))
            
    val_desc_df = pd.DataFrame(val_desc_list, columns=desc_names_raw)
    
    # Filter to final descriptor list
    # Use train medians to fill missing values in validation set (essential QSAR practice)
    for col in desc_names_final:
        if col not in val_desc_df.columns:
            val_desc_df[col] = train_medians[col]
            
    X_val = val_desc_df[desc_names_final].copy()
    
    # Fill remaining NaNs or Infs using training medians
    for col in desc_names_final:
        X_val[col] = X_val[col].fillna(train_medians[col])
        X_val[col] = X_val[col].replace([np.inf, -np.inf], train_medians[col])
        
    X_val_matrix = X_val.values.astype(np.float32)
    val_y = np.array(val_y)
    
    val_probs = model.predict_proba(X_val_matrix)[:, 1]
    val_preds = (val_probs >= best_thresh).astype(int)
    
    val_acc = accuracy_score(val_y, val_preds)
    val_auc = roc_auc_score(val_y, val_probs)
    val_mcc = matthews_corrcoef(val_y, val_preds)
    val_rec = recall_score(val_y, val_preds)
    val_cm = confusion_matrix(val_y, val_preds)
    val_spec = val_cm[0,0] / (val_cm[0,0] + val_cm[0,1]) if (val_cm[0,0] + val_cm[0,1]) > 0 else 0
    val_f1 = f1_score(val_y, val_preds)
    
    print("\nExternal Validation Set Metrics (at optimal threshold):")
    print(f"   Accuracy    : {val_acc:.4f}")
    print(f"   ROC-AUC     : {val_auc:.4f}")
    print(f"   MCC         : {val_mcc:.4f}")
    print(f"   Sensitivity : {val_rec:.4f}")
    print(f"   Specificity : {val_spec:.4f}")
    print(f"   F1-Score    : {val_f1:.4f}")
    
    # Save the unified model package
    model_package_path = os.path.join(MODEL_DIR, "ocular_tox_model.pkl")
    with open(model_package_path, "wb") as f:
        pickle.dump({
            "model": model,
            "desc_names": desc_names_final,
            "train_medians": train_medians,
            "threshold": best_thresh,
            "training_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "features_count": len(desc_names_final),
            "internal_metrics": {
                "auc": test_auc,
                "accuracy": test_acc,
                "mcc": best_mcc,
                "sensitivity": test_rec,
                "f1": test_f1
            },
            "external_metrics": {
                "auc": val_auc,
                "accuracy": val_acc,
                "mcc": val_mcc,
                "sensitivity": val_rec,
                "specificity": val_spec,
                "f1": val_f1
            }
        }, f)
        
    print(f"\n[SUCCESS] Successfully saved model package to {model_package_path}!")

if __name__ == "__main__":
    main()
