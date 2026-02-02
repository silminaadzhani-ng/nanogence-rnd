from app.database import SessionLocal, init_db
from app.models import Recipe, SynthesisBatch, QCMeasurement
from datetime import datetime

init_db()
db = SessionLocal()

# trial_data: name, d10_v_b, d50_v_b, d90_v_b, mean_v_b, d10_n_b, d50_n_b, d90_n_b, mean_n_b, ssa_b, 
#                  d10_v_a, d50_v_a, d90_v_a, mean_v_a, d10_n_a, d50_n_a, d90_n_a, mean_n_a, ssa_a, 
#                  agg_v, agg_n, agg_ssa, ph, solids, settling
results_data = [
    # A1
    ["Trial A1", 5.38, 17.24, 39.83, 20.90, 0.87, 1.14, 2.83, 1.69, 0.58, 0.16, 0.43, 6.58, 1.84, 0.11, 0.15, 0.26, 0.18, 16.64, 11.35, 9.51, 28.79, 11.80, 7.03, 0.0],
    # A2
    ["Trial A2", 3.64, 12.11, 28.82, 14.95, 0.52, 0.65, 1.43, 0.93, 0.89, 0.18, 0.58, 19.91, 11.45, 0.11, 0.16, 0.26, 0.18, 13.58, 1.31, 5.21, 15.34, 11.85, 9.71, 5.0],
    # A3
    ["Trial A3", 4.65, 13.68, 32.94, 17.08, 1.27, 1.90, 5.08, 2.73, 0.64, 1.63, 6.05, 14.38, 7.52, 0.32, 0.44, 0.83, 0.57, 1.83, 2.27, 4.78, 2.86, 11.88, 14.65, 8.0],
    # A4
    ["Trial A4", 5.22, 16.86, 46.82, 23.07, 1.50, 2.21, 5.55, 3.09, 0.54, 2.93, 8.07, 17.65, 9.60, 0.75, 1.10, 3.14, 1.65, 1.05, 2.40, 1.88, 1.95, 11.76, 16.17, 12.0],
    # B1
    ["Trial B1", 8.32, 24.01, 55.64, 29.43, 2.58, 4.14, 10.28, 5.65, 0.35, 0.23, 2.63, 19.25, 7.02, 0.13, 0.17, 0.29, 0.20, 8.23, 4.19, 28.68, 23.25, 11.71, 9.62, 5.0],
    # B2
    ["Trial B2", 1.35, 8.33, 21.41, 10.43, 0.24, 0.35, 0.64, 0.43, 1.86, 0.13, 0.19, 2.42, 0.89, 0.10, 1.14, 0.20, 0.15, 29.65, 11.73, 2.90, 15.97, 11.73, 6.92, 2.0],
    # B3
    ["Trial B3", 8.55, 27.19, 73.97, 36.60, 2.54, 3.82, 9.51, 5.29, 0.33, 3.96, 10.46, 23.12, 12.61, 1.06, 1.63, 4.62, 2.39, 0.79, 2.90, 2.21, 2.39, 11.63, 16.77, 11.5],
    # B4
    ["Trial B4", 5.40, 16.30, 42.13, 21.10, 1.51, 2.31, 5.99, 3.27, 0.54, 2.29, 6.75, 14.77, 7.96, 0.44, 0.57, 1.47, 0.85, 1.39, 2.65, 3.87, 2.59, 11.80, 13.08, 10.0],
    # C1
    ["Trial C1", 11.88, 39.92, 103.60, 52.43, 3.12, 4.72, 11.81, 6.60, 0.24, 2.53, 7.71, 20.01, 10.03, 0.52, 0.69, 1.99, 1.06, 1.20, 5.23, 6.20, 5.05, 11.70, 14.16, 12.0],
    # C2
    ["Trial C2", 9.56, 32.54, 85.46, 45.66, 2.54, 3.82, 9.58, 5.35, 0.29, 1.84, 6.40, 15.64, 8.02, 0.37, 0.50, 1.06, 0.68, 1.63, 5.69, 7.83, 5.59, 11.80, 15.92, 14.0],
    # C3
    ["Trial C3", 3.15, 9.61, 22.04, 11.73, 0.52, 0.66, 1.61, 0.98, 1.02, 0.16, 0.42, 10.32, 5.00, 0.11, 0.15, 0.24, 0.17, 16.97, 2.35, 5.87, 16.70, 11.72, 6.74, 3.0],
    # C4
    ["Trial C4", 4.79, 14.37, 35.91, 18.25, 1.26, 1.86, 5.00, 2.69, 0.62, 0.23, 1.13, 9.09, 4.17, 0.11, 0.16, 0.31, 0.19, 9.79, 4.38, 13.94, 15.89, 11.71, 9.09, 1.0],
    # D1
    ["Trial D1", 15.95, 59.20, 161.10, 78.56, 3.93, 5.66, 13.85, 7.96, 0.17, 4.12, 11.72, 25.43, 13.78, 1.28, 2.05, 5.14, 2.82, 0.73, 5.70, 2.82, 4.27, 11.64, 15.46, 11.0],
    # D2
    ["Trial D2", 7.51, 21.94, 55.00, 28.13, 2.56, 3.98, 9.55, 5.35, 0.39, 0.48, 3.31, 11.35, 5.55, 0.16, 0.25, 0.47, 0.28, 4.51, 5.07, 19.24, 11.68, 11.68, 12.44, 10.0],
    # D3
    ["Trial D3", 5.13, 14.53, 33.70, 17.81, 1.58, 2.56, 6.47, 3.53, 0.58, 0.16, 0.51, 7.66, 2.49, 0.10, 0.14, 0.23, 0.16, 15.29, 7.16, 21.93, 26.50, 11.71, 9.84, 4.0],
    # D4
    ["Trial D4", 0.46, 5.19, 14.83, 7.00, 0.16, 0.20, 0.34, 0.23, 4.29, 0.14, 0.32, 35.35, 9.15, 0.11, 0.14, 0.22, 0.16, 18.99, 0.77, 1.48, 4.43, 11.70, 6.50, 1.0],
]

