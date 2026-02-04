
-- Admin User
INSERT INTO users (username, email, password, role)
VALUES ('admin', 'admin@wh.com', 'admin123', 'admin');

-- Customer User
INSERT INTO users (username, email, password)
VALUES ('user', 'user@wh.com', 'user123');

-- Hotels
INSERT INTO hotels (city, total_capacity, peak_rate, off_peak_rate) VALUES 
('Aberdeen', 90, 140, 70),
('Belfast', 80, 130, 70),
('Birmingham', 110, 150, 75),
('Bristol', 100, 140, 70),
('Cardiff', 90, 130, 70),
('Edinburgh', 120, 160, 80),
('Glasgow', 140, 150, 75),
('London', 160, 200, 100),
('Manchester', 150, 180, 90);

-- Rooms (example for first hotel)
INSERT INTO rooms (hotel_id, room_number, type_name) VALUES
(1, '101', 'Standard'),
(1, '102', 'Double'),
(1, '103', 'Family');

-- Currencies
INSERT INTO currencies (code, rate_to_gbp) VALUES
('GBP', 1.0),
('EUR', 1.17),
('USD', 1.27);

-- Exchange Rates
INSERT INTO exchange_rates (currency_code, rate_to_gbp) VALUES
('USD', 1.25),
('EUR', 1.18);

-- Optional: promote other users to admin if needed
UPDATE users SET role='admin' WHERE username='managershane1';
