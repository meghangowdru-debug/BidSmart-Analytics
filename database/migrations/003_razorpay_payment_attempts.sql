-- BidSmart Analytics — Razorpay test-mode payment service persistence.
-- Apply once after 002_transaction_payment_lifecycle.sql.
-- MySQL DDL implicitly commits; take the normal database backup before applying.
-- No provider credentials or historical payment data are added by this migration.

CREATE TABLE payment_attempts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    transaction_id INT NOT NULL UNIQUE,
    provider_order_id VARCHAR(64) NOT NULL UNIQUE,
    provider_payment_id VARCHAR(64) NULL UNIQUE,
    amount_minor BIGINT NOT NULL,
    currency CHAR(3) NOT NULL,
    status ENUM('ORDER_CREATED', 'PAYMENT_FAILED', 'PAYMENT_COMPLETED')
        NOT NULL DEFAULT 'ORDER_CREATED',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_payment_attempts_transaction FOREIGN KEY (transaction_id)
        REFERENCES transactions(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_payment_attempt_amount CHECK (amount_minor >= 1),
    INDEX idx_payment_attempts_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE payment_webhook_events (
    event_id VARCHAR(64) PRIMARY KEY,
    event_type VARCHAR(64) NOT NULL,
    received_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
