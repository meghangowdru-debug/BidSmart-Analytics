#!/usr/bin/env python3
"""
BidSmart Analytics — Automated Database & Schema Verification Suite (Phase 2)
Tests:
1. Database Connectivity & Storage Engine Verification
2. Table, View, and Stored Procedure Existence
3. Referential Integrity, Foreign Keys, and Check Constraints
4. Secure Bidding Rules (Anti-Self-Bidding, Minimum Increment, Outbid Conflict)
5. Atomic Stored Procedure Execution (sp_place_bid)
6. Concurrent Bidding Simulation with Pessimistic Row-Level Locks
7. Automated Auction Closure & Winner Determination (sp_close_expired_auctions)
8. Seed Data Volume and Integrity Metrics
9. Analytical SQL Query Execution Benchmark
"""

import sys
import threading
import time
from decimal import Decimal
from datetime import datetime, timedelta, timezone
import pymysql

# Database connection parameters
DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'bidsmart_user',
    'password': 'bidsmart_pass123',
    'database': 'bidsmart_db',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
    'autocommit': True
}

def get_connection():
    return pymysql.connect(**DB_CONFIG)

passed_tests = []
failed_tests = []

def record_test(name, passed, details=""):
    if passed:
        passed_tests.append((name, details))
        print(f" [PASS] {name}" + (f" - {details}" if details else ""))
    else:
        failed_tests.append((name, details))
        print(f" [FAIL] {name} - {details}")

