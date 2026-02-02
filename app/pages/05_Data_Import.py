import streamlit as st
import pandas as pd
import datetime
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Recipe, SynthesisBatch, PerformanceTest

st.set_page_config(page_title="Data Import", page_icon="📤", layout="wide")

st.markdown("# 📤 Bulk Data Import")
st.info("Import data from Excel/CSV files or directly from a Google Sheet.")

db: Session = next(get_db())

tab1, tab2 = st.tabs(["📂 File Upload", "🌐 Google Sheet"])

df = None

with tab1:
    uploaded_file = st.file_uploader("Choose a file", type=["csv", "xlsx"])
    if uploaded_file:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

with tab2:
    st.markdown("""
    **Instructions**:
    1. Open your Google Sheet.
    2. Click **File > Share > Publish to web**.
    3. Select your sheet and choose **Comma-separated values (.csv)**.
    4. Paste the generated link below.
    """)
    sheet_url = st.text_input("Public CSV Link")
    if sheet_url:
        try:
            df = pd.read_csv(sheet_url)
        except Exception as e:
            st.error(f"Error reading URL: {e}")

if df is not None:
    st.write("### Preview")
    st.dataframe(df.head())
        
        st.warning("⚠️ Ensure your columns match the expected format: `Recipe`, `BatchRef`, `Strength_1d`, `Strength_28d`, etc.")
        
        if st.button("Run Import"):
            count = 0
            progress_bar = st.progress(0)
            
            # Simple heuristic import logic
            for i, row in df.iterrows():
                # 1. Get or Create Recipe
                r_name = str(row.get("Recipe", "Imported Recipe"))
                recipe = db.query(Recipe).filter(Recipe.name == r_name).first()
                if not recipe:
                    recipe = Recipe(name=r_name, created_by="Import")
                    db.add(recipe)
                    db.commit()
                
                # 2. Create Batch
                b_ref = str(row.get("BatchRef", f"IMP-{i}"))
                # Check exist
                if not db.query(SynthesisBatch).filter(SynthesisBatch.lab_notebook_ref == b_ref).first():
                    batch = SynthesisBatch(
                        recipe_id=recipe.id,
                        lab_notebook_ref=b_ref,
                        execution_date=datetime.datetime.now(),
                        status="Completed"
                    )
                    db.add(batch)
                    db.commit()
                    
                    # 3. Add Performance
                    # Try to parse columns softly
                    try:
                        p = PerformanceTest(
                            batch_id=batch.id,
                            test_type="Mortar",
                            compressive_strength_1d=float(row.get("Strength_1d", 0)),
                            compressive_strength_28d=float(row.get("Strength_28d", 0)),
                            flow=float(row.get("Flow", 0))
                        )
                        db.add(p)
                        db.commit()
                        count += 1
                    except Exception as e:
                        st.error(f"Error parsing row {i}: {e}")
                
                progress_bar.progress((i + 1) / len(df))
            
            st.success(f"Successfully imported {count} records!")
            
    except Exception as e:
        st.error(f"Error reading file: {e}")
