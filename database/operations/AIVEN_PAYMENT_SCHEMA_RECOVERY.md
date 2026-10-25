# Aiven Payment Schema Recovery Procedure

This is an operator-run procedure for repairing an existing BidSmart database
without recreating application tables or changing historical records. It is a
checklist with conditional statements, not a script to run as one batch. Do not
run `database/schema.sql` or migration 001 against an existing database.

Beginners: follow the step-by-step
[AIVEN_MIGRATION_RUNBOOK_BEGINNER.md](./AIVEN_MIGRATION_RUNBOOK_BEGINNER.md)
instead; this file is the reference behind it. The required order is: backup and
verification, migration 002, migration 003, a deliberate decision about existing
sellers, migration 004, then code deployment. Seller setup enforcement is
controlled by `ENABLE_SELLER_PAYMENT_SETUP` and defaults to disabled; enable it
only after the schema exists and sellers have been informed. Before any statement, also verify
that `users.id` and `transactions.id` are signed and that the server time zone
is UTC (`SYSTEM` is not proof); the runbook has the queries.

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
      'users',
      'transactions',
      'payment_attempts',
      'payment_webhook_events',
      'seller_payment_profiles'
  )
ORDER BY TABLE_NAME;

SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT,
       ORDINAL_POSITION
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND (
      (TABLE_NAME = 'users' AND COLUMN_NAME = 'id')
      OR (TABLE_NAME = 'transactions'
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
      OR (TABLE_NAME = 'seller_payment_profiles'
          AND COLUMN_NAME IN (
              'id', 'seller_id', 'setup_mode', 'status', 'completed_at',
              'created_at', 'updated_at'
          ))
  )
ORDER BY TABLE_NAME, ORDINAL_POSITION;

SELECT TABLE_NAME, INDEX_NAME, NON_UNIQUE, SEQ_IN_INDEX, COLUMN_NAME
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME IN (
      'users',
      'transactions',
      'payment_attempts',
      'payment_webhook_events',
      'seller_payment_profiles'
  )
ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;

SELECT TABLE_NAME, CONSTRAINT_NAME, CONSTRAINT_TYPE
FROM information_schema.TABLE_CONSTRAINTS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME IN (
      'users', 'transactions', 'payment_attempts', 'payment_webhook_events',
      'seller_payment_profiles'
  )
ORDER BY TABLE_NAME, CONSTRAINT_TYPE, CONSTRAINT_NAME;

SELECT TABLE_NAME, CONSTRAINT_NAME, CONSTRAINT_TYPE
FROM information_schema.TABLE_CONSTRAINTS
WHERE CONSTRAINT_SCHEMA = DATABASE()
  AND CONSTRAINT_NAME IN (
      'fk_payment_attempts_transaction',
      'chk_payment_attempt_amount',
      'fk_seller_payment_profiles_user'
  )
ORDER BY TABLE_NAME, CONSTRAINT_NAME;

SHOW CREATE TABLE users;
SHOW CREATE TABLE transactions;
SELECT DISTINCT payment_status FROM transactions ORDER BY payment_status;

SELECT @@session.time_zone AS session_time_zone,
       @@global.time_zone AS global_time_zone,
       @@system_time_zone AS system_time_zone,
       NOW() AS session_now,
       UTC_TIMESTAMP() AS utc_now,
       TIMESTAMPDIFF(SECOND, UTC_TIMESTAMP(), NOW()) AS offset_seconds;
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

Expected parent tables `users` and `transactions` must be InnoDB; both `id`
columns must be signed `INT` primary keys, and the transaction definition must
retain its existing required columns, foreign keys, and amount check. The
new constraint-name query must return no rows. The time-zone query must show a
zero offset and a UTC session configuration; if a setting is `SYSTEM`, verify
that the system zone is UTC and that Aiven will keep it UTC. A zero offset at
one instant alone does not establish a non-DST zone.

Only run `SHOW CREATE TABLE payment_attempts`,
`SHOW CREATE TABLE payment_webhook_events`, or
`SHOW CREATE TABLE seller_payment_profiles` if the corresponding table is
reported as existing.

Stop for DBA review if either parent table (`users` or `transactions`) is
absent or not InnoDB; if any listed transaction column other than `settled_at`
is absent or incompatible with the application model; if either `users.id` or
`transactions.id` is not a signed `INT` primary key; if `amount` is
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
check constraint with migration 003. Migration 003 and this recovery
definition both set `ENGINE=InnoDB` explicitly on both new tables, so an
existing table with a different engine is incompatible. Stop and prepare
a separate, reviewed repair if a table is partial or incompatible; never drop
or recreate it automatically.

### 3. Create the seller payment setup table (migration 004)

Needed only by the mandatory seller payment setup feature. Read-only preflight:

```sql
SELECT COUNT(*) AS table_present
FROM information_schema.tables
WHERE table_schema = DATABASE() AND table_name = 'seller_payment_profiles';
```

If the count is 0, confirm `users.id` is `INT` (it must match the foreign key),
then run only the `CREATE TABLE` in `migrations/004_seller_payment_profiles.sql`.
Do not use `IF NOT EXISTS` as a substitute for validation. If the table already
exists, compare it with the migration instead of rerunning it. The migration adds
no rows: existing sellers appear as NOT_STARTED and must complete the simulated
setup in the Seller Console before they can catalog products or create auctions.
Setup is a simulated demo acknowledgement only: no bank details are collected
and no payouts are enabled. Real provider onboarding is not implemented.

Create this table before enabling the backend gate. While
`ENABLE_SELLER_PAYMENT_SETUP=false` (the default), seller product and auction
creation do not depend on this table. If enforcement is enabled while the table
is absent, those creation routes return HTTP 503 (fail closed); login, catalog,
bidding and analytics remain unaffected.

## Per-statement runbook with post-checks

Use this order with explicit human approval before each write. Each statement
commits immediately and cannot be rolled back. Stop at the first failed
post-check. Do not run the migration files as a batch.

Before statement 1, record this fingerprint of the existing rows (the 18-row
baseline, excluding the new column) and the status distribution:

```sql
SELECT COUNT(*) AS row_count,
       SUM(CRC32(CONCAT_WS('|', id, auction_id, buyer_id, seller_id, amount,
                           settlement_type, payment_status, payment_reference,
                           created_at, updated_at))) AS fingerprint
FROM transactions;
SELECT payment_status, COUNT(*) FROM transactions GROUP BY payment_status;
```

**Statement 1 (002, enum).** Adds `SETTLEMENT_FAILED_DEMO`; existing values are
kept. Because the new value is inserted before `CANCELLED`, MySQL rebuilds the
table and maps rows by value name.

```sql
ALTER TABLE transactions
    MODIFY COLUMN payment_status ENUM(
        'SETTLEMENT_PENDING_DEMO',
        'SETTLEMENT_COMPLETED_DEMO',
        'SETTLEMENT_FAILED_DEMO',
        'CANCELLED'
    ) NOT NULL DEFAULT 'SETTLEMENT_PENDING_DEMO';
```

Post-check 1: rerun the fingerprint and status distribution; `row_count` and
`fingerprint` and every status count must equal the baseline. Also run
`SHOW CREATE TABLE transactions` and confirm the four enum values, `NOT NULL`,
the default, the three foreign keys and `chk_transaction_amount`.

**Statement 2 (002, column).** Run only if `updated_at` exists.

```sql
ALTER TABLE transactions
    ADD COLUMN settled_at TIMESTAMP NULL DEFAULT NULL AFTER updated_at;
```

Post-check 2: `SELECT COUNT(*), SUM(settled_at IS NOT NULL) FROM transactions;`
must return the baseline count and `0`. No settlement time is invented.

**Statement 3 (002, index).**

```sql
CREATE INDEX idx_transactions_settled_at ON transactions (settled_at);
```

Post-check 3: `SHOW INDEX FROM transactions WHERE Key_name =
'idx_transactions_settled_at';` returns one row on `settled_at`.

At this point the `settled_at` compatibility risk is closed, but the complete
schema repair is not. Do not deploy the new backend yet. Finish statements 4-6,
complete their post-checks and the final data-count verification, and resolve
the existing-seller rollout decision first.

**Statement 4 (003, `payment_attempts`) and statement 5 (003,
`payment_webhook_events`).** Run each `CREATE TABLE` shown in section 2,
one at a time, without `IF NOT EXISTS`.

Post-check 4/5: confirm the table exists with `ENGINE=InnoDB`; for
`payment_attempts`, confirm with `SHOW CREATE TABLE` the unique keys, the
foreign key to `transactions(id)`, `chk_payment_attempt_amount` and
`idx_payment_attempts_status`. Confirm both new tables have zero rows.

**Statement 6 (004).** Run the single `CREATE TABLE` from
`migrations/004_seller_payment_profiles.sql`. Its definition is: `id INT
AUTO_INCREMENT` primary key; `seller_id INT NOT NULL UNIQUE`; `setup_mode
ENUM('DEMO_SIMULATED') NOT NULL DEFAULT 'DEMO_SIMULATED'`; `status
ENUM('PENDING','DEMO_COMPLETED') NOT NULL DEFAULT 'PENDING'`; `completed_at
DATETIME NULL`; `created_at` and `updated_at` as `DATETIME NOT NULL DEFAULT
CURRENT_TIMESTAMP` (`updated_at` also `ON UPDATE CURRENT_TIMESTAMP`); foreign
key `fk_seller_payment_profiles_user (seller_id)` to `users(id)` with
`ON DELETE RESTRICT ON UPDATE CASCADE`; index `idx_seller_payment_profiles_status`;
InnoDB, utf8mb4. The application writes `completed_at` in UTC, and `DATETIME`
defaults use the session time zone, so verify session, global, and system
time-zone settings in the preflight before applying this migration.

Post-check 6: run `SHOW CREATE TABLE seller_payment_profiles` and confirm the
full definition, defaults, unique seller key, status index, InnoDB engine and
foreign key to `users(id)`; confirm it has zero rows. Finally rerun the
five-table count query from the preflight; every count must equal the baseline.

Legacy rows: transactions that are `SETTLEMENT_COMPLETED_DEMO` before this
repair keep `settled_at = NULL` and have no `payment_attempts` row. The backend
treats them as not payment-verified: they are excluded from verified payment
volume, completed-settlement totals and analytics, and shown with
`payment_verified = false`. They are still listed and counted in
`transaction_count`. Do not backfill timestamps or attempts to change this
without authoritative provider evidence.

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

Source review and isolated tests confirm that the local application handles
missing payment tables in Analytics and payment endpoints (payment routes return
HTTP 503 and Analytics marks payment metrics unavailable). Auction closing loads
the `Transaction` model, which includes `settled_at`; the new application code
is therefore not safe to deploy against a schema where migration 002 is still
missing. The migrations preserve the existing status labels and add columns or
tables, but the currently deployed application version and its compatibility
with these migrations have not been verified. No live Render logs, deployment
metadata, or Aiven schema were inspected. Recommended order:

1. Complete the backup gate and the read-only preflight above.
2. With approval, apply migration 002 (statements 1-3) and pass each
   post-check. Then apply migration 003 (statements 4-5).
3. Decide how existing sellers are handled, then apply migration 004
   (statement 6). The feature flag defaults to disabled, so existing sellers
   are not unexpectedly blocked by deployment. When the table exists and sellers
   have been informed, explicitly set `ENABLE_SELLER_PAYMENT_SETUP=true` to
   enforce the simulated setup. Every seller without a completed profile row
   will then be blocked from product and auction creation until completing it.
4. Review, commit and push the local changes yourself (nothing is staged).
5. Let Render deploy the backend. Confirm `/api/v1/health` responds, then
   re-check Analytics (payment metrics available), the seller Payments &
   Earnings tab (no 503), and closing an auction.
6. Let Vercel deploy the frontend; it needs `VITE_API_BASE_URL` set to the
   Render URL, and the backend `BACKEND_CORS_ORIGINS` must list the Vercel
   origin. Do not print or share the values.

Do not deploy the new application code before the database repair is complete.
Migration 002 is required for auction closing; migrations 003 and 004 are
required for payment persistence and seller setup. Keep the existing deployed
version in service until all migration post-checks pass.

With the local application code, payment checkout and webhooks return HTTP 503
until their required schema exists. The live response is unverified. Do not
enable Razorpay credentials in production before then.

Smoke test after each stage, with real accounts: login; catalog and search;
auction detail; Analytics with date and category filters; seller dashboard and
Payments & Earnings; buyer payment history; admin transaction monitoring; and
Render logs free of 1146 or 1054 errors.

After DBA verification, deploy the code through the normal release process and
check Render health plus seller, buyer-payment-history, webhook, and analytics
endpoints. A successful schema check alone does not prove the production
application is fixed; use authenticated smoke tests and inspect Render logs.
