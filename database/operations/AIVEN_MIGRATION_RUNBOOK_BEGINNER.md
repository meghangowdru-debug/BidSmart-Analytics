# Beginner Runbook: Repair the Aiven Schema (migrations 002, 003, 004)

Read this top to bottom. Do the steps **in order**, **one at a time**.
This file prepares the work; nothing in it has been run. The reference
explanations live in [AIVEN_PAYMENT_SCHEMA_RECOVERY.md](./AIVEN_PAYMENT_SCHEMA_RECOVERY.md).

## Golden rules

- Never run `database/schema.sql` or `migrations/001_initial_schema.sql` on
  Aiven. They delete tables.
- Never paste a whole migration file. Paste **one statement** from this runbook.
- MySQL commits every `ALTER`/`CREATE` immediately. There is no undo.
- Never put passwords, tokens or connection strings in chat, files or Git.
- Do not invent `settled_at` times or `payment_attempts` rows for old transactions.

## Scope of this preflight

For this request, run only the backup check in Phase B and the read-only checks
in Phase C. Stop after A4. Phases D-G describe possible future writes; do not
run any `ALTER`, `CREATE`, migration, deployment, or configuration change as
part of this preflight.

Keep `ENABLE_SELLER_PAYMENT_SETUP` disabled (`false`). This procedure does not
inspect or change Render settings. Before any later deployment, confirm that
setting is false without sharing other environment values. Do not enable it
unless the database schema is verified and you have chosen and communicated a
seller rollout policy.

## STOP conditions (apply to every step)

Stop and do nothing further if **any** of these happens:

1. A statement returns an error.
2. A check returns something different from "Expected".
3. You are unsure which database you are connected to (it must be `defaultdb`).
4. A result is missing or you did not run the check.

When you stop, do not retry and do not "fix it" with other SQL. Copy the exact
statement and error text (no credentials) and ask for review.

## Phase A: Known facts and what is still unverified

The "previously reported" facts below came from earlier checks. They are not
live-verified by this document; recheck them in Workbench before relying on
them.

| Item | Status |
|---|---|
| MySQL 8.4.11 (CHECK constraints are enforced) | Previously reported; recheck A1 |
| `transactions` and `users` are InnoDB | Previously reported; recheck A2 |
| `transactions.updated_at` exists (NOT NULL timestamp) | Previously reported; recheck A2 |
| Constraint names `chk_payment_attempt_amount`, `fk_payment_attempts_transaction`, `fk_seller_payment_profiles_user` are unused | Previously reported; recheck A2 |
| Statuses: 4 pending, 14 completed; no failed value in enum | Previously reported; recheck A4 |
| `settled_at`, its index, and the 3 new tables are absent | Previously reported; recheck A2 |
| `users.id` / `transactions.id` are **signed** | **UNVERIFIED** (check A2) |
| Server time zone is UTC | **UNVERIFIED** (check A3; `SYSTEM` is not an answer) |
| Backups are restorable | **UNVERIFIED** (Phase B) |

### Why the two unverified items block you

- **Signedness:** the new foreign keys use signed `INT`. If either `id` is
  `INT UNSIGNED`, MySQL rejects the key (error 3780) and statement 4 or 6 fails.
- **Time zone:** the app writes times in UTC. `seller_payment_profiles` uses
  `DATETIME DEFAULT CURRENT_TIMESTAMP`, which uses the server's zone. If the
  server is not UTC, `created_at` and `completed_at` would disagree.

## Phase B: Backup gate (no SQL)

1. In the Aiven console, verify the project and MySQL service are the intended
   production service. Do not copy service credentials into chat or a file.
2. Use Aiven's on-demand backup option for that service. Wait for its status to
   show successful completion, then record the service, completion time, and
   backup identifier in your private change record. The previously reported
   backups from 13 and 14 October 2026 do not prove that a fresh backup is ready
   for this change. Do not change backup schedules or retention settings.
3. Arrange a restore test to a **separate, non-production test service**. In the
   restore workflow, verify the target service identity before confirming
   anything. Check any extra service cost or quota first. The target must not
   be the production service that contains `defaultdb`. If the console offers
   only an in-place restore, the target is ambiguous, or the test service would
   incur unapproved charges, **STOP** and ask the Aiven administrator for a
   safe isolated restore procedure.
