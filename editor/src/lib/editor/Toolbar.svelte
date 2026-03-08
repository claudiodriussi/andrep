<script lang="ts">
  import { untrack } from 'svelte';
  import { editor } from '$lib/store/editor.svelte';
  import { history } from '$lib/store/history.svelte';
  import { config } from '$lib/store/config.svelte';
  import { _ } from '$lib/i18n/index.svelte';
  import ColorPicker from './ColorPicker.svelte';
  import type { BorderSide, ToolbarGroupId } from '$lib/types';
  import {
    FilePlus, FolderOpen, Save, Undo2, Redo2,
    Scissors, Copy, ClipboardPaste,
    Bold, Italic, Underline,
    AlignLeft, AlignCenter, AlignRight, AlignJustify,
    AlignVerticalJustifyStart, AlignVerticalJustifyCenter, AlignVerticalJustifyEnd,
    SquareDashed, SquarePlus, Trash2, ListPlus, ListX, ArrowUp, ArrowDown,
  } from 'lucide-svelte';

  type BorderSideName = 'top' | 'bottom' | 'left' | 'right';
  const ALL_SIDES: BorderSideName[] = ['top', 'bottom', 'left', 'right'];

  // Groups implemented so far — unimplemented ones are silently skipped
  const IMPLEMENTED = new Set<ToolbarGroupId>(['file', 'colors', 'borders', 'font', 'align', 'structure']);
  const activeGroups = $derived(
    config.config.toolbarGroups.filter((g) => IMPLEMENTED.has(g)),
  );

  // --- current selection ---
  const cells = $derived(editor.selectedCells);
  const hasSelection = $derived(cells.length > 0);

  // Returns the value if uniform across all selected cells, null if mixed
  function uniformVal<T>(getter: (c: typeof cells[0]) => T): T | null {
    if (cells.length === 0) return null;
    const first = getter(cells[0]);
    return cells.every((c) => getter(c) === first) ? first : null;
  }

  // --- structure ---
  const activeRow = $derived(
    editor.activeCellId ? editor.findRowOfCell(editor.activeCellId) : null,
  );

  function addCell() {
    if (activeRow) editor.addCell(activeRow.id);
  }

  function addRow() {
    const name = prompt(_('Band name:'), 'band');
    if (name?.trim()) editor.addRow(name.trim(), activeRow?.id);
  }

  function deleteRow() {
    if (activeRow) editor.deleteRow(activeRow.id);
  }

  function moveRowUp() {
    if (activeRow) editor.moveRowUp(activeRow.id);
  }

  function moveRowDown() {
    if (activeRow) editor.moveRowDown(activeRow.id);
  }

  // --- align ---
  const alignment         = $derived(uniformVal((c) => c.style.alignment));
  const verticalAlignment = $derived(uniformVal((c) => c.style.verticalAlignment));

  // --- font ---

  const fontFamily     = $derived(uniformVal((c) => c.style.fontFamily));
  const fontSize       = $derived(uniformVal((c) => c.style.fontSize));
  const fontWeight     = $derived(uniformVal((c) => c.style.fontWeight));
  const fontStyleVal   = $derived(uniformVal((c) => c.style.fontStyle));
  const textDecoration = $derived(uniformVal((c) => c.style.textDecoration));

  // --- colors ---
  // Mixed selection (different values) → #808080 as visual placeholder
  const textColor = $derived(uniformVal((c) => c.style.color) ?? '#808080');
  const textColorMixed = $derived(cells.length > 1 && uniformVal((c) => c.style.color) === null);

  const bgRaw = $derived(uniformVal((c) => c.style.backgroundColor) ?? '#808080');
  const isBgTransparent = $derived(
    cells.length > 0 && cells.every((c) => c.style.backgroundColor === 'transparent'),
  );
  const bgColorMixed = $derived(
    cells.length > 1 && uniformVal((c) => c.style.backgroundColor) === null,
  );
  const bgColor = $derived(isBgTransparent ? '#ffffff' : bgRaw === '#808080' ? '#808080' : bgRaw);

  function onTransparentToggle(e: Event) {
    const checked = (e.target as HTMLInputElement).checked;
    editor.applyStyle({ backgroundColor: checked ? 'transparent' : '#ffffff' });
  }

  // --- borders ---
  // "Pen" model: width/style/color are the current pen settings.
  // T/B/L/R buttons are immediate actions: click applies the pen to that side,
  // clicking again removes the border. Each side is fully independent.
  let borderWidth = $state(1);
  let borderStyle = $state<BorderSide['style']>('solid');
  let borderColor = $state('#000000');

  // Read-only border state of the single selected cell (used for the active indicator)
  const singleCell = $derived(cells.length === 1 ? cells[0] : null);
  function sideHasBorder(side: BorderSideName): boolean {
    if (!singleCell) return false;
    const b = singleCell.style.borders[side];
    return b.width > 0 && b.style !== 'none';
  }

  // Sync pen from selection: when the single selected cell changes,
  // load its first active side's settings as the starting pen values.
  // Only tracks selectedCellIds (via selectionKey) — does NOT re-run when
  // cell data changes, so applying a border won't overwrite the pen.
  const selectionKey = $derived([...editor.selectedCellIds].sort().join(','));
  $effect(() => {
    void selectionKey;
    untrack(() => {
      if (cells.length === 1) {
        const borders = cells[0].style.borders;
        const firstActive = ALL_SIDES.find(
          (s) => borders[s].width > 0 && borders[s].style !== 'none',
        );
        if (firstActive) {
          borderWidth = borders[firstActive].width;
          borderStyle = borders[firstActive].style;
          borderColor = borders[firstActive].color;
        }
      } else if (cells.length > 1) {
        borderWidth = 1;
        borderStyle = 'solid';
        borderColor = '#000000';
      }
    });
  });

  // Click a side: apply pen if no border, remove if border already present
  function clickSide(side: BorderSideName) {
    if (!hasSelection) return;
    if (cells.length === 1 && sideHasBorder(side)) {
      editor.applyBorderSides([side], { width: 0, style: 'none' });
    } else {
      editor.applyBorderSides([side], {
        width: borderWidth,
        style: borderStyle,
        color: borderColor,
      });
    }
  }

  function removeAllBorders() {
    if (!hasSelection) return;
    editor.applyBorderSides(ALL_SIDES, { width: 0, style: 'none' });
  }

  const SIDES: { key: BorderSideName; label: string; titleKey: string }[] = [
    { key: 'top',    label: 'T', titleKey: 'Top border — click to apply pen, click again to remove (Ctrl+3)' },
    { key: 'bottom', label: 'B', titleKey: 'Bottom border — click to apply pen, click again to remove (Ctrl+4)' },
    { key: 'left',   label: 'L', titleKey: 'Left border — click to apply pen, click again to remove (Ctrl+1)' },
    { key: 'right',  label: 'R', titleKey: 'Right border — click to apply pen, click again to remove (Ctrl+2)' },
  ];
