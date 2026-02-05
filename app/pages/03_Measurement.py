import streamlit as st
import datetime
import pandas as pd
import uuid
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db, init_db
from app.models import Recipe, SynthesisBatch, QCMeasurement
from app.ui_utils import display_logo

# Ensure database is synced
init_db()

st.set_page_config(page_title="Measurement", page_icon="🧪", layout="wide")
display_logo()

st.markdown("# 🧪 Measurement")

db: Session = next(get_db())

tab_dash, tab1, tab2 = st.tabs(["📊 Dashboard", "📊 Measurement Library", "📝 Record Measurement"])

# --- Dashboard Tab ---
with tab_dash:
    st.subheader("Measurement Analytics")
    col1, col2, col3 = st.columns(3)
    
    total_batches = db.query(SynthesisBatch).count()
    total_qc = db.query(QCMeasurement).count()
    avg_ph = db.query(func.avg(QCMeasurement.ph)).scalar() or 0
    
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
    st.subheader("Measurement Library")
    
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
                "Settling (mm)": qc.settling_height,
                "Age (h)": qc.ageing_time if qc.ageing_time else 0.0,
                "V-d10 (µm, Bef)": qc.psd_before_v_d10,
                "V-d50 (µm, Bef)": qc.psd_before_v_d50,
                "V-d90 (µm, Bef)": qc.psd_before_v_d90,
                "V-Mean (µm, Bef)": qc.psd_before_v_mean,
                "V-d50 (µm, Aft)": qc.psd_after_v_d50,
                "Final Form": qc.custom_metrics.get("final_form", "N/A") if qc.custom_metrics else "N/A",
                "Measured At": qc.measured_at.strftime("%Y-%m-%d %H:%M") if qc.measured_at else "N/A",
                "Measurement ID": qc.batch.lab_notebook_ref if qc.batch else "N/A"
            })
        
        df_lib = pd.DataFrame(library_data)
        
        # Table View with Selection
        selection_event = st.dataframe(
            df_lib[["Measurement ID", "Trial #", "Age (h)", "pH", "Solids %", "V-d50 (µm, Bef)", "Final Form"]], 
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="multi-row",
            key="lib_selection"
        )
        
        selected_rows = selection_event.selection.rows
        df_selected = df_lib.iloc[selected_rows] if selected_rows else df_lib.head(5)

        # Visualization Section
        st.divider()
        st.subheader("📊 Results Comparison")
        
        viz_col1, viz_col2 = st.columns([3, 1])
        
        with viz_col1:
            st.info(f"Showing comparison for **{len(df_selected)}** selected measurement(s).")
            
        with viz_col2:
            metric_options = ["pH", "Solids %", "Settling (mm)", "V-d10 (µm, Bef)", "V-d50 (µm, Bef)", "V-d90 (µm, Bef)", "V-Mean (µm, Bef)", "V-d50 (µm, Aft)"]
            selected_metric = st.selectbox("Select Metric to Compare", options=metric_options, key="viz_metric")
            
        if not df_selected.empty:
            # --- Chart ---
            import plotly.express as px
            fig = px.bar(
                df_selected, 
                x="Measurement ID", 
                y=selected_metric,
                color="Trial #",
                title=f"Comparison: {selected_metric}",
                text_auto='.2f',
                template="plotly_white",
                hover_data=["Age (h)", "Trial #"]
            )
            fig.update_layout(showlegend=True, legend_title_text="Trials")
            st.plotly_chart(fig, use_container_width=True)

            # --- Pivoted Comparison Table ---
            st.subheader("📋 Detailed Comparison (Pivoted)")
            # Metrics to include in pivot
            pivot_metrics = ["Trial #", "Measurement ID", "Age (h)", "pH", "Solids %", "V-d10 (µm, Bef)", "V-d50 (µm, Bef)", "V-d90 (µm, Bef)", "V-Mean (µm, Bef)", "Final Form"]
            
            # Create pivoted view: Metrics as Index, Measurement IDs as Columns
            df_display = df_selected[pivot_metrics].copy()
            
            # Handle duplicate Measurement IDs to prevent crash
            counts = df_display["Measurement ID"].value_counts()
            duplicates = counts[counts > 1].index.tolist()
            
            if duplicates:
                counter = {}
                def make_unique(name):
                    if name in duplicates:
                        counter[name] = counter.get(name, 0) + 1
                        return f"{name} ({counter[name]})"
                    return name
                df_display["Measurement ID"] = df_display["Measurement ID"].apply(make_unique)

            df_pivot = df_display.set_index("Measurement ID").T
            st.dataframe(df_pivot, use_container_width=True)
        else:
            st.warning("Please select at least one row from the table above to compare.")
    else:
        st.info("No experimental results recorded yet.")

