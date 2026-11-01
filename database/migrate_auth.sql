-- ============================================================================
-- Spend Smart: Safe Multi-User Authentication Migration Script
-- Target: Aiven MySQL (defaultdb)
-- Safety: Non-destructive. Preserves all existing records in 'expenses'.
-- ============================================================================

-- 1. Create Users Table
CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  full_name VARCHAR(100) NOT NULL,
  email VARCHAR(191) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Add nullable user_id to expenses table (Existing 4 records remain intact as NULL)
ALTER TABLE expenses 
  ADD COLUMN IF NOT EXISTS user_id INT NULL AFTER id;

-- 3. Add index on user_id for high-performance scoped lookups
ALTER TABLE expenses 
  ADD INDEX IF NOT EXISTS idx_user_id (user_id);

-- 4. Add foreign key constraint linking expenses to users (enforces relational integrity)
-- Note: MySQL does not have 'ADD CONSTRAINT IF NOT EXISTS', so database_migration_manager.py
-- inspects information_schema before adding to prevent duplicate constraint errors.
-- ALTER TABLE expenses ADD CONSTRAINT fk_expenses_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT;
