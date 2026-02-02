import streamlit as st
import json
from datetime import datetime
import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db, init_db
from app.models import Recipe, StockSolutionBatch, RawMaterial
from app.ui_utils import display_logo
import uuid
from app.ml_utils import predict_strength

# Ensure database is synced
init_db()

st.set_page_config(page_title="Recipe Designer", page_icon="📝", layout="wide")
display_logo()

st.markdown("# 📝 Experimental Recipe Designer")

db: Session = next(get_db())

# Function to generate unique recipe code
def generate_recipe_code():
    today_str = datetime.now().strftime("%Y%m%d")
    prefix = f"REC-{today_str}-"
    count = db.query(Recipe).filter(Recipe.code.like(f"{prefix}%")).count()
    return f"{prefix}{count + 1:02d}"

# Handle Edit Mode Session State
if 'edit_recipe_id' not in st.session_state:
    st.session_state.edit_recipe_id = None

edit_recipe = None
if st.session_state.edit_recipe_id:
    # Use UUID to quarry
    edit_recipe = db.query(Recipe).filter(Recipe.id == st.session_state.edit_recipe_id).first()
    if not edit_recipe:
        st.warning("Recipe not found. Exiting edit mode.")
        st.session_state.edit_recipe_id = None

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
        
        # Determine default values based on Edit Mode or Standard Defaults
        d_date = edit_recipe.recipe_date.date() if edit_recipe else datetime.today()
        d_name = edit_recipe.name if edit_recipe else ""
        d_code = edit_recipe.code if edit_recipe else generate_recipe_code()
        
        # Defaults
        d_casi = edit_recipe.ca_si_ratio if edit_recipe else 1.50
        d_solids = edit_recipe.total_solid_content if edit_recipe else 5.0
        d_m_ca = edit_recipe.molarity_ca_no3 if edit_recipe else 1.5
        d_m_si = edit_recipe.molarity_na2sio3 if edit_recipe else 0.75
        d_pce_dosage = edit_recipe.pce_content_wt if edit_recipe else 2.5
        d_pce_conc = 50.0 

        c_code, c_date = st.columns([1, 2])
        c_code.caption(f"ID: **{d_code}**")
        r_date = c_date.date_input("Recipe Date", value=d_date)
        
        name = st.text_input("Recipe Name", value=d_name, placeholder="e.g. CSH-Seed-Standard-2024")
        
        c1, c2 = st.columns(2)
        ca_si = c1.number_input("Ca/Si Ratio", min_value=0.0, max_value=2.5, step=0.05, value=d_casi)
        solids = c2.number_input("Target Solid Content (%)", min_value=0.1, max_value=50.0, value=d_solids)
        
        c3, c4 = st.columns(2)
        m_ca = c3.number_input("Ca(NO3)2 Molarity (mol/L)", min_value=0.01, max_value=10.0, step=0.1, value=d_m_ca)
        m_si = c4.number_input("Na2SiO3 Molarity (mol/L)", min_value=0.01, max_value=10.0, step=0.1, value=d_m_si)
        
        c5, c6 = st.columns(2)
        pce_dosage = c5.number_input("PCE Dosage (%)", min_value=0.0, max_value=100.0, step=0.1, value=d_pce_dosage)
        pce_conc = c6.number_input("PCE Solution Conc. (wt.%)", min_value=1.0, max_value=100.0, value=d_pce_conc)

        st.subheader("🧪 Material & Stock Source")
        ca_batches = db.query(StockSolutionBatch).filter(StockSolutionBatch.chemical_type == "Ca").all()
        si_batches = db.query(StockSolutionBatch).filter(StockSolutionBatch.chemical_type == "Si").all()
        pce_materials = db.query(RawMaterial).filter(RawMaterial.chemical_type == "PCE").all()
        
        ca_opts = {f"{b.code} ({b.molarity}M)": b.id for b in ca_batches}
        si_opts = {f"{b.code} ({b.molarity}M)": b.id for b in si_batches}
        pce_opts = {f"{m.material_name} (Lot: {m.lot_number})": m.brand for m in pce_materials}
        
        # Initial selection indexes for edit mode
        def_ca_idx = 0
        def_si_idx = 0
        def_pce_idx = 0
        
        if edit_recipe:
            if edit_recipe.ca_stock_batch_id:
                for i, bid in enumerate(ca_opts.values()):
                    if bid == edit_recipe.ca_stock_batch_id: def_ca_idx = i + 1; break
            if edit_recipe.si_stock_batch_id:
                for i, bid in enumerate(si_opts.values()):
                    if bid == edit_recipe.si_stock_batch_id: def_si_idx = i + 1; break
            # Pce matching would required exact string match on source dict if we stored keys, but we stored result strings.
            # Skipping complex reverse lookup for PCE source string to ID for now.
        
        ca_batch_selection = st.selectbox("Ca Stock Batch", options=["None"] + list(ca_opts.keys()), index=def_ca_idx)
        si_batch_selection = st.selectbox("Si Stock Batch", options=["None"] + list(si_opts.keys()), index=def_si_idx)
        pce_selection = st.selectbox("PCE Material Source", options=["None"] + list(pce_opts.keys()), index=def_pce_idx)

        # Fetch Brands automatically
        sel_ca_batch = db.query(StockSolutionBatch).filter(StockSolutionBatch.id == ca_opts.get(ca_batch_selection)).first()
        sel_si_batch = db.query(StockSolutionBatch).filter(StockSolutionBatch.id == si_opts.get(si_batch_selection)).first()
        
        source_ca = sel_ca_batch.raw_material.brand if sel_ca_batch and sel_ca_batch.raw_material else "N/A"
        source_si = sel_si_batch.raw_material.brand if sel_si_batch and sel_si_batch.raw_material else "N/A"
        source_pce = pce_opts.get(pce_selection, "N/A")

        st.subheader("🏢 Material Sourcing (Auto)")
        st.info(f"**Ca Source:** {source_ca} | **Si Source:** {source_si} | **PCE Source:** {source_pce}")

    with col2:
        st.subheader("📊 Mass Calculator (Real-time)")
        
        target_val = st.number_input("Target Total Batch Mass (g)", min_value=1.0, value=415.0)
        
        exp_densities = st.expander("Solution Densities (g/mL)", expanded=False)
        d_ca = exp_densities.number_input("Ca Solution Density", value=1.150, format="%.3f")
        d_si = exp_densities.number_input("Si Solution Density", value=1.084, format="%.3f")
        d_pce = exp_densities.number_input("PCE Solution Density", value=1.080, format="%.3f")
        d_water = exp_densities.number_input("Water Density", value=0.998, format="%.3f")
        
        # Stoichiometric Calculation
        # MW used for Na2SiO3 (Anhydrous) and Ca(NO3)2 (Anhydrous)
        MW_SI = 122.06
        MW_CA = 164.09
        st.caption(f"Using MW: Na2SiO3={MW_SI}, Ca(NO3)2={MW_CA}")
        S = MW_SI + ca_si * MW_CA
        pce_conc_factor = pce_conc / 100.0
        # 1. Total Mass is the anchor
        m_total = target_val
        
        # 2. Calculate Mineral Mass based on Target Solids %
        # Interpretation: Target Solids % = (Mass of Anhydrous Ca + Mass of Anhydrous Si) / Total Batch Mass
        target_mineral_mass = m_total * (solids / 100.0)
        
        # target_mineral_mass = n_si * MW_SI + n_ca * MW_CA
        #                     = n_si * MW_SI + (n_si * ca_si) * MW_CA
        #                     = n_si * (MW_SI + ca_si * MW_CA)
        
        if S > 0:
            n_si_mol = target_mineral_mass / S
        else:
            n_si_mol = 0
            
        n_ca_mol = n_si_mol * ca_si
        m_ca_anhydrous = n_ca_mol * MW_CA
        
        # 3. Calculate PCE Mass (Always % of Total Batch Mass)
        mass_pce_sol = m_total * (pce_dosage / 100.0)

        # 4. Calculate Solution Volumes
        v_si_ml = (n_si_mol * 1000) / m_si if m_si > 0 else 0
        v_ca_ml = (n_ca_mol * 1000) / m_ca if m_ca > 0 else 0
        v_pce_ml = mass_pce_sol / d_pce
        
        # 5. Calculate Solution Masses
        mass_si_sol = v_si_ml * d_si
        mass_ca_sol = v_ca_ml * d_ca
        
        # 6. Water is the remainder
        mass_water = m_total - mass_si_sol - mass_ca_sol - mass_pce_sol
        v_water_ml = mass_water / d_water
        
        v_total = v_si_ml + v_ca_ml + v_pce_ml + v_water_ml

        display_source_ca = ca_batch_selection if ca_batch_selection != "None" else "Manual"
        display_source_si = si_batch_selection if si_batch_selection != "None" else "Manual"

        # Calculate solid masses for table display
        solid_mass_si = (n_si_mol * MW_SI) / 1000.0 * 1000.0 # g
        solid_mass_ca = m_ca_anhydrous # g
        solid_mass_pce = mass_pce_sol * pce_conc_factor # g

        calc_data = [
            {
                "Ingredient": "Na2SiO3 Sol.", 
                "Mass (g)": f"{mass_si_sol:.2f}", 
                "Mass %": f"{(mass_si_sol/m_total*100):.1f}%", 
                "Vol (mL)": f"{v_si_ml:.2f}", 
                "Mole (mmol)": f"{n_si_mol*1000:.2f}",
                "Solid (g)": f"{v_si_ml * m_si * MW_SI / 1000.0:.2f}", # Recalculated for check
                "Solid %": f"{(v_si_ml * m_si * MW_SI / 1000.0 / m_total * 100):.2f}%"
            },
            {
                "Ingredient": "Ca(NO3)2 Sol.", 
                "Mass (g)": f"{mass_ca_sol:.2f}", 
                "Mass %": f"{(mass_ca_sol/m_total*100):.1f}%", 
                "Vol (mL)": f"{v_ca_ml:.2f}", 
                "Mole (mmol)": f"{n_ca_mol*1000:.2f}",
                "Solid (g)": f"{m_ca_anhydrous:.2f}",
                "Solid %": f"{(m_ca_anhydrous/m_total*100):.2f}%"
            },
            {
                "Ingredient": "PCE Sol.", 
                "Mass (g)": f"{mass_pce_sol:.2f}", 
                "Mass %": f"{(mass_pce_sol/m_total*100):.1f}%", 
                "Vol (mL)": f"{v_pce_ml:.2f}", 
                "Mole (mmol)": "-",
                "Solid (g)": f"{solid_mass_pce:.2f}",
                "Solid %": f"{(solid_mass_pce/m_total*100):.2f}%"
            },
            {
                "Ingredient": "DI Water", 
                "Mass (g)": f"{mass_water:.2f}", 
                "Mass %": f"{(mass_water/m_total*100):.1f}%", 
                "Vol (mL)": f"{v_water_ml:.2f}", 
                "Mole (mmol)": "-",
                "Solid (g)": "-",
                "Solid %": "-"
            },
            {
                "Ingredient": "TOTAL", 
                "Mass (g)": f"{m_total:.2f}", 
                "Mass %": "100.0%", 
                "Vol (mL)": f"{v_total:.1f}", 
                "Mole (mmol)": "-",
                "Solid (g)": f"{solid_mass_si + m_ca_anhydrous + solid_mass_pce:.2f}",
                "Solid %": f"{( (solid_mass_si + m_ca_anhydrous + solid_mass_pce)/m_total*100 ):.2f}%"
            },
        ]
        # Using dataframe to hide the index column
        st.dataframe(calc_data, use_container_width=True, hide_index=True)
        
        st.caption(f"Theoretical n_Si: {n_si_mol*1000:.2f} mmol | n_Ca: {n_ca_mol*1000:.2f} mmol | PCE solid: {mass_pce_sol * pce_conc_factor:.2f} g")

    st.divider()
    st.divider()
    st.subheader("Process Parameters")
    
    # Defaults from edit_recipe if available
    d_rate_ca = edit_recipe.ca_addition_rate if edit_recipe else 0.5
    d_rate_si = edit_recipe.si_addition_rate if edit_recipe else 0.5
    d_target_ph = edit_recipe.target_ph if edit_recipe else 11.5
    d_notes = edit_recipe.process_config.get("procedure", "") if edit_recipe and edit_recipe.process_config else ""
    
    cp_c1, cp_c2, cp_c3 = st.columns(3)
    rate_ca = cp_c1.number_input("Ca Addition Rate (mL/min)", value=d_rate_ca)
    rate_si = cp_c2.number_input("Si Addition Rate (mL/min)", value=d_rate_si)
    target_ph = cp_c3.number_input("Target pH", value=d_target_ph, step=0.1)
    
    procedure_notes = st.text_area("Procedure Notes", value=d_notes, placeholder="e.g. 1. Dissolve PCX...\n2. Start feeding...", height=150)
    
    p1d = predict_strength(ca_si, m_ca, solids, pce_dosage, target='1d')
    p28d = predict_strength(ca_si, m_ca, solids, pce_dosage, target='28d')
    
    cp1, cp2 = st.columns(2)
    if p1d is not None:
        cp1.metric(label="Predicted 1d Strength", value=f"{p1d:.1f} MPa")
    if p28d is not None:
        cp2.metric(label="Predicted 28d Strength", value=f"{p28d:.1f} MPa")

    st.divider()
    
    # Button Text changes based on context
    btn_label = "🔄 Update Recipe" if edit_recipe else "💾 Save New Recipe"
    col_a, col_b = st.columns([1, 4])
    
    if edit_recipe:
        if col_a.button("❌ Cancel Edit"):
            st.session_state.edit_recipe_id = None
            st.rerun()

    if col_b.button(btn_label, type="primary"):
        if not name:
            st.error("Recipe Name is required.")
        else:
            try:
                proc_config = {"procedure": procedure_notes}
                sources = {"ca": source_ca, "si": source_si, "pce": source_pce}
                
                if edit_recipe:
                    # UPDATE EXISTING
                    edit_recipe.name = name
                    edit_recipe.recipe_date = datetime.combine(r_date, datetime.min.time())
                    edit_recipe.ca_si_ratio = ca_si
                    edit_recipe.molarity_ca_no3 = m_ca
                    edit_recipe.molarity_na2sio3 = m_si
                    edit_recipe.total_solid_content = solids
                    edit_recipe.pce_content_wt = pce_dosage
                    edit_recipe.material_sources = sources
                    edit_recipe.ca_addition_rate = rate_ca
                    edit_recipe.si_addition_rate = rate_si
                    edit_recipe.target_ph = target_ph
                    edit_recipe.ca_stock_batch_id = ca_opts.get(ca_batch_selection)
                    edit_recipe.si_stock_batch_id = si_opts.get(si_batch_selection)
                    edit_recipe.process_config = proc_config
                    # Keep existing code and created_by
                    
                    db.commit()
                    st.success(f"Recipe '{name}' updated successfully!")
                    st.session_state.edit_recipe_id = None # Exit edit mode
                    st.rerun()
                else:
                    # CREATE NEW
                    new_recipe = Recipe(
                        name=name,
                        code=d_code, # Use the generated code
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
                        ca_stock_batch_id=ca_opts.get(ca_batch_selection),
                        si_stock_batch_id=si_opts.get(si_batch_selection),
                        process_config=proc_config,
                        created_by="Silmina Adzhani"
                    )
                    db.add(new_recipe)
                    db.commit()
                    st.success(f"Recipe '{name}' ({d_code}) saved!")
                    st.rerun()
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
                    "Code": r.code if r.code else "N/A",
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
            # Reorder columns to show Code first
            df_lib = pd.DataFrame(lib_data)
            cols = ["Code", "Name", "Date"] + [c for c in df_lib.columns if c not in ["Code", "Name", "Date"]]
            st.dataframe(df_lib[cols], use_container_width=True, hide_index=True)
            
            with st.expander("⚙️ Manage Recipes (Edit / Delete)", expanded=False):
                # Create a comprehensive label for selection
                recipe_map = {f"{r.code} - {r.name}": r.id for r in recipes}
                selected_label = st.selectbox("Select Recipe", options=list(recipe_map.keys()), key="manage_recipe_sel")
                
                if selected_label:
                    selected_id = recipe_map[selected_label]
                    
                    c_edit, c_del = st.columns(2)
                    
                    if c_edit.button("✏️ Edit This Recipe"):
                        st.session_state.edit_recipe_id = selected_id
                        st.switch_page("pages/02_Recipe_Designer.py") # Force reload/navigate
                        
                    if c_del.button("🗑️ Delete This Recipe", type="primary"):
                        target = db.query(Recipe).filter(Recipe.id == selected_id).first()
                        if target:
                            db.delete(target)
                            db.commit()
                            st.success(f"Recipe '{selected_label}' deleted.")
                            st.rerun()
    else:
        st.info("No recipes found in the library.")
