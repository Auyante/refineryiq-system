import os
from sqlalchemy import create_engine, Column, Integer, String, text, inspect
from sqlalchemy.orm import sessionmaker, declarative_base
from passlib.context import CryptContext

# --- TU BASE DE DATOS EN LA NUBE ---
DATABASE_URL = "postgresql://refinery_db_user:c92JlEraE4hJy6qKjSxKGnPhnPESJnbK@dpg-d5vumciqcgvc73a0tq9g-a.virginia-postgres.render.com/refinery_db"

# Configuración
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Modelo de Usuario
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="admin")
    full_name = Column(String)

def fix_admin_user_v2():
    print("🌍 Conectando a Render PostgreSQL...")
    
    # 1. VERIFICACIÓN SEGURA (Sin romper transacciones)
    inspector = inspect(engine)
    if not inspector.has_table("users"):
        print("⚠️ La tabla 'users' NO existe. Creándola desde cero...")
        Base.metadata.create_all(bind=engine)
        print("✅ Tabla 'users' creada.")
    else:
        print("ℹ️ La tabla 'users' ya existe. Continuando...")

    db = SessionLocal()
    
    try:
        # 2. Buscar o Crear Admin
        # Usamos rollback() preventivo por si acaso hubo basura antes
        db.rollback() 
        
        admin = db.query(User).filter(User.username == "admin").first()
        hashed_pw = pwd_context.hash("admin123") 

        if not admin:
            print("👤 El usuario 'admin' no existe. Creando nuevo...")
            new_admin = User(
                username="admin",
                hashed_password=hashed_pw,
                role="admin",
                full_name="Super Admin Nube"
            )
            db.add(new_admin)
            print("✅ Usuario 'admin' creado exitosamente.")
        else:
            print("🔄 El usuario 'admin' ya existe. Reseteando contraseña...")
            admin.hashed_password = hashed_pw
            print("✅ Contraseña actualizada a 'admin123'.")

        db.commit()
        print("\n🚀 ¡LISTO! Ya puedes entrar a https://refineryiq.dev")

    except Exception as e:
        print(f"❌ Error crítico: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_admin_user_v2()