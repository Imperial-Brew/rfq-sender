import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

/**
 * Entry point. React finds the <div id="root"> in index.html and takes
 * over that element — everything rendered by the app lives inside it.
 *
 * StrictMode runs your components twice in development to catch bugs
 * (like effects that don't clean up). It has no effect in production.
 */
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
