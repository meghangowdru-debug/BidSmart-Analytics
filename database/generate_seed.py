#!/usr/bin/env python3
"""
Seed Data Generator for BidSmart Analytics (Phase 2 & 3)
Generates database/seed_data.sql with realistic data adhering to PRD requirements:
- 32 Users (2 Admins, 5 Sellers, 25 Buyers)
- 6 Categories
- 40 Products & 40 Auctions (15 Active, 18 Completed, 4 Unsold, 3 Reserve Not Met)
- ~350-410 Bids spanning 60 days with realistic price escalation and 2 flagged anomaly patterns
- 18 Transactions (Simulated Demo Settlements)
- Watchlist entries, notifications, and audit logs
"""

import sys
import random
from datetime import datetime, timedelta, timezone

PASSWORD_HASH = "$2b$10$.IY4MVG0QMk.ra4HvBil7uAyZvSK9PjJCaAPpB3hFPzPCJvxbybFa"

now = datetime.now(timezone.utc).replace(microsecond=0)

def fmt_dt(dt):
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def fmt_dt_ms(dt, ms=0):
    return dt.strftime(f'%Y-%m-%d %H:%M:%S.{ms:03d}')

def escape_str(s):
    return s.replace("'", "''")

roles_data = [
    (1, 'ADMIN', 'Full system administrative and governance access'),
    (2, 'SELLER', 'Can list, manage, and monitor auction inventories'),
    (3, 'BUYER', 'Can browse, watchlist, bid, and settle won auctions')
]

users_data = [
    # Admins
    (1, 'admin_sarah', 'sarah.chen@bidsmart.io', PASSWORD_HASH, 'Sarah Chen', '+1-555-0101', 1, 'ACTIVE', now - timedelta(days=90)),
    (2, 'admin_alex', 'alex.mercer@bidsmart.io', PASSWORD_HASH, 'Alex Mercer', '+1-555-0102', 1, 'ACTIVE', now - timedelta(days=90)),
    # Sellers
    (3, 'vance_estates', 'marcus.vance@vanceestates.com', PASSWORD_HASH, 'Marcus Vance', '+1-555-0201', 2, 'ACTIVE', now - timedelta(days=85)),
    (4, 'apex_electronics', 'contact@apexelectronics.com', PASSWORD_HASH, 'Liam Apex', '+1-555-0202', 2, 'ACTIVE', now - timedelta(days=80)),
    (5, 'heritage_antiques', 'clara.heritage@antiquities.org', PASSWORD_HASH, 'Clara Oswald', '+1-555-0203', 2, 'ACTIVE', now - timedelta(days=75)),
    (6, 'chronos_luxury', 'concierge@chronoswatches.com', PASSWORD_HASH, 'Julian Sterling', '+1-555-0204', 2, 'ACTIVE', now - timedelta(days=70)),
    (7, 'velocity_motors', 'inventory@velocitymotors.net', PASSWORD_HASH, 'Viktor Rossi', '+1-555-0205', 2, 'ACTIVE', now - timedelta(days=65)),
    # Buyers
    (8, 'elena_r', 'elena.rostova@gmail.com', PASSWORD_HASH, 'Elena Rostova', '+1-555-0301', 3, 'ACTIVE', now - timedelta(days=60)),
    (9, 'david_k', 'david.kumar@outlook.com', PASSWORD_HASH, 'David Kumar', '+1-555-0302', 3, 'ACTIVE', now - timedelta(days=60)),
    (10, 'collector_dan', 'daniel.stone@yahoo.com', PASSWORD_HASH, 'Daniel Stone', '+1-555-0303', 3, 'ACTIVE', now - timedelta(days=58)),
    (11, 'speed_demon', 'marcos.alvarez@motorfan.com', PASSWORD_HASH, 'Marcos Alvarez', '+1-555-0304', 3, 'ACTIVE', now - timedelta(days=55)),
    (12, 'retro_gamer', 'kenji.sato@gamesretro.jp', PASSWORD_HASH, 'Kenji Sato', '+1-555-0305', 3, 'ACTIVE', now - timedelta(days=52)),
    (13, 'luxe_collector', 'sophia.montgomery@luxe.co.uk', PASSWORD_HASH, 'Sophia Montgomery', '+1-555-0306', 3, 'ACTIVE', now - timedelta(days=50)),
    (14, 'gear_head', 'hans.schmidt@industrialgear.de', PASSWORD_HASH, 'Hans Schmidt', '+1-555-0307', 3, 'ACTIVE', now - timedelta(days=48)),
    (15, 'art_aficionado', 'isabella.rossi@artgalerie.fr', PASSWORD_HASH, 'Isabella Rossi', '+1-555-0308', 3, 'ACTIVE', now - timedelta(days=45)),
    (16, 'crypto_whale', 'miles.zhang@cryptoasset.io', PASSWORD_HASH, 'Miles Zhang', '+1-555-0309', 3, 'ACTIVE', now - timedelta(days=42)),
    (17, 'bargain_hunter', 'tom.hardy@gmail.com', PASSWORD_HASH, 'Tom Hardy', '+1-555-0310', 3, 'ACTIVE', now - timedelta(days=40)),
    (18, 'vintage_vault', 'beatrice.webb@vaultcollectibles.com', PASSWORD_HASH, 'Beatrice Webb', '+1-555-0311', 3, 'ACTIVE', now - timedelta(days=38)),
    (19, 'audio_phile', 'andre.dupont@soundstage.com', PASSWORD_HASH, 'Andre Dupont', '+1-555-0312', 3, 'ACTIVE', now - timedelta(days=35)),
    (20, 'watch_maven', 'rachel.green@horologytoday.com', PASSWORD_HASH, 'Rachel Green', '+1-555-0313', 3, 'ACTIVE', now - timedelta(days=32)),
    (21, 'stealth_bidder', 'carlos.m@stealthinvest.com', PASSWORD_HASH, 'Carlos Mendoza', '+1-555-0314', 3, 'ACTIVE', now - timedelta(days=30)),
    (22, 'machinery_pro', 'robert.kowalski@precisionmach.com', PASSWORD_HASH, 'Robert Kowalski', '+1-555-0315', 3, 'ACTIVE', now - timedelta(days=28)),
    (23, 'antique_scout', 'eleanor.vance@estatescout.com', PASSWORD_HASH, 'Eleanor Vance', '+1-555-0316', 3, 'ACTIVE', now - timedelta(days=25)),
    (24, 'pixel_collector', 'tariq.almansoor@pixelvault.ae', PASSWORD_HASH, 'Tariq Al-Mansoor', '+1-555-0317', 3, 'ACTIVE', now - timedelta(days=22)),
    (25, 'timepiece_guru', 'oliver.smith@timepiece.ch', PASSWORD_HASH, 'Oliver Smith', '+1-555-0318', 3, 'ACTIVE', now - timedelta(days=20)),
    (26, 'classic_driver', 'giuseppe.moretti@scuderia.it', PASSWORD_HASH, 'Giuseppe Moretti', '+1-555-0319', 3, 'ACTIVE', now - timedelta(days=18)),
    (27, 'snipe_master', 'viktor.dragov@snipebot.ru', PASSWORD_HASH, 'Viktor Dragov', '+1-555-0320', 3, 'ACTIVE', now - timedelta(days=15)),
    (28, 'shill_shadow', 'shadow.phantom@tempmail.com', PASSWORD_HASH, 'Arthur Pendelton', '+1-555-0321', 3, 'ACTIVE', now - timedelta(days=14)),
    (29, 'casual_shopper', 'emily.clark@icloud.com', PASSWORD_HASH, 'Emily Clark', '+1-555-0322', 3, 'ACTIVE', now - timedelta(days=12)),
    (30, 'tech_pioneer', 'arjun.patel@technova.in', PASSWORD_HASH, 'Arjun Patel', '+1-555-0323', 3, 'ACTIVE', now - timedelta(days=10)),
    (31, 'rare_finds', 'lucas.silva@findsbrazil.br', PASSWORD_HASH, 'Lucas Silva', '+1-555-0324', 3, 'ACTIVE', now - timedelta(days=8)),
    (32, 'nordic_buyer', 'astrid.lindholm@nordicauctions.se', PASSWORD_HASH, 'Astrid Lindholm', '+1-555-0325', 3, 'ACTIVE', now - timedelta(days=5))
]

