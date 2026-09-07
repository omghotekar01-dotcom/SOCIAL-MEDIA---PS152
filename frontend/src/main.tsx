import React from 'react';
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

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeController />
    <AppErrorBoundary>
      <App />
      <ConnectionCenter />
      <FreeConnectorPanel />
    </AppErrorBoundary>
  </React.StrictMode>,
);
