import streamlit as st
import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Recipe, StockSolutionBatch
from app.ml_utils import predict_strength

st.set_page_config(page_title="Recipe Designer", page_icon="📝", layout="wide")

st.markdown("# 📝 Experimental Recipe Designer")

db: Session = next(get_db())

# --- Sidebar: AI Prediction ---
with st.sidebar:
    st.header("🧠 AI Predictor")
    st.info("Adjust parameters to see estimated 28d Strength.")

with st.expander("ℹ️  Instructions", expanded=False):
    st.info("Define the chemical composition, stock solutions, and synthesis process steps.")

# --- Form for Recipe Inputs ---
with st.form("recipe_form"):
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Chemical Composition")
        r_date = st.date_input("Recipe Date", value=datetime.today())
        name = st.text_input("Recipe Name", placeholder="e.g. CSH-Seed-Standard-2024")
        
        c1, c2 = st.columns(2)
        ca_si = c1.number_input("Ca/Si Ratio", min_value=0.5, max_value=2.5, step=0.05, value=1.0)
        solids = c2.number_input("Total Solid Content (%)", min_value=1.0, max_value=50.0, value=10.0)
        
        c3, c4 = st.columns(2)
        m_ca = c3.number_input("Ca Molarity (mol/L)", min_value=0.1, max_value=5.0, step=0.1, value=1.5)
        m_si = c4.number_input("Si Molarity (mol/L)", min_value=0.1, max_value=5.0, step=0.1, value=0.75)
        
        pce = st.number_input("PCE Content (wt.%)", min_value=0.0, max_value=5.0, step=0.1, value=0.5)
        
        st.subheader("🧪 Stock Solution Source")
        # Fetch available batches
        ca_batches = db.query(StockSolutionBatch).filter(StockSolutionBatch.chemical_type == "Ca").all()
        si_batches = db.query(StockSolutionBatch).filter(StockSolutionBatch.chemical_type == "Si").all()
        
        ca_opts = {f"{b.code} ({b.molarity}M)": b.id for b in ca_batches}
        si_opts = {f"{b.code} ({b.molarity}M)": b.id for b in si_batches}
        
        ca_batch_id = st.selectbox("Ca Stock Batch", options=["None"] + list(ca_opts.keys()))
        si_batch_id = st.selectbox("Si Stock Batch", options=["None"] + list(si_opts.keys()))

    with col2:
        st.subheader("Process Parameters")
        c1, c2 = st.columns(2)
        rate_ca = c1.number_input("Ca Addition Rate (mL/min)", value=0.5)
        rate_si = c2.number_input("Si Addition Rate (mL/min)", value=0.5)
        
        st.caption("Synthesis Procedure")
        default_steps = [
            {"step": 1, "description": "Dissolve PCX in DI water", "duration_min": 10},
            {"step": 2, "description": "Adjust pH with NaOH", "duration_min": 5},
            {"step": 3, "description": "Start simultaneous dropwise addition", "duration_min": 60}
        ]
        sequence_json = st.text_area("Procedure Steps (JSON)", value=json.dumps(default_steps, indent=2), height=150)
        
        # Prediction
        pred = predict_strength(ca_si, m_ca, solids, pce)
        if pred:
            st.metric(label="Predicted 28d Strength", value=f"{pred:.1f} MPa")

    submitted = st.form_submit_button("💾 Save Recipe")

    if submitted:
        if not name:
            st.error("Recipe Name is required.")
        else:
            try:
                proc_config = {"steps": json.loads(sequence_json)}
                new_recipe = Recipe(
                    name=name,
                    recipe_date=datetime.combine(r_date, datetime.min.time()),
                    ca_si_ratio=ca_si,
                    molarity_ca_no3=m_ca,
                    molarity_na2sio3=m_si,
                    total_solid_content=solids,
                    pce_content_wt=pce,
                    ca_addition_rate=rate_ca,
                    si_addition_rate=rate_si,
                    ca_stock_batch_id=ca_opts.get(ca_batch_id),
                    si_stock_batch_id=si_opts.get(si_batch_id),
                    process_config=proc_config,
                    created_by="Silmina Adzhani"
                )
                db.add(new_recipe)
                db.commit()
                st.success(f"Recipe '{name}' saved!")
            except Exception as e:
                st.error(f"Error: {str(e)}")

# --- List Recipes ---
st.divider()
st.subheader("📚 Recipe Library")
recipes = db.query(Recipe).order_by(Recipe.created_at.desc()).all()
if recipes:
    data = []
    for r in recipes:
        data.append({
            "Name": r.name,
            "Date": r.recipe_date.strftime("%Y-%m-%d") if r.recipe_date else "N/A",
            "Ca/Si": r.ca_si_ratio,
            "Ca Add. Rate": r.ca_addition_rate,
            "Si Add. Rate": r.si_addition_rate
        })
    st.dataframe(data, use_container_width=True)
