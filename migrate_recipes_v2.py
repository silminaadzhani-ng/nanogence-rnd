from app.database import SessionLocal
from app.models import Recipe
from datetime import datetime

def migrate_ids():
    db = SessionLocal()
    try:
        recipes = db.query(Recipe).all()
        # Group by date to handle the sequence number
        date_counts = {}
        
        for r in recipes:
            # Use recipe_date if available, else today
            rdate = r.recipe_date if r.recipe_date else datetime.now()
            today_str = rdate.strftime("%Y%m%d")
            
            if today_str not in date_counts:
                date_counts[today_str] = 1
            else:
                date_counts[today_str] += 1
                
            new_code = f"NG-{today_str}-{date_counts[today_str]:02d}"
            print(f"Updating {r.name}: {r.code} -> {new_code}")
            r.code = new_code
            
        db.commit()
        print("Migration complete.")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_ids()
