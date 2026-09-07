import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import ConnectionCenter from './ConnectionCenter';
import FreeConnectorPanel from './FreeConnectorPanel';
import ThemeController from './ThemeController';
import './styles.css';
import './post-explorer.css';
import './premium-ui.css';
import './post-toolbar.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeController />
    <App />
    <ConnectionCenter />
    <FreeConnectorPanel />
  </React.StrictMode>,
);
