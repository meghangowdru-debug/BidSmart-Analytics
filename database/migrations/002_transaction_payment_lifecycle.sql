-- BidSmart Analytics — transaction payment lifecycle migration
-- Apply once after 001_initial_schema.sql using the project's migration process.
-- MySQL DDL implicitly commits; take the normal database backup before applying.
-- Existing payment status values are retained for auction-closing compatibility.
-- Historical settled_at values are left NULL because no authoritative completion
-- timestamp exists for transactions created before this migration.

ALTER TABLE transactions
    MODIFY COLUMN payment_status ENUM(
        'SETTLEMENT_PENDING_DEMO',
        'SETTLEMENT_COMPLETED_DEMO',
        'SETTLEMENT_FAILED_DEMO',
        'CANCELLED'
    ) NOT NULL DEFAULT 'SETTLEMENT_PENDING_DEMO',
    ADD COLUMN settled_at TIMESTAMP NULL DEFAULT NULL AFTER updated_at,
    ADD INDEX idx_transactions_settled_at (settled_at);
