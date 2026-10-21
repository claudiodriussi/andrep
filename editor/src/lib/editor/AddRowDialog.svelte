<script lang="ts">
  import { editor } from '$lib/store/editor.svelte';
  import { config } from '$lib/store/config.svelte';
  import { _ } from '$lib/i18n/index.svelte';
  import { RESERVED_BANDS, isReservedBand } from '$lib/bands';

  let name = $state('');
  let inputEl = $state<HTMLInputElement | null>(null);

  // Reset and focus the name field whenever the dialog opens
  $effect(() => {
    if (editor.addRowOpen) {
      name = '';
      setTimeout(() => inputEl?.focus(), 0);
    }
  });

  // User presets, then the other names already in the template — reserved names have their own group
  const presets = $derived(
    [...new Set(config.config.bandNamePresets.map((n) => n.trim()))].filter((n) => n && !isReservedBand(n)),
  );
  const inTemplate = $derived(
    [...new Set(editor.template.rows.map((r) => r.name))].filter(
      (n) => !isReservedBand(n) && !presets.includes(n),
    ),
  );

  function add(bandName: string) {
    const n = bandName.trim();
    if (!n) return;
    editor.addRow(n, editor.addRowAfterId);
    editor.closeAddRow();
  }

  function onOverlayKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') editor.closeAddRow();
  }
</script>

{#if editor.addRowOpen}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="overlay" onkeydown={onOverlayKeydown}>
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
      class="backdrop"
      onclick={() => editor.closeAddRow()}
      onkeydown={(e) => e.key === 'Escape' && editor.closeAddRow()}
    ></div>

    <div class="dialog">
      <div class="dialog-header">
        <span>{_('Add row')}</span>
        <button class="close-btn" onclick={() => editor.closeAddRow()}>×</button>
      </div>

      <div class="dialog-body">
        <div class="name-row">
          <input
            bind:this={inputEl}
            bind:value={name}
            class="name-input"
            placeholder={_('Band name')}
            onkeydown={(e) => e.key === 'Enter' && add(name)}
          />
          <button class="btn-ok" onclick={() => add(name)} disabled={!name.trim()}>OK</button>
        </div>

        <div class="section-title">{_('Reserved names')}</div>
        <div class="reserved-list">
          {#each RESERVED_BANDS as band (band.name)}
            <button class="reserved" onclick={() => add(band.name)}>
              <span class="band-name">{band.name}</span>
              <span class="band-hint">{_(band.hint)}</span>
            </button>
          {/each}
        </div>

        {#if presets.length}
          <div class="section-title">{_('Presets')}</div>
          <div class="chips">
            {#each presets as n (n)}
              <button class="chip" onclick={() => add(n)}>{n}</button>
            {/each}
          </div>
        {/if}

        {#if inTemplate.length}
          <div class="section-title">{_('In this template')}</div>
          <div class="chips">
            {#each inTemplate as n (n)}
              <button class="chip" onclick={() => add(n)}>{n}</button>
            {/each}
          </div>
        {/if}
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

  .dialog {
    position: relative;
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    width: 380px;
    max-width: 95vw;
    max-height: 90vh;
    display: flex;
    flex-direction: column;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);
    z-index: 1;
  }

  .dialog-header {
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

  .dialog-body {
    padding: 14px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .name-row {
    display: flex;
    gap: 6px;
  }

  .name-input {
    flex: 1;
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    color: #1e293b;
    font-size: 12px;
    padding: 4px 6px;
    min-width: 0;
  }
  .name-input:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
  }

  .btn-ok {
    background: #2563eb;
    border: none;
    border-radius: 4px;
    color: #ffffff;
    font-size: 12px;
    padding: 4px 12px;
    cursor: pointer;
  }
  .btn-ok:disabled {
    opacity: 0.5;
    cursor: default;
  }

  .section-title {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #94a3b8;
    margin-top: 4px;
    padding-top: 6px;
    border-top: 1px solid #e2e8f0;
  }

  .reserved-list {
    display: flex;
    flex-direction: column;
  }

  .reserved {
    display: flex;
    align-items: baseline;
    gap: 10px;
    background: transparent;
    border: none;
    border-radius: 3px;
    padding: 4px 6px;
    text-align: left;
    cursor: pointer;
  }
  .reserved:hover { background: #e2e8f0; }

  .band-name {
    font-family: monospace;
    font-size: 12px;
    color: #1e293b;
    min-width: 100px;
  }

  .band-hint {
    font-size: 11px;
    color: #64748b;
  }

  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }

  .chip {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    color: #1e293b;
    font-family: monospace;
    font-size: 12px;
    padding: 3px 8px;
    cursor: pointer;
  }
  .chip:hover { border-color: #3b82f6; }
</style>
