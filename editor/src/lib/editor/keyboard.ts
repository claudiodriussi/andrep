import { editor } from '$lib/store/editor.svelte';
import { _ } from '$lib/i18n/index.svelte';

// --- shortcut documentation ---

export interface ShortcutEntry {
  keys: string;        // display string e.g. "Ctrl+Z"
  description: string; // human readable, will be passed through _()
  group: string;       // group name for display
}

export const SHORTCUT_DOCS: ShortcutEntry[] = [
  // File
  { group: 'File', keys: 'Ctrl+N', description: 'New template' },
  { group: 'File', keys: 'Ctrl+O', description: 'Open' },
  { group: 'File', keys: 'Ctrl+S', description: 'Save' },

  // Edit
  { group: 'Edit', keys: 'Ctrl+Z', description: 'Undo' },
  { group: 'Edit', keys: 'Ctrl+Shift+Z / Ctrl+Y', description: 'Redo' },

  // Clipboard (cells)
  { group: 'Clipboard (cells)', keys: 'Ctrl+C', description: 'Copy cells' },
  { group: 'Clipboard (cells)', keys: 'Ctrl+X', description: 'Cut cells' },
  { group: 'Clipboard (cells)', keys: 'Ctrl+V', description: 'Paste cells' },

  // Clipboard (rows)
  { group: 'Clipboard (rows)', keys: 'Ctrl+Shift+C', description: 'Copy rows' },
  { group: 'Clipboard (rows)', keys: 'Ctrl+Shift+X', description: 'Cut rows' },
  { group: 'Clipboard (rows)', keys: 'Ctrl+Shift+V', description: 'Paste rows' },

  // Selection
  { group: 'Selection', keys: 'Ctrl+A', description: 'Select all' },
  { group: 'Selection', keys: 'Esc', description: 'Clear selection' },

  // Format
  { group: 'Format', keys: 'Ctrl+B', description: 'Bold' },
  { group: 'Format', keys: 'Ctrl+I', description: 'Italic' },
  { group: 'Format', keys: 'Ctrl+U', description: 'Underline' },
  { group: 'Format', keys: 'Ctrl+]', description: 'Font size +1' },
  { group: 'Format', keys: 'Ctrl+[', description: 'Font size −1' },

  // Align H
  { group: 'Align H', keys: 'Ctrl+L', description: 'Left' },
  { group: 'Align H', keys: 'Ctrl+E', description: 'Center' },
  { group: 'Align H', keys: 'Ctrl+R', description: 'Right' },

  // Align V
  { group: 'Align V', keys: 'Ctrl+T', description: 'Top' },
  { group: 'Align V', keys: 'Ctrl+G', description: 'Middle' },
  { group: 'Align V', keys: 'Ctrl+M', description: 'Bottom' },

  // Borders toggle
  { group: 'Borders toggle', keys: 'Ctrl+0', description: 'None' },
  { group: 'Borders toggle', keys: 'Ctrl+1', description: 'Left' },
  { group: 'Borders toggle', keys: 'Ctrl+2', description: 'Right' },
  { group: 'Borders toggle', keys: 'Ctrl+3', description: 'Top' },
  { group: 'Borders toggle', keys: 'Ctrl+4', description: 'Bottom' },

  // Borders remove
  { group: 'Borders remove', keys: 'Ctrl+Shift+1', description: 'Remove left' },
  { group: 'Borders remove', keys: 'Ctrl+Shift+2', description: 'Remove right' },
  { group: 'Borders remove', keys: 'Ctrl+Shift+3', description: 'Remove top' },
  { group: 'Borders remove', keys: 'Ctrl+Shift+4', description: 'Remove bottom' },

  // Navigation
  { group: 'Navigation', keys: 'Arrow keys', description: 'Navigate cells' },
  { group: 'Navigation', keys: 'Shift+Arrow', description: 'Add to selection' },

  // Cell
  { group: 'Cell', keys: 'Enter', description: 'Edit content' },
  { group: 'Cell', keys: 'Alt+Enter', description: 'Properties' },
  { group: 'Cell', keys: 'Insert', description: 'Add cell' },
  { group: 'Cell', keys: 'Delete', description: 'Delete cells' },
  { group: 'Cell', keys: 'Ctrl+←', description: 'Narrow' },
  { group: 'Cell', keys: 'Ctrl+→', description: 'Widen' },
  { group: 'Cell', keys: 'Alt+←', description: 'Move left' },
  { group: 'Cell', keys: 'Alt+→', description: 'Move right' },

  // Row
  { group: 'Row', keys: 'Alt+↑', description: 'Move row up' },
  { group: 'Row', keys: 'Alt+↓', description: 'Move row down' },
  { group: 'Row', keys: 'Alt+Delete', description: 'Delete row' },
  { group: 'Row', keys: 'Alt+Insert', description: 'Add row' },
  { group: 'Row', keys: 'Ctrl+↑', description: 'Row shorter' },
  { group: 'Row', keys: 'Ctrl+↓', description: 'Row taller' },

  // View
  { group: 'View', keys: '?', description: 'Shortcut cheat sheet' },
];

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

  // Cheat sheet — '?' requires Shift on most keyboards, so e.shiftKey=true → key()='Shift+?'
  'Shift+?': () => { editor.cheatSheetOpen = !editor.cheatSheetOpen; },

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
    e.preventDefault(); // prevent char from also being typed into the newly focused textarea
    editor.openInlineEditor(editor.activeCellId, e.key);
  }
}
