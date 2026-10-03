export const config = {
  apiUrl: import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
  agentUrl: import.meta.env.VITE_AGENT_URL ?? 'http://localhost:8001',
  demoMode: import.meta.env.VITE_DEMO_MODE === 'true',
}
