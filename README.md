# OcularTox AI ⌬
> **An Explainable QSAR Decision-Support System for Ocular Toxicity Screening**

Ocular toxicity (eye irritation/damage) is a critical safety endpoint in drug discovery and chemical manufacturing. Traditionally assessed using animal studies (e.g., the Draize test) or expensive *in vitro* wet lab assays, **OcularTox AI** provides a computational alternative. It predicts whether a molecule is toxic or safe directly from its chemical structure (SMILES string)—requiring no lab supplies, no animal testing, and executing in seconds.

This workspace reproduces, optimizes, and significantly extends a published Random Forest QSAR benchmark using the **DARTQSAR** database (4,901 compounds). 

---

## 🚀 Key Gaps Addressed (Beyond the Reference Paper)

While the reference paper reported a Random Forest model with RDKit descriptors achieving an AUC of 0.869, it suffered from five critical scientific gaps. This project addresses all five:

1. **Scaffold-Based Evaluation (OECD Principle 1)**: Evaluated model performance using Bemis-Murcko rings. Random splits overestimate performance by **7% AUC** because they allow identical scaffold cores to appear in training and testing.
2. **Imbalance Handling (SMOTE)**: Corrected the 55/45 class imbalance in the training data using oversampling.
3. **OECD Principle 5 Compliance (Explainability)**: Integrated SHAP (SHapley Additive Explanations) to provide local and global feature impact. The reference paper was a complete black box.
4. **Applicability Domain (Williams Plot)**: Calculated leverage using a hat matrix to identify structurally novel test molecules (outside the training boundary) where predictions are less reliable.
5. **Independent External Validation**: Validated the final model on an independent set of **265 compounds** from a completely separate source, verifying true out-of-sample generalization.

---

## 📊 Key Results

| Split Strategy / Metric | AUC | MCC | Accuracy | Sensitivity | Specificity |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Random Split** (Paper style) | **0.880** | **0.590** | **79.71%** | **76.18%** | **82.65%** |
| **Scaffold Split** (True Novelty) | **0.809** | **0.315** | — | **27.00%** | — |
| **External Validation** (265 novel) | **0.751** | **0.309** | **68.30%** | **68.63%** | **67.21%** |

> ⚠️ **Core Finding**: Scaffold splitting revealed that classical machine learning sensitivity drops to 27% on completely novel scaffolds, highlighting the absolute necessity of evaluating QSAR models using scaffold splitting rather than random splitting.

---

## 💻 Web Workspace Features

OcularTox AI runs a sleek, glassmorphic dark-theme React + Vite frontend that communicates with a FastAPI backend:

* **Single Compound Predictor**: 
  - Paste any SMILES string or search PubChem by name (e.g. *Aspirin*, *Caffeine*, *CCO*).
  - Inspect 2D chemical structure rendering, normal Lipinski Rule of 5 parameters, and PAINS filter alerts.
  - Review toxicity probability, applicability domain status, and SHAP bar chart descriptors.
* **Batch Predictor**: 
  - Upload Excel (`.xlsx`) or CSV (`.csv`) spreadsheets.
  - Automatically identifies titles, header rows, and SMILES columns to run fast, memory-safe predictions in batch.
  - Export predictions to clean, spreadsheet-ready CSV tables.
* **Scientific Documentation Panel**:
  - Live technical specifications dashboard displaying details of the 4-step descriptor cleaning filter.
  - Monospaced terminal console showcasing training datasets, test splits, metrics, and the final confusion matrix.

---

## 📂 Project Structure

```
OcularTox_WebApp/
├── backend/
│   ├── app.py             # FastAPI REST endpoints
│   ├── predictor.py       # Inference engine, PubChem lookup, RDKit descriptors & SHAP
│   └── feature_config.pkl # Medina statistics & training feature list
├── frontend/
│   ├── dist/              # React compiled production build assets
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.jsx        # Landing hub
│   │   │   ├── SinglePredictor.jsx  # Single compound prediction & queue system
│   │   │   ├── BatchPredictor.jsx   # Spreadsheet processing panel
│   │   │   ├── ResearchTools.jsx    # Molecule SVG, SHAP horizontal bar chart, Report
│   │   │   ├── ModelDetails.jsx     # Technical specs & Terminal metrics card
│   │   │   └── Navbar.jsx           # Vertical rail menu navigation
│   │   ├── App.jsx        # App routing, search overlays & notification systems
│   │   └── App.css        # Custom CSS styling sheets
│   └── package.json       # Node package manager configurations
├── models/
│   └── ocular_tox_model.pkl  # Unified ExtraTrees classifier pickle package
├── train_final_model.py   # Complete python model training pipeline script
├── run_app.py             # Launcher script for starting full Web Workspace
├── ocular toxicity.xlsx   # Table S1 DARTQSAR database reference dataset
└── External Validation.xlsx  # Table S6 Validation set details dataset
```

---

## ⚙️ Installation & Setup

### Prerequisites
* Python 3.10+
* Node.js (npm)

### Step 1: Install Python dependencies
```bash
pip install fastapi uvicorn pandas openpyxl scikit-learn rdkit shap joblib pydantic
```

### Step 2: Install Frontend dependencies
```bash
cd frontend
npm install
npm run build
cd ..
```

### Step 3: Run the Workspace
Run the launcher script from the root directory:
```bash
python run_app.py
```
Open your browser and navigate to `http://127.0.0.1:8000`.

---

## 🤝 Research & Credits
* **Database**: DARTQSAR Database (4,901 compounds)
* **Model Classifiers**: ExtraTreesClassifier with 165 filtered RDKit 2D descriptors.
* Built with purpose by **Shubhangini**.
