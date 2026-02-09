import streamlit as st
import datetime
import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db, init_db
from app.models import SynthesisBatch, PerformanceTest, QCMeasurement
from app.ui_utils import display_logo

# Ensure database is synced
init_db()

st.set_page_config(page_title="Performance Results", page_icon="📈", layout="wide")
display_logo()

st.markdown("# 📈 Performance Testing (Mortar)")

db: Session = next(get_db())

tab_dash, tab1, tab2 = st.tabs(["📊 Dashboard", "🧪 Log Test Results", "📚 Recent Results"])

with tab_dash:
    st.subheader("Performance Overview")
    col1, col2, col3 = st.columns(3)
    
    total_tests = db.query(PerformanceTest).count()
    avg_28d = db.query(func.avg(PerformanceTest.compressive_strength_28d)).scalar() or 0
    avg_flow = db.query(func.avg(PerformanceTest.flow)).scalar() or 0
    
    col1.metric("Total Tests", total_tests)
    col2.metric("Avg 28d Strength (MPa)", f"{avg_28d:.1f}")
    col3.metric("Avg Flow (mm)", f"{avg_flow:.1f}")

    if total_tests > 0:
        perf_data = db.query(PerformanceTest.compressive_strength_1d, PerformanceTest.compressive_strength_28d).all()
        df_perf = pd.DataFrame(perf_data, columns=["1d Strength", "28d Strength"])
        st.subheader("Strength Development (1d vs 28d)")
        st.line_chart(df_perf)

with tab1:
    st.subheader("🧪 Log Performance Test")
    
    # 1. Select Synthesis Batch (The "NG Product")
    batches = db.query(SynthesisBatch).order_by(SynthesisBatch.execution_date.desc()).limit(100).all()
    batch_select = st.selectbox(
        "Select Synthesis Batch (NG Product)", 
        options=batches, 
        format_func=lambda x: f"{x.lab_notebook_ref} ({x.recipe.name if x.recipe else 'Unknown Recipe'})",
        key="perf_batch_select"
    )

    if batch_select:
        # Try to find 24h Solid Content measurement for this batch
        qc_24h = db.query(QCMeasurement).filter(
            QCMeasurement.batch_id == batch_select.id,
            QCMeasurement.ageing_time >= 20.0, # Looking for roughly 24h
            QCMeasurement.ageing_time <= 28.0
        ).order_by(func.abs(QCMeasurement.ageing_time - 24.0)).first()
        
        # Fallback to the latest measurement or recipe theoretical if 24h not found
        if not qc_24h:
            qc_24h = db.query(QCMeasurement).filter(QCMeasurement.batch_id == batch_select.id).order_by(QCMeasurement.measured_at.desc()).first()
        
        sc_val = qc_24h.solid_content_measured if qc_24h else (batch_select.recipe.total_solid_content if batch_select.recipe else 0.0)

        st.divider()
        
        with st.form("perf_form_v2"):
            # --- SECTION 1: MIX DESIGN ---
            st.markdown("### 🛠️ Step 1: Mortar Mix Design")
            
            c_m1, c_m2, c_m3 = st.columns(3)
            cem_type = c_m1.text_input("Cement Type", value="CEM I 42.5 N Heidelberg")
            cem_mass = c_m2.number_input("Cement Mass [g]", min_value=0.0, value=450.0, step=1.0)
            sand_mass = c_m3.number_input("Standard Sand [g]", min_value=0.0, value=1350.0, step=1.0)
            
            c_m4, c_m5, c_m6 = st.columns(3)
            # Display solid content for info
            sc_info = c_m4.number_input("NG Solid Content [%]", value=sc_val, help="Fetched from synthesis measurements (prefer 24h).", format="%.2f")
            target_solid_dosage = c_m5.number_input("Target Solid Dosage [% of cem]", min_value=0.0, max_value=5.0, value=0.5, step=0.01)
            wc_ratio = c_m6.number_input("w/cement ratio [-]", min_value=0.1, max_value=1.0, value=0.45, step=0.01)

            # Calculations
            # m_dry = cem_mass * (target_solid_dosage / 100)
            # m_ng_liq = m_dry / (sc_info / 100) if sc_info > 0 else 0
            # liquid_dosage_pct = (m_ng_liq / cem_mass) * 100
            # water_from_ng = m_ng_liq - m_dry
            # total_water = cem_mass * wc_ratio
            # added_water = total_water - water_from_ng
            
            m_dry = cem_mass * (target_solid_dosage / 100.0)
            m_ng_liq = m_dry / (sc_info / 100.0) if sc_info > 0 else 0.0
            liq_dosage_pct = (m_ng_liq / cem_mass) * 100.0 if cem_mass > 0 else 0.0
            water_from_ng = m_ng_liq - m_dry
            total_water = cem_mass * wc_ratio
            added_water = total_water - water_from_ng
            
            st.info(f"💡 **Calculated Mix:** NG Dosage: **{m_ng_liq:.2f} g** ({liq_dosage_pct:.2f}%) | Water from Product: **{water_from_ng:.2f} g** | Water to Add: **{added_water:.2f} g**")

            # --- SECTION 2: TEST RESULTS ---
            st.markdown("### 📝 Step 2: Fresh & Hardened Properties")
            
            st.caption("Fresh Properties")
            f1, f2, f3, f4 = st.columns(4)
            density = f1.number_input("Fresh Density [g/L]", value=2240.0)
            flow = f2.number_input("Mortar Flow [mm]", value=180.0)
            air = f3.number_input("Air Content [%]", value=1.5)
            temp = f4.number_input("Temp [°C]", value=20.0)
            
            st.caption("Compressive Strength (Average MPa)")
            c1, c2, c3, c4 = st.columns(4)
            cs_12h = c1.number_input("12h", value=0.0, format="%.2f")
            cs_16h = c2.number_input("16h", value=0.0, format="%.2f")
            cs_1d = c3.number_input("1d", value=0.0, format="%.2f")
            cs_2d = c4.number_input("2d", value=0.0, format="%.2f")
            
            c5, c6, c7, c8 = st.columns(4)
            cs_3d = c5.number_input("3d", value=0.0, format="%.2f")
            cs_7d = c6.number_input("7d", value=0.0, format="%.2f")
            cs_28d = c7.number_input("28d", value=0.0, format="%.2f")
            num_cubes = c8.number_input("N° of Cubes", value=12, step=1)
            
            st.markdown("---")
            meta1, meta2, meta3 = st.columns(3)
            cast_date = meta1.date_input("Casting Date", value=datetime.date.today())
            cast_time = meta2.text_input("Casting Time", value=datetime.datetime.now().strftime("%Hh%M"))
            operator = meta3.text_input("Operator", value="Silmina Adzhani")
            
            meta4, meta5, meta6 = st.columns(3)
            cube_code = meta4.text_input("Cube Code (e.g. AC-H146)", placeholder="Reference code for the lab")
            humidity = meta5.number_input("Curing RH [%]", value=90.0)
            notes = meta6.text_input("Notes (Global)")

            submitted = st.form_submit_button("✅ Save Performance Record")
            
            if submitted:
                try:
                    mix_data = {
                        "cement_type": cem_type,
                        "cement_mass_g": cem_mass,
                        "sand_mass_g": sand_mass,
                        "target_solid_dosage_pct": target_solid_dosage,
                        "solid_content_pct": sc_info,
                        "dosage_g": m_ng_liq,
                        "dosage_liquid_pct": liq_dosage_pct,
                        "water_from_ng_g": water_from_ng,
                        "wc_ratio": wc_ratio,
                        "water_added_g": added_water,
                        "num_cubes": num_cubes,
                        "casting_time": cast_time,
                        "relative_humidity": humidity
                    }
                    
                    new_test = PerformanceTest(
                        batch_id=batch_select.id,
                        test_type="Mortar",
                        mix_design=mix_data,
                        cast_date=datetime.datetime.combine(cast_date, datetime.time.min),
                        fresh_density=density,
                        flow=flow,
                        air_content=air,
                        temperature=temp,
                        # humidity=humidity, # Not in base model columns yet
                        compressive_strength_12h=cs_12h,
                        compressive_strength_16h=cs_16h,
                        compressive_strength_1d=cs_1d,
                        compressive_strength_2d=cs_2d,
                        compressive_strength_7d=cs_7d,
                        compressive_strength_28d=cs_28d,
                        raw_data={
                            "operator": operator,
                            "cube_code": cube_code,
                            "notes": notes,
                            "cs_3d": cs_3d,
                            "rh": humidity
                        }
                    )
                    db.add(new_test)
                    db.commit()
                    st.success(f"Results for **{batch_select.lab_notebook_ref}** saved successfully!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Error saving results: {e}")

