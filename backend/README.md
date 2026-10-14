# BidSmart Analytics — FastAPI Backend, Bidding Engine & Settlement System

**Module:** Product Catalog, Auction Lifecycle, Secure Bidding Engine, Winner Settlement & Closing, In-App Notifications, RBAC Security, and Connection Pool  
**Framework:** FastAPI 0.110+ (Python 3.11+ / 3.12+ / 3.13+)  
**ORM:** SQLAlchemy 2.0 (Core & ORM)  
**Security:** Native Bcrypt (rounds=12) & Python-Jose JWT (HS256)  
**Concurrency & Locking:** MariaDB/MySQL Stored Procedure (`sp_place_bid`) & SQLAlchemy `SELECT ... FOR UPDATE` Pessimistic Row Locking  
**Database Driver:** PyMySQL  
**Database Engine:** MySQL 8.0+ / MariaDB 10.5+ (InnoDB)  
**Phases Status:**  
- **Phase 3:** Complete & Verified (Database Connection Pool, Latency Diagnostics, Model Mappings)  
- **Phase 4:** Complete & Verified (User Registration, Bcrypt Hashing, JWT Authentication, RBAC Enforcements)  
- **Phase 5:** Complete & Verified (Product Catalog, Auction Management, Whitelisted Filtering/Sorting, Lifecycle Guards)  
- **Phase 6:** Complete & Verified (Atomic Bidding Engine, Concurrency Locking, Anti-Sniping, Bid History Masking)  
- **Phase 7:** Complete & Verified (Auction Closing, Winner Settlement, Reserve Rules, Idempotency, In-App Notifications)  

---

## 1. Architectural Overview & Deliverables

The **BidSmart Analytics** platform implements an end-to-end auction marketplace with real-time atomic bidding, fraud mitigation, idempotent settlement, and event-driven notifications:

1. **Atomic Bidding Engine (`POST /api/v1/auctions/{id}/bids`):**
   - **Role Policy & Integrity Governance:** Only active, authenticated **`BUYER`** accounts may place bids. Sellers and Administrators are strictly forbidden (`HTTP 403 Forbidden`):
     - *Sellers* are prohibited from bidding on any listing to prevent shill bidding and artificial price inflation.
     - *Administrators* are prohibited from bidding to eliminate conflicts of interest, as admins have access to inspect private reserve prices and user accounts.
   - **Anti-Self-Bidding Guard:** Sellers cannot bid on their own listings under any circumstances.
   - **Pricing Invariants:**
     - First bid must meet or exceed the auction's `starting_price`.
     - Subsequent bids must meet or exceed `current_highest_bid + minimum_increment`.
   - **Lifecycle Guards:** Bids are rejected on auctions that have not started (`SCHEDULED`), have expired (`end_time <= now`), or are in closed states (`COMPLETED`, `UNSOLD`, `CANCELLED`, `RESERVE_NOT_MET`).
   - **Client Protection:** Clients cannot tamper with or directly supply `current_highest_bid`, `winner_id`, or `total_bids`. The client supplies only `bid_amount`.

2. **Concurrency & Pessimistic Row Locking:**
   - Every bid acquires an exclusive row-level lock (`SELECT ... FOR UPDATE`) on the target auction record inside an isolated ACID transaction (`sp_place_bid` or SQLAlchemy fallback).
   - When multiple competing bids arrive simultaneously, transactions are serialized. The first valid bid updates the auction aggregate state; subsequent conflicting bids are rejected with `HTTP 400 Bad Request` (`OUTBID_CONFLICT`) without corrupting state or causing double-winner anomalies.
   - Atomic state transitions: updates `current_highest_bid`, `winner_id`, `winning_bid_id`, and `total_bids` in the same transaction. Previous winning bids are demoted (`is_winning_bid = FALSE`).

3. **Anti-Sniping Dynamic Extension:**
   - If a valid bid is placed within the final **30 seconds** of an active auction, the engine automatically extends the `end_time` by **60 seconds**.
   - This thwarts malicious automated sniping bots and gives human bidders fair opportunity to respond.
   - The anti-sniping extension is recorded in `audit_logs` and reflected in the updated `end_time`.

