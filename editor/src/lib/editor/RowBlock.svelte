<script lang="ts">
  import type { Row } from '$lib/types';
  import { editor } from '$lib/store/editor.svelte';
  import { _ } from '$lib/i18n/index.svelte';
  import CellBlock from './CellBlock.svelte';

  const MM_TO_PX = 3.7795275591;

  let {
    row,
    isFirst,
    isLast,
    isFirstOfBand,
  }: { row: Row; isFirst: boolean; isLast: boolean; isFirstOfBand: boolean } = $props();

  const keepTogether = $derived(editor.getBandOptions(row.name).keepTogether ?? false);
  const bandCols     = $derived(editor.getBandOptions(row.name).columns      ?? 1);
  const bandColGap   = $derived(editor.getBandOptions(row.name).columnGap    ?? 0);

  // Derived: is any band option non-default?
  const hasOptions = $derived(keepTogether || bandCols > 1);

  // Button label: number if multi-column, lock if keepTogether only, default icon otherwise
  const optsBtnLabel = $derived(
    bandCols > 1 ? String(bandCols) : keepTogether ? '🔒' : '⊟',
  );

  // Column separator line positions (px relative to cells-area left = content area left)
  const page = $derived(editor.template.page);
  const contentWidth = $derived(page.width - page.marginLeft - page.marginRight);
  const colWidth = $derived(
    bandCols > 1 ? Math.max(0, (contentWidth - bandColGap * (bandCols - 1)) / bandCols) : contentWidth,
  );
  const colSepLines = $derived.by(() => {
    if (bandCols <= 1) return [] as number[];
    const lines: number[] = [];
    for (let i = 1; i < bandCols; i++) {
      const gapStart = i * colWidth + (i - 1) * bandColGap;
      lines.push(gapStart);
      if (bandColGap > 0) lines.push(gapStart + bandColGap);
    }
    return lines;
  });

  const rowHeight = $derived(
    row.cells.length > 0 ? Math.max(...row.cells.map((c) => c.height)) : 24,
  );
  // Visual minimum: always show at least 10px so the row remains clickable in the editor
  const displayHeight = $derived(Math.max(10, rowHeight));

  let editing = $state(false);
  let editName = $state('');
  let nameInput = $state<HTMLInputElement | null>(null);

  // --- band options popup ---
  let bandPopupOpen  = $state(false);
  let bandPopupStyle = $state('');
  let popupKeepTogether = $state(false);
  let popupCols      = $state(1);
  let popupGapMm     = $state(0);

  function openBandPopup(e: MouseEvent) {
    e.stopPropagation();
    const btn = e.currentTarget as HTMLElement;
    const rect = btn.getBoundingClientRect();
    bandPopupStyle = `top: ${rect.bottom + 4}px; left: ${rect.left}px`;
    popupKeepTogether = keepTogether;
    popupCols  = bandCols;
    popupGapMm = Math.round((bandColGap / MM_TO_PX) * 10) / 10;
    bandPopupOpen = true;
  }

  function applyBandPopup() {
    const cols  = Math.max(1, Math.min(10, Math.round(popupCols)));
    const gapPx = cols > 1 && popupGapMm > 0 ? Math.round(popupGapMm * MM_TO_PX) : 0;
    // Apply keepTogether if changed
    if (popupKeepTogether !== keepTogether) editor.toggleBandKeepTogether(row.name);
    editor.setBandColumns(row.name, cols, gapPx);
    bandPopupOpen = false;
  }

  function onBandPopupKey(e: KeyboardEvent) {
    if (e.key === 'Enter') { e.preventDefault(); applyBandPopup(); }
    if (e.key === 'Escape') { e.preventDefault(); bandPopupOpen = false; }
  }

  function startEdit() {
    editName = row.name;
    editing = true;
    setTimeout(() => nameInput?.select(), 0);
  }

  function confirmEdit() {
    editor.renameRow(row.id, editName);
    editing = false;
  }

  function cancelEdit() {
    editing = false;
  }
</script>

