import streamlit as st
import datetime
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import SynthesisBatch, PerformanceTest

st.set_page_config(page_title="Performance Results", page_icon="📈", layout="wide")

st.markdown("# 📈 Performance Testing (Mortar)")

db: Session = next(get_db())

# Select Batch
batches = db.query(SynthesisBatch).order_by(SynthesisBatch.execution_date.desc()).limit(50).all()
batch_select = st.selectbox("Select Synthesis Batch", options=batches, format_func=lambda x: f"{x.lab_notebook_ref} - {x.execution_date.strftime('%Y-%m-%d')}")

if batch_select:
    st.divider()
    st.markdown(f"### Enter Results for: **{batch_select.lab_notebook_ref}**")
    
    with st.form("perf_form"):
        # --- Mix Design Metadata ---
        st.subheader("1. Mix Design")
        m1, m2, m3 = st.columns(3)
        cement_type = m1.text_input("Cement Type", value="CEM I 42.5 N Heidelberg")
        wc_ratio = m2.number_input("w/c Ratio", value=0.45)
        sand_mass = m3.number_input("Standard Sand (g)", value=1350.0)
        
        # --- Fresh Properties ---
        st.subheader("2. Fresh Properties")
        f1, f2, f3 = st.columns(3)
        fresh_density = f1.number_input("Fresh Density (g/L)", value=2240.0) # approx 2.24 g/cm3
        flow = f2.number_input("Flow (mm)", value=170.0)
        air = f3.number_input("Air Content (%)", value=2.0)
        
        # --- Hardened Properties (Averages) ---
        st.subheader("3. Compressive Strength (Average MPa)")
        st.caption("Enter the average strength calculated from Cube A/B/C")
        
        c1, c2, c3, c4 = st.columns(4)
        cs_12h = c1.number_input("12 Hours", step=0.1, format="%.2f")
        cs_16h = c2.number_input("16 Hours", step=0.1, format="%.2f")
        cs_1d = c3.number_input("1 Day", step=0.1, format="%.2f")
        cs_2d = c4.number_input("2 Days", step=0.1, format="%.2f")
        
        c5, c6, c7, c8 = st.columns(4)
        cs_7d = c5.number_input("7 Days", step=0.1, format="%.2f")
        cs_28d = c6.number_input("28 Days", step=0.1, format="%.2f")
        
        # Optional: Full Detail Text
        st.divider()
        st.caption("Observations / Paste Raw Excel Data (Optional)")
        raw_notes = st.text_area("Paste row data or observations here", height=100)

        submitted = st.form_submit_button("💾 Save Results")
        
        if submitted:
            mix_meta = {
                "cement_type": cement_type,
                "wc_ratio": wc_ratio,
                "sand_mass": sand_mass
            }
            
            result = PerformanceTest(
                batch_id=batch_select.id,
                test_type="Mortar",
                mix_design=mix_meta,
                
                # Fresh
                fresh_density=fresh_density,
                flow=flow,
                air_content=air,
                
                # Hardened
                compressive_strength_12h=cs_12h,
                compressive_strength_16h=cs_16h,
                compressive_strength_1d=cs_1d,
                compressive_strength_2d=cs_2d,
                compressive_strength_7d=cs_7d,
                compressive_strength_28d=cs_28d,
                
                raw_data={"notes": raw_notes}
            )
            db.add(result)
            db.commit()
            st.success("Test results saved successfully.")

# View History
st.divider()
st.subheader("Recent Results")
results = db.query(PerformanceTest).order_by(PerformanceTest.cast_date.desc()).limit(10).all()
if results:
    # Flatten data for table
    table_data = []
    for r in results:
        row = {
            "Batch": r.batch.lab_notebook_ref if r.batch else "?",
            "12h": r.compressive_strength_12h,
            "1d": r.compressive_strength_1d,
            "28d": r.compressive_strength_28d,
            "Flow": r.flow,
            "Mix": r.mix_design.get("cement_type", "") if r.mix_design else ""
        }
        table_data.append(row)
    st.dataframe(table_data)
