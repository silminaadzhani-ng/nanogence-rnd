import streamlit as st
import pandas as pd
import plotly.express as px
from app.database import engine

st.set_page_config(page_title="Analytics Explorer", page_icon="🕵️", layout="wide")

st.markdown("# 🕵️ Data Explorer & Analytics")

# Load Data via SQL
# We join Recipes -> Batches -> Results
query = """
SELECT 
    r.name as recipe_name,
    r.ca_si_ratio,
    r.molarity_ca_no3,
    r.pce_content_wt,
    b.lab_notebook_ref,
    b.execution_date,
    p.compressive_strength_1d,
    p.compressive_strength_7d,
    p.compressive_strength_28d,
    p.flow
FROM performance_tests p
JOIN synthesis_batches b ON p.batch_id = b.id
JOIN recipes r ON b.recipe_id = r.id
"""

try:
    df = pd.read_sql(query, engine)
    
    if df.empty:
        st.warning("No data found. Go run some experiments!")
    else:
        st.dataframe(df.head())
        
        st.divider()
        st.subheader("Correlation Plotter")
        
        c1, c2, c3 = st.columns(3)
        x_axis = c1.selectbox("X Axis", options=["ca_si_ratio", "pce_content_wt", "molarity_ca_no3", "flow"])
        y_axis = c2.selectbox("Y Axis", options=["compressive_strength_1d", "compressive_strength_7d", "compressive_strength_28d"])
        color_by = c3.selectbox("Color By", options=["recipe_name", "lab_notebook_ref"])
        
        fig = px.scatter(
            df, 
            x=x_axis, 
            y=y_axis, 
            color=color_by, 
            size="compressive_strength_28d", 
            hover_data=["lab_notebook_ref"],
            title=f"{y_axis} vs {x_axis}"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Simple Stats
        st.subheader("Distribution Analysis")
        fig2 = px.histogram(df, x=y_axis, nbins=10, title=f"Distribution of {y_axis}")
        st.plotly_chart(fig2, use_container_width=True)

except Exception as e:
    st.error(f"Database Error: {e}")