4. Wait for the isolated restore to report success. Verify in the console that
   the restored service is the test service, not production. Connect Workbench
   only to that isolated service and run this read-only identity check:

   ```sql
   SELECT DATABASE() AS db, VERSION() AS version, @@hostname AS server_host;
   ```

   Compare the Workbench connection's host with the isolated test service's
   endpoint in the Aiven console, and confirm the service/host identity is the
   isolated target. `defaultdb` may also be the database name inside the
   restored test service; the service identity, not the database name alone,
   must distinguish it from production. Do not run migrations or write SQL on
   the isolated copy as part of this restore check.
5. Keep the restore completion record and the backup identifier with the
   change record. Do not restore over production and do not alter backup
   configuration.

If you cannot do 1 and 2, **STOP**. Do not run any `ALTER` or `CREATE`.
If you cannot prove that the restore target was isolated and the restore
succeeded, also **STOP** before any production write.

## Phase C: Read-only checks (safe, change nothing)

Run each statement separately in MySQL Workbench against the confirmed
production service and `defaultdb`. These queries read metadata or rows; they
do not change the database. Do not paste their output into chat if it contains
connection details or sensitive data.

**A1. Right database**
```sql
SELECT DATABASE() AS db, VERSION() AS version;
```
Expected: one row showing database `defaultdb` and MySQL `8.4.11`. This proves
which database and server this Workbench session reached; it does not prove the
rest of the schema is compatible. If either value differs or is missing, STOP.

**A2. Signedness** (the key check)
```sql
SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND COLUMN_NAME = 'id'
  AND TABLE_NAME IN ('users', 'transactions');

SELECT TABLE_NAME, ENGINE
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME IN (
      'users', 'transactions', 'payment_attempts',
      'payment_webhook_events', 'seller_payment_profiles'
  )
ORDER BY TABLE_NAME;

SELECT TABLE_NAME, INDEX_NAME, NON_UNIQUE, SEQ_IN_INDEX, COLUMN_NAME
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME IN (
      'users', 'transactions', 'payment_attempts',
      'payment_webhook_events', 'seller_payment_profiles'
  )
ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;

SHOW CREATE TABLE users;
SHOW CREATE TABLE transactions;

SELECT TABLE_NAME, CONSTRAINT_NAME, CONSTRAINT_TYPE
FROM information_schema.TABLE_CONSTRAINTS
WHERE CONSTRAINT_SCHEMA = DATABASE()
  AND CONSTRAINT_NAME IN (
      'fk_payment_attempts_transaction',
      'chk_payment_attempt_amount',
      'fk_seller_payment_profiles_user'
  )
ORDER BY TABLE_NAME, CONSTRAINT_NAME;
```
Expected:

- The ID query returns exactly two rows, each `COLUMN_TYPE` is signed `int`
  (no `unsigned`), and the `SHOW CREATE TABLE` output confirms each ID is the
  `AUTO_INCREMENT` primary key.
- The table query returns `users` and `transactions`, both `InnoDB`. The three
  payment tables were previously reported absent; if any now exists, do not
  create it. Inspect its `SHOW CREATE TABLE` output and compare its entire
  definition with the matching migration before making any decision.
- `SHOW CREATE TABLE transactions` confirms the complete existing definition,
  including `amount DECIMAL(12,2)`, the `settlement_type` and
  `payment_status` enums, `updated_at`, the existing foreign keys, and
  `chk_transaction_amount`. Confirm `settled_at` is absent before migration
  002. `SHOW CREATE TABLE users` must show the parent key definition.
- The index query shows existing indexes. Confirm
  `idx_transactions_settled_at` is absent (or stop and review an existing or
  equivalent index); do not add a duplicate index.
- The constraint-name query returns no rows. It searches the whole database
  for names that the new tables need, not just the affected tables.

These checks establish parent-key type/engine compatibility and reveal
pre-existing constraints that could conflict. If a table, column, key,
constraint, or engine differs from these expectations, STOP; do not repair it
with ad hoc SQL. If a payment table already exists, run `SHOW CREATE TABLE`
for that table only as a read-only inspection; do not run its `CREATE TABLE`
statement.

**A3. Time zone**
```sql
SELECT @@session.time_zone AS session_zone,
       @@global.time_zone AS global_zone,
       @@system_time_zone AS system_zone,
       NOW() AS server_local_now,
       UTC_TIMESTAMP() AS utc_now,
       TIMESTAMPDIFF(SECOND, UTC_TIMESTAMP(), NOW()) AS offset_seconds;
```
Expected: `offset_seconds` is `0`, and session/global settings resolve to UTC.
If either setting is `SYSTEM`, confirm `system_zone` is UTC and Aiven will keep
it UTC. A zero offset at one instant alone does not establish a non-DST zone.
If UTC cannot be confirmed, STOP and ask for a review before any migration.
This matters because the application supplies UTC datetimes and MySQL
`TIMESTAMP` values are converted using the connection time zone; a mismatch
can shift stored/read settlement times. Do not change the server time zone as
part of this preflight.

