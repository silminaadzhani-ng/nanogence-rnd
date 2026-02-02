import streamlit as st
import datetime
from sqlalchemy.orm import Session
from app.database import get_db, init_db
from app.models import StockSolutionBatch, RawMaterial

# Ensure database is synced
init_db()

st.set_page_config(page_title="Raw Materials & Stock Solutions", page_icon="🧪", layout="wide")

st.markdown("# 🧪 Raw materials and stock solution management")

db: Session = next(get_db())

# Predefined Chemical Metadata
CHEMICALS = {
    "Ca(NO3)2·4H2O": {"mw": 236.15, "type": "Ca"},
    "Na2SiO3·5H2O": {"mw": 212.14, "type": "Si"},
    "NaOH": {"mw": 40.00, "type": "NaOH"}
}

tab1, tab2, tab3 = st.tabs(["🏛️ Raw Material Inventory", "➕ Prepare Stock Solution", "📚 Stock Solution Library"])

with tab1:
    st.subheader("Manage Raw Materials")
    
    with st.expander("📥 Log New Received Material", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            mat_name = st.selectbox("Material Name", options=list(CHEMICALS.keys()) + ["Other"])
            if mat_name == "Other":
                mat_name = st.text_input("Custom Material Name")
            
            brand = st.text_input("Brand / Supplier", value="Carl Roth")
            lot = st.text_input("Lot / Batch Number")
        
        with c2:
            received_date = st.date_input("Received Date", value=datetime.date.today())
            qty = st.number_input("Initial Quantity (kg)", min_value=0.0, step=0.1, value=1.0)
            purity = st.number_input("Purity (%)", min_value=0.1, max_value=100.0, value=99.0)
        
        notes = st.text_area("Additional Notes (e.g. Storage location)")
        
        if st.button("Log Material Receipt"):
            try:
                # Basic chem types
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
    st.subheader("Current Raw Material Stock")
    materials = db.query(RawMaterial).order_by(RawMaterial.received_date.desc()).all()
    if materials:
        mat_data = []
        for m in materials:
            mat_data.append({
                "Received": m.received_date.strftime("%Y-%m-%d"),
                "Material": m.material_name,
                "Brand": m.brand,
                "Lot #": m.lot_number,
                "Qty (kg)": m.remaining_quantity_kg,
                "Purity %": m.purity_percent
            })
        st.dataframe(mat_data, use_container_width=True)
    else:
        st.info("No raw materials logged yet.")

with tab2:
    st.subheader("Prepare Stock Solution")
    
    col1, col2 = st.columns(2)
    
    with col1:
        prep_date = st.date_input("Preparation Date", value=datetime.date.today(), key="prep_date")
        
        chem_options = list(CHEMICALS.keys()) + ["Other (Custom)"]
        selected_chem = st.selectbox("Chemical", options=chem_options, key="prep_chem")
        
        custom_name = ""
        custom_mw = 0.0
        
        if selected_chem == "Other (Custom)":
            custom_name = st.text_input("Chemical Name", placeholder="e.g. Al2(SO4)3")
            custom_mw = st.number_input("MW-hydrate (g/mol)", min_value=1.0, step=0.01, value=100.0)
            target_m = st.number_input("Target Molarity (mol/L)", min_value=0.01, step=0.01, value=1.0)
            mw = custom_mw
            chem_type = "Other"
        else:
            target_m = st.number_input("Target Molarity (mol/L)", min_value=0.01, step=0.01, value=1.50 if "Ca" in selected_chem else (0.75 if "Si" in selected_chem else 5.0))
            mw = CHEMICALS[selected_chem]["mw"]
            chem_type = CHEMICALS[selected_chem]["type"]
            
        target_v = st.number_input("Target Volume (mL)", min_value=1.0, step=10.0, value=1000.0)
        
        # Calculation Logic
        required_mass = target_m * (target_v / 1000.0) * mw
        
        st.metric("Required Mass (g)", f"{required_mass:.2f} g")
        
    with col2:
        # Automated Batch Code Logic
        date_str = prep_date.strftime("%Y%m%d")
        prefix = f"{chem_type[:2].upper()}-{date_str}-"
        
        # Search for existing batches today to get count
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
                final_chem_type = chem_type if selected_chem != "Other (Custom)" else f"Other ({custom_name})"
                new_batch = StockSolutionBatch(
                    code=batch_code,
                    chemical_type=final_chem_type,
                    molarity=target_m,
                    target_volume_ml=target_v,
                    actual_mass_g=actual_mass,
                    preparation_date=datetime.datetime.combine(prep_date, datetime.time.min),
                    operator=operator,
                    notes=notes
                )
                db.add(new_batch)
                db.commit()
                st.success(f"Batch {batch_code} saved!")
            except Exception as e:
                st.error(f"Error: {str(e)}")

with tab3:
    st.subheader("Inventory of Prepared Solutions")
    batches = db.query(StockSolutionBatch).order_by(StockSolutionBatch.created_at.desc()).all()
    
    if batches:
        data = []
        for b in batches:
            data.append({
                "Code": b.code,
                "Type": b.chemical_type,
                "Molarity": b.molarity,
                "Volume (mL)": b.target_volume_ml,
                "Mass (g)": b.actual_mass_g,
                "Prep Date": b.preparation_date.strftime("%Y-%m-%d") if b.preparation_date else "N/A",
                "Operator": b.operator
            })
        st.dataframe(data, use_container_width=True)
    else:
        st.info("No batches found.")
