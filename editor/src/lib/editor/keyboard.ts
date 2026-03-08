import { editor } from '$lib/store/editor.svelte';
import { _ } from '$lib/i18n/index.svelte';

// Normalize a KeyboardEvent to a string like 'Ctrl+Shift+ArrowUp', 'Ctrl+b', 'Delete'
function key(e: KeyboardEvent): string {
  const parts: string[] = [];
  if (e.ctrlKey || e.metaKey) parts.push('Ctrl');
  if (e.altKey) parts.push('Alt');
  if (e.shiftKey) parts.push('Shift');
  // Single-char keys: normalize to lowercase so Ctrl+B == Ctrl+b regardless of Shift
  parts.push(e.key.length === 1 ? e.key.toLowerCase() : e.key);
  return parts.join('+');
}

// --- helpers ---

function toggleBold() {
  const cells = editor.selectedCells;
  const allBold = cells.every((c) => c.style.fontWeight === 'bold');
  editor.applyStyle({ fontWeight: allBold ? 'normal' : 'bold' });
}

function toggleItalic() {
  const cells = editor.selectedCells;
  const allItalic = cells.every((c) => c.style.fontStyle === 'italic');
  editor.applyStyle({ fontStyle: allItalic ? 'normal' : 'italic' });
}

function toggleUnderline() {
  const cells = editor.selectedCells;
  const allUnder = cells.every((c) => c.style.textDecoration === 'underline');
  editor.applyStyle({ textDecoration: allUnder ? 'none' : 'underline' });
}

function toggleBorderSide(side: 'top' | 'bottom' | 'left' | 'right') {
  const cells = editor.selectedCells;
  if (cells.length === 0) return;
  const anyMissing = cells.some(
    (c) => c.style.borders[side].width === 0 || c.style.borders[side].style === 'none',
  );
  editor.applyBorderSides(
    [side],
    anyMissing ? { width: 1, style: 'solid', color: '#000000' } : { width: 0, style: 'none' },
  );
}

function changeFontSize(delta: number) {
  for (const cell of editor.selectedCells) {
    cell.style.fontSize = Math.max(6, cell.style.fontSize + delta);
  }
}

function activeRow() {
  if (!editor.activeCellId) return null;
  return editor.findRowOfCell(editor.activeCellId);
}

function adjacentCell(direction: 'left' | 'right') {
  if (!editor.activeCellId) return null;
  const row = editor.findRowOfCell(editor.activeCellId);
  if (!row) return null;
  const idx = row.cells.findIndex((c) => c.id === editor.activeCellId);
  if (idx === -1) return null;
  return direction === 'left' ? (row.cells[idx - 1] ?? null) : (row.cells[idx + 1] ?? null);
}

function adjacentRowCell(direction: 'up' | 'down') {
  if (!editor.activeCellId) return null;
  const row = editor.findRowOfCell(editor.activeCellId);
  if (!row) return null;
  const rowIdx = editor.template.rows.findIndex((r) => r.id === row.id);
  const adjRow = editor.template.rows[direction === 'up' ? rowIdx - 1 : rowIdx + 1];
  if (!adjRow || adjRow.cells.length === 0) return null;
  const colIdx = row.cells.findIndex((c) => c.id === editor.activeCellId);
  return adjRow.cells[Math.min(colIdx, adjRow.cells.length - 1)];
}


// --- shortcut map ---

type Handler = (e: KeyboardEvent) => void;

