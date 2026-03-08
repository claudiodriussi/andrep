<script lang="ts">
  import type { CellType } from '$lib/types';
  import { editor } from '$lib/store/editor.svelte';
  import { _ } from '$lib/i18n/index.svelte';

  const cell = $derived(editor.cellDialogId ? editor.findCell(editor.cellDialogId) : null);

  let content = $state('');
  let type = $state<CellType>('text');
  let embedTarget = $state('');
  let width = $state(100);
  let height = $state(24);
  let x = $state(0);
  let wrap = $state(false);
  let autoStretch = $state(false);
  let rotation = $state<0 | 90 | 180 | 270>(0);
  let cssExtra = $state('');

  // Sync from cell when dialog opens
  $effect(() => {
    if (cell) {
      content = cell.content;
      type = cell.type;
      embedTarget = cell.embedTarget ?? '';
      width = cell.width;
      height = cell.height;
      x = cell.x;
      wrap = cell.wrap;
      autoStretch = cell.autoStretch;
      rotation = cell.rotation ?? 0;
      cssExtra = cell.cssExtra ?? '';
    }
  });

  function ok() {
    if (!editor.cellDialogId) return;
    editor.updateCell(editor.cellDialogId, {
      content,
      type,
      embedTarget: type === 'embed' ? (embedTarget || undefined) : undefined,
      width,
      height,
      x,
      wrap,
      autoStretch,
      rotation: rotation !== 0 ? rotation : undefined,
      cssExtra: cssExtra.trim() || undefined,
    });
    editor.closeCellDialog();
  }

  function cancel() {
    editor.closeCellDialog();
  }

  function onOverlayKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') cancel();
  }
</script>

