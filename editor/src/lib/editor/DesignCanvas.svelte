<script lang="ts">
  import { editor } from '$lib/store/editor.svelte';
  import { config } from '$lib/store/config.svelte';
  import { _ } from '$lib/i18n/index.svelte';
  import RowBlock from './RowBlock.svelte';
  import HRuler from './HRuler.svelte';
  import { handleKeydown } from './keyboard';

  let newRowName = $state('');
  let showRowInput = $state(false);
  let inputEl = $state<HTMLInputElement | null>(null);

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
  const BTN_AREA = 42;
  const CHAR_W = 8;
  const bandColW = $derived.by(() => {
    const names = editor.template.rows.map((r) => r.name);
    // include the name being typed so the column expands in real time
    if (showRowInput && newRowName.trim()) names.push(newRowName.trim());
    return Math.max(80, ...names.map((n) => n.length * CHAR_W + BTN_AREA));
  });

  function addRow(name: string) {
    editor.addRow(name);
    newRowName = '';
    showRowInput = false;
  }

  function confirmAddRow() {
    const name = newRowName.trim();
    if (name) addRow(name);
  }

  function startAddRow() {
    showRowInput = true;
    newRowName = '';
    setTimeout(() => inputEl?.focus(), 0);
  }
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
    {#if showRowInput}
      <input
        bind:this={inputEl}
        bind:value={newRowName}
        class="row-input"
        list="band-name-list"
        onclick={(e) => e.stopPropagation()}
        onkeydown={(e) => {
          e.stopPropagation();
          if (e.key === 'Enter') confirmAddRow();
          if (e.key === 'Escape') { showRowInput = false; newRowName = ''; }
        }}
      />
      <datalist id="band-name-list">
        {#each config.config.bandNamePresets as name (name)}
          <option value={name}></option>
        {/each}
      </datalist>
      <button class="btn-ok" onclick={confirmAddRow}>OK</button>
      <button class="btn-cancel" onclick={() => { showRowInput = false; newRowName = ''; }}>×</button>
    {:else}
      <button class="add-row-btn" onclick={startAddRow}>{_('+ Row')}</button>
    {/if}
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

  .row-input {
    padding: 3px 8px;
    border: 1px solid #3b82f6;
    border-radius: 4px;
    font-size: 12px;
    width: 280px;
    outline: none;
  }

  .btn-ok {
    padding: 3px 10px;
    background: #2563eb;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
  }

  .btn-cancel {
    padding: 3px 8px;
    background: transparent;
    color: #64748b;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
  }
</style>
