import React, { useEffect, useRef, useState } from 'react';
import ReactDOM from 'react-dom/client';
import AppPro from './AppPro';
import AppErrorBoundary from './AppErrorBoundary';
import AudiencePulsePanel from './AudiencePulsePanel';
import ConnectionCenter from './ConnectionCenter';
import FreeConnectorPanel from './FreeConnectorPanel';
import LiveWatchPanel from './LiveWatchPanel';
import ThemeController from './ThemeController';
import { API_BASE } from './api';
import './styles.css';
import './post-explorer.css';
import './premium-ui.css';
import './post-toolbar.css';
import './command-center.css';
import './responsive-pro.css';
import './resilience.css';
import './brand-polish.css';
import './product-polish.css';
import './analysis-pro.css';
import './source-pro.css';
import './view-fixes.css';
import './analysis-hotfix.css';
import './conversation-intelligence.css';
import './audience-pulse.css';
import './live-watch.css';

function NexusRuntime() {
  const [workspaceVersion, setWorkspaceVersion] = useState(0);
  const observedTotal = useRef<number | null>(null);

  useEffect(() => {
    const refreshWorkspace = () => setWorkspaceVersion((value) => value + 1);
    window.addEventListener('nexus:workspace-updated', refreshWorkspace);
    return () => window.removeEventListener('nexus:workspace-updated', refreshWorkspace);
  }, []);

  // Background connector jobs must not make the analyst stare at a blocking
  // spinner. Poll only the lightweight overview count and remount the console
  // when evidence actually changes. This picks up the exhaustive YouTube crawl
  // after the fast first sample has already made the UI usable.
  useEffect(() => {
    let disposed = false;
    const probe = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/overview`, { cache: 'no-store' });
        if (!response.ok) return;
        const payload = await response.json() as { total_events?: number };
        const next = Number(payload.total_events ?? 0);
        if (observedTotal.current === null) {
          observedTotal.current = next;
          return;
        }
        if (next !== observedTotal.current) {
          observedTotal.current = next;
          if (!disposed) setWorkspaceVersion((value) => value + 1);
        }
      } catch {
        // The normal app health/error surfaces handle backend outages.
      }
    };

    void probe();
    const timer = window.setInterval(() => void probe(), 5000);
    return () => {
      disposed = true;
      window.clearInterval(timer);
    };
  }, []);

  return (
    <>
      <ThemeController />
      <AppErrorBoundary>
        <AppPro key={workspaceVersion} />
        <ConnectionCenter />
        <LiveWatchPanel />
        <AudiencePulsePanel />
        <FreeConnectorPanel />
      </AppErrorBoundary>
    </>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <NexusRuntime />
  </React.StrictMode>,
);
