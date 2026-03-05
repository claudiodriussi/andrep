<script lang="ts">
  import { _ } from '$lib/i18n/index.svelte';

  let {
    value,
    palette,
    disabled = false,
    mixed = false,
    transparent = false,
    onpick,
  }: {
    value: string;
    palette: string[];
    disabled?: boolean;
    mixed?: boolean;
    transparent?: boolean;
    onpick: (color: string) => void;
  } = $props();

  let open = $state(false);
  let nativeInput = $state<HTMLInputElement | null>(null);

  // Value passed to the native picker (not meaningful when mixed/transparent)
  const pickerValue = $derived(mixed || transparent ? '#000000' : value);

  function pick(color: string) {
    onpick(color);
    open = false;
  }

  function toggle() {
    if (!disabled) open = !open;
  }
</script>

<div class="cp-wrap">
  <button
    class="cp-trigger"
    class:cp-mixed={mixed}
    class:cp-transparent={transparent}
    style={mixed || transparent ? '' : `background: ${value}`}
    onclick={toggle}
    {disabled}
    title={value}
  ></button>

  {#if open}
    <!-- svelte-ignore a11y_interactive_supports_focus -->
    <div
      class="cp-backdrop"
      role="button"
      aria-label="Close"
      onclick={() => (open = false)}
      onkeydown={(e) => e.key === 'Escape' && (open = false)}
    ></div>

    <div class="cp-dropdown">
      <div class="cp-grid">
        {#each palette as color}
          <button
            class="cp-swatch"
            class:cp-active={!mixed && !transparent && color === value}
            style="background: {color}"
            onclick={() => pick(color)}
            title={color}
          ></button>
        {/each}
      </div>

      <div class="cp-sep"></div>

      <div class="cp-other">
        <!-- hidden native color input -->
        <input
          bind:this={nativeInput}
          type="color"
          value={pickerValue}
          class="cp-hidden"
          onchange={(e) => pick((e.target as HTMLInputElement).value)}
        />
        <!-- current color preview -->
        <div
          class="cp-current"
          class:cp-mixed={mixed}
          class:cp-transparent={transparent}
          style={mixed || transparent ? '' : `background: ${value}`}
        ></div>
        <button class="cp-other-btn" onclick={() => nativeInput?.click()}>
          {_('Other')}…
        </button>
      </div>
    </div>
  {/if}
</div>

<style>
  .cp-wrap {
    position: relative;
    display: inline-flex;
    align-items: center;
  }

  .cp-trigger {
    width: 22px;
    height: 22px;
    border: 1px solid #94a3b8;
    border-radius: 3px;
    cursor: pointer;
    padding: 0;
    flex-shrink: 0;
  }

  .cp-trigger:disabled {
    cursor: default;
    opacity: 0.4;
  }

  .cp-trigger.cp-mixed,
  .cp-current.cp-mixed {
    background-image: repeating-linear-gradient(
      45deg,
      #aaa 0px,
      #aaa 2px,
      #ddd 2px,
      #ddd 5px
    ) !important;
  }

  .cp-trigger.cp-transparent,
  .cp-current.cp-transparent {
    background-image: linear-gradient(45deg, #ccc 25%, transparent 25%),
      linear-gradient(-45deg, #ccc 25%, transparent 25%),
      linear-gradient(45deg, transparent 75%, #ccc 75%),
      linear-gradient(-45deg, transparent 75%, #ccc 75%);
    background-size: 6px 6px;
    background-position:
      0 0,
      0 3px,
      3px -3px,
      -3px 0px;
  }

  .cp-backdrop {
    position: fixed;
    inset: 0;
    z-index: 100;
  }

  .cp-dropdown {
    position: absolute;
    top: calc(100% + 4px);
    left: 0;
    background: white;
    border: 1px solid #cbd5e1;
    border-radius: 5px;
    padding: 6px;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.15);
    z-index: 101;
  }

  .cp-grid {
    display: grid;
    grid-template-columns: repeat(9, 18px);
    gap: 3px;
  }

  .cp-swatch {
    width: 18px;
    height: 18px;
    border: 1px solid #e2e8f0;
    border-radius: 2px;
    cursor: pointer;
    padding: 0;
    transition: transform 0.08s;
  }

  .cp-swatch:hover {
    transform: scale(1.25);
    border-color: #64748b;
    z-index: 1;
    position: relative;
  }

  .cp-swatch.cp-active {
    border: 2px solid #2563eb;
    box-shadow: 0 0 0 1px #93c5fd;
  }

  .cp-sep {
    height: 1px;
    background: #e2e8f0;
    margin: 6px 0;
  }

  .cp-other {
    display: flex;
    align-items: center;
    gap: 5px;
  }

  .cp-hidden {
    position: absolute;
    width: 0;
    height: 0;
    opacity: 0;
    pointer-events: none;
  }

  .cp-current {
    width: 18px;
    height: 18px;
    border: 1px solid #94a3b8;
    border-radius: 2px;
    flex-shrink: 0;
  }

  .cp-other-btn {
    flex: 1;
    padding: 2px 6px;
    font-size: 11px;
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    cursor: pointer;
    color: #475569;
    text-align: center;
    white-space: nowrap;
  }

  .cp-other-btn:hover {
    background: #e2e8f0;
    color: #1e293b;
  }
</style>
