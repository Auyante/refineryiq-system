import os
import bcrypt # Usamos la librería directa
from sqlalchemy import create_engine, Column, Integer, String, text, inspect
from sqlalchemy.orm import sessionmaker, declarative_base

# --- TU BASE DE DATOS EN LA NUBE ---
DATABASE_URL = "postgresql://refinery_db_user:c92JlEraE4hJy6qKjSxKGnPhnPESJnbK@dpg-d5vumciqcgvc73a0tq9g-a.virginia-postgres.render.com/refinery_db"

# Configuración SQLAlchemy
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Modelo de Usuario
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="admin")
    full_name = Column(String)

def fix_admin_user_v3():
    print("🌍 Conectando a Render PostgreSQL...")
    
    # 1. Asegurar que la tabla existe
    inspector = inspect(engine)
    if not inspector.has_table("users"):
        print("⚠️ Tabla 'users' no encontrada. Creándola...")
        Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # 2. Generar el Hash manualmente (Bypassing passlib)
        password_raw = "admin123"
        # Convertimos a bytes, generamos salt y hasheamos
        hashed_bytes = bcrypt.hashpw(password_raw.encode('utf-8'), bcrypt.gensalt())
        hashed_password = hashed_bytes.decode('utf-8') # Convertimos a string para guardar en DB
        
        # 3. Buscar o Crear Admin
        admin = db.query(User).filter(User.username == "admin").first()

        if not admin:
            print("👤 Creando usuario 'admin' nuevo...")
            new_admin = User(
                username="admin",
                hashed_password=hashed_password,
                role="admin",
                full_name="Super Admin Nube"
            )
            db.add(new_admin)
            print("✅ Usuario creado exitosamente.")
        else:
            print("🔄 Usuario 'admin' encontrado. Actualizando contraseña...")
            admin.hashed_password = hashed_password
            print("✅ Contraseña actualizada a 'admin123'.")

        db.commit()
        print("\n🚀 ¡ÉXITO! Ahora ve a https://refineryiq.dev y logueate.")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_admin_user_v3()