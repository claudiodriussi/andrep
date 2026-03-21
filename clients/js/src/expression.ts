/**
 * expression.ts — Token parser and expression evaluator.
 *
 * Mirrors renderer/andrep/variables.py: _parse_tokens, _split_token, eval_expr.
 */

import type { Token } from "./types.js";

// ---------------------------------------------------------------------------
// Token parser
// ---------------------------------------------------------------------------

/**
 * Split token content into (expr, formatters[]).
 *
 * Rules (identical to Python):
 *   1. If \| present → everything before it is the expr
 *   2. Otherwise: first single | (not part of ||) is the separator
 */
function splitToken(token: string): [string, string[]] {
  const escaped = "\\" + "|";
  if (token.includes(escaped)) {
    const idx = token.indexOf(escaped);
    const expr = token.slice(0, idx);
    const rest = token.slice(idx + 2);
    const fmts = rest.split("|").map((f) => f.trim()).filter(Boolean);
    return [expr.trim(), fmts];
  }

  for (let i = 0; i < token.length; i++) {
    if (token[i] === "|") {
      const prevPipe = i > 0 && token[i - 1] === "|";
      const nextPipe = i + 1 < token.length && token[i + 1] === "|";
      if (!prevPipe && !nextPipe) {
        const expr = token.slice(0, i).trim();
        const rest = token.slice(i + 1);
        const fmts = rest.split("|").map((f) => f.trim()).filter(Boolean);
        return [expr, fmts];
      }
    }
  }

  return [token.trim(), []];
}

/**
 * Parse a content string into a flat list of Token objects.
 *
 * - { text, expr: null, fmts: [] } — pure literal
 * - { text, expr, fmts }           — variable token (text = literal before it)
 *
 * Handles nested brackets (depth tracking).
 */
export function parseTokens(content: string): Token[] {
  const result: Token[] = [];
  let i = 0;
  let currentText: string[] = [];

  while (i < content.length) {
    if (content[i] === "[") {
      let depth = 1;
      let j = i + 1;
      while (j < content.length && depth > 0) {
        if (content[j] === "[") depth++;
        else if (content[j] === "]") depth--;
        j++;
      }

      if (depth === 0) {
        const text = currentText.join("");
        currentText = [];
        const tokenStr = content.slice(i + 1, j - 1);
        const [expr, fmts] = splitToken(tokenStr);
        result.push({ text, expr, fmts });
        i = j;
      } else {
        // Unclosed bracket — literal
        currentText.push(content[i]);
        i++;
      }
    } else {
      currentText.push(content[i]);
      i++;
    }
  }

  if (currentText.length > 0) {
    result.push({ text: currentText.join(""), expr: null, fmts: [] });
  }

  return result;
}

// ---------------------------------------------------------------------------
// Expression evaluator
// ---------------------------------------------------------------------------

/**
 * Evaluate expr in the given context (top-level keys become local names).
 *
 * Uses new Function() — safe for trusted server-side code where the template
 * is controlled by the developer, not end users.
 *
 * Returns null on ZeroDivisionError-equivalent (caught as Infinity/NaN check),
 * or "[#expr#]" marker string on other errors (matches Python behaviour).
 */
export function evalExpr(expr: string, ctx: Record<string, unknown>): unknown {
  try {
    const keys = Object.keys(ctx);
    const vals = keys.map((k) => ctx[k]);
    // eslint-disable-next-line @typescript-eslint/no-implied-eval
    const fn = new Function(...keys, `"use strict"; return (${expr});`) as (
      ...args: unknown[]
    ) => unknown;
    const result = fn(...vals);
    if (result === Infinity || result === -Infinity || (typeof result === "number" && isNaN(result))) {
      return 0;
    }
    return result;
  } catch {
    return `[#${expr}#]`;
  }
}
