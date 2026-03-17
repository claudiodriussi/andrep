<script lang="ts">
  import { untrack } from 'svelte';
  import type { CompositionRule, CompositionRuleType, PageConfig, PagePreset } from '$lib/types';
  import { editor } from '$lib/store/editor.svelte';
  import { config } from '$lib/store/config.svelte';
  import { _ } from '$lib/i18n/index.svelte';
  import {
    PAGE_SIZES,
    pageUnitFromConfig, pxToPageUnit, pageUnitToPx,
    mmToPageUnit, pageUnitToMm,
    pageUnitLabel, pageUnitStep,
    type PageUnit,
  } from '$lib/units';

  // dUnit is captured at dialog open time; cannot change while dialog is open
  let dUnit = $state<PageUnit>('mm');
  const dLabel = $derived(pageUnitLabel(dUnit));
  const dStep  = $derived(pageUnitStep(dUnit));

  // State in display units (dUnit)
  let name        = $state('');
  let preset      = $state<PagePreset>('A4');
  let orientation = $state<'portrait' | 'landscape'>('portrait');
  let widthD      = $state(210);
  let heightD     = $state(297);
  let topD        = $state(10);
  let bottomD     = $state(15);
  let leftD       = $state(10);
  let rightD      = $state(10);
  let locale      = $state('');
  let currency    = $state('');

  // Composition rules
  let composition = $state<CompositionRule[]>([]);
  let newRule     = $state<CompositionRuleType>('InsBefore');
  let newTarget   = $state('');

  // Sync from template when dialog opens.
  // All writes are inside untrack() so that reading $state locals (e.g. in
  // detectPreset) does not register them as effect dependencies — otherwise
  // writing widthD/heightD and then reading them in detectPreset() creates a
  // read-write cycle that triggers effect_update_depth_exceeded.
  $effect(() => {
    if (!editor.pageSetupOpen) return;
    untrack(() => {
      const newDUnit = pageUnitFromConfig(config.config.units);
      const p        = editor.template.page;
      const newW     = pxToPageUnit(p.width,        newDUnit);
      const newH     = pxToPageUnit(p.height,       newDUnit);
      dUnit       = newDUnit;
      name        = editor.template.name;
      orientation = p.orientation ?? 'portrait';
      widthD      = newW;
      heightD     = newH;
      topD        = pxToPageUnit(p.marginTop,    newDUnit);
      bottomD     = pxToPageUnit(p.marginBottom, newDUnit);
      leftD       = pxToPageUnit(p.marginLeft,   newDUnit);
      rightD      = pxToPageUnit(p.marginRight,  newDUnit);
      locale      = p.locale    || config.config.defaultLocale;
      currency    = p.currency  || config.config.defaultCurrency;
      preset      = p.preset ?? detectPreset();
      composition = JSON.parse(JSON.stringify(editor.template.composition ?? []));
    });
  });

  // Detect preset by converting display values to mm and comparing
  function detectPreset(): PagePreset {
    const wMm = pageUnitToMm(widthD,  dUnit);
    const hMm = pageUnitToMm(heightD, dUnit);
    const pwMm = orientation === 'portrait' ? wMm : hMm;
    const phMm = orientation === 'portrait' ? hMm : wMm;
    for (const [key, dims] of Object.entries(PAGE_SIZES)) {
      if (Math.abs(pwMm - dims.wMm) < 0.6 && Math.abs(phMm - dims.hMm) < 0.6)
        return key as PagePreset;
    }
    return 'custom';
  }

  function applyPreset(p: PagePreset) {
    preset = p;
    if (p === 'custom') return;
    const dims = PAGE_SIZES[p];
    if (!dims) return;
    const wMm = orientation === 'portrait' ? dims.wMm : dims.hMm;
    const hMm = orientation === 'portrait' ? dims.hMm : dims.wMm;
    widthD  = mmToPageUnit(wMm, dUnit);
    heightD = mmToPageUnit(hMm, dUnit);
  }

  function setOrientation(o: 'portrait' | 'landscape') {
    if (o === orientation) return;
    orientation = o;
    [widthD, heightD] = [heightD, widthD];
  }

  function onSizeInput() {
    preset = detectPreset();
  }

  // Content area in display units
  const contentW    = $derived(Math.max(0, widthD  - leftD  - rightD));
  const contentH    = $derived(Math.max(0, heightD - topD   - bottomD));
  const contentWPx  = $derived(pageUnitToPx(contentW, dUnit));
  const contentHPx  = $derived(pageUnitToPx(contentH, dUnit));

  function ok() {
    const page: PageConfig = {
      preset,
      width:        pageUnitToPx(widthD,   dUnit),
      height:       pageUnitToPx(heightD,  dUnit),
      orientation,
      marginTop:    pageUnitToPx(topD,     dUnit),
      marginBottom: pageUnitToPx(bottomD,  dUnit),
      marginLeft:   pageUnitToPx(leftD,    dUnit),
      marginRight:  pageUnitToPx(rightD,   dUnit),
      locale,
      currency,
    };
    editor.applyPageSetup(name.trim() || 'Template', page, composition);
    editor.closePageSetup();
  }

  function addRule() {
    if (!newTarget.trim()) return;
    composition = [...composition, { rule: newRule, target: newTarget.trim() }];
    newTarget = '';
  }

  function removeRule(i: number) {
    composition = composition.filter((_, idx) => idx !== i);
  }

  function cancel() { editor.closePageSetup(); }

  function onKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') cancel();
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) ok();
  }