categories_data = [
    (1, 'Electronics & Computing', 'electronics-computing', 'Laptops, vintage consoles, audio equipment, and computing devices', 'Cpu'),
    (2, 'Fine Art & Antiques', 'fine-art-antiques', 'Original paintings, classical sculptures, historic artifacts, and rare manuscripts', 'Palette'),
    (3, 'Luxury Watches & Jewelry', 'luxury-watches-jewelry', 'Horological masterpieces, Swiss chronographs, diamonds, and estate jewelry', 'Watch'),
    (4, 'Vintage Motors & Automobilia', 'vintage-motors', 'Classic roadsters, vintage motorcycles, and automobilia memorabilia', 'Car'),
    (5, 'Rare Collectibles & Numismatics', 'rare-collectibles', 'Coins, comic books, trading cards, and historical memorabilia', 'Sparkles'),
    (6, 'Industrial Equipment & Machinery', 'industrial-equipment', 'Precision CNC tooling, laboratory equipment, and industrial hardware', 'Cog')
]

products_raw = [
    # ACTIVE AUCTIONS (1 to 15)
    (1, 4, 1, 'Apple Macintosh 128K (1984) Complete in Original Box', 'Museum-condition original Macintosh 128K, signed motherboard, includes original keyboard, mouse, and manual packing.', 'VINTAGE', 'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0', 'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=200'),
    (2, 6, 3, 'Rolex Submariner Date Ref. 16610 (1998) Swiss-T Dial', 'Unpolished neo-vintage Submariner with tritium dial and matching hands, complete box, punched papers, and anchor.', 'LIKE_NEW', 'https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9', 'https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=200'),
    (3, 3, 5, '1967 Gibson Les Paul Standard Goldtop Original P-90s', 'Original finish, no breaks or repairs. Original Brazilian rosewood board and CTS pots dating to 1967. Includes original Lifton case.', 'VINTAGE', 'https://images.unsplash.com/photo-1516924962500-2b4b3b99ea02', 'https://images.unsplash.com/photo-1516924962500-2b4b3b99ea02?w=200'),
    (4, 4, 1, 'Sony Walkman TPS-L2 Original 1979 First Edition', 'First edition blue and silver stereo cassette player, fully serviced with new drive belts and calibrated pinch roller.', 'VINTAGE', 'https://images.unsplash.com/photo-1508700115892-45ecd05ae2ad', 'https://images.unsplash.com/photo-1508700115892-45ecd05ae2ad?w=200'),
    (5, 5, 2, 'Original Oil on Canvas: Venetian Lagoon Sunset (1892)', 'Signed Italian romanticist landscape, restored and stabilized by certified conservator, framed in gilded baroque wood.', 'USED', 'https://images.unsplash.com/photo-1579783900882-c0d3dad7b119', 'https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?w=200'),
    (6, 6, 3, 'Audemars Piguet Royal Oak Jumbo Extra-Thin Ref. 15202ST', 'Iconic Gerald Genta design, petite tapisserie blue dial, cal. 2121 manufacture movement, 2018 full set.', 'LIKE_NEW', 'https://images.unsplash.com/photo-1524805444758-089113d48a6d', 'https://images.unsplash.com/photo-1524805444758-089113d48a6d?w=200'),
    (7, 7, 4, '1974 Alfa Romeo GTV 2000 Bertone Coupe', 'Restored in Rosso Corsa over black vinyl, dual Weber carburetors, 5-speed manual, California rust-free chassis.', 'USED', 'https://images.unsplash.com/photo-1503376780353-7e6692767b70', 'https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=200'),
    (8, 5, 5, '1999 Pokemon Base Set 1st Edition Charizard Holographic Shadowless PSA 8', 'Authentic PSA 8 Near Mint-Mint specimen, vibrant foil pattern, clean borders, collector grail card.', 'LIKE_NEW', 'https://images.unsplash.com/photo-1613771404784-3a5686aa2be3', 'https://images.unsplash.com/photo-1613771404784-3a5686aa2be3?w=200'),
    (9, 3, 6, 'Bridgeport Series 1 2HP Variable Speed Milling Machine', 'Equipped with 3-axis Acu-Rite digital readout, chrome ways, power table feed, and complete Kurt vise setup.', 'USED', 'https://images.unsplash.com/photo-1581092160607-ee22621dd758', 'https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=200'),
    (10, 4, 1, 'Hasselblad 500C/M Medium Format Film Camera Kit with Zeiss 80mm f/2.8', 'Complete with chrome Carl Zeiss Planar T* 80mm lens, A12 film back, and waist level finder. Clean optics.', 'LIKE_NEW', 'https://images.unsplash.com/photo-1516035069371-29a1b244cc32', 'https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=200'),
    (11, 6, 3, 'Omega Speedmaster Professional Moonwatch Cal. 321 Ed White', 'Stainless steel chronograph, straight lugs, dot-over-ninety bezel, sapphire caseback displaying rebuilt cal. 321.', 'NEW', 'https://images.unsplash.com/photo-1509042239860-f550ce710b93', 'https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=200'),
    (12, 7, 4, '1988 BMW E30 M3 Evolution II Homologation Special', 'Misano Red over cloth tartan interior, 2.3L S14 naturally aspirated motor, verified matching numbers, 64k km.', 'USED', 'https://images.unsplash.com/photo-1552519507-da3b142c6e3d', 'https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=200'),
    (13, 5, 2, 'Ming Dynasty Glazed Celadon Ceramic Incense Burner (15th C.)', 'Tripod ceramic censer with crackled olive glaze, provenance documentation from prominent French estate.', 'VINTAGE', 'https://images.unsplash.com/photo-1565193566173-7a0ee3dbe261', 'https://images.unsplash.com/photo-1565193566173-7a0ee3dbe261?w=200'),
    (14, 3, 5, 'Superman #1 (1939) Golden Age Comic Book CGC 3.5 Restored', 'Historic issue featuring origin recap and pin-up, off-white pages, rare collector milestone piece.', 'USED', 'https://images.unsplash.com/photo-1534447677768-be436bb09401', 'https://images.unsplash.com/photo-1534447677768-be436bb09401?w=200'),
    (15, 4, 6, 'Mitutoyo Linear Height LH-600E 2D High Accuracy Height Gauge', 'High precision pneumatic floating system, color LCD display, digital probe calibration standard included.', 'LIKE_NEW', 'https://images.unsplash.com/photo-1581092335397-9583fe92d232', 'https://images.unsplash.com/photo-1581092335397-9583fe92d232?w=200'),

    # COMPLETED AUCTIONS (16 to 33)
    (16, 4, 1, 'Commodore 64 Golden Edition Commemorative Unit (1986)', 'Limited production celebration unit, gold plated chassis, original box and test cartridge.', 'VINTAGE', 'https://images.unsplash.com/photo-1550745165-9bc0b252726f', 'https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=200'),
    (17, 6, 3, 'Patek Philippe Calatrava Ref. 5196G White Gold', 'Classic 37mm dress watch, silvery opaline dial, manual wind caliber 215 PS, alligator strap with gold buckle.', 'LIKE_NEW', 'https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9', 'https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=200'),
    (18, 5, 2, 'Art Deco Bronze Sculpture "Dancer with Scarf" by Claire Colinet', 'Authentic 1925 foundry cast with gilt patina, signed marble plinth base, certified authenticity certificate.', 'VINTAGE', 'https://images.unsplash.com/photo-1544967082-d9d25d867d66', 'https://images.unsplash.com/photo-1544967082-d9d25d867d66?w=200'),
    (19, 7, 4, '1965 Ford Mustang Fastback 289 V8 4-Speed Manual', 'Wimbledon White with Guardsman Blue Le Mans stripes, dual exhaust, Pony interior, pristine restoration.', 'USED', 'https://images.unsplash.com/photo-1584345604476-8ec5e12e42dd', 'https://images.unsplash.com/photo-1584345604476-8ec5e12e42dd?w=200'),
    (20, 3, 5, '1907 Saint-Gaudens Double Eagle $20 Gold Coin High Relief NGC MS63', 'Wire rim variety, Roman numerals MCMVII, sharp strike and radiant satin luster, premier numismatic asset.', 'NEW', 'https://images.unsplash.com/photo-1610375461246-83df859d849d', 'https://images.unsplash.com/photo-1610375461246-83df859d849d?w=200'),
    (21, 4, 6, 'Haas VF-2 3-Axis Vertical CNC Machining Center (2018)', '20-station tool changer, inline direct drive 12,000 RPM spindle, wireless intuition probing system.', 'USED', 'https://images.unsplash.com/photo-1581092160607-ee22621dd758', 'https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=200'),
    (22, 6, 3, 'Cartier Crash Skeleton Platinum Limited Edition', 'Asymmetrical case design in solid 950 platinum, in-house skeletonized movement 9618 MC, deployment clasp.', 'LIKE_NEW', 'https://images.unsplash.com/photo-1547996160-71dfabbce5ed', 'https://images.unsplash.com/photo-1547996160-71dfabbce5ed?w=200'),
    (23, 5, 2, 'Original Pablo Picasso Drypoint Etching "Le Repas Frugal" (1904)', 'From the Saltimbanques suite, signed in pencil by Picasso, Van Gelder Zonen watermarked paper, framed.', 'VINTAGE', 'https://images.unsplash.com/photo-1579783900882-c0d3dad7b119', 'https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?w=200'),
    (24, 7, 4, '1972 Datsun 240Z Series 1 Sports Coupe', 'Finished in Safari Gold, matching 2.4L L24 inline-6, dual Hitachi carburetors, original wood rim steering wheel.', 'USED', 'https://images.unsplash.com/photo-1503376780353-7e6692767b70', 'https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=200'),
    (25, 3, 5, 'Michael Jordan 1986 Fleer Rookie Card #57 BGS 9.5 Gem Mint', 'Subgrades: Centering 9.5, Corners 9.5, Edges 9.0, Surface 9.5. Iconic modern sports card cornerstone.', 'NEW', 'https://images.unsplash.com/photo-1546519638-68e109498ffc', 'https://images.unsplash.com/photo-1546519638-68e109498ffc?w=200'),
    (26, 4, 1, 'Nakamichi Dragon 3-Head Auto-Reverse Cassette Deck', 'Discrete three-head system with NAAC microprocessor automatic azimuth correction. Serviced and calibrated.', 'LIKE_NEW', 'https://images.unsplash.com/photo-1508700115892-45ecd05ae2ad', 'https://images.unsplash.com/photo-1508700115892-45ecd05ae2ad?w=200'),
    (27, 6, 3, 'Jaeger-LeCoultre Reverso Tribute Monoface Small Seconds Burgundy', 'Stainless steel reversible case, deep sunray burgundy lacquered dial, manual cal. 822/2, Fagliano strap.', 'LIKE_NEW', 'https://images.unsplash.com/photo-1524805444758-089113d48a6d', 'https://images.unsplash.com/photo-1524805444758-089113d48a6d?w=200'),
    (28, 5, 2, 'Japanese Edo Period Samurai Katana Signed Bizen Osafune', 'NBTHK Tokubetsu Hozon certified blade, traditional hamon line, complete with lacquered scabbard and tsuba.', 'VINTAGE', 'https://images.unsplash.com/photo-1565193566173-7a0ee3dbe261', 'https://images.unsplash.com/photo-1565193566173-7a0ee3dbe261?w=200'),
    (29, 7, 4, '1969 Chevrolet Camaro Z/28 DZ302 Cross-Ram V8', 'Hugger Orange with black stripes, factory 4-speed M21 transmission, 12-bolt posi rear end, documented protect-o-plate.', 'USED', 'https://images.unsplash.com/photo-1552519507-da3b142c6e3d', 'https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=200'),
    (30, 3, 5, 'Magic: The Gathering Black Lotus (Unlimited Edition) BGS 8.5', 'Pristine Power Nine card, sharp corners, strong centering, iconic artwork by Christopher Rush.', 'LIKE_NEW', 'https://images.unsplash.com/photo-1613771404784-3a5686aa2be3', 'https://images.unsplash.com/photo-1613771404784-3a5686aa2be3?w=200'),
    (31, 4, 1, 'Neve 1073 Classic Microphone Preamplifier & Equalizer Pair', 'Hand-wired modular UK channel strips in custom 19-inch flight chassis, original Marinair transformers.', 'USED', 'https://images.unsplash.com/photo-1598488035139-bdbb2231ce04', 'https://images.unsplash.com/photo-1598488035139-bdbb2231ce04?w=200'),
    (32, 6, 3, 'Tudor Submariner "Snowflake" Ref. 94110 Blue Dial (1976)', 'Original matte blue dial with warm creamy tritium lume, matching snowflake hands, folded link oyster bracelet.', 'USED', 'https://images.unsplash.com/photo-1509042239860-f550ce710b93', 'https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=200'),
    (33, 4, 6, 'Trumpf TruLaser 1030 Fiber Precision Sheet Metal Cutting System', '3kW solid-state fiber laser source, integrated loading table, low operational hours, full service history.', 'USED', 'https://images.unsplash.com/photo-1581092335397-9583fe92d232', 'https://images.unsplash.com/photo-1581092335397-9583fe92d232?w=200'),

    # UNSOLD AUCTIONS (34 to 37)
    (34, 3, 6, '1895 Heidelberg Commercial Letterpress Printing Press', 'Heavy cast iron letterpress, requires full mechanical restoration and crane transport from rural barn.', 'USED', 'https://images.unsplash.com/photo-1581092160607-ee22621dd758', 'https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=200'),
    (35, 4, 6, 'PerkinElmer Lambda 950 UV/Vis/NIR Spectrophotometer', 'Laboratory grade analytical spectrophotometer, powers on but uncalibrated, missing software dongle.', 'USED', 'https://images.unsplash.com/photo-1581092335397-9583fe92d232', 'https://images.unsplash.com/photo-1581092335397-9583fe92d232?w=200'),
    (36, 5, 2, '19th Century French Pipe Organ Reed Chest & Wooden Bellows', 'Disassembled church organ pipes and oak chest, highly specialized restoration piece, 400kg weight.', 'VINTAGE', 'https://images.unsplash.com/photo-1544967082-d9d25d867d66', 'https://images.unsplash.com/photo-1544967082-d9d25d867d66?w=200'),
    (37, 3, 5, 'Handwritten 1840 Bavarian Commercial Guild Tax Ledger', 'Bound in pigskin parchment, gothic script in German, historical document with moderate foxing.', 'VINTAGE', 'https://images.unsplash.com/photo-1534447677768-be436bb09401', 'https://images.unsplash.com/photo-1534447677768-be436bb09401?w=200'),

    # RESERVE_NOT_MET AUCTIONS (38 to 40)
    (38, 7, 4, '1968 Porsche 911S 2.0L Coupe Matching Numbers Slate Grey', 'Original factory Fuchs alloys, 5-speed manual, documented Kardex, pristine show condition.', 'LIKE_NEW', 'https://images.unsplash.com/photo-1503376780353-7e6692767b70', 'https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=200'),
    (39, 6, 3, 'Patek Philippe Nautilus Ref. 5711/1A-010 Blue Dial Steel', 'The quintessential luxury sports watch, complete box and papers from original 2017 authorized dealer.', 'LIKE_NEW', 'https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9', 'https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=200'),
    (40, 5, 5, 'J.R.R. Tolkien "The Hobbit" (1937) First Edition First Impression', 'Allen & Unwin original publication with author illustrations, rare dust jacket with manuscript correction.', 'VINTAGE', 'https://images.unsplash.com/photo-1544967082-d9d25d867d66', 'https://images.unsplash.com/photo-1544967082-d9d25d867d66?w=200')
]

