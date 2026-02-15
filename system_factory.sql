CREATE TABLE products(
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    article INT NOT NULL
);

CREATE TABLE materials(
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    unit VARCHAR(20),
    stock_balance DECIMAL(10, 2)
);

CREATE TABLE product_materials(
    product_id INTEGER REFERENCES products(id),
    material_id INTEGER REFERENCES materials(id),
    quantity_per_unit DECIMAL(10,2) NOT NULL CHECK (quantity_per_unit > 0),
    PRIMARY KEY (product_id, material_id)
);

CREATE TABLE orders(
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    status TEXT,
    date_of_creation DATE NOT NULL,
    date_of_closing DATE,
    quantity INT NOT NULL
);

INSERT INTO products (name, article) VALUES
('Редуктор', 1001),
('Вал', 1002),
('Корпус', 1003),
('Люк', 2906);

INSERT INTO materials (name, unit, stock_balance) VALUES
('Сталь 45', 'кг', 500),
('Чугун', 'кг', 300),
('Масло', 'л', 100);
('Стекло', 'кг', 400)

INSERT INTO product_materials (product_id, material_id, quantity_per_unit) VALUES
(1, 1, 12.5),
(1, 3, 2.0),
(2, 1, 5.0),
(3, 2, 8.0),
(4, 4, 2.0)

INSERT INTO orders (id, product_id, quantity, status, date_of_creation, date_of_closing) VALUES
(1, 1, 10, 'В работе', '2026-02-10', NULL),
(2, 2, 20, 'Готов', '2026-02-09', '2026-02-14'),
(3, 3, 5, 'Новый', '2026-02-12', NULL);






