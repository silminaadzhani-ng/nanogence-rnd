import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import Recipe, SynthesisBatch, QCMeasurement, PerformanceTest

def seed():
    db = SessionLocal()
    
    # 1. Create Recipes
    # Reference
    recipe_ref = Recipe(
        name="Reference Mix (No Seeds)",
        ca_si_ratio=0.0, # Not applicable
        molarity_ca_no3=0.0,
        total_solid_content=0.0,
        pce_content_wt=0.0,
        created_by="System"
    )
    
    # Trial A (Ca/Si=1.5, 5% Solids, 2% PCE - per header, but rows say 0.5% solid?)
    # User text: "Trial a1 - Ca/Si = 1.50 - 1.5M Ca(NO3)2 - 5% solid - 2wt% PCE"
    recipe_a = Recipe(
        name="Recipe A (Standard CSH)",
        ca_si_ratio=1.5,
        molarity_ca_no3=1.5,
        total_solid_content=5.0, # Using the header value
        pce_content_wt=2.0,
        created_by="System"
    )
    
    # Trial B (Hypothetical variation based on name B1/B2)
    recipe_b = Recipe(
        name="Recipe B",
        ca_si_ratio=1.5,
        molarity_ca_no3=1.5,
        total_solid_content=5.0,
        pce_content_wt=2.0,
        created_by="System"
    )
    
    db.add_all([recipe_ref, recipe_a, recipe_b])
    db.commit()
    
    # 2. Create Batches & Results
    
    # --- AC-H145 (Reference) ---
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
        fresh_density=2270, # 2.27 g/cm3
        flow=180,
        air_content=2.0,
        compressive_strength_12h=2.27,
        compressive_strength_16h=21.0,
        compressive_strength_1d=46.9,
        compressive_strength_2d=54.7,
        compressive_strength_28d=65.0 # Extrapolated for ML Demo
    )
    db.add(p_ref)

    # --- AC-H146 (Trial A1) ---
    b_a1 = SynthesisBatch(
        recipe_id=recipe_a.id,
        lab_notebook_ref="AC-H146",
        execution_date=datetime.datetime(2025, 12, 9, 11, 20),
        operator="AC",
        status="Completed"
    )
    db.add(b_a1)
    db.commit()
    
    # QC for A1
    # 1h Ageing
    qc_a1_1h = QCMeasurement(
        batch_id=b_a1.id,
        ageing_time=1.0,
        ph=9.57, # From user table "Final pH [-] ... 9.57"
        psd_data={
            "before_sonication": {"d10": 2.18, "d50": 7.68, "d90": 18.59},
            "after_sonication": {"d10": 0.44, "d50": 0.57, "d90": 1.22}
        },
        notes="Gelified overnight"
    )
    # 24h Ageing
    qc_a1_24h = QCMeasurement(
        batch_id=b_a1.id,
        ageing_time=24.0,
        ph=0.0, # Not listed in that specific row block?
        psd_data={
            "before_sonication": {"d10": 7.19, "d50": 39.23, "d90": 88.66},
            "after_sonication": {"d10": 2.55, "d50": 3.60, "d90": 6.75}
        }
    )
    db.add_all([qc_a1_1h, qc_a1_24h])
    
    # Perf for A1
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
        compressive_strength_28d=60.0 # Extrapolated
    )
    db.add(p_a1)

    # --- AC-H147 (Trial A2) ---
    b_a2 = SynthesisBatch(
        recipe_id=recipe_a.id, # Same recipe, diff batch
        lab_notebook_ref="AC-H147",
        execution_date=datetime.datetime(2025, 12, 9, 11, 40),
        operator="AC",
        status="Completed"
    )
    db.add(b_a2)
    db.commit()
    p_a2 = PerformanceTest(
        batch_id=b_a2.id,
        test_type="Mortar",
        fresh_density=2240,
        flow=180,
        compressive_strength_12h=2.24,
        compressive_strength_16h=20.7,
        compressive_strength_1d=41.9,
        compressive_strength_2d=51.3,
        compressive_strength_28d=61.0 # Extrapolated
    )
    db.add(p_a2)

    # --- AC-H148 (Trial B1) ---
    b_b1 = SynthesisBatch(
        recipe_id=recipe_b.id,
        lab_notebook_ref="AC-H148",
        execution_date=datetime.datetime(2025, 12, 9, 12, 00),
        operator="AC",
        status="Completed"
    )
    db.add(b_b1)
    db.commit()
    p_b1 = PerformanceTest(
        batch_id=b_b1.id,
        test_type="Mortar",
        fresh_density=2240,
        flow=185,
        compressive_strength_12h=2.24,
        compressive_strength_16h=21.1,
        compressive_strength_1d=43.5,
        compressive_strength_2d=51.6,
        compressive_strength_28d=62.0 # Extrapolated
    )
    db.add(p_b1)

    # --- AC-H149 (Trial B2) ---
    b_b2 = SynthesisBatch(
        recipe_id=recipe_b.id,
        lab_notebook_ref="AC-H149",
        execution_date=datetime.datetime(2025, 12, 9, 12, 15),
        operator="AC",
        status="Completed"
    )
    db.add(b_b2)
    db.commit()
    p_b2 = PerformanceTest(
        batch_id=b_b2.id,
        test_type="Mortar",
        fresh_density=2230,
        flow=200,
        compressive_strength_12h=2.23,
        compressive_strength_16h=20.3,
        compressive_strength_1d=44.3,
        compressive_strength_2d=51.3,
        compressive_strength_28d=61.5 # Extrapolated
    )
    db.add(p_b2)

    db.commit()
    print("Database seeded with 5 Batches!")

if __name__ == "__main__":
    seed()