# Set active auction durations so that they remain safely active for testing
auctions_config = [
    # Active: 1, 2, 3 ending soon (4h, 8h, 12h to prevent early expiration during tests)
    (1, 1500.00, None, 25.00, now - timedelta(days=6, hours=20), now + timedelta(hours=4), 'ACTIVE'),
    (2, 6500.00, 10000.00, 100.00, now - timedelta(days=6, hours=16), now + timedelta(hours=8), 'ACTIVE'),
    (3, 12000.00, None, 250.00, now - timedelta(days=5), now + timedelta(hours=12), 'ACTIVE'),
    # Active: ending in 1 to 7 days
    (4, 450.00, None, 10.00, now - timedelta(days=2), now + timedelta(days=2), 'ACTIVE'),
    (5, 3200.00, 5000.00, 50.00, now - timedelta(days=3), now + timedelta(days=3), 'ACTIVE'),
    (6, 28000.00, 35000.00, 250.00, now - timedelta(days=4), now + timedelta(days=3, hours=12), 'ACTIVE'),
    (7, 18000.00, 25000.00, 250.00, now - timedelta(days=1), now + timedelta(days=4), 'ACTIVE'),
    (8, 8500.00, None, 100.00, now - timedelta(days=2), now + timedelta(days=5), 'ACTIVE'),
    (9, 2500.00, None, 50.00, now - timedelta(days=3), now + timedelta(days=4), 'ACTIVE'),
    (10, 1800.00, None, 25.00, now - timedelta(days=1), now + timedelta(days=6), 'ACTIVE'),
    (11, 7500.00, 9000.00, 100.00, now - timedelta(days=2), now + timedelta(days=5), 'ACTIVE'),
    (12, 45000.00, 60000.00, 500.00, now - timedelta(days=3), now + timedelta(days=6), 'ACTIVE'),
    (13, 1200.00, None, 25.00, now - timedelta(days=1), now + timedelta(days=6, hours=18), 'ACTIVE'),
    (14, 15000.00, 20000.00, 250.00, now - timedelta(days=2), now + timedelta(days=5), 'ACTIVE'),
    (15, 3500.00, None, 50.00, now - timedelta(days=1), now + timedelta(days=7), 'ACTIVE'),

    # Completed: 16 to 33
    (16, 800.00, None, 20.00, now - timedelta(days=55), now - timedelta(days=48), 'COMPLETED'),
    (17, 14000.00, 16000.00, 200.00, now - timedelta(days=52), now - timedelta(days=45), 'COMPLETED'),
    (18, 4500.00, None, 50.00, now - timedelta(days=50), now - timedelta(days=43), 'COMPLETED'),
    (19, 28000.00, 32000.00, 250.00, now - timedelta(days=48), now - timedelta(days=41), 'COMPLETED'),
    (20, 18000.00, None, 250.00, now - timedelta(days=45), now - timedelta(days=38), 'COMPLETED'),
    (21, 35000.00, 42000.00, 500.00, now - timedelta(days=42), now - timedelta(days=35), 'COMPLETED'),
    (22, 65000.00, 75000.00, 500.00, now - timedelta(days=40), now - timedelta(days=33), 'COMPLETED'),
    (23, 12000.00, None, 200.00, now - timedelta(days=38), now - timedelta(days=31), 'COMPLETED'),
    (24, 16000.00, 20000.00, 250.00, now - timedelta(days=35), now - timedelta(days=28), 'COMPLETED'),
    (25, 22000.00, None, 250.00, now - timedelta(days=32), now - timedelta(days=25), 'COMPLETED'),
    (26, 1200.00, None, 25.00, now - timedelta(days=30), now - timedelta(days=23), 'COMPLETED'),
    (27, 7000.00, 8500.00, 100.00, now - timedelta(days=28), now - timedelta(days=21), 'COMPLETED'),
    (28, 8500.00, None, 100.00, now - timedelta(days=25), now - timedelta(days=18), 'COMPLETED'),
    (29, 42000.00, 50000.00, 500.00, now - timedelta(days=22), now - timedelta(days=15), 'COMPLETED'),
    (30, 9500.00, None, 100.00, now - timedelta(days=20), now - timedelta(days=13), 'COMPLETED'),
    (31, 3000.00, None, 50.00, now - timedelta(days=18), now - timedelta(days=11), 'COMPLETED'),
    (32, 6000.00, 7500.00, 100.00, now - timedelta(days=15), now - timedelta(days=8), 'COMPLETED'),
    (33, 48000.00, 55000.00, 500.00, now - timedelta(days=12), now - timedelta(days=5), 'COMPLETED'),

    # Unsold: 34 to 37 (Zero bids)
    (34, 4500.00, None, 50.00, now - timedelta(days=25), now - timedelta(days=18), 'UNSOLD'),
    (35, 6200.00, None, 100.00, now - timedelta(days=20), now - timedelta(days=13), 'UNSOLD'),
    (36, 8500.00, None, 100.00, now - timedelta(days=15), now - timedelta(days=8), 'UNSOLD'),
    (37, 2800.00, None, 50.00, now - timedelta(days=10), now - timedelta(days=3), 'UNSOLD'),

    # Reserve Not Met: 38 to 40 (Bids placed, but below reserve)
    (38, 75000.00, 120000.00, 1000.00, now - timedelta(days=16), now - timedelta(days=9), 'RESERVE_NOT_MET'),
    (39, 55000.00, 90000.00, 1000.00, now - timedelta(days=14), now - timedelta(days=7), 'RESERVE_NOT_MET'),
    (40, 25000.00, 40000.00, 500.00, now - timedelta(days=12), now - timedelta(days=5), 'RESERVE_NOT_MET')
]

