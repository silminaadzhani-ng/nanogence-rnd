import streamlit as st
import sys
import os

# Ensure the project root is in sys.path
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_path not in sys.path:
    sys.path.append(root_path)

from app.database import init_db
from app.ui_utils import display_logo

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

st.markdown("""
### Welcome to the R&D Data Platform

This platform integrates experimental design, synthesis execution, and performance testing for C-S-H seeds.

#### 👈 Select a Module from the Sidebar

*   **🏛️ Materials**: Manage raw chemicals and liquid stock solutions.
*   **📝 Recipe Designer**: Theoretical stoichiometric calculations and AI strength prediction.
*   **🧪 Results**: Log synthesis batches and detailed characterization (PSD, pH, Agglomeration).
*   **📉 Analytics**: Visualize performance trends and mortar testing data.

---
**System Status**: ✅ Database Connected (SQLite)
""")
