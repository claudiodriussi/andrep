<script lang="ts">
  import { onMount } from 'svelte';
  import DesignCanvas from '$lib/editor/DesignCanvas.svelte';
  import Toolbar from '$lib/editor/Toolbar.svelte';
  import { editor } from '$lib/store/editor.svelte';

  const selectedCell = $derived(
    editor.activeCellId ? editor.findCell(editor.activeCellId) : null,
  );

  // Autosave draft to localStorage on every template change (debounced)
  let saveTimer: ReturnType<typeof setTimeout> | null = null;
  $effect(() => {
    // Touch template to track changes — JSON.stringify reads all nested properties
    JSON.stringify(editor.template);
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(() => editor.saveDraft(), 500);
  });

  onMount(() => {
    return () => {
      if (saveTimer) clearTimeout(saveTimer);
    };
  });
</script>

<div class="editor-root">
  <header class="header">
    <span class="app-name">AndRep</span>

    <div class="sep"></div>

    <button class="hbtn" onclick={() => editor.loadJson()} title="Open template (Ctrl+O)">
      ⬆ Open
    </button>
    <button class="hbtn" onclick={() => editor.saveJson()} title="Save template (Ctrl+S)">
      ⬇ Save
    </button>

    <div class="spacer"></div>

    {#if selectedCell}
      <span class="cell-info">
        w:{selectedCell.width}px · h:{selectedCell.height}px · x:{selectedCell.x}px
      </span>
    {/if}

    <button
      class="hbtn"
      class:active={editor.showGuides}
      onclick={() => editor.toggleGuides()}
      title="Toggle design guides"
    >
      ⊞ Guides
    </button>
  </header>

  <Toolbar />

  <DesignCanvas />
</div>

<style>
  .editor-root {
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
  }

  .header {
    height: 36px;
    background: #1e293b;
    color: white;
    display: flex;
    align-items: center;
    padding: 0 12px;
    gap: 6px;
    flex-shrink: 0;
  }

  .app-name {
    font-weight: 700;
    font-size: 14px;
    letter-spacing: 0.05em;
    color: #e2e8f0;
    margin-right: 4px;
  }

  .sep {
    width: 1px;
    height: 20px;
    background: #334155;
  }

  .spacer {
    flex: 1;
  }

  .cell-info {
    font-size: 11px;
    color: #94a3b8;
    font-family: monospace;
    margin-right: 8px;
  }

  .hbtn {
    padding: 3px 10px;
    font-size: 11px;
    background: transparent;
    border: 1px solid #475569;
    border-radius: 3px;
    color: #cbd5e1;
    cursor: pointer;
  }

  .hbtn:hover {
    background: #334155;
    border-color: #64748b;
    color: #e2e8f0;
  }

  .hbtn.active {
    background: #334155;
    border-color: #64748b;
    color: #e2e8f0;
  }
</style>
