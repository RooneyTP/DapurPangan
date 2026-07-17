-- Zephyrus seed data (opsional — main.py auto-seed via SQLAlchemy)
-- File ini otomatis dijalankan oleh PostgreSQL saat first run.
-- Tapi karena main.py juga seed via ORM, ini hanya fallback.

-- Note: Data di-seed otomatis oleh app.main._seed_if_empty()
-- File ini disediakan sebagai referensi / manual reset.

TRUNCATE orders, productions, recipes, stocks, customers, products RESTART IDENTITY CASCADE;

INSERT INTO products (name, category, shelf_life_days, unit, default_production) VALUES
('Tempe', 'fermentasi', 2, 'bungkus', 210);

INSERT INTO recipes (product_id, ingredient_name, quantity_per_unit, unit) VALUES
(1, 'Kedelai', 0.1, 'kg'),
(1, 'Ragi', 0.0005, 'kg');

INSERT INTO stocks (ingredient_name, quantity, unit, min_warning, min_critical) VALUES
('Kedelai', 50, 'kg', 15, 5),
('Ragi', 0.08, 'kg', 0.2, 0.1),
('Plastik kemasan', 220, 'pcs', 50, 20);

INSERT INTO customers (name, address, phone) VALUES
('Warung A', 'Jl. Mawar No. 12', '0812-xxxx-xxxx'),
('Warung B', 'Jl. Melati No. 45', '0813-xxxx-xxxx'),
('Pasar C', 'Pasar Induk Lamongan', '-'),
('Kantin D', 'SMK N 1 Lamongan', '0814-xxxx-xxxx');
