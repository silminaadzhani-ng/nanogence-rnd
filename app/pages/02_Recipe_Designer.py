import streamlit as st
import json
from datetime import datetime
import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db, init_db
from app.models import Recipe, StockSolutionBatch
from app.ui_utils import display_logo
from app.ml_utils import predict_strength

# Ensure database is synced
init_db()

st.set_page_config(page_title="Recipe Designer", page_icon="📝", layout="wide")
display_logo()

st.markdown("# 📝 Experimental Recipe Designer")

db: Session = next(get_db())

# --- Sidebar: AI Prediction ---
with st.sidebar:
    st.header("🧠 AI Predictor")
    st.info("Adjust parameters to see estimated 28d Strength.")

tab_dash, tab1, tab2 = st.tabs(["📊 Dashboard", "➕ Designer & Calculator", "📚 Recipe Library"])

with tab_dash:
    st.subheader("Recipe Analytics")
    col1, col2, col3 = st.columns(3)
    
    total_recipes = db.query(Recipe).count()
    avg_solids = db.query(func.avg(Recipe.total_solid_content)).scalar() or 0
    
    col1.metric("Total Recipes", total_recipes)
    col2.metric("Avg solids (%)", f"{avg_solids:.2f}")
    col3.metric("Last Recipe", db.query(Recipe.name).order_by(Recipe.id.desc()).first()[0] if total_recipes > 0 else "N/A")

    if total_recipes > 0:
        recipe_data = db.query(Recipe.ca_si_ratio).all()
        df_recipes = pd.DataFrame(recipe_data, columns=["Ca/Si Ratio"])
        st.subheader("Ca/Si Ratio Distribution")
        st.bar_chart(df_recipes["Ca/Si Ratio"].value_counts())

