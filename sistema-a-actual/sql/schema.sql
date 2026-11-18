-- Esquema relacional del Sistema A (generado desde los modelos SQLAlchemy).
-- Se crea automáticamente con `python -m scripts.seed`; este archivo es documentación.

CREATE TABLE categories (
	id SERIAL NOT NULL, 
	name VARCHAR(80) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE users (
	id VARCHAR(12) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	email VARCHAR(160) NOT NULL, 
	country VARCHAR(2) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (email)
);
CREATE INDEX ix_users_country ON users (country);

CREATE TABLE carts (
	id SERIAL NOT NULL, 
	user_id VARCHAR(12) NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE orders (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(12) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	total NUMERIC(12, 2) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE INDEX ix_orders_user_id ON orders (user_id);

CREATE TABLE products (
	id VARCHAR(12) NOT NULL, 
	name VARCHAR(160) NOT NULL, 
	description TEXT NOT NULL, 
	price NUMERIC(12, 2) NOT NULL, 
	category_id INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(category_id) REFERENCES categories (id)
);
CREATE INDEX ix_products_category_id ON products (category_id);
CREATE INDEX ix_products_name ON products (name);

CREATE TABLE cart_items (
	cart_id INTEGER NOT NULL, 
	product_id VARCHAR(12) NOT NULL, 
	quantity INTEGER NOT NULL, 
	unit_price NUMERIC(12, 2) NOT NULL, 
	PRIMARY KEY (cart_id, product_id), 
	FOREIGN KEY(cart_id) REFERENCES carts (id) ON DELETE CASCADE, 
	FOREIGN KEY(product_id) REFERENCES products (id)
);

CREATE TABLE inventory (
	product_id VARCHAR(12) NOT NULL, 
	quantity INTEGER NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (product_id), 
	CONSTRAINT ck_inventory_non_negative CHECK (quantity >= 0), 
	FOREIGN KEY(product_id) REFERENCES products (id)
);

CREATE TABLE order_items (
	order_id VARCHAR(36) NOT NULL, 
	product_id VARCHAR(12) NOT NULL, 
	quantity INTEGER NOT NULL, 
	unit_price NUMERIC(12, 2) NOT NULL, 
	PRIMARY KEY (order_id, product_id), 
	FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE CASCADE, 
	FOREIGN KEY(product_id) REFERENCES products (id)
);

CREATE TABLE payments (
	id SERIAL NOT NULL, 
	order_id VARCHAR(36) NOT NULL, 
	amount NUMERIC(12, 2) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	provider_ref VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (order_id), 
	FOREIGN KEY(order_id) REFERENCES orders (id)
);
