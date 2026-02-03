import streamlit as st
import datetime
import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db, init_db
from app.models import SynthesisBatch, PerformanceTest, Recipe
from app.ui_utils import display_logo
from app.auth import check_authentication

# Ensure authentication
check_authentication()

# Ensure database is synced
init_db()

st.set_page_config(page_title="Performance Results", page_icon="📈", layout="wide")
display_logo()

st.markdown("# 📈 Performance Testing (Mortar)")

db: Session = next(get_db())

tab_dash, tab_recipes, tab_log = st.tabs(["📊 Dashboard", "📝 Recipes", "➕ Log Test Results"])

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
        # Get recent 10 tests for the chart
        recent_tests = db.query(PerformanceTest).order_by(PerformanceTest.cast_date.asc()).limit(10).all()
        if recent_tests:
            chart_data = []
            for t in recent_tests:
                label = t.batch.lab_notebook_ref if t.batch else "Unknown"
                chart_data.append({
                    "Batch": label,
                    "1d": t.compressive_strength_1d or 0,
                    "28d": t.compressive_strength_28d or 0
                })
            df_chart = pd.DataFrame(chart_data).set_index("Batch")
            st.subheader("Recent Strength Progress")
            st.line_chart(df_chart)

with tab_recipes:
    st.subheader("📚 Performance Library (by Recipe)")
    search_recipe = st.text_input("🔍 Search Recipe Name/Code", placeholder="e.g. NG-2024...")
    
    query = db.query(Recipe).order_by(Recipe.code.desc())
    if search_recipe:
        query = query.filter((Recipe.name.ilike(f"%{search_recipe}%")) | (Recipe.code.ilike(f"%{search_recipe}%")))
    
    recipes = query.all()
    
    if not recipes:
        st.info("No recipes found matches the search.")
    else:
        for r in recipes:
            # Stats for this recipe
            recipe_tests = db.query(PerformanceTest).join(SynthesisBatch).filter(SynthesisBatch.recipe_id == r.id).all()
            test_count = len(recipe_tests)
            recipe_avg_28d = sum([t.compressive_strength_28d for t in recipe_tests if t.compressive_strength_28d]) / test_count if test_count > 0 else 0
            
            label = f"{r.code} - {r.name} ({test_count} Tests, Avg 28d: {recipe_avg_28d:.1f} MPa)"
            with st.expander(label):
                c_head1, c_head2 = st.columns([2, 1])
                c_head1.markdown(f"**Recipe Goals:** Ca/Si: {r.ca_si_ratio}, Solids: {r.total_solid_content}%, PCE: {r.pce_content_wt}%")
                
                batches = db.query(SynthesisBatch).filter(SynthesisBatch.recipe_id == r.id).order_by(SynthesisBatch.execution_date.desc()).all()
                if not batches:
                    st.caption("No synthesis batches recorded.")
                else:
                    for b in batches:
                        st.markdown(f"---")
                        b_col1, b_col2 = st.columns([3, 1])
                        b_col1.markdown(f"**Batch: {b.lab_notebook_ref}** ({b.execution_date.strftime('%Y-%m-%d')})")
                        b_col2.caption(f"Status: {b.status}")
                        
                        tests = db.query(PerformanceTest).filter(PerformanceTest.batch_id == b.id).all()
                        if not tests:
                            st.caption("No performance tests logged.")
                        else:
                            for t in tests:
                                # Detailed Mix Design Info
                                m = t.mix_design
                                st.markdown(f"**Mix Design Details:**")
                                d1, d2, d3, d4, d5 = st.columns(5)
                                d1.caption(f"Cement: {m.get('cement_mass', 0)}g")
                                d2.caption(f"w/c: {m.get('wc_ratio', 0)}")
                                d3.caption(f"Sand: {m.get('sand_mass', 0)}g")
                                d4.caption(f"NG Dosage: {m.get('ng_dosage_pct', 0)}% solid")
                                d5.caption(f"Added Water: {m.get('water_added_g', 0)}g")

                                # Results Row
                                r1, r2, r3, r4, r5, r6, r7, r8 = st.columns(8)
                                r1.metric("12h", f"{t.compressive_strength_12h or 0:.1f}")
                                r2.metric("16h", f"{t.compressive_strength_16h or 0:.1f}")
                                r3.metric("1d", f"{t.compressive_strength_1d or 0:.1f}")
                                r4.metric("2d", f"{t.compressive_strength_2d or 0:.1f}")
                                r5.metric("3d", f"{t.compressive_strength_3d or 0:.1f}")
                                r6.metric("7d", f"{t.compressive_strength_7d or 0:.1f}")
                                r7.metric("28d", f"{t.compressive_strength_28d or 0:.1f}")
                                r8.metric("Flow", f"{t.flow or 0:.0f}")

                                # Curing & Others
                                st.caption(f"Curing: {t.temperature or 20}°C, {t.humidity or 90}% RH | Operator: {b.operator}")