for row in results_data:
    name = row[0]
    recipe = db.query(Recipe).filter(Recipe.name == name).first()
    if recipe:
        # Create a proxy SynthesisBatch if one doesn't exist for this recipe
        batch = db.query(SynthesisBatch).filter(SynthesisBatch.recipe_id == recipe.id).first()
        if not batch:
            batch = SynthesisBatch(
                recipe_id=recipe.id,
                lab_notebook_ref=f"NB-{name}",
                operator="Seed System",
                status="Completed"
            )
            db.add(batch)
            db.flush()
        
        # Check if QC exists
        qc = db.query(QCMeasurement).filter(QCMeasurement.batch_id == batch.id).first()
        if not qc:
            qc = QCMeasurement(batch_id=batch.id)
            db.add(qc)
        
        # Update values
        qc.psd_before_v_d10 = row[1]
        qc.psd_before_v_d50 = row[2]
        qc.psd_before_v_d90 = row[3]
        qc.psd_before_v_mean = row[4]
        qc.psd_before_n_d10 = row[5]
        qc.psd_before_n_d50 = row[6]
        qc.psd_before_n_d90 = row[7]
        qc.psd_before_n_mean = row[8]
        qc.psd_before_ssa = row[9]
        
        qc.psd_after_v_d10 = row[10]
        qc.psd_after_v_d50 = row[11]
        qc.psd_after_v_d90 = row[12]
        qc.psd_after_v_mean = row[13]
        qc.psd_after_n_d10 = row[14]
        qc.psd_after_n_d50 = row[15]
        qc.psd_after_n_d90 = row[16]
        qc.psd_after_n_mean = row[17]
        qc.psd_after_ssa = row[18]
        
        qc.agglom_vol = row[19]
        qc.agglom_num = row[20]
        qc.agglom_ssa = row[21]
        
        qc.ph = row[22]
        qc.solid_content_measured = row[23]
        qc.settling_height = row[24]

db.commit()
print(f"Successfully seeded {len(results_data)} result rows.")
db.close()
