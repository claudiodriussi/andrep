<script lang="ts">
  import type { Cell } from '$lib/types';
  import { editor } from '$lib/store/editor.svelte';

  let { cell }: { cell: Cell } = $props();

  const selected = $derived(editor.selectedCellIds.has(cell.id));
  const active = $derived(editor.activeCellId === cell.id);
  const s = $derived(cell.style);
  const _noB = { width: 0, style: 'none', color: '#000000' };
  const b = $derived({
    top:    s.borders?.top    ?? _noB,
    bottom: s.borders?.bottom ?? _noB,
    left:   s.borders?.left   ?? _noB,
    right:  s.borders?.right  ?? _noB,
  });

  const flexVA = $derived(
    ({ top: 'flex-start', middle: 'center', bottom: 'flex-end' } as Record<string, string>)[
      s.verticalAlignment
    ] ?? 'flex-start',
  );

  // --- inline editor ---
  const isEditing = $derived(editor.inlineCellId === cell.id);
  let editValue = $state('');

  $effect(() => {
    if (isEditing) editValue = editor.inlineCellInitialValue ?? cell.content;
  });

  function saveInline() {
    cell.content = editValue;
    editor.closeInlineEditor();
  }

  function cancelInline() {
    editor.closeInlineEditor();
  }

  function initEditor(node: HTMLTextAreaElement) {
    node.focus();
    if (editor.inlineCellInitialValue === null) node.select();
    // with initialValue: cursor lands at end (default textarea behavior)
  }

  // --- resize ---
  let draggingW = false;
  let dragStartX = 0;
  let dragStartWidth = 0;

  function onRightHandlePointerDown(e: PointerEvent) {
    e.preventDefault();
    e.stopPropagation();
    editor.pushHistory();
    draggingW = true;
    dragStartX = e.clientX;
    dragStartWidth = cell.width;
    (e.target as Element).setPointerCapture(e.pointerId);
  }

  function snapX(delta: number) { const s = editor.gridStepX; return s > 1 ? Math.round(delta / s) * s : delta; }
  function snapY(delta: number) { const s = editor.gridStepY; return s > 1 ? Math.round(delta / s) * s : delta; }

  function onRightHandlePointerMove(e: PointerEvent) {
    if (!draggingW) return;
    editor.resizeCell(cell.id, Math.max(20, dragStartWidth + snapX(e.clientX - dragStartX)));
  }

  function onRightHandlePointerUp() {
    draggingW = false;
  }

  let draggingH = false;
  let dragStartY = 0;
  let dragStartHeight = 0;

  function onBottomHandlePointerDown(e: PointerEvent) {
    e.preventDefault();
    e.stopPropagation();
    editor.pushHistory();
    draggingH = true;
    dragStartY = e.clientY;
    dragStartHeight = cell.height;
    (e.target as Element).setPointerCapture(e.pointerId);
  }

  function onBottomHandlePointerMove(e: PointerEvent) {
    if (!draggingH) return;
    editor.resizeCellHeight(cell.id, Math.max(10, dragStartHeight + snapY(e.clientY - dragStartY)));
  }

  function onBottomHandlePointerUp() {
    draggingH = false;
  }
</script>

