# BidSmart Analytics — Windows Setup & Developer Guide

This guide walks you through setting up, configuring, running, and testing the **BidSmart Analytics FastAPI Backend, RBAC Authentication System, Auction Catalog, and Secure Bidding Engine** on **Windows 10 / Windows 11**.

---

## 1. Prerequisites for Windows

Ensure you have the following installed on your Windows machine:
1. **Python 3.11, 3.12, or 3.13 (64-bit)**
   - Download from: [python.org/downloads/windows](https://www.python.org/downloads/windows/)
   - **Crucial:** During installation, check the box: **"Add python.exe to PATH"**.
2. **MariaDB 10.5+ or MySQL 8.0+**
   - Option A: [MariaDB MSI Installer for Windows](https://mariadb.org/download/) (Recommended)
   - Option B: [MySQL Installer for Windows](https://dev.mysql.com/downloads/installer/)
   - Option C: XAMPP / WampServer (with MySQL service enabled)
   - Option D: Windows Subsystem for Linux (WSL2) or Docker Desktop
3. **Git for Windows** (Optional but recommended)
   - Download from: [gitforwindows.org](https://gitforwindows.org/)

---

## 2. Database Initialization on Windows

Open **Command Prompt (`cmd.exe`)** or **PowerShell** as Administrator or user with MySQL access.

### Step 2.1: Connect to MySQL / MariaDB
```powershell
mysql -u root -p
```
*(Enter your root password when prompted)*

### Step 2.2: Create Database, User, and Grant Permissions
Run the following SQL commands:
```sql
CREATE DATABASE IF NOT EXISTS bidsmart_db 
  CHARACTER SET utf8mb4 
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'bidsmart_user'@'localhost' IDENTIFIED BY 'bidsmart_pass123';
CREATE USER IF NOT EXISTS 'bidsmart_user'@'127.0.0.1' IDENTIFIED BY 'bidsmart_pass123';

GRANT ALL PRIVILEGES ON bidsmart_db.* TO 'bidsmart_user'@'localhost';
GRANT ALL PRIVILEGES ON bidsmart_db.* TO 'bidsmart_user'@'127.0.0.1';
FLUSH PRIVILEGES;
EXIT;
```

### Step 2.3: Execute Schema and Seed Data
Navigate to your project root in PowerShell:
```powershell
cd C:\path\to\BidSmart

# Load Schema
mysql -u bidsmart_user -pbidsmart_pass123 bidsmart_db < database\schema.sql

# Load Seed Data
mysql -u bidsmart_user -pbidsmart_pass123 bidsmart_db < database\seed_data.sql
```

Verify that the 10 tables, views, and stored procedures are created:
```powershell
mysql -u bidsmart_user -pbidsmart_pass123 bidsmart_db -e "SHOW TABLES; SHOW PROCEDURE STATUS WHERE Db='bidsmart_db';"
```

---

## 3. Python Virtual Environment Setup on Windows

### Step 3.1: Navigate to Backend Directory
```powershell
cd C:\path\to\BidSmart\backend
```

### Step 3.2: Create Virtual Environment
```powershell
python -m venv venv
```

### Step 3.3: Activate Virtual Environment

**In PowerShell:**
```powershell
# If you receive a script execution policy error, bypass it for the current session:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

.\venv\Scripts\Activate.ps1
```

**In Command Prompt (`cmd.exe`):**
```cmd
venv\Scripts\activate.bat
```
*(Your prompt will now show `(venv)` at the beginning).*

### Step 3.4: Install Python Dependencies
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 4. Environment Variables Configuration (`.env`)

In the `backend` directory, duplicate the `.env.example` file to create your local `.env`:

**PowerShell:**
```powershell
Copy-Item .env.example .env
```

**Command Prompt:**
```cmd
copy .env.example .env
```

### Step 4.1: Generate a Secure Secret Key
Generate a strong random 256-bit hexadecimal key in PowerShell:
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```
Copy the generated string.

### Step 4.2: Edit `.env`
Open `.env` in Notepad:
```powershell
notepad .env
```
Ensure your configuration reflects your Windows environment:
```ini
PROJECT_NAME="BidSmart Analytics API"
ENVIRONMENT="development"
DEBUG=True
API_V1_STR="/api/v1"

# Paste your generated secret key here:
SECRET_KEY="your-generated-256-bit-secret-key-here"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# MySQL / MariaDB Windows Connection
MYSQL_SERVER="127.0.0.1"
MYSQL_PORT=3306
MYSQL_USER="bidsmart_user"
MYSQL_PASSWORD="bidsmart_pass123"
MYSQL_DB="bidsmart_db"

# Connection Pool Settings
MYSQL_POOL_SIZE=20
MYSQL_MAX_OVERFLOW=10
MYSQL_POOL_TIMEOUT=30
MYSQL_POOL_RECYCLE=1800

# CORS Allowed Origins
BACKEND_CORS_ORIGINS=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]
```
Save and close the file.

---

## 5. Running the Application on Windows

Start the ASGI server using Uvicorn with auto-reload:
```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 6. Accessing & Testing via Interactive Swagger UI

Open your web browser on Windows:
👉 **[http://localhost:8000/docs](http://localhost:8000/docs)**

### Interactive Bidding Workflow in Swagger UI:

1. **Check Auction Bids (Public):**
   - Expand `GET /api/v1/auctions/{auction_id}/bids`.
   - Enter `auction_id`: `1`, click **Execute**.
   - Note the `current_highest_bid` and `next_minimum_bid`.
   - Notice that bidder identities are anonymized (e.g. `e***r`).

2. **Authenticate as Buyer (`elena_r`):**
   - Click the green **Authorize** button at the top-right of Swagger UI.
   - Enter `username`: `elena_r` and `password`: `password123`.
   - Click **Authorize**, then click **Close**.

3. **Submit a New Winning Bid:**
   - Expand `POST /api/v1/auctions/{auction_id}/bids`.
   - Enter `auction_id`: `1`.
   - Enter body with an amount at or above the `next_minimum_bid`:
     ```json
     {
       "bid_amount": 2500.00
     }
     ```
   - Click **Execute**: Observe `HTTP 201 Created` with `is_winning_bid: true`.

4. **Verify Personal Bidding Stream:**
   - Expand `GET /api/v1/bids/me`, click **Execute**.
   - Observe your newly placed bid on Auction 1 in your personal portfolio.

5. **Verify Role Enforcement:**
   - Log in as `admin_sarah` / `password123` or `vance_estates` / `password123`.
   - Attempt to place a bid on `POST /api/v1/auctions/1/bids`.
   - Observe `HTTP 403 Forbidden` (`"Administrative accounts are prohibited from bidding"` or `"Sellers cannot participate in auction bidding"`).

---

## 7. Testing Endpoints from Windows PowerShell

### 1. Authenticate as Buyer and Place a Bid:
```powershell
# 1. Login as buyer
$loginBody = @{
    username_or_email = "elena_r"
    password = "password123"
} | ConvertTo-Json

$auth = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login" -Method Post -ContentType "application/json" -Body $loginBody
$headers = @{ Authorization = "Bearer " + $auth.access_token }

# 2. Check next minimum bid on Auction 1
$history = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auctions/1/bids?limit=1"
$nextMin = $history.next_minimum_bid
Write-Host "Next required minimum bid is: $" $nextMin

# 3. Submit winning bid
$bidBody = @{ bid_amount = [decimal]$nextMin + 25 } | ConvertTo-Json
$placedBid = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auctions/1/bids" -Method Post -Headers $headers -ContentType "application/json" -Body $bidBody

$placedBid | Format-List
```

### 2. Close an Auction and Settle Winner (Phase 7):
```powershell
# 1. Login as seller or admin
$adminLogin = @{
    username_or_email = "admin_sarah"
    password = "password123"
} | ConvertTo-Json

$authAdmin = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login" -Method Post -ContentType "application/json" -Body $adminLogin
$adminHeaders = @{ Authorization = "Bearer " + $authAdmin.access_token }

# 2. Sweep and close all expired auctions
$batchClose = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auctions/close-expired" -Method Post -Headers $adminHeaders
$batchClose | Format-List

# 3. Close a specific auction (idempotent)
$closeResult = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auctions/1/close" -Method Post -Headers $adminHeaders
$closeResult | Format-List
```

### 3. Check Notifications and Badges (Phase 7):
```powershell
# 1. Check unread notification badge count for Buyer Elena
$unread = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/notifications/unread-count" -Headers $headers
Write-Host "Unread Notifications:" $unread.unread_count

# 2. Fetch notification inbox
$notifs = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/notifications" -Headers $headers
$notifs.items | Format-Table id, type, title, is_read, created_at

# 3. Mark all as read
$marked = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/notifications/read-all" -Method Post -Headers $headers
Write-Host "Marked read count:" $marked.count
```

---

## 8. Running the React Frontend on Windows

The BidSmart React frontend is located in the `frontend/` directory.

### Prerequisites:
- Node.js (v18.0.0 or higher) and npm installed:
  ```powershell
  node --version
  npm --version
  ```

### Installation and Execution:
```powershell
# 1. Navigate to the frontend directory
cd frontend

# 2. Install project dependencies
npm install

# 3. (Optional) Configure environment variables
# By default, client connects to http://localhost:8000/api/v1
# To override:
$env:VITE_API_BASE_URL = "http://localhost:8000"

# 4. Start the Vite development server
npm run dev
# Vite will launch local server at http://localhost:5173

# 5. Execute frontend unit & integration test suite (Vitest)
npm test

# 6. Build optimized production bundle
npm run build
```

### Verified Quick Demo Credentials for UI Testing:
- **Buyer Account:** Username `demo_buyer` (or `elena_r`), Password `Password123` (or `password123`)
- **Seller Account:** Username `demo_seller` (or `vance_estates`), Password `Password123` (or `password123`)
- **Administrator Account:** Username `demo_admin` (or `admin_sarah`), Password `Password123` (or `password123`)

```

---

## 8. Running the Automated Test Suites on Windows

With your virtual environment activated:

```powershell
# Run the complete 82 backend tests
pytest -v

# Run the 43 database verification tests
python ..\database\test_schema.py
```

All 82 backend tests (100% passing) and 43 database verification tests will execute cleanly.
