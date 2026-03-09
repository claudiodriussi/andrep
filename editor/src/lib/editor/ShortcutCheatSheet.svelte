<script lang="ts">
  import { editor } from '$lib/store/editor.svelte';
  import { _ } from '$lib/i18n/index.svelte';
  import { SHORTCUT_DOCS } from './keyboard';

  // Group entries by group name, preserving insertion order
  const groups = $derived.by(() => {
    const map = new Map<string, { keys: string; description: string }[]>();
    for (const entry of SHORTCUT_DOCS) {
      if (!map.has(entry.group)) map.set(entry.group, []);
      map.get(entry.group)!.push({ keys: entry.keys, description: entry.description });
    }
    return [...map.entries()];
  });

  function close() {
    editor.cheatSheetOpen = false;
  }

  function onOverlayKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') close();
  }
</script>

{#if editor.cheatSheetOpen}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="overlay" onkeydown={onOverlayKeydown}>
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
      class="backdrop"
      onclick={close}
      onkeydown={(e) => e.key === 'Escape' && close()}
    ></div>

    <div class="sheet">
      <div class="sheet-header">
        <span>{_('Keyboard shortcuts')}</span>
        <button class="close-btn" onclick={close}>×</button>
      </div>

      <div class="sheet-body">
        <div class="groups-grid">
          {#each groups as [groupName, entries] (groupName)}
            <div class="group">
              <div class="group-title">{groupName}</div>
              <table class="shortcut-table">
                <tbody>
                  {#each entries as entry (entry.keys)}
                    <tr>
                      <td class="key-cell"><kbd>{entry.keys}</kbd></td>
                      <td class="desc-cell">{_(entry.description)}</td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          {/each}
        </div>
      </div>
    </div>
  </div>
{/if}

<style>
  .overlay {
    position: fixed;
    inset: 0;
    z-index: 200;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .backdrop {
    position: absolute;
    inset: 0;
    background: rgba(0, 0, 0, 0.55);
  }

  .sheet {
    position: relative;
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    width: 720px;
    max-width: 95vw;
    max-height: 90vh;
    display: flex;
    flex-direction: column;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);
    z-index: 1;
  }

  .sheet-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 14px;
    background: #dde3ea;
    border-bottom: 1px solid #cbd5e1;
    border-radius: 6px 6px 0 0;
    font-size: 13px;
    font-weight: 600;
    color: #1e293b;
    flex-shrink: 0;
  }

  .close-btn {
    background: transparent;
    border: none;
    color: #64748b;
    font-size: 18px;
    line-height: 1;
    cursor: pointer;
    padding: 0 4px;
  }
  .close-btn:hover { color: #1e293b; }

  .sheet-body {
    padding: 16px;
    overflow-y: auto;
    flex: 1;
  }

  .groups-grid {
    columns: 2;
    column-gap: 24px;
  }

  @media (max-width: 560px) {
    .groups-grid { columns: 1; }
  }

  .group {
    break-inside: avoid;
    margin-bottom: 16px;
  }

  .group-title {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #94a3b8;
    padding-bottom: 4px;
    border-bottom: 1px solid #e2e8f0;
    margin-bottom: 4px;
  }

  .shortcut-table {
    width: 100%;
    border-collapse: collapse;
  }

  .shortcut-table tr {
    line-height: 1.6;
  }

  .key-cell {
    white-space: nowrap;
    padding-right: 10px;
    vertical-align: middle;
  }

  .desc-cell {
    font-size: 11px;
    color: #475569;
    vertical-align: middle;
  }

  kbd {
    display: inline-block;
    font-family: monospace;
    font-size: 10px;
    background: #e2e8f0;
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    padding: 1px 5px;
    color: #1e293b;
    white-space: nowrap;
  }
</style>
