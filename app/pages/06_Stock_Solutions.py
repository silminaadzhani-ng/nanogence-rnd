import streamlit as st
import datetime
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import StockSolutionBatch

st.set_page_config(page_title="Stock Solutions", page_icon="🧪", layout="wide")

st.markdown("# 🧪 Stock Solution Management")

db: Session = next(get_db())

# Predefined Chemical Metadata
CHEMICALS = {
    "Ca(NO3)2·4H2O": {"mw": 236.15, "type": "Ca"},
    "Na2SiO3·5H2O": {"mw": 212.14, "type": "Si"},
    "NaOH": {"mw": 40.00, "type": "NaOH"}
}

tab1, tab2 = st.tabs(["➕ Prepare New Batch", "📚 Batch Library"])

with tab1:
    st.subheader("Prepare Stock Solution")
    
    col1, col2 = st.columns(2)
    
    with col1:
        chem_key = st.selectbox("Chemical", options=list(CHEMICALS.keys()))
        target_m = st.number_input("Target Molarity (mol/L)", min_value=0.01, step=0.01, value=1.50 if "Ca" in chem_key else (0.75 if "Si" in chem_key else 5.0))
        target_v = st.number_input("Target Volume (mL)", min_value=1.0, step=10.0, value=1000.0)
        
        # Calculation Logic
        mw = CHEMICALS[chem_key]["mw"]
        required_mass = target_m * (target_v / 1000.0) * mw
        
        st.metric("Required Mass (g)", f"{required_mass:.2f} g")
        
    with col2:
        # Automated Batch Code Logic
        today_str = datetime.date.today().strftime("%Y%m%d")
        chem_type = CHEMICALS[chem_key]["type"]
        prefix = f"{chem_type}-{today_str}-"
        
        # Search for existing batches today to get count
        count = db.query(StockSolutionBatch).filter(StockSolutionBatch.code.like(f"{prefix}%")).count()
        suggested_code = f"{prefix}{count + 1:02d}"
        
        batch_code = st.text_input("Batch Code", value=suggested_code)
        actual_mass = st.number_input("Actual Mass Weighed (g)", step=0.01, value=required_mass)
        operator = st.text_input("Operator", value="Silmina Adzhani")
        notes = st.text_area("Notes")

    if st.button("Save Stock Batch"):
        if not batch_code:
            st.error("Batch Code is required.")
        else:
            try:
                new_batch = StockSolutionBatch(
                    code=batch_code,
                    chemical_type=CHEMICALS[chem_key]["type"],
                    molarity=target_m,
                    target_volume_ml=target_v,
                    actual_mass_g=actual_mass,
                    operator=operator,
                    notes=notes
                )
                db.add(new_batch)
                db.commit()
                st.success(f"Batch {batch_code} saved!")
            except Exception as e:
                st.error(f"Error: {str(e)}")

with tab2:
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
                "Date": b.created_at.strftime("%Y-%m-%d"),
                "Operator": b.operator
            })
        st.dataframe(data, use_container_width=True)
    else:
        st.info("No batches found.")