**A4. Baseline (write these results down)**
```sql
SELECT COUNT(*) AS row_count,
       SUM(CRC32(CONCAT_WS('|', id, auction_id, buyer_id, seller_id, amount,
                           settlement_type, payment_status, payment_reference,
                           created_at, updated_at))) AS fingerprint
FROM transactions;

SELECT payment_status, COUNT(*) AS n
FROM transactions GROUP BY payment_status ORDER BY payment_status;

SELECT 'users' AS t, COUNT(*) AS n FROM users
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'auctions', COUNT(*) FROM auctions
UNION ALL SELECT 'bids', COUNT(*) FROM bids
UNION ALL SELECT 'transactions', COUNT(*) FROM transactions;
```
Expected: row_count 18; `SETTLEMENT_COMPLETED_DEMO` 14 and
`SETTLEMENT_PENDING_DEMO` 4; counts 36, 41, 41, 428, 18. **Write down the
`fingerprint` number.** The fingerprint combines the existing transaction
identifiers, amount, types, statuses, reference, and timestamps into a
comparison value; it is a practical change detector, not a cryptographic
proof. The separate row and status counts help catch changes too.

If any count or status distribution differs from the documented baseline, or
the fingerprint is empty/different from a repeat of the same unchanged
preflight, STOP. Do not assume the difference is harmless or update the
baseline to make it match. Ask for review and reconcile the difference before
considering a migration.

Only continue if A1, A2, A3 and A4 all match.

## Phase D: Migration 002 (3 statements)

### Step 1: add `SETTLEMENT_FAILED_DEMO` to the status list
```sql
ALTER TABLE transactions
    MODIFY COLUMN payment_status ENUM(
        'SETTLEMENT_PENDING_DEMO',
        'SETTLEMENT_COMPLETED_DEMO',
        'SETTLEMENT_FAILED_DEMO',
        'CANCELLED'
    ) NOT NULL DEFAULT 'SETTLEMENT_PENDING_DEMO';
```
Verify (read-only):
```sql
SELECT payment_status, COUNT(*) AS n FROM transactions GROUP BY payment_status ORDER BY payment_status;
SELECT COUNT(*) AS row_count,
       SUM(CRC32(CONCAT_WS('|', id, auction_id, buyer_id, seller_id, amount,
                           settlement_type, payment_status, payment_reference,
                           created_at, updated_at))) AS fingerprint
FROM transactions;
SHOW CREATE TABLE transactions;
```
Expected: 14 completed, 4 pending; row_count 18; **fingerprint identical to the
number you wrote down**; `SHOW CREATE TABLE` shows the four enum values,
`NOT NULL DEFAULT 'SETTLEMENT_PENDING_DEMO'`, the three foreign keys and
`chk_transaction_amount`. Any difference: STOP.

### Step 2: add the `settled_at` column
```sql
ALTER TABLE transactions
    ADD COLUMN settled_at TIMESTAMP NULL DEFAULT NULL AFTER updated_at;
```
Verify:
```sql
SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'transactions' AND COLUMN_NAME = 'settled_at';
SELECT COUNT(*) AS row_count, SUM(settled_at IS NOT NULL) AS rows_with_settled_at FROM transactions;
```
Expected: `timestamp`, nullable `YES`, default `NULL`; row_count 18;
`rows_with_settled_at` is **0**. Anything else: STOP.

### Step 3: add the `settled_at` index
```sql
CREATE INDEX idx_transactions_settled_at ON transactions (settled_at);
```
Verify:
```sql
SHOW INDEX FROM transactions WHERE Key_name = 'idx_transactions_settled_at';
```
Expected: exactly one row, column `settled_at`. Otherwise STOP.

After Step 3, the code that expects `settled_at` is safe to deploy. Do not
deploy yet; see Phase G.

## Phase E: Migration 003 (2 statements)

