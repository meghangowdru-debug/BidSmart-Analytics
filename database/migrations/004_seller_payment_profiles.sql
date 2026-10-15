-- BidSmart Analytics — Seller payment setup tracking (simulated demo mode).
-- Apply once, after migrations 001-003. Additive only: one CREATE TABLE.
-- No DROP, no ALTER, no data backfill. Existing sellers have no row and are
-- treated as NOT_STARTED by the application until they complete setup.
-- MySQL DDL implicitly commits; take and restore-test the normal backup first.
-- Stores setup state only: no bank, card, or provider credentials.
-- Check that the table is absent before running (see AIVEN_PAYMENT_SCHEMA_RECOVERY.md);
-- do not rerun if it already exists.

CREATE TABLE seller_payment_profiles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    seller_id INT NOT NULL UNIQUE,
    setup_mode ENUM('DEMO_SIMULATED') NOT NULL DEFAULT 'DEMO_SIMULATED',
    status ENUM('PENDING', 'DEMO_COMPLETED') NOT NULL DEFAULT 'PENDING',
    completed_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_seller_payment_profiles_user FOREIGN KEY (seller_id)
        REFERENCES users(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    INDEX idx_seller_payment_profiles_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