4. **Bid History & Anonymity Masking (`GET /api/v1/auctions/{id}/bids`):**
   - **Public & Competing Buyers:** Bidder usernames are masked (e.g. `elena_r` $\rightarrow$ `e***r`, `collector_dan` $\rightarrow$ `c***n`) and `bidder_id` is omitted (`null`) to prevent off-platform collusion.
   - **Listing Seller & Platform Admins:** Full bidder identities and IDs are revealed for fulfillment and dispute management.
   - **Self-Inspection:** Logged-in buyers always see their own unmasked identity with `is_own_bid: true`.

5. **Auction Closing & Winner Settlement (`POST /api/v1/auctions/{id}/close` & `/close-expired`):**
   - **Pessimistic Locking & Idempotency:** Auction closing acquires an exclusive `SELECT ... FOR UPDATE` row lock on the auction record. If the auction is already in a terminal state (`COMPLETED`, `UNSOLD`, `RESERVE_NOT_MET`, `CANCELLED`), the service immediately returns `already_closed: true` without duplicating settlements, transactions, or notifications.
   - **Zero-Bid Resolution (`UNSOLD`):** If an expired auction receives zero bids, its status transitions to `UNSOLD`. `winner_id` and `final_price` remain `null`, and the listing seller is notified that their listing ended with no bids.
   - **Reserve Price Rule Enforcement (`RESERVE_NOT_MET`):** If the highest bid fails to reach the seller's private `reserve_price`, no winner is declared. Status transitions to `RESERVE_NOT_MET`, `winner_id` and `final_price` are set to `null`, all bids are demoted to not winning (`is_winning_bid = FALSE`), and no transaction record is created. Both the seller and top bidders receive explanatory notifications.
   - **Reserve Met / Normal Settlement (`COMPLETED`):** When the reserve is met (or no reserve was configured), status transitions to `COMPLETED`. `winner_id` is set to the highest bidder, and winning bid status is marked `is_winning_bid = TRUE`.
   - **Simulated Demo Transaction:** Automatically inserts a demo settlement transaction record in the `transactions` table with `settlement_type='SIMULATED_DEMO'`, `payment_status='SETTLEMENT_PENDING_DEMO'`, unique transaction reference (`TX-DEMO-{auction_id}-{timestamp}`), and foreign key link.
   - **RBAC & Governance:** Sellers may close only their own listings once the scheduled `end_time` has elapsed. Platform administrators may close any auction and may optionally pass `force=true` to force close an active auction before its scheduled deadline.

6. **In-App Notifications Engine & Lifecycle (`/api/v1/notifications`):**
   - **Real-Time Event Triggers:**
     - `OUTBID`: Instantly dispatched to a leading bidder when displaced by a higher incoming bid.
     - `AUCTION_WON`: Dispatched to the winning buyer upon successful auction settlement.
     - `AUCTION_ENDED`: Dispatched to the listing seller and participating bidders informing them of the final outcome (Sold, Unsold, or Reserve Not Met).
   - **User Inbox Management:**
     - Paginated notification retrieval with unread filters (`GET /api/v1/notifications`).
     - Real-time unread count badge endpoint (`GET /api/v1/notifications/unread-count`).
     - Single notification mark-as-read (`PATCH /api/v1/notifications/{id}/read`).
     - Bulk mark-all-read (`POST /api/v1/notifications/read-all`).
     - Cross-user isolation guarantees: Users cannot view or modify other users' notifications.

7. **Deterministic Local Closing Architecture (No Untracked Scheduler):**
   - The platform intentionally does **not** run an untracked background daemon or hidden scheduler in local development.
   - Instead, auction settlement is exposed via deterministic, idempotent REST endpoints (`POST /api/v1/auctions/close-expired` and `POST /api/v1/auctions/{id}/close`).
   - In production, these endpoints or the underlying service function (`close_all_expired_auctions`) can be triggered by standard schedulers (such as Windows Task Scheduler, systemd timer, cron, or Celery beat) without risk of race conditions or duplicate settlements.