<div
  class="cell"
  class:selected
  class:active
  class:guides={editor.showGuides}
  style="
    width: {cell.width}px;
    height: {cell.height}px;
    font-family: {s.fontFamily};
    font-size: {s.fontSize}pt;
    font-weight: {s.fontWeight};
    font-style: {s.fontStyle};
    text-decoration: {s.textDecoration};
    color: {s.color};
    background-color: {s.backgroundColor};
    text-align: {s.alignment};
    padding: {s.paddingTop}px {s.paddingRight}px {s.paddingBottom}px {s.paddingLeft}px;
    border-top: {b.top.width > 0 ? `${b.top.width}px ${b.top.style} ${b.top.color}` : 'none'};
    border-bottom: {b.bottom.width > 0 ? `${b.bottom.width}px ${b.bottom.style} ${b.bottom.color}` : 'none'};
    border-left: {b.left.width > 0 ? `${b.left.width}px ${b.left.style} ${b.left.color}` : 'none'};
    border-right: {b.right.width > 0 ? `${b.right.width}px ${b.right.style} ${b.right.color}` : 'none'};
    display: flex;
    align-items: {flexVA};
    {cell.cssExtra ?? ''}
  "
  role="button"
  tabindex="0"
  onclick={(e) => {
    e.stopPropagation();
    if (e.shiftKey) {
      editor.selectAdd(cell.id);
    } else if (e.ctrlKey || e.metaKey) {
      editor.openInlineEditor(cell.id);
    } else {
      editor.selectOne(cell.id);
    }
  }}
  ondblclick={(e) => {
    e.stopPropagation();
    editor.selectOne(cell.id);
    editor.openCellDialog(cell.id);
  }}
  onkeydown={undefined}
>
  <div
    class="cell-content"
    style={cell.rotation ? `transform: rotate(${cell.rotation}deg)` : undefined}
  >
    {cell.content || '\u00a0'}
  </div>

  {#if isEditing}
    <!-- svelte-ignore a11y_autofocus -->
    <textarea
      class="inline-editor"
      bind:value={editValue}
      use:initEditor
      style="
        padding: {s.paddingTop}px {s.paddingRight}px {s.paddingBottom}px {s.paddingLeft}px;
        font-family: {s.fontFamily};
        font-size: {s.fontSize}pt;
        font-weight: {s.fontWeight};
        font-style: {s.fontStyle};
        color: {s.color};
        text-align: {s.alignment};
      "
      onblur={saveInline}
      onkeydown={(e) => {
        if (e.key === 'Escape') { e.preventDefault(); cancelInline(); }
        else if (e.key === 'Enter') { e.preventDefault(); saveInline(); }
        e.stopPropagation();
      }}
    ></textarea>
  {/if}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="resize-handle right"
    onpointerdown={onRightHandlePointerDown}
    onpointermove={onRightHandlePointerMove}
    onpointerup={onRightHandlePointerUp}
  ></div>
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="resize-handle bottom"
    onpointerdown={onBottomHandlePointerDown}
    onpointermove={onBottomHandlePointerMove}
    onpointerup={onBottomHandlePointerUp}
  ></div>
</div>

<style>
  .cell {
    position: relative;
    flex-shrink: 0;
    box-sizing: border-box;
    overflow: hidden;
    cursor: pointer;
    user-select: none;
    line-height: 1.3;
  }

  .cell:focus {
    outline: none;
  }

  .cell-content {
    width: 100%;
    min-width: 0;
    overflow: hidden;
    white-space: pre-wrap;
  }

  /* Overlay grigio semitrasparente per celle selezionate */
  .selected::after {
    content: '';
    position: absolute;
    inset: 0;
    background: rgba(0, 0, 0, 0.14);
    pointer-events: none;
  }

  /* Guide: overlay dashed per vedere i contorni nell'editor (indipendente dai bordi template) */
  .guides::before {
    content: '';
    position: absolute;
    inset: 0;
    border: 1px solid rgba(148, 163, 184, 0.3);
    pointer-events: none;
    z-index: 1;
  }

  /* Bordo scuro per la cella attiva (ultima cliccata) */
  .active {
    box-shadow: inset 0 0 0 2px #1e3a5f;
    z-index: 1;
  }

  .inline-editor {
    position: absolute;
    inset: 0;
    z-index: 10;
    width: 100%;
    height: 100%;
    resize: none;
    border: 2px solid #2563eb;
    outline: none;
    background: white;
    line-height: 1.3;
    box-sizing: border-box;
  }

  .resize-handle {
    position: absolute;
    z-index: 3;
  }

  .resize-handle.right {
    top: 0;
    right: 0;
    width: 5px;
    height: 100%;
    cursor: col-resize;
  }

  .resize-handle.bottom {
    bottom: 0;
    left: 0;
    width: 100%;
    height: 5px;
    cursor: row-resize;
  }
</style>
