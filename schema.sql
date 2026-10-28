CREATE DATABASE IF NOT EXISTS spend_smart_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE spend_smart_db;

CREATE TABLE IF NOT EXISTS expenses (
  id INT AUTO_INCREMENT PRIMARY KEY,
  amount DECIMAL(10,2) NOT NULL,
  category VARCHAR(50) NOT NULL,
  expense_date DATE NOT NULL,
  description VARCHAR(255) DEFAULT '',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_expense_date (expense_date),
  INDEX idx_category (category)
);