{#if cell}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="overlay" onkeydown={onOverlayKeydown}>
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
      class="dialog"
      onclick={(e) => e.stopPropagation()}
      onkeydown={(e) => e.stopPropagation()}
    >
      <div class="dialog-header">
        <span>{_('Cell properties')}</span>
        <button class="close-btn" onclick={cancel}>×</button>
      </div>

      <div class="dialog-body">
        <!-- Content -->
        <div class="field-col">
          <label class="field-label" for="cp-content">{_('Content')}</label>
          <textarea
            id="cp-content"
            class="field-textarea"
            bind:value={content}
            rows={3}
            spellcheck={false}
          ></textarea>
        </div>

        <!-- Variable reference -->
        <details class="var-ref">
          <summary>{_('Variable reference')}</summary>
          <div class="var-table">
            <code>[expr]</code><span>{_('var: lookup / expression')}</span>
            <code>[expr | fmt]</code><span>{_('var: with formatter')}</span>
            <code>[expr | f1 | f2]</code><span>{_('var: chained formatters')}</span>
            <code>[a | b \| trim]</code><span>{_('var: \\| splits if expr has |')}</span>
            <code>[expr | date]</code><span>{_('var: locale date')}</span>
            <code>[expr | dd/mm/yyyy]</code><span>{_('var: explicit date format')}</span>
            <code>[expr | .2]</code><span>{_('var: thousands + 2 decimals')}</span>
            <code>[expr | currency]</code><span>{_('var: currency amount')}</span>
            <code>[expr | upper]</code><span>{_('var: uppercase')}</span>
            <code>[expr | space]</code><span>{_('var: empty if null/zero')}</span>
            <code>[url | contain]</code><span>{_('var: image proportional')}</span>
            <code>[val | code128]</code><span>{_('var: barcode Code 128')}</span>
            <code>[val | qr]</code><span>{_('var: QR code')}</span>
          </div>
          <div class="var-sys">
            <span class="sys-label">{_('System')}:</span>
            {#each ['_PAGE', '_DATE', '_TIME', '_USER'] as v (v)}
              <code>[{v}]</code>
            {/each}
          </div>
        </details>

        <!-- Type -->
        <div class="field-row">
          <label class="field-label" for="cp-type">{_('Type')}</label>
          <select id="cp-type" class="field-select" bind:value={type}>
            <option value="text">{_('Text')}</option>
            <option value="markdown">Markdown</option>
            <option value="image">{_('Image')}</option>
            <option value="barcode">Barcode</option>
            <option value="qrcode">QR Code</option>
            <option value="embed">Embed</option>
          </select>
        </div>

        <!-- Embed target -->
        {#if type === 'embed'}
          <div class="field-row">
            <label class="field-label" for="cp-embed">{_('Band target')}</label>
            <input id="cp-embed" class="field-input" type="text" bind:value={embedTarget} />
          </div>
        {/if}

        <div class="section-title">{_('Geometry')}</div>
        <div class="field-row gap">
          <label class="field-label-inline" for="cp-w">W</label>
          <input id="cp-w" class="field-num" type="number" min="1" bind:value={width} />
          <label class="field-label-inline" for="cp-h">H</label>
          <input id="cp-h" class="field-num" type="number" min="1" bind:value={height} />
          <label class="field-label-inline check">
            <input type="checkbox" bind:checked={wrap} />
            {_('Word wrap')}
          </label>
          <label class="field-label-inline check">
            <input type="checkbox" bind:checked={autoStretch} />
            {_('Auto stretch')}
          </label>
        </div>

        <div class="section-title">{_('Text rotation')}</div>
        <div class="field-row gap">
          {#each [0, 90, 180, 270] as deg (deg)}
            <label class="field-label-inline check">
              <input class="radio-blue" type="radio" name="cp-rotation" value={deg} bind:group={rotation} />
              {deg}°
            </label>
          {/each}
        </div>

        <div class="section-title">{_('CSS extra')}</div>
        <div class="field-col">
          <input
            class="field-input mono"
            type="text"
            bind:value={cssExtra}
            spellcheck={false}
            placeholder="opacity: 0.8; letter-spacing: 1px"
          />
        </div>
      </div>

      <div class="dialog-footer">
        <button class="btn-cancel" onclick={cancel}>{_('Cancel')}</button>
        <button class="btn-ok" onclick={ok}>OK</button>
      </div>
    </div>
  </div>
{/if}

<style>
  .overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.55);
    z-index: 200;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .dialog {
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    width: 420px;
    max-width: 95vw;
    max-height: 90vh;
    display: flex;
    flex-direction: column;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);
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
    padding: 12px 14px;
    overflow-y: auto;
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 8px;
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

  .field-label {
    font-size: 11px;
    color: #64748b;
    flex-shrink: 0;
    min-width: 64px;
  }

  .field-label-inline {
    font-size: 11px;
    color: #64748b;
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .field-label-inline.check { gap: 5px; }

  .field-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .field-row.gap {
    gap: 10px;
    flex-wrap: wrap;
  }

  .field-col {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .field-input,
  .field-select {
    flex: 1;
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    color: #1e293b;
    font-size: 12px;
    padding: 4px 6px;
    min-width: 0;
  }

  .field-num {
    width: 58px;
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    color: #1e293b;
    font-size: 12px;
    padding: 4px 6px;
  }

  .field-textarea {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    color: #1e293b;
    font-size: 12px;
    padding: 6px 8px;
    resize: vertical;
    width: 100%;
    box-sizing: border-box;
    font-family: monospace;
    line-height: 1.4;
  }

  .field-input.mono {
    font-family: monospace;
    font-size: 11px;
  }

  .radio-blue {
    accent-color: #2563eb;
  }

  .field-input:focus,
  .field-select:focus,
  .field-num:focus,
  .field-textarea:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
  }

  /* variable reference */
  .var-ref {
    font-size: 11px;
  }

  .var-ref summary {
    color: #94a3b8;
    cursor: pointer;
    user-select: none;
    padding: 2px 0;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  .var-ref summary:hover { color: #64748b; }

  .var-table {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 3px 12px;
    margin-top: 6px;
    padding: 8px;
    background: #f8fafc;
    border-radius: 3px;
    border: 1px solid #e2e8f0;
  }

  .var-table code {
    font-size: 10px;
    color: #2563eb;
    font-family: monospace;
    white-space: nowrap;
  }

  .var-table span {
    font-size: 10px;
    color: #94a3b8;
  }

  .var-sys {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 6px;
    flex-wrap: wrap;
  }

  .sys-label {
    font-size: 10px;
    color: #94a3b8;
  }

  .var-sys code {
    font-size: 10px;
    color: #2563eb;
    font-family: monospace;
  }

  .dialog-footer {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    padding: 10px 14px;
    border-top: 1px solid #e2e8f0;
    flex-shrink: 0;
  }

  .btn-cancel {
    padding: 5px 16px;
    font-size: 12px;
    background: transparent;
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    color: #475569;
    cursor: pointer;
  }
  .btn-cancel:hover { background: #f1f5f9; }

  .btn-ok {
    padding: 5px 16px;
    font-size: 12px;
    background: #2563eb;
    border: 1px solid #1d4ed8;
    border-radius: 3px;
    color: white;
    cursor: pointer;
    font-weight: 500;
  }
  .btn-ok:hover { background: #1d4ed8; }
</style>