random.seed(42)

bids_list = []
bid_id_counter = 1
buyer_ids = list(range(8, 33))

anomaly1_auction_id = 1
anomaly1_bidder_id = 27

auction_state = {}

for (auc_id, st_price, res_price, min_inc, st_time, end_time, status) in auctions_config:
    if status == 'UNSOLD':
        auction_state[auc_id] = {
            'bids': [],
            'winner_id': None,
            'winning_bid_id': None,
            'highest_bid': None,
            'total_bids': 0
        }
        continue

    if status == 'RESERVE_NOT_MET':
        num_bids = random.randint(6, 12)
    elif status == 'COMPLETED':
        num_bids = random.randint(8, 18)
    else: # ACTIVE
        if auc_id in (1, 2, 3):
            num_bids = random.randint(14, 22)
        else:
            num_bids = random.randint(3, 10)

    cur_price = st_price
    cur_time = st_time + timedelta(hours=random.randint(1, 4))
    
    if status == 'ACTIVE':
        bid_end_limit = min(now - timedelta(minutes=random.randint(5, 20)), end_time - timedelta(hours=1))
    else:
        bid_end_limit = end_time - timedelta(seconds=random.randint(10, 300))

    time_span = (bid_end_limit - cur_time).total_seconds()
    if time_span <= 0:
        time_step = 3600
    else:
        time_step = time_span / (num_bids + 1)

    auc_bids = []
    prev_bidder = None

    for b_idx in range(num_bids):
        seller_id = [p[1] for p in products_raw if p[0] == auc_id][0]
        eligible_bidders = [b for b in buyer_ids if b != seller_id and b != prev_bidder]
        
        if seller_id == 3 and b_idx in (2, 5, 8) and 28 in eligible_bidders:
            chosen_bidder = 28
        else:
            chosen_bidder = random.choice(eligible_bidders)

        prev_bidder = chosen_bidder

        cur_time = cur_time + timedelta(seconds=max(30, int(time_step * random.uniform(0.6, 1.4))))
        if cur_time > bid_end_limit:
            cur_time = bid_end_limit - timedelta(seconds=(num_bids - b_idx) * 15)

        is_anomaly = False
        
        if auc_id == 2 and b_idx == 7:
            inc = min_inc * 40
            cur_price += inc
            is_anomaly = True
        elif auc_id == 1 and b_idx >= num_bids - 3:
            chosen_bidder = anomaly1_bidder_id
            cur_price += min_inc * random.randint(1, 3)
            is_anomaly = True
            cur_time = bid_end_limit - timedelta(seconds=(num_bids - b_idx) * 2)
        else:
            multiplier = random.choice([1, 1, 1, 2, 2, 3, 5])
            cur_price += min_inc * multiplier

        if status == 'RESERVE_NOT_MET' and res_price is not None:
            if cur_price >= res_price:
                cur_price = res_price - (min_inc * (num_bids - b_idx + 1))
                if cur_price <= st_price:
                    cur_price = st_price + min_inc * (b_idx + 1)

        bids_list.append({
            'id': bid_id_counter,
            'auction_id': auc_id,
            'bidder_id': chosen_bidder,
            'bid_amount': round(cur_price, 2),
            'bid_time': cur_time,
            'is_winning_bid': False,
            'is_flagged_anomaly': is_anomaly,
            'ip_address': f"192.168.1.{chosen_bidder + 10}"
        })
        auc_bids.append(bid_id_counter)
        bid_id_counter += 1

    if auc_bids:
        bids_list[-1]['is_winning_bid'] = True
        winner = bids_list[-1]['bidder_id']
        winning_id = bids_list[-1]['id']
        highest_amt = bids_list[-1]['bid_amount']
    else:
        winner = None
        winning_id = None
        highest_amt = None

    auction_state[auc_id] = {
        'bids': auc_bids,
        'winner_id': winner if status != 'RESERVE_NOT_MET' else None,
        'winning_bid_id': winning_id,
        'highest_bid': highest_amt,
        'total_bids': len(auc_bids)
    }

