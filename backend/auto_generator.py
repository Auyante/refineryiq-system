import random
from datetime import datetime
from sqlalchemy.orm import Session
from database.connection import SessionLocal # Asegúrate de tener esto o usa el de main
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Configuración Mini-DB para el generador (Replica la de main.py)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:307676@localhost:5432/refineryiq")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# Modelos mínimos necesarios para generar datos
class Kpi(Base):
    __tablename__ = "kpis"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    unit_id = Column(String)
    energy_efficiency = Column(Float)
    throughput = Column(Float)
    quality_score = Column(Float, default=99.9)

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    unit_id = Column(String)
    severity = Column(String)
    message = Column(String)
    acknowledged = Column(Boolean, default=False)

def run_simulation_cycle():
    """Genera datos falsos para que el dashboard se mueva"""
    db = SessionLocal()
    try:
        print(f"🔄 [SIM] Generando datos: {datetime.now()}")
        
        # 1. Generar KPI
        new_kpi = Kpi(
            timestamp=datetime.now(),
            unit_id="CDU-101",
            energy_efficiency=random.uniform(88.0, 95.5),
            throughput=random.uniform(11500, 13000),
            quality_score=random.uniform(95, 100)
        )
        db.add(new_kpi)

        # 2. Generar Alerta Aleatoria (10% probabilidad)
        if random.random() < 0.1:
            alert = Alert(
                timestamp=datetime.now(),
                unit_id="FCC-201",
                severity="MEDIUM",
                message="Ligera vibración detectada en compresor C-201",
                acknowledged=False
            )
            db.add(alert)
            
        db.commit()
        print("✅ [SIM] Datos insertados.")
    except Exception as e:
        print(f"❌ [SIM] Error: {e}")
        db.rollback()
    finally:
        db.close()