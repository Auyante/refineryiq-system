import os
from sqlalchemy import create_engine, Column, Integer, String, text
from sqlalchemy.orm import sessionmaker, declarative_base
from passlib.context import CryptContext

# --- TU BASE DE DATOS EN LA NUBE ---
# (Ya la puse aquí para que no tengas que buscarla)
DATABASE_URL = "postgresql://refinery_db_user:c92JlEraE4hJy6qKjSxKGnPhnPESJnbK@dpg-d5vumciqcgvc73a0tq9g-a.virginia-postgres.render.com/refinery_db"

# Configuración de SQLAlchemy
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Modelo de Usuario (Solo lo necesario para crear el login)
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="admin")
    full_name = Column(String)

def fix_admin_user():
    print("🌍 Conectando a Render PostgreSQL...")
    db = SessionLocal()
    
    try:
        # 1. Verificar si la tabla existe
        try:
            user_count = db.query(User).count()
            print(f"📊 Usuarios actuales en la base de datos: {user_count}")
        except Exception:
            print("⚠️ La tabla 'users' no existe. Creándola ahora...")
            Base.metadata.create_all(bind=engine)

        # 2. Buscar o Crear Admin
        admin = db.query(User).filter(User.username == "admin").first()
        
        hashed_pw = pwd_context.hash("admin123") # <--- LA CONTRASEÑA SERÁ ESTA

        if not admin:
            print("👤 El usuario 'admin' NO existe. Creándolo...")
            new_admin = User(
                username="admin",
                hashed_password=hashed_pw,
                role="admin",
                full_name="Super Admin Nube"
            )
            db.add(new_admin)
            print("✅ Usuario creado exitosamente.")
        else:
            print("🔄 El usuario 'admin' YA existe. Reseteando su contraseña...")
            admin.hashed_password = hashed_pw
            print("✅ Contraseña actualizada a 'admin123'.")

        db.commit()
        print("\n🚀 ¡LISTO! Intenta loguearte en la web ahora.")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    fix_admin_user()