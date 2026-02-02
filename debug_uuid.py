from app.database import SessionLocal
from app.models import Recipe, SynthesisBatch, PerformanceTest
import pandas as pd

session = SessionLocal()

print("--- Recipe ---")
r = session.query(Recipe).first()
print(f"ID: {r.id}, Type: {type(r.id)}")

print("--- Batch ---")
b = session.query(SynthesisBatch).first()
print(f"ID: {b.id}, Type: {type(b.id)}")
print(f"RecipeFK: {b.recipe_id}, Type: {type(b.recipe_id)}")

print("--- Perf ---")
p = session.query(PerformanceTest).first()
print(f"BatchFK: {p.batch_id}, Type: {type(p.batch_id)}")

# Check Join
print("--- Join Test via ORM ---")
try:
    joined = session.query(SynthesisBatch).join(Recipe).first()
    print("Join Batch->Recipe: Success", joined)
except Exception as e:
    print("Join Batch->Recipe: Failed", e)

session.close()
