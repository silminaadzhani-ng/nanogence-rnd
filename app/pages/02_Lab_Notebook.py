import streamlit as st
import datetime
import json
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Recipe, SynthesisBatch, QCMeasurement

st.set_page_config(page_title="Lab Notebook", page_icon="🧪", layout="wide")

st.markdown("# 🧪 Lab Notebook & QC")

db: Session = next(get_db())

tab1, tab2 = st.tabs(["🚀 Start New Batch", "📊 Enter QC Data"])

# --- Tab 1: Start Batch ---
with tab1:
    st.subheader("Plan Synthesis Batch")
    
    recipes = db.query(Recipe).all()
    recipe_options = {f"{r.name} (v{r.version})": r.id for r in recipes}
    
    selected_recipe_name = st.selectbox("Select Recipe", options=list(recipe_options.keys()))
    
    if selected_recipe_name:
        batch_ref = st.text_input("Lab Notebook Reference", placeholder="e.g. NB-2024-001")
        operator = st.text_input("Operator Name", value="Lab Tech")
        
        if st.button("Start Batch"):
            if not batch_ref:
                st.error("Notebook Reference is required.")
            else:
                try:
                    new_batch = SynthesisBatch(
                        recipe_id=recipe_options[selected_recipe_name],
                        lab_notebook_ref=batch_ref,
                        operator=operator,
                        status="Completed", # Auto-complete for MVP speed
                        execution_date=datetime.datetime.utcnow()
                    )
                    db.add(new_batch)
                    db.commit()
                    st.success(f"Batch {batch_ref} created!")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

# --- Tab 2: QC Data ---
with tab2:
    st.subheader("Record Quality Control Data")
    
    # Fetch recent batches
    batches = db.query(SynthesisBatch).order_by(SynthesisBatch.execution_date.desc()).limit(20).all()
    batch_options = {f"{b.lab_notebook_ref} ({b.execution_date.strftime('%Y-%m-%d %H:%M')})": b.id for b in batches}
    
    selected_batch_name = st.selectbox("Select Synthesis Batch", options=list(batch_options.keys()))
    
    if selected_batch_name:
        batch_id = batch_options[selected_batch_name]
        
        with st.form("qc_form"):
            st.markdown("#### 1. General Properties")
            c1, c2, c3 = st.columns(3)
            ageing = c1.number_input("Ageing Time (hours)", value=24.0)
            ph = c2.number_input("pH Value", min_value=0.0, max_value=14.0, step=0.1, value=11.5)
            solids = c3.number_input("Solid Content (%)", step=0.1, value=5.0)
            
            st.markdown("#### 2. PSD (Particle Size Distribution)")
            
            c_bef, c_aft = st.columns(2)
            
            with c_bef:
                st.caption("Before Sonication (Volume)")
                d10_b = st.number_input("D10 (µm) - Before", step=0.1)
                d50_b = st.number_input("D50 (µm) - Before", step=0.1)
                d90_b = st.number_input("D90 (µm) - Before", step=0.1)
            
            with c_aft:
                st.caption("After Sonication (Volume)")
                d10_a = st.number_input("D10 (µm) - After", step=0.1)
                d50_a = st.number_input("D50 (µm) - After", step=0.1)
                d90_a = st.number_input("D90 (µm) - After", step=0.1)
            
            notes = st.text_area("Notes / Comments", placeholder="e.g. Gelified overnight...")
            
            if st.form_submit_button("Save QC Data"):
                # Construct complex JSON for psd_data
                psd_payload = {
                    "before_sonication": {"d10": d10_b, "d50": d50_b, "d90": d90_b},
                    "after_sonication": {"d10": d10_a, "d50": d50_a, "d90": d90_a}
                }
                
                qc = QCMeasurement(
                    batch_id=batch_id,
                    ageing_time=ageing,
                    ph=ph,
                    solid_content_measured=solids,
                    psd_data=psd_payload,
                    notes=notes
                )
                db.add(qc)
                db.commit()
                st.balloons()
                st.success("QC Data Saved")
