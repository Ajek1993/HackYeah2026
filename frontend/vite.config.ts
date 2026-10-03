/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'
import { contentSecurityPolicy } from './csp.js'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_')
  return {
    plugins: [react(), tailwindcss(), contentSecurityPolicy(env)],
    server: {
      host: true,
      port: 5173,
      // File events do not reach the container through a Windows bind mount; poll instead.
      watch:
        process.env.VITE_USE_POLLING === 'true' ? { usePolling: true, interval: 300 } : undefined,
    },
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: ['./src/test/setup.ts'],
    },
  }
})