### Step 4: create `payment_attempts`
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
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_payment_attempts_transaction FOREIGN KEY (transaction_id)
        REFERENCES transactions(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_payment_attempt_amount CHECK (amount_minor >= 1),
    INDEX idx_payment_attempts_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```
Verify:
```sql
SHOW CREATE TABLE payment_attempts;
SELECT COUNT(*) AS row_count FROM payment_attempts;
```
Expected: InnoDB, the foreign key to `transactions` (`id`), the CHECK, the
unique keys, and **0 rows**. Do not insert rows to "make old payments look
verified". Otherwise STOP.

### Step 5: create `payment_webhook_events`
```sql
CREATE TABLE payment_webhook_events (
    event_id VARCHAR(64) PRIMARY KEY,
    event_type VARCHAR(64) NOT NULL,
    received_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```
Verify:
```sql
SHOW CREATE TABLE payment_webhook_events;
SELECT COUNT(*) AS row_count FROM payment_webhook_events;
```
Expected: InnoDB, primary key `event_id`, and 0 rows. Otherwise STOP.

### Checkpoint after migration 003
Rerun the three queries in A4. Counts must still be 36, 41, 41, 428, 18; the
transactions fingerprint must equal the number you wrote down; 14 completed and
4 pending. Any difference: STOP.

## Phase F: Decide about existing sellers (decision gate, no SQL)

Migration 004 creates an empty table. The application setting
`ENABLE_SELLER_PAYMENT_SETUP` defaults to `false`, so creating the table and
deploying the code will not immediately block sellers. If you later enable the
flag, **every current seller without a row will be blocked from creating
products and auctions until they complete simulated setup in their Seller
Console**. Their existing data is not touched, and they can still view, edit,
cancel and close what they have.

Options. **No rollout option has been chosen yet:**

| Option | What happens | Trade-off |
|---|---|---|
| A. Require everyone | Enable `ENABLE_SELLER_PAYMENT_SETUP=true`; each seller completes the demo setup once | Simplest and honest, but sellers are blocked until they act. Tell them first. |
| B. Pre-complete existing sellers | A separate, reviewed INSERT script marks them `DEMO_COMPLETED` | Nobody acknowledged the demo notice, so the "setup complete" record would be untrue. If chosen, it needs a reviewed script, an audit record, and your explicit approval. |
| C. Staged | Create the table with the flag off, announce, then explicitly enable the gate | Supported by the existing feature flag; sellers without completed setup will be blocked once it is enabled. |

**Do not run Step 6 until you have chosen.** Also remember: sellers see
`SETTLEMENT_COMPLETED_DEMO` transactions without `settled_at` or a payment
attempt as **not payment-verified**. Their totals exclude those 14 historical
rows. This is correct; do not "fix" it by inventing data.

## Phase G: Migration 004, then deploy

### Step 6: create `seller_payment_profiles`

Only proceed after choosing the rollout policy above and verifying A2/A3. Do
not enable enforcement until after this table is created and sellers are
informed.
```sql
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
```
Verify:
```sql
SHOW CREATE TABLE seller_payment_profiles;
SELECT COUNT(*) AS row_count FROM seller_payment_profiles;
SELECT TABLE_NAME, CONSTRAINT_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = DATABASE() AND REFERENCED_TABLE_NAME IS NOT NULL
  AND TABLE_NAME IN ('payment_attempts', 'seller_payment_profiles');
```
Expected: InnoDB; **0 rows**; two foreign keys (to `transactions.id` and
`users.id`). Otherwise STOP.

### Final check
Rerun the full A4 block. Counts 36, 41, 41, 428, 18, the original fingerprint,
14 completed / 4 pending. Also rerun:
```sql
SELECT COUNT(*) AS row_count,
       SUM(settled_at IS NOT NULL) AS rows_with_settled_at
FROM transactions;
```
Expected: `row_count` 18 and `rows_with_settled_at` 0.

### Then, and only then, with your explicit approval
1. Push the local commit.
2. Let Render deploy the backend, then Vercel the frontend.
3. Keep `ENABLE_SELLER_PAYMENT_SETUP=false` unless you explicitly choose to
   enforce the flow. After communication and confirming migration 004, set it
   to `true` in the backend secret/configuration dashboard and redeploy Render.
4. Smoke test with real accounts: health endpoint, login, Analytics, seller
   Payments & Earnings, close one auction, seller Payment Setup then listing,
   and check Render logs for MySQL errors 1146 and 1054.

If a step fails partway, follow "Partial failure behavior" in the recovery doc.
Never drop or recreate a table to recover.

## Approvals you must give (nothing happens without them)

1. Backup restore proven (Phase B).
2. Each write step 1 to 6, one at a time.
3. Your seller decision (Phase F).
4. Push and deploy.
