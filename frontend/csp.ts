import type { Plugin } from 'vite'

export function origin(url: string | undefined): string | null {
  if (!url) return null
  try {
    return new URL(url).origin
  } catch {
    return null
  }
}

export function buildPolicy(env: Record<string, string>): string {
  const connect = ["'self'", origin(env.VITE_API_URL), origin(env.VITE_AGENT_URL)].filter(Boolean)
  return [
    "default-src 'self'",
    "script-src 'self'",
    // Leaflet and React set inline style attributes
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: https://tile.openstreetmap.org",
    "font-src 'self'",
    `connect-src ${[...new Set(connect)].join(' ')}`,
    "base-uri 'none'",
    "object-src 'none'",
    "form-action 'self'",
  ].join('; ')
}

/**
 * Content-Security-Policy as a <meta> tag, production build only: the dev server
 * injects inline scripts (HMR, React refresh) that a strict policy would block.
 * HTTP-only directives (frame-ancestors, HSTS) belong to the hosting headers (T24).
 */
export function contentSecurityPolicy(env: Record<string, string>): Plugin {
  const policy = buildPolicy(env)
  return {
    name: 'kryzio-csp',
    apply: 'build',
    transformIndexHtml: () => [
      {
        tag: 'meta',
        attrs: { 'http-equiv': 'Content-Security-Policy', content: policy },
        injectTo: 'head-prepend',
      },
    ],
  }
}
