/**
 * call-server.ts — REST runner for the products catalog demo.
 *
 * Loads the template, runs the loop engine, calls the Python renderer
 * via REST (Flask or FastAPI), and writes HTML + PDF to examples/output/.
 *
 * The Python server must be running first:
 *   ./clients/server/run.sh flask   --template-dir clients/js/examples/templates
 *   ./clients/server/run.sh fastapi --template-dir clients/js/examples/templates
 *
 * Usage (from clients/js/):
 *   npx tsx examples/call-server.ts
 *   npx tsx examples/call-server.ts --html-only
 *   npx tsx examples/call-server.ts --server http://localhost:5000
 */

import { writeFileSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join, dirname } from "node:path";
import { FilesystemLoader } from "../src/loader.js";
import { callAndrepRest } from "../src/cli.js";
import { buildEngine, engineMetadata } from "./loop.js";

const __dir = dirname(fileURLToPath(import.meta.url));
const TEMPLATES = join(__dir, "templates");
const OUTPUT = join(__dir, "output");

const HTML_ONLY  = process.argv.includes("--html-only");
const serverArg  = process.argv.indexOf("--server");
const SERVER_URL = serverArg !== -1 ? process.argv[serverArg + 1] : "http://localhost:5000";

mkdirSync(OUTPUT, { recursive: true });

const loader = new FilesystemLoader(TEMPLATES);
const template = loader.load("products");
const engine = buildEngine(template);
const records = engine.getRecords();
const metadata = engineMetadata(engine);

console.log(`Server: ${SERVER_URL}`);
console.log(`Compiled ${records.length} records for ${engine.articleCount} products`);
console.log(`Grand total: € ${engine.grandTotal.toFixed(2)}`);

// HTML
console.log("Rendering HTML...");
const htmlBuf = await callAndrepRest({ serverUrl: SERVER_URL, template: "products", records, metadata, format: "html" });
const htmlPath = join(OUTPUT, "products-rest.html");
writeFileSync(htmlPath, htmlBuf);
console.log(`HTML saved → ${htmlPath}`);

// PDF
if (!HTML_ONLY) {
  console.log("Rendering PDF...");
  const pdfBuf = await callAndrepRest({ serverUrl: SERVER_URL, template: "products", records, metadata, format: "pdf" });
  const pdfPath = join(OUTPUT, "products-rest.pdf");
  writeFileSync(pdfPath, pdfBuf);
  console.log(`PDF saved → ${pdfPath}`);
}
