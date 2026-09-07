import React, { useEffect, useState } from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import AppErrorBoundary from './AppErrorBoundary';
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
        <App key={workspaceVersion} />
        <ConnectionCenter />
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
