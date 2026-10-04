/**
 * Application entry point (Task 14.1).
 *
 * Mounts the React tree into the `#root` element declared in `index.html`.
 */
import React from 'react';
import ReactDOM from 'react-dom/client';

import App from './App';
import './styles.css';

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error('Root element #root not found in index.html');
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
