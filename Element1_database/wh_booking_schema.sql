-- Users Table
-- Stores system users i.e, customers admins giving access in role-based
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    status TINYINT(1) DEFAULT 0,
    role VARCHAR(20) DEFAULT 'user'
);

-- Hotels Table
-- Stores hotel locations and seasonal pricing details
CREATE TABLE hotels (
    id INT AUTO_INCREMENT PRIMARY KEY,
    city VARCHAR(100) NOT NULL,
    total_capacity INT NOT NULL,
    peak_rate FLOAT NOT NULL,
    off_peak_rate FLOAT NOT NULL
);

-- Rooms Table
-- Stores rooms linked to hotels and tracks availability
CREATE TABLE rooms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    hotel_id INT NOT NULL,
    room_number VARCHAR(10) NOT NULL,
    type_name VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'Available',
    FOREIGN KEY (hotel_id) REFERENCES hotels(id)
);

-- Bookings Table
-- Stores rooms linked to hotels and tracks availability
CREATE TABLE bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    room_id INT NOT NULL,
    check_in DATE NOT NULL,
    check_out DATE NOT NULL,
    guest_count INT NOT NULL,
    total_price FLOAT NOT NULL,
    discount_amount FLOAT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'Confirmed',
    cancellation_fee FLOAT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (room_id) REFERENCES rooms(id)
);

-- Currencies Table
-- Stores supported currencies for price conversion
CREATE TABLE currencies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(5),
    rate_to_gbp DECIMAL(10,4)
);

-- Exchange Rates Table
-- Stores exchange rates relative to GBP
CREATE TABLE IF NOT EXISTS exchange_rates (
    currency_code VARCHAR(3) PRIMARY KEY,
    rate_to_gbp FLOAT NOT NULL
);
