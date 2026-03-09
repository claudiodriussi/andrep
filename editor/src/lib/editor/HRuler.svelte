<script lang="ts">
  import { editor } from '$lib/store/editor.svelte';
  import { config } from '$lib/store/config.svelte';
  import { rulerTicks } from '$lib/units';

  const RULER_H = 22;
  const EXTRA_W = 400; // px of ruler beyond page.width

  const page      = $derived(editor.template.page);
  const rulerWidth = $derived(page.width + EXTRA_W);
  const ticks      = $derived(rulerTicks(rulerWidth, config.config.units));

  // Net content width = page width minus both margins; cells should stay within this
  const contentWidth = $derived(page.width - page.marginLeft - page.marginRight);
</script>

<svg
  width={rulerWidth}
  height={RULER_H}
  style="display: block; flex-shrink: 0; overflow: visible;"
  aria-hidden="true"
>
  <!-- Content area tint (from x=0 to net content width) -->
  <rect
    x={0} y={0}
    width={contentWidth} height={RULER_H}
    fill="#dbeafe" opacity="0.5"
  />

  <!-- Tick marks -->
  {#each ticks as tick (tick.x)}
    <line
      x1={tick.x} y1={RULER_H - tick.h}
      x2={tick.x} y2={RULER_H}
      stroke="#94a3b8" stroke-width="0.5"
    />
    {#if tick.label}
      <text
        x={tick.x + 2} y={RULER_H - tick.h}
        font-size="8" fill="#64748b"
        font-family="ui-monospace, monospace"
        dominant-baseline="hanging"
      >{tick.label}</text>
    {/if}
  {/each}

  <!-- Content width boundary (sum of both margins subtracted) -->
  <line
    x1={contentWidth} y1={0} x2={contentWidth} y2={RULER_H}
    stroke="#3b82f6" stroke-width="1"
  />

  <!-- Page right edge -->
  <line
    x1={page.width} y1={0} x2={page.width} y2={RULER_H}
    stroke="#475569" stroke-width="1.5"
  />
</svg>
