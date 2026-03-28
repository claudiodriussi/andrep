/**
 * server-rest.ts — AndRep demo Node server using a remote Python renderer.
 *
 * Identical to server.ts but delegates rendering to an external Python
 * REST server (Flask or FastAPI) instead of spawning a CLI subprocess.
 *
 * Start the Python server first:
 *   ./clients/server/run.sh flask   --template-dir clients/templates
 *   ./clients/server/run.sh fastapi --template-dir clients/templates
 *
 * Then start this server (from clients/js/):
 *   npx tsx examples/server-rest.ts
 *   RENDERER_URL=http://localhost:5000 npx tsx examples/server-rest.ts
 *   # then open http://localhost:3000
 *
 * Routes:
 *   GET /                      → index.html (browser UI)
 *   GET /report?format=html    → HTML report (inline preview)
 *   GET /report?format=pdf     → PDF (inline, saveable from browser)
 *   GET /records               → raw compiled records JSON (debug)
 */

import http from "node:http";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join, dirname } from "node:path";
import { FilesystemLoader } from "../src/loader.js";
import { callAndrepRest } from "../src/cli.js";
import { buildEngine, engineMetadata } from "./loop.js";

const PORT         = parseInt(process.env["PORT"]         ?? "3000", 10);
const RENDERER_URL = process.env["RENDERER_URL"] ?? "http://localhost:5000";

const __dir    = dirname(fileURLToPath(import.meta.url));
const TEMPLATES = join(__dir, "../../templates");
const PUBLIC    = join(__dir, "public");

// Load template once at startup (templates don't change at runtime)
const loader   = new FilesystemLoader(TEMPLATES, { lang: "js" });
const template = loader.load("products");

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url ?? "/", `http://localhost:${PORT}`);

  // -------------------------------------------------------------------------
  // GET / — browser UI
  // -------------------------------------------------------------------------
  if (url.pathname === "/" && req.method === "GET") {
    try {
      const html = readFileSync(join(PUBLIC, "index.html"), "utf-8");
      res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
      res.end(html);
    } catch {
      res.writeHead(500);
      res.end("Could not load index.html");
    }
    return;
  }

  // -------------------------------------------------------------------------
  // GET /report?format=html|pdf — rendered report
  // -------------------------------------------------------------------------
  if (url.pathname === "/report" && req.method === "GET") {
    const format = url.searchParams.get("format") === "pdf" ? "pdf" : "html";
    try {
      const engine   = buildEngine(template);
      const records  = engine.getRecords();
      const metadata = engineMetadata(engine);

      // Hand off compiled records + metadata to the remote Python renderer
      const output = await callAndrepRest({ serverUrl: RENDERER_URL, template: "products", records, metadata, format });

      if (format === "pdf") {
        res.writeHead(200, {
          "Content-Type": "application/pdf",
          "Content-Disposition": "inline; filename=products.pdf",
          "Content-Length": output.length,
        });
      } else {
        res.writeHead(200, {
          "Content-Type": "text/html; charset=utf-8",
          "Content-Length": output.length,
        });
      }
      res.end(output);
    } catch (err) {
      console.error("Render error:", err);
      res.writeHead(500, { "Content-Type": "text/plain; charset=utf-8" });
      res.end(`Render error:\n${err}`);
    }
    return;
  }

  // -------------------------------------------------------------------------
  // GET /records — raw compiled records (useful for debugging / inspection)
  // -------------------------------------------------------------------------
  if (url.pathname === "/records" && req.method === "GET") {
    const engine  = buildEngine(template);
    const records = engine.getRecords();
    const json    = JSON.stringify(records, null, 2);
    res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
    res.end(json);
    return;
  }

  res.writeHead(404, { "Content-Type": "text/plain" });
  res.end("Not found");
});

server.listen(PORT, () => {
  console.log(`AndRep demo server →  http://localhost:${PORT}`);
  console.log(`  renderer         →  ${RENDERER_URL}`);
  console.log(`  HTML report      →  http://localhost:${PORT}/report?format=html`);
  console.log(`  PDF report       →  http://localhost:${PORT}/report?format=pdf`);
  console.log(`  Compiled records →  http://localhost:${PORT}/records`);
});
