import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import Recipe, SynthesisBatch, QCMeasurement, PerformanceTest, StockSolutionBatch, User
from app.auth import get_password_hash

def seed():
    db = SessionLocal()
    
    # Check if admin exists
    admin_user = db.query(User).filter(User.email == "admin@nanogence.com").first()
    if not admin_user:
        print("Creating Admin User...")
        pwd = input("Enter password for admin@nanogence.com: ")
        hashed = get_password_hash(pwd)
        admin = User(
            email="admin@nanogence.com",
            hashed_password=hashed,
            full_name="Admin User",
            role="Admin"
        )
        db.add(admin)
        db.commit()
        print("Admin user created.")
    
    # 0. Create Stock Solution Batches
    ca_stock = StockSolutionBatch(
        code="CA-20240202-01",
        chemical_type="Ca",
        molarity=1.5,
        target_volume_ml=1000,
        actual_mass_g=354.22,
        operator="Silmina Adzhani"
    )
    si_stock = StockSolutionBatch(
        code="SI-20240202-01",
        chemical_type="Si",
        molarity=0.75,
        target_volume_ml=1000,
        actual_mass_g=159.10,
        operator="Silmina Adzhani"
    )
    db.add_all([ca_stock, si_stock])
    db.commit()

    # 1. Create Recipes
    recipe_ref = Recipe(
        name="Reference Mix (No Seeds)",
        recipe_date=datetime.datetime(2025, 1, 1),
        ca_si_ratio=0.0,
        molarity_ca_no3=0.0,
        molarity_na2sio3=0.0,
        total_solid_content=0.0,
        pce_content_wt=0.0,
        ca_addition_rate=0.0,
        si_addition_rate=0.0,
        created_by="System"
    )
    
    recipe_a = Recipe(
        name="Recipe A (Standard CSH)",
        recipe_date=datetime.datetime(2025, 2, 2),
        ca_si_ratio=1.5,
        molarity_ca_no3=1.5,
        molarity_na2sio3=0.75,
        total_solid_content=5.0,
        pce_content_wt=2.0,
        ca_addition_rate=0.5,
        si_addition_rate=0.5,
        ca_stock_batch_id=ca_stock.id,
        si_stock_batch_id=si_stock.id,
        created_by="System"
    )
    
    db.add_all([recipe_ref, recipe_a])
    db.commit()
    
    # 2. Create Batches & Results
    b_ref = SynthesisBatch(
        recipe_id=recipe_ref.id,
        lab_notebook_ref="AC-H145",
        execution_date=datetime.datetime(2025, 12, 9, 10, 50),
        operator="AC",
        status="Completed"
    )
    db.add(b_ref)
    db.commit()
    
    p_ref = PerformanceTest(
        batch_id=b_ref.id,
        test_type="Mortar",
        mix_design={"cement": "CEM I 42.5 N Heidelberg", "wc": 0.45},
        fresh_density=2270,
        flow=180,
        air_content=2.0,
        compressive_strength_12h=2.27,
        compressive_strength_16h=21.0,
        compressive_strength_1d=46.9,
        compressive_strength_2d=54.7,
        compressive_strength_28d=65.0
    )
    db.add(p_ref)

    b_a1 = SynthesisBatch(
        recipe_id=recipe_a.id,
        lab_notebook_ref="AC-H146",
        execution_date=datetime.datetime(2025, 12, 9, 11, 20),
        operator="AC",
        status="Completed"
    )
    db.add(b_a1)
    db.commit()
    
    p_a1 = PerformanceTest(
        batch_id=b_a1.id,
        test_type="Mortar",
        mix_design={"cement": "CEM I 42.5 N Heidelberg", "wc": 0.45, "seed_dosage": "0.5% solid"},
        fresh_density=2270,
        flow=170,
        compressive_strength_12h=2.27,
        compressive_strength_16h=21.2,
        compressive_strength_1d=42.1,
        compressive_strength_2d=51.0,
        compressive_strength_28d=60.0
    )
    db.add(p_a1)

    db.commit()
    print("Database seeded with updated schema!")

if __name__ == "__main__":
    seed()
