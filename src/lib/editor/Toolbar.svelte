<script lang="ts">
  import { untrack } from 'svelte';
  import { editor } from '$lib/store/editor.svelte';
  import type { BorderSide } from '$lib/types';

  type BorderSideName = 'top' | 'bottom' | 'left' | 'right';
  const ALL_SIDES: BorderSideName[] = ['top', 'bottom', 'left', 'right'];

  // --- current selection ---
  const cells = $derived(editor.selectedCells);
  const hasSelection = $derived(cells.length > 0);

  // Returns the value if uniform across all selected cells, null if mixed
  function uniformVal<T>(getter: (c: typeof cells[0]) => T): T | null {
    if (cells.length === 0) return null;
    const first = getter(cells[0]);
    return cells.every((c) => getter(c) === first) ? first : null;
  }

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

  function onTextColorChange(e: Event) {
    editor.applyStyle({ color: (e.target as HTMLInputElement).value });
  }

  function onBgColorChange(e: Event) {
    editor.applyStyle({ backgroundColor: (e.target as HTMLInputElement).value });
  }

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

  const SIDES: { key: BorderSideName; label: string; title: string }[] = [
    { key: 'top', label: 'T', title: 'Top border — click to apply pen, click again to remove (Ctrl+3)' },
    { key: 'bottom', label: 'B', title: 'Bottom border — click to apply pen, click again to remove (Ctrl+4)' },
    { key: 'left', label: 'L', title: 'Left border — click to apply pen, click again to remove (Ctrl+1)' },
    { key: 'right', label: 'R', title: 'Right border — click to apply pen, click again to remove (Ctrl+2)' },
  ];
</script>

<div class="toolbar" class:disabled={!hasSelection}>
  <!-- COLORS -->
  <div class="group">
    <span class="group-label">COLORS</span>

    <label class="color-item" title={textColorMixed ? 'Text color (mixed values)' : 'Text color'}>
      <span class="color-label" class:mixed={textColorMixed}>Text</span>
      <div class="color-swatch-wrap">
        <input
          type="color"
          value={textColor}
          onchange={onTextColorChange}
          disabled={!hasSelection}
        />
        <div
          class="color-preview"
          class:mixed-preview={textColorMixed}
          style="background:{textColor}"
        ></div>
      </div>
    </label>

    <label
      class="color-item"
      title={bgColorMixed ? 'Background color (mixed values)' : 'Background color'}
    >
      <span class="color-label" class:mixed={bgColorMixed}>BG</span>
      <div class="color-swatch-wrap">
        <input
          type="color"
          value={bgColor}
          onchange={onBgColorChange}
          disabled={!hasSelection || isBgTransparent}
        />
        <div
          class="color-preview"
          class:transparent-preview={isBgTransparent}
          class:mixed-preview={bgColorMixed && !isBgTransparent}
          style="background:{isBgTransparent ? 'transparent' : bgColor}"
        ></div>
      </div>
    </label>

    <label class="transp-label" title="Transparent background">
      <input
        type="checkbox"
        checked={isBgTransparent}
        onchange={onTransparentToggle}
        disabled={!hasSelection}
      />
      <span>transp.</span>
    </label>
  </div>

  <div class="sep"></div>

  <!-- BORDERS -->
  <div class="group">
    <span class="group-label">BORDERS</span>

    <!-- Pen: width -->
    <input
      type="number"
      class="width-input"
      value={borderWidth}
      min="1"
      max="10"
      title="Pen width (px)"
      disabled={!hasSelection}
      onchange={(e) => {
        borderWidth = Number((e.target as HTMLInputElement).value);
      }}
    />
    <span class="unit">px</span>

    <!-- Pen: style -->
    <select
      class="style-select"
      value={borderStyle}
      disabled={!hasSelection}
      title="Pen style"
      onchange={(e) => {
        borderStyle = (e.target as HTMLSelectElement).value as BorderSide['style'];
      }}
    >
      <option value="solid">─── solid</option>
      <option value="dashed">- - dashed</option>
      <option value="dotted">··· dotted</option>
      <option value="double">═══ double</option>
    </select>

    <!-- Pen: color -->
    <label class="color-item" title="Pen color">
      <div class="color-swatch-wrap">
        <input
          type="color"
          value={borderColor}
          disabled={!hasSelection}
          onchange={(e) => {
            borderColor = (e.target as HTMLInputElement).value;
          }}
        />
        <div class="color-preview" style="background:{borderColor}"></div>
      </div>
    </label>

    <!-- Side buttons: click to apply pen, click again to remove -->
    <div class="sides">
      {#each SIDES as s}
        <button
          class="side-btn"
          class:active={sideHasBorder(s.key)}
          onclick={() => clickSide(s.key)}
          title={s.title}
          disabled={!hasSelection}
        >
          {s.label}
        </button>
      {/each}
    </div>

    <!-- Remove all borders -->
    <button
      class="remove-btn"
      onclick={removeAllBorders}
      disabled={!hasSelection}
      title="Remove all borders (Ctrl+0)"
    >
      ✕ all
    </button>
  </div>
</div>

<style>
  .toolbar {
    height: 32px;
    background: #f1f5f9;
    border-bottom: 1px solid #cbd5e1;
    display: flex;
    align-items: center;
    padding: 0 12px;
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

  .color-swatch-wrap {
    position: relative;
    width: 22px;
    height: 22px;
  }

  .color-swatch-wrap input[type='color'] {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    opacity: 0;
    cursor: pointer;
    border: none;
    padding: 0;
  }

  .color-swatch-wrap input[type='color']:disabled {
    cursor: default;
  }

  .color-preview {
    width: 22px;
    height: 22px;
    border: 1px solid #94a3b8;
    border-radius: 3px;
    pointer-events: none;
  }

  .mixed {
    font-style: italic;
    color: #94a3b8;
  }

  .mixed-preview {
    background-image: repeating-linear-gradient(
      45deg,
      #aaa 0px,
      #aaa 2px,
      #ddd 2px,
      #ddd 5px
    ) !important;
  }

  .transparent-preview {
    background-image: linear-gradient(45deg, #ccc 25%, transparent 25%),
      linear-gradient(-45deg, #ccc 25%, transparent 25%),
      linear-gradient(45deg, transparent 75%, #ccc 75%),
      linear-gradient(-45deg, transparent 75%, #ccc 75%);
    background-size: 6px 6px;
    background-position:
      0 0,
      0 3px,
      3px -3px,
      -3px 0px;
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
    height: 22px;
    padding: 0 8px;
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    background: white;
    font-size: 11px;
    cursor: pointer;
    color: #ef4444;
  }

  .remove-btn:hover:not(:disabled) {
    background: #fef2f2;
    border-color: #ef4444;
  }

  .remove-btn:disabled {
    cursor: default;
    opacity: 0.4;
  }
</style>
