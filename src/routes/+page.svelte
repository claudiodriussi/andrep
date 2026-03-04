<script lang="ts">
  import { onMount } from 'svelte';
  import DesignCanvas from '$lib/editor/DesignCanvas.svelte';
  import Toolbar from '$lib/editor/Toolbar.svelte';
  import { editor } from '$lib/store/editor.svelte';
  import { config } from '$lib/store/config.svelte';
  import { _ } from '$lib/i18n/index.svelte';

  const selectedCell = $derived(
    editor.activeCellId ? editor.findCell(editor.activeCellId) : null,
  );

  // Autosave template draft to localStorage on every change (debounced 500ms)
  let templateSaveTimer: ReturnType<typeof setTimeout> | null = null;
  $effect(() => {
    JSON.stringify(editor.template); // touch all nested properties to track changes
    if (templateSaveTimer) clearTimeout(templateSaveTimer);
    templateSaveTimer = setTimeout(() => editor.saveDraft(), 500);
  });

  // Autosave config to localStorage on every change (debounced 500ms)
  let configSaveTimer: ReturnType<typeof setTimeout> | null = null;
  $effect(() => {
    JSON.stringify(config.config); // touch all nested properties to track changes
    if (configSaveTimer) clearTimeout(configSaveTimer);
    configSaveTimer = setTimeout(() => config.save(), 500);
  });

  onMount(() => {
    return () => {
      if (templateSaveTimer) clearTimeout(templateSaveTimer);
      if (configSaveTimer) clearTimeout(configSaveTimer);
    };
  });

  let showConfigMenu = $state(false);
</script>

<div class="editor-root">
  <header class="header">
    <span class="app-name">AndRep</span>

    <div class="sep"></div>

    <button class="hbtn" onclick={() => editor.loadJson()} title={_('Open template (Ctrl+O)')}>
      ⬆ {_('Open')}
    </button>
    <button class="hbtn" onclick={() => editor.saveJson()} title={_('Save template (Ctrl+S)')}>
      ⬇ {_('Save')}
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
      title={_('Toggle design guides')}
    >
      ⊞ {_('Guides')}
    </button>

    <div class="sep"></div>

    <!-- Config menu -->
    <div class="config-wrap">
      <button
        class="hbtn"
        class:active={showConfigMenu}
        onclick={() => (showConfigMenu = !showConfigMenu)}
        title={_('Configuration')}
      >
        ⚙
      </button>
      {#if showConfigMenu}
        <div
          class="config-backdrop"
          role="button"
          tabindex="-1"
          aria-label="Close menu"
          onclick={() => (showConfigMenu = false)}
          onkeydown={(e) => e.key === 'Escape' && (showConfigMenu = false)}
        ></div>
        <div class="config-menu">
          <button class="menu-item" onclick={() => { config.loadJson(); showConfigMenu = false; }}>
            ⬆ {_('Load config')}
          </button>
          <button class="menu-item" onclick={() => { config.saveJson(); showConfigMenu = false; }}>
            ⬇ {_('Save config')}
          </button>
          <div class="menu-sep"></div>
          <button class="menu-item danger" onclick={() => { config.reset(); showConfigMenu = false; }}>
            ↺ {_('Reset to defaults')}
          </button>
        </div>
      {/if}
    </div>
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

  .config-wrap {
    position: relative;
  }

  .config-backdrop {
    position: fixed;
    inset: 0;
    z-index: 99;
  }

  .config-menu {
    position: absolute;
    top: calc(100% + 6px);
    right: 0;
    background: #1e293b;
    border: 1px solid #475569;
    border-radius: 4px;
    padding: 4px 0;
    min-width: 160px;
    z-index: 100;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
  }

  .menu-item {
    display: block;
    width: 100%;
    padding: 6px 14px;
    text-align: left;
    background: transparent;
    border: none;
    color: #cbd5e1;
    font-size: 12px;
    cursor: pointer;
  }

  .menu-item:hover {
    background: #334155;
    color: #e2e8f0;
  }

  .menu-item.danger:hover {
    background: #450a0a;
    color: #fca5a5;
  }

  .menu-sep {
    height: 1px;
    background: #334155;
    margin: 4px 0;
  }
</style>
