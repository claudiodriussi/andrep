-- AndRep sample database
-- sqlite3 sample.db < create_db.sql

CREATE TABLE categories (
    id          INTEGER PRIMARY KEY,
    code        TEXT    NOT NULL,
    description TEXT    NOT NULL
);

CREATE TABLE articles (
    id          INTEGER PRIMARY KEY,
    code        TEXT    NOT NULL,
    description TEXT    NOT NULL,
    type        TEXT    NOT NULL CHECK(type IN ('STD','SRV','KIT')),
    category_id INTEGER NOT NULL REFERENCES categories(id),
    uom         TEXT    NOT NULL,
    price       REAL    NOT NULL,
    ean         TEXT,               -- EAN-13 barcode
    url         TEXT                -- QR code URL
);

CREATE TABLE movements (
    id          INTEGER PRIMARY KEY,
    article_id  INTEGER NOT NULL REFERENCES articles(id),
    date        TEXT    NOT NULL,   -- ISO date YYYY-MM-DD
    type        TEXT    NOT NULL CHECK(type IN ('C','S')),  -- C=load S=unload
    qty         REAL    NOT NULL,
    unit_price  REAL    NOT NULL,
    notes       TEXT
);

-- -----------------------------------------------------------------------
-- Categories
-- -----------------------------------------------------------------------
INSERT INTO categories VALUES
  (1, 'PASS',  'Passive components'),
  (2, 'SEMI',  'Semiconductors'),
  (3, 'CONN',  'Connectors and cables'),
  (4, 'MCU',   'Microcontrollers and SBCs'),
  (5, 'POWER', 'Power supplies'),
  (6, 'TOOL',  'Tools and instruments'),
  (7, 'SRV',   'Services'),
  (8, 'KIT',   'Development kits');

