# Aiven Payment Schema Recovery Procedure

This is an operator-run procedure for repairing an existing BidSmart database
without recreating application tables or changing historical records. It is a
checklist with conditional statements, not a script to run as one batch. Do not
run `database/schema.sql` or migration 001 against an existing database.

No production database was inspected or modified while preparing this document.
The reported Workbench observations are not a substitute for the read-only
preflight below.

## What the repository establishes

- `migrations/001_initial_schema.sql` defines the original application schema,
  but starts by dropping and recreating application tables. Its presence in the
  repository does not prove it was applied to any specific database.
- `migrations/002_transaction_payment_lifecycle.sql` modifies the
  `transactions.payment_status` enum and adds `settled_at` and
  `idx_transactions_settled_at`. It is a non-idempotent `ALTER TABLE`; do not
  rerun it blindly.
- `migrations/003_razorpay_payment_attempts.sql` creates
  `payment_attempts` and `payment_webhook_events`. It is non-idempotent and
  depends on `transactions` already existing. Its `transaction_id INT` matches
  the original schema's `transactions.id INT`.
- `database/schema.sql` is a fresh-install schema, not an upgrade script. It
  drops existing tables, including the payment tables, and must never be used
  to repair an existing database.
- The repository contains no reliable migration ledger. Given the reported
  existing `transactions` table, absent `settled_at` and index, and absent
  payment tables, the exact scripts previously applied cannot be determined.
  The metadata preflight must decide each action separately.

Required dependency order is: established base tables (`001` schema or an
equivalent existing schema), transaction lifecycle changes (`002`), then
payment persistence tables (`003`).

## Required backup and recovery gate

Before any write:

1. Confirm the target database name and server version with the read-only
   preflight. Stop if the target is not the intended Aiven database.
2. Take a fresh Aiven on-demand backup and confirm it completed successfully.
3. Produce a separate, encrypted logical backup using the approved secure
   operator environment. Include routines, triggers, and events, as well as
   all application tables. Keep it access-restricted; do not put connection
   credentials on a command line or in shell history.
4. Confirm the restore procedure and permissions. An existing backup is not
   considered recoverable until a restore has been tested to an isolated
   database or the organization has otherwise verified its recovery process.
5. Schedule a maintenance window, pause application writes if required by the
   operator's consistency policy, and retain the pre-change backup until
   post-migration verification is complete.

If a backup cannot be made or the restore path is unknown, stop before DDL.

## Read-only preflight

Run these statements in Workbench against the confirmed target database. They
only read server metadata and rows. Do not share output containing credentials
or connection details.

```sql
SELECT DATABASE() AS target_database, VERSION() AS mysql_version;

SELECT TABLE_NAME, ENGINE
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME IN (
      'transactions',
      'payment_attempts',
      'payment_webhook_events'
  )
ORDER BY TABLE_NAME;

SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT,
       ORDINAL_POSITION
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND (
      (TABLE_NAME = 'transactions'
       AND COLUMN_NAME IN (
           'id', 'auction_id', 'buyer_id', 'seller_id', 'amount',
           'settlement_type', 'payment_status', 'payment_reference',
           'created_at', 'updated_at', 'settled_at'
       ))
      OR (TABLE_NAME = 'payment_attempts'
          AND COLUMN_NAME IN (
              'id', 'transaction_id', 'provider_order_id',
              'provider_payment_id', 'amount_minor', 'currency', 'status'
          ))
      OR (TABLE_NAME = 'payment_webhook_events'
          AND COLUMN_NAME IN ('event_id', 'event_type', 'received_at'))
  )
ORDER BY TABLE_NAME, ORDINAL_POSITION;

SELECT TABLE_NAME, INDEX_NAME, NON_UNIQUE, SEQ_IN_INDEX, COLUMN_NAME
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME IN (
      'transactions',
      'payment_attempts',
      'payment_webhook_events'
  )
ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;

SELECT TABLE_NAME, CONSTRAINT_NAME, CONSTRAINT_TYPE
FROM information_schema.TABLE_CONSTRAINTS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME IN ('transactions', 'payment_attempts', 'payment_webhook_events')
ORDER BY TABLE_NAME, CONSTRAINT_TYPE, CONSTRAINT_NAME;

SHOW CREATE TABLE transactions;
SELECT DISTINCT payment_status FROM transactions ORDER BY payment_status;
```

Before any DDL, record the following table counts in the change record so
they can be compared after repair:

```sql
SELECT 'users' AS table_name, COUNT(*) AS row_count FROM users
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'auctions', COUNT(*) FROM auctions
UNION ALL SELECT 'bids', COUNT(*) FROM bids
UNION ALL SELECT 'transactions', COUNT(*) FROM transactions;
```

Only run `SHOW CREATE TABLE payment_attempts` or
`SHOW CREATE TABLE payment_webhook_events` if the corresponding table is
reported as existing.

Stop for DBA review if `transactions` is absent or not InnoDB; if any listed
core column other than `settled_at` is absent or incompatible with the
application model; if `id` is not a signed `INT` primary key; if `amount` is
not compatible with `DECIMAL(12,2)`; if `settlement_type` is not exactly an
`ENUM` containing only `SIMULATED_DEMO`; if `payment_status` is not an `ENUM`;
if `updated_at` is not timestamp-compatible; if the target version is below
MySQL 8.0.16; or if existing values or constraints do not fit the rules below.
In particular, the signedness of `transactions.id` must match the signed
`INT` used for `payment_attempts.transaction_id`; MySQL foreign keys require
compatible types. MySQL versions before 8.0.16 may parse but not enforce
`CHECK` constraints; do not silently omit the required amount check.

## Conditional repair steps

