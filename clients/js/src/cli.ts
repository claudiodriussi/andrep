/**
 * cli.ts — Helpers to invoke the AndRep Python renderer.
 *
 * Node.js only.
 *
 * Two transports available:
 *   - callAndrep()     — CLI subprocess (python -m andrep render)
 *   - callAndrepRest() — REST endpoint (POST /render on a running server)
 *
 * Example (CLI):
 *
 *   const pdf = await callAndrep({
 *     template: "sells",
 *     templateDir: "/path/to/templates",
 *     records: engine.getRecords(),
 *     format: "pdf",
 *   });
 *   fs.writeFileSync("report.pdf", pdf);
 *
 * Example (REST):
 *
 *   const pdf = await callAndrepRest({
 *     serverUrl: "http://localhost:5000",
 *     template: "sells",
 *     records: engine.getRecords(),
 *     format: "pdf",
 *   });
 *   fs.writeFileSync("report.pdf", pdf);
 */

import { spawn } from "node:child_process";
import type { CompiledRecord } from "./types.js";

export interface CallAndrepOptions {
  /** Template name (resolved by --template-dir) or absolute path to .json. */
  template: string;
  /** Compiled records produced by AndRepEngine.getRecords(). */
  records: CompiledRecord[];
  /** Output format. Default: "html". */
  format?: "html" | "pdf";
  /** Directory where the Python renderer looks for templates. */
  templateDir?: string;
  /**
   * Renderer metadata passed as --meta JSON to the Python renderer.
   * Used to set renderer attributes accessible in page_role band expressions:
   *   title  → [_r.title]   (report title)
   *   name   → [_r.name[0]] (company info array, as in stdhdr.json)
   *   Any other attribute settable on AndRepRenderer.
   */
  metadata?: Record<string, unknown>;
  /** Python executable. Default: "python3". */
  python?: string;
}

export interface CallAndrepRestOptions {
  /** Base URL of the AndRep REST server (Flask or FastAPI). */
  serverUrl: string;
  /** Template name (must be available in the server's template-dir). */
  template: string;
  /** Compiled records produced by AndRepEngine.getRecords(). */
  records: CompiledRecord[];
  /** Output format. Default: "html". */
  format?: "html" | "pdf";
  /** Renderer metadata (title, name, ...) — same semantics as CLI --meta. */
  metadata?: Record<string, unknown>;
}

/**
 * Run `python -m andrep render` with the given compiled records.
 *
 * Records are written to the renderer's stdin (--records -).
 * Output is collected from stdout and returned as a Buffer.
 *
 * The Python renderer must be on PYTHONPATH (set PYTHONPATH or use
 * call_andrep.sh which handles this automatically).
 */
export function callAndrep(opts: CallAndrepOptions): Promise<Buffer> {
  const {
    template,
    records,
    format = "html",
    templateDir,
    metadata,
    python = "python3",
  } = opts;

  const args = [
    "-m", "andrep", "render",
    "--template", template,
    "--records", "-",      // read from stdin
    "--output",  "-",      // write to stdout
    "--format",  format,
  ];
  if (templateDir) args.push("--template-dir", templateDir);
  if (metadata)    args.push("--meta", JSON.stringify(metadata));

  return new Promise((resolve, reject) => {
    const child = spawn(python, args, { stdio: ["pipe", "pipe", "pipe"] });

    const chunks: Buffer[] = [];
    const errChunks: Buffer[] = [];

    child.stdout.on("data", (chunk: Buffer) => chunks.push(chunk));
    child.stderr.on("data", (chunk: Buffer) => errChunks.push(chunk));

    child.on("error", reject);

    child.on("close", (code) => {
      if (code !== 0) {
        const stderr = Buffer.concat(errChunks).toString("utf-8");
        reject(new Error(`andrep renderer exited with code ${code}:\n${stderr}`));
        return;
      }
      resolve(Buffer.concat(chunks));
    });

    // Write records to stdin and close it
    const json = JSON.stringify(records, null, 2);
    child.stdin.write(json, "utf-8", (err) => {
      if (err) reject(err);
      else child.stdin.end();
    });
  });
}

/**
 * Call the AndRep REST server (POST /render) and return the output as a Buffer.
 *
 * Compatible with both server_flask.py and server_fastapi.py.
 * The server must have the requested template available in its template-dir.
 */
export async function callAndrepRest(opts: CallAndrepRestOptions): Promise<Buffer> {
  const { serverUrl, template, records, format = "html", metadata } = opts;

  const url = serverUrl.replace(/\/$/, "") + "/render";
  const body = JSON.stringify({ template, records, format, metadata });

  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "(no body)");
    throw new Error(`AndRep REST server returned ${res.status}: ${text}`);
  }

  const arrayBuf = await res.arrayBuffer();
  return Buffer.from(arrayBuf);
}