-- -----------------------------------------------------------------------
-- Articles  (30+ rows to span multiple PDF pages)
-- -----------------------------------------------------------------------
INSERT INTO articles VALUES
  -- Passive
  ( 1, 'ART001', '10 ohm ceramic resistor 1/4W',        'STD', 1, 'PCS',   0.45, '5901234123457', 'https://parts.example.com/ART001'),
  ( 2, 'ART002', '100 ohm ceramic resistor 1/4W',       'STD', 1, 'PCS',   0.45, '5901234123464', 'https://parts.example.com/ART002'),
  ( 3, 'ART003', '1K ohm resistor 1/4W',                'STD', 1, 'PCS',   0.45, '5901234123471', 'https://parts.example.com/ART003'),
  ( 4, 'ART004', '10K ohm resistor 1/4W',               'STD', 1, 'PCS',   0.45, '5901234123488', 'https://parts.example.com/ART004'),
  ( 5, 'ART005', '100nF ceramic capacitor 50V',         'STD', 1, 'PCS',   0.30, '5901234123495', 'https://parts.example.com/ART005'),
  ( 6, 'ART006', '10uF electrolytic capacitor 25V',     'STD', 1, 'PCS',   0.55, '5901234123501', 'https://parts.example.com/ART006'),
  ( 7, 'ART007', '100uF electrolytic capacitor 25V',    'STD', 1, 'PCS',   0.80, '5901234123518', 'https://parts.example.com/ART007'),
  ( 8, 'ART008', '470uF electrolytic capacitor 16V',    'STD', 1, 'PCS',   0.95, '5901234123525', 'https://parts.example.com/ART008'),
  ( 9, 'ART009', '10uH inductor SMD 2A',                'STD', 1, 'PCS',   1.20, '5901234123532', 'https://parts.example.com/ART009'),
  (10, 'ART010', 'Crystal 16MHz HC-49',                 'STD', 1, 'PCS',   0.90, '5901234123549', 'https://parts.example.com/ART010'),
  -- Semiconductors
  (11, 'ART011', '1N4148 signal diode',                 'STD', 2, 'PCS',   0.12, '5901234123556', 'https://parts.example.com/ART011'),
  (12, 'ART012', '1N4007 rectifier diode 1A',           'STD', 2, 'PCS',   0.18, '5901234123563', 'https://parts.example.com/ART012'),
  (13, 'ART013', 'LED red 5mm',                         'STD', 2, 'PCS',   0.15, '5901234123570', 'https://parts.example.com/ART013'),
  (14, 'ART014', 'LED green 5mm',                       'STD', 2, 'PCS',   0.15, '5901234123587', 'https://parts.example.com/ART014'),
  (15, 'ART015', 'BC547 NPN transistor',                'STD', 2, 'PCS',   0.20, '5901234123594', 'https://parts.example.com/ART015'),
  (16, 'ART016', 'IRF540N N-channel MOSFET',            'STD', 2, 'PCS',   1.80, '5901234123600', 'https://parts.example.com/ART016'),
  (17, 'ART017', 'LM358 dual op-amp DIP8',              'STD', 2, 'PCS',   0.65, '5901234123617', 'https://parts.example.com/ART017'),
  (18, 'ART018', 'NE555 timer DIP8',                    'STD', 2, 'PCS',   0.55, '5901234123624', 'https://parts.example.com/ART018'),
  -- Connectors
  (19, 'ART019', 'USB-C cable 1m',                      'STD', 3, 'PCS',   3.50, '5901234123631', 'https://parts.example.com/ART019'),
  (20, 'ART020', 'USB-A to micro-B cable 2m',           'STD', 3, 'PCS',   2.80, '5901234123648', 'https://parts.example.com/ART020'),
  (21, 'ART021', '2.54mm pin header 40p straight',      'STD', 3, 'PCS',   0.60, '5901234123655', 'https://parts.example.com/ART021'),
  (22, 'ART022', 'JST-XH 2p connector set',             'STD', 3, 'PCS',   0.35, '5901234123662', 'https://parts.example.com/ART022'),
  -- MCU / SBC
  (23, 'ART023', 'STM32F103C8T6 microcontroller',       'STD', 4, 'PCS',   4.20, '5901234123679', 'https://parts.example.com/ART023'),
  (24, 'ART024', 'ESP32-WROOM-32 module',               'STD', 4, 'PCS',   5.90, '5901234123686', 'https://parts.example.com/ART024'),
  (25, 'ART025', 'Raspberry Pi Pico',                   'STD', 4, 'PCS',   6.50, '5901234123693', 'https://parts.example.com/ART025'),
  (26, 'ART026', 'Arduino Nano clone',                  'STD', 4, 'PCS',   4.80, '5901234123709', 'https://parts.example.com/ART026'),
  -- Power
  (27, 'ART027', 'LM7805 5V regulator TO-220',          'STD', 5, 'PCS',   0.75, '5901234123716', 'https://parts.example.com/ART027'),
  (28, 'ART028', 'LM317 adjustable regulator',          'STD', 5, 'PCS',   0.85, '5901234123723', 'https://parts.example.com/ART028'),
  (29, 'ART029', 'DC-DC step-down module 3A',           'STD', 5, 'PCS',   3.20, '5901234123730', 'https://parts.example.com/ART029'),
  (30, 'ART030', '12V 2A switching power supply',       'STD', 5, 'PCS',  14.50, '5901234123747', 'https://parts.example.com/ART030'),
  -- Tools
  (31, 'ART031', 'Digital multimeter pocket',           'STD', 6, 'PCS',  18.00, '5901234123754', 'https://parts.example.com/ART031'),
  (32, 'ART032', 'Soldering iron 60W adjustable',       'STD', 6, 'PCS',  32.00, '5901234123761', 'https://parts.example.com/ART032'),
  (33, 'ART033', 'Breadboard 830 tie-points',           'STD', 6, 'PCS',   5.50, '5901234123778', 'https://parts.example.com/ART033'),
  -- Services
  (34, 'SRV001', 'Technical support',                   'SRV', 7, 'HRS',  85.00, NULL, NULL),
  (35, 'SRV002', 'Testing and certification',           'SRV', 7, 'HRS',  95.00, NULL, NULL),
  (36, 'SRV003', 'PCB design and layout',               'SRV', 7, 'HRS', 110.00, NULL, NULL),
  (37, 'SRV004', 'Firmware development',                'SRV', 7, 'HRS', 120.00, NULL, NULL),
  -- Kits
  (38, 'KIT001', 'STM32 development starter kit',       'KIT', 8, 'PCS',  38.00, '5901234123785', 'https://parts.example.com/KIT001'),
  (39, 'KIT002', 'Environmental sensors kit',           'KIT', 8, 'PCS',  52.00, '5901234123792', 'https://parts.example.com/KIT002'),
  (40, 'KIT003', 'ESP32 IoT prototyping kit',           'KIT', 8, 'PCS',  65.00, '5901234123808', 'https://parts.example.com/KIT003'),
  (41, 'KIT004', 'Power electronics learning kit',      'KIT', 8, 'PCS',  48.00, '5901234123815', 'https://parts.example.com/KIT004');

