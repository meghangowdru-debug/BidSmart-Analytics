# BidSmart Analytics — Database Architecture & Engineering Guide (Phase 2)

**Component:** Relational Storage & Analytical Schema  
**Database Engine:** MySQL 8.0+ / MariaDB 10.5+ (InnoDB Storage Engine)  
**Character Set & Collation:** `utf8mb4` / `utf8mb4_unicode_ci`  
**Schema Version:** 1.0.0 (Phase 2 Single Source of Truth)  
**Target Release:** Production v1.0  

---

## 1. Architectural Overview & Design Philosophy

The **BidSmart Analytics** database is engineered to solve the hardest problems in auction systems:
1. **Zero Race Conditions:** Millisecond-level concurrent bids during auction closing moments are serialized cleanly with pessimistic row locks (`SELECT ... FOR UPDATE`).
2. **Immutable Financial Auditing:** Bids and audit logs form an append-only ledger; transactions record demo settlements; status changes are strictly governed by state machines.
3. **Optimized Analytics Execution:** Schema normalization (3NF) is paired with composite B-Tree indexes, enabling sub-millisecond aggregations, window ranking (`DENSE_RANK`, `ROW_NUMBER`), and time-series growth tracking (`LAG`).
4. **Marketplace Integrity:** Anti-self-bidding rules, minimum increment validation, and anti-sniping soft-close extensions are enforced directly at the database layer.

---

## 2. Entity-Relationship Diagram (ERD)

The complete visual ERD and cardinality matrix are documented in [`ERD.md`](./ERD.md).

```
                      +-------------------+
                      |       roles       |
                      +---------+---------+
                                | 1
                                | *
                      +---------+---------+
                      |       users       |
                      +---+---+---+---+---+
                          |   |   |   |
         +----------------+   |   |   +----------------+
         | 1                  | 1 | 1                  | 1
         | *                  | * | *                  | *
+--------+--------+  +--------+-+ +-+--------+  +------+---------+
|    products     |  |watchlist | |notificat.|  |   audit_logs   |
+--------+--------+  +----------+ +----------+  +----------------+
         | 1
         | 1
+--------+--------+
|    auctions     |<-------------------+
+---+--------+----+                    |
    | 1      | 1                       |
    | *      | 1                       |
+---+----+ +-+--------------+          |
|  bids  | |  transactions  |          |
+--------+ +----------------+          |
    |                                  |
    +--- (winning_bid circular FK) ----+
```

---

## 3. Comprehensive Data Dictionary

### 3.1 `roles`
System security roles defining access entitlements for Role-Based Access Control (RBAC).

| Column | Data Type | Nullable | Key / Constraint | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `INT` | No | `PRIMARY KEY AUTO_INCREMENT` | Unique role identifier. |
| `name` | `VARCHAR(50)` | No | `UNIQUE` | Role name (`'ADMIN'`, `'SELLER'`, `'BUYER'`). |
| `description`| `VARCHAR(255)`| No | None | Human-readable role description. |
| `created_at` | `TIMESTAMP` | No | `DEFAULT CURRENT_TIMESTAMP` | Role creation timestamp. |

### 3.2 `users`
Platform accounts for buyers, sellers, and administrators.

| Column | Data Type | Nullable | Key / Constraint | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `INT` | No | `PRIMARY KEY AUTO_INCREMENT` | Unique user identifier. |
| `username` | `VARCHAR(50)` | No | `UNIQUE` | Unique user handle (alphanumeric). |
| `email` | `VARCHAR(100)`| No | `UNIQUE` | Unique contact and login email. |
| `password_hash` | `VARCHAR(255)`| No | None | `bcrypt` cryptographic password hash. |
| `full_name` | `VARCHAR(100)`| No | None | Legal or display full name. |
| `phone` | `VARCHAR(20)` | Yes | None | Optional contact phone number. |
| `role_id` | `INT` | No | `FK -> roles(id)` | Assigned RBAC role. |
| `status` | `ENUM(...)` | No | `DEFAULT 'ACTIVE'` | `'ACTIVE'`, `'SUSPENDED'`, `'PENDING_VERIFICATION'`. |
| `created_at` | `TIMESTAMP` | No | `DEFAULT CURRENT_TIMESTAMP` | Account creation timestamp. |
| `updated_at` | `TIMESTAMP` | No | `ON UPDATE CURRENT_TIMESTAMP` | Last profile update timestamp. |

