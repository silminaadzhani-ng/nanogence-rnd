import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .database import Base

class StockSolutionBatch(Base):
    __tablename__ = "stock_solution_batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String, unique=True, index=True) # e.g. CA-20240101-01
    chemical_type = Column(String) # 'Ca', 'Si', 'NaOH'
    molarity = Column(Float)
    target_volume_ml = Column(Float)
    actual_mass_g = Column(Float)
    operator = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(String)

    # Relationships
    recipes_ca = relationship("Recipe", foreign_keys="Recipe.ca_stock_batch_id", back_populates="ca_stock_batch")
    recipes_si = relationship("Recipe", foreign_keys="Recipe.si_stock_batch_id", back_populates="si_stock_batch")

class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, index=True)
    parent_recipe_id = Column(UUID(as_uuid=True), ForeignKey('recipes.id'), nullable=True)
    version = Column(Integer, default=1)
    
    # Synthesis Parameters
    recipe_date = Column(DateTime, default=datetime.utcnow)
    ca_si_ratio = Column(Float)
    molarity_ca_no3 = Column(Float)
    molarity_na2sio3 = Column(Float)
    total_solid_content = Column(Float)
    pce_content_wt = Column(Float)
    
    # Material Sourcing
    material_sources = Column(JSON, default=dict) # e.g. {"ca": "Carl Roth", "si": "Sigma", "pce": "BASF"}
    
    # Stock solution link
    ca_stock_batch_id = Column(UUID(as_uuid=True), ForeignKey('stock_solution_batches.id'), nullable=True)
    si_stock_batch_id = Column(UUID(as_uuid=True), ForeignKey('stock_solution_batches.id'), nullable=True)

    # Process Config
    ca_addition_rate = Column(Float) # mL/min
    si_addition_rate = Column(Float) # mL/min
    target_ph = Column(Float)
    
    # Process Config (stored as JSON for flexibility in step definitions)
    # Example: {"feeding_sequence": [{"step": "A", "duration": 10}], "rate": 5.0}
    process_config = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String) # Simple string for now, could be User FK later
    
    # Relationships
    ca_stock_batch = relationship("StockSolutionBatch", foreign_keys=[ca_stock_batch_id], back_populates="recipes_ca")
    si_stock_batch = relationship("StockSolutionBatch", foreign_keys=[si_stock_batch_id], back_populates="recipes_si")
    batches = relationship("SynthesisBatch", back_populates="recipe")
    children = relationship("Recipe", remote_side=[id], backref="parent")

class SynthesisBatch(Base):
    __tablename__ = "synthesis_batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey('recipes.id'))
    lab_notebook_ref = Column(String, unique=True, index=True)
    execution_date = Column(DateTime, default=datetime.utcnow)
    operator = Column(String)
    status = Column(String, default="In-Progress") # Planned, In-Progress, Completed
    
    recipe = relationship("Recipe", back_populates="batches")
    qc_measurements = relationship("QCMeasurement", back_populates="batch")
    performance_tests = relationship("PerformanceTest", back_populates="batch")

class QCMeasurement(Base):
    __tablename__ = "qc_measurements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey('synthesis_batches.id'))
    measured_at = Column(DateTime, default=datetime.utcnow)
    ageing_time = Column(Float, default=0.0) # e.g. 1 hour, 24 hours
    
    # Core Physicochemical
    ph = Column(Float, nullable=True)
    solid_content_measured = Column(Float, nullable=True)
    settling_height = Column(Float, nullable=True)
    
    # Complex PSD Data (Before/After Sonication, Volume/Number distributions)
    # Structure: {
    #   "before_sonication": {"volume": {"d10": ...}, "number": {...}, "ssa": ...},
    #   "after_sonication": {...}
    # }
    psd_data = Column(JSON, default=dict)
    
    notes = Column(String, nullable=True)
    custom_metrics = Column(JSON, default=dict)

    batch = relationship("SynthesisBatch", back_populates="qc_measurements")

class PerformanceTest(Base):
    __tablename__ = "performance_tests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey('synthesis_batches.id'))
    test_type = Column(String) # "Mortar" or "Cement Paste"
    cast_date = Column(DateTime, default=datetime.utcnow)
    
    # Mix Design Metadata (Cement Type, w/c, Sand, etc.)
    mix_design = Column(JSON, default=dict)
    
    # Fresh Properties
    fresh_density = Column(Float, nullable=True)
    flow = Column(Float, nullable=True)
    air_content = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)

    # Hardened Properties (Averages)
    compressive_strength_12h = Column(Float, nullable=True)
    compressive_strength_16h = Column(Float, nullable=True)
    compressive_strength_1d = Column(Float, nullable=True)
    compressive_strength_2d = Column(Float, nullable=True)
    compressive_strength_7d = Column(Float, nullable=True)
    compressive_strength_28d = Column(Float, nullable=True)
    
    # Store full Cube A/B/C details here
    raw_data = Column(JSON, default=dict)

    batch = relationship("SynthesisBatch", back_populates="performance_tests")