# --- Record Characterization Tab ---
with tab2:
    st.subheader("1. Select Recipe from Library")
    
    # Recipe Search Bar
    search_query = st.text_input("🔍 Search Recipe Name", placeholder="e.g. Trial A1", key="recipe_search_qc")

    query = db.query(Recipe).order_by(Recipe.name.asc())
    if search_query:
        query = query.filter(Recipe.name.ilike(f"%{search_query}%"))
    
    recipes = query.all()
    recipe_table_data = []
    for r in recipes:
        recipe_table_data.append({
            "ID": str(r.id),
            "Code": r.code if r.code else "N/A",
            "Name": r.name,
            "Created": r.recipe_date.strftime("%Y-%m-%d %H:%M") if r.recipe_date else "N/A",
            "Recipe_Date_Obj": r.recipe_date
        })
    
    df_recipes = pd.DataFrame(recipe_table_data)
    
    recipe_selection = st.dataframe(
        df_recipes,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_order=["Name", "Code", "Created"]
    )
    
    selected_indices = recipe_selection.selection.rows
    
    if selected_indices:
        idx = selected_indices[0]
        sel_recipe_id = recipe_table_data[idx]["ID"]
        sel_recipe_code = recipe_table_data[idx]["Code"]
        sel_recipe_name = recipe_table_data[idx]["Name"]
        sel_recipe_date = recipe_table_data[idx]["Recipe_Date_Obj"]
        
        st.success(f"Selected Recipe: **{sel_recipe_code}** - {sel_recipe_name} (Created: {sel_recipe_date.strftime('%Y-%m-%d %H:%M') if sel_recipe_date else 'N/A'})")
        
        st.divider()
        st.subheader("2. Measurement entry")
        
        c_time1, c_time2 = st.columns(2)
        measurement_date = c_time1.date_input("Measurement Date", value=datetime.date.today())
        age_h = c_time2.number_input("Ageing Time (hours)", min_value=0.0, step=0.5, value=0.0, help="Unique ageing point for this measurement.")
        
        with st.form("characterization_form"):
            c_meta1, c_meta2 = st.columns(2)
            # Default ID now includes age to ensure uniqueness per requirement
            batch_ref = c_meta1.text_input("Measurement ID", value=f"NB-{sel_recipe_code}-{age_h}h")
            operator = c_meta2.text_input("Operator Name", value="Silmina Adzhani")
            
            measurement_ts = datetime.datetime.combine(measurement_date, datetime.datetime.now().time())

            st.markdown("#### General Properties")
            c1, c2, c3, c4 = st.columns(4)
            final_form = c1.selectbox("Final Form", ["Suspension", "Gelified", "Precipitate", "Other"])
            final_ph = c2.number_input("Final pH", value=11.50)
            final_solids = c3.number_input("Final Solids content (%)", value=5.0)
            settling = c4.number_input("Settling Height (mm)", value=0.0)

            st.markdown("#### Particle Size Analysis (PSD)")
            psd_rows = ["d10 (µm)", "d50 (µm)", "d90 (µm)", "Mean (µm)", "SSA (m²/cm³)"]
            psd_cols = ["Volume (Before)", "Number (Before)", "Volume (After)", "Number (After)"]
            psd_init_df = pd.DataFrame(0.0, index=psd_rows, columns=psd_cols)
            edited_psd = st.data_editor(psd_init_df, use_container_width=True, key="psd_editor_age")

            if st.form_submit_button("✅ Save Measurement"):
                if not batch_ref:
                    st.error("Reference is required.")
                else:
                    try:
                        target_recipe_uuid = uuid.UUID(sel_recipe_id)
                        # Ensure batch exists
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
                                execution_date=sel_recipe_date # Baseline
                            )
                            db.add(batch)
                            db.flush()
                        
                        # Save QC
                        qc = QCMeasurement(
                            batch_id=batch.id,
                            measured_at=measurement_ts,
                            ageing_time=age_h,
                            ph=final_ph,
                            solid_content_measured=final_solids,
                            settling_height=settling,
                            
                            psd_before_v_d10=float(edited_psd.at["d10 (µm)", "Volume (Before)"]),
                            psd_before_v_d50=float(edited_psd.at["d50 (µm)", "Volume (Before)"]),
                            psd_before_v_d90=float(edited_psd.at["d90 (µm)", "Volume (Before)"]),
                            psd_before_v_mean=float(edited_psd.at["Mean (µm)", "Volume (Before)"]),
                            psd_before_ssa=float(edited_psd.at["SSA (m²/cm³)", "Volume (Before)"]),
                            
                            psd_before_n_d10=float(edited_psd.at["d10 (µm)", "Number (Before)"]),
                            psd_before_n_d50=float(edited_psd.at["d50 (µm)", "Number (Before)"]),
                            psd_before_n_d90=float(edited_psd.at["d90 (µm)", "Number (Before)"]),
                            psd_before_n_mean=float(edited_psd.at["Mean (µm)", "Number (Before)"]),

                            psd_after_v_d10=float(edited_psd.at["d10 (µm)", "Volume (After)"]),
                            psd_after_v_d50=float(edited_psd.at["d50 (µm)", "Volume (After)"]),
                            psd_after_v_d90=float(edited_psd.at["d90 (µm)", "Volume (After)"]),
                            psd_after_v_mean=float(edited_psd.at["Mean (µm)", "Volume (After)"]),
                            psd_after_ssa=float(edited_psd.at["SSA (m²/cm³)", "Volume (After)"]),

                            psd_after_n_d10=float(edited_psd.at["d10 (µm)", "Number (After)"]),
                            psd_after_n_d50=float(edited_psd.at["d50 (µm)", "Number (After)"]),
                            psd_after_n_d90=float(edited_psd.at["d90 (µm)", "Number (After)"]),
                            psd_after_n_mean=float(edited_psd.at["Mean (µm)", "Number (After)"]),
                            custom_metrics={"final_form": final_form}
                        )
                        db.add(qc)
                        db.commit()
                        st.success(f"Results saved. Sample Age: {age_h:.1f} hours.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
    else:
        st.info("👆 Select a Recipe trial to log measurement timeline.")
