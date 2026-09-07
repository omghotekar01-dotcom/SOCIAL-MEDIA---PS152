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
    const themeMeta = document.querySelector<HTMLMetaElement>('meta[name="theme-color"]');
    themeMeta?.setAttribute('content', theme === 'dark' ? '#0b0e14' : '#f5f7fb');
    try { window.localStorage.setItem(STORAGE_KEY, theme); } catch { /* noop */ }
  }, [theme]);

  // Free Source Lab intentionally updates the active evidence workspace without
  // forcing each connector component to know about App's internal React state.
  // A short reload makes every dashboard view, chart and evidence count converge
  // on the same backend snapshot after a successful connector action.
  useEffect(() => {
    let timer: number | undefined;
    const onWorkspaceUpdated = () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(() => window.location.reload(), 180);
    };
    window.addEventListener('nexus:workspace-updated', onWorkspaceUpdated);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener('nexus:workspace-updated', onWorkspaceUpdated);
    };
  }, []);

  useEffect(() => {
    const syncNetworkState = () => {
      document.documentElement.dataset.network = navigator.onLine ? 'online' : 'offline';
    };
    syncNetworkState();
    window.addEventListener('online', syncNetworkState);
    window.addEventListener('offline', syncNetworkState);
    return () => {
      window.removeEventListener('online', syncNetworkState);
      window.removeEventListener('offline', syncNetworkState);
    };
  }, []);

  const next = theme === 'light' ? 'dark' : 'light';

  return (
    <button
      className="theme-switcher"
      type="button"
      onClick={() => setTheme(next)}
      aria-label={`Switch to ${next} mode`}
      aria-pressed={theme === 'dark'}
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