---

## 2. Directory Layout

```
backend/
├── app/
│   ├── api/
│   │   ├── deps.py                            # OAuth2 bearer, require_active_buyer, require_seller, require_admin
│   │   └── v1/
│   │       ├── api.py                         # Master API v1 router mounting all domain endpoints
│   │       └── endpoints/
│   │           ├── auctions.py                # Auction lifecycle, CRUD, filtering, cancel & close endpoints
│   │           ├── auth.py                    # Registration, JWT login, OAuth2 form, refresh token
│   │           ├── bids.py                    # Secure bidding engine, anti-sniping, masked bid history
│   │           ├── categories.py              # Category catalog inspection
│   │           ├── health.py                  # Database connection pool diagnostics & health check
│   │           ├── notifications.py           # In-app notifications inbox, badges & read lifecycle
│   │           ├── products.py                # Product CRUD & seller inventory management
│   │           └── users.py                   # User profiles, admin governance, role promotion
│   ├── core/
│   │   ├── config.py                          # Pydantic BaseSettings, database URIs, security params
│   │   └── security.py                        # Bcrypt password hashing & JWT token issuance
│   ├── db/
│   │   ├── base.py                            # Master ORM model imports for SQLAlchemy metadata
│   │   ├── base_class.py                      # DeclarativeBase base class
│   │   └── session.py                         # QueuePool configuration (pool_size=20, max_overflow=10)
│   ├── models/                                # 10 mapped SQLAlchemy models (roles, users, products, auctions, etc.)
│   │   ├── auction.py                         # Auction model & AuctionStatus enum
│   │   ├── audit_log.py                       # AuditLog model for change tracking
│   │   ├── bid.py                             # Bid model & integrity constraints
│   │   ├── notification.py                    # Notification model & NotificationType enum
│   │   └── transaction.py                     # Transaction model & SettlementType / PaymentStatus enums
│   ├── schemas/                               # Pydantic request/response validation contracts
│   │   ├── auction.py                         # Auction schemas with formatted pricing & countdown
│   │   ├── bid.py                             # Bid placement & masked bid history schemas
│   │   ├── notification.py                    # Notification list, badge & read status schemas
│   │   └── settlement.py                      # AuctionCloseResult & BatchCloseResponse schemas
│   └── services/
│       └── auction_closing.py                 # Transactional settlement service with row locking & idempotency
├── tests/                                     # Automated test suites (80/80 passing)
│   ├── conftest.py                            # Pytest fixtures & database seed cleanup hooks
│   ├── test_auctions.py                       # 12 auction lifecycle & filtering tests
│   ├── test_auth.py                           # 23 authentication & RBAC governance tests
│   ├── test_bids.py                           # 10 bidding engine, locking, masking & anti-sniping tests
│   ├── test_closing_and_notifications.py       # 9 settlement, zero-bid, reserve & notification tests
│   ├── test_config.py                         # 4 settings & CORS parsing tests
│   ├── test_db_connection.py                  # 3 connection pool & health tests
│   ├── test_health.py                         # 4 health diagnostic & OpenAPI tests
│   ├── test_models.py                         # 5 ORM mapping & relationship tests
│   └── test_products.py                       # 10 product catalog & inventory tests
├── .env.example                               # Environment template with connection strings
└── requirements.txt                           # Production dependencies
```

---

## 3. RBAC & Bidding Permission Matrix

