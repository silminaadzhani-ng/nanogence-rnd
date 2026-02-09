import streamlit as st
import datetime
import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db, init_db
from app.models import SynthesisBatch, PerformanceTest, QCMeasurement, RawMaterial
from app.ui_utils import display_logo

# Ensure database is synced
init_db()

st.set_page_config(page_title="Performance Results", page_icon="📈", layout="wide")
display_logo()

st.markdown("# 📈 Performance Testing (Mortar)")

db: Session = next(get_db())

tab_dash, tab_mix, tab_log, tab_lib = st.tabs(["📊 Dashboard", "⚖️ Mix Design", "📝 Log Results", "📚 Library"])

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

with tab_mix:
    st.subheader("🛠️ Step 1: Design & Cast Mix")
    
    # 1. Select Synthesis Batch (The "NG Product")
    raw_batches = db.query(SynthesisBatch).order_by(SynthesisBatch.execution_date.desc()).all()
    batch_options = [None] + raw_batches
    
    def format_batch(x):
        if x is None: return "Reference / Commercial (No Synthesis Batch)"
        return f"{x.lab_notebook_ref} ({x.recipe.name if x.recipe else 'Unknown'})"

    batch_select = st.selectbox(
        "Select Synthesis Batch (NG Product)", 
        options=batch_options, 
        format_func=format_batch,
        key="mix_batch_select"
    )

    # Manage Solid Content state
    if "sc_input" not in st.session_state:
        st.session_state.sc_input = 0.0
    
    # Update SC when batch changes
    current_batch_id = batch_select.id if batch_select else "REF"
    if "last_processed_batch_id" not in st.session_state or st.session_state.last_processed_batch_id != current_batch_id:
        st.session_state.last_processed_batch_id = current_batch_id
        if batch_select:
            qc_24h = db.query(QCMeasurement).filter(
                QCMeasurement.batch_id == batch_select.id,
                QCMeasurement.ageing_time >= 20.0,
                QCMeasurement.ageing_time <= 28.0
            ).order_by(func.abs(QCMeasurement.ageing_time - 24.0)).first()
            if not qc_24h:
                qc_24h = db.query(QCMeasurement).filter(QCMeasurement.batch_id == batch_select.id).order_by(QCMeasurement.measured_at.desc()).first()
            st.session_state.sc_input = qc_24h.solid_content_measured if qc_24h else (batch_select.recipe.total_solid_content if batch_select.recipe else 0.0)
        else:
            st.session_state.sc_input = 0.0

    # Sub-header logic...
    st.markdown("---")
    
    c_m1, c_m2, c_m3 = st.columns(3)
    # Fetch available cements from RawMaterial inventory
    available_cements = db.query(RawMaterial).filter(RawMaterial.chemical_type == "Cement").all()
    if available_cements:
        cem_options = [f"{m.material_name} ({m.brand})" for m in available_cements]
        cem_type = c_m1.selectbox("Cement Type", options=cem_options, key="cem_type_mix")
    else:
        st.warning("⚠️ No Cements found in Inventory. Please add them in the Materials page.")
        cem_type = c_m1.text_input("Cement Type (Manual)", value="CEM I 42.5 N Heidelberg")
    
    cem_mass = c_m2.number_input("Cement Mass [g]", min_value=0.0, value=450.0, step=1.0)

    available_sands = db.query(RawMaterial).filter(RawMaterial.chemical_type == "Sand").all()
    if available_sands:
        sand_options = [f"{m.material_name} ({m.lot_number})" for m in available_sands]
        sand_type = c_m3.selectbox("Standard Sand Source", options=sand_options, key="sand_type_mix")
        sand_mass = c_m3.number_input("Standard Sand Mass [g]", min_value=0.0, value=1350.0, step=1)
    else:
        sand_mass = c_m3.number_input("Standard Sand [g]", min_value=0.0, value=1350.0, step=1.0)
        sand_type = "Standard Sand"
    
    c_m4, c_m5, c_m6, c_m7 = st.columns(4)
    sc_info = c_m4.number_input("NG Solid Content [%]", key="sc_input", format="%.2f", help="Automatically fetched from batch measurements or theoretical recipe content.")
    target_solid_dosage = c_m5.number_input("Target Solid Dosage [% of cem]", min_value=0.0, max_value=5.0, value=0.5, step=0.01)
    wc_ratio = c_m6.number_input("w/cement ratio [-]", min_value=0.1, max_value=1.0, value=0.45, step=0.01)
    defoamer_g = c_m7.number_input("Defoamer [g]", min_value=0.0, value=0.0, step=0.01)

    # --- Precise Calculations Matching User spreadsheet logic ---
    # 1. Target Dry Mass [g]
    m_dry_target = cem_mass * (target_solid_dosage / 100.0)
    
    # 2. Dosage [g] (Liquid Mass of NG product)
    # Formula: m_liq = cem_mass * (target_solid / 100) / (sc / 100)
    if sc_info > 0:
        m_ng_liq = round(m_dry_target / (sc_info / 100.0), 2)
    else:
        m_ng_liq = 0.0
    
    # 3. Water from NG [g]
    # Formula: dosage [g] * (1 - NG Solid Content / 100)
    water_from_ng = round(m_ng_liq * (1 - (sc_info / 100.0)), 2)
    
    # 4. Final Added Water (Water [g] in user table)
    # Formula: total added water = (w/cement ratio * cement mass [g]) - Water from NG
    added_water = round((wc_ratio * cem_mass) - water_from_ng, 2)
    
    # Total water for display
    total_water_req = round(cem_mass * wc_ratio, 2)
    
    # 6. Liquid Dosage % (for reporting/verification)
    liq_dosage_pct = (m_ng_liq / cem_mass) * 100.0 if cem_mass > 0 else 0.0

    st.markdown("#### 📋 Mix Design Summary Table")
    mix_summary_data = [
        ["Cement", f"{cem_mass:.1f} g", cem_type],
        ["Sand", f"{sand_mass:.1f} g", "Standard sand"],
        ["NG Product", f"{m_ng_liq:.2f} g", f"at {sc_info:.2f}% SC"],
        ["Defoamer", f"{defoamer_g:.3f} g", "Optional additive"],
        ["---", "---", "---"],
        ["Calculated Added Water", f"**{added_water:.2f} g**", f"at w/c {wc_ratio}"]
    ]
    st.table(pd.DataFrame(mix_summary_data, columns=["Component", "Mass", "Note"]))

    st.markdown("---")
    st.caption("Casting Metadata")
    
    # Logic to get the next sequential H-number and operator initials
    def get_auto_code(op_name):
        initials = "".join([p[0].upper() for p in op_name.split() if p]) or "OP"
        try:
            # Query all PerformanceTest records and find the maximum -H number in raw_data
            all_tests = db.query(PerformanceTest).all()
            max_num = 144 # Starting base for old experiments if none found
            for t in all_tests:
                code = t.raw_data.get("cube_code", "")
                if "-H" in code:
                    try:
                        num_part = code.split("-H")[-1].strip()
                        # handle cases like "H145 (ref)"
                        num_only = "".join(filter(str.isdigit, num_part))
                        if num_only:
                            num = int(num_only)
                            if num > max_num: max_num = num
                    except: continue
            return f"{initials}-H{max_num + 1}"
        except:
            return f"{initials}-H145"

    meta_row1 = st.columns(3)
    operator = meta_row1[0].text_input("Operator", value="Silmina Adzhani", key="op_mix")
    
    # Auto-generate code based on operator
    suggested_code = get_auto_code(operator)
    cube_code = meta_row1[1].text_input("Cube Code (Auto-generated)", value=suggested_code, key="cube_code_mix")
    cast_date = meta_row1[2].date_input("Casting Date", value=datetime.date.today(), key="cast_date_mix")

    meta_row2 = st.columns(3)
    # Time Selection Format
    cast_time_val = meta_row2[0].time_input("Casting Time", value=datetime.datetime.now().time(), key="cast_time_input")
    # Format for storage: HHhMM
    cast_time_str = cast_time_val.strftime("%Hh%M")
    
    humidity = meta_row2[1].number_input("Curing RH [%]", value=90.0)
    num_cubes = meta_row2[2].number_input("N° of Cubes", value=12, step=1)

    if st.button("✅ Initialise Mix & Casting", type="primary"):
        if not cube_code:
            st.error("Please enter/confirm a Cube Code.")
        else:
            try:
                mix_data = {
                    "cement_type": cem_type, "cement_mass_g": cem_mass, 
                    "sand_type": sand_type, "sand_mass_g": sand_mass,
                    "target_solid_dosage_pct": target_solid_dosage, "solid_content_pct": sc_info,
                    "dosage_g": m_ng_liq, "dosage_liquid_pct": liq_dosage_pct,
                    "water_from_ng_g": water_from_ng, "wc_ratio": wc_ratio,
                    "water_added_g": added_water, "num_cubes": num_cubes,
                    "casting_time": cast_time_str, "relative_humidity": humidity,
                    "defoamer_g": defoamer_g
                }
                new_test = PerformanceTest(
                    batch_id=batch_select.id if batch_select else None, 
                    test_type="Mortar", 
                    mix_design=mix_data,
                    cast_date=datetime.datetime.combine(cast_date, datetime.time.min),
                    raw_data={"operator": operator, "cube_code": cube_code, "rh": humidity}
                )
                db.add(new_test)
                db.commit()
                st.success(f"Mix Design for **{cube_code}** saved successfully!")
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

