<script lang="ts">
  import DesignCanvas from '$lib/editor/DesignCanvas.svelte';
  import { editor } from '$lib/store/editor.svelte';

  // Info cella: mostra la cella attiva (ultima cliccata)
  const selectedCell = $derived(
    editor.activeCellId ? editor.findCell(editor.activeCellId) : null,
  );
</script>

<div class="editor-root">
  <header class="toolbar">
    <span class="app-name">AndRep</span>
    {#if selectedCell}
      <span class="cell-info">
        w:{selectedCell.width}px · h:{selectedCell.height}px · x:{selectedCell.x}px
      </span>
    {/if}
    <span class="spacer"></span>
    <button
      class="guide-toggle"
      class:active={editor.showGuides}
      onclick={() => editor.toggleGuides()}
      title="Mostra/nascondi bordi celle"
    >
      ⊞ Guide
    </button>
  </header>
  <DesignCanvas />
</div>

<style>
  .editor-root {
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
  }

  .toolbar {
    height: 36px;
    background: #1e293b;
    color: white;
    display: flex;
    align-items: center;
    padding: 0 16px;
    gap: 24px;
    flex-shrink: 0;
  }

  .app-name {
    font-weight: 700;
    font-size: 14px;
    letter-spacing: 0.05em;
    color: #e2e8f0;
  }

  .cell-info {
    font-size: 11px;
    color: #94a3b8;
    font-family: monospace;
  }

  .spacer {
    flex: 1;
  }

  .guide-toggle {
    padding: 3px 10px;
    font-size: 11px;
    background: transparent;
    border: 1px solid #475569;
    border-radius: 3px;
    color: #94a3b8;
    cursor: pointer;
  }

  .guide-toggle.active {
    background: #334155;
    border-color: #64748b;
    color: #e2e8f0;
  }
</style>
