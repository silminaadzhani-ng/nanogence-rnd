import streamlit as st
import datetime
import pandas as pd
from sqlalchemy.orm import Session
from app.database import get_db, init_db
from app.models import Recipe, SynthesisBatch, QCMeasurement
from app.ui_utils import display_logo

# Ensure database is synced
init_db()

st.set_page_config(page_title="Results", page_icon="🧪", layout="wide")
display_logo()

st.markdown("# 🧪 Synthesis Results & Characterization")

db: Session = next(get_db())

tab1, tab2, tab3 = st.tabs(["📊 Results Library", "🚀 Log Batch", "📝 Detailed QC Entry"])

# --- Tab 1: Results Library ---
with tab1:
    st.subheader("Synthesis Characterization Table")
    
    # Query all results linking Recipe -> Batch -> QC
    query = db.query(
        Recipe.name.label("Trial"),
        QCMeasurement
    ).join(SynthesisBatch, Recipe.id == SynthesisBatch.recipe_id)\
     .join(QCMeasurement, SynthesisBatch.id == QCMeasurement.batch_id)\
     .order_by(Recipe.name.asc())
    
    results = query.all()
    
    if results:
        data = []
        for trial_name, qc in results:
            data.append({
                "Trial #": trial_name,
                "d10_v_bef": qc.psd_before_v_d10,
                "d50_v_bef": qc.psd_before_v_d50,
                "d90_v_bef": qc.psd_before_v_d90,
                "mean_v_bef": qc.psd_before_v_mean,
                "d10_v_aft": qc.psd_after_v_d10,
                "d50_v_aft": qc.psd_after_v_d50,
                "d90_v_aft": qc.psd_after_v_d90,
                "mean_v_aft": qc.psd_after_v_mean,
                "Agg_Vol": qc.agglom_vol,
                "Agg_SSA": qc.agglom_ssa,
                "pH": qc.ph,
                "Solids %": qc.solid_content_measured,
                "Settling": qc.settling_height,
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No results recorded yet.")

# --- Tab 2: Start Batch ---
with tab2:
    st.subheader("Plan Synthesis Batch")
    
    recipes = db.query(Recipe).all()
    recipe_options = {f"{r.name} (v{r.version})": r.id for r in recipes}
    
    selected_recipe_name = st.selectbox("Select Recipe", options=list(recipe_options.keys()))
    
    if selected_recipe_name:
        batch_ref = st.text_input("Lab Notebook Reference", placeholder="e.g. NB-2024-001")
        operator = st.text_input("Operator Name", value="Silmina Adzhani")
        
        if st.button("Start Batch"):
            if not batch_ref:
                st.error("Notebook Reference is required.")
            else:
                try:
                    new_batch = SynthesisBatch(
                        recipe_id=recipe_options[selected_recipe_name],
                        lab_notebook_ref=batch_ref,
                        operator=operator,
                        status="Completed",
                        execution_date=datetime.datetime.utcnow()
                    )
                    db.add(new_batch)
                    db.commit()
                    st.success(f"Batch {batch_ref} created!")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

# --- Tab 3: Detailed QC ---
with tab3:
    st.subheader("Record Full Characterization Data")
    
    batches = db.query(SynthesisBatch).order_by(SynthesisBatch.execution_date.desc()).limit(50).all()
    batch_options = {f"{b.lab_notebook_ref} (Recipe: {b.recipe.name})": b.id for b in batches}
    
    selected_batch_name = st.selectbox("Select Synthesis Batch", options=list(batch_options.keys()), key="qc_batch_select")
    
    if selected_batch_name:
        batch_id = batch_options[selected_batch_name]
        
        with st.form("detailed_qc_form"):
            st.markdown("### 1. pH & Solids")
            c1, c2, c3 = st.columns(3)
            final_ph = c1.number_input("Final pH", step=0.01, value=11.5)
            final_solids = c2.number_input("Final Solids (%)", step=0.01)
            settling = c3.number_input("Settling Height (mm)", step=0.1)

            st.markdown("### 2. Particle Size Distribution (PSD)")
            st.info("Record D10, D50, D90, and Mean for both Volume and Number distributions.")
            
            # --- Before Sonication ---
            st.markdown("#### A. Before Sonication")
            v1, v2, v3, v4, v5 = st.columns(5)
            d10_vb = v1.number_input("V-D10 (bef)", step=0.01)
            d50_vb = v2.number_input("V-D50 (bef)", step=0.01)
            d90_vb = v3.number_input("V-D90 (bef)", step=0.01)
            mean_vb = v4.number_input("V-Mean (bef)", step=0.01)
            ssa_b = v5.number_input("SSA (bef)", step=0.01)

            n1, n2, n3, n4 = st.columns(4)
            d10_nb = n1.number_input("N-D10 (bef)", step=0.01)
            d50_nb = n2.number_input("N-D50 (bef)", step=0.01)
            d90_nb = n3.number_input("N-D90 (bef)", step=0.01)
            mean_nb = n4.number_input("N-Mean (bef)", step=0.01)

            # --- After Sonication ---
            st.markdown("#### B. After Sonication")
            av1, av2, av3, av4, av5 = st.columns(5)
            d10_va = av1.number_input("V-D10 (aft)", step=0.01)
            d50_va = av2.number_input("V-D50 (aft)", step=0.01)
            d90_va = av3.number_input("V-D90 (aft)", step=0.01)
            mean_va = av4.number_input("V-Mean (aft)", step=0.01)
            ssa_a = av5.number_input("SSA (aft)", step=0.01)

            an1, an2, an3, an4 = st.columns(4)
            d10_na = an1.number_input("N-D10 (aft)", step=0.01)
            d50_na = an2.number_input("N-D50 (aft)", step=0.01)
            d90_na = an3.number_input("N-D90 (aft)", step=0.01)
            mean_na = an4.number_input("N-Mean (aft)", step=0.01)

            st.markdown("### 3. Agglomeration Factors")
            af1, af2, af3 = st.columns(3)
            agg_v = af1.number_input("Agglom. Factor (Vol)", step=0.01)
            agg_n = af2.number_input("Agglom. Factor (Num)", step=0.01)
            agg_ssa = af3.number_input("Agglom. Factor (SSA)", step=0.01)

            if st.form_submit_button("💾 Save characterization"):
                qc = QCMeasurement(
                    batch_id=batch_id,
                    ph=final_ph,
                    solid_content_measured=final_solids,
                    settling_height=settling,
                    psd_before_v_d10=d10_vb, psd_before_v_d50=d50_vb, psd_before_v_d90=d90_vb, psd_before_v_mean=mean_vb,
                    psd_before_n_d10=d10_nb, psd_before_n_d50=d50_nb, psd_before_n_d90=d90_nb, psd_before_n_mean=mean_nb,
                    psd_before_ssa=ssa_b,
                    psd_after_v_d10=d10_va, psd_after_v_d50=d50_va, psd_after_v_d90=d90_va, psd_after_v_mean=mean_va,
                    psd_after_n_d10=d10_na, psd_after_n_d50=d50_na, psd_after_n_d90=d90_na, psd_after_n_mean=mean_na,
                    psd_after_ssa=ssa_a,
                    agglom_vol=agg_v, agglom_num=agg_n, agglom_ssa=agg_ssa
                )
                db.add(qc)
                db.commit()
                st.success("Results updated successfully!")
                st.rerun()
