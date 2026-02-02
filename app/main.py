import streamlit as st

st.set_page_config(
    page_title="Nanogence R&D Platform",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🧪 Nanogence R&D Platform")

st.markdown("""
### Welcome to the R&D Data Platform

This platform integrates experimental design, synthesis execution, and performance testing for C-S-H seeds.

#### 👈 Select a Module from the Sidebar

*   **Recipe Designer**: Create new synthesis recipes or clone existing ones.
*   **Lab Notebook**: Execute batches and record process parameters/QC.
*   **Results & Analytics**: Analyze performance data and predictive models.

---
**System Status**: ✅ Database Connected (SQLite)
""")