*Indexes:*
- `idx_users_role (role_id)`
- `idx_users_status (status)`

### 3.3 `categories`
Standard product taxonomy classifications for filtering and analytical aggregations.

| Column | Data Type | Nullable | Key / Constraint | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `INT` | No | `PRIMARY KEY AUTO_INCREMENT` | Category identifier. |
| `name` | `VARCHAR(50)` | No | `UNIQUE` | Display category name. |
| `slug` | `VARCHAR(60)` | No | `UNIQUE` | URL-safe slug identifier. |
| `description`| `TEXT` | Yes | None | Category description and scope. |
| `icon_name` | `VARCHAR(50)` | No | `DEFAULT 'Tag'` | Frontend Lucide icon identifier. |
| `created_at` | `TIMESTAMP` | No | `DEFAULT CURRENT_TIMESTAMP` | Record creation timestamp. |

### 3.4 `products`
Items submitted by sellers to be auctioned.

| Column | Data Type | Nullable | Key / Constraint | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `INT` | No | `PRIMARY KEY AUTO_INCREMENT` | Unique product identifier. |
| `seller_id` | `INT` | No | `FK -> users(id)` | Seller who owns the listing. |
| `category_id`| `INT` | No | `FK -> categories(id)` | Category classification. |
| `title` | `VARCHAR(150)`| No | None | Product title / headline. |
| `description`| `TEXT` | No | None | Detailed markdown description. |
| `condition_status` | `ENUM(...)` | No | `DEFAULT 'USED'` | `'NEW'`, `'LIKE_NEW'`, `'USED'`, `'VINTAGE'`. |
| `image_url` | `VARCHAR(500)`| No | None | High-resolution primary image URL. |
| `thumbnail_url`| `VARCHAR(500)`| Yes| None | Compressed thumbnail preview URL. |
| `created_at` | `TIMESTAMP` | No | `DEFAULT CURRENT_TIMESTAMP` | Submission timestamp. |
| `updated_at` | `TIMESTAMP` | No | `ON UPDATE CURRENT_TIMESTAMP` | Last update timestamp. |

*Indexes:*
- `FULLTEXT INDEX ft_products_title_desc (title, description)` (MySQL full-text search)
- `idx_products_category (category_id)`
- `idx_products_seller (seller_id)`

### 3.5 `auctions`
Core auction lifecycle state machine managing pricing, schedules, and resolution.

| Column | Data Type | Nullable | Key / Constraint | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `INT` | No | `PRIMARY KEY AUTO_INCREMENT` | Unique auction identifier. |
| `product_id` | `INT` | No | `FK -> products(id), UNIQUE` | 1:1 linked product listing. |
| `starting_price` | `DECIMAL(12,2)` | No | `CHECK (starting_price >= 0.01)` | Minimum opening bid. |
| `current_highest_bid`| `DECIMAL(12,2)`| Yes | None | Real-time highest accepted bid. |
| `reserve_price` | `DECIMAL(12,2)` | Yes | None | Confidential reserve price threshold. |
| `minimum_increment` | `DECIMAL(10,2)` | No | `DEFAULT 1.00, CHECK >= 0.01` | Required minimum bid step. |
| `start_time` | `TIMESTAMP` | No | None | Bidding open timestamp. |
| `end_time` | `TIMESTAMP` | No | `CHECK (end_time > start_time)` | Scheduled auction close timestamp. |
| `status` | `ENUM(...)` | No | `DEFAULT 'DRAFT'` | `'DRAFT'`, `'SCHEDULED'`, `'ACTIVE'`, `'COMPLETED'`, `'UNSOLD'`, `'RESERVE_NOT_MET'`, `'CANCELLED'`. |
| `winner_id` | `INT` | Yes | `FK -> users(id)` | Final winning bidder. |
| `winning_bid_id` | `INT` | Yes | `FK -> bids(id)` | Final winning bid record. |
| `total_bids` | `INT UNSIGNED`| No | `DEFAULT 0` | Running counter of accepted bids. |
| `created_at` | `TIMESTAMP` | No | `DEFAULT CURRENT_TIMESTAMP` | Record creation timestamp. |
| `updated_at` | `TIMESTAMP` | No | `ON UPDATE CURRENT_TIMESTAMP` | State transition timestamp. |

