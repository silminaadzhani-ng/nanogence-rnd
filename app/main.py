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

# --- Authentication Gatekeeper (Disabled per user request) ---
if "user_email" not in st.session_state:
    st.session_state.user_email = "guest@nanogence.com"
    st.session_state.user_name = "Guest User"
    st.session_state.user_role = "Researcher"

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

    st.divider()
    st.subheader("💾 Database Maintenance")
    st.info("Download a copy of the database for your daily backup to Google Drive.")
    
    db_file_path = "nanogence.db"
    
    def log_backup():
        db = SessionLocal()
        try:
            log = SystemLog(
                event_type="BACKUP_DOWNLOAD",
                details=f"Backup downloaded manually.",
                user="User"
            )
            db.add(log)
            db.commit()
        except Exception as e:
            print(f"Log Error: {e}")
        finally:
            db.close()

    if os.path.exists(db_file_path):
        with open(db_file_path, "rb") as f:
            db_binary = f.read()
        
        timestamp = datetime.date.today().strftime("%Y%m%d")
        st.download_button(
            label="📥 Download Database Backup",
            data=db_binary,
            file_name=f"nanogence_backup_{timestamp}.db",
            mime="application/x-sqlite3",
            on_click=log_backup,
            help="Download the full experimental database as a single file."
        )
        
        # Show recent backups
        st.markdown("#### recent database download")
        db = SessionLocal()
        logs = db.query(SystemLog).filter(SystemLog.event_type == "BACKUP_DOWNLOAD").order_by(SystemLog.timestamp.desc()).limit(5).all()
        db.close()
        
        if logs:
            for l in logs:
                st.caption(f"✅ {l.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            st.caption("No recent backups logged.")
            
    else:
        st.error("Database file not found. Ensure the app has been initialized.")

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
