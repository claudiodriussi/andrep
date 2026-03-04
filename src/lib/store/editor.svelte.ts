import type { BorderSide, Cell, CellStyle, Row, Template } from '$lib/types';

const STORAGE_KEY = 'andrep-draft';

let _uid = 1;
const uid = () => `r${_uid++}`;

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
    style: defaultStyle(),
  };
}

function makeRow(name: string): Row {
  return { id: uid(), name, cells: [] };
}

function emptyTemplate(): Template {
  return {
    _type: 'andrep-template',
    name: 'New template',
    version: '1.0',
    page: {
      width: 794,
      height: 1123,
      marginTop: 40,
      marginBottom: 40,
      marginLeft: 30,
      marginRight: 30,
      orientation: 'portrait',
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
    return data as Template;
  } catch {
    return emptyTemplate();
  }
}

class EditorState {
  template = $state<Template>(loadDraft());

  selectedCellIds = $state<Set<string>>(new Set());
  // Last clicked cell — receives the focus border highlight
  activeCellId = $state<string | null>(null);
  // Toggle design guides (dashed cell outlines visible only in the editor)
  showGuides = $state(true);

  // All selected cells as an array (consumed by the toolbar)
  selectedCells = $derived(
    this.template.rows.flatMap((r) => r.cells).filter((c) => this.selectedCellIds.has(c.id)),
  );

  toggleGuides() {
    this.showGuides = !this.showGuides;
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

  addRow(name: string) {
    this.template.rows.push(makeRow(name));
  }

  deleteRow(rowId: string) {
    const idx = this.template.rows.findIndex((r) => r.id === rowId);
    if (idx === -1) return;
    const row = this.template.rows[idx];
    const rowCellIds = new Set(row.cells.map((c) => c.id));
    this.selectedCellIds = new Set([...this.selectedCellIds].filter((id) => !rowCellIds.has(id)));
    if (this.activeCellId && rowCellIds.has(this.activeCellId)) this.activeCellId = null;
    this.template.rows.splice(idx, 1);
  }

  moveRowUp(rowId: string) {
    const idx = this.template.rows.findIndex((r) => r.id === rowId);
    if (idx <= 0) return;
    const [row] = this.template.rows.splice(idx, 1);
    this.template.rows.splice(idx - 1, 0, row);
  }

  moveRowDown(rowId: string) {
    const idx = this.template.rows.findIndex((r) => r.id === rowId);
    if (idx === -1 || idx >= this.template.rows.length - 1) return;
    const [row] = this.template.rows.splice(idx, 1);
    this.template.rows.splice(idx + 1, 0, row);
  }

  // --- cells ---

  addCell(rowId: string) {
    const row = this.template.rows.find((r) => r.id === rowId);
    if (!row) return;
    const cell = makeCell();
    const last = row.cells.at(-1);
    cell.x = last ? last.x + last.width : 0;
    row.cells.push(cell);
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
        if (this.activeCellId === cellId) this.activeCellId = null;
        return;
      }
    }
  }

  renameRow(rowId: string, name: string) {
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

  // --- style ---

  applyStyle(patch: Partial<CellStyle>) {
    for (const cell of this.selectedCells) {
      Object.assign(cell.style, patch);
    }
  }

  applyBorderSides(sides: ('top' | 'bottom' | 'left' | 'right')[], patch: Partial<BorderSide>) {
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
          alert('Invalid file: not an AndRep template.');
          return;
        }
        this.template = data as Template;
        this.clearSelection();
        this.clearDraft();
      } catch {
        alert('Invalid JSON file.');
      }
    };
    input.click();
  }
}

export const editor = new EditorState();
