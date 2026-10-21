<script lang="ts">
  import { editor } from '$lib/store/editor.svelte';
  import { _ } from '$lib/i18n/index.svelte';
  import RowBlock from './RowBlock.svelte';
  import HRuler from './HRuler.svelte';
  import { handleKeydown } from './keyboard';

  const page = $derived(editor.template.page);

  // For each row, whether it is the first global occurrence of its band name
  const firstOfBand = $derived.by(() => {
    const seen = new Set<string>();
    return editor.template.rows.map((row) => {
      if (seen.has(row.name)) return false;
      seen.add(row.name);
      return true;
    });
  });

  // Band column width: adapts to the longest band name.
  // 8px/char (bold 11px, slightly generous to avoid clipping) + 42px for controls + padding
  const BTN_AREA = 57; // padding(6) + opts-btn(14) + gaps(4) + controls(33)
  const CHAR_W = 8;
  const bandColW = $derived.by(() => {
    const names = editor.template.rows.map((r) => r.name);
    return Math.max(80, ...names.map((n) => n.length * CHAR_W + BTN_AREA));
  });
</script>

<svelte:window onkeydown={handleKeydown} />

<div
  class="canvas"
  style="--band-col-w: {bandColW}px"
  onclick={() => editor.clearSelection()}
  role="presentation"
>
  <!-- Header row: band column label + ruler -->
  <div class="header-row">
    <div class="band-col-header">{_('Band')}</div>
    <HRuler />
  </div>

  <!-- Rows wrapper — page guide lines via CSS background -->
  <div
    class="rows-wrapper"
    style="
      --guide-cw: {bandColW + page.width - page.marginLeft - page.marginRight}px;
      --guide-pr: {bandColW + page.width}px;
    "
  >
    {#each editor.template.rows as row, i (row.id)}
      <div role="presentation" onclick={(e) => e.stopPropagation()}>
        <RowBlock
          {row}
          isFirst={i === 0}
          isLast={i === editor.template.rows.length - 1}
          isFirstOfBand={firstOfBand[i]}
        />
      </div>
    {/each}

    <!-- Add row -->
    <div class="add-row-area" role="presentation" onclick={(e) => e.stopPropagation()}>
      <button class="add-row-btn" onclick={() => editor.openAddRow()}>{_('+ Row')}</button>
  </div>
  </div><!-- rows-wrapper -->
</div>

<style>
  .canvas {
    overflow-x: auto;
    overflow-y: auto;
    flex: 1;
    background: #f8fafc;
    min-height: 0;
  }

  .header-row {
    display: flex;
    height: 22px;
    background: #dde3ea;
    border-bottom: 2px solid #94a3b8;
    position: sticky;
    top: 0;
    z-index: 20;
  }

  .band-col-header {
    position: sticky;
    left: 0;
    width: var(--band-col-w, 120px);
    min-width: var(--band-col-w, 120px);
    background: #dde3ea;
    border-right: 2px solid #94a3b8;
    display: flex;
    align-items: center;
    padding: 0 6px;
    font-size: 10px;
    font-weight: 700;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    z-index: 21;
  }

  /* Page guide lines: left-margin, right-margin, page-right-edge */
  /* Guide lines: content-width boundary (blue) + physical page edge (gray) */
  .rows-wrapper {
    background:
      linear-gradient(to bottom, #3b82f660, #3b82f660) var(--guide-cw) 0 / 1px 100% no-repeat,
      linear-gradient(to bottom, #47556980, #47556980) var(--guide-pr) 0 / 1px 100% no-repeat;
  }

  .add-row-area {
    padding: 10px 12px 10px calc(var(--band-col-w, 120px) + 8px);
    display: flex;
    align-items: flex-start;
    gap: 6px;
  }

  .add-row-btn {
    padding: 5px 14px;
    background: #2563eb;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 500;
  }

  .add-row-btn:hover {
    background: #1d4ed8;
  }
</style>
