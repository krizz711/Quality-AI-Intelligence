CREATE TABLE IF NOT EXISTS grr_analyses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  operators INTEGER NOT NULL,
  parts INTEGER NOT NULL,
  trials INTEGER NOT NULL,
  grr_percent REAL NOT NULL,
  repeatability_percent REAL NOT NULL,
  reproducibility_percent REAL NOT NULL,
  number_of_distinct_categories INTEGER,
  part_tolerance REAL,
  verdict TEXT CHECK(verdict IN ('excellent','acceptable','unacceptable')),
  ai_analysis TEXT,
  raw_measurements TEXT
);

CREATE TABLE IF NOT EXISTS spc_data (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  process_name TEXT NOT NULL,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  measurement_value REAL NOT NULL,
  sample_mean REAL,
  ucl REAL,
  lcl REAL,
  centerline REAL,
  in_control BOOLEAN DEFAULT 1,
  violation_type TEXT
);

CREATE TABLE IF NOT EXISTS alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  type TEXT NOT NULL,
  severity TEXT NOT NULL,
  message TEXT NOT NULL,
  process_name TEXT,
  status TEXT DEFAULT 'active' CHECK(status IN ('active','resolved','acknowledged')),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  resolved_at DATETIME,
  resolved_by TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  event_type TEXT NOT NULL,
  description TEXT NOT NULL,
  user_id TEXT,
  ip_address TEXT,
  metadata TEXT
);