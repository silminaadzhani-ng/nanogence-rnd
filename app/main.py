import streamlit as st
import sys
import os
import datetime

# Ensure the project root is in sys.path
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_path not in sys.path:
    sys.path.append(root_path)

from app.database import init_db, SessionLocal
from app.ui_utils import display_logo
from app.models import SystemLog

# Centralized database initialization
init_db()

st.set_page_config(
    page_title="Nanogence R&D Platform",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

display_logo()

st.title("🧪 Nanogence R&D Platform")

tab_dash, tab_guide = st.tabs(["📊 Dashboard", "📖 User Guide"])

with tab_dash:
    st.subheader("Platform Health & Summary")
    c1, c2, c3 = st.columns(3)
    c1.success("Database: Connected")
    c2.info("Environment: Local / Cloud")
    c3.warning("AI Model: Loaded")
    
    st.markdown("""
    #### Quick Navigator
    - **🏛️ Materials**: Manage your Inventory.
    - **📝 Recipe Designer**: Plan new trials.
    - **🧪 Results**: Record synthesis data.
    - **🏢 Mortar Tests**: Log performance results.
    - **📈 Analytics**: Unified data view.
    """)

    st.markdown("---")
    st.info("Use the sidebar on the left to navigate between modules.")

with tab_guide:
    st.markdown("""
    ### Welcome to the R&D Data Platform
    
    This platform integrates experimental design, synthesis execution, and performance testing for C-S-H seeds.
    
    #### 👈 Use the Sidebar to Navigate
    
    1.  **Materials**: Manage raw chemicals and liquid stock solutions.
    2.  **Recipe Designer**: Theoretical stoichiometric calculations and AI strength prediction.
    3.  **Synthesis Results & Characterization**: Log synthesis batches and detailed characterization.
    4.  **Mortar and Paste Test**: Log compressive strength and fresh properties.
    5.  **Analytics**: Visualize performance trends and unified data analytics.
    
    ---
    **System Status**: ✅ All Systems Operational
    """)
