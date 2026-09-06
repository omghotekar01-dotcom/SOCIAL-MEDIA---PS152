import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import FreeConnectorPanel from './FreeConnectorPanel';
import './styles.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <FreeConnectorPanel />
    <App />
  </React.StrictMode>,
);
