import type { BorderSide, BandOptions, Cell, CellStyle, CellType, CompositionRule, PageConfig, Row, Template } from '$lib/types';
import { _ } from '$lib/i18n/index.svelte';
import { history } from './history.svelte';
import { config } from './config.svelte';
import { presetToPx } from '$lib/units';

const STORAGE_KEY = 'andrep-draft';

let _uid = 1;
const uid = () => `r${_uid++}`;

// After loading a template from storage or file, advance _uid past
// all existing IDs so new items don't collide with loaded ones.
function syncUid(template: Template) {
  for (const row of template.rows) {
    const n = parseInt(row.id.replace(/\D/g, ''));
    if (!isNaN(n) && n >= _uid) _uid = n + 1;
    for (const cell of row.cells) {
      const m = parseInt(cell.id.replace(/\D/g, ''));
      if (!isNaN(m) && m >= _uid) _uid = m + 1;
    }
  }
}

function borderSide(): BorderSide {
  return { width: 0, style: 'none', color: '#000000' };
}

function defaultStyle(): CellStyle {
  return {
    fontFamily: 'Arial',
    fontSize: 11,
    fontWeight: 'normal',
    fontStyle: 'normal',
    textDecoration: 'none',
    color: '#000000',
    backgroundColor: '#ffffff',
    alignment: 'left',
    verticalAlignment: 'top',
    paddingTop: 2,
    paddingBottom: 2,
    paddingLeft: 4,
    paddingRight: 4,
    borders: {
      top: borderSide(),
      bottom: borderSide(),
      left: borderSide(),
      right: borderSide(),
    },
  };
}

function makeCell(): Cell {
  return {
    id: uid(),
    content: '',
    type: 'text',
    x: 0,
    width: 100,
    height: 24,
    wrap: false,
    autoStretch: false,
    style: defaultStyle(),
  };
}

function makeRow(name: string): Row {
  return { id: uid(), name, cells: [makeCell()] };
}

function emptyTemplate(opts?: {
  preset?: typeof config.config.defaultPreset;
  margins?: { top: number; bottom: number; left: number; right: number };
}): Template {
  const preset = opts?.preset ?? config.config.defaultPreset;
  const m      = opts?.margins ?? config.config.defaultMargins;
  const dims   = presetToPx(preset, 'portrait');
  return {
    _type: 'andrep-template',
    name: 'New template',
    version: '1.0',
    page: {
      preset,
      width:        dims.width,
      height:       dims.height,
      marginTop:    m.top,
      marginBottom: m.bottom,
      marginLeft:   m.left,
      marginRight:  m.right,
      orientation: 'portrait',
      locale:   config.config.defaultLocale,
      currency: config.config.defaultCurrency,
    },
    rows: [],
  };
}

function loadDraft(): Template {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return emptyTemplate();
    const data = JSON.parse(raw);
    if (data?._type !== 'andrep-template') return emptyTemplate();
    const t = data as Template;
    syncUid(t);
    return t;
  } catch {
    return emptyTemplate();
  }
}

class EditorState {
  template = $state<Template>(loadDraft());

  selectedCellIds = $state<Set<string>>(new Set());
  // Last clicked cell — receives the focus border highlight
  activeCellId = $state<string | null>(null);
  // Cell properties dialog — set to a cell id to open the dialog
  cellDialogId = $state<string | null>(null);
  // Inline text editor — set to a cell id to open the textarea overlay
  inlineCellId = $state<string | null>(null);
  // When set, the inline editor starts with this value instead of cell.content (printable-char trigger)
  inlineCellInitialValue = $state<string | null>(null);
  // Clipboards (in-memory, independent from system clipboard)
  cellClipboard = $state<Cell[] | null>(null);
  rowClipboard  = $state<Row[]  | null>(null);

  // Cheat-sheet overlay (keyboard shortcuts)
  cheatSheetOpen = $state(false);

  // Toggle design guides (dashed cell outlines visible only in the editor)
  showGuides = $state(true);
  gridStepX = $state(4); // px — horizontal resize step (keyboard + drag)
  gridStepY = $state(4); // px — vertical resize step (keyboard + drag)