| Endpoint | Public / Anonymous | BUYER | SELLER | ADMIN |
|---|:---:|:---:|:---:|:---:|
| `POST /api/v1/auctions/{id}/bids` | 401 Unauthorized | **201 Created** | 403 Forbidden | 403 Forbidden |
| `GET /api/v1/auctions/{id}/bids` | 200 OK (Masked) | 200 OK (Masked) | 200 OK (Unmasked for Owner) | 200 OK (Unmasked) |
| `GET /api/v1/bids/me` | 401 Unauthorized | **200 OK** | 403 Forbidden | 403 Forbidden |
| `POST /api/v1/auctions/{id}/close` | 401 Unauthorized | 403 Forbidden | **200 OK (Owner Only)** | **200 OK (Any Auction)** |
| `POST /api/v1/auctions/close-expired` | 401 Unauthorized | 403 Forbidden | **200 OK** | **200 OK** |
| `GET /api/v1/notifications` | 401 Unauthorized | **200 OK** | **200 OK** | **200 OK** |
| `GET /api/v1/notifications/unread-count` | 401 Unauthorized | **200 OK** | **200 OK** | **200 OK** |
| `PATCH /api/v1/notifications/{id}/read` | 401 Unauthorized | **200 OK (Own Only)** | **200 OK (Own Only)** | **200 OK (Own Only)** |
| `POST /api/v1/notifications/read-all` | 401 Unauthorized | **200 OK** | **200 OK** | **200 OK** |

---

## 4. API Endpoints Specification

### 4.1 Bidding Engine Endpoints
- **`POST /api/v1/auctions/{auction_id}/bids`**
  - **Body:** `{"bid_amount": 2500.00}`
  - **Success (201 Created):** Returns placed bid metadata, `new_highest_bid`, and calculated `minimum_next_bid`.
  - **Validation Errors (400 Bad Request):**
    - Bid below starting price or minimum increment.
    - Auction expired, not started, or already closed.
    - Concurrent outbid conflict (`OUTBID_CONFLICT`).
  - **Role Rejections (403 Forbidden):** Sellers or Administrators attempting to bid; buyers attempting to bid on own listings.

- **`GET /api/v1/auctions/{auction_id}/bids`**
  - **Query Params:** `page` (default 1), `page_size` (default 20, max 100).
  - **Returns:** Chronological bid history, current winning bid, and next minimum bid. Anonymizes bidder identity (`e***r`) for public viewers.

- **`GET /api/v1/bids/me`**
  - **Returns:** Paginated bidding stream for the authenticated buyer across active and closed listings.

### 4.2 Auction Closing & Settlement Endpoints
- **`POST /api/v1/auctions/{auction_id}/close`**
  - **Query Params:** `force: bool = False` (permitted only for administrators).
  - **Permissions:** Permitted for the owning seller or an administrator.
  - **Idempotency:** Calling on an already closed auction returns its current terminal state with `already_closed: true` and 0 new notifications.
  - **Returns:**
    ```json
    {
      "auction_id": 1,
      "status": "COMPLETED",
      "already_closed": false,
      "winner_id": 8,
      "winner_username": "elena_r",
      "final_price": "2450.00",
      "reserve_price": "2000.00",
      "reserve_met": true,
      "total_bids": 14,
      "transaction_id": 19,
      "transaction_reference": "TX-DEMO-1-1791570500",
      "notifications_dispatched": 4,
      "message": "Auction successfully closed and settled with winning buyer."
    }
    ```

- **`POST /api/v1/auctions/close-expired`**
  - **Permissions:** Admin or Seller maintenance endpoint.
  - **Function:** Queries all active auctions with `end_time <= NOW()` and executes transactional settlement on each using `SELECT ... FOR UPDATE` locks.
  - **Returns:**
    ```json
    {
      "processed_count": 5,
      "completed_count": 3,
      "unsold_count": 1,
      "reserve_failed_count": 1,
      "already_closed_count": 0,
      "results": [...]
    }
    ```

### 4.3 Notification Management Endpoints
- **`GET /api/v1/notifications`**
  - **Query Params:** `page` (default 1), `page_size` (default 20), `unread_only: bool = False`.
  - **Returns:** User's in-app notification inbox with total and unread counts.
- **`GET /api/v1/notifications/unread-count`**
  - **Returns:** `{"unread_count": 3}` for navbar notification badge indicators.
