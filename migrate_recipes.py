from sqlalchemy import text
from app.database import get_db, init_db

init_db()
db = next(get_db())

try:
    # Try to select the code column to see if it exists
    db.execute(text("SELECT code FROM recipes LIMIT 1"))
    print("Column 'code' already exists.")
except Exception:
    print("Adding 'code' column...")
    try:
        # Add the column if it doesn't exist (SQLite syntax)
        db.execute(text("ALTER TABLE recipes ADD COLUMN code VARCHAR"))
        db.commit()
        print("Column 'code' added successfully.")
    except Exception as e:
        print(f"Error adding column: {e}")
