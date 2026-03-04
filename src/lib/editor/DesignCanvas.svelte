<script lang="ts">
  import { editor } from '$lib/store/editor.svelte';
  import { _ } from '$lib/i18n/index.svelte';
  import RowBlock from './RowBlock.svelte';

  let newRowName = $state('');
  let showRowInput = $state(false);
  let inputEl = $state<HTMLInputElement | null>(null);

  // Band column width: adapts to the longest band name.
  // Estimated 7px/char + 38px for the 3 control buttons (11px × 3 + padding + gap)
  const BTN_AREA = 38;
  const CHAR_W = 7;
  const bandColW = $derived(
    Math.max(80, ...editor.template.rows.map((r) => r.name.length * CHAR_W + BTN_AREA)),
  );

  function confirmAddRow() {
    const name = newRowName.trim();
    if (name) {
      editor.addRow(name);
      newRowName = '';
      showRowInput = false;
    }
  }

  function startAddRow() {
    showRowInput = true;
    setTimeout(() => inputEl?.focus(), 0);
  }
</script>

<svelte:window
  onkeydown={(e) => {
    if (e.key === 'a' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      editor.selectAll();
    }
  }}
/>

<div
  class="canvas"
  style="--band-col-w: {bandColW}px"
  onclick={() => editor.clearSelection()}
  role="presentation"
>
  <!-- Header row: band column label + ruler placeholder -->
  <div class="header-row">
    <div class="band-col-header">{_('Band')}</div>
    <div class="ruler-placeholder">
      <!-- horizontal ruler — phase 2 -->
    </div>
  </div>

  <!-- Flat row list -->
  {#each editor.template.rows as row, i (row.id)}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div role="presentation" onclick={(e) => e.stopPropagation()}>
      <RowBlock
        {row}
        isFirst={i === 0}
        isLast={i === editor.template.rows.length - 1}
      />
    </div>
  {/each}

  <!-- Add row -->
  <div class="add-row-area">
    {#if showRowInput}
      <input
        bind:this={inputEl}
        bind:value={newRowName}
        class="row-input"
        placeholder={_('Row name (e.g. Header, Band, Footer)...')}
        onclick={(e) => e.stopPropagation()}
        onkeydown={(e) => {
          if (e.key === 'Enter') confirmAddRow();
          if (e.key === 'Escape') {
            showRowInput = false;
            newRowName = '';
          }
        }}
      />
      <button class="btn-ok" onclick={confirmAddRow}>OK</button>
      <button
        class="btn-cancel"
        onclick={() => {
          showRowInput = false;
          newRowName = '';
        }}>×</button
      >
    {:else}
      <button class="add-row-btn" onclick={startAddRow}>{_('+ Row')}</button>
    {/if}
  </div>
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

  .ruler-placeholder {
    flex: 1;
  }

  .add-row-area {
    padding: 10px 12px 10px calc(var(--band-col-w, 120px) + 8px);
    display: flex;
    align-items: center;
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
