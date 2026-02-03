import streamlit as st
import os
import datetime
from sqlalchemy.orm import Session
from app.database import get_db, init_db, SessionLocal
from app.models import SystemLog
from app.ui_utils import display_logo

# Ensure database is synced
init_db()

st.set_page_config(page_title="Admin & Settings", page_icon="⚙️", layout="wide")
display_logo()

st.title("⚙️ Admin & Settings")

tab1, tab2 = st.tabs(["💾 Database Backup", "🛠️ System Logs"])

db_file_path = "nanogence.db"

with tab1:
    st.header("Database Maintenance")
    st.info("Download a copy of the database for your daily backup to Google Drive.")

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
            help="Download the full experimental database as a single file.",
            type="primary"
        )
    else:
        st.error("Database file not found.")

with tab2:
    st.header("Recent System Activity")
    db: Session = next(get_db())
    logs = db.query(SystemLog).order_by(SystemLog.timestamp.desc()).limit(50).all()
    
    if logs:
        log_data = []
        for l in logs:
            log_data.append({
                "Timestamp": l.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "Event": l.event_type,
                "Details": l.details,
                "User": l.user
            })
        st.table(log_data)
    else:
        st.info("No system activity logged yet.")
