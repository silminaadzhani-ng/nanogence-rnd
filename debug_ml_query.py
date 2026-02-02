from app.database import SessionLocal
from app.models import Recipe, SynthesisBatch, PerformanceTest

session = SessionLocal()

print(f"Recipes: {session.query(Recipe).count()}")
print(f"Batches: {session.query(SynthesisBatch).count()}")
print(f"Perfs: {session.query(PerformanceTest).count()}")

print("--- Data Check ---")
for p in session.query(PerformanceTest).all():
    print(f"Perf ID: {p.id}, BatchID: {p.batch_id}, 28d: {p.compressive_strength_28d}")

print("--- Join Batch -> Recipe ---")
q1 = session.query(SynthesisBatch).join(Recipe)
print(f"Count: {q1.count()}")

print("--- Join Perf -> Batch ---")
q2 = session.query(PerformanceTest).join(SynthesisBatch)
print(f"Count: {q2.count()}")

print("--- Full Join ---")
q3 = session.query(PerformanceTest)\
    .join(SynthesisBatch, PerformanceTest.batch)\
    .join(Recipe, SynthesisBatch.recipe)
print(f"Count: {q3.count()}")

session.close()
