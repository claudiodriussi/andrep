/**
 * engine.ts — AndRepEngine: loop engine that produces compiled records.
 *
 * Usage:
 *
 *   class MyReport extends AndRepEngine {
 *     private total = 0;
 *
 *     override onAfterBand(band: string, ctx: Ctx) {
 *       if (band === "band") this.total += (ctx.row as any).price;
 *     }
 *   }
 *
 *   const engine = new MyReport(template);
 *   for (const row of rows) engine.emit("band", { row });
 *   engine.emit("totals", { total: engine.total });
 *
 *   const records = engine.getRecords();   // → JSON array for Python renderer
 */

import type { Template, Row, Token, CompiledRecord, ScalarValue, EngineState } from "./types.js";
import { parseTokens, evalExpr } from "./expression.js";
import { applyFormatter, type FormatterFn } from "./formatters.js";

/** Caller-provided context: named variables accessible in template expressions. */
export type Ctx = Record<string, unknown>;

// Band names handled automatically by the Python renderer — never emit these.
const PAGE_ROLES = new Set([
  "first_header",
  "page_header",
  "page_footer",
  "last_footer",
  "page_filler",
]);

function todayStr(): string {
  const d = new Date();
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const yyyy = d.getFullYear();
  return `${dd}/${mm}/${yyyy}`;
}

function nowStr(): string {
  const d = new Date();
  return d.toTimeString().slice(0, 8); // HH:MM:SS
}

function currentUser(): string {
  try {
    // Node.js only
    return (process.env["USER"] ?? process.env["USERNAME"] ?? "").trim() || "unknown";
  } catch {
    return "unknown";
  }
}

export class AndRepEngine {
  // -------------------------------------------------------------------------
  // Public state — readable in template expressions as _r.*
  //
  // The intersection with Record<string,unknown> allows setting arbitrary
  // metadata (e.g. engine.state.name = ["Acme", "Rome"]) so that templates
  // like stdhdr.json can use [_r.name[0]] — identical to Python's r.name = ...
  // -------------------------------------------------------------------------

  readonly state: EngineState & Record<string, unknown> = {
    curBand: "",
    lastBand: "",
    started: false,
    count: 0,
    bandCount: {},
    title: "",
    date: todayStr(),
    time: nowStr(),
    user: currentUser(),
  };

  /**
   * Workspace — set values accessible in all expressions (like Python's r["key"]).
   * Use: engine.globals.reportTitle = "Sales Q1"
   */
  globals: Ctx = {};

  /**
   * Custom formatters — applied before built-ins.
   * fn(value, fmtString) → any
   */
  formatters: Record<string, FormatterFn> = {};

  // -------------------------------------------------------------------------
  // Private
  // -------------------------------------------------------------------------

  protected readonly template: Template;

  /** band name → Row[] */
  private readonly bands: Map<string, Row[]>;

  /** cell.id → Token[] (pre-parsed at construction) */
  private readonly cellTokens: Map<string, Token[]>;

  private readonly emissions: CompiledRecord[] = [];

  // Per-emit patch state (reset after each emit)
  private _bandCss = "";
  private _cellPatches: Map<string, string> = new Map(); // content_match → cssExtra

  constructor(template: Template) {
    this.template = template;
    this.state.title = template.name ?? "";

    // Group rows by band name
    this.bands = new Map();
    for (const row of template.rows ?? []) {
      if (!this.bands.has(row.name)) this.bands.set(row.name, []);
      this.bands.get(row.name)!.push(row);
    }

    // Pre-parse tokens for every cell
    this.cellTokens = new Map();
    for (const row of template.rows ?? []) {
      for (const cell of row.cells ?? []) {
        this.cellTokens.set(cell.id, parseTokens(cell.content ?? ""));
      }
    }

    this.onInit();
  }

  // -------------------------------------------------------------------------
  // Hooks — override in subclass
  // -------------------------------------------------------------------------

  /** Called once at construction time. */
  // eslint-disable-next-line @typescript-eslint/no-empty-function
  onInit(): void {}

  /** Called before the first emit(). */
  // eslint-disable-next-line @typescript-eslint/no-empty-function
  onBefore(): void {}

  /**
   * Called before each emit(), after ctx is set.
   * Call patchBand() / patch() here.
   */
  // eslint-disable-next-line @typescript-eslint/no-empty-function
  onBeforeBand(_band: string, _ctx: Ctx): void {}

  /**
   * Called after each emit().
   * Accumulate totals here (ctx is the same object passed to emit).
   */
  // eslint-disable-next-line @typescript-eslint/no-empty-function
  onAfterBand(_band: string, _ctx: Ctx): void {}

  /** Called by getRecords() before serialisation. */
  // eslint-disable-next-line @typescript-eslint/no-empty-function
  onAfter(): void {}

  // -------------------------------------------------------------------------
  // Emit
  // -------------------------------------------------------------------------

