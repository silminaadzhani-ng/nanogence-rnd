from app.database import SessionLocal
from app.models import Recipe

def migrate_ids():
    db = SessionLocal()
    try:
        recipes = db.query(Recipe).all()
        print(f"Found {len(recipes)} recipes.")
        for r in recipes:
            print(f"ID: {r.id}, Code: {r.code}, Name: {r.name}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate_ids()
