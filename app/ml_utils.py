import pandas as pd
import pickle
import os
import numpy as np
from sqlalchemy import create_engine
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
from app.database import DATABASE_URL, SessionLocal
from app.models import Recipe, SynthesisBatch, PerformanceTest

# Define feature columns explicitly to ensure consistency between Training and Inference
FEATURES = ['ca_si_ratio', 'molarity_ca_no3', 'total_solid_content', 'pce_content_wt']
TARGETS = ['compressive_strength_1d', 'compressive_strength_28d']
MODEL_DIR = "models"
if not os.path.exists(MODEL_DIR):
    os.makedirs(MODEL_DIR)

def load_data():
    """Fetch data from SQLite and flatten it for ML."""
    session = SessionLocal()
    try:
        query = session.query(
            Recipe.ca_si_ratio,
            Recipe.molarity_ca_no3,
            Recipe.total_solid_content,
            Recipe.pce_content_wt,
            PerformanceTest.compressive_strength_1d,
            PerformanceTest.compressive_strength_28d
        ).join(SynthesisBatch, Recipe.batches) \
         .join(PerformanceTest, SynthesisBatch.performance_tests)
         
        results = query.all()
        
        data = []
        for row in results:
            data.append({
                "ca_si_ratio": row.ca_si_ratio,
                "molarity_ca_no3": row.molarity_ca_no3,
                "total_solid_content": row.total_solid_content,
                "pce_content_wt": row.pce_content_wt,
                "compressive_strength_1d": row.compressive_strength_1d,
                "compressive_strength_28d": row.compressive_strength_28d
            })
            
        return pd.DataFrame(data)
    finally:
        session.close()

def train_model():
    """Trains XGBoost regressors for each target and saves them."""
    df = load_data()
    
    if len(df) < 5:
        return {"status": "error", "message": f"Not enough data to train. Found {len(df)} records, need at least 5."}
    
    results = {"status": "success", "metrics": {}, "data_count": len(df)}
    
    for target in TARGETS:
        # Filter rows that have this specific target
        df_target = df.dropna(subset=[target])
        if len(df_target) < 5:
            continue
            
        X = df_target[FEATURES]
        y = df_target[target]
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        model = XGBRegressor(n_estimators=100, learning_rate=0.1, max_depth=3)
        model.fit(X_train, y_train)
        
        predictions = model.predict(X_test)
        rmse = np.sqrt(mean_squared_error(y_test, predictions))
        
        # Save per-target model
        model_path = os.path.join(MODEL_DIR, f"model_{target}.pkl")
        with open(model_path, "wb") as f:
            pickle.dump(model, f)
            
        results["metrics"][target] = rmse
        
    return results

def predict_strength(ca_si, molarity, solids, pce, target='28d'):
    """Loads specific model and predicts strength."""
    target_col = f"compressive_strength_{target}"
    model_path = os.path.join(MODEL_DIR, f"model_{target_col}.pkl")
    
    if not os.path.exists(model_path):
        return None
        
    with open(model_path, "rb") as f:
        model = pickle.load(f)
        
    input_df = pd.DataFrame([{
        'ca_si_ratio': ca_si, 
        'molarity_ca_no3': molarity, 
        'total_solid_content': solids, 
        'pce_content_wt': pce
    }])
    
    val = float(model.predict(input_df)[0])
    return val if val > 0 else 0.0 # Clamp to 0
