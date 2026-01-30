import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles/global.css';

// Suppress DevTools-related console errors
const originalConsoleError = console.error;
console.error = (...args) => {
  const message = args[0];
  if (typeof message === 'string' && 
      (message.includes('devtools://') || 
       (message.includes('Failed to fetch') && message.includes('devtools')))) {
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
