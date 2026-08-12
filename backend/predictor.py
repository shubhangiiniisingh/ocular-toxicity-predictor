import os
import pickle
import joblib
import numpy as np
import pandas as pd
import json
import urllib.request
import urllib.parse
from rdkit import Chem
from rdkit.Chem import Descriptors, Crippen, rdMolDescriptors, DataStructs, Lipinski
from rdkit.Chem import AllChem
from rdkit.Chem.FilterCatalog import FilterCatalog, FilterCatalogParams
from rdkit.Chem.Draw import rdMolDraw2D
import shap

COMMON_COMPOUNDS = {
    "aspirin": "CC(=O)OC1=CC=CC=C1C(=O)O",
    "chloroacetonitrile": "ClCC#N",
    "caffeine": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",
    "phenol": "Oc1ccccc1",
    "acetone": "CC(=O)C",
    "ethanol": "CCO",
    "methanol": "CO",
    "benzene": "c1ccccc1",
    "formaldehyde": "C=O",
    "paracetamol": "CC(=O)NC1=CC=C(O)C=C1",
    "acetaminophen": "CC(=O)NC1=CC=C(O)C=C1",
    "ibuprofen": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O",
    "nicotine": "CN1CCCC1C2=CN=CC=C2",
    "acetic acid": "CC(=O)O",
    "benzoic acid": "O=C(O)c1ccccc1",
    "toluene": "Cc1ccccc1",
    "chloroform": "ClC(Cl)Cl",
    "urea": "NC(N)=O",
    "glucose": "C(C1C(C(C(C(O1)O)O)O)O)O",
    "salicylic acid": "O=C(O)c1ccccc1O",
}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class OcularToxPredictor:
    def __init__(self, model_path=None, metadata_path=None, config_path=None):
        if model_path is None:
            model_path = os.path.join(BASE_DIR, "extratree_model.pkl")
        if metadata_path is None:
            metadata_path = os.path.join(BASE_DIR, "extratree_metadata.pkl")
        if config_path is None:
            config_path = os.path.join(BASE_DIR, "backend", "feature_config.pkl")

        print(f"Loading pre-trained ExtraTrees model from {model_path}...")
        self.model = joblib.load(model_path)
        self.metadata = joblib.load(metadata_path)
        
        with open(config_path, "rb") as f:
            config = pickle.load(f)
            
        self.desc_names = config["desc_names"]
        self.train_medians = config["train_medians"]
        self.means = config["means"]
        self.stds = config["stds"]
        self.background_sample = config["background_sample"]
        
        # Optimal threshold from metadata (0.45)
        self.threshold = float(self.metadata.get("threshold_optimised", 0.45))
        self._reference_library = None
        try:
            pains_params = FilterCatalogParams()
            pains_params.AddCatalog(FilterCatalogParams.FilterCatalogs.PAINS)
            self.pains_catalog = FilterCatalog(pains_params)
        except Exception:
            self.pains_catalog = None
        
        # Initialize SHAP explainer
        print("Initializing SHAP TreeExplainer...")
        try:
            self.explainer = shap.TreeExplainer(self.model, self.background_sample)
        except Exception as e:
            print(f"SHAP initialization warning: {e}")
            self.explainer = None
            
        print("Predictor successfully initialized!")

    def lookup_pubchem_sync(self, compound_name):
        """Lookup PubChem API or local dictionary to resolve compound name to SMILES."""
        if not compound_name or not isinstance(compound_name, str):
            return None
            
        name_clean = compound_name.strip().lower()
        if name_clean in COMMON_COMPOUNDS:
            return COMMON_COMPOUNDS[name_clean]
            
        try:
            encoded_name = urllib.parse.quote(compound_name.strip())
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{encoded_name}/property/CanonicalSMILES/JSON"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=4) as response:
                data = json.loads(response.read().decode('utf-8'))
                props = data.get("PropertyTable", {}).get("Properties", [])
                if props and "CanonicalSMILES" in props[0]:
                    return props[0]["CanonicalSMILES"]
        except Exception:
            pass
            
        return None

    def is_smiles(self, s):
        """Check if a string is a SMILES or a compound name."""
        if not s or not isinstance(s, str):
            return False
        if ' ' in s.strip():
            return False
        try:
            mol = Chem.MolFromSmiles(s.strip())
            return mol is not None
        except Exception:
            return False

    def get_compound_name(self, smiles, input_name=None, allow_pubchem=True):
        """Find the name of a compound given its SMILES and optionally the user's input name."""
        if input_name and not self.is_smiles(input_name):
            return input_name.strip().title()
            
        try:
            mol = Chem.MolFromSmiles(smiles)
            if mol:
                can_smiles = Chem.MolToSmiles(mol)
            else:
                can_smiles = smiles
        except Exception:
            can_smiles = smiles
            
        # 1. Check local COMMON_COMPOUNDS
        for name, common_smi in COMMON_COMPOUNDS.items():
            try:
                cmol = Chem.MolFromSmiles(common_smi)
                if cmol and Chem.MolToSmiles(cmol) == can_smiles:
                    return name.title()
            except Exception:
                if common_smi == smiles or common_smi == can_smiles:
                    return name.title()
                    
        if not allow_pubchem:
            return "Unknown Compound"

        # 2. Try PubChem Synonyms API
        try:
            encoded_smiles = urllib.parse.quote(can_smiles)
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{encoded_smiles}/synonyms/JSON"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read().decode('utf-8'))
                info = data.get("InformationList", {}).get("Information", [])
                if info and "Synonym" in info[0] and info[0]["Synonym"]:
                    return info[0]["Synonym"][0].title()
        except Exception:
            pass
            
        # 3. Try PubChem property IUPACName
        try:
            encoded_smiles = urllib.parse.quote(can_smiles)
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{encoded_smiles}/property/IUPACName/JSON"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read().decode('utf-8'))
                props = data.get("PropertyTable", {}).get("Properties", [])
                if props and "IUPACName" in props[0]:
                    return props[0]["IUPACName"].title()
        except Exception:
            pass
            
        return "Unknown Compound"

    def standardize_smiles(self, smi, allow_pubchem=True):
        """Clean and canonicalize input SMILES or compound name, keeping the largest fragment."""
        if not smi or not isinstance(smi, str):
            return None, None
            
        cleaned_input = smi.strip()
        try:
            mol = Chem.MolFromSmiles(cleaned_input)
            if mol is None and allow_pubchem:
                # If direct RDKit parsing fails, try resolving input as a compound name
                resolved_smiles = self.lookup_pubchem_sync(cleaned_input)
                if resolved_smiles:
                    mol = Chem.MolFromSmiles(resolved_smiles)
                    cleaned_input = resolved_smiles
                    
            if mol is None:
                return None, None
                
            frags = Chem.GetMolFrags(mol, asMols=True, sanitizeFrags=True)
            largest = max(frags, key=lambda m: m.GetNumHeavyAtoms())
            canonical_smi = Chem.MolToSmiles(largest)
            return canonical_smi, largest
        except Exception:
            return None, None

    def draw_molecule_svg(self, mol):
        """Generate a sleek vector SVG image of the chemical structure."""
        if mol is None:
            return ""
        try:
            drawer = rdMolDraw2D.MolDraw2DSVG(350, 300)
            opts = drawer.drawOptions()
            opts.clearBackground = False
            opts.bondLineWidth = 2
            rdMolDraw2D.PrepareAndDrawMolecule(drawer, mol)
            drawer.FinishDrawing()
            svg = drawer.GetDrawingText()
            return svg
        except Exception:
            return ""

    def calculate_properties(self, mol):
        """Extract core physicochemical properties."""
        if mol is None:
            return {}
        try:
            mw = round(Descriptors.MolWt(mol), 2)
            logp = round(Crippen.MolLogP(mol), 2)
            tpsa = round(rdMolDescriptors.CalcTPSA(mol), 2)
            hbd = rdMolDescriptors.CalcNumHBD(mol)
            hba = rdMolDescriptors.CalcNumHBA(mol)
            rotb = rdMolDescriptors.CalcNumRotatableBonds(mol)
            formula = rdMolDescriptors.CalcMolFormula(mol)
            exact_mass = round(Descriptors.ExactMolWt(mol), 4)
            heavy_atoms = mol.GetNumHeavyAtoms()
            num_atoms = mol.GetNumAtoms()
            num_bonds = mol.GetNumBonds()
            ring_count = rdMolDescriptors.CalcNumRings(mol)
            aromatic_rings = rdMolDescriptors.CalcNumAromaticRings(mol)
            fraction_csp3 = round(rdMolDescriptors.CalcFractionCSP3(mol), 3)
            ro5 = {
                "mw_pass": mw <= 500,
                "logp_pass": logp <= 5,
                "hbd_pass": hbd <= 5,
                "hba_pass": hba <= 10,
                "violations": sum([mw > 500, logp > 5, hbd > 5, hba > 10]),
                "status": "Pass" if sum([mw > 500, logp > 5, hbd > 5, hba > 10]) <= 1 else "Review"
            }
            pains_match = self.pains_catalog.GetFirstMatch(mol) if self.pains_catalog else None
            return {
                "mw": mw,
                "exact_mass": exact_mass,
                "logp": logp,
                "tpsa": tpsa,
                "hbd": hbd,
                "hba": hba,
                "rotb": rotb
                ,"formula": formula,
                "heavy_atoms": heavy_atoms,
                "num_atoms": num_atoms,
                "num_bonds": num_bonds,
                "rings": ring_count,
                "aromatic_rings": aromatic_rings,
                "fraction_csp3": fraction_csp3,
                "lipinski_ro5": ro5,
                "pains": {"flagged": bool(pains_match), "alert": pains_match.GetDescription() if pains_match else "No PAINS alert detected"}
            }
        except Exception:
            return {}

    def extract_features(self, mol):
        """Compute all RDKit descriptors and subset to the 165 features expected by the model."""
        if mol is None:
            return None
        raw_vals = {}
        for name, func in Descriptors.descList:
            try:
                raw_vals[name] = func(mol)
            except Exception:
                raw_vals[name] = np.nan
                
        feature_vector = []
        for name in self.desc_names:
            val = raw_vals.get(name, np.nan)
            if pd.isna(val) or np.isinf(val):
                val = self.train_medians.get(name, 0.0)
            feature_vector.append(val)
            
        return np.array(feature_vector, dtype=np.float32).reshape(1, -1)

    def check_applicability_domain(self, feature_vector):
        """Assess whether the molecule falls within the model's domain of applicability."""
        if feature_vector is None:
            return "Unknown", 0.0
            
        arr = feature_vector.flatten()
        z_scores = []
        for idx, name in enumerate(self.desc_names):
            m = self.means.get(name, 0.0)
            s = self.stds.get(name, 1.0)
            z = abs((arr[idx] - m) / s)
            z_scores.append(z)
            
        max_z = np.max(z_scores)
        mean_z = np.mean(z_scores)
        
        if max_z <= 3.5 and mean_z <= 1.5:
            status = "Inside Domain (Reliable)"
            confidence = "High"
        elif max_z <= 5.0 and mean_z <= 2.2:
            status = "Borderline Domain"
            confidence = "Moderate"
        else:
            status = "Out of Domain (Unreliable)"
            confidence = "Low"
            
        return status, confidence, round(float(mean_z), 2)

    def get_shap_explanation(self, feature_vector):
        """Compute SHAP values to identify top positive and negative feature contributions."""
        if self.explainer is None or feature_vector is None:
            return []
        try:
            shap_values = self.explainer.shap_values(feature_vector)
            # ExtraTrees model binary classification -> shap_values shape: (1, 165, 2) or (1, 165)
            if isinstance(shap_values, list):
                vals = shap_values[1].flatten()
            elif len(shap_values.shape) == 3:
                vals = shap_values[0, :, 1]
            else:
                vals = shap_values.flatten()
                
            arr = feature_vector.flatten()
            contributions = []
            for idx, name in enumerate(self.desc_names):
                contributions.append({
                    "feature": name,
                    "val": round(float(arr[idx]), 3),
                    "impact": round(float(vals[idx]), 4)
                })
                
            # Sort by absolute SHAP impact
            contributions.sort(key=lambda x: abs(x["impact"]), reverse=True)
            return contributions[:8]
        except Exception as e:
            print(f"SHAP calculation error: {e}")
            return []

    def predict_single(self, smiles_input, allow_pubchem=True, allow_shap=True):
        """Run complete single molecule prediction pipeline."""
        try:
            canonical_smi, mol = self.standardize_smiles(smiles_input)
            if mol is None:
                return {
                    "success": False,
                    "error": "Invalid SMILES string. Unable to parse chemical structure."
                }
                
            svg = self.draw_molecule_svg(mol)
            props = self.calculate_properties(mol)
            features = self.extract_features(mol)
            
            # Prediction probabilities
            probs = self.model.predict_proba(features)[0]
            prob_toxic = float(probs[1])
            
            # Classification based on research threshold (0.45)
            prediction = "Toxic" if prob_toxic >= self.threshold else "Non-Toxic"
            
            # Applicability domain
            ad_status, ad_confidence, mean_z = self.check_applicability_domain(features)
            
            # SHAP explainability
            shap_top = self.get_shap_explanation(features) if allow_shap else []
            
            # Get compound name
            compound_name = self.get_compound_name(canonical_smi, input_name=smiles_input, allow_pubchem=allow_pubchem)
            
            return {
                "success": True,
                "input_smiles": smiles_input,
                "canonical_smiles": canonical_smi,
                "compound_name": compound_name,
                "prediction": prediction,
                "probability_toxic": round(prob_toxic, 4),
                "probability_nontoxic": round(1.0 - prob_toxic, 4),
                "threshold_used": self.threshold,
                "properties": props,
                "svg": svg,
                "ad_status": ad_status,
                "ad_confidence": ad_confidence,
                "mean_z_score": mean_z,
                "shap_explanation": shap_top
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Prediction failed: {str(e)}"
            }

    def predict_batch(self, smiles_list):
        """Run batch predictions over a list of SMILES."""
        results = []
        for idx, smi in enumerate(smiles_list):
            res = self.predict_single(smi, allow_pubchem=False, allow_shap=False)
            if res["success"]:
                results.append({
                    "index": idx + 1,
                    "input_smiles": smi,
                    "canonical_smiles": res["canonical_smiles"],
                    "compound_name": res["compound_name"],
                    "prediction": res["prediction"],
                    "probability_toxic": res["probability_toxic"],
                    "mw": res["properties"].get("mw", "-"),
                    "logp": res["properties"].get("logp", "-"),
                    "tpsa": res["properties"].get("tpsa", "-"),
                    "ad_status": res["ad_status"],
                    "status": "Valid"
                })
            else:
                results.append({
                    "index": idx + 1,
                    "input_smiles": smi,
                    "canonical_smiles": "-",
                    "compound_name": "-",
                    "prediction": "Error",
                    "probability_toxic": 0.0,
                    "mw": "-",
                    "logp": "-",
                    "tpsa": "-",
                    "ad_status": "Invalid SMILES",
                    "status": "Invalid"
                })
        return results

    def _load_reference_library(self):
        """Load the supplied dataset lazily; this is never used to change model weights."""
        if self._reference_library is not None:
            return self._reference_library
        path = os.path.join(BASE_DIR, "ocular toxicity.xlsx")
        library = []
        try:
            data = pd.read_excel(path, sheet_name="Table S1", skiprows=1)
            smiles_col = next((c for c in data.columns if "smiles" in str(c).lower()), None)
            label_col = next((c for c in data.columns if str(c).strip().lower() in {"label", "toxicity", "class", "y"}), None)
            if smiles_col:
                for _, row in data[[smiles_col] + ([label_col] if label_col else [])].dropna(subset=[smiles_col]).head(4901).iterrows():
                    canonical, mol = self.standardize_smiles(str(row[smiles_col]))
                    if mol:
                        library.append({"smiles": canonical, "label": row.get(label_col, None), "fp": AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)})
        except Exception as exc:
            print(f"Reference library unavailable: {exc}")
        self._reference_library = library
        return library

    def find_similar(self, smiles_input, limit=5):
        canonical, mol = self.standardize_smiles(smiles_input)
        if mol is None:
            return {"success": False, "error": "Enter a valid SMILES string or compound name first."}
        library = self._load_reference_library()
        if not library:
            return {"success": True, "query": canonical, "reference_available": False, "results": []}
        query_fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
        scored = []
        for item in library:
            score = DataStructs.TanimotoSimilarity(query_fp, item["fp"])
            scored.append({"smiles": item["smiles"], "similarity": round(float(score), 3), "label": item["label"]})
        scored.sort(key=lambda item: item["similarity"], reverse=True)
        return {"success": True, "query": canonical, "reference_available": True, "results": scored[:limit]}
