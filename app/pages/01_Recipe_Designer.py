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
    m_ca = c3.number_input("Ca(NO3)2 Molarity (mol/L)", min_value=0.01, max_value=10.0, step=0.1, value=1.5)
    m_si = c4.number_input("Na2SiO3 Molarity (mol/L)", min_value=0.01, max_value=10.0, step=0.1, value=0.75)
    
    c5, c6 = st.columns(2)
    pce_dosage = c5.number_input("PCE Dosage", min_value=0.0, max_value=100.0, step=0.1, value=2.0)
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
    
    cv1, cv2 = st.columns(2)
    target_basis = cv1.selectbox("Target Basis", ["Total Volume (mL)", "Total Mass (g)"])
    target_val = cv2.number_input("Target Value", min_value=1.0, value=400.0)
    
    pce_basis = st.selectbox("PCE Dosage Basis", ["% of Ca(NO3)2 Mass", "% of Total Batch Mass"])
    
    exp_densities = st.expander("Solution Densities (g/mL)", expanded=False)
    d_ca = exp_densities.number_input("Ca Solution Density", value=1.150, format="%.3f")
    d_si = exp_densities.number_input("Si Solution Density", value=1.084, format="%.3f")
    d_pce = exp_densities.number_input("PCE Solution Density", value=1.080, format="%.3f")
    d_water = exp_densities.number_input("Water Density", value=0.998, format="%.3f")
    
    # Stoichiometric Calculation
    MW_SI = 122.06
    MW_CA = 164.09
    
    S = MW_SI + ca_si * MW_CA
    alpha = solids / 100.0
    pce_conc_factor = pce_conc / 100.0
    
    if target_basis == "Total Mass (g)":
        m_total = target_val
    else:
        if pce_basis == "% of Total Batch Mass":
            delta = pce_dosage / 100.0
        else:
            delta = (pce_dosage / 100.0) * (alpha * ca_si * MW_CA / S) / pce_conc_factor

        denom_pce = delta * (1.0 - (d_water / d_pce))
        denom_mineral = (alpha / S) * ( ((d_si - d_water) / m_si) + (ca_si * (d_ca - d_water) / m_ca) )
        denom = 1.0 - denom_pce - denom_mineral
        m_total = (target_val * d_water) / denom

    n_si_mol = (m_total * alpha) / S
    n_ca_mol = n_si_mol * ca_si
    m_ca_anhydrous = n_si_mol * ca_si * MW_CA
    
    v_si_ml = (n_si_mol * 1000) / m_si if m_si > 0 else 0
    v_ca_ml = (n_ca_mol * 1000) / m_ca if m_ca > 0 else 0
    
    mass_si_sol = v_si_ml * d_si
    mass_ca_sol = v_ca_ml * d_ca
    
    if pce_basis == "% of Total Batch Mass":
        mass_pce_sol = m_total * (pce_dosage / 100.0)
    else:
        mass_pce_sol = (m_ca_anhydrous * (pce_dosage / 100.0)) / pce_conc_factor
    
    v_pce_ml = mass_pce_sol / d_pce
    
    if target_basis == "Total Mass (g)":
        mass_water = m_total - mass_si_sol - mass_ca_sol - mass_pce_sol
        v_water_ml = mass_water / d_water
        v_total = v_si_ml + v_ca_ml + v_pce_ml + v_water_ml
    else:
        v_total = target_val
        v_water_ml = v_total - v_si_ml - v_ca_ml - v_pce_ml
        mass_water = v_water_ml * d_water
        m_total = mass_si_sol + mass_ca_sol + mass_pce_sol + mass_water

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
    c1, c2, c3 = st.columns(3)
    rate_ca = c1.number_input("Ca Addition Rate (mL/min)", value=0.5)
    rate_si = c2.number_input("Si Addition Rate (mL/min)", value=0.5)
    target_ph = c3.number_input("Target pH", value=11.5, step=0.1)
    
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

st.divider()
st.subheader("📚 Recipe Library")

# Search and Filters
c1, c2, c3 = st.columns([2, 1, 1])
search_query = c1.text_input("🔍 Search Recipe Name", placeholder="e.g. Trial A")
series_filter = c2.multiselect("Filter Series", options=["Series A", "Series B", "Series C", "Series D"], default=[])

query = db.query(Recipe).order_by(Recipe.name.asc())

if search_query:
    query = query.filter(Recipe.name.ilike(f"%{search_query}%"))

# Filter by series (using naming convention or Ca/Si ratio as proxy)
# ... (rest of filtering logic)
if series_filter:
    series_conditions = []
    if "Series A" in series_filter: series_conditions.append(Recipe.ca_si_ratio == 1.25)
    if "Series B" in series_filter: series_conditions.append(Recipe.ca_si_ratio == 1.50)
    if "Series C" in series_filter: series_conditions.append(Recipe.ca_si_ratio == 1.75)
    if "Series D" in series_filter: series_conditions.append(Recipe.ca_si_ratio == 2.00)
    from sqlalchemy import or_
    query = query.filter(or_(*series_conditions))

recipes = query.all()
c3.metric("Total Recipes", len(recipes))

if recipes:
    data = []
    for r in recipes:
        ca_batch = r.ca_stock_batch.code if r.ca_stock_batch else "N/A"
        si_batch = r.si_stock_batch.code if r.si_stock_batch else "N/A"
        data.append({
            "Name": r.name,
            "Date": r.recipe_date.strftime("%Y-%m-%d") if r.recipe_date else "N/A",
            "Ca/Si": r.ca_si_ratio,
            "Solids %": r.total_solid_content,
            "Ca M": r.molarity_ca_no3,
            "Si M": r.molarity_na2sio3,
            "PCE %": r.pce_content_wt,
            "Target pH": r.target_ph,
            "Ca Batch": ca_batch,
            "Si Batch": si_batch,
            "Ca Rate": r.ca_addition_rate,
            "Si Rate": r.si_addition_rate,
        })
    st.dataframe(data, use_container_width=True)
    
    with st.expander("🗑️ Delete Recipes", expanded=False):
        recipe_to_delete = st.selectbox("Select Recipe to Remove", options=[r.name for r in recipes], key="del_recipe")
        if st.button("Confirm Delete", type="primary"):
            target = db.query(Recipe).filter(Recipe.name == recipe_to_delete).first()
            if target:
                db.delete(target)
                db.commit()
                st.success(f"Recipe '{recipe_to_delete}' deleted.")
                st.rerun()
