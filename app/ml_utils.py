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
TARGET = 'compressive_strength_28d'
MODEL_PATH = "model.pkl"

def load_data():
    """Fetch data from SQLite and flatten it for ML."""
    session = SessionLocal()
    try:
        query = session.query(
            Recipe.ca_si_ratio,
            Recipe.molarity_ca_no3,
            Recipe.total_solid_content,
            Recipe.pce_content_wt,
            PerformanceTest.compressive_strength_28d
        ).join(SynthesisBatch, Recipe.batches) \
         .join(PerformanceTest, SynthesisBatch.performance_tests) \
         .filter(PerformanceTest.compressive_strength_28d != None)
         
        results = query.all()
        
        data = []
        for row in results:
            data.append({
                "ca_si_ratio": row.ca_si_ratio,
                "molarity_ca_no3": row.molarity_ca_no3,
                "total_solid_content": row.total_solid_content,
                "pce_content_wt": row.pce_content_wt,
                "compressive_strength_28d": row.compressive_strength_28d
            })
            
        return pd.DataFrame(data)
    finally:
        session.close()

def train_model():
    """Trains an XGBoost regressor and saves it."""
    df = load_data()
    
    if len(df) < 5:
        return {"status": "error", "message": f"Not enough data to train. Found {len(df)} records, need at least 5."}
    
    X = df[FEATURES]
    y = df[TARGET]
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = XGBRegressor(n_estimators=100, learning_rate=0.1, max_depth=3)
    model.fit(X_train, y_train)
    
    # Eval
    predictions = model.predict(X_test)
    mse = mean_squared_error(y_test, predictions) # Default squared=True
    rmse = np.sqrt(mse)
    
    # Save
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
        
    return {"status": "success", "rmse": rmse, "data_count": len(df)}

def predict_strength(ca_si, molarity, solids, pce):
    """Loads model and predicts strength for single input."""
    if not os.path.exists(MODEL_PATH):
        return None
        
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
        
    input_df = pd.DataFrame([{
        'ca_si_ratio': ca_si, 
        'molarity_ca_no3': molarity, 
        'total_solid_content': solids, 
        'pce_content_wt': pce
    }])
    
    return float(model.predict(input_df)[0])
