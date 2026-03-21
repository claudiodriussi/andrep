/**
 * loader.ts — Template loader with composition support.
 *
 * Mirrors renderer/andrep/loader.py (FilesystemLoader) and the
 * load_template() composition logic in renderer.py.
 *
 * Node.js only (uses fs and path).
 */

import { readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import type { Template } from "./types.js";

// ---------------------------------------------------------------------------
// Protocol
// ---------------------------------------------------------------------------

export interface TemplateLoader {
  /**
   * Load a template by name and apply composition rules.
   * Throws if the template is not found.
   */
  load(name: string): Template;
}

// ---------------------------------------------------------------------------
// FilesystemLoader
// ---------------------------------------------------------------------------

/**
 * Loads templates from the filesystem and applies composition rules.
 *
 * Search order (identical to Python FilesystemLoader):
 *   1. customDir/<name>.json  (local overrides)
 *   2. baseDir/<name>.json    (standard templates)
 *
 * @param baseDir   - Base directory for standard templates.
 * @param customDir - Optional override directory (default: baseDir/custom).
 */
export class FilesystemLoader implements TemplateLoader {
  private readonly baseDir: string;
  private readonly customDir: string;

  constructor(baseDir: string, customDir?: string) {
    this.baseDir = resolve(baseDir);
    this.customDir = customDir ? resolve(customDir) : join(this.baseDir, "custom");
  }

  load(name: string): Template {
    const tmpl = this._loadRaw(name);
    return this._applyComposition(tmpl);
  }

  // -------------------------------------------------------------------------
  // Internal
  // -------------------------------------------------------------------------

  private _loadRaw(name: string): Template {
    const filename = name.endsWith(".json") ? name : `${name}.json`;
    const candidates = [
      join(this.customDir, filename),
      join(this.baseDir, filename),
    ];
    for (const p of candidates) {
      try {
        const text = readFileSync(p, "utf-8");
        return JSON.parse(text) as Template;
      } catch {
        // try next
      }
    }
    throw new Error(`Template not found: "${name}" (searched ${candidates.join(", ")})`);
  }

  private _applyComposition(tmpl: Template): Template {
    const rules = tmpl.composition ?? [];
    if (rules.length === 0) return tmpl;

    // Work on a shallow copy — rows array is replaced, not mutated in-place
    let result = { ...tmpl, rows: [...(tmpl.rows ?? [])] };

    for (const comp of rules) {
      const rule = comp.rule.toLowerCase().replace(/[_-]/g, "");
      const target = comp.target;
      if (!target) continue;

      let refTmpl: Template;
      try {
        refTmpl = this._loadRaw(target); // targets are NOT further composed (1 level)
      } catch {
        continue; // missing target → skip (same as Python)
      }

      const refRows = refTmpl.rows ?? [];
      const mainRows = result.rows;

      if (rule === "insbefore" || rule === "insertbefore") {
        const refBands = _groupByName(refRows);
        const newRows: typeof mainRows = [];
        const inserted = new Set<string>();
        for (const row of mainRows) {
          if (refBands.has(row.name) && !inserted.has(row.name)) {
            newRows.push(...refBands.get(row.name)!);
            inserted.add(row.name);
          }
          newRows.push(row);
        }
        for (const [name, rows] of refBands) {
          if (!inserted.has(name)) newRows.unshift(...rows);
        }
        result = { ...result, rows: newRows };

      } else if (rule === "insafter" || rule === "insertafter") {
        const refBands = _groupByName(refRows);
        const newRows: typeof mainRows = [];
        const inserted = new Set<string>();
        for (const row of mainRows) {
          newRows.push(row);
          if (refBands.has(row.name) && !inserted.has(row.name)) {
            newRows.push(...refBands.get(row.name)!);
            inserted.add(row.name);
          }
        }
        for (const [name, rows] of refBands) {
          if (!inserted.has(name)) newRows.push(...rows);
        }
        result = { ...result, rows: newRows };

      } else if (rule === "replace") {
        const refBands = _groupByName(refRows);
        const seen = new Set<string>();
        const newRows: typeof mainRows = [];
        for (const row of mainRows) {
          if (refBands.has(row.name)) {
            if (!seen.has(row.name)) {
              newRows.push(...refBands.get(row.name)!);
              seen.add(row.name);
            }
          } else {
            newRows.push(row);
          }
        }
        result = { ...result, rows: newRows };

      } else if (rule === "ifnot") {
        const existingNames = new Set(mainRows.map((r) => r.name));
        const toAdd = refRows.filter((r) => !existingNames.has(r.name));
        result = { ...result, rows: [...mainRows, ...toAdd] };
      }
    }

    // Remove composition key from the resolved template
    const { composition: _removed, ...clean } = result as Template & { composition?: unknown };
    void _removed;
    return clean as Template;
  }
}

function _groupByName<T extends { name: string }>(rows: T[]): Map<string, T[]> {
  const map = new Map<string, T[]>();
  for (const row of rows) {
    if (!map.has(row.name)) map.set(row.name, []);
    map.get(row.name)!.push(row);
  }
  return map;
}
