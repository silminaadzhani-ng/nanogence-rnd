import streamlit as st
import pandas as pd
import plotly.express as px
from app.database import engine, init_db
from app.ui_utils import display_logo

# Ensure database is synced
init_db()

st.set_page_config(page_title="Analytics Explorer", page_icon="🕵️", layout="wide")
display_logo()

st.markdown("# 🕵️ Data Explorer & Analytics")

tab_dash, tab1 = st.tabs(["📊 Dashboard", "🕵️ Advanced Explorer"])

# Load Data via SQL
query = """
SELECT 
    r.name as recipe_name,
    r.ca_si_ratio,
    r.molarity_ca_no3,
    r.pce_content_wt,
    b.lab_notebook_ref as measurement_id,
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
    
    with tab_dash:
        st.subheader("Global Trends")
        if df.empty:
            st.info("No data available for dashboard.")
        else:
            col1, col2 = st.columns(2)
            fig_trend = px.line(df.sort_values("execution_date"), x="execution_date", y="compressive_strength_28d", title="28d Strength Evolution Over Time")
            col1.plotly_chart(fig_trend, use_container_width=True)
            
            fig_dist = px.box(df, y="compressive_strength_28d", points="all", title="Strength Variability Range")
            col2.plotly_chart(fig_dist, use_container_width=True)

    with tab1:
        if df.empty:
            st.warning("No data found. Go run some experiments!")
        else:
            st.dataframe(df.head())
            
            st.divider()
            st.subheader("Correlation Plotter")
            
            c1, c2, c3 = st.columns(3)
            x_axis = c1.selectbox("X Axis", options=["ca_si_ratio", "pce_content_wt", "molarity_ca_no3", "flow"])
            y_axis = c2.selectbox("Y Axis", options=["compressive_strength_1d", "compressive_strength_7d", "compressive_strength_28d"])
            color_by = c3.selectbox("Color By", options=["recipe_name", "measurement_id"])
            
            fig = px.scatter(
                df, 
                x=x_axis, 
                y=y_axis, 
                color=color_by, 
                size="compressive_strength_28d" if "compressive_strength_28d" in df.columns else None, 
                hover_data=["measurement_id"],
                title=f"{y_axis} vs {x_axis}"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Simple Stats
            st.subheader("Distribution Analysis")
            fig2 = px.histogram(df, x=y_axis, nbins=10, title=f"Distribution of {y_axis}")
            st.plotly_chart(fig2, use_container_width=True)

except Exception as e:
    st.error(f"Database Error: {e}")
