/**
 * loop.ts — Shared loop engine for the products catalog demo.
 *
 * Both the CLI runner and the REST server call buildEngine() to get
 * a ready-to-use AndRepEngine with all records compiled.
 *
 * The same loop logic can be adapted to accept data from a database,
 * REST API, or any other source — data.ts is the only thing that changes.
 */

import { AndRepEngine } from "../src/engine.js";
import type { Ctx } from "../src/engine.js";
import type { Template } from "../src/types.js";
import { PRODUCTS, COMPANY_INFO } from "./data.js";

/** Metadata to pass to the Python renderer (for page_role band expressions). */
export function engineMetadata(engine: AndRepEngine): Record<string, unknown> {
  return {
    title: engine.state.title,
    name: COMPANY_INFO,   // used by stdhdr: [_r.name[0]], [_r.name[1]], ...
  };
}

class ProductsEngine extends AndRepEngine {
  private totalValue = 0;
  private count = 0;

  override onAfterBand(band: string, ctx: Ctx): void {
    if (band === "band") {
      const row = ctx["row"] as { price: number; qty: number };
      this.totalValue += row.price * row.qty;
      this.count++;
    }
  }

  override onBeforeBand(band: string, _ctx: Ctx): void {
    if (band === "band") {
      // Zebra striping: odd rows get a light gray background
      if (this.state.bandCount["band"] !== undefined && this.state.bandCount["band"] % 2 === 1) {
        this.patchBand("background:#f9fafb");
      }
    }
  }

  get grandTotal(): number { return this.totalValue; }
  get articleCount(): number { return this.count; }
}

/**
 * Build and run the products engine.
 * Returns the engine after all emit() calls — call getRecords() on it.
 */
export function buildEngine(template: Template): ProductsEngine {
  const engine = new ProductsEngine(template);

  // Metadata — accessible as _r.title, _r.name in template expressions
  engine.state.title = "Products Catalog";
  engine.state.name = COMPANY_INFO;  // used by stdhdr: [_r.name[0]], [_r.name[1]], ...

  // Header row
  engine.emit("col_header");

  // Data rows
  for (const row of PRODUCTS) {
    engine.emit("band", { row });
  }

  // Totals
  const totals = {
    count: engine.articleCount,
    value: engine.grandTotal,
  };
  engine.emit("totals", { totals });

  return engine;
}
