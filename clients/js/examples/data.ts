/**
 * data.ts — Hardcoded product catalog for the AndRep JS client demo.
 *
 * Same data is used by the CLI runner and the REST server.
 */

// EAN-13 check digit calculator
function ean13(base12: string): string {
  let sum = 0;
  for (let i = 0; i < 12; i++) {
    sum += parseInt(base12[i]) * (i % 2 === 0 ? 1 : 3);
  }
  return base12 + ((10 - (sum % 10)) % 10);
}

// Small SVG thumbnail — solid color + code label (self-contained, no external URLs)
function thumb(code: string, bg: string, fg = "#555"): string {
  const label = code.slice(0, 6);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="60" height="60"><rect width="60" height="60" fill="${bg}" rx="4"/><text x="30" y="38" font-size="9" font-family="Arial" text-anchor="middle" fill="${fg}">${label}</text></svg>`;
  return `data:image/svg+xml;base64,${Buffer.from(svg).toString("base64")}`;
}

export interface Product {
  code: string;
  desc: string;
  brand: string;      // stored lowercase to demonstrate capitalize formatter
  category: string;
  qty: number;
  price: number;
  ean: string;
  img: string;        // SVG data URI thumbnail
}

export const PRODUCTS: Product[] = [
  {
    code: "ELE-001",
    desc: "STM32 Nucleo-64 development board — ARM Cortex-M4 @ 84 MHz, 512KB Flash",
    brand: "stmicroelectronics",
    category: "ELE",
    qty: 42,
    price: 14.90,
    ean: ean13("590123412378"),
    img: thumb("ELE-001", "#dbeafe", "#1d4ed8"),
  },
  {
    code: "ELE-002",
    desc: "10 Ω resistor 1/4W 5% (pack of 100)",
    brand: "vishay",
    category: "ELE",
    qty: 850,
    price: 0.45,
    ean: ean13("590123412345"),
    img: thumb("ELE-002", "#dbeafe", "#1d4ed8"),
  },
  {
    code: "ELE-003",
    desc: "100 nF ceramic capacitor 50V X7R (pack of 50)",
    brand: "kemet",
    category: "ELE",
    qty: 320,
    price: 1.20,
    ean: ean13("590123412352"),
    img: thumb("ELE-003", "#dbeafe", "#1d4ed8"),
  },
  {
    code: "KIT-001",
    desc: "Arduino Starter Kit — includes Uno R3, breadboard, jumpers, components",
    brand: "arduino",
    category: "KIT",
    qty: 18,
    price: 38.00,
    ean: ean13("590123412369"),
    img: thumb("KIT-001", "#dcfce7", "#15803d"),
  },
  {
    code: "KIT-002",
    desc: "Raspberry Pi 5 Starter Kit — Pi 5 4GB, case, PSU, 32GB microSD, heatsink",
    brand: "raspberry pi ltd",
    category: "KIT",
    qty: 9,
    price: 109.90,
    ean: ean13("590123412376"),
    img: thumb("KIT-002", "#dcfce7", "#15803d"),
  },
  {
    code: "MECH-001",
    desc: "M3 × 10mm hex socket cap screws stainless steel (pack of 50)",
    brand: "würth elektronik",
    category: "MECH",
    qty: 200,
    price: 3.50,
    ean: ean13("590123412383"),
    img: thumb("MECH-001", "#fef9c3", "#a16207"),
  },
  {
    code: "MECH-002",
    desc: "DIN rail 35mm × 1000mm — galvanised steel TS 35",
    brand: "phoenix contact",
    category: "MECH",
    qty: 25,
    price: 8.70,
    ean: ean13("590123412390"),
    img: thumb("MECH-002", "#fef9c3", "#a16207"),
  },
  {
    code: "OPT-001",
    desc: "5mm green LED 560nm 2500 mcd 30° viewing angle (pack of 20)",
    brand: "kingbright",
    category: "OPT",
    qty: 500,
    price: 2.80,
    ean: ean13("590123412406"),
    img: thumb("OPT-001", "#f3e8ff", "#7e22ce"),
  },
  {
    code: "OPT-002",
    desc: "0.96\" OLED display 128×64 I2C SSD1306 — white on black",
    brand: "waveshare",
    category: "OPT",
    qty: 30,
    price: 6.50,
    ean: ean13("590123412413"),
    img: thumb("OPT-002", "#f3e8ff", "#7e22ce"),
  },
  {
    code: "OPT-003",
    desc: "IR obstacle avoidance sensor module — adjustable distance 2–30 cm",
    brand: "generic",
    category: "OPT",
    qty: 75,
    price: 1.90,
    ean: ean13("590123412420"),
    img: thumb("OPT-003", "#f3e8ff", "#7e22ce"),
  },
];

export const COMPANY_INFO = [
  "ACME Electronics & Components Srl",
  "Via Industriale 42, 20100 Milano MI",
  "info@acme-electronics.example",
  "P.IVA: IT00000000001",
];