-- -----------------------------------------------------------------------
-- Movements  (subset of articles for demo purposes)
-- -----------------------------------------------------------------------
INSERT INTO movements VALUES
  -- ART001
  ( 1,  1, '2026-01-05', 'C', 500, 0.38, 'Purchase order PO2026/001'),
  ( 2,  1, '2026-01-20', 'S',  50, 0.45, NULL),
  ( 3,  1, '2026-02-03', 'S',  80, 0.45, NULL),
  ( 4,  1, '2026-03-01', 'C', 200, 0.37, 'Purchase order PO2026/018'),
  -- ART003
  ( 5,  3, '2026-01-05', 'C', 300, 0.38, 'Purchase order PO2026/001'),
  ( 6,  3, '2026-02-10', 'S',  40, 0.45, NULL),
  -- ART007
  ( 7,  7, '2026-01-05', 'C', 300, 0.70, 'Purchase order PO2026/001'),
  ( 8,  7, '2026-02-10', 'S',  40, 0.80, NULL),
  ( 9,  7, '2026-02-28', 'S',  60, 0.80, NULL),
  -- ART023
  (10, 23, '2026-01-10', 'C',  50, 3.90, 'Purchase order PO2026/005'),
  (11, 23, '2026-02-15', 'S',  10, 4.20, NULL),
  (12, 23, '2026-03-05', 'S',   8, 4.20, NULL),
  -- ART024
  (13, 24, '2026-01-15', 'C',  40, 5.20, NULL),
  (14, 24, '2026-02-20', 'S',  12, 5.90, NULL),
  (15, 24, '2026-03-08', 'S',   8, 5.90, 'Customer: Acme Ltd'),
  -- ART025
  (16, 25, '2026-01-18', 'C',  30, 5.80, NULL),
  (17, 25, '2026-02-22', 'S',   5, 6.50, NULL),
  -- SRV001
  (18, 34, '2026-01-22', 'S',   8, 85.00, 'Customer: Acme Ltd'),
  (19, 34, '2026-02-14', 'S',   4, 85.00, 'Customer: Beta Inc'),
  (20, 34, '2026-03-03', 'S',  12, 85.00, 'Customer: Acme Ltd'),
  -- SRV003
  (21, 36, '2026-02-05', 'S',  16, 110.00, 'Project: IoT gateway board'),
  (22, 36, '2026-03-12', 'S',   8, 110.00, 'Project: sensor node v2'),
  -- KIT001
  (23, 38, '2026-01-08', 'C',  20, 32.00, NULL),
  (24, 38, '2026-02-01', 'S',   5, 38.00, NULL),
  (25, 38, '2026-03-10', 'S',   3, 38.00, NULL),
  -- KIT003
  (26, 40, '2026-01-08', 'C',  15, 57.00, NULL),
  (27, 40, '2026-02-25', 'S',   4, 65.00, NULL),
  (28, 40, '2026-03-15', 'S',   6, 65.00, 'Customer: Beta Inc');
