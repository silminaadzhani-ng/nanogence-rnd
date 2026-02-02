import streamlit as st
import datetime
import pandas as pd
import uuid
from sqlalchemy.orm import Session
from app.database import get_db, init_db
from app.models import StockSolutionBatch, RawMaterial
from app.ui_utils import display_logo

# Ensure database is synced
init_db()

st.set_page_config(page_title="Materials", page_icon="🧪", layout="wide")
display_logo()

st.markdown("# 🧪 Materials")

db: Session = next(get_db())

# Predefined Chemical Metadata (Defaults)
CHEMICALS = {
    "Ca(NO3)2·4H2O": {"mw": 236.15, "type": "Ca"},
    "Na2SiO3·5H2O": {"mw": 212.14, "type": "Si"},
    "NaOH": {"mw": 40.00, "type": "NaOH"}
}

tab_dash, tab1, tab2 = st.tabs(["📊 Dashboard", "🏛️ Raw Material Inventory", "🧪 Stock Solution Management"])

with tab_dash:
    st.subheader("Inventory Overview")
    col1, col2, col3 = st.columns(3)
    
    total_rm = db.query(RawMaterial).count()
    total_ss = db.query(StockSolutionBatch).count()
    
    col1.metric("Total Raw Materials", total_rm)
    col2.metric("Active Stock Solutions", total_ss)
    col3.metric("Last Update", datetime.date.today().strftime("%Y-%m-%d"))

    # Simple chart of stock solutions by type
    if total_ss > 0:
        ss_types = db.query(StockSolutionBatch.chemical_type).all()
        df_types = pd.DataFrame(ss_types, columns=["Type"])
        type_counts = df_types["Type"].value_counts()
        st.bar_chart(type_counts)

