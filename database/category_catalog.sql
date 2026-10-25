-- Marketplace taxonomy only. This file creates no users or marketplace listings.
INSERT IGNORE INTO categories (name, slug, description, icon_name) VALUES
('Electronics & Computing', 'electronics-computing', 'Laptops, vintage consoles, audio equipment, and computing devices', 'Cpu'),
('Fine Art & Antiques', 'fine-art-antiques', 'Original paintings, classical sculptures, historic artifacts, and rare manuscripts', 'Palette'),
('Luxury Watches & Jewelry', 'luxury-watches-jewelry', 'Horological masterpieces, Swiss chronographs, diamonds, and estate jewelry', 'Watch'),
('Vintage Motors & Automobilia', 'vintage-motors', 'Classic roadsters, vintage motorcycles, and automobilia memorabilia', 'Car'),
('Rare Collectibles & Numismatics', 'rare-collectibles', 'Coins, comic books, trading cards, and historical memorabilia', 'Sparkles'),
('Industrial Equipment & Machinery', 'industrial-equipment', 'Precision CNC tooling, laboratory equipment, and industrial hardware', 'Cog');
