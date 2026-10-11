# BidSmart Analytics — React Frontend Application

Production-grade Single Page Application (SPA) for the BidSmart Analytics AI-Powered Online Bidding Platform.

---

## 1. Technology Stack

- **Framework:** React 19 + Vite 8
- **Styling:** Tailwind CSS v4 (`@tailwindcss/vite`)
- **Navigation:** React Router v7
- **HTTP Client:** Centralized Axios client (`src/api/client.js`)
- **Icons:** Lucide React
- **Data Visualization:** Recharts (Bidding momentum & listing breakdown charts)
- **Testing:** Vitest + React Testing Library + JSDOM

---

## 2. Page Hierarchy & Features

| Route | Page Component | Access Level | Description & Features |
|---|---|---|---|
| `/` | `HomePage` | Public | Hero banner, live stats, ending soonest lots, popular lots, category taxonomies, security architecture pillars. |
| `/catalog` | `CatalogPage` | Public | Search keyword matching, category filter, status filter, condition filter, whitelisted sort orders, pagination. |
| `/auctions/:id` | `AuctionDetailPage` | Public / Role-aware | Product specs, high-resolution media, confidential reserve indicator (masked for unauthorized viewers), real-time countdown, `BidConsole` (atomic bidding, anti-sniping notices, BUYER validation), and `BidHistoryTable` (identity privacy masking). |
| `/login` | `LoginPage` | Public | JWT login with username or email, form validation, error handling, quick demo account fillers (`Buyer`, `Seller`, `Admin`). |
| `/register` | `RegisterPage` | Public | User registration with password complexity enforcement, role selector cards (`BUYER` vs `SELLER`; direct `ADMIN` self-assignment blocked). |
| `/dashboard/buyer` | `BuyerDashboardPage` | `BUYER`, `ADMIN` | Personal bid history, active high bids, won lots, client-synced watchlist, notifications, Recharts activity trend. |
| `/dashboard/seller` | `SellerDashboardPage` | `SELLER`, `ADMIN` | Unmasked reserve price monitoring, product cataloging modal, auction launcher modal, single lot closing, batch sweep for seller's inventory, Recharts status breakdown. |
| `/dashboard/admin` | `AdminDashboardPage` | `ADMIN` | Universal cross-seller sweep, administrative force close, auction cancellation, user RBAC role promotion and suspension, category oversight. |
| `/notifications` | `NotificationsPage` | Authenticated | In-app notification center, unread badge counters, filter by unread, mark-as-read single and mark-all-as-read, direct link navigation to auction lots. |
| `/profile` | `ProfilePage` | Authenticated | Profile contact details editing, secure password changing with current password verification, account role & status overview. |
| `*` | `NotFoundPage` | Public | 404 handler with quick navigation back to home or catalog. |

---

## 3. Real-Time REST Polling Intervals

BidSmart uses REST polling for real-time synchronization without claiming persistent WebSockets:
- **Active Auction Details & Bids:** 8-second polling interval on `/auctions/{id}` during active auctions to update current highest bid, anti-sniping extension deadlines, and bid count.
- **Notification Badges:** 30-second background polling interval on `/api/v1/notifications/unread-count` for authenticated users.

---

## 4. Backend Integration Gaps & Graceful Fallbacks

- **Watchlist Endpoint:** In Phase 7/8 audit, it was confirmed that while the `watchlist` database table and SQLAlchemy model exist, no `/api/v1/watchlist` API endpoints are currently mounted in the FastAPI router aggregator.
- **Frontend Fallback:** The frontend implements `WatchlistContext`, which stores starred auction IDs in client `localStorage` scoped per buyer (`bidsmart_watchlist_{userId}`) and fetches live auction details on-demand via `auctionsApi.getAuction(id)`.

---

## 5. Environment Configuration

The frontend connects to the FastAPI backend via Axios. By default, it targets `http://localhost:8000/api/v1`.

To customize the backend base URL, create a `.env` file in the `frontend` root:
```env
VITE_API_BASE_URL=http://localhost:8000
```

---

## 6. Running the Application

### Development Server:
```bash
cd frontend
npm install
npm run dev
```

### Production Build:
```bash
npm run build
```

### Run Vitest Test Suite:
```bash
npm test
```
All 24 test suites pass successfully.