- **`PATCH /api/v1/notifications/{notification_id}/read`**
  - **Returns:** Updated notification object with `is_read: true`.
- **`POST /api/v1/notifications/read-all`**
  - **Returns:** `{"message": "All notifications marked as read.", "count": 3}`.

---

## 5. Seed Accounts for Manual Testing

All seed accounts share the default password: **`password123`**

| Role | Username | Email | Purpose |
|---|---|---|---|
| **ADMIN** | `admin_sarah` | `sarah.chen@bidsmart.io` | Governance, user moderation, force closing |
| **ADMIN** | `admin_alex` | `alex.mercer@bidsmart.io` | Secondary administrator |
| **SELLER** | `vance_estates` | `marcus.vance@vanceestates.com` | High-value estate & art auctions owner |
| **SELLER** | `apex_electronics` | `contact@apexelectronics.com` | Owns Auction 1 (Apple Macintosh 128K) |
| **BUYER** | `elena_r` | `elena.rostova@gmail.com` | Active bidder (User ID: 8) |
| **BUYER** | `david_k` | `david.kumar@outlook.com` | Active bidder (User ID: 9) |
| **BUYER** | `collector_dan` | `daniel.stone@yahoo.com` | Active bidder (User ID: 10) |

---

## 6. Testing Auction Closing & Settlement Locally

Because the backend does not rely on an untracked background daemon, closing can be tested deterministically in local environments:

### Option A: Via Swagger UI (`http://localhost:8000/docs`)
1. **Trigger Single Auction Close:**
   - Log in as the listing seller (`apex_electronics`) or administrator (`admin_sarah`).
   - Expand `POST /api/v1/auctions/{auction_id}/close`.
   - Enter `auction_id` of an auction whose deadline has passed (e.g. `16`).
   - Click **Execute**: Inspect the settlement outcome (`COMPLETED`, `UNSOLD`, or `RESERVE_NOT_MET`), generated demo transaction, and notification count.
   - Click **Execute** a second time: Notice `already_closed: true` demonstrating idempotency.

2. **Trigger Batch Sweep (`POST /api/v1/auctions/close-expired`):**
   - Under `POST /api/v1/auctions/close-expired`, click **Execute**.
   - Observe the batch response summarizing how many expired auctions were processed and settled.

3. **Check In-App Notifications:**
   - Log in as buyer `elena_r`.
   - Execute `GET /api/v1/notifications/unread-count`: Observe your unread notification count badge.
   - Execute `GET /api/v1/notifications`: Read your `AUCTION_WON` or `OUTBID` notifications.
   - Execute `POST /api/v1/notifications/read-all`: Mark all notifications read.

### Option B: Via Python CLI / Script
```python
from app.db.session import SessionLocal
from app.services.auction_closing import close_all_expired_auctions

db = SessionLocal()
try:
    summary = close_all_expired_auctions(db=db, closing_user_id=1)
    print(f"Processed: {summary.processed_count} | Completed: {summary.completed_count} | Unsold: {summary.unsold_count}")
finally:
    db.close()
```

---

## 7. Production Configuration and Safe Test Commands

For Render, explicitly configure `ENVIRONMENT=production`, `DEBUG=False`, a
strong `SECRET_KEY`, the production `MYSQL_SERVER`, `MYSQL_PORT`, `MYSQL_USER`,
`MYSQL_PASSWORD`, and `MYSQL_DB`, and `BACKEND_CORS_ORIGINS` containing the
deployed Vercel origin. Configuration validation rejects debug mode, placeholder
credentials, and loopback database hosts in production. Set values through the
Render environment/secret settings; never print or commit secret values.

Payments remain restricted to Razorpay TEST MODE. Configure
`RAZORPAY_MODE=test`, `RAZORPAY_CURRENCY=USD`, `RAZORPAY_KEY_ID`,
`RAZORPAY_KEY_SECRET`, and `RAZORPAY_WEBHOOK_SECRET` in the backend secret
manager. Do not put secret values in frontend variables. Keep test mode enabled
until a complete test-mode checkout and signed-webhook flow has been manually
verified; this codebase does not enable live payment mode.

