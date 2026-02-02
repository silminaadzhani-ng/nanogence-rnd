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

tab1, tab2, tab3 = st.tabs(["📊 Results Library", "🚀 Log Batch", "📝 Simplified QC Entry"])

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
        library_data = []
        for trial_name, qc in results:
            library_data.append({
                "Trial #": trial_name,
                "pH": qc.ph,
                "Solids %": qc.solid_content_measured,
                "Settling": qc.settling_height,
                "V-d50 (Bef)": qc.psd_before_v_d50,
                "V-d50 (Aft)": qc.psd_after_v_d50,
                "Agg Vol": qc.agglom_vol,
                "Agg SSA": qc.agglom_ssa,
                "Ref": qc.batch.lab_notebook_ref if qc.batch else "N/A"
            })
        
        df_lib = pd.DataFrame(library_data)
        st.dataframe(df_lib, use_container_width=True)
    else:
        st.info("No experimental results recorded yet in the database.")

# --- Tab 2: Start Batch ---
with tab2:
    st.subheader("Plan Synthesis Batch")
    
    recipes = db.query(Recipe).all()
    recipe_options = {f"{r.name} (v{r.version})": r.id for r in recipes}
    
    selected_recipe_name = st.selectbox("Select Recipe for this Sample", options=list(recipe_options.keys()))
    
    if selected_recipe_name:
        batch_ref = st.text_input("Notebook / Lab Reference", placeholder="e.g. Volume 2, Page 12")
        operator = st.text_input("Operator Name", value="Silmina Adzhani")
        
        if st.button("Start Batch & Lock Reference"):
            if not batch_ref:
                st.error("Notebook Reference is mandatory for traceability.")
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
                    st.success(f"Batch {batch_ref} is now ready for QC data.")
                except Exception as e:
                    st.error(f"Error creating batch: {str(e)}")

# --- Tab 3: Detailed QC ---
with tab3:
    st.subheader("Characterization Data Entry")
    
    batches = db.query(SynthesisBatch).order_by(SynthesisBatch.execution_date.desc()).limit(50).all()
    batch_options = {f"{b.lab_notebook_ref} (Recipe: {b.recipe.name})": str(b.id) for b in batches}
    
    selected_batch_name = st.selectbox("Select Batch to enter results", options=list(batch_options.keys()), key="qc_batch_select")
    
    if selected_batch_name:
        batch_id = batch_options[selected_batch_name]
        
        with st.form("simplified_qc_form"):
            st.markdown("#### 1. General Properties")
            c1, c2, c3 = st.columns(3)
            final_ph = c1.number_input("Final pH", value=11.50)
            final_solids = c2.number_input("Final Solids content (%)", value=5.0)
            settling = c3.number_input("Settling Height (mm)", value=0.0)

            st.markdown("#### 2. Particle Size Analysis (PSD)")
            st.caption("Enter Before and After values in the grid below:")
            
            # Prepare a clean grid for PSD data
            psd_rows = ["d10 (µm)", "d50 (µm)", "d90 (µm)", "Mean (µm)", "SSA (m²/cm³)"]
            psd_cols = ["Volume (Before)", "Number (Before)", "Volume (After)", "Number (After)"]
            
            psd_init_df = pd.DataFrame(0.0, index=psd_rows, columns=psd_cols)
            
            edited_psd = st.data_editor(
                psd_init_df,
                use_container_width=True,
                key="psd_editor"
            )

            st.markdown("#### 3. Factors")
            f1, f2, f3 = st.columns(3)
            agg_v = f1.number_input("Agglom. Factor (Vol)", value=1.0)
            agg_n = f2.number_input("Agglom. Factor (Num)", value=1.0)
            agg_ssa = f3.number_input("Agglom. Factor (SSA)", value=1.0)

            if st.form_submit_button("✅ Save Characterization"):
                try:
                    # Extract from edited_psd
                    qc = QCMeasurement(
                        batch_id=batch_id,
                        ph=final_ph,
                        solid_content_measured=final_solids,
                        settling_height=settling,
                        
                        # Before Sonication (Vol)
                        psd_before_v_d10=edited_psd.at["d10 (µm)", "Volume (Before)"],
                        psd_before_v_d50=edited_psd.at["d50 (µm)", "Volume (Before)"],
                        psd_before_v_d90=edited_psd.at["d90 (µm)", "Volume (Before)"],
                        psd_before_v_mean=edited_psd.at["Mean (µm)", "Volume (Before)"],
                        psd_before_ssa=edited_psd.at["SSA (m²/cm³)", "Volume (Before)"],
                        
                        # Before Sonication (Num)
                        psd_before_n_d10=edited_psd.at["d10 (µm)", "Number (Before)"],
                        psd_before_n_d50=edited_psd.at["d50 (µm)", "Number (Before)"],
                        psd_before_n_d90=edited_psd.at["d90 (µm)", "Number (Before)"],
                        psd_before_n_mean=edited_psd.at["Mean (µm)", "Number (Before)"],

                        # After Sonication (Vol)
                        psd_after_v_d10=edited_psd.at["d10 (µm)", "Volume (After)"],
                        psd_after_v_d50=edited_psd.at["d50 (µm)", "Volume (After)"],
                        psd_after_v_d90=edited_psd.at["d90 (µm)", "Volume (After)"],
                        psd_after_v_mean=edited_psd.at["Mean (µm)", "Volume (After)"],
                        psd_after_ssa=edited_psd.at["SSA (m²/cm³)", "Volume (After)"],

                        # After Sonication (Num)
                        psd_after_n_d10=edited_psd.at["d10 (µm)", "Number (After)"],
                        psd_after_n_d50=edited_psd.at["d50 (µm)", "Number (After)"],
                        psd_after_n_d90=edited_psd.at["d90 (µm)", "Number (After)"],
                        psd_after_n_mean=edited_psd.at["Mean (µm)", "Number (After)"],

                        agglom_vol=agg_v,
                        agglom_num=agg_n,
                        agglom_ssa=agg_ssa
                    )
                    db.add(qc)
                    db.commit()
                    st.success(f"Characterization data saved for {selected_batch_name}!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Critical entry error: {e}")
