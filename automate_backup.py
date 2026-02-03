import shutil
import os
import datetime

# --- CONFIGURATION ---
# 1. Path to your Nanogence database
SOURCE_DB = "nanogence.db"

# 2. Path to your Google Drive folder (Change this to your actual Google Drive path)
# Example: "C:/Users/YourName/Google Drive/Backups/Nanogence"
GDRIVE_PATH = "C:/Path/To/Your/Company/GoogleDrive/Nanogence_Backups"

def perform_backup():
    if not os.path.exists(SOURCE_DB):
        print(f"Error: {SOURCE_DB} not found in current directory.")
        return

    # Create destination folder if it doesn't exist
    if not os.path.exists(GDRIVE_PATH):
        try:
            os.makedirs(GDRIVE_PATH)
        except Exception as e:
            print(f"Error creating backup directory: {e}")
            return

    # Generate filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dest_filename = f"nanogence_backup_{timestamp}.db"
    dest_path = os.path.join(GDRIVE_PATH, dest_filename)

    try:
        shutil.copy2(SOURCE_DB, dest_path)
        print(f"✅ Success! Database backed up to: {dest_path}")
    except Exception as e:
        print(f"❌ Backup failed: {e}")

if __name__ == "__main__":
    perform_backup()
