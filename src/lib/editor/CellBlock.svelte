<script lang="ts">
  import type { Cell } from '$lib/types';
  import { editor } from '$lib/store/editor.svelte';

  let { cell }: { cell: Cell } = $props();

  const selected = $derived(editor.selectedCellIds.has(cell.id));
  const active = $derived(editor.activeCellId === cell.id);
  const s = $derived(cell.style);
  const b = $derived(s.borders);
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
    border: 1px dashed rgba(148, 163, 184, 0.7);
    pointer-events: none;
    z-index: 1;
  }

  /* Bordo scuro per la cella attiva (ultima cliccata) */
  .active {
    box-shadow: inset 0 0 0 2px #1e3a5f;
    z-index: 1;
  }
</style>
