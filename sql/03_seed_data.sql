-- Insert admin
INSERT INTO admins (name, email, password) VALUES
('Admin User', 'admin@ecommerce.com', 'admin123');

-- Insert customers
INSERT INTO users (name, email, password, phone, address, city, pincode) VALUES
('John Doe', 'john@gmail.com', 'password123', '9876543210', '123 Main St', 'Mumbai', '400001'),
('Jane Smith', 'jane@yahoo.com', 'pass456', '8765432109', '456 Park Ave', 'Delhi', '110001');

-- Insert categories
INSERT INTO categories (cat_name, cat_desc) VALUES
('Electronics', 'Electronic devices'),
('Clothing', 'Fashion items'),
('Books', 'Books and novels');

-- Insert products
INSERT INTO products (product_name, description, price, stock, category_id, category_name, image_url) VALUES
('iPhone 15', 'Latest Apple phone', 99999.99, 50, 1, 'Electronics', '/images/iphone15.jpg'),
('Samsung S24', 'Android flagship', 89999.99, 30, 1, 'Electronics', '/images/samsung.jpg'),
('Nike Shoes', 'Running shoes', 4999.99, 100, 2, 'Clothing', '/images/nike.jpg'),
('Harry Potter', 'Fantasy novel', 499.99, 200, 3, 'Books', '/images/harrypotter.jpg');

-- Insert cart items
INSERT INTO cart (user_id, product_id, quantity) VALUES
(1, 1, 1),
(1, 2, 2);

-- Insert order
INSERT INTO orders (user_id, total_amount, status) VALUES
(1, 189999.98, 'pending');

-- Insert order items
INSERT INTO order_items (order_id, product_id, product_name, price, quantity) VALUES
(1, 1, 'iPhone 15', 99999.99, 1),
(1, 2, 'Samsung S24', 89999.99, 1);

-- Insert reviews
INSERT INTO reviews (user_id, product_id, rating, comment) VALUES
(1, 1, 5, 'Great phone!'),
(2, 1, 4, 'Good but expensive');