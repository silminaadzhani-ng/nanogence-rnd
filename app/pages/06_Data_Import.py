import streamlit as st
import pandas as pd
import datetime
import uuid
from sqlalchemy.orm import Session
from app.database import get_db, init_db
from app.models import Recipe, SynthesisBatch, PerformanceTest, RawMaterial, StockSolutionBatch, QCMeasurement
from app.ui_utils import display_logo

# Ensure database is synced
init_db()

st.set_page_config(page_title="Data Import", page_icon="📤", layout="wide")
display_logo()

st.markdown("# 📤 Bulk Data Import")
st.info("Import historical data from CSV, Excel, or Google Sheets.")

db: Session = next(get_db())

# Define import types and their expected columns (headers)
IMPORT_TYPES = {
    "Raw Materials": ["material_name", "chemical_type", "brand", "lot_number", "molecular_weight", "purity_percent", "initial_quantity_kg", "received_date"],
    "Stock Solutions": ["code", "chemical_type", "molarity", "target_volume_ml", "actual_mass_g", "preparation_date", "operator", "source_lot_number"],
    "Recipes": ["name", "ca_si_ratio", "molarity_ca", "molarity_si", "solids_percent", "pce_dosage", "target_ph"],
    "Synthesis Results": ["recipe_name", "batch_ref", "execution_date", "operator", "ph", "solids_measured", "strength_1d", "strength_28d", "flow"]
}

import_mode = st.selectbox("Select Import Category", options=list(IMPORT_TYPES.keys()))

with st.expander("📋 Expected Column Formats", expanded=False):
    st.write(f"For **{import_mode}**, your file should contain these headers:")
    st.code(", ".join(IMPORT_TYPES[import_mode]))
    st.caption("Note: Dates should be in YYYY-MM-DD format.")

tab1, tab2 = st.tabs(["📂 File Upload", "🌐 Google Sheet Link"])

df = None

with tab1:
    uploaded_file = st.file_uploader(f"Upload {import_mode} File", type=["csv", "xlsx"])
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                xls = pd.ExcelFile(uploaded_file)
                sheet_names = xls.sheet_names
                selected_sheet = st.selectbox("Select Sheet", options=sheet_names) if len(sheet_names) > 1 else sheet_names[0]
                df = pd.read_excel(uploaded_file, sheet_name=selected_sheet)
        except Exception as e:
            st.error(f"Error reading file: {e}")

with tab2:
    st.markdown("Paste your public Google Sheet link below (must be shared as 'Anyone with the link' or published as CSV).")
    sheet_url = st.text_input("Google Sheet Link", placeholder="Paste your Google Sheet URL here")
    if sheet_url:
        try:
            final_url = sheet_url
            if "docs.google.com/spreadsheets" in sheet_url:
                if "/export" not in sheet_url and "/pub" not in sheet_url:
                    import re
                    gid_match = re.search(r"gid=(\d+)", sheet_url)
                    gid = gid_match.group(1) if gid_match else "0"
                    base_url = sheet_url.split("/edit")[0]
                    final_url = f"{base_url}/export?format=csv&gid={gid}"
            df = pd.read_csv(final_url)
        except Exception as e:
            st.error(f"Error reading Google Sheet: {e}")

if df is not None:
    st.subheader("Data Preview")
    st.dataframe(df.head())
    
    if st.button(f"🚀 Confirm Import ({len(df)} rows)"):
        count = 0
        progress = st.progress(0)
        
        for i, row in df.iterrows():
            try:
                if import_mode == "Raw Materials":
                    new_rm = RawMaterial(
                        material_name=str(row.get("material_name", "")),
                        chemical_type=str(row.get("chemical_type", "Other")),
                        brand=str(row.get("brand", "Unknown")),
                        lot_number=str(row.get("lot_number", "")),
                        molecular_weight=float(row.get("molecular_weight", 100.0)),
                        purity_percent=float(row.get("purity_percent", 99.0)),
                        initial_quantity_kg=float(row.get("initial_quantity_kg", 0.0)),
                        remaining_quantity_kg=float(row.get("initial_quantity_kg", 0.0)),
                        received_date=pd.to_datetime(row.get("received_date", datetime.date.today()))
                    )
                    db.add(new_rm)
                    count += 1

                elif import_mode == "Stock Solutions":
                    lot = str(row.get("source_lot_number", ""))
                    rm = db.query(RawMaterial).filter(RawMaterial.lot_number == lot).first() if lot else None
                    new_ss = StockSolutionBatch(
                        code=str(row.get("code", "")),
                        chemical_type=str(row.get("chemical_type", "")),
                        molarity=float(row.get("molarity", 0.0)),
                        target_volume_ml=float(row.get("target_volume_ml", 0.0)),
                        actual_mass_g=float(row.get("actual_mass_g", 0.0)),
                        preparation_date=pd.to_datetime(row.get("preparation_date", datetime.date.today())),
                        operator=str(row.get("operator", "Import")),
                        raw_material_id=rm.id if rm else None
                    )
                    db.add(new_ss)
                    count += 1

                elif import_mode == "Recipes":
                    new_recipe = Recipe(
                        name=str(row.get("name", "")),
                        ca_si_ratio=float(row.get("ca_si_ratio", 1.0)),
                        molarity_ca_no3=float(row.get("molarity_ca", 1.5)),
                        molarity_na2sio3=float(row.get("molarity_si", 0.75)),
                        total_solid_content=float(row.get("solids_percent", 5.0)),
                        pce_content_wt=float(row.get("pce_dosage", 2.0)),
                        target_ph=float(row.get("target_ph", 11.5)),
                        created_by="Import"
                    )
                    db.add(new_recipe)
                    count += 1

                elif import_mode == "Synthesis Results":
                    r_name = str(row.get("recipe_name", ""))
                    recipe = db.query(Recipe).filter(Recipe.name == r_name).first()
                    if not recipe:
                        recipe = Recipe(name=r_name, created_by="Auto-Import")
                        db.add(recipe)
                        db.commit()

                    batch = SynthesisBatch(
                        recipe_id=recipe.id,
                        lab_notebook_ref=str(row.get("batch_ref", f"IMP-{uuid.uuid4().hex[:6]}")),
                        execution_date=pd.to_datetime(row.get("execution_date", datetime.date.today())),
                        operator=str(row.get("operator", "Import")),
                        status="Completed"
                    )
                    db.add(batch)
                    db.commit()

                    qc = QCMeasurement(
                        batch_id=batch.id,
                        ph=float(row.get("ph", 0)),
                        solid_content_measured=float(row.get("solids_measured", 0))
                    )
                    db.add(qc)

                    perf = PerformanceTest(
                        batch_id=batch.id,
                        test_type="Mortar",
                        compressive_strength_1d=float(row.get("strength_1d", 0)),
                        compressive_strength_28d=float(row.get("strength_28d", 0)),
                        flow=float(row.get("flow", 0))
                    )
                    db.add(perf)
                    count += 1

            except Exception as row_err:
                st.error(f"Error at row {i}: {row_err}")
            
            progress.progress((i + 1) / len(df))
        
        db.commit()
        st.success(f"Successfully imported {count} records into {import_mode}!")
        if st.button("Refresh Page"): st.rerun()
