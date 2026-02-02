import streamlit as st
import datetime
import pandas as pd
import uuid
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

tab_dash, tab1, tab2 = st.tabs(["📊 Dashboard", "📊 Results Library", "📝 Record Characterization"])

# --- Dashboard Tab ---
with tab_dash:
    st.subheader("Synthesis Analytics")
    col1, col2, col3 = st.columns(3)
    
    total_batches = db.query(SynthesisBatch).count()
    total_qc = db.query(QCMeasurement).count()
    avg_ph = db.query(st.func.avg(QCMeasurement.ph)).scalar() or 0
    
    col1.metric("Total Batches", total_batches)
    col2.metric("QC Entries", total_qc)
    col3.metric("Avg Trial pH", f"{avg_ph:.2f}")

    if total_qc > 0:
        qc_data = db.query(QCMeasurement.ph, QCMeasurement.solid_content_measured).all()
        df_qc = pd.DataFrame(qc_data, columns=["pH", "Solids (%)"])
        st.subheader("pH vs Solids Distribution")
        st.scatter_chart(df_qc, x="pH", y="Solids (%)")

# --- Results Library Tab ---
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
                "Ref": qc.batch.lab_notebook_ref if qc.batch else "N/A"
            })
        
        df_lib = pd.DataFrame(library_data)
        st.dataframe(df_lib, use_container_width=True)
    else:
        st.info("No experimental results recorded yet.")

# --- Record Characterization Tab (New Workflow) ---
with tab2:
    st.subheader("1. Select Recipe from Library")
    
    # Show Recipe Table
    recipes = db.query(Recipe).order_by(Recipe.name.asc()).all()
    recipe_table_data = []
    for r in recipes:
        recipe_table_data.append({
            "ID": str(r.id),
            "Name": r.name,
            "Ca/Si": r.ca_si_ratio,
            "Solids %": r.total_solid_content,
            "Created": r.recipe_date.strftime("%Y-%m-%d") if r.recipe_date else "N/A"
        })
    
    df_recipes = pd.DataFrame(recipe_table_data)
    
    # Use st.dataframe for selection
    recipe_selection = st.dataframe(
        df_recipes,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_order=["Name", "Ca/Si", "Solids %", "Created"]
    )
    
    selected_indices = recipe_selection.selection.rows
    
    if selected_indices:
        idx = selected_indices[0]
        sel_recipe_id = recipe_table_data[idx]["ID"]
        sel_recipe_name = recipe_table_data[idx]["Name"]
        
        st.success(f"Selected: **{sel_recipe_name}**")
        
        st.divider()
        st.subheader("2. Batch Reference & QC Entry")
        
        with st.form("characterization_form"):
            col_a, col_b = st.columns(2)
            batch_ref = col_a.text_input("Notebook / Lab Reference", value=f"NB-{sel_recipe_name}-{datetime.date.today().strftime('%Y%m%d')}")
            operator = col_b.text_input("Operator Name", value="Silmina Adzhani")
            
            st.markdown("#### General Properties")
            c1, c2, c3 = st.columns(3)
            final_ph = c1.number_input("Final pH", value=11.50)
            final_solids = c2.number_input("Final Solids content (%)", value=5.0)
            settling = c3.number_input("Settling Height (mm)", value=0.0)

            st.markdown("#### Particle Size Analysis (PSD)")
            st.caption("Enter values in the grid below:")
            
            psd_rows = ["d10 (µm)", "d50 (µm)", "d90 (µm)", "Mean (µm)", "SSA (m²/cm³)"]
            psd_cols = ["Volume (Before)", "Number (Before)", "Volume (After)", "Number (After)"]
            psd_init_df = pd.DataFrame(0.0, index=psd_rows, columns=psd_cols)
            
            edited_psd = st.data_editor(psd_init_df, use_container_width=True, key="psd_editor_new")

            if st.form_submit_button("✅ Save Characterization for this Recipe"):
                if not batch_ref:
                    st.error("Notebook Reference is required.")
                else:
                    try:
                        # 1. Create the SynthesisBatch (or find existing one with same ref)
                        target_recipe_uuid = uuid.UUID(sel_recipe_id)
                        batch = db.query(SynthesisBatch).filter(
                            SynthesisBatch.recipe_id == target_recipe_uuid,
                            SynthesisBatch.lab_notebook_ref == batch_ref
                        ).first()
                        
                        if not batch:
                            batch = SynthesisBatch(
                                recipe_id=target_recipe_uuid,
                                lab_notebook_ref=batch_ref,
                                operator=operator,
                                status="Completed",
                                execution_date=datetime.datetime.utcnow()
                            )
                            db.add(batch)
                            db.flush() # Get the batch ID
                        
                        # 2. Save QC Measurement
                        qc = QCMeasurement(
                            batch_id=batch.id,
                            ph=final_ph,
                            solid_content_measured=final_solids,
                            settling_height=settling,
                            
                            psd_before_v_d10=edited_psd.at["d10 (µm)", "Volume (Before)"],
                            psd_before_v_d50=edited_psd.at["d50 (µm)", "Volume (Before)"],
                            psd_before_v_d90=edited_psd.at["d90 (µm)", "Volume (Before)"],
                            psd_before_v_mean=edited_psd.at["Mean (µm)", "Volume (Before)"],
                            psd_before_ssa=edited_psd.at["SSA (m²/cm³)", "Volume (Before)"],
                            
                            psd_before_n_d10=edited_psd.at["d10 (µm)", "Number (Before)"],
                            psd_before_n_d50=edited_psd.at["d50 (µm)", "Number (Before)"],
                            psd_before_n_d90=edited_psd.at["d90 (µm)", "Number (Before)"],
                            psd_before_n_mean=edited_psd.at["Mean (µm)", "Number (Before)"],

                            psd_after_v_d10=edited_psd.at["d10 (µm)", "Volume (After)"],
                            psd_after_v_d50=edited_psd.at["d50 (µm)", "Volume (After)"],
                            psd_after_v_d90=edited_psd.at["d90 (µm)", "Volume (After)"],
                            psd_after_v_mean=edited_psd.at["Mean (µm)", "Volume (After)"],
                            psd_after_ssa=edited_psd.at["SSA (m²/cm³)", "Volume (After)"],

                            psd_after_n_d10=edited_psd.at["d10 (µm)", "Number (After)"],
                            psd_after_n_d50=edited_psd.at["d50 (µm)", "Number (After)"],
                            psd_after_n_d90=edited_psd.at["d90 (µm)", "Number (After)"],
                            psd_after_n_mean=edited_psd.at["Mean (µm)", "Number (After)"]
                        )
                        db.add(qc)
                        db.commit()
                        st.success(f"Results successfully linked to Recipe: {sel_recipe_name}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error saving results: {e}")
    else:
        st.info("👆 Please click a Recipe name in the table above to start entering characterization results.")
