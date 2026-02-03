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
                                m1, m2, m3, m4, m5, m6 = st.columns(6)
                                m1.metric("12h", f"{t.compressive_strength_12h or 0:.1f}")
                                m2.metric("1d", f"{t.compressive_strength_1d or 0:.1f}")
                                m3.metric("2d", f"{t.compressive_strength_2d or 0:.1f}")
                                m4.metric("7d", f"{t.compressive_strength_7d or 0:.1f}")
                                m5.metric("28d", f"{t.compressive_strength_28d or 0:.1f}")
                                m6.metric("Flow", f"{t.flow or 0:.0f}")

with tab_log:
    st.subheader("➕ Log New Performance Results")
    # Select Batch
    batches = db.query(SynthesisBatch).order_by(SynthesisBatch.execution_date.desc()).limit(50).all()
    batch_select = st.selectbox("Select Synthesis Batch to link results", options=batches, format_func=lambda x: f"{x.lab_notebook_ref} ({x.recipe.code if x.recipe else 'N/A'})")

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