  // All selected cells as an array (consumed by the toolbar)
  selectedCells = $derived(
    this.template.rows.flatMap((r) => r.cells).filter((c) => this.selectedCellIds.has(c.id)),
  );

  // --- history ---

  pushHistory() {
    history.push(this.template);
  }

  undo() {
    const prev = history.undo(this.template);
    if (!prev) return;
    this.template = prev;
    syncUid(this.template);
    this.#restoreSelection();
  }

  redo() {
    const next = history.redo(this.template);
    if (!next) return;
    this.template = next;
    syncUid(this.template);
    this.#restoreSelection();
  }

  // After undo/redo: keep selection IDs that still exist in the restored template.
  #restoreSelection() {
    const allIds = new Set(this.template.rows.flatMap((r) => r.cells.map((c) => c.id)));
    this.selectedCellIds = new Set([...this.selectedCellIds].filter((id) => allIds.has(id)));
    if (this.activeCellId && !allIds.has(this.activeCellId)) this.activeCellId = null;
  }

  newTemplate() {
    if (this.template.rows.length > 0) {
      if (!confirm(_('Create new template? Unsaved changes will be lost.'))) return;
    }
    this.template = emptyTemplate();
    this.clearSelection();
    this.clearDraft();
    history.clear();
  }

  // --- page setup dialog ---
  pageSetupOpen = $state(false);

  openPageSetup() {
    this.pageSetupOpen = true;
  }

  closePageSetup() {
    this.pageSetupOpen = false;
  }

  getBandOptions(bandName: string): BandOptions {
    return this.template.bands?.[bandName] ?? {};
  }

  toggleBandKeepTogether(bandName: string) {
    this.pushHistory();
    const current = this.template.bands?.[bandName]?.keepTogether ?? false;
    const bands = { ...(this.template.bands ?? {}) };
    if (current) {
      // turn off — remove entry, clean up if empty
      const { [bandName]: _removed, ...rest } = bands;
      this.template.bands = Object.keys(rest).length > 0 ? rest : undefined;
    } else {
      bands[bandName] = { ...bands[bandName], keepTogether: true };
      this.template.bands = bands;
    }
  }

  applyPageSetup(name: string, page: PageConfig, composition: CompositionRule[]) {
    this.pushHistory();
    this.template.name = name;
    this.template.page = { ...page };
    this.template.composition = composition.length > 0 ? [...composition] : undefined;
  }

  toggleGuides() {
    this.showGuides = !this.showGuides;
  }

  openCellDialog(id: string) {
    this.cellDialogId = id;
  }

  closeCellDialog() {
    this.cellDialogId = null;
  }

  openInlineEditor(id: string, initialValue?: string) {
    this.selectOne(id);
    this.inlineCellInitialValue = initialValue ?? null;
    this.inlineCellId = id;
  }

  closeInlineEditor() {
    this.inlineCellId = null;
    this.inlineCellInitialValue = null;
  }

  // --- selection ---
  // Always reassign selectedCellIds (new Set) instead of mutating in-place:
  // Svelte 5 does not reliably track in-place Set mutations across components.

  selectOne(id: string) {
    this.selectedCellIds = new Set([id]);
    this.activeCellId = id;
  }

  selectAdd(id: string) {
    const s = new Set(this.selectedCellIds);
    if (s.has(id)) {
      s.delete(id);
      this.activeCellId = this.activeCellId === id ? null : this.activeCellId;
    } else {
      s.add(id);
      this.activeCellId = id;
    }
    this.selectedCellIds = s;
  }

  selectRow(rowId: string) {
    const row = this.template.rows.find((r) => r.id === rowId);
    if (!row) return;
    this.selectedCellIds = new Set(row.cells.map((c) => c.id));
    this.activeCellId = row.cells[0]?.id ?? null;
  }


  selectAll() {
    this.selectedCellIds = new Set(
      this.template.rows.flatMap((r) => r.cells.map((c) => c.id)),
    );
    this.activeCellId = this.template.rows[0]?.cells[0]?.id ?? null;
  }

  clearSelection() {
    this.selectedCellIds = new Set();
    this.activeCellId = null;
  }

  // --- rows ---

  addRow(name: string, afterRowId?: string) {
    this.pushHistory();
    const row = makeRow(name);
    if (afterRowId) {
      const idx = this.template.rows.findIndex((r) => r.id === afterRowId);
      if (idx !== -1) { this.template.rows.splice(idx + 1, 0, row); return; }
    }
    this.template.rows.push(row);
  }

  deleteRow(rowId: string) {
    this.pushHistory();
    const idx = this.template.rows.findIndex((r) => r.id === rowId);
    if (idx === -1) return;
    const row = this.template.rows[idx];
    const rowCellIds = new Set(row.cells.map((c) => c.id));
    this.selectedCellIds = new Set([...this.selectedCellIds].filter((id) => !rowCellIds.has(id)));
    // Move active cell to the row below, or above if it was the last
    if (this.activeCellId && rowCellIds.has(this.activeCellId)) {
      const next = this.template.rows[idx + 1] ?? this.template.rows[idx - 1] ?? null;
      const nextCell = next?.cells[0] ?? null;
      if (nextCell) this.selectOne(nextCell.id); else this.activeCellId = null;
    }
    this.template.rows.splice(idx, 1);
  }

  moveRowUp(rowId: string) {
    const idx = this.template.rows.findIndex((r) => r.id === rowId);
    if (idx <= 0) return;
    this.pushHistory();
    const [row] = this.template.rows.splice(idx, 1);
    this.template.rows.splice(idx - 1, 0, row);
  }

  moveRowDown(rowId: string) {
    const idx = this.template.rows.findIndex((r) => r.id === rowId);
    if (idx === -1 || idx >= this.template.rows.length - 1) return;
    this.pushHistory();
    const [row] = this.template.rows.splice(idx, 1);
    this.template.rows.splice(idx + 1, 0, row);
  }

  // --- cells ---

  addCell(rowId: string) {
    const row = this.template.rows.find((r) => r.id === rowId);
    if (!row) return;
    this.pushHistory();
    const cell = makeCell();
    // Insert after active cell if it belongs to this row, otherwise append
    const activeIdx = this.activeCellId
      ? row.cells.findIndex((c) => c.id === this.activeCellId)
      : -1;
    if (activeIdx !== -1) {
      const ref = row.cells[activeIdx];
      cell.height = ref.height;
      cell.x = ref.x + ref.width;
      row.cells.splice(activeIdx + 1, 0, cell);
    } else {
      const last = row.cells.at(-1);
      cell.height = last ? last.height : cell.height;
      cell.x = last ? last.x + last.width : 0;
      row.cells.push(cell);
    }
  }

  deleteCell(cellId: string) {
    for (const row of this.template.rows) {
      const idx = row.cells.findIndex((c) => c.id === cellId);
      if (idx !== -1) {
        row.cells.splice(idx, 1);
        if (this.selectedCellIds.has(cellId)) {
          const s = new Set(this.selectedCellIds);
          s.delete(cellId);
          this.selectedCellIds = s;
        }
        if (this.activeCellId === cellId) {
          // activate next cell, or previous if it was the last, or null
          const next = row.cells[idx] ?? row.cells[idx - 1] ?? null;
          if (next) this.selectOne(next.id); else this.activeCellId = null;
        }
        return;
      }
    }
  }

  deleteSelectedCells() {
    this.pushHistory();
    const ids = this.selectedCellIds;
    if (ids.size === 0) return;
    let nextActiveId: string | null = null;
    for (const row of this.template.rows) {
      if (!nextActiveId && this.activeCellId && ids.has(this.activeCellId)) {
        const idx = row.cells.findIndex((c) => c.id === this.activeCellId);
        if (idx !== -1) {
          // find first surviving cell after, then before
          const after = row.cells.slice(idx + 1).find((c) => !ids.has(c.id));
          const before = row.cells.slice(0, idx).reverse().find((c) => !ids.has(c.id));
          nextActiveId = (after ?? before)?.id ?? null;
        }
      }
      row.cells = row.cells.filter((c) => !ids.has(c.id));
    }
    this.selectedCellIds = new Set();
    if (nextActiveId) this.selectOne(nextActiveId); else this.activeCellId = null;
  }

  moveCellInRow(cellId: string, direction: 'left' | 'right') {
    this.pushHistory();
    for (const row of this.template.rows) {
      const idx = row.cells.findIndex((c) => c.id === cellId);
      if (idx === -1) continue;
      const swapIdx = direction === 'left' ? idx - 1 : idx + 1;
      if (swapIdx < 0 || swapIdx >= row.cells.length) return;
      [row.cells[idx], row.cells[swapIdx]] = [row.cells[swapIdx], row.cells[idx]];
      let x = 0;
      for (const cell of row.cells) { cell.x = x; x += cell.width; }
      return;
    }
  }

  resizeCellHeight(cellId: string, newHeight: number) {
    const row = this.findRowOfCell(cellId);
    if (row) {
      for (const cell of row.cells) cell.height = newHeight;
    }
  }

  resizeCell(cellId: string, newWidth: number) {
    for (const row of this.template.rows) {
      const idx = row.cells.findIndex((c) => c.id === cellId);
      if (idx === -1) continue;
      row.cells[idx].width = newWidth;
      // Recalculate x of subsequent cells to keep the model consistent
      let x = row.cells[idx].x + newWidth;
      for (let i = idx + 1; i < row.cells.length; i++) {
        row.cells[i].x = x;
        x += row.cells[i].width;
      }
      return;
    }
  }

  renameRow(rowId: string, name: string) {
    this.pushHistory();
    const row = this.template.rows.find((r) => r.id === rowId);
    if (row && name.trim()) row.name = name.trim();
  }

  findCell(cellId: string): Cell | null {
    for (const row of this.template.rows) {
      const cell = row.cells.find((c) => c.id === cellId);
      if (cell) return cell;
    }
    return null;
  }

  findRowOfCell(cellId: string): Row | null {
    return this.template.rows.find((r) => r.cells.some((c) => c.id === cellId)) ?? null;
  }

  updateCell(cellId: string, props: {
    content: string;
    type: CellType;
    embedTarget: string | undefined;
    width: number;
    height: number;
    x: number;
    wrap: boolean;
    autoStretch: boolean;
    rotation: 0 | 90 | 180 | 270 | undefined;
    cssExtra: string | undefined;
  }) {
    this.pushHistory();
    const cell = this.findCell(cellId);
    if (!cell) return;
    cell.content = props.content;
    cell.type = props.type;
    cell.embedTarget = props.embedTarget || undefined;
    cell.wrap = props.wrap;
    cell.autoStretch = props.autoStretch;
    cell.rotation = props.rotation || undefined;
    cell.cssExtra = props.cssExtra || undefined;
    cell.x = Math.max(0, props.x);
    cell.height = Math.max(10, props.height);
    this.resizeCell(cellId, Math.max(20, props.width));
  }

  // --- clipboard ---

  copyCells() {
    if (this.selectedCells.length === 0) return;
    this.cellClipboard = JSON.parse(JSON.stringify(this.selectedCells));
  }

  cutCells() {
    if (this.selectedCells.length === 0) return;
    this.copyCells();
    this.deleteSelectedCells(); // pushes history
  }

  pasteCells() {
    if (!this.cellClipboard || !this.activeCellId) return;
    const row = this.findRowOfCell(this.activeCellId);
    if (!row) return;
    this.pushHistory();
    const activeCell = row.cells.find((c) => c.id === this.activeCellId)!;
    const idx = row.cells.indexOf(activeCell);
    let x = activeCell.x;
    const inserted: Cell[] = [];
    for (const src of this.cellClipboard) {
      const cell: Cell = { ...JSON.parse(JSON.stringify(src)), id: uid(), x };
      x += cell.width;
      inserted.push(cell);
    }
    row.cells.splice(idx, 0, ...inserted);
    this.selectedCellIds = new Set(inserted.map((c) => c.id));
    this.activeCellId = inserted[0].id;
  }

  copyRows() {
    const rowIds = new Set<string>();
    for (const cellId of this.selectedCellIds) {
      const row = this.findRowOfCell(cellId);
      if (row) rowIds.add(row.id);
    }
    const rows = this.template.rows.filter((r) => rowIds.has(r.id));
    if (rows.length === 0) return;
    this.rowClipboard = JSON.parse(JSON.stringify(rows));
  }

  cutRows() {
    if (this.selectedCellIds.size === 0) return;
    this.copyRows();
    this.pushHistory();
    const rowIds = new Set<string>();
    for (const cellId of this.selectedCellIds) {
      const row = this.findRowOfCell(cellId);
      if (row) rowIds.add(row.id);
    }
    // Find a surviving row to land on (first row below, then above)
    const surviving = this.template.rows.filter((r) => !rowIds.has(r.id));
    const activeRow = this.activeCellId ? this.findRowOfCell(this.activeCellId) : null;
    if (activeRow && rowIds.has(activeRow.id)) {
      const activeIdx = this.template.rows.indexOf(activeRow);
      const land = this.template.rows.slice(activeIdx + 1).find((r) => !rowIds.has(r.id))
        ?? this.template.rows.slice(0, activeIdx).reverse().find((r) => !rowIds.has(r.id))
        ?? null;
      const landCell = land?.cells[0] ?? null;
      if (landCell) this.selectOne(landCell.id); else this.activeCellId = null;
    }
    this.selectedCellIds = new Set();
    this.template.rows = surviving;
  }

  pasteRows() {
    if (!this.rowClipboard) return;
    this.pushHistory();
    const beforeId = this.activeCellId ? this.findRowOfCell(this.activeCellId)?.id : undefined;
    const cloned: Row[] = this.rowClipboard.map((r) => ({
      ...JSON.parse(JSON.stringify(r)),
      id: uid(),
      cells: (r.cells as Cell[]).map((c) => ({ ...JSON.parse(JSON.stringify(c)), id: uid() })),
    }));
    if (beforeId) {
      const idx = this.template.rows.findIndex((r) => r.id === beforeId);
      this.template.rows.splice(idx, 0, ...cloned);
    } else {
      this.template.rows.push(...cloned);
    }
    this.selectedCellIds = new Set(cloned.flatMap((r) => r.cells.map((c) => c.id)));
    this.activeCellId = cloned[0].cells[0]?.id ?? null;
  }

  // --- style ---

  applyStyle(patch: Partial<CellStyle>) {
    this.pushHistory();
    for (const cell of this.selectedCells) {
      Object.assign(cell.style, patch);
    }
  }

  applyBorderSides(sides: ('top' | 'bottom' | 'left' | 'right')[], patch: Partial<BorderSide>) {
    this.pushHistory();
    for (const cell of this.selectedCells) {
      for (const side of sides) {
        Object.assign(cell.style.borders[side], patch);
      }
    }
  }

  // --- draft autosave ---

  saveDraft() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.template));
    } catch {
      // localStorage may be unavailable (private browsing, storage quota, etc.)
    }
  }

  clearDraft() {
    localStorage.removeItem(STORAGE_KEY);
  }

  // --- file ---

  saveJson() {
    this.clearDraft();
    const json = JSON.stringify(this.template, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${this.template.name.replace(/\s+/g, '_')}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  loadJson() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json,application/json';
    input.onchange = async () => {
      const file = input.files?.[0];
      if (!file) return;
      try {
        const text = await file.text();
        const data = JSON.parse(text);
        if (data?._type !== 'andrep-template') {
          alert(_('Invalid file: not an AndRep template.'));
          return;
        }
        this.template = data as Template;
        syncUid(this.template);
        this.clearSelection();
        this.clearDraft();
      } catch {
        alert(_('Invalid JSON file.'));
      }
    };
    input.click();
  }
}

export const editor = new EditorState();