*Indexes:*
- `idx_auctions_status_end_time (status, end_time)`: Sub-millisecond closure query index.
- `idx_auctions_winner (winner_id)`
- `idx_auctions_highest_bid (current_highest_bid)`

### 3.6 `bids`
Immutable financial ledger of all bids submitted and accepted.

| Column | Data Type | Nullable | Key / Constraint | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `INT` | No | `PRIMARY KEY AUTO_INCREMENT` | Unique bid transaction ID. |
| `auction_id` | `INT` | No | `FK -> auctions(id)` | Target auction listing. |
| `bidder_id` | `INT` | No | `FK -> users(id)` | User who submitted the bid. |
| `bid_amount` | `DECIMAL(12,2)` | No | `CHECK (bid_amount >= 0.01)` | Monetary amount submitted. |
| `bid_time` | `TIMESTAMP(3)`| No | `DEFAULT CURRENT_TIMESTAMP(3)` | Millisecond-accurate timestamp. |
| `is_winning_bid` | `BOOLEAN` | No | `DEFAULT FALSE` | True if currently highest bid. |
| `is_flagged_anomaly` | `BOOLEAN` | No | `DEFAULT FALSE` | True if flagged for human review. |
| `ip_address` | `VARCHAR(45)` | No | `DEFAULT '127.0.0.1'` | IPv4/IPv6 client address for audit. |
| `created_at` | `TIMESTAMP` | No | `DEFAULT CURRENT_TIMESTAMP` | Ingestion timestamp. |

*Indexes:*
- `idx_bids_auction_amount (auction_id, bid_amount DESC)`: Sub-millisecond highest bid retrieval.
- `idx_bids_bidder (bidder_id)`
- `idx_bids_time (bid_time)`
- `idx_bids_flagged (is_flagged_anomaly)`
- `idx_bids_auction_time (auction_id, bid_time)`

### 3.7 `watchlist`
User bookmarks for monitoring active listings.

| Column | Data Type | Nullable | Key / Constraint | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `INT` | No | `PRIMARY KEY AUTO_INCREMENT` | Bookmark ID. |
| `user_id` | `INT` | No | `FK -> users(id)` | User bookmarking the listing. |
| `auction_id` | `INT` | No | `FK -> auctions(id)` | Target auction listing. |
| `created_at` | `TIMESTAMP` | No | `DEFAULT CURRENT_TIMESTAMP` | Bookmark timestamp. |

*Unique Composite Constraint:* `UNIQUE KEY uq_user_auction_watchlist (user_id, auction_id)` prevents duplicate bookmarks.

### 3.8 `notifications`
Real-time and asynchronous user notifications.

