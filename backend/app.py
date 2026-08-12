import os
import io
import urllib.request
import urllib.parse
import json
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from backend.predictor import OcularToxPredictor

app = FastAPI(
    title="Ocular Toxicity AI Predictor",
    description="REST API for predicting ocular toxicity of chemical compounds using pre-trained ExtraTrees model",
    version="1.0.0"
)

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize predictor singleton
predictor = OcularToxPredictor()

class SinglePredictionRequest(BaseModel):
    smiles: str

@app.get("/api/health")
def health_check():
    return {"status": "ok", "model_loaded": True}

@app.get("/api/model-info")
def get_model_info():
    """Return model performance metrics and research metadata."""
    meta = predictor.metadata
    return {
        "model_name": meta.get("model_name", "ExtraTree"),
        "algorithm": meta.get("algorithm", "ExtraTreesClassifier"),
        "created_on": meta.get("created_on", "2026-08-07"),
        "fingerprint_type": meta.get("fingerprint_type", "RDKit 2D Descriptors"),
        "n_features": predictor.model.n_features_in_,
        "threshold": predictor.threshold,
        "internal_auc": meta.get("internal_auc", 0.8801),
        "external_auc": meta.get("external_auc", 0.7514),
        "dataset_stats": {
            "training_compounds": 4901,
            "external_compounds": 266,
            "feature_set": "165 Filtered Descriptors"
        }
    }

@app.post("/api/predict")
def predict_single(req: SinglePredictionRequest):
    """Predict ocular toxicity for a single SMILES string."""
    if not req.smiles or not req.smiles.strip():
        raise HTTPException(status_code=400, detail="SMILES string is required")
        
    res = predictor.predict_single(req.smiles.strip())
    if not res["success"]:
        raise HTTPException(status_code=400, detail=res["error"])
        
    return res

@app.get("/api/lookup")
def lookup_pubchem_smiles(name: str = Query(..., min_length=1)):
    """Lookup PubChem API or local dictionary to resolve a chemical compound name to SMILES."""
    smiles = predictor.lookup_pubchem_sync(name.strip())
    if smiles:
        return {"success": True, "name": name, "smiles": smiles}
    raise HTTPException(status_code=404, detail=f"Compound '{name}' not found on PubChem. Please check spelling or enter SMILES directly.")

@app.post("/api/predict/batch")
async def predict_batch(file: UploadFile = File(...)):
    """Process an uploaded Excel or CSV file containing SMILES strings."""
    try:
        content = await file.read()
        filename = file.filename.lower()
        
        if filename.endswith(".xlsx") or filename.endswith(".xls"):
            df = pd.read_excel(io.BytesIO(content))
        elif filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Please upload a .xlsx or .csv file.")
            
        if len(df) > 0:
            # Check if the first row contains header-like strings (e.g. "smiles")
            # when the columns are unnamed or default
            first_row_values = [str(x).strip().lower() for x in df.iloc[0].values]
            is_first_row_header = any("smiles" in val or val == "label" for val in first_row_values)
            is_unnamed_cols = any("unnamed:" in str(col).lower() for col in df.columns)
            
            if is_first_row_header or is_unnamed_cols:
                if is_first_row_header:
                    new_header = df.iloc[0].astype(str)
                    df = df[1:]
                    df.columns = new_header
                elif len(df) > 1:
                    second_row_values = [str(x).strip().lower() for x in df.iloc[1].values]
                    if any("smiles" in val or val == "label" for val in second_row_values):
                        new_header = df.iloc[1].astype(str)
                        df = df[2:]
                        df.columns = new_header
            
        # Find column containing SMILES
        smiles_col = None
        for col in df.columns:
            if "smiles" in str(col).lower():
                smiles_col = col
                break
                
        if smiles_col is None:
            # Check if any column contains SMILES structures by scanning data values
            for col in df.columns:
                sample = df[col].dropna().astype(str).tolist()[:5]
                valid_count = 0
                for s in sample:
                    if len(s.strip()) > 0 and ' ' not in s:
                        if predictor.is_smiles(s):
                            valid_count += 1
                if valid_count >= 2 or (len(sample) == 1 and valid_count == 1):
                    smiles_col = col
                    break
                    
        if smiles_col is None:
            # Fallback to first column
            smiles_col = df.columns[0]
            
        smiles_list = df[smiles_col].dropna().astype(str).tolist()[:500]  # Cap at 500 rows for web safety
        
        results = predictor.predict_batch(smiles_list)
        return {
            "total_processed": len(results),
            "smiles_column_used": str(smiles_col),
            "results": results
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")

@app.get("/api/similarity")
def similarity_search(smiles: str = Query(..., min_length=1), limit: int = Query(5, ge=1, le=10)):
    """Find chemically similar compounds in the optional local reference dataset."""
    result = predictor.find_similar(smiles, limit)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

# Serve frontend production build if available
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))
