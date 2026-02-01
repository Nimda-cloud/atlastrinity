import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles/global.css';

// Suppress DevTools-related console errors
// Suppress DevTools-related console errors
const originalConsoleError = console.error;
const originalConsoleWarn = console.warn;

console.warn = (...args) => {
  const message = args[0];
  if (typeof message === 'string') {
    // Suppress Google Maps depreciation warning
    if (message.includes('google.maps.places.Autocomplete is not available')) return;
    // Suppress Electron Security Warning in renderer console
    if (message.includes('Insecure Content-Security-Policy')) return;
  }
  originalConsoleWarn.apply(console, args);
};

console.error = (...args) => {
  const message = args[0];
  if (
    typeof message === 'string' &&
    (message.includes('devtools://') ||
      (message.includes('Failed to fetch') && message.includes('devtools')))
  ) {
    // Suppress DevTools-related errors
    return;
  }
  originalConsoleError.apply(console, args);
};

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