| Column | Data Type | Nullable | Key / Constraint | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `INT` | No | `PRIMARY KEY AUTO_INCREMENT` | Notification identifier. |
| `user_id` | `INT` | No | `FK -> users(id)` | Recipient user ID. |
| `type` | `ENUM(...)` | No | `DEFAULT 'SYSTEM'` | `'OUTBID'`, `'AUCTION_WON'`, `'AUCTION_ENDED'`, `'PRICE_ALERT'`, `'ANOMALY_ALERT'`, `'SYSTEM'`. |
| `title` | `VARCHAR(150)`| No | None | Notification title. |
| `message` | `TEXT` | No | None | Full notification body text. |
| `is_read` | `BOOLEAN` | No | `DEFAULT FALSE` | Read status. |
| `link_url` | `VARCHAR(255)`| Yes| None | Deep link to UI route. |
| `created_at` | `TIMESTAMP` | No | `DEFAULT CURRENT_TIMESTAMP` | Dispatch timestamp. |

*Indexes:*
- `idx_notifications_user_read (user_id, is_read)`

### 3.9 `transactions` (Simulated Demo Settlement)
Non-monetary demo escrow settlements for completed auctions.

| Column | Data Type | Nullable | Key / Constraint | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `INT` | No | `PRIMARY KEY AUTO_INCREMENT` | Transaction identifier. |
| `auction_id` | `INT` | No | `FK -> auctions(id), UNIQUE` | Associated completed auction (1:1). |
| `buyer_id` | `INT` | No | `FK -> users(id)` | Winning buyer. |
| `seller_id` | `INT` | No | `FK -> users(id)` | Listing seller. |
| `amount` | `DECIMAL(12,2)` | No | `CHECK (amount >= 0.01)` | Final winning amount ($). |
| `settlement_type` | `ENUM(...)` | No | `DEFAULT 'SIMULATED_DEMO'` | `'SIMULATED_DEMO'`. |
| `payment_status` | `ENUM(...)` | No | `DEFAULT 'SETTLEMENT_PENDING_DEMO'` | `'SETTLEMENT_PENDING_DEMO'`, `'SETTLEMENT_COMPLETED_DEMO'`, `'CANCELLED'`. |
| `payment_reference` | `VARCHAR(64)` | No | `UNIQUE` | Demo reference hash (`TX-DEMO-...`). |
| `created_at` | `TIMESTAMP` | No | `DEFAULT CURRENT_TIMESTAMP` | Invoice creation timestamp. |
| `updated_at` | `TIMESTAMP` | No | `ON UPDATE CURRENT_TIMESTAMP` | Settlement status change timestamp. |

### 3.10 `audit_logs`
Immutable compliance and security audit trail.

| Column | Data Type | Nullable | Key / Constraint | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `INT` | No | `PRIMARY KEY AUTO_INCREMENT` | Log event identifier. |
| `user_id` | `INT` | Yes | `FK -> users(id) ON DELETE SET NULL` | User performing or subject of action. |
| `action` | `VARCHAR(60)` | No | None | Event name (`'BID_ACCEPTED'`, `'USER_ROLE_ELEVATED'`, etc.). |
| `entity_type` | `VARCHAR(50)` | No | None | Affected entity (`'AUCTION'`, `'USER'`, `'BID'`). |
| `entity_id` | `INT` | Yes | None | Primary key of affected entity. |
| `old_values` | `JSON` | Yes | None | Pre-modification state diff. |
| `new_values` | `JSON` | Yes | None | Post-modification state diff. |
| `ip_address` | `VARCHAR(45)` | No | `DEFAULT '127.0.0.1'` | Client IP address. |
| `created_at` | `TIMESTAMP` | No | `DEFAULT CURRENT_TIMESTAMP` | Event timestamp. |

*Indexes:*
- `idx_audit_action (action)`
- `idx_audit_created (created_at)`
- `idx_audit_user (user_id)`

---

## 4. Secure Bidding & Concurrency Control Deep Dive

### 4.1 The High-Concurrency Dilemma in Auctions
During the closing seconds of an auction, multiple bidders may submit bids simultaneously:
- **Without Pessimistic Locking:** Transaction A reads highest bid $500. Transaction B reads highest bid $500. Both submit $510. Both pass validation. Transaction B overwrites Transaction A. Two bidders believe they are winning, or total bid counters desynchronize.
- **With BidSmart Pessimistic Locking:** When a bid request arrives, the backend executes `SELECT ... FOR UPDATE` on the targeted auction row. MySQL InnoDB acquires an exclusive write lock. All other concurrent transactions attempting to read or write that auction row are queued until the active transaction commits.

