import os
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./nanogence.db")

# Fix for Heroku/Render/Neon sometimes providing 'postgres://' instead of 'postgresql://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL, connect_args=connect_args
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    import app.models # Register models
    Base.metadata.create_all(bind=engine)
    
    # Soft Migrations (for SQLite existing tables)
    inspector = inspect(engine)
    
    def add_column_if_missing(table_name, col_name, col_type):
        cols = [c["name"] for c in inspector.get_columns(table_name)]
        if col_name not in cols:
            with engine.begin() as conn: # engine.begin() handles commits automatically
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}"))
                print(f"Added column {col_name} to {table_name}")

    if "recipes" in inspector.get_table_names():
        add_column_if_missing("recipes", "recipe_date", "DATETIME")
        add_column_if_missing("recipes", "molarity_na2sio3", "FLOAT")
        add_column_if_missing("recipes", "ca_addition_rate", "FLOAT")
        add_column_if_missing("recipes", "si_addition_rate", "FLOAT")
        add_column_if_missing("recipes", "ca_stock_batch_id", "VARCHAR")
        add_column_if_missing("recipes", "si_stock_batch_id", "VARCHAR")
        add_column_if_missing("recipes", "material_sources", "JSON")
        add_column_if_missing("recipes", "target_ph", "FLOAT")
        add_column_if_missing("recipes", "code", "VARCHAR")

    if "stock_solution_batches" in inspector.get_table_names():
        add_column_if_missing("stock_solution_batches", "preparation_date", "DATETIME")
        add_column_if_missing("stock_solution_batches", "raw_material_id", "VARCHAR")

    if "raw_materials" in inspector.get_table_names():
        add_column_if_missing("raw_materials", "molecular_weight", "FLOAT")

    if "qc_measurements" in inspector.get_table_names():
        new_cols = [
            ("psd_before_v_d10", "FLOAT"), ("psd_before_v_d50", "FLOAT"), ("psd_before_v_d90", "FLOAT"), ("psd_before_v_mean", "FLOAT"),
            ("psd_before_n_d10", "FLOAT"), ("psd_before_n_d50", "FLOAT"), ("psd_before_n_d90", "FLOAT"), ("psd_before_n_mean", "FLOAT"),
            ("psd_before_ssa", "FLOAT"),
            ("psd_after_v_d10", "FLOAT"), ("psd_after_v_d50", "FLOAT"), ("psd_after_v_d90", "FLOAT"), ("psd_after_v_mean", "FLOAT"),
            ("psd_after_n_d10", "FLOAT"), ("psd_after_n_d50", "FLOAT"), ("psd_after_n_d90", "FLOAT"), ("psd_after_n_mean", "FLOAT"),
            ("psd_after_ssa", "FLOAT"),
            ("agglom_vol", "FLOAT"), ("agglom_num", "FLOAT"), ("agglom_ssa", "FLOAT"),
            ("measured_at", "DATETIME"), ("ageing_time", "FLOAT")
        ]
        for col, dtype in new_cols:
            add_column_if_missing("qc_measurements", col, dtype)
