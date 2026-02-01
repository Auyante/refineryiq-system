import os
import codecs

def fix_frontend_files():
    print("🚑 ARREGLANDO RUTAS Y CODIFICACIÓN DEL FRONTEND...")
    
    # Rutas base (asumiendo que ejecutas desde 'backend/')
    base_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(base_dir, '..', 'frontend', 'src')
    dashboard_path = os.path.join(frontend_dir, 'views', 'Dashboard.js')
    index_path = os.path.join(frontend_dir, 'index.js')

    # 1. ARREGLAR INDEX.JS (Error Unicode BOM)
    if os.path.exists(index_path):
        print("📄 Corrigiendo codificación de index.js...")
        try:
            # Leer con utf-8-sig maneja el BOM automáticamente
            with open(index_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()
            # Guardar como utf-8 limpio elimina el BOM
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print("   ✅ index.js arreglado.")
        except Exception as e:
            print(f"   ❌ Error en index.js: {e}")

    # 2. ARREGLAR DASHBOARD.JS (Errores de rutas)
    if os.path.exists(dashboard_path):
        print("📄 Corrigiendo rutas en Dashboard.js...")
        try:
            with open(dashboard_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # --- Correcciones de Rutas ---
            # Como movimos el archivo una carpeta adentro (views/), 
            # tenemos que salir un nivel (../) para encontrar los archivos.
            
            # 1. CSS: './App.css' -> '../App.css'
            content = content.replace("from './App.css'", "from '../App.css'")
            content = content.replace('from "./App.css"', 'from "../App.css"')
            
            # 2. Componentes: './components/...' -> '../components/...'
            content = content.replace("from './components/", "from '../components/")
            content = content.replace('from "./components/', 'from "../components/')
            
            # 3. Eliminar Router (Dashboard ya no es la App principal)
            # Quitamos las importaciones de routing que ya no se usan aquí
            content = content.replace("BrowserRouter as Router,", "")
            content = content.replace("BrowserRouter as Router", "")
            content = content.replace("Routes,", "")
            content = content.replace("Route,", "")
            content = content.replace("Route", "")
            
            # Quitamos las etiquetas <Router> que envuelven el return
            content = content.replace("<Router>", "")
            content = content.replace("</Router>", "")

            # Guardar cambios
            with open(dashboard_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print("   ✅ Dashboard.js arreglado (rutas actualizadas).")
            
        except Exception as e:
            print(f"   ❌ Error en Dashboard.js: {e}")
    else:
        print(f"   ⚠️ No encontré el archivo: {dashboard_path}")
        print("      Asegúrate de haber creado la carpeta 'views' y el archivo 'Dashboard.js'")

if __name__ == "__main__":
    fix_frontend_files()