lines = []
lines.append("-- =============================================================================")
lines.append("-- BidSmart Analytics — Seed Data for Local Development & Testing")
lines.append("-- Populates Roles, Users, Categories, Products, Auctions, Bids, Transactions,")
lines.append("-- Watchlist, Notifications, and Audit Logs")
lines.append("-- Total Auctions: 40 | Total Bids: ~350-410 | Users: 32")
lines.append("-- =============================================================================")
lines.append("\nUSE bidsmart_db;\n")
lines.append("SET FOREIGN_KEY_CHECKS = 0;\n")

# 1. ROLES
lines.append("-- 1. INSERT ROLES")
lines.append("INSERT INTO roles (id, name, description) VALUES")
role_vals = [f"({r[0]}, '{escape_str(r[1])}', '{escape_str(r[2])}')" for r in roles_data]
lines.append(",\n".join(role_vals) + ";\n")

# 2. USERS
lines.append("-- 2. INSERT USERS (2 Admins, 5 Sellers, 25 Buyers)")
lines.append("INSERT INTO users (id, username, email, password_hash, full_name, phone, role_id, status, created_at) VALUES")
user_vals = []
for u in users_data:
    user_vals.append(f"({u[0]}, '{escape_str(u[1])}', '{escape_str(u[2])}', '{u[3]}', '{escape_str(u[4])}', '{u[5]}', {u[6]}, '{u[7]}', '{fmt_dt(u[8])}')")