with tab_log:
    st.subheader("📝 Step 2: Log Fresh & Hardened Results")
    
    # Select from existing performance tests
    perf_tests = db.query(PerformanceTest).order_by(PerformanceTest.cast_date.desc()).limit(50).all()
    if not perf_tests:
        st.info("No mixes designed yet. Go to the 'Mix Design' tab first.")
    else:
        perf_select = st.selectbox(
            "Select Trial to Update", 
            options=perf_tests,
            format_func=lambda x: f"{x.raw_data.get('cube_code', 'Unnamed')} ({x.batch.lab_notebook_ref if x.batch else 'Ref'}) - {x.cast_date.strftime('%Y-%m-%d')}"
        )

        if perf_select:
            st.markdown(f"#### Updating Results for: **{perf_select.raw_data.get('cube_code', 'N/A')}**")
            with st.form("results_log_form"):
                st.caption("Fresh Properties")
                f1, f2, f3, f4 = st.columns(4)
                density = f1.number_input("Fresh Density [g/L]", value=float(perf_select.fresh_density or 2240.0))
                flow = f2.number_input("Mortar Flow [mm]", value=float(perf_select.flow or 180.0))
                air = f3.number_input("Air Content [%]", value=float(perf_select.air_content or 1.5))
                temp = f4.number_input("Temp [°C]", value=float(perf_select.temperature or 20.0))
                
                st.caption("Compressive Strength (Average MPa)")
                c1, c2, c3, c4 = st.columns(4)
                cs_12h = c1.number_input("12h", value=float(perf_select.compressive_strength_12h or 0.0), format="%.2f")
                cs_16h = c2.number_input("16h", value=float(perf_select.compressive_strength_16h or 0.0), format="%.2f")
                cs_1d = c3.number_input("1d", value=float(perf_select.compressive_strength_1d or 0.0), format="%.2f")
                cs_2d = c4.number_input("2d", value=float(perf_select.compressive_strength_2d or 0.0), format="%.2f")
                
                c5, c6, c7 = st.columns(3)
                cs_3d = c5.number_input("3d", value=float(perf_select.raw_data.get("cs_3d", 0.0)), format="%.2f")
                cs_7d = c6.number_input("7d", value=float(perf_select.compressive_strength_7d or 0.0), format="%.2f")
                cs_28d = c7.number_input("28d", value=float(perf_select.compressive_strength_28d or 0.0), format="%.2f")

                notes = st.text_area("Observations / Raw Notes", value=perf_select.raw_data.get("notes", ""))

                if st.form_submit_button("💾 Save Results"):
                    try:
                        perf_select.fresh_density = density
                        perf_select.flow = flow
                        perf_select.air_content = air
                        perf_select.temperature = temp
                        perf_select.compressive_strength_12h = cs_12h
                        perf_select.compressive_strength_16h = cs_16h
                        perf_select.compressive_strength_1d = cs_1d
                        perf_select.compressive_strength_2d = cs_2d
                        perf_select.compressive_strength_7d = cs_7d
                        perf_select.compressive_strength_28d = cs_28d
                        
                        new_raw = dict(perf_select.raw_data)
                        new_raw["cs_3d"] = cs_3d
                        new_raw["notes"] = notes
                        perf_select.raw_data = new_raw
                        
                        db.commit()
                        st.success("Results updated successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

with tab_lib:
    st.subheader("📚 Performance Testing Library")
    results = db.query(PerformanceTest).order_by(PerformanceTest.cast_date.desc()).all()
    if results:
        table_data = []
        for r in results:
            mix = r.mix_design or {}
            raw = r.raw_data or {}
            table_data.append({
                "Date": r.cast_date.strftime("%Y-%m-%d") if r.cast_date else "N/A",
                "Measurement ID": r.batch.lab_notebook_ref if r.batch else "Ref",
                "Cube Code": raw.get("cube_code", "N/A"),
                "Cem [g]": mix.get("cement_mass_g", 0),
                "NG [g]": mix.get("dosage_g", 0),
                "Water NG [g]": mix.get("water_from_ng_g", 0),
                "w/c": mix.get("wc_ratio", 0),
                "WATER ADDED [g]": f"**{mix.get('water_added_g', 0):.2f}**",
                "Defoamer [g]": mix.get("defoamer_g", 0),
                "1d [MPa]": r.compressive_strength_1d,
                "28d [MPa]": r.compressive_strength_28d,
                "Operator": raw.get("operator", "N/A")
            })
        st.dataframe(table_data, use_container_width=True)
    else:
        st.info("No performance test results found.")
