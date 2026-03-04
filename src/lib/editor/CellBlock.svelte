<script lang="ts">
  import type { Cell } from '$lib/types';
  import { editor } from '$lib/store/editor.svelte';

  let { cell }: { cell: Cell } = $props();

  const selected = $derived(editor.selectedCellIds.has(cell.id));
  const active = $derived(editor.activeCellId === cell.id);
  const s = $derived(cell.style);
  const borders = $derived(editor.showGuides ? s.borders : null);
</script>

<div
  class="cell"
  class:selected
  class:active
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
    border-top: {borders ? `${borders.top.width}px ${borders.top.style} ${borders.top.color}` : 'none'};
    border-bottom: {borders ? `${borders.bottom.width}px ${borders.bottom.style} ${borders.bottom.color}` : 'none'};
    border-left: {borders ? `${borders.left.width}px ${borders.left.style} ${borders.left.color}` : 'none'};
    border-right: {borders ? `${borders.right.width}px ${borders.right.style} ${borders.right.color}` : 'none'};
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

  /* Bordo scuro per la cella attiva (ultima cliccata).
     box-shadow inset: non conflitte con outline:none del :focus */
  .active {
    box-shadow: inset 0 0 0 2px #1e3a5f;
    z-index: 1;
  }
</style>