lines.append(",\n".join(user_vals) + ";\n")

# 3. CATEGORIES
lines.append("-- 3. INSERT CATEGORIES (6 Product Classifications)")
lines.append("INSERT INTO categories (id, name, slug, description, icon_name) VALUES")
cat_vals = [f"({c[0]}, '{escape_str(c[1])}', '{escape_str(c[2])}', '{escape_str(c[3])}', '{c[4]}')" for c in categories_data]
lines.append(",\n".join(cat_vals) + ";\n")

# 4. PRODUCTS
lines.append("-- 4. INSERT PRODUCTS (40 Catalog Listings)")
lines.append("INSERT INTO products (id, seller_id, category_id, title, description, condition_status, image_url, thumbnail_url, created_at) VALUES")
prod_vals = []
for p in products_raw:
    p_created = now - timedelta(days=60)
    prod_vals.append(f"({p[0]}, {p[1]}, {p[2]}, '{escape_str(p[3])}', '{escape_str(p[4])}', '{p[5]}', '{p[6]}', '{p[7]}', '{fmt_dt(p_created)}')")
lines.append(",\n".join(prod_vals) + ";\n")

# 5. AUCTIONS
lines.append("-- 5. INSERT AUCTIONS (40 Auctions: 15 Active, 18 Completed, 4 Unsold, 3 Reserve Not Met)")
lines.append("INSERT INTO auctions (id, product_id, starting_price, current_highest_bid, reserve_price, minimum_increment, start_time, end_time, status, winner_id, total_bids, created_at) VALUES")
auc_vals = []
for a in auctions_config:
    auc_id = a[0]
    st = auction_state[auc_id]
    cur_bid_str = f"{st['highest_bid']:.2f}" if st['highest_bid'] is not None else "NULL"
    res_price_str = f"{a[2]:.2f}" if a[2] is not None else "NULL"
    winner_str = f"{st['winner_id']}" if st['winner_id'] is not None else "NULL"
    auc_vals.append(f"({auc_id}, {auc_id}, {a[1]:.2f}, {cur_bid_str}, {res_price_str}, {a[3]:.2f}, '{fmt_dt(a[4])}', '{fmt_dt(a[5])}', '{a[6]}', {winner_str}, {st['total_bids']}, '{fmt_dt(a[4])}')")