with tab2:
    st.subheader("📚 Performance Testing Library")
    results = db.query(PerformanceTest).order_by(PerformanceTest.cast_date.desc()).all()
    if results:
        # Flatten data for table
        table_data = []
        for r in results:
            mix = r.mix_design or {}
            raw = r.raw_data or {}
            
            row = {
                "Date": r.cast_date.strftime("%Y-%m-%d") if r.cast_date else "N/A",
                "Measurement ID": r.batch.lab_notebook_ref if r.batch else "?",
                "Cube Code": raw.get("cube_code", "N/A"),
                "Cement Type": mix.get("cement_type", "N/A"),
                "Cem [g]": mix.get("cement_mass_g", 0),
                "Sand [g]": mix.get("sand_mass_g", 0),
                "NG Product": r.batch.recipe.name if r.batch and r.batch.recipe else "None",
                "SC [%]": mix.get("solid_content_pct", 0),
                "Dosage [%]": mix.get("target_solid_dosage_pct", 0),
                "NG [g]": mix.get("dosage_g", 0),
                "Water NG [g]": mix.get("water_from_ng_g", 0),
                "w/c": mix.get("wc_ratio", 0),
                "Water Added [g]": mix.get("water_added_g", 0),
                "Flow [mm]": r.flow,
                "12h": r.compressive_strength_12h,
                "16h": r.compressive_strength_16h,
                "1d": r.compressive_strength_1d,
                "2d": r.compressive_strength_2d,
                "3d": raw.get("cs_3d", 0),
                "7d": r.compressive_strength_7d,
                "28d": r.compressive_strength_28d,
                "Operator": raw.get("operator", "N/A")
            }
            table_data.append(row)
        
        df_results = pd.DataFrame(table_data)
        
        # Display with selection for deletion/review
        st.dataframe(
            df_results, 
            use_container_width=True,
            hide_index=True,
            column_config={
                "Dosage [%]": st.column_config.NumberColumn("Solid Dosage [%]", format="%.2f"),
                "SC [%]": st.column_config.NumberColumn("SC (%)", format="%.2f"),
                "NG [g]": st.column_config.NumberColumn("NG Liquid [g]", format="%.2f"),
            }
        )
        
        if st.button("🗑️ Clear Selected (Dev Only)", type="secondary", help="Deletion logic can be added here"):
            st.info("Feature coming soon: Row selection and deletion.")
    else:
        st.info("No performance test results found.")
