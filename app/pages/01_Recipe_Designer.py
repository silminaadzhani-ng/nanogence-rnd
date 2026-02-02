import streamlit as st
import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import get_db, init_db
from app.models import Recipe, StockSolutionBatch

# Ensure database is synced
init_db()
from app.ml_utils import predict_strength

st.set_page_config(page_title="Recipe Designer", page_icon="📝", layout="wide")

st.markdown("# 📝 Experimental Recipe Designer")

db: Session = next(get_db())

# --- Sidebar: AI Prediction ---
with st.sidebar:
    st.header("🧠 AI Predictor")
    st.info("Adjust parameters to see estimated 28d Strength.")

with st.expander("ℹ️  Instructions", expanded=False):
    st.info("Define the chemical composition, stock solutions, and synthesis process steps.")

# --- Form for Recipe Inputs ---
with st.form("recipe_form"):
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Chemical Composition")
        r_date = st.date_input("Recipe Date", value=datetime.today())
        name = st.text_input("Recipe Name", placeholder="e.g. CSH-Seed-Standard-2024")
        
        c1, c2 = st.columns(2)
        ca_si = c1.number_input("Ca/Si Ratio", min_value=0.0, max_value=2.5, step=0.05, value=1.0)
        solids = c2.number_input("Target Solid Content (%)", min_value=0.1, max_value=50.0, value=5.0)
        
        c3, c4 = st.columns(2)
        m_ca = c3.number_input("Ca Molarity (mol/L)", min_value=0.01, max_value=10.0, step=0.1, value=1.5)
        m_si = c4.number_input("Si Molarity (mol/L)", min_value=0.01, max_value=10.0, step=0.1, value=0.75)
        
        c5, c6 = st.columns(2)
        pce_dosage = c5.number_input("PCE Dosage (wt.% of solids)", min_value=0.0, max_value=50.0, step=0.1, value=2.0)
        pce_conc = c6.number_input("PCE Solution Conc. (wt.%)", min_value=1.0, max_value=100.0, value=50.0)

        st.subheader("🏢 Material Sourcing")
        s1, s2 = st.columns(2)
        source_ca = s1.text_input("Ca(NO3)2 Source", value="Carl Roth")
        source_si = s2.text_input("Na2SiO3 Source", value="Carl Roth")
        source_pce = st.text_input("PCE Brand/Source", value="Cromogenia PCX 50")

        st.subheader("🧪 Stock Solution Source")
        # Fetch available batches
        ca_batches = db.query(StockSolutionBatch).filter(StockSolutionBatch.chemical_type == "Ca").all()
        si_batches = db.query(StockSolutionBatch).filter(StockSolutionBatch.chemical_type == "Si").all()
        
        ca_opts = {f"{b.code} ({b.molarity}M)": b.id for b in ca_batches}
        si_opts = {f"{b.code} ({b.molarity}M)": b.id for b in si_batches}
        
        ca_batch_id = st.selectbox("Ca Stock Batch", options=["None"] + list(ca_opts.keys()))
        si_batch_id = st.selectbox("Si Stock Batch", options=["None"] + list(si_opts.keys()))

    with col2:
        st.subheader("📊 Mass Calculator (Real-time)")
        target_total_mass = st.number_input("Target Total Batch Mass (g)", min_value=1.0, value=400.0)
        
        # Densities (g/mL) - often needed for volume -> mass conversion
        # We can use defaults or let user override
        exp_densities = st.expander("Solution Densities (g/mL)", expanded=False)
        d_ca = exp_densities.number_input("Ca Solution Density", value=1.2, step=0.01)
        d_si = exp_densities.number_input("Si Solution Density", value=1.1, step=0.01)
        
        # Calculation Logic
        target_solids_g = (solids / 100.0) * target_total_mass
        
        # MW assumptions for yield calculation (simplified stoichiometric yield)
        # Assuming C-S-H (C-S-H I/II average)
        # Yield is driven by Si (limiting) + Ca + OH
        # For simplify: Moles Si = target_solids_g / (MW_CSH_equivalent)
        # But user gave exact masses in example. Let's use a simpler "Scaling" approach if possible.
        # Fixed logic from user example:
        # If we know Ca/Si, Molarity Si, Molarity Ca:
        # n_si = volume_si * m_si
        # n_ca = n_si * ca_si
        # volume_ca = n_ca / m_ca
        # volume_si = ?
        
        # Alternative: We solve for volume_si based on the fact that 
        # m_solids = m_csh + m_pce_solid
        # This gets complex without knowing CSH chemistry.
        # User example: 415g total, 5% solid -> ~20g solids.
        # If we use the provided masses as a baseline and scale:
        pce_mass_g = (pce_dosage / 100.0) * target_solids_g / (pce_conc / 100.0)
        
        # Heuristic: 1 mole of Si roughly contributes ~120-150g to CSH solids depending on hydration
        mw_csh_per_si = 75 + ca_si * 56 + 18 # Simplified Si + Ca + H2O
        moles_si_needed = (target_solids_g - (pce_dosage/100.0)*target_solids_g) / mw_csh_per_si
        
        v_si_ml = moles_si_needed * 1000 / m_si if m_si > 0 else 0
        v_ca_ml = (moles_si_needed * ca_si) * 1000 / m_ca if m_ca > 0 else 0
        
        mass_si_sol = v_si_ml * d_si
        mass_ca_sol = v_ca_ml * d_ca
        mass_pce_sol = pce_mass_g
        mass_water = target_total_mass - mass_si_sol - mass_ca_sol - mass_pce_sol
        
        # Determine display sources (Batch code vs Brand)
        display_source_ca = ca_batch_id if ca_batch_id != "None" else source_ca
        display_source_si = si_batch_id if si_batch_id != "None" else source_si

        calc_data = [
            {"Ingredient": "Na2SiO3 Solution", "Source": display_source_si, "Conc.": f"{m_si} M", "Mass (g)": f"{mass_si_sol:.2f}"},
            {"Ingredient": "Ca(NO3)2 Solution", "Source": display_source_ca, "Conc.": f"{m_ca} M", "Mass (g)": f"{mass_ca_sol:.2f}"},
            {"Ingredient": "PCE Solution", "Source": source_pce, "Conc.": f"{pce_conc}%", "Mass (g)": f"{mass_pce_sol:.2f}"},
            {"Ingredient": "DI Water", "Source": "DI", "Conc.": "-", "Mass (g)": f"{mass_water:.2f}"},
            {"Ingredient": "TOTAL", "Source": "-", "Conc.": "-", "Mass (g)": f"{target_total_mass:.2f}"},
        ]
        st.table(calc_data)

        st.divider()
        st.subheader("Process Parameters")
        c1, c2 = st.columns(2)
        rate_ca = c1.number_input("Ca Addition Rate (mL/min)", value=0.5)
        rate_si = c2.number_input("Si Addition Rate (mL/min)", value=0.5)
        
        st.caption("Synthesis Procedure")
        procedure_notes = st.text_area("Procedure Notes", placeholder="e.g. 1. Dissolve PCX...\n2. Start feeding...", height=150)
        
        # Prediction
        p1d = predict_strength(ca_si, m_ca, solids, pce_dosage, target='1d')
        p28d = predict_strength(ca_si, m_ca, solids, pce_dosage, target='28d')
        
        c1, c2 = st.columns(2)
        if p1d is not None:
            c1.metric(label="Predicted 1d Strength", value=f"{p1d:.1f} MPa")
        if p28d is not None:
            c2.metric(label="Predicted 28d Strength", value=f"{p28d:.1f} MPa")

    submitted = st.form_submit_button("💾 Save Recipe")

    if submitted:
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

# --- List Recipes ---
st.divider()
st.subheader("📚 Recipe Library")
recipes = db.query(Recipe).order_by(Recipe.created_at.desc()).all()
if recipes:
    data = []
    for r in recipes:
        data.append({
            "Name": r.name,
            "Date": r.recipe_date.strftime("%Y-%m-%d") if r.recipe_date else "N/A",
            "Ca/Si": r.ca_si_ratio,
            "Ca Add. Rate": r.ca_addition_rate,
            "Si Add. Rate": r.si_addition_rate
        })
    st.dataframe(data, use_container_width=True)