lines.append(",\n".join(auc_vals) + ";\n")

# 6. BIDS
lines.append(f"-- 6. INSERT BIDS ({len(bids_list)} Granular Historical & Active Bids)")
lines.append("INSERT INTO bids (id, auction_id, bidder_id, bid_amount, bid_time, is_winning_bid, is_flagged_anomaly, ip_address) VALUES")
bid_chunks = []
chunk_size = 50
for i in range(0, len(bids_list), chunk_size):
    chunk = bids_list[i:i + chunk_size]
    chunk_str = []
    for b in chunk:
        chunk_str.append(f"({b['id']}, {b['auction_id']}, {b['bidder_id']}, {b['bid_amount']:.2f}, '{fmt_dt_ms(b['bid_time'])}', {'TRUE' if b['is_winning_bid'] else 'FALSE'}, {'TRUE' if b['is_flagged_anomaly'] else 'FALSE'}, '{b['ip_address']}')")
    bid_chunks.append(",\n".join(chunk_str))

for idx, c_str in enumerate(bid_chunks):
    if idx > 0:
        lines.append("INSERT INTO bids (id, auction_id, bidder_id, bid_amount, bid_time, is_winning_bid, is_flagged_anomaly, ip_address) VALUES")
    lines.append(c_str + ";\n")

# 7. UPDATE AUCTIONS WITH WINNING_BID_ID
lines.append("-- 7. UPDATE AUCTIONS WITH WINNING_BID_ID CIRCULAR FOREIGN KEYS")
for auc_id, st in auction_state.items():
    if st['winning_bid_id'] is not None:
        lines.append(f"UPDATE auctions SET winning_bid_id = {st['winning_bid_id']} WHERE id = {auc_id};")
lines.append("\n")

# 8. TRANSACTIONS
lines.append("-- 8. INSERT TRANSACTIONS (18 Demo Settlements for Completed Auctions)")
lines.append("INSERT INTO transactions (id, auction_id, buyer_id, seller_id, amount, settlement_type, payment_status, payment_reference, created_at) VALUES")
tx_vals = []
tx_id = 1
for a in auctions_config:
    if a[6] == 'COMPLETED':
        auc_id = a[0]
        seller_id = [p[1] for p in products_raw if p[0] == auc_id][0]
        st = auction_state[auc_id]
        buyer_id = st['winner_id']
        amount = st['highest_bid']
        close_time = a[5]
        ref = f"TX-DEMO-{auc_id:04d}-{int(close_time.timestamp())}"
        status = 'SETTLEMENT_COMPLETED_DEMO' if auc_id < 30 else 'SETTLEMENT_PENDING_DEMO'
        tx_vals.append(f"({tx_id}, {auc_id}, {buyer_id}, {seller_id}, {amount:.2f}, 'SIMULATED_DEMO', '{status}', '{ref}', '{fmt_dt(close_time)}')")
        tx_id += 1
lines.append(",\n".join(tx_vals) + ";\n")

# 9. WATCHLIST
lines.append("-- 9. INSERT WATCHLIST ENTRIES (35 Sample Bookmarks)")
lines.append("INSERT INTO watchlist (user_id, auction_id, created_at) VALUES")
watchlist_pairs = set()
while len(watchlist_pairs) < 35:
    u = random.choice(buyer_ids)
    a = random.randint(1, 40)
    watchlist_pairs.add((u, a))
watchlist_vals = [f"({u}, {a}, '{fmt_dt(now - timedelta(days=random.randint(1, 30)))}')" for (u, a) in sorted(watchlist_pairs)]
lines.append(",\n".join(watchlist_vals) + ";\n")