with tab1:
    st.subheader("Raw Material Inventory")
    
    with st.expander("📥 Log New Received Material", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            mat_name = st.selectbox("Material Name", options=list(CHEMICALS.keys()) + ["Other"])
            if mat_name == "Other":
                mat_name = st.text_input("Custom Material Name")
            
            default_mw = CHEMICALS.get(mat_name, {}).get("mw", 100.0)
            mw_input = st.number_input("Molecular Weight (hydrate basis, g/mol)", min_value=0.1, value=default_mw, format="%.2f")
            brand = st.text_input("Brand / Supplier", value="Carl Roth")
        
        with c2:
            lot = st.text_input("Lot / Batch Number")
            received_date = st.date_input("Received Date", value=datetime.date.today())
            qty = st.number_input("Initial Quantity (kg)", min_value=0.0, step=0.1, value=1.0)
            purity = st.number_input("Purity (%)", min_value=0.1, max_value=100.0, value=99.0)
        
        notes = st.text_area("Additional Notes (e.g. Storage location)")
        
        if st.button("Log Material Receipt"):
            try:
                c_type = "Other"
                if "Ca" in mat_name: c_type = "Ca"
                elif "Si" in mat_name: c_type = "Si"
                elif "PCE" in mat_name: c_type = "PCE"
                elif "NaOH" in mat_name: c_type = "NaOH"

                new_mat = RawMaterial(
                    material_name=mat_name,
                    chemical_type=c_type,
                    brand=brand,
                    lot_number=lot,
                    molecular_weight=mw_input,
                    received_date=datetime.datetime.combine(received_date, datetime.time.min),
                    initial_quantity_kg=qty,
                    remaining_quantity_kg=qty,
                    purity_percent=purity,
                    notes=notes
                )
                db.add(new_mat)
                db.commit()
                st.success(f"Logged receipt of {qty}kg {mat_name}")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {str(e)}")

    st.divider()
    materials = db.query(RawMaterial).order_by(RawMaterial.received_date.desc()).all()
    if materials:
        mat_data = []
        for m in materials:
            mat_data.append({
                "ID": str(m.id), # Keep ID for deletion logic
                "Received": m.received_date.strftime("%Y-%m-%d"),
                "Material": m.material_name,
                "Lot #": m.lot_number,
                "MW": m.molecular_weight,
                "Qty (kg)": m.remaining_quantity_kg,
                "Brand": m.brand,
            })
        
        df_materials = pd.DataFrame(mat_data)
        
        # Use built-in multi-row selection for robustness
        event = st.dataframe(
            df_materials, 
            use_container_width=True, 
            hide_index=True,
            on_select="rerun",
            selection_mode="multi-row",
            column_order=["Received", "Material", "Lot #", "MW", "Qty (kg)", "Brand"] # Hide the technical ID from the user
        )
        
        selected_row_indices = event.selection.rows
        if selected_row_indices:
            st.warning(f"⚠️ {len(selected_row_indices)} material(s) selected.")
            if st.button("🗑️ Delete Selected Materials", type="primary"):
                try:
                    deleted_count = 0
                    for idx in selected_row_indices:
                        raw_id_str = mat_data[idx]["ID"]
                        target_uuid = uuid.UUID(raw_id_str)
                        target = db.query(RawMaterial).filter(RawMaterial.id == target_uuid).first()
                        if target:
                            db.delete(target)
                            deleted_count += 1
                    db.commit()
                    st.success(f"✅ Successfully deleted {deleted_count} material(s).")
                    st.rerun()
                except Exception as e:
                    st.error(f"Deletion failed: {e}")
    else:
        st.info("No raw materials logged yet.")

with tab2:
    st.subheader("Prepare and Manage Stock Solutions")
    
    # Fetch RM options
    rm_list = db.query(RawMaterial).all()
    rm_options = {f"{m.material_name} (Lot: {m.lot_number})": str(m.id) for m in rm_list}
    
    if not rm_options:
        st.warning("Please log raw materials first to prepare stock solutions.")
    else:
        with st.expander("➕ Prepare New Batch", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                prep_date = st.date_input("Preparation Date", value=datetime.date.today(), key="prep_date")
                selected_rm_key = st.selectbox("Source Raw Material", options=list(rm_options.keys()))
                selected_rm_id_str = rm_options[selected_rm_key]
                selected_rm = db.query(RawMaterial).filter(RawMaterial.id == uuid.UUID(selected_rm_id_str)).first()
                
                target_m = st.number_input("Target Molarity (mol/L)", min_value=0.01, step=0.01, value=1.50 if "Ca" in selected_rm.chemical_type else 0.75)
                target_v = st.number_input("Target Volume (mL)", min_value=1.0, step=10.0, value=1000.0)
                
                mw = selected_rm.molecular_weight if selected_rm.molecular_weight else 100.0
                required_mass = target_m * (target_v / 1000.0) * mw / (selected_rm.purity_percent / 100.0)
                st.metric("Required Mass (g)", f"{required_mass:.2f} g")
                
            with col2:
                chem_type = selected_rm.chemical_type
                date_str = prep_date.strftime("%Y%m%d")
                prefix = f"{chem_type[:2].upper()}-{date_str}-"
                count = db.query(StockSolutionBatch).filter(StockSolutionBatch.code.like(f"{prefix}%")).count()
                suggested_code = f"{prefix}{count + 1:02d}"
                
                batch_code = st.text_input("Batch Code", value=suggested_code)
                actual_mass = st.number_input("Actual Mass Weighed (g)", step=0.01, value=required_mass)
                operator = st.text_input("Operator", value="Silmina Adzhani")
                notes = st.text_area("Notes", key="batch_notes")

            if st.button("Save Stock Batch"):
                if not batch_code:
                    st.error("Batch Code is required.")
                else:
                    try:
                        new_batch = StockSolutionBatch(
                            code=batch_code,
                            chemical_type=selected_rm.chemical_type,
                            molarity=target_m,
                            target_volume_ml=target_v,
                            actual_mass_g=actual_mass,
                            preparation_date=datetime.datetime.combine(prep_date, datetime.time.min),
                            raw_material_id=selected_rm.id,
                            operator=operator,
                            notes=notes
                        )
                        db.add(new_batch)
                        db.commit()
                        st.success(f"Batch {batch_code} saved!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

        st.divider()
        st.subheader("Active Stock Solutions")
        batches = db.query(StockSolutionBatch).order_by(StockSolutionBatch.created_at.desc()).all()
        if batches:
            ss_data = []
            for b in batches:
                source_lot = b.raw_material.lot_number if b.raw_material else "N/A"
                ss_data.append({
                    "ID": str(b.id),
                    "Code": b.code,
                    "Type": b.chemical_type,
                    "Molarity": b.molarity,
                    "Volume (mL)": b.target_volume_ml,
                    "Mass (g)": b.actual_mass_g,
                    "Source Lot": source_lot,
                    "Prep Date": b.preparation_date.strftime("%Y-%m-%d") if b.preparation_date else "N/A",
                    "Operator": b.operator
                })
            
            df_ss = pd.DataFrame(ss_data)
            event_ss = st.dataframe(
                df_ss, 
                use_container_width=True, 
                hide_index=True,
                on_select="rerun",
                selection_mode="multi-row",
                key="df_ss_table",
                column_order=["Code", "Type", "Molarity", "Volume (mL)", "Mass (g)", "Source Lot", "Prep Date", "Operator"]
            )
            
            selected_ss_indices = event_ss.selection.rows
            if selected_ss_indices:
                st.warning(f"⚠️ {len(selected_ss_indices)} batch(es) selected.")
                if st.button("🗑️ Delete Selected Batches", type="primary"):
                    try:
                        del_ss_count = 0
                        for idx in selected_ss_indices:
                            target_ss_id_str = ss_data[idx]["ID"]
                            target_ss_uuid = uuid.UUID(target_ss_id_str)
                            target = db.query(StockSolutionBatch).filter(StockSolutionBatch.id == target_ss_uuid).first()
                            if target:
                                db.delete(target)
                                del_ss_count += 1
                        db.commit()
                        st.success(f"✅ Successfully deleted {del_ss_count} batch(es).")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Deletion failed: {e}")
        else:
            st.info("No active stock solutions found.")
