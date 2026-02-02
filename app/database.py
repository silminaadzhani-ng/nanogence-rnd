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
    if "recipes" in inspector.get_table_names():
        cols = [c["name"] for c in inspector.get_columns("recipes")]
        with engine.connect() as conn:
            if "recipe_date" not in cols:
                conn.execute(text("ALTER TABLE recipes ADD COLUMN recipe_date DATETIME"))
            if "molarity_na2sio3" not in cols:
                conn.execute(text("ALTER TABLE recipes ADD COLUMN molarity_na2sio3 FLOAT"))
            if "ca_addition_rate" not in cols:
                conn.execute(text("ALTER TABLE recipes ADD COLUMN ca_addition_rate FLOAT"))
            if "si_addition_rate" not in cols:
                conn.execute(text("ALTER TABLE recipes ADD COLUMN si_addition_rate FLOAT"))
            if "ca_stock_batch_id" not in cols:
                conn.execute(text("ALTER TABLE recipes ADD COLUMN ca_stock_batch_id VARCHAR"))
            if "si_stock_batch_id" not in cols:
                conn.execute(text("ALTER TABLE recipes ADD COLUMN si_stock_batch_id VARCHAR"))
            if "material_sources" not in cols:
                conn.execute(text("ALTER TABLE recipes ADD COLUMN material_sources JSON"))
            conn.commit()