# 10. NOTIFICATIONS
lines.append("-- 10. INSERT NOTIFICATIONS (Sample Alerts for Bidders and Sellers)")
lines.append("INSERT INTO notifications (user_id, type, title, message, is_read, link_url, created_at) VALUES")
notifications_data = [
    (8, 'AUCTION_WON', 'Victory! You Won the Auction', 'Congratulations! You won the Commodore 64 Golden Edition with a bid of $1,420.00.', True, '/dashboard/won', now - timedelta(days=48)),
    (9, 'AUCTION_WON', 'Victory! You Won the Auction', 'Congratulations! You won the Patek Philippe Calatrava Ref. 5196G.', True, '/dashboard/won', now - timedelta(days=45)),
    (10, 'OUTBID', 'You Have Been Outbid', 'Someone placed a higher bid on Apple Macintosh 128K. Counter-bid now!', False, '/auctions/1', now - timedelta(minutes=14)),
    (11, 'AUCTION_WON', 'Victory! You Won the Auction', 'Congratulations! You won the 1965 Ford Mustang Fastback 289 V8.', True, '/dashboard/won', now - timedelta(days=41)),
    (12, 'OUTBID', 'You Have Been Outbid', 'Someone placed a higher bid on Rolex Submariner Date Ref. 16610.', False, '/auctions/2', now - timedelta(minutes=40)),
    (13, 'AUCTION_WON', 'Victory! You Won the Auction', 'Congratulations! You won the Cartier Crash Skeleton Platinum Edition.', True, '/dashboard/won', now - timedelta(days=33)),
    (15, 'AUCTION_WON', 'Victory! You Won the Auction', 'Congratulations! You won the Picasso Drypoint Etching "Le Repas Frugal".', True, '/dashboard/won', now - timedelta(days=31)),
    (16, 'AUCTION_WON', 'Victory! You Won the Auction', 'Congratulations! You won the 1907 Saint-Gaudens Double Eagle $20 Gold Coin.', True, '/dashboard/won', now - timedelta(days=38)),
    (27, 'ANOMALY_ALERT', 'Bidding Rate Warning', 'Multiple high-frequency bids detected on auction #1. Please ensure manual participation.', True, '/auctions/1', now - timedelta(minutes=12)),
    (3, 'AUCTION_ENDED', 'Listing Closed Unsold', 'Your listing for Heidelberg Letterpress closed without bids.', True, '/dashboard/sales', now - timedelta(days=18)),
    (7, 'AUCTION_ENDED', 'Reserve Price Not Reached', 'Your auction for 1968 Porsche 911S ended at $96,000, falling short of reserve.', True, '/dashboard/sales', now - timedelta(days=9)),
    (6, 'AUCTION_ENDED', 'Listing Sold Successfully', 'Your auction for Rolex Submariner Ref. 16610 was marked completed.', True, '/dashboard/sales', now - timedelta(days=8)),
    (4, 'PRICE_ALERT', 'Price Threshold Reached', 'Apple Macintosh 128K has surpassed $2,000.00.', False, '/auctions/1', now - timedelta(hours=1))
]
notif_vals = [f"({n[0]}, '{n[1]}', '{escape_str(n[2])}', '{escape_str(n[3])}', {'TRUE' if n[4] else 'FALSE'}, '{n[5]}', '{fmt_dt(n[6])}')" for n in notifications_data]
lines.append(",\n".join(notif_vals) + ";\n")

# 11. AUDIT LOGS
lines.append("-- 11. INSERT AUDIT LOGS (Security, Admin & Anomaly Audit Records)")
lines.append("INSERT INTO audit_logs (user_id, action, entity_type, entity_id, old_values, new_values, ip_address, created_at) VALUES")
audit_data = [
    (1, 'USER_ROLE_ELEVATED', 'USER', 3, '{"role": "BUYER"}', '{"role": "SELLER"}', '10.0.0.1', now - timedelta(days=85)),
    (1, 'USER_ROLE_ELEVATED', 'USER', 4, '{"role": "BUYER"}', '{"role": "SELLER"}', '10.0.0.1', now - timedelta(days=80)),
    (3, 'AUCTION_CREATED', 'AUCTION', 1, 'null', '{"starting_price": 1500.00, "minimum_increment": 25.00}', '192.168.1.13', now - timedelta(days=7)),
    (4, 'AUCTION_CREATED', 'AUCTION', 2, 'null', '{"starting_price": 6500.00, "reserve_price": 10000.00}', '192.168.1.14', now - timedelta(days=7)),
    (27, 'ANOMALY_FLAGGED', 'BID', 21, 'null', '{"reason": "RAPID_BID_BURST", "window_seconds": 4.2, "bids_in_window": 3}', '192.168.1.37', now - timedelta(minutes=15)),
    (13, 'ANOMALY_FLAGGED', 'BID', 48, 'null', '{"reason": "EXTREME_PRICE_JUMP", "price_jump": 4000.00, "increment_factor": 40.0}', '192.168.1.23', now - timedelta(minutes=42)),
    (1, 'AUCTION_FORCE_CLOSED', 'AUCTION', 16, '{"status": "ACTIVE"}', '{"status": "COMPLETED", "reason": "SCHEDULED_EXPIRATION"}', '10.0.0.1', now - timedelta(days=48)),
    (1, 'SETTLEMENT_VERIFIED', 'TRANSACTION', 1, '{"status": "SETTLEMENT_PENDING_DEMO"}', '{"status": "SETTLEMENT_COMPLETED_DEMO"}', '10.0.0.1', now - timedelta(days=47))
]
audit_vals = [f"({a[0]}, '{a[1]}', '{a[2]}', {a[3]}, '{escape_str(a[4])}', '{escape_str(a[5])}', '{a[6]}', '{fmt_dt(a[7])}')" for a in audit_data]
lines.append(",\n".join(audit_vals) + ";\n")

lines.append("SET FOREIGN_KEY_CHECKS = 1;\n")

content = "\n".join(lines)
with open("/home/user/database/seed_data.sql", "w", encoding="utf-8") as f:
    f.write(content)

print(f"Successfully generated /home/user/database/seed_data.sql with {len(bids_list)} bids and 40 auctions.")
