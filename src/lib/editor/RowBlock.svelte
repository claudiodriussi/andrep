<script lang="ts">
  import type { Row } from '$lib/types';
  import { editor } from '$lib/store/editor.svelte';
  import CellBlock from './CellBlock.svelte';

  let {
    row,
    isFirst,
    isLast,
  }: {
    row: Row;
    isFirst: boolean;
    isLast: boolean;
  } = $props();

  const rowHeight = $derived(
    row.cells.length > 0 ? Math.max(...row.cells.map((c) => c.height)) : 24,
  );

  let editing = $state(false);
  let editName = $state('');
  let nameInput = $state<HTMLInputElement | null>(null);

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

<div class="row-block" style="height: {rowHeight}px">
  <div class="band-col">
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
        title="Click per selezionare la riga · Doppio click per rinominare"
      >{row.name}</span>
    {/if}
    <div class="row-controls">
      <button
        class="ctrl-btn"
        disabled={isFirst}
        onclick={() => editor.moveRowUp(row.id)}
        title="Sposta su (Alt+↑)"
      >▲</button>
      <button
        class="ctrl-btn"
        disabled={isLast}
        onclick={() => editor.moveRowDown(row.id)}
        title="Sposta giù (Alt+↓)"
      >▼</button>
      <button
        class="ctrl-btn del"
        onclick={() => editor.deleteRow(row.id)}
        title="Elimina riga (Alt+Del)"
      >×</button>
    </div>
  </div>

  <div class="cells-area">
    {#each row.cells as cell (cell.id)}
      <CellBlock {cell} />
    {/each}
    <button
      class="add-cell-btn"
      style="height: {rowHeight}px"
      onclick={() => editor.addCell(row.id)}
      title="Aggiungi cella (Ins)"
    >+</button>
  </div>
</div>

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
    display: flex;
    align-items: flex-start;
  }

  .add-cell-btn {
    width: 20px;
    min-width: 20px;
    flex-shrink: 0;
    background: transparent;
    border: 1px dashed #94a3b8;
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