<svelte:window
  onclick={() => { if (bandPopupOpen) bandPopupOpen = false; }}
  onkeydown={(e) => { if (e.key === 'Escape' && bandPopupOpen) bandPopupOpen = false; }}
/>

<div class="row-block" style="height: {displayHeight}px">
  <div class="band-col">
    {#if isFirstOfBand}
      <button
        class="opts-btn"
        class:active={hasOptions}
        onclick={openBandPopup}
        title={_('Band options')}
      >{optsBtnLabel}</button>
    {:else}
      <span class="opts-spacer"></span>
    {/if}
    {#if editing}
      <input
        bind:this={nameInput}
        bind:value={editName}
        class="band-name-input"
        onblur={confirmEdit}
        onkeydown={(e) => {
          if (e.key === 'Enter') { confirmEdit(); e.preventDefault(); }
          if (e.key === 'Escape') { cancelEdit(); e.preventDefault(); }
        }}
      />
    {:else}
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <span
        class="band-name"
        role="button"
        tabindex="0"
        onclick={(e) => { e.stopPropagation(); editor.selectRow(row.id); }}
        ondblclick={startEdit}
        title={_('Click to select · Double-click to rename')}
      >{row.name}</span>
    {/if}
    <div class="row-controls">
      <button
        class="ctrl-btn"
        disabled={isFirst}
        onclick={() => editor.moveRowUp(row.id)}
        title={_('Move up (Alt+↑)')}
      >▲</button>
      <button
        class="ctrl-btn"
        disabled={isLast}
        onclick={() => editor.moveRowDown(row.id)}
        title={_('Move down (Alt+↓)')}
      >▼</button>
      <button
        class="ctrl-btn del"
        onclick={() => editor.deleteRow(row.id)}
        title={_('Delete row (Alt+Del)')}
      >×</button>
    </div>
  </div>

  <div class="cells-area">
    {#each colSepLines as px (px)}
      <div class="col-sep-line" style="left: {px}px; height: {displayHeight}px"></div>
    {/each}
    {#each row.cells as cell (cell.id)}
      <CellBlock {cell} />
    {/each}
    <button
      class="add-cell-btn"
      style="height: {displayHeight}px"
      onclick={() => editor.addCell(row.id)}
      title={_('Add cell (Ins)')}
    >+</button>
  </div>
</div>

{#if bandPopupOpen}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="band-popup"
    style={bandPopupStyle}
    onclick={(e) => e.stopPropagation()}
    onkeydown={onBandPopupKey}
  >
    <div class="band-popup-title">{_('Band options')}</div>

    <div class="band-popup-row">
      <label class="band-popup-check-label">
        <input type="checkbox" bind:checked={popupKeepTogether} />
        {_('Keep together')}
      </label>
    </div>

    <div class="band-popup-row">
      <label class="band-popup-label" for="bp-cols">{_('Columns')}</label>
      <input id="bp-cols" class="band-popup-num" type="number" min="1" max="10" step="1"
        bind:value={popupCols} />
    </div>
    {#if popupCols > 1}
      <div class="band-popup-row">
        <label class="band-popup-label" for="bp-gap">{_('Gap')}</label>
        <input id="bp-gap" class="band-popup-num" type="number" min="0" max="100" step="0.1"
          bind:value={popupGapMm} />
        <span class="band-popup-unit">mm</span>
      </div>
    {/if}

    <div class="band-popup-footer">
      <button class="band-popup-cancel" onclick={() => bandPopupOpen = false}>{_('Cancel')}</button>
      <button class="band-popup-ok" onclick={applyBandPopup}>OK</button>
    </div>
  </div>
{/if}

<style>
  .row-block {
    display: flex;
    border-bottom: 1px solid #e5e7eb;
  }

  .band-col {
    position: sticky;
    left: 0;
    width: var(--band-col-w, 120px);
    min-width: var(--band-col-w, 120px);
    background: #eef2f7;
    border-right: 2px solid #94a3b8;
    display: flex;
    align-items: center;
    padding: 0 3px;
    gap: 2px;
    z-index: 10;
    overflow: hidden;
  }

  .opts-btn {
    width: 14px;
    height: 14px;
    background: transparent;
    border: none;
    padding: 0;
    margin: 0;
    font-size: 9px;
    line-height: 14px;
    text-align: center;
    cursor: pointer;
    flex-shrink: 0;
    box-sizing: border-box;
    color: #64748b;
    opacity: 0;
    transition: opacity 0.12s;
  }

  .band-col:hover .opts-btn {
    opacity: 0.45;
  }

  .opts-btn:hover {
    opacity: 1 !important;
  }

  .opts-btn.active {
    opacity: 1;
    color: #2563eb;
    font-weight: 700;
  }

  .opts-spacer {
    width: 14px;
    height: 14px;
    flex-shrink: 0;
    box-sizing: border-box;
  }

  .band-name {
    flex: 1;
    font-size: 11px;
    font-weight: 600;
    color: #374151;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
    cursor: default;
  }

  .band-name-input {
    flex: 1;
    min-width: 0;
    font-size: 11px;
    font-weight: 600;
    color: #1e3a5f;
    background: #fff;
    border: 1px solid #3b82f6;
    border-radius: 2px;
    padding: 0 2px;
    outline: none;
    height: 16px;
  }

  .row-controls {
    display: flex;
    flex-direction: row;
    gap: 0;
    flex-shrink: 0;
  }

  .ctrl-btn {
    width: 11px;
    height: 11px;
    padding: 0;
    font-size: 7px;
    line-height: 1;
    background: transparent;
    border: none;
    color: #94a3b8;
    cursor: pointer;
    border-radius: 1px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .ctrl-btn:hover:not(:disabled) {
    background: #dbeafe;
    color: #2563eb;
  }

  .ctrl-btn.del:hover:not(:disabled) {
    background: #fee2e2;
    color: #dc2626;
  }

  .ctrl-btn:disabled {
    opacity: 0.25;
    cursor: default;
  }

  .cells-area {
    position: relative;
    display: flex;
    align-items: flex-start;
  }

  .col-sep-line {
    position: absolute;
    top: 0;
    width: 1px;
    background: rgba(16, 185, 129, 0.55); /* teal — distinct from the blue page guide */
    pointer-events: none;
  }

  /* Band options popup — fixed so it escapes all overflow containers */
  .band-popup {
    position: fixed;
    z-index: 500;
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 5px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
    padding: 8px 10px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    min-width: 170px;
  }

  .band-popup-title {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: #94a3b8;
    padding-bottom: 4px;
    border-bottom: 1px solid #e2e8f0;
  }

  .band-popup-row {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .band-popup-check-label {
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 11px;
    color: #374151;
    cursor: pointer;
    user-select: none;
  }

  .band-popup-label {
    font-size: 11px;
    color: #64748b;
    min-width: 52px;
    flex-shrink: 0;
  }

  .band-popup-num {
    width: 52px;
    background: #fff;
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    color: #1e293b;
    font-size: 12px;
    padding: 3px 5px;
  }

  .band-popup-num:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
  }

  .band-popup-unit {
    font-size: 11px;
    color: #94a3b8;
  }

  .band-popup-footer {
    display: flex;
    justify-content: flex-end;
    gap: 6px;
    margin-top: 2px;
  }

  .band-popup-cancel {
    padding: 3px 10px;
    font-size: 11px;
    background: transparent;
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    color: #475569;
    cursor: pointer;
  }
  .band-popup-cancel:hover { background: #f1f5f9; }

  .band-popup-ok {
    padding: 3px 10px;
    font-size: 11px;
    background: #2563eb;
    border: 1px solid #1d4ed8;
    border-radius: 3px;
    color: white;
    cursor: pointer;
    font-weight: 500;
  }
  .band-popup-ok:hover { background: #1d4ed8; }

  .add-cell-btn {
    width: 20px;
    min-width: 20px;
    flex-shrink: 0;
    background: transparent;
    border: 1px solid #94a3b8;
    color: #6b7280;
    font-size: 14px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-left: 2px;
  }

  .add-cell-btn:hover {
    background: #dbeafe;
    border-color: #3b82f6;
    color: #2563eb;
  }
</style>
