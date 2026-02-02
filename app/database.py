import os
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./nanogence.db")

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
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

    if "stock_solution_batches" in inspector.get_table_names():
        add_column_if_missing("stock_solution_batches", "preparation_date", "DATETIME")
        add_column_if_missing("stock_solution_batches", "raw_material_id", "VARCHAR")

    if "raw_materials" in inspector.get_table_names():
        add_column_if_missing("raw_materials", "molecular_weight", "FLOAT")
