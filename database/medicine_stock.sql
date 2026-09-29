CREATE DATABASE medicine_stock_db;
USE medicine_stock_db;

CREATE TABLE suppliers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    supplier_name VARCHAR(100),
    contact_number VARCHAR(15),
    address TEXT
);

CREATE TABLE medicines (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    category VARCHAR(100),
    batch_number VARCHAR(100),
    supplier_id INT,
    manufacture_date DATE,
    expiry_date DATE,
    quantity INT,
    price DECIMAL(10,2),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
);

CREATE TABLE sales (
    id INT AUTO_INCREMENT PRIMARY KEY,
    medicine_id INT,
    customer_name VARCHAR(100) DEFAULT 'Walk-in Customer',
    quantity_sold INT,
    total_amount DECIMAL(10,2),
    sale_date DATE,
    FOREIGN KEY (medicine_id) REFERENCES medicines(id)
);

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE,
    password VARCHAR(255),
    role VARCHAR(50)
);

INSERT INTO users (username, password, role)
VALUES ('admin', 'admin123', 'Admin');