const SHORTCUTS: Record<string, Handler> = {
  // Undo / Redo
  'Ctrl+z': (e) => { e.preventDefault(); editor.undo(); },
  'Ctrl+Shift+z': (e) => { e.preventDefault(); editor.redo(); },
  'Ctrl+y':       (e) => { e.preventDefault(); editor.redo(); },

  // File
  'Ctrl+n': (e) => { e.preventDefault(); editor.newTemplate(); },
  'Ctrl+s': (e) => { e.preventDefault(); editor.saveJson(); },
  'Ctrl+o': (e) => { e.preventDefault(); editor.loadJson(); },

  // Copy / cut / paste — cells
  'Ctrl+c': (e) => { e.preventDefault(); editor.copyCells(); },
  'Ctrl+x': (e) => { e.preventDefault(); editor.cutCells(); },
  'Ctrl+v': (e) => { e.preventDefault(); editor.pasteCells(); },

  // Copy / cut / paste — rows (Shift+Ctrl)
  'Ctrl+Shift+c': (e) => { e.preventDefault(); editor.copyRows(); },
  'Ctrl+Shift+x': (e) => { e.preventDefault(); editor.cutRows(); },
  'Ctrl+Shift+v': (e) => { e.preventDefault(); editor.pasteRows(); },

  // Selection
  'Ctrl+a': (e) => { e.preventDefault(); editor.selectAll(); },
  'Escape': () => { editor.clearSelection(); },

  // Text formatting
  'Ctrl+b': (e) => { e.preventDefault(); toggleBold(); },
  'Ctrl+i': (e) => { e.preventDefault(); toggleItalic(); },
  'Ctrl+u': (e) => { e.preventDefault(); toggleUnderline(); },

  // Font size
  'Ctrl+]': (e) => { e.preventDefault(); changeFontSize(+1); },
  'Ctrl+[': (e) => { e.preventDefault(); changeFontSize(-1); },

  // Text alignment (horizontal)
  'Ctrl+l': (e) => { e.preventDefault(); editor.applyStyle({ alignment: 'left' }); },
  'Ctrl+e': (e) => { e.preventDefault(); editor.applyStyle({ alignment: 'center' }); },
  'Ctrl+r': (e) => { e.preventDefault(); editor.applyStyle({ alignment: 'right' }); },

  // Text alignment (vertical)
  'Ctrl+t': (e) => { e.preventDefault(); editor.applyStyle({ verticalAlignment: 'top' }); },
  'Ctrl+g': (e) => { e.preventDefault(); editor.applyStyle({ verticalAlignment: 'middle' }); },
  'Ctrl+m': (e) => { e.preventDefault(); editor.applyStyle({ verticalAlignment: 'bottom' }); },

  // Borders — toggle (apply pen 1px solid black if absent, remove if present)
  'Ctrl+0': (e) => { e.preventDefault(); editor.applyBorderSides(['top', 'bottom', 'left', 'right'], { width: 0, style: 'none' }); },
  'Ctrl+1': (e) => { e.preventDefault(); toggleBorderSide('left'); },
  'Ctrl+2': (e) => { e.preventDefault(); toggleBorderSide('right'); },
  'Ctrl+3': (e) => { e.preventDefault(); toggleBorderSide('top'); },
  'Ctrl+4': (e) => { e.preventDefault(); toggleBorderSide('bottom'); },

  // Cell navigation
  'ArrowLeft':       (e) => { const c = adjacentCell('left');  if (c) { e.preventDefault(); editor.selectOne(c.id); } },
  'ArrowRight':      (e) => { const c = adjacentCell('right'); if (c) { e.preventDefault(); editor.selectOne(c.id); } },
  'Shift+ArrowLeft': (e) => { const c = adjacentCell('left');  if (c) { e.preventDefault(); editor.selectAdd(c.id); } },
  'Shift+ArrowRight':(e) => { const c = adjacentCell('right'); if (c) { e.preventDefault(); editor.selectAdd(c.id); } },

  // Cells
  'Delete': () => { editor.deleteSelectedCells(); },
  'Insert': () => { const r = activeRow(); if (r) editor.addCell(r.id); },
  'Ctrl+ArrowLeft':  (e) => { e.preventDefault(); const c = editor.activeCellId ? editor.findCell(editor.activeCellId) : null; if (c) { editor.pushHistory(); editor.resizeCell(c.id, Math.max(20, c.width - editor.gridStepX)); } },
  'Ctrl+ArrowRight': (e) => { e.preventDefault(); const c = editor.activeCellId ? editor.findCell(editor.activeCellId) : null; if (c) { editor.pushHistory(); editor.resizeCell(c.id, c.width + editor.gridStepX); } },

  // Row navigation
  'ArrowUp':        (e) => { const c = adjacentRowCell('up');   if (c) { e.preventDefault(); editor.selectOne(c.id); } },
  'ArrowDown':      (e) => { const c = adjacentRowCell('down'); if (c) { e.preventDefault(); editor.selectOne(c.id); } },
  'Shift+ArrowUp':  (e) => { const c = adjacentRowCell('up');   if (c) { e.preventDefault(); editor.selectAdd(c.id); } },
  'Shift+ArrowDown':(e) => { const c = adjacentRowCell('down'); if (c) { e.preventDefault(); editor.selectAdd(c.id); } },

  // Inline text editor
  'Enter': (e) => { e.preventDefault(); if (editor.activeCellId) editor.openInlineEditor(editor.activeCellId); },

  // Cell properties dialog
  'Alt+Enter': (e) => { e.preventDefault(); if (editor.activeCellId) editor.openCellDialog(editor.activeCellId); },

  // Cell reorder
  'Alt+ArrowLeft':  (e) => { e.preventDefault(); if (editor.activeCellId) editor.moveCellInRow(editor.activeCellId, 'left'); },
  'Alt+ArrowRight': (e) => { e.preventDefault(); if (editor.activeCellId) editor.moveCellInRow(editor.activeCellId, 'right'); },

  // Rows
  'Alt+ArrowUp':    (e) => { e.preventDefault(); const r = activeRow(); if (r) editor.moveRowUp(r.id); },
  'Alt+ArrowDown':  (e) => { e.preventDefault(); const r = activeRow(); if (r) editor.moveRowDown(r.id); },
  'Alt+Delete':     () => { const r = activeRow(); if (r) editor.deleteRow(r.id); },
  'Alt+Insert':     () => { const name = prompt(_('Band name:'), 'band'); if (name?.trim()) editor.addRow(name.trim(), activeRow()?.id); },
  'Ctrl+ArrowUp':   (e) => { e.preventDefault(); const r = activeRow(); if (r) { editor.pushHistory(); for (const c of r.cells) c.height = Math.max(10, c.height - editor.gridStepY); } },
  'Ctrl+ArrowDown': (e) => { e.preventDefault(); const r = activeRow(); if (r) { editor.pushHistory(); for (const c of r.cells) c.height += editor.gridStepY; } },
};

