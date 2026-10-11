-- =============================================================================
-- BidSmart Analytics — SQL Analytics Query Suite
-- Dialect: MySQL 8.0+ / MariaDB 10.5+
-- Validated against: database/schema.sql and database/seed_data.sql
-- =============================================================================

USE bidsmart_db;

-- -----------------------------------------------------------------------------
-- Query 1: Executive Platform Overview & KPI Aggregation
-- Purpose: Aggregates total auctions, active auctions, success rates, GMV,
-- and average price metrics in a single pass.
-- -----------------------------------------------------------------------------
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
    ROUND(AVG(CASE WHEN a.status = 'COMPLETED' THEN (a.current_highest_bid - a.starting_price) END), 2) AS avg_dollar_increase,
    ROUND(SUM(CASE WHEN a.status = 'COMPLETED' THEN a.current_highest_bid ELSE 0 END), 2) AS total_realized_gmv
FROM auctions a
LEFT JOIN (
    SELECT 
        auction_id, 
        COUNT(id) AS total_accepted_bids,
        COUNT(DISTINCT bidder_id) AS unique_bidders
    FROM bids 
    GROUP BY auction_id
) b_agg ON a.id = b_agg.auction_id;

-- -----------------------------------------------------------------------------
-- Query 2: Category Performance with GROUP BY & HAVING
-- Purpose: Analyzes category gross merchandise value, conversion rates, and
-- average price appreciation across catalog segments with completed sales.
-- -----------------------------------------------------------------------------
SELECT 
    c.id AS category_id,
    c.name AS category_name,
    COUNT(a.id) AS total_listings,
    SUM(CASE WHEN a.status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed_sales,
    ROUND(
        (SUM(CASE WHEN a.status = 'COMPLETED' THEN 1 ELSE 0 END) / COUNT(a.id)) * 100, 
        1
    ) AS category_conversion_rate_pct,
    COALESCE(SUM(a.total_bids), 0) AS total_bids_submitted,
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
GROUP BY c.id, c.name
HAVING completed_sales >= 1
ORDER BY total_category_gmv DESC;

-- -----------------------------------------------------------------------------
-- Query 3: Top 5 Auctions by Bidding Activity via CTE & DENSE_RANK()
-- Purpose: Identifies the listings with the highest competitive bid velocity.
-- -----------------------------------------------------------------------------
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

-- -----------------------------------------------------------------------------
-- Query 4: Second-Highest Winning Price (Vickrey Proxy Gap Analysis)
-- Purpose: Evaluates the dollar spread between the 1st and 2nd highest bids.
-- -----------------------------------------------------------------------------
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

-- -----------------------------------------------------------------------------
-- Query 5: Monthly Bidding Trends & Month-over-Month Growth using LAG()
-- Purpose: Tracks platform velocity and month-over-month percentage changes.
-- -----------------------------------------------------------------------------
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
        ((total_bids_placed - LAG(total_bids_placed, 1) OVER (ORDER BY bid_month)) / 
         NULLIF(LAG(total_bids_placed, 1) OVER (ORDER BY bid_month), 0)) * 100, 2
    ) AS mom_bid_volume_growth_pct,
    active_bidders,
    LAG(active_bidders, 1) OVER (ORDER BY bid_month) AS prev_month_bidders,
    ROUND(
        ((active_bidders - LAG(active_bidders, 1) OVER (ORDER BY bid_month)) / 
         NULLIF(LAG(active_bidders, 1) OVER (ORDER BY bid_month), 0)) * 100, 2
    ) AS mom_bidder_growth_pct,
    total_nominal_bid_value
FROM MonthlyAggregatesCTE
ORDER BY bid_month DESC;

-- -----------------------------------------------------------------------------
-- Query 6: Cumulative Running Totals for GMV and Bids
-- Purpose: Analyzes cumulative market growth across closed auction dates.
-- -----------------------------------------------------------------------------
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

-- -----------------------------------------------------------------------------
-- Query 7: Identification of Auctions Without Bids (Anti-Join Analysis)
-- Purpose: Identifies dead inventory or mispriced listings.
-- -----------------------------------------------------------------------------
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

-- -----------------------------------------------------------------------------
-- Query 8: Repeat Bidder Engagement & Cohort Retention Analysis
-- Purpose: Segments buyers by frequency, win rates, and total expenditure.
-- -----------------------------------------------------------------------------
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
JOIN roles r ON u.role_id = r.id
WHERE r.name = 'BUYER'
GROUP BY u.id, u.username, u.created_at
HAVING total_bids_submitted >= 3
ORDER BY total_bids_submitted DESC;