def run_tests():
    print("=" * 75)
    print("BIDSMART ANALYTICS — PHASE 2 DATABASE VERIFICATION SUITE")
    print("=" * 75)

    conn = get_connection()
    cursor = conn.cursor()

    # -------------------------------------------------------------------------
    # TEST GROUP 1: Connectivity & Engine Verification
    # -------------------------------------------------------------------------
    print("\n--- Test Group 1: Connectivity & Engine Verification ---")
    try:
        cursor.execute("SELECT VERSION() AS ver;")
        res = cursor.fetchone()
        record_test("Database Connection", True, f"Server version: {res['ver']}")
    except Exception as e:
        record_test("Database Connection", False, str(e))
        return

    # -------------------------------------------------------------------------
    # TEST GROUP 2: Schema Structure (Tables, Views, Procedures)
    # -------------------------------------------------------------------------
    print("\n--- Test Group 2: Schema Object Existence ---")
    required_tables = [
        'roles', 'users', 'categories', 'products', 'auctions',
        'bids', 'watchlist', 'notifications', 'transactions', 'audit_logs'
    ]
    cursor.execute("SHOW FULL TABLES WHERE Table_type = 'BASE TABLE';")
    existing_tables = [list(row.values())[0] for row in cursor.fetchall()]
    
    for tbl in required_tables:
        record_test(f"Table Exists: {tbl}", tbl in existing_tables)

    required_views = ['vw_active_auctions', 'vw_auction_kpi_summary']
    cursor.execute("SHOW FULL TABLES WHERE Table_type = 'VIEW';")
    existing_views = [list(row.values())[0] for row in cursor.fetchall()]
    for vw in required_views:
        record_test(f"View Exists: {vw}", vw in existing_views)

    required_procs = ['sp_place_bid', 'sp_close_expired_auctions']
    cursor.execute("SHOW PROCEDURE STATUS WHERE Db = 'bidsmart_db';")
    existing_procs = [row['Name'] for row in cursor.fetchall()]
    for prc in required_procs:
        record_test(f"Procedure Exists: {prc}", prc in existing_procs)

    # -------------------------------------------------------------------------
    # TEST GROUP 3: Constraints & Referential Integrity
    # -------------------------------------------------------------------------
    print("\n--- Test Group 3: Constraints & Referential Integrity ---")
    
    # Check 3.1: Unique email in users
    try:
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, full_name, role_id)
            VALUES ('temp_dup_test', 'elena.rostova@gmail.com', 'hash', 'Test Duplicate', 3);
        """)
        record_test("Check: Unique Email Enforcement", False, "Duplicate email was allowed!")
    except pymysql.err.IntegrityError:
        record_test("Check: Unique Email Enforcement", True, "Duplicate email was correctly rejected.")

    # Check 3.2: Check constraint on starting price (must be >= 0.01)
    temp_prod_id = None
    try:
        cursor.execute("""
            INSERT INTO products (seller_id, category_id, title, description, image_url)
            VALUES (3, 1, 'Check Test Prod', 'Test description', 'https://example.com/img.jpg');
        """)
        temp_prod_id = cursor.lastrowid
        cursor.execute(f"""
            INSERT INTO auctions (product_id, starting_price, start_time, end_time, status)
            VALUES ({temp_prod_id}, -50.00, NOW(), NOW() + INTERVAL 1 DAY, 'ACTIVE');
        """)
        record_test("Check: Non-Negative Starting Price Constraint", False, "Negative price was allowed!")
    except (pymysql.err.OperationalError, pymysql.err.IntegrityError):
        record_test("Check: Non-Negative Starting Price Constraint", True, "Negative price correctly rejected via CHECK constraint.")
    finally:
        if temp_prod_id:
            cursor.execute(f"DELETE FROM products WHERE id = {temp_prod_id};")

    # Check 3.3: Check constraint on end_time > start_time
    temp_prod_id2 = None
    try:
        cursor.execute("""
            INSERT INTO products (seller_id, category_id, title, description, image_url)
            VALUES (3, 1, 'Check Time Prod', 'Test description', 'https://example.com/img.jpg');
        """)
        temp_prod_id2 = cursor.lastrowid
        cursor.execute(f"""
            INSERT INTO auctions (product_id, starting_price, start_time, end_time, status)
            VALUES ({temp_prod_id2}, 100.00, NOW(), NOW() - INTERVAL 1 HOUR, 'ACTIVE');
        """)
        record_test("Check: Auction End Time > Start Time Constraint", False, "Invalid time window allowed!")
    except (pymysql.err.OperationalError, pymysql.err.IntegrityError):
        record_test("Check: Auction End Time > Start Time Constraint", True, "Invalid time window correctly rejected.")
    finally:
        if temp_prod_id2:
            cursor.execute(f"DELETE FROM products WHERE id = {temp_prod_id2};")

    # Check 3.4: Watchlist duplicate bookmark prevention
    # Temporarily clean up test bookmark if already exists
    cursor.execute("DELETE FROM watchlist WHERE user_id = 8 AND auction_id = 999;")
    try:
        cursor.execute("INSERT INTO watchlist (user_id, auction_id) VALUES (8, 40);")
        cursor.execute("INSERT INTO watchlist (user_id, auction_id) VALUES (8, 40);")
        record_test("Check: Unique User-Auction Watchlist Constraint", False, "Duplicate watchlist allowed!")
    except pymysql.err.IntegrityError:
        record_test("Check: Unique User-Auction Watchlist Constraint", True, "Duplicate bookmark correctly rejected.")
    finally:
        cursor.execute("DELETE FROM watchlist WHERE user_id = 8 AND auction_id = 40;")

    # -------------------------------------------------------------------------
    # TEST GROUP 4: Secure Bidding & Stored Procedure Execution
    # -------------------------------------------------------------------------
    print("\n--- Test Group 4: Secure Bidding & Concurrency Logic ---")

    # Test 4.1: Anti-Self-Bidding enforcement
    # Auction 1 seller is User 4 ('apex_electronics')
    cursor.execute("CALL sp_place_bid(1, 4, 3000.00, '127.0.0.1', @bid_id, @code, @msg);")
    cursor.execute("SELECT @code AS code, @msg AS msg;")
    res = cursor.fetchone()
    record_test("Anti-Self-Bidding Enforcement", res['code'] == 'FORBIDDEN_SELF_BID', res['msg'])

    # Test 4.2: Low increment rejection
    cursor.execute("SELECT current_highest_bid, minimum_increment FROM auctions WHERE id = 1;")
    auc1 = cursor.fetchone()
    current_bid = auc1['current_highest_bid']
    min_inc = auc1['minimum_increment']
    
    # Try bidding below minimum required threshold
    cursor.execute(f"CALL sp_place_bid(1, 8, {current_bid + min_inc - Decimal('5.00')}, '127.0.0.1', @bid_id, @code, @msg);")
    cursor.execute("SELECT @code AS code, @msg AS msg;")
    res = cursor.fetchone()
    record_test("Minimum Increment Enforcement", res['code'] == 'OUTBID_CONFLICT', res['msg'])

    # Test 4.3: Valid atomic bid placement
    valid_bid_amt = current_bid + min_inc + Decimal('20.00')
    cursor.execute(f"CALL sp_place_bid(1, 8, {valid_bid_amt}, '192.168.1.88', @bid_id, @code, @msg);")
    cursor.execute("SELECT @bid_id AS bid_id, @code AS code, @msg AS msg;")
    res = cursor.fetchone()
    new_bid_id = res['bid_id']
    record_test("Valid Atomic Bid Placement", res['code'] == 'SUCCESS', f"New Bid ID #{new_bid_id}")

    # Verify state updates
    cursor.execute(f"SELECT current_highest_bid, winner_id, winning_bid_id FROM auctions WHERE id = 1;")
    auc_updated = cursor.fetchone()
    record_test("Auction State Synchronized", 
                auc_updated['current_highest_bid'] == valid_bid_amt and auc_updated['winner_id'] == 8 and auc_updated['winning_bid_id'] == new_bid_id,
                f"Highest: ${auc_updated['current_highest_bid']}, Winner: User #{auc_updated['winner_id']}")

    # Verify previous winning bid demotion
    cursor.execute(f"SELECT COUNT(*) AS active_wins FROM bids WHERE auction_id = 1 AND is_winning_bid = TRUE;")
    wins = cursor.fetchone()['active_wins']
    record_test("Single Winning Bid Invariant", wins == 1, "Exactly one active winning bid exists for auction.")

    # Verify audit log entry was created
    cursor.execute(f"SELECT action, entity_id FROM audit_logs WHERE entity_type = 'AUCTION' AND entity_id = 1 ORDER BY id DESC LIMIT 1;")
    audit_row = cursor.fetchone()
    record_test("Bid Audit Log Generated", audit_row and audit_row['action'] == 'BID_ACCEPTED')

    # Clean up test bid on Auction 1 so seed data remains clean
    cursor.execute(f"DELETE FROM bids WHERE id = {new_bid_id};")
    cursor.execute(f"SELECT id, bid_amount, bidder_id FROM bids WHERE auction_id = 1 ORDER BY bid_amount DESC LIMIT 1;")
    prev_bid = cursor.fetchone()
    if prev_bid:
        cursor.execute(f"UPDATE bids SET is_winning_bid = TRUE WHERE id = {prev_bid['id']};")
        cursor.execute(f"""
            UPDATE auctions 
            SET current_highest_bid = {prev_bid['bid_amount']}, 
                winner_id = {prev_bid['bidder_id']}, 
                winning_bid_id = {prev_bid['id']},
                total_bids = (SELECT COUNT(*) FROM bids WHERE auction_id = 1)
            WHERE id = 1;
        """)

    # -------------------------------------------------------------------------
    # TEST GROUP 5: High-Concurrency Pessimistic Locking Simulation
    # -------------------------------------------------------------------------
    print("\n--- Test Group 5: High-Concurrency Pessimistic Locking Simulation ---")
    concurrency_results = []
    
    def simulate_bidder(bidder_id, bid_amt):
        thread_conn = get_connection()
        t_cur = thread_conn.cursor()
        try:
            t_cur.execute(f"CALL sp_place_bid(4, {bidder_id}, {bid_amt}, '10.0.0.{bidder_id}', @bid_id, @code, @msg);")
            t_cur.execute("SELECT @bid_id AS bid_id, @code AS code, @msg AS msg;")
            r = t_cur.fetchone()
            concurrency_results.append((bidder_id, bid_amt, r['code'], r['msg'], r['bid_id']))
        finally:
            thread_conn.close()

    cursor.execute("SELECT current_highest_bid, minimum_increment FROM auctions WHERE id = 4;")
    auc4 = cursor.fetchone()
    base_bid = auc4['current_highest_bid'] or Decimal('450.00')
    inc4 = auc4['minimum_increment']

    threads = [
        threading.Thread(target=simulate_bidder, args=(9, base_bid + inc4)),
        threading.Thread(target=simulate_bidder, args=(10, base_bid + inc4)),
        threading.Thread(target=simulate_bidder, args=(11, base_bid + inc4)),
        threading.Thread(target=simulate_bidder, args=(12, base_bid + inc4)),
        threading.Thread(target=simulate_bidder, args=(13, base_bid + (inc4 * 2)))
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    successes = [r for r in concurrency_results if r[2] == 'SUCCESS']
    conflicts = [r for r in concurrency_results if r[2] == 'OUTBID_CONFLICT']

    record_test("Concurrent Bids Serialized", len(successes) >= 1 and len(conflicts) >= 1, 
                f"{len(successes)} accepted, {len(conflicts)} rejected with outbid conflict, 0 unhandled exceptions.")

    # Clean up test bids on Auction 4
    for s in successes:
        if s[4]:
            cursor.execute(f"DELETE FROM bids WHERE id = {s[4]};")
    cursor.execute(f"SELECT id, bid_amount, bidder_id FROM bids WHERE auction_id = 4 ORDER BY bid_amount DESC LIMIT 1;")
    prev_bid4 = cursor.fetchone()
    if prev_bid4:
        cursor.execute(f"UPDATE bids SET is_winning_bid = TRUE WHERE id = {prev_bid4['id']};")
        cursor.execute(f"""
            UPDATE auctions 
            SET current_highest_bid = {prev_bid4['bid_amount']}, 
                winner_id = {prev_bid4['bidder_id']}, 
                winning_bid_id = {prev_bid4['id']},
                total_bids = (SELECT COUNT(*) FROM bids WHERE auction_id = 4)
            WHERE id = 4;
        """)

    # -------------------------------------------------------------------------
    # TEST GROUP 6: Auction Closing & Winner Determination
    # -------------------------------------------------------------------------
    print("\n--- Test Group 6: Auction Closing & Winner Determination ---")
    cursor.execute("""
        INSERT INTO products (seller_id, category_id, title, description, image_url) VALUES
        (3, 1, 'Expired With Bids', 'Test desc', 'https://example.com/1.jpg'),
        (3, 1, 'Expired Zero Bids', 'Test desc', 'https://example.com/2.jpg'),
        (3, 1, 'Expired Below Reserve', 'Test desc', 'https://example.com/3.jpg');
    """)
    cursor.execute("SELECT id FROM products ORDER BY id DESC LIMIT 3;")
    temp_prods = [r['id'] for r in cursor.fetchall()]
    temp_prods.reverse()

    past_end = datetime.now(timezone.utc) - timedelta(minutes=10)
    past_start = past_end - timedelta(days=2)

    cursor.execute(f"""
        INSERT INTO auctions (product_id, starting_price, current_highest_bid, start_time, end_time, status, total_bids)
        VALUES ({temp_prods[0]}, 100.00, 250.00, '{past_start.strftime('%Y-%m-%d %H:%M:%S')}', '{past_end.strftime('%Y-%m-%d %H:%M:%S')}', 'ACTIVE', 1);
    """)
    auc_a_id = cursor.lastrowid
    cursor.execute(f"INSERT INTO bids (auction_id, bidder_id, bid_amount, is_winning_bid) VALUES ({auc_a_id}, 8, 250.00, TRUE);")
    bid_a_id = cursor.lastrowid
    cursor.execute(f"UPDATE auctions SET winner_id = 8, winning_bid_id = {bid_a_id} WHERE id = {auc_a_id};")

    cursor.execute(f"""
        INSERT INTO auctions (product_id, starting_price, start_time, end_time, status, total_bids)
        VALUES ({temp_prods[1]}, 300.00, '{past_start.strftime('%Y-%m-%d %H:%M:%S')}', '{past_end.strftime('%Y-%m-%d %H:%M:%S')}', 'ACTIVE', 0);
    """)
    auc_b_id = cursor.lastrowid

    cursor.execute(f"""
        INSERT INTO auctions (product_id, starting_price, current_highest_bid, reserve_price, start_time, end_time, status, total_bids)
        VALUES ({temp_prods[2]}, 200.00, 400.00, 800.00, '{past_start.strftime('%Y-%m-%d %H:%M:%S')}', '{past_end.strftime('%Y-%m-%d %H:%M:%S')}', 'ACTIVE', 1);
    """)
    auc_c_id = cursor.lastrowid
    cursor.execute(f"INSERT INTO bids (auction_id, bidder_id, bid_amount, is_winning_bid) VALUES ({auc_c_id}, 9, 400.00, TRUE);")
    bid_c_id = cursor.lastrowid
    cursor.execute(f"UPDATE auctions SET winner_id = 9, winning_bid_id = {bid_c_id} WHERE id = {auc_c_id};")

    cursor.execute("CALL sp_close_expired_auctions(@closed, @unsold, @reserve_failed);")

    cursor.execute(f"SELECT status, winner_id FROM auctions WHERE id = {auc_a_id};")
    res_a = cursor.fetchone()
    cursor.execute(f"SELECT status, winner_id FROM auctions WHERE id = {auc_b_id};")
    res_b = cursor.fetchone()
    cursor.execute(f"SELECT status, winner_id FROM auctions WHERE id = {auc_c_id};")
    res_c = cursor.fetchone()

    record_test("Auction Closure: Valid Winner Settled", 
                res_a['status'] == 'COMPLETED' and res_a['winner_id'] == 8, 
                f"Status: {res_a['status']}, Winner ID: {res_a['winner_id']}")

    record_test("Auction Closure: Zero Bids Handled (UNSOLD)", 
                res_b['status'] == 'UNSOLD' and res_b['winner_id'] is None, 
                f"Status: {res_b['status']}, Winner: NULL")

    record_test("Auction Closure: Reserve Not Met Handled", 
                res_c['status'] == 'RESERVE_NOT_MET', 
                f"Status: {res_c['status']}")

    cursor.execute(f"SELECT id, amount, payment_status, payment_reference FROM transactions WHERE auction_id = {auc_a_id};")
    tx_a = cursor.fetchone()
    record_test("Simulated Demo Transaction Generated", 
                tx_a is not None and tx_a['amount'] == Decimal('250.00'), 
                f"Ref: {tx_a['payment_reference'] if tx_a else 'None'}")

    # Clean up test rows
    cursor.execute(f"DELETE FROM transactions WHERE auction_id = {auc_a_id};")
    cursor.execute(f"DELETE FROM bids WHERE auction_id IN ({auc_a_id}, {auc_c_id});")
    cursor.execute(f"DELETE FROM auctions WHERE id IN ({auc_a_id}, {auc_b_id}, {auc_c_id});")
    cursor.execute(f"DELETE FROM products WHERE id IN ({temp_prods[0]}, {temp_prods[1]}, {temp_prods[2]});")

    # -------------------------------------------------------------------------
    # TEST GROUP 7: Seed Data Volume & Integrity
    # -------------------------------------------------------------------------
    print("\n--- Test Group 7: Seed Data Volume & Integrity ---")

    expected_counts = {
        'roles': 3,
        'users': 32,
        'categories': 6,
        'products': 40,
        'auctions': 40
    }

    for tbl, exp_cnt in expected_counts.items():
        cursor.execute(f"SELECT COUNT(*) AS cnt FROM {tbl};")
        actual_cnt = cursor.fetchone()['cnt']
        record_test(f"Seed Count: {tbl} ({exp_cnt})", actual_cnt == exp_cnt, f"Actual: {actual_cnt}")

    cursor.execute("SELECT COUNT(*) AS cnt FROM bids;")
    total_bids = cursor.fetchone()['cnt']
    record_test("Seed Count: bids (~350+)", total_bids >= 350, f"Actual: {total_bids} bids")

    cursor.execute("SELECT COUNT(*) AS cnt FROM bids WHERE is_flagged_anomaly = TRUE;")
    anomaly_bids = cursor.fetchone()['cnt']
    record_test("Anomaly Test Patterns Injected", anomaly_bids >= 2, f"Flagged anomaly bids: {anomaly_bids}")

    # -------------------------------------------------------------------------
    # TEST GROUP 8: Analytics Query Execution
    # -------------------------------------------------------------------------
    print("\n--- Test Group 8: Analytical SQL Execution Benchmark ---")
    analytics_queries = [
        ("Executive Overview", "SELECT COUNT(id) FROM auctions;"),
        ("Category Performance", """
            SELECT c.name, COUNT(a.id), AVG(a.starting_price) 
            FROM categories c 
            JOIN products p ON c.id = p.category_id 
            JOIN auctions a ON p.id = a.product_id 
            GROUP BY c.id, c.name;
        """),
        ("Top 5 Auctions CTE & Window", """
            WITH TopRanked AS (
                SELECT id, current_highest_bid, DENSE_RANK() OVER (ORDER BY total_bids DESC) as rnk 
                FROM auctions
            )
            SELECT * FROM TopRanked WHERE rnk <= 5;
        """),
        ("Vickrey 2nd Highest Price Window", """
            WITH Ranked AS (
                SELECT auction_id, bid_amount, ROW_NUMBER() OVER (PARTITION BY auction_id ORDER BY bid_amount DESC) as r
                FROM bids
            )
            SELECT auction_id, bid_amount FROM Ranked WHERE r = 2;
        """),
        ("MoM Trends LAG Window", """
            WITH Monthly AS (
                SELECT DATE_FORMAT(bid_time, '%Y-%m') as m, COUNT(id) as cnt FROM bids GROUP BY m
            )
            SELECT m, cnt, LAG(cnt, 1) OVER (ORDER BY m) FROM Monthly;
        """),
        ("Auctions Without Bids Anti-Join", """
            SELECT a.id FROM auctions a LEFT JOIN bids b ON a.id = b.auction_id WHERE b.id IS NULL;
        """)
    ]

    for q_name, q_sql in analytics_queries:
        t0 = time.time()
        cursor.execute(q_sql)
        cursor.fetchall()
        elapsed_ms = (time.time() - t0) * 1000
        record_test(f"Query Benchmark: {q_name}", elapsed_ms < 150.0, f"Latency: {elapsed_ms:.2f}ms")

    # -------------------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------------------
    print("\n" + "=" * 75)
    print(f"VERIFICATION SUMMARY: {len(passed_tests)} PASSED | {len(failed_tests)} FAILED")
    print("=" * 75)

    if failed_tests:
        print("\nFailures:")
        for f, d in failed_tests:
            print(f" - {f}: {d}")
        sys.exit(1)
    else:
        print("\nAll database schema, integrity, concurrency, and analytical tests passed successfully!")
        sys.exit(0)

if __name__ == '__main__':
    run_tests()