with tab1:
    with st.expander("ℹ️  Instructions", expanded=False):
        st.info("Define the chemical composition, stock solutions, and synthesis process steps.")

    # --- Recipe Inputs ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Chemical Composition")
        r_date = st.date_input("Recipe Date", value=datetime.today())
        name = st.text_input("Recipe Name", placeholder="e.g. CSH-Seed-Standard-2024")
        
        c1, c2 = st.columns(2)
        ca_si = c1.number_input("Ca/Si Ratio", min_value=0.0, max_value=2.5, step=0.05, value=1.0)
        solids = c2.number_input("Target Solid Content (%)", min_value=0.1, max_value=50.0, value=5.0)
        
        c3, c4 = st.columns(2)
        m_ca = c3.number_input("Ca(NO3)2 Molarity (mol/L)", min_value=0.01, max_value=10.0, step=0.1, value=4.0)
        m_si = c4.number_input("Na2SiO3 Molarity (mol/L)", min_value=0.01, max_value=10.0, step=0.1, value=2.0)
        
        c5, c6 = st.columns(2)
        pce_dosage = c5.number_input("PCE Dosage (wt.% of total)", min_value=0.0, max_value=100.0, step=0.1, value=1.25)
        pce_conc = c6.number_input("PCE Solution Conc. (wt.%)", min_value=1.0, max_value=100.0, value=50.0)

        st.subheader("🏢 Material Sourcing")
        s1, s2 = st.columns(2)
        source_ca = s1.text_input("Ca(NO3)2 Source", value="Carl Roth")
        source_si = s2.text_input("Na2SiO3 Source", value="Carl Roth")
        source_pce = st.text_input("PCE Brand/Source", value="Cromogenia PCX 50")

        st.subheader("🧪 Stock Solution Source")
        ca_batches = db.query(StockSolutionBatch).filter(StockSolutionBatch.chemical_type == "Ca").all()
        si_batches = db.query(StockSolutionBatch).filter(StockSolutionBatch.chemical_type == "Si").all()
        
        ca_opts = {f"{b.code} ({b.molarity}M)": b.id for b in ca_batches}
        si_opts = {f"{b.code} ({b.molarity}M)": b.id for b in si_batches}
        
        ca_batch_id = st.selectbox("Ca Stock Batch", options=["None"] + list(ca_opts.keys()))
        si_batch_id = st.selectbox("Si Stock Batch", options=["None"] + list(si_opts.keys()))

    with col2:
        st.subheader("📊 Mass Calculator (Real-time)")
        
        target_val = st.number_input("Target Total Batch Mass (g)", min_value=1.0, value=415.0)
        
        exp_densities = st.expander("Solution Densities (g/mL)", expanded=False)
        d_ca = exp_densities.number_input("Ca Solution Density", value=1.401, format="%.3f")
        d_si = exp_densities.number_input("Si Solution Density", value=1.230, format="%.3f")
        d_pce = exp_densities.number_input("PCE Solution Density", value=1.080, format="%.3f")
        d_water = exp_densities.number_input("Water Density", value=0.998, format="%.3f")
        
        # Stoichiometric Calculation
        MW_SI = 122.06
        MW_CA = 164.09
        
        S = MW_SI + ca_si * MW_CA
        alpha = solids / 100.0
        pce_conc_factor = pce_conc / 100.0
        
        # Fixed to Total Mass (g)
        m_total = target_val
        
        # Fixed to % of Total Batch Mass
        mass_pce_sol = m_total * (pce_dosage / 100.0)
        v_pce_ml = mass_pce_sol / d_pce
        
        # Calculate minerals based on target solids and remaining available mass
        # Note: In C-S-H synthesis, we usually assume the target solids percentage 
        # is the total mineral content (C-S-H phase) relative to total batch mass.
        n_si_mol = (m_total * alpha) / S
        n_ca_mol = n_si_mol * ca_si
        
        v_si_ml = (n_si_mol * 1000) / m_si if m_si > 0 else 0
        v_ca_ml = (n_ca_mol * 1000) / m_ca if m_ca > 0 else 0
        
        mass_si_sol = v_si_ml * d_si
        mass_ca_sol = v_ca_ml * d_ca
        
        mass_water = m_total - mass_si_sol - mass_ca_sol - mass_pce_sol
        v_water_ml = mass_water / d_water
        v_total = v_si_ml + v_ca_ml + v_pce_ml + v_water_ml

        display_source_ca = ca_batch_id if ca_batch_id != "None" else source_ca
        display_source_si = si_batch_id if si_batch_id != "None" else source_si

        calc_data = [
            {"Ingredient": "Na2SiO3 Solution", "Source": display_source_si, "Conc.": f"{m_si} M", "Mass (g)": f"{mass_si_sol:.2f}"},
            {"Ingredient": "Ca(NO3)2 Solution", "Source": display_source_ca, "Conc.": f"{m_ca} M", "Mass (g)": f"{mass_ca_sol:.2f}"},
            {"Ingredient": "PCE Solution", "Source": source_pce, "Conc.": f"{pce_conc}%", "Mass (g)": f"{mass_pce_sol:.2f}"},
            {"Ingredient": "DI Water", "Source": "DI", "Conc.": f"{d_water:.3f} g/mL", "Mass (g)": f"{mass_water:.2f}"},
            {"Ingredient": "TOTAL", "Source": "BATCH", "Conc.": f"{v_total:.1f} mL", "Mass (g)": f"{m_total:.2f}"},
        ]
        st.table(calc_data)
        st.caption(f"Theoretical n_Si: {n_si_mol*1000:.2f} mmol | n_Ca: {n_ca_mol*1000:.2f} mmol | PCE solid: {mass_pce_sol * pce_conc_factor:.2f} g")

    st.divider()
    st.subheader("Process Parameters")
    cp_c1, cp_c2, cp_c3 = st.columns(3)
    rate_ca = cp_c1.number_input("Ca Addition Rate (mL/min)", value=0.5)
    rate_si = cp_c2.number_input("Si Addition Rate (mL/min)", value=0.5)
    target_ph = cp_c3.number_input("Target pH", value=11.5, step=0.1)
    
    procedure_notes = st.text_area("Procedure Notes", placeholder="e.g. 1. Dissolve PCX...\n2. Start feeding...", height=150)
    
    p1d = predict_strength(ca_si, m_ca, solids, pce_dosage, target='1d')
    p28d = predict_strength(ca_si, m_ca, solids, pce_dosage, target='28d')
    
    cp1, cp2 = st.columns(2)
    if p1d is not None:
        cp1.metric(label="Predicted 1d Strength", value=f"{p1d:.1f} MPa")
    if p28d is not None:
        cp2.metric(label="Predicted 28d Strength", value=f"{p28d:.1f} MPa")

    st.divider()
    if st.button("💾 Save Recipe"):
        if not name:
            st.error("Recipe Name is required.")
        else:
            try:
                proc_config = {"procedure": procedure_notes}
                sources = {"ca": source_ca, "si": source_si, "pce": source_pce}
                new_recipe = Recipe(
                    name=name,
                    recipe_date=datetime.combine(r_date, datetime.min.time()),
                    ca_si_ratio=ca_si,
                    molarity_ca_no3=m_ca,
                    molarity_na2sio3=m_si,
                    total_solid_content=solids,
                    pce_content_wt=pce_dosage,
                    material_sources=sources,
                    ca_addition_rate=rate_ca,
                    si_addition_rate=rate_si,
                    target_ph=target_ph,
                    ca_stock_batch_id=ca_opts.get(ca_batch_id),
                    si_stock_batch_id=si_opts.get(si_batch_id),
                    process_config=proc_config,
                    created_by="Silmina Adzhani"
                )
                db.add(new_recipe)
                db.commit()
                st.success(f"Recipe '{name}' saved!")
            except Exception as e:
                st.error(f"Error: {str(e)}")

