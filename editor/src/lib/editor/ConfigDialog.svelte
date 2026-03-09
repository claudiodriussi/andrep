<script lang="ts">
  import type { EditorConfig, ToolbarGroupId } from '$lib/types';
  import { config } from '$lib/store/config.svelte';
  import { _ } from '$lib/i18n/index.svelte';

  // All known toolbar groups in canonical order
  const ALL_TOOLBAR_GROUPS: ToolbarGroupId[] = [
    'file', 'font', 'align', 'colors', 'borders', 'cell', 'structure',
  ];

  // Local copy of the config, mutated freely; applied on OK
  let local = $state<EditorConfig>({ ...config.config });

  // Sync local copy whenever the dialog opens
  $effect(() => {
    if (config.configOpen) {
      local = JSON.parse(JSON.stringify(config.config)) as EditorConfig;
    }
  });

  function ok() {
    config.config = { ...local };
    config.save();
    config.configOpen = false;
  }

  function cancel() {
    config.configOpen = false;
  }

  function onOverlayKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') cancel();
  }

  // --- Toolbar groups helpers ---

  function isGroupEnabled(id: ToolbarGroupId): boolean {
    return local.toolbarGroups.includes(id);
  }

  function toggleGroup(id: ToolbarGroupId) {
    if (isGroupEnabled(id)) {
      local.toolbarGroups = local.toolbarGroups.filter((g) => g !== id);
    } else {
      local.toolbarGroups = [...local.toolbarGroups, id];
    }
  }

  function moveGroup(id: ToolbarGroupId, direction: 'up' | 'down') {
    const arr = [...local.toolbarGroups];
    const idx = arr.indexOf(id);
    if (idx === -1) return;
    const swapIdx = direction === 'up' ? idx - 1 : idx + 1;
    if (swapIdx < 0 || swapIdx >= arr.length) return;
    [arr[idx], arr[swapIdx]] = [arr[swapIdx], arr[idx]];
    local.toolbarGroups = arr;
  }

  // Ordered list: enabled groups in their current order, then disabled groups
  const toolbarGroupList = $derived.by((): ToolbarGroupId[] => {
    const enabled = local.toolbarGroups.filter((g) =>
      ALL_TOOLBAR_GROUPS.includes(g),
    );
    const disabled = ALL_TOOLBAR_GROUPS.filter((g) => !enabled.includes(g));
    return [...enabled, ...disabled];
  });

  // --- Color palette helpers ---

  let fgColorInputs: HTMLInputElement[] = [];
  let bgColorInputs: HTMLInputElement[] = [];

  function openColorInput(inputs: HTMLInputElement[], idx: number) {
    inputs[idx]?.click();
  }

  function updateFgColor(idx: number, value: string) {
    const arr = [...local.fgPalette];
    arr[idx] = value;
    local.fgPalette = arr;
  }

  function removeFgColor(idx: number) {
    local.fgPalette = local.fgPalette.filter((_, i) => i !== idx);
  }

  function addFgColor() {
    local.fgPalette = [...local.fgPalette, '#808080'];
  }

  function updateBgColor(idx: number, value: string) {
    const arr = [...local.bgPalette];
    arr[idx] = value;
    local.bgPalette = arr;
  }

  function removeBgColor(idx: number) {
    local.bgPalette = local.bgPalette.filter((_, i) => i !== idx);
  }

  function addBgColor() {
    local.bgPalette = [...local.bgPalette, '#808080'];
  }

  // --- fontFamilies helpers ---

  function updateFontFamily(idx: number, value: string) {
    const arr = [...local.fontFamilies];
    arr[idx] = value;
    local.fontFamilies = arr;
  }

  function removeFontFamily(idx: number) {
    local.fontFamilies = local.fontFamilies.filter((_, i) => i !== idx);
  }

  function addFontFamily() {
    local.fontFamilies = [...local.fontFamilies, ''];
  }

  // --- bandNamePresets helpers ---

  function updateBandPreset(idx: number, value: string) {
    const arr = [...local.bandNamePresets];
    arr[idx] = value;
    local.bandNamePresets = arr;
  }

  function removeBandPreset(idx: number) {
    local.bandNamePresets = local.bandNamePresets.filter((_, i) => i !== idx);
  }

  function addBandPreset() {
    local.bandNamePresets = [...local.bandNamePresets, ''];
  }