// Shift+Ctrl+1/2/3/4 — remove specific border side.
// Uses e.code (Digit1…4) instead of e.key because Shift changes e.key to '!'/'@'/etc. on most locales.
const REMOVE_BORDER_CODES: Record<string, 'left' | 'right' | 'top' | 'bottom'> = {
  'Digit1': 'left', 'Digit2': 'right', 'Digit3': 'top', 'Digit4': 'bottom',
};

export function handleKeydown(e: KeyboardEvent): void {
  // Don't intercept when the user is typing in a form field
  const tag = (e.target as HTMLElement).tagName;
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

  // Shift+Ctrl+1/2/3/4 — always remove (uses e.code for locale independence)
  if (e.ctrlKey && e.shiftKey && !e.altKey) {
    const side = REMOVE_BORDER_CODES[e.code];
    if (side) {
      e.preventDefault();
      editor.applyBorderSides([side], { width: 0, style: 'none' });
      return;
    }
  }

  // Named shortcuts
  const handler = SHORTCUTS[key(e)];
  if (handler) { handler(e); return; }

  // Printable character — open inline editor with that char pre-typed (Excel/Delphi behavior)
  if (
    e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey &&
    editor.activeCellId
  ) {
    editor.openInlineEditor(editor.activeCellId, e.key);
  }
}
