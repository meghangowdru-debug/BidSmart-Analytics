-- =============================================================================
-- BidSmart Analytics — Production Database Schema
-- Dialect: MySQL 8.0+ / MariaDB 10.5+
-- Storage Engine: InnoDB
-- Character Set: utf8mb4 / utf8mb4_unicode_ci
-- Phase: 2 (Database Design Single Source of Truth)
-- =============================================================================

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS notifications;
DROP TABLE IF EXISTS watchlist;
DROP TABLE IF EXISTS bids;
DROP TABLE IF EXISTS auctions;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS roles;

SET FOREIGN_KEY_CHECKS = 1;

-- -----------------------------------------------------------------------------
-- 1. ROLES TABLE
-- Purpose: System security roles defining access entitlements (RBAC).
-- -----------------------------------------------------------------------------
CREATE TABLE roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 2. USERS TABLE
-- Purpose: Platform accounts for buyers, sellers, and administrators.
-- -----------------------------------------------------------------------------
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NULL,
    role_id INT NOT NULL,
    status ENUM('ACTIVE', 'SUSPENDED', 'PENDING_VERIFICATION') NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_users_role FOREIGN KEY (role_id) 
        REFERENCES roles(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    INDEX idx_users_role (role_id),
    INDEX idx_users_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 3. CATEGORIES TABLE
-- Purpose: Product taxonomy classification for filtering and analytics.
-- -----------------------------------------------------------------------------
CREATE TABLE categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    slug VARCHAR(60) NOT NULL UNIQUE,
    description TEXT NULL,
    icon_name VARCHAR(50) NOT NULL DEFAULT 'Tag',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 4. PRODUCTS TABLE
-- Purpose: Tangible and digital goods listed by sellers.
-- -----------------------------------------------------------------------------
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 5. AUCTIONS TABLE
-- Purpose: Core auction listing orchestrating time windows, increments & state.
-- -----------------------------------------------------------------------------
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
    CONSTRAINT chk_minimum_increment CHECK (minimum_increment >= 0.01),
    INDEX idx_auctions_status_end_time (status, end_time),
    INDEX idx_auctions_winner (winner_id),
    INDEX idx_auctions_highest_bid (current_highest_bid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 6. BIDS TABLE
-- Purpose: Granular, immutable ledger of all submitted and accepted bids.
-- -----------------------------------------------------------------------------
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
    CONSTRAINT chk_bid_amount CHECK (bid_amount >= 0.01),
    INDEX idx_bids_auction_amount (auction_id, bid_amount DESC),
    INDEX idx_bids_bidder (bidder_id),
    INDEX idx_bids_time (bid_time),
    INDEX idx_bids_flagged (is_flagged_anomaly),
    INDEX idx_bids_auction_time (auction_id, bid_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Circular foreign key: auctions.winning_bid_id -> bids.id
ALTER TABLE auctions 
ADD CONSTRAINT fk_auctions_winning_bid 
FOREIGN KEY (winning_bid_id) REFERENCES bids(id) ON DELETE SET NULL ON UPDATE CASCADE;

-- -----------------------------------------------------------------------------
-- 7. WATCHLIST TABLE
-- Purpose: User bookmarks for tracking active auctions of interest.
-- -----------------------------------------------------------------------------
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 8. NOTIFICATIONS TABLE
-- Purpose: Real-time and async user alerts (outbid, won, closing soon).
-- -----------------------------------------------------------------------------
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 9. TRANSACTIONS (SIMULATED DEMO SETTLEMENT) TABLE
-- Purpose: Non-monetary demo invoice and escrow settlement tracking.
-- -----------------------------------------------------------------------------
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
    CONSTRAINT chk_transaction_amount CHECK (amount >= 0.01),
    INDEX idx_transactions_status (payment_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 10. AUDIT LOGS TABLE
-- Purpose: Immutable security and administrative governance audit trail.
-- -----------------------------------------------------------------------------
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
    INDEX idx_audit_created (created_at),
    INDEX idx_audit_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- STORED PROCEDURES: CONCURRENCY CONTROL, ATOMIC BIDDING & CLOSING
-- =============================================================================

DELIMITER $$

-- -----------------------------------------------------------------------------
-- sp_place_bid
-- Purpose: Atomically validate and record a bid using row-level locking.
-- Guarantees anti-self-bidding, temporal validity, increment thresholds,
-- and executes an anti-sniping soft-close time extension if needed.
-- -----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_place_bid$$
CREATE PROCEDURE sp_place_bid(
    IN p_auction_id INT,
    IN p_bidder_id INT,
    IN p_bid_amount DECIMAL(12, 2),
    IN p_ip_address VARCHAR(45),
    OUT p_bid_id INT,
    OUT p_status_code VARCHAR(20),
    OUT p_status_message VARCHAR(255)
)
proc_label: BEGIN
    DECLARE v_seller_id INT;
    DECLARE v_auction_status VARCHAR(20);
    DECLARE v_start_time TIMESTAMP;
    DECLARE v_end_time TIMESTAMP;
    DECLARE v_current_bid DECIMAL(12, 2);
    DECLARE v_min_increment DECIMAL(10, 2);
    DECLARE v_starting_price DECIMAL(12, 2);
    DECLARE v_total_bids INT;
    DECLARE v_required_min DECIMAL(12, 2);
    DECLARE v_seconds_remaining INT;
    DECLARE v_is_anti_snipe_extended BOOLEAN DEFAULT FALSE;
    DECLARE v_now TIMESTAMP;

    SET v_now = CURRENT_TIMESTAMP;
    SET p_bid_id = NULL;

    -- Start explicit ACID transaction
    START TRANSACTION;

    -- 1. Lock auction record exclusively with FOR UPDATE to prevent race conditions
    SELECT 
        p.seller_id,
        a.status,
        a.start_time,
        a.end_time,
        a.current_highest_bid,
        a.minimum_increment,
        a.starting_price,
        a.total_bids
    INTO 
        v_seller_id,
        v_auction_status,
        v_start_time,
        v_end_time,
        v_current_bid,
        v_min_increment,
        v_starting_price,
        v_total_bids
    FROM auctions a
    JOIN products p ON a.product_id = p.id
    WHERE a.id = p_auction_id
    FOR UPDATE;

    -- Check existence
    IF v_seller_id IS NULL THEN
        ROLLBACK;
        SET p_status_code = 'NOT_FOUND';
        SET p_status_message = 'Auction listing does not exist.';
        LEAVE proc_label;
    END IF;

    -- 2. Anti-Self-Bidding Enforcement
    IF v_seller_id = p_bidder_id THEN
        ROLLBACK;
        SET p_status_code = 'FORBIDDEN_SELF_BID';
        SET p_status_message = 'Marketplace rule violation: Sellers cannot bid on their own listings.';
        LEAVE proc_label;
    END IF;

    -- 3. Auction Status Verification
    IF v_auction_status != 'ACTIVE' THEN
        ROLLBACK;
        SET p_status_code = 'AUCTION_NOT_ACTIVE';
        SET p_status_message = CONCAT('Cannot bid: Auction status is ', v_auction_status);
        LEAVE proc_label;
    END IF;

    -- 4. Temporal Window Verification
    IF v_now < v_start_time THEN
        ROLLBACK;
        SET p_status_code = 'AUCTION_NOT_STARTED';
        SET p_status_message = 'Auction has not started yet.';
        LEAVE proc_label;
    END IF;

    IF v_now > v_end_time THEN
        -- Auto-close expired auction lazily
        UPDATE auctions SET status = 'COMPLETED' WHERE id = p_auction_id;
        COMMIT;
        SET p_status_code = 'AUCTION_EXPIRED';
        SET p_status_message = 'Auction deadline has passed.';
        LEAVE proc_label;
    END IF;

    -- 5. Calculate Required Minimum Threshold
    IF v_total_bids = 0 THEN
        SET v_required_min = v_starting_price;
    ELSE
        SET v_required_min = v_current_bid + v_min_increment;
    END IF;

    IF p_bid_amount < v_required_min THEN
        ROLLBACK;
        SET p_status_code = 'OUTBID_CONFLICT';
        SET p_status_message = CONCAT('Bid $', p_bid_amount, ' is below required minimum $', v_required_min);
        LEAVE proc_label;
    END IF;

    -- 6. Insert New Winning Bid Record
    INSERT INTO bids (
        auction_id,
        bidder_id,
        bid_amount,
        bid_time,
        is_winning_bid,
        is_flagged_anomaly,
        ip_address
    ) VALUES (
        p_auction_id,
        p_bidder_id,
        p_bid_amount,
        CURRENT_TIMESTAMP(3),
        TRUE,
        FALSE,
        p_ip_address
    );

    SET p_bid_id = LAST_INSERT_ID();

    -- 7. Demote Previous Winning Bids for this Auction
    UPDATE bids 
    SET is_winning_bid = FALSE 
    WHERE auction_id = p_auction_id AND id != p_bid_id;

    -- 8. Check Anti-Sniping Rule: If bid within final 30 seconds, extend by 60 seconds
    SET v_seconds_remaining = TIMESTAMPDIFF(SECOND, v_now, v_end_time);
    IF v_seconds_remaining <= 30 THEN
        SET v_end_time = DATE_ADD(v_end_time, INTERVAL 60 SECOND);
        SET v_is_anti_snipe_extended = TRUE;
    END IF;

    -- 9. Update Auction Aggregate State
    UPDATE auctions 
    SET 
        current_highest_bid = p_bid_amount,
        winner_id = p_bidder_id,
        winning_bid_id = p_bid_id,
        total_bids = total_bids + 1,
        end_time = v_end_time,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_auction_id;

    -- 10. Audit Log Entry
    INSERT INTO audit_logs (
        user_id,
        action,
        entity_type,
        entity_id,
        old_values,
        new_values,
        ip_address
    ) VALUES (
        p_bidder_id,
        'BID_ACCEPTED',
        'AUCTION',
        p_auction_id,
        JSON_OBJECT('previous_highest_bid', v_current_bid, 'previous_total_bids', v_total_bids),
        JSON_OBJECT('new_highest_bid', p_bid_amount, 'bid_id', p_bid_id, 'anti_snipe_extended', v_is_anti_snipe_extended),
        p_ip_address
    );

    COMMIT;
    SET p_status_code = 'SUCCESS';
    SET p_status_message = 'Bid accepted and serialized successfully.';
END$$

-- -----------------------------------------------------------------------------
-- sp_close_expired_auctions
-- Purpose: Identifies all active auctions whose end_time has passed, resolves
-- winners, handles zero-bid auctions, checks reserve prices, and creates
-- simulated demo transaction records.
-- -----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_close_expired_auctions$$
CREATE PROCEDURE sp_close_expired_auctions(
    OUT p_closed_count INT,
    OUT p_unsold_count INT,
    OUT p_reserve_failed_count INT
)
proc_label: BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE v_auction_id INT;
    DECLARE v_product_id INT;
    DECLARE v_seller_id INT;
    DECLARE v_total_bids INT;
    DECLARE v_winning_bid_id INT;
    DECLARE v_winner_id INT;
    DECLARE v_current_highest_bid DECIMAL(12, 2);
    DECLARE v_reserve_price DECIMAL(12, 2);
    DECLARE v_payment_ref VARCHAR(64);

    -- Cursor iterating through active auctions past their deadline
    DECLARE cur_expired CURSOR FOR 
        SELECT 
            a.id,
            a.product_id,
            p.seller_id,
            a.total_bids,
            a.winning_bid_id,
            a.winner_id,
            a.current_highest_bid,
            a.reserve_price
        FROM auctions a
        JOIN products p ON a.product_id = p.id
        WHERE a.status = 'ACTIVE' AND a.end_time <= CURRENT_TIMESTAMP
        FOR UPDATE;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;

    SET p_closed_count = 0;
    SET p_unsold_count = 0;
    SET p_reserve_failed_count = 0;

    OPEN cur_expired;

    close_loop: LOOP
        FETCH cur_expired INTO 
            v_auction_id,
            v_product_id,
            v_seller_id,
            v_total_bids,
            v_winning_bid_id,
            v_winner_id,
            v_current_highest_bid,
            v_reserve_price;

        IF done THEN
            LEAVE close_loop;
        END IF;

        -- CASE A: Zero bids received -> UNSOLD
        IF v_total_bids = 0 OR v_winner_id IS NULL THEN
            UPDATE auctions 
            SET 
                status = 'UNSOLD',
                winner_id = NULL,
                winning_bid_id = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = v_auction_id;

            INSERT INTO notifications (user_id, type, title, message)
            VALUES (
                v_seller_id,
                'AUCTION_ENDED',
                'Auction Closed Unsold',
                CONCAT('Your listing for product #', v_product_id, ' closed without any bids.')
            );

            SET p_unsold_count = p_unsold_count + 1;

        -- CASE B: Bids received, but below reserve price -> RESERVE_NOT_MET
        ELSEIF v_reserve_price IS NOT NULL AND v_current_highest_bid < v_reserve_price THEN
            UPDATE auctions 
            SET 
                status = 'RESERVE_NOT_MET',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = v_auction_id;

            INSERT INTO notifications (user_id, type, title, message)
            VALUES (
                v_seller_id,
                'AUCTION_ENDED',
                'Reserve Price Not Reached',
                CONCAT('Your auction ended at $', v_current_highest_bid, ', which did not meet your reserve price of $', v_reserve_price)
            );

            SET p_reserve_failed_count = p_reserve_failed_count + 1;

        -- CASE C: Valid bids meeting reserve -> COMPLETED with winner settlement
        ELSE
            UPDATE auctions 
            SET 
                status = 'COMPLETED',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = v_auction_id;

            -- Generate unique simulated transaction reference
            SET v_payment_ref = CONCAT('TX-DEMO-', v_auction_id, '-', UNIX_TIMESTAMP());

            INSERT INTO transactions (
                auction_id,
                buyer_id,
                seller_id,
                amount,
                settlement_type,
                payment_status,
                payment_reference
            ) VALUES (
                v_auction_id,
                v_winner_id,
                v_seller_id,
                v_current_highest_bid,
                'SIMULATED_DEMO',
                'SETTLEMENT_PENDING_DEMO',
                v_payment_ref
            );

            -- Winner Notification
            INSERT INTO notifications (user_id, type, title, message, link_url)
            VALUES (
                v_winner_id,
                'AUCTION_WON',
                'Victory! You Won the Auction',
                CONCAT('Congratulations! You won auction #', v_auction_id, ' with a winning bid of $', v_current_highest_bid),
                CONCAT('/dashboard/won')
            );

            -- Seller Notification
            INSERT INTO notifications (user_id, type, title, message, link_url)
            VALUES (
                v_seller_id,
                'AUCTION_ENDED',
                'Listing Sold Successfully',
                CONCAT('Your auction #', v_auction_id, ' has completed successfully at $', v_current_highest_bid),
                CONCAT('/dashboard/sales')
            );

            SET p_closed_count = p_closed_count + 1;
        END IF;

    END LOOP;

    CLOSE cur_expired;
END$$

DELIMITER ;

-- =============================================================================
-- HELPER VIEWS FOR MONITORING AND REPORTING
-- =============================================================================

CREATE OR REPLACE VIEW vw_active_auctions AS
SELECT 
    a.id AS auction_id,
    p.title AS product_title,
    c.name AS category_name,
    u.username AS seller_username,
    a.starting_price,
    COALESCE(a.current_highest_bid, a.starting_price) AS current_price,
    a.minimum_increment,
    a.total_bids,
    a.start_time,
    a.end_time,
    TIMESTAMPDIFF(SECOND, CURRENT_TIMESTAMP, a.end_time) AS seconds_remaining
FROM auctions a
JOIN products p ON a.product_id = p.id
JOIN categories c ON p.category_id = c.id
JOIN users u ON p.seller_id = u.id
WHERE a.status = 'ACTIVE' AND a.end_time > CURRENT_TIMESTAMP;

CREATE OR REPLACE VIEW vw_auction_kpi_summary AS
SELECT 
    COUNT(id) AS total_auctions,
    SUM(CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END) AS active_count,
    SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed_count,
    SUM(CASE WHEN status = 'UNSOLD' THEN 1 ELSE 0 END) AS unsold_count,
    SUM(CASE WHEN status = 'RESERVE_NOT_MET' THEN 1 ELSE 0 END) AS reserve_not_met_count,
    ROUND(SUM(CASE WHEN status = 'COMPLETED' THEN current_highest_bid ELSE 0 END), 2) AS total_realized_gmv,
    ROUND(AVG(CASE WHEN status = 'COMPLETED' THEN current_highest_bid END), 2) AS avg_winning_price,
    ROUND(AVG(starting_price), 2) AS avg_starting_price
FROM auctions;
