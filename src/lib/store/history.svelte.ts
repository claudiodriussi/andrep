import type { Template } from '$lib/types';

const MAX = 100;

class HistoryState {
  past = $state<string[]>([]);
  future = $state<string[]>([]);

  get canUndo() { return this.past.length > 0; }
  get canRedo() { return this.future.length > 0; }

  push(template: Template) {
    this.past.push(JSON.stringify(template));
    if (this.past.length > MAX) this.past.shift();
    this.future = [];
  }

  undo(current: Template): Template | null {
    if (this.past.length === 0) return null;
    this.future.push(JSON.stringify(current));
    return JSON.parse(this.past.pop()!);
  }

  redo(current: Template): Template | null {
    if (this.future.length === 0) return null;
    this.past.push(JSON.stringify(current));
    return JSON.parse(this.future.pop()!);
  }

  clear() {
    this.past = [];
    this.future = [];
  }
}

export const history = new HistoryState();
