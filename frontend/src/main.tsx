import React, { useEffect, useState } from 'react';
import ReactDOM from 'react-dom/client';
import AppPro from './AppPro';
import AppErrorBoundary from './AppErrorBoundary';
import AudiencePulsePanel from './AudiencePulsePanel';
import ConnectionCenter from './ConnectionCenter';
import FreeConnectorPanel from './FreeConnectorPanel';
import ThemeController from './ThemeController';
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

function NexusRuntime() {
  const [workspaceVersion, setWorkspaceVersion] = useState(0);

  useEffect(() => {
    const refreshWorkspace = () => setWorkspaceVersion((value) => value + 1);
    window.addEventListener('nexus:workspace-updated', refreshWorkspace);
    return () => window.removeEventListener('nexus:workspace-updated', refreshWorkspace);
  }, []);

  return (
    <>
      <ThemeController />
      <AppErrorBoundary>
        <AppPro key={workspaceVersion} />
        <ConnectionCenter />
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