  /**
   * Emit a band with the given context.
   *
   * @param band    - Band name (must exist in the template).
   * @param ctx     - Named variables accessible in template expressions.
   * @param silent  - If true, fire hooks without recording the emission.
   */
  emit(band: string, ctx: Ctx = {}, silent = false): void {
    if (PAGE_ROLES.has(band)) {
      throw new Error(
        `emit("${band}"): page-role bands are managed automatically by the Python renderer. Do not emit them.`
      );
    }

    if (!this.state.started) {
      this.state.started = true;
      this.onBefore();
    }

    this.onBeforeBand(band, ctx);

    if (!silent) {
      const ns = this._buildNs(band, ctx);
      this.emissions.push(this._compileBand(band, ns));
    }

    this._bandCss = "";
    this._cellPatches = new Map();

    this.state.lastBand = this.state.curBand;
    this.state.curBand = band;
    this.state.count++;
    this.state.bandCount[band] = (this.state.bandCount[band] ?? 0) + 1;

    this.onAfterBand(band, ctx);
  }

  /** Insert an explicit page break marker into the record stream. */
  pageBreak(): void {
    this.emissions.push({ band: "__page_break__" });
  }

  // -------------------------------------------------------------------------
  // Patch helpers (call from onBeforeBand)
  // -------------------------------------------------------------------------

  /** Apply cssExtra to all cells of the current band emission. */
  patchBand(css: string): void {
    this._bandCss = css;
  }

  /**
   * Apply cssExtra to cells whose content contains contentMatch.
   * Multiple calls accumulate — last write wins per match.
   */
  patch(contentMatch: string, css: string): void {
    this._cellPatches.set(contentMatch, css);
  }

  // -------------------------------------------------------------------------
  // Query
  // -------------------------------------------------------------------------

  hasBand(name: string): boolean {
    return this.bands.has(name) && (this.bands.get(name)?.length ?? 0) > 0;
  }

  // -------------------------------------------------------------------------
  // Output
  // -------------------------------------------------------------------------

  /**
   * Return the compiled records array (call after all emit() calls).
   * Pass this to callAndrep() or POST to a REST endpoint.
   */
  getRecords(): CompiledRecord[] {
    this.onAfter();
    return this.emissions;
  }

  // -------------------------------------------------------------------------
  // Internal — namespace and compilation
  // -------------------------------------------------------------------------

  private _buildNs(band: string, ctx: Ctx): Ctx {
    // Build _r as a snapshot of state with curBand updated.
    // Record<string,unknown> spread includes arbitrary metadata set by the caller
    // (e.g. state.name = ["Acme", ...]) — mirrors Python's renderer attributes.
    const _r = { ...this.state, curBand: band };

    // Expose the same top-level system variables as the Python renderer:
    // _name, _date, _time, _user, _page — templates can use either form.
    return {
      ...this.globals,
      ...ctx,
      _r,
      _name: this.state.title,
      _date: this.state.date,
      _time: this.state.time,
      _user: this.state.user,
      _page: 1,  // pagination is handled by the Python renderer
    };
  }

  private _compileBand(bandName: string, ns: Ctx): CompiledRecord {
    const rows = this.bands.get(bandName) ?? [];
    const values: ScalarValue[] = [];
    const cssExtras: string[] = [];
    const embeds: Record<string, CompiledRecord> = {};

    for (const row of rows) {
      for (const cell of row.cells ?? []) {
        if (cell.type === "embed") {
          const target = cell.embedTarget ?? "";
          if (target && this.bands.has(target)) {
            embeds[cell.id] = this._compileBand(target, ns);
          }
          // embed cells contribute no values, but do contribute a cssExtra slot
        } else {
          const tokens = this.cellTokens.get(cell.id) ?? [];
          for (const tok of tokens) {
            if (tok.expr !== null) {
              let val = evalExpr(tok.expr, ns);
              // Apply only JS-registered formatters; Python handles the rest.
              for (const fmt of tok.fmts) {
                val = applyFormatter(val, fmt, this.formatters);
              }
              values.push(val as ScalarValue);
            }
          }
        }

        // cssExtra — static or @-expression
        let cellCss = cell.cssExtra ?? "";
        if (cellCss.startsWith("@")) {
          const res = evalExpr(cellCss.slice(1), ns);
          cellCss = res ? String(res) : "";
        }
        // Apply patch() overrides
        const content = cell.content ?? "";
        for (const [match, patchCss] of this._cellPatches) {
          if (content.includes(match)) {
            cellCss = cellCss ? `${cellCss};${patchCss}` : patchCss;
          }
        }
        cssExtras.push(cellCss);
      }
    }

    const record: CompiledRecord = { band: bandName };
    if (values.length > 0) record.values = values;
    if (this._bandCss || cssExtras.some(Boolean)) {
      record.css_extras = cssExtras;
      record.band_css = this._bandCss;
    }
    if (Object.keys(embeds).length > 0) record.embeds = embeds;

    return record;
  }
}
