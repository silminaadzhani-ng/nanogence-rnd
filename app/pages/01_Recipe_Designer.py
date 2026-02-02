import streamlit as st
import json
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Recipe

from app.ml_utils import predict_strength

st.set_page_config(page_title="Recipe Designer", page_icon="📝", layout="wide")

st.markdown("# 📝 Experimental Recipe Designer")

# Initialize DB Session
db: Session = next(get_db())

# --- Sidebar: AI Prediction ---
with st.sidebar:
    st.header("🧠 AI Predictor")
    st.info("Adjust parameters to see estimated 28d Strength.")
    # Placeholders that will be updated by form state if we used session state, 
    # but for simple form, we might need to move inputs out of form or use a callback.
    # For MVP, we'll put the prediction INSIDE the main flow after inputs.

with st.expander("ℹ️  Instructions", expanded=False):
    st.info("Define the chemical composition and synthesis process steps here. All recipes are versioned.")

# --- Form for Recipe Inputs ---
with st.form("recipe_form"):
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Chemical Composition")
        name = st.text_input("Recipe Name", placeholder="e.g. CSH-Seed-Standard-2024")
        ca_si = st.number_input("Ca/Si Ratio", min_value=0.5, max_value=2.5, step=0.05, value=1.0)
        molarity = st.number_input("Ca(NO3)2 Molarity (mol/L)", min_value=0.1, max_value=5.0, step=0.1, value=1.0)
        solids = st.number_input("Total Solid Content (%)", min_value=1.0, max_value=50.0, value=10.0)
        pce = st.number_input("PCE Content (wt.%)", min_value=0.0, max_value=5.0, step=0.1, value=0.5)
        
        # Live Prediction Block
        pred_strength = predict_strength(ca_si, molarity, solids, pce)
        if pred_strength:
            st.metric(label="Predicted 28d Strength (MPa)", value=f"{pred_strength:.1f} MPa")
        else:
            st.caption("Train model to see predictions.")

    with col2:
        st.subheader("Process Parameters")
        feed_rate = st.number_input("Addition Rate (mL/min)", value=10.0)
        
        st.caption("Feeding Sequence (JSON format for now)")
        # In a full app, this would be a dynamic list builder.
        default_steps = [
            {"step": 1, "description": "Dissolve 8.28g of PCX 50 in 260.36g DI water", "duration_min": 10},
            {"step": 2, "description": "Mix to ensure homogeneity", "duration_min": 15},
            {"step": 3, "description": "Adjust pH to 11.7 +/- 0.2 with 5M NaOH", "duration_min": 5},
            {"step": 4, "description": "Mix to ensure pH homogeneity", "duration_min": 10},
            {"step": 5, "description": "Add Ca and Si solutions dropwise (0.5 mL/min)", "duration_min": 60},
            {"step": 6, "description": "Monitor and adjust pH (11.7 +/- 0.2)", "duration_min": 0},
            {"step": 7, "description": "Post-synthesis mixing", "duration_min": 60}
        ]
        sequence_json = st.text_area("Steps Config", value=json.dumps(default_steps, indent=2), height=200)

    submitted = st.form_submit_button("💾 Save Recipe")

    if submitted:
        if not name:
            st.error("Please provide a name for the recipe.")
        else:
            try:
                proc_config = {
                    "rate_of_addition": feed_rate,
                    "feeding_sequence": json.loads(sequence_json)
                }
                
                new_recipe = Recipe(
                    name=name,
                    ca_si_ratio=ca_si,
                    molarity_ca_no3=molarity,
                    total_solid_content=solids,
                    pce_content_wt=pce,
                    process_config=proc_config,
                    created_by="Silmina Adzhani" 
                )
                db.add(new_recipe)
                db.commit()
                st.success(f"Recipe '{name}' saved successfully!")
            except json.JSONDecodeError:
                st.error("Invalid JSON in Process Parameters.")
            except Exception as e:
                st.error(f"Error saving recipe: {str(e)}")

# --- List Existing Recipes ---
st.divider()
st.subheader("📚 Recipe Library")

recipes = db.query(Recipe).order_by(Recipe.created_at.desc()).limit(10).all()

if recipes:
    data = []
    for r in recipes:
        data.append({
            "Name": r.name,
            "Date": r.created_at.strftime("%Y-%m-%d"),
            "Ca/Si": r.ca_si_ratio,
            "PCE (%)": r.pce_content_wt,
            "ID": str(r.id)
        })
    st.dataframe(data, use_container_width=True)
else:
    st.info("No recipes found. Create one above!")