with tab_log:
    st.subheader("➕ Log New Performance Results")
    # Select Batch
    batches = db.query(SynthesisBatch).order_by(SynthesisBatch.execution_date.desc()).limit(50).all()
    batch_select = st.selectbox("Select Synthesis Batch to link results", options=batches, format_func=lambda x: f"{x.lab_notebook_ref} ({x.recipe.code if x.recipe else 'N/A'})")

    if batch_select:
        st.divider()
        st.markdown(f"### Enter Results for: **{batch_select.lab_notebook_ref}**")
        recipe = batch_select.recipe
        
        # --- Mix Design Calculator ---
        st.subheader("1. Mix Design Calculator")
        c_calc1, c_calc2, c_calc3 = st.columns(3)
        c_mass = c_calc1.number_input("Cement Mass (g)", value=450.0, step=1.0)
        target_wc = c_calc2.number_input("Target w/c Ratio", value=0.45, step=0.01)
        ng_dosage_pct = c_calc3.number_input("NG Dosage (% solid on cement)", value=0.5, step=0.05)
        
        # Calculations
        product_solids = recipe.total_solid_content if recipe else 0.0
        total_water_needed = c_mass * target_wc
        dosage_dry_g = c_mass * (ng_dosage_pct / 100.0)
        dosage_wet_g = dosage_dry_g / (product_solids / 100.0) if product_solids > 0 else 0.0
        water_from_ng = dosage_wet_g - dosage_dry_g
        water_to_add = total_water_needed - water_from_ng
        
        res_col1, res_col2, res_col3, res_col4 = st.columns(4)
        res_col1.metric("Wet NG Dosage (g)", f"{dosage_wet_g:.2f} g")
        res_col2.metric("Water from NG (g)", f"{water_from_ng:.2f} g")
        res_col3.metric("Actual Water to Add (g)", f"{water_to_add:.2f} g")
        res_col4.info(f"Basis: {product_solids}% Solids")

        with st.form("perf_form"):
            # --- Mix Design Metadata ---
            m1, m2, m3 = st.columns(3)
            cement_type = m1.text_input("Cement Type", value="CEM I 42.5 N Heidelberg")
            sand_mass = m2.number_input("Standard Sand (g)", value=1350.0)
            num_cubes = m3.number_input("Number of Cubes", value=12, step=1)
            
            # --- Fresh Properties ---
            st.subheader("2. Fresh Properties")
            f1, f2, f3 = st.columns(3)
            fresh_density = f1.number_input("Fresh Density (g/L)", value=2240.0)
            flow = f2.number_input("Flow (mm)", value=170.0)
            air = f3.number_input("Air Content (%)", value=2.0)
            
            # --- Hardened Properties (Averages) ---
            st.subheader("3. Compressive Strength (Average MPa)")
            st.caption("Enter the average strength calculated from Cube A/B/C")
            
            c1, c2, c3, c4 = st.columns(4)
            cs_12h = c1.number_input("12 Hours", step=0.1, format="%.2f", value=0.0)
            cs_16h = c2.number_input("16 Hours", step=0.1, format="%.2f", value=0.0)
            cs_1d = c3.number_input("1 Day", step=0.1, format="%.2f", value=0.0)
            cs_2d = c4.number_input("2 Days", step=0.1, format="%.2f", value=0.0)
            
            c5, c6, c7, c8 = st.columns(4)
            cs_3d = c5.number_input("3 Days", step=0.1, format="%.2f", value=0.0)
            cs_7d = c6.number_input("7 Days", step=0.1, format="%.2f", value=0.0)
            cs_28d = c7.number_input("28 Days", step=0.1, format="%.2f", value=0.0)
            
            # --- Curing Conditions ---
            st.subheader("4. Curing & Environment")
            e1, e2 = st.columns(2)
            cur_temp = e1.number_input("Curing Temp (°C)", value=20.0)
            cur_rh = e2.text_input("Curing RH (%)", value="90%")

            submitted = st.form_submit_button("💾 Save Results")
            
            if submitted:
                mix_meta = {
                    "cement_type": cement_type,
                    "cement_mass": c_mass,
                    "sand_mass": sand_mass,
                    "wc_ratio": target_wc,
                    "ng_dosage_pct": ng_dosage_pct,
                    "ng_dosage_g": dosage_wet_g,
                    "water_from_ng": water_from_ng,
                    "water_added_g": water_to_add,
                    "num_cubes": num_cubes
                }
                
                result = PerformanceTest(
                    batch_id=batch_select.id,
                    test_type="Mortar",
                    mix_design=mix_meta,
                    fresh_density=fresh_density,
                    flow=flow,
                    air_content=air,
                    temperature=cur_temp,
                    humidity=float(cur_rh.replace("%","")) if "%" in cur_rh else float(cur_rh),
                    compressive_strength_12h=cs_12h if cs_12h > 0 else None,
                    compressive_strength_16h=cs_16h if cs_16h > 0 else None,
                    compressive_strength_1d=cs_1d if cs_1d > 0 else None,
                    compressive_strength_2d=cs_2d if cs_2d > 0 else None,
                    compressive_strength_3d=cs_3d if cs_3d > 0 else None,
                    compressive_strength_7d=cs_7d if cs_7d > 0 else None,
                    compressive_strength_28d=cs_28d if cs_28d > 0 else None
                )
                db.add(result)
                db.commit()
                st.success("Test results saved successfully.")
