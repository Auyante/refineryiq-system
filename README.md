# 🏭 RefineryIQ - Sistema de Gestión Inteligente de Refinerías

![Dashboard Preview](docs/screenshots/dashboard.png)

## 🚀 **Descripción del Proyecto**
Sistema completo de gestión industrial desarrollado para optimizar operaciones en refinerías petroleras. Incluye monitoreo en tiempo real, análisis predictivo y gestión de activos. Proyecto final de Ingeniería de Sistemas desarrollado como demostración técnica completa.

## ✨ **Características Principales**

### 📊 **Dashboard en Tiempo Real**
- Visualización de KPIs operativos (OEE, eficiencia, producción)
- Gráficos interactivos con Recharts
- Actualización automática cada 60 segundos
- Generación de reportes PDF profesionales

### ⚠️ **Sistema de Alertas Inteligentes**
- Clasificación por severidad (HIGH, MEDIUM, LOW)
- Historial completo de incidencias (50 registros)
- Reconocimiento automático de alertas antiguas
- Integración con unidades y tags de proceso

### 🔧 **Gestión de Activos**
- Inventario completo de 9+ equipos industriales
- Estado operativo en tiempo real (OPERATIONAL/MAINTENANCE)
- Lecturas de sensores con unidades de medida
- Búsqueda y filtrado avanzado

### ⚡ **Análisis Energético**
- Auditoría de consumo por unidad (CDU, FCC, HT, ALK)
- Cálculo de índice de eficiencia (0-100%)
- Detección de ineficiencias con recomendaciones
- Visualización con barras de progreso

### 🤖 **Mantenimiento Predictivo**
- Modelo Random Forest para predicción de fallas
- Probabilidades de riesgo por equipo (0-100%)
- Recomendaciones automatizadas por nivel de riesgo
- Gráfico de radar para análisis multidimensional

### 📦 **Gestión de Suministros**
- Monitor de tanques IoT (niveles, capacidad, estado)
- Inventario químico con estados (OK/LOW/CRITICAL)
- Generación automática de órdenes de compra
- Exportación a CSV

## 🛠️ **Stack Tecnológico Exacto**

### **Frontend (React 18.2.0)**
```json
{
  "react": "^18.2.0",
  "react-dom": "^18.2.0",
  "react-icons": "^4.12.0",
  "react-router-dom": "^6.20.0",
  "axios": "^1.6.2",
  "recharts": "^2.10.0",
  "whatwg-fetch": "^3.6.19"
}
### **Backend (Python FastAPI)**
fastapi==0.104.1
uvicorn[standard]==0.24.0
asyncpg==0.29.0
pydantic==2.5.0
python-multipart==0.0.6
sqlalchemy==2.0.25
apscheduler==3.10.4
psycopg2-binary==2.9.9
python-dateutil==2.8.2
passlib[bcrypt]==1.7.4
numpy==1.24.3
pandas==2.0.3
scikit-learn==1.3.0
joblib==1.3.2