</script>

{#if editor.pageSetupOpen}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="overlay" onkeydown={onKeydown}>
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="dialog" onclick={(e) => e.stopPropagation()} onkeydown={(e) => e.stopPropagation()}>

      <div class="dialog-header">
        <span>{_('Page setup')}</span>
        <button class="close-btn" onclick={cancel}>×</button>
      </div>

      <div class="dialog-body">

        <!-- Template name -->
        <div class="section-title">{_('Document')}</div>
        <div class="field-row">
          <label class="field-label" for="ps-name">{_('Name')}</label>
          <input id="ps-name" class="field-input" type="text" bind:value={name} />
        </div>
        <div class="field-row">
          <label class="field-label" for="ps-locale">{_('Locale')}</label>
          <input id="ps-locale" class="field-input short" type="text" bind:value={locale} />
          <label class="field-label ml" for="ps-currency">{_('Currency')}</label>
          <input id="ps-currency" class="field-input short" type="text" bind:value={currency} />
        </div>

        <!-- Page size -->
        <div class="section-title">{_('Page')}</div>
        <div class="field-row">
          <label class="field-label" for="ps-preset">{_('Format')}</label>
          <select id="ps-preset" class="field-select" bind:value={preset} onchange={() => applyPreset(preset)}>
            <option value="A6">A6</option>
            <option value="A5">A5</option>
            <option value="A4">A4</option>
            <option value="A3">A3</option>
            <option value="Letter">Letter</option>
            <option value="Legal">Legal</option>
            <option value="custom">{_('Custom')}</option>
          </select>
          <div class="orientation-btns">
            <button
              class="ori-btn"
              class:active={orientation === 'portrait'}
              onclick={() => setOrientation('portrait')}
              title={_('Portrait')}
            >▯</button>
            <button
              class="ori-btn"
              class:active={orientation === 'landscape'}
              onclick={() => setOrientation('landscape')}
              title={_('Landscape')}
            >▭</button>
          </div>
        </div>
        <div class="field-row">
          <label class="field-label" for="ps-w">W</label>
          <input id="ps-w" class="field-num" type="number" min="10" max="2000" step={dStep}
            bind:value={widthD} oninput={onSizeInput} />
          <span class="unit">{dLabel}</span>
          <label class="field-label ml" for="ps-h">H</label>
          <input id="ps-h" class="field-num" type="number" min="10" max="2000" step={dStep}
            bind:value={heightD} oninput={onSizeInput} />
          <span class="unit">{dLabel}</span>
        </div>
        <!-- Margins -->
        <div class="section-title">{_('Margins')}</div>

        <div class="margins-grid">
          <!-- Top -->
          <div class="mg-top">
            <label class="mg-label" for="ps-mt">{_('Top')}</label>
            <input id="ps-mt" class="field-num" type="number" min="0" max="100" step={dStep} bind:value={topD} />
            <span class="unit">{dLabel}</span>
          </div>

          <!-- Left + Right side by side -->
          <div class="mg-sides">
            <div class="mg-side">
              <label class="mg-label" for="ps-ml">{_('Left')}</label>
              <input id="ps-ml" class="field-num" type="number" min="0" max="100" step={dStep} bind:value={leftD} />
              <span class="unit">{dLabel}</span>
            </div>

            <!-- Content area info -->
            <div class="content-info">
              <span class="content-label">{_('Content area')}</span>
              <span class="content-val">{contentW.toFixed(dUnit === 'inch' ? 2 : 1)} × {contentH.toFixed(dUnit === 'inch' ? 2 : 1)} {dLabel}</span>
              <span class="content-px">{contentWPx} × {contentHPx} px</span>
            </div>

            <div class="mg-side">
              <label class="mg-label" for="ps-mr">{_('Right')}</label>
              <input id="ps-mr" class="field-num" type="number" min="0" max="100" step={dStep} bind:value={rightD} />
              <span class="unit">{dLabel}</span>
            </div>
          </div>

          <!-- Bottom -->
          <div class="mg-bottom">
            <label class="mg-label" for="ps-mb">{_('Bottom')}</label>
            <input id="ps-mb" class="field-num" type="number" min="0" max="100" step={dStep} bind:value={bottomD} />
            <span class="unit">{dLabel}</span>
          </div>
        </div>

        <!-- Composition -->
        <div class="section-title">{_('Composition')}</div>
        <div class="comp-list">
          {#if composition.length === 0}
            <div class="comp-empty">{_('No composition rules')}</div>
          {/if}
          {#each composition as rule, i (i)}
            <div class="comp-item">
              <span class="comp-rule">{rule.rule}</span>
              <span class="comp-target">{rule.target}</span>
              <button class="comp-del" onclick={() => removeRule(i)}>×</button>
            </div>
          {/each}
        </div>
        <div class="field-row">
          <select class="field-select comp-rule-sel" bind:value={newRule}>
            <option value="InsBefore">InsBefore</option>
            <option value="InsAfter">InsAfter</option>
            <option value="IfNot">IfNot</option>
            <option value="Replace">Replace</option>
          </select>
          <input
            class="field-input"
            type="text"
            bind:value={newTarget}
            placeholder={_('Template name')}
            onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addRule(); } }}
          />
          <button class="btn-add" onclick={addRule} disabled={!newTarget.trim()}>+</button>
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
    width: 460px;
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
  .section-title:first-child {
    border-top: none;
    padding-top: 0;
    margin-top: 0;
  }

  .field-label {
    font-size: 11px;
    color: #64748b;
    flex-shrink: 0;
    min-width: 56px;
  }
  .field-label.ml { margin-left: 8px; }

  .field-row {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .field-input {
    flex: 1;
    background: #fff;
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    color: #1e293b;
    font-size: 12px;
    padding: 4px 6px;
    min-width: 0;
  }
  .field-input.short { flex: 0 0 80px; }

  .field-select {
    flex: 1;
    background: #fff;
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    color: #1e293b;
    font-size: 12px;
    padding: 4px 6px;
  }

  .field-num {
    width: 64px;
    background: #fff;
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

  .unit {
    font-size: 11px;
    color: #94a3b8;
  }

  /* Orientation buttons */
  .orientation-btns {
    display: flex;
    gap: 4px;
    margin-left: 4px;
  }
  .ori-btn {
    width: 30px;
    height: 26px;
    font-size: 14px;
    background: #fff;
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    cursor: pointer;
    color: #64748b;
    display: flex;
    align-items: center;
    justify-content: center;
    line-height: 1;
  }
  .ori-btn:hover { background: #f1f5f9; }
  .ori-btn.active {
    background: #dbeafe;
    border-color: #3b82f6;
    color: #1d4ed8;
  }

  /* Margins layout */
  .margins-grid {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
  }

  .mg-top, .mg-bottom {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .mg-sides {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
  }

  .mg-side {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .mg-label {
    font-size: 11px;
    color: #64748b;
    min-width: 40px;
    text-align: right;
  }

  /* Content area info (center between left/right margins) */
  .content-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    padding: 8px;
    background: #f1f5f9;
    border: 1px dashed #cbd5e1;
    border-radius: 4px;
    min-width: 0;
  }
  .content-label {
    font-size: 10px;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  .content-val {
    font-size: 12px;
    font-weight: 600;
    color: #334155;
  }
  .content-px {
    font-size: 10px;
    color: #94a3b8;
    font-family: monospace;
  }

  /* Composition */
  .comp-list {
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    background: #fff;
    min-height: 44px;
    max-height: 120px;
    overflow-y: auto;
  }

  .comp-empty {
    font-size: 11px;
    color: #94a3b8;
    padding: 10px 8px;
    text-align: center;
  }

  .comp-item {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 3px 6px;
    border-bottom: 1px solid #f1f5f9;
  }
  .comp-item:last-child { border-bottom: none; }

  .comp-rule {
    color: #2563eb;
    font-family: monospace;
    font-size: 11px;
    min-width: 76px;
    flex-shrink: 0;
  }

  .comp-target {
    flex: 1;
    color: #1e293b;
    font-family: monospace;
    font-size: 11px;
  }

  .comp-del {
    background: transparent;
    border: none;
    color: #94a3b8;
    font-size: 15px;
    line-height: 1;
    cursor: pointer;
    padding: 0 2px;
    flex-shrink: 0;
  }
  .comp-del:hover { color: #ef4444; }

  .comp-rule-sel { flex: 0 0 104px; }

  .btn-add {
    padding: 4px 10px;
    font-size: 14px;
    font-weight: 600;
    background: #2563eb;
    border: 1px solid #1d4ed8;
    border-radius: 3px;
    color: white;
    cursor: pointer;
    flex-shrink: 0;
    line-height: 1;
  }
  .btn-add:hover { background: #1d4ed8; }
  .btn-add:disabled { background: #94a3b8; border-color: #94a3b8; cursor: default; }

  /* Footer */
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