### 4.2 Database Stored Procedure: `sp_place_bid`
The platform implements an atomic stored procedure `sp_place_bid` encapsulating all validation and serialization steps:
1. `START TRANSACTION;`
2. `SELECT ... FROM auctions WHERE id = p_auction_id FOR UPDATE;` (Acquires exclusive row lock).
3. **Anti-Self-Bidding Check:** Rejects if `seller_id == p_bidder_id` (`FORBIDDEN_SELF_BID`).
4. **Status & Time Check:** Rejects if status is not `ACTIVE` or if current time is outside `[start_time, end_time]`.
5. **Threshold Check:** Rejects if `bid_amount < (current_highest_bid + minimum_increment)` (`OUTBID_CONFLICT`).
6. **Insert Bid:** Writes new bid with `is_winning_bid = TRUE`.
7. **Demote Prior Bids:** Updates previous bids for that auction to `is_winning_bid = FALSE`.
8. **Anti-Sniping Soft-Close:** If remaining time $\le 30\text{ seconds}$, extends `end_time` by 60 seconds.
9. **Update Auction State:** Updates `current_highest_bid`, `winner_id`, `winning_bid_id`, and increments `total_bids`.
10. **Write Audit Log & Commit:** Records structured JSON diff and commits the transaction.

---

## 5. Auction Closing & Winner Determination

### 5.1 Automated Closure Daemon: `sp_close_expired_auctions`
A background scheduler calls `sp_close_expired_auctions` every 5 seconds.
The procedure selects active auctions where `end_time <= CURRENT_TIMESTAMP` with `FOR UPDATE`:
- **Branch 1: Zero Bids Received (`total_bids = 0`):**
  - Transitions status to `UNSOLD`.
  - Sets `winner_id = NULL` and `winning_bid_id = NULL`.
  - Dispatches an `AUCTION_ENDED` notification to the seller.
- **Branch 2: Bids Received but Below Reserve (`current_highest_bid < reserve_price`):**
  - Transitions status to `RESERVE_NOT_MET`.
  - Sets `winner_id = NULL`.
  - Notifies seller of highest market valuation.
- **Branch 3: Valid Winning Bids (`total_bids >= 1` and Reserve Met):**
  - Transitions status to `COMPLETED`.
  - Sets `winner_id` to highest accepted bidder.
  - Generates simulated escrow invoice in `transactions` with status `SETTLEMENT_PENDING_DEMO`.
  - Dispatches `AUCTION_WON` notification to buyer and `AUCTION_ENDED` notification to seller.

---

## 6. Seed Data & Local Development Quickstart

### 6.1 Database Setup via CLI
```bash
# 1. Connect to MySQL as root or privileged user
mysql -u root -p

# 2. Run initial schema migration
mysql -u bidsmart_user -p<YOUR_DATABASE_PASSWORD> bidsmart_db < database/schema.sql

# 3. Load comprehensive seed data (32 users, 40 auctions, ~400 bids)
mysql -u bidsmart_user -p<YOUR_DATABASE_PASSWORD> bidsmart_db < database/seed_data.sql

# 4. Verify seed data
mysql -u bidsmart_user -p<YOUR_DATABASE_PASSWORD> bidsmart_db -e "SELECT * FROM vw_auction_kpi_summary;"
```

### 6.2 Running Automated Verification Test Suite
```bash
python3 database/test_schema.py
```
This automated test suite verifies:
- All 10 tables, views, and stored procedures exist.
- Primary key, foreign key, and check constraint integrity.
- Anti-self-bidding rejection.
- Minimum increment enforcement.
- Outbid conflict serialization.
- High-concurrency pessimistic locking simulation.
- Automated auction closure and winner resolution.
