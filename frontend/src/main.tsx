import React, { useEffect, useRef, useState } from 'react';
import ReactDOM from 'react-dom/client';
import AppPro from './AppPro';
import AppErrorBoundary from './AppErrorBoundary';
import AudiencePulsePanel from './AudiencePulsePanel';
import ConnectionCenter from './ConnectionCenter';
import PrototypeSourceCenter from './PrototypeSourceCenter';
import PS26152AuditPanel from './PS26152AuditPanel';
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
import './ps26152-audit.css';
import './ps26152-network.css';
import './prototype-source-center.css';

function NexusRuntime() {
  const [workspaceVersion, setWorkspaceVersion] = useState(0);
  const youtubeFingerprint = useRef<string | null>(null);

  useEffect(() => {
    const refreshWorkspace = () => setWorkspaceVersion((value) => value + 1);
    window.addEventListener('nexus:workspace-updated', refreshWorkspace);
    return () => window.removeEventListener('nexus:workspace-updated', refreshWorkspace);
  }, []);

  // Exact YouTube URLs return a fast analytical sample while the server continues
  // the provider-bounded comment/reply crawl. Probe one lightweight root record so
  // the main dashboard refreshes when the background state/count changes without
  // repeatedly recalculating heavy analytics during collection.
  useEffect(() => {
    let disposed = false;
    const probe = async () => {
      try {
        const response = await fetch(
          `${API_BASE}/api/events?limit=1&platform=youtube&newest_first=false`,
          { cache: 'no-store' },
        );
        if (!response.ok) return;
        const payload = await response.json() as {
          events?: Array<{
            id: string;
            public_profile?: Record<string, unknown>;
          }>;
        };
        const root = payload.events?.[0];
        if (!root) {
          youtubeFingerprint.current = null;
          return;
        }
        const profile = root.public_profile || {};
        const state = String(profile.background_collection_state || 'idle');
        const captured = Number(profile.captured_comment_count || 0);
        const stopReason = String(profile.collection_stop_reason || '');
        const fingerprint = `${root.id}|${state}|${captured}|${stopReason}`;

        if (youtubeFingerprint.current === null) {
          youtubeFingerprint.current = fingerprint;
          return;
        }
        if (fingerprint !== youtubeFingerprint.current) {
          youtubeFingerprint.current = fingerprint;
          if (!disposed) setWorkspaceVersion((value) => value + 1);
        }
      } catch {
        // Normal NEXUS health/error surfaces handle backend outages.
      }
    };

    void probe();
    const timer = window.setInterval(() => void probe(), 4000);
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
        <AudiencePulsePanel />
        <PrototypeSourceCenter />
        <PS26152AuditPanel />
      </AppErrorBoundary>
    </>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <NexusRuntime />
  </React.StrictMode>,
);
