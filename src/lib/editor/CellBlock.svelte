<script lang="ts">
  import type { Cell } from '$lib/types';
  import { editor } from '$lib/store/editor.svelte';

  let { cell }: { cell: Cell } = $props();

  const selected = $derived(editor.selectedCellIds.has(cell.id));
  const active = $derived(editor.activeCellId === cell.id);
  const s = $derived(cell.style);
  const b = $derived(s.borders);

  let draggingW = false;
  let dragStartX = 0;
  let dragStartWidth = 0;

  function onRightHandlePointerDown(e: PointerEvent) {
    e.preventDefault();
    e.stopPropagation();
    draggingW = true;
    dragStartX = e.clientX;
    dragStartWidth = cell.width;
    (e.target as Element).setPointerCapture(e.pointerId);
  }

  function onRightHandlePointerMove(e: PointerEvent) {
    if (!draggingW) return;
    editor.resizeCell(cell.id, Math.max(20, dragStartWidth + e.clientX - dragStartX));
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
    draggingH = true;
    dragStartY = e.clientY;
    dragStartHeight = cell.height;
    (e.target as Element).setPointerCapture(e.pointerId);
  }

  function onBottomHandlePointerMove(e: PointerEvent) {
    if (!draggingH) return;
    editor.resizeCellHeight(cell.id, Math.max(10, dragStartHeight + e.clientY - dragStartY));
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
  "
  role="button"
  tabindex="0"
  onclick={(e) => {
    e.stopPropagation();
    if (e.shiftKey) {
      editor.selectAdd(cell.id);
    } else {
      editor.selectOne(cell.id);
    }
  }}
  onkeydown={(e) => {
    if (e.key === 'Enter') editor.selectOne(cell.id);
  }}
>
  {cell.content || '\u00a0'}
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
