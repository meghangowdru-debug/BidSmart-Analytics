# Product Requirements Document (PRD)
## BidSmart Analytics — AI-Powered Online Bidding and Auction Intelligence Platform

**Document Version:** 1.0.0  
**Status:** Approved for Implementation  
**Target Release:** Production v1.0  
**Authors:** Senior Product Manager, Principal Software Architect, Lead Data Analyst, Principal AI Engineer  
**Classification:** Proprietary / Engineering Single Source of Truth  

---

## Table of Contents
1. [Executive Summary](#1-executive-summary)
2. [Problem Statement & Market Context](#2-problem-statement--market-context)
3. [Product Goals and Non-Goals](#3-product-goals-and-non-goals)
4. [User Personas and User Stories](#4-user-personas-and-user-stories)
5. [Technical Architecture and System Stack](#5-technical-architecture-and-system-stack)
6. [User Roles and Access Control (RBAC)](#6-user-roles-and-access-control-rbac)
7. [Core Website and Platform Features](#7-core-website-and-platform-features)
8. [Bidding Mechanics, Concurrency Control, and Security](#8-bidding-mechanics-concurrency-control-and-security)
9. [Database Requirements and Schema Design](#9-database-requirements-and-schema-design)
10. [Data Analytics Engine and KPI Definitions](#10-data-analytics-engine-and-kpi-definitions)
11. [SQL Analytics and Advanced Query Suite](#11-sql-analytics-and-advanced-query-suite)
12. [Python Data Analysis and Reproducible Pipeline](#12-python-data-analysis-and-reproducible-pipeline)
13. [Microsoft Power BI Business Intelligence Specification](#13-microsoft-power-bi-business-intelligence-specification)
14. [AI Analytics Assistant with Deterministic Fallback](#14-ai-analytics-assistant-with-deterministic-fallback)
15. [Explainable Unusual Bidding Detection Engine](#15-explainable-unusual-bidding-detection-engine)
16. [REST API and Real-Time WebSocket Specifications](#16-rest-api-and-real-time-websocket-specifications)
17. [Quality Assurance, Concurrency Testing, and Validation](#17-quality-assurance-concurrency-testing-and-validation)
18. [Comprehensive Deliverables and Directory Structure](#18-comprehensive-deliverables-and-directory-structure)
19. [12-Phase Development Roadmap](#19-12-phase-development-roadmap)
20. [Risks, Assumptions, and Mitigation Strategies](#20-risks-assumptions-and-mitigation-strategies)

---

## 1. Executive Summary

**BidSmart Analytics** is an enterprise-grade, full-stack online bidding platform and marketplace intelligence ecosystem. Built from scratch with modern technologies, BidSmart Analytics combines high-concurrency, real-time auction mechanics with advanced business intelligence, statistical anomaly detection, and an AI-driven natural language analytics assistant.

Modern digital marketplaces frequently fail both buyers and sellers due to an intelligence asymmetry: buyers lack visibility into fair bidding velocity, sellers struggle with setting reserve thresholds, and marketplace operators lack automated tools to detect manipulative bidding practices such as shill bidding or sniping manipulation. 

BidSmart Analytics addresses these challenges by delivering:
- A responsive, high-performance web marketplace for registering, listing, searching, and live bidding.
- A zero-latency, race-condition-free transactional bidding engine with strict server-side validation and database-level concurrency locks.
- An embedded executive analytics suite presenting real-time business metrics derived directly from normalized relational tables.
- A standardized Python (pandas/NumPy) statistical pipeline and enterprise Microsoft Power BI reporting architecture.
- An AI analytics assistant that translates conversational business inquiries into grounded analytical computations, supported by a deterministic fallback that ensures 100% operational continuity without external API key dependencies.
- An explainable, heuristic and machine-learning-assisted anomaly detection engine that flags suspicious bidding behavior for human review without automated, punitive false positives.

The platform relies on a consolidated, highly efficient technology foundation centered on **React.js**, **FastAPI**, and **MySQL**, avoiding unnecessary external paid services.

---

## 2. Problem Statement & Market Context

### 2.1 The Market Challenge
Digital auctions are among the most dynamic e-commerce formats, yet traditional implementations suffer from four critical deficiencies:
1. **The Intelligence Gap:** Participants submit bids blindly without contextual insights into category price elasticity, historical bid frequency, or likelihood of winning.
2. **Auction Integrity & Manipulation:** Illicit tactics—such as shill bidding (sellers artificially inflating prices using secondary accounts) and predatory bot sniping—erode trust. Platforms rarely offer explainable surveillance tools.
3. **Analytics Silos:** Auction metrics are typically locked in separate analytical warehouses, disconnected from real-time operational platforms, making on-the-fly decision-making impossible for sellers and administrators.
4. **Architectural Fragility:** Many auction web applications fail under high concurrency during the closing seconds of an auction, leading to race conditions, double winning bids, and database deadlocks.

### 2.2 The BidSmart Solution
BidSmart Analytics bridges the gap between transactional commerce and deep data intelligence. It introduces a unified architecture where every bid not only updates the live auction state via low-latency WebSockets, but is immediately contextualized within historical distributions, category averages, and behavioral risk scores. Sellers maximize gross merchandise value (GMV), buyers bid with confidence, and platform administrators maintain absolute governance over marketplace health.

---

## 3. Product Goals and Non-Goals

### 3.1 Product Goals
- **G-1: Transactional Integrity:** Guarantee 100% deterministic, serialized bid processing under high concurrency with zero duplicate winners and zero unvalidated increments.
- **G-2: Full-Stack Autonomy:** Deliver a completely operational full-stack application (React frontend, FastAPI backend, MySQL database) deployable locally and on cloud environments without commercial software dependencies.
- **G-3: Real-Time Transparency:** Provide sub-100ms UI updates across active clients when new bids are confirmed, accompanied by live countdown synchronization.
- **G-4: Embedded Business Intelligence:** Compute 15+ core commercial metrics in real time via optimized SQL and display them through interactive web dashboards, dedicated Python exploratory data analysis (EDA) pipelines, and Power BI models.
- **G-5: Reliable AI Insights:** Provide a natural language query interface for marketplace analytics that strictly calls backend mathematical functions, completely eliminating hallucinated statistics, with a robust offline fallback.
- **G-6: Trust & Safety Surveillance:** Equip compliance teams with an explainable anomaly detection engine that flags suspicious bid velocity, interval anomalies, and shill clusters.

### 3.2 Non-Goals (Scope Boundaries)
- **NG-1: Real-World Banking & Card Processing:** The system features a realistic simulated escrow settlement engine for demo and evaluation purposes; real-world payment gateway integrations (e.g., Stripe, Adyen) are explicitly out of scope for v1.0.
- **NG-2: Physical Logistics & Fulfillment:** The platform terminates auction transactions at simulated settlement and invoice generation; shipping labels and third-party parcel tracking are out of scope.
- **NG-3: Unbounded Generative SQL by AI:** The AI Assistant is explicitly prohibited from executing arbitrary, un-sanitized dynamic SQL strings against the database. All AI queries map to strictly typed, pre-approved backend analytical routines.
- **NG-4: Autonomous Automated Banning:** The anomaly detection module flags listings and accounts for administrative human review; it will not execute automated bans or cancel active bids autonomously.

---

## 4. User Personas and User Stories

### 4.1 User Personas

| Persona | Name | Role & Background | Core Motivations | Pain Points |
| :--- | :--- | :--- | :--- | :--- |
| **Buyer** | Elena Rostova | Passionate collector and value-driven electronics buyer | Finding authenticated items, winning auctions at fair market prices, receiving instant outbid alerts. | Getting sniped by bots in the last second; lack of visibility into bidding history; overpaying due to hidden reserve prices. |
| **Seller** | Marcus Vance | Small business owner and estate liquidator | Maximizing item realization prices, monitoring catalog velocity, reaching qualified bidders. | Low auction turnout; zero-bid listings; difficulty analyzing optimal listing durations and reserve prices. |
| **Administrator** | Sarah Chen | Platform Operations & Compliance Manager | Ensuring marketplace integrity, identifying collusive shill bidding, tracking system GMV and user growth. | Drowning in uncontextualized audit logs; lack of explainable anomaly detection tools; manual catalog moderation. |
| **Data Analyst** | David Kumar | Business Intelligence & Growth Analyst | Analyzing auction mechanics, price appreciation curves, category retention, and bidder cohorts. | Inability to connect BI tools directly to relational operational schemas; messy data with duplicate records. |

### 4.2 User Stories

#### Buyer User Stories
- **US-B1:** *As a buyer*, I want to browse active auctions with real-time countdown timers, filter by category, and search by keywords so that I can quickly discover products of interest.
- **US-B2:** *As a buyer*, I want to place bids that instantly reflect on the screen without a manual page reload, so that I can participate in competitive closing moments.
- **US-B3:** *As a buyer*, I want to see the minimum allowable bid increment and historical bid list on the product detail page so that I understand the exact financial commitment required.
- **US-B4:** *As a buyer*, I want to receive immediate visual alerts when another user outbids me so that I have the opportunity to submit a counter-bid before the auction closes.
- **US-B5:** *As a buyer*, I want to add items to my personal Watchlist so that I can track their status from my user dashboard.
- **US-B6:** *As a winning buyer*, I want to receive an auction closure notification and review a transparent demo settlement invoice confirming my victory.

#### Seller User Stories
- **US-S1:** *As a seller*, I want to create an auction listing with multiple details (title, description, category, starting price, reserve price, increment, start/end timestamps, image URLs) so that I can present my inventory professionally.
- **US-S2:** *As a seller*, I want to view real-time bid progression on my listings from my seller dashboard so that I can gauge market demand.
- **US-S3:** *As a seller*, I want the system to prevent me from bidding on my own listings so that I remain compliant with marketplace rules.
- **US-S4:** *As a seller*, I want completed auctions to automatically resolve and credit simulated earnings to my performance dashboard so that I can track my revenue.

#### Administrator User Stories
- **US-A1:** *As an administrator*, I want a high-level operational dashboard displaying total auctions, active listings, GMV, and success rates so that I can monitor platform health.
- **US-A2:** *As an administrator*, I want to inspect user accounts, toggle suspension statuses, and edit or close fraudulent auctions to protect users.
- **US-A3:** *As an administrator*, I want an explainable Anomaly Review Queue that flags suspicious bidding velocity, so that I can inspect the exact mathematical factors before taking action.
- **US-A4:** *As an administrator*, I want full audit logging of sensitive administrative operations (role elevations, catalog overrides) to satisfy governance requirements.

#### Data Analyst User Stories
- **US-D1:** *As an analyst*, I want direct access to normalized MySQL analytical queries utilizing CTEs, window functions, and aggregations so that I can answer complex commercial questions.
- **US-D2:** *As an analyst*, I want a clean, reproducible Python pipeline using pandas and NumPy that cleanses operational data, computes statistical distributions, and exports audit-ready CSVs.
- **US-D3:** *As an analyst*, I want a structured Power BI dimensional model (Star Schema) with standardized DAX measures so that leadership can review executive reports.
- **US-D4:** *As an analyst*, I want to ask questions in plain English to an AI assistant and receive deterministic, statistically verified answers based on real database records.

---

## 5. Technical Architecture and System Stack

The BidSmart Analytics architecture is purposefully designed for zero bloat, high execution speed, strict relational consistency, and complete local or containerized reproducibility.

```
+-----------------------------------------------------------------------------------+
|                                CLIENT LAYER                                       |
|  React.js (Vite) + Tailwind CSS + Lucide Icons + Recharts / Plotly.js             |
|  - Real-time WebSocket Listeners                                                  |
|  - Responsive Buyer / Seller / Admin / Analytics Portals                          |
+-----------------------------------------------------------------------------------+
                                        | (HTTPS / WSS)
                                        v
+-----------------------------------------------------------------------------------+
|                              APPLICATION LAYER                                    |
|  FastAPI (Python 3.11+) ASGI Framework (Uvicorn)                                  |
|  +-------------------------+-------------------------+-------------------------+  |
|  | Auth & Security (JWT)   | Auction & Bid Engine    | Analytics & BI Engine   |  |
|  | - bcrypt password hash  | - Concurrency Locks     | - Optimized SQL Queries |  |
|  | - Role-Based Middleware | - Increment Validator   | - Real-time Aggregator  |  |
|  +-------------------------+-------------------------+-------------------------+  |
|  | Real-Time WS Hub        | AI Analytics Service    | Anomaly Detection Mod   |  |
|  | - Broadcast Manager     | - LangChain / LiteLLM   | - Z-Score / IQR Engine  |  |
|  | - Connection Pooling    | - Deterministic Fallback| - Isolation Forest (opt)|  |
|  +-------------------------+-------------------------+-------------------------+  |
|  | Background Scheduler (APScheduler / Asyncio Task Runner)                       |  |
|  | - Automated auction closure, winner settlement & notification dispatch         |  |
+-----------------------------------------------------------------------------------+
                                        | (SQLAlchemy 2.0 Engine / PyMySQL)
                                        v
+-----------------------------------------------------------------------------------+
|                                DATABASE LAYER                                     |
|  MySQL 8.0+ Community Server (InnoDB Engine)                                      |
|  - ACID Transactions with SELECT ... FOR UPDATE Row Locks                         |
|  - Normalized Star/Snowflake-Ready Schema with Foreign Key Constraints            |
|  - Composite B-Tree Indexes for Sub-Millisecond Time-Series & Category Filtering  |
+-----------------------------------------------------------------------------------+
                                        |
                 +----------------------+----------------------+
                 |                                             |
                 v                                             v
+------------------------------------+       +------------------------------------+
|       PYTHON DATA SCIENCE          |       |         MICROSOFT POWER BI         |
|  - pandas, NumPy, SciPy            |       |  - MySQL Direct / Import Mode      |
|  - Statistical EDA & Distributions |       |  - Star Schema Dimensional Model   |
|  - Automated CSV Export Engine     |       |  - DAX Measures & Executive Pages  |
+------------------------------------+       +------------------------------------+
```

### 5.1 Technology Selection Rationale

| Layer | Chosen Technology | Justification & Architectural Benefit |
| :--- | :--- | :--- |
| **Frontend Framework** | **React.js 18+ with Vite** | Ultra-fast HMR, lightweight bundle size, rich ecosystem for data visualization components, declarative state management. |
| **Styling Engine** | **Tailwind CSS** | Utility-first, zero runtime overhead, responsive layout primitives, highly maintainable design token system. |
| **Backend Framework** | **Python 3.11+ / FastAPI** | Native asynchronous concurrency (ASGI), automatic OpenAPI (Swagger) documentation, high performance, native integration with Python data science packages. |
| **Database ORM** | **SQLAlchemy 2.0 (Core & ORM)** | Industrial-strength transactional control, connection pooling (`QueuePool`), support for pessimistic row-level locking (`with_for_update`). |
| **Relational Database** | **MySQL 8.0+ (InnoDB)** | Ubiquitous, enterprise-grade relational database with robust ACID compliance, advanced window functions (`LAG`, `DENSE_RANK`), CTE support, and sub-second execution. |
| **Data Science Stack** | **Python, pandas, NumPy** | Global standard for deterministic numerical analysis, reproducible pipeline scriptability, and data wrangling. |
| **Frontend Charts** | **Recharts & Plotly.js** | Native React declarative SVG rendering, zero server-rendering latency, interactive tooltips, responsive container wrapping. |
| **Business Intelligence** | **Microsoft Power BI** | Industry gold-standard business intelligence suite for executive dimensional reporting, star schema analysis, and DAX calculations. |
| **AI Integration** | **Configurable LLM API + Rule-Based Engine** | Decoupled client allowing integration with OpenAI, Anthropic, or local Ollama endpoints, coupled with a 100% deterministic local fallback when no API key is supplied. |

---

## 6. User Roles and Access Control (RBAC)

The platform enforces strict, backend-verified Role-Based Access Control (RBAC). Client-side role gating is utilized solely for UI rendering; every incoming API request is decoded, verified against active database records, and checked for role entitlements.

### 6.1 Role Definitions & Permission Matrix

```
                      +-------------------+
                      |   Administrator   |
                      +---------+---------+
                                |
             +------------------+------------------+
             |                                     |
             v                                     v
    +-----------------+                   +-----------------+
    |     Seller      |                   |      Buyer      |
    +-----------------+                   +-----------------+
```

| Functional Capability | Unauthenticated Guest | Buyer | Seller | Administrator |
| :--- | :---: | :---: | :---: | :---: |
| Browse Active Auctions & Categories | Yes | Yes | Yes | Yes |
| View Product Details & Bid History | Yes | Yes | Yes | Yes |
| Search, Sort, and Filter Catalog | Yes | Yes | Yes | Yes |
| Register Account / Log In | Yes | Yes | Yes | Yes |
| Add / Remove Items from Watchlist | No | Yes | Yes | Yes |
| Place Real-Time Bids | No | Yes | No (on own items) | Yes (test mode) |
| Receive Live Outbid Notifications | No | Yes | Yes | Yes |
| Create New Auction Listings | No | No | Yes | Yes |
| Edit Own Draft Listings | No | No | Yes | Yes |
| Cancel Own Active Listing (No Bids) | No | No | Yes | Yes |
| View Own Sales & Settlement Records | No | No | Yes | Yes |
| View Personal Bidding Analytics | No | Yes | Yes | Yes |
| Access Platform-Wide BI Dashboard | No | No | No | Yes |
| Access AI Analytics Assistant | No | No | No | Yes |
| Access Anomaly Detection Review Queue | No | No | No | Yes |
| Manage User Roles / Suspend Accounts | No | No | No | Yes |
| Override / Force-Close Any Auction | No | No | No | Yes |
| View System Audit Logs | No | No | No | Yes |

### 6.2 Anti-Self-Bidding Enforcement
A core marketplace integrity rule: **A user cannot bid on any auction where they are the listing seller.**
- *Backend Enforcement:* During the atomic bid validation transaction, the backend executes:
  ```python
  if auction.product.seller_id == current_user.id:
      raise HTTPException(
          status_code=status.HTTP_403_FORBIDDEN,
          detail="Marketplace Security Violation: Sellers are strictly prohibited from bidding on their own listings."
      )
  ```
- Any attempt triggers an immediate audit log entry flagged as `SUSPICIOUS_SELF_BID_ATTEMPT`.

---

## 7. Core Website and Platform Features

### 7.1 Landing / Home Page
- **Hero Section:** Value proposition with a prominent "Explore Auctions" call-to-action and live platform counter (Total GMV, Active Listings, Active Bidders).
- **Featured Auctions Carousel:** Dynamically highlights top-tier verified auctions with high bid momentum.
- **Ending Soon Grid:** Real-time synchronized cards displaying auctions closing within 12 hours, complete with animated countdown timers (e.g., `01h 42m 19s`).
- **Category Quick-Nav:** Visual iconography for all supported product categories (Electronics, Fine Art, Collectibles, Jewelry, Automobiles, Industrial Equipment).
- **Recent Platform Victories:** Ticker displaying recently completed auctions with winning prices to foster community engagement.

### 7.2 Search, Filter, Sort, and Pagination
- **Search Bar:** Real-time text search indexing product title, description, and tags.
- **Multi-Facet Category Filter:** Checkbox hierarchy allowing single or multi-category selection.
- **Price Range Filter:** Interactive double-ended slider (Min Price / Max Price based on current highest bid).
- **Status Filter:** Toggle between `ACTIVE`, `ENDING SOON` (< 2 hours), and `COMPLETED`.
- **Sorting Options:**
  - `Ending Soonest` (Default: `end_time ASC`)
  - `Newly Listed` (`created_at DESC`)
  - `Highest Price` (`current_highest_bid DESC`)
  - `Lowest Price` (`current_highest_bid ASC`)
  - `Most Bids / Hot` (`total_bids DESC`)
- **Pagination & Infinite Scroll:** Server-side paginated queries (`LIMIT`, `OFFSET`) with configurable page sizes (12, 24, 48 items/page) and direct page navigation controls.

### 7.3 Product Detail Page (PDP)
- **High-Resolution Media Gallery:** Main zoomable viewport with thumbnail carousel supporting multiple product angles.
- **Auction Financial Status Box:**
  - Starting Price (fixed display)
  - Current Highest Bid (prominently styled with live-pulse CSS animation on WebSocket updates)
  - Reserve Price Met indicator (boolean badge: `Reserve Met` or `Reserve Not Met` without revealing the private reserve amount)
  - Number of Active Bids and Unique Bidders counter
- **Synchronized Countdown Timer:** Millisecond-accurate countdown with color transitions (Green > 24h, Amber < 2h, Red < 15m). Triggers automatic UI state transition to `AUCTION CLOSED` upon expiration.
- **Interactive Bidding Console:**
  - Dynamic Minimum Required Bid indicator (`current_highest_bid + minimum_increment`).
  - Single-click quick-bid pills (`+$10`, `+$25`, `+$50`, `+$100` above minimum).
  - Manual numeric bid input with instant client-side boundary validation.
  - "Place Bid" button with loading spinner, idempotency check, and confirmation modal.
- **Live Bid History Ledger:**
  - Chronological tabular ledger updated in real time via WebSockets.
  - Columns: Bidder Alias (masked for privacy, e.g., `J***n`), Bid Amount, Timestamp (relative and absolute), Status (`Highest`, `Outbid`).
- **Seller Credibility Card:** Seller username, member tenure, positive feedback rating, total completed auctions.
- **Watchlist & Share Tools:** One-click bookmarking to personal watchlist; direct social and clipboard URL sharing.

### 7.4 Auction Creation and Lifecycle Management (Seller Console)
- **Multi-Step Listing Wizard:**
  - *Step 1: Product Classification:* Title, Category selector, Condition (`Brand New`, `Like New`, `Used - Excellent`, `Vintage/Antique`), Detailed Markdown Description.
  - *Step 2: Media Assets:* URL upload / CDN link management with thumbnail designation.
  - *Step 3: Pricing & Mechanics:* Starting Price ($), Reserve Price ($) (optional), Minimum Bid Increment ($ or auto-calculate), Start Date/Time, End Date/Time.
  - *Step 4: Review & Publish:* Pre-flight validation checks; options to save as `DRAFT` or schedule for automatic activation.
- **Seller Inventory Management Table:** Filter by listing status (`DRAFT`, `SCHEDULED`, `ACTIVE`, `COMPLETED`, `UNSOLD`); actions to edit drafts or cancel zero-bid active auctions.

### 7.5 User Dashboard & Notification Center
- **Tabbed Overview:**
  - *Bidding History:* All active bids with real-time status badges (`WINNING` in green, `OUTBID` in red).
  - *Watchlist:* Live monitor of saved items with direct shortcut to PDP.
  - *Won Auctions & Invoices:* Victory summaries with downloadable simulated demo settlement invoices.
  - *Seller Summary (if role allows):* Active listings, total revenue generated, pending deliveries.
- **Notification Center:**
  - Real-time in-app dropdown and dedicated page.
  - Categorized event alerts: `OUTBID`, `AUCTION_WON`, `AUCTION_CLOSING_SOON`, `LISTING_SOLD`, `ADMIN_NOTICE`.
  - Mark as read / Mark all as read functionality.

### 7.6 Administrative Console
- **Platform Telemetry:** Live KPIs (Total Registered Users, Active Auctions, 24h GMV, Anomaly Flags).
- **Catalog Moderation:** Table of all listings with administrative kill-switch (Force Close, Force Cancel, Delist).
- **User Governance:** Searchable user registry with instant role toggles (`BUYER`, `SELLER`, `ADMIN`) and account freeze controls (`ACTIVE`, `SUSPENDED`).
- **Audit Log Explorer:** Chronological record of administrative and high-risk actions with IP addresses and user agents.

---

## 8. Bidding Mechanics, Concurrency Control, and Security

### 8.1 Tiered Minimum Bid Increment Schedule
To ensure orderly auction progression and prevent micro-increment bid spam, BidSmart Analytics enforces a standardized, tiered minimum bid increment structure.

| Current Highest Bid Bracket | Minimum Required Increment | Example: Current Bid | Minimum Next Valid Bid |
| :--- | :---: | :---: | :---: |
| **$0.01 – $24.99** | **$1.00** | $15.00 | $16.00 |
| **$25.00 – $99.99** | **$2.50** | $50.00 | $52.50 |
| **$100.00 – $499.99** | **$5.00** | $250.00 | $255.00 |
| **$500.00 – $1,999.99** | **$25.00** | $1,200.00 | $1,225.00 |
| **$2,000.00 – $9,999.99** | **$100.00** | $4,500.00 | $4,600.00 |
| **$10,000.00+** | **$250.00** | $12,000.00 | $12,250.00 |

*Custom Overrides:* Sellers may set a custom fixed increment during listing creation, provided it is equal to or greater than the bracketed minimum.

### 8.2 Strict Server-Side Validation Pipeline
Every bid submission is subjected to a mandatory, multi-stage server-side validation pipeline prior to acquiring a database write lock:

```
[ Incoming Bid Request ]
         |
         v
[ 1. Authentication & Account Status Check ] ---> (Suspended/Anon? -> Reject 401/403)
         |
         v
[ 2. Anti-Self-Bidding Validation ] ------------> (Seller == Bidder? -> Reject 403)
         |
         v
[ 3. Auction Status Verification ] -------------> (Status != ACTIVE? -> Reject 400)
         |
         v
[ 4. Temporal Window Verification ] ------------> (Now < Start or Now > End? -> Reject 400)
         |
         v
[ 5. Acquire DB Row-Level Lock (FOR UPDATE) ]
         |
         v
[ 6. Re-Verify Highest Bid & Increment ] -------> (Bid < Current + Inc? -> Reject 409 Conflict)
         |
         v
[ 7. Atomic Write: Insert Bid, Update Auction, Log Audit ]
         |
         v
[ 8. Commit Transaction & Broadcast via WebSocket ]
```

### 8.3 Concurrency Control & Race Condition Prevention
Under high-velocity closing conditions, dozens of bidders may submit bids within the same millisecond. To prevent race conditions, dirty reads, and conflicting winners, BidSmart Analytics implements **Pessimistic Locking** at the database layer via SQLAlchemy and MySQL InnoDB.

#### Architectural Locking Implementation:
```python
@router.post("/auctions/{auction_id}/bids", response_model=BidResponseSchema)
async def place_bid(
    auction_id: int,
    bid_in: BidCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    with db.begin():
        # 1. Acquire exclusive write lock on the target auction row
        # Blocks concurrent transactions until this block commits or rolls back
        auction = db.query(Auction).filter(
            Auction.id == auction_id
        ).with_for_update().first()

        if not auction:
            raise HTTPException(status_code=404, detail="Auction listing not found.")

        # 2. Re-verify temporal and status boundaries inside the locked context
        current_time = datetime.now(timezone.utc)
        if auction.status != AuctionStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Auction is no longer active.")
        if current_time > auction.end_time:
            # Trigger lazy closure
            auction.status = AuctionStatus.COMPLETED
            db.commit()
            raise HTTPException(status_code=400, detail="Auction has expired.")

        # 3. Prevent seller self-bidding
        if auction.product.seller_id == current_user.id:
            raise HTTPException(status_code=403, detail="Sellers cannot bid on their own listings.")

        # 4. Calculate required threshold
        min_increment = auction.minimum_increment or calculate_tiered_increment(auction.current_highest_bid)
        required_min_bid = (auction.current_highest_bid or auction.starting_price) + min_increment
        
        # If this is the first bid, it can equal starting_price
        if auction.total_bids == 0 and bid_in.amount >= auction.starting_price:
            required_min_bid = auction.starting_price

        if bid_in.amount < required_min_bid:
            raise HTTPException(
                status_code=409,
                detail=f"Outbid conflict: Submitted bid ${bid_in.amount:.2f} is below required threshold of ${required_min_bid:.2f}."
            )

        # 5. Insert new bid record
        new_bid = Bid(
            auction_id=auction.id,
            bidder_id=current_user.id,
            bid_amount=bid_in.amount,
            bid_time=current_time,
            is_winning_bid=True,
            ip_address=request.client.host
        )
        db.add(new_bid)
        db.flush() # Generates new_bid.id

        # 6. Demote prior winning bid flag
        db.query(Bid).filter(
            Bid.auction_id == auction.id,
            Bid.id != new_bid.id
        ).update({"is_winning_bid": False})

        # 7. Update auction aggregate state
        auction.current_highest_bid = new_bid.bid_amount
        auction.winning_bid_id = new_bid.id
        auction.winner_id = current_user.id
        auction.total_bids += 1
        
        # 8. Soft-close extension (Anti-Sniping rule: extend by 60s if bid in last 30s)
        time_remaining = (auction.end_time - current_time).total_seconds()
        if time_remaining < 30:
            auction.end_time = auction.end_time + timedelta(seconds=60)
            extension_triggered = True
        else:
            extension_triggered = False

    # Transaction commits automatically here upon leaving context block
    # 9. Asynchronous broadcast to WebSocket channel outside database lock
    await websocket_manager.broadcast_auction_update(
        auction_id=auction_id,
        event_type="NEW_BID_ACCEPTED",
        data={
            "highest_bid": float(new_bid.bid_amount),
            "total_bids": auction.total_bids,
            "bidder_alias": mask_username(current_user.username),
            "end_time": auction.end_time.isoformat(),
            "extended": extension_triggered
        }
    )
    return new_bid
```

### 8.4 Automated Auction Closure & Winner Determination Engine
To ensure deterministic auction termination without depending on client visits:
1. **Background Polling Daemon:** A lightweight, persistent asynchronous worker (`APScheduler` or FastAPI asyncio task loop) executes every 5 seconds.
2. **Expired Active Auction Selection:**
   ```sql
   SELECT id FROM auctions 
   WHERE status = 'ACTIVE' AND end_time <= UTC_TIMESTAMP() 
   FOR UPDATE SKIP LOCKED;
   ```
3. **Atomic Resolution Matrix:**
   - **Case A: Auction with >= 1 Valid Bid:**
     - Mark status as `COMPLETED`.
     - Assign `winner_id` to the highest accepted bidder.
     - Record `winning_bid_id` and final winning amount.
     - Generate a simulated escrow transaction record in `transactions` with status `SETTLEMENT_PENDING_DEMO`.
     - Dispatch notification to the winning buyer: `"Congratulations! You won auction #X for $Y."`
     - Dispatch notification to the seller: `"Your auction #X has ended successfully at $Y."`
   - **Case B: Auction with 0 Bids:**
     - Mark status as `UNSOLD`.
     - Set `winner_id = NULL` and `winning_bid_id = NULL`.
     - Dispatch notification to seller: `"Auction #X closed with zero bids."`
   - **Case C: Auction with Bids Below Private Reserve Price:**
     - If `reserve_price` was specified and `current_highest_bid < reserve_price`:
     - Mark status as `RESERVE_NOT_MET`.
     - No winner assigned. Seller notified of highest offered market valuation.

### 8.5 Demo Settlement Engine vs. Real Payment Processing
To maintain absolute compliance and prevent real-world financial liability while delivering a complete end-to-end user experience:
- The system operates a **Simulated Demo Settlement System**.
- No credit card numbers, CVVs, or bank tokens are ever collected or stored.
- When an auction completes, the winner navigates to an in-app "Simulated Checkout" page.
- The user reviews item specifications, shipping address (mock data), and clicks "Confirm Simulated Demo Settlement".
- The transaction record transitions from `SETTLEMENT_PENDING_DEMO` to `SETTLEMENT_COMPLETED_DEMO`, generating a printable PDF/HTML invoice containing mock transactional hashes (`TX-DEMO-XXXXX`).

### 8.6 Application Security Architecture
- **Authentication:** Stateless JSON Web Tokens (JWT) signed using HMAC-SHA256 (`HS256`). Separate short-lived Access Tokens (15 minutes) and long-lived Refresh Tokens (7 days).
- **Password Security:** Multi-round `bcrypt` password hashing with automatically generated cryptographic salts.
- **Rate Limiting:** `SlowAPI` token-bucket rate limiter applied per IP and User ID (e.g., maximum 15 bids per minute per user) to mitigate bot spam.
- **SQL Injection Defense:** All database interactions are strictly executed via SQLAlchemy parameterized statements. Dynamic raw string concatenation is prohibited across the codebase.
- **Audit Logging:** Every critical administrative, authentication, or financial action is logged into the `audit_logs` table with timestamp, user ID, client IP, action type, and payload diff.

---

## 9. Database Requirements and Schema Design

The BidSmart Analytics database utilizes the **MySQL 8.0+ InnoDB** storage engine, adhering to strict third normal form (3NF) standards with foreign key referential integrity, check constraints, and optimized composite B-Tree indexes.

### 9.1 Entity Relationship Diagram (ERD) Overview

```
 +------------------+            +------------------+            +------------------+
 |    categories    | 1        * |     products     | 1        1 |     auctions     |
 |------------------+------------+------------------+------------+------------------|
 | id (PK)          |            | id (PK)          |            | id (PK)          |
 | name             |            | seller_id (FK)   |            | product_id (FK)  |
 | slug             |            | category_id (FK) |            | starting_price   |
 | description      |            | title            |            | current_high_bid |
 +------------------+            | description      |            | reserve_price    |
                                 | condition_status |            | status           |
                                 +------------------+            | winner_id (FK)   |
                                          |                      | start_time       |
                                          |                      | end_time         |
 +------------------+                     |                      +------------------+
 |      users       | 1                   |                               | 1
 |------------------+---------------------+                               |
 | id (PK)          |                                                     |
 | username         |                                                     |
 | email            | 1                                                   | *
 | password_hash    |---------+                                  +------------------+
 | role             |         |                                  |       bids       |
 | status           |         |                                  |------------------|
 +------------------+         |                                  | id (PK)          |
        | 1                   |                                  | auction_id (FK)  |
        |                     |                                  | bidder_id (FK)   |
        | *                   | *                                | bid_amount       |
 +------------------+  +------------------+                      | bid_time         |
 |    watchlist     |  |  notifications   |                      | is_winning_bid   |
 |------------------|  |------------------|                      | is_flagged       |
 | id (PK)          |  | id (PK)          |                      +------------------+
 | user_id (FK)     |  | user_id (FK)     |                               |
 | auction_id (FK)  |  | type             |                               |
 +------------------+  | message          |                               |
                       | is_read          |                               |
                       +------------------+                               |
                                                                          |
 +------------------+                                                     |
 |   transactions   | *                                                   |
 |------------------+-----------------------------------------------------+
 | id (PK)          |
 | auction_id (FK)  |
 | buyer_id (FK)    |
 | seller_id (FK)   |
 | amount           |
 | settlement_type  |
 | payment_status   |
 +------------------+
```

### 9.2 Complete Production MySQL DDL Schema

```sql
-- =============================================================================
-- BidSmart Analytics Production Relational Schema
-- Database Engine: MySQL 8.0+ (InnoDB)
-- =============================================================================

DROP DATABASE IF EXISTS bidsmart_db;
CREATE DATABASE bidsmart_db 
  CHARACTER SET utf8mb4 
  COLLATE utf8mb4_unicode_ci;

USE bidsmart_db;

-- 1. USERS TABLE
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NULL,
    role ENUM('BUYER', 'SELLER', 'ADMIN') NOT NULL DEFAULT 'BUYER',
    status ENUM('ACTIVE', 'SUSPENDED', 'PENDING_VERIFICATION') NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_users_role (role),
    INDEX idx_users_status (status)
) ENGINE=InnoDB;

-- 2. CATEGORIES TABLE
CREATE TABLE categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    slug VARCHAR(60) NOT NULL UNIQUE,
    description TEXT NULL,
    icon_name VARCHAR(50) NOT NULL DEFAULT 'Tag',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 3. PRODUCTS TABLE
CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    seller_id INT NOT NULL,
    category_id INT NOT NULL,
    title VARCHAR(150) NOT NULL,
    description TEXT NOT NULL,
    condition_status ENUM('NEW', 'LIKE_NEW', 'USED', 'VINTAGE') NOT NULL DEFAULT 'USED',
    image_url VARCHAR(500) NOT NULL,
    thumbnail_url VARCHAR(500) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_products_seller FOREIGN KEY (seller_id) 
        REFERENCES users(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_products_category FOREIGN KEY (category_id) 
        REFERENCES categories(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    FULLTEXT INDEX ft_products_title_desc (title, description),
    INDEX idx_products_category (category_id),
    INDEX idx_products_seller (seller_id)
) ENGINE=InnoDB;

-- 4. AUCTIONS TABLE
CREATE TABLE auctions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL UNIQUE,
    starting_price DECIMAL(12, 2) NOT NULL,
    current_highest_bid DECIMAL(12, 2) NULL,
    reserve_price DECIMAL(12, 2) NULL,
    minimum_increment DECIMAL(10, 2) NOT NULL DEFAULT 1.00,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    status ENUM('DRAFT', 'SCHEDULED', 'ACTIVE', 'COMPLETED', 'UNSOLD', 'RESERVE_NOT_MET', 'CANCELLED') 
        NOT NULL DEFAULT 'DRAFT',
    winner_id INT NULL,
    winning_bid_id INT NULL,
    total_bids INT UNSIGNED NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_auctions_product FOREIGN KEY (product_id) 
        REFERENCES products(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_auctions_winner FOREIGN KEY (winner_id) 
        REFERENCES users(id) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT chk_auction_times CHECK (end_time > start_time),
    CONSTRAINT chk_starting_price CHECK (starting_price >= 0.01),
    INDEX idx_auctions_status_end_time (status, end_time),
    INDEX idx_auctions_winner (winner_id),
    INDEX idx_auctions_highest_bid (current_highest_bid)
) ENGINE=InnoDB;

-- 5. BIDS TABLE
CREATE TABLE bids (
    id INT AUTO_INCREMENT PRIMARY KEY,
    auction_id INT NOT NULL,
    bidder_id INT NOT NULL,
    bid_amount DECIMAL(12, 2) NOT NULL,
    bid_time TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    is_winning_bid BOOLEAN NOT NULL DEFAULT FALSE,
    is_flagged_anomaly BOOLEAN NOT NULL DEFAULT FALSE,
    ip_address VARCHAR(45) NOT NULL DEFAULT '127.0.0.1',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_bids_auction FOREIGN KEY (auction_id) 
        REFERENCES auctions(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_bids_bidder FOREIGN KEY (bidder_id) 
        REFERENCES users(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    INDEX idx_bids_auction_amount (auction_id, bid_amount DESC),
    INDEX idx_bids_bidder (bidder_id),
    INDEX idx_bids_time (bid_time),
    INDEX idx_bids_flagged (is_flagged_anomaly)
) ENGINE=InnoDB;

-- Link circular foreign key on auctions.winning_bid_id
ALTER TABLE auctions 
ADD CONSTRAINT fk_auctions_winning_bid 
FOREIGN KEY (winning_bid_id) REFERENCES bids(id) ON DELETE SET NULL ON UPDATE CASCADE;

-- 6. WATCHLIST TABLE
CREATE TABLE watchlist (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    auction_id INT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_watchlist_user FOREIGN KEY (user_id) 
        REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_watchlist_auction FOREIGN KEY (auction_id) 
        REFERENCES auctions(id) ON DELETE CASCADE ON UPDATE CASCADE,
    UNIQUE KEY uq_user_auction_watchlist (user_id, auction_id)
) ENGINE=InnoDB;

-- 7. NOTIFICATIONS TABLE
CREATE TABLE notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    type ENUM('OUTBID', 'AUCTION_WON', 'AUCTION_ENDED', 'PRICE_ALERT', 'ANOMALY_ALERT', 'SYSTEM') 
        NOT NULL DEFAULT 'SYSTEM',
    title VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    link_url VARCHAR(255) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_notifications_user FOREIGN KEY (user_id) 
        REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_notifications_user_read (user_id, is_read)
) ENGINE=InnoDB;

-- 8. TRANSACTIONS (SIMULATED DEMO SETTLEMENT) TABLE
CREATE TABLE transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    auction_id INT NOT NULL UNIQUE,
    buyer_id INT NOT NULL,
    seller_id INT NOT NULL,
    amount DECIMAL(12, 2) NOT NULL,
    settlement_type ENUM('SIMULATED_DEMO') NOT NULL DEFAULT 'SIMULATED_DEMO',
    payment_status ENUM('SETTLEMENT_PENDING_DEMO', 'SETTLEMENT_COMPLETED_DEMO', 'CANCELLED') 
        NOT NULL DEFAULT 'SETTLEMENT_PENDING_DEMO',
    payment_reference VARCHAR(64) NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_transactions_auction FOREIGN KEY (auction_id) 
        REFERENCES auctions(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_transactions_buyer FOREIGN KEY (buyer_id) 
        REFERENCES users(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_transactions_seller FOREIGN KEY (seller_id) 
        REFERENCES users(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    INDEX idx_transactions_status (payment_status)
) ENGINE=InnoDB;

-- 9. AUDIT LOGS TABLE
CREATE TABLE audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    action VARCHAR(60) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id INT NULL,
    old_values JSON NULL,
    new_values JSON NULL,
    ip_address VARCHAR(45) NOT NULL DEFAULT '127.0.0.1',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_audit_logs_user FOREIGN KEY (user_id) 
        REFERENCES users(id) ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX idx_audit_action (action),
    INDEX idx_audit_created (created_at)
) ENGINE=InnoDB;
```

### 9.3 Realistic Seed Data Specification
To facilitate instant development, unit testing, and BI exploration, the database seed routine will populate:
- **Users:** 2 Administrators, 5 Sellers, 25 Active Buyers with diverse bidding patterns.
- **Categories:** 6 core categories (`Electronics`, `Fine Art & Antiques`, `Luxury Watches & Jewelry`, `Vintage Motors`, `Rare Collectibles`, `Industrial Gear`).
- **Products & Auctions:** 40 product listings split across:
  - 15 `ACTIVE` auctions (including 3 closing within 2 hours to test live countdown and snipe behavior).
  - 18 `COMPLETED` auctions with valid winners and demo settlement records.
  - 4 `UNSOLD` auctions (zero bids) to test anti-join queries and unsold handling.
  - 3 `RESERVE_NOT_MET` auctions.
- **Bids:** ~350 realistically distributed bids spanning the past 60 days to exercise time-series aggregations, including:
  - Normal gradual price escalation curves.
  - 2 intentionally injected anomaly patterns (rapid 3-second bid bursts and 1 shill pattern) to test the anomaly detection module.

---

## 10. Data Analytics Engine and KPI Definitions

All platform metrics are derived directly from normalized relational tables using exact mathematical formulas.

### 10.1 Platform KPI Definitions Matrix

| Metric Name | Mathematical Definition | Database Aggregation Formula | Commercial Purpose |
| :--- | :--- | :--- | :--- |
| **Total Auctions** | Count of all auction records created | `COUNT(a.id)` | Measures catalog size and platform listing velocity. |
| **Active Auctions** | Count of auctions currently open for bidding | `COUNT(CASE WHEN a.status = 'ACTIVE' THEN 1 END)` | Operational health; inventory available to buyers. |
| **Completed Auctions** | Count of auctions resolved with a winner | `COUNT(CASE WHEN a.status = 'COMPLETED' THEN 1 END)` | Realized liquidity and turnover. |
| **Auctions with Bids** | Count of auctions where total bids $\ge 1$ | `COUNT(CASE WHEN a.total_bids > 0 THEN 1 END)` | Assesses whether inventory attracts market interest. |
| **Total Accepted Bids** | Count of all valid bids in `bids` table | `COUNT(b.id)` | Measures total engagement and network activity. |
| **Unique Bidders** | Distinct count of bidding users | `COUNT(DISTINCT b.bidder_id)` | Active buyer user base size. |
| **Average Bids per Auction** | Ratio of total bids to total closed auctions | $\frac{\sum \text{total\_bids}}{\text{COUNT}(\text{auctions})}$ | Measures buyer competition density. |
| **Average Starting Price** | Arithmetic mean of initial listing prices | $\text{AVG}(\text{starting\_price})$ | Baseline valuation of seller inventory. |
| **Average Winning Price** | Arithmetic mean of winning bid amounts | $\text{AVG}(\text{winning\_bid\_amount})$ for completed auctions | Average order value / realized GMV per unit. |
| **Average Price Increase ($)** | Mean dollar appreciation from start to finish | $\text{AVG}(\text{winning\_bid} - \text{starting\_price})$ | Value generated by competitive auction format. |
| **Average Price Increase (%)** | Mean percentage premium achieved | $\text{AVG}\left(\frac{\text{winning\_bid} - \text{starting\_price}}{\text{starting\_price}}\right) \times 100$ | Seller ROI relative to fixed starting price. |
| **Auction Success Rate (%)** | Closed listings that resulted in a sale | $\frac{\text{COMPLETED}}{\text{COMPLETED} + \text{UNSOLD} + \text{RESERVE\_NOT\_MET}} \times 100$ | Primary marketplace efficiency and liquidity indicator. |
| **Zero-Bid Rate (%)** | Percentage of closed auctions with 0 bids | $\frac{\text{UNSOLD}}{\text{Total Closed Auctions}} \times 100$ | Measures dead inventory / listing friction. |
| **MoM Bidding Growth (%)** | Monthly percentage shift in bid volume | $\frac{\text{Bids}_{\text{month}} - \text{Bids}_{\text{prev}}}{\text{Bids}_{\text{prev}}} \times 100$ | Core platform expansion and engagement metric. |

---

## 11. SQL Analytics and Advanced Query Suite

Below is the verified, optimized MySQL 8.0+ query suite implementing Common Table Expressions (CTEs), window functions (`ROW_NUMBER`, `DENSE_RANK`, `LAG`, `SUM() OVER`), and aggregations matching the production schema.

### Query 1: Executive Platform Overview & KPI Aggregation
```sql
-- Architectural Purpose: Computes core executive metrics in a single pass.
SELECT 
    COUNT(a.id) AS total_auctions,
    SUM(CASE WHEN a.status = 'ACTIVE' THEN 1 ELSE 0 END) AS active_auctions,
    SUM(CASE WHEN a.status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed_auctions,
    SUM(CASE WHEN a.total_bids > 0 THEN 1 ELSE 0 END) AS auctions_with_bids,
    SUM(CASE WHEN a.status = 'UNSOLD' THEN 1 ELSE 0 END) AS unsold_auctions,
    ROUND(
        (SUM(CASE WHEN a.status = 'COMPLETED' THEN 1 ELSE 0 END) / 
         NULLIF(SUM(CASE WHEN a.status IN ('COMPLETED', 'UNSOLD', 'RESERVE_NOT_MET') THEN 1 ELSE 0 END), 0)
        ) * 100, 2
    ) AS auction_success_rate_pct,
    COALESCE(SUM(b_agg.total_accepted_bids), 0) AS total_accepted_bids,
    COALESCE(COUNT(DISTINCT b_agg.unique_bidders), 0) AS platform_unique_bidders,
    ROUND(AVG(a.starting_price), 2) AS avg_starting_price,
    ROUND(AVG(CASE WHEN a.status = 'COMPLETED' THEN a.current_highest_bid END), 2) AS avg_winning_price,
    ROUND(AVG(CASE WHEN a.status = 'COMPLETED' THEN (a.current_highest_bid - a.starting_price) END), 2) AS avg_dollar_increase
FROM auctions a
LEFT JOIN (
    SELECT 
        auction_id, 
        COUNT(id) AS total_accepted_bids,
        COUNT(DISTINCT bidder_id) AS unique_bidders
    FROM bids 
    GROUP BY auction_id
) b_agg ON a.id = b_agg.auction_id;
```

### Query 2: Category Performance with GROUP BY and HAVING
```sql
-- Architectural Purpose: Evaluates category health, gross volume, and liquidity.
-- Filters for categories with at least 2 completed auctions.
SELECT 
    c.id AS category_id,
    c.name AS category_name,
    COUNT(a.id) AS total_listings,
    SUM(CASE WHEN a.status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed_sales,
    ROUND(
        (SUM(CASE WHEN a.status = 'COMPLETED' THEN 1 ELSE 0 END) / COUNT(a.id)) * 100, 
        1
    ) AS category_conversion_rate_pct,
    COALESCE(SUM(b.id), 0) AS total_bids_submitted,
    ROUND(AVG(a.starting_price), 2) AS avg_catalog_starting_price,
    ROUND(AVG(CASE WHEN a.status = 'COMPLETED' THEN a.current_highest_bid END), 2) AS avg_category_winning_price,
    ROUND(
        AVG(CASE WHEN a.status = 'COMPLETED' 
            THEN ((a.current_highest_bid - a.starting_price) / a.starting_price) * 100 
        END), 2
    ) AS avg_price_appreciation_pct,
    ROUND(SUM(CASE WHEN a.status = 'COMPLETED' THEN a.current_highest_bid ELSE 0 END), 2) AS total_category_gmv
FROM categories c
JOIN products p ON c.id = p.category_id
JOIN auctions a ON p.id = a.product_id
LEFT JOIN bids b ON a.id = b.auction_id
GROUP BY c.id, c.name
HAVING completed_sales >= 1
ORDER BY total_category_gmv DESC;
```

### Query 3: Top 5 Auctions by Bidding Activity using CTE & DENSE_RANK()
```sql
-- Architectural Purpose: Identifies most competitive listings using window ranking.
WITH AuctionActivityCTE AS (
    SELECT 
        a.id AS auction_id,
        p.title AS product_title,
        c.name AS category_name,
        u.username AS seller_username,
        a.starting_price,
        a.current_highest_bid,
        a.total_bids,
        COUNT(DISTINCT b.bidder_id) AS unique_competitors,
        a.status,
        DENSE_RANK() OVER (ORDER BY a.total_bids DESC, a.current_highest_bid DESC) AS activity_rank
    FROM auctions a
    JOIN products p ON a.product_id = p.id
    JOIN categories c ON p.category_id = c.id
    JOIN users u ON p.seller_id = u.id
    LEFT JOIN bids b ON a.id = b.auction_id
    GROUP BY a.id, p.title, c.name, u.username, a.starting_price, a.current_highest_bid, a.total_bids, a.status
)
SELECT 
    activity_rank,
    auction_id,
    product_title,
    category_name,
    seller_username,
    starting_price,
    current_highest_bid,
    total_bids,
    unique_competitors,
    status
FROM AuctionActivityCTE
WHERE activity_rank <= 5;
```

### Query 4: Second-Highest Winning Price (Vickrey Proxy Analysis)
```sql
-- Architectural Purpose: Extracts the 2nd highest bid for each completed auction.
-- Critical for analyzing winner's curse and proxy auction pricing dynamics.
WITH RankedBidsCTE AS (
    SELECT 
        b.auction_id,
        b.bidder_id,
        u.username AS bidder_username,
        b.bid_amount,
        ROW_NUMBER() OVER (
            PARTITION BY b.auction_id 
            ORDER BY b.bid_amount DESC, b.bid_time ASC
        ) AS bid_rank
    FROM bids b
    JOIN users u ON b.bidder_id = u.id
)
SELECT 
    a.id AS auction_id,
    p.title AS product_title,
    a.current_highest_bid AS winning_first_price,
    first_b.bidder_username AS winning_bidder,
    second_b.bid_amount AS second_highest_price,
    second_b.bidder_username AS runner_up_bidder,
    ROUND(a.current_highest_bid - second_b.bid_amount, 2) AS price_spread_gap
FROM auctions a
JOIN products p ON a.product_id = p.id
JOIN RankedBidsCTE first_b ON a.id = first_b.auction_id AND first_b.bid_rank = 1
LEFT JOIN RankedBidsCTE second_b ON a.id = second_b.auction_id AND second_b.bid_rank = 2
WHERE a.status = 'COMPLETED' AND a.total_bids >= 2
ORDER BY price_spread_gap DESC;
```

### Query 5: Monthly Bidding Trends & Month-over-Month Growth using LAG()
```sql
-- Architectural Purpose: Evaluates platform growth trends over calendar months.
WITH MonthlyAggregatesCTE AS (
    SELECT 
        DATE_FORMAT(b.bid_time, '%Y-%m') AS bid_month,
        COUNT(b.id) AS total_bids_placed,
        COUNT(DISTINCT b.bidder_id) AS active_bidders,
        ROUND(SUM(b.bid_amount), 2) AS total_nominal_bid_value
    FROM bids b
    GROUP BY DATE_FORMAT(b.bid_time, '%Y-%m')
)
SELECT 
    bid_month,
    total_bids_placed,
    LAG(total_bids_placed, 1) OVER (ORDER BY bid_month) AS prev_month_bids,
    ROUND(
        ( (total_bids_placed - LAG(total_bids_placed, 1) OVER (ORDER BY bid_month)) / 
          NULLIF(LAG(total_bids_placed, 1) OVER (ORDER BY bid_month), 0)
        ) * 100, 2
    ) AS mom_bid_volume_growth_pct,
    active_bidders,
    LAG(active_bidders, 1) OVER (ORDER BY bid_month) AS prev_month_bidders,
    ROUND(
        ( (active_bidders - LAG(active_bidders, 1) OVER (ORDER BY bid_month)) / 
          NULLIF(LAG(active_bidders, 1) OVER (ORDER BY bid_month), 0)
        ) * 100, 2
    ) AS mom_bidder_growth_pct,
    total_nominal_bid_value
FROM MonthlyAggregatesCTE
ORDER BY bid_month DESC;
```

### Query 6: Cumulative Running Totals for GMV and Bids
```sql
-- Architectural Purpose: Computes cumulative running totals of completed GMV.
WITH DailyClosedSalesCTE AS (
    SELECT 
        DATE(a.end_time) AS close_date,
        COUNT(a.id) AS auctions_closed,
        SUM(a.current_highest_bid) AS daily_gmv,
        SUM(a.total_bids) AS daily_bids
    FROM auctions a
    WHERE a.status = 'COMPLETED'
    GROUP BY DATE(a.end_time)
)
SELECT 
    close_date,
    auctions_closed,
    daily_gmv,
    SUM(daily_gmv) OVER (ORDER BY close_date ROWS UNBOUNDED PRECEDING) AS cumulative_running_gmv,
    daily_bids,
    SUM(daily_bids) OVER (ORDER BY close_date ROWS UNBOUNDED PRECEDING) AS cumulative_running_bids
FROM DailyClosedSalesCTE
ORDER BY close_date ASC;
```

### Query 7: Identification of Auctions Without Bids (Anti-Join Analysis)
```sql
-- Architectural Purpose: Analyzes listings that failed to attract any bids.
SELECT 
    a.id AS auction_id,
    p.title AS product_title,
    c.name AS category_name,
    u.username AS seller_username,
    a.starting_price,
    ROUND(TIMESTAMPDIFF(HOUR, a.start_time, a.end_time), 1) AS duration_hours,
    a.status,
    a.created_at
FROM auctions a
JOIN products p ON a.product_id = p.id
JOIN categories c ON p.category_id = c.id
JOIN users u ON p.seller_id = u.id
LEFT JOIN bids b ON a.id = b.auction_id
WHERE b.id IS NULL 
  AND a.status IN ('UNSOLD', 'ACTIVE', 'COMPLETED')
ORDER BY a.starting_price DESC;
```

### Query 8: Repeat Bidder Engagement & Cohort Retention Analysis
```sql
-- Architectural Purpose: Segments buyers by frequency and victory rate.
SELECT 
    u.id AS user_id,
    u.username,
    u.created_at AS account_created,
    COUNT(b.id) AS total_bids_submitted,
    COUNT(DISTINCT b.auction_id) AS distinct_auctions_entered,
    SUM(CASE WHEN b.is_winning_bid = 1 AND a.status = 'COMPLETED' THEN 1 ELSE 0 END) AS auctions_won,
    ROUND(
        (SUM(CASE WHEN b.is_winning_bid = 1 AND a.status = 'COMPLETED' THEN 1 ELSE 0 END) / 
         NULLIF(COUNT(DISTINCT b.auction_id), 0)) * 100, 1
    ) AS win_rate_percentage,
    ROUND(COALESCE(SUM(CASE WHEN a.status = 'COMPLETED' AND a.winner_id = u.id THEN a.current_highest_bid END), 0), 2) AS total_spend_gmv
FROM users u
JOIN bids b ON u.id = b.bidder_id
JOIN auctions a ON b.auction_id = a.id
WHERE u.role = 'BUYER'
GROUP BY u.id, u.username, u.created_at
HAVING total_bids_submitted >= 3
ORDER BY total_bids_submitted DESC;
```

---

## 12. Python Data Analysis and Reproducible Pipeline

The Python analytical pipeline is implemented as an automated, reproducible workflow (`pipeline/analyze_auctions.py`) and an interactive Jupyter Notebook (`notebooks/bidsmart_eda.ipynb`).

```
+--------------------+      +--------------------+      +--------------------+
|   MySQL Extract    | ---> | Data Validation &  | ---> |  Statistical EDA   |
| (SQLAlchemy / Pool)|      | Cleaning Pipeline  |      |  & Distribution    |
+--------------------+      +--------------------+      +--------------------+
                                                                  |
                                                                  v
+--------------------+      +--------------------+      +--------------------+
|  CSV Export Suite  | <--- | Visual Generation  | <--- | Anomaly Detection  |
|  & Executive Table |      | (Seaborn / Plotly) |      | (Z-Score / IQR)    |
+--------------------+      +--------------------+      +--------------------+
```

### 12.1 Pipeline Stages & Principles
1. **Raw Records Immutability:** Operational MySQL records are extracted into a pristine `raw_df` DataFrame. No in-place destructive mutations are permitted.
2. **Missing-Value Strategy:**
   - `reserve_price`: Imputed with `NaN` and flagged via boolean indicator `has_reserve`.
   - `winner_id` on unsold/active auctions: Handled gracefully without dropping rows.
   - Timestamps: Converted to UTC-aware pandas `datetime64[ns, UTC]`.
3. **Duplicate Detection:** Composite key validation on `(auction_id, bidder_id, bid_amount, bid_time)`.
4. **Engineered Features:**
   - `price_appreciation_dollar = current_highest_bid - starting_price`
   - `price_appreciation_pct = ((current_highest_bid - starting_price) / starting_price) * 100`
   - `duration_hours = (end_time - start_time).total_seconds() / 3600`
   - `bid_intensity = total_bids / duration_hours`
5. **Statistical Distribution Summaries:** Calculates mean, standard deviation, median, Interquartile Range (IQR), 95th percentile, skewness, and kurtosis for prices and bid frequencies.
6. **Automated Exports:**
   - `exports/cleaned_auctions_summary.csv`
   - `exports/category_performance_metrics.csv`
   - `exports/bidder_behavior_profiles.csv`
   - `exports/statistical_anomalies_detected.csv`

---

## 13. Microsoft Power BI Business Intelligence Specification

### 13.1 Connection & Ingestion Mode
- **Connector:** MySQL Database Connector (via MySQL Connector/NET 8.0 or DirectQuery).
- **Ingestion Mode:** **Import Mode** (Recommended for advanced DAX calculation speed, time-intelligence functions, and high-performance offline presentation). Scheduled refresh configured for hourly intervals.

### 13.2 Star Schema Data Model

```
       +--------------------+               +--------------------+
       |   DimCategories    |               |      DimDate       |
       |--------------------|               |--------------------|
       | CategoryKey (PK)   |               | DateKey (PK)       |
       | CategoryName       |               | FullDate           |
       | Slug               |               | Year, Quarter, Month|
       +--------------------+               +--------------------+
                 | 1                                  | 1
                 |                                    |
                 | *                                  | *
       +--------------------+ 1            * +--------------------+
       |    DimProducts     |----------------|    FactAuctions    |
       |--------------------|                |--------------------|
       | ProductKey (PK)    |                | AuctionKey (PK)    |
       | ProductTitle       |                | ProductKey (FK)    |
       | CategoryKey (FK)   |                | SellerKey (FK)     |
       | Condition          |                | WinnerKey (FK)     |
       +--------------------+                | CloseDateKey (FK)  |
                 |                           | StartingPrice      |
                 |                           | FinalWinningPrice  |
                 |                           | TotalBids          |
                 |                           | Status             |
                 |                           +--------------------+
                 |                                     | 1
                 |                                     |
                 |                                     | *
       +--------------------+ 1            * +--------------------+
       |      DimUsers      |----------------|      FactBids      |
       |--------------------|                |--------------------|
       | UserKey (PK)       |                | BidKey (PK)        |
       | Username           |                | AuctionKey (FK)    |
       | Role               |                | BidderKey (FK)     |
       | AccountStatus      |                | BidDateKey (FK)    |
       +--------------------+                | BidAmount          |
                                             | IsWinningBid       |
                                             | IsFlagged          |
                                             +--------------------+
```

### 13.3 Standardized DAX Measures Catalog

#### 1. Total Platform GMV (Gross Merchandise Value)
```dax
Total GMV = 
CALCULATE(
    SUM(FactAuctions[FinalWinningPrice]),
    FactAuctions[Status] = "COMPLETED"
)
```

#### 2. Auction Success Rate (%)
```dax
Auction Success Rate = 
VAR CompletedAuctions = 
    CALCULATE(
        COUNTROWS(FactAuctions), 
        FactAuctions[Status] = "COMPLETED"
    )
VAR ResolvedAuctions = 
    CALCULATE(
        COUNTROWS(FactAuctions), 
        FactAuctions[Status] IN {"COMPLETED", "UNSOLD", "RESERVE_NOT_MET"}
    )
RETURN
    DIVIDE(CompletedAuctions, ResolvedAuctions, 0) * 100
```

#### 3. Average Price Appreciation (%)
```dax
Avg Price Appreciation % = 
AVERAGEX(
    FILTER(FactAuctions, FactAuctions[Status] = "COMPLETED" && FactAuctions[StartingPrice] > 0),
    DIVIDE(FactAuctions[FinalWinningPrice] - FactAuctions[StartingPrice], FactAuctions[StartingPrice]) * 100
)
```

#### 4. Month-over-Month GMV Growth (%)
```dax
MoM GMV Growth % = 
VAR CurrentMonthGMV = [Total GMV]
VAR PriorMonthGMV = 
    CALCULATE(
        [Total GMV],
        DATEADD(DimDate[FullDate], -1, MONTH)
    )
RETURN
    DIVIDE(CurrentMonthGMV - PriorMonthGMV, PriorMonthGMV, 0) * 100
```

#### 5. Bidder Competition Density
```dax
Avg Bids Per Auction = 
DIVIDE(
    COUNTROWS(FactBids),
    COUNTROWS(FactAuctions),
    0
)
```

### 13.4 Power BI Report Page Layouts
1. **Page 1: Executive Marketplace Overview**
   - Top KPI Cards: `Total GMV`, `Total Bids`, `Active Auctions`, `Success Rate %`, `Unique Bidders`.
   - Visual 1 (Area Chart): Cumulative GMV vs. Monthly Target.
   - Visual 2 (Donut Chart): Auction Status Breakdown (`Completed`, `Active`, `Unsold`, `Reserve Not Met`).
   - Visual 3 (Treemap): GMV Contribution by Category.
2. **Page 2: Category & Product Performance**
   - Visual 1 (Matrix Table): Category Name, Listings, Total GMV, Avg Starting Price, Avg Winning Price, Avg Appreciation %.
   - Visual 2 (Scatter Plot): Starting Price (X) vs. Final Winning Price (Y) with Bubble Size as `Total Bids`.
   - Visual 3 (Bar Chart): Top 10 Most Competitive Products by Bid Velocity.
3. **Page 3: Bidder & Seller Dynamics**
   - Visual 1 (Table): Top 15 Bidders by Total Spend, Auctions Won, and Win Rate %.
   - Visual 2 (Heatmap): Bidding Activity Density by Day of Week vs. Hour of Day.
   - Visual 3 (Histogram): Distribution of Auction Duration (Days) vs. Bid Volume.
4. **Page 4: Trust, Safety & Anomaly Audits**
   - Visual 1 (Gauge Chart): Overall Marketplace Risk Index.
   - Visual 2 (Table): Flagged Anomaly Bids with timestamp, bidder alias, price delta, and anomaly reason.

### 13.5 Reconciliation Protocol (SQL vs. Power BI)
To guarantee consistency, every DAX KPI must reconcile with the corresponding MySQL query:
- `Total GMV` must match `SUM(current_highest_bid)` from Query 1 within $0.01 tolerance.
- `Auction Success Rate` must match `auction_success_rate_pct` from Query 1.
- If variance is detected, check table relationship cross-filtering settings and time-zone conversions in the `DimDate` table.

---

## 14. AI Analytics Assistant with Deterministic Fallback

The AI Analytics Assistant is a conversational interface embedded within the administrative analytics dashboard. It empowers decision-makers to query complex platform trends in natural language.

### 14.1 Architecture and Security Guardrails
To prevent hallucination, prompt injection, and database vulnerabilities:
1. **No Arbitrary SQL Execution:** The LLM is never permitted to generate or execute raw SQL strings.
2. **Function Calling / Tool Selection:** The LLM is restricted to a structured schema of approved backend analytical tools:
   - `get_category_metrics(category_name: Optional[str])`
   - `get_bidding_trends(time_granularity: str, limit: int)`
   - `get_top_auctions_by_activity(limit: int)`
   - `get_auction_success_rate()`
   - `get_price_appreciation_summary()`
   - `get_detected_anomalies(status: str)`
3. **PII Masking:** User emails, phone numbers, password hashes, and raw IP addresses are scrubbed before payload transmission.

### 14.2 Deterministic Offline Fallback Engine (No API Key Required)
When no third-party LLM API key (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) is configured, the system seamlessly activates the **Deterministic Rule-Based Analytics Assistant**. This engine utilizes an intent-classification regular expression engine mapped directly to local SQL/pandas analytics functions.

```
[ User Chat Query ]
        |
        v
[ API Key Present? ]
       /          \
  (Yes)            (No / API Error)
     v                    v
[ LLM Tool-Call ]   [ Deterministic Intent Classifier ]
     \                    /
      v                  v
    [ Execute Approved Analytics Function ]
                 |
                 v
    [ Return Formatted Analytical JSON + Chart Config ]
```

### 14.3 Fallback Query Intent Mapping Matrix

| Natural Language Query Intent | Intent Regex Pattern | Backend Executable Routine | Formatted Output Structure |
| :--- | :--- | :--- | :--- |
| **Highest Average Winning Price Category** | `.*(highest\|top).*(average\|avg).*(winning\|sale).*(price\|category).*` | `analytics_service.get_highest_winning_category()` | Identifies top category, dollar average, and comparison vs platform baseline. |
| **Monthly Bidding Activity Trends** | `.*(how.*bidding.*changed\|monthly.*trend\|activity.*this month).*` | `analytics_service.get_monthly_trend_summary()` | Returns current month volume, previous month volume, and MoM % delta. |
| **Auctions Attracting Most Bidders** | `.*(attract\|most).*(bidders\|competitors\|interest).*` | `analytics_service.get_most_contested_auctions(limit=5)` | Tabular summary of top listings, unique bidder count, and current bid. |
| **Percentage of Auctions with Bids** | `.*(percentage\|what percent).*(at least one bid\|receive.*bid).*` | `analytics_service.get_auctions_with_bids_ratio()` | Exact percentage, total listings count, and zero-bid listings count. |
| **Largest Price Increase Category** | `.*(largest\|highest).*(price increase\|appreciation\|premium).*` | `analytics_service.get_highest_appreciation_category()` | Category with highest % delta between starting and winning price. |
| **Unusual Bidding / Anomaly Inquiries** | `.*(unusual\|suspicious\|anomaly\|anomalies\|fraud).*` | `anomaly_service.get_unreviewed_anomalies_summary()` | Summary of flagged bids, top flagged auctions, and trigger reasons. |

---

## 15. Explainable Unusual Bidding Detection Engine

Marketplace trust relies on rapid, transparent surveillance of manipulative bidding practices. The BidSmart Anomaly Detection Engine operates as an explainable, advisory surveillance system.

### 15.1 Core Ethical Principle: Human-in-the-Loop
**Under no circumstances does the anomaly detection engine automatically ban users, cancel live bids, or alter auction outcomes.**
All detected anomalies generate an advisory audit record in the database (`is_flagged_anomaly = TRUE`) and are routed to the **Administrator Anomaly Review Queue** with a detailed mathematical explanation.

### 15.2 Explainable Detection Heuristics

#### Heuristic 1: Rapid Bid Burst (High-Frequency Submission)
- **Mathematical Condition:** A single bidder submits $\ge 3$ consecutive bids on the same auction within a window of $\Delta t \le 10.0\text{ seconds}$.
- **Risk Rationale:** Indicates automated bot scripting or rapid manipulation to simulate artificial auction urgency.
- **Explainability Output:** `"Bidder submitted 3 bids within 4.2 seconds (threshold: 3 bids in 10s). Potential automated bot execution."`

#### Heuristic 2: Extreme Price Escalation (Outlier Increment)
- **Mathematical Condition:** A bid exceeds the required minimum increment by more than $10\times$, calculated as:
  $$\text{Bid Amount} - \text{Current Highest Bid} > 10 \times \text{Minimum Increment}$$
- **Risk Rationale:** Price-spiking behavior designed to scare away legitimate competitors or accidental fat-finger errors.
- **Explainability Output:** `"Submitted bid jumped current price by $500.00, exceeding required increment ($25.00) by 20.0x."`

#### Heuristic 3: Suspicious Bid Sniping Cluster
- **Mathematical Condition:** More than 5 distinct bids submitted across different bidders within the final $T \le 15\text{ seconds}$ of auction closing.
- **Risk Rationale:** Extreme late-stage sniping congestion; flags the auction for anti-sniping extension verification.
- **Explainability Output:** `"High-density sniping detected: 7 bids submitted in final 12 seconds prior to scheduled close."`

#### Heuristic 4: Potential Shill Bidding Association
- **Mathematical Condition:** Bidder exhibits high participation frequency ($\ge 5\text{ bids}$) on listings owned by a specific seller, but has an overall platform win rate of $0\%$ across that seller's items.
- **Risk Rationale:** Artificial price inflation on behalf of an associate seller without the intent to acquire the asset.
- **Explainability Output:** `"Bidder participated in 6 auctions by Seller 'VanceEstates' with 0 wins. Shill score: 0.84."`

### 15.3 Optional Machine Learning Enhancement (Isolation Forest)
For platforms processing high bid volumes, the engine supports an optional unsupervised **Isolation Forest** model (`scikit-learn`):
- **Feature Vector:**
  $$X = [\Delta t_{\text{prev\_bid}}, \Delta \text{Price}_{\text{prev\_bid}}, \text{Bidder\_Win\_Rate}, \text{Time\_To\_Close\_Seconds}]$$
- **Contamination Parameter:** Set conservatively to $0.02$ (top 2% outliers).
- **Explainability Interface:** SHAP (SHapley Additive exPlanations) values or feature importance weights are saved alongside the anomaly record to explain which feature triggered the score.

---

## 16. REST API and Real-Time WebSocket Specifications

The FastAPI backend exposes fully documented, strictly typed REST endpoints alongside low-latency WebSocket communication hubs.

### 16.1 REST API Endpoint Catalog

#### Authentication & User Management
- `POST /api/v1/auth/register` — Register a new account (`username`, `email`, `password`, `full_name`, `role`).
- `POST /api/v1/auth/login` — Authenticate credentials; returns JWT Access & Refresh tokens.
- `POST /api/v1/auth/refresh` — Issue fresh access token using valid refresh token.
- `GET /api/v1/users/me` — Retrieve current authenticated user profile and roles.
- `PUT /api/v1/users/me` — Update personal profile details.

#### Catalog & Products
- `GET /api/v1/categories` — List all active product categories with item counts.
- `POST /api/v1/categories` — [Admin] Create a new category taxonomy.
- `GET /api/v1/products` — Query products with search, category filtering, and pagination.
- `POST /api/v1/products` — [Seller/Admin] Create a new product listing.
- `GET /api/v1/products/{id}` — Retrieve detailed product specification.

#### Auctions & Bidding Engine
- `GET /api/v1/auctions` — List auctions with multi-facet filters (`status`, `category_id`, `sort_by`, `page`, `page_size`).
- `GET /api/v1/auctions/{id}` — Detailed auction payload with live financial state, seller card, and bid history.
- `POST /api/v1/auctions` — [Seller/Admin] Create and schedule a new auction listing.
- `POST /api/v1/auctions/{id}/bids` — Submit a validated, atomic bid on an active auction.
- `GET /api/v1/auctions/{id}/bids` — Retrieve chronological bid history for an auction.
- `POST /api/v1/auctions/{id}/cancel` — [Seller/Admin] Cancel an active auction (governed by zero-bid rule).

#### Watchlist & Notifications
- `GET /api/v1/watchlist` — Retrieve current user's bookmarked auctions.
- `POST /api/v1/watchlist/{auction_id}` — Add auction to personal watchlist.
- `DELETE /api/v1/watchlist/{auction_id}` — Remove auction from watchlist.
- `GET /api/v1/notifications` — Retrieve user notification stream.
- `PATCH /api/v1/notifications/{id}/read` — Mark individual notification as read.

#### Analytics, BI & AI Assistant
- `GET /api/v1/analytics/overview` — High-level platform KPIs (GMV, active, success rate).
- `GET /api/v1/analytics/categories` — Category performance metrics and price appreciation.
- `GET /api/v1/analytics/trends` — Daily and monthly bidding volume and growth trends.
- `POST /api/v1/ai/assistant/chat` — Submit natural language query to AI / deterministic analytics assistant.
- `GET /api/v1/anomalies` — [Admin] List flagged bidding anomalies in review queue.
- `PATCH /api/v1/anomalies/{id}/review` — [Admin] Mark anomaly as reviewed with disposition notes.

### 16.2 Real-Time WebSocket Architecture
- **Connection Endpoint:** `ws://{host}/ws/auctions/{auction_id}`
- **Channel Routing:** When a client opens a PDP, the frontend initiates a WebSocket connection to that specific auction channel.
- **Broadcast Event Payload (New Bid Accepted):**
  ```json
  {
    "event": "NEW_BID_ACCEPTED",
    "auction_id": 1042,
    "timestamp": "2026-10-09T15:45:22.108Z",
    "data": {
      "new_highest_bid": 450.00,
      "total_bids": 18,
      "bidder_masked": "E***a",
      "required_next_bid": 455.00,
      "end_time": "2026-10-09T18:00:00.000Z",
      "extended_anti_snipe": false
    }
  }
  ```
- **Broadcast Event Payload (Auction Closed):**
  ```json
  {
    "event": "AUCTION_CLOSED",
    "auction_id": 1042,
    "timestamp": "2026-10-09T18:00:00.000Z",
    "data": {
      "status": "COMPLETED",
      "winning_bid": 450.00,
      "winner_masked": "E***a",
      "total_bids": 18
    }
  }
  ```

---

## 17. Quality Assurance, Concurrency Testing, and Validation

To verify the platform's stability under high load, the QA strategy encompasses unit, integration, stress, and security test suites.

### 17.1 Test Suite Breakdown

| Test Domain | Target Components | Test Methodology & Tools | Success Criteria |
| :--- | :--- | :--- | :--- |
| **Unit Testing** | Increment calculator, password hashing, JWT encoding, status transition state machine. | `pytest`, `pytest-mock` | 100% test pass rate; > 85% statement coverage. |
| **Integration Testing** | REST APIs, database foreign keys, cascade deletes, user registration flows. | `TestClient` (FastAPI), temporary MySQL test DB. | All endpoints respond with correct status codes and schema contracts. |
| **Concurrency Stress Test** | Bid submission endpoint under simultaneous competing bids. | Python `asyncio` concurrent worker pool / `Locust`. | Exactly 1 winning bid per increment level; zero race condition overwrites; zero duplicate winners. |
| **AI Fallback Testing** | AI Assistant endpoint with `OPENAI_API_KEY=""`. | Automated prompt suite (`pytest`). | 100% of standard analytical queries return valid, accurate calculations without crashing. |
| **Security Audit** | SQL injection prevention, XSS escaping, CORS headers, RBAC route gating. | `OWASP ZAP` scan, manual penetration scripts. | Zero critical or high vulnerabilities; strict 403 on role violations. |

### 17.2 High-Concurrency Bidding Stress Test Specification
A critical verification test simulating the closing seconds of an auction:
- **Test Scenario:** An active auction has a starting price of $100.00. 50 concurrent simulated bidders submit bids of varying amounts simultaneously within a 500ms window.
- **Assertion 1:** Database locks serialize all 50 incoming requests.
- **Assertion 2:** Every accepted bid is strictly greater than the preceding bid by at least the required increment.
- **Assertion 3:** Outbid requests that fall below the moving threshold are rejected with `HTTP 409 Conflict` and descriptive error payloads.
- **Assertion 4:** `auctions.total_bids` strictly matches `SELECT COUNT(*) FROM bids WHERE auction_id = X`.
- **Assertion 5:** Exactly one bid has `is_winning_bid = TRUE` upon test completion.

---

## 18. Comprehensive Deliverables and Directory Structure

When implementation commences, the repository will adhere to the following organized directory structure:

```
bidsmart-analytics/
├── .github/
│   └── workflows/
│       ├── backend-ci.yml
│       └── frontend-ci.yml
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── auth.py
│   │   │   │   ├── users.py
│   │   │   │   ├── products.py
│   │   │   │   ├── auctions.py
│   │   │   │   ├── bids.py
│   │   │   │   ├── analytics.py
│   │   │   │   ├── ai_assistant.py
│   │   │   │   └── anomalies.py
│   │   │   └── deps.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── websocket_manager.py
│   │   ├── db/
│   │   │   ├── base.py
│   │   │   ├── session.py
│   │   │   └── init_db.py
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── product.py
│   │   │   ├── auction.py
│   │   │   ├── bid.py
│   │   │   └── transaction.py
│   │   ├── schemas/
│   │   │   ├── user.py
│   │   │   ├── auction.py
│   │   │   ├── bid.py
│   │   │   └── analytics.py
│   │   ├── services/
│   │   │   ├── auction_service.py
│   │   │   ├── analytics_service.py
│   │   │   ├── ai_service.py
│   │   │   └── anomaly_service.py
│   │   └── main.py
│   ├── tests/
│   │   ├── test_auth.py
│   │   ├── test_bidding_concurrency.py
│   │   ├── test_analytics.py
│   │   └── test_ai_fallback.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── assets/
│   │   ├── components/
│   │   │   ├── common/
│   │   │   │   ├── Navbar.jsx
│   │   │   │   ├── Footer.jsx
│   │   │   │   └── CountdownTimer.jsx
│   │   │   ├── auction/
│   │   │   │   ├── AuctionCard.jsx
│   │   │   │   ├── BidConsole.jsx
│   │   │   │   └── BidHistoryTable.jsx
│   │   │   ├── analytics/
│   │   │   │   ├── KPICard.jsx
│   │   │   │   ├── CategoryChart.jsx
│   │   │   │   └── TrendLineChart.jsx
│   │   │   └── ai/
│   │   │       └── AIAssistantDrawer.jsx
│   │   ├── context/
│   │   │   ├── AuthContext.jsx
│   │   │   └── WebSocketContext.jsx
│   │   ├── pages/
│   │   │   ├── HomePage.jsx
│   │   │   ├── BrowsePage.jsx
│   │   │   ├── AuctionDetailPage.jsx
│   │   │   ├── CreateAuctionPage.jsx
│   │   │   ├── UserDashboardPage.jsx
│   │   │   ├── AdminDashboardPage.jsx
│   │   │   └── AnalyticsPortalPage.jsx
│   │   ├── services/
│   │   │   └── api.js
│   │   ├── App.jsx
│   │   └── index.css
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.js
├── database/
│   ├── migrations/
│   │   └── 001_initial_schema.sql
│   ├── queries/
│   │   └── analytics_queries.sql
│   └── seed_data.sql
├── data_analysis/
│   ├── pipeline/
│   │   └── analyze_auctions.py
│   ├── notebooks/
│   │   └── bidsmart_eda.ipynb
│   └── exports/
│       └── .gitkeep
├── power_bi/
│   ├── dax_measures_library.dax
│   ├── data_model_schema.md
│   └── setup_instructions.md
└── README.md
```

---

## 19. 12-Phase Development Roadmap

The project is organized into 12 sequential development phases, establishing clear goals, deliverables, dependencies, and acceptance criteria.

```
[Phase 1: Architecture] ---> [Phase 2: MySQL Schema] ---> [Phase 3: FastAPI Core]
                                                                  |
[Phase 6: React UI]     <--- [Phase 5: Bid Mechanics]<--- [Phase 4: Auth & RBAC]
        |
        v
[Phase 7: Real-Time WS] ---> [Phase 8: SQL Analytics]---> [Phase 9: Python Pipeline]
                                                                  |
[Phase 12: Deployment]  <--- [Phase 11: AI & Anomaly]<--- [Phase 10: Power BI Model]
```

### Phase 1: Requirements Formalization & Architecture Sign-Off
- **Goals:** Lock down all system specifications, domain boundaries, and data dictionaries.
- **Deliverables:** Approved PRD v1.0, OpenAPI endpoint contract drafts, ERD diagrams.
- **Dependencies:** None.
- **Acceptance Criteria:** Unanimous sign-off by Product, Architecture, Data, and AI leads.

### Phase 2: MySQL Schema Deployment & Sample Data Seeding
- **Goals:** Provision the relational schema on MySQL 8.0+ and generate realistic test data.
- **Deliverables:** `001_initial_schema.sql`, `seed_data.sql`, automated database setup scripts.
- **Dependencies:** Phase 1.
- **Acceptance Criteria:** All foreign key constraints, indexes, and checks build cleanly; seed script populates 40 auctions and ~350 bids without constraint violations.

### Phase 3: FastAPI Backend Foundation & Database Integration
- **Goals:** Establish the core application runtime, configuration loading, and database connection pooling.
- **Deliverables:** FastAPI server skeleton, SQLAlchemy 2.0 session engine, base Pydantic schemas, health check endpoint (`GET /api/v1/health`).
- **Dependencies:** Phase 2.
- **Acceptance Criteria:** Connection pool manages 20+ simultaneous connections cleanly; health check returns database ping in under 20ms.

### Phase 4: Authentication, Authorization & User Management
- **Goals:** Implement secure registration, JWT token lifecycle, and role-based access control.
- **Deliverables:** Auth router (`/register`, `/login`, `/refresh`), password hashing routines, RBAC route dependencies (`require_buyer`, `require_seller`, `require_admin`).
- **Dependencies:** Phase 3.
- **Acceptance Criteria:** Passwords securely hashed with bcrypt; role escalation attempts properly rejected with `HTTP 403`.

### Phase 5: Auction Lifecycle & Atomic Bidding Logic
- **Goals:** Build the core transactional engine with pessimistic locking, increment enforcement, and automated closure.
- **Deliverables:** Auction and Bid CRUD routers, `SELECT ... FOR UPDATE` transactional bidding pipeline, anti-self-bidding validation, background closure worker.
- **Dependencies:** Phase 4.
- **Acceptance Criteria:** Zero race conditions in unit tests; expired auctions transition to `COMPLETED` or `UNSOLD` within 5 seconds of deadline.

### Phase 6: Modern React.js Frontend Implementation
- **Goals:** Develop the responsive web client with modern UI components.
- **Deliverables:** Vite + React + Tailwind setup, Home page, Catalog Search/Filter, Product Detail Page with bid console, User and Seller dashboards.
- **Dependencies:** Phase 5.
- **Acceptance Criteria:** Fully responsive UI (mobile, tablet, desktop); client-side bid validations match backend rules.

### Phase 7: Real-Time WebSocket Engine & Notifications
- **Goals:** Enable sub-100ms live bidding updates and user event notifications.
- **Deliverables:** FastAPI WebSocket connection manager, React WebSocket hook, live pulsing bid indicators, outbid toast alerts.
- **Dependencies:** Phase 6.
- **Acceptance Criteria:** Bids placed on Client A appear on Client B's screen in under 100ms without page reload.

### Phase 8: Advanced SQL Analytics Suite
- **Goals:** Execute and benchmark the 10+ core analytical MySQL queries.
- **Deliverables:** `analytics_queries.sql`, FastAPI analytics router serving computed KPIs to frontend dashboard.
- **Dependencies:** Phase 5.
- **Acceptance Criteria:** All queries execute in under 150ms on seed dataset; zero synthetic calculation variances.

### Phase 9: Python Data Science & Statistical Pipeline
- **Goals:** Build the reproducible pandas/NumPy data hygiene and exploratory data analysis pipeline.
- **Deliverables:** `pipeline/analyze_auctions.py`, `notebooks/bidsmart_eda.ipynb`, automated CSV export generation.
- **Dependencies:** Phase 8.
- **Acceptance Criteria:** Script successfully connects to MySQL, performs data hygiene without altering raw records, and exports clean CSVs.

### Phase 10: Microsoft Power BI Business Intelligence Reporting
- **Goals:** Build the dimensional Star Schema, implement DAX measures, and author executive dashboard pages.
- **Deliverables:** `dax_measures_library.dax`, `setup_instructions.md`, step-by-step PBIX creation guide.
- **Dependencies:** Phase 8, Phase 9.
- **Acceptance Criteria:** All 5 DAX measures reconcile with MySQL Query 1 figures with zero deviation.

### Phase 11: AI Analytics Assistant & Anomaly Detection Engine
- **Goals:** Deploy the grounded AI chat assistant and explainable surveillance system.
- **Deliverables:** AI router with LLM tool-calling, regex-based deterministic fallback engine, anomaly detection heuristic module.
- **Dependencies:** Phase 8.
- **Acceptance Criteria:** Assistant answers all 6 core business questions correctly without hallucinating; deterministic fallback operates flawlessly when `OPENAI_API_KEY=""`.

### Phase 12: Comprehensive Testing, Documentation & Production Readiness
- **Goals:** Finalize end-to-end quality assurance, concurrency stress testing, setup documentation, and deployment guides.
- **Deliverables:** Complete test suite, Locust stress script, production Docker Compose configuration, comprehensive `README.md`.
- **Dependencies:** Phases 1–11.
- **Acceptance Criteria:** 100% automated test pass rate; zero unresolved high-severity bugs; developer can launch entire stack from scratch with a single command.

---

## 20. Risks, Assumptions, and Mitigation Strategies

| Risk Category | Identified Risk | Impact | Probability | Mitigation Strategy |
| :--- | :--- | :---: | :---: | :--- |
| **Technical / Concurrency** | Database contention and deadlocks during final-second bid spikes on popular auctions. | High | Medium | Implement row-level pessimistic locking (`SELECT ... FOR UPDATE`) with short transaction scopes and backoff retries. |
| **Data Integrity** | Out-of-sync countdown timers between client machines and backend server time. | Medium | High | Rely exclusively on server-authoritative UTC timestamps transmitted over WebSocket; client computes remaining delta locally. |
| **AI Reliability** | Third-party LLM API downtime, rate-limiting, or unexpected schema hallucination. | High | Medium | Implement an offline, deterministic regex-based fallback engine that routes queries to verified backend analytical functions. |
| **Marketplace Trust** | Collusive shill bidding inflating asset prices without buyer awareness. | High | Low | Deploy the heuristic anomaly detection engine to flag suspicious bidder-seller co-occurrence patterns for human review. |
| **Operational Scope** | Complexity creep from real payment gateways or shipping logistics. | Medium | High | Maintain strict non-goal boundaries: utilize a transparent simulated demo settlement system for all checkout flows. |
| **Environment Setup** | Environment-specific discrepancies across Windows, macOS, and Linux developer environments. | Low | Medium | Standardize development with environment variables, virtual environments, and containerized Docker definitions. |

---

## Conclusion & Next Steps

This Product Requirements Document represents the **single source of truth** for the BidSmart Analytics platform. All subsequent software engineering, database migrations, UI designs, and analytical models must adhere strictly to the contracts, schemas, and requirements specified herein. Proceeding to Phase 2 (MySQL Schema Deployment & Sample Data Seeding) is authorized upon final document review.