function ensureTrailingSlash(url: string): string {
  return url.endsWith('/') ? url : url + '/'
}

export const config = {
  apiUrl: ensureTrailingSlash(import.meta.env.VITE_API_URL ?? 'http://localhost:8000'),
  agentUrl: import.meta.env.VITE_AGENT_URL ?? 'http://localhost:8001',
  demoMode: import.meta.env.VITE_DEMO_MODE === 'true',
  // Ships in the presentation bundle: guards only against accidental scenario switching
  demoToken: import.meta.env.VITE_DEMO_TOKEN ?? '',
}