</script>

<div class="toolbar" class:disabled={!hasSelection}>
  {#each activeGroups as groupId, i (groupId)}
    {#if i > 0}<div class="sep"></div>{/if}

    {#if groupId === 'file'}
      <!-- FILE -->
      <div class="group">
        <span class="group-label">{_('File')}</span>
        <button class="tb-btn" onclick={() => editor.newTemplate()} title={_('New template (Ctrl+N)')}>
          <FilePlus size={14} />
        </button>
        <button class="tb-btn" onclick={() => editor.loadJson()} title={_('Open template (Ctrl+O)')}>
          <FolderOpen size={14} />
        </button>
        <button class="tb-btn" onclick={() => editor.saveJson()} title={_('Save template (Ctrl+S)')}>
          <Save size={14} />
        </button>
        <div class="sep-inner"></div>
        <button class="tb-btn" onclick={() => editor.undo()} disabled={!history.canUndo}
          title={_('Undo (Ctrl+Z)')}
        ><Undo2 size={14} /></button>
        <button class="tb-btn" onclick={() => editor.redo()} disabled={!history.canRedo}
          title={_('Redo (Ctrl+Y / Ctrl+Shift+Z)')}
        ><Redo2 size={14} /></button>
        <div class="sep-inner"></div>
        <button class="tb-btn remove-btn" onclick={() => editor.cutCells()} disabled={!hasSelection}
          title={_('Cut cells (Ctrl+X)\nCut rows: Ctrl+Shift+X')}
        ><Scissors size={14} /></button>
        <button class="tb-btn" onclick={() => editor.copyCells()} disabled={!hasSelection}
          title={_('Copy cells (Ctrl+C)\nCopy rows: Ctrl+Shift+C')}
        ><Copy size={14} /></button>
        <button class="tb-btn" onclick={() => editor.pasteCells()} disabled={!editor.cellClipboard}
          title={_('Paste cells (Ctrl+V)\nPaste rows: Ctrl+Shift+V')}
        ><ClipboardPaste size={14} /></button>
      </div>

    {:else if groupId === 'align'}
      <!-- ALIGN -->
      <div class="group">
        <span class="group-label">{_('Align')}</span>
        <div class="align-btns">
          <button class="tb-btn" class:active={alignment === 'left'}
            onclick={() => editor.applyStyle({ alignment: 'left' })}
            disabled={!hasSelection} title={_('Align left (Ctrl+L)')}
          ><AlignLeft size={13} /></button>
          <button class="tb-btn" class:active={alignment === 'center'}
            onclick={() => editor.applyStyle({ alignment: 'center' })}
            disabled={!hasSelection} title={_('Center (Ctrl+E)')}
          ><AlignCenter size={13} /></button>
          <button class="tb-btn" class:active={alignment === 'right'}
            onclick={() => editor.applyStyle({ alignment: 'right' })}
            disabled={!hasSelection} title={_('Align right (Ctrl+R)')}
          ><AlignRight size={13} /></button>
          <button class="tb-btn" class:active={alignment === 'justify'}
            onclick={() => editor.applyStyle({ alignment: 'justify' })}
            disabled={!hasSelection} title={_('Justify')}
          ><AlignJustify size={13} /></button>
        </div>
        <div class="sep-inner"></div>
        <div class="align-btns">
          <button class="tb-btn" class:active={verticalAlignment === 'top'}
            onclick={() => editor.applyStyle({ verticalAlignment: 'top' })}
            disabled={!hasSelection} title={_('Align top (Ctrl+T)')}
          ><AlignVerticalJustifyStart size={13} /></button>
          <button class="tb-btn" class:active={verticalAlignment === 'middle'}
            onclick={() => editor.applyStyle({ verticalAlignment: 'middle' })}
            disabled={!hasSelection} title={_('Align middle (Ctrl+G)')}
          ><AlignVerticalJustifyCenter size={13} /></button>
          <button class="tb-btn" class:active={verticalAlignment === 'bottom'}
            onclick={() => editor.applyStyle({ verticalAlignment: 'bottom' })}
            disabled={!hasSelection} title={_('Align bottom (Ctrl+M)')}
          ><AlignVerticalJustifyEnd size={13} /></button>
        </div>
      </div>

    {:else if groupId === 'font'}
      <!-- FONT -->
      <div class="group">
        <span class="group-label">{_('Font')}</span>
        <select
          class="font-select"
          style="font-family: {fontFamily ?? 'inherit'}"
          disabled={!hasSelection}
          title={_('Font family')}
          onchange={(e) => {
            const v = (e.target as HTMLSelectElement).value;
            if (v) editor.applyStyle({ fontFamily: v });
          }}
        >
          {#if fontFamily === null}
            <option value="" disabled selected>{_('mixed')}</option>
          {/if}
          {#each config.config.fontFamilies as f}
            <option value={f} selected={f === fontFamily} style="font-family: {f}">{f}</option>
          {/each}
        </select>
        <input
          type="number"
          class="size-input"
          value={fontSize ?? ''}
          min="6"
          max="144"
          placeholder={fontSize === null ? '·' : ''}
          disabled={!hasSelection}
          title={_('Font size (pt)')}
          onchange={(e) => {
            const v = Number((e.target as HTMLInputElement).value);
            if (v >= 1) editor.applyStyle({ fontSize: v });
          }}
        />
        <span class="unit">pt</span>
        <div class="fmt-btns">
          <button
            class="tb-btn"
            class:active={fontWeight === 'bold'}
            onclick={() => editor.applyStyle({ fontWeight: fontWeight === 'bold' ? 'normal' : 'bold' })}
            disabled={!hasSelection}
            title={_('Bold (Ctrl+B)')}
          ><Bold size={13} /></button>
          <button
            class="tb-btn"
            class:active={fontStyleVal === 'italic'}
            onclick={() => editor.applyStyle({ fontStyle: fontStyleVal === 'italic' ? 'normal' : 'italic' })}
            disabled={!hasSelection}
            title={_('Italic (Ctrl+I)')}
          ><Italic size={13} /></button>
          <button
            class="tb-btn"
            class:active={textDecoration === 'underline'}
            onclick={() => editor.applyStyle({ textDecoration: textDecoration === 'underline' ? 'none' : 'underline' })}
            disabled={!hasSelection}
            title={_('Underline (Ctrl+U)')}
          ><Underline size={13} /></button>
        </div>
      </div>

    {:else if groupId === 'structure'}
      <!-- STRUCTURE -->
      <div class="group">
        <span class="group-label">{_('Structure')}</span>
        <button class="tb-btn" onclick={addCell} disabled={!activeRow}
          title={_('Add cell (Insert)')}
        ><SquarePlus size={13} /></button>
        <button class="tb-btn remove-btn" onclick={() => editor.deleteSelectedCells()} disabled={!hasSelection}
          title={_('Delete selected cells (Delete)')}
        ><Trash2 size={13} /></button>
        <div class="sep-inner"></div>
        <button class="tb-btn" onclick={addRow}
          title={_('Add row after current (Alt+Insert)')}
        ><ListPlus size={13} /></button>
        <button class="tb-btn remove-btn" onclick={deleteRow} disabled={!activeRow}
          title={_('Delete row (Alt+Delete)')}
        ><ListX size={13} /></button>
        <button class="tb-btn" onclick={moveRowUp} disabled={!activeRow}
          title={_('Move row up (Alt+↑)')}
        ><ArrowUp size={13} /></button>
        <button class="tb-btn" onclick={moveRowDown} disabled={!activeRow}
          title={_('Move row down (Alt+↓)')}
        ><ArrowDown size={13} /></button>
      </div>

    {:else if groupId === 'colors'}
      <!-- COLORS -->
      <div class="group">
        <span class="group-label">{_('Colors')}</span>
        <div class="color-item" title={textColorMixed ? _('Text color (mixed)') : _('Font color')}>
          <span class="color-label" class:mixed={textColorMixed}>{_('Text')}</span>
          <ColorPicker
            value={textColor}
            palette={config.config.fgPalette}
            mixed={textColorMixed}
            disabled={!hasSelection}
            onpick={(color) => editor.applyStyle({ color })}
          />
        </div>
        <div
          class="color-item"
          title={bgColorMixed ? _('Background color (mixed)') : _('Background color')}
        >
          <span class="color-label" class:mixed={bgColorMixed}>{_('BG')}</span>
          <ColorPicker
            value={bgColor}
            palette={config.config.bgPalette}
            mixed={bgColorMixed && !isBgTransparent}
            transparent={isBgTransparent}
            disabled={!hasSelection}
            onpick={(color) => editor.applyStyle({ backgroundColor: color })}
          />
        </div>
        <label class="transp-label" title={_('Transparent background')}>
          <input
            type="checkbox"
            checked={isBgTransparent}
            onchange={onTransparentToggle}
            disabled={!hasSelection}
          />
          <span>{_('transp.')}</span>
        </label>
      </div>

    {:else if groupId === 'borders'}
      <!-- BORDERS -->
      <div class="group">
        <span class="group-label">{_('Borders')}</span>
        <input
          type="number"
          class="width-input"
          value={borderWidth}
          min="1"
          max="10"
          title={_('Pen width (px)')}
          disabled={!hasSelection}
          onchange={(e) => { borderWidth = Number((e.target as HTMLInputElement).value); }}
        />
        <span class="unit">px</span>
        <select
          class="style-select"
          value={borderStyle}
          disabled={!hasSelection}
          title={_('Pen style')}
          onchange={(e) => {
            borderStyle = (e.target as HTMLSelectElement).value as BorderSide['style'];
          }}
        >
          <option value="solid">─── {_('solid')}</option>
          <option value="dashed">- - {_('dashed')}</option>
          <option value="dotted">··· {_('dotted')}</option>
          <option value="double">═══ {_('double')}</option>
        </select>
        <ColorPicker
          value={borderColor}
          palette={config.config.fgPalette}
          disabled={!hasSelection}
          onpick={(color) => { borderColor = color; }}
        />
        <div class="sides">
          {#each SIDES as s}
            <button
              class="side-btn"
              class:active={sideHasBorder(s.key)}
              onclick={() => clickSide(s.key)}
              title={_(s.titleKey)}
              disabled={!hasSelection}
            >{s.label}</button>
          {/each}
        </div>
        <button
          class="tb-btn remove-btn"
          onclick={removeAllBorders}
          disabled={!hasSelection}
          title={_('Remove all borders (Ctrl+0)')}
        ><SquareDashed size={13} /></button>
      </div>
    {/if}
  {/each}
</div>

<style>
  .toolbar {
    min-height: 32px;
    background: #f1f5f9;
    border-bottom: 1px solid #cbd5e1;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    padding: 4px 12px;
    gap: 8px;
    flex-shrink: 0;
    font-size: 11px;
  }

  .toolbar.disabled {
    opacity: 0.5;
  }

  .group {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .group-label {
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: #94a3b8;
    text-transform: uppercase;
    margin-right: 2px;
  }

  .sep {
    width: 1px;
    height: 20px;
    background: #cbd5e1;
    margin: 0 4px;
  }

  .color-item {
    display: flex;
    align-items: center;
    gap: 4px;
    cursor: pointer;
  }

  .color-label {
    color: #475569;
  }

  .mixed {
    font-style: italic;
    color: #94a3b8;
  }

  .transp-label {
    display: flex;
    align-items: center;
    gap: 3px;
    cursor: pointer;
    color: #475569;
  }

  .sides {
    display: flex;
    gap: 2px;
  }

  .side-btn {
    width: 22px;
    height: 22px;
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    background: white;
    font-size: 10px;
    font-weight: 700;
    cursor: pointer;
    color: #475569;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .side-btn.active {
    background: #2563eb;
    border-color: #1d4ed8;
    color: white;
  }

  .side-btn:disabled {
    cursor: default;
    opacity: 0.4;
  }

  .width-input {
    width: 36px;
    height: 22px;
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    padding: 0 4px;
    font-size: 11px;
    text-align: right;
    background: white;
  }

  .width-input:disabled {
    background: #f8fafc;
    color: #94a3b8;
  }

  .unit {
    color: #94a3b8;
    font-size: 10px;
  }

  .style-select {
    height: 22px;
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    font-size: 11px;
    background: white;
    padding: 0 4px;
  }

  .style-select:disabled {
    background: #f8fafc;
    color: #94a3b8;
  }

  .remove-btn {
    color: #ef4444;
  }

  .remove-btn:hover:not(:disabled) {
    background: #fef2f2;
    border-color: #ef4444;
  }

  .tb-btn {
    width: 22px;
    height: 22px;
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    background: white;
    cursor: pointer;
    color: #475569;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
  }

  .tb-btn:hover:not(:disabled) {
    background: #f1f5f9;
    border-color: #94a3b8;
  }

  .tb-btn.active {
    background: #2563eb;
    border-color: #1d4ed8;
    color: white;
  }

  .tb-btn:disabled {
    cursor: default;
    opacity: 0.4;
  }

  .align-btns {
    display: flex;
    gap: 2px;
  }

  .sep-inner {
    width: 1px;
    height: 16px;
    background: #e2e8f0;
    margin: 0 2px;
  }

  .font-select {
    width: 140px;
    height: 22px;
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    padding: 0 4px;
    font-size: 12px;
    background: white;
  }

  .font-select:disabled {
    background: #f8fafc;
    color: #94a3b8;
  }

  .size-input {
    width: 40px;
    height: 22px;
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    padding: 0 4px;
    font-size: 11px;
    text-align: right;
    background: white;
  }

  .size-input:disabled {
    background: #f8fafc;
    color: #94a3b8;
  }

  .fmt-btns {
    display: flex;
    gap: 2px;
  }
</style>
