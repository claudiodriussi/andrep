import type { Cell, CellStyle, Row, Template } from '$lib/types';

let _uid = 1;
const uid = () => `r${_uid++}`;

function borderSide(w = 1) {
  return { width: w, style: 'solid' as const, color: '#cccccc' };
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

class EditorState {
  template = $state<Template>({
    name: 'Nuovo template',
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
  });

  selectedCellIds = $state<Set<string>>(new Set());
  // Ultima cella cliccata — ha il bordo di focus visivo
  activeCellId = $state<string | null>(null);
  // Toggle guide di design (bordi celle visibili nell'editor)
  showGuides = $state(true);

  toggleGuides() {
    this.showGuides = !this.showGuides;
  }

  // Tutte le celle selezionate come array (per toolbar)
  selectedCells = $derived(
    this.template.rows.flatMap((r) => r.cells).filter((c) => this.selectedCellIds.has(c.id)),
  );

  // --- selezione ---
  // Nota: riassegnare sempre selectedCellIds (new Set) invece di mutare in-place,
  // perché Svelte 5 non traccia le mutazioni di Set cross-componente in modo affidabile.

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

  // --- righe ---

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

  // --- celle ---

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
}

export const editor = new EditorState();
