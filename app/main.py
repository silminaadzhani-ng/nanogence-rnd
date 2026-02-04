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
    from app.database import engine
    
    st.subheader("Platform Health & Summary")
    c1, c2, c3 = st.columns(3)
    
    # Check Database Type
    db_url = str(engine.url)
    if "postgresql" in db_url:
        c1.success("Database: ☁️ Cloud (Persistent)")
    else:
        c1.error("Database: ⚠️ Local (Data lost on sleep)")
        st.warning("⚠️ **CRITICAL: You are using temporary storage.** To save your data permanently, you must add your Database Secrets to the Streamlit Cloud settings.")

    c2.info("Environment: Production")
    c3.success("AI Model: Active")
    
    st.markdown("""
    #### Quick Navigator
    - **🏛️ Raw Materials**: Manage your Inventory.
    - **📝 Recipes**: Plan new trials.
    - **🧪 Measurement**: Record synthesis data.
    - **🏢 Mortar and Paste Test**: Log performance results.
    - **📈 Analytics**: Unified data view.
    """)

    st.markdown("---")
    st.info("Use the sidebar on the left to navigate between modules.")

with tab_guide:
    st.markdown("""
    ### Welcome to the R&D Data Platform
    
    This platform integrates experimental design, synthesis execution, and performance testing for C-S-H seeds.
    
    #### 👈 Use the Sidebar to Navigate
    
    1.  **Raw Materials**: Manage raw chemicals and liquid stock solutions.
    2.  **Recipes**: Theoretical stoichiometric calculations and AI strength prediction.
    3.  **Measurement**: Log synthesis batches and detailed characterization.
    4.  **Mortar and Paste Test**: Log compressive strength and fresh properties.
    5.  **Analytics**: Visualize performance trends and unified data analytics.
    6.  **Data Import**: Bulk upload historical data.
    7.  **Admin**: System logs and database maintenance.
    
    ---
    **System Status**: ✅ All Systems Operational
    """)
