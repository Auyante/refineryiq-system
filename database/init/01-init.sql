-- Tabla principal de datos de proceso
CREATE TABLE IF NOT EXISTS process_data (
    id SERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL,
    unit_id VARCHAR(20) NOT NULL,
    tag_id VARCHAR(50) NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    quality INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabla de alertas
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    time TIMESTAMPTZ DEFAULT NOW(),
    unit_id VARCHAR(20),
    tag_id VARCHAR(50),
    message TEXT,
    severity VARCHAR(10),
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by VARCHAR(50)
);

-- Tabla de KPIs
CREATE TABLE IF NOT EXISTS kpis (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    unit_id VARCHAR(20),
    efficiency DOUBLE PRECISION,
    throughput DOUBLE PRECISION,
    energy_consumption DOUBLE PRECISION,
    quality_score DOUBLE PRECISION
);

-- Índices para mejor performance
CREATE INDEX IF NOT EXISTS idx_process_data_time ON process_data (time DESC);
CREATE INDEX IF NOT EXISTS idx_process_data_unit ON process_data (unit_id);
CREATE INDEX IF NOT EXISTS idx_alerts_acknowledged ON alerts (acknowledged, time DESC);
CREATE INDEX IF NOT EXISTS idx_kpis_unit ON kpis (unit_id, timestamp DESC);

-- Datos iniciales de ejemplo
INSERT INTO kpis (unit_id, efficiency, throughput, energy_consumption, quality_score) VALUES
('CDU-101', 87.5, 10500, 45.2, 94.3),
('FCC-201', 82.3, 7500, 68.7, 88.5),
('HT-301', 91.2, 5200, 32.1, 96.8);

-- Insertar algunas alertas de ejemplo
INSERT INTO alerts (unit_id, tag_id, message, severity) VALUES
('FCC-201', 'TEMP_REACTOR', 'Temperatura elevada en reactor FCC', 'high'),
('CDU-101', 'PRESS_TOWER', 'Presión fuera de rango normal', 'medium');