export interface BorderSide {
  width: number;
  style: 'none' | 'solid' | 'dashed' | 'dotted' | 'double';
  color: string;
}

export interface CellBorders {
  top: BorderSide;
  bottom: BorderSide;
  left: BorderSide;
  right: BorderSide;
}

export interface CellStyle {
  fontFamily: string;
  fontSize: number;
  fontWeight: 'normal' | 'bold';
  fontStyle: 'normal' | 'italic';
  textDecoration: 'none' | 'underline' | 'line-through';
  color: string;
  backgroundColor: string;
  alignment: 'left' | 'center' | 'right' | 'justify';
  verticalAlignment: 'top' | 'middle' | 'bottom';
  paddingTop: number;
  paddingBottom: number;
  paddingLeft: number;
  paddingRight: number;
  borders: CellBorders;
}

export type CellType = 'text' | 'markdown' | 'image' | 'barcode' | 'qrcode' | 'embed';

// Semantica del campo `content` per tipo:
//   text     — testo con interpolazione [VAR|formatter]
//   markdown — markdown con interpolazione [VAR|formatter]; il renderer converte in HTML
//   image    — URL, path relativo o data URI; può contenere [VAR] che risolve a uno di questi
//   barcode  — valore da codificare (stringa/numero o [VAR])
//   qrcode   — valore da codificare (URL, testo o [VAR])
//   embed    — non usato (la band è in embedTarget)

export interface Cell {
  id: string;
  content: string;
  type: CellType;
  embedTarget?: string; // solo se type === 'embed': nome della band da espandere in questa cella
  x: number;
  width: number;
  height: number;
  wrap: boolean;
  style: CellStyle;
}

export interface Row {
  id: string;
  name: string; // nome band — più righe con lo stesso nome formano una band
  cells: Cell[];
}

export interface PageConfig {
  width: number;
  height: number;
  marginTop: number;
  marginBottom: number;
  marginLeft: number;
  marginRight: number;
  orientation: 'portrait' | 'landscape';
}

export type CompositionRuleType = 'IFNOT' | 'REPLACE' | 'INSBEFORE' | 'INSAFTER' | 'EMBED';

export interface CompositionRule {
  rule: CompositionRuleType;
  target: string; // nome del template o band di riferimento
}

export interface Template {
  name: string;
  version: string;
  page: PageConfig;
  rows: Row[];
  composition?: CompositionRule[]; // regole di composizione dichiarate dal template
}
