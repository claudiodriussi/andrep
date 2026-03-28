/**
 * run-cli.ts — CLI runner for the products catalog demo.
 *
 * Loads the template, runs the loop engine, calls the Python renderer
 * via CLI subprocess, and writes HTML + PDF to examples/output/.
 *
 * Usage (from clients/js/):
 *   npx tsx examples/run-cli.ts
 *   npx tsx examples/run-cli.ts --html-only
 */

import { writeFileSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join, dirname } from "node:path";
import { FilesystemLoader } from "../src/loader.js";
import { callAndrep } from "../src/cli.js";
import { buildEngine, engineMetadata } from "./loop.js";

const __dir = dirname(fileURLToPath(import.meta.url));
const TEMPLATES = join(__dir, "../../templates");
const OUTPUT = join(__dir, "output");
const HTML_ONLY = process.argv.includes("--html-only");

mkdirSync(OUTPUT, { recursive: true });

const loader = new FilesystemLoader(TEMPLATES, { lang: "js" });
const template = loader.load("products");
const engine = buildEngine(template);
const records = engine.getRecords();
const metadata = engineMetadata(engine);

console.log(`Compiled ${records.length} records for ${engine.articleCount} products`);
console.log(`Grand total: € ${engine.grandTotal.toFixed(2)}`);

// Write records JSON for inspection
const recordsPath = join(OUTPUT, "products-records.json");
writeFileSync(recordsPath, JSON.stringify(records, null, 2), "utf-8");
console.log(`Records saved → ${recordsPath}`);

// HTML
console.log("Rendering HTML...");
const htmlBuf = await callAndrep({
  template: "products",
  templateDir: TEMPLATES,
  records,
  metadata,
  format: "html",
});
const htmlPath = join(OUTPUT, "products.html");
writeFileSync(htmlPath, htmlBuf);
console.log(`HTML saved → ${htmlPath}`);

// PDF
if (!HTML_ONLY) {
  console.log("Rendering PDF...");
  const pdfBuf = await callAndrep({
    template: "products",
    templateDir: TEMPLATES,
    records,
    metadata,
    format: "pdf",
  });
  const pdfPath = join(OUTPUT, "products.pdf");
  writeFileSync(pdfPath, pdfBuf);
  console.log(`PDF saved → ${pdfPath}`);
}