with tab2:
    st.subheader("📚 Recipe Library")

    # Filter Bar
    f1, f2 = st.columns([3, 1])
    search_query = f1.text_input("🔍 Search Recipe Name", placeholder="e.g. Trial A1", key="lib_search")

    # Build Query
    query = db.query(Recipe).order_by(Recipe.name.asc())

    if search_query:
        query = query.filter(Recipe.name.ilike(f"%{search_query}%"))

    recipes = query.all()
    f2.metric("Total Recipes", len(recipes))

    if recipes:
        lib_data = []
        for r in recipes:
            try:
                ca_batch_code = r.ca_stock_batch.code if r.ca_stock_batch else "N/A"
                si_batch_code = r.si_stock_batch.code if r.si_stock_batch else "N/A"
                lib_data.append({
                    "Name": r.name,
                    "Date": r.recipe_date.strftime("%Y-%m-%d") if r.recipe_date else "N/A",
                    "Ca/Si": r.ca_si_ratio,
                    "Solids %": r.total_solid_content,
                    "Ca M": r.molarity_ca_no3,
                    "Si M": r.molarity_na2sio3,
                    "PCE %": r.pce_content_wt,
                    "Target pH": r.target_ph,
                    "Ca Batch": ca_batch_code,
                    "Si Batch": si_batch_code,
                    "Ca Rate": r.ca_addition_rate,
                    "Si Rate": r.si_addition_rate,
                })
            except Exception as e:
                st.error(f"Error loading recipe '{r.name}': {e}")
        
        if lib_data:
            st.dataframe(lib_data, use_container_width=True)
            
            with st.expander("🗑️ Delete Recipes", expanded=False):
                recipe_to_delete = st.selectbox("Select Recipe to Remove", options=[r.name for r in recipes], key="del_recipe")
                if st.button("Confirm Delete", type="primary"):
                    target = db.query(Recipe).filter(Recipe.name == recipe_to_delete).first()
                    if target:
                        db.delete(target)
                        db.commit()
                        st.success(f"Recipe '{recipe_to_delete}' deleted.")
                        st.rerun()
    else:
        st.info("No recipes found in the library.")