Apply one statement at a time only after the preflight confirms its exact
precondition. These are not safe to execute as a blind batch.

### 1. Repair transaction lifecycle (migration 002)

The required `payment_status` enum values are exactly:

```text
SETTLEMENT_PENDING_DEMO
SETTLEMENT_COMPLETED_DEMO
SETTLEMENT_FAILED_DEMO
CANCELLED
```

- If `payment_status` already supports all four values, preserve it; do not
  modify it. If it is a strict superset, stop and have the DBA confirm that
  every additional value must be preserved before changing anything.
- If it is an `ENUM` containing only a subset of the four values above, first
  confirm that `SELECT DISTINCT` returned no values outside that set. Then,
  only if needed, apply:

```sql
ALTER TABLE transactions
    MODIFY COLUMN payment_status ENUM(
        'SETTLEMENT_PENDING_DEMO',
        'SETTLEMENT_COMPLETED_DEMO',
        'SETTLEMENT_FAILED_DEMO',
        'CANCELLED'
    ) NOT NULL DEFAULT 'SETTLEMENT_PENDING_DEMO';
```

- If `settled_at` is absent, apply:

```sql
ALTER TABLE transactions
    ADD COLUMN settled_at TIMESTAMP NULL DEFAULT NULL AFTER updated_at;
```

  If present, verify it is nullable and timestamp-compatible; stop if it has a
  different type/default rather than replacing it automatically.
- If `idx_transactions_settled_at` is absent and no equivalent single-column
  index on `settled_at` exists, apply:

```sql
CREATE INDEX idx_transactions_settled_at ON transactions (settled_at);
```

  If that name exists with a different definition, stop for review.

Historical `settled_at` remains NULL unless an authoritative completion time is
available. Do not infer settlement timestamps from auction close or row update
times.

### 2. Create missing payment persistence tables (migration 003)

First verify `transactions.id` is signed `INT` with the expected primary key.
If `payment_attempts` is absent, create it using the migration's constraints:

```sql
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
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_payment_attempts_transaction
        FOREIGN KEY (transaction_id)
        REFERENCES transactions(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_payment_attempt_amount CHECK (amount_minor >= 1),
    INDEX idx_payment_attempts_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

If `payment_webhook_events` is absent, create it:

```sql
CREATE TABLE payment_webhook_events (
    event_id VARCHAR(64) PRIMARY KEY,
    event_type VARCHAR(64) NOT NULL,
    received_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

If either table already exists, do not run `CREATE TABLE IF NOT EXISTS` as a
substitute for validation: that syntax can silently leave a wrongly defined
table in place. Compare its columns, exact compatible types (including
signedness), defaults, indexes, primary/unique keys, foreign key, engine, and
check constraint with migration 003. The recovery definition explicitly uses
InnoDB for both new tables; the webhook-event migration relies on the server's
default engine, so verify that its effective engine is InnoDB. Stop and prepare
a separate, reviewed repair if a table is partial or incompatible; never drop
or recreate it automatically.

## Partial failure behavior

MySQL DDL implicitly commits; do not assume a multi-statement migration rolls
back as one transaction. If a statement fails:

1. Stop; do not immediately rerun either migration file or the whole procedure.
2. Record the exact failed statement and error for the DBA without exposing
   credentials.
3. Re-run the read-only preflight to determine which prior DDL statements
   persisted.
4. Verify data and constraints before applying only the missing, independently
   validated statement.
5. If a table exists but is partial or incompatible, do not drop it or silently
   omit constraints. Obtain a reviewed, data-preserving repair plan.

## Post-change verification

Repeat the preflight metadata queries and confirm:

- `transactions.payment_status` accepts all required enum values and preserves
  its `NOT NULL` and default behavior.
- `transactions.settled_at` is nullable and
  `idx_transactions_settled_at` indexes that column.
- `payment_attempts` is InnoDB; its `transaction_id` is a unique signed `INT`
  FK to the matching signed `transactions.id`; provider IDs are unique; status
  enum, amount check, and status index match migration 003.
- `payment_webhook_events` is InnoDB with its primary key and expected columns.
- The post-change counts for users, products, auctions, bids, and transactions
  match the recorded pre-change counts. No historical settlement timestamps
  were fabricated.

## Deployment order and readiness

The new application code tolerates a missing payment schema (analytics shows
payment metrics as unavailable; payment routes return HTTP 503), so deploying
it before the repair is safe and already fixes the analytics `Network Error`.
The reverse is not true: the code currently deployed (commit `a539cd8`) fails
with HTTP 500 on the missing table or column. Recommended order:

1. Review, commit and push the local changes yourself (nothing is staged).
2. Let Render deploy the backend. Confirm `/api/v1/health` responds and
   Analytics loads with payment metrics shown as unavailable.
3. Complete the backup gate, preflight and conditional repairs above.
4. Re-check Analytics (payment metrics should become available) and the
   seller Payments & Earnings tab (no 503).
5. Let Vercel deploy the frontend; it needs `VITE_API_BASE_URL` set to the
   Render URL, and the backend `BACKEND_CORS_ORIGINS` must list the Vercel
   origin. Do not print or share the values.

Payment checkout and webhooks remain unavailable (HTTP 503) until the repair is
complete. Do not enable Razorpay credentials in production before then.

Smoke test after each stage, with real accounts: login; catalog and search;
auction detail; Analytics with date and category filters; seller dashboard and
Payments & Earnings; buyer payment history; admin transaction monitoring; and
Render logs free of 1146 or 1054 errors.

After DBA verification, deploy the code through the normal release process and
check Render health plus seller, buyer-payment-history, webhook, and analytics
endpoints. A successful schema check alone does not prove the production
application is fixed; use authenticated smoke tests and inspect Render logs.