Ordinary tests use the isolated SQLite fixture. From `backend\`, these targeted
commands do not use the configured application database:

```powershell
python -m pytest -q -m "not mysql" tests\test_auctions.py tests\test_bids.py
python -m pytest -q tests\test_payment_service.py tests\test_payments_api.py
python -m pytest -q tests\test_analytics.py tests\test_transaction_payment_lifecycle.py
python -m pytest -q -m "not mysql" tests\test_closing_and_notifications.py
```

Do not run `tests\test_db_connection.py` or any `mysql`-marked concurrency test
as an ordinary test. They require a separately provisioned, disposable local
database named `bidsmart_concurrency_test`, the stored procedure
`sp_place_bid`, `BIDSMART_TEST_MYSQL_URL`, and the exact opt-in
`BIDSMART_ALLOW_MYSQL_TEST_WRITES=I_UNDERSTAND_THIS_IS_DISPOSABLE`. Review the
fixture safeguards and target identity before opting in; never use application
database settings as the test target. The legacy database verification script
is not part of the isolated test commands and must only be run against a
separately prepared disposable database.

---

## 8. Phase 8 — React Frontend Implementation

BidSmart Analytics includes a modern, high-velocity single-page application built with React, Vite, Tailwind CSS, React Router, Axios, and Recharts.

### Technology Architecture
- **Framework & Build:** React 19 + Vite
- **Styling:** Tailwind CSS v4 (`@tailwindcss/vite`) with responsive layout and accessible design tokens
- **Routing:** React Router v7 with role-gated `ProtectedRoute` guards (`BUYER`, `SELLER`, `ADMIN`)
- **HTTP Client:** Centralized Axios instance (`src/api/client.js`) with automatic JWT injection, 401 token eviction, and human-friendly error extraction
- **Data Visualization:** Recharts responsive charts (Bidding Momentum line charts, Listing Status bar charts)
- **State & Context:**
  - `AuthContext`: Centralized JWT authentication, profile caching, and role permissions
  - `NotificationContext`: In-app notification center with background REST polling
  - `WatchlistContext`: Graceful buyer bookmarking synchronized with `localStorage` (addressing backend gap)

### Live Update Polling Intervals (REST Architecture)
The frontend utilizes documented polling intervals rather than persistent WebSockets:
- **Active Auction Details & Bids:** 8-second polling interval on `/auctions/{id}` to synchronize highest bids and anti-sniping deadline extensions.
- **Notification Badge Counter:** 30-second background polling interval on `/api/v1/notifications/unread-count` to update notification badges without page reload.

### Verified Backend Integration Gaps & Graceful Fallbacks
- **Watchlist Endpoint Gap:** During the Phase 7/8 audit, it was confirmed that while the `watchlist` SQL table and SQLAlchemy model exist, no `/api/v1/watchlist` API endpoints are mounted in `api_router`.
- **Frontend Fallback:** The frontend implements `WatchlistContext` which persists starred auction IDs in client `localStorage` scoped per buyer (`bidsmart_watchlist_{userId}`) and fetches live auction details on-demand via `auctionsApi.getAuction(id)`.

### Frontend Test Suite Results (`npm test` in `frontend/`)
```
 RUN  v4.1.11 /home/user/frontend

 ✓ src/test/components.test.jsx (15 tests)
 ✓ src/test/auction.test.jsx (4 tests)
 ✓ src/test/pages.test.jsx (3 tests)
 ✓ src/test/auth.test.jsx (2 tests)

 Test Files  4 passed (4)
      Tests  24 passed (24)
   Duration  5.51s
```

### Production Build Verification (`npm run build` in `frontend/`)
```
vite v8.3.4 building client environment for production...
✓ 2574 modules transformed.
dist/index.html                   0.45 kB
dist/assets/index-BLBgrIOY.css   50.06 kB
dist/assets/index-IwMxPjj_.js   833.00 kB
✓ built in 961ms
```
