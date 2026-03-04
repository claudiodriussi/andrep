import type { EditorConfig } from '$lib/types';

const STORAGE_KEY = 'andrep-config';

const DEFAULT_CONFIG: EditorConfig = {
  _type: 'andrep-config',
  locale: 'en',
  units: 'px',
  toolbarGroups: ['colors', 'borders', 'font', 'align', 'cell', 'structure'],
  defaultFont: 'Arial',
  defaultFontSize: 11,
  bandNamePresets: ['Header', 'Band', 'Footer', 'Title', 'Group', 'Total'],
  // Foreground palette: dark tones suitable for text and borders
  fgPalette: [
    '#000000', '#1f2937', '#374151', '#6b7280', '#9ca3af', '#d1d5db', '#ffffff',
    '#dc2626', '#ea580c', '#d97706', '#ca8a04', '#16a34a', '#0284c7', '#2563eb',
    '#4f46e5', '#7c3aed', '#be185d', '#0f766e',
  ],
  // Background palette: light tones suitable for cell backgrounds
  bgPalette: [
    '#ffffff', '#f9fafb', '#f3f4f6', '#e5e7eb', '#d1d5db', '#9ca3af',
    '#fef2f2', '#fee2e2', '#fff7ed', '#ffedd5', '#fefce8', '#fef9c3',
    '#f0fdf4', '#dcfce7', '#eff6ff', '#dbeafe', '#fdf4ff', '#f3e8ff',
  ],
};

function loadConfig(): EditorConfig {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...DEFAULT_CONFIG };
    const data = JSON.parse(raw);
    if (data?._type !== 'andrep-config') return { ...DEFAULT_CONFIG };
    // Merge with defaults so new fields added in future versions are populated
    return { ...DEFAULT_CONFIG, ...data };
  } catch {
    return { ...DEFAULT_CONFIG };
  }
}

class ConfigState {
  config = $state<EditorConfig>(loadConfig());

  save() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.config));
    } catch {
      // localStorage may be unavailable (private browsing, storage quota, etc.)
    }
  }

  saveJson() {
    const json = JSON.stringify(this.config, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'andrep-config.json';
    a.click();
    URL.revokeObjectURL(url);
  }

  loadJson() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json,application/json';
    input.onchange = async () => {
      const file = input.files?.[0];
      if (!file) return;
      try {
        const text = await file.text();
        const data = JSON.parse(text);
        if (data?._type !== 'andrep-config') {
          alert('Invalid file: not an AndRep config.');
          return;
        }
        // Merge with defaults to handle missing fields from older config files
        this.config = { ...DEFAULT_CONFIG, ...data };
        this.save();
      } catch {
        alert('Invalid JSON file.');
      }
    };
    input.click();
  }

  reset() {
    this.config = { ...DEFAULT_CONFIG };
    this.save();
  }
}

export const config = new ConfigState();
