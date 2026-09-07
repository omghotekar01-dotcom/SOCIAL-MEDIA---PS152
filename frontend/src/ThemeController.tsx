import { useEffect, useState } from 'react';
import { Moon, Sun } from 'lucide-react';

type Theme = 'light' | 'dark';

const STORAGE_KEY = 'nexus-theme';

function initialTheme(): Theme {
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (saved === 'dark' || saved === 'light') return saved;
  } catch {
    // Local storage can be unavailable in hardened/private browser contexts.
  }
  return 'light';
}

export default function ThemeController() {
  const [theme, setTheme] = useState<Theme>(initialTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    try { window.localStorage.setItem(STORAGE_KEY, theme); } catch { /* noop */ }
  }, [theme]);

  const next = theme === 'light' ? 'dark' : 'light';

  return (
    <button
      className="theme-switcher"
      type="button"
      onClick={() => setTheme(next)}
      aria-label={`Switch to ${next} mode`}
      title={`Switch to ${next} mode`}
    >
      <span className="theme-switcher-icon">{theme === 'light' ? <Sun size={16} /> : <Moon size={16} />}</span>
      <span className="theme-switcher-copy">
        <b>{theme === 'light' ? 'Light' : 'Dark'}</b>
        <small>Theme</small>
      </span>
    </button>
  );
}