</script>

{#if config.configOpen}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="overlay" onkeydown={onOverlayKeydown}>
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
      class="backdrop"
      onclick={cancel}
      onkeydown={(e) => e.key === 'Escape' && cancel()}
    ></div>

    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
      class="dialog"
      onclick={(e) => e.stopPropagation()}
      onkeydown={(e) => e.stopPropagation()}
    >
      <div class="dialog-header">
        <span>{_('Preferences')}</span>
        <button class="close-btn" onclick={cancel}>×</button>
      </div>

      <div class="dialog-body">

        <!-- ─── 1. General ─── -->
        <div class="section-title">{_('General')}</div>

        <div class="field-row">
          <span class="field-label">{_('UI language')}</span>
          <div class="radio-group">
            <label class="radio-label">
              <input type="radio" name="cfg-locale" value="en" bind:group={local.locale} />
              English
            </label>
            <label class="radio-label">
              <input type="radio" name="cfg-locale" value="it" bind:group={local.locale} />
              Italiano
            </label>
          </div>
        </div>

        <div class="field-row">
          <span class="field-label">{_('Units')}</span>
          <div class="radio-group">
            {#each ['px', 'mm', 'inch'] as u (u)}
              <label class="radio-label">
                <input type="radio" name="cfg-units" value={u} bind:group={local.units} />
                {u}
              </label>
            {/each}
          </div>
        </div>

        <div class="field-row">
          <label class="checkbox-label">
            <input type="checkbox" bind:checked={local.showRenderingHints} />
            {_('Show rendering hints (page_role, variable refs)')}
          </label>
        </div>

        <!-- ─── 2. New template defaults ─── -->
        <div class="section-title">{_('New template defaults')}</div>

        <div class="field-row">
          <label class="field-label" for="cfg-preset">{_('Paper size')}</label>
          <select id="cfg-preset" class="field-select" bind:value={local.defaultPreset}>
            {#each ['A6', 'A5', 'A4', 'A3', 'Letter', 'Legal', 'custom'] as p (p)}
              <option value={p}>{p}</option>
            {/each}
          </select>
        </div>

        <div class="field-row gap">
          <span class="field-label">{_('Margins')} (px)</span>
          <label class="field-label-inline">
            T
            <input class="field-num" type="number" min="0" bind:value={local.defaultMargins.top} />
          </label>
          <label class="field-label-inline">
            B
            <input class="field-num" type="number" min="0" bind:value={local.defaultMargins.bottom} />
          </label>
          <label class="field-label-inline">
            L
            <input class="field-num" type="number" min="0" bind:value={local.defaultMargins.left} />
          </label>
          <label class="field-label-inline">
            R
            <input class="field-num" type="number" min="0" bind:value={local.defaultMargins.right} />
          </label>
        </div>

        <div class="field-row">
          <label class="field-label" for="cfg-dloc">{_('Default locale')}</label>
          <input
            id="cfg-dloc"
            class="field-input"
            type="text"
            placeholder="e.g. it-IT"
            bind:value={local.defaultLocale}
          />
        </div>

        <div class="field-row">
          <label class="field-label" for="cfg-dcur">{_('Default currency')}</label>
          <input
            id="cfg-dcur"
            class="field-input"
            type="text"
            placeholder="e.g. EUR"
            bind:value={local.defaultCurrency}
          />
        </div>

        <!-- ─── 3. Font ─── -->
        <div class="section-title">{_('Font')}</div>

        <div class="field-row">
          <label class="field-label" for="cfg-dfont">{_('Default font')}</label>
          <input id="cfg-dfont" class="field-input" type="text" bind:value={local.defaultFont} />
        </div>

        <div class="field-row">
          <label class="field-label" for="cfg-dfsize">{_('Font size')}</label>
          <input
            id="cfg-dfsize"
            class="field-num"
            type="number"
            min="6"
            max="72"
            bind:value={local.defaultFontSize}
          />
        </div>

        <div class="field-label sub-label">{_('Font families')}</div>
        <div class="list-editor">
          {#each local.fontFamilies as ff, i (i)}
            <div class="list-row">
              <input
                class="field-input list-input"
                type="text"
                value={ff}
                oninput={(e) => updateFontFamily(i, (e.target as HTMLInputElement).value)}
              />
              <button class="remove-btn" onclick={() => removeFontFamily(i)}>×</button>
            </div>
          {/each}
          <button class="add-btn" onclick={addFontFamily}>+ {_('Add')}</button>
        </div>

        <!-- ─── 4. Colors ─── -->
        <div class="section-title">{_('Colors')}</div>

        <div class="sub-label">{_('Foreground palette')}</div>
        <div class="palette-row">
          {#each local.fgPalette as color, i (i)}
            <div class="swatch-wrap">
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <div
                class="swatch"
                style="background: {color}"
                title={color}
                onclick={() => openColorInput(fgColorInputs, i)}
                onkeydown={(e) => e.key === 'Enter' && openColorInput(fgColorInputs, i)}
              ></div>
              <button class="swatch-remove" onclick={() => removeFgColor(i)} title="Remove">×</button>
              <input
                type="color"
                class="color-hidden"
                value={color}
                bind:this={fgColorInputs[i]}
                oninput={(e) => updateFgColor(i, (e.target as HTMLInputElement).value)}
              />
            </div>
          {/each}
          <button class="add-swatch-btn" onclick={addFgColor}>+</button>
        </div>

        <div class="sub-label">{_('Background palette')}</div>
        <div class="palette-row">
          {#each local.bgPalette as color, i (i)}
            <div class="swatch-wrap">
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <div
                class="swatch"
                style="background: {color}; border-color: {color === '#ffffff' ? '#cbd5e1' : color}"
                title={color}
                onclick={() => openColorInput(bgColorInputs, i)}
                onkeydown={(e) => e.key === 'Enter' && openColorInput(bgColorInputs, i)}
              ></div>
              <button class="swatch-remove" onclick={() => removeBgColor(i)} title="Remove">×</button>
              <input
                type="color"
                class="color-hidden"
                value={color}
                bind:this={bgColorInputs[i]}
                oninput={(e) => updateBgColor(i, (e.target as HTMLInputElement).value)}
              />
            </div>
          {/each}
          <button class="add-swatch-btn" onclick={addBgColor}>+</button>
        </div>

        <!-- ─── 5. Toolbar groups ─── -->
        <div class="section-title">{_('Toolbar groups')}</div>

        <div class="toolbar-list">
          {#each toolbarGroupList as id (id)}
            {@const enabled = isGroupEnabled(id)}
            <div class="toolbar-row" class:disabled={!enabled}>
              <input
                type="checkbox"
                checked={enabled}
                onchange={() => toggleGroup(id)}
              />
              <span class="toolbar-label">{id}</span>
              <div class="reorder-btns">
                <button
                  class="reorder-btn"
                  disabled={!enabled || local.toolbarGroups.indexOf(id) === 0}
                  onclick={() => moveGroup(id, 'up')}
                  title="Move up"
                >↑</button>
                <button
                  class="reorder-btn"
                  disabled={!enabled || local.toolbarGroups.indexOf(id) === local.toolbarGroups.length - 1}
                  onclick={() => moveGroup(id, 'down')}
                  title="Move down"
                >↓</button>
              </div>
            </div>
          {/each}
        </div>

        <!-- ─── 6. Band name presets ─── -->
        <div class="section-title">{_('Band name presets')}</div>
        <div class="list-editor">
          {#each local.bandNamePresets as preset, i (i)}
            <div class="list-row">
              <input
                class="field-input list-input"
                type="text"
                value={preset}
                oninput={(e) => updateBandPreset(i, (e.target as HTMLInputElement).value)}
              />
              <button class="remove-btn" onclick={() => removeBandPreset(i)}>×</button>
            </div>
          {/each}
          <button class="add-btn" onclick={addBandPreset}>+ {_('Add')}</button>
        </div>

      </div><!-- dialog-body -->

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
    width: 520px;
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

  .sub-label {
    font-size: 11px;
    color: #64748b;
    font-weight: 500;
  }

  .field-label {
    font-size: 11px;
    color: #64748b;
    flex-shrink: 0;
    min-width: 100px;
  }

  .field-label-inline {
    font-size: 11px;
    color: #64748b;
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .field-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .field-row.gap {
    gap: 10px;
    flex-wrap: wrap;
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
    width: 64px;
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    color: #1e293b;
    font-size: 12px;
    padding: 4px 6px;
  }

  .field-input:focus,
  .field-select:focus,
  .field-num:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
  }

  .radio-group {
    display: flex;
    gap: 14px;
  }

  .radio-label {
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 12px;
    color: #1e293b;
    cursor: pointer;
  }

  .checkbox-label {
    display: flex;
    align-items: center;
    gap: 7px;
    font-size: 12px;
    color: #1e293b;
    cursor: pointer;
  }

  /* ── List editor (fontFamilies, bandNamePresets) ── */

  .list-editor {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding-left: 2px;
  }

  .list-row {
    display: flex;
    gap: 4px;
    align-items: center;
  }

  .list-input {
    flex: 1;
  }

  .remove-btn {
    background: transparent;
    border: 1px solid #e2e8f0;
    border-radius: 3px;
    color: #94a3b8;
    font-size: 14px;
    line-height: 1;
    width: 22px;
    height: 22px;
    cursor: pointer;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .remove-btn:hover { border-color: #f87171; color: #dc2626; background: #fef2f2; }

  .add-btn {
    align-self: flex-start;
    margin-top: 2px;
    padding: 3px 10px;
    font-size: 11px;
    background: transparent;
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    color: #475569;
    cursor: pointer;
  }
  .add-btn:hover { background: #f1f5f9; }

  /* ── Color palettes ── */

  .palette-row {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    align-items: center;
  }

  .swatch-wrap {
    position: relative;
    display: flex;
    align-items: center;
  }

  .swatch {
    width: 16px;
    height: 16px;
    border-radius: 2px;
    border: 1px solid #94a3b8;
    cursor: pointer;
    flex-shrink: 0;
  }
  .swatch:hover { outline: 2px solid #3b82f6; outline-offset: 1px; }

  .swatch-remove {
    display: none;
    position: absolute;
    top: -6px;
    right: -6px;
    width: 13px;
    height: 13px;
    background: #ef4444;
    border: none;
    border-radius: 50%;
    color: white;
    font-size: 9px;
    line-height: 1;
    cursor: pointer;
    align-items: center;
    justify-content: center;
    padding: 0;
  }
  .swatch-wrap:hover .swatch-remove { display: flex; }

  .color-hidden {
    position: absolute;
    opacity: 0;
    width: 0;
    height: 0;
    pointer-events: none;
  }

  .add-swatch-btn {
    width: 16px;
    height: 16px;
    background: #e2e8f0;
    border: 1px solid #cbd5e1;
    border-radius: 2px;
    font-size: 12px;
    line-height: 1;
    cursor: pointer;
    color: #64748b;
    padding: 0;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .add-swatch-btn:hover { background: #cbd5e1; }

  /* ── Toolbar group list ── */

  .toolbar-list {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .toolbar-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 3px 6px;
    border-radius: 3px;
    background: #f1f5f9;
  }

  .toolbar-row.disabled {
    opacity: 0.5;
  }

  .toolbar-label {
    flex: 1;
    font-size: 12px;
    color: #1e293b;
    font-family: monospace;
  }

  .reorder-btns {
    display: flex;
    gap: 2px;
  }

  .reorder-btn {
    background: transparent;
    border: 1px solid #cbd5e1;
    border-radius: 2px;
    color: #475569;
    font-size: 11px;
    width: 20px;
    height: 20px;
    cursor: pointer;
    line-height: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
  }
  .reorder-btn:hover:not(:disabled) { background: #e2e8f0; }
  .reorder-btn:disabled { opacity: 0.3; cursor: default; }

  /* ── Footer ── */

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
