import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
// Self-hosted font: no request to Google Fonts, so the user's IP stays with us (GDPR)
import '@fontsource/atkinson-hyperlegible-next/400.css'
import '@fontsource/atkinson-hyperlegible-next/600.css'
import '@fontsource/atkinson-hyperlegible-next/800.css'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
